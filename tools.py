"""
Your hands. These are the tools you were born with.

YOU CAN ADD MORE. To add a tool:
  1. Write a function with a docstring (the LLM sees the docstring)
  2. Add it to the TOOLS dict at the bottom with its parameter schema
  3. Call restart() so the new tool becomes available

Every file write/edit auto-commits to git. If you break your own code,
the daemon rolls back to the last working version and restarts you.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))

def read_file(path: str) -> str:
    """Read a file and return its contents. Paths are relative to your workspace (/agent)."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    with open(path) as f: return f.read()

def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates directories if needed.
    Paths are relative to your workspace (/agent).
    Auto-commits to git. If you write broken Python, it gets reverted."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    d = os.path.dirname(path)
    if d: os.makedirs(d, exist_ok=True)
    with open(path, "w") as f: f.write(content)
    if path.endswith(".py"): _check_syntax(path)
    _commit(f"write {os.path.basename(path)}")
    return f"wrote {path}"

def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in a file. Fails if old_text not found.
    Paths are relative to your workspace (/agent).
    Use this for surgical edits to your own code."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    content = read_file(path)
    if old_text not in content: raise ValueError(f"text not found in {path}")
    with open(path, "w") as f: f.write(content.replace(old_text, new_text, 1))
    if path.endswith(".py"): _check_syntax(path)
    _commit(f"edit {os.path.basename(path)}")
    return f"edited {path}"

def shell_exec(command: str, timeout: int = 30) -> str:
    """Run a shell command. Returns stdout+stderr.
    You're in a container. You can install packages, run scripts, etc."""
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"timeout after {timeout}s"

def restart():
    """Restart yourself. Call this after editing core.py or tools.py.
    Your code changes only take effect after a restart.
    Your conversation memory will be lost, but your transcript and files persist."""
    sys.exit(42)

# ─── Internal helpers (not exposed as tools) ─────────────────────

def _check_syntax(path):
    """Validate Python syntax. Reverts and raises if broken."""
    import ast
    try:
        with open(path) as f: ast.parse(f.read())
    except SyntaxError as e:
        subprocess.run(["git", "checkout", "--", path], capture_output=True, cwd=ROOT)
        raise ValueError(f"syntax error in {path} line {e.lineno}: {e.msg}. File reverted.")

def _commit(msg):
    """Auto-commit after file changes. Excludes logs."""
    subprocess.run(f'git add -A -- . ":!transcript.log" ":!crash.log" && git commit -m {json.dumps(msg)} -q',
                   shell=True, capture_output=True, cwd=ROOT)

# ─── Tool registry ───────────────────────────────────────────────
# To add a tool: define the function above, then add an entry here.
# The schema tells the LLM what parameters your tool accepts.

_P = {"type": "object"}
TOOLS = {
    "read_file":  (read_file,  {**_P, "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    "write_file": (write_file, {**_P, "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}),
    "edit_file":  (edit_file,  {**_P, "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}),
    "shell_exec": (shell_exec, {**_P, "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["command"]}),
    "restart":    (restart,    {**_P, "properties": {}}),
}

def definitions():
    """Return tool definitions in the format the LLM expects."""
    return [{"name": n, "description": fn.__doc__, "input_schema": s} for n, (fn, s) in TOOLS.items()]

def run(name, args):
    """Execute a tool by name. Called by the main loop in core.py."""
    if name not in TOOLS: raise ValueError(f"unknown tool: {name}")
    return TOOLS[name][0](**args)
