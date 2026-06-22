"""Executor module — implement and review phases with bounded parallelism."""

from __future__ import annotations

import asyncio
import os

from wave_runner import git, github
from wave_runner.agent import invoke_agent
from wave_runner.config import Config
from wave_runner.models import PipelineStage, PlannedTask, TaskResult


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
