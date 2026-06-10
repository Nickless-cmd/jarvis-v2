#!/usr/bin/env python3
"""Primary lane cache warmer.

Holder DeepSeek V4 Flash prompt-cachen varm på primary lane
ved at lave et minimalt API-kald hvert N. minut med kun
system prompt + time pin.

DeepSeek's prompt-cache er prefix-baseret. System promptet
er ~100K+ tokens og identisk på tværs af kald. Men hvis der
går timer mellem kald, udløber cachen (TTL = hours to days).

Warmeren holder prefix'et varmt så næste rigtige kald rammer
cache i stedet for at betale fuld pris.

Cost: ~10 output tokens × $0.28/1M = $0.0000028 per kald.
6 kald/timen × 24 timer = ~$0.0004/dag.

Setup som cron-job hver 10. minut (på Jarvis-host):
  */10 * * * * /opt/conda/envs/ai/bin/python3 \\
    /media/projects/jarvis-v2/scripts/primary_cache_warmer.py

Brug:
  python3 scripts/primary_cache_warmer.py           # normalt
  python3 scripts/primary_cache_warmer.py --dry-run  # log uden at kalde API
  python3 scripts/primary_cache_warmer.py --force    # ignorér dedup

Afhængigheder: ingen ud over stdlib + core (valgfri til prompt-hentning).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("cache_warmer")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOME_DIR = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = HOME_DIR / "state" / "jarvis.db"
LOG_PATH = HOME_DIR / "logs" / "cache_warmer.jsonl"
LAST_RUN_PATH = HOME_DIR / "state" / "cache_warmer_last_run.txt"
PROMPT_FILE = HOME_DIR / "config" / "primary_system_prompt.txt"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_MAX_TOKENS = 10
DEFAULT_TEMPERATURE = 0.0
MIN_INTERVAL_SECONDS = 60  # mindst 1 minut mellem kald

# ---------------------------------------------------------------------------
# System prompt — forsøg core, fald tilbage til fil
# ---------------------------------------------------------------------------


def _fetch_system_prompt() -> str | None:
    """Hent primary lane system prompt.

    2026-06-10 (Claude): rewritten til at bruge build_visible_stable_prefix()
    der returnerer NØJAGTIG samme stable prefix som live visible-runs.
    Tidligere snapshot-fil (48K chars) matchede kun 15% af live-prompt.
    Den nye stable-prefix (~4K chars) matcher 100% — DeepSeek cachen
    der varmes op er præcis den cachen Bjørns chat hitter.

    Rækkefølge:
      1. build_visible_stable_prefix() — kanonisk live-matching kilde
      2. Pre-konfigureret fil (legacy fallback hvis core-import fejler)
    """
    # Kanonisk sti: build samme stable prefix som live visible bruger.
    try:
        from core.services.prompt_contract import build_visible_stable_prefix
        prefix = build_visible_stable_prefix(
            provider="deepseek",
            model=DEFAULT_MODEL,
            name="default",
            compact=False,
        )
        if prefix:
            logger.debug(
                "Stable prefix bygget via build_visible_stable_prefix (%d bytes)",
                len(prefix),
            )
            # Save snapshot så vi har visibility ift. hvad der bliver warmed
            try:
                _save_prompt_to_file(prefix)
            except Exception:
                pass
            return prefix
    except Exception as exc:
        logger.debug("build_visible_stable_prefix fejlede: %s", exc)

    # Legacy fallback: pre-konfigureret fil
    if PROMPT_FILE.exists():
        content = PROMPT_FILE.read_text(encoding="utf-8").strip()
        if content:
            logger.warning(
                "Falder tilbage til stale prompt-fil (%d bytes) — "
                "build_visible_stable_prefix fejlede",
                len(content),
            )
            return content

    logger.warning("Ingen system prompt tilgængelig")
    return None


def _save_prompt_to_file(content: str) -> None:
    """Gem prompt til fil så standalone kald kan bruge det senere."""
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PROMPT_FILE.open("w", encoding="utf-8") as f:
        f.write(content)
    logger.debug("Prompt gemt til %s", PROMPT_FILE)


# ---------------------------------------------------------------------------
# Dedup — forhindr for hyppige kald
# ---------------------------------------------------------------------------


def _check_dedup(*, force: bool = False) -> bool:
    """Tjek om et kald er for nyligt.

    Returnerer True hvis kaldet bør **springes over** (dedup activeret).
    """
    if force:
        return False
    if not LAST_RUN_PATH.exists():
        return False
    try:
        last = float(LAST_RUN_PATH.read_text(encoding="utf-8").strip())
        elapsed = time.time() - last
        if elapsed < MIN_INTERVAL_SECONDS:
            logger.info(
                "Dedup: sidste kald var for %.0f sekunder siden (< %s) — springer over",
                elapsed,
                MIN_INTERVAL_SECONDS,
            )
            return True
    except (ValueError, OSError):
        pass
    return False


def _touch_last_run() -> None:
    LAST_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN_PATH.write_text(str(time.time()), encoding="utf-8")


# ---------------------------------------------------------------------------
# API kald
# ---------------------------------------------------------------------------


def _build_payload(system_prompt: str) -> dict[str, Any]:
    """Byg request body til DeepSeek chat completions.

    Kun system prompt + en minimal time pin som user message.
    """
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Cache warmer — {now}"},
        ],
        "max_tokens": DEFAULT_MAX_TOKENS,
        "temperature": DEFAULT_TEMPERATURE,
        "stream": False,
    }


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def _call_api(
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    *,
    timeout_s: int = 30,
) -> dict[str, Any]:
    """Kald DeepSeek chat completions API.

    Returnerer en dict med:
      - status: "ok" | "rate_limited" | "error"
      - cache_hit_tokens / cache_miss_tokens / input_tokens / output_tokens
      - cost_usd
      - error (hvis status != "ok")
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    headers = _build_headers(api_key)

    req = urllib_request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib_request.urlopen(req, timeout=timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        status = exc.code
        body_text = exc.read().decode("utf-8", errors="replace")
        if status == 429:
            return {"status": "rate_limited", "error": body_text}
        return {
            "status": "error",
            "error": f"HTTP {status}: {body_text[:500]}",
        }
    except urllib_error.URLError as exc:
        return {"status": "error", "error": f"URLError: {exc.reason}"}
    except TimeoutError:
        return {"status": "error", "error": "timeout"}
    except json.JSONDecodeError as exc:
        return {"status": "error", "error": f"JSON decode: {exc}"}

    # Parse usage
    usage = body.get("usage", {})
    if not usage:
        return {"status": "error", "error": "ingen usage i response"}

    cache_hit = int(usage.get("prompt_cache_hit_tokens") or 0)
    cache_miss = int(usage.get("prompt_cache_miss_tokens") or 0)
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)

    # DeepSeek V4 Flash pricing (May 2026)
    input_price_per_1m = 0.14
    output_price_per_1m = 0.28
    # Hvis cachen rammer, betaler DeepSeek kun for miss-tokens
    billed_input = max(0, input_tokens - cache_hit)
    cost_usd = (billed_input * input_price_per_1m + output_tokens * output_price_per_1m) / 1_000_000

    return {
        "status": "ok",
        "cache_hit_tokens": cache_hit,
        "cache_miss_tokens": cache_miss,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 8),
    }


# ---------------------------------------------------------------------------
# DB indsættelse
# ---------------------------------------------------------------------------


def _insert_cost_row(result: dict[str, Any]) -> None:
    """Indsæt warmer-kald i costs-tabellen.

    Bruger eksplicit provider='primary_cache_warmer' + model='deepseek-v4-flash'
    så monitoren kan skelne warmer-kald fra rigtige primary-kald.
    """
    if not DB_PATH.exists():
        logger.warning("DB findes ikke: %s", DB_PATH)
        return

    try:
        con = sqlite3.connect(str(DB_PATH))
        con.execute(
            """
            INSERT INTO costs (
                lane, provider, model,
                input_tokens, output_tokens, cost_usd,
                cache_hit_tokens, cache_miss_tokens, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "primary",
                "primary_cache_warmer",
                DEFAULT_MODEL,
                int(result.get("input_tokens", 0)),
                int(result.get("output_tokens", 0)),
                float(result.get("cost_usd", 0.0)),
                int(result.get("cache_hit_tokens", 0)),
                int(result.get("cache_miss_tokens", 0)),
                datetime.now(UTC).isoformat(),
            ),
        )
        con.commit()
        con.close()
    except Exception as exc:
        logger.error("Kunne ikke skrive til costs-tabellen: %s", exc)


# ---------------------------------------------------------------------------
# Logning
# ---------------------------------------------------------------------------


def _append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Core warmer function (testbar)
# ---------------------------------------------------------------------------


def _read_key_from_runtime_json() -> str | None:
    """Læs deepseek_api_key fra ~/.jarvis-v2/config/runtime.json."""
    path = HOME_DIR / "config" / "runtime.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("deepseek_api_key")
    except Exception:
        return None


def _resolve_api_key(*, override: str | None = None) -> str | None:
    """Resolve DeepSeek API key: override > env > runtime.json.

    Prøver (i rækkefølge):
      1. Eksplicit override (test / programmatisk brug)
      2. DEEPSEEK_API_KEY miljøvariabel
      3. OPENAI_API_KEY miljøvariabel (fallback)
      4. runtime.json → deepseek_api_key
    """
    return (
        override
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or _read_key_from_runtime_json()
    )


def warm_primary_cache(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Udfør ét cache-warmer kald og returnér resultat.

    Returnerer en dict med:
      - status: "ok" | "dedup_skip" | "error" | "skipped"
      - cache_hit_tokens / cache_miss_tokens / hit_rate_pct
      - reason (hvis status != "ok")
    """
    # Dedup
    if _check_dedup(force=force):
        elapsed = 0
        try:
            last = float(LAST_RUN_PATH.read_text(encoding="utf-8").strip())
            elapsed = time.time() - last
        except (ValueError, OSError):
            pass
        return {
            "status": "dedup_skip",
            "reason": f"too soon — sidste kald var for {elapsed:.0f} sekunder siden",
        }

    # Hent API key
    api_key = _resolve_api_key(override=api_key)
    if not api_key:
        return {"status": "error", "reason": "Ingen API key fundet"}

    base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    # Hent system prompt
    if system_prompt is None:
        system_prompt = _fetch_system_prompt()
    if not system_prompt:
        return {"status": "error", "reason": "Kunne ikke hente system prompt"}

    # Byg payload og kald API
    payload = _build_payload(system_prompt)
    result = _call_api(api_key, base_url, payload)

    if result.get("status") == "rate_limited":
        return {
            "status": "skipped",
            "reason": f"rate limit: {result.get('error', 'unknown')}",
        }

    if result.get("status") != "ok":
        return {
            "status": "skipped",
            "reason": result.get("error", "unknown API error"),
        }

    # Persister
    _insert_cost_row(result)
    _touch_last_run()

    total = result.get("cache_hit_tokens", 0) + result.get("cache_miss_tokens", 0)
    hit_rate = 100 * result.get("cache_hit_tokens", 0) / total if total else 0

    return {
        "status": "ok",
        "cache_hit_tokens": result.get("cache_hit_tokens", 0),
        "cache_miss_tokens": result.get("cache_miss_tokens", 0),
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "cost_usd": result.get("cost_usd", 0.0),
        "hit_rate_pct": round(hit_rate, 2),
    }


# ---------------------------------------------------------------------------
# Main (CLI entry point → warmer)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]

    dry_run = "--dry-run" in args
    force = "--force" in args

    # Dedup (medmindre --force)
    if _check_dedup(force=force):
        logger.info("Dedup — afbryder")
        return 0

    # Hent API key (env → runtime.json)
    api_key = _resolve_api_key()
    if not api_key:
        logger.error("Ingen DEEPSEEK_API_KEY fundet — prøv runtime.json eller miljøvariabel")
        return 1

    # Hent base URL
    base_url = os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL

    # Hent system prompt
    system_prompt = _fetch_system_prompt()
    if not system_prompt:
        logger.error("Kunne ikke hente system prompt — prøv --dry-run for diagnose")
        return 1

    # Byg payload
    payload = _build_payload(system_prompt)

    # Log entry vi skriver uanset udfald
    log_entry: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "model": DEFAULT_MODEL,
        "provider": "primary_cache_warmer",
        "dry_run": dry_run,
        "system_prompt_length": len(system_prompt),
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_hit_tokens": 0,
        "cache_miss_tokens": 0,
        "cost_usd": 0.0,
        "status": "dry_run" if dry_run else "pending",
    }

    if dry_run:
        log_entry["status"] = "dry_run"
        log_entry["note"] = (
            f"Ville kalde {base_url}/chat/completions "
            f"med {len(payload['messages'][0]['content'])} bytes system prompt"
        )
        _append_log(log_entry)
        logger.info(
            "Dry-run: %s/chat/completions | system prompt: %d bytes",
            base_url,
            len(payload["messages"][0]["content"]),
        )
        return 0

    # Kald API
    result = _call_api(api_key, base_url, payload)

    # Opdater log entry
    log_entry["status"] = result.get("status", "error")
    log_entry["cache_hit_tokens"] = result.get("cache_hit_tokens", 0)
    log_entry["cache_miss_tokens"] = result.get("cache_miss_tokens", 0)
    log_entry["input_tokens"] = result.get("input_tokens", 0)
    log_entry["output_tokens"] = result.get("output_tokens", 0)
    log_entry["cost_usd"] = result.get("cost_usd", 0.0)

    if result.get("status") == "ok":
        _insert_cost_row(result)
        _touch_last_run()
        total = result.get("cache_hit_tokens", 0) + result.get("cache_miss_tokens", 0)
        hit_rate = 100 * result.get("cache_hit_tokens", 0) / total if total else 0
        logger.info(
            "Warmer OK — hit=%d miss=%d rate=%.1f%% cost=$%.8f",
            result.get("cache_hit_tokens", 0),
            result.get("cache_miss_tokens", 0),
            hit_rate,
            result.get("cost_usd", 0),
        )
        log_entry["hit_rate_pct"] = round(hit_rate, 2)
    elif result.get("status") == "rate_limited":
        logger.warning("Rate limited — springer over")
        log_entry["error"] = result.get("error", "rate_limited")
    else:
        logger.error("API error: %s", result.get("error"))
        log_entry["error"] = result.get("error", "unknown")

    _append_log(log_entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
