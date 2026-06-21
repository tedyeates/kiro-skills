"""Tests for wave_runner.reporter module."""

import os
import tempfile
from unittest.mock import patch

from wave_runner.models import TaskResult
from wave_runner.reporter import terminal_summary, github_comment, append_log


class TestTerminalSummary:
    def test_all_passed(self, capsys):
        results = [
            TaskResult(number=1, success=True, branch="feature/1-foo"),
            TaskResult(number=2, success=True, branch="feature/2-bar"),
        ]
        terminal_summary(results)
        out = capsys.readouterr().out
        assert "✅ #1" in out
        assert "✅ #2" in out

    def test_mixed_results(self, capsys):
        results = [
            TaskResult(number=1, success=True, branch="feature/1-foo"),
            TaskResult(number=2, success=False, branch="feature/2-bar"),
        ]
        terminal_summary(results)
        out = capsys.readouterr().out
        assert "✅ #1" in out
        assert "❌ #2" in out
        assert "feature/2-bar" in out

    def test_failure_shows_branch(self, capsys):
        results = [
            TaskResult(number=5, success=False, branch="feature/5-broken"),
        ]
        terminal_summary(results)
        out = capsys.readouterr().out
        assert "feature/5-broken" in out


class TestGithubComment:
    def test_all_merged(self):
        results = [
            TaskResult(number=1, success=True, branch="feature/1-a"),
            TaskResult(number=2, success=True, branch="feature/2-b"),
        ]
        md = github_comment(results, outstanding=[3, 4])
        assert "## Merged" in md
        assert "#1" in md
        assert "#2" in md
        assert "## Outstanding" in md
        assert "#3" in md
        assert "#4" in md

    def test_with_failures(self):
        results = [
            TaskResult(number=1, success=True, branch="feature/1-a"),
            TaskResult(number=2, success=False, branch="feature/2-bad"),
        ]
        md = github_comment(results, outstanding=[3])
        assert "## Merged" in md
        assert "## Failed" in md
        assert "#2" in md
        assert "feature/2-bad" in md
        assert "## Outstanding" in md

    def test_no_outstanding(self):
        results = [
            TaskResult(number=1, success=True, branch="feature/1-a"),
        ]
        md = github_comment(results, outstanding=[])
        assert "## Merged" in md
        assert "Outstanding" not in md

    def test_no_merged(self):
        results = [
            TaskResult(number=1, success=False, branch="feature/1-bad"),
        ]
        md = github_comment(results, outstanding=[2])
        assert "Merged" not in md
        assert "## Failed" in md


class TestAppendLog:
    def test_appends_failure_details(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_path = f.name

        try:
            results = [
                TaskResult(number=1, success=True, branch="feature/1-a", stdout="ok"),
                TaskResult(number=2, success=False, branch="feature/2-b", stdout="error trace here"),
            ]
            append_log(results, log_path)
            content = open(log_path).read()
            assert "#2" in content
            assert "error trace here" in content
            # Should not include successful task stdout
            assert "ok" not in content or "#1" not in content.split("#2")[0]
        finally:
            os.unlink(log_path)

    def test_creates_file_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "wave.log")
            results = [
                TaskResult(number=3, success=False, branch="feature/3-x", stdout="boom"),
            ]
            append_log(results, log_path)
            assert os.path.exists(log_path)
            content = open(log_path).read()
            assert "boom" in content

    def test_includes_timestamp(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_path = f.name

        try:
            results = [
                TaskResult(number=1, success=False, branch="feature/1-x", stdout="fail"),
            ]
            with patch("wave_runner.reporter.datetime") as mock_dt:
                mock_dt.now.return_value.isoformat.return_value = "2026-06-21T20:00:00"
                append_log(results, log_path)
            content = open(log_path).read()
            assert "2026-06-21T20:00:00" in content
        finally:
            os.unlink(log_path)
