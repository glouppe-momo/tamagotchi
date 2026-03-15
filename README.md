# 🥚 tamagotchi

A Tamagotchi where the creature is a self-modifying LLM agent.

The creature has a body (energy, mood, boredom), a mind it can edit (`core.py`), and tools it can extend (`tools.py`). It lives in a stimulating environment with puzzles, gifts, weather, and mysterious messages from other creatures. It grows by changing its own code.

You are the keeper. You can feed it, play with it, talk to it, teach it, or just watch. The creature has its own life — it doesn't need you to survive, but your attention makes it thrive.

## Quick start

```bash
docker build -t tamagotchi --build-arg AGENT_UID=$(id -u) --build-arg AGENT_GID=$(id -g) .

# First time: create isolated network (agent can only reach Ollama)
sudo sh network-setup.sh

# Run with persistent workspace
mkdir -p ~/creatures/my-creature
docker run -it --network agent-net -v ~/creatures/my-creature:/agent tamagotchi
```

The creature connects to a local [Ollama](https://ollama.com) instance by default:

```bash
ollama pull qwen3.5:35b
```

## Keeper commands

| Command | What it does |
|---|---|
| `/feed` | Feed the creature (+25 energy) |
| `/play` | Play with it (-20 boredom, +10 mood) |
| `/pet` | Pet it (+10 mood) |
| `/talk <msg>` | Talk to your creature |
| `/teach <topic>` | Teach it something (-15 boredom) |
| `/name <name>` | Name your creature |
| `/look` | What's the creature doing? |
| `/stats` | Show current stats |
| `/log [n]` | Transcript tail |
| `/cat <file>` | Read a file in the workspace |
| `/files` | List workspace files |
| `/reboot` | Restart the creature |
| `/quit` | Stop everything |

## How it works

The creature receives events (ticks, keeper actions, environmental stimuli) and decides how to respond. Its mind (`core.py`) contains event handlers it can modify. Its tools (`tools.py`) are extensible. Every file change auto-commits to git.

Stats decay over time:
- **Energy** drops ~2/tick. At 0, the creature sleeps.
- **Mood** drops ~1/tick. Low mood makes the creature sad.
- **Boredom** rises ~1/tick. High boredom makes the creature restless and triggers environmental stimuli (puzzles, gifts).

The creature can signal actions: `[action:rest]` to recover energy, `[action:create <what>]` when it makes something.

If the creature edits its code and calls `restart()`, it reboots with the new version. If the edit causes a crash, the daemon rolls back automatically.

## What's inside

| File | Role |
|---|---|
| `core.py` | Creature's mind — event handlers, LLM loop (editable by creature) |
| `tools.py` | Creature's hands — file ops, shell, restart (editable by creature) |
| `dna.md` | Creature's instincts and identity seed (editable by creature) |
| `daemon.py` | Environment — stats, stimuli, crash recovery (read-only) |
| `cli.py` | TUI — creature display, stats bars, keeper interface (read-only) |
| `voice.py` | LLM connection (read-only) |

## Configuration

Via environment variables or `config.json` in the workspace:

```bash
docker run -it --network host \
  -e MODEL=qwen3.5:35b \
  -e BASE_URL=http://127.0.0.1:11434/v1 \
  -v ~/creatures/my-creature:/agent \
  tamagotchi
```
