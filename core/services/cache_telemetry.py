"""Per-request cache-telemetri for den synlige DeepSeek-lane (2026-06-30).

Hvorfor: costs-bordet optager kun ÉN aggregeret række pr. tur (first-pass under
lane=primary, agentiske ture under lane=visible) — de individuelle agentiske
RUNDER er usynlige. Det gjorde det umuligt at verificere om prefix-cachen holder
RUNDE FOR RUNDE (fx tool_choice-fixet der skal holde [system,tools] byte-stabilt).

Denne modul skriver ÉN JSONL-linje pr. synligt DeepSeek-kald med:
  - run_id + round_index + autonomous → isolér ÉN brugers ÉN tur, runde for runde
  - prefix_sha + prefix_len → hash af det cachebare [system + tools]; SAMME hash
    over runder = prefixet er stabilt (cachen kan holde); skift = en breaker
  - cache_hit / cache_miss → DeepSeeks faktiske native tal (10× pris-forskel)

Aflæs: ~/.jarvis-v2/logs/cache_telemetry.jsonl. Self-safe — må ALDRIG kaste ind i
stream-stien.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def prefix_signature(system_content: str, tools: Any) -> tuple[str, int]:
    """Beregn (sha-prefix, længde) for det cachebare [system + tools].

    Det er PRÆCIS den del DeepSeek-templaten lægger forrest (system så tools);
    ændrer ÉN byte sig her, brækker prefix-cachen fra det punkt. Deterministisk
    serialisering (sort_keys) så identisk indhold giver identisk hash."""
    try:
        sys_part = str(system_content or "")
        tools_part = json.dumps(tools or [], sort_keys=True, ensure_ascii=False)
        blob = sys_part + "\n--tools--\n" + tools_part
        sha = hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()[:16]
        return sha, len(blob)
    except Exception:
        return "", 0


def component_signatures(messages: list[dict[str, Any]], tools: Any) -> dict[str, str | int]:
    """Fingerprint prompt regions separately, without recording their contents.

    The first system message is the stable prefix. A system message after the
    conversation begins is the live tail; its expected changes must not be
    mistaken for a break in the stable prefix.
    """
    system = ""
    tail = ""
    seen_conversation = False
    for message in messages:
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        if role == "system" and not seen_conversation and not system:
            system = content
        elif role == "system" and seen_conversation:
            tail = content
        elif role != "system":
            seen_conversation = True
    tools_text = json.dumps(tools or [], sort_keys=True, ensure_ascii=False)

    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:16] if value else ""

    return {
        "system_sha": digest(system), "system_len": len(system),
        "tools_sha": digest(tools_text), "tools_len": len(tools_text),
        "tail_sha": digest(tail), "tail_len": len(tail),
    }


def record_visible_cache(
    *,
    run_id: str = "",
    round_index: int = -1,
    autonomous: bool = False,
    lane: str = "",
    provider: str = "",
    model: str = "",
    prefix_sha: str = "",
    prefix_len: int = 0,
    cache_hit: int = 0,
    cache_miss: int = 0,
    session_id: str = "",
    system_sha: str = "",
    tools_sha: str = "",
    tail_sha: str = "",
    system_len: int = 0,
    tools_len: int = 0,
    tail_len: int = 0,
) -> None:
    """Append én telemetri-linje. Self-safe (sluger alt)."""
    try:
        import os
        from pathlib import Path
        home = Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))
        log_dir = home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / "cache_telemetry.jsonl"
        _in = int(cache_hit) + int(cache_miss)
        line = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "session_id": session_id,
            "round": round_index,
            "auto": bool(autonomous),
            "lane": lane,
            "provider": provider,
            "model": model,
            "prefix_sha": prefix_sha,
            "prefix_len": prefix_len,
            "system_sha": system_sha,
            "tools_sha": tools_sha,
            "tail_sha": tail_sha,
            "system_len": int(system_len),
            "tools_len": int(tools_len),
            "tail_len": int(tail_len),
            "hit": int(cache_hit),
            "miss": int(cache_miss),
            "pct": round(100.0 * int(cache_hit) / _in, 1) if _in else 0.0,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
        # Cache→Central (spec §3.2/§3.3): fodr Centralen med prefix-cache-helbred, så
        # central_watch kan flagge når caching brækker (kold hit-rate = ~10x omkostning).
        # Kun ved reel cache-aktivitet (_in>0) — første/tomme kald er ikke et signal.
        if _in > 0:
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish("cache.telemetry", line)
            except Exception:
                pass
            try:
                from core.services import central_timeseries
                from core.services.central_core import central
                central().observe({
                    "cluster": "cost", "nerve": "prefix_cache", "kind": "telemetry",
                    "run_id": run_id, "pct": line["pct"], "prefix_sha": prefix_sha,
                    "lane": lane, "provider": provider,
                    "hit": int(cache_hit), "miss": int(cache_miss),
                })
                central_timeseries.record("cost", "prefix_cache", value=float(line["pct"]),
                                          meta={"prefix_sha": prefix_sha, "lane": lane})
            except Exception:
                pass
    except Exception:
        pass
