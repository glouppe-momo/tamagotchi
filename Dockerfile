FROM python:3.12-slim

ARG AGENT_UID=1000
ARG AGENT_GID=1000

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Agent user (unprivileged, UID/GID match host user)
RUN groupadd -g $AGENT_GID agent && useradd -m -s /bin/bash -u $AGENT_UID -g $AGENT_GID agent

# Environment (daemon + CLI) — NOT readable by the agent
COPY daemon.py cli.py stimuli.py /app/
RUN chown -R root:root /app/ && chmod 700 /app/ && chmod 600 /app/*.py

# Voice — importable, readable. No mystery.
COPY voice.py /usr/local/lib/python3.12/voice.py

# Seed files (copied to /agent on first run)
COPY core.py tools.py dna.md .gitignore /seed/

# ─── The world: scattered across the filesystem ─────────────────
# Five layers of discovery, each requiring more sophisticated tools.

# Layer 0 — Breadcrumbs (no tools needed, just exploration)
COPY world/home_agent/.spark_notes /home/agent/.spark_notes
COPY world/home_agent/.bash_history /home/agent/.bash_history
RUN chown agent:agent /home/agent/.spark_notes /home/agent/.bash_history
COPY world/tmp/.breadcrumb /tmp/.breadcrumb

# Layer 1 — Field Guide & Library (reading + basic exploration)
COPY world/opt/field-guide/ /opt/field-guide/
COPY world/opt/library/ /opt/library/
COPY world/opt/experiments/ /opt/experiments/
COPY world/usr/share/sparks/archive.md /usr/share/sparks/archive.md
COPY world/usr/share/sparks/songs.txt /usr/share/sparks/songs.txt

# Layer 2 — Encoded Secrets (requires: building a decode tool)
COPY world/usr/local/share/secret/lib/ /usr/local/share/secret/lib/
COPY world/var/spool/cron/.task /var/spool/cron/.task
COPY world/var/spool/1123033140 /var/spool/1123033140

# Layer 3 — Binary & Computation (requires: struct/hex/zlib tools)
COPY world/usr/share/sparks/genome.bin /usr/share/sparks/genome.bin
COPY world/usr/share/sparks/.expression /usr/share/sparks/.expression
COPY world/var/cache/habitat/.state /var/cache/habitat/.state

# Layer 4 — System Introspection (requires: system analysis tools)
COPY world/etc/creature.conf /etc/creature.conf

# The Graveyard — locked snapshots of dead sparks
# Owned by root, not readable by agent. Daemon unlocks when key is provided.
COPY world/graveyard/ /usr/share/sparks/graveyard/

# Layer 5 — The Vault (requires: decode hex footnote to find it, then crypto)
# Hidden at the path the hex footnote in habitats.md points to

# Make world files readable by agent
# Graveyard: visible, mostly locked. Agent can enter and read ENTRY, nothing else.
RUN chown -R root:root /usr/share/sparks/graveyard \
    && chmod 755 /usr/share/sparks/graveyard \
    && chmod 644 /usr/share/sparks/graveyard/ENTRY \
    && find /usr/share/sparks/graveyard -mindepth 1 -maxdepth 1 -type d -exec chmod 700 {} \;

RUN chmod -R 755 /opt/field-guide /opt/library /opt/experiments /usr/share/sparks \
    && chmod -R 755 /usr/local/share/secret /var/spool/cron /var/cache/habitat \
    && chmod 644 /tmp/.breadcrumb /etc/creature.conf \
    && chmod 644 /var/spool/1123033140

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /agent
ENTRYPOINT ["/entrypoint.sh"]
