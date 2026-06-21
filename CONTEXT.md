# Wave Runner

Domain vocabulary for the autonomous task orchestration system.

## Language

### Orchestration

**Wave Runner**: Pure Python script that coordinates LLM agents to implement an entire PRD autonomously, wave by wave.
_Avoid_: orchestrator script, pipeline runner

**Wave**: A batch of unblocked tasks that can be executed in parallel. Derived from the dependency graph — tasks whose blockers are all closed.
_Avoid_: batch, sprint, round

**Orchestrator**: The deterministic Python coordination logic within the wave runner. No LLM — purely subprocess management, git operations, and GitHub queries.
_Avoid_: controller, scheduler, agent

### Agents

**Implementer**: LLM agent that reads an issue, reads design.md, writes code via TDD, and commits. Does not branch, push, or interact with GitHub.
_Avoid_: coder, builder, developer

**Reviewer**: LLM agent that performs adversarial code review and fixes mechanical issues (type errors, test failures, dead code). Commits fixes. Does not push or create PRs.
_Avoid_: checker, validator

**Merger**: LLM agent invoked only on failure (merge conflict or test failure after integration). Resolves the issue surgically within 3 attempts. Does not refactor or change approach.
_Avoid_: fixer, integrator, resolver

### Git Topology

**Feature Branch**: Long-lived branch (`feature/<prd-number>-<slug>`) that accumulates all merged task branches across waves. One per PRD.
_Avoid_: integration branch, develop branch

**Task Branch**: Short-lived branch forked from the feature branch for a single issue. Lives in a worktree. Merged back into feature branch by the orchestrator.
_Avoid_: issue branch, work branch

**Worktree**: A `git worktree` checkout giving a task branch its own isolated directory. Created by the orchestrator, cleaned on success, left for inspection on failure.
_Avoid_: clone, container, workspace

### Lifecycle

**Issue Label**: GitHub label indicating current pipeline stage. Orchestrator reads labels on resume to enter the pipeline at the correct point.
_Avoid_: status, state, tag

**Halt**: The wave runner stops after the current wave completes because one or more tasks failed. No new wave starts. Human intervenes, fixes, relabels, re-runs.
_Avoid_: stop, pause, abort
