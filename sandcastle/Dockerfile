FROM node:22-bookworm

RUN apt-get update && apt-get install -y \
    git curl jq python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# pnpm via corepack
RUN corepack enable && corepack prepare pnpm@latest --activate

# Git identity for agent commits
RUN git config --global user.name "kiro-agent" \
    && git config --global user.email "kiro-agent@noreply"

ARG AGENT_UID=1000
ARG AGENT_GID=1000
RUN groupmod -o -g $AGENT_GID node \
    && usermod -o -u $AGENT_UID -g $AGENT_GID -d /home/agent -m -l agent node

USER ${AGENT_UID}:${AGENT_GID}

# Kiro CLI
RUN curl -fsSL https://cli.kiro.dev/install | bash
ENV PATH="/home/agent/.local/bin:$PATH"

WORKDIR /home/agent
ENTRYPOINT ["sleep", "infinity"]
