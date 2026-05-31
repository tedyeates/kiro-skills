---
name: improve-codebase-architecture
description: Find deepening opportunities in a codebase — turn shallow modules into deep ones for better testability and AI-navigability. Use when user wants to improve architecture, find refactoring opportunities, review code structure, or says "improve architecture". Best run after completing a wave of tasks.
---
# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. Run this after completing a wave of implementation tasks, before starting the next wave.

Use the vocabulary defined in [LANGUAGE.md](LANGUAGE.md) consistently.

## Process

### 1. Explore

Read the project's domain glossary and any ADRs first. Then walk the codebase organically, noting friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their **seams**?
- Which parts are untested or hard to test through their current interface?

Apply the **deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.

### 2. Present candidates

For each candidate, present:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture causes friction
- **Solution** — plain English description of what would change
- **Benefits** — explained in terms of locality and leverage, and how tests would improve
- **Before / After** — conceptual description of the shallowness and the deepening
- **Recommendation strength** — `Strong`, `Worth exploring`, or `Speculative`

End with a **Top recommendation**: which candidate to tackle first and why.

**Do NOT propose interfaces yet.** Ask: "Which of these would you like to explore?"

### 3. Grilling loop

Once the user picks a candidate, walk the design tree:
- Constraints and dependencies
- Shape of the deepened module
- What sits behind the seam
- What tests survive the refactor

Side effects during the conversation:
- **New term needed?** → Add to project glossary / CONTEXT.md
- **Fuzzy term?** → Sharpen it immediately
- **User rejects with load-bearing reason?** → Offer an ADR to record why, so future reviews don't re-suggest it
- **Want to explore interfaces?** → Design the deepened module's public API together

### 4. Implement

After the grilling resolves the design, implement the refactor using the `tdd` skill — one vertical slice at a time.
