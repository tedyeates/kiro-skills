---
name: diagnose
description: Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce, minimise, hypothesise, instrument, fix, regression-test. Enhances the implementation phase. Use when user says "diagnose this", "debug this", reports a bug, says something is broken/throwing/failing, or describes a performance regression.
---
# Diagnose

A discipline for hard bugs. Skip phases only when explicitly justified.

## Phase 1 — Build a Feedback Loop

**This is the skill.** Everything else is mechanical. Spend disproportionate effort here.

Try these in order until you have a fast, deterministic, agent-runnable pass/fail signal:

1. **Failing test** at whatever seam reaches the bug
2. **Curl / HTTP script** against a running dev server
3. **CLI invocation** with fixture input, diffing stdout against known-good
4. **Headless browser script** (Playwright/Puppeteer) — drives UI, asserts on DOM/console
5. **Replay a captured trace** — save a real request/payload, replay through the code path
6. **Throwaway harness** — minimal subset of the system exercising the bug path
7. **Property / fuzz loop** — 1000 random inputs looking for the failure mode
8. **Bisection harness** — automate "boot at state X, check, repeat" for `git bisect run`
9. **Differential loop** — same input through old vs new version, diff outputs
10. **HITL script** — last resort, drive a human with a structured script

### Iterate on the loop

- Can I make it faster? (Cache setup, narrow scope)
- Can I make the signal sharper? (Assert on specific symptom)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem)

### If you cannot build a loop

Stop. Say so explicitly. List what you tried. Ask the user for: environment access, captured artifacts (HAR, logs, core dump), or permission for temporary instrumentation.

**Do not proceed without a loop.**

## Phase 2 — Reproduce

Run the loop. Confirm:
- [ ] The failure matches what the **user** described (not a different nearby failure)
- [ ] Reproducible across multiple runs
- [ ] Exact symptom captured (error message, wrong output, timing)

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any. Each must be falsifiable:

> "If [X] is the cause, then [action] will make the bug disappear / make it worse."

Show the ranked list to the user — they often have domain knowledge that re-ranks instantly. Don't block on it; proceed with your ranking if they're AFK.

## Phase 4 — Instrument

Each probe maps to a specific prediction from Phase 3. **One variable at a time.**

Preference:
1. Debugger / REPL inspection (one breakpoint beats ten logs)
2. Targeted logs at boundaries that distinguish hypotheses
3. Never "log everything and grep"

**Tag every debug log** with a unique prefix: `[DEBUG-a4f2]`. Cleanup = single grep.

For **performance regressions**: establish baseline measurement first, then bisect. Measure first, fix second.

## Phase 5 — Fix + Regression Test

1. Write regression test at the correct seam **before** the fix (if a correct seam exists)
2. Watch it fail
3. Apply the fix
4. Watch it pass
5. Re-run the Phase 1 feedback loop against the original scenario

If no correct seam exists for a regression test, note it — the architecture is preventing the bug from being locked down.

## Phase 6 — Cleanup + Post-Mortem

- [ ] Original repro no longer reproduces
- [ ] Regression test passes (or absence of seam documented)
- [ ] All `[DEBUG-...]` instrumentation removed
- [ ] Throwaway prototypes deleted

**Then ask: what would have prevented this bug?** If the answer involves architectural change, recommend running the `improve-codebase-architecture` skill.
