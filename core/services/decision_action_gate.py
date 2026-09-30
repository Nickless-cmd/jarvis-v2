"""Current-turn opportunities for three low-adherence behavioral decisions.

The deterministic checks deliberately distinguish a proven action from an
unconfirmed one. They do not write behavioral_decision_reviews or change the
rolling adherence score; those still require the independent review path.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime, timedelta

from core.runtime.db import connect
from core.services.decision_evidence import _citat_traef
from core.services.experience_correction_listener import (
    _looks_like_acknowledgement,
    _looks_like_correction,
)


_EXPLICIT_ERROR = re.compile(
    r"\b(du tog fejl|du tager fejl|du misforstod|det var forkert|forkert svar|"
    r"din fejl|du havde uret|det kan ikk?e? passe|det passer ikke)\b|^\s*forkert\b",
    re.IGNORECASE,
)
_HISTORY = re.compile(
    r"\b(sidst|tidligere|førhen|forrige|husker du|kan du huske|"
    r"vi aftalte|vi besluttede|du sagde|din historie|vores historie|"
    r"hvilken fil|hvad står der i filen|hvad står der i repo|"
    r"hvilke? commits?|sidste commit)\b",
    re.IGNORECASE,
)
_REPO_QUESTION = re.compile(
    r"\b(hvad|hvor|hvordan|hvilke?|kan du finde)\b[^?.!\n]{0,90}"
    r"\b(repo(?:et|ets)?|kodebasen|projektets kode)\b",
    re.IGNORECASE,
)
_IMPLIED_CORRECTION = re.compile(
    r"\b(står stadig|er stadig forkert|kan (?:også|osse) vise|"
    r"kan (?:også|osse) se|den ene ting der ikke går op)\b",
    re.IGNORECASE,
)
_JARVIS_ANALYSIS_WRONG = re.compile(
    r"\bjarvis['’]?(?:s)?\s+(?:tal|analyse|påstand|konklusion)\b"
    r"[^.!?\n]{0,180}\b(?:strider|vendt om|forkert|ikke korrekt)\b",
    re.IGNORECASE,
)
_MEMORY_TOOLS = frozenset({
    "recall", "search_memory", "recall_memories", "search_jarvis_brain",
    "unified_recall", "recall_before_act", "read_brain_entry",
})


def _turn_text(user_message: str) -> str:
    """Discard the transport's attachment instructions before classifying words."""
    text = str(user_message or "").strip()
    if text.startswith("[The user attached ") and "\n\n---\n\n" in text:
        text = text.split("\n\n---\n\n", 1)[1].strip()
    return text


def _correction_excerpt(user_message: str) -> str:
    """Use the challenged claim, not a long paste's unrelated opening words."""
    text = _turn_text(user_message)
    for pattern in (_JARVIS_ANALYSIS_WRONG, _IMPLIED_CORRECTION, _EXPLICIT_ERROR):
        match = pattern.search(text[:4000])
        if match:
            return text[max(0, match.start() - 60): match.end() + 140]
    return text[:300]


def opportunities(user_message: str) -> set[str]:
    """Return only triggers with a concrete observable opportunity."""
    text = _turn_text(user_message)
    if not text:
        return set()
    found: set[str] = set()
    # The existing listener only scans the first 240 characters. Direct user
    # feedback also arrives as "still" / "can also", and a long Claude paste
    # can correct Jarvis' analysis after its introductory sentence.
    direct_error = bool(_EXPLICIT_ERROR.search(text[:400]))
    analysis_error = bool(_JARVIS_ANALYSIS_WRONG.search(text[:4000]))
    if (_looks_like_correction(text) or direct_error or analysis_error
            or _IMPLIED_CORRECTION.search(text[:500])):
        found.add("quote")
        if direct_error or analysis_error:
            found.add("admit")
    if _HISTORY.search(text[:500]) or _REPO_QUESTION.search(text[:500]):
        found.add("memory")
    return found


def query_current_memory(user_message: str, session_id: str | None) -> str | None:
    """Read current-turn memory; the caller gives this a bounded future."""
    from core.services.recall import recall

    result = recall(_turn_text(user_message)[:500], limit=3, session_id=session_id)
    if result.get("status") != "ok":
        return None
    return str(result.get("text") or "")[:1200] or None


def action_section(user_message: str, *, recall_text: str | None) -> str:
    """A short volatile prompt tail, immediately before the current answer."""
    due = opportunities(user_message)
    if not due:
        return ""
    lines = ["[Aktiv forpligtelse i denne tur]"]
    if "quote" in due:
        lines.append(
            "Brugeren rettede eller standsede dig. Gengiv først kort den konkrete "
            "pointe i den seneste brugerbesked, før du fortsætter."
        )
    if "admit" in due:
        lines.append("Hvis din tidligere påstand var forkert, tag ansvar for fejlen i første del af svaret.")
    if "memory" in due:
        if recall_text:
            lines.append("Hukommelsen blev søgt i denne tur. Brug kun relevante fund, og verificér aktuelle fakta.")
            lines.append(recall_text[:1200])
        else:
            lines.append("Hukommelsesopslaget gav intet svar i tide. Brug recall før du svarer på egen historie.")
    lines.append("[/Aktiv forpligtelse]")
    return "\n".join(lines)


def evaluate_turn(
    *, user_message: str, answer_text: str,
    memory_recalled: bool, tool_names: list[str],
) -> dict[str, str]:
    """Count proven actions; absence of proof stays unconfirmed."""
    due = opportunities(user_message)
    answer = str(answer_text or "")
    outcomes: dict[str, str] = {}
    if "quote" in due:
        outcomes["quote"] = (
            "kept" if _citat_traef([_correction_excerpt(user_message)], [answer[:1200]])
            else "unconfirmed"
        )
    if "admit" in due:
        outcomes["admit"] = (
            "kept" if _looks_like_acknowledgement(answer[:400]) else "unconfirmed"
        )
    if "memory" in due:
        used_tool = any(str(name or "").lower() in _MEMORY_TOOLS for name in tool_names)
        outcomes["memory"] = "kept" if memory_recalled or used_tool else "unconfirmed"
    return outcomes


def _ensure_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS decision_action_opportunities (
            run_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            created_at TEXT NOT NULL,
            outcome TEXT NOT NULL DEFAULT 'pending',
            memory_recalled INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (run_id, kind)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_decision_action_created "
        "ON decision_action_opportunities (created_at)"
    )


def record_opportunities(run_id: str, user_message: str, *, memory_recalled: bool) -> None:
    """Persist each actual trigger once, without storing conversation text."""
    if not run_id:
        return
    due = opportunities(user_message)
    if not due:
        return
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_table(conn)
        for kind in due:
            conn.execute(
                "INSERT OR IGNORE INTO decision_action_opportunities "
                "(run_id, kind, created_at, memory_recalled) VALUES (?, ?, ?, ?)",
                (run_id, kind, now, int(kind == "memory" and memory_recalled)),
            )
            if kind == "memory" and memory_recalled:
                conn.execute(
                    "UPDATE decision_action_opportunities SET memory_recalled = 1 "
                    "WHERE run_id = ? AND kind = 'memory'",
                    (run_id,),
                )
        conn.commit()


def record_outcomes(
    run_id: str, user_message: str, answer_text: str, *, tool_names: list[str],
) -> None:
    """Finalize observations at the persisted assistant message boundary."""
    if not run_id:
        return
    record_opportunities(run_id, user_message, memory_recalled=False)
    with connect() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT memory_recalled FROM decision_action_opportunities "
            "WHERE run_id = ? AND kind = 'memory'",
            (run_id,),
        ).fetchone()
        outcomes = evaluate_turn(
            user_message=user_message,
            answer_text=answer_text,
            memory_recalled=bool(row["memory_recalled"]) if row else False,
            tool_names=tool_names,
        )
        for kind, outcome in outcomes.items():
            conn.execute(
                "UPDATE decision_action_opportunities SET outcome = ? "
                "WHERE run_id = ? AND kind = ? AND outcome = 'pending'",
                (outcome, run_id, kind),
            )
        conn.commit()


def opportunity_summary(*, days: int = 7) -> dict[str, dict[str, int]]:
    """Observed kept / all triggered opportunities, with uncertainty explicit."""
    cutoff = (datetime.now(UTC) - timedelta(days=max(1, days))).isoformat()
    result = {}
    with connect() as conn:
        try:
            rows = conn.execute(
                "SELECT kind, outcome, COUNT(*) AS n FROM decision_action_opportunities "
                "WHERE created_at >= ? GROUP BY kind, outcome",
                (cutoff,),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc).lower():
                return {}
            raise
    for row in rows:
        kind = str(row["kind"])
        entry = result.setdefault(kind, {"opportunities": 0, "kept": 0, "unconfirmed": 0, "pending": 0})
        n = int(row["n"])
        entry["opportunities"] += n
        if row["outcome"] == "kept":
            entry["kept"] += n
        elif row["outcome"] == "unconfirmed":
            entry["unconfirmed"] += n
        else:
            entry["pending"] += n
    return result
