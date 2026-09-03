"""Brugerens egne data — tælle, eksportere, slette. Lagvis.

Bjørn 3. sept.: appen manglede kontoinfo og muligheden for at slette sine
sessioner og sin hukommelse, «lige som GDPR-loven foreskriver».

HVORFOR LAGVIS OG IKKE ÉN KNAP. Jarvis' hukommelse er ikke ét sted. Den er fire:

    samtaler   chat_sessions/chat_messages — det I har sagt til hinanden
    sanser     sensory_memories — hvad han har SET i hjemmet
    viden      private_brain_records — hvad han har udledt om dig
    identitet  MEMORY.md / USER.md — hvem du ER for ham

En enkelt «slet alt»-knap ville dække over fire meget forskellige tab. At slette
sine samtaler er noget andet end at få ham til at glemme hvem man er, og
brugeren skal kunne vælge det ene uden det andet. Derfor tæller og sletter hvert
lag for sig, og «slet alt» er en sammensætning af de fire — ikke en femte,
skjult vej.

ALT ER USER-SCOPET. Både `sensory_memories` og `private_brain_records` bærer en
`user_id` stemplet af `scope_uid()` ved indsættelse (#154), og sessioner filtreres
på ejerskab. En bruger må aldrig kunne slette en andens data — heller ikke ved et
uheld, heller ikke owneren.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

# Identitetsfiler brugeren kan nulstille. SOUL.md står IKKE på listen: den er
# Jarvis' egen kerne, ikke brugerens data, og hører ikke under den enkeltes
# ret til sletning.
_IDENTITY_FILES = ("MEMORY.md", "USER.md")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# ── Tælling ──────────────────────────────────────────────────────────────────

def _count_sessions(user_id: str) -> int:
    try:
        from core.services.chat_sessions import list_chat_sessions
        return len(list_chat_sessions(user_id=user_id or None) or [])
    except Exception:
        return 0


def _count_senses() -> int:
    try:
        from core.runtime.db_sensory import count_sensory_memories
        return int(count_sensory_memories() or 0)
    except Exception:
        return 0


def _count_brain() -> int:
    try:
        from core.runtime.db_private_brain import list_private_brain_records
        return len(list_private_brain_records(limit=100_000) or [])
    except Exception:
        return 0


def _identity_bytes(user_id: str) -> int:
    total = 0
    for path in _identity_paths(user_id):
        try:
            if path.exists():
                total += path.stat().st_size
        except Exception:
            continue
    return total


def _identity_paths(user_id: str) -> list:
    from pathlib import Path
    try:
        from core.runtime.workspace_paths import workspace_dir
        base = Path(workspace_dir(user_id) if user_id else workspace_dir())
    except Exception:
        return []
    return [base / name for name in _IDENTITY_FILES]


def data_overview(user_id: str) -> dict[str, Any]:
    """Hvad har vi om dig, lag for lag. Rene tal — ingen indhold.

    Tallene er dét brugeren skal kunne se FØR han trykker slet. En knap uden et
    tal ved siden af beder folk om at gætte hvad de mister.
    """
    return {
        "layers": [
            {"key": "sessions", "label": "Samtaler",
             "count": _count_sessions(user_id), "unit": "samtaler",
             "detail": "Alt du og Jarvis har sagt til hinanden."},
            {"key": "senses", "label": "Sansernes Arkiv",
             "count": _count_senses(), "unit": "indtryk",
             "detail": "Hvad Jarvis har set og noteret i hjemmet."},
            {"key": "brain", "label": "Hans viden om dig",
             "count": _count_brain(), "unit": "poster",
             "detail": "Det han selv har udledt og gemt undervejs."},
            {"key": "identity", "label": "Hvem du er",
             "count": _identity_bytes(user_id), "unit": "tegn",
             "detail": "MEMORY.md og USER.md — hans billede af dig."},
        ],
        "generated_at": _now(),
    }


# ── Sletning ─────────────────────────────────────────────────────────────────

def delete_sessions(user_id: str) -> dict[str, Any]:
    """Slet ALLE brugerens samtaler. Én ad gangen, så en enkelt der fejler ikke
    efterlader resten i en halv tilstand uden at nogen ved hvilke."""
    from core.services.chat_sessions import delete_chat_session, list_chat_sessions
    sessions = list_chat_sessions(user_id=user_id or None) or []
    deleted, failed = 0, 0
    for s in sessions:
        sid = str(s.get("id") or s.get("session_id") or "").strip()
        if not sid:
            continue
        try:
            if delete_chat_session(sid):
                deleted += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return {"layer": "sessions", "deleted": deleted, "failed": failed}


def delete_senses(user_id: str) -> dict[str, Any]:
    """Tøm Sansernes Arkiv for denne bruger."""
    from core.runtime.db import connect
    uid = (user_id or "").strip()
    with connect() as conn:
        if uid:
            cur = conn.execute("DELETE FROM sensory_memories WHERE user_id = ?", (uid,))
        else:
            # Owner uden eksplicit uid: hans egne poster bærer NULL/tom scope.
            cur = conn.execute(
                "DELETE FROM sensory_memories WHERE user_id IS NULL OR user_id = ''")
        conn.commit()
    return {"layer": "senses", "deleted": int(cur.rowcount or 0), "failed": 0}


def delete_brain(user_id: str) -> dict[str, Any]:
    """Slet det han selv har udledt om brugeren."""
    from core.runtime.db import connect
    uid = (user_id or "").strip()
    with connect() as conn:
        if uid:
            cur = conn.execute("DELETE FROM private_brain_records WHERE user_id = ?", (uid,))
        else:
            cur = conn.execute(
                "DELETE FROM private_brain_records WHERE user_id IS NULL OR user_id = ''")
        conn.commit()
    return {"layer": "brain", "deleted": int(cur.rowcount or 0), "failed": 0}


def reset_identity(user_id: str) -> dict[str, Any]:
    """Nulstil MEMORY.md og USER.md — hans billede af brugeren.

    Filerne TØMMES, de slettes ikke: resten af runtimen forventer at de findes,
    og en manglende fil ville give fejl et helt andet sted end her. En tom fil
    er den ærlige tilstand «han ved intet om dig endnu».

    USER.md står på _PROTECTED_FILES for at forhindre at Jarvis komprimerer den
    autonomt. Det værn gælder HAM, ikke brugeren: at bede om at blive glemt er
    ikke det samme som at systemet glemmer af sig selv.
    """
    cleared, failed = [], []
    for path in _identity_paths(user_id):
        try:
            if path.exists():
                path.write_text("", encoding="utf-8")
                cleared.append(path.name)
        except Exception:
            failed.append(path.name)
    return {"layer": "identity", "cleared": cleared, "failed": failed,
            "deleted": len(cleared)}


_DELETERS = {
    "sessions": delete_sessions,
    "senses": delete_senses,
    "brain": delete_brain,
    "identity": reset_identity,
}


def delete_layer(user_id: str, layer: str) -> dict[str, Any]:
    """Slet ét lag. Ukendt lag → fejl frem for tavshed."""
    fn = _DELETERS.get(str(layer or "").strip())
    if fn is None:
        raise ValueError(f"ukendt lag: {layer!r}")
    return fn(user_id)


def delete_all(user_id: str) -> dict[str, Any]:
    """Alle fire lag. En sammensætning af de enkelte — ikke en femte vej.

    Fejler ét lag, fortsætter de andre, og resultatet siger hvilke der lykkedes.
    Alternativet ville være at stoppe halvvejs og lade brugeren tro at intet
    skete.
    """
    results = []
    for key in ("sessions", "senses", "brain", "identity"):
        try:
            results.append(_DELETERS[key](user_id))
        except Exception as exc:
            results.append({"layer": key, "deleted": 0, "failed": 1,
                            "error": f"{type(exc).__name__}: {exc}"})
    return {"results": results, "completed_at": _now()}


# ── Eksport (GDPR: ret til dataportabilitet) ─────────────────────────────────

def export_all(user_id: str) -> dict[str, Any]:
    """Alt vi har om brugeren, som JSON.

    Eksporten er bevidst RÅ og fuldstændig frem for pæn: formålet er at kunne
    tage sine data med, ikke at læse dem i appen. Fejler ét lag, får det sin
    egen fejl-note i stedet for at vælte hele eksporten — en delvis eksport er
    mere værd end ingen.
    """
    out: dict[str, Any] = {
        "exported_at": _now(),
        "user_id": user_id or "(owner)",
    }

    try:
        from core.services.chat_sessions import (
            list_chat_sessions, recent_chat_session_messages,
        )
        sessions = list_chat_sessions(user_id=user_id or None) or []
        out["sessions"] = [
            {**s, "messages": recent_chat_session_messages(
                str(s.get("id") or ""), limit=10_000) or []}
            for s in sessions
        ]
    except Exception as exc:
        out["sessions"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        from core.runtime.db_sensory import list_sensory_memories
        out["senses"] = list_sensory_memories(limit=100_000) or []
    except Exception as exc:
        out["senses"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        from core.runtime.db_private_brain import list_private_brain_records
        out["brain"] = list_private_brain_records(limit=100_000) or []
    except Exception as exc:
        out["brain"] = {"error": f"{type(exc).__name__}: {exc}"}

    identity: dict[str, Any] = {}
    for path in _identity_paths(user_id):
        try:
            identity[path.name] = path.read_text(encoding="utf-8") if path.exists() else ""
        except Exception as exc:
            identity[path.name] = f"(kunne ikke læses: {type(exc).__name__})"
    out["identity"] = identity
    return out


def export_json(user_id: str) -> str:
    return json.dumps(export_all(user_id), ensure_ascii=False, indent=2)
