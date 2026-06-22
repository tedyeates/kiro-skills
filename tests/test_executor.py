"""Tests for executor module — implement and review phases."""

import asyncio
from unittest.mock import patch, call, MagicMock

import pytest

from wave_runner.agent import AgentResult
from wave_runner.config import Config
from wave_runner.executor import run_wave, _run_task, _invoke_with_retry
from wave_runner.hooks import PreReviewOutput
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


class TestInvokeWithRetry:
    """Test retry logic for transient agent failures."""

    @patch("wave_runner.executor.invoke_agent")
    def test_returns_immediately_on_success(self, mock_agent):
        mock_agent.return_value = AgentResult(success=True, reason=None, stdout="ok")
        result = _invoke_with_retry("implementer", "do it", "/work")
        assert result.success is True
        assert mock_agent.call_count == 1

    @patch("wave_runner.executor.invoke_agent")
    def test_retries_on_no_result_line(self, mock_agent):
        mock_agent.side_effect = [
            AgentResult(success=False, reason="no result line", stdout=""),
            AgentResult(success=True, reason=None, stdout="ok"),
        ]
        result = _invoke_with_retry("implementer", "do it", "/work")
        assert result.success is True
        assert mock_agent.call_count == 2

    @patch("wave_runner.executor.invoke_agent")
    def test_no_retry_on_real_failure(self, mock_agent):
        mock_agent.return_value = AgentResult(success=False, reason="tests broke", stdout="")
        result = _invoke_with_retry("implementer", "do it", "/work")
        assert result.success is False
        assert mock_agent.call_count == 1


class TestRunTask:
    """Test _run_task handles implement→review pipeline stages."""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, config, feature_branch, design_path, worktree_base):
        """FULL stage: implementer succeeds → tests pass → review_loop succeeds → label merging."""
        planned = make_planned(10, PipelineStage.FULL)

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor._run_tests") as mock_tests, \
             patch("wave_runner.executor.review_loop") as mock_review:

            mock_impl.return_value = AgentResult(success=True, reason=None, stdout="done")
            mock_tests.return_value = True
            mock_review.return_value = AgentResult(success=True, reason=None, stdout="reviewed")

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is True
        assert result.number == 10
        mock_git.create_worktree.assert_called_once()
        assert mock_gh.update_label.call_args_list == [
            call(10, "implementing", "reviewing", "owner/repo"),
            call(10, "reviewing", "merging", "owner/repo"),
        ]

    @pytest.mark.asyncio
    async def test_implementer_failure(self, config, feature_branch, design_path, worktree_base):
        """Implementer fails → label impl-failed, no reviewer."""
        planned = make_planned(10, PipelineStage.FULL)

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor.review_loop") as mock_review:

            mock_impl.return_value = AgentResult(success=False, reason="tests broke", stdout="")

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is False
        mock_gh.update_label.assert_called_once_with(10, "implementing", "impl-failed", "owner/repo")
        mock_review.assert_not_called()

    @pytest.mark.asyncio
    async def test_post_implement_test_failure(self, config, feature_branch, design_path, worktree_base):
        """Implementer claims success but tests fail → impl-failed."""
        planned = make_planned(10, PipelineStage.FULL)

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor._run_tests") as mock_tests, \
             patch("wave_runner.executor.review_loop") as mock_review:

            mock_impl.return_value = AgentResult(success=True, reason=None, stdout="done")
            mock_tests.return_value = False

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is False
        mock_gh.update_label.assert_called_once_with(10, "implementing", "impl-failed", "owner/repo")
        mock_review.assert_not_called()

    @pytest.mark.asyncio
    async def test_reviewer_failure(self, config, feature_branch, design_path, worktree_base):
        """Implementer succeeds but reviewer fails → label review-failed."""
        planned = make_planned(10, PipelineStage.FULL)

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor._run_tests") as mock_tests, \
             patch("wave_runner.executor.review_loop") as mock_review:

            mock_impl.return_value = AgentResult(success=True, reason=None, stdout="done")
            mock_tests.return_value = True
            mock_review.return_value = AgentResult(success=False, reason="lint errors", stdout="")

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is False
        assert mock_gh.update_label.call_args_list == [
            call(10, "implementing", "reviewing", "owner/repo"),
            call(10, "reviewing", "review-failed", "owner/repo"),
        ]

    @pytest.mark.asyncio
    async def test_review_stage_skips_implementer(self, config, feature_branch, design_path, worktree_base):
        """REVIEW stage: skip implementer, run review_loop directly."""
        planned = make_planned(10, PipelineStage.REVIEW)
        planned.task.labels = ["reviewing"]

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor.review_loop") as mock_review:

            mock_review.return_value = AgentResult(success=True, reason=None, stdout="reviewed")

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is True
        mock_impl.assert_not_called()
        mock_gh.update_label.assert_called_once_with(10, "reviewing", "merging", "owner/repo")

    @pytest.mark.asyncio
    async def test_merge_stage_skips_both(self, config, feature_branch, design_path, worktree_base):
        """MERGE stage: no agents invoked, result is immediately success."""
        planned = make_planned(10, PipelineStage.MERGE)
        planned.task.labels = ["merging"]

        with patch("wave_runner.executor.git") as mock_git, \
             patch("wave_runner.executor.github") as mock_gh, \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor.review_loop") as mock_review:

            sem = asyncio.Semaphore(2)
            result = await _run_task(planned, config, feature_branch, design_path, worktree_base, sem)

        assert result.success is True
        mock_impl.assert_not_called()
        mock_review.assert_not_called()
        mock_gh.update_label.assert_not_called()


class TestRunWave:
    """Test run_wave orchestrates tasks in bounded parallel."""

    @pytest.mark.asyncio
    async def test_runs_tasks_in_parallel_respects_concurrency(self, config, feature_branch, design_path, worktree_base):
        """All tasks in wave run, bounded by semaphore."""
        wave = [make_planned(i, PipelineStage.FULL) for i in range(1, 4)]

        with patch("wave_runner.executor.git"), \
             patch("wave_runner.executor.github"), \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor._run_tests") as mock_tests, \
             patch("wave_runner.executor.review_loop") as mock_review:

            mock_impl.return_value = AgentResult(success=True, reason=None, stdout="done")
            mock_tests.return_value = True
            mock_review.return_value = AgentResult(success=True, reason=None, stdout="reviewed")

            results = await run_wave(wave, config, feature_branch, design_path, worktree_base)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_partial_failure_returns_all_results(self, config, feature_branch, design_path, worktree_base):
        """If some tasks fail, all results still returned."""
        wave = [make_planned(1, PipelineStage.FULL), make_planned(2, PipelineStage.FULL)]

        with patch("wave_runner.executor.git"), \
             patch("wave_runner.executor.github"), \
             patch("wave_runner.executor._invoke_with_retry") as mock_impl, \
             patch("wave_runner.executor._run_tests") as mock_tests, \
             patch("wave_runner.executor.review_loop") as mock_review:

            def impl_side_effect(name, prompt, cwd):
                if "#2" in prompt:
                    return AgentResult(success=False, reason="broken", stdout="")
                return AgentResult(success=True, reason=None, stdout="done")

            mock_impl.side_effect = impl_side_effect
            mock_tests.return_value = True
            mock_review.return_value = AgentResult(success=True, reason=None, stdout="reviewed")

            results = await run_wave(wave, config, feature_branch, design_path, worktree_base)

        assert len(results) == 2
        outcomes = {r.number: r.success for r in results}
        assert outcomes[2] is False
        assert outcomes[1] is True
