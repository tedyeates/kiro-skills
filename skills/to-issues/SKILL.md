---
name: to-issues
description: Break a plan or PRD into independently-implementable tasks using vertical slices with dependency ordering. Use when user wants to break down work, create tasks from a design, split into issues, or says "break this into tasks".
---
# To Issues

Break a plan into independently-implementable vertical slices. Publishes to GitHub Issues or local markdown depending on project config.

Reads issue tracker config from `.kiro/steering/project-config.md`. Run `setup` first if missing.

## Process

### 1. Gather context

Work from whatever is already in the conversation — design.md or discussion. If the user passes a file path, read it.

### 2. Explore the codebase (if needed)

Understand current state. Use the project's domain vocabulary. Respect ADRs.

### 3. Draft vertical slices

Break the plan into **tracer bullet** tasks. Each task is a thin vertical slice cutting through ALL layers end-to-end — not a horizontal slice of one layer.

Rules:
- Each slice delivers a narrow but COMPLETE path (schema, API, UI, tests) that is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- Slices are either **AFK** (can be implemented without human input) or **HITL** (human interaction needed)
- Prefer AFK over HITL where possible

### 4. Identify dependencies

For each task, determine which other tasks must complete first (`Blocked by`). Tasks with no dependencies can run in parallel immediately.

### 5. Quiz the user

Present the breakdown as a numbered list. For each task show:
- **Title**: short descriptive name
- **Type**: AFK / HITL
- **Blocked by**: which tasks must complete first (if any)
- **Acceptance criteria**: how to verify it's done

Ask:
- Does the granularity feel right?
- Are the dependency relationships correct?
- Should any tasks be merged or split?
- Are the correct tasks marked AFK vs HITL?

Iterate until approved.

### 6. Output

#### If GitHub (per project-config.md)

Publish issues in dependency order (blockers first) so IDs are available for API calls. Use [GITHUB-API.md](./GITHUB-API.md) for exact API patterns.

For each task:
1. Create the issue with `gh issue create` using `--json id,number,url`
2. Link as sub-issue of the parent PRD issue
3. Add `blocked_by` dependencies for each blocker
4. Apply `ready-for-agent` label (AFK) or `ready-for-human` label (HITL)

Issue body template:

```markdown
## What to build

Concise description of the vertical slice. Describe end-to-end behavior, not layer-by-layer.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

#### If local (per project-config.md)

Write to `.kiro/specs/{title}/tasks.md`:

```markdown
## Task N: [Title]

**Type**: AFK | HITL
**Blocked by**: Task X, Task Y | None

### What to build

Concise description of the vertical slice. Describe end-to-end behavior, not layer-by-layer.

### Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

#### Both modes: generate dependency diagram

Write a mermaid diagram to `.kiro/specs/{title}/dependency-graph.md`:

```markdown
# Dependency Graph

```mermaid
graph LR
  subgraph "Parallel batch 1"
    T1[#num Title]
    T2[#num Title]
  end
  subgraph "Parallel batch 2"
    T3[#num Title]
  end
  T1 --> T3
  T2 --> T3
`` `
```

Compute batches: tasks with no unresolved blockers = batch 1, tasks whose blockers are all in earlier batches = batch 2, etc.
