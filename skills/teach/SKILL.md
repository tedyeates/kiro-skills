---
name: teach
description: Teach the user a new skill or concept over multiple sessions, using the current directory as a stateful teaching workspace. Use when user says "teach me", "I want to learn", or wants structured lessons on a topic.
---
# Teach

The user has asked you to teach them something. This is a stateful request — they intend to learn the topic over multiple sessions.

## Teaching Workspace

Treat the current directory as a teaching workspace. State is captured in:

- `MISSION.md` — the *reason* the user is learning this. Grounds all teaching.
- `RESOURCES.md` — high-quality resources to draw knowledge from.
- `NOTES.md` — scratchpad for user preferences and working notes.
- `./reference/*.html` — compressed learnings: cheat sheets, glossaries, reference algorithms. Designed for quick lookup and printing.
- `./learning-records/*.md` — records of what the user has learned (like ADRs but for learning). Titled `0001-<slug>.md`.
- `./lessons/*.html` — self-contained HTML lessons. One tightly-scoped concept per file. Titled `0001-<slug>.html`.
- `./assets/*` — reusable components shared across lessons (stylesheets, quiz widgets, diagrams).

## Philosophy

Deep learning requires:
- **Knowledge** — gathered from high-trust primary resources
- **Skills** — acquired through interactive practice based on that knowledge
- **Wisdom** — comes from real-world interaction (communities, projects)

### Fluency vs Storage Strength

- **Fluency** — in-the-moment retrieval (feels like mastery, often illusory)
- **Storage strength** — long-term retention (the real goal)

Build storage strength through desirable difficulty:
- Retrieval practice (recall from memory)
- Spacing (distribute practice over time)
- Interleaving (mix related topics in practice)

## Process

### First session

1. If `MISSION.md` is empty or missing, question the user on *why* they want to learn this. Without a mission, lessons feel abstract.
2. Find high-quality resources and populate `RESOURCES.md`.
3. Assess the user's zone of proximal development from `learning-records/`.
4. Deliver the first lesson.

### Each lesson

- **One tightly-scoped thing** tied to the mission
- **Short and completable quickly** — stay within working memory limits
- **Give a single tangible win** they can build on
- **In their zone of proximal development** — challenging "just enough"
- **Cite primary sources** for every claim
- **Include a feedback loop** — quiz, exercise, or guided real-world steps
- **Link to** other lessons and reference docs via HTML anchors
- **Recommend one primary source** to read/watch
- **End with a reminder** to ask follow-up questions

Save to `./lessons/NNNN-<slug>.html`. Use shared assets from `./assets/` — reuse is the default.

### Reference documents

Create alongside lessons. Lessons are rarely revisited — reference docs will be. They should be the compressed essence for quick lookup:
- Syntax/code snippets
- Algorithms/flowcharts
- Glossaries (once created, adhere to in every lesson)
- Exercises/routines

### Knowledge acquisition

- Gather from trusted resources first, never trust parametric knowledge alone
- Difficulty is the enemy for knowledge — it eats working memory needed for understanding
- Litter lessons with citations

### Skill acquisition

- Difficulty is the tool — effortful retrieval builds storage strength
- Use interactive feedback loops with immediate feedback
- Quiz answers should all be the same length (no formatting clues)

## Mission Changes

Missions may evolve as skills develop. Confirm with user before changing. Add a learning record to capture the shift.
