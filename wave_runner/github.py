"""GitHub CLI interactions for issue and PR management."""

import json
import re
import subprocess


def fetch_prd(number: int, repo: str) -> dict:
    """Fetch PRD issue details. Returns dict with title, body, design_path."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{number}", "--jq", "{title: .title, body: .body}"],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    match = re.search(r"^Design:\s*(.+)$", data["body"] or "", re.MULTILINE)
    data["design_path"] = match.group(1).strip() if match else None
    return data


def fetch_sub_issues(prd_number: int, repo: str) -> list[dict]:
    """Fetch all sub-issues of a PRD with their blockers."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{prd_number}/sub_issues?per_page=100"],
        check=True,
        capture_output=True,
        text=True,
    )
    issues = json.loads(result.stdout)
    tasks = []
    for issue in issues:
        blockers_result = subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/{issue['number']}/dependencies/blocked_by"],
            check=True,
            capture_output=True,
            text=True,
        )
        blockers = json.loads(blockers_result.stdout)
        tasks.append({
            "id": issue["id"],
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "labels": [l["name"] for l in issue.get("labels", [])],
            "blockers": [b["number"] for b in blockers],
        })
    return tasks


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
