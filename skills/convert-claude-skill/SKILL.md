---
name: convert-claude-skill
description: Convert a Claude Code skill (SKILL.md) into its Kiro equivalent (skill, steering file, or agent config). Use when user wants to convert a Claude skill, port a skill from Claude Code, or mentions "convert skill".
---
# Convert Claude Skill

Convert a Claude Code skill into its closest Kiro-native equivalent.

## Process

### 1. Acquire the source

Read the Claude skill source. Accept any of:
- A file path to a local SKILL.md
- A GitHub URL (raw or blob) to a SKILL.md
- Pasted markdown content in the conversation

Extract the YAML frontmatter (`name`, `description`) and the instruction body. Also check for sibling files in the same directory (supporting docs like `tests.md`, `LANGUAGE.md`, etc.).

### 2. Classify the skill

Determine which Kiro construct it maps to using [MAPPING.md](MAPPING.md). Present your recommendation:

**Show the user:**
- Source skill name and description
- Recommended Kiro construct (skill / steering file / agent config)
- Reasoning for the classification
- How it will be activated in Kiro (trigger phrases, always-loaded, agent swap)
- Which Kiro spec phase it augments (if applicable): requirements, design, tasks, or implementation
- Preview of the output file(s) to be generated

### 3. Confirm with user

Ask: "Does this mapping look right? Should I adjust anything before generating?"

Wait for explicit confirmation before writing files.

### 4. Generate the output

Write the Kiro-native file(s) based on the classification:

- **Skill** → `skills/<name>/SKILL.md` with Kiro frontmatter + adapted body
- **Steering file** → `steering/<name>.md` with appropriate `inclusion` frontmatter
- **Agent config** → `agents/<name>.json` with prompt, tools, resources

Adaptations to make during conversion:
- Replace slash-command references with natural language trigger descriptions
- Remove references to Claude Code-specific features (`.claude-plugin`, `CLAUDE.md`)
- Replace "issue tracker" references with generic task/file output unless the project has one configured
- Add Kiro spec phase context where applicable (e.g., "This skill enhances the requirements phase")
- Preserve the core instruction logic and workflow steps unchanged

### 5. Report

Tell the user:
- What was generated and where
- How to activate it (add to agent resources, place in steering dir, etc.)
- Any manual adjustments recommended
