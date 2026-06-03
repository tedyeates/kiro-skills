---
name: deploy
description: Copy skills, agents, and steering files from this repo to ~/.kiro/ for global use. Use when user says "deploy", "update global", "install skills", "sync skills", or wants to update their global kiro config.
---
# Deploy

Copy this repo's skills, agents, and steering files to the global `~/.kiro/` directory.

## Process

Detect the OS and run the appropriate commands:

### Windows (PowerShell)

```powershell
Copy-Item -Recurse -Force .\skills\* ~\.kiro\skills\
Copy-Item -Force .\agents\* ~\.kiro\agents\
Copy-Item -Force .\steering\* ~\.kiro\steering\
```

### macOS / Linux

```bash
cp -r ./skills/* ~/.kiro/skills/
cp ./agents/*.json ~/.kiro/agents/
cp ./steering/* ~/.kiro/steering/
```

Report what was copied (count of skills, agents, steering files).
