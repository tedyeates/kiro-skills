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

## Language Guides

Before writing code, consult the `language-guide` skill for the project's tech stack. If an applicable guide exists, **read it first** and follow those patterns throughout implementation.

## Workflow

### 1. Planning

Before writing any code:
- [ ] Check for applicable language guides and read them
- [ ] Confirm with user what interface changes are needed
- [ ] Confirm which behaviors to test (prioritize — you can't test everything)
- [ ] Identify deep module opportunities (small interface, deep implementation)
- [ ] List the behaviors to test (not implementation steps)
- [ ] Get user approval on the plan

Ask: "What should the public interface look like? Which behaviors matter most?"

### 2. Tracer Bullet

Write ONE integration test that proves the feature is **reachable from its entry point** — the route loads, the page renders, the endpoint responds, or the action triggers. Not internal logic — proof that a user can reach it.

```
RED:   Write test for reachability → test fails (route 404s, page throws, component doesn't mount)
GREEN: Wire the minimum to make it reachable → test passes
```

This catches the "built but not connected" failure mode before you go deep on behavior. Every feature must have at least one integration test proving reachability. If one already exists for the file/route being modified, update it as needed rather than creating a new one.

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

### 4. Refactor

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
[ ] Code is minimal for this test
[ ] No speculative features added
```
