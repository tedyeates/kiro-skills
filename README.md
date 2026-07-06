# Kiro Skills Collection

Augmentation skills for Kiro CLI, adapted from [mattpocock/skills](https://github.com/mattpocock/skills). These skills enhance Kiro's requirements → design → tasks → implement flow with battle-tested engineering practices.

Made a stripped down version for my workflow, stealing what I found most useful, check out above link for full Claude Code version.

## Prerequisites

1. Install fallow globally:

```powershell
npm install -g fallow
```

2. Install fallow skills (select **kiro-cli agent** when prompted):

```powershell
npx skills add fallow-rs/fallow-skills
```

## Quick Start

1. Clone this repo and open it in Kiro CLI:

```powershell
cd D:\Projects\skills
kiro-cli chat
```

2. Run the deploy skill from local repo:

```
run deploy skill
```

3. Reload to pick up the new skills/agents/steering:

```
/quit
kiro-cli
```

That's it — all skills, agents, and steering files are now available globally with slash commands.

## Process Flow

The complete workflow from idea to shipped code:

```
┌─────────────────────────────────────────────────────────────────┐
│  0. setup              → One-time repo config (run once)        │
├─────────────────────────────────────────────────────────────────┤
│  1. grill-with-docs    → Stress-test plan, build shared lang   │
│     └─ (or grill-me for quick sessions without doc updates)    │
│  2. prototype          → Throwaway code to answer design Qs    │
│  3. to-prd             → Synthesize into PRD                   │
│  4. to-issues          → Break into parallel-ready tasks       │
│  5. tdd                → Red-green-refactor per task           │
│  6. diagnose           → Fix bugs that arise                   │
│  7. improve-arch       → Refactor after each wave              │
├─────────────────────────────────────────────────────────────────┤
│  Supporting (any time):                                         │
│  • zoom-out            → Understand unfamiliar code            │
│  • handoff             → Pass work to another session          │
│  • write-a-skill       → Create new skills                    │
│  • convert-claude-skill → Port Claude Code skills             │
└─────────────────────────────────────────────────────────────────┘
```

See [docs/process-flow.md](docs/process-flow.md) for the detailed step-by-step guide.

## Skills Overview

### Engineering (daily code work)

| Skill | Kiro Phase | What It Does |
|-------|-----------|-------------|
| [setup](skills/setup/SKILL.md) | Pre-requisite | One-time repo config: issue tracker, triage labels, domain docs layout |
| [grill-with-docs](skills/grill-with-docs/SKILL.md) | Requirements | Relentless interview that updates CONTEXT.md glossary and creates ADRs inline |
| [grill-me](skills/grill-me/SKILL.md) | Requirements | Lightweight interview without doc updates |
| [prototype](skills/prototype/SKILL.md) | Design | Throwaway code to answer design questions (terminal app or UI variations) |
| [to-prd](skills/to-prd/SKILL.md) | Design | Synthesize conversation into PRD with modules, user stories, testing decisions |
| [to-issues](skills/to-issues/SKILL.md) | Tasks | Break PRD into vertical-slice tasks with wave grouping and interface boundaries |
| [tdd](skills/tdd/SKILL.md) | Implementation | Red-green-refactor loop, one test at a time, never horizontal |
| [diagnose](skills/diagnose/SKILL.md) | Implementation | 6-phase structured debugging with feedback loop construction |
| [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md) | Post-wave | Find shallow modules, propose deepening opportunities |
| [zoom-out](skills/zoom-out/SKILL.md) | Any | Explain code at higher abstraction level using domain vocabulary |

### Productivity (workflow tools)

| Skill | What It Does |
|-------|-------------|
| [handoff](skills/handoff/SKILL.md) | Compact conversation into a handoff doc for another session |
| [write-a-skill](skills/write-a-skill/SKILL.md) | Create new skills with proper structure and progressive disclosure |

### Meta

| Skill | What It Does |
|-------|-------------|
| [convert-claude-skill](skills/convert-claude-skill/SKILL.md) | Convert any Claude Code skill into its Kiro equivalent |

## Agents

| Agent | Purpose |
|-------|---------|
| [skill-converter](agents/skill-converter.json) | Convert Claude skills to Kiro format |
| [implementer](agents/implementer.json) | Constrained agent for headless task execution via subagent pipelines |
| [reviewer](agents/reviewer.json) | Quality gate: type check, test, dead-code analysis, auto-fix |

### Running the Implementer

The implementer agent accepts a GitHub issue number, fetches the ticket details, reads the relevant `design.md` for context, and implements the task using TDD.

**Prerequisites:**
- `gh` CLI authenticated (`gh auth status`)
- `.kiro/steering/project-config.md` with repo configured (created by `setup` skill)
- A `design.md` in `.kiro/specs/<feature>/design.md`

**Usage:**

```powershell
# Run a single task by issue number
kiro-cli chat --no-interactive --trust-all-tools --agent implementer "Implement issue #12 for feature reviewer-agent"
```

The agent will:
1. Read `project-config.md` for the repo name
2. Run `gh issue view <number>` to fetch task details
3. Read `.kiro/specs/*/design.md` for architectural context
4. Implement via TDD (red → green → refactor)

### Running the Reviewer

The reviewer agent is a quality gate that runs after the implementer. It checks type safety, runs tests, performs dead-code analysis (JS/TS only via fallow), and auto-fixes mechanical issues.

**Prerequisites:**
- Same as implementer (gh CLI, project-config.md)
- `fallow` CLI installed globally (`npm install -g fallow`) — only needed for JS/TS projects

**Usage:**

```powershell
# Run reviewer on a branch after implementer finishes
kiro-cli chat --no-interactive --trust-all-tools --agent reviewer "Review issue #12"
```

**What it does:**
1. Reads `corrections.md` to avoid known mistakes
2. Runs type checking, tests, and `fallow dead-code` (if JS/TS)
3. Fixes mechanical issues (type errors, test failures, dead code) — up to 3 attempts
4. On success: commits fixes and reports AGENT_RESULT
5. On failure: reports what passed/failed and what was attempted

**Fix boundary — reviewer will fix:**
- Type errors
- Test failures
- Dead code (unused exports, files, dependencies)

**Combining with implementer in a pipeline:**

```powershell
# Implementer → Reviewer pipeline via subagent
kiro-cli chat --no-interactive --trust-all-tools "Implement issue #12 for feature X, then review it" \
  --agent implementer --then --agent reviewer
```

Or use the subagent `stages` approach in your own agent to wire them together with a `loop_to` for the review cycle.

## Steering Files

These skills work alongside Kiro steering files. Copy to your global config or per-repo:

```powershell
Copy-Item .\steering\* ~\.kiro\steering\
```

| File | Purpose |
|------|---------|
| `.kiro/steering/project-config.md` | Per-repo config created by `setup` skill |
| `.kiro/steering/caveman.md` | Ultra-compressed communication mode (~75% token savings) |
| `.kiro/steering/corrections.md` | Rules for auto-logging mistakes; references `.kiro/corrections.md` for the actual log |

### Corrections system

`corrections.md` uses a two-file design:

- **`.kiro/steering/corrections.md`** — The rules (when to log, format, subagent delegation). Always loaded as steering context.
- **`.kiro/corrections.md`** — The actual log file (lives outside steering). Referenced via `#[[file:.kiro/corrections.md]]` directive. Auto-created on first error entry.

The log file lives outside `steering/` so it can grow without bloating the steering context. Subagents receive both files so they read existing corrections and append new ones.

## Sandcastle Runner

The sandcastle runner autonomously implements a whole PRD's worth of GitHub issues. It runs Kiro agents **sequentially inside a Docker container** and gates success on **deterministic test + type-check results** rather than parsing agent self-reporting. It replaces the older `wave_runner` (Python) with a simpler, more reliable TypeScript orchestrator built on [`@ai-hero/sandcastle`](https://www.npmjs.com/package/@ai-hero/sandcastle).

### How it works

For a given PRD issue number, the runner:

1. Fetches the PRD issue body and extracts the `Design: .kiro/specs/<feature>/design.md` path
2. Fetches sub-issues, keeps only open ones labeled `ready-for-agent` (configurable) with all blockers closed
3. Creates/checks out a `feature/prd-<number>` branch
4. Spins up a `kiro-runner` Docker sandbox (mounts `~/.kiro/` for auth/agents/skills) and runs the one-time setup command
5. For each unblocked task, in issue-number order:
   - Runs the **implementer** agent (issue + design context passed inline via prompt — no GitHub creds in the container)
   - Runs test + type-check
   - Runs the **reviewer** agent (always, for quality or to fix failures)
   - Runs test + type-check again as the **final gate**
   - Halts immediately (`exit 1`) if the final gate fails
6. Pushes the branch and opens a PR via `gh` on the host when all tasks pass

Agent stdout/stderr is written to `.sandcastle/logs/<issue>-implementer.log` and `<issue>-reviewer.log`; the terminal only shows concise status lines.

### Files

| File | Purpose |
|------|---------|
| `sandcastle/Dockerfile` | Shared `kiro-runner` image: `node:22-bookworm` + Python3/venv/pip, pnpm (corepack), git, kiro-cli. Built once, reused across repos. |
| `sandcastle/main.template.ts` | Per-project orchestrator template. Copied to `.sandcastle/main.ts` in a target repo and customised. |
| `skills/sandcastle-init/SKILL.md` | Skill that scaffolds `.sandcastle/main.ts` into a repo (`sandcastle init`). |
| `docs/wsl-setup.md` | One-time WSL/Docker/toolchain setup. |

### One-time setup

Full instructions in [docs/wsl-setup.md](docs/wsl-setup.md). Summary:

1. Install WSL (Ubuntu 24.04), plus `git`, `curl`, `jq`, Docker, Node 22 + pnpm, Python 3, `gh` (authenticated), and `kiro-cli` (logged in).
2. Clone your repos under `~/projects/`.
3. Build the shared image:

   ```bash
   docker build -t kiro-runner -f ~/projects/kiro-skills/sandcastle/Dockerfile .
   ```

4. Verify:

   ```bash
   docker run --rm --entrypoint bash kiro-runner -c "node --version && pnpm --version && python3 --version && git --version"
   ```

### Initialise a repo

From inside your target repo in Kiro CLI, run the scaffolding skill:

```
sandcastle init
```

This copies `sandcastle/main.template.ts` → `.sandcastle/main.ts`, installs `tsx` and `@ai-hero/sandcastle` as dev deps, adds `.sandcastle/logs/` to `.gitignore`, and fills in the config block from `.kiro/steering/project-config.md`.

Then edit the config block in `.sandcastle/main.ts` to match your project:

```typescript
const config = {
  repo: "tedyeates/stockmanager",
  setup:
    "cd stockmanagement_bg && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ../stockmanagement-fe && pnpm install",
  test: "cd stockmanagement_bg && .venv/bin/pytest && cd ../stockmanagement-fe && pnpm test",
  typeCheck:
    "cd stockmanagement_bg && .venv/bin/pyright && cd ../stockmanagement-fe && pnpm tsc --noEmit",
  timeoutSeconds: 900, // per-agent timeout
  agentLabel: "ready-for-agent", // only tasks with this label are implemented
};
```

### Run

```bash
# Preview the task plan without executing
npx tsx .sandcastle/main.ts --prd <number> --dry-run

# Execute: implement all unblocked tasks, then open a PR
npx tsx .sandcastle/main.ts --prd <number>
```

**Requirements for the PRD issue:** its body must contain a `Design: .kiro/specs/<feature>/design.md` line so agents receive architectural context, and sub-issues should be linked with blocker relationships so the runner can order them correctly.

**Notes:**
- Tasks run sequentially on a single feature branch — no task branches, no merge step. This avoids conflicts and eliminates a separate merger agent.
- Success is decided only by deterministic checks; the runner halts on the first task that fails its final gate, so broken code never cascades.
- Parallel execution, resume-from-labels, and retry-on-failure are intentionally out of scope (see `.kiro/specs/sandcastle-runner/design.md`).

**Task selection (`agentLabel`):**
- Only open sub-issues carrying the `agentLabel` (default `ready-for-agent`) are considered. `ready-for-human` and unlabeled tasks are ignored.
- If a wave has no labeled tasks at all, the runner exits cleanly (`exit 0`, "Nothing to do") without creating a branch or container.
- If labeled tasks exist but all are blocked by open dependencies, the runner halts (`exit 1`) before spinning up the sandbox.
- A `ready-for-agent` task blocked by a `ready-for-human` task stays blocked until the human task is done — the runner won't build on top of unfinished human work. It gets picked up on a later run once the blocker is closed.

## Documentation

- [Process Flow](docs/process-flow.md) — Step-by-step guide through the complete workflow
- [WSL Setup](docs/wsl-setup.md) — One-time environment setup for the sandcastle runner
- [Analysis Report](docs/claude-skills-analysis.md) — Full breakdown of the Claude skills codebase and Kiro mapping
- [Implementation Plan](implementation-plan.md) — How this repo was built
- [Mapping Reference](skills/convert-claude-skill/MAPPING.md) — Decision tree for Claude → Kiro conversion
