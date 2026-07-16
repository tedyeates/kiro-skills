---
name: to-spec
description: Synthesize the current conversation into a spec with seam identification, module design, and user stories. Publishes to the issue tracker. Use when user wants to create a spec/PRD, write up the design, or says "create the spec", "to spec", "write the PRD".
---
# To Spec

Synthesize conversation context into a structured spec. Do NOT interview the user — just synthesize what you already know from the conversation and codebase.

Reads issue tracker config from `.kiro/steering/project-config.md`. Run `setup` first if missing.

## Process

### 1. Explore the codebase

Understand the current state. If the project has a domain glossary (CONTEXT.md or steering files), use that vocabulary throughout. Respect any ADRs in the area being touched.

### 2. Identify testing seams

Before writing the spec, sketch out the **seams** at which you're going to test the feature. A seam is a place where you can alter behaviour without editing the code at that place — typically an interface boundary where tests can grab hold.

Rules for seam selection:
- **Prefer existing seams** over creating new ones (less refactoring)
- **Use the highest seam possible** — test through the public interface, not internal functions
- If new seams are needed, propose them at the **highest point** you can
- **Fewer seams across the codebase = better** — the ideal number is one per module
- One adapter means a hypothetical seam; two adapters means a real one — don't introduce a seam unless something actually varies across it

Present the proposed seams to the user and get confirmation before proceeding.

### 3. Identify modules

Sketch out the major modules to build or modify. Actively look for opportunities to extract **deep modules** — a lot of functionality behind a simple, testable interface which rarely changes.

Present the module list to the user:
- Which modules are new vs modified
- What the public interface of each looks like (conceptually)
- Where the testing seams land on each module

Get user confirmation before proceeding.

### 4. Write the spec

Write to `.kiro/specs/{title}/design.md`. Use the template below.

### 5. Publish to GitHub (if configured)

If `project-config.md` specifies `Type: github`, publish a **summarised** version as a GitHub Issue:

```bash
gh issue create --title "Spec: {title}" --body "{summary}" --json id,number,url
```

The summary contains only:

```markdown
## Problem
{1-2 sentences}

## Solution
{1-2 sentences}

## Testing Seams
- {seam 1}
- {seam 2}

## Key Decisions
- {bullet}
- {bullet}
```

Apply `ready-for-agent` label. Record the returned `id`, `number`, and `url` — `to-tickets` will use these to link sub-issues.

Store the issue reference at the top of `design.md`:

```markdown
<!-- GitHub: #number url -->
```

---

## Spec Template

## Problem Statement

The problem from the user's perspective.

## Solution

The solution from the user's perspective.

## User Stories

A LONG, numbered list of user stories:

1. As a [actor], I want [capability], so that [benefit]

Cover ALL aspects of the feature. Be exhaustive.

## Testing Seams

The seams at which this feature will be tested, with rationale:

| Seam | Existing/New | Modules it covers | How tests use it |
|------|-------------|-------------------|-----------------|
| {interface name} | Existing | {modules} | {test strategy} |

## Implementation Decisions

- Modules to build/modify and their interface contracts
- Technical clarifications
- Architectural decisions
- Schema changes
- API contracts
- Key interactions between modules

Do NOT include specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose (state machine, schema, type shape), inline it and note it came from a prototype.

## Testing Decisions

- What makes a good test: only test external behavior through the identified seams, not implementation details
- Which modules will be tested through which seams
- Prior art for tests in the codebase (similar test patterns already in use)

## Out of Scope

Things explicitly NOT included in this spec.

## Further Notes

Any additional context, constraints, or open questions.
