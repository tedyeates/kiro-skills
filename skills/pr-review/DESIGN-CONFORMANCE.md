# Design Conformance Review

Per-section conformance rules and severity ladder. This file documents what the design conformance agent checks when comparing a PR diff against the originating design spec.

## Principle

**"1 spec = 1 PR"** — the entire spec is compared against the entire PR. If a PR implements half a spec, unimplemented stories are High findings.

## Sections Checked

| Spec Section | Conformance Question | What constitutes a finding |
|---|---|---|
| ER Diagram | Do migrations/schema include all columns, types, FKs? Extra columns not in spec? | Missing column = High, wrong type = Medium, extra column = Low (scope creep) |
| Personas & Roles | Do roles match spec permissions? Cross-layer enforcement if Access Matrix section exists? | Role can do something spec forbids = Critical, missing role restriction = High, frontend shows control backend rejects = High, bypass path = High, missing nav link = Medium, missing access tests = High |
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

## Access Matrix Deep Check (Personas & Roles Section 2)

When the design spec contains an `## Access Matrix Enforcement` section (with View/Read, Field-Level Edit, Action-Level matrices), section 2 becomes a **completeness-oriented** check rather than a purely diff-oriented one.

### Diff-Oriented vs Completeness-Oriented

| | Standard (diff-oriented) | Access Matrix (completeness-oriented) |
|---|---|---|
| **Input** | What changed in this PR | What the spec says must be enforced |
| **Question** | "Does this code match the spec?" | "For every restriction, is there enforcement at every layer?" |
| **Scope** | Only files in the diff | Any file that touches access control (may need to read files not in the diff) |
| **Catches** | Wrong implementation | Missing implementation |

### Checks Performed

For each role × entity × action in the matrix:

1. **Backend**: Read RLS policies, `field_permissions`, service functions. Verify denied actions have actual enforcement.
2. **Frontend**: Read UI components. Verify denied actions don't render controls. No "click then error" patterns.
3. **Navigation**: Verify accessible routes have discoverable nav links.
4. **Bypasses**: Find direct DB writes that skip the role-checked path.
5. **Tests**: Verify access matrix test coverage exists per spec requirements.

### When to Trigger

- The spec has `## Access Matrix Enforcement` → perform full cross-layer audit
- The spec only has a simple Personas table → perform basic role matching (standard behaviour)
