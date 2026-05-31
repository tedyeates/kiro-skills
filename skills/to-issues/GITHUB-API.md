# GitHub API Reference

API version: `2026-03-10`. All `gh api` calls require this header (set automatically by `gh`).

## Create issue

```bash
gh issue create \
  --title "Task: {title}" \
  --body "{body}" \
  --label "ready-for-agent" \
  --json id,number,url
```

Returns `id` (needed for sub-issues/dependencies), `number` (human reference), `url`.

## Add sub-issue

Links a child task to the parent PRD issue. Requires the child's `id` (not number).

```bash
gh api repos/{owner}/{repo}/issues/{parent_number}/sub_issues \
  -X POST \
  -f sub_issue_id={child_id}
```

## Add dependency (blocked by)

Establishes execution ordering. The `issue_id` is the **blocker's** id.

```bash
gh api repos/{owner}/{repo}/issues/{task_number}/dependencies/blocked_by \
  -X POST \
  -f issue_id={blocker_id}
```

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

## Orchestrator pattern (Option C)

1. **Initial**: call sub_issues + blocked_by per task → build full graph
2. **Per batch**: call sub_issues only → refresh open/closed state
3. **Eligible tasks**: open + `ready-for-agent` label + all blockers closed

## Notes

- `id` vs `number`: API endpoints for sub-issues and dependencies use the issue `id` (large integer), not the `#number`. Always capture `id` at creation time.
- Rate limits: 5,000 requests/hour (primary), 80 content-generating POST/minute (secondary). A 10-task PRD uses ~31 POSTs.
- Create issues in dependency order (blockers first) so their IDs are available for subsequent dependency calls.
