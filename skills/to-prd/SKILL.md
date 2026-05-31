---
name: to-prd
description: Synthesize the current conversation into a PRD with module identification, deep-module thinking, and user stories. Use when user wants to create a PRD, write up the design, or says "create the PRD".
---
# To PRD

Synthesize conversation context into a structured PRD. Do NOT interview the user — just synthesize what you already know from the conversation and codebase.

Reads issue tracker config from `.kiro/steering/project-config.md`. Run `setup` first if missing.

## Process

### 1. Explore the codebase

Understand the current state. If the project has a domain glossary (CONTEXT.md or steering files), use that vocabulary throughout. Respect any ADRs in the area being touched.

### 2. Identify modules

Sketch out the major modules to build or modify. Actively look for opportunities to extract **deep modules** — modules that encapsulate a lot of functionality behind a simple, testable interface which rarely changes.

Present the module list to the user:
- Which modules are new vs modified
- What the public interface of each looks like (conceptually)
- Which modules should have tests

Get user confirmation before proceeding.

### 3. Write the PRD

Write to `.kiro/specs/{title}/design.md`. Use the template below.

---

## Problem Statement

The problem from the user's perspective.

## Solution

The solution from the user's perspective.

## User Stories

A LONG, numbered list of user stories:

1. As a [actor], I want [capability], so that [benefit]

Cover ALL aspects of the feature. Be exhaustive.

## Implementation Decisions

- Modules to build/modify and their module boundary contracts (what module A promises to module B)
- Technical clarifications
- Architectural decisions
- Schema changes
- API contracts
- Key interactions between modules

Do NOT include specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose (state machine, schema, type shape), inline it and note it came from a prototype.

## Testing Decisions

- What makes a good test: only test external behavior through public interfaces, not implementation details
- Which modules will be tested
- Prior art for tests in the codebase (similar test patterns already in use)

## Out of Scope

Things explicitly NOT included in this PRD.

## Further Notes

Any additional context, constraints, or open questions.

---

### 4. Publish to GitHub (if configured)

If `project-config.md` specifies `Type: github`, publish a **summarised** version as a GitHub Issue:

```bash
gh issue create --title "PRD: {title}" --body "{summary}" --json id,number,url
```

The summary contains only:

```markdown
## Problem
{1-2 sentences}

## Solution
{1-2 sentences}

## Key Decisions
- {bullet}
- {bullet}
```

No label on the parent issue. Record the returned `id`, `number`, and `url` — `to-issues` will use these to link sub-issues.

Store the issue reference at the top of `design.md`:

```markdown
<!-- GitHub: #number url -->
```
