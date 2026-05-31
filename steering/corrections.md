# Universal Corrections

## Behavior

Every response with mistake, error, wrong command, false assumption, or retry — MUST append correction entry to log below.

**Read corrections log BEFORE starting work.** Never repeat listed mistake.

## When to Write

- Wrong CLI command or binary name
- Missing flags, env vars, config for command to work
- Import path or module resolution issues
- API/library usage differs from assumption
- File paths or naming conventions wrong
- Build/test/lint commands needing specific args
- Platform-specific gotchas (OS, runtime version, etc.)
- Any false assumption
- Any error requiring retry or workaround

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
