"""Executor module — implement/review phases and merge phase."""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess

from wave_runner import git, github
from wave_runner.agent import invoke_agent, AgentResult
from wave_runner.config import Config
from wave_runner.hooks import run_pre_review
from wave_runner.models import PipelineStage, PlannedTask, TaskResult
from wave_runner.pipeline import review_loop


MAX_MERGER_ATTEMPTS = 3
AGENT_RETRY_ATTEMPTS = 2


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

        # Run setup command if configured (e.g. venv creation, dep install)
        if config.setup_command:
            await asyncio.to_thread(_run_setup, config.setup_command, worktree_path)

        # Implement phase
        if planned.stage == PipelineStage.FULL:
            impl_prompt = f"Implement issue #{number} for feature {feature_branch}"
            if design_path:
                impl_prompt += f". Design: {design_path}"

            impl_result = await asyncio.to_thread(
                _invoke_with_retry, "implementer", impl_prompt, worktree_path
            )

            if not impl_result.success:
                await asyncio.to_thread(github.update_label, number, "implementing", "impl-failed", config.repo)
                await asyncio.to_thread(github.post_comment, number, f"Implementer failed: {impl_result.reason}", config.repo)
                return TaskResult(number=number, success=False, branch=branch, stdout=impl_result.stdout)

            # Deterministic test verification after implementer
            if config.test_command and not await asyncio.to_thread(_run_tests, config.test_command, worktree_path):
                await asyncio.to_thread(github.update_label, number, "implementing", "impl-failed", config.repo)
                await asyncio.to_thread(github.post_comment, number, "Implementer claimed success but tests fail", config.repo)
                return TaskResult(number=number, success=False, branch=branch, stdout="post-implement test verification failed")

            # Deterministic type check verification after implementer
            if config.type_check_command and not await asyncio.to_thread(_run_tests, config.type_check_command, worktree_path):
                await asyncio.to_thread(github.update_label, number, "implementing", "impl-failed", config.repo)
                await asyncio.to_thread(github.post_comment, number, "Implementer claimed success but type checking fails", config.repo)
                return TaskResult(number=number, success=False, branch=branch, stdout="post-implement type check verification failed")

            await asyncio.to_thread(github.update_label, number, "implementing", "reviewing", config.repo)

        # Review phase — use pipeline.review_loop with pre-review hooks
        is_ts = _has_ts_files(worktree_path)
        review_result = await asyncio.to_thread(
            review_loop,
            cwd=worktree_path,
            base_ref=feature_branch,
            test_command=config.test_command,
            type_check_command=config.type_check_command,
            is_ts_project=is_ts,
            issue_number=number,
            repo=config.repo,
        )

        if not review_result.success:
            await asyncio.to_thread(github.update_label, number, "reviewing", "review-failed", config.repo)
            await asyncio.to_thread(github.post_comment, number, f"Reviewer failed: {review_result.reason}", config.repo)
            return TaskResult(number=number, success=False, branch=branch, stdout=review_result.stdout)

        await asyncio.to_thread(github.update_label, number, "reviewing", "merging", config.repo)
        return TaskResult(number=number, success=True, branch=branch, stdout=review_result.stdout)


def _invoke_with_retry(name: str, prompt: str, cwd: str) -> AgentResult:
    """Invoke agent with retry on transient 'no result line' failures."""
    for attempt in range(AGENT_RETRY_ATTEMPTS):
        result = invoke_agent(name, prompt, cwd)
        if result.success or result.reason != "no result line":
            return result
    return result


def _has_ts_files(path: str) -> bool:
    """Check if directory contains TypeScript/JavaScript files."""
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith((".ts", ".tsx", ".js", ".jsx")):
                return True
    return False


# --- Merge phase (sync, sequential) ---


def _run_tests(test_command: str, cwd: str) -> bool:
    """Run the test command. Returns True if tests pass."""
    if not test_command:
        return True
    try:
        subprocess.run(
            shlex.split(test_command),
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _run_setup(setup_command: str, cwd: str) -> None:
    """Run setup command in worktree. Raises on failure."""
    subprocess.run(
        setup_command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        shell=True,
    )


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
