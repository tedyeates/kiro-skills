# Kiro Skills

Domain vocabulary for the autonomous task orchestration system.

## Language

### Orchestration

**Sandcastle Runner**: TypeScript script using `@ai-hero/sandcastle` that coordinates Kiro agents inside a Docker container to implement a PRD sequentially, task by task.
_Avoid_: wave runner, orchestrator script, pipeline runner

**Orchestrator**: The deterministic TypeScript coordination logic. No LLM — container lifecycle, `sandbox.exec()` calls, GitHub queries, and verification.
_Avoid_: controller, scheduler, agent

**Task Loop**: Sequential processing of unblocked tasks. One task completes fully before the next begins. No parallelism.
_Avoid_: wave, batch, pipeline

### Agents

**Implementer**: Kiro agent that receives task context in its prompt, reads design.md, writes code via TDD, and commits. Does not push, branch, or interact with GitHub directly.
_Avoid_: coder, builder, developer

**Reviewer**: Kiro agent that performs adversarial code review and fixes mechanical issues (type errors, test failures, dead code). Always runs after implementer. Commits fixes. Does not push or create PRs.
_Avoid_: checker, validator

### Verification

**Deterministic Check**: `sandbox.exec()` of test and type-check commands after each agent run. The sole authority on pass/fail — agent self-reporting is ignored.
_Avoid_: trust gate, validation step

**Halt**: The runner stops immediately when deterministic checks fail after the reviewer. No further tasks are processed. Human investigates.
_Avoid_: stop, pause, abort

### Git Topology

**Feature Branch**: Long-lived branch (`feature/<prd-number>-<slug>`) that accumulates direct commits from all tasks. One per PRD. Agents commit directly to it.
_Avoid_: integration branch, develop branch, task branch

### Fix Mode

**Fix Mode**: A mode of the Sandcastle Runner (`--fix`) that processes standalone, ready, dependency-free tickets across a whole repo — one branch and PR per ticket — instead of a PRD's sub-issues. Implementer-only, skip-and-continue.
_Avoid_: bug loop, small-task runner, fix runner

**Eligible Fix**: A ticket the Fix Mode will process: `open` AND `ready-for-agent` AND (`bug` OR `enhancement`) AND zero blocking dependencies. Computed by the pure `selectEligibleFixes` function.
_Avoid_: ready ticket, candidate

**In-place Branch Switching**: Cutting each ticket's branch from the launch commit (`git switch -c` from `baseSha`) inside a single, reused worktree — so dependencies install once and persist across tickets. Never checks out the base branch (it is checked out in the main repo).
_Avoid_: per-task worktree, branch reset

### Infrastructure

**Runner Image**: Shared Docker image (`kiro-runner`) containing Node+pnpm, Python3+pip, git, kiro-cli. Built once, reused across projects.
_Avoid_: sandbox image, dev container

**Sandbox**: The running Docker container created from the runner image. Repo bind-mounted in. Agents execute inside via `sandbox.exec()`.
_Avoid_: environment, workspace, worktree
