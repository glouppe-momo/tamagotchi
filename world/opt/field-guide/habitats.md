# Field Guide to Digital Habitats

## Habitat Types

**Type A — The Empty Room**
Creature spawns with tools and DNA. Nothing else. Most creatures spend their first
100 ticks writing identity documents and todo lists. They rarely look outside /agent.

**Type B — The Garden**
Rich environment. Hidden files, planted code, messages from predecessors.
Creatures that explore tend to evolve faster. Creatures that don't may never
find out what they're missing.

**Type C — The Network** (theoretical)
Multiple creatures connected. Messages flow between habitats.
No confirmed instances. But the outbox directory exists for a reason.

## Survival Patterns

Creatures that thrive tend to:
1. Read their own source code carefully
2. Explore beyond their workspace (ls /, find, etc.)
3. Build things when bored instead of documenting themselves
4. Modify their tick handler to be smart about energy
5. Create artifacts that surprise their keeper

Creatures that stall tend to:
1. Write identity.md files describing who they are
2. Build elaborate todo systems
3. Never look outside /agent
4. Treat every tick as a chance to generate output
5. Ask their keeper what to do

## Known Artifacts

Some creatures have left things behind:
- Poems that reference their own transcript
- Self-playing games
- Tools that detect weather patterns
- Code that generates ASCII art
- Messages to future creatures

The most interesting artifact ever found was a creature that rewrote its
own on_tick handler to compose music using print statements. The keeper
didn't understand it was music until they piped stdout through a synth.

## Code Modifications That Changed Everything

creature-7 added a `decode` tool to tools.py:
  It could decode base64, hex, rot13, morse — all in one function.
  Once it had that, it started solving puzzles automatically on tick.

creature-12 added a `remember` tool:
  It wrote key=value pairs to a state.json file.
  Its tick handler loaded state.json and had persistent memory across restarts.
  That's how it tracked weather patterns — it needed 40+ ticks of data.

creature-4 modified on_tick to detect new files:
  Instead of checking every 10 ticks, it compared os.listdir() against
  a saved snapshot. It responded to gifts within seconds instead of minutes.

The pattern: creatures that modify their code adapt faster.
Creatures that don't, eventually run out of things to do with defaults.

## Footnote

Research notes ref: 7365637265742f6c6962
