---
name: fix-loop
description: Grind through a repo's ready, dependency-free bug/enhancement tickets one at a time, each on its own branch into a PR, by dispatching implementer sub-agents. The loop runs in-session and offloads each ticket's implementation to a sub-agent so the main context stays clean. Use when user says "fix loop", "grind through tickets", "simple loop for simple tasks", or wants standalone tickets implemented unattended.
---
# Fix Loop

Process every ready, standalone ticket in a repo sequentially. Each ticket is
implemented by an `implementer` **sub-agent** — so its work never fills the main
agent's context — gated on deterministic checks, and landed as its own PR
targeting the branch you launched from.

One implementer attempt per ticket. No reviewer, no blocker graph, no
halt-on-failure: a failed ticket is parked as a draft PR and relabelled, then
the loop continues to the next.

## Prerequisites

- `gh` CLI authenticated (`gh auth status`)
- `.kiro/steering/project-config.md` with `Repo:`, `test_command`, and
  `type_check_command` (created by `setup`)
- Labels `ready-for-agent` and `impl-failed` exist in the repo (run `setup` to provision)
- `implementer` agent deployed

## Process

### 1. Read config

Read `.kiro/steering/project-config.md` for `{owner}/{repo}`, `test_command`,
and `type_check_command`. If any are missing, tell the user to run `setup` and stop.

### 2. Startup guards

- **Dirty tree → refuse.** Run `git status --porcelain`; if it prints anything,
  stop with an error. The loop must never mix uncommitted work into an agent branch.
- **Capture the launch point:**
  - `base_branch` = `git rev-parse --abbrev-ref HEAD`
  - `base_sha` = `git rev-parse HEAD`
  - Every fix branch is cut from `base_sha`, and every PR targets `base_branch`.
- **Base branch must be on the remote** — PRs target it. If
  `git ls-remote --heads origin <base_branch>` is empty, warn the user to push it
  first (PR creation will otherwise fail).

### 3. Fetch candidates (host `gh`)

```bash
gh issue list --repo {owner}/{repo} --state open --label ready-for-agent \
  --json number,title,body,labels
```

For each candidate, resolve blocking edges:

```bash
gh api repos/{owner}/{repo}/issues/{n}/dependencies/blocked_by --jq "[.[].number]"
```

Treat an API error as "no dependency info available" — do not crash the loop.

### 4. Select eligible tickets

A ticket is **eligible** iff ALL hold:
- `state == "open"`
- carries `ready-for-agent`
- carries `bug` OR `enhancement`
- has **zero** blocking edges (any `blocked_by` entry → ineligible)

Order eligible tickets by **ascending issue number**. This is the one piece of
error-prone logic — get it exactly right.

Print the eligible plan plus a skipped-with-reason list. If the user only wants
a preview (e.g. "just show me the plan"), stop here without touching branches,
sub-agents, or the remote.

If there are **no** eligible tickets, report "Nothing to do" and stop.

### 5. Loop — one ticket at a time, ascending order

For each eligible ticket `#n`, sequentially (never in parallel):

1. **Cut a fresh branch from the launch commit:**
   ```bash
   git switch -c fix/issue-{n} {base_sha}
   ```
   Never `git switch` to `base_branch` itself. Cutting from `base_sha` keeps each
   fix independent and avoids any "switch back" step.

2. **Dispatch the implementer sub-agent** (blocking) using the `subagent` tool —
   one stage, role `implementer` — so the ticket's implementation work stays out
   of the main context:

   ```json
   {
     "task": "Implement fix-loop ticket #{n}",
     "stages": [
       {
         "name": "implement-{n}",
         "role": "implementer",
         "prompt_template": "Implement the following standalone ticket using TDD, then stop.\n\n## Ticket #{n}: {title}\n\n{body}\n\nWork only on the current branch (fix/issue-{n}). Implement the change and its tests. Do NOT open a PR, push, or close the issue — the orchestrator handles git. Read any design doc the ticket references for context.\n\nContext files: .kiro/steering/corrections.md and .kiro/corrections.md — read existing corrections before starting and append any new process errors."
       }
     ]
   }
   ```

   Include both `corrections.md` files in the sub-agent context per the
   corrections steering rules.

3. **Run deterministic checks in the main session** (the sub-agent's self-report
   is never the gate): run `type_check_command`, then `test_command`. Capture
   pass/fail.

4. **Commit whatever the implementer produced:**
   ```bash
   git add -A && git commit -m "fix: #{n} {title}"
   ```
   (If the implementer already committed and the tree is clean, skip.)

5. **Push and open a PR:**
   ```bash
   git push -u origin fix/issue-{n}
   ```

   - **Pass** (type-check + test both green):
     ```bash
     gh pr create --repo {owner}/{repo} --base {base_branch} --head fix/issue-{n} \
       --title "fix: #{n} {title}" --body "Closes #{n}"
     gh issue close {n} --repo {owner}/{repo}
     ```
     Close explicitly — since the PR base is not the default branch, merge
     auto-close will not fire.

   - **Fail:** open a **draft** PR for inspection, then relabel so the ticket is
     not re-picked and a human catches it:
     ```bash
     gh pr create --repo {owner}/{repo} --base {base_branch} --head fix/issue-{n} \
       --title "fix: #{n} {title} [impl-failed]" --body "Attempt for #{n}. Checks failed — see PR." --draft
     gh issue edit {n} --repo {owner}/{repo} --add-label impl-failed --remove-label ready-for-agent
     ```
     Do **not** retry and do **not** run a reviewer. Skip and continue.

6. Record the outcome (PR URL, pass/fail) and move to the next ticket.

### 6. Return to launch branch and summarise

```bash
git switch {base_branch}
```

Print an end-of-run summary:

```
Fix loop complete ({owner}/{repo}, base {base_branch}):
- ✓ Fixed: N   {#n → PR url, ...}
- ✗ Failed: M  {#n → draft PR url, relabelled impl-failed, ...}
```

## Rules

- **Sequential only** — one ticket, one branch, one sub-agent at a time. No parallelism.
- **Deterministic checks are the sole gate** — never trust the sub-agent's self-report.
- **No reviewer, no retry** — a human investigates failures.
- **Skip-and-continue** — one bad ticket never blocks the batch.
- **Independent tickets only** — any blocking edge → skip. Dependent work belongs in the PRD/wayfinder flow.

## Out of Scope

- Parallel execution, reviewer pass, second implementer attempt.
- Blocker-graph resolution or wave computation.
- Resuming or a label-based state machine across runs.
