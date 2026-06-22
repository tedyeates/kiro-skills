"""Git operations for the wave-runner orchestrator."""

import subprocess


def create_feature_branch(name: str, base: str) -> None:
    """Create and check out a feature branch from base."""
    subprocess.run(
        ["git", "checkout", "-b", name, base],
        check=True,
        capture_output=True,
        text=True,
    )


def create_worktree(branch: str, path: str, base: str) -> None:
    """Create a worktree at path on a new branch forked from base."""
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, path, base],
        check=True,
        capture_output=True,
        text=True,
    )


def remove_worktree(path: str) -> None:
    """Remove a worktree and prune metadata."""
    subprocess.run(
        ["git", "worktree", "remove", path, "--force"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "worktree", "prune"],
        check=True,
        capture_output=True,
        text=True,
    )


def merge_branch(source: str, cwd: str) -> str:
    """Merge source branch into current branch in given directory.

    Returns 'success' or 'conflict'.
    """
    try:
        subprocess.run(
            ["git", "merge", source, "--no-edit"],
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return "success"
    except subprocess.CalledProcessError:
        return "conflict"


def revert_merge(cwd: str) -> None:
    """Abort a conflicted merge or undo a committed merge.

    Detects whether a merge is in progress (conflict state) and uses
    merge --abort; otherwise resets to before the merge commit.
    """
    # Check if we're mid-merge (conflict state)
    merge_head = subprocess.run(
        ["git", "rev-parse", "--verify", "MERGE_HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if merge_head.returncode == 0:
        subprocess.run(
            ["git", "merge", "--abort"],
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
    else:
        subprocess.run(
            ["git", "reset", "--hard", "HEAD~1"],
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
        )


def push_branch(branch: str) -> None:
    """Push branch with -u flag to set up remote tracking."""
    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        check=True,
        capture_output=True,
        text=True,
    )
