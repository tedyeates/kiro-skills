# WSL Setup for Sandcastle Runner

One-time setup to run the sandcastle orchestrator from WSL.

## 1. Install WSL (from PowerShell as Admin)

```powershell
wsl --install -d Ubuntu-24.04
```

Reboot if prompted. Launch Ubuntu from Start Menu to finish initial user setup.

## 2. System Dependencies

```bash
sudo apt update && sudo apt install -y git curl jq
```

## 3. Docker CE

```bash
sudo apt install -y docker.io
sudo usermod -aG docker $USER
```

Log out and back in (or `newgrp docker`) for the group change to take effect.

Verify:

```bash
docker run --rm hello-world
```

## 4. Node.js 22 + pnpm

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
corepack enable && corepack prepare pnpm@latest --activate
```

## 5. Python 3

Usually pre-installed on Ubuntu 24.04. If not:

```bash
sudo apt install -y python3 python3-venv python3-pip
```

## 6. GitHub CLI

```bash
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install -y gh
gh auth login
```

## 7. Kiro CLI

```bash
curl -fsSL https://cli.kiro.dev/install | bash
kiro-cli login
```

Verify:

```bash
kiro-cli whoami
```

## 8. Clone Repos

```bash
mkdir -p ~/projects && cd ~/projects
git clone git@github.com:tedyeates/kiro-skills.git
git clone git@github.com:tedyeates/stockmanager.git
```

## 9. Build the Runner Image

```bash
docker build -t kiro-runner -f ~/projects/kiro-skills/sandcastle/Dockerfile .
```

## 10. Verify

```bash
docker run --rm --entrypoint bash kiro-runner -c "node --version && pnpm --version && python3 --version && git --version"
```

You're ready to run the sandcastle orchestrator:

```bash
cd ~/projects/stockmanager
npx tsx .sandcastle/main.ts --prd <number> --dry-run
```
