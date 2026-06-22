"""Tests for the CLI module — entry point and main orchestration loop."""

from unittest.mock import patch, MagicMock

import pytest

from wave_runner.cli import parse_args, derive_repo, main_loop


class TestParseArgs:
    def test_prd_required(self):
        args = parse_args(["--prd", "42"])
        assert args.prd == 42

    def test_defaults(self):
        args = parse_args(["--prd", "1"])
        assert args.concurrency is None
        assert args.base == "main"
        assert args.dry_run is False

    def test_all_flags(self):
        args = parse_args(["--prd", "10", "--concurrency", "5", "--base", "develop", "--dry-run"])
        assert args.prd == 10
        assert args.concurrency == 5
        assert args.base == "develop"
        assert args.dry_run is True

    def test_missing_prd_raises(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_help_prints_usage(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--prd" in captured.out


class TestDeriveRepo:
    @patch("wave_runner.cli.subprocess.run")
    def test_derives_from_https(self, mock_run):
        mock_run.return_value = MagicMock(stdout="https://github.com/owner/repo.git\n")
        assert derive_repo() == "owner/repo"

    @patch("wave_runner.cli.subprocess.run")
    def test_derives_from_ssh(self, mock_run):
        mock_run.return_value = MagicMock(stdout="git@github.com:owner/repo.git\n")
        assert derive_repo() == "owner/repo"

    @patch("wave_runner.cli.subprocess.run")
    def test_strips_dotgit(self, mock_run):
        mock_run.return_value = MagicMock(stdout="https://github.com/foo/bar.git\n")
        assert derive_repo() == "foo/bar"

    @patch("wave_runner.cli.subprocess.run")
    def test_no_dotgit_suffix(self, mock_run):
        mock_run.return_value = MagicMock(stdout="https://github.com/foo/bar\n")
        assert derive_repo() == "foo/bar"


class TestMainLoop:
    @patch("wave_runner.cli.reporter")
    @patch("wave_runner.cli.github")
    @patch("wave_runner.cli.planner")
    @patch("wave_runner.cli.executor")
    @patch("wave_runner.cli.git")
    @patch("wave_runner.cli._build_config")
    def test_dry_run_prints_plan(self, mock_config, mock_git, mock_exec, mock_planner, mock_github, mock_reporter, capsys):
        from wave_runner.config import Config
        mock_config.return_value = Config(repo="owner/repo", test_command="pytest", concurrency=3)
        mock_github.fetch_prd.return_value = {"title": "Feature", "body": "", "design_path": None}
        mock_github.fetch_sub_issues.return_value = [
            {"number": 1, "state": "open", "labels": ["ready-for-agent"], "blockers": []},
            {"number": 2, "state": "open", "labels": ["ready-for-agent"], "blockers": [1]},
        ]

        from wave_runner.models import Task, TaskState, PlannedTask, PipelineStage
        mock_planner.compute_wave.return_value = [
            PlannedTask(task=Task(number=1, state=TaskState.OPEN, labels=["ready-for-agent"], blockers=[]), stage=PipelineStage.FULL),
        ]

        args = parse_args(["--prd", "99", "--dry-run"])
        result = main_loop(args)

        captured = capsys.readouterr()
        assert "#1" in captured.out
        assert "DRY RUN" in captured.out
        mock_exec.run_wave.assert_not_called()
        mock_git.create_feature_branch.assert_not_called()

    @patch("wave_runner.cli._branch_exists")
    @patch("wave_runner.cli.reporter")
    @patch("wave_runner.cli.github")
    @patch("wave_runner.cli.planner")
    @patch("wave_runner.cli.executor")
    @patch("wave_runner.cli.git")
    @patch("wave_runner.cli._build_config")
    def test_halts_on_failure(self, mock_config, mock_git, mock_exec, mock_planner, mock_github, mock_reporter, mock_branch_exists):
        from wave_runner.config import Config
        mock_config.return_value = Config(repo="owner/repo", test_command="pytest", concurrency=3)
        mock_branch_exists.return_value = False
        mock_github.fetch_prd.return_value = {"title": "Feature X", "body": "", "design_path": None}
        mock_github.fetch_sub_issues.return_value = [
            {"number": 1, "state": "open", "labels": ["ready-for-agent"], "blockers": []},
        ]

        from wave_runner.models import Task, TaskState, PlannedTask, PipelineStage, TaskResult
        mock_planner.compute_wave.return_value = [
            PlannedTask(task=Task(number=1, state=TaskState.OPEN), stage=PipelineStage.FULL),
        ]

        async def fake_run_wave(*a, **kw):
            return [TaskResult(number=1, success=False, branch="task/1", stdout="error")]

        mock_exec.run_wave = fake_run_wave
        mock_exec.run_merge_phase.return_value = []

        args = parse_args(["--prd", "99"])
        result = main_loop(args)

        assert result == "halted"
        mock_github.create_pr.assert_not_called()

    @patch("wave_runner.cli._branch_exists")
    @patch("wave_runner.cli.reporter")
    @patch("wave_runner.cli.github")
    @patch("wave_runner.cli.planner")
    @patch("wave_runner.cli.executor")
    @patch("wave_runner.cli.git")
    @patch("wave_runner.cli._build_config")
    def test_creates_pr_on_success(self, mock_config, mock_git, mock_exec, mock_planner, mock_github, mock_reporter, mock_branch_exists):
        from wave_runner.config import Config
        mock_config.return_value = Config(repo="owner/repo", test_command="pytest", concurrency=3)
        mock_branch_exists.return_value = False
        mock_github.fetch_prd.return_value = {"title": "Feature X", "body": "", "design_path": None}
        mock_github.fetch_sub_issues.side_effect = [
            [{"number": 1, "state": "open", "labels": ["ready-for-agent"], "blockers": []}],
            [{"number": 1, "state": "closed", "labels": [], "blockers": []}],
        ]

        from wave_runner.models import Task, TaskState, PlannedTask, PipelineStage, TaskResult
        mock_planner.compute_wave.return_value = [
            PlannedTask(task=Task(number=1, state=TaskState.OPEN), stage=PipelineStage.FULL),
        ]

        async def fake_run_wave(*a, **kw):
            return [TaskResult(number=1, success=True, branch="task/1")]

        mock_exec.run_wave = fake_run_wave
        mock_exec.run_merge_phase.return_value = [TaskResult(number=1, success=True, branch="task/1")]

        args = parse_args(["--prd", "99"])
        result = main_loop(args)

        assert result == "complete"
        mock_git.push_branch.assert_called_once()
        mock_github.create_pr.assert_called_once()
