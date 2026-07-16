---
name: grill-with-docs
description: Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates CONTEXT.md and ADRs inline as decisions crystallise. Enhances the requirements phase. Use when user wants to stress-test a plan against their project's language and documented decisions, says "grill with docs", or wants domain-aware requirements gathering.
---
# Grill With Docs

Relentless interview that also builds and maintains the project's shared language (CONTEXT.md) and architectural decision records (ADRs).

## Process

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

For each question:
1. Provide your recommended answer
2. Wait for my response before continuing

Ask the questions **one at a time**.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Domain awareness

Throughout the interview, actively invoke `/domain-modeling` to maintain the project's shared language. This means:

- Challenge terms against the existing `CONTEXT.md` glossary
- Sharpen fuzzy or overloaded language into precise canonical terms
- Stress-test domain relationships with concrete edge-case scenarios
- Cross-reference claims with what the code actually does
- Update `CONTEXT.md` inline as terms are resolved (use [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md))
- Offer ADRs sparingly — only when hard-to-reverse, surprising, and a real trade-off (use [ADR-FORMAT.md](./ADR-FORMAT.md))

See the `/domain-modeling` skill for the full discipline. The key rule: `CONTEXT.md` is a glossary and nothing else — no implementation details.