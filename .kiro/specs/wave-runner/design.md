<!-- GitHub: #12 https://github.com/tedyeates/kiro-skills/issues/12 -->

# Wave Runner

## Problem Statement

Implementing a full PRD (10-50 tasks across multiple waves) is currently manual — you run each agent one at a time, manage branches, merge, and track progress yourself. This is tedious and doesn't scale. The existing implementer and reviewer agents work well individually but have no coordination layer.

## Solution

A pure Python orchestration script (`wave-runner`) that autonomously implements an entire PRD by coordinating kiro-cli agents wave by wave. It fetches unblocked tasks from GitHub, runs implementer→reviewer pipelines in bounded parallelism, merges results sequentially into a feature branch, and loops until all tasks are done or a failure halts the run. On completion it raises a single PR.

## User Stories

1. As a developer, I want to run `wave-runner --prd 42` and have it implement all tasks for that PRD, so that I can step away and return to a completed feature branch.
2. As a developer, I want the orchestrator to derive the repo from my current git remote, so that I don't have to pass redundant config.
3. As a developer, I want task branches to fork from the feature branch, so that each implementer has access to code from previously merged waves.
4. As a developer, I want bounded parallelism with a configurable concurrency limit, so that I can balance speed against rate limits and machine resources.
5. As a developer, I want each task to flow through implementer→reviewer in parallel within a wave, so that slow tasks don't block faster ones from progressing.
6. As a developer, I want the merger phase to be sequential (one branch at a time into feature branch), so that test failures are attributable to a specific branch.
7. As a developer, I want the orchestrator to attempt merge conflict resolution and test fixes via an LLM merger agent (up to 3 attempts), so that simple integration issues are handled automatically.
8. As a developer, I want failed merges to be reverted so the feature branch stays in a passing state.
9. As a developer, I want issue labels to reflect pipeline stage (implementing, reviewing, merging, *-failed), so that I can see status at a glance and the orchestrator can resume from the correct point.
10. As a developer, I want the orchestrator to halt after a wave if any task failed, so that I can intervene before dependent tasks start on a broken base.
11. As a developer, I want to fix a failed task and relabel it to the appropriate stage, then re-run the script to continue from where it left off.
12. As a developer, I want a report posted to the PRD issue after each wave showing what merged, what failed (with branch names), and what's outstanding.
13. As a developer, I want a local log file with full failure details so I can act immediately without visiting GitHub.
14. As a developer, I want a single PR raised from feature branch to main when all tasks are complete, with a body listing all closed sub-issues.
15. As a developer, I want a `--dry-run` flag that shows the wave plan without executing anything.
16. As a developer, I want the design.md path extracted from the PRD issue body, so that the implementer knows where to find architectural context.
17. As a developer, I want worktrees created in a predictable sibling directory (`<repo>-waves/<prd>/<issue>/`), so I can find and inspect them.
18. As a developer, I want worktrees cleaned up after successful merge but preserved on failure for inspection.
19. As a developer, I want the agents to output a standardised `AGENT_RESULT: SUCCESS/FAILED` line so the orchestrator can reliably detect outcomes.
20. As a developer, I want deterministic steps (branching, merging, testing, pushing, labelling) handled by Python — not by LLM agents — so that costs are minimised and reliability is maximised.
21. As a developer, I want to install wave-runner via pip with a console entry point so it's available on PATH from any project.

## Implementation Decisions

### Modules

| Module | Responsibility | Interface |
|--------|---------------|-----------|
| **cli** | Argument parsing, entry point | `main()` → parses args, calls orchestrator |
| **config** | Parse project-config.md YAML frontmatter | `load_config(repo_root) → Config` |
| **github** | All gh CLI interactions | `fetch_prd()`, `fetch_sub_issues()`, `update_label()`, `post_comment()`, `close_issue()`, `create_pr()` |
| **planner** | Compute next wave from task graph | `compute_wave(tasks) → List[Task]` |
| **executor** | Coordinate implement→review→merge pipeline | `run_wave(wave, config) → WaveResult` |
| **git** | All git operations (worktrees, merge, revert) | `create_feature_branch()`, `create_worktree()`, `remove_worktree()`, `merge_branch()`, `revert_merge()`, `push_branch()` |
| **agent** | Invoke kiro-cli subprocess, parse result | `invoke_agent(name, prompt, cwd) → AgentResult` |
| **reporter** | Terminal output, GitHub comments, log file | `terminal_summary()`, `github_comment()`, `append_log()` |

### Module Contracts

- **cli → config**: CLI reads config once at startup, passes `Config` to executor.
- **cli → github**: Fetches PRD issue and sub-issues, passes task list to planner.
- **planner → executor**: Planner returns ordered task list for current wave. Executor runs them.
- **executor → agent**: Executor invokes agents via `invoke_agent()`. Receives `AgentResult` (success/failure + stdout).
- **executor → git**: Executor delegates all git operations to git module. Never calls git directly.
- **executor → github**: After each task stage, executor updates labels. After merge, closes issue.
- **executor → reporter**: After wave completes, executor passes `WaveResult` to reporter.

### Architecture

- **No LLM in orchestrator** — All coordination is deterministic Python.
- **Subprocess invocation** — Agents run as `kiro-cli chat --no-interactive --trust-all-tools --agent <name> "<prompt>"` in the worktree directory.
- **Agent prompt must include base-ref** — The executor passes `Base ref: <feature-branch>` in the reviewer (and implementer if needed) prompt so agents can diff against the correct branch point, not a hardcoded default.
- **Git worktrees for isolation** — Each task gets its own worktree forked from the feature branch.
- **GitHub as source of truth** — Issue state (open/closed) and labels determine what to run.
- **Single feature branch per PRD** — `feature/<prd-number>-<slug>`, accumulates all merged task branches.
- **Bounded parallelism** — `asyncio` with semaphore for concurrency control (default 3).
- **Pipeline with merge gate** — Implementer→reviewer flows per-task in parallel; merger waits for all to reach `merging` state.

### Label Lifecycle

```
ready-for-agent → implementing → reviewing → merging → closed
                       ↓              ↓           ↓
                  impl-failed    review-failed  merge-failed
```

### Resume Behaviour

On re-run, the orchestrator reads issue labels:
- `implementing` → run reviewer (skip implementer)
- `reviewing` → run merger (skip implementer + reviewer)
- `merging` → attempt merge (skip implementer + reviewer)
- `*-failed` → skip (human must relabel after fixing)
- `ready-for-agent` + all blockers closed → run full pipeline

### Merger Agent (LLM fallback)

Invoked only when:
1. `git merge` produces conflicts, OR
2. Tests fail after merge

Receives: issue context, design.md, conflict/test output.
Contract: fix surgically, commit, output `AGENT_RESULT`. 3 attempts max.
On failure: orchestrator reverts merge, labels `merge-failed`.

### Config Format (project-config.md)

```yaml
---
inclusion: always
repo: tedyeates/kiro-skills
test_command: pnpm test
build_command: pnpm build
concurrency: 3
---
```

### Agent Output Contract

All agents output as final line:
```
AGENT_RESULT: SUCCESS
```
or
```
AGENT_RESULT: FAILED — <reason>
```

### PRD Issue Body Convention

The PRD issue body includes a `Design:` line for the orchestrator to extract:
```
Design: .kiro/specs/wave-runner/design.md
```

## Testing Decisions

- Test through public module interfaces, not internal functions.
- **config**: parse real and malformed frontmatter.
- **planner**: given a task graph, assert correct wave computation (topological batching).
- **git**: mock subprocess calls, verify correct git commands issued.
- **agent**: mock kiro-cli subprocess, verify stdout parsing for SUCCESS/FAILED.
- **executor**: integration test with all dependencies mocked — verify correct label transitions, halt on failure, resume from label state.
- **reporter**: assert output format matches expected templates.
- **github**: mock gh CLI output, verify correct API calls constructed.
- Use `pytest` with `unittest.mock` for subprocess mocking.

## Out of Scope

- Docker container isolation (future upgrade path — worktrees for v1).
- Rich TUI / progress bars (plain terminal output).
- Token cost tracking or timing metrics.
- Auto-retry of failed tasks without human intervention.
- Multi-repo orchestration.
- CI/CD integration (runs locally only).
- Modifying the `to-issues` or `to-prd` skills.

## Further Notes

- The `deploy` skill should be updated to run `pip install -e` for the wave-runner package.
- The `setup` skill should be updated to prompt for `test_command` and `build_command` in project-config.md frontmatter.
- Existing implementer and reviewer agent prompts need updating: remove git topology steps, add `AGENT_RESULT` output.
- New merger agent config and prompt needed.
- `to-prd` skill should be updated to include `Design:` path in PRD issue body.
