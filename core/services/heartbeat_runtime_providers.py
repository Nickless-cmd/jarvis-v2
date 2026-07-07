"""Concrete heartbeat provider-executor bodies extracted from ``heartbeat_runtime``.

Behavior-preserving split (Boy-Scout rule). Each function performs a single
provider HTTP dispatch and returns the normalized execution dict.

Monkeypatch-seam preservation: the sibling helpers these bodies depend on
(``_estimate_tokens``, ``_load_provider_api_key``, ``_http_error_detail``,
``_extract_openai_text``, ``_extract_openrouter_text``) are resolved lazily
through the :mod:`core.services.heartbeat_runtime` facade module at call time,
so tests that ``monkeypatch.setattr(heartbeat_runtime, ...)`` still take effect
even though the caller lives in this submodule. These functions are re-exported
from ``heartbeat_runtime`` so ``heartbeat_runtime.<name>`` imports/patches keep
working unchanged.
"""

from __future__ import annotations

import json
from urllib import error as urllib_error
from urllib import request as urllib_request


def _execute_ollama_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    from core.services import heartbeat_runtime as _hb

    base_url = target["base_url"] or "http://127.0.0.1:11434"
    payload = {
        "model": target["model"],
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.7,
            # 512 trunkerede beslutnings-JSON'en når reasoning-modeller (glm/deepseek)
            # emitterede thinking-præambel før objektet → "Unterminated JSON object"
            # → parse-fejl → regel-baseret fallback (13/16 fejl over 5 dage, 29. jun).
            "num_predict": 1536,
        },
    }
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        detail = _hb._http_error_detail(exc)
        raise RuntimeError(f"ollama-http-error:{exc.code}:{detail}") from exc
    except (urllib_error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("ollama-request-failed") from exc
    text = str(data.get("response") or "").strip()
    if not text:
        raise RuntimeError("Heartbeat ollama execution returned no response")
    return {
        "text": text,
        "input_tokens": int(data.get("prompt_eval_count") or _hb._estimate_tokens(prompt)),
        "output_tokens": int(data.get("eval_count") or _hb._estimate_tokens(text)),
        "cost_usd": 0.0,
        "execution_status": "success",
    }


def _execute_openai_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    from core.services import heartbeat_runtime as _hb

    api_key = _hb._load_provider_api_key(provider="openai", profile=target["auth_profile"])
    base_url = target["base_url"] or "https://api.openai.com/v1"
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/responses",
        data=json.dumps({"model": target["model"], "input": prompt}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = _hb._extract_openai_text(data)
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": int(usage.get("input_tokens", _hb._estimate_tokens(prompt))),
        "output_tokens": int(usage.get("output_tokens", _hb._estimate_tokens(text))),
        "cost_usd": 0.0,
    }


def _execute_openrouter_prompt(
    *, prompt: str, target: dict[str, str]
) -> dict[str, object]:
    from core.services import heartbeat_runtime as _hb

    api_key = _hb._load_provider_api_key(
        provider="openrouter", profile=target["auth_profile"]
    )
    base_url = target["base_url"] or "https://openrouter.ai/api/v1"
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": target["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = _hb._extract_openrouter_text(data)
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or _hb._estimate_tokens(prompt)
        ),
        "output_tokens": int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or _hb._estimate_tokens(text)
        ),
        "cost_usd": 0.0,
    }


def _execute_groq_prompt(*, prompt: str, target: dict[str, str]) -> dict[str, object]:
    from core.services import heartbeat_runtime as _hb

    api_key = _hb._load_provider_api_key(provider="groq", profile=target["auth_profile"])
    base_url = target["base_url"] or "https://api.groq.com/openai/v1"
    req = urllib_request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": target["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 1536,  # var 512 → trunkerede beslutnings-JSON (29. jun)
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = str(
        (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
    ).strip()
    if not text:
        raise RuntimeError("Heartbeat groq execution returned no response")
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": int(usage.get("prompt_tokens") or _hb._estimate_tokens(prompt)),
        "output_tokens": int(usage.get("completion_tokens") or _hb._estimate_tokens(text)),
        "cost_usd": 0.0,
        "execution_status": "success",
    }


__all__ = [
    "_execute_ollama_prompt",
    "_execute_openai_prompt",
    "_execute_openrouter_prompt",
    "_execute_groq_prompt",
]
