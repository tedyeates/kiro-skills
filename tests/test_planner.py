from wave_runner.models import Task, TaskState, PlannedTask, PipelineStage
from wave_runner.planner import compute_wave


def _task(number, state="open", labels=None, blockers=None):
    return Task(
        number=number,
        state=TaskState(state),
        labels=labels or [],
        blockers=blockers or [],
    )


class TestAllUnblocked:
    def test_returns_all_open_tasks_with_no_blockers(self):
        tasks = [_task(1), _task(2), _task(3)]
        result = compute_wave(tasks)
        assert {pt.task.number for pt in result} == {1, 2, 3}

    def test_all_unblocked_get_full_pipeline(self):
        tasks = [_task(1, labels=["ready-for-agent"])]
        result = compute_wave(tasks)
        assert result[0].stage == PipelineStage.FULL


class TestPartialBlockers:
    def test_excludes_tasks_with_open_blockers(self):
        tasks = [
            _task(1),  # no blockers, eligible
            _task(2, blockers=[1]),  # blocked by open #1
        ]
        result = compute_wave(tasks)
        assert {pt.task.number for pt in result} == {1}

    def test_includes_task_when_all_blockers_closed(self):
        tasks = [
            _task(1, state="closed"),
            _task(2, blockers=[1]),  # blocker is closed
        ]
        result = compute_wave(tasks)
        assert {pt.task.number for pt in result} == {2}


class TestResumeStates:
    def test_implementing_label_enters_review_stage(self):
        tasks = [_task(1, labels=["implementing"])]
        result = compute_wave(tasks)
        assert result[0].stage == PipelineStage.REVIEW

    def test_reviewing_label_enters_merge_stage(self):
        tasks = [_task(1, labels=["reviewing"])]
        result = compute_wave(tasks)
        assert result[0].stage == PipelineStage.MERGE

    def test_merging_label_enters_merge_stage(self):
        tasks = [_task(1, labels=["merging"])]
        result = compute_wave(tasks)
        assert result[0].stage == PipelineStage.MERGE


class TestAllDone:
    def test_returns_empty_when_all_closed(self):
        tasks = [_task(1, state="closed"), _task(2, state="closed")]
        result = compute_wave(tasks)
        assert result == []

    def test_returns_empty_when_all_blocked(self):
        tasks = [
            _task(1, blockers=[99]),  # blocker not in list, treated as open
            _task(2, blockers=[99]),
        ]
        result = compute_wave(tasks)
        assert result == []


class TestFailedTasksExcluded:
    def test_impl_failed_excluded(self):
        tasks = [_task(1, labels=["impl-failed"])]
        result = compute_wave(tasks)
        assert result == []

    def test_review_failed_excluded(self):
        tasks = [_task(1, labels=["review-failed"])]
        result = compute_wave(tasks)
        assert result == []

    def test_merge_failed_excluded(self):
        tasks = [_task(1, labels=["merge-failed"])]
        result = compute_wave(tasks)
        assert result == []

    def test_failed_blocker_blocks_dependents(self):
        tasks = [
            _task(1, labels=["impl-failed"]),
            _task(2, blockers=[1]),  # blocked by failed task
        ]
        result = compute_wave(tasks)
        assert result == []
