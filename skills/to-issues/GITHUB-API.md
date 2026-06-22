# GitHub API Reference

## Create issue

`gh issue create` does NOT support `--json`. To get the `id` back (needed for sub-issues/dependencies), use the REST API:

```bash
gh api repos/{owner}/{repo}/issues \
  -X POST \
  -f title="Task: {title}" \
  -f body="{body}" \
  --jq "{id: .id, number: .number, url: .html_url}"
```

To add a label at creation time, pass it as a JSON array:

```bash
gh api repos/{owner}/{repo}/issues \
  -X POST \
  -f title="Task: {title}" \
  -f body="{body}" \
  -f "labels[][name]={label}" \
  --jq "{id: .id, number: .number, url: .html_url}"
```

Alternatively, add labels after creation:

```bash
gh issue edit {number} --add-label "ready-for-agent"
```

## Add sub-issue

Links a child task to the parent PRD issue. Requires the child's `id` (not number). Use `-F` (not `-f`) to send as integer:

```bash
gh api repos/{owner}/{repo}/issues/{parent_number}/sub_issues \
  -X POST \
  -F sub_issue_id={child_id}
```

**Critical:** `-f` sends strings, `-F` sends integers/booleans. The sub-issues API requires an integer `sub_issue_id`.

## Add dependency (blocked by)

Establishes execution ordering. Use `-F` for the integer id. Requires API version header:

```bash
gh api repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by \
  -X POST \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  -F issue_id={blocker_id}
```

**Critical:** `issue_id` is the blocker's `id` (large integer), not its `#number`.

## Read operations (for orchestrator)

### List all sub-issues of parent

```bash
gh api repos/{owner}/{repo}/issues/{parent_number}/sub_issues?per_page=100
```

Returns array of issues with `id`, `number`, `state`, `labels`.

### List blockers for a task

```bash
gh api repos/{owner}/{repo}/issues/{task_number}/dependencies/blocked_by
```

Returns array of blocking issues with their `state` (open/closed).

## Orchestrator pattern

1. **Initial**: call sub_issues + blocked_by per task → build full graph
2. **Per batch**: call sub_issues only → refresh open/closed state
3. **Eligible tasks**: open + `ready-for-agent` label + all blockers closed

## Notes

- `id` vs `number`: API endpoints for sub-issues and dependencies use the issue `id` (large integer), not the `#number`. Always capture `id` at creation time.
- `-f` vs `-F`: Use `-f` for string fields (title, body). Use `-F` for integer fields (sub_issue_id, blocker_id).
- `--jq`: Use to extract specific fields from the response JSON.
- `gh issue create` only returns a URL to stdout — no `--json` flag exists. Use `gh api` directly when you need the `id`.
- Rate limits: 5,000 requests/hour (primary), 80 content-generating POST/minute (secondary). A 10-task PRD uses ~31 POSTs.
- Create issues in dependency order (blockers first) so their IDs are available for subsequent dependency calls.
