"""CLI and main orchestration loop for wave-runner."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys

from wave_runner import executor, git, github, planner, reporter
from wave_runner.config import load_config, Config
from wave_runner.models import Task, TaskState, PlannedTask, TaskResult


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Wave-runner: orchestrate PRD implementation wave by wave")
    parser.add_argument("--prd", type=int, required=True, help="PRD issue number")
    parser.add_argument("--concurrency", type=int, default=None, help="Max parallel tasks per wave (overrides config)")
    parser.add_argument("--base", type=str, default="main", help="Base branch (default: main)")
    parser.add_argument("--dry-run", action="store_true", help="Show wave plan without executing")
    return parser.parse_args(argv)


def derive_repo() -> str:
    """Derive owner/repo from git remote origin URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    )
    url = result.stdout.strip()
    # Handle SSH: git@github.com:owner/repo.git
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    raise RuntimeError(f"Cannot derive repo from remote URL: {url}")


def _slugify(title: str) -> str:
    """Turn a title into a branch-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:40]


def _build_tasks(raw_issues: list[dict]) -> list[Task]:
    """Convert raw issue dicts into Task models."""
    return [
        Task(
            number=i["number"],
            state=TaskState.CLOSED if i["state"] == "closed" else TaskState.OPEN,
            labels=i.get("labels", []),
            blockers=i.get("blockers", []),
        )
        for i in raw_issues
    ]


def _all_closed(raw_issues: list[dict]) -> bool:
    return all(i["state"] == "closed" for i in raw_issues)


def _branch_exists(branch: str) -> bool:
    """Check if a local branch already exists."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", branch],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _build_config(args: argparse.Namespace) -> Config:
    """Load config from project-config.md, with CLI overrides."""
    from pathlib import Path
    try:
        cfg = load_config(Path(os.getcwd()))
    except Exception:
        # Fallback: derive repo, no test command
        cfg = Config(repo=derive_repo(), test_command="")

    if args.concurrency is not None:
        cfg.concurrency = args.concurrency
    return cfg


def main_loop(args: argparse.Namespace) -> str:
    """Main orchestration loop. Returns 'complete', 'halted', or 'empty'."""
    config = _build_config(args)
    repo = config.repo
    prd = github.fetch_prd(args.prd, repo)
    title = prd["title"]
    design_path = prd.get("design_path")
    feature_branch = f"feature/{args.prd}-{_slugify(title)}"
    repo_dir = os.getcwd()
    worktree_base = os.path.abspath(os.path.join(repo_dir, "..", f"{args.prd}"))
    log_path = os.path.join(repo_dir, "wave-runner.log")

    # Fetch sub-issues
    raw_issues = github.fetch_sub_issues(args.prd, repo)
    tasks = _build_tasks(raw_issues)
    wave = planner.compute_wave(tasks)

    # Dry run mode
    if args.dry_run:
        print(f"DRY RUN — Wave plan for PRD #{args.prd} ({title}):")
        print(f"  Feature branch: {feature_branch}")
        print(f"  Concurrency: {config.concurrency}")
        print(f"  Test command: {config.test_command or '(none)'}")
        if not wave:
            print("  No eligible tasks.")
        for pt in wave:
            print(f"  #{pt.task.number} [{pt.stage.value}]")
        return "dry-run"

    # Create or reuse feature branch
    if not _branch_exists(feature_branch):
        git.create_feature_branch(feature_branch, args.base)
    else:
        subprocess.run(
            ["git", "checkout", feature_branch],
            check=True, capture_output=True, text=True,
        )

    # Main loop
    while True:
        raw_issues = github.fetch_sub_issues(args.prd, repo)

        if _all_closed(raw_issues):
            # All done — push and raise PR
            git.push_branch(feature_branch)
            closed_list = "\n".join(f"- #{i['number']}" for i in raw_issues)
            github.create_pr(
                head=feature_branch,
                base=args.base,
                title=title,
                body=f"Implements PRD #{args.prd}\n\n## Closed issues\n\n{closed_list}",
                repo=repo,
            )
            summary = f"All tasks complete for PRD #{args.prd}. PR raised from `{feature_branch}` → `{args.base}`."
            github.post_comment(args.prd, summary, repo)
            print(summary)
            return "complete"

        tasks = _build_tasks(raw_issues)
        wave = planner.compute_wave(tasks)

        if not wave:
            print("No eligible tasks (all blocked or failed). Halting.")
            return "empty"

        # Label tasks as implementing
        for pt in wave:
            if pt.stage.value == "full":
                github.update_label(pt.task.number, "ready-for-agent", "implementing", repo)

        # Run implement + review phase (async)
        wave_results: list[TaskResult] = asyncio.run(
            executor.run_wave(wave, config, feature_branch, design_path, worktree_base)
        )

        # Run merge phase (sequential) for successful tasks
        mergeable = [
            {"number": r.number, "branch": r.branch, "worktree_path": os.path.join(worktree_base, str(r.number))}
            for r in wave_results if r.success
        ]

        merge_results: list[TaskResult] = []
        if mergeable:
            merge_results = executor.run_merge_phase(mergeable, feature_branch, repo_dir, config)

        all_results = [r for r in wave_results if not r.success] + merge_results

        # Report
        outstanding = [t.number for t in tasks if t.state == TaskState.OPEN and t.number not in {r.number for r in all_results}]
        reporter.terminal_summary(all_results)
        comment = reporter.github_comment(all_results, outstanding)
        github.post_comment(args.prd, f"## Wave Report\n\n{comment}", repo)
        reporter.append_log(all_results, log_path)

        # Halt on any failure
        if any(not r.success for r in all_results):
            print("Failures detected. Halting after wave report.")
            return "halted"


def main():
    """Entry point."""
    args = parse_args()
    result = main_loop(args)
    if result == "halted":
        sys.exit(1)


if __name__ == "__main__":
    main()
