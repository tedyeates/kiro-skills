# Design Conformance Review

Per-section conformance rules and severity ladder. This file documents what the design conformance agent checks when comparing a PR diff against the originating design spec.

## Principle

**"1 spec = 1 PR"** — the entire spec is compared against the entire PR. If a PR implements half a spec, unimplemented stories are High findings.

## Sections Checked

| Spec Section | Conformance Question | What constitutes a finding |
|---|---|---|
| ER Diagram | Do migrations/schema include all columns, types, FKs? Extra columns not in spec? | Missing column = High, wrong type = Medium, extra column = Low (scope creep) |
| Personas & Roles | Do roles match spec permissions? | Role can do something spec forbids = Critical, missing role restriction = High |
| State Diagram | Do status transitions in code match the diagram? | Missing transition = High, extra transition not in spec = Medium |
| Flowchart | Does business logic follow same branching/sequencing? | Wrong branch logic = High, missing branch = Medium |
| User Stories | Is each story implemented? Any skipped? | Story not implemented = High, partially done (edge case skipped) = Medium |
| Implementation Decisions | Are stated module boundaries and patterns followed? | Wrong architecture = High, minor pattern deviation = Low |
| Testing Decisions | Is stated tooling used? | Wrong framework = Medium (depth owned by test-quality agent) |

## Severity Ladder

| Severity | Meaning | Examples |
|----------|---------|----------|
| **Critical** | Auth violation — role can do something spec forbids, spec-required auth not implemented | Endpoint missing auth middleware; role has access spec denies |
| **High** | Missing story/state — user story not implemented, state transition missing, table missing columns | Story skipped entirely; enum missing a status; migration lacks a column |
| **Medium** | Edge case skipped — story mostly done but edge case from spec not covered | Happy path works but spec-defined error branch missing; extra state transition not in diagram |
| **Low** | Naming/scope creep — naming deviation, minor pattern divergence, code does X but spec is silent | Column named differently; helper added that spec doesn't mention; minor pattern deviation |

## Rules

1. **1 spec = 1 PR** — the entire spec is compared against the entire PR.
2. **Missing spec sections are skipped** with a note in the summary (not a finding).
3. **Scope creep**: code does X, spec is silent on X → Low finding.
4. **Only checks against what the spec explicitly states** — does not invent requirements.
5. **No filesystem access** — analysis is based solely on the diff and spec content provided.
