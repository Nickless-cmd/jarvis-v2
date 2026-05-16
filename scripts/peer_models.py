"""Peer model adapters for interlanguage validation experiment.

Hver peer kalder generate(prompt, peer_id) og får et expression-string
tilbage. Adapter-laget abstraherer model-API-forskelle.

Modelvalg (2026-05-16):
- claude / claude_jp: claude-sonnet-4.6 via GitHub Copilot proxy
  (Anthropic-arkitektur, anden end Jarvis' deepseek)
- glm / glm_jp: glm-5.1:cloud via lokal Ollama
  (Zhipu-arkitektur, anden end Jarvis OG Claude)
- ollama_local: deepseek-v4-flash:cloud via lokal Ollama
  (samme arkitektur som Jarvis — kontrol for arkitektur-effekt)
- random: generate_state_expression() uden mood-bias (gulv-baseline)

Spec: docs/superpowers/specs/2026-05-16-interlanguage-validation-design.md
"""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Callable

logger = logging.getLogger("peer_models")

OLLAMA_LOCALHOST = "http://127.0.0.1:11434"
COPILOT_PROFILE = "copilot"


# ---------------------------------------------------------------------------
# Claude via GitHub Copilot proxy
# ---------------------------------------------------------------------------

def _generate_claude(prompt: str) -> str:
    """Claude Sonnet 4.6 via GitHub Copilot.

    Bruger _post_github_copilot_chat_completion fra eksisterende
    non_visible_lane_execution-service (samme route som Jarvis selv
    bruger ved cheap-lane fallback).
    """
    from core.services.non_visible_lane_execution import (
        _post_github_copilot_chat_completion,
        _extract_github_copilot_text,
    )
    data = _post_github_copilot_chat_completion(
        payload={
            "model": "claude-sonnet-4.6",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": 200,
        },
        profile=COPILOT_PROFILE,
    )
    text = _extract_github_copilot_text(data)
    return (text or "").strip()


# ---------------------------------------------------------------------------
# Ollama localhost — fælles for GLM + deepseek-v4-flash
# ---------------------------------------------------------------------------

def _ollama_chat(model: str, prompt: str, *, timeout: int = 60) -> str:
    """POST mod localhost Ollama /api/chat — virker for cloud-modeller routet via Ollama."""
    req = urllib.request.Request(
        f"{OLLAMA_LOCALHOST}/api/chat",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read())
    msg = body.get("message", {})
    return str(msg.get("content", "")).strip()


def _generate_glm(prompt: str) -> str:
    """GLM 5.1 via lokal Ollama cloud-route."""
    return _ollama_chat("glm-5.1:cloud", prompt)


def _generate_ollama_local(prompt: str) -> str:
    """deepseek-v4-flash:cloud via lokal Ollama (samme model som Jarvis).

    Bemærk: Jarvis selv bruger samme model OG samme endpoint, men i
    en separat session/context — så denne peer tester "samme model,
    forskellig session" vs. "samme model, samme session (Jarvis)".
    """
    return _ollama_chat("deepseek-v4-flash:cloud", prompt)


# ---------------------------------------------------------------------------
# Random baseline — ignorer prompt, gen pure random expression
# ---------------------------------------------------------------------------

def _generate_random(prompt: str) -> str:
    """Random baseline — bruger generate_state_expression() uden mood-bias.

    NB: vi ignorerer prompten helt. Random peer er en "pure-syntax" kontrol
    der viser hvordan tilfældige expressions ser ud uden semantisk forankring.
    """
    from core.services.interlanguage_practice import generate_state_expression
    return generate_state_expression(mood_override=None)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

ADAPTERS: dict[str, Callable[[str], str]] = {
    "claude": _generate_claude,
    "claude_jp": _generate_claude,       # samme adapter, forskellig prompt
    "glm": _generate_glm,
    "glm_jp": _generate_glm,             # samme adapter, forskellig prompt
    "ollama_local": _generate_ollama_local,
    "random": _generate_random,
}


def generate(prompt: str, peer_id: str) -> str:
    """Dispatch til peer-specific adapter. Raise ValueError ved ukendt peer."""
    adapter = ADAPTERS.get(peer_id)
    if adapter is None:
        raise ValueError(f"Unknown peer_id: {peer_id}")
    return adapter(prompt)


if __name__ == "__main__":
    # CLI smoke-test: python scripts/peer_models.py <peer_id>
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <peer_id>  (one of: {sorted(ADAPTERS.keys())})")
        sys.exit(1)
    peer = sys.argv[1]
    prompt = "Reply with exactly 'OK' and nothing else."
    try:
        out = generate(prompt, peer)
        print(f"[{peer}] {out!r}")
    except Exception as exc:
        print(f"[{peer}] ERROR: {type(exc).__name__}: {exc}")
        sys.exit(2)
