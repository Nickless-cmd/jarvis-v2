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


def _requeue(deltas: list[dict[str, Any]]) -> None:
    """Læg ubekræftede deltas TILBAGE i akkumulatoren (merge-forward), så en fejlet flush
    ikke taber vinduet — næste flush forsøger igen. Verdicts der ankom MENS flushet kørte
    lægges oveni (deres count summeres). Selv-sikker."""
    if not deltas:
        return
    try:
        with _LOCK:
            for d in deltas:
                nerve = str(d.get("nerve") or "")
                decision = str(d.get("decision") or "")
                if not nerve or not decision:
                    continue
                key = (nerve, decision)
                cnt = int(d.get("count") or 0)
                entry = _ACC.get(key)
                if entry is None:
                    _ACC[key] = {"cluster": d.get("cluster", "") or "", "count": cnt,
                                 "last_ts": d.get("last_ts", ""),
                                 "last_reason": d.get("last_reason", "")}
                else:
                    entry["count"] += cnt
                    # bevar det NYESTE last_ts/reason (ankomne-under-flush er nyere)
                    if d.get("last_ts", "") > entry.get("last_ts", ""):
                        entry["last_ts"] = d["last_ts"]
                        if d.get("last_reason"):
                            entry["last_reason"] = d["last_reason"]
                    if d.get("cluster") and not entry.get("cluster"):
                        entry["cluster"] = d["cluster"]
    except Exception:
        return


def flush() -> int:
    """Skriv akkumulerede deltas til den persistente tabel. Returnerer antal rækker rørt.

    Kaldes på cadence + ved run-slut (api-proces). Selv-sikker — kaster ALDRIG.

    HOLDBARHED: akkumulatoren drænes FØR skrivet, men bekræftes bagefter. Fejler DB-skrivet
    (låst ud over busy_timeout, WAL-kontention på den store live-DB, disk-fejl) re-køes
    HELE vinduet, så tællerne ikke tabes stille (= ground-truth for shadow→enforce-flip
    forbliver komplet). Uden dette eroderede en travl live-DB ledgeren usynligt."""
    deltas = _drain()
    if not deltas:
        return 0
    try:
        written = db_gate_verdicts.apply_deltas(deltas)
    except Exception:
        written = 0
    if not written:
        # Skrivet fejlede totalt (connect-niveau) → intet blev committet → re-kø HELE
        # vinduet. (apply_deltas committer batchen som ét; delvis fejl er kun enkelt-rækker
        # den selv springer over — sjældent, og re-kø der ville dobbelt-tælle de committede.)
        _requeue(deltas)
        return 0
    return written


def summary() -> dict[str, dict[str, Any]]:
    """Aggregeret verdict-fordeling pr. nerve fra den persistente tabel (survives restart)."""
    return db_gate_verdicts.summary()
