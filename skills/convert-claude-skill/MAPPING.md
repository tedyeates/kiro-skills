# Mapping Decision Tree: Claude Code → Kiro

## Classification Rules

Ask these questions in order. First match wins.

### 1. Is it always-loaded project rules?

**Indicators**: The skill is referenced in `CLAUDE.md`, contains project conventions, coding standards, or domain glossary content. It has no interactive workflow — just rules the agent should always follow.

**→ Kiro Steering File** (`.kiro/steering/<name>.md`)

```markdown
---
inclusion: always
---
# Content here
```

Examples: `CLAUDE.md` rules, `CONTEXT.md` glossary, coding conventions.

---

### 2. Is it an agent identity/persona?

**Indicators**: Defines who the agent is, what tools it should use, what files it can access, or how it should behave at a fundamental level. Not a workflow — a mode of operation.

**→ Kiro Agent Config** (`.kiro/agents/<name>.json`)

```json
{
  "name": "agent-name",
  "description": "What this agent does",
  "prompt": "System prompt defining behavior",
  "tools": ["read", "write", "shell"],
  "resources": ["skill://skills/**/SKILL.md"]
}
```

Examples: `caveman` (communication mode), specialized reviewer agents.

---

### 3. Is it a workflow that augments a Kiro spec phase?

**Indicators**: The skill has a multi-step process, produces artifacts (PRDs, issues, tests), and maps to one of Kiro's phases (requirements, design, tasks, implementation).

**→ Kiro Skill** (`.kiro/skills/<name>/SKILL.md`) with spec-phase annotation in description.

Map to phase:
- Interviews/grilling/requirements gathering → **Requirements phase**
- PRD creation/design docs/module planning → **Design phase**
- Issue breakdown/task splitting/vertical slices → **Tasks phase**
- TDD/debugging/implementation loops → **Implementation phase**
- Architecture review/refactoring → **Post-implementation**

---

### 4. Is it an on-demand instruction set?

**Indicators**: Has a clear trigger ("Use when..."), provides step-by-step guidance, loaded only when needed.

**→ Kiro Skill** (`.kiro/skills/<name>/SKILL.md`)

```markdown
---
name: skill-name
description: What it does. Use when [triggers].
---
# Instructions
```

Examples: `zoom-out`, `handoff`, `write-a-skill`.

---

## Conversion Templates

### Template: Skill (workflow augmentation)

```markdown
---
name: <name>
description: <what it does>. Enhances the <phase> phase of development. Use when <triggers>.
---
# <Title>

<Adapted instruction body — same logic, Kiro-native references>
```

### Template: Steering File

```markdown
---
inclusion: always
---
# <Title>

<Rules/conventions/glossary content>
```

### Template: Agent Config

```json
{
  "name": "<name>",
  "description": "<description>",
  "prompt": "<system prompt from skill body>",
  "tools": ["read", "write", "shell", "grep", "glob", "code"],
  "allowedTools": ["read", "grep", "glob"],
  "resources": ["skill://skills/**/SKILL.md"]
}
```

---

## Common Adaptations

| Claude Code Pattern | Kiro Equivalent |
|-------------------|----------------|
| `/skill-name` slash command | Natural language trigger in `description` field |
| `CLAUDE.md` reference | `.kiro/steering/` files |
| `CONTEXT.md` reference | Project's `CONTEXT.md` at repo root (domain glossary) |
| `docs/adr/` reference | Same — ADRs are project-level, not tool-specific |
| "publish to issue tracker" | Write to file or use project's configured tracker |
| `disable-model-invocation: true` | Short skill body (Kiro loads full content regardless) |
| Sibling reference files (`tests.md`) | Same — place in skill directory, reference with relative links |
