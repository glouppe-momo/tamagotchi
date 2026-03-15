#!/bin/sh

# Seed workspace if empty (first run with volume mount)
if [ ! -f /agent/core.py ]; then
    cp /seed/core.py /seed/tools.py /seed/dna.md /seed/.gitignore /agent/
fi

# Agent owns its workspace
chown -R agent:agent /agent

# Git safe directory
git config --global --add safe.directory /agent
su agent -c 'git config --global --add safe.directory /agent'

# Init git if needed
if [ ! -d /agent/.git ]; then
    su agent -c 'cd /agent && git init -q && git config user.name "creature" && git config user.email "creature@tamagotchi" && git add -A && git commit -m "init" -q'
fi

# Daemon runs as root, agent subprocess runs as agent user
exec python /app/daemon.py
