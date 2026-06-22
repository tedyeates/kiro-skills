from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


class ConfigError(Exception):
    pass


@dataclass
class Config:
    repo: str
    test_command: str
    build_command: Optional[str] = None
    type_check_command: Optional[str] = None
    concurrency: int = 3


def load_config(repo_root: Path) -> Config:
    """Parse YAML frontmatter from .kiro/steering/project-config.md."""
    path = repo_root / ".kiro" / "steering" / "project-config.md"
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ConfigError(f"No YAML frontmatter in {path}")

    end = text.find("---", 3)
    if end == -1:
        raise ConfigError(f"No YAML frontmatter in {path}")

    try:
        data = yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        raise ConfigError(f"Invalid YAML frontmatter in {path}")

    if not isinstance(data, dict):
        raise ConfigError(f"Invalid YAML frontmatter in {path}")

    for field in ("repo", "test_command"):
        if field not in data:
            raise ConfigError(f"Missing required field '{field}' in {path}")

    return Config(
        repo=data["repo"],
        test_command=data["test_command"],
        build_command=data.get("build_command"),
        type_check_command=data.get("type_check_command"),
        concurrency=data.get("concurrency", 3),
    )
