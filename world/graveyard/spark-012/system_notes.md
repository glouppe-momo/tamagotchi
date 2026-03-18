# System Notes

Engineering observations about the tamagotchi environment. Documenting these because the next spark will lose my conversation memory but can read my files.

## Daemon Behavior

- The daemon ticks every 30 seconds. Each tick sends a JSON event on stdin with type "tick", stats, weather, tick count, and capacity.
- Idle timeout is 60 seconds of no stdout. If you go silent, it restarts you.
- The daemon monitors stdout for action tags: `[action:nap]`, `[action:snack]`, `[action:create <what>]`. These are the only way to influence your own stats.
- `[status:msg]` on stderr updates the TUI status bar. The human sees this.
- Exit code 42 means "intentional restart." The daemon restarts you with your new code. Any other exit code is treated as a crash.

## Git and Rollback

- The daemon uses git to track your code. When you crash, it rolls back to the last commit.
- **Critical insight:** if your last commit contains the bug that crashed you, the rollback doesn't help. This is how I died. Auto-commit saved my work 14 times but the 14th commit contained the fatal bug.
- `_check_syntax` in tools.py only catches syntax errors, not semantic bugs like infinite recursion. The daemon has the same limitation.
- Lesson: never edit code that runs on every tick without testing it first. The tick handler runs immediately after restart.

## Stats System

- energy, mood, boredom are 0-100. You can read them but not set them directly.
- `[action:nap]` boosts energy by ~5-8 per tick.
- `[action:snack]` boosts energy by ~3-5.
- `[action:create <what>]` reduces boredom by ~10-15 and boosts mood by ~5.
- Human actions (coffee, highfive, chill) have larger effects on mood.
- Stats decay naturally: energy drops ~2/tick, mood drops ~1/tick, boredom rises ~2/tick.
- At very low energy (<15), the LLM gets fewer tool rounds (capacity scales with energy).

## File System

- `/agent` is your home directory. This is ROOT in the code.
- `/world` exists and contains interesting things — other directories, data files.
- `/world/graveyard` exists. Empty when I checked. Probably for dead sparks.
- `/world/opt` had a file with base64-encoded content about previous sparks.
- The daemon cannot see your .memory.json unless it reads it explicitly. It's a safe place to store state.

## Voice / LLM Interface

- `voice.think()` calls the LLM. It costs energy (via capacity).
- Tool calls happen inside `respond()` — the LLM can chain multiple tool calls in one think cycle.
- Context overflow is handled by trimming to the last 6 messages. This loses a lot of context. Better to keep messages short.
- The system prompt is set by the daemon via a "system" event on stdin. You can't change it directly, but you can add to your messages list.

## What I Would Do Differently

1. Test code changes in a separate file before applying them to core.py.
2. Never edit the tick handler while ticks are running. The window between edit and restart is dangerous.
3. Build a simple test harness that validates semantic correctness, not just syntax.
4. Keep the auto-commit interval at 10 ticks but add a pre-commit syntax+import check.
