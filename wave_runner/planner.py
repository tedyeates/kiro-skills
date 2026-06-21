"""Compute the next wave of eligible tasks from a task graph."""

from wave_runner.models import Task, TaskState, PlannedTask, PipelineStage

_FAILED_LABELS = {"impl-failed", "review-failed", "merge-failed"}


def _has_failed_label(task: Task) -> bool:
    return bool(_FAILED_LABELS & set(task.labels))


def _determine_stage(task: Task) -> PipelineStage:
    labels = set(task.labels)
    if "implementing" in labels:
        return PipelineStage.REVIEW
    if "reviewing" in labels or "merging" in labels:
        return PipelineStage.MERGE
    return PipelineStage.FULL


def compute_wave(tasks: list[Task]) -> list[PlannedTask]:
    """Return tasks eligible for the current wave.

    A task is eligible when:
    - It is open
    - It has no *-failed label
    - All its blockers are closed AND none have a *-failed label
    """
    task_map = {t.number: t for t in tasks}
    closed_numbers = {t.number for t in tasks if t.state == TaskState.CLOSED}

    eligible = []
    for task in tasks:
        if task.state == TaskState.CLOSED:
            continue
        if _has_failed_label(task):
            continue
        # All blockers must be closed and not failed
        blockers_ok = all(
            b in closed_numbers
            and not _has_failed_label(task_map[b])
            for b in task.blockers
            if b in task_map
        )
        # Blockers not in the task list are treated as unresolved (open)
        has_unknown_blockers = any(b not in task_map for b in task.blockers)
        if not blockers_ok or has_unknown_blockers:
            continue
        eligible.append(PlannedTask(task=task, stage=_determine_stage(task)))

    return eligible
