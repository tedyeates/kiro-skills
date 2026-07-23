---
name: deploy
description: Copy skills, agents, and steering files from this repo to ~/.kiro/ for global use. Use when user says "deploy", "update global", "install skills", "sync skills", or wants to update their global kiro config.
---
# Deploy

Copy this repo's skills, agents, and steering files to the global `~/.kiro/` directory.

## Process

### 1. Check for differences

Before copying, diff the repo against the global `~/.kiro/` directory:

```bash
diff -rq ./skills/ ~/.kiro/skills/
diff -rq ./agents/ ~/.kiro/agents/
diff -rq ./steering/ ~/.kiro/steering/
```

Report a summary table of changes: modified files, new files (only in repo), and files only in global (would be preserved, not deleted).

- If **no differences** → report "Already up to date" and stop.
- If **files only exist in global** (not in repo) → warn that these won't be overwritten but highlight them so the user can decide if they should be pulled back into the repo.
- If **files differ or are new in repo** → show the summary and ask the user to confirm before copying.

### 2. Copy (after confirmation)

Detect the OS and run the appropriate commands:

#### Windows (PowerShell)

```powershell
Copy-Item -Recurse -Force .\skills\* ~\.kiro\skills\
Copy-Item -Force .\agents\* ~\.kiro\agents\
Copy-Item -Force .\steering\* ~\.kiro\steering\
```

#### macOS / Linux

```bash
cp -r ./skills/* ~/.kiro/skills/
cp ./agents/* ~/.kiro/agents/
cp ./steering/* ~/.kiro/steering/
```

Report what was copied (count of skills, agents, steering files).

Note: `agents/` contains both `*.json` configs and their `*-prompt.md` files
(referenced via `"prompt": "file://<name>-prompt.md"`). Copy the whole
directory contents — not just `*.json` — or agents will fail to resolve their
prompt files.
