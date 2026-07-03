"""Reporter module — formats wave results for terminal, GitHub, and log file."""

from __future__ import annotations

from datetime import datetime

from wave_runner.models import TaskResult


def terminal_summary(results: list[TaskResult]) -> None:
    """Print pass/fail per task, with branch names for failures."""
    for r in results:
        if r.success:
            print(f"  ✅ #{r.number}")
        else:
            print(f"  ❌ #{r.number} ({r.branch})")


def github_comment(results: list[TaskResult], outstanding: list[int] | None = None) -> str:
    """Return markdown string with merged/failed/outstanding sections."""
    outstanding = outstanding or []
    merged = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    sections: list[str] = []

    if merged:
        lines = ["## Merged", ""]
        for r in merged:
            lines.append(f"- #{r.number}")
        sections.append("\n".join(lines))

    if failed:
        lines = ["## Failed", ""]
        for r in failed:
            lines.append(f"- #{r.number} (`{r.branch}`)")
        sections.append("\n".join(lines))

    if outstanding:
        lines = ["## Outstanding", ""]
        for num in outstanding:
            lines.append(f"- #{num}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def append_log(results: list[TaskResult], log_path: str) -> None:
    """Append timestamped failure details to log file."""
    failures = [r for r in results if not r.success]
    if not failures:
        return

    timestamp = datetime.now().isoformat()

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n--- {timestamp} ---\n")
        for r in failures:
            f.write(f"\n### #{r.number} ({r.branch})\n")
            f.write(r.stdout)
            f.write("\n")
