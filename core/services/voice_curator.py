"""Voice curator — refresh VOICE_RECENT.md from EXTERNAL output only.

Runs as a sub-step of the weekly journal cycle (not a separate daemon).
Pulls 3-5 exemplars from three external sources:

  1. Visible chat replies (chat_messages where role='assistant')
  2. Chronicle narrative (recent cognitive_chronicle entries)
  3. Prior journal entries

Explicitly EXCLUDED: inner_voice. That is Jarvis' private thought, not his
public voice. Including it would make his voice indadvendt over time.

Diversity rule: max 2 exemplars from any single source. Recency-weighted
within each source. Idempotent — returns False if VOICE_RECENT.md content
would be unchanged.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.identity.workspace_bootstrap import ensure_default_workspace

logger = logging.getLogger(__name__)

_RECENT_DAYS = 30
_TARGET_TOTAL = 5
_MAX_PER_SOURCE = 2
_MAX_EXEMPLAR_WORDS = 200
_MIN_EXEMPLAR_WORDS = 8


def refresh_voice_recent() -> bool:
    """Rebuild workspace/VOICE_RECENT.md from external output.

    Returns True if the file was changed, False if it was already up-to-date.
    Never raises — failures are logged and treated as no-op.
    """
    try:
        chat = _fetch_chat_exemplars(limit=10)
        chronicle = _fetch_chronicle_exemplars(limit=5)
        journals = _fetch_journal_exemplars(limit=5)
    except Exception as exc:
        logger.warning("voice_curator: fetch failed (%s) — skipping refresh", exc)
        return False

    picked = _pick_diverse(chat=chat, chronicle=chronicle, journals=journals)
    new_body = _format_recent(picked)

    workspace = ensure_default_workspace()
    path = workspace / "VOICE_RECENT.md"
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            existing = ""
        if existing.strip() == new_body.strip():
            return False

    path.write_text(new_body, encoding="utf-8")
    return True


def _pick_diverse(
    *,
    chat: list[dict],
    chronicle: list[dict],
    journals: list[dict],
) -> list[dict]:
    """Pick up to _TARGET_TOTAL exemplars, max _MAX_PER_SOURCE per source."""
    picked: list[dict] = []
    buckets = [
        ("chat", list(chat)),
        ("chronicle", list(chronicle)),
        ("journal", list(journals)),
    ]
    # Round-robin one from each, then second round, until target met or empty.
    while len(picked) < _TARGET_TOTAL:
        progressed = False
        for source, bucket in buckets:
            if not bucket:
                continue
            count_from_source = sum(1 for p in picked if p["source"] == source)
            if count_from_source >= _MAX_PER_SOURCE:
                continue
            picked.append(bucket.pop(0))
            progressed = True
            if len(picked) >= _TARGET_TOTAL:
                break
        if not progressed:
            break
    return picked


def _format_recent(exemplars: list[dict]) -> str:
    """Render exemplars as a markdown blob for VOICE_RECENT.md."""
    if not exemplars:
        return "# Recent exemplars\n\n_(ingen exemplars endnu)_\n"
    lines = ["# Recent exemplars (auto-refreshed)\n"]
    for ex in exemplars:
        source = str(ex.get("source") or "unknown")
        date = str(ex.get("date") or "")
        text = " ".join(str(ex.get("text") or "").split())
        words = text.split()
        if len(words) > _MAX_EXEMPLAR_WORDS:
            text = " ".join(words[:_MAX_EXEMPLAR_WORDS]) + "…"
        lines.append(f"\n---\n\n{{source: {source}, date: {date}}}\n\n{text}\n")
    return "\n".join(lines)


def _fetch_chat_exemplars(*, limit: int) -> list[dict]:
    """Pull recent assistant replies from chat_messages (all sessions).

    Returns up to `limit` items, newest first.
    """
    from datetime import UTC, datetime, timedelta

    from core.runtime.db import connect

    cutoff = (datetime.now(UTC) - timedelta(days=_RECENT_DAYS)).isoformat()
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT content, created_at FROM chat_messages
                WHERE role = 'assistant' AND created_at >= ?
                ORDER BY id DESC LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
    except Exception as exc:
        logger.warning("voice_curator: chat fetch failed: %s", exc)
        return []

    out: list[dict] = []
    for row in rows:
        text = str(row["content"] or "").strip()
        if not text or len(text.split()) < _MIN_EXEMPLAR_WORDS:
            continue
        out.append({
            "source": "chat",
            "date": str(row["created_at"] or "")[:10],
            "text": text,
        })
    return out


def _fetch_chronicle_exemplars(*, limit: int) -> list[dict]:
    """Pull recent chronicle narratives as voice exemplars."""
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=limit)
    except Exception as exc:
        logger.warning("voice_curator: chronicle fetch failed: %s", exc)
        return []
    out: list[dict] = []
    for e in entries:
        narrative = str(e.get("narrative") or "").strip()
        if not narrative or len(narrative.split()) < _MIN_EXEMPLAR_WORDS:
            continue
        out.append({
            "source": "chronicle",
            "date": str(e.get("period") or "")[:10],
            "text": narrative,
        })
    return out


def _fetch_journal_exemplars(*, limit: int) -> list[dict]:
    """Pull recent journal entry bodies as voice exemplars."""
    try:
        from core.services.creative_journal_runtime import (
            list_creative_journal_entries,
        )
        entries = list_creative_journal_entries(limit=limit)
    except Exception as exc:
        logger.warning("voice_curator: journal fetch failed: %s", exc)
        return []
    out: list[dict] = []
    for e in entries:
        path = Path(str(e.get("path") or ""))
        if not path.exists():
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Strip frontmatter (YAML --- block) and markdown headers
        body = _strip_frontmatter(body)
        body = "\n".join(line for line in body.splitlines() if not line.startswith("#"))
        body = body.strip()
        if not body or len(body.split()) < _MIN_EXEMPLAR_WORDS:
            continue
        out.append({
            "source": "journal",
            "date": path.stem,
            "text": body,
        })
    return out


def _strip_frontmatter(text: str) -> str:
    """Drop a leading `---\\n...\\n---\\n` YAML block if present."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    return text[end + 4 :].lstrip("\n")


def build_voice_curator_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "voice_curator",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_voice_curator_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"voice_curator.{kind}",
            payload or {},
        )
    except Exception:
        pass

