---
name: handoff
description: Compact the current conversation into a handoff document so another agent session can continue the work. Use when user says "handoff", "save context for later", "write a handoff", or wants to pass work to another session.
---
# Handoff

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

## Process

### 1. Summarise the conversation

Capture:
- **Goal**: What the user is trying to accomplish
- **Decisions made**: Key choices and their reasoning
- **Current state**: What's been done, what's in progress
- **Next steps**: What the next session should focus on
- **Blockers**: Anything unresolved that needs human input

### 2. Reference, don't duplicate

Do NOT duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, CONTEXT.md). Reference them by path instead.

### 3. Suggest skills

Include a "Suggested skills" section recommending which skills the next session should invoke based on where the work left off.

### 4. Redact sensitive information

Strip API keys, passwords, tokens, or PII. Reference them by key name only.

### 5. Save the document

Save to the project's docs directory (e.g., `docs/handoff-<date>.md`) or the OS temp directory if the user prefers not to commit it.

## Template

```markdown
# Handoff — {Brief title}

**Date**: {ISO date}
**Goal**: {One-line summary}

## Context

{2-3 paragraphs of what was discussed and decided}

## Artifacts

- {path/to/prd.md} — PRD for feature X
- {path/to/CONTEXT.md} — Updated glossary
- {docs/adr/0003-chose-postgres.md} — Database decision

## Current State

- [x] Completed step
- [ ] In progress step
- [ ] Not started step

## Next Steps

1. {What the next session should do first}
2. {Then this}
3. {Then this}

## Suggested Skills

- `grill-with-docs` — if requirements need further refinement
- `to-prd` — if ready to write the design doc
- `tdd` — if implementation is next

## Open Questions

- {Anything unresolved that needs human input}
```

## If the user passed arguments

Treat them as a description of what the next session will focus on and tailor the document accordingly — emphasise the relevant context and de-emphasise the rest.
