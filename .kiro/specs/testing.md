# Testing

Project-wide testing strategy and conventions. Accumulates across features.

## Strategy

- The Sandcastle Runner and its modes are **glue code**. Primary verification is:
  1. `--dry-run` — asserts the planned task/ticket list without executing agents or Docker.
  2. Real runs gated on **deterministic checks** (`test` + `typeCheck`) — the sole
     pass/fail authority; agent self-reporting is never trusted.
- Extract and unit-test **pure functions** that encode error-prone logic; leave
  orchestration/IO glue to integration-level verification.

## Framework & Runner

- Orchestrator scripts run via `npx tsx`. Per-project `test`/`typeCheck` commands are
  configured in `.kiro/steering/project-config.md` and reused by the runner.

## Fix Mode (sandcastle)

- **Unit**: `selectEligibleFixes(issues)` — pure function; test via synthetic issue
  arrays covering label presence/absence, `bug`/`enhancement` gating, dependency edges,
  state, and ascending-number ordering. Assert only the returned subset (external behaviour).
- **Integration**: `--fix --dry-run` prints the correct eligible plan and creates no sandbox.
- Reuses the existing `runChecks` verification path unchanged.

## File Index

| Path | Summary |
|------|---------|
