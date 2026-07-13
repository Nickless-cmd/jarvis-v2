"""Gate-mønster-læring — vane-bryder oven på gate-substratet (2026-07-13).

Når en gate fyrer på det SAMME mønster igen og igen (fx fact_gate 'self_stats' på
et gentaget tal-claim), er det ikke bare en enkelt blokering — det er en VANE. Dette
modul akkumulerer gate-fyringer pr. (mønster, normaliseret-detected) og lader Centralen
NUDGE når en vane krydser en tærskel, i stedet for kun at blokere reaktivt hver gang.

To lag (samme mønster som gate_verdict_ledger):
  * ``record_gate_pattern(...)`` — kaldes fra en flagget gate-adapter. In-memory increment
    under lås; kaster ALDRIG (instrumentering må ikke vælte gate-eval). Bedste-indsats
    durabel persist til runtime_state (self-safe, fire-and-forget).
  * ``repeated_patterns(threshold=...)`` — overflade-kandidaterne (vaner) til Centralen/CLI.

Nøgle = (pattern, normalized_detected). Normalisering: lowercase + whitespace-kollaps +
cifre→'#', så '2500 kald' og '3000 kald' tæller som SAMME vane-form. Aldring: fyringer
ældre end ``_MAX_AGE_S`` tælder ikke med i repeated_patterns (en gammel byge ældes ud —
samme lære som central_stale_count-fælden).
"""
from __future__ import annotations

import re
import threading
import time
from typing import Any

# key = (pattern, normalized_detected) → {pattern, sample, count, first_ts, last_ts,
#                                          sessions, emitted}
_STORE: dict[tuple[str, str], dict[str, Any]] = {}
_LOCK = threading.Lock()

_MAX_AGE_S = 7 * 24 * 3600.0     # fyringer ældre end 7 dage tæller ikke i repeated_patterns
_EMIT_THRESHOLD = 3              # antal fyringer før Centralen nudges (én gang pr. krydsning)
_RUNTIME_KEY = "central.gate_pattern_learning"
_MAX_KEYS = 500                  # loft mod ubegrænset vækst (drop ældste ved overløb)
_PERSIST_MIN_INTERVAL_S = 30.0   # throttle: højst én durabel skriv pr. 30s (hot-path-hygiejne)
_last_persist_ts = 0.0
_hydrated = False                # lazy-hydrate ved første brug → læring overlever restart (Jarvis reboot'er ofte)


def _ensure_hydrated() -> None:
    """Genindlæs den durable snapshot ÉN gang ved første brug (ikke ved import → tests offline-rene).
    Sætter flaget FØR hydrate (undgår re-entry/deadlock, da hydrate selv tager _LOCK). Self-safe."""
    global _hydrated
    if _hydrated:
        return
    _hydrated = True
    try:
        hydrate()
    except Exception:
        pass

_WS = re.compile(r"\s+")
_NUM = re.compile(r"\d+")


def _normalize_detected(text: str) -> str:
    """Normalisér den detekterede substring til en vane-FORM: lowercase, whitespace-kollaps,
    cifre→'#'. Så tal-varianter af samme claim-form aggregerer. Self-safe."""
    try:
        s = _WS.sub(" ", str(text or "").strip().lower())
        s = _NUM.sub("#", s)
        return s[:120]
    except Exception:
        return ""


def record_gate_pattern(pattern: str, detected_text: str, *,
                        session_id: str = "", now: float | None = None) -> dict[str, Any]:
    """Registrér én gate-fyring for (pattern, detected_text). Self-safe — kaster ALDRIG.

    Returnerer entry-snapshottet (til test/introspektion). Krydser tælleren ``_EMIT_THRESHOLD``
    NETOP nu, emitteres én central-nudge (gate_pattern_repeat, cluster central_meta)."""
    try:
        _ensure_hydrated()
        pat = str(pattern or "").strip()
        if not pat:
            return {}
        norm = _normalize_detected(detected_text)
        ts = float(now if now is not None else time.time())
        key = (pat, norm)
        crossed = False
        snapshot: dict[str, Any]
        with _LOCK:
            entry = _STORE.get(key)
            if entry is None:
                if len(_STORE) >= _MAX_KEYS:
                    _evict_oldest_locked()
                entry = {
                    "pattern": pat,
                    "sample": str(detected_text or "")[:120],
                    "count": 0,
                    "first_ts": ts,
                    "last_ts": ts,
                    "sessions": set(),
                    "emitted": False,
                }
                _STORE[key] = entry
            entry["count"] += 1
            entry["last_ts"] = ts
            if session_id:
                try:
                    entry["sessions"].add(str(session_id))
                except Exception:
                    pass
            if entry["count"] >= _EMIT_THRESHOLD and not entry["emitted"]:
                entry["emitted"] = True
                crossed = True
            snapshot = {"pattern": entry["pattern"], "sample": entry["sample"],
                        "count": entry["count"]}
        if crossed:
            _emit_repeat_nudge(pat, snapshot["sample"], snapshot["count"],
                               n_sessions=len(entry.get("sessions") or ()))
        _persist_best_effort()
        return snapshot
    except Exception:
        return {}


def repeated_patterns(threshold: int = 3, now: float | None = None) -> list[dict[str, Any]]:
    """Overflade vane-kandidaterne: mønstre med count ≥ threshold indenfor alders-vinduet.

    Returnerer [{pattern, sample, count}] sorteret faldende på count. Self-safe."""
    try:
        _ensure_hydrated()
        cutoff = float(now if now is not None else time.time()) - _MAX_AGE_S
        out: list[dict[str, Any]] = []
        with _LOCK:
            for entry in _STORE.values():
                if entry["count"] >= threshold and entry["last_ts"] >= cutoff:
                    out.append({"pattern": entry["pattern"], "sample": entry["sample"],
                                "count": entry["count"]})
        out.sort(key=lambda e: e["count"], reverse=True)
        return out
    except Exception:
        return []


def _evict_oldest_locked() -> None:
    """Drop den ældste (mindst nyligt sete) nøgle. Kaldes under _LOCK."""
    try:
        oldest = min(_STORE.items(), key=lambda kv: kv[1]["last_ts"])
        _STORE.pop(oldest[0], None)
    except Exception:
        pass


def _emit_repeat_nudge(pattern: str, sample: str, count: int, *, n_sessions: int) -> None:
    """Nudge-substratet: fortæl Centralen at et gate-mønster er blevet en VANE. Self-safe."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "central_meta",
            "nerve": "gate_pattern_repeat",
            "kind": "pattern_habit",
            "trigger_pattern": pattern,
            "detected_text": str(sample or "")[:120],
            "count": count,
            "n_sessions": n_sessions,
            "flagged": True,
        })
    except Exception:
        pass


def _persist_best_effort() -> None:
    """Bedste-indsats durabel snapshot til runtime_state (overlever genstart). Fire-and-forget,
    fuldt self-safe: en DB-/offline-fejl må ALDRIG påvirke gate-eval. Læses tilbage af
    ``hydrate()`` ved proces-start (kaldes eksplicit, ikke ved import — så tests er offline-rene).

    Throttlet til højst én skriv pr. ``_PERSIST_MIN_INTERVAL_S`` — record kaldes pr. gate-fyring,
    så en DB-skriv hver gang ville være hot-path-spild. Data-tab ved crash = seneste vindue."""
    global _last_persist_ts
    try:
        now = time.time()
        if now - _last_persist_ts < _PERSIST_MIN_INTERVAL_S:
            return
        _last_persist_ts = now
        from core.runtime.db_core import set_runtime_state_value
        with _LOCK:
            payload = [
                {"pattern": e["pattern"], "sample": e["sample"], "count": e["count"],
                 "first_ts": e["first_ts"], "last_ts": e["last_ts"],
                 "emitted": e["emitted"], "sessions": list(e.get("sessions") or ())}
                for e in _STORE.values()
            ]
        set_runtime_state_value(_RUNTIME_KEY, payload)
    except Exception:
        pass


def hydrate() -> int:
    """Genindlæs durabel snapshot fra runtime_state ind i in-memory-store. Kaldes eksplicit
    ved proces-start (IKKE ved import — holder unit-tests offline). Self-safe. Returnerer antal
    genindlæste nøgler."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        rows = get_runtime_state_value(_RUNTIME_KEY, []) or []
        n = 0
        with _LOCK:
            for r in rows:
                try:
                    pat = str(r.get("pattern") or "")
                    if not pat:
                        continue
                    norm = _normalize_detected(r.get("sample") or "")
                    _STORE[(pat, norm)] = {
                        "pattern": pat,
                        "sample": str(r.get("sample") or "")[:120],
                        "count": int(r.get("count") or 0),
                        "first_ts": float(r.get("first_ts") or 0.0),
                        "last_ts": float(r.get("last_ts") or 0.0),
                        "sessions": set(r.get("sessions") or ()),
                        "emitted": bool(r.get("emitted")),
                    }
                    n += 1
                except Exception:
                    continue
        return n
    except Exception:
        return 0


def _reset() -> None:
    """Test-hook: ryd in-memory-store + hydrate-flag."""
    global _hydrated
    with _LOCK:
        _STORE.clear()
    _hydrated = False
