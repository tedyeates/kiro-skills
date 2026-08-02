# Security

Project-wide security decisions and constraints. Accumulates across features.

## Auth & Credentials

- **Headless agent auth** uses `KIRO_API_KEY`, passed into the Docker sandbox as an env
  var (never baked into the image). Absence of the key fails fast at startup.
- **GitHub credentials never enter the container.** All `gh` operations (issue queries,
  PR creation, issue close, label edits) run on the host. Agents inside the sandbox
  receive issue content inline via their prompt and have no GitHub access.
- The sandbox mounts `~/.kiro` (read-only) for auth/agents/skills and `~/.aws` for AWS
  access; the repo/worktree is bind-mounted for the agent to work on.

## Fix Mode (sandcastle)

- Fix mode inherits the above: `gh` on host, `KIRO_API_KEY` for the container.
- Refuses to start on a dirty working tree, preventing uncommitted host changes from
  leaking into agent branches/PRs.
- Failed tickets are pushed as **draft** PRs — visible for inspection, not mergeable by
  accident.

## Sensitive Endpoints & Data Flows

_None specific to tooling features so far._

## File Index

| Path | Summary |
|------|---------|
