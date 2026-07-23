---
name: pr-resolve
description: Interactive PR review comment executor — pulls unresolved comments, triages into mechanical fixes vs discussion items, and works through them one at a time with user confirmation. Resolves threads and replies with change summaries. Use when user says "pr-resolve", "fix PR comments", "resolve PR", "work through review", or wants to address PR feedback interactively.
---
# PR Resolve

Interactive executor for PR review comments. Pulls unresolved findings (from any reviewer — bot or human), triages them, and drives resolution one item at a time with the human in the loop.

## Philosophy

Every comment gets: a fix + a prevention measure (test, correction, or flagged skill update). One commit per item. The spec is assumed correct — only the user initiates spec changes.

## Prerequisites

- `gh` CLI authenticated
- `.kiro/steering/project-config.md` with `Repo:` configured (created by `setup` skill)
- PR has review comments to resolve

## Invocation

```
/pr-resolve <PR#>
```

## Process

### 1. Read config and checkout

Read `.kiro/steering/project-config.md` to extract `{owner}/{repo}`.

```bash
gh pr checkout {pr_number}
```

### 2. Resolve spec

Locate the design spec using this fallback chain:

1. PR body contains `Spec: .kiro/specs/<path>/design.md` → use that path
2. Search `.kiro/specs/` directories for one matching the branch name or PR title keywords
3. Ask user: "Which spec does this PR implement?"
4. If user declines → proceed without spec (design conformance items will lack context)

Read the spec once and hold it as context for all items.

### 3. Pull unresolved comments

Fetch all review comments on the PR:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --paginate
```

Filter to unresolved threads only. If resuming from a previous session, report progress:

> "5 of 12 comments remain unresolved."

### 4. Triage

**Check for existing triage file:** `.kiro/pr-resolve-{pr_number}.md`

If it exists, load it — skip re-triaging. Present the remaining items to the user.

If it doesn't exist, perform fresh triage:

Group unresolved comments by axis:
1. **Security** (security-related comments)
2. **Test Quality** (test-related comments)
3. **Design Conformance** (design/spec-related comments)

Within each axis, order by file to minimise context switching.

Split into two categories:

- **Mechanical** — comment describes a specific code change with clear location (add validation, missing null check, test doesn't assert X)
- **Needs discussion** — questions an architectural choice, flags a missing capability, or has multiple valid resolutions

Present the triage to the user for approval. User can reclassify items.

**Save triage** to `.kiro/pr-resolve-{pr_number}.md` after user approves. This file persists across sessions so re-invocation doesn't re-triage from scratch.

### 5. Work through items

Process in order: security → test → design. For each item:

#### 5a. Present plan

**Before proposing any fix**, consult the `language-guide` skill for the project's tech stack.

**When the fix involves writing or modifying tests**, also read:
- `tdd/mocking.md` — mocks only at external boundaries, never internal modules
- `tdd/tests.md` — test behaviour and stable contracts, not implementation details

Do NOT propose a fix until you have consulted applicable guides.

Show the user **all four parts** — do NOT present a plan missing the prevention line:

1. **Comment:** The original review comment (quoted)
2. **Fix:** Proposed code/config change
3. **Prevention:** Exactly one of: new/tweaked test, `.kiro/corrections.md` entry, or flagged skill update. State which and why. This is mandatory — never skip it, even for discussion items.
4. **Approach:** One of three modes:
   - **Add tests to existing code** — comment asks for test coverage on code that already exists and functions → write tests that verify current behaviour, run them. No red-green-refactor cycle (TDD is for building new functionality test-first, not for retroactively covering existing code).
   - **TDD** — the fix requires *new code that doesn't exist yet* → write failing test first, then implement.
   - **Direct fix** — fix is already covered by existing tests → explain which test covers it.

**Wait for user confirmation before implementing.**

#### 5b. Implement

**If adding tests to existing code** (coverage requested, code already exists):
1. Read the code under test — understand its current behaviour
2. Write tests covering core behaviour (rendering, interactions, state changes) — not exhaustive internals
3. Run tests — if they pass, done. If they fail, the code has a bug: present the failure to user before fixing
4. Add prevention measure

**If TDD needed** (fix requires new code):
1. Write test that should pass if the fix is correct
2. Run test — confirm RED
3. Implement the fix — confirm GREEN
4. Add prevention measure

**If direct fix** (coverage exists):
1. Implement the fix
2. Run targeted tests
3. Add prevention measure
4. Explain why new test isn't needed — i.e., how existing tests cover this. If the answer is unclear ("how did this issue surface if tests covered it?"), propose one of:
   - Tweak existing test to catch this pattern
   - Add to `.kiro/corrections.md` as an implementation issue
   - Flag skill update needed

#### 5c. Handle test failures

If the fix breaks existing tests, **do not auto-fix**. Present to user:
- Broken test location
- Fix location
- Error output

User decides: update the test (it was wrong) or revert the fix (fix was wrong).

#### 5d. Commit

One commit containing: fix + prevention measure (test/correction/skill flag).

```bash
git add <changed files>
```

Invoke `caveman-commit` to generate the commit message. Include `Refs #{pr_number}` in the body.

```bash
git commit -m "<generated message>"
```

#### 5e. Reply and resolve

Reply to the PR comment explaining the change:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  --method POST \
  --field body="Fixed in \`{short_sha}\` — {one-line summary of change}"
```

For discussion items that went through grilling, include the decision reasoning in the reply.

Resolve the thread:

```bash
gh api graphql -f query='
  mutation {
    resolveReviewThread(input: {threadId: "{thread_node_id}"}) {
      thread { isResolved }
    }
  }
'
```

#### 5f. Confirm continuation

After each item, stop and ask:

> "Item resolved. Continue to next, or stop here for this session?"

If user stops — remaining items stay unresolved on GitHub, picked up next invocation.

### 6. Discussion items

When reaching an item triaged as "needs discussion":

1. Inform user: "This one needs discussion. Here's the question: [X]"
2. Offer: "Grill on it now, or skip for later?"
3. If grilling: invoke `/grill-with-docs` inline — domain terms may sharpen, ADRs may emerge
4. If user states the spec should change: user drives the spec update (skill doesn't propose spec changes unprompted)
5. After resolution: present a full 5a plan (including prevention) then implement via 5b–5e

### 7. Final gate

When all items are resolved (or user has resolved the session):

1. Run full test suite
2. Report result

```
PR #{pr_number} resolve complete:
- {X}/{Y} comments resolved this session
- All tests passing ✓
- Remaining unresolved: {Z} (pick up next session)
```

If tests fail at the final gate, present failures to user for decision.

**Reconcile triage file:** Before exiting, update `.kiro/pr-resolve-{pr_number}.md`:
- Remove items resolved this session (and any resolved externally on GitHub)
- Persist only still-unresolved items
- If nothing remains, delete the file

This keeps the file authoritative so the next invocation opens straight into an accurate remaining-items list without re-fetching GitHub thread state.

## Flagging skill updates

When "why did this slip through" → "skill needs updating":

- Do NOT edit the skill file
- Reply to the PR comment: "Prevention: skill `{name}` should be updated to [description]. Flagged as follow-up."
- User can later pass that comment as a prompt to an agent working on the skills repo

## Edge Cases

**No unresolved comments:** Report clean state and exit.

**Comment on deleted line:** Show the comment context, ask user if still relevant. If not, resolve with "No longer applicable — code removed."

**Skip and resolve:** User can say "skip — not an issue" for any item. Skill resolves the thread with a reply: "Reviewed — no action needed. Reason: {user's reason}."

## See Also

| Skill | Relationship |
|-------|-------------|
| `caveman-commit` | Model-invoked in step 5d for commit message generation |
| `grill-with-docs` | Invoked for discussion items needing domain grilling |
| `tdd` | Consulted guides (`mocking.md`, `tests.md`) when fixes involve tests |
