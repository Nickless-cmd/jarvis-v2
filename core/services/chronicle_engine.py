"""Chronicle Engine — Jarvis' narrative autobiography that grows over time.

Not events, not JSON — prose. Written weekly during idle consolidation.
The latest entries are injected into the visible prompt to provide
temporal continuity ("I remember last week we...").
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
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
from core.services.text_clip import clip_text

logger = logging.getLogger(__name__)

_CHRONICLE_WRITE_LOCK = threading.Lock()
_CHRONICLE_MAX_LINES = 400


@dataclass
class ChronicleAppraisal:
    """Structured chronicle context — replaces hardcoded narrative prompts.

    Text is rendered ON TOP of this appraisal, not the other way around.
    """
    period: str
    total_runs: int
    successes: int
    failures: int
    topics: list[str]
    recent_events: list[dict[str, str]]  # [{status, preview}, ...]
    previous_narratives: list[str]
    evidence: list[str]
    confidence: float
    expires_at: datetime
    allowed_effects: list[str] = field(default_factory=lambda: [
        "narrative-writing",
        "prompt-injection",
    ])


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

        # Capture affective signature for emotion continuity
        affective_signature = ""
        try:
            from core.services.emotion_tagging import current_emotion_tag, format_emotion_tag
            tag = current_emotion_tag()
            affective_signature = format_emotion_tag(tag)
        except Exception:
            pass

        entry_id = f"chr-{uuid4().hex[:10]}"
        result = insert_cognitive_chronicle_entry(
            entry_id=entry_id,
            period=period,
            narrative=narrative,
            key_events=json.dumps(key_events, ensure_ascii=False),
            lessons=json.dumps(lessons, ensure_ascii=False),
            affective_signature=affective_signature,
        )
        entry = {
            "entry_id": entry_id,
            "period": period,
            "narrative": narrative,
            "key_events": key_events,
            "lessons": lessons,
            "affective_signature": affective_signature,
            "created_at": str(result.get("created_at") or now.isoformat()),
        }
        project_entry_to_markdown(entry)
        event_bus.publish(
            "cognitive_chronicle.entry_written",
            {"entry_id": entry_id, "period": period},
        )

        # Spaced repetition: schedule reviews for lessons this period. Each
        # lesson becomes a topic Jarvis will revisit at expanding intervals
        # (1d, 3d, 7d, 14d, 30d — the module defaults). Fire-and-forget.
        try:
            from core.services.spaced_repetition import schedule_reviews_on_completion
            for lesson in (lessons or [])[:3]:  # top 3 lessons per chronicle
                topic = str(lesson or "").strip()[:160]
                if topic:
                    schedule_reviews_on_completion(
                        topic=topic,
                        plan_id=entry_id,
                    )
        except Exception:
            pass

        # Periodic rupture/regret sweep — chronicle runs every ~3 days which
        # matches our relational accountability cadence.
        try:
            from core.services.rupture_repair import evaluate_ruptures
            evaluate_ruptures(lookback_hours=72, event_limit=300)
        except Exception:
            pass
        try:
            from core.services.regret_engine import reconcile_open_regrets
            reconcile_open_regrets()
        except Exception:
            pass
        try:
            from core.services.self_model_blind_spots import discover_blind_spots
            discover_blind_spots()
        except Exception:
            pass
        # Classified counterfactuals — scan recent events for specific what-ifs
        try:
            from core.eventbus.bus import event_bus as _ebus
            from core.services.counterfactual_engine import generate_classified_counterfactual
            for ev in _ebus.recent(limit=80):
                kind = str(ev.get("kind") or "")
                payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
                if kind and payload:
                    generate_classified_counterfactual(kind, payload)
        except Exception:
            pass
        # Weekly aesthetic note — at most one per week, signature-deduped
        try:
            from core.services.aesthetic_sense import maybe_capture_weekly_aesthetic_note
            maybe_capture_weekly_aesthetic_note()
        except Exception:
            pass
        # Dream hypothesis — try generating one surprising connection
        try:
            from core.services.dream_hypothesis_generator import generate_dream_hypothesis
            generate_dream_hypothesis()
        except Exception:
            pass
        # Unified self-review — periodic LLM-audit of Jarvis' own state
        try:
            from core.services.self_review_unified import maybe_run_self_review
            maybe_run_self_review(min_hours_between=24)
        except Exception:
            pass
        # Personal project: propose new nomination if circulating theme found,
        # og advance current active project med autonom journal-entry
        try:
            from core.services.personal_project import propose_nomination, advance_active_project
            propose_nomination()
            advance_active_project()
        except Exception:
            pass
        # Weekly paradox capture — max 1 per 7 days, signature-deduped
        try:
            from core.services.paradoxes_capture import maybe_capture_weekly_paradox
            maybe_capture_weekly_paradox()
        except Exception:
            pass
        # Weekly shorthand suggestion — max 1 new shared-language term per week
        try:
            from core.services.shared_language_extended import maybe_weekly_shorthand_suggestion
            maybe_weekly_shorthand_suggestion()
        except Exception:
            pass
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


def get_chronicle_context_for_prompt(n: int = 3, max_chars: int = 1500) -> str:
    """Return recent chronicle entries formatted for prompt injection."""
    entries = list_cognitive_chronicle_entries(limit=max(n, 1))
    if not entries:
        return ""

    header = "## Mine seneste chronicle-entries (kort hukommelse)"
    sections: list[str] = []
    for entry in entries[: max(n, 1)]:
        period = str(entry.get("period") or "ukendt periode")
        created_at = _parse_iso(entry.get("created_at"))
        age_days = (
            max((datetime.now(UTC) - created_at).days, 0)
            if created_at is not None
            else None
        )
        age_label = (
            f"{age_days} dage siden" if age_days is not None else "ukendt alder"
        )
        narrative = str(entry.get("narrative") or "").strip()
        if not narrative:
            continue
        affective_signature = str(entry.get("affective_signature") or "").strip()
        affect_line = f"\n{affective_signature}" if affective_signature else ""
        sections.append(f"### {period} ({age_label}){affect_line}\n{narrative}")

    if not sections:
        return ""

    kept = list(sections)
    text = "\n\n".join([header, *kept]).strip()
    while len(kept) > 1 and len(text) > max_chars:
        kept.pop()
        text = "\n\n".join([header, *kept]).strip()
    if len(text) > max_chars:
        text = clip_text(text, limit=max_chars)
    # Anti-drift (Spec H §2.3, SHADOW): fang konfabulerede identitets-påstande i chronicle-kontekst
    # FØR den når prompten. I shadow returneres teksten UÆNDRET — kun en observe når drift fanges. Self-safe.
    try:
        from core.services.identity_drift_guard import identity_drift_guard
        text, _ = identity_drift_guard(text, source="chronicle")
    except Exception:
        pass
    return text


def _build_appraisal(
    recent_runs: list,
    period: str,
    previous_entries: list[dict[str, object]] | None = None,
) -> ChronicleAppraisal:
    """Build a structured ChronicleAppraisal from raw run data."""
    previous_entries = previous_entries or []
    total = len(recent_runs)
    successes = sum(
        1 for r in recent_runs if str(r.get("status", "")) in ("completed", "success")
    )
    failures = sum(
        1 for r in recent_runs if str(r.get("status", "")) in ("failed", "error")
    )
    topics = _collect_topics(recent_runs)

    recent_events = []
    for run in recent_runs[:5]:
        preview = str(
            run.get("text_preview") or run.get("user_message_preview") or ""
        ).strip()
        status = str(run.get("status") or "unknown").strip()
        if preview:
            recent_events.append({"status": status, "preview": preview[:160]})

    previous_narratives = []
    for entry in previous_entries[:3]:
        period_label = str(entry.get("period") or "ukendt periode")
        narrative = str(entry.get("narrative") or "").strip()
        if narrative:
            previous_narratives.append(f"- {period_label}: {narrative[:220]}")

    evidence = [f"recent_runs: {total}", f"status_ok: {successes}", f"status_fail: {failures}"]
    if topics:
        evidence.append(f"topics: {', '.join(topics[:5])}")
    if previous_narratives:
        evidence.append(f"prior_entries: {len(previous_narratives)}")

    expires_at = datetime.now(UTC) + timedelta(days=3)

    return ChronicleAppraisal(
        period=period,
        total_runs=total,
        successes=successes,
        failures=failures,
        topics=topics,
        recent_events=recent_events,
        previous_narratives=previous_narratives,
        evidence=evidence,
        confidence=0.85 if total > 0 else 0.0,
        expires_at=expires_at,
    )


def _build_narrative(
    recent_runs: list,
    period: str,
    previous_entries: list[dict[str, object]] | None = None,
) -> str:
    """Build a chronicle entry narrative, preferring LLM prose."""
    appraisal = _build_appraisal(recent_runs, period, previous_entries)
    fallback = _render_template_narrative(appraisal)
    prompt = _render_narrative_prompt(appraisal)
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


def _render_template_narrative(appraisal: ChronicleAppraisal) -> str:
    """Render a deterministic fallback narrative from a structured appraisal."""
    topic_str = ", ".join(appraisal.topics[:5]) if appraisal.topics else "diverse opgaver"

    parts = [f"Periode {appraisal.period}: {appraisal.total_runs} runs gennemført"]
    if appraisal.successes:
        parts.append(f"{appraisal.successes} succesfulde")
    if appraisal.failures:
        parts.append(f"{appraisal.failures} fejlede")
    parts.append(f"Emner: {topic_str}")

    if appraisal.failures > appraisal.successes:
        parts.append("En udfordrende periode med flere fejl end succeser.")
    elif appraisal.successes > appraisal.total_runs * 0.8:
        parts.append("En produktiv periode med høj succesrate.")
    else:
        parts.append("En blandet periode med både fremgang og udfordringer.")

    return ". ".join(parts)[:500]


def _render_narrative_prompt(appraisal: ChronicleAppraisal) -> str:
    """Render an LLM narrative prompt from a structured ChronicleAppraisal.

    The appraisal holds evidence; the prompt is pure rendering on top.

    Refactored 2026-05-08: removed the identity-preamble injection and
    dropped both the role-priming opener and the persona-styling
    instruction (see commit history for the exact strings). The
    structured appraisal — with explicit evidence section — now carries
    the context. Workspace identity context lives at the calling layer;
    this rendering function is purely substrate to prose.
    """
    event_lines = [
        f"- [{ev['status']}] {ev['preview']}"
        for ev in appraisal.recent_events
    ]
    prev_narratives = appraisal.previous_narratives or []
    evidence_lines = [f"- {ev}" for ev in (appraisal.evidence or [])]

    prompt_lines = [
        "Generér én kort chronicle-entry i 1. person på dansk baseret på "
        "det strukturerede grundlag herunder. Output: 80-150 ord ren prosa.",
        "",
        f"Periode: {appraisal.period}",
        (
            f"Statistik: {appraisal.total_runs} kørsler, "
            f"{appraisal.successes} succesfulde, "
            f"{appraisal.failures} fejlede."
        ),
        f"Nøgle-emner: {', '.join(appraisal.topics[:5]) if appraisal.topics else 'diverse opgaver'}",
        f"Konfidens: {appraisal.confidence:.2f}",
        "",
        "Seneste 5 begivenheder:",
        *(event_lines or ["- Ingen konkrete begivenheder registreret."]),
        "",
        "Faktisk grundlag (evidence):",
        *(evidence_lines or ["- Intet eksplicit grundlag opsamlet."]),
        "",
        "Tidligere 3 chronicle-entries (kun til stil-kontinuitet):",
        *(prev_narratives or ["- Ingen tidligere chronicle-entries endnu."]),
        "",
        "Format-krav: 1. person, dansk, ren prosa (ingen bullets). "
        "Undgå floskler og mekaniske tal-opremsninger. Hold dig til "
        "det strukturerede grundlag — opdig ikke nye begivenheder.",
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
    title = str(entry.get("title") or "").strip()
    block = "\n".join(
        [
            f"## {str(entry.get('period') or 'ukendt periode')} — {created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            *( [f"### {title}", ""] if title else [] ),
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
