# Process Flow — From Idea to Shipped Code

Step-by-step guide through the complete workflow using these skills with Kiro CLI.

## Prerequisites

- Kiro CLI installed and configured
- Skills available via agent resources (see README Quick Start)
- Git repo initialized

---

## Step 0: Setup (once per repo)

**Skill**: `setup`
**Trigger**: "set up this project" / "configure skills for this repo"

What happens:
1. Agent explores your repo (git remotes, existing config, project type)
2. Asks you three questions one at a time:
   - Where do issues live? (GitHub / GitLab / local markdown / other)
   - What triage labels do you use? (defaults provided)
   - Where does domain documentation live? (single-context / multi-context)
3. Writes `.kiro/steering/project-config.md` — an always-loaded steering file that other skills read

**Output**: `.kiro/steering/project-config.md`

**When to re-run**: Only if you switch issue trackers or want to start fresh.

---

## Step 1: Grill (requirements gathering)

**Skill**: `grill-with-docs` (recommended) or `grill-me` (lightweight)
**Trigger**: "grill me about this" / "stress-test this plan" / "grill with docs"
**Kiro phase**: Requirements

What happens:
1. Agent interviews you relentlessly about your plan — one question at a time
2. Probes scope, edge cases, dependencies, naming, priorities
3. *(grill-with-docs only)* Updates `CONTEXT.md` glossary inline as terms are resolved
4. *(grill-with-docs only)* Offers ADRs when decisions are hard-to-reverse, surprising, and involve real trade-offs
5. Stops when every branch of the decision tree has a clear answer

**Output**:
- Shared understanding between you and the agent
- *(grill-with-docs)* Updated `CONTEXT.md` with precise domain vocabulary
- *(grill-with-docs)* ADRs in `docs/adr/` for significant architectural decisions

**Tips**:
- Use `grill-with-docs` for new features or significant changes
- Use `grill-me` for quick refinements or when you don't want file changes
- The glossary compounds across sessions — each grilling makes future sessions more precise

---

## Step 2: Prototype (optional — design exploration)

**Skill**: `prototype`
**Trigger**: "prototype this" / "let me play with it" / "try a few designs"
**Kiro phase**: Design

What happens:
1. Agent identifies the question being answered
2. Routes to one of two branches:
   - **Logic branch** → builds a tiny interactive terminal app to drive a state machine
   - **UI branch** → generates 3+ radically different UI variations on one route
3. You interact with the prototype to answer the design question
4. Answer is captured; prototype is deleted or absorbed

**Output**: A validated design decision (captured in ADR, commit message, or NOTES.md)

**When to use**: When you're unsure about state transitions, data models, or visual layout. Skip if the design is obvious.

---

## Step 3: To PRD (design synthesis)

**Skill**: `to-prd`
**Trigger**: "create the PRD" / "write up the design"
**Kiro phase**: Design

What happens:
1. Agent explores the codebase, reads glossary and ADRs
2. Identifies modules to build/modify — looks for deep module opportunities
3. Presents module list for your confirmation
4. Writes a structured PRD: problem, solution, user stories, implementation decisions, testing decisions, out-of-scope

**Output**: A PRD document with exhaustive user stories and module interfaces

**Important**: The agent does NOT interview you here — it synthesizes what's already been discussed. Run `grill-with-docs` first if requirements aren't clear.

---

## Step 4: To Issues (task breakdown)

**Skill**: `to-issues`
**Trigger**: "break this into tasks" / "create issues from this"
**Kiro phase**: Tasks

What happens:
1. Agent reads the PRD (or current conversation)
2. Breaks it into vertical-slice tasks — each cuts through ALL layers end-to-end
3. Groups tasks into waves based on dependencies
4. Ensures no two tasks in the same wave edit the same files
5. Presents the breakdown for your review and iteration

**Output**: A task list with this structure per task:
- Title, Type (AFK/HITL), Wave number
- Blocked-by dependencies
- Interface boundary (files this task owns exclusively)
- Acceptance criteria

**Key constraint**: Tasks in the same wave are designed for parallel execution — they define their own interfaces and never touch the same files.

---

## Step 5: Wave Runner (parallel execution)

**Tool**: `scripts/wave-runner.py`
**Kiro phase**: Implementation

What happens:
1. Script parses the task list from Step 4
2. Validates dependencies (no task can depend on a same/later wave task)
3. For each wave, spawns parallel Kiro CLI sessions (one per AFK task)
4. Each session uses the `implementer` agent with TDD discipline
5. On wave completion, marks successful tasks `[x]` in the tasks file
6. Stops on failure or when HITL tasks block the next wave
7. On re-run, skips already-completed `[x]` tasks

```bash
# See the wave decomposition
python scripts/wave-runner.py tasks.md --dry-run

# Execute with defaults
python scripts/wave-runner.py tasks.md

# Custom settings
python scripts/wave-runner.py tasks.md --agent my-agent --max-parallel 6
```

**HITL tasks**: Skipped during execution. If a future task depends on a HITL task, the script stops after the current wave and tells you which HITL tasks to complete. Mark them done manually (`## [x] Task N:`) and re-run.

**Logs**: Each sub-agent's full output is written to `.wave-runner/task-N.log`.

**Within each task**, the `tdd` skill drives implementation:
1. Write ONE failing test (red)
2. Write minimal code to pass it (green)
3. Refactor if needed
4. Repeat until acceptance criteria met

---

## Step 6: Diagnose (when things break)

**Skill**: `diagnose`
**Trigger**: "diagnose this" / "debug this" / "this is broken"
**Kiro phase**: Implementation

What happens:
1. **Feedback loop** — identify what observable signal tells you it's broken
2. **Reproduce** — get a minimal reproduction
3. **Minimise** — strip away everything irrelevant
4. **Hypothesise** — form a theory about the cause
5. **Instrument** — add logging/assertions to confirm or deny
6. **Fix** — apply the fix and add a regression test

**When to use**: When a test fails unexpectedly, a bug is reported, or performance regresses. Don't use for "I don't know what to build" — that's a grilling problem.

---

## Step 7: Improve Architecture (post-wave refactoring)

**Skill**: `improve-codebase-architecture`
**Trigger**: "improve architecture" / "find refactoring opportunities"
**Kiro phase**: Post-implementation

What happens:
1. Agent reads the domain glossary and ADRs
2. Walks the codebase looking for shallow modules (wide interfaces, little encapsulation)
3. Proposes deepening opportunities — modules that could encapsulate more behind simpler interfaces
4. Suggests new glossary terms if the code reveals concepts not yet named

**When to use**: After completing a wave of tasks. The codebase has grown; this skill finds where it can be simplified.

---

## Supporting Skills (use any time)

### zoom-out

**Trigger**: "zoom out" / "explain this at a higher level"

One-liner that asks the agent to go up a layer of abstraction and map relevant modules using domain vocabulary. Use when you're lost in unfamiliar code.

### handoff

**Trigger**: "handoff" / "save context for later"

Compacts the current conversation into a portable document for another session. References existing artifacts by path, suggests which skills to invoke next.

### write-a-skill

**Trigger**: "write a skill" / "create a new skill"

Meta-skill for authoring new skills with proper structure, description requirements, and progressive disclosure.

### convert-claude-skill

**Trigger**: "convert this Claude skill"

Converts any Claude Code skill into its Kiro-native equivalent (skill, steering file, or agent config).

---

## Typical Session Examples

### New feature (full flow)

```
You: "I want to add real-time notifications to the app"
     → grill-with-docs (builds shared language, resolves design questions)
     → prototype (if unsure about WebSocket vs SSE state model)
     → to-prd (synthesizes into structured design)
     → to-issues (breaks into parallel tasks)
     → wave-runner (executes tasks with TDD)
     → improve-architecture (clean up after)
```

### Bug fix

```
You: "Users are seeing stale data after updating their profile"
     → diagnose (reproduce, minimise, hypothesise, fix)
```

### Understanding unfamiliar code

```
You: "zoom out on the payment processing module"
     → zoom-out (maps modules and callers at higher abstraction)
```

### Continuing work from yesterday

```
You: "handoff — I need to pick this up tomorrow"
     → handoff (saves context doc)
[next day]
You: [paste handoff doc] "continue from here"
     → agent picks up where you left off
```
