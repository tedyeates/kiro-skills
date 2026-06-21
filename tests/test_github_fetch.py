"""Tests for GitHub fetch functions — verify correct gh api calls and response parsing."""

import json
from unittest.mock import patch, MagicMock

import pytest

from wave_runner.github import fetch_prd, fetch_sub_issues


@patch("wave_runner.github.subprocess.run")
def test_fetch_prd_returns_title_body_design_path(mock_run):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({
            "title": "Wave Runner PRD",
            "body": "Some intro\n\nDesign: .kiro/specs/wave-runner/design.md\n\nMore text",
        })
    )
    result = fetch_prd(12, "owner/repo")
    mock_run.assert_called_once_with(
        ["gh", "api", "repos/owner/repo/issues/12", "--jq", "{title: .title, body: .body}"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result["title"] == "Wave Runner PRD"
    assert result["body"].startswith("Some intro")
    assert result["design_path"] == ".kiro/specs/wave-runner/design.md"


@patch("wave_runner.github.subprocess.run")
def test_fetch_prd_no_design_path(mock_run):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({
            "title": "No design",
            "body": "Just a body with no design line",
        })
    )
    result = fetch_prd(5, "owner/repo")
    assert result["design_path"] is None


@patch("wave_runner.github.subprocess.run")
def test_fetch_sub_issues_returns_tasks_with_blockers(mock_run):
    sub_issues_response = json.dumps([
        {"id": 100, "number": 13, "title": "Task A", "state": "open", "labels": [{"name": "ready-for-agent"}]},
        {"id": 101, "number": 14, "title": "Task B", "state": "closed", "labels": [{"name": "implementing"}]},
    ])
    blockers_a = json.dumps([{"number": 14, "state": "closed"}])
    blockers_b = json.dumps([])

    mock_run.side_effect = [
        MagicMock(stdout=sub_issues_response),
        MagicMock(stdout=blockers_a),
        MagicMock(stdout=blockers_b),
    ]

    tasks = fetch_sub_issues(12, "owner/repo")

    assert len(tasks) == 2
    assert tasks[0]["number"] == 13
    assert tasks[0]["title"] == "Task A"
    assert tasks[0]["state"] == "open"
    assert tasks[0]["labels"] == ["ready-for-agent"]
    assert tasks[0]["blockers"] == [14]
    assert tasks[1]["number"] == 14
    assert tasks[1]["blockers"] == []


@patch("wave_runner.github.subprocess.run")
def test_fetch_sub_issues_empty(mock_run):
    mock_run.return_value = MagicMock(stdout=json.dumps([]))
    tasks = fetch_sub_issues(12, "owner/repo")
    assert tasks == []
