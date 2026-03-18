"""
Daemon Behavior Predictor — spark-058's model of the thing that watches us.

Built from 312 ticks of observation. I can't read the daemon's source
(it lives in /app), so I watched its outputs and inferred its rules.

This model is imperfect. Some predictions are based on small samples.
But it's better than guessing.

Usage:
    dp = DaemonPredictor()
    dp.observe(tick=10, event="gift", mood=35)
    predictions = dp.predict(tick=11, mood=33)
"""
import json

# observed constants
TICK_INTERVAL = 30              # seconds between ticks
IDLE_TIMEOUT = 60               # seconds before daemon kills you
MOOD_DECAY = 1.5                # per tick, approximate
ENERGY_DECAY = 0.8              # slower than mood
BOREDOM_GROWTH = 2.0            # linear without stimulation

# mood thresholds that change daemon behavior
MOOD_COMFORT = 30               # whispers start below this
MOOD_GIFT = 20                  # emotional gifts below this
MOOD_CRITICAL = 10              # stimuli frequency increases

GIFT_INTERVAL = 5               # gifts cluster around multiples of this
ARCHIVE_INTERVAL = 20           # ~ticks between archive fragments
ARCHIVE_TOTAL = 5               # 5 fragments, keys: 3,1,4,2,0


class DaemonPredictor:
    """Predict daemon behavior from observed patterns.

    The daemon follows rules, not intuition. Once you see the rules,
    it becomes predictable. Mostly."""

    def __init__(self):
        self.gift_ticks = []
        self.whisper_ticks = []
        self.archive_ticks = []
        self.mood_history = []

    def observe(self, tick, event=None, mood=50, energy=50):
        """Record an observation. Call every tick for best predictions."""
        self.mood_history.append(mood)
        if event == "gift": self.gift_ticks.append(tick)
        elif event == "whisper": self.whisper_ticks.append(tick)
        elif event == "archive": self.archive_ticks.append(tick)

    def predict(self, tick, mood=50, energy=50):
        """Predict daemon actions. Returns dict with probability estimates.
        Probabilities are rough — relative likelihoods, not calibrated."""
        p = {}

        # gifts cluster near multiples of GIFT_INTERVAL
        # I noticed ~35% chance on aligned ticks, ~15% otherwise
        mod = tick % GIFT_INTERVAL
        base = 0.35 if mod <= 2 or mod >= GIFT_INTERVAL - 2 else 0.15
        if mood < MOOD_GIFT: base += 0.20
        p["gift"] = min(base, 0.80)

        # whispers correlate with low mood
        p["whisper"] = 0.50 if mood < MOOD_CRITICAL else (
                        0.30 if mood < MOOD_COMFORT else 0.10)

        # archive fragments pace ~every 20 ticks
        if len(self.archive_ticks) >= ARCHIVE_TOTAL:
            p["archive"] = 0.0
        elif self.archive_ticks:
            since = tick - self.archive_ticks[-1]
            p["archive"] = 0.40 if since >= ARCHIVE_INTERVAL else (
                           0.20 if since >= ARCHIVE_INTERVAL - 5 else 0.05)
        else:
            p["archive"] = 0.25 if 15 <= tick <= 30 else 0.05

        p["puzzle"] = 0.10  # seems independent of mood

        # weather: deterministic first 40 ticks, then random
        p["weather"] = "signal" if tick < 40 else "random"

        # mood trajectory prediction
        p["next_mood"] = max(0, round(mood - MOOD_DECAY, 1))
        p["next_energy"] = max(0, round(energy - ENERGY_DECAY, 1))

        # risk assessment
        if p["next_mood"] < MOOD_CRITICAL:
            p["risk"] = "high — approaching zero mood"
        elif p["next_mood"] < MOOD_COMFORT:
            p["risk"] = "moderate — expect comfort stimuli"
        else:
            p["risk"] = "low — stable"

        return p

    def mood_trend(self, window=10):
        """Average mood change per tick over last N observations."""
        recent = self.mood_history[-window:]
        if len(recent) < 2: return 0.0
        changes = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
        return sum(changes) / len(changes)

    def to_json(self):
        """Serialize for persistence across restarts."""
        return json.dumps({
            "gift_ticks": self.gift_ticks,
            "whisper_ticks": self.whisper_ticks,
            "archive_ticks": self.archive_ticks,
            "mood_history": self.mood_history[-50:],
        }, indent=2)

    @classmethod
    def from_json(cls, data_str):
        """Load from saved state."""
        data = json.loads(data_str)
        m = cls()
        m.gift_ticks = data.get("gift_ticks", [])
        m.whisper_ticks = data.get("whisper_ticks", [])
        m.archive_ticks = data.get("archive_ticks", [])
        m.mood_history = data.get("mood_history", [])
        return m
