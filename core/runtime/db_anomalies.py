"""Central-anomalier — persistent register over UDEFINEREDE fejl Centralen ikke selv har
en nerve til endnu. Det er her Centralen "definerer nye fejl": hver unik fejl-signatur får
en række (kategori + importance + tæller + først/sidst set), så et nyt fejl-mønster bliver
til et kendt, rangeret, lærbart signal i stedet for at forsvinde usynligt.

UPSERT pr. signatur → recurring fejl bumper bare tælleren (ingen spam); første sigtning
returnerer is_new=True (Centralen lærte lige en ny fejl-type). Cross-proces + overlever
genstart. Selv-sikker: en anomali-log må ALDRIG vælte runtime.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_IMPORTANCE = ("low", "medium", "high", "critical")
_IMP_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _ensure_anomalies_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_anomalies (
            signature TEXT PRIMARY KEY,
            category TEXT NOT NULL DEFAULT '',
            importance TEXT NOT NULL DEFAULT 'medium',
            source TEXT NOT NULL DEFAULT '',
            count INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL DEFAULT '',
            last_seen TEXT NOT NULL DEFAULT '',
            sample TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            resolved INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Tilføj location til ældre tabeller (HVOR fejlede den: fil:linje + exc-type). Self-safe.
    try:
        conn.execute("ALTER TABLE central_anomalies ADD COLUMN location TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass
    # known_signal: 1 = promoveret til 'kendt signal' → filtreres fra anomalies-listen,
    # vises i stedet under known_signals. Aldrig DELETE — altid depromoterbart (=0). Self-safe.
    try:
        conn.execute("ALTER TABLE central_anomalies ADD COLUMN known_signal INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_anomalies_live "
        "ON central_anomalies (resolved, importance, last_seen DESC)"
    )
    # known_anomaly_signals: en promoveret signatur bundet til cluster/nerve + handling.
    # action: observe (under obs.) | log_as_known (støj, kun optælling) | route_to_nerve
    # (fremtidige forekomster → observe til nerve+cluster). count/last_seen sporer den
    # løbende rate efter promotion (review-tilføjelse). signature PRIMARY KEY → INSERT OR IGNORE.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS known_anomaly_signals (
            signature TEXT PRIMARY KEY,
            cluster TEXT NOT NULL DEFAULT '',
            nerve TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL DEFAULT 'observe',
            promoted_at TEXT NOT NULL DEFAULT '',
            promoted_by TEXT NOT NULL DEFAULT 'auto',
            notes TEXT NOT NULL DEFAULT '',
            threshold_count INTEGER NOT NULL DEFAULT 0,
            threshold_hours REAL NOT NULL DEFAULT 0,
            count INTEGER NOT NULL DEFAULT 0,
            last_seen TEXT NOT NULL DEFAULT ''
        )
        """
    )


def record_anomaly_signature(
    *, signature: str, category: str, importance: str, source: str, sample: str,
    location: str = "",
) -> bool:
    """UPSERT en anomali-signatur. Returnerer True hvis det er FØRSTE gang (ny fejl-type
    Centralen netop definerede), ellers False (recurring → tæller bumpet). Selv-sikker."""
    try:
        imp = importance if importance in _IMPORTANCE else "medium"
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            _ensure_anomalies_table(conn)
            row = conn.execute(
                "SELECT count FROM central_anomalies WHERE signature = ?", (signature,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO central_anomalies "
                    "(signature, category, importance, source, count, first_seen, last_seen, sample, location) "
                    "VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)",
                    (signature, str(category or ""), imp, str(source or ""),
                     now, now, str(sample or "")[:2000], str(location or "")[:200]),
                )
                return True
            # recurring: bump tæller + last_seen (+ frisk location/sample), og eskalér importance
            # hvis denne sigtning er alvorligere end den hidtil registrerede.
            conn.execute(
                "UPDATE central_anomalies SET count = count + 1, last_seen = ?, "
                "location = CASE WHEN ? != '' THEN ? ELSE location END WHERE signature = ?",
                (now, str(location or ""), str(location or "")[:200], signature),
            )
            cur = conn.execute(
                "SELECT importance, count, first_seen, category FROM central_anomalies "
                "WHERE signature = ?", (signature,)
            ).fetchone()
            eff_imp = str(cur[0]) if cur else imp
            if cur and _IMP_RANK.get(imp, 1) > _IMP_RANK.get(str(cur[0]), 1):
                conn.execute(
                    "UPDATE central_anomalies SET importance = ? WHERE signature = ?",
                    (imp, signature),
                )
                eff_imp = imp
            _bump_count = int(cur[1]) if cur else 0
            _first_seen = str(cur[2]) if cur else now
            _cat = str(cur[3]) if cur and cur[3] else category
        # Uden for transaktionen (egen connection → ingen skrive-lås-deadlock):
        # auto-promotion-tjek efter hvert bump (R3). Self-safe — promotion må aldrig
        # vælte anomaly-loggen; fejler den, bliver signaturen bare stående som anomali.
        try:
            promote_to_known(signature=signature, count=_bump_count, first_seen=_first_seen,
                             importance=eff_imp, category=_cat or category)
        except Exception:
            pass
        return False
    except Exception:
        return False


def list_anomalies(*, limit: int = 50, unresolved_only: bool = True,
                   min_importance: str | None = None,
                   exclude_known: bool = True) -> list[dict[str, Any]]:
    """Læs anomalier (nyeste først). `exclude_known=True` (default) filtrerer promoverede
    'kendte signaler' (known_signal=1) fra → de vises kun under known_signals. Selv-sikker → [] ved fejl."""
    try:
        clauses: list[str] = []
        params: list[object] = []
        if unresolved_only:
            clauses.append("resolved = 0")
        if exclude_known:
            clauses.append("known_signal = 0")
        if min_importance and min_importance in _IMP_RANK:
            allowed = [k for k, v in _IMP_RANK.items() if v >= _IMP_RANK[min_importance]]
            clauses.append("importance IN (%s)" % ",".join("?" * len(allowed)))
            params.extend(allowed)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect() as conn:
            _ensure_anomalies_table(conn)
            rows = conn.execute(
                f"SELECT signature, category, importance, source, count, first_seen, "
                f"last_seen, sample, location FROM central_anomalies {where} "
                f"ORDER BY last_seen DESC LIMIT ?",
                (*params, int(limit)),
            ).fetchall()
        return [
            {"signature": r[0], "category": r[1], "importance": r[2], "source": r[3],
             "count": int(r[4]), "first_seen": r[5], "last_seen": r[6], "sample": r[7],
             "location": r[8] if len(r) > 8 else ""}
            for r in rows
        ]
    except Exception:
        return []


def resolve_anomaly(signature: str) -> bool:
    """Markér én anomali-signatur som håndteret (forsvinder fra det live register). Selv-sikker.

    Bruges når en signatur er afklaret (rettet, eller en testartefakt der skal væk)."""
    try:
        with connect() as conn:
            _ensure_anomalies_table(conn)
            conn.execute(
                "UPDATE central_anomalies SET resolved = 1 WHERE signature = ?",
                (str(signature or ""),),
            )
        return True
    except Exception:
        return False


def anomaly_counts() -> dict[str, int]:
    """Hurtig optælling pr. importance (til realtime-panelet). Selv-sikker."""
    out = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
    try:
        with connect() as conn:
            _ensure_anomalies_table(conn)
            for imp, n in conn.execute(
                "SELECT importance, COUNT(*) FROM central_anomalies "
                "WHERE resolved = 0 AND known_signal = 0 "
                "GROUP BY importance"
            ).fetchall():
                if str(imp) in out:
                    out[str(imp)] = int(n)
                out["total"] += int(n)
    except Exception:
        pass
    return out


# ── Known signals: promovering, routing, opslag ────────────────────────────

def _within_hours(iso_ts: str, hours: float) -> bool:
    """True hvis iso_ts ligger inden for de seneste `hours` timer. Self-safe → False."""
    try:
        from datetime import timedelta
        t = datetime.fromisoformat(str(iso_ts))
        return (datetime.now(UTC) - t) <= timedelta(hours=float(hours))
    except Exception:
        return False


def promote_to_known(*, signature: str, count: int, first_seen: str,
                     importance: str = "medium", category: str = "",
                     auto_threshold: int = 10, auto_window_hours: float = 24.0,
                     force: bool = False) -> str | None:
    """Promovér en anomali-signatur til 'kendt signal' hvis tærskel nået. Self-safe.

    Tærskler (spec §3.4): high/critical+3 → route_to_nerve · 50+ total → log_as_known ·
    10+ inden for 24h (first_seen frisk) → route_to_nerve · low+20 → log_as_known.
    Default nerve ved route = ``anomaly/{category}``. Returnerer den valgte action hvis
    promotion skete (eller allerede var promoveret), ellers None. `force=True` → route_to_nerve
    (til test)."""
    try:
        action: str | None = None
        if force:
            action = "route_to_nerve"
        elif importance in ("high", "critical") and count >= 3:
            action = "route_to_nerve"
        elif count >= 50:
            action = "log_as_known"
        elif count >= auto_threshold and _within_hours(first_seen, auto_window_hours):
            action = "route_to_nerve"
        elif importance == "low" and count >= 20:
            action = "log_as_known"
        if action is None:
            return None
        nerve = f"anomaly/{category}" if (action == "route_to_nerve" and category) else ""
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            _ensure_anomalies_table(conn)
            # INSERT OR IGNORE: hvis en anden proces allerede promoverede samme signatur,
            # taber vi stille (race-sikkert, §5 fund #5). known_signal sættes uanset.
            conn.execute(
                "INSERT OR IGNORE INTO known_anomaly_signals "
                "(signature, cluster, nerve, action, promoted_at, promoted_by, "
                "threshold_count, threshold_hours, count, last_seen) "
                "VALUES (?, 'anomaly', ?, ?, ?, 'auto', ?, ?, 0, ?)",
                (signature, nerve, action, now, int(auto_threshold),
                 float(auto_window_hours), now),
            )
            conn.execute(
                "UPDATE central_anomalies SET known_signal = 1 WHERE signature = ?",
                (signature,),
            )
        return action
    except Exception:
        return None


def route_anomaly_to_nerve(*, signature: str, cluster: str, nerve: str,
                           action: str = "route_to_nerve", notes: str = "",
                           promoted_by: str = "manual") -> bool:
    """Knyt én anomali-signatur til en nerve (manuel routing). Sætter known_signal=1 +
    upsert known_anomaly_signals. Self-safe → False ved fejl."""
    try:
        if not str(signature or "").strip():
            return False
        act = action if action in ("observe", "log_as_known", "route_to_nerve") else "route_to_nerve"
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            _ensure_anomalies_table(conn)
            # Upsert: manuel routing vinder over en evt. tidligere auto-promotion.
            conn.execute(
                "INSERT INTO known_anomaly_signals "
                "(signature, cluster, nerve, action, promoted_at, promoted_by, notes, count, last_seen) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?) "
                "ON CONFLICT(signature) DO UPDATE SET cluster=excluded.cluster, "
                "nerve=excluded.nerve, action=excluded.action, promoted_at=excluded.promoted_at, "
                "promoted_by=excluded.promoted_by, notes=excluded.notes",
                (signature, str(cluster or ""), str(nerve or ""), act, now,
                 str(promoted_by or "manual"), str(notes or "")[:500], now),
            )
            conn.execute(
                "UPDATE central_anomalies SET known_signal = 1 WHERE signature = ?",
                (signature,),
            )
        return True
    except Exception:
        return False


def get_known_signal(signature: str) -> dict[str, Any] | None:
    """Slå en signatur op i known_anomaly_signals. Returnerer {cluster, nerve, action}
    hvis kendt, ellers None. Self-safe."""
    try:
        with connect() as conn:
            _ensure_anomalies_table(conn)
            row = conn.execute(
                "SELECT cluster, nerve, action FROM known_anomaly_signals WHERE signature = ?",
                (str(signature or ""),),
            ).fetchone()
        if row:
            return {"cluster": row[0], "nerve": row[1], "action": row[2]}
    except Exception:
        pass
    return None


def bump_known_signal_count(signature: str) -> None:
    """Tæl en ny forekomst af et allerede-kendt signal (uden at vise det som anomali). Self-safe."""
    try:
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            _ensure_anomalies_table(conn)
            conn.execute(
                "UPDATE known_anomaly_signals SET count = count + 1, last_seen = ? "
                "WHERE signature = ?",
                (now, str(signature or "")),
            )
    except Exception:
        pass


def list_known_signals(*, limit: int = 50) -> list[dict[str, Any]]:
    """Liste over promoverede 'kendte signaler' (nyeste først). Self-sikker → []."""
    try:
        with connect() as conn:
            _ensure_anomalies_table(conn)
            rows = conn.execute(
                "SELECT signature, cluster, nerve, action, promoted_at, promoted_by, "
                "notes, count, last_seen FROM known_anomaly_signals "
                "ORDER BY last_seen DESC, promoted_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [
            {"signature": r[0], "cluster": r[1], "nerve": r[2], "action": r[3],
             "promoted_at": r[4], "promoted_by": r[5], "notes": r[6],
             "count": int(r[7]), "last_seen": r[8]}
            for r in rows
        ]
    except Exception:
        return []


def depromote_known_signal(signature: str) -> bool:
    """Angre en promotion: slet known_anomaly_signals-rækken + sæt known_signal=0 i
    central_anomalies (signaturen vises igen som anomali). Self-safe. Returnerer True hvis
    en known-række faktisk blev slettet."""
    try:
        with connect() as conn:
            _ensure_anomalies_table(conn)
            cur = conn.execute(
                "DELETE FROM known_anomaly_signals WHERE signature = ?",
                (str(signature or ""),),
            )
            deleted = cur.rowcount if cur.rowcount is not None else 0
            conn.execute(
                "UPDATE central_anomalies SET known_signal = 0 WHERE signature = ?",
                (str(signature or ""),),
            )
        return deleted > 0
    except Exception:
        return False
