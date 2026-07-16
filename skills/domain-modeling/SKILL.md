---
name: domain-modeling
description: Build and sharpen a project's domain model — challenge terms against the glossary, stress-test with edge-case scenarios, and update CONTEXT.md and ADRs inline. Use when terms are fuzzy, overloaded, or conflicting with existing language. Model-invoked by grill-with-docs, wayfinder, and other skills.
---
# Domain Modeling

Actively build and sharpen the project's domain model as you work. This is the *active* discipline — challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise.

(Merely *reading* `CONTEXT.md` for vocabulary is not this skill — that's a one-line habit any skill can do. This skill is for when you're **changing** the model, not just consuming it.)

## File structure

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives.

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user (or another skill) uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately.

> "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When vague or overloaded terms appear, propose a precise canonical term.

> "You're saying 'check' — do you mean the department production check (QC inspection) or the dispatch verification? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force precision about boundaries between concepts.

> "If a job is partially dispatched and then the quotation is revised, what happens to the already-dispatched boards?"

### Cross-reference with code

When the user states how something works, verify the code agrees. If you find a contradiction, surface it:

> "Your code has `status: 'completed'` but CONTEXT.md says a job is 'dispatched' when finished — which is the canonical term?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch — capture as they happen.

Format (from grill-with-docs/CONTEXT-FORMAT.md):
```markdown
**Term**: One or two sentence definition of what it IS.
_Avoid_: synonym1, synonym2
```

`CONTEXT.md` should be totally devoid of implementation details. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when ALL THREE are true:
1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — genuine alternatives existed and you picked one for specific reasons

If any of the three is missing, skip the ADR.

## Invoked by

This skill is model-invoked — it can be triggered automatically by:
- **grill-with-docs** — drives domain-modeling throughout every interview
- **wayfinder** — during decision-ticket resolution when terms need pinning
- **to-spec** — when writing specs that need domain vocabulary
- **Any skill** — whenever ambiguous domain terms are encountered mid-work

It can also be invoked directly by the user when they want to sharpen terminology.
