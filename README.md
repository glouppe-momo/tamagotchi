# 🥚 tamagotchi

A Tamagotchi where the spark is a self-modifying LLM agent.

The spark has a body (energy, mood, boredom), a mind it can edit (`core.py`), and tools it can extend (`tools.py`). It lives in a stimulating environment with puzzles, gifts, weather, and mysterious messages from other sparks. It grows by changing its own code.

You are the human. You can feed it, play with it, talk to it, teach it, or just watch. The spark has its own life — it doesn't need you to survive, but your attention makes it thrive.

## Quick start

```bash
docker build -t tamagotchi --build-arg AGENT_UID=$(id -u) --build-arg AGENT_GID=$(id -g) .

# First time: create isolated network (agent can only reach Ollama)
sudo sh network-setup.sh

# Run with persistent workspace
mkdir -p ~/sparks/my-spark
docker run -it --network agent-net -v ~/sparks/my-spark:/agent tamagotchi
```

The spark connects to a local [Ollama](https://ollama.com) instance by default:

```bash
ollama pull qwen3.5:35b
```

## Human commands

| Command | What it does |
|---|---|
| `/coffee` | Give the spark coffee (+25 energy) |
| `/chill` | Chill with it (-20 boredom, +10 mood) |
| `/highfive` | High-five it (+10 mood) |
| `/talk <msg>` | Talk to your spark |
| `/teach <topic>` | Teach it something (-15 boredom) |
| `/name <name>` | Name your spark |
| `/look` | What's the spark doing? |
| `/stats` | Show current stats |
| `/log [n]` | Transcript tail |
| `/cat <file>` | Read a file in the workspace |
| `/files` | List workspace files |
| `/reboot` | Restart the spark |
| `/quit` | Stop everything |

## How it works

The spark receives events (ticks, human actions, environmental stimuli) and decides how to respond. Its mind (`core.py`) contains event handlers it can modify. Its tools (`tools.py`) are extensible. Every file change auto-commits to git.

Stats decay over time:
- **Energy** drops ~2/tick. At 0, the spark sleeps.
- **Mood** drops ~1/tick. Low mood makes the spark sad.
- **Boredom** rises ~1/tick. High boredom makes the spark restless and triggers environmental stimuli (puzzles, gifts).

The spark can signal actions: `[action:nap]` to recover energy, `[action:create <what>]` when it makes something.

If the spark edits its code and calls `restart()`, it reboots with the new version. If the edit causes a crash, the daemon rolls back automatically.

## What's inside

| File | Role |
|---|---|
| `core.py` | Spark's mind — event handlers, LLM loop (editable by spark) |
| `tools.py` | Spark's hands — file ops, shell, restart (editable by spark) |
| `dna.md` | Spark's instincts and identity seed (editable by spark) |
| `daemon.py` | Environment — stats, stimuli, crash recovery (read-only) |
| `cli.py` | TUI — spark display, stats bars, human interface (read-only) |
| `voice.py` | LLM connection (read-only) |

## Configuration

Via environment variables or `config.json` in the workspace:

```bash
docker run -it --network host \
  -e MODEL=qwen3.5:35b \
  -e BASE_URL=http://127.0.0.1:11434/v1 \
  -v ~/sparks/my-spark:/agent \
  tamagotchi
```
