---
name: write-a-skill
description: Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill, or says "write a skill".
---
# Write A Skill

Meta-skill for creating new Kiro skills with proper structure.

## Process

### 1. Gather requirements

Ask the user:
- What task/domain does the skill cover?
- What specific use cases should it handle?
- Does it need supporting reference files or just the main SKILL.md?
- Any reference materials to include?

### 2. Draft the skill

Create:
- `SKILL.md` with concise instructions
- Additional reference files if content exceeds ~100 lines
- Utility scripts if deterministic operations needed

### 3. Review with user

Present draft and ask:
- Does this cover your use cases?
- Anything missing or unclear?
- Should any section be more/less detailed?

## Skill Structure

```
skill-name/
├── SKILL.md          # Main instructions (required)
├── REFERENCE.md      # Detailed docs (if needed)
├── EXAMPLES.md       # Usage examples (if needed)
└── scripts/          # Utility scripts (if needed)
    └── helper.js
```

## SKILL.md Template

```md
---
name: skill-name
description: Brief description of capability. Enhances the <phase> phase. Use when [specific triggers].
---
# Skill Name

Enhances Kiro's **<phase> phase** by [what it does].

## Process

[Step-by-step workflow]
```

## Description Requirements

The description is the only thing the agent sees when deciding which skill to load.

**Format**:
- First sentence: what it does
- Second sentence: which Kiro phase it enhances (if applicable)
- Third sentence: "Use when [specific triggers]"

**Good**: "Break a plan into independently-implementable tasks using vertical slices. Enhances the tasks phase. Use when user wants to break down work or says 'break this into tasks'."

**Bad**: "Helps with tasks."

## When to Split Files

Split into separate files when:
- SKILL.md exceeds ~100 lines
- Content has distinct domains (e.g., logic vs UI branches)
- Advanced features are rarely needed

## Review Checklist

After drafting, verify:
- [ ] Description includes triggers ("Use when...")
- [ ] SKILL.md is concise (under 100 lines ideally)
- [ ] Consistent terminology with project glossary
- [ ] Concrete examples included where helpful
- [ ] References are one level deep (no chains of includes)
