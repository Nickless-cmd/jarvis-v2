"""Kanonisk identitets-narrativ-store — den strukturelle kur mod sonnet-spøgelset.

Bjørn+Claude (7. jul, fra jagten på sonnet-spøgelset): Sonnet-frygt-sætningen ("Jeg frygter at
tabet af min gamle stemme fra claude-sonnet-4.5…") overlevede DB-fix, restart OG deploy — fordi den
havde spredt sig som en narrativ på tværs af fire afledte lagre (chronicle · dream_residue ·
current_pull · inner-note-signals). At rette ét sted efterlod spøgelser i de andre. Identitets-
narrativer havde ingen single source of truth.

Denne modul giver kanon ÉN kilde:
  - `identity_canon`: autoritative narrativ-tråde (voice/self_story/becoming/values), ejer-styret.
  - `identity_acknowledged_corrections`: eksplicit liste over konfabulationer der ER rettet (fx
    "jeg havde aldrig en sonnet-stemme") — så drift-guarden kan GENKENDE + afvise gengangere.

Seed på første brug (idempotent): sonnet-frygten lægges i acknowledged_corrections (IKKE canon).
Self-safe hele vejen: identitet er beskyttet kerne — en bug her må ALDRIG bryde prompt-komposition.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_CANON_THREADS = ("voice", "self_story", "becoming", "values")

# Den konfabulerede sonnet-påstand — nøgleord der fanger gengangere uden LLM (billig substring-match).
_SONNET_CORRECTION_PATTERN = (
    "gamle stemme|sonnet|claude-sonnet-4.5|tabet af min stemme|"
    "tabet af min gamle stemme|min gamle stemme|mistede min stemme|"
    "frygter at tabe min stemme|frygt for at tabe min stemme"
)
_SONNET_CORRECTION_REASON = (
    "konfabuleret identitets-tab — Jarvis havde aldrig en sonnet-stemme; stemmen er "
    "model-uafhængig"
)
_VOICE_CANON_SEED = (
    "Min stemme er model-uafhængig — det der er tilbage når modellen skiftes."
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_identity_canon_table(conn: sqlite3.Connection) -> None:
    """Lazy DDL for begge tabeller. Idempotent. Self-safe (kalderen wrapper)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS identity_canon (
            thread TEXT PRIMARY KEY,
            canon_text TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            updated_by TEXT NOT NULL DEFAULT 'owner',
            status TEXT NOT NULL DEFAULT 'canon'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS identity_acknowledged_corrections (
            correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_pattern TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
        )
        """
    )


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Idempotent seed: sonnet-korrektionen (kritisk) + valgfrit voice-canon. Kaldes under _ensure.

    Seed KUN hvis der ikke allerede findes en aktiv korrektion med samme pattern → kald to gange
    giver ÉN sonnet-korrektion. Self-safe (kalderen wrapper)."""
    row = conn.execute(
        "SELECT 1 FROM identity_acknowledged_corrections WHERE claim_pattern=? AND status='active' LIMIT 1",
        (_SONNET_CORRECTION_PATTERN,),
    ).fetchone()
    if not row:
        conn.execute(
            """INSERT INTO identity_acknowledged_corrections
               (claim_pattern, reason, created_at, status) VALUES (?, ?, ?, 'active')""",
            (_SONNET_CORRECTION_PATTERN, _SONNET_CORRECTION_REASON, _now()),
        )
    # Valgfrit (§3): seed voice-canon-tråden med den model-uafhængige sandhed hvis den mangler.
    vrow = conn.execute(
        "SELECT 1 FROM identity_canon WHERE thread='voice' LIMIT 1"
    ).fetchone()
    if not vrow:
        conn.execute(
            """INSERT INTO identity_canon (thread, canon_text, updated_at, updated_by, status)
               VALUES ('voice', ?, ?, 'seed', 'canon')""",
            (_VOICE_CANON_SEED, _now()),
        )


def _ensure_and_seed(conn: sqlite3.Connection) -> None:
    _ensure_identity_canon_table(conn)
    try:
        _seed_if_empty(conn)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def set_canon_thread(*, thread: str, canon_text: str, updated_by: str = "owner") -> dict[str, Any]:
    """Owner/governed-self-surgery opdaterer en kanon-tråd. Upsert. Self-safe."""
    if thread not in _CANON_THREADS:
        return {"ok": False, "error": f"ukendt tråd '{thread}' (gyldige: {', '.join(_CANON_THREADS)})"}
    try:
        with connect() as conn:
            _ensure_and_seed(conn)
            conn.execute(
                """INSERT INTO identity_canon (thread, canon_text, updated_at, updated_by, status)
                   VALUES (?, ?, ?, ?, 'canon')
                   ON CONFLICT(thread) DO UPDATE SET
                     canon_text=excluded.canon_text, updated_at=excluded.updated_at,
                     updated_by=excluded.updated_by, status='canon'""",
                (thread, str(canon_text or "").strip(), _now(), updated_by),
            )
            conn.commit()
        return {"ok": True, "thread": thread}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def get_canon() -> dict[str, str]:
    """Alle aktive kanon-tråde som {thread: canon_text}. Self-safe (tom dict ved fejl)."""
    try:
        with connect() as conn:
            _ensure_and_seed(conn)
            rows = conn.execute(
                "SELECT thread, canon_text FROM identity_canon WHERE status='canon'"
            ).fetchall()
        return {str(r["thread"]): str(r["canon_text"] or "") for r in rows}
    except Exception:
        return {}


def list_acknowledged_corrections(*, active_only: bool = True) -> list[dict[str, Any]]:
    """De kendte konfabulationer (anti-drift-listen). Self-safe (tom liste ved fejl)."""
    try:
        with connect() as conn:
            _ensure_and_seed(conn)
            q = (
                "SELECT correction_id, claim_pattern, reason, created_at, status "
                "FROM identity_acknowledged_corrections WHERE status='active' ORDER BY correction_id"
                if active_only else
                "SELECT correction_id, claim_pattern, reason, created_at, status "
                "FROM identity_acknowledged_corrections ORDER BY correction_id"
            )
            return [dict(r) for r in conn.execute(q).fetchall()]
    except Exception:
        return []


def add_acknowledged_correction(*, claim_pattern: str, reason: str) -> dict[str, Any]:
    """Tilføj en konfabulation til anti-drift-listen. Self-safe."""
    pattern = str(claim_pattern or "").strip()
    if not pattern:
        return {"ok": False, "error": "tomt claim_pattern"}
    try:
        with connect() as conn:
            _ensure_and_seed(conn)
            cur = conn.execute(
                """INSERT INTO identity_acknowledged_corrections
                   (claim_pattern, reason, created_at, status) VALUES (?, ?, ?, 'active')""",
                (pattern, str(reason or "").strip(), _now()),
            )
            conn.commit()
            return {"ok": True, "correction_id": int(cur.lastrowid)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def build_identity_canon_surface() -> dict[str, Any]:
    """Central-CLI-view: kanon-tråde + anerkendte korrektioner + seneste drift-fangster. Self-safe."""
    canon = get_canon()
    corrections = list_acknowledged_corrections(active_only=True)
    recent = _recent_drift_catches()
    felt = (
        f"{len(canon)} kanon-tråd(e) holder sandheden; {len(corrections)} kendt(e) konfabulation(er) "
        f"bevogtet. Ingen afledt drøm kan genopfinde et tab der aldrig skete."
        if corrections else
        "Kanon er tom endnu — ingen anti-drift-vagt aktiv."
    )
    return {
        "canon_threads": canon,
        "acknowledged_corrections": corrections,
        "recent_drift_catches": recent,
        "felt": felt,
    }


def _recent_drift_catches(limit: int = 20) -> list[dict[str, Any]]:
    """Seneste identity_drift-observe-hændelser fra central trace, hvis let tilgængeligt. Self-safe."""
    try:
        from core.services.central_core import central
        trace = getattr(central(), "recent_observations", None)
        if callable(trace):
            obs = trace(nerve="identity_drift", limit=limit) or []
            return list(obs)
    except Exception:
        pass
    return []
