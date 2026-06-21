"""GitHub CLI mutations for issue and PR management."""

import subprocess


def update_label(number: int, old: str, new: str, repo: str) -> None:
    """Remove old label and add new label to an issue."""
    subprocess.run(
        ["gh", "issue", "edit", str(number), "--remove-label", old, "--add-label", new, "--repo", repo],
        check=True,
        capture_output=True,
    )


def post_comment(number: int, body: str, repo: str) -> None:
    """Post a markdown comment on an issue."""
    subprocess.run(
        ["gh", "issue", "comment", str(number), "--body", body, "--repo", repo],
        check=True,
        capture_output=True,
    )


def close_issue(number: int, repo: str) -> None:
    """Close an issue."""
    subprocess.run(
        ["gh", "issue", "close", str(number), "--repo", repo],
        check=True,
        capture_output=True,
    )


def create_pr(head: str, base: str, title: str, body: str, repo: str) -> None:
    """Create a pull request via gh CLI."""
    subprocess.run(
        ["gh", "pr", "create", "--head", head, "--base", base, "--title", title, "--body", body, "--repo", repo],
        check=True,
        capture_output=True,
    )
