<!-- GitHub: #1 https://github.com/tedyeates/kiro-skills/issues/1 -->

## Problem Statement

The implementer agent produces code but has no automated quality gate. Type errors, test failures, and dead code can slip through unnoticed. There's no agent that checks the implementer's output, fixes mechanical issues, and reports remaining problems to the human. Additionally, the `improve-codebase-architecture` skill relies on vague manual exploration with no data-driven analysis tool, and fallow (the tool that provides that data) has no install path documented anywhere.

## Solution

Add a reviewer agent that runs type checking, tests, and fallow dead-code analysis on code produced by the implementer. The reviewer fixes what it can (up to 3 attempts) and reports pass/fail to the human. Update `improve-codebase-architecture` to use fallow for its Explore phase. Document fallow installation in the README and setup skill.

## User Stories

1. As a developer using subagent pipelines, I want a reviewer stage after the implementer, so that code quality issues are caught before I see the output.
2. As a developer, I want the reviewer to fix type errors automatically, so that I don't have to manually correct trivial mistakes.
3. As a developer, I want the reviewer to fix test failures, so that passing tests are guaranteed when the reviewer reports success.
4. As a developer, I want the reviewer to run fallow dead-code analysis, so that unused exports, files, and dependencies are cleaned up automatically.
5. As a developer, I want the reviewer to auto-fix dead code using `fallow fix`, so that mechanical cleanup doesn't require my intervention.
6. As a developer, I want the reviewer to retry up to 3 times, so that fixes that introduce new issues get a chance to stabilize.
7. As a developer, I want the reviewer to report clearly on failure, so that I know exactly what passed, what failed, and what was attempted.
8. As a developer, I want the reviewer to report clearly on success, so that I know what was fixed and which files were modified.
9. As a developer, I want the reviewer to log mistakes to corrections.md, so that repeated errors are avoided across sessions.
10. As a developer, I want the reviewer to read corrections.md before starting, so that it doesn't repeat known mistakes.
11. As a developer, I want the reviewer to skip fallow on non-JS/TS projects, so that it doesn't produce noise on unsupported codebases.
12. As a developer, I want the reviewer to only fix mechanical issues (dead code, type errors, test failures), so that it doesn't refactor architecture or change business logic.
13. As a developer, I want the reviewer to stop and report to me (not loop back to the implementer), so that I maintain control over design decisions.
14. As a developer, I want `improve-codebase-architecture` to run fallow health, dupes, and circular-deps commands, so that architectural exploration is grounded in real data.
15. As a developer, I want `improve-codebase-architecture` to still allow organic exploration after fallow, so that issues the tool misses are still discoverable.
16. As a developer, I want the setup skill to install fallow globally, so that the reviewer and improve-arch skill can use it immediately.
17. As a developer, I want the README to document fallow prerequisites, so that I know what to install before using these skills.
18. As a developer, I want the implementer agent to reference global skill paths, so that skills work regardless of which repo I'm in.
19. As a developer, I want both implementer and reviewer to have corrections.md in their resources, so that the corrections system works in subagent pipelines.
20. As a developer, I want the setup skill's triage labels section to only default to `ready-for-agent` and `ready-for-human`, so that it matches what's actually used.

## Implementation Decisions

- **Reviewer agent config** — new agent JSON with: prompt describing the check-fix-verify loop (3 attempts max), tools matching implementer plus fallow commands, resources loading fallow skill, diagnose skill, and both corrections files via global paths.
- **Allowed shell commands** — superset of implementer: same build/test/check commands plus `fallow dead-code`, `fallow fix`, `fallow audit`, `fallow health`, `fallow dupes`.
- **Reviewer is a terminal stage** — outputs REVIEW PASSED or REVIEW FAILED. No loop back to implementer. Human decides next steps on failure.
- **Fix boundary** — reviewer fixes type errors, test failures, and dead code (via `fallow fix --yes`). Does NOT fix complexity, duplication, or architectural issues.
- **Fallow scope in reviewer** — `fallow dead-code` for detection, `fallow fix --dry-run` then `fallow fix --yes` for removal, `fallow dead-code` to verify. No audit/health/dupes.
- **improve-codebase-architecture update** — Explore phase runs `fallow health --format json --quiet --hotspots`, `fallow dupes --format json --quiet`, and `fallow dead-code --format json --quiet --circular-deps` first, then proceeds with organic exploration.
- **Global skill paths** — all agent resources use `skill://~/.kiro/skills/...` paths. Implementer updated accordingly.
- **Corrections resources** — both agents explicitly include `file://.kiro/steering/corrections.md` and `file://.kiro/corrections.md` in resources.
- **Setup skill** — adds `npm install -g fallow` as a prerequisite step.
- **README** — new Prerequisites section before Quick Start with fallow CLI install and fallow skill install instructions.
- **Setup triage labels** — reduce defaults to only `ready-for-agent` and `ready-for-human`.

## Testing Decisions

No automated tests — deliverables are agent JSON configs and markdown skill files. Validation:
- `kiro-cli agent validate` on reviewer.json and updated implementer.json
- Manual smoke test: run reviewer agent on a project with intentional dead code

## Out of Scope

- Reviewer looping back to implementer
- Fallow audit/health/dupes in the reviewer (those belong to improve-codebase-architecture)
- Rust-specific tooling or configuration
- Non-interactive fallow skill install automation
- `.fallowrc.json` auto-creation
- Complexity or duplication fixes in the reviewer

## Further Notes

- Fallow is JS/TS only. Reviewer skips fallow commands when no JS/TS files are present.
- Fallow skill is installed from `npx skills add fallow-rs/fallow-skills` (requires manual selection of kiro-cli agent when prompted).
- The reviewer assumes fallow is already globally installed — it does not install it itself.
