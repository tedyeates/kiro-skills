<!-- GitHub: #30 https://github.com/tedyeates/kiro-skills/issues/30 -->


## Problem Statement

The wave_runner Python orchestrator is too complex and flaky — 8 modules, async parallelism, pre-review hooks, a merger agent, and hard-to-debug silent failures. Debugging requires reading Python tracebacks across multiple async tasks. The process itself (fetch unblocked tasks → implement → review → merge → repeat) is sound, but the implementation has too many moving parts.

## Solution

Replace wave_runner with a Kiro skill (`orchestrate`) that follows the same process as a procedural recipe. Kiro becomes the orchestrator — spawning agents as shell subprocesses with OS-level cwd isolation via git worktrees. The skill is deterministic (branching, merging, labelling, verification) and delegates only code writing to LLM agents. Failures are immediately visible (log files per task, halts on failure) rather than buried in async task results.

## User Stories

1. As a developer, I want to say "orchestrate" and have Kiro ask me for the PRD issue number and execution mode, so that I can start a run with minimal input.
2. As a developer, I want the skill to fetch all sub-issues of my PRD and compute waves from the dependency graph, so that tasks run in the correct order.
3. As a developer, I want the skill to show me the wave plan before executing, so that I can confirm it looks right.
4. As a developer, I want the skill to create a feature branch from main, so that all task work accumulates in one branch.
5. As a developer, I want each task to get its own git worktree forked from the feature branch, so that parallel agents don't conflict on the filesystem.
6. As a developer, I want `setup_command` to run in each worktree, so that dependencies are installed per-environment without copying directories.
7. As a developer, I want up to N implementer agents spawned in parallel (controlled by `concurrency` config), so that a wave of tasks runs efficiently.
8. As a developer, I want agents invoked as `kiro-cli chat --no-interactive --agent <name> "<prompt>"` with cwd set to the worktree, so that isolation is enforced at the OS level.
9. As a developer, I want agent stdout/stderr captured to a log file per task, so that I can debug failures by reading the log.
10. As a developer, I want the orchestrator to pass check-work commands (test, type_check, build) in the agent prompt, so that agents know exactly what commands to run for verification.
11. As a developer, I want agents to retry internally up to 3 times within a single session before reporting failure, so that they can try different approaches with memory of what didn't work.
12. As a developer, I want the orchestrator to run check-work (test + type_check + build) as a trust gate after each agent finishes, so that agent claims of success are verified deterministically.
13. As a developer, I want the trust gate to treat the task as failed immediately if checks don't pass (even if agent claimed success), so that broken code doesn't proceed to the next stage.
14. As a developer, I want AGENT_RESULT parsed from agent output with fallback to exit code, so that a missing result line doesn't halt the wave unnecessarily.
15. As a developer, I want GitHub labels updated as tasks transition stages (ready-for-agent → implementing → reviewing → merging → closed), so that I can see status at a glance.
16. As a developer, I want failed tasks labelled (impl-failed, review-failed, merge-failed) and the wave halted, so that I can intervene before dependent tasks start.
17. As a developer, I want the merge phase to be sequential (one branch at a time into feature branch), so that test failures are attributable to a specific branch.
18. As a developer, I want Kiro (running the skill) to resolve merge conflicts directly — read conflict markers, fix, run check-work, retry up to 3 times — so that simple integration issues are handled without a separate merger agent.
19. As a developer, I want failed merges reverted and labelled merge-failed, so that the feature branch stays in a passing state.
20. As a developer, I want worktrees cleaned up on success and preserved on failure, so that I can inspect failed task output directly.
21. As a developer, I want to choose "auto" (all waves without pausing) or "wave-by-wave" (confirm between waves), so that I can supervise closely or run hands-off.
22. As a developer, I want the skill to push the feature branch and raise a PR when all tasks are complete, so that the feature is ready for final review.
23. As a developer, I want the skill to resume from label state on re-run — `implementing` reruns implementer fresh (nuke worktree), `reviewing` reruns reviewer in existing worktree, `merging` reattempts merge, `*-failed` skipped until human relabels — so that I can fix issues and continue without restarting.
24. As a developer, I want the last 20 lines of the agent log surfaced on "no result" failures, so that I can immediately see what happened without opening the file.
25. As a developer, I want the design.md path extracted from the PRD issue body (same convention as wave_runner), so that the implementer has architectural context.
26. As a developer, I want the reviewer to independently review the diff, assess test quality/coverage, find code issues, and run checks itself — not just fix pre-computed findings — so that it acts as a proper second pair of eyes.

## Implementation Decisions

### Skill Structure

The `orchestrate` skill is a SKILL.md recipe that Kiro follows step by step. No Python code, no async, no package. Kiro uses `shell` to run git commands and spawn agent subprocesses, `read`/`write` for conflict resolution, and `grep` for parsing logs.

### Environment Isolation

Each task gets a git worktree: `../<repo-name>-waves/<prd-number>/<issue-number>/`. Worktrees fork from the feature branch. `setup_command` runs per worktree (e.g. `pnpm install`, `python -m venv .venv && pip install -r requirements.txt`). No dep_dirs copying.

### Agent Invocation

```
kiro-cli chat --no-interactive --agent <name> "<prompt>" > <log-path> 2>&1
```

OS-level cwd set to the worktree. Parallel invocations capped by `concurrency` from project-config.md.

### Agent Prompts

Implementer prompt includes:
- Issue number
- Design path
- Check commands (test, type_check, build) from config
- "3 attempts to get checks passing" instruction

Reviewer prompt includes:
- Issue number
- Base ref (feature branch) for diffing
- Check commands from config
- "Independently review, run checks, fix issues, 3 attempts" instruction

Working directory NOT included in prompts (enforced at OS level).

### Check-Work Trust Gate

After each agent finishes, orchestrator runs in the worktree:
1. `type_check_command` (if configured)
2. `test_command`
3. `build_command` (if configured)

Fail fast on first non-zero exit. If any fail and agent claimed SUCCESS, mark task as failed.

### AGENT_RESULT Contract

Agents output `AGENT_RESULT: SUCCESS` or `AGENT_RESULT: FAILED — <reason>`.

Parsing logic:
- AGENT_RESULT present → use it
- Missing + exit 0 → treat as success, log warning
- Missing + exit non-zero → treat as failure

### Merge Phase

Sequential, in main repo directory:
1. `git merge task/<number> --no-edit`
2. If conflict → Kiro reads markers, resolves, stages, commits
3. Run check-work in main repo
4. If fails → Kiro retries fix (up to 3 attempts)
5. If still fails → `git merge --abort` or revert, label merge-failed, halt

### Label Lifecycle

```
ready-for-agent → implementing → reviewing → merging → closed
                       ↓              ↓           ↓
                  impl-failed    review-failed  merge-failed
```

### Resume Semantics

| Label | Action |
|-------|--------|
| `ready-for-agent` + blockers closed | Full pipeline |
| `implementing` | Nuke worktree, re-run implementer |
| `reviewing` | Re-run reviewer in existing worktree |
| `merging` | Re-attempt merge |
| `*-failed` | Skip (human must relabel) |

### Feature Branch & PR

- Branch: `feature/<prd-number>-<slug>` (from main)
- Task branches: `task/<issue-number>` (from feature branch)
- Worktrees: `../<repo-name>-waves/<prd-number>/<issue-number>/`
- On completion: push feature branch, `gh pr create`

### Project Config (simplified)

```yaml
---
inclusion: always
repo: owner/repo-name
test_command: pnpm test
type_check_command: tsc --noEmit
build_command: pnpm build
setup_command: pnpm install
concurrency: 3
---
```

Removed: `dep_dirs` (no longer needed).

### Agent Config Changes

**implementer.json** — widen `allowedCommands` to cover standard node/python commands:
- Add `tsc.*`, `mypy.*`, `pnpm build.*`, `npm run.*`

**reviewer.json** — same widening plus prompt rewrite:
- Remove reliance on pre-computed results
- Add independent review, own check-work, 3-attempt internal retry

**merger agent** — no longer needed (Kiro handles merges directly). Kept in repo as reference for future programmatic version.

### Debugging

- Each agent invocation logs to `../<repo>-waves/<prd>/<issue>/agent.log`
- On failure: skill reports issue number, failure type (timeout/exit code/no result/FAILED reason), log path
- On "no result": surfaces last 20 lines of log
- Wave halts on any task failure

## Testing Decisions

No automated tests for this deliverable — it's a skill recipe (markdown) and agent prompts. Validation is manual: run the skill on a real PRD and confirm the process works end-to-end.

The existing wave_runner tests remain as reference for when the programmatic version is built later.

## Out of Scope

- Deleting wave_runner (kept as reference for future programmatic approach)
- Fallow dead-code analysis (dropped for v1)
- Docker container isolation
- Rich TUI / progress bars
- Token cost tracking
- Auto-retry of `*-failed` tasks without human intervention
- CI/CD integration
- dep_dirs / base worktree optimization
- Pre-review hooks (replaced by agent-internal retries + trust gate)

## Further Notes

- The `setup` skill template should be updated to remove `dep_dirs` from the config format.
- pnpm is preferred for Node projects (content-addressable store makes parallel worktree installs fast).
- The skill is intended as a process prototype. Once validated, the process will be re-implemented programmatically (building on wave_runner learnings).
- Existing implementer TDD skill resource stays — agents still follow TDD internally.
