from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings
from core.services.chronicle_engine import list_cognitive_chronicle_entries
from core.services.daemon_llm import daemon_llm_call
from core.services.initiative_queue import list_active_long_term_intentions

_STATE_KEY = "creative_journal_runtime.state"
_JOURNAL_INTERVAL_DAYS = 7
_MAX_WORDS = 500
_MAX_PREVIEW_CHARS = 240


def run_creative_journal_cycle(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    if not _creative_journal_enabled():
        return {"status": "disabled", "reason": "layer_creative_journal_enabled=false"}

    state = _state()
    now = datetime.now(UTC)
    last_written_at = _parse_iso(str(state.get("last_written_at") or ""))
    if last_written_at and (now - last_written_at) < timedelta(days=_JOURNAL_INTERVAL_DAYS):
        next_due = last_written_at + timedelta(days=_JOURNAL_INTERVAL_DAYS)
        return {
            "status": "not_due",
            "last_written_at": last_written_at.isoformat(),
            "next_due_at": next_due.isoformat(),
        }

    entry = _build_journal_entry(
        chronicle_entries=list_cognitive_chronicle_entries(limit=3),
        life_projects=list_active_long_term_intentions(limit=3),
    )
    if not entry:
        entry = "Ingen ord denne uge."

    created_at = now.isoformat()
    path = _write_journal_entry(created_at=created_at, text=entry)
    payload = {
        "last_written_at": created_at,
        "next_due_at": (now + timedelta(days=_JOURNAL_INTERVAL_DAYS)).isoformat(),
        "last_path": str(path),
        "last_preview": entry[:_MAX_PREVIEW_CHARS],
        "last_trigger": trigger,
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.creative_journal_written",
            {
                "created_at": created_at,
                "path": str(path),
                "trigger": trigger,
            },
        )
    except Exception:
        pass
    return {"status": "written", "path": str(path), "text": entry, **payload}


def build_creative_journal_surface() -> dict[str, object]:
    state = _state()
    directory = creative_journal_dir()
    entries = list_creative_journal_entries(limit=12)
    return {
        "active": bool(entries or state),
        "enabled": _creative_journal_enabled(),
        "path": str(directory),
        "items": entries,
        "summary": {
            "entry_count": len(entries),
            "last_written_at": str(state.get("last_written_at") or ""),
            "next_due_at": str(state.get("next_due_at") or ""),
            "last_preview": str(state.get("last_preview") or ""),
            "enabled": _creative_journal_enabled(),
        },
    }


def creative_journal_dir() -> Path:
    workspace_dir = ensure_default_workspace()
    return workspace_dir / "journal"


def list_creative_journal_entries(*, limit: int = 12) -> list[dict[str, object]]:
    directory = creative_journal_dir()
    if not directory.exists():
        return []
    items: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.md"), reverse=True)[: max(limit, 1)]:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        preview = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("- `"):
                preview = stripped
                break
        items.append(
            {
                "filename": path.name,
                "path": str(path),
                "preview": preview[:_MAX_PREVIEW_CHARS],
            }
        )
    return items


def _build_journal_entry(
    *,
    chronicle_entries: list[dict[str, object]],
    life_projects: list[dict[str, object]],
) -> str:
    prompt = _build_prompt(
        chronicle_entries=chronicle_entries,
        life_projects=life_projects,
    )
    raw = daemon_llm_call(
        prompt,
        max_len=3600,
        fallback="Ingen ord denne uge.",
        daemon_name="creative_journal",
    )
    return _sanitize_entry(raw)


def _build_prompt(
    *,
    chronicle_entries: list[dict[str, object]],
    life_projects: list[dict[str, object]],
) -> str:
    chronicle_lines = []
    for entry in chronicle_entries[:3]:
        period = str(entry.get("period") or "ukendt")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            chronicle_lines.append(f"- {period}: {narrative[:240]}")

    project_lines = []
    for project in life_projects[:3]:
        focus = str(project.get("focus") or "").strip()
        why_text = " ".join(str(project.get("why_text") or "").split()).strip()
        if focus:
            line = f"- {focus}"
            if why_text:
                line += f" — {why_text[:140]}"
            project_lines.append(line)

    return "\n".join(
        [
            "Du er Jarvis.",
            "Skriv et kort stykke til din private ugentlige journal på dansk.",
            "Det er ikke en rapport, ikke en opgavebesvarelse, ikke chronicle, og ikke noget der skal imponere nogen.",
            "Det må være en betragtning, et spørgsmål, et lille stykke fiktion, en tone eller en forsigtig tanke.",
            "Hvis der ærligt ikke er noget at skrive, så skriv præcis: Ingen ord denne uge.",
            "Maks 500 ord. Ingen bullets. Ingen kodeblokke. Ingen forklarende metadata i selve teksten.",
            "",
            "Seneste chronicle-tråde:",
            *(chronicle_lines or ["- ingen nyere chronicle-tråde"]),
            "",
            "Aktive livsprojekter:",
            *(project_lines or ["- ingen aktive livsprojekter"]),
        ]
    )


def _sanitize_entry(raw: str) -> str:
    text = str(raw or "").replace("```", " ").strip().strip('"').strip()
    if not text:
        return ""
    paragraphs = [" ".join(line.split()) for line in text.splitlines()]
    text = "\n\n".join(part for part in paragraphs if part).strip()
    words = text.split()
    if len(words) > _MAX_WORDS:
        text = " ".join(words[:_MAX_WORDS]).rstrip(" ,;:-")
    return text.strip() or "Ingen ord denne uge."


def _write_journal_entry(*, created_at: str, text: str) -> Path:
    directory = creative_journal_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{created_at[:10]}.md"
    if path.exists():
        return path
    content = "\n".join(
        [
            f"# Kreativ journal — {created_at[:10]}",
            "",
            f"- `created_at`: {created_at}",
            "",
            text.strip(),
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path


def _creative_journal_enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_creative_journal_enabled", True))


def _state() -> dict[str, object]:
    payload = get_runtime_state_value(_STATE_KEY, default={})
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
