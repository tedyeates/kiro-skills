---
name: setup
description: One-time per-repo configuration that other skills depend on — issue tracker type, triage labels, and domain docs layout. Use when starting a new project, setting up skills for the first time, or when other skills report missing configuration.
---
# Setup

Scaffold the per-repo configuration that the engineering skills assume. Run once per repo before using `grill-with-docs`, `to-issues`, `to-prd`, `tdd`, `diagnose`, or `improve-codebase-architecture`.

## Process

### 0. Prerequisites

Check if `fallow` is on PATH:

```bash
fallow --version
```

- If found, skip installation.
- If not found, run:

```bash
npm install -g fallow
```

Verify installation succeeded with `fallow --version`.

### 1. Explore

Read the current repo to understand its starting state:
- `git remote -v` — is this a GitHub/GitLab repo?
- `CONTEXT.md` and `CONTEXT-MAP.md` at the repo root
- `docs/adr/` and any `src/*/docs/adr/` directories
- `.kiro/steering/` — existing steering files
- `.kiro/skills/` — existing skills
- `package.json`, `Makefile`, etc. — project type

### 2. Present findings and ask

Summarise what's present and what's missing. Walk the user through three decisions **one at a time** — present a section, get the answer, then move to the next.

**Section A — Issue tracker**

> Where do issues live for this repo? Skills like `to-issues` need to know whether to call `gh`, `glab`, write local markdown, or something else.

Options:
- **GitHub** — uses `gh` CLI
- **GitLab** — uses `glab` CLI
- **Local markdown** — issues as files under `.kiro/specs/<title>/tasks.md`
- **Other** — describe the workflow in one paragraph

Default: infer from `git remote` (GitHub remote → GitHub, GitLab remote → GitLab).

**If GitHub selected:**
1. Run `gh auth status` — verify CLI is authenticated
2. Run `gh repo view --json nameWithOwner` — confirm repo access and capture `owner/repo`
3. Create labels if they don't exist:
   ```bash
   gh label create "ready-for-agent" --description "Fully specified, AFK-ready" --color 0E8A16 --force
   gh label create "ready-for-human" --description "Needs human implementation" --color FBCA04 --force
   ```
   (The `--force` flag updates existing labels without error)
4. Verify write access — if label creation succeeded, write access is confirmed

**Section B — Triage labels** (skip if not using triage skill)

> The triage roles and their label strings in your tracker.

Defaults:
- `ready-for-agent`
- `ready-for-human`

Ask if the user wants to override any.

**Section C — Domain docs layout**

> Where does the project's shared language live?

Options:
- **Single-context** — one `CONTEXT.md` + `docs/adr/` at the repo root (most repos)
- **Multi-context** — `CONTEXT-MAP.md` at root pointing to per-context files (monorepos)
- **None yet** — will be created lazily by `grill-with-docs` when first term is resolved

### 3. Write configuration

Create `.kiro/steering/project-config.md`:

```markdown
---
inclusion: always
---
# Project Configuration

## Issue Tracker

Type: {github | gitlab | local | other}
Repo: {owner/repo-name — if github or gitlab}
CLI: {gh | glab — if applicable}
Write access: verified
{If other: one-paragraph description of workflow}

## Triage Labels

| Role | Label |
|------|-------|
| ready-for-agent | {label} |
| ready-for-human | {label} |

## Domain Docs

Layout: {single-context | multi-context}
Glossary: {path to CONTEXT.md or "not yet created"}
ADRs: {path to docs/adr/ or "not yet created"}
```

### 4. Create missing structure (if user agrees)

Offer to create:
- `CONTEXT.md` — empty template from grill-with-docs/CONTEXT-FORMAT.md
- `docs/adr/` — empty directory
- `.kiro/corrections.md`

Only create what the user confirms.

### 5. Done

Tell the user:
- What was configured
- Which skills will now read from `project-config.md`
- They can edit `.kiro/steering/project-config.md` directly later
