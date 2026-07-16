# Skill Linkages

How skills connect, invoke, and hand off to each other.

```mermaid
graph TD
    %% Router
    ask-ted["ask-ted<br/>(router)"]

    %% Main flow
    grill-with-docs["grill-with-docs"]
    grill-me["grill-me"]
    prototype["prototype"]
    to-spec["to-spec"]
    to-tickets["to-tickets"]
    tdd["tdd"]
    code-review["code-review"]

    %% On-ramps
    diagnose["diagnose"]
    wayfinder["wayfinder"]
    research["research"]

    %% Vocabulary layers (model-invoked)
    domain-modeling["domain-modeling<br/>(model-invoked)"]

    %% Codebase health
    improve-arch["improve-codebase-<br/>architecture"]

    %% Productivity
    handoff["handoff"]
    teach["teach"]
    zoom-out["zoom-out"]

    %% Agents (outside sandcastle box)
    implementer-agent["implementer<br/>(agent)"]
    reviewer-agent["reviewer<br/>(agent)"]

    %% Meta
    setup["setup"]
    sandcastle-init["sandcastle-init"]
    write-a-skill["write-a-skill"]
    deploy["deploy"]

    %% === SANDCASTLE RUNNER (group box) ===
    subgraph sandcastle ["Sandcastle Runner (main.ts)"]
        direction TB
        sc-fetch["Fetch PRD + design.md"]
        sc-branch["Create feature branch"]
        sc-docker["Spin up Docker sandbox"]
        sc-impl["Run implementer agent"]
        sc-check1["Test + type-check"]
        sc-review["Run reviewer agent"]
        sc-check2["Final gate:<br/>test + type-check"]
        sc-next{"More tasks?"}
        sc-pr["Push + open PR"]

        sc-fetch --> sc-branch --> sc-docker --> sc-impl
        sc-impl --> sc-check1 --> sc-review --> sc-check2
        sc-check2 --> sc-next
        sc-next -->|"yes"| sc-impl
        sc-next -->|"no"| sc-pr
    end

    %% === MAIN FLOW ===
    ask-ted -.->|"routes to"| grill-with-docs
    ask-ted -.->|"routes to"| diagnose
    ask-ted -.->|"routes to"| wayfinder
    ask-ted -.->|"routes to"| research

    grill-with-docs -->|"synthesize"| to-spec
    grill-with-docs -->|"detour"| prototype
    grill-with-docs ==>|"invokes"| domain-modeling

    to-spec -->|"break down"| to-tickets
    to-tickets -->|"per ticket"| tdd
    tdd -->|"before commit"| code-review

    %% === ON-RAMPS ===
    wayfinder -->|"map clears"| to-spec
    wayfinder ==>|"research tickets"| research
    wayfinder ==>|"grilling tickets"| grill-me
    wayfinder ==>|"invokes"| domain-modeling
    wayfinder ==>|"prototype tickets"| prototype

    diagnose -->|"post-mortem"| improve-arch

    research -.->|"feeds into"| grill-with-docs

    %% === SANDCASTLE CONNECTIONS ===
    to-tickets -->|"hands off to"| sandcastle
    sandcastle-init -.->|"scaffolds"| sandcastle
    sc-impl ==>|"uses"| implementer-agent
    sc-review ==>|"uses"| reviewer-agent
    implementer-agent -.->|"drives"| tdd
    reviewer-agent -.->|"drives"| code-review

    %% === VOCABULARY LAYER ===
    domain-modeling -.->|"maintains"| CONTEXT.md

    %% === CODEBASE HEALTH ===
    improve-arch -->|"generates idea"| grill-with-docs

    %% === CROSSING SESSIONS ===
    prototype -->|"results via"| handoff
    handoff -.->|"new session"| grill-with-docs

    %% === PRECONDITION ===
    setup -.->|"required by"| to-spec
    setup -.->|"required by"| to-tickets
    setup -.->|"required by"| wayfinder
    setup -.->|"required by"| sandcastle

    %% Styling
    classDef router fill:#f9f,stroke:#333,stroke-width:2px
    classDef main fill:#bbf,stroke:#333
    classDef onramp fill:#bfb,stroke:#333
    classDef model fill:#ffb,stroke:#333
    classDef auto fill:#fdb,stroke:#333
    classDef agent fill:#fcb,stroke:#933,stroke-width:2px
    classDef meta fill:#ddd,stroke:#333
    classDef scStep fill:#fed,stroke:#c84,stroke-width:1px

    class ask-ted router
    class grill-with-docs,to-spec,to-tickets,tdd,code-review,prototype main
    class diagnose,wayfinder,research onramp
    class domain-modeling model
    class sandcastle-init auto
    class implementer-agent,reviewer-agent agent
    class setup,deploy,write-a-skill,handoff,teach,zoom-out,grill-me,improve-arch meta
    class sc-fetch,sc-branch,sc-docker,sc-impl,sc-check1,sc-review,sc-check2,sc-next,sc-pr scStep
```

## Legend

| Style | Meaning |
|-------|---------|
| Pink | Router (entry point) |
| Blue | Main flow (idea → ship) |
| Green | On-ramps (generate work, merge onto main flow) |
| Yellow | Model-invoked vocabulary layers |
| Orange box | Sandcastle runner (autonomous execution) |
| Red-outlined | Agents (implementer, reviewer) |
| Grey | Standalone / productivity / meta |

## Edge types

| Edge | Meaning |
|------|---------|
| `→` solid | Hands off to / next step in flow |
| `==>` thick | Invokes as sub-skill during execution |
| `-.->` dotted | Feeds into / routes to / optional relationship |

## Sandcastle process (per task)

```
Fetch PRD → Create branch → Docker sandbox
    ↓
┌─────────────────────────────────────┐
│  For each unblocked task:           │
│                                     │
│  implementer agent (TDD)            │
│       ↓                             │
│  test + type-check                  │
│       ↓                             │
│  reviewer agent (Standards + Spec)  │
│       ↓                             │
│  FINAL GATE: test + type-check      │
│       ↓                             │
│  ❌ fail → halt immediately         │
│  ✅ pass → next task                │
└─────────────────────────────────────┘
    ↓
Push branch + open PR
```

## Invocation summary

| Skill/Agent | Type | Invoked by |
|-------------|------|-----------|
| domain-modeling | model-invoked | grill-with-docs, wayfinder, any skill when terms are fuzzy |
| code-review | model-invoked | tdd (before commit), reviewer agent (quality gate), user directly |
| research | model-invoked | wayfinder (research tickets), user directly |
| prototype | model-invoked | grill-with-docs (detour), wayfinder (prototype tickets), user directly |
| tdd | model-invoked | to-tickets (per ticket), implementer agent (per task), user directly |
| implementer | agent | sandcastle runner (per task) |
| reviewer | agent | sandcastle runner (after implementer, always) |
