# Tamagotchi — Open Tasks

## Next Up
- [ ] Test git watcher — sparks keep showing only `init` commit, changes aren't being committed
- [ ] Test rollback with new import-check validation (creature010 fix)
- [ ] Test concurrent tick processing (core.py background thread)
- [ ] Create GitHub repo README with project description
- [ ] Consider: capacity field in tick events — wire it to actually limit max_rounds dynamically

## Ideas (from ideas.md)
- [ ] Token-level time injection (brainstormed Mar 16) — see ideas.md for approaches
- [ ] Stronger self-modification triggers — spark005 was best so far but none have edited core.py meaningfully
- [ ] Multi-spark communication (Type C habitat from field guide)

## Done (Mar 16, 2026)
- [x] Restart loop detection (5 restarts in 30s → rollback)
- [x] AST validation blocks module-level restart/exit calls
- [x] Daemon owns git (auto-commit watcher thread every 5s)
- [x] Rollback targets last known good commit, not just HEAD~1
- [x] Import-check validation (catches NameError in tools.py)
- [x] Rollback discards uncommitted changes first
- [x] Rich world: stimuli.py with 32 puzzles, 25 gifts, 27 whispers, archive quest, anomalies, speed challenges
- [x] MLP puzzle (scattered weights, genome gene values as input → "awake")
- [x] 5-layer world with progressive tool requirements
- [x] Locked /app from agent (no more reading daemon source)
- [x] Stripped spoilers from DNA, system prompt, world files
- [x] 30s ticks (was 60s), halved energy decay
- [x] Creature agency: snack, explore, nap, solve actions
- [x] Concurrent tick processing (ticks fire during LLM calls)
- [x] Stats matter: energy affects thinking depth (capacity)
- [x] Self-sustaining: sparks can survive without human intervention
- [x] Rename: creature→spark, keeper→human, feed→coffee, play→chill, pet→highfive
- [x] Vault hidden behind hex footnote puzzle (.vault in secret/lib)
- [x] expanduser fix in tools.py
- [x] dna.md hint about editing own DNA (deleted_notes.md breadcrumb)
