"""Pipeline coordination — composes agents and hooks into retry loops."""

from __future__ import annotations

from wave_runner.agent import AgentResult, invoke_agent
from wave_runner.hooks import PreReviewOutput, run_pre_review, format_for_prompt


def _hooks_pass(output: PreReviewOutput) -> bool:
    """Check if all deterministic hooks passed."""
    if not output.test_passed:
        return False
    if not output.type_check_passed:
        return False
    if output.fallow_output not in (None, "(no dead code found)"):
        return False
    return True


def review_loop(
    *,
    cwd: str,
    base_ref: str,
    test_command: str,
    type_check_command: str | None = None,
    is_ts_project: bool = False,
    issue_number: int,
    repo: str,
    max_attempts: int = 3,
    agent_timeout: int = 600,
) -> AgentResult:
    """Pre-review hook → reviewer → post-review hook, looping until clean.

    Returns:
        AgentResult indicating final pass/fail.
    """
    for attempt in range(1, max_attempts + 1):
        hook_output = run_pre_review(
            cwd=cwd,
            base_ref=base_ref,
            test_command=test_command,
            type_check_command=type_check_command,
            is_ts_project=is_ts_project,
        )

        # After a reviewer fix, if hooks pass we're done
        if attempt > 1 and _hooks_pass(hook_output):
            return AgentResult(success=True, reason=None, stdout="post-review hook passed")

        prompt = (
            f"Review issue #{issue_number}. Working directory: {cwd}. "
            f"Base ref: {base_ref}. Repo: {repo}. "
            f"Attempt {attempt}/{max_attempts}.\n\n"
            f"# Pre-Review Check Results\n\n{format_for_prompt(hook_output)}"
        )

        result = invoke_agent("reviewer", prompt, cwd, timeout=agent_timeout)

        if not result.success:
            return result

    # Final validation after last reviewer attempt
    final = run_pre_review(
        cwd=cwd,
        base_ref=base_ref,
        test_command=test_command,
        type_check_command=type_check_command,
        is_ts_project=is_ts_project,
    )

    if _hooks_pass(final):
        return AgentResult(success=True, reason=None, stdout="post-review hook passed after final attempt")

    return AgentResult(success=False, reason=f"checks still failing after {max_attempts} attempts", stdout="")
