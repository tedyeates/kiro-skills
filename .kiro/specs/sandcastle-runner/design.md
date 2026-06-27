<!-- GitHub: #37 https://github.com/tedyeates/kiro-skills/issues/37 -->

# Kiro Sandcastle Runner

## Problem Statement

The current wave_runner (Python) is flaky and fails regularly. The primary failure modes are brittle `AGENT_RESULT` parsing from agent stdout and unnecessary complexity from async parallelism. A simpler, more reliable orchestration approach is needed that uses deterministic verification instead of parsing agent self-reporting.

## Solution

A TypeScript script using `@ai-hero/sandcastle` that runs Kiro agents sequentially inside a Docker container. The orchestrator fetches unblocked tasks from GitHub, creates a sandbox, runs implementer → checks → reviewer → final checks for each task, and creates a PR when all tasks pass. Success is determined solely by deterministic test/type-check results, not agent output parsing.

## User Stories

1. As a developer, I want to run `npx tsx .sandcastle/main.ts --prd 42` from WSL so that all unblocked tasks for a PRD are implemented automatically
2. As a developer, I want the runner to fetch task details from GitHub so that the source of truth is always the issue tracker
3. As a developer, I want tasks processed sequentially so that each task builds on the previous task's work without merge conflicts
4. As a developer, I want deterministic checks (test + type-check) to gate success so that I never get false positives from agent self-reporting
5. As a developer, I want the reviewer to always run (even if implementer checks pass) so that code quality is enforced
6. As a developer, I want the runner to halt immediately on failure so that broken code doesn't cascade to subsequent tasks
7. As a developer, I want a PR created automatically when all tasks pass so that I can review the complete feature branch
8. As a developer, I want agent stdout logged to files so that I can debug failures without noisy terminal output
9. As a developer, I want concise status lines in the terminal so that I can monitor progress at a glance
10. As a developer, I want a shared Docker image (`kiro-runner`) that works for both Python and pnpm projects so that I build once and reuse across repos
11. As a developer, I want the orchestrator to pass issue content to agents via prompt so that no GitHub credentials are needed inside the container
12. As a developer, I want agents to commit their own work so that commit messages have meaningful context
13. As a developer, I want a configurable timeout per agent invocation so that hung agents are killed without blocking forever
14. As a developer, I want a one-time WSL setup process documented so that I can get the environment running from scratch
15. As a developer, I want the design.md path extracted from the PRD body so that agents receive architectural context automatically
16. As a developer, I want project setup (dep install) to run once at container start so that tasks don't waste time reinstalling
17. As a developer, I want the runner image to include kiro-cli, git, Node+pnpm, and Python3+pip so that it supports my full stack

## Implementation Decisions

### Modules

**1. Shared Docker Image (`kiro-runner`)**
- Fat image: `node:22-bookworm` base + Python3+venv+pip, pnpm (corepack), git, kiro-cli
- Git identity baked in: `kiro-agent` / `kiro-agent@noreply`
- `ENTRYPOINT ["sleep", "infinity"]` — sandcastle `exec`s into it
- Built once, referenced by name in all projects
- Lives in skills repo as a template/reference

**2. Per-project `main.ts`** (`.sandcastle/main.ts`)
- TypeScript script, run via `npx tsx`
- Imports `@ai-hero/sandcastle` for container lifecycle
- Defines project-specific commands (setup, test, type-check)
- Accepts `--prd <number>` CLI arg
- Skills repo provides a scaffolding skill/template

**3. Orchestrator Logic** (within `main.ts`)

Flow:
```
1. Parse --prd arg
2. Fetch PRD issue body → extract design.md path
3. Fetch sub-issues → filter to open + no open blockers
4. Create/checkout feature branch
5. Create sandbox (docker, mount repo + ~/.kiro/)
6. Run setup command (onSandboxReady hook)
7. For each task:
   a. Fetch issue body (gh on host)
   b. sandbox.exec(kiro-cli implementer with issue+design context)
   c. sandbox.exec(test + type-check)
   d. If fail → sandbox.exec(kiro-cli reviewer with failure context)
      If pass → sandbox.exec(kiro-cli reviewer for quality review)
   e. sandbox.exec(test + type-check) — final gate
   f. If fail → halt, exit 1
   g. If pass → log success, continue
8. Push feature branch
9. Create PR via gh (on host)
```

**4. Bind Mounts**

| Host (WSL) | Container | Purpose |
|---|---|---|
| `~/projects/<repo>` | `/home/agent/workspace` | The repo (read-write) |
| `~/.kiro/` | `/home/agent/.kiro/` | Auth, agents, skills, steering |

No `~/.config/gh/` mount — orchestrator handles all GitHub ops on host.

**5. Agent Prompt Changes**

Implementer and reviewer prompts updated:
- Remove "run `gh issue view`" step — context provided inline
- Remove `gh issue view.*` from `allowedCommands`
- Add instruction to install new deps if added

**6. Branch Strategy**

- `branchStrategy: { type: "branch", branch: "feature/<prd>-<slug>" }`
- Agents commit directly to feature branch
- No task branches, no merge phase
- Eliminates merger agent entirely

**7. Task Sourcing**

```bash
gh api repos/<repo>/issues/<prd>/sub_issues
```
Filter: `state === "open"` AND all blockers are closed (state === "closed").
Process in issue number order (lowest first).

### Configuration Shape (per-project `main.ts`)

```typescript
const config = {
  repo: "tedyeates/stockmanager",
  setup: "cd stockmanagement_bg && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ../stockmanagement-fe && pnpm install",
  test: "cd stockmanagement_bg && .venv/bin/pytest && cd ../stockmanagement-fe && pnpm test",
  typeCheck: "cd stockmanagement_bg && .venv/bin/pyright && cd ../stockmanagement-fe && pnpm tsc --noEmit",
  timeoutSeconds: 900, // 15min per agent, tweakable
};
```

## Testing Decisions

- The orchestrator is a script, not a library — testing is primarily integration-level
- Verify via dry-run mode (`--dry-run` flag that shows task plan without executing)
- Agent behavior tested implicitly through the deterministic checks
- No unit tests for the `main.ts` initially — it's glue code. If it grows complex, extract and test

## Out of Scope

- Parallel task execution (explicitly sequential only)
- Custom sandcastle `AgentProvider` for kiro-cli (using `sandbox.exec()` directly)
- Dependency graph / wave computation (just filter unblocked)
- GitHub label state machine / resume from labels (start fresh each run)
- Retry implementer on failure (reviewer handles fixes)
- MCP servers inside the container
- Notifications or webhooks on completion

## Further Notes

### WSL Setup (one-time prerequisite)

1. `wsl --install` (Windows) → Ubuntu 24.04
2. In WSL:
   ```bash
   # System deps
   sudo apt update && sudo apt install -y git curl jq

   # Docker CE
   sudo apt install -y docker.io
   sudo usermod -aG docker $USER
   # (re-login for group to take effect)

   # Node.js 22 + pnpm
   curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
   sudo apt install -y nodejs
   corepack enable && corepack prepare pnpm@latest --activate

   # Python 3 (usually pre-installed on Ubuntu 24.04)
   sudo apt install -y python3 python3-venv python3-pip

   # GitHub CLI
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt update && sudo apt install -y gh
   gh auth login

   # Kiro CLI
   curl -fsSL https://cli.kiro.dev/install | bash
   kiro-cli login --use-device-flow

   # Clone repos
   mkdir ~/projects && cd ~/projects
   git clone git@github.com:tedyeates/stockmanager.git
   ```

3. Build shared image:
   ```bash
   docker build -t kiro-runner -f ~/projects/skills/sandcastle/Dockerfile .
   ```

### Dockerfile (reference — lives in skills repo)

```dockerfile
FROM node:22-bookworm

RUN apt-get update && apt-get install -y \
    git curl jq python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# pnpm via corepack
RUN corepack enable && corepack prepare pnpm@latest --activate

# Git identity for agent commits
RUN git config --global user.name "kiro-agent" \
    && git config --global user.email "kiro-agent@noreply"

ARG AGENT_UID=1000
ARG AGENT_GID=1000
RUN groupmod -o -g $AGENT_GID node \
    && usermod -o -u $AGENT_UID -g $AGENT_GID -d /home/agent -m -l agent node

USER ${AGENT_UID}:${AGENT_GID}

# Kiro CLI
RUN curl -fsSL https://cli.kiro.dev/install | bash
ENV PATH="/home/agent/.local/bin:$PATH"

WORKDIR /home/agent
ENTRYPOINT ["sleep", "infinity"]
```
