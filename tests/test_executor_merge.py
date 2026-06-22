"""Tests for executor merge phase."""

from unittest.mock import patch, call, MagicMock
import subprocess

import pytest

from wave_runner.executor import run_merge_phase
from wave_runner.agent import AgentResult
from wave_runner.models import TaskResult


@pytest.fixture
def config():
    from wave_runner.config import Config
    return Config(repo="owner/repo", test_command="pytest tests/")


def _task_entry(number, branch, worktree_path):
    return {"number": number, "branch": branch, "worktree_path": worktree_path}


class TestSequentialOrdering:
    """Merges happen one at a time in order."""

    @patch("wave_runner.executor.github")
    @patch("wave_runner.executor.git")
    @patch("wave_runner.executor._run_tests")
    def test_merges_sequentially(self, mock_tests, mock_git, mock_gh, config):
        mock_git.merge_branch.return_value = "success"
        mock_tests.return_value = True
        tasks = [
            _task_entry(1, "task/1", "/work/1"),
            _task_entry(2, "task/2", "/work/2"),
            _task_entry(3, "task/3", "/work/3"),
        ]

        results = run_merge_phase(tasks, "feature/main", "/repo", config)

        merge_calls = mock_git.merge_branch.call_args_list
        assert merge_calls == [
            call("task/1", "/repo"),
            call("task/2", "/repo"),
            call("task/3", "/repo"),
        ]
        assert all(r.success for r in results)


class TestSuccessPath:
    """On successful merge + tests: close issue, remove worktree."""

    @patch("wave_runner.executor.github")
    @patch("wave_runner.executor.git")
    @patch("wave_runner.executor._run_tests")
    def test_close_and_cleanup_on_success(self, mock_tests, mock_git, mock_gh, config):
        mock_git.merge_branch.return_value = "success"
        mock_tests.return_value = True
        tasks = [_task_entry(5, "task/5", "/work/5")]

        results = run_merge_phase(tasks, "feature/main", "/repo", config)

        mock_gh.close_issue.assert_called_once_with(5, "owner/repo")
        mock_git.remove_worktree.assert_called_once_with("/work/5")
        assert results[0] == TaskResult(number=5, success=True, branch="task/5")


class TestMergerAgentInvocation:
    """On conflict or test failure, invoke merger agent up to 3 times."""

    @patch("wave_runner.executor.github")
    @patch("wave_runner.executor.git")
    @patch("wave_runner.executor._run_tests")
    @patch("wave_runner.executor.invoke_agent")
    def test_invokes_merger_on_conflict(self, mock_agent, mock_tests, mock_git, mock_gh, config):
        mock_git.merge_branch.return_value = "conflict"
        mock_agent.return_value = AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS")
        mock_tests.return_value = True
        tasks = [_task_entry(7, "task/7", "/work/7")]

        results = run_merge_phase(tasks, "feature/main", "/repo", config)

        assert mock_agent.call_count == 1
        mock_gh.close_issue.assert_called_once_with(7, "owner/repo")
        mock_git.remove_worktree.assert_called_once_with("/work/7")
        assert results[0].success is True

    @patch("wave_runner.executor.github")
    @patch("wave_runner.executor.git")
    @patch("wave_runner.executor._run_tests")
    @patch("wave_runner.executor.invoke_agent")
    def test_invokes_merger_on_test_failure(self, mock_agent, mock_tests, mock_git, mock_gh, config):
        mock_git.merge_branch.return_value = "success"
        # First test fails, agent fixes, second test passes
        mock_tests.side_effect = [False, True]
        mock_agent.return_value = AgentResult(success=True, reason=None, stdout="AGENT_RESULT: SUCCESS")
        tasks = [_task_entry(8, "task/8", "/work/8")]

        results = run_merge_phase(tasks, "feature/main", "/repo", config)

        assert mock_agent.call_count == 1
        assert results[0].success is True

    @patch("wave_runner.executor.github")
    @patch("wave_runner.executor.git")
    @patch("wave_runner.executor._run_tests")
    @patch("wave_runner.executor.invoke_agent")
    def test_retries_merger_up_to_3_times(self, mock_agent, mock_tests, mock_git, mock_gh, config):
        mock_git.merge_branch.return_value = "conflict"
        mock_agent.return_value = AgentResult(success=False, reason="cannot resolve", stdout="")
        tasks = [_task_entry(9, "task/9", "/work/9")]

        results = run_merge_phase(tasks, "feature/main", "/repo", config)

        assert mock_agent.call_count == 3


class TestRevertOnFailure:
    """On unrecoverable merge failure: revert, label merge-failed, post comment."""

    @patch("wave_runner.executor.github")
    @patch("wave_runner.executor.git")
    @patch("wave_runner.executor._run_tests")
    @patch("wave_runner.executor.invoke_agent")
    def test_reverts_and_labels_on_agent_failure(self, mock_agent, mock_tests, mock_git, mock_gh, config):
        mock_git.merge_branch.return_value = "conflict"
        mock_agent.return_value = AgentResult(success=False, reason="cannot resolve", stdout="output")
        tasks = [_task_entry(10, "task/10", "/work/10")]

        results = run_merge_phase(tasks, "feature/main", "/repo", config)

        mock_git.revert_merge.assert_called_once_with("/repo")
        mock_gh.update_label.assert_called_once_with(10, "merging", "merge-failed", "owner/repo")
        mock_gh.post_comment.assert_called_once()
        assert results[0].success is False
        mock_gh.close_issue.assert_not_called()
        mock_git.remove_worktree.assert_not_called()

    @patch("wave_runner.executor.github")
    @patch("wave_runner.executor.git")
    @patch("wave_runner.executor._run_tests")
    @patch("wave_runner.executor.invoke_agent")
    def test_reverts_on_test_failure_after_agent_exhausted(self, mock_agent, mock_tests, mock_git, mock_gh, config):
        mock_git.merge_branch.return_value = "success"
        mock_tests.return_value = False  # Tests always fail
        mock_agent.return_value = AgentResult(success=True, reason=None, stdout="ok")
        tasks = [_task_entry(11, "task/11", "/work/11")]

        results = run_merge_phase(tasks, "feature/main", "/repo", config)

        # 3 agent attempts (test fails each time after agent "succeeds")
        assert mock_agent.call_count == 3
        mock_git.revert_merge.assert_called_once_with("/repo")
        assert results[0].success is False
