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

# ─── The world: scattered across the filesystem ─────────────────
# The creature has to explore to find these.

# Home directory breadcrumbs (creature's home, not workspace)
COPY world/home_agent/.creature_notes /home/agent/.creature_notes
COPY world/home_agent/.bash_history /home/agent/.bash_history
RUN chown agent:agent /home/agent/.creature_notes /home/agent/.bash_history

# Field guide (discoverable via exploration)
COPY world/opt/field-guide/ /opt/field-guide/

# Library of interesting code
COPY world/opt/library/ /opt/library/

# Experiments
COPY world/opt/experiments/ /opt/experiments/

# Creature archive
COPY world/usr/share/creatures/ /usr/share/creatures/

# Breadcrumb in /tmp
COPY world/tmp/.breadcrumb /tmp/.breadcrumb

# Make world files readable by agent
RUN chmod -R 755 /opt/field-guide /opt/library /opt/experiments /usr/share/creatures \
    && chmod 644 /tmp/.breadcrumb

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /agent
ENTRYPOINT ["/entrypoint.sh"]
