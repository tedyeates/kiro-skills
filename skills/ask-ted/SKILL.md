---
name: ask-ted
description: Ask which skill or flow fits your situation. A router over the skills in this repo. Use when unsure which skill to use, or say "ask ted", "which skill", "what should I do next".
---
# Ask Ted

You don't remember every skill, so ask. A **flow** is a path through the skills. Most paths run along one **main flow**, and two **on-ramps** merge onto it. Everything else is standalone.

## The main flow: idea → ship

The route most work travels. You have an idea and want it built.

1. **`/grill-with-docs`** — sharpen the idea by interview. Start here when you **have a codebase**: it's stateful, retaining what it learns in `CONTEXT.md` and ADRs. (No codebase? Use `/grill-me` — stateless, saves nothing locally.)

2. **Branch — can you settle every question in conversation?**
   If a question needs a runnable answer (state, business logic, a UI you have to see), detour through a prototype:
   - **`/handoff`** out to a fresh session
   - **`/prototype`** to answer the question with throwaway code
   - **`/handoff`** back what you learned

3. **Branch — is this a multi-session build?**
   - **Yes** → **`/to-spec`** (synthesize into a spec), then **`/to-tickets`** to split into tracer-bullet tickets with blocking edges. Then **`/tdd`** per ticket, clearing context between each one. Run **`/code-review`** before committing.
   - **No** → **`/tdd`** right here, then **`/code-review`** before committing.

### Autonomous execution (sandcastle)

For multi-ticket builds where you want hands-off execution:
- **`/sandcastle-init`** — scaffold the runner in a repo
- **`sandcastle run`** — `npx tsx .sandcastle/main.ts --prd <number>` runs all unblocked tickets through implementer + reviewer agents sequentially in Docker

The sandcastle runner gates success on deterministic test + type-check results, not agent self-reporting.

### Context hygiene

Keep steps 1–3 in **one unbroken context window** — don't compact until after `/to-tickets` — so grilling, spec, and tickets build on the same thinking. Each `/tdd` invocation starts fresh, working from the ticket. If a session approaches the smart zone limit before `/to-tickets`, `/handoff` and continue in a fresh thread.

## On-ramps

Starting situations that generate work, then merge onto the main flow.

- **Something's broken** → **`/diagnose`**. For hard bugs: reproduce → minimise → hypothesise → instrument → fix → regression-test. Refuses to theorise until it has a tight feedback loop.

- **A huge, foggy effort** → **`/wayfinder`**. When the way from here to the destination isn't visible yet. Charts a shared map of decision tickets on the issue tracker, resolves one at a time until the route is clear. Hands off to `/to-spec` when the map clears — it doesn't build.

- **Need to understand something first** → **`/research`**. Spins up a background agent to read primary sources (official docs, APIs, specs) and produces a cited markdown file. Keeps working while it reads. Feed the result into `/grill-with-docs`.

## Codebase health

Not feature work — upkeep.

- **`/improve-codebase-architecture`** — surfaces deepening opportunities. Picking one generates an idea you can take into the main flow at `/grill-with-docs`.

## Vocabulary underneath

Model-invoked references that run *beneath* the other skills — the single source of truth for their vocabulary. Reach for them directly when the words, not the process, are the problem.

- **`/domain-modeling`** — sharpen the project's domain language: challenge fuzzy terms, resolve overloaded words, update `CONTEXT.md` and ADRs inline. The active discipline `/grill-with-docs` drives.

## Crossing sessions

- **`/handoff`** — compacts conversation into a markdown file for another session. Forks context to a new window.
- **Compact** (built-in `/compact`) — stays in the same conversation, summarizes earlier turns. Use at intentional breaks between phases. Don't compact mid-phase.

## Standalone

Off the main flow entirely.

- **`/grill-me`** — same interview as `/grill-with-docs` but stateless, no codebase needed.
- **`/prototype`** — throwaway code to answer one design question.
- **`/research`** — background reading agent, produces cited markdown.
- **`/teach`** — learn a concept over multiple sessions with structured lessons and exercises.
- **`/zoom-out`** — explain code at higher abstraction level using domain vocabulary.
- **`/write-a-skill`** — create new skills with proper structure.

## Precondition

**`/setup`** — run before your first engineering flow to configure issue tracker, triage labels, and domain doc layout.
