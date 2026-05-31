# Logic Prototype

A tiny interactive terminal app that lets the user drive a state model by hand. Use this when the question is about **business logic, state transitions, or data shape**.

## When this is the right shape

- "I'm not sure if this state machine handles the edge case where X then Y."
- "Does this data model actually let me represent the case where..."
- "I want to feel out what the API should look like before writing it."
- Anything where the user wants to **press buttons and watch state change**.

If the question is "what should this look like" — wrong branch. Use [UI.md](UI.md).

## Process

### 1. State the question

Write down what state model and what question you're prototyping. One paragraph at the top of the file.

### 2. Pick the language

Use whatever the host project uses. Match existing conventions for tooling.

### 3. Isolate the logic in a portable module

Put the actual logic behind a small, pure interface that could be lifted into the real codebase later. The TUI is throwaway; the logic module shouldn't be.

The right shape depends on the question:
- **A pure reducer** — `(state, action) => state`. Good when actions are discrete events.
- **A state machine** — explicit states and transitions. Good when "which actions are legal right now" is part of the question.
- **A small set of pure functions** over a plain data type. Good when there's no implicit current state.
- **A class/module with a clear method surface** when the logic genuinely owns ongoing internal state.

Keep it pure: no I/O, no terminal code. The TUI imports it; nothing flows the other direction.

### 4. Build the smallest TUI that exposes the state

On every tick, clear the screen and re-render the whole frame. Each frame has:
1. **Current state**, pretty-printed (one field per line or formatted JSON)
2. **Keyboard shortcuts** at the bottom: `[a] add item [d] delete item [q] quit`

Behaviour:
1. Initialise state — a single in-memory object. Render first frame on start.
2. Read one keystroke at a time, dispatch to a handler that mutates state.
3. Re-render the full frame after every action.
4. Loop until quit.

### 5. Make it runnable in one command

Add a script to the project's existing task runner. The user should run `pnpm run <name>` or equivalent.

### 6. Hand it over

Give the user the run command. The interesting moments are when they say "wait, that shouldn't be possible" — those are the bugs in the _idea_.

### 7. Capture the answer

When done, record what it taught you in a `NOTES.md` next to the prototype before deleting.

## Anti-patterns

- Don't add tests — a prototype that needs tests is no longer a prototype.
- Don't wire it to the real database — use in-memory.
- Don't generalise — the prototype answers one question.
- Don't blur logic and TUI together — keep the TUI as a thin shell over a pure module.
