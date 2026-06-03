# Kiro Skills Collection

Augmentation skills for Kiro CLI, adapted from [mattpocock/skills](https://github.com/mattpocock/skills). These skills enhance Kiro's requirements → design → tasks → implement flow with battle-tested engineering practices.

Made a stripped down version for my workflow, stealing what I found most useful, check out above link for full Claude Code version.

## Quick Start

### Option A: Reference from agent config

Add to any agent's `resources` field:

```json
{
  "resources": [
    "skill://path/to/skills/**/SKILL.md"
  ]
}
```

### Option B: Copy to global skills

```powershell
Copy-Item -Recurse .\skills\* ~\.kiro\skills\
```

Then any agent with `"skill://~/.kiro/skills/**/SKILL.md"` in resources will have access.

### Option C: Use the provided agents

```powershell
Copy-Item .\agents\*.json ~\.kiro\agents\
```

Then switch with `/agent skill-converter` or `/agent implementer`.

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


The agent will:
1. Read `project-config.md` for the repo name
2. Run `gh issue view <number>` to fetch task details
3. Read `.kiro/specs/*/design.md` for architectural context
4. Implement via TDD (red → green → refactor)

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

## Documentation

- [Process Flow](docs/process-flow.md) — Step-by-step guide through the complete workflow
- [Analysis Report](docs/claude-skills-analysis.md) — Full breakdown of the Claude skills codebase and Kiro mapping
- [Implementation Plan](implementation-plan.md) — How this repo was built
- [Mapping Reference](skills/convert-claude-skill/MAPPING.md) — Decision tree for Claude → Kiro conversion
