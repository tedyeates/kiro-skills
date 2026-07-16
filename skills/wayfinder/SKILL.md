---
name: wayfinder
description: Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets on the issue tracker. Resolve them one at a time until the way to the destination is clear. Use when user says "wayfinder", has a foggy/huge effort, or needs to chart a multi-session plan.
---
# Wayfinder

A loose idea has arrived — too big for one agent session, wrapped in fog: the way from here to the **destination** isn't visible yet.

Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the issue tracker, then works its **decision tickets** one at a time until the route is clear.

Reads issue tracker config from `.kiro/steering/project-config.md`. Run `setup` first if missing.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear — nothing left to decide before someone builds. The pull to just do the work is the signal you've reached the edge of the map and it's time to hand off to `/to-spec`.

## The Map

The map is a single issue on the tracker, labelled `wayfinder:map`. Its tickets are child issues. The map is an **index**, not a store — it lists decisions made and points at tickets holding detail; a decision lives in exactly one place (its ticket).

### Map body

```markdown
## Destination

{What this map is finding its way to}

## Notes

{Constraints, context, effort-specific overrides}

## Decisions so far

- [{ticket title}](link) — {one-line gist}

## Not yet specified

{Fog: suspected questions not yet sharp enough to ticket}

## Out of scope

{Work consciously ruled out of this effort}
```

### Tickets

Each ticket is a child issue of the map. Its body is the question, sized to one context window:

```markdown
## Question

{The decision to resolve}
```

Each carries a `wayfinder:` label — one of: `research`, `prototype`, `grilling`, `task`.

## Ticket Types

- **Research** (AFK): Reading docs, APIs, local resources. Resolved by a `/research` subagent. Use when knowledge outside current context is required.
- **Prototype** (HITL): Make a cheap artifact to react to via `/prototype`. Use when "how should it look/behave" is the question.
- **Grilling** (HITL): Conversation via `/grill-me` and `/domain-modeling`, one question at a time. The default.
- **Task** (AFK or HITL): Manual work that must happen before a decision can be made. The one type that *does* rather than decides — earns its place by unblocking a decision.

## Fog of war

The map is deliberately incomplete. Beyond live tickets lies fog — decisions you can tell are coming but can't pin down because they hang on open questions.

**Fog or ticket?** Can you state the question precisely now?
- **Yes** → ticket (even if blocked and can't act on it yet)
- **No** → stays in "Not yet specified"

Resolving a ticket clears fog ahead of it, graduating what's now specifiable into fresh tickets.

## Invocation

### Chart the map (user has a loose idea)

1. **Name the destination.** Run `/grill-me` and `/domain-modeling` to pin down what this map finds its way to.
2. **Map the frontier.** Grill breadth-first: fan out across the whole space, surfacing open decisions and first steps. **If no fog surfaces** — the way is already clear — stop and tell the user they don't need a map.
3. **Create the map** as a tracker issue (`wayfinder:map` label).
4. **Create tickets** as child issues, then wire blocking edges in a second pass.
5. **Fire research subagents** for each `research` ticket.
6. Stop — charting is one session's work.

### Work through the map (user passes a map URL/number)

1. Load the map (low-res view).
2. Choose a ticket: user-named one, or first frontier ticket (open, unblocked, unclaimed).
3. **Claim it** — assign before any work.
4. Resolve it — invoke the skills the ticket type names. Use `/domain-modeling` when terms are fuzzy.
5. Record the resolution: post answer as a comment, close the issue, append to map's "Decisions so far".
6. Graduate fog: add newly-specifiable tickets, clear graduated patches from "Not yet specified".

**Never resolve more than one ticket per session** (except research tickets, which run as subagents).

## When the map clears

When no tickets remain and "Not yet specified" is empty, the way is clear. **Hand off** — don't build:
- Merge onto the main flow at `/to-spec`, which collapses the map's linked decisions into a buildable plan
- Then `/to-tickets` and `/tdd` as usual

Go straight to `/tdd` only when the effort turned out genuinely small (one-session scope).

## Out of scope handling

When a ticket turns out to sit past the destination — mis-scoped or exposed by a resolution:
- **Close it**
- Add one line to "Out of scope" with the gist + why
- It stays out of "Decisions so far" (scope boundary ≠ step on the route)
