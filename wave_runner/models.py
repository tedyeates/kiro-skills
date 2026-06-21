from dataclasses import dataclass, field
from enum import Enum


class TaskState(Enum):
    OPEN = "open"
    CLOSED = "closed"


class PipelineStage(Enum):
    """Which stage of the pipeline a task should enter."""
    FULL = "full"  # Run full pipeline (implement → review → merge)
    REVIEW = "review"  # Skip implementer, start at reviewer
    MERGE = "merge"  # Skip implementer + reviewer, go to merge


@dataclass
class Task:
    number: int
    state: TaskState
    labels: list[str] = field(default_factory=list)
    blockers: list[int] = field(default_factory=list)


@dataclass
class PlannedTask:
    """A task eligible for the current wave, with its pipeline entry point."""
    task: Task
    stage: PipelineStage
