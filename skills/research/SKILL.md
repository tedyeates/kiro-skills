---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a cited Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---
# Research

Spin up a **background agent** to do the research, so the main session keeps working while it reads.

## Triggers

- User asks to research a topic, look up docs, or gather API facts
- Another skill (wayfinder, grill-with-docs) needs facts from outside the current context
- The agent encounters a question it can't confidently answer from memory and the answer lives in official docs

## Process

1. **Investigate the question against primary sources** — official docs, source code, specs, first-party APIs — not secondary write-ups. Follow every claim back to the source that owns it.

2. **Write the findings to a single Markdown file**, citing each claim's source with a URL or file path.

3. **Save it where the repo already keeps such notes**; match the existing convention:
   - If `docs/research/` exists, put it there
   - If `docs/` exists, put it under `docs/research/`
   - Otherwise, create `docs/research/` and note where it went

## Output format

```markdown
# Research: {topic}

Date: {date}
Question: {the original question}

## Findings

### {Sub-topic 1}

{Finding with inline citations}

Source: {URL or file path}

### {Sub-topic 2}

{Finding}

Source: {URL}

## Summary

{2-3 sentence synthesis answering the original question}

## Open questions

- {Anything that couldn't be resolved from available sources}
```

## Rules

- **Primary sources only** — official docs, source repos, RFCs, API references. Not blog posts, tutorials, or Stack Overflow unless they're the only source.
- **Cite every claim** — no uncited assertions
- **Declare confidence** — if a source is ambiguous or the docs are unclear, say so
- **Keep it short** — the file should answer the question, not be a textbook. Target under 500 words unless the topic genuinely requires more.
