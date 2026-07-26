# GitHub API Reference

## Passing the issue body (read this first)

Ticket bodies are multi-line markdown. **Never inline them as a shell string** and **never
pass a `@path` pointer with `-f` or `--body`** — those store the value verbatim, so an
`@/tmp/tk/01.md` "pointer" ends up as the literal issue body and the real content is lost when
the temp file is cleaned up.

Two safe ways to deliver a body:

1. **`gh api` with a file** — write the body to a file, then read it with **`-F body=@<path>`**
   (capital `-F` triggers `@file` expansion; lowercase `-f` does **not** — it would store the
   literal string `@<path>`):

   ```bash
   gh api repos/{owner}/{repo}/issues -X POST \
     -f title="Task: {title}" \
     -F body=@"{bodyfile}" \
     --jq "{id: .id, number: .number, url: .html_url}"
   ```

2. **`gh issue create --body-file`** — but this returns only a URL, so use it only when you
   don't need the `id`. To add labels/sub-issues/deps you need the `id`, so prefer option 1.

**Where to write the body file:** use a repo-tracked or session-stable path (e.g.
`.scratch/{name}/bodies/NN.md`), NOT bare `/tmp` — `/tmp` is cleared on reboot/cleanup and any
issue still pointing at it becomes a dangling reference. If you must use `/tmp`, read the file
into the request with `-F body=@...` at creation time so the content is uploaded, never
referenced.

## Create issue

`gh issue create` does NOT support `--json`. To get the `id` back (needed for sub-issues/dependencies), use the REST API. Pass the body from a file with **`-F body=@<path>`** (see above):

```bash
gh api repos/{owner}/{repo}/issues \
  -X POST \
  -f title="Task: {title}" \
  -F body=@"{bodyfile}" \
  --jq "{id: .id, number: .number, url: .html_url}"
```

To add a label at creation time, pass it as a JSON array:

```bash
gh api repos/{owner}/{repo}/issues \
  -X POST \
  -f title="Task: {title}" \
  -F body=@"{bodyfile}" \
  -f "labels[][name]={label}" \
  --jq "{id: .id, number: .number, url: .html_url}"
```

Alternatively, add labels after creation:

```bash
gh issue edit {number} --add-label "ready-for-agent"
```

## Add sub-issue

Links a child task to the parent spec issue. Requires the child's `id` (not number). Use `-F` (not `-f`) to send as integer:

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
- `-f` vs `-F`: Use `-f` for static string fields (title). Use `-F` for integer fields (sub_issue_id, blocker_id) **and** to read a value from a file via `@<path>` (e.g. the multi-line `body=@bodyfile`). `-f` never expands `@` — it stores the literal string.
- **Body delivery**: always upload the body content (`-F body=@file` or `--body-file`), never a `@/tmp/...` pointer via `-f`/`--body`. See "Passing the issue body" at the top.
- `--jq`: Use to extract specific fields from the response JSON.
- `gh issue create` only returns a URL to stdout — no `--json` flag exists. Use `gh api` directly when you need the `id`.
- Rate limits: 5,000 requests/hour (primary), 80 content-generating POST/minute (secondary). A 10-task PRD uses ~31 POSTs.
- Create issues in dependency order (blockers first) so their IDs are available for subsequent dependency calls.
