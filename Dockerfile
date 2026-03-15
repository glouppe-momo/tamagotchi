FROM python:3.12-slim

ARG AGENT_UID=1000
ARG AGENT_GID=1000

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Agent user (unprivileged, UID/GID match host user)
RUN groupadd -g $AGENT_GID agent && useradd -m -s /bin/bash -u $AGENT_UID -g $AGENT_GID agent

# Environment (daemon + CLI) — readable but not editable by the agent
COPY daemon.py cli.py /app/
RUN chown -R root:root /app/ && chmod 755 /app/ && chmod 644 /app/*.py

# Voice — importable, readable. No mystery.
COPY voice.py /usr/local/lib/python3.12/voice.py

# Seed files (copied to /agent on first run)
COPY core.py tools.py dna.md .gitignore /seed/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /agent
ENTRYPOINT ["/entrypoint.sh"]
