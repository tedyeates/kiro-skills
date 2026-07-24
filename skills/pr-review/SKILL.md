---
name: pr-review
description: Review an open PR across three axes — security, test quality, and design conformance — by spawning sub-agents in parallel and posting GitHub reviews with inline comments. Use when user says "pr-review", "review PR", "review #42", or wants automated PR feedback.
---
# PR Review

Orchestrator skill that reviews an open PR across three axes:
1. **Security** — OWASP/ASVS/CWE checklist (`pr-security` agent)
2. **Test Quality** — Beck/ISTQB/SMURF checklist (`pr-test-quality` agent)
3. **Design Conformance** — spec section comparison including persona access matrix enforcement (`pr-design-conformance` agent)

Posts results as GitHub PR reviews with inline comments.

## Invocation

```
/pr-review <PR#>
```

## Prerequisites

- `gh` CLI authenticated
- `.kiro/steering/project-config.md` with `Repo:` configured (created by `setup` skill)
- Sub-agents deployed: `pr-security`, `pr-test-quality`, `pr-design-conformance`

## Process

### 1. Read config

Read `.kiro/steering/project-config.md` to extract `{owner}/{repo}`.

### 2. Checkout PR branch

Ensure the PR branch is checked out locally so sub-agents can read files and run `git diff`:

```bash
gh pr checkout {pr_number}
```

Store the base branch ref for sub-agents:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number} --jq '.base.ref'
```

### 3. Fetch PR metadata and file list

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number} --jq '{body: .body, base: .base.ref, head: .head.ref}'
```

Fetch the list of changed files (needed for position computation in step 7):

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/files --paginate
```

This returns an array of objects with `filename`, `patch`, `additions`, `deletions`, `status`. Keep this data for position mapping.

### 4. Resolve specs

Three specs to locate:

**design.md** — fallback chain:
1. PR body contains `Spec: .kiro/specs/<path>/design.md` → use that path
2. Search `.kiro/specs/` directories for one matching the branch name or PR title keywords
3. Ask user: "Which spec does this PR implement?"
4. If user declines or no spec found → skip design-conformance axis entirely

**security.md** — look for `.kiro/specs/security.md`:
- If exists → read it
- If not → bootstrap (see step 4b)

**testing.md** — look for `.kiro/specs/testing.md`:
- If exists → read it
- If not → bootstrap (see step 4b)

### 4b. Bootstrap missing project specs

If `security.md` or `testing.md` don't exist, create minimal versions by scanning the codebase:

**security.md inference:**
- Check `package.json` / `requirements.txt` / `Cargo.toml` for auth libraries
- Look for auth middleware, RLS policies, session config
- Identify sensitive paths (API routes, admin endpoints)
- Write to `.kiro/specs/security.md`

**testing.md inference:**
- Check for test framework config (`vitest.config`, `jest.config`, `pytest.ini`, etc.)
- Identify test file patterns and directories
- Note assertion libraries and mocking approaches
- Write to `.kiro/specs/testing.md`

Both files use this template:

```markdown
# {Security|Testing} Spec

## Overview
{1-2 sentences about the project's approach}

## Architecture
{Key patterns, frameworks, libraries}

## File Index
| Path | Summary |
|------|---------|
```

### 5. Spawn sub-agents in parallel

Sub-agents read files from disk and run `git diff` themselves. Do NOT pass inline diffs — pass only the context they need to orient: PR number, base branch, file list, and the relevant spec.

Use the subagent tool with all three stages having no `depends_on` (parallel execution):

```json
{
  "task": "Review PR #{pr_number}",
  "stages": [
    {
      "name": "security",
      "role": "pr-security",
      "prompt_template": "Review PR #{pr_number} for security issues.\n\nRepo: {owner}/{repo}\nBase branch: {base_branch}\nChanged files:\n{file_list}\n\nRun `git diff {base_branch}...HEAD` to see the diff. Read source files as needed.\n\nSECURITY SPEC:\n{security_md_contents}\n\nReturn JSON: { summary: string, comments: [{ path: string, line?: number, body: string }] }"
    },
    {
      "name": "test-quality",
      "role": "pr-test-quality",
      "prompt_template": "Review PR #{pr_number} for test quality issues.\n\nRepo: {owner}/{repo}\nBase branch: {base_branch}\nChanged files:\n{file_list}\n\nRun `git diff {base_branch}...HEAD` to see the diff. Read source files as needed.\n\nTESTING SPEC:\n{testing_md_contents}\n\nReturn JSON: { summary: string, comments: [{ path: string, line?: number, body: string }] }"
    },
    {
      "name": "design-conformance",
      "role": "pr-design-conformance",
      "prompt_template": "Compare PR #{pr_number} against the design spec and report deviations.\n\nRepo: {owner}/{repo}\nBase branch: {base_branch}\nChanged files:\n{file_list}\n\nRun `git diff {base_branch}...HEAD` to see the diff. Read source files as needed.\n\nDESIGN SPEC:\n{design_md_contents}\n\nReturn JSON: { summary: string, comments: [{ path: string, line?: number, body: string }] }"
    }
  ]
}
```

If design.md was not found (step 4), omit the `design-conformance` stage entirely.

### 6. Collect and transform results

Each sub-agent returns:

```typescript
interface SubAgentResult {
  summary: string;    // Markdown summary with severity counts
  comments: Comment[];
}

interface Comment {
  path: string;       // Relative file path
  line?: number;      // Line in new file version (absent = file-level)
  body: string;       // Markdown with severity tag prefix
}
```

Parse each result's JSON.

### 7. Post GitHub reviews

#### 7a. Clean up pending reviews

Before posting, delete any stale PENDING reviews owned by the current user:

```bash
CURRENT_USER=$(gh api /user --jq '.login')
PENDING_IDS=$(gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  --jq "[.[] | select(.state == \"PENDING\" and .user.login == \"$CURRENT_USER\")] | .[].id")

for id in $PENDING_IDS; do
  gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews/$id --method DELETE
done
```

#### 7b. Compute positions

Sub-agents return `line` (line number in the new file version). The GitHub Reviews API requires `position` — a 1-indexed offset within the diff hunk counting from the `@@` line.

For each comment with a `line` value, compute `position` from the patch data fetched in step 3:
1. Find the file's `patch` string from the files array
2. Walk through the patch lines, tracking the current new-file line number from the `@@` header (the `+` start value)
3. For each line that is context (` `) or addition (`+`), increment the new-file line counter
4. When the new-file line counter matches the comment's `line`, the current 1-indexed offset from the `@@` is the `position`

If a comment has no `line` (file-level finding), use `position: 1`.

#### 7c. Post reviews

For each sub-agent result, post according to its findings:

**Case A — findings exist:**

Transform to GitHub Review API payload:

```json
{
  "body": "{summary}",
  "event": "COMMENT",
  "comments": [
    {
      "path": "src/file.ts",
      "body": "**[HIGH]** Issue description...",
      "position": 12
    }
  ]
}
```

All reviews use `event: "COMMENT"` — the `REQUEST_CHANGES` event is not used because it fails when the reviewer is the PR author (common in solo projects and bot-less setups).

Post via:
```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews \
  --method POST \
  --input payload.json
```

**Case B — no findings (clean pass):**

Do NOT post a review. Post a regular comment instead:

```bash
gh pr comment {pr_number} --repo {owner}/{repo} \
  --body "✓ {Axis name}: no issues found."
```

Axis names: "Security", "Test Quality", "Design Conformance"

### 8. Report summary

Print a final summary to the user:

```
PR #{pr_number} reviewed:
- 🔒 Security: {X findings | ✓ clean}
- 🧪 Test Quality: {X findings | ✓ clean}
- 📐 Design Conformance: {X findings | ✓ clean | ⊘ skipped (no spec)}

Reviews posted to: https://github.com/{owner}/{repo}/pull/{pr_number}
```

---

## Edge Cases

**Binary files:** Exclude binary files from the file list passed to sub-agents.

**Draft PRs:** Review normally — drafts benefit from early feedback.

**No test files in diff:** The test-quality agent handles this gracefully — it checks whether *existing* tests cover new code, not just new tests in the diff.

**Sub-agent parse failure:** If a sub-agent's output can't be parsed as valid JSON, post a comment noting the axis failed and include the raw output for debugging:
```bash
gh pr comment {pr_number} --repo {owner}/{repo} \
  --body "⚠️ {Axis} review failed to produce structured output. Raw result:\n\n{raw_output}"
```
