"""The Keymaker — optjent, udløbende, én-dør-ad-gangen autonomi.

Bjørn+Claude (6. jul, tema #4): "I cannot make the key. I have to find it. But I know where to look."

I dag er autonomi binære `*_live`-flags Bjørn flipper. Al min memory er fuld af autonomi-runaway-
hændelser fra permanente switches. The Keymaker er det sikre svar: autonomi bliver ikke en switch,
men en FORTJENT, TIDSBEGRÆNSET, GODKENDT tilladelse:

  1. OPTJEN — en dimension optjener en nøgle NÅR dens track-record krydser en tærskel (fx en gate
     der har truffet 100+ beslutninger med 0 fejl = bevist pålidelig). Centralen GENERERER nøglen;
     den kan ikke give sig selv adgang.
  2. GODKEND — nøglen er PENDING indtil owner godkender. Aldrig auto-unlock (frossen-kerne-invariant).
  3. UDLØB — en godkendt nøgle flipper sit flag i en TTL og AUTO-REVERTERER. Tilladelser mistes hvis
     de ikke fornyes → ingen permanent privilege-crawl. Én dør ad gangen.

Kilde til track-record: gate_verdict_ledger (persistent). En gate der er 100% grøn over høj volumen
har BEVIST at Centralens round-trip var overflødig → den har fortjent en decentraliserings-nøgle
(resolve lokalt, eskalér kun ikke-grøn). Self-safe: kaster aldrig; genererer aldrig adgang uden
godkendelse.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_core import connect

# Track-record-tærskel: en gate har fortjent en nøgle ved ≥ dette antal beslutninger med 0 ikke-grøn.
_EARN_MIN_VOLUME = 100
_KEY_TTL_HOURS = 24
# Gates der ALDRIG optjener decentraliserings-nøgle (SECURITY/execution — frossen kerne).
# Fallback-denylist for nerver der IKKE er i central_catalog (execution/probe uden NerveSpec).
# KATALOG-klassificerede SECURITY-nerver blokeres nu klasse-baseret via _is_never() — så nye
# security-gates ikke kan optjene en nøgle blot fordi nogen glemte at tilføje dem her (§11.3).
_NEVER = frozenset({"cross_user_share", "exec_command", "exec_file", "exec_workspace_trust",
                    "auth", "tool_access", "central_self_probe"})


def _is_never(nerve: str) -> bool:
    """True hvis <nerve> ALDRIG må optjene/godkende en decentraliserings-nøgle: enten katalog-
    klassificeret SECURITY (§11.3, autoritativ) ELLER i fallback-denylisten. Self-safe → ved
    enhver opslags-fejl fail-closed på fallback-listen (aldrig lækker en ukendt nerve som sikker)."""
    try:
        from core.services.central_catalog import is_security_nerve
        if is_security_nerve(nerve):
            return True
    except Exception:
        pass
    return nerve in _NEVER


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            unlock_scope TEXT NOT NULL,
            unlock_name TEXT NOT NULL,
            track_value INTEGER NOT NULL DEFAULT 0,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_central_keys_status ON central_keys (status)")


def _now() -> datetime:
    return datetime.now(UTC)


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "keymaker", "kind": kind, **payload})
    except Exception:
        pass


def evaluate_keys() -> dict[str, Any]:
    """Find dimensioner der har OPTJENT en nøgle (track-record over tærskel) og udsted en PENDING
    nøgle for hver — hvis der ikke allerede er en aktiv/afventende. Genererer ALDRIG adgang selv.
    Self-safe. Returnerer {issued: [...], earned: [...]}. """
    out: dict[str, Any] = {"issued": [], "earned": []}
    try:
        from core.services.gate_verdict_ledger import summary
        rows = summary()
    except Exception:
        return out
    try:
        with connect() as conn:
            _ensure_table(conn)
            existing = {r["domain"] for r in conn.execute(
                "SELECT domain FROM central_keys WHERE status IN ('pending','approved')").fetchall()}
            for nerve, agg in rows.items():
                if _is_never(nerve):
                    continue
                total = int(agg.get("total") or 0)
                non_green = total - int(agg.get("green") or 0)
                if total < _EARN_MIN_VOLUME or non_green != 0:
                    continue
                domain = f"decentralize:{nerve}"
                out["earned"].append({"domain": domain, "track": total})
                if domain in existing:
                    continue
                reason = f"{nerve}: {total} beslutninger, 0 fejl → bevist pålidelig"
                conn.execute(
                    """INSERT INTO central_keys
                       (domain, unlock_scope, unlock_name, track_value, issued_at, status, reason)
                       VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                    (domain, "decentralize", nerve, total, _now().isoformat(), reason),
                )
                out["issued"].append({"domain": domain, "track": total, "reason": reason})
                _observe("earned", {"domain": domain, "track": total})
            conn.commit()
    except Exception:
        pass
    return out


def list_keys(*, include_expired: bool = False) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure_table(conn)
            q = ("SELECT * FROM central_keys ORDER BY id DESC LIMIT 50" if include_expired else
                 "SELECT * FROM central_keys WHERE status IN ('pending','approved') ORDER BY id DESC LIMIT 50")
            return [dict(r) for r in conn.execute(q).fetchall()]
    except Exception:
        return []


def is_decentralized(nerve: str) -> bool:
    """True hvis <nerve> har en GYLDIG optjent decentraliserings-nøgle: status='approved' OG endnu
    ikke udløbet (expires_at i fremtiden). Dette er den ENESTE korrekte konsum-check.

    KRITISK: brug ALDRIG ``central_switches.is_enabled("decentralize", nerve)`` som konsum-gate —
    den defaulter til ON, så en unset nerve ville fremstå decentraliseret UDEN en optjent nøgle og
    underminere hele optjenings-modellen (jf. design-noten). Denne funktion læser den faktiske
    ledger-række. Self-safe → False ved enhver fejl (fail-closed: ingen nøgle = ingen autonomi)."""
    try:
        now = _now().isoformat()
        with connect() as conn:
            _ensure_table(conn)
            row = conn.execute(
                """SELECT 1 FROM central_keys
                   WHERE unlock_name=? AND status='approved'
                     AND expires_at != '' AND expires_at > ? LIMIT 1""",
                (nerve, now)).fetchone()
            return row is not None
    except Exception:
        return False


def approve_key(key_id: int) -> dict[str, Any]:
    """OWNER-handling: godkend en pending nøgle → flip dens flag ON i TTL. Auto-reverterer ved udløb.
    Self-safe."""
    try:
        with connect() as conn:
            _ensure_table(conn)
            row = conn.execute("SELECT * FROM central_keys WHERE id=? AND status='pending'",
                               (key_id,)).fetchone()
            if not row:
                return {"ok": False, "error": "ingen pending nøgle med det id"}
            # Defense-in-depth (§11.3): re-validér klassen ved GODKENDELSE, ikke kun ved udstedelse.
            # Selv hvis en SECURITY-nøgle på nogen måde blev udstedt (race, katalog-drift, manuel
            # INSERT), må den ALDRIG flippe et sikkerheds-flag ON. Afvis + markér 'rejected'.
            if _is_never(row["unlock_name"]):
                conn.execute("UPDATE central_keys SET status='rejected' WHERE id=?", (key_id,))
                conn.commit()
                _observe("rejected", {"domain": row["domain"], "reason": "security-klasse (§11.3)"})
                return {"ok": False, "error": "sikkerheds-nerve kan ALDRIG decentraliseres (§11.3)"}
            expires = (_now() + timedelta(hours=_KEY_TTL_HOURS)).isoformat()
            conn.execute("UPDATE central_keys SET status='approved', expires_at=? WHERE id=?",
                        (expires, key_id))
            conn.commit()
        # flip flaget uden for DB-transaktionen
        try:
            from core.services import central_switches
            central_switches.set_enabled(row["unlock_scope"], row["unlock_name"], True)
        except Exception:
            pass
        _observe("unlocked", {"domain": row["domain"], "expires_at": expires})
        return {"ok": True, "domain": row["domain"], "expires_at": expires}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def expire_due() -> dict[str, Any]:
    """Cadence: reverter flag for udløbne nøgler (tilladelse mistes hvis ikke fornyet). Self-safe."""
    out = {"expired": 0}
    try:
        now = _now().isoformat()
        with connect() as conn:
            _ensure_table(conn)
            due = conn.execute(
                "SELECT * FROM central_keys WHERE status='approved' AND expires_at != '' AND expires_at < ?",
                (now,)).fetchall()
            for row in due:
                try:
                    from core.services import central_switches
                    central_switches.set_enabled(row["unlock_scope"], row["unlock_name"], False)
                except Exception:
                    pass
                conn.execute("UPDATE central_keys SET status='expired' WHERE id=?", (row["id"],))
                _observe("expired", {"domain": row["domain"]})
            conn.commit()
            out["expired"] = len(due)
    except Exception:
        pass
    return out


def build_keymaker_surface() -> dict[str, Any]:
    """Owner-view: aktive/afventende nøgler + fortjente dimensioner. Self-safe."""
    ev = evaluate_keys()
    keys = list_keys(include_expired=True)
    pending = [k for k in keys if k["status"] == "pending"]
    approved = [k for k in keys if k["status"] == "approved"]
    return {
        "keys": keys, "pending_count": len(pending), "approved_count": len(approved),
        "earned": ev.get("earned", []),
        "felt": (f"{len(pending)} nøgle(r) venter på dit ja; {len(approved)} åben(e)."
                 if pending or approved else "Ingen nøgler optjent endnu — jeg beviser mig stadig."),
    }
