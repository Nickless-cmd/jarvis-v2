"""API-forbindelses-nerve — Jarvis mærker hvem/hvad der forbinder til hans API.

Middleware kalder ``record(...)`` pr. HTTP-request (metadata-only). Vi:
  1. Opdaterer en IN-MEMORY presence-tabel (billig, låst — ingen DB i request-hot-path, jf. DB#1).
  2. Observerer SELEKTIVT til Centralens connections-cluster (nerve ``api_request``): kun ved
     NY forbindelse (first-seen af en (ip,user) i vinduet) + ved FEJL (status ≥ 400). Ellers
     ville hver poll/ping oversvømme trace-bufferen. Så Jarvis "mærker" nye forbindelser + fejl.
  3. Akkumulerer detalje-rækker til batchet flush (cadence) → persistent + GDPR-retention.

GDPR: metadata-only (ingen body/indhold). Fuld IP → /24 efter 48t (db_api_connections). Self-safe:
kaster ALDRIG (en observabilitets-nerve må ikke kunne vælte et API-svar).
"""
from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from typing import Any

from core.runtime import db_api_connections as _db

# (ip, user_id) → presence-state (in-memory, live)
_PRESENCE: dict[tuple[str, str], dict[str, Any]] = {}
# detalje-rækker der venter på flush
_LOG_BUFFER: list[dict[str, Any]] = []
_LOCK = threading.Lock()
_MAX_BUFFER = 2000  # bounded — drop ældste hvis flush hænger

# Opportunistisk flush (api-processen ejer bufferen; cadence kører i runtime → kan ikke flushe DEN
# her, jf. gate-ledger-læren). Throttlet: max én baggrunds-flush pr. _FLUSH_EVERY_S.
_FLUSH_EVERY_S = 30.0
_RETENTION_EVERY_S = 1800.0
_last_flush = 0.0
_last_retention = 0.0
_flush_inflight = False

# stier vi ikke gider observere som "forbindelse" (intern støj), men STADIG tæller i presence.
_QUIET_PATHS = ("/health", "/api/internal/", "/presence/ping", "/central/realtime")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def record(*, ip: str, method: str, path: str, status: int, latency_ms: int,
           user_id: str = "", session_id: str = "", error: str = "") -> None:
    """Registrér én API-request (metadata-only). Billig, låst, kaster ALDRIG."""
    try:
        ip = (ip or "unknown").strip()
        user_id = (user_id or "").strip()
        path = (path or "")[:200]
        is_error = int(status or 0) >= 400
        now = _now_iso()
        key = (ip, user_id)
        is_new = False
        with _LOCK:
            st = _PRESENCE.get(key)
            if st is None:
                is_new = True
                _PRESENCE[key] = {
                    "ip": ip, "user_id": user_id, "first_seen": now, "last_seen": now,
                    "request_count": 1, "error_count": 1 if is_error else 0,
                    "last_method": method, "last_path": path, "last_status": int(status or 0),
                    "_dirty": True,
                }
            else:
                st["last_seen"] = now
                st["request_count"] += 1
                if is_error:
                    st["error_count"] += 1
                st["last_method"] = method
                st["last_path"] = path
                st["last_status"] = int(status or 0)
                st["_dirty"] = True
            if len(_LOG_BUFFER) < _MAX_BUFFER:
                _LOG_BUFFER.append({
                    "ts": now, "ip": ip, "method": method, "path": path,
                    "status": int(status or 0), "latency_ms": int(latency_ms or 0),
                    "user_id": user_id, "session_id": (session_id or "")[:80], "error": (error or "")[:200],
                })
        # Selektiv Central-observe (uden for låsen): kun NY forbindelse eller FEJL. Metadata-only.
        _quiet = any(path.startswith(p) for p in _QUIET_PATHS)
        if (is_new and not _quiet) or is_error:
            try:
                from core.services.central_core import central
                central().observe({
                    "cluster": "connections", "nerve": "api_request",
                    "kind": "error" if is_error else "new_connection",
                    "ip": ip, "user_id": user_id or "?", "method": method, "path": path,
                    "status": int(status or 0), "latency_ms": int(latency_ms or 0),
                })
            except Exception:
                pass
        _maybe_flush_async()
    except Exception:
        return


def _maybe_flush_async() -> None:
    """Throttlet baggrunds-flush (api-proces ejer bufferen). Spawner en daemon-tråd så request-
    stien aldrig blokerer på DB. GDPR-retention køres sjældnere. Self-safe."""
    global _last_flush, _last_retention, _flush_inflight
    now = time.monotonic()
    if _flush_inflight or (now - _last_flush) < _FLUSH_EVERY_S:
        return
    _last_flush = now
    do_retention = (now - _last_retention) >= _RETENTION_EVERY_S
    if do_retention:
        _last_retention = now

    def _bg() -> None:
        global _flush_inflight
        try:
            flush()
            if do_retention:
                retention_sweep()
        except Exception:
            pass
        finally:
            _flush_inflight = False

    try:
        _flush_inflight = True
        threading.Thread(target=_bg, name="api-conn-flush", daemon=True).start()
    except Exception:
        _flush_inflight = False


def _drain() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Snapshot dirty presence-deltas + log-buffer under lås; nulstil buffer + dirty-flag."""
    with _LOCK:
        presence_deltas = []
        for st in _PRESENCE.values():
            if st.get("_dirty"):
                presence_deltas.append({k: v for k, v in st.items() if k != "_dirty"})
                st["_dirty"] = False
        logs = list(_LOG_BUFFER)
        _LOG_BUFFER.clear()
        # bounded in-memory presence: drop rækker der ikke er set i >1t (holdes i DB)
        cutoff = datetime.fromtimestamp(datetime.now(UTC).timestamp() - 3600, UTC).isoformat()
        stale = [k for k, st in _PRESENCE.items() if st.get("last_seen", "") < cutoff]
        for k in stale:
            _PRESENCE.pop(k, None)
        return presence_deltas, logs


def flush() -> int:
    """Batch-flush presence + log til DB (cadence). Self-safe."""
    try:
        presence_deltas, logs = _drain()
        if not presence_deltas and not logs:
            return 0
        return _db.flush_records(presence_deltas, logs)
    except Exception:
        return 0


def retention_sweep() -> dict[str, int]:
    """GDPR-retention (cadence): anonymisér IP > 48t → /24, slet gammel log, prune presence."""
    try:
        return _db.anonymize_and_prune()
    except Exception:
        return {"anonymized": 0, "deleted": 0, "pruned": 0}


def presence_view(*, active_within_s: int = 300, limit: int = 100) -> dict[str, Any]:
    """Hvem er forbundet til API'et? Fletter live in-memory + persistent DB. Self-safe.

    Returnerer aggregat: {connections: [...], active_count, total_count, error_count}. Kun metadata
    (ip/user/tællere/tid/status) — aldrig indhold."""
    try:
        # flush dirty først så DB-view er friskt
        try:
            flush()
        except Exception:
            pass
        rows = _db.read_presence(active_within_s=active_within_s, limit=limit)
        active = sum(1 for r in rows if r.get("active"))
        errs = sum(int(r.get("error_count") or 0) for r in rows)
        return {"connections": rows, "active_count": active, "total_count": len(rows),
                "error_count": errs, "recent_errors": _db.read_recent_errors(limit=15)}
    except Exception:
        return {"connections": [], "active_count": 0, "total_count": 0, "error_count": 0,
                "recent_errors": []}
