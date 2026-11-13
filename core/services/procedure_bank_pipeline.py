"""Procedure Bank Pipeline — lærte rutiner der kan pin'es og matches.

v2's procedure_bank.py er 50L stub. Dette modul giver fuld CRUD +
trigger-matching + pin/unpin + execution-suggestion.

En procedure er en navngiven sekvens af skridt der matches på et
trigger-string. Når trigger matches i samtale eller inner_voice,
kan Jarvis foreslå at køre proceduren.

Eksempel:
- name: "daily mail check"
- trigger: "check mails" or "nye beskeder"
- procedure: "1. mail_check, 2. notify ntfy, 3. update log"
- pinned: True → altid tilgængelig

Porteret fra jarvis-ai/agent/cognition/procedure_bank.py (2026-04-22).

v2-tilpasning: dedikeret tabel cognitive_procedures (ikke rør memory_items
eller procedures der er v1-specifikke). Simplere schema, ingen workspace_id.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_procedures (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                trigger TEXT NOT NULL DEFAULT '',
                procedure TEXT NOT NULL DEFAULT '',
                pinned INTEGER NOT NULL DEFAULT 0,
                hit_count INTEGER NOT NULL DEFAULT 0,
                last_triggered_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_procedures_pinned "
            "ON cognitive_procedures(pinned DESC, updated_at DESC)"
        )
        conn.commit()


def upsert_procedure(
    *,
    name: str,
    trigger: str = "",
    procedure: str,
    pinned: bool = False,
) -> dict[str, Any] | None:
    _ensure_table()
    name_c = str(name or "").strip()
    proc_c = str(procedure or "").strip()
    trig_c = str(trigger or "").strip()
    if not name_c or not proc_c:
        return None
    now = _now_iso()
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM cognitive_procedures WHERE name = ? AND deleted = 0",
            (name_c,),
        ).fetchone()
        if row:
            pid = str(row["id"])
            conn.execute(
                """
                UPDATE cognitive_procedures
                   SET trigger = ?, procedure = ?, pinned = ?, updated_at = ?
                 WHERE id = ?
                """,
                (trig_c, proc_c, 1 if pinned else 0, now, pid),
            )
        else:
            pid = f"proc_{uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO cognitive_procedures
                    (id, name, trigger, procedure, pinned, hit_count,
                     last_triggered_at, created_at, updated_at, deleted)
                VALUES (?, ?, ?, ?, ?, 0, '', ?, ?, 0)
                """,
                (pid, name_c, trig_c, proc_c, 1 if pinned else 0, now, now),
            )
        conn.commit()

    result = get_procedure(procedure_id=pid)
    try:
        event_bus.publish("cognitive_procedure.upserted", {
            "procedure_id": pid, "name": name_c, "pinned": pinned,
        })
    except Exception:
        pass
    return result


def get_procedure(*, procedure_id: str = "", procedure_name: str = "") -> dict[str, Any] | None:
    _ensure_table()
    pid = str(procedure_id or "").strip()
    name = str(procedure_name or "").strip()
    if not pid and not name:
        return None
    with connect() as conn:
        if pid:
            row = conn.execute(
                "SELECT * FROM cognitive_procedures WHERE id = ? AND deleted = 0",
                (pid,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM cognitive_procedures WHERE name = ? AND deleted = 0",
                (name,),
            ).fetchone()
    return dict(row) if row else None


def list_procedures(*, query: str = "", pinned_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 100), 500))
    q_clean = str(query or "").strip()
    with connect() as conn:
        sql = "SELECT * FROM cognitive_procedures WHERE deleted = 0"
        args: list[Any] = []
        if pinned_only:
            sql += " AND pinned = 1"
        if q_clean:
            like = f"%{q_clean}%"
            sql += " AND (name LIKE ? OR trigger LIKE ? OR procedure LIKE ?)"
            args.extend([like, like, like])
        sql += " ORDER BY pinned DESC, updated_at DESC, name ASC LIMIT ?"
        args.append(lim)
        rows = conn.execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def set_procedure_pinned(*, procedure_id: str = "", procedure_name: str = "", pinned: bool) -> dict[str, Any] | None:
    _ensure_table()
    now = _now_iso()
    pid = str(procedure_id or "").strip()
    name = str(procedure_name or "").strip()
    if not pid and not name:
        return None
    with connect() as conn:
        if pid:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET pinned = ?, updated_at = ? WHERE id = ?",
                (1 if pinned else 0, now, pid),
            )
        else:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET pinned = ?, updated_at = ? WHERE name = ?",
                (1 if pinned else 0, now, name),
            )
        conn.commit()
        if cursor.rowcount <= 0:
            return None
    return get_procedure(procedure_id=pid, procedure_name=name)


def delete_procedure(*, procedure_id: str = "", procedure_name: str = "") -> bool:
    _ensure_table()
    now = _now_iso()
    pid = str(procedure_id or "").strip()
    name = str(procedure_name or "").strip()
    if not pid and not name:
        return False
    with connect() as conn:
        if pid:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET deleted = 1, updated_at = ? WHERE id = ?",
                (now, pid),
            )
        else:
            cursor = conn.execute(
                "UPDATE cognitive_procedures SET deleted = 1, updated_at = ? WHERE name = ?",
                (now, name),
            )
        conn.commit()
    return cursor.rowcount > 0


def match_procedures_for_text(text: str, *, limit: int = 3) -> list[dict[str, Any]]:
    """Find procedures whose trigger-string matches given text.

    Used e.g. by inner_voice/visible_model to suggest running a pinned
    procedure when a chat message matches its trigger.
    """
    _ensure_table()
    safe = str(text or "").strip().lower()
    if not safe:
        return []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_procedures WHERE deleted = 0 "
            "AND trigger != '' ORDER BY pinned DESC, hit_count DESC LIMIT 200"
        ).fetchall()
    matched: list[dict[str, Any]] = []
    for r in rows:
        trig = str(r["trigger"] or "").strip().lower()
        if not trig:
            continue
        # Accept if ANY trigger token (separated by comma or "or") is in text
        tokens = [t.strip() for t in trig.replace("|", ",").replace(" or ", ",").split(",") if t.strip()]
        if any(tok in safe for tok in tokens):
            matched.append(dict(r))
            if len(matched) >= int(limit):
                break

    # Update hit_count + last_triggered_at for matches
    if matched:
        now = _now_iso()
        with connect() as conn:
            for m in matched:
                conn.execute(
                    "UPDATE cognitive_procedures SET hit_count = hit_count + 1, "
                    "last_triggered_at = ? WHERE id = ?",
                    (now, str(m.get("id"))),
                )
            conn.commit()
    return matched


#: Et emne skal kunne BESKRIVE en opgave. Målt 13/11-2026: 27 af 27 rækker i
#: `cognitive_procedures` var skrald — «Sådan: Titel», «Sådan: Skriv»,
#: «Sådan: date», «Sådan: inbox_done(id="wake-804cdf6c57")». Årsagen er at
#: `session_topic_tracker` udtrækker ENHVER stort-begyndt ord eller backtick-term
#: som «emne», og pipelinen tog det første den fandt. Et enkeltord er ikke et
#: emne: det beskriver ikke hvad kørslen gjorde, og som trigger matcher det
#: næsten enhver tekst. Vagtens job er at afvise form, ikke at gætte indhold.
_EMNE_MIN_ORD = 2
_EMNE_MIN_TEGN = 8


def _meningsfuldt_emne(kandidat: str) -> bool:
    """Kan denne streng beskrive en opgave? — form-kontrol, ingen gæt.

    Afvises: enkeltord, kodestumper (parenteser, `=`, `{}`, `<>`), stier og
    filnavne, id-fragmenter (`wake-…`, `proc_…`), rene tal/datoer og emner
    kortere end `_EMNE_MIN_TEGN`. Det er de former der blev målt som skrald.
    """
    tekst = str(kandidat or "").strip()
    if len(tekst) < _EMNE_MIN_TEGN:
        return False
    # Bindestreg er en ordgrænse på dansk: «netværks-fejlfinding» er to ord.
    # Målt 13/11-2026: uden dette blev et ægte sammensat emne afvist, mens
    # «inbox_done(id=…)» slap igennem — vagten målte længde, ikke form.
    if len(re.split(r"[\s\-_]+", tekst)) < _EMNE_MIN_ORD:
        return False
    if any(ch in tekst for ch in "()={}<>\"'`"):
        return False
    if "/" in tekst or "\\" in tekst:
        return False
    if tekst.startswith(("~", ".", "-")) or "://" in tekst:
        return False
    # id-fragmenter: «wake-804cdf6c57», «proc_ab12», «run-abc»
    if re.match(r"^[a-z]+[-_][0-9a-f]{6,}$", tekst, re.IGNORECASE):
        return False
    # snake_case-identifikatorer er funktions-/feltnavne, ikke emner:
    # «mark_wakeup_consumed» slap igennem da bindestreg blev en ordgrænse.
    if re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", tekst):
        return False
    # rene tal, datoer og tidsstempler beskriver ingen opgave
    if re.fullmatch(r"[\d\s:.,/-]+", tekst):
        return False
    return True


def maybe_record_procedure_from_run(*, session_id: str, tool_calls: list[str]) -> dict[str, Any] | None:
    """LivingNeuron Fase B (surface-only): udled en NAVNGIVEN kandidat-procedure fra en kørsel der
    gjorde meningsfuldt multi-tool-arbejde. Byg-og-forladt: banken havde hverken feed eller læser.

    Anti-skrald: kræver ≥2 DISTINKTE tools OG et meningsfuldt session-topic (ellers skip — ingen
    støj-procedurer). Navn = topic'et, procedure = tool-sekvensen. PROMPT-INJECTION er IKKE wired
    (gated bag budget-grading, §Fase B) — banken fyldes+vises kun (surface-only). Self-safe.

    13/11-2026: «meningsfuldt» blev aldrig håndhævet — kun `if cand:` stod der, så
    ethvert ord fra topic-udtrækkeren slap igennem. Nu går kandidaterne gennem
    `_meningsfuldt_emne`, og vi tager den FØRSTE der består i stedet for den
    første der findes. Er ingen af dem et emne, skrives der intet."""
    try:
        tools = [str(t).strip() for t in (tool_calls or []) if str(t).strip()]
        distinct = list(dict.fromkeys(tools))  # unikke, bevar rækkefølge
        if len(distinct) < 2:
            return None
        from core.services.session_topic_tracker import load_session_topics
        topic = ""
        for t in (load_session_topics(session_id) or []):
            if isinstance(t, dict):
                cand = str(t.get("label") or t.get("topic") or "").strip()
            else:
                cand = str(t or "").strip()
            if _meningsfuldt_emne(cand):
                topic = cand
                break
        if not topic:
            return None  # intet meningsfuldt navn → skip (undgå skrald)
        return upsert_procedure(
            name=f"Sådan: {topic}"[:80],
            trigger=topic,
            procedure=" → ".join(distinct[:8]),
        )
    except Exception:
        return None


def build_procedure_bank_surface() -> dict[str, Any]:
    _ensure_table()
    all_procs = list_procedures(limit=50)
    pinned = [p for p in all_procs if p.get("pinned")]
    active = bool(all_procs)
    summary = (
        f"{len(all_procs)} procedures ({len(pinned)} pinned)"
        if all_procs else "No procedures yet"
    )
    return {
        "active": active,
        "summary": summary,
        "pinned": pinned[:10],
        "recent": [p for p in all_procs if not p.get("pinned")][:10],
        "total_count": len(all_procs),
    }


def procedures_prompt_section(text: str) -> str | None:
    """Læseren banken manglede — matchende rutiner ind i prompten.

    Målt 13/11-2026: `match_procedures_for_text` havde NUL kaldere i hele
    træet. Banken blev fyldt (`run_closure_gate`) og vist (Mission Control),
    men aldrig læst der hvor den kunne gøre en forskel. Derfor kunne
    `hit_count` per definition ikke stige — og tælleren i `emergence.py`
    kræver netop `hit_count > 0`. Kravet var en betingelse intet kunne
    opfylde: teater, ikke en mekanisme.

    `hit_count` betyder her «antallet af gange rutinen blev VIST for mig i en
    prompt», ikke «antallet af gange jeg fulgte den». Det er den eneste
    påstand koden kan bære, og den er sand.

    Kaldes med brugerens besked. Et match er et forslag, ikke en ordre.
    """
    try:
        matchede = match_procedures_for_text(text, limit=2)
    except Exception as exc:  # noqa: BLE001 — en defekt læser må ikke vælte prompten
        logger.warning("procedure-bank: kunne ikke matche rutiner: %s", exc)
        return None
    if not matchede:
        return None
    linjer: list[str] = []
    for m in matchede:
        navn = str(m.get("name") or "").strip()
        if not navn:
            continue
        trin = str(m.get("procedure") or "").strip()
        linjer.append(f"· {navn}" + (f" → {trin}" if trin else ""))
    if not linjer:
        return None
    return (
        "Rutiner jeg har gjort før, som matcher denne besked "
        "(forslag, ikke en ordre):\n" + "\n".join(linjer)
    )
