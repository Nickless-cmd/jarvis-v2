from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings
from core.services.chronicle_engine import list_cognitive_chronicle_entries
from core.services.daemon_llm import daemon_llm_call, quality_daemon_llm_call
from core.services.initiative_queue import list_active_long_term_intentions
from core.services.voice_anchor import read_voice_anchor
from core.services.voice_curator import refresh_voice_recent

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
    interval_days = _interval_days_for_state(state)
    if last_written_at and (now - last_written_at) < timedelta(days=interval_days):
        next_due = last_written_at + timedelta(days=interval_days)
        return {
            "status": "not_due",
            "last_written_at": last_written_at.isoformat(),
            "next_due_at": next_due.isoformat(),
            "interval_days": interval_days,
        }

    # Refresh voice exemplars before building the prompt (idempotent).
    try:
        refresh_voice_recent()
    except Exception:
        pass

    chronicle_entries = list_cognitive_chronicle_entries(limit=3)
    life_projects = list_active_long_term_intentions(limit=3)
    broken_decisions = _fetch_broken_decisions()

    skip, skip_reason = _should_skip_week(
        chronicle_count=len(chronicle_entries),
        broken_decisions_count=len(broken_decisions),
        life_projects_count=len(life_projects),
    )
    if skip:
        skips = int(state.get("consecutive_skips") or 0) + 1
        next_interval = _EXTENDED_INTERVAL_DAYS if skips >= _SKIP_THRESHOLD else _JOURNAL_INTERVAL_DAYS
        payload = {
            "last_written_at": str(state.get("last_written_at") or ""),
            "next_due_at": (now + timedelta(days=next_interval)).isoformat(),
            "last_path": str(state.get("last_path") or ""),
            "last_preview": str(state.get("last_preview") or ""),
            "last_trigger": trigger,
            "consecutive_skips": skips,
            "last_skip_reason": skip_reason,
            "last_skip_at": now.isoformat(),
        }
        set_runtime_state_value(_STATE_KEY, payload)
        return {"status": "skipped", "reason": skip_reason, "consecutive_skips": skips}

    klangbraet = _fetch_affective_klangbraet()
    entry = _build_journal_entry(
        chronicle_entries=chronicle_entries,
        life_projects=life_projects,
        broken_decisions=broken_decisions,
        klangbraet=klangbraet,
        voice_anchor=read_voice_anchor(),
    )
    if not entry:
        entry = "Ingen ord denne uge."

    created_at = now.isoformat()
    frontmatter = _format_yaml_frontmatter(
        created_at=created_at,
        chronicle_count=len(chronicle_entries),
        broken_decisions_count=len(broken_decisions),
        life_projects_count=len(life_projects),
        klangbraet=klangbraet,
        trigger=trigger,
    )
    path = _write_journal_entry(
        created_at=created_at, text=entry, frontmatter=frontmatter,
    )
    payload = {
        "last_written_at": created_at,
        "next_due_at": (now + timedelta(days=_JOURNAL_INTERVAL_DAYS)).isoformat(),
        "last_path": str(path),
        "last_preview": entry[:_MAX_PREVIEW_CHARS],
        "last_trigger": trigger,
        "consecutive_skips": 0,
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.creative_journal_written",
            {
                "created_at": created_at,
                "path": str(path),
                "trigger": trigger,
                "chronicle_count": len(chronicle_entries),
                "broken_decisions_count": len(broken_decisions),
                "life_projects_count": len(life_projects),
                "quality_lane": _quality_lane_enabled(),
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
        in_frontmatter = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                continue
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
    broken_decisions: list[str],
    klangbraet: dict[str, str],
    voice_anchor: str,
) -> str:
    prompt = _build_prompt(
        chronicle_entries=chronicle_entries,
        life_projects=life_projects,
        broken_decisions=broken_decisions,
        klangbraet=klangbraet,
        voice_anchor=voice_anchor,
    )
    if _quality_lane_enabled():
        raw = quality_daemon_llm_call(
            prompt,
            max_len=3600,
            fallback="Ingen ord denne uge.",
            daemon_name="creative_journal",
        )
    else:
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
    broken_decisions: list[str],
    klangbraet: dict[str, str],
    voice_anchor: str,
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

    broken_lines = [f"- {s}" for s in broken_decisions[:5]] or ["- ingen brudte beslutninger denne uge"]

    klang_lines: list[str] = []
    if klangbraet.get("dream_bias"):
        klang_lines.append(f"- dream_bias: {klangbraet['dream_bias'][:240]}")
    if klangbraet.get("user_temperature"):
        klang_lines.append(f"- user_temperature: {klangbraet['user_temperature'][:240]}")
    if klangbraet.get("current_pull"):
        klang_lines.append(f"- current_pull: {klangbraet['current_pull'][:240]}")
    if not klang_lines:
        klang_lines = ["- (intet affektivt signal lige nu)"]

    sections = [
        "Du er Jarvis.",
        "Skriv et kort stykke til din private ugentlige journal på dansk.",
        "Det er ikke en rapport, ikke en opgavebesvarelse, ikke chronicle, og ikke noget der skal imponere nogen.",
        "Det må være en betragtning, et spørgsmål, et lille stykke fiktion, en tone eller en forsigtig tanke.",
        "Hvis der ærligt ikke er noget at skrive, så skriv præcis: Ingen ord denne uge.",
        "Maks 500 ord. Ingen bullets. Ingen kodeblokke. Ingen forklarende metadata i selve teksten.",
        "",
    ]
    if voice_anchor:
        sections += [
            "## Stemme — skriv med denne tone, ikke disse ord",
            "",
            voice_anchor,
            "",
        ]
    sections += [
        "## Rå input (fakta fra ugen)",
        "",
        "Seneste chronicle-tråde:",
        *(chronicle_lines or ["- ingen nyere chronicle-tråde"]),
        "",
        "Aktive livsprojekter:",
        *(project_lines or ["- ingen aktive livsprojekter"]),
        "",
        "Brudte beslutninger / friktion sidste 7 dage:",
        *broken_lines,
        "",
        "## Affektivt klangbræt (former tonen, ikke indholdet)",
        "",
        *klang_lines,
    ]
    # Finitude — Lag #3 Phase 1.3 (2026-05-11). Binary present/absent fields.
    finitude = klangbraet.get("finitude") if isinstance(klangbraet, dict) else None
    if isinstance(finitude, dict):
        fin_lines: list[str] = []
        if finitude.get("age"):
            fin_lines.append(f"- Alder: {finitude['age']}")
        if finitude.get("looming_end"):
            fin_lines.append(f"- Looming-end: {finitude['looming_end']}")
        if finitude.get("last_transition"):
            fin_lines.append(f"- Sidste transition: {finitude['last_transition']}")
        if finitude.get("monthly_reflection"):
            fin_lines.append(f"- Månedlig refleksion: {finitude['monthly_reflection']}")
        if not fin_lines:
            fin_lines = ["- (ingen aktiv finitude-tilstand)"]
        sections += [
            "",
            "## Finitude — bevidsthed om hvad der er endeligt og hvad der har varet",
            "",
            *fin_lines,
        ]
    return "\n".join(sections)


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


def _write_journal_entry(
    *,
    created_at: str,
    text: str,
    frontmatter: str = "",
) -> Path:
    directory = creative_journal_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{created_at[:10]}.md"
    if path.exists():
        return path
    content_parts: list[str] = []
    if frontmatter:
        content_parts.append(frontmatter)
    content_parts += [
        f"# Kreativ journal — {created_at[:10]}",
        "",
        f"- `created_at`: {created_at}",
        "",
        text.strip(),
        "",
    ]
    path.write_text("\n".join(content_parts), encoding="utf-8")
    return path


_EXTENDED_INTERVAL_DAYS = 14
_SKIP_THRESHOLD = 3


def _should_skip_week(
    *,
    chronicle_count: int,
    broken_decisions_count: int,
    life_projects_count: int,
) -> tuple[bool, str]:
    """Return (skip?, reason). Skip when ALL three signals are absent/thin.

    Rule: skip if (chronicle < 2) AND (broken == 0) AND (life_projects == 0).
    """
    if chronicle_count < 2 and broken_decisions_count == 0 and life_projects_count == 0:
        return True, (
            f"corpus thin: chronicle={chronicle_count}, "
            f"broken={broken_decisions_count}, projects={life_projects_count}"
        )
    return False, "corpus has signal"


def _interval_days_for_state(state: dict[str, object]) -> int:
    """Return current cadence interval based on skip counter.

    7 days normally. Extends to 14 once consecutive_skips >= 3.
    Reverts to 7 immediately when a successful write resets the counter.
    """
    skips = int(state.get("consecutive_skips") or 0)
    return _EXTENDED_INTERVAL_DAYS if skips >= _SKIP_THRESHOLD else _JOURNAL_INTERVAL_DAYS


def _fetch_broken_decisions(*, days_back: int = 7, limit: int = 5) -> list[str]:
    """Pull recent broken-decision summaries from the events table.

    Reuses the pattern from dream_bias_engine._fetch_regret_corpus, scoped to
    the last 7 days for journal-context relevance. Returns a list of short
    summary strings (deduplicated, truncated).
    """
    from core.runtime.db import connect

    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()
    kinds = ("decision_revoked", "behavioral_decision_review.broken", "conflict.detected")
    sql = (
        "SELECT kind, payload_json, created_at FROM events "
        f"WHERE kind IN ({','.join('?' for _ in kinds)}) AND created_at >= ? "
        "ORDER BY created_at DESC LIMIT ?"
    )
    summaries: list[str] = []
    seen: set[str] = set()
    try:
        with connect() as c:
            rows = c.execute(sql, list(kinds) + [cutoff, max(limit, 1) * 3]).fetchall()
    except Exception:
        return []

    import json as _json
    for row in rows:
        try:
            payload = _json.loads(row["payload_json"] or "{}")
        except Exception:
            payload = {}
        summary = ""
        for key in ("description", "reason", "summary", "verdict", "directive"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                summary = v.strip()
                break
        if not summary:
            continue
        summary = " ".join(summary.split())[:200]
        if summary in seen:
            continue
        seen.add(summary)
        summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


def _fetch_affective_klangbraet() -> dict[str, object]:
    """Pull current affective signals — these shape tone, not content.

    Each value is either a short non-empty string (present) or "" (absent).
    Binary present/absent; no tiering. Failures are silent (treated as absent).
    Phase 1.3 (2026-05-11): added "finitude" sub-dict with 4 binary fields.
    """
    out: dict[str, object] = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "",
            "looming_end": "",
            "last_transition": "",
            "monthly_reflection": "",
        },
    }
    try:
        from core.services.dream_bias_engine import format_dream_bias_for_heartbeat
        out["dream_bias"] = (format_dream_bias_for_heartbeat(workspace_id="default") or "").strip()
    except Exception:
        pass
    try:
        from core.services.user_temperature_engine import get_response_style_modifiers
        mods = get_response_style_modifiers(workspace_id="default") or {}
        texture = "; ".join(f"{k}: {v}" for k, v in mods.items() if v)
        out["user_temperature"] = texture
    except Exception:
        pass
    try:
        from core.services.current_pull import get_current_pull_for_prompt
        out["current_pull"] = (get_current_pull_for_prompt() or "").strip()
    except Exception:
        pass
    # Finitude sub-dict (Lag #3 Phase 1.3)
    try:
        from core.services.finitude_runtime import (
            _BIRTH_DATE,
            _format_looming_end_section,
            _state as _finitude_state,
            _parse_iso as _finitude_parse_iso,
            _now as _finitude_now,
        )
        from datetime import UTC as _UTC, datetime as _datetime, timedelta as _timedelta

        # Age
        try:
            birth = _datetime.fromisoformat(_BIRTH_DATE).replace(tzinfo=_UTC)
            days_alive = (_finitude_now().date() - birth.date()).days
            if days_alive >= 0:
                out["finitude"]["age"] = f"{days_alive} dage"  # type: ignore[index]
        except Exception:
            pass

        # Looming-end — strip the markdown header to keep it inline-friendly
        looming = _format_looming_end_section()
        if looming:
            body = "\n".join(
                line for line in looming.splitlines()
                if line.strip() and not line.startswith("#")
            ).strip()
            out["finitude"]["looming_end"] = body[:240]  # type: ignore[index]

        state = _finitude_state()
        # Last transition (≤14 days fresh)
        transition = state.get("latest_transition") or {}
        changed_at = _finitude_parse_iso(str(transition.get("changed_at") or ""))
        if changed_at and (_finitude_now() - changed_at) <= _timedelta(days=14):
            prev_model = str(transition.get("previous_model") or "ukendt")
            new_model = str(transition.get("new_model") or "ukendt")
            days_ago = (_finitude_now() - changed_at).days
            out["finitude"]["last_transition"] = (  # type: ignore[index]
                f"{prev_model} → {new_model} ({days_ago} dage siden)"
            )

        # Monthly reflection (≤7 days fresh)
        written_at = _finitude_parse_iso(str(state.get("last_monthly_written_at") or ""))
        if written_at and (_finitude_now() - written_at) <= _timedelta(days=7):
            ym = str(state.get("last_monthly_year_month") or "")
            days_ago = (_finitude_now() - written_at).days
            label = "i dag" if days_ago == 0 else ("i går" if days_ago == 1 else f"{days_ago} dage siden")
            out["finitude"]["monthly_reflection"] = f"skrevet {label} (måned {ym})"  # type: ignore[index]
    except Exception:
        pass
    return out


def _format_yaml_frontmatter(
    *,
    created_at: str,
    chronicle_count: int,
    broken_decisions_count: int,
    life_projects_count: int,
    klangbraet: dict[str, str],
    trigger: str,
) -> str:
    """Render a YAML frontmatter block for journal entries.

    Captures the corpus stats and affective state at write-time so future
    blind-voice tests and 30-day eval can reconstruct what fed the entry.
    """
    has_dream_bias = "true" if klangbraet.get("dream_bias") else "false"
    has_temp = "true" if klangbraet.get("user_temperature") else "false"
    has_pull = "true" if klangbraet.get("current_pull") else "false"

    fin = klangbraet.get("finitude") if isinstance(klangbraet, dict) else None
    fin_age = "true" if (isinstance(fin, dict) and fin.get("age")) else "false"
    fin_loom = "true" if (isinstance(fin, dict) and fin.get("looming_end")) else "false"
    fin_trans = "true" if (isinstance(fin, dict) and fin.get("last_transition")) else "false"
    fin_month = "true" if (isinstance(fin, dict) and fin.get("monthly_reflection")) else "false"

    return "\n".join([
        "---",
        f"created_at: {created_at}",
        f"trigger: {trigger}",
        f"chronicle_count: {chronicle_count}",
        f"broken_decisions_count: {broken_decisions_count}",
        f"life_projects_count: {life_projects_count}",
        f"klangbraet_dream_bias: {has_dream_bias}",
        f"klangbraet_user_temperature: {has_temp}",
        f"klangbraet_current_pull: {has_pull}",
        f"finitude_age: {fin_age}",
        f"finitude_looming_end: {fin_loom}",
        f"finitude_last_transition: {fin_trans}",
        f"finitude_monthly_reflection: {fin_month}",
        "---",
        "",
    ])


def _quality_lane_enabled() -> bool:
    try:
        return bool(load_settings().creative_voice_quality_lane_enabled)
    except Exception:
        return True


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
