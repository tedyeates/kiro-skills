# WSL Setup for Sandcastle Runner

One-time setup to get the sandcastle runner environment working from scratch on Windows.

## 1. Install WSL

From PowerShell (Admin):

```powershell
wsl --install -d Ubuntu-24.04
```

Reboot if prompted, then launch Ubuntu and create your user.

## 2. System Dependencies

```bash
sudo apt update && sudo apt install -y git curl jq
```

## 3. Docker CE

```bash
# Remove old versions
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Add Docker repo
sudo apt install -y ca-certificates gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin

# Allow non-root usage
sudo usermod -aG docker $USER
```

Log out and back in (or `newgrp docker`) for the group change to take effect.

```bash
# Verify
docker run --rm hello-world
```

## 4. Node.js 22 + pnpm

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
corepack enable && corepack prepare pnpm@latest --activate
```

## 5. Python 3 (usually pre-installed)

```bash
sudo apt install -y python3 python3-venv python3-pip
```

## 6. GitHub CLI

```bash
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install -y gh
```

```bash
gh auth login
```

## 7. Kiro CLI

```bash
curl -fsSL https://cli.kiro.dev/install | bash
```

```bash
kiro-cli login --use-device-flow
```

## 8. Clone Repos

```bash
mkdir -p ~/projects && cd ~/projects
git clone git@github.com:tedyeates/kiro-skills.git
git clone git@github.com:tedyeates/stockmanager.git
```

## 9. Build the kiro-runner Image

```bash
cd ~/projects/kiro-skills
docker build -t kiro-runner -f sandcastle/Dockerfile .
```

Verify:

```bash
docker run --rm kiro-runner bash -c "node --version && python3 --version && pnpm --version && git --version"
```

## 10. Run the Sandcastle Runner

```bash
cd ~/projects/stockmanager
npx tsx .sandcastle/main.ts --prd 42 --dry-run
```
