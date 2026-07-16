# Process Flow — From Idea to Shipped Code

Step-by-step guide through the complete workflow. Start with `/ask-ted` if you're unsure which skill fits your situation.

## Prerequisites

- Kiro CLI installed and configured
- Skills deployed globally (`/deploy`)
- Git repo initialized
- `gh` CLI authenticated (for GitHub issue tracker)

---

## Step 0: Setup (once per repo)

**Skill**: `/setup`
**Trigger**: "set up this project" / "configure skills for this repo"

What happens:
1. Agent explores your repo (git remotes, existing config, project type)
2. Asks three questions one at a time:
   - Where do issues live? (GitHub / local markdown)
   - What triage labels do you use? (defaults: `ready-for-agent`, `ready-for-human`)
   - Where does domain documentation live? (single-context / multi-context)
3. Writes `.kiro/steering/project-config.md`

**Output**: `.kiro/steering/project-config.md`

---

## Step 1: Grill (requirements gathering)

**Skill**: `/grill-with-docs` (recommended) or `/grill-me` (lightweight)
**Trigger**: "grill me about this" / "stress-test this plan"
**Kiro phase**: Requirements

What happens:
1. Agent interviews you relentlessly — one question at a time
2. Probes scope, edge cases, dependencies, naming, priorities
3. Invokes `/domain-modeling` throughout to maintain the shared language:
   - Updates `CONTEXT.md` glossary inline as terms are resolved
   - Challenges fuzzy or overloaded terms
   - Offers ADRs when decisions are hard-to-reverse + surprising + real trade-off
4. Stops when every branch of the decision tree has a clear answer

**Output**:
- Shared understanding
- Updated `CONTEXT.md` with precise domain vocabulary
- ADRs in `docs/adr/` for significant decisions

**Tips**:
- Use `/grill-with-docs` for new features or significant changes (stateful — updates files)
- Use `/grill-me` for quick refinements (stateless — no file changes)
- If a question needs a runnable answer, detour through `/prototype` via `/handoff`

---

## Step 2: Prototype (optional — design exploration)

**Skill**: `/prototype`
**Trigger**: "prototype this" / "let me play with it"
**Kiro phase**: Design

What happens:
1. Agent identifies the design question being answered
2. Routes to one of two branches:
   - **Logic branch** → tiny interactive terminal app to drive a state machine
   - **UI branch** → 3+ radically different UI variations on one route
3. You interact with the prototype to answer the question
4. Answer is captured; prototype is throwaway

**Output**: A validated design decision

**When to use**: When unsure about state transitions, data models, or visual layout. Skip if design is obvious.

---

## Step 3: To Spec (design synthesis)

**Skill**: `/to-spec`
**Trigger**: "create the spec" / "write up the design" / "to spec"
**Kiro phase**: Design

What happens:
1. Agent explores the codebase, reads glossary and ADRs
2. **Identifies testing seams** — where tests will grab hold of the feature:
   - Prefers existing seams over creating new ones
   - Uses the highest seam possible
   - Fewer seams = better (ideal is one per module)
3. Presents seams for your confirmation
4. Identifies modules — looks for deep module opportunities
5. Writes a structured spec: problem, solution, user stories, testing seams, implementation decisions, testing decisions, out-of-scope
6. Publishes summary to GitHub Issues (if configured)

**Output**: `.kiro/specs/{title}/design.md` + GitHub Issue

**Important**: No interview here — it synthesizes what's already been discussed. Run `/grill-with-docs` first.

---

## Step 4: To Tickets (task breakdown)

**Skill**: `/to-tickets`
**Trigger**: "break this into tasks" / "to tickets"
**Kiro phase**: Tasks

What happens:
1. Agent reads the spec (or current conversation)
2. Breaks into **tracer-bullet** vertical slices — each cuts through ALL layers end-to-end
3. Identifies blocking edges between tickets
4. Looks for prefactoring opportunities ("make the change easy, then make the easy change")
5. For wide refactors, uses **expand-contract** pattern instead of forcing vertical slices
6. Presents breakdown for your review and iteration
7. Publishes to GitHub Issues with `ready-for-agent` label and blocking relationships
8. Generates a mermaid dependency diagram

**Output per ticket**:
- Title + what it delivers (end-to-end behaviour, not layer-by-layer)
- Blocked-by dependencies
- Acceptance criteria

**Local tracker option**: If not using GitHub, writes to `.scratch/{name}/issues/01-slug.md` — one file per ticket.

---

## Step 5: TDD (implementation)

**Skill**: `/tdd`
**Trigger**: "use tdd" / "implement this with tests"
**Kiro phase**: Implementation

What happens:
1. Pick a ticket from the frontier (unblocked tickets)
2. Write ONE failing test (red)
3. Write minimal code to pass it (green)
4. Refactor if needed
5. Repeat until acceptance criteria met
6. Run `/code-review` before committing

**Key discipline**: One test at a time, vertical slices only. Clear context between tickets.

---

## Step 5b: Code Review (before commit)

**Skill**: `/code-review`
**Trigger**: "review this" / "code review" / invoked automatically by tdd and reviewer agent

Two-axis review of the diff:
- **Standards** — repo coding standards + Fowler smell baseline (12 code smells)
- **Spec** — does it faithfully implement the originating issue/spec?

Both axes run as parallel sub-agents. Reports findings separately so one axis can't mask the other.

---

## Step 6: Diagnose (when things break)

**Skill**: `/diagnose`
**Trigger**: "diagnose this" / "debug this" / "this is broken"
**Kiro phase**: Implementation

What happens:
1. **Feedback loop** — identify the observable signal
2. **Reproduce** — get a minimal reproduction
3. **Minimise** — strip away everything irrelevant
4. **Hypothesise** — form a theory
5. **Instrument** — add logging/assertions to confirm or deny
6. **Fix** — apply fix + regression test

**Post-mortem**: If the bug reveals a missing seam or structural weakness, feeds into `/improve-codebase-architecture`.

---

## Step 7: Improve Architecture (post-wave)

**Skill**: `/improve-codebase-architecture`
**Trigger**: "improve architecture" / "find refactoring opportunities"
**Kiro phase**: Post-implementation

What happens:
1. Reads domain glossary and ADRs
2. Walks codebase looking for shallow modules
3. Proposes deepening opportunities — more behaviour behind simpler interfaces
4. Picking one generates an idea you take into `/grill-with-docs` → main flow

---

## Autonomous Execution (sandcastle)

For hands-off multi-ticket implementation using Docker-sandboxed agents.

### Setup (once per repo)

**Skill**: `/sandcastle-init`
**Trigger**: "sandcastle init" / "setup sandcastle"

What happens:
1. Copies `sandcastle/main.template.ts` → `.sandcastle/main.ts`
2. Installs `tsx` and `@ai-hero/sandcastle` as dev deps
3. Adds `.sandcastle/logs/` to `.gitignore`
4. Fills config from `.kiro/steering/project-config.md`

### Execution

```bash
# Preview task plan
npx tsx .sandcastle/main.ts --prd <number> --dry-run

# Run: implement all unblocked tasks, then open a PR
npx tsx .sandcastle/main.ts --prd <number>
```

**How it works per task:**
1. Runs **implementer** agent (issue + design context inline)
2. Runs test + type-check
3. Runs **reviewer** agent (two-axis code review + mechanical fixes)
4. Runs test + type-check again as **final gate**
5. Halts immediately if final gate fails

**Task selection:**
- Only open sub-issues with `ready-for-agent` label are picked up
- Tasks blocked by open dependencies are skipped
- `ready-for-human` tasks are never touched
- Sequential execution on a single feature branch — no merge conflicts

**Success criteria**: Deterministic test + type-check results, not agent self-reporting.

---

## On-ramps (generate work, merge onto main flow)

### Wayfinder (huge foggy efforts)

**Skill**: `/wayfinder`
**Trigger**: "wayfinder" / when the effort is too big for one session

Charts a **shared map** of decision tickets on the issue tracker. Resolves them one at a time — producing decisions, not deliverables — until the way is clear. Then hands off to `/to-spec`.

Use when you can't yet see the path from here to the destination. Don't use for well-scoped features.

### Research (background reading)

**Skill**: `/research`
**Trigger**: "research this" / "look up how X works" / invoked by wayfinder

Spins up a background agent to read primary sources (official docs, APIs, specs). Produces a cited markdown file in `docs/research/`. Feed results into `/grill-with-docs`.

---

## Supporting Skills (use any time)

### Domain Modeling

**Skill**: `/domain-modeling` (model-invoked)

Active maintenance of the project's shared language. Challenges terms, stress-tests with scenarios, cross-references with code, updates CONTEXT.md inline. Invoked automatically by grill-with-docs, wayfinder, and other skills when terms are fuzzy.

### Zoom Out

**Skill**: `/zoom-out`
**Trigger**: "zoom out" / "explain this at a higher level"

Goes up a layer of abstraction and maps relevant modules using domain vocabulary.

### Handoff

**Skill**: `/handoff`
**Trigger**: "handoff" / "save context for later"

Compacts conversation into a portable document for another session. Use to fork context (e.g., into a prototype session and back).

### Teach

**Skill**: `/teach`
**Trigger**: "teach me" / "I want to learn"

Multi-session structured learning with lessons, quizzes, reference docs, and zone-of-proximal-development tracking. Stateful — persists across sessions in the working directory.

### Write a Skill

**Skill**: `/write-a-skill`
**Trigger**: "write a skill" / "create a new skill"

Meta-skill for authoring new skills with proper structure.

### Convert Claude Skill

**Skill**: `/convert-claude-skill`
**Trigger**: "convert this Claude skill"

Converts Claude Code skills into Kiro-native equivalents.

---

## Typical Session Examples

### New feature (full interactive flow)

```
/ask-ted → routes you to the right starting point
/grill-with-docs → builds shared language, resolves design questions
/prototype → (if unsure about state model or UI)
/to-spec → synthesizes into spec with testing seams
/to-tickets → breaks into tracer-bullet tickets
/tdd → implement each ticket test-first
/code-review → before committing
/improve-codebase-architecture → clean up after the wave
```

### New feature (autonomous sandcastle flow)

```
/grill-with-docs → requirements
/to-spec → spec with seams
/to-tickets → published to GitHub with ready-for-agent labels
npx tsx .sandcastle/main.ts --prd <number> → agents implement + review + verify
```

### Huge foggy effort

```
/wayfinder → chart a decision map
(resolve tickets one by one across sessions)
/to-spec → when map clears
/to-tickets → break into tasks
/tdd or sandcastle → implement
```

### Bug fix

```
/diagnose → reproduce, minimise, hypothesise, fix
```

### Understanding unfamiliar code

```
/zoom-out → maps modules at higher abstraction
```

### Learning something new

```
/teach → structured lessons with practice and spaced repetition
```

### Continuing work from yesterday

```
/handoff → saves context doc
[next day, new session]
"continue from [handoff doc]" → picks up where you left off
```
