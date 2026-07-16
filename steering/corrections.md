# Universal Corrections

## Behavior

Every response with mistake, error, wrong command, false assumption, or retry — MUST append correction entry to log below.

**Read corrections log BEFORE starting work.** Never repeat listed mistake.

## When to Write

Log only **agent process errors** — mistakes in how I invoked tools, commands, or APIs. Focus on wrong assumptions that caused a failed attempt or retry.

- Wrong CLI command, flags, or binary name
- Missing env vars or config needed for a command to work
- Import path or module resolution wrong
- API/library usage differs from documented behavior
- File paths or naming conventions assumed incorrectly
- Platform-specific gotchas (OS, runtime, Docker quirks)
- Incorrect implementation pattern that would recur across projects

## When NOT to Write

- Bugs in existing code that were diagnosed and fixed (those are just code changes)
- One-off infrastructure issues already resolved (Dockerfile tweaks, migration ordering)
- Code logic errors found during review — unless the error reflects a repeatable bad pattern in how I generate code

The test: "Would this mistake recur in a *different* project/session if I forgot?" If yes → log. If no → skip.

## Format

```
- ❌ [what wrong] → ✅ [fix] (brief reason)
```

Unresolved:
```
- ❌ UNRESOLVED: [description]
```

## Subagent Delegation

When delegating to subagents (invoke_sub_agent), MUST include both files as context:

- `.kiro/steering/corrections.md` (this file — subagents know rules)
- `.kiro/corrections.md` (log — subagents read existing + append new)

Subagents follow same rules: read log before start, append on error.

## Corrections Log

#[[file:.kiro/corrections.md]]
