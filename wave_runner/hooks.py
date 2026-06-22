"""Pre-review hook — runs deterministic checks before invoking the reviewer agent."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class PreReviewOutput:
    """Collected output from deterministic pre-review checks."""

    diff: str
    test_output: str
    test_passed: bool
    fallow_output: str | None  # None if not a TS/JS project


def run_pre_review(
    *,
    cwd: str,
    base_ref: str,
    test_command: str,
    is_ts_project: bool = False,
) -> PreReviewOutput:
    """Run git diff, tests, and optionally fallow before handing off to reviewer.

    Args:
        cwd: Worktree path to run checks in.
        base_ref: Branch to diff against (feature branch).
        test_command: Test command from project config (e.g. "pytest", "pnpm test").
        is_ts_project: Whether to run fallow dead-code analysis.

    Returns:
        PreReviewOutput with all collected results.
    """
    diff = _run_diff(cwd, base_ref)
    test_output, test_passed = _run_tests(cwd, test_command)
    fallow_output = _run_fallow(cwd) if is_ts_project else None

    return PreReviewOutput(
        diff=diff,
        test_output=test_output,
        test_passed=test_passed,
        fallow_output=fallow_output,
    )


def format_for_prompt(output: PreReviewOutput) -> str:
    """Format pre-review output for injection into reviewer prompt."""
    sections = []

    sections.append("## Git Diff (against base ref)\n```diff\n" + output.diff + "\n```")

    status = "PASSED" if output.test_passed else "FAILED"
    sections.append(f"## Tests ({status})\n```\n" + output.test_output + "\n```")

    if output.fallow_output is not None:
        sections.append("## Fallow Dead-Code Analysis\n```\n" + output.fallow_output + "\n```")

    return "\n\n".join(sections)


def _run_diff(cwd: str, base_ref: str) -> str:
    """Run git diff against base ref to get only this task's changes."""
    proc = subprocess.run(
        ["git", "diff", f"{base_ref}...HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout.strip() or "(no changes)"


def _run_tests(cwd: str, test_command: str) -> tuple[str, bool]:
    """Run test command, return (output, passed)."""
    proc = subprocess.run(
        test_command.split(),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = (proc.stdout + proc.stderr).strip()
    return output, proc.returncode == 0


def _run_fallow(cwd: str) -> str:
    """Run fallow dead-code analysis."""
    proc = subprocess.run(
        ["fallow", "dead-code"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (proc.stdout + proc.stderr).strip() or "(no dead code found)"
