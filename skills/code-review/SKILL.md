---
name: code-review
description: Two-axis review of the diff since a fixed point — Standards (does the code follow repo conventions + Fowler smell baseline?) and Spec (does it faithfully implement the originating issue/spec?). Runs both reviews as parallel sub-agents. Use when user wants to review a branch, PR, or says "review since X", "code review", "review this".
---
# Code Review

Two-axis review of the diff between `HEAD` and a fixed point:
- **Standards** — does the code conform to this repo's coding standards?
- **Spec** — does the code faithfully implement the originating issue/spec?

Both axes run as **parallel sub-agents** so they don't pollute each other's context, then this skill aggregates their findings.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point — a commit SHA, branch name, tag, `main`, `HEAD~5`, etc. If they didn't specify one, default to `main` (merge-base).

Capture the diff: `git diff $(git merge-base main HEAD)...HEAD`
Capture commits: `git log $(git merge-base main HEAD)..HEAD --oneline`

Confirm the diff is non-empty before proceeding.

### 2. Identify the spec source

Look for the originating spec in this order:
1. Issue references in commit messages (`#123`, `Closes #45`)
2. A path the user passed as argument
3. A spec file under `.kiro/specs/` matching the branch name or feature
4. If nothing found, ask the user. If they say there isn't one, the Spec axis reports "no spec available"

### 3. Identify the standards sources

Look for coding standards docs in the repo: `CODING_STANDARDS.md`, `CONTRIBUTING.md`, `.kiro/steering/` files, linter configs.

On top of repo-documented standards, always carry the **smell baseline** (Fowler, _Refactoring_ ch.3):

- **Mysterious Name** — name doesn't reveal what it does → rename
- **Duplicated Code** — same logic shape in multiple hunks → extract
- **Feature Envy** — method reaches into another object's data more than its own → move it
- **Data Clumps** — same fields travel together → bundle into a type
- **Primitive Obsession** — primitive standing in for a domain concept → give it a type
- **Repeated Switches** — same switch/if-cascade recurs → polymorphism or map
- **Shotgun Surgery** — one change forces scattered edits → gather into one module
- **Divergent Change** — one file edited for unrelated reasons → split
- **Speculative Generality** — abstraction for needs the spec doesn't have → delete
- **Message Chains** — long `a.b().c().d()` navigation → hide behind one method
- **Middle Man** — class that mostly delegates → cut it
- **Refused Bequest** — subclass ignores most of what it inherits → use composition

**Rules:**
- Repo standards override the baseline (if repo endorses something baseline flags, suppress it)
- Smells are always judgement calls, never hard violations
- Skip anything tooling already enforces (linter, formatter)

### 4. Spawn both sub-agents in parallel

Use the subagent tool with two stages (no dependency between them):

**Standards sub-agent prompt:**
- The full diff and commit list
- Standards source files + the smell baseline above (pasted in full)
- Brief: "Report — per file/hunk where relevant — (a) every place the diff violates a documented standard, citing the standard; (b) any baseline smell, naming it and quoting the hunk. Distinguish hard violations from judgement calls. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt:**
- The diff and commit list
- The spec contents (path or fetched issue body)
- Brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec sub-agent.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned.

End with a one-line summary: total findings per axis, and the worst issue within each axis. Don't pick a single winner across axes — that's the reranking the separation exists to prevent.

### 6. Fix mechanical issues (optional)

If the user asks (or if running inside the reviewer agent), fix:
- Type errors, test failures, dead code flagged by Standards
- Missing acceptance criteria implementation flagged by Spec

Do NOT fix judgement-call smells unless explicitly asked.

## Why two axes

A change can pass one axis and fail the other:
- Code follows every standard but implements the wrong thing → **Standards pass, Spec fail**
- Code does exactly what the issue asked but breaks conventions → **Spec pass, Standards fail**

Reporting them separately stops one axis from masking the other.
