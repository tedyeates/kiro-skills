---
name: prototype
description: Build a throwaway prototype to flesh out a design — either a runnable terminal app for state/business-logic questions, or several radically different UI variations toggleable from one route. Enhances the design phase. Use when user wants to prototype, sanity-check a data model or state machine, mock up a UI, explore design options, or says "prototype this", "let me play with it", "try a few designs".
---
# Prototype

Enhances Kiro's **design phase** by building throwaway code that answers a design question before committing to an approach.

A prototype is **throwaway code that answers a question**. The question decides the shape.

## Pick a branch

Identify which question is being answered — from the user's prompt, the surrounding code, or by asking:

- **"Does this logic / state model feel right?"** → [LOGIC.md](LOGIC.md). Build a tiny interactive terminal app that pushes the state machine through cases that are hard to reason about on paper.
- **"What should this look like?"** → [UI.md](UI.md). Generate several radically different UI variations on a single route, switchable via a URL search param and a floating bottom bar.

If the question is genuinely ambiguous, default to whichever branch better matches the surrounding code (a backend module → logic; a page or component → UI) and state the assumption.

## Rules that apply to both

1. **Throwaway from day one, clearly marked.** Locate prototype code close to where it will actually be used. Name it so a reader can see it's a prototype, not production.
2. **One command to run.** Whatever the project's existing task runner supports. The user must be able to start it without thinking.
3. **No persistence by default.** State lives in memory. If the question involves a database, hit a scratch DB or local file with a clear "PROTOTYPE — wipe me" name.
4. **Skip the polish.** No tests, no error handling beyond what makes it runnable, no abstractions.
5. **Surface the state.** After every action (logic) or on every variant switch (UI), show the full relevant state so the user can see what changed.
6. **Delete or absorb when done.** Either delete it or fold the validated decision into real code — don't leave it rotting.

## When done

The _answer_ is the only thing worth keeping. Capture it somewhere durable (commit message, ADR, issue, or a `NOTES.md` next to the prototype) along with the question it was answering.
