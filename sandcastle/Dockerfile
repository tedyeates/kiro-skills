FROM node:22-bookworm

RUN apt-get update && apt-get install -y \
    git curl jq python3 python3-venv python3-pip \
    libtap-parser-sourcehandler-pgtap-perl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# pnpm via corepack
RUN corepack enable && corepack prepare pnpm@latest --activate

# Supabase CLI — Go binary via .deb package (global npm install is blocked)
# Filename is versioned so we resolve the latest tag first.
RUN SUPABASE_VERSION=$(curl -fsSL https://api.github.com/repos/supabase/cli/releases/latest | jq -r '.tag_name' | sed 's/^v//') \
    && curl -fsSL -o /tmp/supabase.deb \
       "https://github.com/supabase/cli/releases/download/v${SUPABASE_VERSION}/supabase_${SUPABASE_VERSION}_linux_amd64.deb" \
    && dpkg -i /tmp/supabase.deb \
    && rm /tmp/supabase.deb

# Playwright system libraries (chromium): libnss3, libnspr4, etc.
# Version-agnostic OS deps — the version-matched browser BINARY is installed
# per-project in the setup step (`pnpm exec playwright install chromium`) so it
# lands under the agent's ~/.cache and matches the project's pinned Playwright.
RUN npx -y playwright install-deps chromium

ARG AGENT_UID=1000
ARG AGENT_GID=1000
RUN groupmod -o -g $AGENT_GID node \
    && usermod -o -u $AGENT_UID -g $AGENT_GID -d /home/agent -m -l agent node

USER ${AGENT_UID}:${AGENT_GID}

# Git identity for agent commits. MUST run after the USER switch so it writes
# /home/agent/.gitconfig — running as root would write /root/.gitconfig, leaving
# the agent user with no identity ("fatal: unable to auto-detect email address").
RUN git config --global user.name "kiro-agent" \
    && git config --global user.email "kiro-agent@noreply"

# Kiro CLI
RUN curl -fsSL https://cli.kiro.dev/install | bash
ENV PATH="/home/agent/.local/bin:$PATH"

WORKDIR /home/agent
ENTRYPOINT ["sleep", "infinity"]
