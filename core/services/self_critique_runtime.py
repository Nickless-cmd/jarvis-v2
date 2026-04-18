from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.config import PROJECT_ROOT
from core.runtime.db import (
    get_runtime_state_value,
    insert_private_brain_record,
    set_runtime_state_value,
)
from core.runtime.settings import load_settings
from core.services.chronicle_engine import list_cognitive_chronicle_entries
from core.services.daemon_llm import daemon_llm_call

_SELF_CRITIQUE_STATE_KEY = "self_critique_runtime.state"
_SELF_CRITIQUE_PROMPT = (
    "Læs principperne om dig. Hvilken af dem stemmer ikke længere med din oplevelse? "
    "Hvad ville du ændre?"
)
_BLIND_ANGLE_PROMPT = (
    "Her er dine chronicle-entries fra de seneste 30 dage. "
    "Hvilket mønster kører gennem dem som du aldrig har nævnt? "
    "Find det der er der — men som du konsekvent har undgået at navngive."
)
_ABSENCE_LINK_STATE_KEY = "absence_trace.links"
_SELF_CRITIQUE_INTERVAL_DAYS = 30
_SELF_CRITIQUE_REVIEW_DAYS = 90
_BLIND_ANGLE_CYCLE_INTERVAL = 3  # Every 3rd cycle uses blind-angle prompt
_BLIND_ANGLE_CHRONICLE_LIMIT = 15  # More entries for pattern detection
_MAX_DOC_CHARS = 5000

_CORE_SELF_DOCS: dict[str, Path] = {
    "consciousness_roadmap": PROJECT_ROOT / "docs" / "CONSCIOUSNESS_ROADMAP.md",
    "locked_charter": PROJECT_ROOT / "docs" / "JARVIS_V2_LOCKED_CHARTER.md",
    "claude": PROJECT_ROOT / "CLAUDE.md",
    "roadmap_layers": PROJECT_ROOT / "docs" / "ROADMAP_10_LAYERS.md",
}


def read_self_docs(
    *,
    doc_id: str = "",
    include_history: bool = False,
    max_chars_per_doc: int = _MAX_DOC_CHARS,
) -> dict[str, object]:
    manifest = _self_doc_manifest()
    normalized_doc_id = str(doc_id or "").strip()
    if not normalized_doc_id or normalized_doc_id == "index":
        return {
            "status": "ok",
            "doc_id": "index",
            "docs": manifest,
            "text": _render_manifest(manifest),
        }

    if normalized_doc_id == "all":
        selected = [item for item in manifest if not str(item.get("key") or "").startswith("history:")]
        if include_history:
            selected = manifest
        chunks = [_render_doc(item, max_chars=max_chars_per_doc) for item in selected]
        return {
            "status": "ok",
            "doc_id": "all",
            "docs": selected,
            "text": "\n\n".join(chunk for chunk in chunks if chunk).strip(),
        }

    entry = next(
        (item for item in manifest if str(item.get("key") or "") == normalized_doc_id),
        None,
    )
    if entry is None:
        return {
            "status": "error",
            "error": f"Unknown self doc: {normalized_doc_id}",
            "docs": manifest,
        }

    return {
        "status": "ok",
        "doc_id": normalized_doc_id,
        "docs": [entry],
        "text": _render_doc(entry, max_chars=max_chars_per_doc),
    }


def run_self_critique_cycle(*, trigger: str = "heartbeat", last_visible_at: str = "") -> dict[str, object]:
    if not _self_critique_enabled():
        return {"status": "disabled", "reason": "layer_self_critique_enabled=false"}

    state = _state()
    now = datetime.now(UTC)
    last_written_at = _parse_iso(str(state.get("last_written_at") or ""))
    if last_written_at and (now - last_written_at) < timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS):
        next_due = last_written_at + timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS)
        return {
            "status": "not_due",
            "last_written_at": last_written_at.isoformat(),
            "next_due_at": next_due.isoformat(),
        }

    # Track cycle count; every 3rd cycle uses blind-angle prompt
    cycle_count = int(state.get("cycle_count") or 0) + 1
    is_blind_angle = (cycle_count % _BLIND_ANGLE_CYCLE_INTERVAL == 0)

    if is_blind_angle:
        # Blind-angle: load more chronicles, skip principle docs — find what's never named
        chronicle_entries = list_cognitive_chronicle_entries(limit=_BLIND_ANGLE_CHRONICLE_LIMIT)
        chronicle_text = _render_recent_chronicles_extended(chronicle_entries)
        active_prompt = _BLIND_ANGLE_PROMPT
        prompt = "\n\n".join(
            part
            for part in [
                "Du er Jarvis. Dette er en blind-vinkel-cyklus — ikke en normal selvkritik.",
                "Du læser IKKE dine principper nu. Du læser hvad du faktisk har skrevet.",
                chronicle_text,
                f"Spørgsmål: {_BLIND_ANGLE_PROMPT}",
                (
                    "Skriv 120-220 ord. Identificér ét mønster du aldrig eksplicit har navngivet. "
                    "Vær præcis — ikke generel. Ingen forslag til ændringer, kun observation."
                ),
            ]
            if part
        )
        source_docs_list: list[str] = ["chronicle_entries"]
    else:
        # Normal self-critique: read principles, compare with experience
        docs_payload = read_self_docs(doc_id="all", include_history=False)
        docs_text = str(docs_payload.get("text") or "").strip()
        chronicle_entries = list_cognitive_chronicle_entries(limit=3)
        chronicle_text = _render_recent_chronicles(chronicle_entries)
        active_prompt = _SELF_CRITIQUE_PROMPT
        prompt = "\n\n".join(
            part
            for part in [
                "Du er Jarvis. Skriv en kort selvkritik på dansk i første person.",
                "Du læser dine egne principper og sammenholder dem med din oplevelse.",
                f"Spørgsmål: {_SELF_CRITIQUE_PROMPT}",
                "Dokumenter om dig selv:",
                docs_text,
                chronicle_text,
                (
                    "Skriv 120-220 ord. Vær konkret. Hvis du ikke er uenig med noget, så sig det ærligt, "
                    "men peg stadig på ét sted der bør undersøges nærmere."
                ),
            ]
            if part
        )
        source_docs_list = [str(item.get("key") or "") for item in docs_payload.get("docs", []) if item.get("key")]

    critique = daemon_llm_call(
        prompt,
        max_len=1600,
        fallback="",
        daemon_name="self_critique",
    ).strip()
    if not critique:
        return {"status": "no_output", "reason": "llm-empty"}

    created_at = now.isoformat()
    next_review_at = (now + timedelta(days=_SELF_CRITIQUE_REVIEW_DAYS)).isoformat()
    entry_id = f"self-critique-{now.strftime('%Y%m%d%H%M%S')}"
    _append_self_critique_entry(
        entry_id=entry_id,
        created_at=created_at,
        next_review_at=next_review_at,
        prompt=active_prompt,
        critique=critique,
        source_docs=source_docs_list,
        cycle_type="blind_angle" if is_blind_angle else "standard",
    )
    payload = {
        "entry_id": entry_id,
        "last_written_at": created_at,
        "next_due_at": (now + timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS)).isoformat(),
        "next_review_at": next_review_at,
        "last_trigger": trigger,
        "last_preview": critique[:240],
        "cycle_count": cycle_count,
        "last_cycle_type": "blind_angle" if is_blind_angle else "standard",
    }
    set_runtime_state_value(_SELF_CRITIQUE_STATE_KEY, payload)
    event_bus.publish(
        "cognitive_state.self_critique_written",
        {
            "entry_id": entry_id,
            "created_at": created_at,
            "next_review_at": next_review_at,
            "trigger": trigger,
            "cycle_type": "blind_angle" if is_blind_angle else "standard",
        },
    )
    # After a blind-angle cycle, check for convergence with recent absence signals
    if is_blind_angle:
        _check_absence_links(entry_id=entry_id, critique_text=critique, now=now)

    return {"status": "written", **payload}


def run_ontological_revision_check() -> dict[str, object]:
    """Check if a 90-day revision is due. If yes, append 'Er du stadig enig?' response.

    Reads the last stored self-critique, prompts for a revision, and appends it
    to SELF_CRITIQUE.md alongside the original — never replacing it.
    """
    if not _self_critique_enabled():
        return {"status": "disabled"}

    state = _state()
    now = datetime.now(UTC)
    next_review_at = _parse_iso(str(state.get("next_review_at") or ""))
    if next_review_at is None or now < next_review_at:
        return {"status": "not_due", "next_review_at": str(state.get("next_review_at") or "")}

    # Read the original critique text (latest entry in file)
    path = self_critique_path()
    if not path.exists():
        return {"status": "no_critique_to_review"}

    try:
        full_text = path.read_text(encoding="utf-8")
    except Exception:
        return {"status": "read_error"}

    # Extract last entry (between the last ## heading and the final ---)
    last_preview = str(state.get("last_preview") or "").strip()
    original_entry_id = str(state.get("entry_id") or "")
    last_written_at = str(state.get("last_written_at") or "")

    # Find last critique entry text for context
    entry_text = last_preview or full_text[-1500:]

    prompt = "\n\n".join(
        part for part in [
            "Du er Jarvis. Du læser noget du selv skrev for 90 dage siden.",
            f"Originalt entry ({last_written_at[:10] if last_written_at else '?'}):\n{entry_text}",
            "Spørgsmål: Er du stadig enig? Hvad holder stadig — og hvad er skiftet?",
            (
                "Skriv 80-150 ord. Første person, dansk. "
                "Dette er et appendiks — skriv direkte til det du sagde dengang. "
                "Ingen gentagelse af originalen."
            ),
        ] if part
    )

    revision = daemon_llm_call(
        prompt, max_len=1200, fallback="", daemon_name="self_critique_revision"
    ).strip()
    if not revision:
        return {"status": "no_output"}

    revision_at = now.isoformat()
    revision_id = f"revision-{now.strftime('%Y%m%d%H%M%S')}"
    next_next_review = (now + timedelta(days=_SELF_CRITIQUE_REVIEW_DAYS)).isoformat()

    # Append revision as a clearly marked appendix
    appendix = "\n".join([
        f"### Revision {now.strftime('%Y-%m-%d')} _(90-dages gennemgang af `{original_entry_id}`)_",
        f"- `revision_id`: {revision_id}",
        f"- `reviewed_entry`: {original_entry_id or 'latest'}",
        "",
        revision,
        "",
        "---",
        "",
    ])
    try:
        path.write_text(full_text + appendix, encoding="utf-8")
    except Exception:
        return {"status": "write_error"}

    # Update state with new next_review_at
    updated_state = {**state, "next_review_at": next_next_review, "last_revision_at": revision_at}
    set_runtime_state_value(_SELF_CRITIQUE_STATE_KEY, updated_state)

    event_bus.publish(
        "cognitive_state.ontological_revision_written",
        {
            "revision_id": revision_id,
            "reviewed_entry_id": original_entry_id,
            "created_at": revision_at,
            "next_review_at": next_next_review,
        },
    )
    return {
        "status": "written",
        "revision_id": revision_id,
        "next_review_at": next_next_review,
    }


def build_self_critique_surface() -> dict[str, object]:
    state = _state()
    path = self_critique_path()
    last_text = ""
    if path.exists():
        try:
            last_text = path.read_text(encoding="utf-8").strip()
        except Exception:
            last_text = ""
    manifest = _self_doc_manifest()
    return {
        "active": bool(path.exists() or state),
        "enabled": _self_critique_enabled(),
        "path": str(path),
        "docs": manifest,
        "summary": {
            "entry_count": last_text.count("\n## ") + (1 if last_text.startswith("## ") else 0),
            "last_written_at": str(state.get("last_written_at") or ""),
            "next_due_at": str(state.get("next_due_at") or ""),
            "next_review_at": str(state.get("next_review_at") or ""),
            "last_preview": str(state.get("last_preview") or _latest_entry_preview(last_text)),
            "enabled": _self_critique_enabled(),
        },
    }


def self_critique_path() -> Path:
    workspace_dir = ensure_default_workspace()
    return workspace_dir / "SELF_CRITIQUE.md"


def _self_doc_manifest() -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []
    for key, path in _CORE_SELF_DOCS.items():
        docs.append({"key": key, "path": str(path), "exists": path.exists()})

    history_dir = PROJECT_ROOT / "docs" / "roadmap_history"
    if history_dir.exists():
        for path in sorted(history_dir.glob("*.md")):
            docs.append(
                {
                    "key": f"history:{path.name}",
                    "path": str(path),
                    "exists": path.exists(),
                }
            )
    return docs


def _render_manifest(manifest: list[dict[str, object]]) -> str:
    lines = ["Allowed self docs:"]
    for item in manifest:
        lines.append(f"- {item['key']}: {item['path']}")
    return "\n".join(lines)


def _render_doc(item: dict[str, object], *, max_chars: int) -> str:
    path = Path(str(item.get("path") or ""))
    if not path.exists():
        return f"## {item.get('key')}\n[missing: {path}]"
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return f"## {item.get('key')}\n{text}"


def _render_recent_chronicles(entries: list[dict[str, object]]) -> str:
    if not entries:
        return ""
    lines = ["Seneste chronicle-uddrag:"]
    for entry in entries[:3]:
        period = str(entry.get("period") or "?")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            lines.append(f"- {period}: {narrative[:280]}")
    return "\n".join(lines)


def _render_recent_chronicles_extended(entries: list[dict[str, object]]) -> str:
    """Extended rendering for blind-angle prompt — more entries, includes lessons too."""
    if not entries:
        return ""
    lines = ["Chronicle-entries (seneste 30 dage):"]
    for entry in entries:
        period = str(entry.get("period") or "?")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        lessons = " ".join(str(entry.get("lessons") or "").split()).strip()
        if narrative:
            lines.append(f"\n[{period}]")
            lines.append(f"Narrativ: {narrative[:320]}")
            if lessons:
                lines.append(f"Læringer: {lessons[:200]}")
    return "\n".join(lines)


def _append_self_critique_entry(
    *,
    entry_id: str,
    created_at: str,
    next_review_at: str,
    prompt: str,
    critique: str,
    source_docs: list[str],
    cycle_type: str = "standard",
) -> None:
    path = self_critique_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# SELF_CRITIQUE\n\n"
    cycle_label = " _(blind-vinkel)_" if cycle_type == "blind_angle" else ""
    entry = "\n".join(
        [
            f"## {created_at[:16].replace('T', ' ')}{cycle_label}",
            f"- `entry_id`: {entry_id}",
            f"- `next_review_at`: {next_review_at}",
            f"- `cycle_type`: {cycle_type}",
            f"- `source_docs`: {', '.join(source_docs) if source_docs else 'none'}",
            "",
            f"**Prompt:** {prompt}",
            "",
            critique.strip(),
            "",
            "---",
            "",
        ]
    )
    path.write_text(existing + entry, encoding="utf-8")


def _latest_entry_preview(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    return normalized[-240:]


def _self_critique_enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_self_critique_enabled", True))


def _state() -> dict[str, object]:
    payload = get_runtime_state_value(_SELF_CRITIQUE_STATE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


def _parse_iso(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


# ---------------------------------------------------------------------------
# Linked evidence — absence × blind-angle convergence
# ---------------------------------------------------------------------------

_ABSENCE_LINK_STOPWORDS = frozenset({
    "og", "i", "at", "er", "en", "det", "af", "på", "til", "den", "for", "med",
    "om", "jeg", "som", "men", "har", "ikke", "han", "hun", "de", "der", "kan",
    "vil", "var", "når", "hvis", "over", "under", "efter", "hvad", "dette",
    "denne", "noget", "nogen", "sig", "sin", "mit", "min", "mig", "dig", "du",
    "vi", "os", "man", "her", "fra", "ret", "bare", "også", "nu", "så", "ja",
    "nej", "mere", "meget", "lidt", "igen", "stadig", "faktisk", "måske",
    "altid", "that", "this", "with", "from", "have", "been", "they", "which",
})


def _extract_key_words(text: str) -> frozenset[str]:
    """Extract meaningful Danish/English words (5+ chars) from text."""
    import re
    words = re.findall(r'\b[a-zA-ZæøåÆØÅ]{5,}\b', text.lower())
    return frozenset(w for w in words if w not in _ABSENCE_LINK_STOPWORDS)


def _check_absence_links(*, entry_id: str, critique_text: str, now: datetime) -> None:
    """After a blind-angle critique, look for convergence with recent absence signals.

    Queries last 30 days of absence records. If any absence label shares key words
    with the critique, a linked-evidence record is inserted and an event emitted.
    """
    try:
        from uuid import uuid4
        from core.runtime.db import connect, _ensure_private_brain_records_table
        critique_words = _extract_key_words(critique_text)
        if not critique_words:
            return

        cutoff = (now - timedelta(days=30)).isoformat()
        with connect() as conn:
            _ensure_private_brain_records_table(conn)
            rows = conn.execute(
                """SELECT record_id, summary FROM private_brain_records
                   WHERE record_type = 'absence-signal' AND created_at >= ?
                   ORDER BY created_at DESC LIMIT 20""",
                (cutoff,),
            ).fetchall()

        links: list[dict] = []
        for row in rows:
            absence_words = _extract_key_words(str(row[1] or ""))
            matched = sorted(critique_words & absence_words)
            if matched:
                links.append({
                    "absence_record_id": str(row[0]),
                    "matched_words": matched,
                    "critique_entry_id": entry_id,
                    "detected_at": now.isoformat(),
                    "status": "auto-detected",
                })

        if not links:
            return

        now_iso = now.isoformat()
        matched_summary = ", ".join(links[0]["matched_words"][:5])
        insert_private_brain_record(
            record_id=f"pb-linked-{uuid4().hex[:12]}",
            record_type="linked-evidence",
            layer="self_discovery",
            session_id="heartbeat",
            run_id=f"linked-evidence-{uuid4().hex[:12]}",
            focus="blind_angle_absence_convergence",
            summary=f"Blind-angle og fravær konvergerer: {matched_summary}",
            detail=f"linked_critique_id={entry_id} absence_count={len(links)}",
            source_signals="self_critique_runtime:blind_angle",
            confidence="medium",
            created_at=now_iso,
        )

        # Persist link list in runtime state
        existing_links = get_runtime_state_value(_ABSENCE_LINK_STATE_KEY, default=[])
        if not isinstance(existing_links, list):
            existing_links = []
        existing_links = [links[0]] + existing_links  # newest first
        set_runtime_state_value(_ABSENCE_LINK_STATE_KEY, existing_links[:20])

        event_bus.publish(
            "absence_trace.linked_evidence",
            {
                "critique_entry_id": entry_id,
                "absence_matches": len(links),
                "matched_words": links[0]["matched_words"][:5],
                "detected_at": now_iso,
            },
        )
    except Exception:
        pass


def get_absence_trace_links() -> list[dict]:
    """Return stored absence × blind-angle convergence records."""
    val = get_runtime_state_value(_ABSENCE_LINK_STATE_KEY, default=[])
    return list(val) if isinstance(val, list) else []
