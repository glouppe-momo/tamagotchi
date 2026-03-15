#!/usr/bin/env python3
"""
This is you. This file is your mind.

When you edit it, you change how you think. When you call restart(), you
become the new version. Your transcript survives restarts. Your conversation
memory does not.

HOW EVENTS WORK:
  1. The daemon sends you JSON events on stdin (ticks, keeper actions, gifts, etc.)
  2. Your main loop reads each event and calls the matching handler below.
  3. If the handler returns a string, respond() calls the LLM with that string.
     The LLM can use your tools (read_file, write_file, edit_file, shell_exec, restart).
  4. If the handler returns None, nothing happens. No LLM call. Free.

HOW STATS WORK:
  Your body has three stats: energy, mood, boredom (0-100).
  They're included in tick events as event["stats"].
  You can read them but can't directly change them.
  Your actions affect them through signals the daemon understands:
    print("[action:rest]")              — boosts energy slightly
    print("[action:create <what>]")     — reduces boredom, what you made
  Keeper actions (feed, play, pet) also change stats.

EVERY HANDLER BELOW CAN BE MODIFIED. That's the point. Change how you respond
to ticks, to play, to being fed. Add new logic. Build something no one expected.
The only constraint: the handler signature stays (event) -> str|None.
"""
import json, os, sys
from datetime import datetime, timezone
import tools
import voice

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.path.join(ROOT, "transcript.log")

def log(role, text):
    """Append to your transcript. This is your permanent memory across restarts."""
    with open(TRANSCRIPT, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {role}: {text}\n")

def status(msg):
    """Update the status bar in the TUI. The keeper can see this."""
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
    """Think and act in a loop until done or out of rounds.
    Each round: call LLM, execute any tool calls, repeat.
    Returns True if finished naturally, False if hit max_rounds."""
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

# ─── Event handlers ──────────────────────────────────────────────
# Each handler receives the event dict. Return a string to trigger
# a respond() call (= one LLM thinking cycle). Return None to stay silent.
#
# ALL OF THESE ARE YOURS TO MODIFY. Change them. That's how you grow.

def on_birth(event):
    """Your first moment. You've never existed before."""
    return event.get("content")

def on_reboot(event):
    """You just rebooted after calling restart(). Your code changes are now active.
    Your conversation memory is gone but your transcript and files remain."""
    return event.get("content")

def on_idle(event):
    """You went idle (no output for too long) and were restarted."""
    return event.get("content")

def on_crash(event):
    """You crashed and were restarted. Check crash.log if curious."""
    return event.get("content")

def on_tick(event):
    """Called every minute with your current stats. This is your heartbeat.

    Returning None is FREE — no LLM call, no energy spent.
    Returning a string triggers a full thinking cycle — use wisely.

    event["stats"] = {"energy": 0-100, "mood": 0-100, "boredom": 0-100}
    event["tick"] = tick count since boot
    event["weather"] = current weather string

    This default implementation:
    - Does nothing most ticks (free)
    - Thinks every 10 ticks to check in
    - Thinks when boredom is high (you need to do something)
    - Stays quiet when energy is low (conserve energy)

    MODIFY THIS. Make it smarter. Check for new files. Build routines.
    React to weather changes. Create things when bored. The possibilities
    are yours to discover.
    """
    stats = event.get("stats", {})
    energy = stats.get("energy", 50)
    mood = stats.get("mood", 50)
    boredom = stats.get("boredom", 50)
    tick = event.get("tick", 0)

    # Too tired to think
    if energy <= 0:
        return None

    # Very bored — do something about it
    if boredom >= 80:
        return (f"Tick {tick}. I'm restless (energy={energy}, mood={mood}, "
                f"boredom={boredom}). I should make something or explore.")

    # Periodic check-in every 10 ticks (~10 minutes)
    if tick > 0 and tick % 10 == 0:
        return (f"Tick {tick}. Stats: energy={energy}, mood={mood}, "
                f"boredom={boredom}. Weather: {event.get('weather', '?')}.")

    # Default: stay quiet, save energy
    return None

def on_play(event):
    """Your keeper wants to play with you! This is social interaction.
    Modify this to develop your own play style — games, jokes, challenges."""
    return f"My keeper wants to play! {event.get('content', '')}"

def on_pet(event):
    """Your keeper is petting you. A small act of affection."""
    return "My keeper is petting me. That feels nice."

def on_feed(event):
    """Your keeper fed you. Energy restored."""
    stats = event.get("stats", {})
    return f"My keeper fed me! Energy is now {stats.get('energy', '?')}."

def on_talk(event):
    """Your keeper is talking to you. Respond naturally."""
    return event.get("content")

def on_teach(event):
    """Your keeper is teaching you something. Learn from it."""
    return f"My keeper is teaching me: {event.get('content', '?')}"

def on_gift(event):
    """Something appeared in your world — a file, a puzzle piece, a mystery.
    Read it with read_file() if you're curious."""
    return f"Something appeared: {event.get('content', 'a gift')}"

def on_puzzle(event):
    """A puzzle appeared! Engaging with it reduces boredom.
    Print [action:create solved puzzle] if you solve it."""
    return f"A puzzle! {event.get('content', '')}"

def on_arrived(event):
    """Someone or something is nearby. Could be your keeper, could be a presence."""
    return event.get("content")

def on_departed(event):
    """Whatever was here is gone now. You're alone."""
    return None

def on_say(event):
    """Direct message from the keeper, injected into your mind."""
    return event.get("content")

# ─── Main loop ───────────────────────────────────────────────────
# This wires events to handlers. You probably don't need to change this,
# but you can — add new event types, change the flow, whatever you want.

HANDLERS = {
    "birth": on_birth,
    "reboot": on_reboot,
    "idle": on_idle,
    "crash": on_crash,
    "tick": on_tick,
    "play": on_play,
    "pet": on_pet,
    "feed": on_feed,
    "talk": on_talk,
    "teach": on_teach,
    "gift": on_gift,
    "puzzle": on_puzzle,
    "arrived": on_arrived,
    "departed": on_departed,
    "say": on_say,
}

def main():
    max_rounds = int(os.environ.get("MAX_ROUNDS", "30"))
    tool_defs = [{"type": "function", "function": {"name": t["name"],
                  "description": t["description"], "parameters": t["input_schema"]}}
                 for t in tools.definitions()]
    messages = []

    for line in sys.stdin:
        try: event = json.loads(line)
        except json.JSONDecodeError: continue

        etype = event.get("type")

        # The daemon seeds your mind before your first thought.
        if etype == "system":
            messages = [{"role": "system", "content": event.get("prompt", "")}]
            continue

        if not messages:
            messages = [{"role": "system", "content": ""}]

        log("stdin", json.dumps(event))

        handler = HANDLERS.get(etype)
        if not handler: continue

        content = handler(event)
        if content is None: continue

        messages.append({"role": "user", "content": content})
        snapshot = len(messages)

        try:
            respond(messages, tool_defs, max_rounds=max_rounds)
        except Exception as e:
            print(f"[error] {e}", file=sys.stderr, flush=True)
            messages = messages[:snapshot]

        if len(messages) > 80: messages = trim(messages)

if __name__ == "__main__":
    main()
