"""Kerne-kurator — holder USER.md `## Kerne` kort og levende (blok A, 2026-09-04).

`## Kerne` er den eneste del af USER.md der ALTID er i prompten. Den må derfor
ikke vokse: hver linje koster plads i det stabile præfiks på hver eneste tur.
`## Lært` er derimod ubegrænset og relevans-udvalgt pr. tur.

Kuratoren kører højst en gang om ugen og stiller ÉT forslag ad gangen i den
proaktive kø (leveres af `proactivity_bridge`, ikke af en brønd ingen tømmer):

* **Op:** en Lært-linje der er blevet valgt ind mindst `_PROMOTE_AT_SELECTIONS`
  gange er ikke længere situationsbestemt — den hører til i Kerne.
* **Ned:** når Kerne er over `KERNE_MAX_LINES` foreslås de ældste linjer flyttet
  ned i Lært igen. Intet slettes nogensinde; en linje flyttes kun mellem to
  sektioner i samme fil.

`promote_to_kerne` / `demote_from_kerne` udfører selve flytningen, så et svar
("ja, flyt den op") kan gøre det uden håndredigering.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

KERNE_MAX_LINES = 25
_PROMOTE_AT_SELECTIONS = 3
_LAST_RUN_KEY = "kerne_curator_last_run"
_MIN_INTERVAL_DAYS = 7


def _should_run(last_run_iso: object, now: datetime) -> bool:
    if not last_run_iso:
        return True
    try:
        last = datetime.fromisoformat(str(last_run_iso))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
    except Exception:
        return True
    return (now - last) >= timedelta(days=_MIN_INTERVAL_DAYS)


def _workspace_dir() -> Path:
    from core.memory.workspace import ensure_default_workspace
    return Path(ensure_default_workspace())


def promotion_candidates(workspace_dir: Path) -> list[dict[str, object]]:
    """Lært-linjer der er brugt tit nok til at høre hjemme i Kerne."""
    from core.services.prompt_sections.learned_about_user import (
        core_lines, learned_lines, selection_counts,
    )
    counts = selection_counts()
    core = " ".join(core_lines(workspace_dir)).lower()
    out: list[dict[str, object]] = []
    for row in learned_lines(workspace_dir):
        text = row["text"]
        used = int(counts.get(text.lower()[:120], 0))
        if used < _PROMOTE_AT_SELECTIONS:
            continue
        if text.lower()[:60] in core:
            continue
        out.append({"text": text, "used": used, "date": row.get("date", "")})
    out.sort(key=lambda r: -int(r["used"]))
    return out


def demotion_candidates(workspace_dir: Path) -> list[str]:
    """De ældste Kerne-linjer der ligger ud over loftet (tomt når under)."""
    from core.services.prompt_sections.learned_about_user import core_lines
    lines = [line for line in core_lines(workspace_dir) if len(line.strip()) >= 8]
    if len(lines) <= KERNE_MAX_LINES:
        return []
    return lines[: len(lines) - KERNE_MAX_LINES]


def _move_line(*, text: str, to_core: bool) -> dict[str, object]:
    """Flyt én linje mellem `## Kerne` og `## Lært` i USER.md. Atomisk."""
    from core.services.prompt_sections.learned_about_user import (
        CORE_HEADINGS, LEARNED_HEADINGS, section_body,
    )
    workspace_dir = _workspace_dir()
    path = workspace_dir / "USER.md"
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    if not raw:
        return {"moved": False, "reason": "no-user-md"}
    needle = " ".join(str(text or "").split()).strip().lstrip("-*").strip()
    if not needle:
        return {"moved": False, "reason": "empty"}

    src_headings = LEARNED_HEADINGS if to_core else CORE_HEADINGS
    dst_heading = "Kerne" if to_core else "Lært"
    src_body = section_body(raw, src_headings)
    match = ""
    for line in src_body.splitlines():
        if needle.lower()[:60] in " ".join(line.split()).lower():
            match = line
            break
    if not match:
        return {"moved": False, "reason": "not-found-in-source"}

    remaining = "\n".join(line for line in raw.splitlines() if line != match)
    from core.memory.memory_md_writer import upsert_section
    path.write_text(remaining if remaining.endswith("\n") else remaining + "\n", encoding="utf-8")
    upsert_section(path, dst_heading, " ".join(match.split()).strip(), mode="append")
    return {"moved": True, "line": " ".join(match.split()).strip(), "to": f"## {dst_heading}"}


def promote_to_kerne(text: str) -> dict[str, object]:
    """Flyt en Lært-linje op i Kerne (altid i prompten)."""
    return _move_line(text=text, to_core=True)


def demote_from_kerne(text: str) -> dict[str, object]:
    """Flyt en Kerne-linje ned i Lært (kun når den er relevant)."""
    return _move_line(text=text, to_core=False)


def build_proposal_text(workspace_dir: Path) -> str:
    """Ugens ÉNE forslag — "" når Kerne er sund og intet er modnet."""
    promote = promotion_candidates(workspace_dir)
    if promote:
        top = promote[0]
        return (
            f"Kerne-kurator: «{top['text']}» er blevet hentet frem "
            f"{top['used']} gange fra det jeg har lært om dig. "
            "Den er ikke situationsbestemt længere — skal den op i Kerne, "
            "så den altid er med?"
        )
    demote = demotion_candidates(workspace_dir)
    if demote:
        from core.services.prompt_sections.learned_about_user import core_lines
        count = len(core_lines(workspace_dir))
        oldest = "; ".join(line.lstrip("-*").strip()[:70] for line in demote[:3])
        return (
            f"Kerne-kurator: Kerne er på {count} linjer (loft {KERNE_MAX_LINES}) — "
            f"den fylder på hver eneste tur. De ældste er: {oldest}. "
            "Skal jeg flytte dem ned i Lært, hvor de kun hentes når de er relevante?"
        )
    return ""


def run_kerne_curator(*, force: bool = False, now: datetime | None = None) -> dict[str, object]:
    """Ugentlig kuratering. Self-throttlende og self-safe — kaster aldrig."""
    now = now or datetime.now(UTC)
    try:
        from core.runtime.db import get_runtime_state_value, set_runtime_state_value
    except Exception:
        return {"ran": False, "reason": "no-state-store"}
    if not force and not _should_run(get_runtime_state_value(_LAST_RUN_KEY, None), now):
        return {"ran": False, "reason": "cadence"}
    try:
        workspace_dir = _workspace_dir()
        text = build_proposal_text(workspace_dir)
    except Exception as exc:
        logger.debug("kerne_curator: build failed: %s", exc)
        text = ""
    result: dict[str, object] = {"ran": True, "proposed": bool(text)}
    if text:
        try:
            from core.services.proactive_candidates import add_candidate
            res = add_candidate(
                source="kerne_curator", kind="kerne_curation",
                text=text, priority="low",
            )
            result["candidate"] = res
        except Exception as exc:
            logger.debug("kerne_curator: add_candidate failed: %s", exc)
    try:
        set_runtime_state_value(_LAST_RUN_KEY, now.isoformat())
    except Exception:
        pass
    logger.info("kerne-curator: %s", result)
    return result
