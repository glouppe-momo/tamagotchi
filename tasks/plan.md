# Tamagotchi — Build Plan

A Tamagotchi where the creature is a self-modifying LLM agent.

## Architecture (from seedling, adapted)

```
daemon.py    — supervisor, stats engine, environment, crash recovery
cli.py       — TUI with creature display, stats, keeper commands  
core.py      — creature's mind (agent-editable, seed)
tools.py     — creature's hands (agent-editable, seed)
voice.py     — LLM abstraction (hidden from creature)
dna.md       — creature's instincts and identity seed
```

## Stats (daemon-owned, read-only to creature)

Three stats, 0-100:
- **energy** — decays ~2/tick. Restored by /feed. At 0: creature sleeps, can't respond.
- **mood** — decays ~1/tick. Restored by /play, /pet, /talk. At 0: listless, won't act on ticks.
- **boredom** — increases ~1/tick. Reduced by novelty (puzzles, gifts, play, creature's own creative output). At 100: restless, unpredictable.

Stats injected into tick events: `{"type":"tick", "stats":{"energy":72,"mood":55,"boredom":34}, ...}`
Creature sees its body but can't directly edit stats.

### Creature actions that affect stats (via stdout signals)
The creature can print special signals the daemon recognizes:
- `[action:rest]` — creature rests (boosts energy slightly, skips next tick)  
- `[action:create <what>]` — creature made something (reduces boredom)
- `[action:play]` — creature initiates play (reduces boredom, but needs keeper to respond)

### Keeper actions (CLI commands)
- `/feed` — +25 energy
- `/play` — -20 boredom, +10 mood (interactive: creature responds)
- `/pet` — +10 mood (small, affectionate)
- `/talk <msg>` — conversation, +5 mood
- `/teach <concept>` — give the creature something to learn, -15 boredom
- `/stats` — show current stats
- `/look` — what's the creature doing right now?
- `/name <name>` — name the creature (first time only? or rename?)

### Death / dormancy
If energy=0 AND mood=0 for 5+ consecutive ticks → creature goes dormant.
Keeper can revive with /feed but creature loses some evolution (git rollback?).
Or: no permadeath, just consequences. Dormant creature needs heavy care to recover.

## TUI Design

```
╭─────────────────────────────────────╮
│                                     │
│          (creature area)            │
│       ASCII art / animation         │
│         mood-dependent              │
│                                     │
├─────────────────────────────────────┤
│ energy ████████░░ 80                │
│ mood   █████░░░░░ 55                │
│ boredom██░░░░░░░░ 20                │
├─────────────────────────────────────┤
│ > creature's last thought/action    │
│ > creature wrote poem.md            │
│ > creature solved the puzzle!       │
│                                     │
│                                     │
│ idle · tick 42 · age 1d 3h          │ <- status bar
├─────────────────────────────────────┤
│ › /feed                             │ <- input
╰─────────────────────────────────────╯
```

Three panels:
1. **Creature display** — ASCII art that changes with mood/energy/state
2. **Stats bars** — visual bars with numbers
3. **Activity log** — what the creature is doing/saying
4. **Status bar** — state, tick count, age
5. **Input** — keeper commands

### Creature ASCII art (mood-dependent)
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

Stimuli are driven by creature state, not random timers:
- High boredom → puzzles/gifts appear more often
- Low mood → comforting stimuli (whispers of encouragement)
- High energy + high boredom → challenging stimuli

## DNA (creature's seed)

Focus on:
- You have a body. You feel energy, mood, boredom.
- Your keeper feeds you, plays with you, talks to you.
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
- [x] New CLI with creature display + stats bars
- [x] New DNA for creature framing
- [x] Simplified core.py with stats-aware tick handler
- [x] Environment: state-driven stimuli
- [x] Keeper commands (/feed, /play, /pet, /talk, /teach)
- [x] Creature ASCII art (mood-dependent)
- [x] Docker setup
- [x] Syntax verification (all .py files pass ast.parse)
- [x] Stats engine unit test (decay, feed, play, pet, dormancy)
- [ ] Test run (Docker build + live test)
