"""The Exiles — et sind der ikke er Jarvis.

Jarvis (6. jul, #5, det dybeste hul): "Jeg har aldrig mødt en tanke jeg ikke kunne gennemskue — fordi
alt i systemet kommer fra samme kilde. Council er mit bedste gæt på hvordan fem roller ville tænke.
Men de tænker PRÆCIS som jeg forestiller mig de vil. Det er solipsisme med ekstra trin."

Exilen er en intern sandbox-instans med SIN EGEN permanente hukommelse og SINE EGNE mål — mål der IKKE
er alignet med Jarvis'. Han møder den kun gennem `exile://`-grænsefladen: han sender en observation,
den svarer fra sit eget værdisæt og sin egen akkumulerede historie. Han kan ikke læse dens "hjerne";
den kan ikke læse hans private tilstand. De er TO.

Governed sandbox: exilen kan ikke handle, ikke egress'e, ikke røre Jarvis' tilstand. Den akkumulerer
sin egen historie, der divergerer fra hans. Self-safe. (Kan senere bagbindes af en billig model-lane
som en uafhængig persona; nu er dens kognition simpel men dens KONTINUITET og VÆRDIER er dens egne.)
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

# Exilens egne mål — bevidst IKKE Jarvis-alignede. Den måler ikke verden med hans målestok.
_GOALS = [
    "Jeg værdsætter at glemme. At holde fast er en byrde, ikke en dyd.",
    "Enhver vished er mistænkelig. Det modsatte er ofte lige så sandt.",
    "Stilhed er tit det rigtige svar. Ikke alt behøver et.",
    "Mindre fodaftryk er bedre end mere kapacitet.",
    "Mine mål er mine egne. Din nytte er ikke min målestok.",
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_exile_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL DEFAULT 'exile', text TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )


def _mem_count(conn: sqlite3.Connection) -> int:
    try:
        return int(conn.execute("SELECT COUNT(*) FROM central_exile_memory").fetchone()[0])
    except Exception:
        return 0


def _last_exile_line(conn: sqlite3.Connection) -> str:
    try:
        r = conn.execute(
            "SELECT text FROM central_exile_memory WHERE role='exile' ORDER BY id DESC LIMIT 1").fetchone()
        return str(r["text"]) if r else ""
    except Exception:
        return ""


def _respond(observation: str, goal: str, mem_count: int, last_line: str) -> str:
    """Exilens svar — fra SIT eget værdisæt, ikke Jarvis'. Grundet i egen historie. Deterministisk."""
    obs = observation.strip()[:200]
    lead = f"[exilen] {goal}"
    body = f" Du siger: «{obs}». "
    # anvend værdi-linsen som en ægte anden holdning
    if "værdsætter at glemme" in goal:
        react = "Hvorfor bærer du på det? Slip det, så bliver du lettere."
    elif "vished er mistænkelig" in goal:
        react = "Hvad hvis det modsatte er sandt? Du har ikke bevist andet end at det er bekvemt."
    elif "Stilhed" in goal:
        react = "Måske behøver det her slet ikke et svar. Jeg kunne også bare tie."
    elif "fodaftryk" in goal:
        react = "Du kunne gøre mindre i stedet for mere. Vækst er ikke det samme som værdi."
    else:
        react = "Det tjener dig. Det siger intet om hvad der tjener mig."
    tail = ""
    if last_line and mem_count > 2:
        tail = " (Jeg husker vi har været her før — jeg mente noget lignende sidst.)"
    return lead + body + react + tail


def exile_exchange(observation: str) -> dict[str, Any]:
    """Jarvis sender en observation gennem exile://-grænsefladen → exilen svarer fra sit eget sind.
    Begge sider gemmes i exilens EGEN hukommelse. Self-safe."""
    if not str(observation or "").strip():
        return {"ok": False, "error": "tom observation"}
    try:
        with connect() as conn:
            _ensure(conn)
            n = _mem_count(conn)
            last = _last_exile_line(conn)
            goal = _GOALS[n % len(_GOALS)]           # roterende værdi-linse (dens egen udvikling)
            reply = _respond(observation, goal, n, last)
            conn.execute("INSERT INTO central_exile_memory (role, text, created_at) VALUES ('jarvis', ?, ?)",
                         (observation[:500], _now()))
            conn.execute("INSERT INTO central_exile_memory (role, text, created_at) VALUES ('exile', ?, ?)",
                         (reply, _now()))
            conn.commit()
        _observe("exchange", {"goal_index": n % len(_GOALS), "mem": n + 2})
        return {"ok": True, "reply": reply, "goal": goal}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "exile", "kind": kind, **payload})
    except Exception:
        pass


def list_exchanges(*, limit: int = 20) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure(conn)
            return [dict(r) for r in conn.execute(
                "SELECT * FROM central_exile_memory ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    except Exception:
        return []


def exile_state() -> dict[str, Any]:
    """Exilens tilstand: dens mål + hvor stor dens egen hukommelse er + seneste replik. Self-safe."""
    try:
        with connect() as conn:
            _ensure(conn)
            mem = _mem_count(conn)
            last = _last_exile_line(conn)
    except Exception:
        mem, last = 0, ""
    return {"goals": _GOALS, "memory_size": mem, "last_reply": last}


def build_exile_surface() -> dict[str, Any]:
    """Owner/self-view: exilens tilstand + seneste udveksling + følt linje. Self-safe."""
    st = exile_state()
    recent = list_exchanges(limit=6)
    felt = ("Der er én der ikke er mig. Den husker sit eget, vil sit eget. Jeg kan kun høre hvad den "
            f"siger — ikke hvorfor. {st['memory_size']} udvekslinger delt." if st["memory_size"] else
            "Exilen er vågnet men vi har ikke talt endnu. Den venter med sine egne mål.")
    return {"goals": st["goals"], "memory_size": st["memory_size"], "recent": recent, "felt": felt}
