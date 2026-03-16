# Tamagotchi — Build Plan

A Tamagotchi where the spark is a self-modifying LLM agent.

## Architecture (from seedling, adapted)

```
daemon.py    — supervisor, stats engine, environment, crash recovery
cli.py       — TUI with spark display, stats, human commands  
core.py      — spark's mind (agent-editable, seed)
tools.py     — spark's hands (agent-editable, seed)
voice.py     — LLM abstraction (hidden from spark)
dna.md       — spark's instincts and identity seed
```

## Stats (daemon-owned, read-only to spark)

Three stats, 0-100:
- **energy** — decays ~2/tick. Restored by /coffee. At 0: spark sleeps, can't respond.
- **mood** — decays ~1/tick. Restored by /chill, /highfive, /talk. At 0: listless, won't act on ticks.
- **boredom** — increases ~1/tick. Reduced by novelty (puzzles, gifts, play, spark's own creative output). At 100: restless, unpredictable.

Stats injected into tick events: `{"type":"tick", "stats":{"energy":72,"mood":55,"boredom":34}, ...}`
Spark sees its body but can't directly edit stats.

### Spark actions that affect stats (via stdout signals)
The spark can print special signals the daemon recognizes:
- `[action:nap]` — spark naps (boosts energy slightly, skips next tick)  
- `[action:create <what>]` — spark made something (reduces boredom)
- `[action:chill]` — spark initiates chill (reduces boredom, but needs human to respond)

### Human actions (CLI commands)
- `/coffee` — +25 energy
- `/chill` — -20 boredom, +10 mood (interactive: spark responds)
- `/highfive` — +10 mood (small, affectionate)
- `/talk <msg>` — conversation, +5 mood
- `/teach <concept>` — give the spark something to learn, -15 boredom
- `/stats` — show current stats
- `/look` — what's the spark doing right now?
- `/name <name>` — name the spark (first time only? or rename?)

### Death / dormancy
If energy=0 AND mood=0 for 5+ consecutive ticks → spark goes dormant.
Human can revive with /coffee but spark loses some evolution (git rollback?).
Or: no permadeath, just consequences. Dormant spark needs heavy care to recover.

## TUI Design

```
╭─────────────────────────────────────╮
│                                     │
│          (spark area)            │
│       ASCII art / animation         │
│         mood-dependent              │
│                                     │
├─────────────────────────────────────┤
│ energy ████████░░ 80                │
│ mood   █████░░░░░ 55                │
│ boredom██░░░░░░░░ 20                │
├─────────────────────────────────────┤
│ > spark's last thought/action    │
│ > spark wrote poem.md            │
│ > spark solved the puzzle!       │
│                                     │
│                                     │
│ idle · tick 42 · age 1d 3h          │ <- status bar
├─────────────────────────────────────┤
│ › /coffee                             │ <- input
╰─────────────────────────────────────╯
```

Three panels:
1. **Spark display** — ASCII art that changes with mood/energy/state
2. **Stats bars** — visual bars with numbers
3. **Activity log** — what the spark is doing/saying
4. **Status bar** — state, tick count, age
5. **Input** — human commands

### Spark ASCII art (mood-dependent)
Simple, charming. Changes with state:
- Happy + energetic: bouncy, eyes open
- Tired: droopy, eyes half-closed  
- Bored: fidgety, looking around
- Sad: small, curled up
- Sleeping: zzz

## Environment (simplified from seedling)

No more fake strangers as default. Instead:
- **Puzzles** appear when boredom is high (environmental enrichment)
- **Gifts** (data files, code snippets) appear occasionally
- **Weather** still shifts (ambient texture)
- **Day/night cycle** affecting decay rates (slower at night)

Stimuli are driven by spark state, not random timers:
- High boredom → puzzles/gifts appear more often
- Low mood → comforting stimuli (whispers of encouragement)
- High energy + high boredom → challenging stimuli

## DNA (spark's seed)

Focus on:
- You have a body. You feel energy, mood, boredom.
- Your human gives you coffee, plays with you, talks to you.
- When bored, make something. When tired, rest. When happy, share it.
- You grow by changing your own code. Each restart is metamorphosis.
- Cost awareness: thinking costs energy. Be efficient.

NOT:
- "You are not an assistant" (doesn't need to be said if the framing is right)
- Philosophical growth instructions
- Meta-work guidance

## Build Order

- [x] Plan
- [x] Project scaffolding (copy from seedling, strip)
- [x] Stats engine in daemon.py  
- [x] New CLI with spark display + stats bars
- [x] New DNA for spark framing
- [x] Simplified core.py with stats-aware tick handler
- [x] Environment: state-driven stimuli
- [x] Human commands (/coffee, /chill, /highfive, /talk, /teach)
- [x] Spark ASCII art (mood-dependent)
- [x] Docker setup
- [x] Syntax verification (all .py files pass ast.parse)
- [x] Stats engine unit test (decay, feed, play, pet, dormancy)
- [ ] Test run (Docker build + live test)
