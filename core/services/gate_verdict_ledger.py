"""Gate-verdict-ledger — in-memory akkumulator + batchet flush til persistent tabel.

To lag:
  * `record(...)`  — kaldes fra `central().decide` PR. VERDICT. Kun en dict-increment
    under en lås; INGEN DB, INGEN I/O. Skal være billig nok til decide-hot-pathen og
    kaster ALDRIG (en tæller må ikke påvirke governance).
  * `flush()`      — kaldes periodisk (cadence, ~1 min). Snapshotter akkumulatoren, nulstiller
    den, og UPSERT'er deltaerne til `gate_verdict_counts` i én DB-tur. Data-tab ved crash
    er begrænset til det seneste flush-vindue (~1 min) — acceptabelt for en statistik-tæller.

`summary()` læser den persistente tabel (survives restart) og bruges til flip-beslutningen
"kan denne gate flippes fra shadow til enforce?" samt CLI/rapport.
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from core.runtime import db_gate_verdicts

# nøgle = (nerve, decision) → {cluster, count, last_ts, last_reason}
_ACC: dict[tuple[str, str], dict[str, Any]] = {}
_LOCK = threading.Lock()


def record(nerve: str, cluster: str, decision: str, reason: str = "") -> None:
    """Akkumulér ét verdict in-memory. Billig, låst, kaster ALDRIG.

    Kaldes fra central().decide for HVERT governet gate-udfald. DB røres ikke her.
    """
    try:
        if not nerve or not decision:
            return
        key = (nerve, decision)
        now = datetime.now(UTC).isoformat()
        with _LOCK:
            entry = _ACC.get(key)
            if entry is None:
                _ACC[key] = {"cluster": cluster or "", "count": 1,
                             "last_ts": now, "last_reason": (reason or "")[:240]}
            else:
                entry["count"] += 1
                entry["last_ts"] = now
                if cluster:
                    entry["cluster"] = cluster
                if reason:
                    entry["last_reason"] = reason[:240]
    except Exception:
        return


def _drain() -> list[dict[str, Any]]:
    """Snapshot + nulstil akkumulatoren under lås. Returnerer delta-liste til UPSERT."""
    with _LOCK:
        if not _ACC:
            return []
        deltas = [
            {"nerve": nerve, "cluster": e["cluster"], "decision": decision,
             "count": e["count"], "last_ts": e["last_ts"], "last_reason": e["last_reason"]}
            for (nerve, decision), e in _ACC.items()
        ]
        _ACC.clear()
        return deltas


def flush() -> int:
    """Skriv akkumulerede deltas til den persistente tabel. Returnerer antal rækker rørt.

    Kaldes på cadence. Selv-sikker — ved fejl mistes vinduets tællere, aldrig runtime.
    """
    try:
        deltas = _drain()
        if not deltas:
            return 0
        return db_gate_verdicts.apply_deltas(deltas)
    except Exception:
        return 0


def summary() -> dict[str, dict[str, Any]]:
    """Aggregeret verdict-fordeling pr. nerve fra den persistente tabel (survives restart)."""
    return db_gate_verdicts.summary()
