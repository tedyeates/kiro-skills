"""Pre-review hook — runs deterministic checks before invoking the reviewer agent."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass


@dataclass
class PreReviewOutput:
    """Collected output from deterministic pre-review checks."""

    diff: str
    test_output: str
    test_passed: bool
    type_check_output: str | None  # None if no type_check_command configured
    type_check_passed: bool
    fallow_output: str | None  # None if not a TS/JS project


def run_pre_review(
    *,
    cwd: str,
    base_ref: str,
    test_command: str,
    type_check_command: str | None = None,
    is_ts_project: bool = False,
) -> PreReviewOutput:
    """Run git diff, type check, tests, and optionally fallow before handing off to reviewer.

    Args:
        cwd: Worktree path to run checks in.
        base_ref: Branch to diff against (feature branch).
        test_command: Test command from project config (e.g. "pytest", "pnpm test").
        type_check_command: Type check command (e.g. "mypy .", "pyright", "tsc --noEmit").
        is_ts_project: Whether to run fallow dead-code analysis.

    Returns:
        PreReviewOutput with all collected results.
    """
    diff = _run_diff(cwd, base_ref)
    test_output, test_passed = _run_tests(cwd, test_command)
    type_check_output, type_check_passed = _run_type_check(cwd, type_check_command)
    fallow_output = _run_fallow(cwd) if is_ts_project else None

    return PreReviewOutput(
        diff=diff,
        test_output=test_output,
        test_passed=test_passed,
        type_check_output=type_check_output,
        type_check_passed=type_check_passed,
        fallow_output=fallow_output,
    )


def format_for_prompt(output: PreReviewOutput) -> str:
    """Format pre-review output for injection into reviewer prompt."""
    sections = []

    sections.append("## Git Diff (against base ref)\n```diff\n" + output.diff + "\n```")

    if output.type_check_output is not None:
        tc_status = "PASSED" if output.type_check_passed else "FAILED"
        sections.append(f"## Type Check ({tc_status})\n```\n" + output.type_check_output + "\n```")

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
    if not test_command:
        return "(no test command configured)", True
    proc = subprocess.run(
        shlex.split(test_command),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = (proc.stdout + proc.stderr).strip()
    return output, proc.returncode == 0


def _run_type_check(cwd: str, type_check_command: str | None) -> tuple[str | None, bool]:
    """Run type check command, return (output, passed). Returns (None, True) if not configured."""
    if not type_check_command:
        return None, True
    proc = subprocess.run(
        shlex.split(type_check_command),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
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
