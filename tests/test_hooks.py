"""Tests for pre-review hook module."""

from unittest.mock import patch, MagicMock
import subprocess

from wave_runner.hooks import run_pre_review, format_for_prompt, PreReviewOutput


@patch("wave_runner.hooks.subprocess.run")
def test_diff_uses_three_dot_against_base_ref(mock_run):
    mock_run.return_value = MagicMock(stdout="diff output", stderr="", returncode=0)

    run_pre_review(cwd="/work", base_ref="feature/x", test_command="pytest")

    diff_call = mock_run.call_args_list[0]
    assert diff_call.args[0] == ["git", "diff", "feature/x...HEAD"]
    assert diff_call.kwargs["cwd"] == "/work"


@patch("wave_runner.hooks.subprocess.run")
def test_runs_test_command_from_config(mock_run):
    mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)

    run_pre_review(cwd="/work", base_ref="feature/x", test_command="pnpm test")

    test_call = mock_run.call_args_list[1]
    assert test_call.args[0] == ["pnpm", "test"]


@patch("wave_runner.hooks.subprocess.run")
def test_test_failure_captured(mock_run):
    def side_effect(cmd, **kwargs):
        if cmd[0] == "git":
            return MagicMock(stdout="diff", stderr="", returncode=0)
        return MagicMock(stdout="FAILED test_x", stderr="", returncode=1)

    mock_run.side_effect = side_effect

    result = run_pre_review(cwd="/work", base_ref="feature/x", test_command="pytest")

    assert result.test_passed is False
    assert "FAILED" in result.test_output


@patch("wave_runner.hooks.subprocess.run")
def test_fallow_skipped_for_non_ts(mock_run):
    mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)

    result = run_pre_review(
        cwd="/work", base_ref="feature/x", test_command="pytest", is_ts_project=False
    )

    assert result.fallow_output is None
    assert mock_run.call_count == 2  # diff + tests only


@patch("wave_runner.hooks.subprocess.run")
def test_fallow_runs_for_ts_project(mock_run):
    mock_run.return_value = MagicMock(stdout="no issues", stderr="", returncode=0)

    result = run_pre_review(
        cwd="/work", base_ref="feature/x", test_command="pnpm test", is_ts_project=True
    )

    assert result.fallow_output is not None
    fallow_call = mock_run.call_args_list[2]
    assert fallow_call.args[0] == ["fallow", "dead-code"]


@patch("wave_runner.hooks.subprocess.run")
def test_type_check_runs_when_configured(mock_run):
    mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)

    result = run_pre_review(
        cwd="/work", base_ref="feature/x", test_command="pytest",
        type_check_command="mypy .",
    )

    assert result.type_check_passed is True
    assert result.type_check_output == "ok"
    # diff, tests, type_check = 3 calls
    assert mock_run.call_count == 3
    tc_call = mock_run.call_args_list[2]
    assert tc_call.args[0] == ["mypy", "."]


@patch("wave_runner.hooks.subprocess.run")
def test_type_check_skipped_when_not_configured(mock_run):
    mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)

    result = run_pre_review(
        cwd="/work", base_ref="feature/x", test_command="pytest",
    )

    assert result.type_check_output is None
    assert result.type_check_passed is True
    assert mock_run.call_count == 2  # diff + tests only


@patch("wave_runner.hooks.subprocess.run")
def test_type_check_failure_captured(mock_run):
    def side_effect(cmd, **kwargs):
        if cmd[0] == "git":
            return MagicMock(stdout="diff", stderr="", returncode=0)
        if cmd[0] == "pytest":
            return MagicMock(stdout="ok", stderr="", returncode=0)
        # type check fails
        return MagicMock(stdout="error: type mismatch", stderr="", returncode=1)

    mock_run.side_effect = side_effect

    result = run_pre_review(
        cwd="/work", base_ref="feature/x", test_command="pytest",
        type_check_command="mypy .",
    )

    assert result.type_check_passed is False
    assert "type mismatch" in result.type_check_output


def test_format_for_prompt_includes_all_sections():
    output = PreReviewOutput(
        diff="+ new line",
        test_output="5 passed",
        test_passed=True,
        type_check_output="Success: no issues found",
        type_check_passed=True,
        fallow_output="unused: foo.ts",
    )

    formatted = format_for_prompt(output)

    assert "## Git Diff" in formatted
    assert "+ new line" in formatted
    assert "## Type Check (PASSED)" in formatted
    assert "Success: no issues found" in formatted
    assert "## Tests (PASSED)" in formatted
    assert "5 passed" in formatted
    assert "## Fallow Dead-Code" in formatted
    assert "unused: foo.ts" in formatted


def test_format_for_prompt_omits_fallow_when_none():
    output = PreReviewOutput(
        diff="changes",
        test_output="ok",
        test_passed=True,
        type_check_output=None,
        type_check_passed=True,
        fallow_output=None,
    )

    formatted = format_for_prompt(output)

    assert "Fallow" not in formatted
    assert "Type Check" not in formatted


def test_format_for_prompt_shows_failed_status():
    output = PreReviewOutput(
        diff="changes",
        test_output="FAILED test_x",
        test_passed=False,
        type_check_output="error: incompatible types",
        type_check_passed=False,
        fallow_output=None,
    )

    formatted = format_for_prompt(output)

    assert "## Tests (FAILED)" in formatted
    assert "## Type Check (FAILED)" in formatted
