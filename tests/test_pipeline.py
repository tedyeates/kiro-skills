"""Tests for pipeline coordination module."""

from unittest.mock import patch, call

from wave_runner.agent import AgentResult
from wave_runner.hooks import PreReviewOutput
from wave_runner.pipeline import review_loop


COMMON_ARGS = dict(
    cwd="/work",
    base_ref="feature/x",
    test_command="pytest",
    issue_number=10,
    repo="owner/repo",
)


def _passing_output(**overrides):
    defaults = dict(
        diff="+ line", test_output="ok", test_passed=True,
        type_check_output=None, type_check_passed=True, fallow_output=None,
    )
    defaults.update(overrides)
    return PreReviewOutput(**defaults)


def _failing_output(**overrides):
    defaults = dict(
        diff="d", test_output="FAIL", test_passed=False,
        type_check_output=None, type_check_passed=True, fallow_output=None,
    )
    defaults.update(overrides)
    return PreReviewOutput(**defaults)


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_passes_first_attempt_if_reviewer_succeeds_and_hooks_clean(mock_hook, mock_agent):
    mock_hook.return_value = _passing_output()
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="done")

    result = review_loop(**COMMON_ARGS, max_attempts=3)

    assert result.success is True
    assert mock_agent.call_count == 1
    # Final validation after reviewer
    assert mock_hook.call_count == 2


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_loops_when_post_hook_fails_after_reviewer(mock_hook, mock_agent):
    mock_hook.side_effect = [
        _failing_output(),
        _failing_output(),
        _passing_output(),
    ]
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="fixed")

    result = review_loop(**COMMON_ARGS, max_attempts=3)

    assert result.success is True
    assert mock_agent.call_count == 2


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_fails_if_reviewer_returns_failure(mock_hook, mock_agent):
    mock_hook.return_value = _failing_output()
    mock_agent.return_value = AgentResult(success=False, reason="type errors", stdout="")

    result = review_loop(**COMMON_ARGS, max_attempts=3)

    assert result.success is False
    assert result.reason == "type errors"
    assert mock_agent.call_count == 1


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_fails_after_max_attempts_exhausted(mock_hook, mock_agent):
    mock_hook.return_value = _failing_output()
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="tried")

    result = review_loop(**COMMON_ARGS, max_attempts=2)

    assert result.success is False
    assert "2 attempts" in result.reason
    assert mock_agent.call_count == 2


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_prompt_includes_hook_output_and_attempt(mock_hook, mock_agent):
    mock_hook.return_value = _passing_output(diff="+ new", test_output="3 passed")
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="ok")

    review_loop(**COMMON_ARGS, max_attempts=1)

    prompt = mock_agent.call_args.args[1]
    assert "issue #10" in prompt
    assert "Attempt 1/1" in prompt
    assert "## Git Diff" in prompt
    assert "+ new" in prompt
    assert "## Tests (PASSED)" in prompt


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_type_check_failure_triggers_reviewer(mock_hook, mock_agent):
    mock_hook.side_effect = [
        _failing_output(test_passed=True, test_output="ok", type_check_passed=False, type_check_output="error"),
        _passing_output(),
    ]
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="fixed types")

    result = review_loop(**COMMON_ARGS, max_attempts=3)

    assert result.success is True
    assert mock_agent.call_count == 1


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_passes_type_check_command_to_hook(mock_hook, mock_agent):
    mock_hook.return_value = _passing_output()
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="ok")

    review_loop(**COMMON_ARGS, type_check_command="mypy .", max_attempts=1)

    # First call to run_pre_review should include type_check_command
    hook_kwargs = mock_hook.call_args_list[0].kwargs
    assert hook_kwargs["type_check_command"] == "mypy ."
