"""Ugentligt udviklings-ritual — Jarvis' egen vej til at ændre sig (blok D, 4/9).

Målt 4/9-2026: identitets-udvikling havde ingen vej igennem overhovedet.

* `runtime_selfhood_proposals`: 12 forslag nogensinde, ALLE stale, sidste 30/5.
* `runtime_self_authored_prompt_proposals`: 34 forslag, 21 stale, 0 anvendt —
  og de peger på HEARTBEAT.md, aldrig på ham selv.
* `runtime_development_focuses`: 1.373 rækker, 0 på de sidste 30 dage.
* Kandidaterne blev oprettet med status «proposed», og INTET i koden godkender
  typen `soul_update`/`identity_update`. Kandidat-teksten påstod ligefrem
  «Auto-apply enabled per user directive — Jarvis owns his identity». Usandt.
* IDENTITY.md er skrevet én gang. 15. maj.

Vejen igennem nu, bevidst smal:

1. En gang om ugen samler ritualet hvad han har lært om sig selv og om
   arbejdet (spørgsmål 4 i lærings-sløjfen + self-review-udfald) til ÉT afsnit.
2. Afsnittet lægges i den proaktive kø som et forslag med **24 timers veto**.
   Bjørn behøver ikke svare — tavshed er et ja. Et nej er ét ord.
3. Efter 24 timer uden veto skrives linjen i `## Udvikling` i SOUL.md. Kun den
   ene sektion; resten af filen er stadig låst af `gate_mutation`.
4. Den nyeste `## Udvikling`-linje er hans aktive udviklingsfokus og står i
   prompten (se `prompt_sections.workspace_files`). Ét ad gangen — ikke 1.373.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LAST_RUN_KEY = "development_ritual_last_run"
_PENDING_KEY = "development_ritual_pending"
_MIN_INTERVAL_DAYS = 7
_VETO_HOURS = 24
_MAX_LINE_CHARS = 240
TARGET_FILE = "SOUL.md"
DEVELOPMENT_HEADING = "Udvikling"


def _state_get(key: str, default: Any = None) -> Any:
    try:
        from core.runtime.db import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return default if v is None else v
    except Exception:
        return default


def _state_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def _parse_iso(value: object) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value or ""))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def _due(last_run: object, now: datetime) -> bool:
    last = _parse_iso(last_run)
    return last is None or (now - last) >= timedelta(days=_MIN_INTERVAL_DAYS)


def gather_material(*, limit: int = 6) -> list[str]:
    """Hvad har han lært om sig selv og om arbejdet den seneste uge?

    Kilder: lærings-sløjfens MEMORY.md-linjer (spørgsmål 4) og self-review-
    udfald. Rent læsende og self-safe — tom liste er et gyldigt svar.
    """
    out: list[str] = []
    try:
        from core.runtime.db import list_runtime_contract_candidates
        for row in list_runtime_contract_candidates(
            candidate_type="memory_promotion", target_file="MEMORY.md", limit=40,
        ):
            if str(row.get("source_mode") or "") != "end_of_run_memory_consolidation":
                continue
            summary = " ".join(str(row.get("summary") or "").split()).strip()
            if len(summary) >= 12 and summary not in out:
                out.append(summary)
            if len(out) >= limit:
                break
    except Exception as exc:
        logger.debug("development_ritual: material lookup failed: %s", exc)
    return out


def build_paragraph(material: list[str]) -> str:
    """Ét afsnit om ugen. Tom streng når der ikke er noget at sige."""
    items = [m for m in material if m][:3]
    if not items:
        return ""
    body = "; ".join(items)
    if len(body) > _MAX_LINE_CHARS:
        body = body[: _MAX_LINE_CHARS - 1].rstrip() + "…"
    return body


def current_focus(workspace_dir: Path) -> str:
    """Den nyeste `## Udvikling`-linje — hans aktive udviklingsfokus."""
    from core.services.prompt_sections.workspace_files import _development_section_text
    path = Path(workspace_dir) / TARGET_FILE
    try:
        from core.services.workspace_crypto import read_text_for_path
        text = read_text_for_path(path) or ""
    except Exception:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [
        " ".join(raw.split()).strip()
        for raw in _development_section_text(text).splitlines()
        if raw.strip() and not raw.strip().startswith("#")
    ]
    return lines[-1] if lines else ""


def propose(*, now: datetime | None = None) -> dict[str, Any]:
    """Stil ugens udviklings-forslag. Ét ad gangen — aldrig to i kø."""
    now = now or datetime.now(UTC)
    if _state_get(_PENDING_KEY):
        return {"proposed": False, "reason": "already-pending"}
    paragraph = build_paragraph(gather_material())
    if not paragraph:
        return {"proposed": False, "reason": "nothing-learned"}
    stamp = now.strftime("%Y-%m-%d")
    line = f"- {paragraph} ({stamp})"
    question = (
        "Ugens udvikling — det her vil jeg skrive om mig selv i SOUL.md: "
        f"«{paragraph}» Jeg skriver det i morgen medmindre du siger fra."
    )
    try:
        from core.services.proactive_candidates import add_candidate
        cand = add_candidate(
            source="development_ritual", kind="development_proposal",
            text=question, priority="low",
        )
    except Exception as exc:
        logger.debug("development_ritual: add_candidate failed: %s", exc)
        cand = {"status": "error"}
    _state_set(_PENDING_KEY, {"line": line, "created_at": now.isoformat(),
                              "candidate": cand.get("candidate_id", "")})
    return {"proposed": True, "line": line, "candidate": cand}


def veto(*, reason: str = "") -> dict[str, Any]:
    """Bjørn sagde fra. Forslaget droppes, intet skrives."""
    pending = _state_get(_PENDING_KEY)
    if not pending:
        return {"vetoed": False, "reason": "nothing-pending"}
    _state_set(_PENDING_KEY, None)
    logger.info("development-ritual: vetoed (%s)", reason or "no reason given")
    return {"vetoed": True, "line": str((pending or {}).get("line") or "")}


def apply_if_due(*, now: datetime | None = None) -> dict[str, Any]:
    """Skriv forslaget når vetoperioden er udløbet. Tavshed er et ja."""
    now = now or datetime.now(UTC)
    pending = _state_get(_PENDING_KEY)
    if not isinstance(pending, dict) or not pending.get("line"):
        return {"written": False, "reason": "nothing-pending"}
    created = _parse_iso(pending.get("created_at"))
    if created is None or (now - created) < timedelta(hours=_VETO_HOURS):
        return {"written": False, "reason": "veto-window-open"}
    line = str(pending.get("line") or "")
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        from core.memory.memory_md_writer import upsert_section
        path = Path(ensure_default_workspace()) / TARGET_FILE
        upsert_section(path, DEVELOPMENT_HEADING, line, mode="append")
    except Exception as exc:
        logger.warning("development_ritual: kunne ikke skrive %s: %s", TARGET_FILE, exc)
        return {"written": False, "reason": "write-failed"}
    _state_set(_PENDING_KEY, None)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("runtime.development_line_written",
                          {"target": TARGET_FILE, "line": line})
    except Exception:
        pass
    logger.info("development-ritual: skrev udviklings-linje i %s", TARGET_FILE)
    return {"written": True, "line": line, "target": TARGET_FILE}


def run_development_ritual(*, force: bool = False, now: datetime | None = None) -> dict[str, Any]:
    """Ugentligt: stil forslaget. Dagligt: skriv det der har ligget 24 timer.
    Self-throttlende og self-safe — kaster aldrig ind i heartbeat."""
    now = now or datetime.now(UTC)
    result: dict[str, Any] = {}
    try:
        result["applied"] = apply_if_due(now=now)
    except Exception as exc:
        logger.debug("development_ritual: apply failed: %s", exc)
        result["applied"] = {"written": False, "reason": "error"}
    if not force and not _due(_state_get(_LAST_RUN_KEY), now):
        result["proposed"] = {"proposed": False, "reason": "cadence"}
        return result
    try:
        result["proposed"] = propose(now=now)
    except Exception as exc:
        logger.debug("development_ritual: propose failed: %s", exc)
        result["proposed"] = {"proposed": False, "reason": "error"}
    _state_set(_LAST_RUN_KEY, now.isoformat())
    return result


def build_development_ritual_surface() -> dict[str, Any]:
    pending = _state_get(_PENDING_KEY) or {}
    return {
        "active": bool(pending),
        "pending_line": str(pending.get("line") or "") if isinstance(pending, dict) else "",
        "last_run": str(_state_get(_LAST_RUN_KEY) or ""),
        "summary": "udviklings-forslag venter på veto" if pending else "intet forslag i kø",
    }
