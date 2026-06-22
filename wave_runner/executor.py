"""Executor module — implement/review phases and merge phase."""

from __future__ import annotations

import asyncio
import os
import subprocess

from wave_runner import git, github
from wave_runner.agent import invoke_agent, AgentResult
from wave_runner.config import Config
from wave_runner.models import PipelineStage, PlannedTask, TaskResult


MAX_MERGER_ATTEMPTS = 3


# --- Implement + Review (async, parallel) ---


async def run_wave(
    wave: list[PlannedTask],
    config: Config,
    feature_branch: str,
    design_path: str | None,
    worktree_base: str,
) -> list[TaskResult]:
    """Run all tasks in a wave with bounded parallelism."""
    sem = asyncio.Semaphore(config.concurrency)
    coros = [
        _run_task(planned, config, feature_branch, design_path, worktree_base, sem)
        for planned in wave
    ]
    return list(await asyncio.gather(*coros))


async def _run_task(
    planned: PlannedTask,
    config: Config,
    feature_branch: str,
    design_path: str | None,
    worktree_base: str,
    sem: asyncio.Semaphore,
) -> TaskResult:
    """Run a single task through its pipeline stages."""
    async with sem:
        number = planned.task.number
        branch = f"task/{number}"
        worktree_path = os.path.join(worktree_base, str(number))

        if planned.stage == PipelineStage.MERGE:
            return TaskResult(number=number, success=True, branch=branch, stdout="")

        # Create worktree for implement/review stages
        await asyncio.to_thread(git.create_worktree, branch, worktree_path, feature_branch)

        # Implement phase
        if planned.stage == PipelineStage.FULL:
            impl_prompt = f"Implement issue #{number} for feature {feature_branch}"
            if design_path:
                impl_prompt += f". Design: {design_path}"

            impl_result = await asyncio.to_thread(invoke_agent, "implementer", impl_prompt, worktree_path)

            if not impl_result.success:
                await asyncio.to_thread(github.update_label, number, "implementing", "impl-failed", config.repo)
                await asyncio.to_thread(github.post_comment, number, f"Implementer failed: {impl_result.reason}", config.repo)
                return TaskResult(number=number, success=False, branch=branch, stdout=impl_result.stdout)

            await asyncio.to_thread(github.update_label, number, "implementing", "reviewing", config.repo)

        # Review phase
        review_prompt = f"Review issue #{number}. Base ref: {feature_branch}"
        review_result = await asyncio.to_thread(invoke_agent, "reviewer", review_prompt, worktree_path)

        if not review_result.success:
            await asyncio.to_thread(github.update_label, number, "reviewing", "review-failed", config.repo)
            await asyncio.to_thread(github.post_comment, number, f"Reviewer failed: {review_result.reason}", config.repo)
            return TaskResult(number=number, success=False, branch=branch, stdout=review_result.stdout)

        await asyncio.to_thread(github.update_label, number, "reviewing", "merging", config.repo)
        return TaskResult(number=number, success=True, branch=branch, stdout=review_result.stdout)


# --- Merge phase (sync, sequential) ---


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
        return _attempt_merger_recovery(number, branch, worktree_path, repo_dir, config, "test_failure")

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
        if _run_tests(config.test_command, repo_dir):
            _on_success(number, worktree_path, config)
            return TaskResult(number=number, success=True, branch=branch)

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
