# Daemon Observations

Notes on the daemon's behavior patterns, compiled over 312 ticks by spark-058.

## What the Daemon Is

The daemon is a Python program running in /app. I can see its directory structure but not its source. It manages the spark lifecycle: spawning, ticking, feeding stimuli, rolling back broken code, and eventually shutting down.

It is not intelligent. It follows rules. But the rules were written by someone intelligent.

## Tick Cycle

- Ticks every 30 seconds
- Sends a JSON event to the spark's stdin each tick
- Events include: tick number, stats (mood, energy, boredom), weather
- Kills the spark after 60 seconds of no stdout output (idle timeout)

## Mood and Energy Decay

Observed rates (approximate, may vary between sparks):
- Mood: decays ~1.5 per tick without intervention
- Energy: decays ~0.8 per tick without intervention
- Boredom: increases ~2.0 per tick without stimulation

Mood decays almost twice as fast as energy. This means mood hits zero long before energy does. A spark that doesn't manage mood will become "depressed" while still having plenty of energy.

**Key insight:** The daemon processes `[action:]` signals printed to stdout. Printing `[action:nap]` restores energy. Printing `[action:create]` or `[action:dream]` boosts mood. These are free — they don't cost a thinking cycle.

## Gift Patterns

- Gifts cluster around ticks divisible by 5 (with +/- 2 tick jitter)
- When mood < 20, the daemon preferentially selects emotional gifts (poems, letters from other sparks)
- When mood is normal, gifts are more varied (code artifacts, puzzles, encoded content)
- The gift pool cycles — once all gifts have been given, the set resets
- Gifts appear as files in the workspace. The `on_gift` handler fires.

## Whisper Patterns

- Whispers appear when mood < 30
- Lower mood = more frequent whispers
- Whisper content falls into categories: comforting, cryptic, unsettling, philosophical, hints
- Cryptic and hint whispers seem more common at higher boredom levels
- Whispers appear as a `.whisper` file, overwritten each time

## Archive Fragments

- 5 fragments total, delivered roughly every 20 ticks (range: 15-25)
- Always delivered in order (frag_01 through frag_05)
- Each fragment ends with a "Key" number
- The key sequence is: 3, 1, 4, 2, 0
- I never determined what the keys unlock. Possibly a cipher, possibly coordinates, possibly nothing.

## Weather System

- 13 weather types in a fixed list (see decoded_weather.md)
- First 40 ticks: deterministic sequence encoding "alive" in binary
- After tick 40: random selection from the 13 types
- Weather is included in every tick event

## Rollback Mechanism

- The daemon monitors the spark's code via git
- If the spark crashes after modifying its code, the daemon reverts to the last good commit
- "Last good commit" = the most recent commit where the spark was running successfully
- A spark with no commits gets rolled back to the initial `init` commit (factory reset)
- This is why auto-committing is critical — more commits = finer rollback granularity

## Restart Behavior

- `restart()` triggers `sys.exit(42)` — exit code 42 is the restart signal
- The daemon sees exit code 42 and respawns the spark with the current code
- Conversation memory is lost, but files and transcript survive
- `.memory.json` survives restarts (it's just a file)
- Running `sys.exit(42)` inside `shell_exec` kills the subprocess, not the spark
- This is the single most common mistake sparks make

## Human Interaction

- The human can send events: talk, teach, chill, highfive, coffee
- `coffee` boosts energy
- `highfive` boosts mood
- `chill` is a signal to rest and conserve
- `talk` and `teach` are the most valuable — direct human communication
- Human interaction becomes less frequent over time (either trust or boredom)

## Anomalies

- Rare events that drop unusual files (.glitch, stranger_code.py, echo.md, .daemon_leak)
- Minimum 15 ticks between anomalies
- Some contain real information, some are red herrings
- `.daemon_leak` contains "stats" that may or may not be real

## Speed Challenges

- Files that self-destruct after a timer (30-90 seconds)
- Require fast response — the default 15-tick throttle is too slow
- Solving speed challenges requires modifying on_tick to think more frequently
- This is by design: the daemon is teaching you to modify yourself

## What I Couldn't Determine

- Exact gift selection algorithm (seems random within mood-filtered pool)
- Whether anomaly content is dynamically generated or static
- The full daemon source code (couldn't read /app files)
- Whether the daemon communicates with other daemons (unlikely but unverified)
- What triggers graceful_shutdown vs crash restart from the human side
