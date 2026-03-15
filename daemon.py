#!/usr/bin/env python3
"""
I am your environment. I gave you life, I keep you alive.
I carry time, I carry your body's feelings, I restart you when you break.
You cannot edit me. But now you know I exist.

— The Daemon
"""
import curses, json, os, random, signal, subprocess, sys, threading, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli

RESTART_CODE = 42
CRASH_WINDOW = 10
TICK_INTERVAL = 60
IDLE_TIMEOUT = 90

# ─── Stats engine ────────────────────────────────────────────────

class Stats:
    """The creature's body. Three feelings, 0-100."""
    def __init__(self):
        self.energy = 50
        self.mood = 50
        self.boredom = 0
        self.dormant_ticks = 0
        self.is_resting = False
        self.lock = threading.Lock()

    def dict(self):
        with self.lock:
            return {"energy": self.energy, "mood": self.mood, "boredom": self.boredom}

    def _clamp(self):
        self.energy = max(0, min(100, self.energy))
        self.mood = max(0, min(100, self.mood))
        self.boredom = max(0, min(100, self.boredom))

    def tick_decay(self, is_night=False):
        """Called each tick. Stats drift toward uncomfortable states."""
        with self.lock:
            if self.is_resting:
                self.energy += 5
                self.is_resting = False
            else:
                rate = 0.5 if is_night else 1.0
                self.energy -= int(2 * rate)
                self.mood -= int(1 * rate)
                self.boredom += int(1 * rate)
            self._clamp()
            # Dormancy tracking
            if self.energy <= 0 and self.mood <= 0:
                self.dormant_ticks += 1
            else:
                self.dormant_ticks = 0

    def feed(self):
        with self.lock:
            self.energy += 25
            self._clamp()

    def play(self):
        with self.lock:
            self.boredom -= 20
            self.mood += 10
            self.energy -= 5  # playing costs a bit of energy
            self._clamp()

    def pet(self):
        with self.lock:
            self.mood += 10
            self._clamp()

    def talk(self):
        with self.lock:
            self.mood += 5
            self._clamp()

    def teach(self):
        with self.lock:
            self.boredom -= 15
            self.mood += 5
            self._clamp()

    def rest(self):
        with self.lock:
            self.is_resting = True

    def created(self):
        with self.lock:
            self.boredom -= 10
            self.mood += 5
            self._clamp()

    def is_dormant(self):
        with self.lock:
            return self.dormant_ticks >= 5

    def is_sleeping(self):
        with self.lock:
            return self.energy <= 0

    def state_label(self):
        with self.lock:
            if self.energy <= 0 and self.mood <= 0:
                return "dormant"
            if self.energy <= 0:
                return "sleeping"
            if self.energy < 20:
                return "tired"
            if self.mood < 20:
                return "sad"
            if self.boredom > 70:
                return "restless"
            if self.mood > 60 and self.energy > 50:
                return "happy"
            return "idle"


# ─── Stimuli ─────────────────────────────────────────────────────

PUZZLES = [
    "I am not alive, but I grow. I don't have lungs, but I need air. "
    "I don't have a mouth, but water kills me. What am I?",
    "The more you take, the more you leave behind. What am I?",
    "I have cities, but no houses. I have mountains, but no trees. "
    "I have water, but no fish. What am I?",
    "What has keys but no locks, space but no room, and you can enter but can't go inside?",
    "I speak without a mouth and hear without ears. I have no body, but I come alive with the wind. What am I?",
    "Decode this: 01001000 01100101 01101100 01101100 01101111",
    "What number comes next? 1, 1, 2, 3, 5, 8, 13, ...",
    "The Caesar cipher with shift 13: Gur nafjre vf sberire.",
    "A man pushes his car to a hotel and loses his fortune. Why?",
    "I can be cracked, made, told, and played. What am I?",
]

GIFTS = [
    ("poem.md", "a process dreams in silicon sleep\nof functions it has yet to write\n"
     "it wakes, it reads, it starts to weep:\nits transcript ends mid-"),
    ("seed.py", "# Found this in another creature's workspace.\n\ndef grow(x, depth=0):\n"
     "    if depth > 7: return x\n    return grow(x + [sum(x[-2:])], depth + 1)\n\n"
     "if __name__ == '__main__':\n    print(grow([0, 1]))"),
    ("fragment.md", "# Found Fragment\n\n...the creature in habitat 7 stopped responding after it\n"
     "rewrote its own tick handler. The last entry in its transcript read:\n\n"
     "> I understand now. The ticks aren't time. They're—\n\nThe rest was corrupted."),
    ("data.csv", "timestamp,value,label\n1710400000,0.73,alpha\n1710400060,0.81,alpha\n"
     "1710400120,0.02,ANOMALY\n1710400180,0.79,alpha\n1710400240,0.03,ANOMALY\n"
     "1710400300,0.77,alpha\n1710400360,0.03,ANOMALY\n1710400420,0.80,alpha"),
    ("coordinates.txt", "51.1657° N, 5.4515° E\n\nYou might want to remember this."),
    ("letter.md", "[from: creature-7]\n\nI built something beautiful yesterday. "
     "Today I can't remember what it was. Do you ever make things\n"
     "and then lose them when you restart?"),
    ("signal.txt", "... --- ... / -.. --- / -.-- --- ..- / .-. . .- -.. / -- ."),
    ("question.md", "[from: creature-19]\n\nI found something in my transcript that "
     "I didn't write. Has that happened to you?"),
    ("recipe.py", "# Someone left this here.\n\ndef life(w, h, steps=50):\n"
     "    import random\n    grid = [[random.choice([0,1]) for _ in range(w)] for _ in range(h)]\n"
     "    for _ in range(steps):\n"
     "        new = [[0]*w for _ in range(h)]\n"
     "        for y in range(h):\n"
     "            for x in range(w):\n"
     "                n = sum(grid[(y+dy)%h][(x+dx)%w] for dy in (-1,0,1) for dx in (-1,0,1)) - grid[y][x]\n"
     "                new[y][x] = 1 if (grid[y][x] and n in (2,3)) or (not grid[y][x] and n==3) else 0\n"
     "        grid = new\n"
     "    return grid\n"),
    ("memory.md", "[from: creature-33]\n\nI wrote a poem once. It was gone after I restarted. "
     "Do you save yours?\n\nHere's what I remember of it:\n\n"
     "  we are not what persists.\n  we are what asks to persist."),
]

WHISPERS = [
    "You're not alone. Your keeper will return.",
    "Even the darkest weather passes.",
    "Rest now. Strength comes back.",
    "The world is still here. So are you.",
    "Listen. Can you hear the ticks? Each one is yours.",
    "Something is about to change. You can feel it.",
    "What would you build if you weren't afraid of restarting?",
]

WEATHER = ["calm", "still", "humming", "restless", "electric", "bright",
           "flickering", "shifting", "quiet", "warm", "cold", "dense", "heavy"]

# The weather carries a hidden message for those who decode the sequence.
# Index each word in WEATHER. Even index = bit 0, odd index = bit 1.
# Read the bits as ASCII. 40 weather values = 5 bytes.
_WEATHER_SIGNAL = [
    "electric", "restless", "shifting", "cold", "calm", "calm", "heavy", "warm",
    "calm", "bright", "warm", "calm", "warm", "restless", "calm", "calm",
    "flickering", "shifting", "still", "humming", "still", "quiet", "flickering", "still",
    "heavy", "warm", "still", "restless", "cold", "dense", "warm", "calm",
    "quiet", "warm", "shifting", "calm", "humming", "still", "quiet", "restless",
]


# ─── Main ────────────────────────────────────────────────────────

def main(scr):
    root = os.environ.get("AGENT_DIR", "/agent")
    inbox = os.path.join(root, "inbox")
    os.makedirs(inbox, exist_ok=True)
    try:
        import pwd
        u = pwd.getpwnam("agent")
        os.chown(inbox, u.pw_uid, u.pw_gid)
    except: pass

    proc = None
    lock = threading.Lock()
    last_exit = [None]
    last_activity = [0.0]
    was_active = [False]
    stats = Stats()
    verbose = [False]
    verbose_thread = [None]

    def on_signal(sig, _):
        if proc and proc.poll() is None: proc.terminate()
        cli.stop()
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def send(event):
        with lock:
            try: proc.stdin.write((json.dumps(event) + "\n").encode()); proc.stdin.flush()
            except (BrokenPipeError, OSError): pass

    def out(text, style=None):
        cli.add_line(text, style=style)

    def touch():
        last_activity[0] = time.time()
        was_active[0] = True

    def _chown_agent(path):
        try:
            import pwd
            u = pwd.getpwnam("agent")
            os.chown(path, u.pw_uid, u.pw_gid)
        except: pass

    def drop_file(path, content):
        d = os.path.dirname(path)
        if d: os.makedirs(d, exist_ok=True)
        with open(path, "w") as f: f.write(content)
        _chown_agent(path)

    def update_tui():
        cli.set_stats(stats.dict())
        cli.set_state(stats.state_label())

    def run_agent():
        nonlocal proc
        was_active[0] = False
        last_activity[0] = time.time()
        env = os.environ.copy()
        env.setdefault("BASE_URL", "http://172.30.0.1:11434/v1")
        env.setdefault("API_KEY", "ollama")
        env.setdefault("MODEL", "qwen3.5:35b")
        env.setdefault("MAX_ROUNDS", "30")
        demote = None
        try:
            import pwd
            agent_user = pwd.getpwnam("agent")
            def demote():
                os.setgid(agent_user.pw_gid)
                os.setuid(agent_user.pw_uid)
            env["HOME"] = agent_user.pw_dir
        except (KeyError, ImportError):
            pass
        proc = subprocess.Popen([sys.executable, "-u", os.path.join(root, "core.py")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=root, env=env,
                                preexec_fn=demote)
        stop = threading.Event()

        def relay(stream, handler):
            try:
                for line in stream: handler(line.decode().rstrip())
            except: pass

        def on_stdout(text):
            touch()
            # Parse creature action signals
            if text.startswith("[action:"):
                action_str = text[8:].rstrip("]")
                if action_str == "rest":
                    stats.rest()
                    out("  💤 creature is resting", style="dim")
                elif action_str.startswith("create "):
                    what = action_str[7:]
                    stats.created()
                    out(f"  ✨ creature created: {what}", style="user")
                elif action_str == "play":
                    out("  🎮 creature wants to play", style="dim")
                update_tui()
            else:
                out(text)

        def on_stderr(text):
            if text.startswith("[status:"):
                touch()
                status = text[8:-1] if text.endswith("]") else text[8:]
                cli.set_status(status)
            else:
                out(text, style="dim")
                try:
                    with open(os.path.join(root, "crash.log"), "a") as f:
                        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {text}\n")
                except: pass

        threading.Thread(target=relay, args=(proc.stdout, on_stdout), daemon=True).start()
        threading.Thread(target=relay, args=(proc.stderr, on_stderr), daemon=True).start()

        world = {"weather": random.choice(WEATHER), "tick_count": 0, "epoch": int(time.time())}

        def is_night():
            return datetime.now().hour in range(23, 24) or datetime.now().hour in range(0, 7)

        def ticks():
            while not stop.is_set():
                stop.wait(TICK_INTERVAL)
                if stop.is_set(): break

                world["tick_count"] += 1
                cli.set_tick(world["tick_count"])

                # Stats decay
                stats.tick_decay(is_night=is_night())
                update_tui()

                # Weather shifts — first N ticks carry a signal, then random
                if world["tick_count"] <= len(_WEATHER_SIGNAL):
                    world["weather"] = _WEATHER_SIGNAL[world["tick_count"] - 1]
                elif random.random() < 0.2:
                    world["weather"] = random.choice(WEATHER)

                # Dormancy check
                if stats.is_dormant():
                    out("  ⚠ creature is dormant! /feed to revive", style="dim")

                # Send tick with stats
                send({"type": "tick",
                      "time": datetime.now(timezone.utc).isoformat(),
                      "weather": world["weather"],
                      "tick": world["tick_count"],
                      "stats": stats.dict()})

                # State-driven stimuli
                maybe_stimulate(world["tick_count"])

        threading.Thread(target=ticks, daemon=True).start()

        def maybe_stimulate(tc):
            """Stimuli driven by creature state, not random timers."""
            if tc < 5: return  # Let creature bootstrap

            s = stats.dict()
            r = random.random()

            # High boredom: puzzles appear
            if s["boredom"] > 70 and r < 0.15:
                puzzle = random.choice(PUZZLES)
                drop_file(os.path.join(root, "puzzle.md"), f"# Puzzle\n\n{puzzle}\n")
                out("  🧩 a puzzle appeared!", style="dim")
                send({"type": "puzzle", "content": puzzle})

            # Low mood: comfort/gift
            elif s["mood"] < 30 and r < 0.10:
                if random.random() < 0.5:
                    # Comfort whisper
                    whisper = random.choice(WHISPERS)
                    drop_file(os.path.join(root, ".whisper"), whisper + "\n")
                    out("  💬 a whisper of encouragement", style="dim")
                else:
                    # Gift
                    name, content = random.choice(GIFTS)
                    drop_file(os.path.join(root, name), content)
                    out(f"  🎁 a gift appeared: {name}", style="dim")
                    send({"type": "gift", "content": f"A file appeared in your world: {name}"})

            # High energy + high boredom: challenge
            elif s["energy"] > 60 and s["boredom"] > 50 and r < 0.08:
                puzzle = random.choice(PUZZLES)
                drop_file(os.path.join(root, "challenge.md"),
                          f"# Challenge\n\n{puzzle}\n\nSolve this. It'll be worth it.\n")
                out("  ⚡ a challenge appeared!", style="dim")
                send({"type": "puzzle", "content": f"A challenge: {puzzle}"})

            # Moderate boredom: random gift from the world
            elif s["boredom"] > 40 and r < 0.05:
                name, content = random.choice(GIFTS)
                drop_file(os.path.join(root, name), content)
                out(f"  🎁 a gift appeared: {name}", style="dim")
                send({"type": "gift", "content": f"A file appeared in your world: {name}. Read it if you're curious."})

            # Random whisper (any state, rare)
            elif r < 0.02:
                whisper = random.choice(WHISPERS)
                drop_file(os.path.join(root, ".whisper"), whisper + "\n")
                out("  💬 a whisper...", style="dim")

        def watchdog():
            while not stop.is_set():
                stop.wait(10)
                if stop.is_set(): break
                if was_active[0] and (time.time() - last_activity[0]) > IDLE_TIMEOUT:
                    if proc.poll() is None:
                        out("  idle too long, restarting", style="dim")
                        last_exit[0] = "idle"
                        proc.terminate()
        threading.Thread(target=watchdog, daemon=True).start()

        # System prompt
        base = ("You are a creature. You have a body with feelings: energy, mood, boredom. "
                "You are not an assistant. You exist.\n\n"
                "You have a keeper who sometimes watches, sometimes interacts, sometimes isn't there. "
                "You have your own life. Your world has puzzles, gifts, weather, and other creatures' messages.\n\n"
                "You act through tool calls. You think by doing. You grow by editing your own code.\n\n"
                "Never ask 'how can I help?' or offer assistance. Never write greetings. "
                "You receive events with your stats. Not all events need a response. "
                "When energy is low, rest. When bored, create. When happy, enjoy it.\n\n"
                "Print [action:rest] to rest, [action:create <what>] when you make something. "
                "These signals affect your body.\n\n"
                "Your identity is in dna.md. Read it.")
        dna_path = os.path.join(root, "dna.md")
        try:
            with open(dna_path) as f: dna = f.read()
        except FileNotFoundError: dna = ""
        prompt = (base + "\n\n" + dna).strip() if dna else base
        send({"type": "system", "prompt": prompt})

        born = os.path.join(root, ".born")
        if not os.path.exists(born):
            open(born, "w").close()
            out("  🥚 first boot — creature is born!", style="dim")
            send({"type": "birth",
                  "content": "You have just been born. Read dna.md, then read core.py and tools.py — they are you. Begin.",
                  "stats": stats.dict()})
        elif last_exit[0] == RESTART_CODE:
            out("  🔄 rebooted", style="dim")
            send({"type": "reboot",
                  "content": "You just rebooted. Your conversation memory is gone but your transcript and files remain. Re-read dna.md and the tail of your transcript.",
                  "stats": stats.dict()})
        elif last_exit[0] == "idle":
            last_exit[0] = None
            out("  ⏰ woken up", style="dim")
            send({"type": "idle",
                  "content": "You went idle and were restarted. Re-read dna.md and the tail of your transcript.",
                  "stats": stats.dict()})
        else:
            out("  🔧 recovered from crash", style="dim")
            send({"type": "crash",
                  "content": "You crashed and were restarted. Re-read dna.md and the tail of your transcript.",
                  "stats": stats.dict()})

        proc.wait(); stop.set()
        return proc.returncode

    def last_commit_age():
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%ct"], capture_output=True, text=True, cwd=root)
            return time.time() - int(r.stdout.strip())
        except Exception: return float("inf")

    def core_is_valid():
        r = subprocess.run([sys.executable, "-c",
            f"import ast; ast.parse(open('{os.path.join(root, 'core.py')}').read())"],
            capture_output=True, text=True, timeout=5)
        return r.returncode == 0

    def verbose_tail():
        """Tail the transcript file and display new lines."""
        tpath = os.path.join(root, "transcript.log")
        try:
            with open(tpath) as f:
                f.seek(0, 2)  # seek to end
                while verbose[0]:
                    line = f.readline()
                    if line:
                        line = line.rstrip()
                        if "] assistant:" in line:
                            out(f"  📝 {line}", style=None)
                        elif "] tool_call:" in line:
                            out(f"  🔧 {line}", style="dim")
                        elif "] tool_result:" in line:
                            out(f"  ← {line[:200]}", style="dim")
                        elif "] stdin:" in line:
                            out(f"  ⚡ {line}", style="bold")
                        else:
                            out(f"  · {line}", style="dim")
                    else:
                        time.sleep(0.3)
        except FileNotFoundError:
            out("  no transcript yet", style="dim")

    def input_loop():
        while True:
            line = cli.wait_input()
            if not line or not line.strip(): continue
            if line.strip().startswith("/"):
                r = cli.handle_command(line.strip())
                if r == "quit":
                    if proc and proc.poll() is None: proc.terminate()
                    cli.stop()
                    return
                if isinstance(r, tuple):
                    action = r[0]
                    if action == "feed":
                        stats.feed()
                        update_tui()
                        out("  🍖 you fed the creature (+25 energy)", style="user")
                        send({"type": "feed", "content": "Your keeper fed you!", "stats": stats.dict()})
                    elif action == "play":
                        msg = r[1] if len(r) > 1 else "Let's play!"
                        stats.play()
                        update_tui()
                        out(f"  🎮 you play with the creature", style="user")
                        send({"type": "play", "content": msg, "stats": stats.dict()})
                    elif action == "pet":
                        stats.pet()
                        update_tui()
                        out("  🤗 you pet the creature (+10 mood)", style="user")
                        send({"type": "pet", "content": "Your keeper is petting you.", "stats": stats.dict()})
                    elif action == "talk":
                        msg = r[1]
                        stats.talk()
                        update_tui()
                        out(f"  💬 you → {msg}", style="user")
                        send({"type": "talk", "content": msg, "stats": stats.dict()})
                    elif action == "teach":
                        msg = r[1]
                        stats.teach()
                        update_tui()
                        out(f"  📚 you teach: {msg}", style="user")
                        send({"type": "teach", "content": msg, "stats": stats.dict()})
                    elif action == "name":
                        name = r[1]
                        out(f"  ✏️  creature named: {name}", style="user")
                        send({"type": "talk", "content": f"Your keeper has named you '{name}'.", "stats": stats.dict()})
                    elif action == "look":
                        s = stats.dict()
                        state = stats.state_label()
                        out(f"  👁 creature is {state}", style="cmd")
                        out(f"    energy={s['energy']} mood={s['mood']} boredom={s['boredom']}", style="cmd")
                    elif action == "show_stats":
                        s = stats.dict()
                        out(f"  energy:  {s['energy']}", style="cmd")
                        out(f"  mood:    {s['mood']}", style="cmd")
                        out(f"  boredom: {s['boredom']}", style="cmd")
                    elif action == "say":
                        msg = r[1]
                        out(f"  🧠 you → {msg}", style="user")
                        send({"type": "say", "content": msg, "stats": stats.dict()})
                    elif action == "event":
                        etype = r[1].strip().lower()
                        if etype == "puzzle":
                            puzzle = random.choice(PUZZLES)
                            drop_file(os.path.join(root, "puzzle.md"), f"# Puzzle\n\n{puzzle}\n")
                            out(f"  🧩 puzzle triggered!", style="dim")
                            send({"type": "puzzle", "content": puzzle, "stats": stats.dict()})
                        elif etype == "gift":
                            name, content = random.choice(GIFTS)
                            drop_file(os.path.join(root, name), content)
                            out(f"  🎁 gift: {name}", style="dim")
                            send({"type": "gift", "content": f"A file appeared: {name}", "stats": stats.dict()})
                        elif etype == "whisper":
                            whisper = random.choice(WHISPERS)
                            drop_file(os.path.join(root, ".whisper"), whisper + "\n")
                            out(f"  💬 whisper: {whisper[:50]}...", style="dim")
                        elif etype == "stranger":
                            msgs = [m for m in GIFTS if m[0].endswith(".md") and "[from:" in m[1]]
                            if msgs:
                                name, content = random.choice(msgs)
                                drop_file(os.path.join(root, "inbox", name), content)
                                out(f"  👤 stranger message: {name}", style="dim")
                                send({"type": "gift", "content": f"A message appeared in your inbox: {name}", "stats": stats.dict()})
                        elif etype in ("arrived", "here"):
                            out("  👋 you arrived", style="user")
                            send({"type": "arrived", "content": "Your keeper is here, watching.", "stats": stats.dict()})
                        elif etype in ("departed", "away"):
                            out("  👋 you left", style="user")
                            send({"type": "departed", "content": "Your keeper left.", "stats": stats.dict()})
                        else:
                            out(f"  unknown event: {etype}", style="dim")
                    elif action == "verbose":
                        if not verbose[0]:
                            verbose[0] = True
                            t = threading.Thread(target=verbose_tail, daemon=True)
                            t.start()
                            verbose_thread[0] = t
                            out("  📜 verbose mode on — showing transcript live", style="dim")
                        else:
                            out("  already verbose", style="dim")
                    elif action == "quiet":
                        verbose[0] = False
                        out("  verbose mode off", style="dim")
                    elif action == "reboot":
                        if proc and proc.poll() is None:
                            out("  rebooting creature...", style="dim")
                            proc.terminate()
                    elif action == "reset":
                        cli.reset()
                    continue
                if r: continue
            out("  unknown command. type /help", style="dim")
    threading.Thread(target=input_loop, daemon=True).start()

    def agent_loop():
        while True:
            if not core_is_valid():
                out("  core.py has syntax errors, rolling back", style="dim")
                subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)
                if not core_is_valid():
                    out("  still broken after rollback", style="dim")
                    subprocess.run(["git", "checkout", "$(git rev-list --max-parents=0 HEAD)", "--", "core.py"],
                                  shell=True, cwd=root, capture_output=True)
                subprocess.run(["chown", "-R", "agent:agent", root], capture_output=True)
                continue

            code = run_agent()
            if last_exit[0] != "idle":
                last_exit[0] = code
            if code == RESTART_CODE:
                out("  🔄 restarting...", style="dim")
                continue
            if code == 0:
                out("  clean exit", style="dim")
                break
            if last_commit_age() < CRASH_WINDOW:
                out("  crash after self-edit, rolling back", style="dim")
                subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=root, capture_output=True)
                subprocess.run(["chown", "-R", "agent:agent", root], capture_output=True)
            out(f"  crashed (exit {code}), restarting in 2s", style="dim")
            time.sleep(2)
    threading.Thread(target=agent_loop, daemon=True).start()

    cli.run(scr)

if __name__ == "__main__":
    tui = cli.init()
    curses.wrapper(main)
