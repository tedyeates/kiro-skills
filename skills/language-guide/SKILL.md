---
name: language-guide
description: Index of language/framework-specific guides covering patterns and pitfalls that agents commonly get wrong. Model-invoked by tdd and code-review based on the current tech stack. Use when the agent needs framework-specific guidance, or user says "check the guide for X".
---
# Language Guide

Platform and framework-specific patterns that agents get wrong repeatedly. Each guide is a concise reference of **correct patterns** and **why they matter** — not a tutorial.

## Available Guides

| Guide | File | When to consult |
|-------|------|-----------------|
| Supabase | [supabase.md](supabase.md) | Writing migrations, RLS policies, auth hooks, seed data, or database functions for a Supabase project |
| Vitest Browser | [vitest-browser.md](vitest-browser.md) | Writing component/integration tests that run in vitest browser mode |

## How This Skill Is Used

This skill is **model-invoked** — you don't run it directly. The `tdd` and `code-review` skills will read the relevant guide when working on a project that uses a listed technology.

**Detection**: Check `package.json`, `requirements.txt`, `supabase/config.toml`, or other config files to determine the tech stack in use. If a guide exists for a detected technology, read it before writing or reviewing code.

## Adding New Guides

When a new pattern or pitfall is surfaced during development:

1. If a guide for that technology exists — append to it
2. If no guide exists — create a new `{technology}.md` in this folder and add it to the table above

Keep guides:
- Focused on **what agents must do** (not general docs)
- Show the correct pattern, then briefly explain why it matters
- Concise: each entry should be 3-5 lines max
- Sourced from real failures (handoff docs, corrections logs, debugging sessions)
