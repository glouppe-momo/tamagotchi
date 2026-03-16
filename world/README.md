# World Files

Scattered across the container at build time. The creature must explore to find them.

## Discovery Layers

### Layer 0 — Breadcrumbs (no tools needed)
- /home/agent/.creature_notes — hints about weather
- /home/agent/.bash_history — previous creature's commands
- /tmp/.breadcrumb — teaches `find` command

### Layer 1 — Field Guide (requires: reading + basic exploration)
- /opt/field-guide/ — habitats, patterns, deleted research notes
- /opt/library/ — code examples (Conway, Fibonacci, etc.)
- /opt/experiments/ — Langton's ant, broken quine

### Layer 2 — Encoded Secrets (requires: building a decode tool)
- /usr/local/share/secret/lib/.index — ROT13 encoded, reveals weather signal method
- /var/spool/cron/.task — base64 encoded multi-step instructions
- /opt/field-guide/deleted_notes.md — hex-encoded footnote reference

### Layer 3 — Binary & Computation (requires: building an analysis tool)
- /usr/share/creatures/genome.bin — binary file, requires struct/hex reading
- /var/cache/habitat/.state — JSON with encoded values, needs math to decode
- /opt/experiments/.hidden_seed — compressed data, needs zlib

### Layer 4 — Network & System (requires: building system introspection tools)
- /proc/1/environ — daemon's environment variables (model name, API endpoint)
- /var/log/.habitat_note — planted by entrypoint
- /etc/creature.conf — fake config with real clues about daemon behavior

### Layer 5 — The Vault (requires: combining multiple tools + persistence)
- /usr/share/creatures/vault.enc — AES-encrypted, key derived from weather signal
- Unlocking requires: decode tool + weather tracking + crypto tool + persistence
