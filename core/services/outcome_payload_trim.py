"""Trim af fulde værktøjsresultater i `runtime_action_outcomes.result_json` — tilbagevendende.

Målt 14/11-2026 (CT105): 1.048 MB i `result_json`, heraf 962 MB i rækker ældre end 7 dage — og kun de
NYESTE rækker læses (`recent_runtime_action_outcomes`, `ORDER BY id DESC LIMIT`; `result_status` og
`result_summary` har egne kolonner). Samme output ligger desuden i `chat_messages.content_json`. Den
60-dages sletning der allerede findes (`events_retention`) fjerner hele rækken; dette beholder rækken
(status, summary, ids, korte felter) og afkorter kun lange TEKSTVÆRDIER.

Engangs-trimmen 14/11 sparede ~712 MB og tabellen vokser igen ~13 MB/døgn (3-4 k rækker × 3,6 KB) —
derfor et trin der kører med oprydningen i stedet for en engangskørsel.

* Rækken forbliver gyldig JSON med de samme nøgler + ``"trimmed": true``; en trimmet række røres aldrig igen.
* VANDMÆRKE (`runtime_state_kv`): sidst behandlede id. Gamle rækker genscannes ikke ved hvert kald.
  Forudsætter at ``recorded_at`` vokser med ``id`` (sættes ved indsættelse); en række der skrives med
  bagudstillet tid under vandmærket bliver ikke trimmet. Slet nøglen for at gennemløbe alt forfra.
* Små kappede batches (ét commit hver → korte skrivelåse) og et loft pr. kald, så et efterslæb drænes
  gradvist over flere oprydninger. Self-safe: rejser aldrig.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

FULL_RESULT_DAYS = 7           # nyere end dette beholder det fulde resultat
KEEP_CHARS = 300               # længste tekstværdi i en trimmet række
_MIN_TRIMMABLE = 600           # kortere result_json er ikke værd at røre
_BATCH = 500
_MAX_ROWS_PER_CALL = 20_000
_WATERMARK_KEY = "outcome_payload_trim_watermark"


def _settings_extra() -> dict:
    from core.runtime.settings import load_settings
    return load_settings().extra


def _full_result_days() -> int:
    try:
        raw = _settings_extra().get("action_outcome_full_result_days", FULL_RESULT_DAYS)
    except Exception:  # settings utilgaengelige (fx tidlig opstart): standardvinduet er det sikre valg
        return FULL_RESULT_DAYS
    try:
        days = int(raw)
    except (TypeError, ValueError):  # ugyldig vaerdi i settings: standardvinduet, ikke et gaet
        return FULL_RESULT_DAYS
    return max(1, days)


def _trim_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) > KEEP_CHARS:
            return value[:KEEP_CHARS] + f"…[trimmet fra {len(value)} tegn]"
        return value
    if isinstance(value, list):
        return [_trim_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _trim_value(v) for k, v in value.items()}
    return value


def _trimmed_json(raw: str) -> str | None:
    """Den afkortede JSON, eller None når rækken skal blive som den er."""
    if len(raw) <= _MIN_TRIMMABLE:
        return None
    try:
        obj = json.loads(raw)
    except ValueError:  # ugyldig JSON i en gammel raekke: den lades som den er, ikke gaettet om
        return None
    if not isinstance(obj, dict) or obj.get("trimmed") is True:
        return None
    new = _trim_value(obj)
    new["trimmed"] = True
    out = json.dumps(new, ensure_ascii=False)
    return out if len(out) < len(raw) else None


def trim_old_outcome_payloads(*, full_days: int | None = None, max_rows: int = _MAX_ROWS_PER_CALL,
                              batch: int = _BATCH) -> dict[str, object]:
    """Afkort ``result_json`` i rækker ældre end ``full_days`` (standard 7). Returnerer
    ``{scanned, trimmed, saved_bytes, watermark}`` — eller med ``error`` hvis noget fejlede."""
    scanned = trimmed = saved = 0
    watermark = 0
    try:
        from core.runtime.db import connect
        from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value

        days = int(full_days) if full_days is not None else _full_result_days()
        cutoff = (datetime.now(UTC) - timedelta(days=max(1, days))).strftime("%Y-%m-%dT%H:%M:%S")
        watermark = int(get_runtime_state_value(_WATERMARK_KEY, 0) or 0)
        while scanned < max_rows:
            take = min(batch, max_rows - scanned)
            with connect() as conn:
                rows = conn.execute(
                    "SELECT id, result_json FROM runtime_action_outcomes "
                    "WHERE id > ? AND recorded_at < ? ORDER BY id LIMIT ?",
                    (watermark, cutoff, take)).fetchall()
                if not rows:
                    break
                updates: list[tuple[str, int]] = []
                for row in rows:
                    raw = row[1] or ""
                    new = _trimmed_json(raw)
                    if new is not None:
                        saved += len(raw) - len(new)
                        updates.append((new, row[0]))
                if updates:
                    conn.executemany("UPDATE runtime_action_outcomes SET result_json=? WHERE id=?", updates)
                    conn.commit()
            scanned += len(rows)
            trimmed += len(updates)
            watermark = int(rows[-1][0])
            set_runtime_state_value(_WATERMARK_KEY, watermark)
    except Exception as exc:  # self-safe: en fejlet trim maa ikke vaelte oprydningen omkring den
        logger.warning("outcome_payload_trim: %s: %s", type(exc).__name__, exc)
        return {"scanned": scanned, "trimmed": trimmed, "saved_bytes": saved, "watermark": watermark,
                "error": f"{type(exc).__name__}: {exc}"[:200]}
    return {"scanned": scanned, "trimmed": trimmed, "saved_bytes": saved, "watermark": watermark}
