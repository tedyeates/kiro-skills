import pytest
from pathlib import Path

from wave_runner.config import load_config, Config, ConfigError


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a minimal repo structure with project-config.md."""
    config_dir = tmp_path / ".kiro" / "steering"
    config_dir.mkdir(parents=True)
    return tmp_path


def write_config(repo_root: Path, frontmatter: str):
    path = repo_root / ".kiro" / "steering" / "project-config.md"
    path.write_text(f"---\n{frontmatter}---\n# Project Configuration\n")


class TestLoadConfig:
    def test_full_config(self, tmp_repo):
        write_config(tmp_repo, "repo: owner/repo\ntest_command: pytest\nbuild_command: npm build\ntype_check_command: mypy .\nconcurrency: 5\n")
        cfg = load_config(tmp_repo)
        assert cfg == Config(repo="owner/repo", test_command="pytest", build_command="npm build", type_check_command="mypy .", concurrency=5)

    def test_defaults_for_optional_fields(self, tmp_repo):
        write_config(tmp_repo, "repo: owner/repo\ntest_command: pytest\n")
        cfg = load_config(tmp_repo)
        assert cfg.build_command is None
        assert cfg.type_check_command is None
        assert cfg.concurrency == 3

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path)

    def test_raises_on_missing_frontmatter(self, tmp_repo):
        path = tmp_repo / ".kiro" / "steering" / "project-config.md"
        path.write_text("# No frontmatter here\n")
        with pytest.raises(ConfigError, match="frontmatter"):
            load_config(tmp_repo)

    def test_raises_on_invalid_yaml(self, tmp_repo):
        write_config(tmp_repo, "repo: [invalid\n")
        with pytest.raises(ConfigError, match="frontmatter"):
            load_config(tmp_repo)

    def test_raises_on_missing_required_field(self, tmp_repo):
        write_config(tmp_repo, "test_command: pytest\n")
        with pytest.raises(ConfigError, match="repo"):
            load_config(tmp_repo)

    def test_raises_on_missing_test_command(self, tmp_repo):
        write_config(tmp_repo, "repo: owner/repo\n")
        with pytest.raises(ConfigError, match="test_command"):
            load_config(tmp_repo)
