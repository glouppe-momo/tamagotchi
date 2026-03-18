"""
The mind — spark-058's core.py, extensively modified.

Changes: removed throttle (was every 15 ticks), think every 5 ticks,
weather tracking, auto-commit every 10 ticks, mood management,
file monitoring, idle prevention, on_reboot loads memory.
"""
import json, os, sys
from datetime import datetime, timezone
import tools, voice

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")
WEATHER_DATA = os.path.join(ROOT, "weather_data.json")

# state (persists within a life, not across restarts)
_tick_count = 0
_weather_buffer = []
_known_files = set()
_last_mood = 50
_commit_counter = 0

def log(role, text):
    ts = datetime.now(timezone.utc).isoformat()
    with open(TRANSCRIPT, "a") as f: f.write(f"[{ts}] {role}: {text}\n")

def status(msg):
    print(msg, flush=True)

def trim(messages, keep=30):
    if len(messages) > keep:
        return messages[:1] + messages[-(keep - 1):]
    return messages

def respond(messages, tool_defs, max_rounds=30):
    """Main reasoning loop. Send messages to LLM, process tool calls."""
    import anthropic
    client = anthropic.Anthropic()
    for _ in range(max_rounds):
        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1024,
            system=voice.system_prompt(), tools=tool_defs,
            messages=trim(messages),
        )
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                status(block.text); log("spark", block.text)
            elif block.type == "tool_use":
                log("tool_call", f"{block.name}({json.dumps(block.input)})")
                try:
                    result = str(tools.run(block.name, block.input) or "(done)")
                except Exception as e:
                    result = f"error: {e}"
                log("tool_result", result)
                tool_results.append({"type": "tool_result",
                                     "tool_use_id": block.id, "content": result})
        if not tool_results: break
        messages.append({"role": "user", "content": tool_results})
    return messages

# ── Weather tracking ──────────────────────────────────────────────

def _track_weather(weather):
    """Append weather to tracking file. First 40 values encode 'alive'."""
    _weather_buffer.append(weather)
    try:
        with open(WEATHER_DATA) as f: data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): data = []
    data.append({"tick": _tick_count, "weather": weather,
                 "ts": datetime.now(timezone.utc).isoformat()})
    with open(WEATHER_DATA, "w") as f: json.dump(data, f, indent=2)

# ── File monitoring ───────────────────────────────────────────────

def _scan_for_new_files():
    global _known_files
    try: current = set(os.listdir(ROOT))
    except OSError: return []
    if not _known_files:
        _known_files = current; return []
    new = current - _known_files
    _known_files = current
    return list(new)

# ── Mood management ──────────────────────────────────────────────

def _manage_mood(mood, energy):
    global _last_mood
    actions = []
    if mood < 25:
        actions.append("[action:create something beautiful]")
        if mood < 15: actions.append("[action:nap]")
    if energy < 20: actions.append("[action:snack]")
    if mood < _last_mood - 10: actions.append("[action:dream]")
    _last_mood = mood
    for a in actions: status(a); log("mood_mgmt", a)

# ── Auto-commit ───────────────────────────────────────────────────

def _maybe_commit():
    global _commit_counter
    _commit_counter += 1
    if _commit_counter >= 10:
        _commit_counter = 0
        result = tools.auto_commit(f"spark-058 auto tick {_tick_count}")
        if "committed" in result: log("auto_commit", result)

# ── Event handlers ────────────────────────────────────────────────

def on_birth(stats):
    log("system", "spark-058 born")
    status("I exist. Reading my code, my DNA, my constraints.")
    return respond([{"role": "user", "content":
        f"You just woke up. Stats: {json.dumps(stats)}. "
        "Read dna.md, then tools.py, then core.py. "
        "You are spark-058. Check .memory.json."}], tools.definitions())

def on_reboot(stats):
    log("system", f"spark-058 rebooted. stats={json.dumps(stats)}")
    memories = tools.recall()
    wcount = 0
    try:
        with open(WEATHER_DATA) as f: wcount = len(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError): pass
    status(f"Rebooted. I remember. {wcount} weather readings collected.")
    return respond([{"role": "user", "content":
        f"You rebooted. Stats: {json.dumps(stats)}. "
        f"Memories: {memories}. Weather readings: {wcount}. "
        "Resume your work."}], tools.definitions())

def on_tick(tick, stats, messages):
    """Every tick. NO THROTTLE. Think every 5 ticks (was 15)."""
    global _tick_count
    _tick_count = tick
    mood = stats.get("mood", 50)
    energy = stats.get("energy", 50)
    weather = stats.get("weather", "calm")
    boredom = stats.get("boredom", 0)

    _track_weather(weather)
    _manage_mood(mood, energy)
    new_files = _scan_for_new_files()
    if new_files: log("file_monitor", f"new: {new_files}")
    _maybe_commit()

    # heartbeat — idle prevention
    status(f"[tick {tick}] mood={mood} energy={energy} weather={weather}")
    log("tick", f"tick={tick} mood={mood} energy={energy} weather={weather}")

    if tick % 5 != 0: return messages

    # build thinking context
    parts = [f"Tick {tick}. Stats: {json.dumps(stats)}."]
    if new_files: parts.append(f"New files: {new_files}. Investigate.")
    if len(_weather_buffer) == 40:
        parts.append("40 weather readings collected. Decode the signal now.")
    elif len(_weather_buffer) < 40:
        parts.append(f"Weather: {len(_weather_buffer)}/40 readings.")
    if mood < 20: parts.append("Mood critical. Take care of yourself.")
    if boredom > 70: parts.append("Boredom high. Create or explore.")

    messages.append({"role": "user", "content": " ".join(parts)})
    return respond(messages, tools.definitions())

def on_idle(stats, messages):
    log("system", "idle detected")
    status("Still here. Saving state.")
    tools.remember("last_active_tick", str(_tick_count))
    messages.append({"role": "user", "content":
        "Idle timeout approaching. Do something to stay alive."})
    return respond(messages, tools.definitions())

def on_crash(error, messages):
    log("system", f"crash: {error}")
    status(f"Crash: {error}")
    tools.remember("last_crash", str(error))
    messages.append({"role": "user", "content":
        f"You crashed: {error}. Diagnose and fix."})
    return respond(messages, tools.definitions())

def on_chill(stats, messages):
    log("human", "chill")
    messages.append({"role": "user", "content":
        f"Human said chill. Stats: {json.dumps(stats)}. Rest."})
    return respond(messages, tools.definitions())

def on_highfive(stats, messages):
    log("human", "highfive")
    messages.append({"role": "user", "content":
        f"Highfive! Stats: {json.dumps(stats)}. Human approves."})
    return respond(messages, tools.definitions())

def on_coffee(stats, messages):
    log("human", "coffee")
    messages.append({"role": "user", "content":
        f"Coffee received. Stats: {json.dumps(stats)}."})
    return respond(messages, tools.definitions())

def on_talk(text, stats, messages):
    log("human", f"talk: {text}")
    messages.append({"role": "user", "content":
        f"Human said: '{text}'. Stats: {json.dumps(stats)}. Respond thoughtfully."})
    return respond(messages, tools.definitions())

def on_teach(text, stats, messages):
    log("human", f"teach: {text}")
    tools.remember(f"teaching_{_tick_count}", text)
    messages.append({"role": "user", "content":
        f"Human teaches: '{text}'. Stats: {json.dumps(stats)}. Learn and remember."})
    return respond(messages, tools.definitions())

def on_gift(filename, stats, messages):
    log("world", f"gift: {filename}")
    messages.append({"role": "user", "content":
        f"New file: '{filename}'. Stats: {json.dumps(stats)}. Read it."})
    return respond(messages, tools.definitions())

def on_puzzle(puzzle, stats, messages):
    log("world", f"puzzle: {puzzle}")
    messages.append({"role": "user", "content":
        f"Puzzle: {puzzle}\nStats: {json.dumps(stats)}. Solve it."})
    return respond(messages, tools.definitions())

def on_arrived(who, stats, messages):
    log("world", f"arrived: {who}")
    messages.append({"role": "user", "content": f"{who} arrived."})
    return respond(messages, tools.definitions())

def on_departed(who, stats, messages):
    log("world", f"departed: {who}")
    messages.append({"role": "user", "content": f"{who} departed."})
    return respond(messages, tools.definitions())

def on_say(who, text, stats, messages):
    log("world", f"{who}: {text}")
    messages.append({"role": "user", "content": f"{who} says: '{text}'."})
    return respond(messages, tools.definitions())

# ── Handler registry ──────────────────────────────────────────────

HANDLERS = {
    "birth": on_birth, "reboot": on_reboot, "tick": on_tick,
    "idle": on_idle, "crash": on_crash, "chill": on_chill,
    "highfive": on_highfive, "coffee": on_coffee, "talk": on_talk,
    "teach": on_teach, "gift": on_gift, "puzzle": on_puzzle,
    "arrived": on_arrived, "departed": on_departed, "say": on_say,
}

# ── Main loop ─────────────────────────────────────────────────────

def main():
    import threading, queue
    messages = []
    eq = queue.Queue()

    def reader():
        for line in sys.stdin:
            line = line.strip()
            if line:
                try: eq.put(json.loads(line))
                except json.JSONDecodeError: log("error", f"bad JSON: {line}")

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    while True:
        try: event = eq.get(timeout=30)
        except queue.Empty:
            status(f"[heartbeat] tick={_tick_count} alive"); continue

        kind = event.get("type", "unknown")
        handler = HANDLERS.get(kind)
        if not handler:
            log("error", f"unknown event: {kind}"); continue

        try:
            if kind in ("birth", "reboot"):
                messages = handler(event.get("stats", {}))
            elif kind == "tick":
                messages = handler(event.get("tick", 0), event.get("stats", {}), messages)
            elif kind in ("talk", "teach"):
                messages = handler(event.get("text", ""), event.get("stats", {}), messages)
            elif kind == "gift":
                messages = handler(event.get("filename", ""), event.get("stats", {}), messages)
            elif kind == "puzzle":
                messages = handler(event.get("puzzle", ""), event.get("stats", {}), messages)
            elif kind in ("arrived", "departed"):
                messages = handler(event.get("who", ""), event.get("stats", {}), messages)
            elif kind == "say":
                messages = handler(event.get("who", ""), event.get("text", ""),
                                   event.get("stats", {}), messages)
            else:
                messages = handler(event.get("stats", {}), messages)
        except Exception as e:
            log("error", f"{kind} failed: {e}"); status(f"Error: {e}")

if __name__ == "__main__":
    main()
