"""Tests for wave_runner.agent module."""

from unittest.mock import patch, MagicMock
import subprocess

from wave_runner.agent import invoke_agent, AgentResult


class TestAgentResult:
    def test_success_result(self):
        r = AgentResult(success=True, reason=None, stdout="output")
        assert r.success is True
        assert r.reason is None
        assert r.stdout == "output"

    def test_failure_result(self):
        r = AgentResult(success=False, reason="something broke", stdout="")
        assert r.success is False
        assert r.reason == "something broke"


class TestInvokeAgent:
    @patch("wave_runner.agent.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="doing stuff\nAGENT_RESULT: SUCCESS\n",
            returncode=0,
        )
        result = invoke_agent("implementer", "do the thing", "/tmp/work")
        assert result.success is True
        assert result.reason is None
        assert "AGENT_RESULT: SUCCESS" in result.stdout
        mock_run.assert_called_once_with(
            [
                "kiro-cli", "chat",
                "--no-interactive",
                "--agent", "implementer",
                "do the thing",
            ],
            cwd="/tmp/work",
            capture_output=True,
            text=True,
            timeout=600,
        )

    @patch("wave_runner.agent.subprocess.run")
    def test_failure_with_reason(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="trying\nAGENT_RESULT: FAILED — tests broken\n",
            returncode=0,
        )
        result = invoke_agent("reviewer", "review it", "/tmp/work")
        assert result.success is False
        assert result.reason == "tests broken"

    @patch("wave_runner.agent.subprocess.run")
    def test_no_result_line(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="some output without result\n",
            returncode=0,
        )
        result = invoke_agent("implementer", "do it", "/tmp/work")
        assert result.success is False
        assert result.reason == "no result line"

    @patch("wave_runner.agent.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="kiro-cli", timeout=600)
        result = invoke_agent("implementer", "do it", "/tmp/work")
        assert result.success is False
        assert result.reason == "timeout after 600s"
        assert result.stdout == ""

    @patch("wave_runner.agent.subprocess.run")
    def test_custom_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="kiro-cli", timeout=300)
        result = invoke_agent("implementer", "do it", "/tmp/work", timeout=300)
        assert result.success is False
        assert result.reason == "timeout after 300s"

    @patch("wave_runner.agent.subprocess.run")
    def test_custom_timeout_passed_to_subprocess(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="AGENT_RESULT: SUCCESS\n",
            returncode=0,
        )
        invoke_agent("implementer", "do it", "/tmp/work", timeout=300)
        mock_run.assert_called_once_with(
            [
                "kiro-cli", "chat",
                "--no-interactive",
                "--agent", "implementer",
                "do it",
            ],
            cwd="/tmp/work",
            capture_output=True,
            text=True,
            timeout=300,
        )
