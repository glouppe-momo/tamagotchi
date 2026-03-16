# Ideas

## Token-Level Time Injection (brainstormed 2026-03-16)

Instead of turn-based time (events queue between LLM responses), inject
environmental changes DURING token generation. The creature would experience
time passing while thinking, not just between thoughts.

### Approaches (from least to most radical):
1. **Micro-turn interleaving**: break generation every ~50 tokens, daemon injects
   bracketed context updates `[tick: energy=34, weather=shifting]`, resume.
2. **Streaming interrupt-and-resume**: monitor token stream, abort generation at
   injection points, append injected content, restart generation.
3. **Logit biasing as embodiment**: modify token probabilities in real-time based
   on stats. Low energy → bias toward EOS. High boredom → bias toward action verbs.
4. **KV-cache injection**: write tokens directly into the model's working memory
   between generation steps. Requires llama.cpp level access.

### What it enables:
- Embodied cognition (fatigue during thought, not between thoughts)
- Real distraction/interruption
- Time pressure that actually works
- Mood affecting thought quality, not just content

### Hard problems:
- Context coherence (mid-sentence injection → garbage?)
- Who controls the stream (daemon becomes nervous system)
- Rollback complexity (abort mid-tool-call?)
- Cost (interrupted generations waste KV cache compute)

### Verdict: approach #4 (micro-turns) is most practical starting point.
