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
            "run_id": run_id,
            "round": round_index,
            "auto": bool(autonomous),
            "lane": lane,
            "provider": provider,
            "model": model,
            "prefix_sha": prefix_sha,
            "prefix_len": prefix_len,
            "hit": int(cache_hit),
            "miss": int(cache_miss),
            "pct": round(100.0 * int(cache_hit) / _in, 1) if _in else 0.0,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:
        pass
