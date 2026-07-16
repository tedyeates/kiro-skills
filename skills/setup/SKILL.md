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
   # Triage labels
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

**Section D — Commands**

> The sandcastle runner and reviewer agent need to know how to test, type-check, and build your project.

Ask for each command. Infer defaults from project files:
- `package.json` with `"test"` script → `pnpm test` or `npm test`
- `pyproject.toml` with pytest config → `pytest`
- `tsconfig.json` present → `tsc --noEmit`
- `mypy.ini` or `[tool.mypy]` in `pyproject.toml` → `mypy .`
- `Cargo.toml` → `cargo test` / `cargo check`

Present inferred defaults and let user confirm or override:

| Command | Purpose | Example |
|---------|---------|---------|
| `test_command` | Run tests | `pytest`, `pnpm test`, `cargo test` |
| `type_check_command` | Static type checking | `mypy .`, `tsc --noEmit`, `cargo check` |
| `build_command` | Build step (optional) | `pnpm build`, `cargo build` |
| `setup_command` | Per-worktree setup (optional) | `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt` |

The `setup_command` runs once per worktree before the implementer agent starts. Typical use: creating a venv and installing deps so test/type-check commands work in isolated worktrees.

Infer defaults:
- `requirements.txt` present → `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt`
- `pyproject.toml` with `[project.dependencies]` → `python -m venv .venv && .venv/Scripts/pip install -e .`
- `package.json` present → `npm ci` or `pnpm install`
- No dependency file → omit

If `setup_command` creates a venv, the user **must** prefix `test_command` and `type_check_command` with the venv binary path. Subprocesses don't inherit venv activation — each command runs in a fresh process, so only explicit paths work:

- Windows: `.venv/Scripts/pytest`, `.venv/Scripts/mypy .`
- Linux/macOS: `.venv/bin/pytest`, `.venv/bin/mypy .`

Example (Windows, Python project):
```yaml
setup_command: "python -m venv .venv && .venv/Scripts/pip install -r requirements.txt"
test_command: ".venv/Scripts/pytest"
type_check_command: ".venv/Scripts/mypy ."
```

All commands are written to the YAML frontmatter of `project-config.md`.

### 3. Write configuration

Create `.kiro/steering/project-config.md`:

```markdown
---
inclusion: always
repo: {owner/repo-name — if github or gitlab}
test_command: {test command, e.g. "pytest", "pnpm test"}
type_check_command: {type check command or omit if none, e.g. "mypy .", "tsc --noEmit"}
build_command: {build command or omit if none, e.g. "pnpm build"}
setup_command: {worktree setup or omit if none, e.g. "python -m venv .venv && .venv/Scripts/pip install -r requirements.txt"}
concurrency: 3
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
