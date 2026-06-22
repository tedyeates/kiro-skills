"""Executor module — merge phase for wave-runner orchestrator."""

from __future__ import annotations

import subprocess

from wave_runner import git, github
from wave_runner.agent import invoke_agent, AgentResult
from wave_runner.config import Config
from wave_runner.models import TaskResult


MAX_MERGER_ATTEMPTS = 3


def _run_tests(test_command: str, cwd: str) -> bool:
    """Run the test command. Returns True if tests pass."""
    try:
        subprocess.run(
            test_command.split(),
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def run_merge_phase(
    tasks: list[dict],
    feature_branch: str,
    repo_dir: str,
    config: Config,
) -> list[TaskResult]:
    """Sequentially merge each task branch into the feature branch.

    Args:
        tasks: List of dicts with number, branch, worktree_path.
        feature_branch: The feature branch to merge into.
        repo_dir: Path to the repo (where merges happen).
        config: Project config with repo name and test_command.

    Returns:
        List of TaskResult for each task.
    """
    results: list[TaskResult] = []

    for entry in tasks:
        number = entry["number"]
        branch = entry["branch"]
        worktree_path = entry["worktree_path"]

        result = _merge_single_task(number, branch, worktree_path, repo_dir, config)
        results.append(result)

    return results


def _merge_single_task(
    number: int,
    branch: str,
    worktree_path: str,
    repo_dir: str,
    config: Config,
) -> TaskResult:
    """Attempt to merge a single task branch, invoking merger agent on failure."""
    merge_result = git.merge_branch(branch, repo_dir)

    if merge_result == "success":
        if _run_tests(config.test_command, repo_dir):
            _on_success(number, worktree_path, config)
            return TaskResult(number=number, success=True, branch=branch)
        # Tests failed — try merger agent
        return _attempt_merger_recovery(number, branch, worktree_path, repo_dir, config, "test_failure")

    # Conflict — try merger agent
    return _attempt_merger_recovery(number, branch, worktree_path, repo_dir, config, "conflict")


def _attempt_merger_recovery(
    number: int,
    branch: str,
    worktree_path: str,
    repo_dir: str,
    config: Config,
    failure_type: str,
) -> TaskResult:
    """Invoke merger agent up to MAX_MERGER_ATTEMPTS times."""
    for _ in range(MAX_MERGER_ATTEMPTS):
        agent_result = invoke_agent(
            "merger",
            f"Fix {failure_type} merging {branch} into feature branch for issue #{number}",
            repo_dir,
        )
        if not agent_result.success:
            continue
        # Agent claims success — verify tests pass
        if _run_tests(config.test_command, repo_dir):
            _on_success(number, worktree_path, config)
            return TaskResult(number=number, success=True, branch=branch)

    # All attempts exhausted
    _on_failure(number, branch, repo_dir, config)
    return TaskResult(number=number, success=False, branch=branch, stdout=f"{failure_type}: merger agent failed after {MAX_MERGER_ATTEMPTS} attempts")


def _on_success(number: int, worktree_path: str, config: Config) -> None:
    """Close issue and remove worktree."""
    github.close_issue(number, config.repo)
    git.remove_worktree(worktree_path)


def _on_failure(number: int, branch: str, repo_dir: str, config: Config) -> None:
    """Revert merge, label merge-failed, post comment."""
    git.revert_merge(repo_dir)
    github.update_label(number, "merging", "merge-failed", config.repo)
    github.post_comment(
        number,
        f"Merge of `{branch}` failed after {MAX_MERGER_ATTEMPTS} merger agent attempts. Branch preserved for manual inspection.",
        config.repo,
    )
