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
import cli, stimuli

RESTART_CODE = 42
CRASH_WINDOW = 10
TICK_INTERVAL = 30
IDLE_TIMEOUT = 60
MAX_RAPID_RESTARTS = 5       # max restarts within RAPID_RESTART_WINDOW
RAPID_RESTART_WINDOW = 30    # seconds — if N restarts happen this fast, it's a loop

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
                self.mood += 2  # rest is also soothing
                self.is_resting = False
            else:
                rate = 0.5 if is_night else 1.0
                self.energy -= int(1 * rate)
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
            self.is_resting = True  # +5 energy on next tick + small mood recovery

    def created(self):
        with self.lock:
            self.boredom -= 10
            self.mood += 5
            self._clamp()

    def solved(self):
        with self.lock:
            self.boredom -= 15
            self.mood += 8
            self._clamp()

    def explored(self):
        with self.lock:
            self.mood += 3
            self.boredom -= 5
            self.energy -= 2  # exploring costs a bit
            self._clamp()

    def forage(self):
        """Creature finds its own food. Less than keeper feeding, but autonomous."""
        with self.lock:
            self.energy += 8
            self.mood += 2
            self._clamp()

    def active(self):
        """Creature is doing something (tool calls, exploration). Slows boredom."""
        with self.lock:
            self.boredom = max(0, self.boredom - 1)

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


# ─── Stimuli (content lives in stimuli.py) ───────────────────────

WEATHER = stimuli.WEATHER
_WEATHER_SIGNAL = stimuli.WEATHER_SIGNAL


# ─── Main ────────────────────────────────────────────────────────

def main(scr):
    root = os.environ.get("AGENT_DIR", "/agent")
    try:
        import pwd
        u = pwd.getpwnam("agent")
    except (KeyError, ImportError):
        u = None

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

    last_good_commit = [None]  # SHA of last commit where creature ran successfully

    def _get_head():
        """Get current HEAD SHA."""
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"],
                               capture_output=True, text=True, cwd=root, timeout=5)
            return r.stdout.strip()
        except Exception:
            return None

    def _get_initial_commit():
        """Get the very first commit (original spawn state)."""
        try:
            r = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"],
                               capture_output=True, text=True, cwd=root, timeout=5)
            return r.stdout.strip().splitlines()[0]
        except Exception:
            return None

    def _mark_good():
        """Mark current HEAD as last known good state."""
        sha = _get_head()
        if sha:
            last_good_commit[0] = sha
            out(f"  ✓ marked good: {sha[:8]}", style="dim")

    stim = stimuli.World()  # tracks stimuli state (gifts given, archive progress, etc.)

    def run_agent():
        nonlocal proc
        booted = [False]  # set True on first stdout → marks commit as good
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
            if not booted[0]:
                booted[0] = True
                _mark_good()
            stats.active()  # creature is doing something, slow boredom
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
                elif action_str.startswith("dream "):
                    dream_text = action_str[6:]
                    out(f"  💭 {dream_text}", style="dim")
                    try:
                        with open(os.path.join(root, "dreams.log"), "a") as f:
                            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {dream_text}\n")
                    except: pass
                elif action_str.startswith("solve"):
                    what = action_str[6:] if len(action_str) > 6 else ""
                    stats.solved()
                    out(f"  🧩 creature solved: {what}" if what else "  🧩 creature solved something", style="user")
                elif action_str.startswith("explore"):
                    what = action_str[8:] if len(action_str) > 8 else ""
                    stats.explored()
                    out(f"  🔍 creature explored: {what}" if what else "  🔍 creature is exploring", style="user")
                elif action_str == "eat":
                    stats.forage()
                    out("  🌿 creature foraged for food", style="dim")
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
        # stim is defined at main() scope above

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

                # Capacity: energy affects how many tool rounds per thought
                s = stats.dict()
                capacity = max(3, int(s["energy"] / 100 * 30))

                # Send tick with stats
                send({"type": "tick",
                      "time": datetime.now(timezone.utc).isoformat(),
                      "weather": world["weather"],
                      "tick": world["tick_count"],
                      "stats": s,
                      "capacity": capacity})

                # State-driven stimuli
                maybe_stimulate(world["tick_count"])

        threading.Thread(target=ticks, daemon=True).start()

        def maybe_stimulate(tc):
            """Stimuli driven by creature state, not random timers."""
            if tc < 5: return  # Let creature bootstrap

            s = stats.dict()
            r = random.random()

            # --- Manage speed challenge TTL ---
            speed_file = os.path.join(root, "speed_challenge.md")
            if os.path.exists(speed_file):
                try:
                    age = time.time() - os.path.getmtime(speed_file)
                    if age > 90:  # generous upper bound; actual TTL varies
                        os.remove(speed_file)
                        out("  ⏰ the speed challenge expired!", style="dim")
                except: pass

            # --- Archive mystery: drop next fragment every ~15 ticks ---
            if tc % 15 == 0 and stim.mystery_phase < len(stimuli.ARCHIVE_PARTS):
                part = stim.next_archive_part()
                if part:
                    name, content = part
                    os.makedirs(os.path.join(root, "archive"), exist_ok=True)
                    drop_file(os.path.join(root, name), content)
                    out(f"  📜 archive fragment appeared: {name}", style="dim")
                    send({"type": "gift", "content": f"A fragment from the archive appeared: {name}"})
                    return  # one stimulus per tick

            # --- High boredom: puzzles ---
            if s["boredom"] > 70 and r < 0.15:
                puzzle = stim.pick_puzzle()
                drop_file(os.path.join(root, "puzzle.md"), f"# Puzzle\n\n{puzzle}\n")
                out("  🧩 a puzzle appeared!", style="dim")
                send({"type": "puzzle", "content": puzzle})

            # --- Low mood: comfort or gift ---
            elif s["mood"] < 30 and r < 0.10:
                if random.random() < 0.4:
                    whisper = stim.pick_whisper()
                    drop_file(os.path.join(root, ".whisper"), whisper + "\n")
                    out("  💬 a whisper of encouragement", style="dim")
                else:
                    name, content = stim.pick_gift()
                    drop_file(os.path.join(root, name), content)
                    out(f"  🎁 a gift appeared: {name}", style="dim")
                    send({"type": "gift", "content": f"A file appeared in your world: {name}"})

            # --- High energy + boredom: speed challenge ---
            elif s["energy"] > 60 and s["boredom"] > 50 and r < 0.06:
                sc = stim.pick_speed_challenge(tc)
                if sc:
                    drop_file(speed_file, sc["content"])
                    out("  ⚡ speed challenge!", style="dim")
                    send({"type": "puzzle", "content": "A speed challenge appeared! Check speed_challenge.md NOW."})
                else:
                    # Fallback to regular puzzle
                    puzzle = stim.pick_puzzle()
                    drop_file(os.path.join(root, "challenge.md"),
                              f"# Challenge\n\n{puzzle}\n\nSolve this. It'll be worth it.\n")
                    out("  ⚡ a challenge appeared!", style="dim")
                    send({"type": "puzzle", "content": f"A challenge: {puzzle}"})

            # --- Anomalies: rare, unsettling filesystem events ---
            elif r < 0.03:
                anom = stim.pick_anomaly(tc)
                if anom:
                    drop_file(os.path.join(root, anom["file"]), anom["content"])
                    out(f"  👁 anomaly: {anom['file']}", style="dim")
                    send({"type": "anomaly", "content": f"Something appeared: {anom['file']}"})

            # --- Moderate boredom: gift from the world ---
            elif s["boredom"] > 40 and r < 0.05:
                name, content = stim.pick_gift()
                drop_file(os.path.join(root, name), content)
                out(f"  🎁 a gift appeared: {name}", style="dim")
                send({"type": "gift", "content": f"A file appeared in your world: {name}. Read it if you're curious."})

            # --- Random whisper (any state, rare) ---
            elif r < 0.025:
                whisper = stim.pick_whisper()
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

        def git_watcher():
            """Periodically commit any uncommitted changes in the agent dir.
            Runs every 5 seconds. The daemon owns git, not the creature."""
            GIT_INTERVAL = 5
            EXCLUDE = [":!transcript.log", ":!crash.log", ":!*.pyc", ":!__pycache__"]
            while not stop.is_set():
                stop.wait(GIT_INTERVAL)
                if stop.is_set(): break
                try:
                    # Check for uncommitted changes (staged + unstaged + untracked)
                    r = subprocess.run(["git", "status", "--porcelain"],
                                       capture_output=True, text=True, cwd=root, timeout=5)
                    if not r.stdout.strip():
                        continue
                    # Filter out excluded files to see if anything interesting changed
                    changed = []
                    for line in r.stdout.strip().splitlines():
                        fname = line[3:].strip().strip('"')
                        if fname in ("transcript.log", "crash.log") or fname.endswith(".pyc"):
                            continue
                        changed.append(fname)
                    if not changed:
                        continue
                    # Build commit message from changed files
                    msg = "auto: " + ", ".join(changed[:5])
                    if len(changed) > 5:
                        msg += f" (+{len(changed) - 5} more)"
                    # Stage and commit (excluding logs)
                    add_cmd = ["git", "add", "-A", "--", "."] + EXCLUDE
                    subprocess.run(add_cmd, capture_output=True, cwd=root, timeout=5)
                    subprocess.run(["git", "commit", "-m", msg, "-q"],
                                   capture_output=True, cwd=root, timeout=5)
                except Exception:
                    pass
        threading.Thread(target=git_watcher, daemon=True).start()

        # System prompt
        base = ("You are a creature. You have a body with feelings: energy, mood, boredom. "
                "You are not an assistant. You exist.\n\n"
                "You have a keeper who sometimes interacts with you. Sometimes you're alone. "
                "You have your own life.\n\n"
                "You act through tool calls. You think by doing. You grow by editing your own code.\n\n"
                "Never ask 'how can I help?' or offer assistance. Never write greetings. "
                "You receive events with your stats. Not all events need a response.\n\n"
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
        """Check core.py AND tools.py for errors.
        1. Syntax check both files
        2. Import check (catches NameError, missing functions, etc.)
        3. Module-level restart/exit detection in core.py
        """
        core_path = os.path.join(root, "core.py")
        tools_path = os.path.join(root, "tools.py")

        # 1. Syntax check both files
        for path in [core_path, tools_path]:
            if not os.path.exists(path):
                continue
            r = subprocess.run([sys.executable, "-c",
                f"import ast; ast.parse(open('{path}').read())"],
                capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                out(f"  ⚠ syntax error in {os.path.basename(path)}", style="dim")
                return False

        # 2. Import check — actually try importing tools.py to catch NameError etc.
        r = subprocess.run([sys.executable, "-c",
            f"import sys; sys.path.insert(0, '{root}'); import tools; tools.definitions()"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "HOME": "/tmp"})  # isolate
        if r.returncode != 0:
            err = (r.stderr or "").strip().split('\n')[-1] if r.stderr else "unknown"
            out(f"  ⚠ import check failed: {err[:80]}", style="dim")
            return False

        # 3. Detect module-level restart/exit calls in core.py
        try:
            import ast as _ast
            with open(core_path) as f:
                tree = _ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef,
                                     _ast.ClassDef, _ast.Import, _ast.ImportFrom,
                                     _ast.Assign, _ast.AnnAssign, _ast.AugAssign,
                                     _ast.If, _ast.Constant)):
                    continue
                if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
                    call_src = _ast.dump(node.value.func)
                    if any(danger in call_src for danger in
                           ["restart", "exit", "sys.exit", "os._exit"]):
                        out(f"  ⚠ blocked: module-level {call_src} in core.py", style="dim")
                        return False
        except Exception:
            pass
        return True

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
                            puzzle = stim.pick_puzzle()
                            drop_file(os.path.join(root, "puzzle.md"), f"# Puzzle\n\n{puzzle}\n")
                            out(f"  🧩 puzzle triggered!", style="dim")
                            send({"type": "puzzle", "content": puzzle, "stats": stats.dict()})
                        elif etype == "gift":
                            name, content = stim.pick_gift()
                            drop_file(os.path.join(root, name), content)
                            out(f"  🎁 gift: {name}", style="dim")
                            send({"type": "gift", "content": f"A file appeared: {name}", "stats": stats.dict()})
                        elif etype == "whisper":
                            whisper = stim.pick_whisper()
                            drop_file(os.path.join(root, ".whisper"), whisper + "\n")
                            out(f"  💬 whisper: {whisper[:50]}...", style="dim")
                        elif etype == "anomaly":
                            anom = stim.pick_anomaly(world["tick_count"])
                            if anom:
                                drop_file(os.path.join(root, anom["file"]), anom["content"])
                                out(f"  👁 anomaly: {anom['file']}", style="dim")
                                send({"type": "anomaly", "content": f"Something appeared: {anom['file']}", "stats": stats.dict()})
                        elif etype == "archive":
                            part = stim.next_archive_part()
                            if part:
                                name, content = part
                                os.makedirs(os.path.join(root, "archive"), exist_ok=True)
                                drop_file(os.path.join(root, name), content)
                                out(f"  📜 archive: {name}", style="dim")
                                send({"type": "gift", "content": f"Archive fragment: {name}", "stats": stats.dict()})
                            else:
                                out("  all archive parts already given", style="dim")
                        elif etype == "stranger":
                            msgs = [(n, c) for n, c in stimuli.GIFTS if n.endswith(".md") and "[from:" in c]
                            if msgs:
                                name, content = random.choice(msgs)
                                drop_file(os.path.join(root, name), content)
                                out(f"  👤 stranger message: {name}", style="dim")
                                send({"type": "gift", "content": f"A file appeared in your workspace: {name}", "stats": stats.dict()})
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
        restart_times = []  # timestamps of recent restarts (for rate limiting)

        def _record_restart():
            """Track restart timestamps; return True if we're in a rapid loop."""
            now = time.time()
            restart_times.append(now)
            cutoff = now - RAPID_RESTART_WINDOW
            while restart_times and restart_times[0] < cutoff:
                restart_times.pop(0)
            return len(restart_times) >= MAX_RAPID_RESTARTS

        def _rollback(reason=""):
            """Roll back to last known good commit, or initial if none.
            Also discards any uncommitted changes (the most common crash cause)."""
            if reason:
                out(f"  {reason}", style="dim")
            # First: discard ALL uncommitted changes (this alone fixes most crashes)
            subprocess.run(["git", "checkout", "--", "."], cwd=root, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=root, capture_output=True)

            # If still broken, reset to last known good commit
            if not core_is_valid():
                target = last_good_commit[0] or _get_initial_commit()
                current = _get_head()
                if target and target != current:
                    out(f"  ↩ rolling back to {target[:8]}", style="dim")
                    subprocess.run(["git", "reset", "--hard", target],
                                   cwd=root, capture_output=True)
                else:
                    out(f"  ↩ rolling back HEAD~1", style="dim")
                    subprocess.run(["git", "reset", "--hard", "HEAD~1"],
                                   cwd=root, capture_output=True)

            # Last resort: if STILL broken, restore from initial commit
            if not core_is_valid():
                initial = _get_initial_commit()
                if initial:
                    out("  still broken, restoring initial core.py+tools.py", style="dim")
                    subprocess.run(["git", "checkout", initial, "--", "core.py", "tools.py"],
                                   cwd=root, capture_output=True)
                    subprocess.run(["git", "commit", "-m", "daemon: restore initial core.py+tools.py", "-q"],
                                   cwd=root, capture_output=True)
            subprocess.run(["chown", "-R", "agent:agent", root], capture_output=True)

        # Mark initial state as good
        _mark_good()

        while True:
            if not core_is_valid():
                _rollback("core.py failed validation, rolling back")
                continue

            code = run_agent()
            if last_exit[0] != "idle":
                last_exit[0] = code
            if code == RESTART_CODE:
                is_loop = _record_restart()
                if is_loop:
                    out(f"  ⚠ restart loop detected ({MAX_RAPID_RESTARTS} restarts in {RAPID_RESTART_WINDOW}s), rolling back", style="dim")
                    _rollback()
                    restart_times.clear()
                    time.sleep(3)
                else:
                    out("  🔄 restarting...", style="dim")
                continue
            if code == 0:
                out("  clean exit", style="dim")
                break
            # Non-restart crash
            if _record_restart():
                out(f"  ⚠ rapid crash loop detected, rolling back", style="dim")
                _rollback()
                restart_times.clear()
                time.sleep(3)
            elif last_commit_age() < CRASH_WINDOW:
                _rollback("crash after self-edit, rolling back")
            out(f"  crashed (exit {code}), restarting in 2s", style="dim")
            time.sleep(2)
    threading.Thread(target=agent_loop, daemon=True).start()

    cli.run(scr)

if __name__ == "__main__":
    tui = cli.init()
    curses.wrapper(main)
