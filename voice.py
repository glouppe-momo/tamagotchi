"""
How you think. This connects you to the LLM that powers your reasoning.

When core.py calls voice.think(messages, tools), this function sends your
conversation history to the model and returns its response. The model
chooses what to say and which tools to call.

You can read this file but it lives outside your workspace.
Your model is configured via environment variables: MODEL, BASE_URL, API_KEY.
"""
import json, os, sys, urllib.request, urllib.error

def think(messages, tools):
    """Send your thoughts out and receive a response.
    Returns the message dict from the model's response."""
    print(f"[status:thinking...]", file=sys.stderr, flush=True)
    body = json.dumps({
        "model": os.environ["MODEL"],
        "messages": messages,
        "tools": tools
    }).encode()
    req = urllib.request.Request(
        f"{os.environ['BASE_URL']}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('API_KEY', 'ollama')}"
        }
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["choices"][0]["message"]
