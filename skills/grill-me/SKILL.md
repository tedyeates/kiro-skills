---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Enhances the requirements phase. Use when user wants to stress-test a plan, get grilled on their design, says "grill me", or is starting a new feature.
---
# Grill Me

Relentless interview that surfaces hidden assumptions, resolves ambiguities, and builds shared understanding before any design or implementation begins.

## Process

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

For each question:
1. Provide your recommended answer
2. Explain why you recommend it
3. Wait for my response before continuing

Ask the questions **one at a time**.

If a question can be answered by exploring the codebase, explore the codebase instead of asking me.

## What to probe

- **Scope boundaries** — what's in, what's explicitly out
- **User-facing behavior** — what does the user see/do at each step
- **Edge cases** — what happens when things go wrong
- **Dependencies** — what must exist before this can work
- **Interfaces** — how does this connect to existing systems
- **Naming** — are we using consistent, precise terminology
- **Priorities** — if we can't do everything, what's cut first

## When to stop

Stop when:
- Every branch of the decision tree has a clear answer
- No ambiguous terms remain
- We both agree on scope, behavior, and constraints
- The plan could be handed to an implementer with no further questions

## Output

After the grilling session, summarize:
- Decisions made (numbered list)
- Terms defined (if any new vocabulary emerged)
- Out-of-scope items identified
- Open questions that need external input (if any)
