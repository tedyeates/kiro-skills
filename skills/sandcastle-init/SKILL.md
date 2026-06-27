---
name: sandcastle-init
description: Initialize the sandcastle runner in a new repo — copies template, installs deps, customises config. Use when user says "sandcastle init", "setup sandcastle", "init runner", or wants to add the sandcastle orchestrator to a project.
---
# Sandcastle Init

Set up the sandcastle orchestrator in the current repo so it can run agent pipelines via Docker.

## Prerequisites

- WSL environment configured (see `docs/wsl-setup.md` in skills repo)
- `kiro-runner` Docker image built
- Repo has `.kiro/steering/project-config.md` (run `setup` skill first if not)

## Process

### 1. Check prerequisites

```bash
docker image inspect kiro-runner --format "{{.Id}}" 2>/dev/null
```

If image missing, tell user to build it:
```
docker build -t kiro-runner -f ~/projects/kiro-skills/sandcastle/Dockerfile .
```

Read `.kiro/steering/project-config.md` — extract `repo`, `test_command`, `type_check_command`, `setup_command` from frontmatter. If missing, ask user for each.

### 2. Install dependencies

Check if `package.json` exists with `"packageManager"` containing `npm` or a `package-lock.json` exists:
- If npm project → `npm install --save-dev tsx @ai-hero/sandcastle`
- Otherwise → `pnpm add -D tsx @ai-hero/sandcastle` (initializes pnpm if needed)

### 3. Copy and customise template

1. Create `.sandcastle/` directory
2. Copy `~/projects/kiro-skills/sandcastle/main.template.ts` → `.sandcastle/main.ts`
3. Replace the config block with values from project-config:

```typescript
const config = {
  repo: "<repo from project-config>",
  setup: "<setup_command from project-config>",
  test: "<test_command from project-config>",
  typeCheck: "<type_check_command from project-config>",
  timeoutSeconds: 900,
};
```

If `setup_command` is absent, use `"echo 'no setup'"`.
If `type_check_command` is absent, use `"echo 'no type check'"`.

### 4. Add to .gitignore

Append to `.gitignore` if not already present:

```
.sandcastle/logs/
```

### 5. Confirm

Tell user:
- `.sandcastle/main.ts` ready
- Run `npx tsx .sandcastle/main.ts --prd <number> --dry-run` to verify
- PRD issues need a `Design: .kiro/specs/<feature>/design.md` line in the body for agents to get context
