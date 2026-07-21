---
name: pr-review
description: Review an open PR across three axes — security, test quality, and design conformance — by spawning sub-agents in parallel and posting GitHub reviews with inline comments. Use when user says "pr-review", "review PR", "review #42", or wants automated PR feedback.
---
# PR Review

Orchestrator skill that reviews an open PR across three axes:
1. **Security** — OWASP/ASVS/CWE checklist (`pr-security` agent)
2. **Test Quality** — Beck/ISTQB/SMURF checklist (`pr-test-quality` agent)
3. **Design Conformance** — spec section comparison (`pr-design-conformance` agent)

Posts results as GitHub PR reviews with inline comments, severity-based event types, and clean-pass notifications.

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

### 2. Fetch PR metadata and diff

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number} --template '{{.body}}'
```

Fetch file-level diff with line positions (NOT `gh pr diff` which lacks line mapping):

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/files --paginate
```

This returns an array of objects with `filename`, `patch`, `additions`, `deletions`, `status`. Reconstruct a unified diff from the patches for each file.

### 3. Resolve specs

Three specs to locate:

**design.md** — fallback chain:
1. PR body contains `Spec: .kiro/specs/<path>/design.md` → use that path
2. Search `.kiro/specs/` directories for one matching the branch name or PR title keywords
3. Ask user: "Which spec does this PR implement?"
4. If user declines or no spec found → skip design-conformance axis entirely

**security.md** — look for `.kiro/specs/security.md`:
- If exists → read it
- If not → bootstrap (see step 3b)

**testing.md** — look for `.kiro/specs/testing.md`:
- If exists → read it
- If not → bootstrap (see step 3b)

### 3b. Bootstrap missing project specs

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

### 4. Spawn sub-agents in parallel

Use the subagent tool with all three stages having no `depends_on` (parallel execution):

```json
{
  "task": "Review PR #{pr_number}",
  "stages": [
    {
      "name": "security",
      "role": "pr-security",
      "prompt_template": "Review this PR diff for security issues.\n\nPR: {owner}/{repo}#{pr_number}\n\nDIFF:\n{diff}\n\nSECURITY SPEC:\n{security_md_contents}\n\nReturn JSON: { summary: string, comments: [{ path: string, line?: number, body: string }] }"
    },
    {
      "name": "test-quality",
      "role": "pr-test-quality",
      "prompt_template": "Review this PR diff for test quality issues.\n\nPR: {owner}/{repo}#{pr_number}\n\nDIFF:\n{diff}\n\nTESTING SPEC:\n{testing_md_contents}\n\nReturn JSON: { summary: string, comments: [{ path: string, line?: number, body: string }] }"
    },
    {
      "name": "design-conformance",
      "role": "pr-design-conformance",
      "prompt_template": "Compare this PR diff against the design spec and report deviations.\n\nPR: {owner}/{repo}#{pr_number}\n\nDIFF:\n{diff}\n\nDESIGN SPEC:\n{design_md_contents}\n\nReturn JSON: { summary: string, comments: [{ path: string, line?: number, body: string }] }"
    }
  ]
}
```

If design.md was not found (step 3), omit the `design-conformance` stage entirely.

### 5. Collect and transform results

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

Parse each result's JSON. For each sub-agent, determine the highest severity from its comments:
- Parse severity from `body` prefix: `**[CRITICAL]**`, `**[HIGH]**`, `**[MEDIUM]**`, `**[LOW]**`
- Map to event type (see step 6)

### 6. Post GitHub reviews

For each sub-agent result, post according to its findings:

**Case A — findings exist:**

Transform to GitHub Review API payload:

```json
{
  "body": "{summary}",
  "event": "{REQUEST_CHANGES|COMMENT}",
  "comments": [
    {
      "path": "src/file.ts",
      "body": "**[HIGH]** Issue description...",
      "line": 42,
      "side": "RIGHT"
    }
  ]
}
```

Severity → event mapping:

| Highest severity in findings | `event` value |
|------------------------------|---------------|
| Critical or High             | `REQUEST_CHANGES` |
| Medium or Low only           | `COMMENT` |

Comment transformation rules:
- Comment with `line` → include `line` and `side: "RIGHT"` (new file side)
- Comment without `line` → include `subject_type: "file"` (file-level comment)

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

### 7. Report summary

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

**Large PRs:** If the diff is very large, include all files but note in the sub-agent prompt that the review should focus on security/test/design-critical paths rather than mechanical changes.

**Binary files:** Exclude binary files from the diff passed to sub-agents.

**Draft PRs:** Review normally — drafts benefit from early feedback.

**No test files in diff:** The test-quality agent handles this gracefully — it checks whether *existing* tests cover new code, not just new tests in the diff.

**Sub-agent parse failure:** If a sub-agent's output can't be parsed as valid JSON, post a comment noting the axis failed and include the raw output for debugging:
```bash
gh pr comment {pr_number} --repo {owner}/{repo} \
  --body "⚠️ {Axis} review failed to produce structured output. Raw result:\n\n{raw_output}"
```
