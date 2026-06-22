"""Tests for executor module — implement and review phases."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from wave_runner.agent import AgentResult
from wave_runner.config import Config
from wave_runner.executor import run_wave, _run_task
from wave_runner.models import PlannedTask, PipelineStage, Task, TaskResult, TaskState


@pytest.fixture
def config():
    return Config(repo="owner/repo", test_command="pytest", concurrency=2)


@pytest.fixture
def feature_branch():
    return "feature/42-my-feature"


@pytest.fixture
def design_path():
    return ".kiro/specs/wave-runner/design.md"


@pytest.fixture
def worktree_base():
    return "D:/Projects/repo-waves/prd/42"


def make_planned(number: int, stage: PipelineStage = PipelineStage.FULL) -> PlannedTask:
    return PlannedTask(task=Task(number=number, state=TaskState.OPEN, labels=["implementing"]), stage=stage)


class TestRunTask:
    """Test _run_task handles implement→review pipeline stages."""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, config, feature_branch, design_path, worktree_base):
        """FULL stage: implementer succeeds → label reviewing → reviewer succeeds → label merging."""
        planned = make_planned(10, PipelineStage.FULL)

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor.invoke_agent") as mock_agent:

            mock_agent.side_effect = [
                AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS"),
                AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS"),
            ]

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is True
        assert result.number == 10
        # Should create worktree
        mock_git.create_worktree.assert_called_once()
        # Label transitions: implementing→reviewing, then reviewing→merging
        assert mock_gh.update_label.call_args_list == [
            call(10, "implementing", "reviewing", "owner/repo"),
            call(10, "reviewing", "merging", "owner/repo"),
        ]

    @pytest.mark.asyncio
    async def test_implementer_failure(self, config, feature_branch, design_path, worktree_base):
        """Implementer fails → label impl-failed, post comment, no reviewer."""
        planned = make_planned(10, PipelineStage.FULL)

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor.invoke_agent") as mock_agent:

            mock_agent.return_value = AgentResult(success=False, reason="tests broke", stdout="")

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is False
        mock_gh.update_label.assert_called_once_with(10, "implementing", "impl-failed", "owner/repo")
        mock_gh.post_comment.assert_called_once()
        # Reviewer should not have been invoked
        assert mock_agent.call_count == 1

    @pytest.mark.asyncio
    async def test_reviewer_failure(self, config, feature_branch, design_path, worktree_base):
        """Implementer succeeds but reviewer fails → label review-failed, post comment."""
        planned = make_planned(10, PipelineStage.FULL)

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor.invoke_agent") as mock_agent:

            mock_agent.side_effect = [
                AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS"),
                AgentResult(success=False, reason="lint errors", stdout=""),
            ]

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is False
        assert mock_gh.update_label.call_args_list == [
            call(10, "implementing", "reviewing", "owner/repo"),
            call(10, "reviewing", "review-failed", "owner/repo"),
        ]
        mock_gh.post_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_stage_skips_implementer(self, config, feature_branch, design_path, worktree_base):
        """REVIEW stage: skip implementer, run reviewer directly."""
        planned = make_planned(10, PipelineStage.REVIEW)
        planned.task.labels = ["reviewing"]

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor.invoke_agent") as mock_agent:

            mock_agent.return_value = AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS")

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is True
        # Only reviewer invoked
        assert mock_agent.call_count == 1
        mock_gh.update_label.assert_called_once_with(10, "reviewing", "merging", "owner/repo")

    @pytest.mark.asyncio
    async def test_merge_stage_skips_both(self, config, feature_branch, design_path, worktree_base):
        """MERGE stage: no agents invoked, result is immediately success."""
        planned = make_planned(10, PipelineStage.MERGE)
        planned.task.labels = ["merging"]

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor.invoke_agent") as mock_agent:

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is True
        mock_agent.assert_not_called()
        mock_gh.update_label.assert_not_called()


class TestRunWave:
    """Test run_wave orchestrates tasks in bounded parallel."""

    @pytest.mark.asyncio
    async def test_runs_tasks_in_parallel_respects_concurrency(self, config, feature_branch, design_path, worktree_base):
        """All tasks in wave run, bounded by semaphore."""
        wave = [make_planned(i, PipelineStage.FULL) for i in range(1, 4)]

        with patch("wave_runner.executor.git"), \
             patch("wave_runner.executor.github"), \
             patch("wave_runner.executor.invoke_agent") as mock_agent:

            mock_agent.return_value = AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS")

            results = await run_wave(wave, config, feature_branch, design_path, worktree_base)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_partial_failure_returns_all_results(self, config, feature_branch, design_path, worktree_base):
        """If some tasks fail, all results still returned."""
        wave = [make_planned(1, PipelineStage.FULL), make_planned(2, PipelineStage.FULL)]

        with patch("wave_runner.executor.git"), \
             patch("wave_runner.executor.github"), \
             patch("wave_runner.executor.invoke_agent") as mock_agent:

            # First task: impl succeeds, review succeeds
            # Second task: impl fails
            call_count = [0]
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                # Task 1 calls: impl(1), review(1) = success, success
                # Task 2 calls: impl(2) = failure
                # Order is nondeterministic in parallel, so use prompt to determine
                prompt = args[1] if len(args) > 1 else kwargs.get("prompt", "")
                if "#2" in prompt and "Implement" in prompt:
                    return AgentResult(success=False, reason="broken", stdout="")
                return AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS")

            mock_agent.side_effect = side_effect

            results = await run_wave(wave, config, feature_branch, design_path, worktree_base)

        assert len(results) == 2
        # At least one should have failed
        outcomes = {r.number: r.success for r in results}
        assert outcomes[2] is False
        assert outcomes[1] is True
