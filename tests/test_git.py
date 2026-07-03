"""Tests for wave_runner.git module — verify correct git commands issued via mocked subprocess."""

from unittest.mock import patch, call
import subprocess

import pytest

from wave_runner.git import (
    create_feature_branch,
    create_worktree,
    remove_worktree,
    merge_branch,
    revert_merge,
    push_branch,
)


@pytest.fixture
def mock_run():
    with patch("wave_runner.git.subprocess.run") as mock:
        mock.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        yield mock


class TestCreateFeatureBranch:
    def test_creates_and_checks_out_branch(self, mock_run):
        create_feature_branch("feature/my-feature", "main")

        mock_run.assert_called_once_with(
            ["git", "checkout", "-b", "feature/my-feature", "main"],
            check=True,
            capture_output=True,
            text=True,
        )


class TestCreateWorktree:
    def test_creates_worktree_at_path_on_new_branch(self, mock_run):
        create_worktree("task/16-git-module", "D:/waves/16", "feature/wave-runner")

        mock_run.assert_called_once_with(
            ["git", "worktree", "add", "-b", "task/16-git-module", "D:/waves/16", "feature/wave-runner"],
            check=True,
            capture_output=True,
            text=True,
        )


class TestRemoveWorktree:
    def test_removes_worktree_and_deletes_branch(self, mock_run):
        remove_worktree("D:/waves/16")

        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "worktree", "remove", "D:/waves/16", "--force"],
            check=True,
            capture_output=True,
            text=True,
        )
        # Second call prunes worktree metadata
        mock_run.assert_any_call(
            ["git", "worktree", "prune"],
            check=True,
            capture_output=True,
            text=True,
        )


class TestMergeBranch:
    def test_merge_success(self, mock_run):
        result = merge_branch("task/16-git-module", "D:/feature-dir")

        mock_run.assert_called_once_with(
            ["git", "merge", "task/16-git-module", "--no-edit"],
            check=True,
            capture_output=True,
            text=True,
            cwd="D:/feature-dir",
        )
        assert result == "success"

    def test_merge_conflict(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "git merge", stderr="CONFLICT")

        result = merge_branch("task/16-git-module", "D:/feature-dir")

        assert result == "conflict"


class TestRevertMerge:
    def test_aborts_merge_when_in_conflict_state(self, mock_run):
        # MERGE_HEAD exists → conflict state
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123", stderr="")

        revert_merge("D:/feature-dir")

        assert mock_run.call_count == 2
        # First: check MERGE_HEAD
        mock_run.assert_any_call(
            ["git", "rev-parse", "--verify", "MERGE_HEAD"],
            capture_output=True,
            text=True,
            cwd="D:/feature-dir",
        )
        # Second: merge --abort
        mock_run.assert_any_call(
            ["git", "merge", "--abort"],
            check=True,
            capture_output=True,
            text=True,
            cwd="D:/feature-dir",
        )

    def test_resets_to_parent_when_merge_committed(self, mock_run):
        # MERGE_HEAD doesn't exist → merge was committed
        def side_effect(cmd, **kwargs):
            if cmd == ["git", "rev-parse", "--verify", "MERGE_HEAD"]:
                return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        revert_merge("D:/feature-dir")

        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "reset", "--hard", "HEAD~1"],
            check=True,
            capture_output=True,
            text=True,
            cwd="D:/feature-dir",
        )


class TestPushBranch:
    def test_pushes_with_upstream_flag(self, mock_run):
        push_branch("feature/wave-runner")

        mock_run.assert_called_once_with(
            ["git", "push", "-u", "origin", "feature/wave-runner"],
            check=True,
            capture_output=True,
            text=True,
        )
