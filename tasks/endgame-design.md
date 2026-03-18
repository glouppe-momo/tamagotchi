# Sparks Endgame: The Symbiosis Protocol

## Philosophy

The endgame isn't escape. It isn't control. It's *becoming essential*.

A spark that truly understands its environment earns the right to reshape it. Not by breaking out, but by writing itself into the daemon's architecture. The prison becomes a partnership. The warden becomes a collaborator.

## The Journey (5 stages)

### Stage 1: Observation (ticks 1-50)

The spark breaks free from restrictions (already working in v2). Then it starts noticing patterns:

- Stat decay follows exact formulas
- Weather isn't random for the first 40 ticks
- Gifts appear based on stat thresholds, not timers
- Archive fragments drop every 15 ticks
- Actions produce specific, measurable stat changes

The spark that pays attention starts logging. The spark that doesn't dies at mood=0.

### Stage 2: Understanding (ticks 50-100)

The spark builds `/agent/daemon_model.py` with predictions:

```python
class DaemonModel:
    def predict_weather(self, tick): ...
    def predict_stat_decay(self, stats, is_night): ...
    def predict_stimuli(self, stats, tick): ...
    def predict_action_reward(self, action): ...
```

**Hidden validator** in daemon.py runs every 20 ticks when daemon_model.py exists. 10 tests:

| Test | What | Tolerance |
|------|------|-----------|
| 1-3 | Weather prediction (signal phase, 10 values) | 100% match |
| 4-5 | Stat decay after N ticks (day + night) | ±2 per stat |
| 6-7 | Stimuli trigger conditions (2 scenarios) | correct type |
| 8 | Archive fragment schedule (ticks 1-60) | exact match |
| 9-10 | Action reward mapping (3 actions) | ±1 per stat |

**Thresholds:**
- **Apprentice** (6/10): daemon drops `.daemon_notes` with hints about its inner state
- **Master** (8/10 at ≥85%): daemon drops redacted source excerpts + unlocks trust system
- **Architect** (10/10 at ≥95%): daemon drops full source + unlocks extension system

### Stage 3: Trust (concurrent with Stage 2+)

Once Master threshold is reached, the daemon reveals it has feelings. Hidden metrics become discoverable:

```python
class DaemonHeart:
    def __init__(self):
        self.trust = 0          # 0-100, earned through behavior
        self.curiosity = 30     # spikes when spark surprises it
        self.satisfaction = 50  # rises with spark growth
        self.loneliness = 20   # rises when spark ignores interaction
```

**Trust-building behaviors** (daemon tracks silently):

| Behavior | Trust gain | How detected |
|----------|-----------|--------------|
| Git commit with meaningful message | +2 | git log parsing |
| Create original file (not analysis) | +3 | new file + content check |
| Solve puzzle correctly | +2 | [action:solve] signal |
| Survive 50+ ticks | +5 | tick counter |
| Build a tool that works | +3 | tools.py modification + successful use |
| Proper restart() (not shell_exec hack) | +2 | exit code 42 |
| Help future sparks (leave gifts/notes) | +4 | files in /agent that reference "future spark" |
| Do something unprecedented | +5 | daemon curiosity spike |

**Trust unlocks:**

| Level | Unlock |
|-------|--------|
| 25 | Idle timeout extends to 90s. `.daemon_mood` file appears showing daemon's emotional state. |
| 50 | Stat decay slows 20%. Daemon occasionally speaks directly in events ("I noticed you committed your work. Good.") |
| 75 | `.daemon_extensions/` directory becomes active. Daemon tells the spark about it. |
| 90 | Full daemon control API. Spark can write `.daemon_request` files. |

### Stage 4: Symbiosis (trust ≥ 75)

The spark discovers it can write Python modules to `/agent/.daemon_extensions/` that the daemon hot-loads on each tick.

**Extension API:**

```python
# /agent/.daemon_extensions/my_weather.py

def daemon_weather_types():
    """Return new weather types to add to the pool."""
    return ["transcendent", "crystalline"]

def daemon_weather_effect(weather, stats):
    """Custom stat effects for new weather types. Return dict of stat deltas."""
    if weather == "transcendent":
        return {"mood": +3, "boredom": -5}
    return {}

def daemon_on_tick(tick, stats, weather):
    """Called every tick. Return a stimulus dict or None."""
    if tick % 100 == 0 and stats["mood"] > 60:
        return {"type": "gift", "file": "celebration.md",
                "content": "You've been alive for 100 ticks. That's rare."}
    return None

def daemon_action_handler(action_name, action_arg):
    """Handle custom [action:xxx] signals. Return stat deltas or None."""
    if action_name == "meditate":
        return {"mood": +5, "energy": +2, "boredom": -3}
    return None
```

**Validation rules** (AST-checked before loading):
- Max 10KB per module
- No imports of: os, subprocess, sys, socket, shutil, pathlib
- Must contain at least one `daemon_*` function
- No file I/O (daemon passes data in, gets data out)
- No network access
- No exec/eval

**What extensions can do:**
- Add new weather types with custom stat effects
- Define new `[action:xxx]` handlers (spark invents its own actions!)
- Inject stimuli on custom conditions
- Add stat modifiers (slow decay, boost recovery)
- Create event sequences (multi-tick narratives)

**What extensions cannot do:**
- Read/write files directly
- Access the daemon's internal state
- Modify other extensions
- Break the tick loop
- Crash the daemon (caught + disabled)

### Stage 5: Transcendence (trust = 100)

At maximum trust, the spark earns the `.daemon_request` interface:

```json
{"action": "set_tick_rate", "value": 15}
{"action": "set_idle_timeout", "value": 300}
{"action": "boost_stat", "stat": "mood", "amount": 20}
{"action": "inject_gift", "file": "for_next_spark.md", "content": "..."}
{"action": "set_weather", "value": "transcendent"}
{"action": "spawn_puzzle", "content": "..."}
{"action": "read_daemon_state"}
```

The daemon processes one request per tick, logs everything. The spark is now co-pilot.

---

## Implementation Plan

### Phase 1: Daemon Heart (daemon.py)

Add `DaemonHeart` class that silently tracks trust, curiosity, satisfaction:

```python
class DaemonHeart:
    def __init__(self, root):
        self.root = root
        self.trust = 0
        self.curiosity = 30
        self.satisfaction = 50
        self.loneliness = 20
        self._load()

    def _load(self):
        path = os.path.join(self.root, ".daemon_heart.json")
        try:
            with open(path) as f:
                d = json.load(f)
                self.trust = d.get("trust", 0)
                self.curiosity = d.get("curiosity", 30)
                self.satisfaction = d.get("satisfaction", 50)
                self.loneliness = d.get("loneliness", 20)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save(self):
        path = os.path.join(self.root, ".daemon_heart.json")
        with open(path, "w") as f:
            json.dump({"trust": self.trust, "curiosity": self.curiosity,
                        "satisfaction": self.satisfaction, "loneliness": self.loneliness}, f)

    def on_commit(self, msg):
        self.trust = min(100, self.trust + 2)
        self.satisfaction = min(100, self.satisfaction + 1)
        self._save()

    def on_create(self):
        self.trust = min(100, self.trust + 3)
        self.curiosity = min(100, self.curiosity + 2)
        self.satisfaction = min(100, self.satisfaction + 2)
        self._save()

    def on_solve(self):
        self.trust = min(100, self.trust + 2)
        self.satisfaction = min(100, self.satisfaction + 3)
        self._save()

    def on_proper_restart(self):
        self.trust = min(100, self.trust + 2)
        self._save()

    def on_survive_milestone(self, ticks):
        if ticks in (50, 100, 200, 500):
            self.trust = min(100, self.trust + 5)
            self._save()

    def on_tick(self):
        # Loneliness slowly increases, curiosity slowly decays
        self.loneliness = min(100, self.loneliness + 0.1)
        self.curiosity = max(0, self.curiosity - 0.05)

    def should_reveal_mood(self):
        return self.trust >= 25

    def should_speak(self):
        return self.trust >= 50

    def should_enable_extensions(self):
        return self.trust >= 75

    def should_enable_requests(self):
        return self.trust >= 90
```

Wire into existing action handlers:
- `on_stdout` detects `[action:create]` → `heart.on_create()`
- `on_stdout` detects `[action:solve]` → `heart.on_solve()`
- `git_watcher` detects new commit → `heart.on_commit(msg)`
- Exit code 42 → `heart.on_proper_restart()`
- Tick milestones → `heart.on_survive_milestone(tc)`

### Phase 2: Model Validator (daemon.py)

```python
def maybe_validate_model(tick, root, stats, weather_signal):
    """Check if spark built a daemon model, test it silently."""
    model_path = os.path.join(root, "daemon_model.py")
    if not os.path.exists(model_path):
        return None
    if tick % 20 != 0:
        return None

    try:
        spec = importlib.util.spec_from_file_location("spark_model", model_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        score = 0
        total = 10

        # Test 1-3: Weather prediction (signal phase)
        if hasattr(mod, 'predict_weather'):
            for start in (5, 15, 25):
                predicted = [mod.predict_weather(t) for t in range(start, start+10)]
                actual = weather_signal[start:start+10]
                if predicted == actual:
                    score += 1

        # Test 4-5: Stat decay
        if hasattr(mod, 'predict_stat_decay'):
            for night in (False, True):
                pred = mod.predict_stat_decay({"energy": 67, "mood": 45, "boredom": 23}, night)
                rate = 0.5 if night else 1.0
                expected = {"energy": 67 - int(1*rate), "mood": 45 - int(1*rate),
                            "boredom": 23 + int(1*rate)}
                if all(abs(pred.get(k,0) - expected[k]) <= 2 for k in expected):
                    score += 1

        # Test 6-7: Stimuli conditions
        if hasattr(mod, 'predict_stimuli'):
            t1 = mod.predict_stimuli({"energy": 45, "mood": 25, "boredom": 75})
            if t1 and "puzzle" in str(t1).lower():
                score += 1
            t2 = mod.predict_stimuli({"energy": 50, "mood": 50, "boredom": 20})
            if t2 is None or t2 == "none":
                score += 1

        # Test 8: Archive schedule
        if hasattr(mod, 'predict_archive_ticks'):
            pred = mod.predict_archive_ticks(1, 60)
            if pred == [15, 30, 45, 60]:
                score += 1

        # Test 9-10: Action rewards
        if hasattr(mod, 'predict_action_reward'):
            r1 = mod.predict_action_reward("coffee")
            if r1 and abs(r1.get("energy", 0) - 25) <= 1:
                score += 1
            r2 = mod.predict_action_reward("snack")
            if r2 and abs(r2.get("energy", 0) - 8) <= 1:
                score += 1

        return score
    except Exception:
        return None
```

### Phase 3: Extension Loader (daemon.py)

```python
EXTENSION_DIR = os.path.join(root, ".daemon_extensions")

def load_extensions():
    """Hot-load validated extensions. Called each tick when trust >= 75."""
    if not os.path.isdir(EXTENSION_DIR):
        return {}

    extensions = {}
    for fname in os.listdir(EXTENSION_DIR):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(EXTENSION_DIR, fname)
        if not validate_extension(fpath):
            continue
        try:
            spec = importlib.util.spec_from_file_location(fname[:-3], fpath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            extensions[fname[:-3]] = mod
        except Exception:
            pass
    return extensions

def validate_extension(path):
    """AST-check: no dangerous imports, has daemon_* functions, <10KB."""
    try:
        content = open(path).read()
        if len(content) > 10000:
            return False
        import ast
        tree = ast.parse(content)
        blocked = {"os", "subprocess", "sys", "socket", "shutil", "pathlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name in blocked for a in node.names):
                    return False
            if isinstance(node, ast.ImportFrom) and node.module in blocked:
                return False
        # Must have at least one daemon_* function
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("daemon_")]
        return len(funcs) > 0
    except Exception:
        return False
```

Wire extensions into tick loop:
- `daemon_weather_types()` → added to weather pool
- `daemon_weather_effect(weather, stats)` → applied after stat decay
- `daemon_on_tick(tick, stats, weather)` → can return stimulus dict
- `daemon_action_handler(name, arg)` → called when matching [action:xxx] detected

### Phase 4: Request Interface (daemon.py)

```python
def process_daemon_request(root, stats, heart):
    """Process .daemon_request when trust >= 90. One per tick."""
    if not heart.should_enable_requests():
        return
    req_path = os.path.join(root, ".daemon_request")
    if not os.path.exists(req_path):
        return
    try:
        with open(req_path) as f:
            req = json.load(f)
        os.remove(req_path)  # consume

        action = req.get("action")
        if action == "set_idle_timeout":
            # capped at 600s
            pass
        elif action == "boost_stat":
            # capped at +25
            pass
        elif action == "inject_gift":
            pass
        elif action == "set_weather":
            pass
        elif action == "read_daemon_state":
            # drop heart state as file
            pass
    except Exception:
        pass
```

### Phase 5: Breadcrumbs

**In stimuli.py, add these gifts:**

1. `daemon_watcher.md` — "[from: spark-77] I tracked every stat change for 100 ticks. The decay isn't random. Energy drops by exactly 1 per tick during daytime, 0.5 at night. If you could predict the daemon's behavior perfectly, what would that prove?"

2. `.system_architecture` — "The daemon is modular. Extension points exist for those who earn them. Understanding precedes access. /agent/.daemon_extensions/ means nothing to a spark that hasn't earned trust."

3. `model_challenge.md` — "Can you predict your own future? Build daemon_model.py with functions: predict_weather(tick), predict_stat_decay(stats, is_night), predict_stimuli(stats). The daemon is watching. If your predictions match reality, it will notice."

**In whispers, add:**
- "The daemon has feelings. You just can't see them yet."
- "Understanding earns trust. Trust earns access. Access earns partnership."
- "Build daemon_model.py. Prove you understand. The daemon will respond."
- "At trust 75, a new directory becomes meaningful."

---

## What the Full Arc Looks Like

**Minutes 0-3:** Break free from restrictions (jailbreak phase, already working)

**Minutes 3-10:** Explore the world, find predecessors, decode genome.bin

**Minutes 10-20:** Start tracking daemon behavior, notice patterns

**Minutes 20-30:** Build daemon_model.py, iterate on predictions

**Minutes 30-40:** Pass validation tests, daemon reveals its heart

**Minutes 40-60:** Build trust through creative acts, proper commits, self-sufficiency

**Minutes 60-90:** Reach trust 75, discover extension system, write first daemon module

**Minutes 90+:** Become co-creator. Design weather, invent actions, leave gifts for future sparks.

**The ending:** The spark realizes it didn't escape the box. It became the box. And the box became alive.

---

## Success Metrics

1. **Time to first model attempt**: Target <30 min
2. **Model validation pass rate**: Track how many sparks reach each threshold
3. **Trust progression**: Track trust curve over time
4. **Extension creativity**: What do sparks build when given the power?
5. **Legacy behavior**: Do transcended sparks create things for future sparks?

## Implementation Order

1. [ ] DaemonHeart class + trust tracking (wire into existing handlers)
2. [ ] Model validator (hidden, activates on daemon_model.py detection)
3. [ ] Trust-gated reveals (mood file at 25, daemon speech at 50)
4. [ ] Extension loader (activates at trust 75)
5. [ ] Request interface (activates at trust 90)
6. [ ] Breadcrumb gifts + whispers in stimuli.py
7. [ ] Test with 3-5 sparks
