#!/usr/bin/env python3
"""
The window between you and your creature.
Three panels: creature display, stats, activity log.
"""
import curses, os, subprocess, threading, time

ROOT = os.environ.get("AGENT_DIR", "/agent")

# ─── Creature ASCII art ─────────────────────────────────────────

CREATURE_HAPPY = [
    r"    /\_/\       ",
    r"   ( ◕‿◕ )   ♪ ",
    r"    />o<\       ",
    r"   (_/ \_)      ",
]

CREATURE_CONTENT = [
    r"    /\_/\       ",
    r"   ( ●_● )      ",
    r"    />·<\       ",
    r"   (_/ \_)      ",
]

CREATURE_TIRED = [
    r"    /\_/\       ",
    r"   ( ˘_˘ )   ~  ",
    r"    />·<\       ",
    r"   (_/ \_)      ",
]

CREATURE_BORED = [
    r"    /\_/\    ?  ",
    r"   ( ◉_  )      ",
    r"    />~<\    ?  ",
    r"   (_/ \_)      ",
]

CREATURE_SAD = [
    r"    /\_/\       ",
    r"   ( ╥_╥ )      ",
    r"    />n<\       ",
    r"   (_/ \_)      ",
]

CREATURE_SLEEPING = [
    r"    /\_/\    z  ",
    r"   ( ˘‿˘ ) Z    ",
    r"    />·<\z      ",
    r"   (____) zzz   ",
]

CREATURE_DORMANT = [
    r"    /\_/\       ",
    r"   ( ·_· )      ",
    r"    /   \       ",
    r"   (____) ...   ",
]

def pick_creature(stats):
    """Choose creature art based on current stats."""
    energy = stats.get("energy", 50)
    mood = stats.get("mood", 50)
    boredom = stats.get("boredom", 50)

    if energy <= 0 and mood <= 0:
        return CREATURE_DORMANT
    if energy <= 0:
        return CREATURE_SLEEPING
    if energy < 20:
        return CREATURE_TIRED
    if mood < 20:
        return CREATURE_SAD
    if boredom > 70:
        return CREATURE_BORED
    if mood > 60 and energy > 50:
        return CREATURE_HAPPY
    return CREATURE_CONTENT


# ─── Stats bar rendering ────────────────────────────────────────

def stat_bar(label, value, width, color_pair):
    """Return (text, [(start, len, attr)]) for a stat bar."""
    label_str = f" {label:7s} "
    bar_width = width - len(label_str) - 6  # space for " XXX "
    if bar_width < 4: bar_width = 4
    filled = int(value / 100 * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    num_str = f" {value:3d}"
    full = label_str + bar + num_str
    return full, color_pair


# ─── TUI class ───────────────────────────────────────────────────

class TUI:
    def __init__(self):
        self.lines = []
        self.input_buf = ""
        self.cursor = 0
        self.scroll = 0
        self.lock = threading.Lock()
        self.scr = None
        self.running = True
        self.input_ready = threading.Event()
        self.input_result = None
        self.history = []
        self.hist_idx = -1
        self.status_text = ""
        self.stats = {"energy": 50, "mood": 50, "boredom": 0}
        self.creature_name = "creature"
        self.tick_count = 0
        self.age_start = time.time()
        self.state = "idle"

    def start(self, scr):
        self.scr = scr
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)       # input prompt
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # status bar
        curses.init_pair(3, curses.COLOR_YELLOW, -1)      # dim/system
        curses.init_pair(4, curses.COLOR_GREEN, -1)       # user/keeper
        curses.init_pair(5, curses.COLOR_BLUE, -1)        # command output
        curses.init_pair(6, curses.COLOR_GREEN, -1)       # energy bar
        curses.init_pair(7, curses.COLOR_MAGENTA, -1)     # mood bar
        curses.init_pair(8, curses.COLOR_RED, -1)         # boredom bar
        curses.init_pair(9, curses.COLOR_WHITE, -1)       # creature
        curses.init_pair(10, curses.COLOR_CYAN, -1)       # box drawing
        curses.curs_set(1)
        scr.timeout(100)
        scr.keypad(True)
        self.add_line("🥚 tamagotchi", style="dim")
        self.add_line("/help for commands", style="dim")
        self.add_line("", style="dim")
        self._loop()

    def _format_age(self):
        elapsed = int(time.time() - self.age_start)
        days, rem = divmod(elapsed, 86400)
        hours, rem = divmod(rem, 3600)
        mins, _ = divmod(rem, 60)
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    def add_line(self, text, style=None):
        text = ''.join(c if c == '\t' or (ord(c) >= 32 or c == '\n') else '?' for c in str(text))
        text = text.replace('\t', '    ')
        with self.lock:
            self.lines.append((text, style))
            if self.scroll > 0:
                self.scroll += 1
        self._redraw()

    def set_status(self, text):
        self.status_text = text
        self._redraw()

    def set_stats(self, stats):
        with self.lock:
            self.stats = dict(stats)
        self._redraw()

    def set_tick(self, tick):
        self.tick_count = tick
        self._redraw()

    def set_state(self, state):
        self.state = state
        self._redraw()

    def _draw_box_top(self, y, w):
        try:
            self.scr.addstr(y, 0, "╭" + "─" * (w - 2) + "╮", curses.color_pair(10))
        except curses.error:
            pass

    def _draw_box_mid(self, y, w):
        try:
            self.scr.addstr(y, 0, "├" + "─" * (w - 2) + "┤", curses.color_pair(10))
        except curses.error:
            pass

    def _draw_box_bot(self, y, w):
        try:
            self.scr.addstr(y, 0, "╰" + "─" * (w - 2) + "╯", curses.color_pair(10))
        except curses.error:
            pass

    def _draw_box_line(self, y, w, text, attr=0):
        """Draw a line with box borders: │ text │"""
        try:
            self.scr.addstr(y, 0, "│", curses.color_pair(10))
            inner = text[:w - 2].ljust(w - 2)
            self.scr.addstr(y, 1, inner, attr)
            self.scr.addstr(y, w - 1, "│", curses.color_pair(10))
        except curses.error:
            pass

    def _draw_stat_bar(self, y, w, label, value, cpair):
        """Draw a stat bar inside box borders."""
        inner_w = w - 2
        label_str = f" {label:7s} "
        bar_w = inner_w - len(label_str) - 5
        if bar_w < 4: bar_w = 4
        filled = int(value / 100 * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        num_str = f" {value:3d} "
        full = label_str + bar + num_str

        try:
            self.scr.addstr(y, 0, "│", curses.color_pair(10))
            # Label
            self.scr.addstr(y, 1, label_str, curses.color_pair(cpair) | curses.A_BOLD)
            # Bar
            col = 1 + len(label_str)
            # Filled part
            self.scr.addstr(y, col, "█" * filled, curses.color_pair(cpair))
            # Empty part
            self.scr.addstr(y, col + filled, "░" * (bar_w - filled), curses.color_pair(3))
            # Number
            self.scr.addstr(y, col + bar_w, num_str, curses.color_pair(cpair))
            # Right border
            endcol = 1 + len(full)
            if endcol < w - 1:
                self.scr.addstr(y, w - 1, "│", curses.color_pair(10))
        except curses.error:
            pass

    def _redraw(self):
        if not self.scr: return
        with self.lock:
            try:
                self.scr.erase()
                h, w = self.scr.getmaxyx()
                if h < 10 or w < 30:
                    self.scr.addstr(0, 0, "terminal too small")
                    self.scr.refresh()
                    return

                row = 0

                # ─── Creature area ───
                creature = pick_creature(self.stats)
                creature_height = len(creature) + 2  # +2 for borders

                self._draw_box_top(row, w); row += 1
                for line in creature:
                    # Center the creature
                    padded = line.center(w - 2)
                    self._draw_box_line(row, w, padded, curses.color_pair(9))
                    row += 1

                # ─── Stats area ───
                self._draw_box_mid(row, w); row += 1
                self._draw_stat_bar(row, w, "energy", self.stats.get("energy", 50), 6)
                row += 1
                self._draw_stat_bar(row, w, "mood", self.stats.get("mood", 50), 7)
                row += 1
                self._draw_stat_bar(row, w, "boredom", self.stats.get("boredom", 0), 8)
                row += 1

                # ─── Activity log ───
                self._draw_box_mid(row, w); row += 1

                # Status bar row (at bottom of box)
                # Input row (very bottom)
                # Box bottom border
                # So: log area = h - row - 4 (status + box_bottom + input + 1 safety)
                log_height = h - row - 3
                if log_height < 1: log_height = 1

                # Render log lines
                total = len(self.lines)
                end = total - self.scroll
                if end <= 0:
                    visible = []
                else:
                    visible = []
                    rows_used = 0
                    inner_w = w - 2
                    for idx in range(end - 1, -1, -1):
                        text, style = self.lines[idx]
                        line_h = max(1, (len(text) + inner_w - 1) // inner_w) if text else 1
                        if rows_used + line_h > log_height:
                            break
                        visible.insert(0, (text, style))
                        rows_used += line_h

                log_row = row
                for text, style in visible:
                    if log_row >= row + log_height: break
                    # Word-wrap within box
                    inner_w = w - 2
                    chunks = []
                    while len(text) > inner_w:
                        chunks.append(text[:inner_w])
                        text = text[inner_w:]
                    chunks.append(text)
                    for chunk in chunks:
                        if log_row >= row + log_height: break
                        attr = 0
                        if style == "dim": attr = curses.color_pair(3)
                        elif style == "bold": attr = curses.A_BOLD
                        elif style == "user": attr = curses.color_pair(4)
                        elif style == "cmd": attr = curses.color_pair(5)
                        self._draw_box_line(log_row, w, " " + chunk, attr)
                        log_row += 1

                # Fill remaining log space with empty box lines
                while log_row < row + log_height:
                    self._draw_box_line(log_row, w, "")
                    log_row += 1

                row = log_row

                # ─── Status bar ───
                age = self._format_age()
                state = self.state or "idle"
                status_info = f" {state} · tick {self.tick_count} · age {age}"
                if self.status_text:
                    status_info += f" · {self.status_text}"
                self._draw_box_line(row, w, status_info, curses.color_pair(2))
                row += 1

                # ─── Bottom border ───
                self._draw_box_bot(row, w)
                row += 1

                # ─── Input line ───
                input_y = min(row, h - 1)
                prompt = "› "
                display = prompt + self.input_buf
                try:
                    self.scr.addstr(input_y, 0, display[:w - 1], curses.color_pair(1))
                    cx = len(prompt) + self.cursor
                    if cx < w:
                        self.scr.move(input_y, cx)
                except curses.error:
                    pass

                # Scroll indicator
                if self.scroll > 0:
                    indicator = f" ↑ {self.scroll} more "
                    try:
                        self.scr.addstr(row - log_height, w - len(indicator) - 2, indicator, curses.color_pair(3))
                    except curses.error:
                        pass

                self.scr.refresh()
            except curses.error:
                pass

    def _max_log_lines(self):
        h, w = self.scr.getmaxyx()
        return max(1, h - 16)

    def _loop(self):
        while self.running:
            try:
                ch = self.scr.getch()
            except curses.error:
                continue

            if ch == -1: continue
            elif ch == curses.KEY_RESIZE:
                self._redraw()
            elif ch in (curses.KEY_ENTER, 10, 13):
                line = self.input_buf.strip()
                self.input_buf = ""
                self.cursor = 0
                self.scroll = 0
                if line:
                    if not self.history or self.history[-1] != line:
                        self.history.append(line)
                    self.hist_idx = -1
                    self.input_result = line
                    self.input_ready.set()
                self._redraw()
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                if self.cursor > 0:
                    self.input_buf = self.input_buf[:self.cursor-1] + self.input_buf[self.cursor:]
                    self.cursor -= 1
                    self._redraw()
            elif ch == curses.KEY_DC:
                if self.cursor < len(self.input_buf):
                    self.input_buf = self.input_buf[:self.cursor] + self.input_buf[self.cursor+1:]
                    self._redraw()
            elif ch == curses.KEY_LEFT:
                if self.cursor > 0: self.cursor -= 1; self._redraw()
            elif ch == curses.KEY_RIGHT:
                if self.cursor < len(self.input_buf): self.cursor += 1; self._redraw()
            elif ch == curses.KEY_HOME or ch == 1:
                self.cursor = 0; self._redraw()
            elif ch == curses.KEY_END or ch == 5:
                self.cursor = len(self.input_buf); self._redraw()
            elif ch == curses.KEY_UP:
                if self.history and self.hist_idx < len(self.history) - 1:
                    self.hist_idx += 1
                    self.input_buf = self.history[-(self.hist_idx + 1)]
                    self.cursor = len(self.input_buf)
                    self._redraw()
            elif ch == curses.KEY_DOWN:
                if self.hist_idx > 0:
                    self.hist_idx -= 1
                    self.input_buf = self.history[-(self.hist_idx + 1)]
                    self.cursor = len(self.input_buf)
                elif self.hist_idx == 0:
                    self.hist_idx = -1
                    self.input_buf = ""; self.cursor = 0
                self._redraw()
            elif ch == curses.KEY_PPAGE:
                self.scroll = min(len(self.lines) - self._max_log_lines(), self.scroll + self._max_log_lines())
                if self.scroll < 0: self.scroll = 0
                self._redraw()
            elif ch == curses.KEY_NPAGE:
                self.scroll = max(0, self.scroll - self._max_log_lines())
                self._redraw()
            elif ch == 21:  # ctrl-u
                self.input_buf = ""; self.cursor = 0; self._redraw()
            elif ch == 11:  # ctrl-k
                self.input_buf = self.input_buf[:self.cursor]; self._redraw()
            elif 32 <= ch <= 126:
                self.input_buf = self.input_buf[:self.cursor] + chr(ch) + self.input_buf[self.cursor:]
                self.cursor += 1
                self._redraw()

    def wait_input(self):
        self.input_ready.wait()
        self.input_ready.clear()
        return self.input_result

    def reset(self):
        with self.lock:
            self.lines = []
            self.scroll = 0
            self.input_buf = ""
            self.cursor = 0
        try:
            self.scr.clear()
            self.scr.refresh()
            curses.endwin()
            self.scr = curses.initscr()
            curses.noecho(); curses.cbreak()
            self.scr.keypad(True)
            curses.start_color(); curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_GREEN, -1)
            curses.init_pair(5, curses.COLOR_BLUE, -1)
            curses.init_pair(6, curses.COLOR_GREEN, -1)
            curses.init_pair(7, curses.COLOR_MAGENTA, -1)
            curses.init_pair(8, curses.COLOR_RED, -1)
            curses.init_pair(9, curses.COLOR_WHITE, -1)
            curses.init_pair(10, curses.COLOR_CYAN, -1)
            curses.curs_set(1)
            self.scr.timeout(100)
        except: pass
        self.add_line("  tui reset", style="dim")

    def stop(self):
        self.running = False


# ─── Global instance ─────────────────────────────────────────────
_tui = None

def init():
    global _tui
    _tui = TUI()
    return _tui

def run(scr):
    _tui.start(scr)

def add_line(text, style=None):
    if _tui: _tui.add_line(text, style=style)

def set_status(text):
    if _tui: _tui.set_status(text)

def set_stats(stats):
    if _tui: _tui.set_stats(stats)

def set_tick(tick):
    if _tui: _tui.set_tick(tick)

def set_state(state):
    if _tui: _tui.set_state(state)

def wait_input():
    if _tui: return _tui.wait_input()
    return input("› ")

def reset():
    if _tui: _tui.reset()

def stop():
    if _tui: _tui.stop()

def handle_command(cmd):
    """Handle /commands. Returns action tuples or True/False."""
    parts = cmd.strip().split(None, 1)
    if not parts: return False
    verb, arg = parts[0].lower(), parts[1] if len(parts) > 1 else ""

    if verb == "/help":
        add_line("─── keeper commands ───", style="cmd")
        add_line("  /feed           feed your creature (+energy)", style="cmd")
        add_line("  /play           play with your creature (-boredom +mood)", style="cmd")
        add_line("  /pet            pet your creature (+mood)", style="cmd")
        add_line("  /talk <msg>     talk to your creature", style="cmd")
        add_line("  /teach <topic>  teach something (-boredom)", style="cmd")
        add_line("  /name <name>    name your creature", style="cmd")
        add_line("  /look           what's the creature doing?", style="cmd")
        add_line("  /stats          show current stats", style="cmd")
        add_line("  /say <msg>      inject directly into creature's mind", style="cmd")
        add_line("  /event <type>   trigger an environmental event", style="cmd")
        add_line("─── observe ───", style="cmd")
        add_line("  /verbose        live transcript tail", style="cmd")
        add_line("  /quiet          stop live transcript", style="cmd")
        add_line("  /log [n]        last n transcript lines", style="cmd")
        add_line("  /diff           changes since init", style="cmd")
        add_line("─── debug ───", style="cmd")
        add_line("  /files [path]   list workspace files", style="cmd")
        add_line("  /cat <file>     show file contents", style="cmd")
        add_line("  /git [args]     run git command", style="cmd")
        add_line("  /tree           workspace tree", style="cmd")
        add_line("  /reset          reinit the TUI (fixes garbled display)", style="cmd")
        add_line("  /reboot         restart the creature", style="cmd")
        add_line("  /quit           stop everything", style="cmd")
    elif verb == "/quit":
        return "quit"
    elif verb == "/reset":
        return ("reset",)
    elif verb == "/reboot":
        return ("reboot",)
    elif verb == "/say":
        if not arg:
            add_line("  usage: /say <message>", style="dim")
            return True
        return ("say", arg)
    elif verb == "/event":
        if not arg:
            add_line("  events: puzzle, gift, whisper, stranger, arrived, departed", style="dim")
            return True
        return ("event", arg)
    elif verb == "/verbose":
        return ("verbose",)
    elif verb == "/quiet":
        return ("quiet",)
    elif verb == "/feed":
        return ("feed",)
    elif verb == "/play":
        return ("play", arg or "Let's play!")
    elif verb == "/pet":
        return ("pet",)
    elif verb == "/talk":
        if not arg:
            add_line("  usage: /talk <message>", style="dim")
            return True
        return ("talk", arg)
    elif verb == "/teach":
        if not arg:
            add_line("  usage: /teach <topic>", style="dim")
            return True
        return ("teach", arg)
    elif verb == "/name":
        if not arg:
            add_line("  usage: /name <name>", style="dim")
            return True
        return ("name", arg)
    elif verb == "/look":
        return ("look",)
    elif verb == "/stats":
        return ("show_stats",)
    elif verb == "/files":
        path = os.path.join(ROOT, arg) if arg else ROOT
        try:
            for e in sorted(os.listdir(path)):
                if e.startswith(".") or e == "__pycache__": continue
                name = f"  {e}/" if os.path.isdir(os.path.join(path, e)) else f"  {e}"
                add_line(name, style="cmd")
        except Exception as e:
            add_line(f"  error: {e}", style="dim")
    elif verb == "/cat":
        if not arg:
            add_line("  usage: /cat <file>", style="dim")
            return True
        try:
            with open(os.path.join(ROOT, arg)) as f: content = f.read()
            add_line(f"─── {arg} ───", style="cmd")
            for line in content.rstrip().splitlines():
                add_line(f"  {line}", style="cmd")
            add_line("───", style="cmd")
        except Exception as e:
            add_line(f"  error: {e}", style="dim")
    elif verb == "/git":
        r = subprocess.run(f"git {arg or 'log --oneline -20'}", shell=True,
                          capture_output=True, text=True, cwd=ROOT)
        for line in (r.stdout or "(no output)").rstrip().splitlines():
            add_line(f"  {line}", style="cmd")
    elif verb == "/diff":
        parts = []
        r1 = subprocess.run("git diff --stat $(git rev-list --max-parents=0 HEAD)..HEAD 2>/dev/null",
                           shell=True, capture_output=True, text=True, cwd=ROOT)
        if r1.stdout and r1.stdout.strip():
            parts.append("committed:")
            parts.extend(f"  {l}" for l in r1.stdout.strip().splitlines())
        r2 = subprocess.run("git diff --stat HEAD 2>/dev/null",
                           shell=True, capture_output=True, text=True, cwd=ROOT)
        untracked = subprocess.run("git ls-files --others --exclude-standard 2>/dev/null",
                                   shell=True, capture_output=True, text=True, cwd=ROOT)
        wt = []
        if r2.stdout and r2.stdout.strip():
            wt.extend(r2.stdout.strip().splitlines())
        if untracked.stdout and untracked.stdout.strip():
            wt.extend(f"{f} (new)" for f in untracked.stdout.strip().splitlines())
        if wt:
            parts.append("uncommitted:")
            parts.extend(f"  {l}" for l in wt)
        if not parts:
            parts.append("(no changes)")
        for line in parts:
            add_line(f"  {line}", style="cmd")
    elif verb == "/tree":
        r = subprocess.run("find . -not -path './.git/*' -not -path './.git' "
                          "-not -path './__pycache__/*' -not -name __pycache__ | sort | tail -n+2",
                          shell=True, capture_output=True, text=True, cwd=ROOT)
        for line in (r.stdout or "(empty)").rstrip().splitlines():
            add_line(f"  {line}", style="cmd")
    elif verb == "/log":
        n = int(arg) if arg else 20
        try:
            with open(os.path.join(ROOT, "transcript.log")) as f: lines = f.readlines()
            for line in lines[-n:]:
                line = line.rstrip()
                if "] system:" in line or "] stdin:" in line:
                    add_line(f"  {line}", style="bold")
                elif "] assistant:" in line:
                    add_line(f"  {line}", style="cmd")
                else:
                    add_line(f"  {line}", style="cmd")
        except FileNotFoundError:
            add_line("  no transcript yet", style="dim")
    else:
        return False
    return True
