# Review Findings — Issues #23, #24, #25

Reviewed: 2026-06-21

These may be resolved by future wave-runner implementation but are recorded here for tracking.

## 🟡 Warnings

### reviewer-prompt.md hardcodes `git diff master`

The adversarial review section says `git diff master`. Fragile if:
- Default branch is `main`
- Orchestrator runs reviewer against a feature branch (not master)

**Likely resolution:** Orchestrator passes the base ref as part of the agent prompt, or reviewer reads it from config. Check when executor module (#20) is implemented.

### merger-prompt.md doesn't specify how to discover the test command

Says "run the project's test command" but doesn't explain discovery. Other agents read `project-config.md` which will include `test_command` per design.md.

**Likely resolution:** Once config module (#13) is implemented and `project-config.md` gains `test_command` field, merger prompt should reference it explicitly. Or the orchestrator passes it in the agent invocation.

## Status

- [ ] Revisit after #13 (config module) and #20 (executor) are implemented
