"""Pipeline coordination — composes agents and hooks into retry loops."""

from __future__ import annotations

from wave_runner.agent import AgentResult, invoke_agent
from wave_runner.hooks import run_pre_review, format_for_prompt


def review_loop(
    *,
    cwd: str,
    base_ref: str,
    test_command: str,
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
            is_ts_project=is_ts_project,
        )

        # After a reviewer fix, if hooks pass we're done
        if attempt > 1 and hook_output.test_passed and hook_output.fallow_output in (None, "(no dead code found)"):
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
        is_ts_project=is_ts_project,
    )

    if final.test_passed and final.fallow_output in (None, "(no dead code found)"):
        return AgentResult(success=True, reason=None, stdout="post-review hook passed after final attempt")

    return AgentResult(success=False, reason=f"checks still failing after {max_attempts} attempts", stdout="")
