from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.config import PROJECT_ROOT
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings
from core.services.chronicle_engine import list_cognitive_chronicle_entries
from core.services.daemon_llm import daemon_llm_call

_SELF_CRITIQUE_STATE_KEY = "self_critique_runtime.state"
_SELF_CRITIQUE_PROMPT = (
    "Læs principperne om dig. Hvilken af dem stemmer ikke længere med din oplevelse? "
    "Hvad ville du ændre?"
)
_SELF_CRITIQUE_INTERVAL_DAYS = 30
_SELF_CRITIQUE_REVIEW_DAYS = 90
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

    docs_payload = read_self_docs(doc_id="all", include_history=False)
    docs_text = str(docs_payload.get("text") or "").strip()
    chronicle_entries = list_cognitive_chronicle_entries(limit=3)
    chronicle_text = _render_recent_chronicles(chronicle_entries)
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
        prompt=_SELF_CRITIQUE_PROMPT,
        critique=critique,
        source_docs=[str(item.get("key") or "") for item in docs_payload.get("docs", []) if item.get("key")],
    )
    payload = {
        "entry_id": entry_id,
        "last_written_at": created_at,
        "next_due_at": (now + timedelta(days=_SELF_CRITIQUE_INTERVAL_DAYS)).isoformat(),
        "next_review_at": next_review_at,
        "last_trigger": trigger,
        "last_preview": critique[:240],
    }
    set_runtime_state_value(_SELF_CRITIQUE_STATE_KEY, payload)
    event_bus.publish(
        "cognitive_state.self_critique_written",
        {
            "entry_id": entry_id,
            "created_at": created_at,
            "next_review_at": next_review_at,
            "trigger": trigger,
        },
    )
    return {"status": "written", **payload}


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


def _append_self_critique_entry(
    *,
    entry_id: str,
    created_at: str,
    next_review_at: str,
    prompt: str,
    critique: str,
    source_docs: list[str],
) -> None:
    path = self_critique_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# SELF_CRITIQUE\n\n"
    entry = "\n".join(
        [
            f"## {created_at[:16].replace('T', ' ')}",
            f"- `entry_id`: {entry_id}",
            f"- `next_review_at`: {next_review_at}",
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
