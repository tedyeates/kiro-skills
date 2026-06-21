"""Tests for GitHub mutation functions — verify correct shell commands constructed."""

from unittest.mock import patch, call
import subprocess

import pytest

from wave_runner.github import update_label, post_comment, close_issue, create_pr


@patch("wave_runner.github.subprocess.run")
def test_update_label(mock_run):
    update_label(42, "ready-for-agent", "implementing", "owner/repo")
    mock_run.assert_called_once_with(
        ["gh", "issue", "edit", "42", "--remove-label", "ready-for-agent", "--add-label", "implementing", "--repo", "owner/repo"],
        check=True,
        capture_output=True,
    )


@patch("wave_runner.github.subprocess.run")
def test_post_comment(mock_run):
    post_comment(7, "Wave complete: 3/3 merged", "owner/repo")
    mock_run.assert_called_once_with(
        ["gh", "issue", "comment", "7", "--body", "Wave complete: 3/3 merged", "--repo", "owner/repo"],
        check=True,
        capture_output=True,
    )


@patch("wave_runner.github.subprocess.run")
def test_close_issue(mock_run):
    close_issue(19, "owner/repo")
    mock_run.assert_called_once_with(
        ["gh", "issue", "close", "19", "--repo", "owner/repo"],
        check=True,
        capture_output=True,
    )


@patch("wave_runner.github.subprocess.run")
def test_create_pr(mock_run):
    create_pr("feature/wave-runner", "main", "feat: wave runner", "Closes #12", "owner/repo")
    mock_run.assert_called_once_with(
        ["gh", "pr", "create", "--head", "feature/wave-runner", "--base", "main", "--title", "feat: wave runner", "--body", "Closes #12", "--repo", "owner/repo"],
        check=True,
        capture_output=True,
    )


@patch("wave_runner.github.subprocess.run")
def test_update_label_raises_on_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr="not found")
    with pytest.raises(subprocess.CalledProcessError):
        update_label(99, "old", "new", "owner/repo")


@patch("wave_runner.github.subprocess.run")
def test_post_comment_raises_on_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr="auth required")
    with pytest.raises(subprocess.CalledProcessError):
        post_comment(7, "msg", "owner/repo")


@patch("wave_runner.github.subprocess.run")
def test_close_issue_raises_on_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr="rate limited")
    with pytest.raises(subprocess.CalledProcessError):
        close_issue(19, "owner/repo")


@patch("wave_runner.github.subprocess.run")
def test_create_pr_raises_on_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "gh", stderr="already exists")
    with pytest.raises(subprocess.CalledProcessError):
        create_pr("feat/x", "main", "title", "body", "owner/repo")
