"""Agent runner module — invokes kiro-cli agents and parses structured output."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class AgentResult:
    """Result of an agent invocation."""

    success: bool
    reason: str | None
    stdout: str


def invoke_agent(
    name: str,
    prompt: str,
    cwd: str,
    *,
    timeout: int = 600,
) -> AgentResult:
    """Run a kiro-cli agent as a subprocess and parse AGENT_RESULT line.

    Args:
        name: Agent name (implementer, reviewer, merger).
        prompt: Prompt string to pass to the agent.
        cwd: Working directory for the subprocess.
        timeout: Max seconds to wait (default 10 min).

    Returns:
        AgentResult with parsed success/failure and full stdout.
    """
    cmd = [
        "kiro-cli", "chat",
        "--no-interactive",
        "--agent", name,
        prompt,
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return AgentResult(success=False, reason=f"timeout after {timeout}s", stdout="")

    stdout = proc.stdout
    return _parse_result(stdout)


def _parse_result(stdout: str) -> AgentResult:
    """Parse AGENT_RESULT line from stdout."""
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if stripped == "AGENT_RESULT: SUCCESS":
            return AgentResult(success=True, reason=None, stdout=stdout)
        if stripped.startswith("AGENT_RESULT: FAILED"):
            reason = stripped.removeprefix("AGENT_RESULT: FAILED").lstrip(" —\u2014-").strip()
            return AgentResult(success=False, reason=reason or "unknown", stdout=stdout)

    return AgentResult(success=False, reason="no result line", stdout=stdout)
