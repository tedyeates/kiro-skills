---
name: orchestrate
description: Autonomous PRD implementation — fetches unblocked tasks, spawns parallel agents in isolated worktrees, verifies, merges, repeats until done. Use when user says "orchestrate", "run the orchestrator", "implement the PRD", "run tasks", or wants to autonomously implement a set of GitHub issues.
---
# Orchestrate

Autonomously implement a PRD by coordinating implementer and reviewer agents across isolated git worktrees. Fetches unblocked tasks from GitHub, spawns agents in parallel, verifies deterministically, merges sequentially, repeats wave by wave until all tasks are done, then raises a PR.

## Prerequisites

- `.kiro/steering/project-config.md` exists with `repo`, `test_command`, `setup_command` configured (run `setup` skill first)
- `gh` CLI authenticated (`gh auth status`)
- GitHub labels created (run `setup` skill)
- PRD issue with sub-issues and `blocked_by` dependencies (run `to-issues` skill)

## Process

### 1. Gather inputs

Read `.kiro/steering/project-config.md` YAML frontmatter to get:
- `repo` — GitHub owner/repo
- `test_command` — e.g. `pnpm test`, `.venv/Scripts/pytest`
- `type_check_command` — e.g. `tsc --noEmit`, `.venv/Scripts/mypy .` (optional)
- `build_command` — e.g. `pnpm build` (optional)
- `setup_command` — e.g. `pnpm install` (optional)
- `concurrency` — max parallel agents (default 3)

Ask the user:
1. **Which PRD issue number?** (or extract from user's message)
2. **Auto or wave-by-wave?** Auto runs all waves without pausing. Wave-by-wave asks for confirmation between waves.

### 2. Fetch PRD and build task graph

```bash
# Fetch PRD issue body to extract design.md path
gh issue view <prd_number> --repo <repo> --json body --jq .body
```

Extract `Design: <path>` from the body.

```bash
# Fetch all sub-issues
gh api repos/<repo>/issues/<prd_number>/sub_issues?per_page=100
```

For each sub-issue, fetch blockers:
```bash
gh api repos/<repo>/issues/<number>/dependencies/blocked_by
```

Build the task graph: each task has `number`, `state` (open/closed), `labels`, and `blockers` (list of issue numbers).

### 3. Compute current wave

Eligible tasks for this wave:
- State: open
- Label: `ready-for-agent` OR `implementing` OR `reviewing` OR `merging`
- NOT labelled `*-failed` (skip these — human must relabel)
- All blockers: closed

Display the wave plan:
```
Wave 1:
  #31 — Create orchestrate SKILL.md (ready-for-agent → full pipeline)
  #32 — Rewrite reviewer prompt (ready-for-agent → full pipeline)
  #33 — Update implementer prompt (implementing → resume from review)
```

Ask: **"Proceed with this wave?"** (skip in auto mode after first wave)

### 4. Create/checkout feature branch

```bash
# Derive slug from PRD title (lowercase, hyphens, truncate)
git checkout main
git pull
git checkout -b feature/<prd_number>-<slug>  # or checkout existing if resuming
```

If branch already exists (resume), just check it out.

### 5. Per-task: Create worktree and setup

For each task in the wave, determine entry point from labels:

| Label | Action |
|-------|--------|
| `ready-for-agent` | Full pipeline (implement → review → merge) |
| `implementing` | Nuke worktree if exists, re-run implementer |
| `reviewing` | Re-run reviewer in existing worktree |
| `merging` | Skip to merge phase |

Create worktrees (for tasks needing implement or review):
```bash
# Worktree path: ../<repo-name>-waves/<prd-number>/<issue-number>/
git worktree add -b task/<number> ../<repo>-waves/<prd>/<number>/ feature/<prd>-<slug>
```

Run setup in each worktree (if `setup_command` configured):
```bash
cd <worktree_path> && <setup_command>
```

### 6. Implement phase (parallel)

For tasks entering the full pipeline, update labels:
```bash
gh issue edit <number> --repo <repo> --remove-label "ready-for-agent" --add-label "implementing"
```

Spawn up to `concurrency` implementer agents in parallel:
```bash
kiro-cli chat --no-interactive --agent implementer \
  "Implement issue #<N>. Design: <design_path>. Check commands — test: `<test_command>`, type_check: `<type_check_command>`, build: `<build_command>`. Run these to verify your work. You have 3 attempts to get them passing." \
  > ../<repo>-waves/<prd>/<N>/agent.log 2>&1
```

Each invocation runs with `working_dir` set to the worktree path.

**Wait for all to complete.**

### 7. Post-implement trust gate (check-work)

For each task that completed the implement phase, run in the worktree:
```bash
<type_check_command>  # if configured
<test_command>
<build_command>       # if configured
```

**Parse result:**
- Check agent log for `AGENT_RESULT: SUCCESS` or `AGENT_RESULT: FAILED — <reason>`
- Fallback: if no AGENT_RESULT line found and exit code 0, treat as success (log warning)
- If no AGENT_RESULT and exit code non-zero, treat as failure

**On check-work pass:** update label to `reviewing`, proceed to review phase.

**On check-work fail:**
```bash
gh issue edit <number> --repo <repo> --remove-label "implementing" --add-label "impl-failed"
```
Report: "Task #N failed implementation. Log: `<path>/agent.log`"
Surface last 20 lines of log. **Halt the wave.**

### 8. Review phase (parallel)

Spawn up to `concurrency` reviewer agents in parallel:
```bash
kiro-cli chat --no-interactive --agent reviewer \
  "Review issue #<N>. Base ref: feature/<prd>-<slug>. Check commands — test: `<test_command>`, type_check: `<type_check_command>`, build: `<build_command>`. Review the diff, check test quality/coverage, fix issues. 3 attempts to get checks passing." \
  > ../<repo>-waves/<prd>/<N>/reviewer.log 2>&1
```

Each invocation runs with `working_dir` set to the worktree path.

**Wait for all to complete.**

### 9. Post-review trust gate (check-work)

Same as post-implement: run check-work in each worktree.

**On pass:** update label to `merging`.

**On fail:**
```bash
gh issue edit <number> --repo <repo> --remove-label "reviewing" --add-label "review-failed"
```
Report failure, surface log tail. **Halt the wave.**

### 10. Merge phase (sequential)

Switch to main repo directory (on feature branch). For each task labelled `merging`:

```bash
git merge task/<number> --no-edit
```

**If merge succeeds cleanly:**
- Run check-work in main repo (test + type_check + build)
- If passes → success
- If fails → attempt fix (see below)

**If merge has conflicts:**
- Read conflict markers from affected files
- Resolve the conflicts (fix the code)
- `git add .` then `git commit --no-edit`
- Run check-work
- If passes → success
- If fails → attempt fix (see below)

**Fix attempts (up to 3):**
1. Read test/type-check/build output
2. Fix the issue
3. `git add .` && `git commit -m "fix: resolve merge issue for #<N>"`
4. Re-run check-work
5. If still fails after 3 attempts → revert and fail

**On merge success:**
```bash
# Close issue
gh issue close <number> --repo <repo>
# Cleanup worktree
git worktree remove ../<repo>-waves/<prd>/<number>/ --force
git branch -D task/<number>
```

If worktree removal fails (Windows lock), log warning and continue.

**On merge failure (after 3 attempts):**
```bash
git merge --abort  # or git reset --hard HEAD~1 if already committed
gh issue edit <number> --repo <repo> --remove-label "merging" --add-label "merge-failed"
```
Report failure. **Halt the wave.**

### 11. Wave complete

After all tasks in the wave are merged:

- Report: "Wave complete. N tasks merged successfully."
- If **wave-by-wave mode**: ask "Continue to next wave?"
- If **auto mode**: proceed immediately

Check if more waves remain (open sub-issues with unresolved blockers that are now closeable). If yes, go to step 3. If no more tasks, proceed to step 12.

### 12. Push and raise PR

```bash
git push -u origin feature/<prd>-<slug>
gh pr create --repo <repo> --title "feat: <PRD title>" --body "Implements #<prd_number>\n\nClosed issues:\n- #N\n- #M\n..."
```

Report: "PR raised. All tasks complete."

## Failure Handling Summary

| Failure | Action |
|---------|--------|
| Implementer fails (AGENT_RESULT: FAILED) | Label `impl-failed`, halt wave |
| Post-implement check-work fails | Label `impl-failed`, halt wave |
| Reviewer fails | Label `review-failed`, halt wave |
| Post-review check-work fails | Label `review-failed`, halt wave |
| Merge conflict unresolvable (3 attempts) | Revert, label `merge-failed`, halt wave |
| Post-merge check-work fails (3 attempts) | Revert, label `merge-failed`, halt wave |
| Agent "no result" (no AGENT_RESULT + exit 0) | Treat as success, log warning, run trust gate |
| Agent timeout | Treat as failure, report timeout |
| Worktree removal fails | Log warning, continue |

## Resume

Re-running the skill on the same PRD picks up where it left off based on labels:

| Label | Resume action |
|-------|--------------|
| `ready-for-agent` + all blockers closed | Full pipeline |
| `implementing` | Delete worktree, re-run implementer from scratch |
| `reviewing` | Re-run reviewer in existing worktree |
| `merging` | Re-attempt merge |
| `impl-failed` / `review-failed` / `merge-failed` | Skip (human must fix and relabel) |
| Closed | Skip (already done) |
