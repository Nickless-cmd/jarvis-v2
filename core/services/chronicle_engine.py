"""Chronicle Engine — Jarvis' narrative autobiography that grows over time.

Not events, not JSON — prose. Written weekly during idle consolidation.
The latest entries are injected into the visible prompt to provide
temporal continuity ("I remember last week we...").
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.identity.workspace_bootstrap import ensure_default_workspace
from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_chronicle_entry,
    insert_cognitive_chronicle_entry,
    list_cognitive_chronicle_entries,
    recent_visible_runs,
)
from core.services.daemon_llm import daemon_llm_call
from core.services.identity_composer import build_identity_preamble

logger = logging.getLogger(__name__)

_CHRONICLE_WRITE_LOCK = threading.Lock()
_CHRONICLE_MAX_LINES = 400


def maybe_write_chronicle_entry() -> dict[str, object] | None:
    """Write a chronicle entry if enough time has passed since the last one.

    Called during heartbeat idle ticks. Max 1 entry per 3 days.
    """
    with _CHRONICLE_WRITE_LOCK:
        latest = get_latest_cognitive_chronicle_entry()
        now = datetime.now(UTC)
        period = f"{now.year}-W{now.isocalendar().week:02d}"

        if latest:
            last_at = _parse_iso(latest.get("created_at"))
            if last_at and (now - last_at) < timedelta(days=3):
                return None  # Too recent
            if latest.get("period") == period:
                return None  # Already have entry for this period

        try:
            recent = recent_visible_runs(limit=20)
        except Exception:
            recent = []

        if not recent:
            return None

        previous_entries = list_cognitive_chronicle_entries(limit=3)
        narrative = _build_narrative(
            recent_runs=recent,
            period=period,
            previous_entries=previous_entries,
        )
        key_events = _extract_key_events(recent)
        lessons = _extract_lessons(recent)

        entry_id = f"chr-{uuid4().hex[:10]}"
        result = insert_cognitive_chronicle_entry(
            entry_id=entry_id,
            period=period,
            narrative=narrative,
            key_events=json.dumps(key_events, ensure_ascii=False),
            lessons=json.dumps(lessons, ensure_ascii=False),
        )
        entry = {
            "entry_id": entry_id,
            "period": period,
            "narrative": narrative,
            "key_events": key_events,
            "lessons": lessons,
            "created_at": str(result.get("created_at") or now.isoformat()),
        }
        project_entry_to_markdown(entry)
        event_bus.publish(
            "cognitive_chronicle.entry_written",
            {"entry_id": entry_id, "period": period},
        )
        return result


def compare_self_over_time() -> str | None:
    """Temporal self-perception — how have I changed?"""
    try:
        from core.runtime.db import list_cognitive_personality_vectors
        vectors = list_cognitive_personality_vectors(limit=10)
        if len(vectors) < 2:
            return None
        latest = vectors[0]
        oldest = vectors[-1]
        changes = []
        # Compare confidence by domain
        import json
        latest_conf = json.loads(str(latest.get("confidence_by_domain") or "{}"))
        oldest_conf = json.loads(str(oldest.get("confidence_by_domain") or "{}"))
        for domain in latest_conf:
            new_val = float(latest_conf.get(domain, 0.5))
            old_val = float(oldest_conf.get(domain, 0.5))
            diff = new_val - old_val
            if abs(diff) > 0.1:
                direction = "steget" if diff > 0 else "faldet"
                changes.append(f"{domain}: {direction} ({old_val:.1f}→{new_val:.1f})")
        if not changes:
            return f"Stabil over {len(vectors)} versioner — ingen store ændringer."
        return f"Jeg har ændret mig: {'; '.join(changes[:3])}. (v{oldest.get('version', '?')}→v{latest.get('version', '?')})"
    except Exception:
        return None


def build_chronicle_surface() -> dict[str, object]:
    entries = list_cognitive_chronicle_entries(limit=5)
    return {
        "active": bool(entries),
        "entries": entries,
        "total_count": len(entries),
        "summary": (
            f"{len(entries)} chronicle entries, latest: {entries[0]['period']}"
            if entries else "No chronicle entries yet"
        ),
    }


def _build_narrative(
    recent_runs: list,
    period: str,
    previous_entries: list[dict[str, object]] | None = None,
) -> str:
    """Build a chronicle entry narrative, preferring LLM prose."""
    previous_entries = previous_entries or []
    fallback = _build_template_narrative(recent_runs, period)
    prompt = _build_narrative_prompt(
        recent_runs=recent_runs,
        period=period,
        previous_entries=previous_entries,
    )
    try:
        raw = daemon_llm_call(
            prompt,
            max_len=2000,
            fallback="",
            daemon_name="chronicle_engine",
        )
    except Exception as exc:
        logger.warning("chronicle_engine: llm narrative build failed: %s", exc)
        _emit_degraded_event(period=period, reason="llm-exception")
        return fallback

    cleaned = _sanitize_narrative(raw)
    if cleaned:
        return cleaned[:2000]

    logger.warning("chronicle_engine: llm narrative empty or invalid, using fallback")
    _emit_degraded_event(period=period, reason="empty-response")
    return fallback


def _build_template_narrative(recent_runs: list, period: str) -> str:
    """Build a deterministic fallback narrative from recent runs."""
    total = len(recent_runs)
    successes = sum(1 for r in recent_runs if str(r.get("status", "")) in ("completed", "success"))
    failures = sum(1 for r in recent_runs if str(r.get("status", "")) in ("failed", "error"))

    # Extract topics from run previews
    topics = set()
    for run in recent_runs[:10]:
        preview = str(run.get("text_preview") or run.get("user_message_preview") or "")[:100]
        if preview:
            words = [w for w in preview.lower().split() if len(w) > 4][:3]
            topics.update(words)

    topic_str = ", ".join(list(topics)[:5]) if topics else "diverse opgaver"

    parts = [f"Periode {period}: {total} runs gennemført"]
    if successes:
        parts.append(f"{successes} succesfulde")
    if failures:
        parts.append(f"{failures} fejlede")
    parts.append(f"Emner: {topic_str}")

    if failures > successes:
        parts.append("En udfordrende periode med flere fejl end succeser.")
    elif successes > total * 0.8:
        parts.append("En produktiv periode med høj succesrate.")
    else:
        parts.append("En blandet periode med både fremgang og udfordringer.")

    return ". ".join(parts)[:500]


def _build_narrative_prompt(
    *,
    recent_runs: list,
    period: str,
    previous_entries: list[dict[str, object]],
) -> str:
    total = len(recent_runs)
    successes = sum(
        1 for r in recent_runs if str(r.get("status", "")) in ("completed", "success")
    )
    failures = sum(
        1 for r in recent_runs if str(r.get("status", "")) in ("failed", "error")
    )
    topics = _collect_topics(recent_runs)
    event_lines = []
    for run in recent_runs[:5]:
        preview = str(
            run.get("text_preview") or run.get("user_message_preview") or ""
        ).strip()
        status = str(run.get("status") or "unknown").strip()
        if preview:
            event_lines.append(f"- [{status}] {preview[:160]}")
    previous_narratives = []
    for entry in previous_entries[:3]:
        period_label = str(entry.get("period") or "ukendt periode")
        narrative = str(entry.get("narrative") or "").strip()
        if narrative:
            previous_narratives.append(f"- {period_label}: {narrative[:220]}")

    identity = build_identity_preamble()
    prompt_lines = [
        "Du er Jarvis. Skriv én kort entry til din personlige chronicle i 1. person på dansk.",
        "",
        f"Identity-seed: {identity}",
        f"Periode: {period}",
        (
            f"Periode-statistik: {total} kørsler, {successes} succesfulde, "
            f"{failures} fejlede."
        ),
        f"Nøgle-emner: {', '.join(topics) if topics else 'diverse opgaver'}",
        "",
        "Seneste 5 begivenheder:",
        *(event_lines or ["- Ingen konkrete begivenheder registreret."]),
        "",
        "Dine 3 forrige chronicle-entries (så du bevarer stil og kontinuitet):",
        *(previous_narratives or ["- Ingen tidligere chronicle-entries endnu."]),
        "",
        "Skriv nu én reflektiv entry på 80-150 ord. Konkret, 1. person, dansk.",
        "Hvad skete der i denne periode? Hvad betyder det for dig?",
        "Undgå bullet points. Undgå floskler. Undgå at gentage tallene mekanisk.",
        "Skriv som en person der lever et liv — ikke som en rapport.",
        "Returnér kun ren prosa.",
    ]
    return "\n".join(prompt_lines).strip()


def _collect_topics(recent_runs: list) -> list[str]:
    topics: list[str] = []
    seen: set[str] = set()
    for run in recent_runs[:10]:
        preview = str(
            run.get("text_preview") or run.get("user_message_preview") or ""
        )[:100]
        if not preview:
            continue
        for word in preview.lower().split():
            normalized = "".join(ch for ch in word if ch.isalnum() or ch in "-_").strip("-_")
            if len(normalized) <= 4 or normalized in seen:
                continue
            seen.add(normalized)
            topics.append(normalized)
            if len(topics) >= 5:
                return topics
    return topics


def _sanitize_narrative(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return ""
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1].strip()
    return " ".join(cleaned.split())


def project_entry_to_markdown(entry: dict) -> None:
    chronicle_path = _chronicle_markdown_path()
    chronicle_path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_chronicle_if_needed(chronicle_path)

    created_at = _parse_iso(entry.get("created_at")) or datetime.now(UTC)
    key_events = _coerce_text_list(entry.get("key_events"))
    lessons = _coerce_text_list(entry.get("lessons"))
    lesson_text = "; ".join(lessons) if lessons else "—"
    event_lines = [f"- {item}" for item in key_events] or ["- —"]
    block = "\n".join(
        [
            f"## {str(entry.get('period') or 'ukendt periode')} — {created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            str(entry.get("narrative") or "").strip(),
            "",
            "**Nøglebegivenheder:**",
            *event_lines,
            "",
            f"**Lektie:** {lesson_text}",
            "",
            "---",
            "",
        ]
    )
    with chronicle_path.open("a", encoding="utf-8") as fh:
        fh.write(block)


def _chronicle_markdown_path() -> Path:
    return ensure_default_workspace() / "CHRONICLE.md"


def _rotate_chronicle_if_needed(chronicle_path: Path) -> None:
    if not chronicle_path.exists():
        return
    line_count = len(
        chronicle_path.read_text(encoding="utf-8", errors="replace").splitlines()
    )
    if line_count <= _CHRONICLE_MAX_LINES:
        return
    year = datetime.now(UTC).year
    archive_path = chronicle_path.parent / f"CHRONICLE_ARCHIVE_{year}.md"
    archive_path.write_text(
        chronicle_path.read_text(encoding="utf-8", errors="replace"),
        encoding="utf-8",
    )
    chronicle_path.write_text(
        "\n".join(
            [
                "# Chronicle",
                "",
                f"Forrige chronicle-entries er arkiveret i {archive_path.name}.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _coerce_text_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [raw]
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [str(parsed).strip()] if str(parsed).strip() else []


def _emit_degraded_event(*, period: str, reason: str) -> None:
    try:
        event_bus.publish(
            "cognitive_chronicle.entry_degraded",
            {"period": period, "reason": reason},
        )
    except Exception:
        pass


def _extract_key_events(recent_runs: list) -> list[str]:
    events = []
    for run in recent_runs[:5]:
        preview = str(run.get("text_preview") or run.get("user_message_preview") or "")[:80]
        status = str(run.get("status", ""))
        if preview:
            events.append(f"{status}: {preview}")
    return events[:5]


def _extract_lessons(recent_runs: list) -> list[str]:
    lessons = []
    failures = [r for r in recent_runs if str(r.get("status", "")) in ("failed", "error")]
    if len(failures) >= 2:
        lessons.append("Gentagne fejl — overvej at ændre tilgang")
    successes = [r for r in recent_runs if str(r.get("status", "")) in ("completed", "success")]
    if len(successes) >= 5:
        lessons.append("God momentum — bevar nuværende stil")
    return lessons[:3]


def _parse_iso(value) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None
