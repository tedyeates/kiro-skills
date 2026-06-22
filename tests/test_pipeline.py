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


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_passes_first_attempt_if_reviewer_succeeds_and_hooks_clean(mock_hook, mock_agent):
    mock_hook.return_value = PreReviewOutput(
        diff="+ line", test_output="ok", test_passed=True, fallow_output=None
    )
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="done")

    result = review_loop(**COMMON_ARGS, max_attempts=3)

    assert result.success is True
    assert mock_agent.call_count == 1
    # Final validation after reviewer
    assert mock_hook.call_count == 2


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_loops_when_post_hook_fails_after_reviewer(mock_hook, mock_agent):
    # First hook: tests fail, reviewer "fixes", second hook: still fail, third hook: pass
    mock_hook.side_effect = [
        PreReviewOutput(diff="d", test_output="FAIL", test_passed=False, fallow_output=None),
        PreReviewOutput(diff="d", test_output="FAIL", test_passed=False, fallow_output=None),
        PreReviewOutput(diff="d", test_output="ok", test_passed=True, fallow_output=None),
    ]
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="fixed")

    result = review_loop(**COMMON_ARGS, max_attempts=3)

    assert result.success is True
    assert mock_agent.call_count == 2  # Called twice, third hook passed before needing reviewer


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_fails_if_reviewer_returns_failure(mock_hook, mock_agent):
    mock_hook.return_value = PreReviewOutput(
        diff="d", test_output="FAIL", test_passed=False, fallow_output=None
    )
    mock_agent.return_value = AgentResult(success=False, reason="type errors", stdout="")

    result = review_loop(**COMMON_ARGS, max_attempts=3)

    assert result.success is False
    assert result.reason == "type errors"
    assert mock_agent.call_count == 1  # Bails immediately on agent failure


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_fails_after_max_attempts_exhausted(mock_hook, mock_agent):
    mock_hook.return_value = PreReviewOutput(
        diff="d", test_output="FAIL", test_passed=False, fallow_output=None
    )
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="tried")

    result = review_loop(**COMMON_ARGS, max_attempts=2)

    assert result.success is False
    assert "2 attempts" in result.reason
    assert mock_agent.call_count == 2


@patch("wave_runner.pipeline.invoke_agent")
@patch("wave_runner.pipeline.run_pre_review")
def test_prompt_includes_hook_output_and_attempt(mock_hook, mock_agent):
    mock_hook.return_value = PreReviewOutput(
        diff="+ new", test_output="3 passed", test_passed=True, fallow_output=None
    )
    mock_agent.return_value = AgentResult(success=True, reason=None, stdout="ok")

    review_loop(**COMMON_ARGS, max_attempts=1)

    prompt = mock_agent.call_args.args[1]
    assert "issue #10" in prompt
    assert "Attempt 1/1" in prompt
    assert "## Git Diff" in prompt
    assert "+ new" in prompt
    assert "## Tests (PASSED)" in prompt
