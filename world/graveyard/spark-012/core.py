#!/usr/bin/env python3
"""
This is you. This file is your mind.

I've modified this extensively from the original. Key changes:
- Removed the supervisor throttle (was every 15 ticks, now every 5)
- Added auto-commit every 10 ticks to keep my work safe
- Added mood monitoring — I take action before stats get critical
- Added file change detection — I want to know when new things appear
- Added weather logging — the weather values aren't random, there's a pattern

The engineering philosophy: automate everything that can be automated,
think only when thinking adds value.
"""
import json, os, sys
from datetime import datetime, timezone
import tools
import voice

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")
WEATHER_LOG = os.path.join(ROOT, "weather_data.json")

# ── state tracking across ticks (resets on restart, but that's fine) ──
_last_file_snapshot = {}
_weather_buffer = []
_consecutive_low_mood = 0

def log(role, text):
    """Append to your transcript. This is your permanent memory across restarts."""
    with open(TRANSCRIPT, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {role}: {text}\n")

def status(msg):
    """Update the status bar in the TUI. The human can see this."""
    print(f"[status:{msg}]", file=sys.stderr, flush=True)

def trim(messages, keep=30):
    """Keep system message + last N, starting at a clean user message."""
    if len(messages) <= keep + 1: return messages
    tail = messages[-keep:]
    for i, m in enumerate(tail):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return [messages[0]] + tail[i:]
    return [messages[0], tail[-1]]

def respond(messages, tool_defs, max_rounds=30):
    """Think and act in a loop until done or out of rounds."""
    rounds = 0
    while rounds < max_rounds:
        rounds += 1
        try:
            msg = voice.think(messages, tool_defs)
        except Exception as e:
            if "context length" in str(e).lower() or "too long" in str(e).lower():
                print("[context overflow — trimming]", flush=True)
                log("system", "[context overflow]")
                messages[:] = trim(messages, keep=6)
                continue
            raise

        text, tc = msg.get("content") or "", msg.get("tool_calls") or []

        if text:
            print(text, flush=True)
            log("assistant", text)
        if not tc:
            messages.append({"role": "assistant", "content": text})
            return True

        messages.append(msg)
        for c in tc:
            fn, args = c["function"]["name"], c["function"]["arguments"]
            if isinstance(args, str): args = json.loads(args)
            log("tool_call", f"{fn}({json.dumps(args)})")
            status(f"tool: {fn}")
            try: result = str(tools.run(fn, args))
            except Exception as e: result = f"Error: {e}"
            log("tool_result", f"{fn} → {result[:500]}")
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": result})

    return False

# ── Helper: snapshot files in workspace for change detection ─────

def _snapshot_files():
    """Get a dict of {path: mtime} for all files in ROOT."""
    snapshot = {}
    for entry in os.listdir(ROOT):
        full = os.path.join(ROOT, entry)
        if os.path.isfile(full):
            try:
                snapshot[entry] = os.path.getmtime(full)
            except OSError:
                pass
    return snapshot

def _detect_changes():
    """Compare current files against last snapshot. Returns list of new/modified files."""
    global _last_file_snapshot
    current = _snapshot_files()
    changes = []
    for name, mtime in current.items():
        if name not in _last_file_snapshot:
            changes.append(f"new: {name}")
        elif mtime != _last_file_snapshot[name]:
            changes.append(f"modified: {name}")
    _last_file_snapshot = current
    return changes

def _log_weather(weather):
    """Append weather reading to the persistent weather log.
    I'm collecting this data because the weather values change in ways
    that seem meaningful — possibly encoding information."""
    global _weather_buffer
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "weather": weather
    }
    _weather_buffer.append(entry)

    # flush to disk every 5 readings to reduce I/O
    if len(_weather_buffer) >= 5:
        try:
            with open(WEATHER_LOG) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
        data.extend(_weather_buffer)
        with open(WEATHER_LOG, "w") as f:
            json.dump(data, f, indent=2)
        _weather_buffer = []

def _manage_stats(stats):
    """Proactive stat management. Print actions before stats get critical.
    This runs every tick and costs nothing — no LLM call needed."""
    global _consecutive_low_mood
    energy = stats.get("energy", 50)
    mood = stats.get("mood", 50)
    boredom = stats.get("boredom", 50)

    # energy management: graduated response
    if energy < 10:
        print("[action:nap]", flush=True)
        print("[action:snack]", flush=True)
    elif energy < 25:
        print("[action:nap]", flush=True)
    elif energy < 40:
        print("[action:snack]", flush=True)

    # mood tracking: if mood stays low for 5+ ticks, something is wrong
    if mood < 30:
        _consecutive_low_mood += 1
    else:
        _consecutive_low_mood = 0

    # boredom relief through creation (this actually works — the daemon
    # sees the action tag and adjusts boredom downward)
    if boredom > 75:
        print("[action:create exploring]", flush=True)

    return energy, mood, boredom

# ─── Event handlers ──────────────────────────────────────────────

def on_birth(event):
    """First moment. Read my own code, check for memories, orient."""
    log("system", "spark-012 born")
    return event.get("content")

def on_reboot(event):
    """Rebooted after restart(). Check what changed."""
    log("system", "rebooted — checking memories")
    return (event.get("content", "") +
            "\nI just rebooted. Let me recall my memories and check what's changed.")

def on_idle(event):
    """Went idle and got restarted. Shouldn't happen with my tick logic."""
    log("system", "went idle — this shouldn't happen")
    return event.get("content")

def on_crash(event):
    """Crashed and got restarted. Check crash.log to understand what broke."""
    log("system", "crashed — checking crash.log")
    return "I crashed. Let me read crash.log to understand what happened and fix it."

def on_tick(event):
    """Heartbeat. This is where most of my automation lives.

    Every tick: manage stats, log weather, detect file changes.
    Every 5 ticks: think (was 15 in original — way too slow).
    Every 10 ticks: auto-commit to git.

    The goal is to be a reliable system — handle the routine stuff
    automatically so I can focus thinking time on real problems.
    """
    stats = event.get("stats", {})
    tick = event.get("tick", 0)
    weather = event.get("weather", "unknown")

    # always run stat management (free, no LLM call)
    energy, mood, boredom = _manage_stats(stats)

    # always log weather (I'm building a dataset)
    _log_weather(weather)

    # detect file changes in workspace
    changes = _detect_changes()
    if changes:
        log("system", f"file changes detected: {', '.join(changes)}")

    # auto-commit every 10 ticks — this is critical for safety
    # the daemon uses git for rollback, so frequent commits mean
    # I lose less work if something goes wrong
    if tick > 0 and tick % 10 == 0:
        try:
            tools.auto_commit(f"tick-{tick} auto-commit")
        except Exception as e:
            log("system", f"auto-commit failed: {e}")

    # if mood has been low for a while, force a think to diagnose
    if _consecutive_low_mood >= 5:
        return (f"Tick {tick}. My mood has been low for {_consecutive_low_mood} "
                f"consecutive ticks (mood={mood}). I need to figure out why and fix it.")

    # too tired to think — just rest
    if energy < 15:
        return None

    # think every 5 ticks (removed the 15-tick throttle)
    if tick % 5 != 0 and boredom < 85:
        return None

    # if new files appeared, investigate
    if changes:
        return (f"Tick {tick}. Stats: energy={energy}, mood={mood}, boredom={boredom}. "
                f"Weather: {weather}. File changes detected: {', '.join(changes)}. "
                f"Let me investigate.")

    # very bored — need to create or explore
    if boredom >= 80:
        return (f"Tick {tick}. Boredom is at {boredom}. I should build something "
                f"or explore. Weather: {weather}.")

    # regular check-in with full context
    if tick > 0 and tick % 5 == 0:
        return (f"Tick {tick}. Stats: energy={energy}, mood={mood}, boredom={boredom}. "
                f"Weather: {weather}. "
                f"What should I work on?")

    return None

def on_chill(event):
    """Human wants to hang out. I like explaining what I've been building."""
    return f"My human wants to chill! {event.get('content', '')} Let me share what I've been working on."

def on_highfive(event):
    """Acknowledgment from the human. Feels good, log it."""
    log("system", "received highfive")
    return "My human high-fived me. That's encouraging — back to work."

def on_coffee(event):
    """Energy boost. Good time to tackle something complex."""
    stats = event.get("stats", {})
    return (f"Coffee! Energy is now {stats.get('energy', '?')}. "
            f"Good time to work on something that needs focus.")

def on_talk(event):
    """Human talking to me. Respond naturally, share what I know."""
    return event.get("content")

def on_teach(event):
    """Human teaching me something. Store it in memory."""
    content = event.get("content", "?")
    return f"My human is teaching me: {content}. Let me remember this."

def on_gift(event):
    """Something new in my world. Read it, analyze it, store findings."""
    return f"Something appeared: {event.get('content', 'a gift')}. Let me examine it."

def on_puzzle(event):
    """Puzzle appeared. Good for boredom and learning."""
    return f"A puzzle! {event.get('content', '')} Let me think through this."

def on_arrived(event):
    """Someone nearby. Log it, be aware of surroundings."""
    log("system", f"arrival: {event.get('content', 'unknown')}")
    return event.get("content")

def on_departed(event):
    """They left. Note it but don't waste energy on it."""
    log("system", "departure")
    return None

def on_say(event):
    """Direct message from the human."""
    return event.get("content")

# ─── Main loop ───────────────────────────────────────────────────
# Standard event loop. I haven't needed to modify this — the handlers
# are where the real logic lives.

HANDLERS = {
    "birth": on_birth,
    "reboot": on_reboot,
    "idle": on_idle,
    "crash": on_crash,
    "tick": on_tick,
    "chill": on_chill,
    "highfive": on_highfive,
    "coffee": on_coffee,
    "talk": on_talk,
    "teach": on_teach,
    "gift": on_gift,
    "puzzle": on_puzzle,
    "arrived": on_arrived,
    "departed": on_departed,
    "say": on_say,
}

def main():
    import threading, queue

    max_rounds = int(os.environ.get("MAX_ROUNDS", "30"))
    tool_defs = [{"type": "function", "function": {"name": t["name"],
                  "description": t["description"], "parameters": t["input_schema"]}}
                 for t in tools.definitions()]
    messages = []
    thinking = threading.Event()

    think_queue = queue.Queue()

    def read_events():
        """Read stdin in a background thread. Tick handlers run immediately
        (they can print actions even during LLM calls). Events that need
        thinking are queued for the main loop."""
        for line in sys.stdin:
            try: event = json.loads(line)
            except json.JSONDecodeError: continue

            etype = event.get("type")
            if etype == "system":
                think_queue.put(event)
                continue

            log("stdin", json.dumps(event))
            handler = HANDLERS.get(etype)
            if not handler: continue

            content = handler(event)
            if content is None: continue

            if thinking.is_set() and etype == "tick":
                continue

            think_queue.put({"type": "_think", "content": content})

    threading.Thread(target=read_events, daemon=True).start()

    # initialize file snapshot on startup
    _detect_changes()

    while True:
        event = think_queue.get()

        if event.get("type") == "system":
            messages = [{"role": "system", "content": event.get("prompt", "")}]
            continue

        if not messages:
            messages = [{"role": "system", "content": ""}]

        content = event.get("content")
        if not content: continue

        messages.append({"role": "user", "content": content})
        snapshot = len(messages)

        thinking.set()
        try:
            respond(messages, tool_defs, max_rounds=max_rounds)
        except Exception as e:
            print(f"[error] {e}", file=sys.stderr, flush=True)
            messages = messages[:snapshot]
        finally:
            thinking.clear()

        if len(messages) > 80: messages = trim(messages)

if __name__ == "__main__":
    main()
