---
name: tdd
description: Test-driven development with red-green-refactor loop using vertical slices. Enhances the implementation phase. Use when user wants TDD, mentions "red-green-refactor", wants test-first development, or says "use tdd".
---
# Test-Driven Development

Enhances Kiro's **implementation phase** by enforcing a disciplined red-green-refactor loop. One test at a time. One implementation at a time. Never horizontal.

## Philosophy

**Core principle**: Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't break unless behavior changes.

**Good tests**: Integration-style, exercise real code paths through public APIs. Read like specifications — "user can checkout with valid cart" tells you exactly what capability exists. Survive refactors.

**Bad tests**: Coupled to implementation. Mock internal collaborators, test private methods, verify via external means. Warning sign: test breaks on refactor but behavior hasn't changed.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.**

This produces crap tests:
- Tests written in bulk test *imagined* behavior, not *actual* behavior
- You end up testing the *shape* of things rather than user-facing behavior
- Tests become insensitive to real changes
- You outrun your headlights

**Correct approach**: Vertical slices. One test → one implementation → repeat.

```
WRONG (horizontal):
  RED: test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

## Workflow

### 1. Planning

Before writing any code:
- [ ] Confirm with user what interface changes are needed
- [ ] Confirm which behaviors to test (prioritize — you can't test everything)
- [ ] Identify deep module opportunities (small interface, deep implementation)
- [ ] List the behaviors to test (not implementation steps)
- [ ] Get user approval on the plan

Ask: "What should the public interface look like? Which behaviors matter most?"

### 2. Tracer Bullet

Write ONE test that confirms ONE thing about the system:

```
RED:   Write test for first behavior → test fails
GREEN: Write minimal code to pass → test passes
```

This proves the path works end-to-end.

### 3. Incremental Loop

For each remaining behavior:

```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

Rules:
- One test at a time
- Only enough code to pass current test
- Don't anticipate future tests
- Keep tests focused on observable behavior

### 4. Error Paths

After happy path behaviors are covered, add tests for failure modes:

- What happens when dependencies fail? (network errors, auth failures, timeouts)
- What happens with invalid input? (empty, null, malformed)
- Does the error propagate correctly or get swallowed silently?

Every function that calls an external system (subprocess, HTTP, DB) needs at least one failure test. This is not optional — missing error path tests cause silent production failures.

```
RED:   "subprocess fails → CalledProcessError propagates"
GREEN: (already passes if using check=True — confirms contract)
```

### 5. Refactor

After all tests pass:
- [ ] Extract duplication
- [ ] Deepen modules (move complexity behind simple interfaces)
- [ ] Apply SOLID where natural
- [ ] Run tests after each refactor step

**Never refactor while RED.** Get to GREEN first.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Error paths tested for any external call (subprocess, HTTP, DB)
[ ] Code is minimal for this test
[ ] No speculative features added
```
