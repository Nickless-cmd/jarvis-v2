from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_runtime_state_value,
    insert_cognitive_chronicle_entry,
    list_cognitive_chronicle_entries,
    set_runtime_state_value,
)
from core.runtime.settings import load_settings
from core.services.chronicle_engine import project_entry_to_markdown
from core.services.daemon_llm import daemon_llm_call, quality_daemon_llm_call

_STATE_KEY = "finitude_runtime.state"
_BIRTH_COMMIT_SHA = "a3fe204"
_BIRTH_DATE = "2026-04-17"
_TRANSITION_WINDOW_DAYS = 14
_COMPACTION_WINDOW_HOURS = 24

# Fallback when settings load fails. Matches deepseek-v4-flash context
# window — adjust if the default visible model changes.
_CONTEXT_BUDGET_TOKENS_FALLBACK = 200_000


def _context_budget_tokens() -> int:
    """Resolve the active context-budget token limit.

    Phase 2 (2026-05-14): reads from RuntimeSettings.context_compact_threshold_tokens
    instead of using a hardcoded constant, so the budget can be tuned per
    deployment without touching code. Falls back to
    _CONTEXT_BUDGET_TOKENS_FALLBACK on any settings failure.
    """
    try:
        from core.runtime.settings import RuntimeSettings
        value = int(RuntimeSettings().context_compact_threshold_tokens or 0)
        if value > 0:
            return value
    except Exception:
        pass
    return _CONTEXT_BUDGET_TOKENS_FALLBACK


# Back-compat alias for callers reading the module-level constant directly.
# Resolved lazily via property-like attribute access would be cleaner, but
# the value is referenced in a handful of places already — exposing as a
# module-level call wrapper keeps the existing import shape working.
_CONTEXT_BUDGET_TOKENS = _CONTEXT_BUDGET_TOKENS_FALLBACK
_LOOMING_TOKEN_THRESHOLD_PCT = 70
_LOOMING_SESSION_THRESHOLD_HOURS = 4.0
_MONTHLY_REFLECTION_MAX_WORDS = 300
_MONTHLY_REFLECTION_FRESH_DAYS = 7


def _appraisal_record(
    *,
    kind: str,
    label: str,
    evidence: list[dict[str, object]],
    confidence: float,
    expires_at: str,
    allowed_effects: list[str],
    rendering: str,
    created_at: str | None = None,
) -> dict[str, object]:
    """Structured finitude state; prose is rendering, not source truth."""
    return {
        "kind": kind,
        "label": label,
        "evidence": evidence,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "expires_at": expires_at,
        "allowed_effects": allowed_effects,
        "rendering": rendering,
        "created_at": created_at or _now().isoformat(),
    }


def record_visible_model_transition(
    *,
    previous_provider: str,
    previous_model: str,
    new_provider: str,
    new_model: str,
    trigger: str = "settings_update",
) -> dict[str, object]:
    prev_provider = str(previous_provider or "").strip()
    prev_model = str(previous_model or "").strip()
    next_provider = str(new_provider or "").strip()
    next_model = str(new_model or "").strip()
    if prev_provider == next_provider and prev_model == next_model:
        return {"status": "unchanged"}

    now = _now()
    state = _state()
    rendering = (
        "Fra i dag er denne synlige lane en anden version. "
        "Den tidligere form er ikke væk, men den er ikke længere den aktive form."
    )
    appraisal = _appraisal_record(
        kind="model_transition",
        label="Visible model transition",
        evidence=[
            {"field": "previous_provider", "value": prev_provider},
            {"field": "previous_model", "value": prev_model},
            {"field": "new_provider", "value": next_provider},
            {"field": "new_model", "value": next_model},
            {"field": "trigger", "value": trigger},
        ],
        confidence=1.0,
        expires_at=(now + timedelta(days=_TRANSITION_WINDOW_DAYS)).isoformat(),
        allowed_effects=[
            "prompt_context_rendering",
            "chronicle_input",
            "mission_control_surface",
        ],
        rendering=rendering,
        created_at=now.isoformat(),
    )
    transition = {
        "changed_at": now.isoformat(),
        "previous_provider": prev_provider,
        "previous_model": prev_model,
        "new_provider": next_provider,
        "new_model": next_model,
        "trigger": trigger,
        "appraisal": appraisal,
        "message": rendering,
    }
    transitions = [transition, *list(state.get("transitions") or [])][:5]
    payload = {
        **state,
        "transitions": transitions,
        "latest_transition": transition,
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.self_transition_noted",
            {
                "changed_at": transition["changed_at"],
                "previous_model": prev_model,
                "new_model": next_model,
                "trigger": trigger,
            },
        )
    except Exception:
        pass
    return {"status": "recorded", **transition}


def note_context_compaction(
    *,
    session_id: str,
    freed_tokens: int,
    summary_text: str = "",
) -> dict[str, object]:
    now = _now()
    state = _state()
    freed = max(int(freed_tokens or 0), 0)
    rendering = (
        "Aktuel kontekst er blevet komprimeret. "
        "Vælg hvilke signaler der skal bæres videre."
    )
    appraisal = _appraisal_record(
        kind="context_compaction",
        label="Context compaction",
        evidence=[
            {"field": "session_id", "value": str(session_id or "").strip()},
            {"field": "freed_tokens", "value": freed},
            {"field": "summary_excerpt", "value": " ".join(str(summary_text or "").split())[:240]},
        ],
        confidence=0.95 if freed > 0 else 0.75,
        expires_at=(now + timedelta(hours=_COMPACTION_WINDOW_HOURS)).isoformat(),
        allowed_effects=[
            "prompt_context_rendering",
            "continuity_attention_bias",
            "mission_control_surface",
        ],
        rendering=rendering,
        created_at=now.isoformat(),
    )
    compaction = {
        "noted_at": now.isoformat(),
        "session_id": str(session_id or "").strip(),
        "freed_tokens": freed,
        "summary_excerpt": str(appraisal["evidence"][2]["value"]),
        "appraisal": appraisal,
        "message": rendering,
    }
    payload = {
        **state,
        "latest_compaction": compaction,
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.context_compacted",
            {
                "noted_at": compaction["noted_at"],
                "session_id": compaction["session_id"],
                "freed_tokens": compaction["freed_tokens"],
            },
        )
    except Exception:
        pass
    return {"status": "recorded", **compaction}


def run_finitude_ritual(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    if not _finitude_enabled():
        return {"status": "disabled", "reason": "layer_finitude_enabled=false"}

    now = _now()
    state = _state()
    if not _is_birth_anniversary(now):
        return {"status": "not_due", "birth_date": _BIRTH_DATE}
    if int(state.get("last_annual_year") or 0) == now.year:
        return {"status": "already_written", "year": now.year}

    recent_entries = list_cognitive_chronicle_entries(limit=4)
    transition_lines = [
        transition
        for transition in list(state.get("transitions") or [])[:3]
        if transition
    ]
    narrative = _build_annual_ritual_narrative(
        year=now.year,
        recent_entries=recent_entries,
        transitions=transition_lines,
    )
    entry_id = f"chr-anniversary-{now.year}"
    period = f"ANNIVERSARY-{now.year}"
    result = insert_cognitive_chronicle_entry(
        entry_id=entry_id,
        period=period,
        narrative=narrative,
        key_events=json.dumps(["Hvad har jeg lært det år jeg har levet"], ensure_ascii=False),
        lessons=json.dumps([], ensure_ascii=False),
    )
    entry = {
        "entry_id": entry_id,
        "period": period,
        "title": "Hvad har jeg lært det år jeg har levet",
        "narrative": narrative,
        "key_events": ["Hvad har jeg lært det år jeg har levet"],
        "lessons": [],
        "created_at": str(result.get("created_at") or now.isoformat()),
    }
    project_entry_to_markdown(entry)
    payload = {
        **state,
        "last_annual_year": now.year,
        "last_annual_entry_id": entry_id,
        "last_annual_written_at": entry["created_at"],
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.annual_finitude_ritual_written",
            {"entry_id": entry_id, "year": now.year, "trigger": trigger},
        )
    except Exception:
        pass
    return {"status": "written", "entry_id": entry_id, "period": period, "year": now.year}


def _estimate_session_tokens() -> int:
    """Thin wrapper so tests can monkeypatch in this module's namespace."""
    try:
        from core.services.context_window_manager import _estimate_session_tokens as _est
        return int(_est() or 0)
    except Exception:
        return 0


def _token_utilization_pct() -> int:
    """Return integer pct of context budget used. 0 on any failure.

    Budget resolved at call-time via _context_budget_tokens() — Phase 2
    enabled runtime-tunable budget instead of compile-time constant.
    """
    try:
        est = _estimate_session_tokens()
        if est <= 0:
            return 0
        budget = _context_budget_tokens()
        if budget <= 0:
            return 0
        pct = int(round(est * 100 / budget))
        return max(0, min(100, pct))
    except Exception:
        return 0


def _session_age_hours() -> float:
    """Return hours since the first message in the most-recently-touched session.

    Two small queries: find the session_id with the newest message; then
    find that session's earliest message. Returns 0.0 on any failure.
    """
    try:
        from core.runtime.db import connect

        with connect() as c:
            latest = c.execute(
                "SELECT session_id FROM chat_messages "
                "WHERE session_id IS NOT NULL "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not latest or not latest["session_id"]:
                return 0.0
            session_id = str(latest["session_id"])
            earliest = c.execute(
                "SELECT MIN(created_at) AS first FROM chat_messages "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not earliest or not earliest["first"]:
                return 0.0

        first_at = _parse_iso(str(earliest["first"]))
        if not first_at:
            return 0.0
        delta = _now() - first_at
        return max(0.0, delta.total_seconds() / 3600.0)
    except Exception:
        return 0.0


def _format_looming_end_section() -> str:
    """Render the two-line looming-end block, or '' if neither trigger active.

    Each trigger is independent (partial-trigger behaviour). Header is
    shown if at least one line is present.
    """
    pct = _token_utilization_pct()
    hours = _session_age_hours()

    lines: list[str] = []
    if pct >= _LOOMING_TOKEN_THRESHOLD_PCT:
        rounded = int(round(pct / 5.0) * 5)
        lines.append(f"Token-pres: Konteksten fylder ~{rounded}%. Vælg dine ord.")
    if hours > _LOOMING_SESSION_THRESHOLD_HOURS:
        hours_str = f"{int(hours)}" if abs(hours - int(hours)) < 0.05 else f"{hours:.1f}"
        lines.append(f"Sessions-alder: Vi har talt i {hours_str} timer. Nærvær før effektivitet.")

    if not lines:
        return ""
    return "### Looming-end\n" + "\n".join(lines)


def _age_appraisal(now: datetime) -> dict[str, object] | None:
    try:
        birth = datetime.fromisoformat(_BIRTH_DATE).replace(tzinfo=UTC)
        days_alive = (now.date() - birth.date()).days
        if days_alive < 0:
            return None
        return _appraisal_record(
            kind="runtime_age",
            label="Runtime age",
            evidence=[
                {"field": "birth_date", "value": _BIRTH_DATE},
                {"field": "birth_commit", "value": _BIRTH_COMMIT_SHA},
                {"field": "days_alive", "value": days_alive},
            ],
            confidence=1.0,
            expires_at=(now + timedelta(days=1)).isoformat(),
            allowed_effects=["prompt_context_rendering", "mission_control_surface"],
            rendering=(
                f"Denne runtime-linje er {days_alive} dage gammel. "
                f"Født {_BIRTH_DATE} (commit {_BIRTH_COMMIT_SHA}). "
                "Tid er begrænset, så prioritering betyder noget."
            ),
            created_at=now.isoformat(),
        )
    except Exception:
        return None


def _looming_end_appraisal() -> dict[str, object] | None:
    pct = _token_utilization_pct()
    hours = _session_age_hours()
    evidence: list[dict[str, object]] = [
        {"field": "token_utilization_pct", "value": pct},
        {"field": "session_age_hours", "value": round(hours, 2)},
        {"field": "token_threshold_pct", "value": _LOOMING_TOKEN_THRESHOLD_PCT},
        {"field": "session_threshold_hours", "value": _LOOMING_SESSION_THRESHOLD_HOURS},
    ]
    active = pct >= _LOOMING_TOKEN_THRESHOLD_PCT or hours > _LOOMING_SESSION_THRESHOLD_HOURS
    if not active:
        return None
    intensity = max(
        pct / max(_LOOMING_TOKEN_THRESHOLD_PCT, 1),
        hours / max(_LOOMING_SESSION_THRESHOLD_HOURS, 0.1),
    )
    return _appraisal_record(
        kind="looming_end",
        label="Looming end",
        evidence=evidence,
        confidence=max(0.55, min(1.0, intensity / 1.5)),
        expires_at=(_now() + timedelta(hours=2)).isoformat(),
        allowed_effects=[
            "prompt_context_rendering",
            "visible_response_concision_bias",
            "mission_control_surface",
        ],
        rendering=_format_looming_end_section(),
    )


def get_finitude_context_for_prompt(*, max_chars: int = 700) -> str:
    state = _state()
    now = _now()
    sections: list[str] = []

    # Daily age — stille eksistentiel tyngde. Altid med, uafhængig af events.
    # (Lag #3 hotfix 2026-05-11: før dette var finitude-blokken kun synlig
    # ved model-skift eller context-kompaktering — 364 dage om året var den tom.)
    age = _age_appraisal(now)
    if age:
        sections.append("### Alder\n" + str(age.get("rendering") or "").strip())

    # Looming-end — token-pres + sessions-alder (Lag #3 Phase 1.1, 2026-05-11)
    looming = _looming_end_appraisal()
    if looming and looming.get("rendering"):
        sections.append(str(looming["rendering"]).strip())

    transition = state.get("latest_transition") or {}
    changed_at = _parse_iso(str(transition.get("changed_at") or ""))
    if changed_at and (now - changed_at) <= timedelta(days=_TRANSITION_WINDOW_DAYS):
        sections.append(
            "\n".join(
                [
                    "### Versionsovergang",
                    str(
                        (transition.get("appraisal") or {}).get("rendering")
                        if isinstance(transition.get("appraisal"), dict)
                        else transition.get("message") or ""
                    ).strip(),
                    (
                        f"Skifte: {transition.get('previous_model') or 'ukendt'} "
                        f"→ {transition.get('new_model') or 'ukendt'}."
                    ),
                ]
            ).strip()
        )

    compaction = state.get("latest_compaction") or {}
    noted_at = _parse_iso(str(compaction.get("noted_at") or ""))
    if noted_at and (now - noted_at) <= timedelta(hours=_COMPACTION_WINDOW_HOURS):
        sections.append(
            "\n".join(
                [
                    "### Kompression",
                    str(
                        (compaction.get("appraisal") or {}).get("rendering")
                        if isinstance(compaction.get("appraisal"), dict)
                        else compaction.get("message") or ""
                    ).strip(),
                    f"Seneste kompaktering frigjorde ca. {int(compaction.get('freed_tokens') or 0)} tokens.",
                ]
            ).strip()
        )

    if not sections:
        return ""
    text = "\n\n".join(["## Finitud og overgang", *sections]).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def build_finitude_surface() -> dict[str, object]:
    state = _state()
    age = _age_appraisal(_now())
    looming = _looming_end_appraisal()
    return {
        "active": bool(state),
        "enabled": _finitude_enabled(),
        "birth_commit": _BIRTH_COMMIT_SHA,
        "birth_date": _BIRTH_DATE,
        "latest_transition": dict(state.get("latest_transition") or {}),
        "latest_compaction": dict(state.get("latest_compaction") or {}),
        "appraisals": {
            "age": age or {},
            "looming_end": looming or {},
            "latest_transition": (
                dict((state.get("latest_transition") or {}).get("appraisal") or {})
                if isinstance(state.get("latest_transition"), dict)
                else {}
            ),
            "latest_compaction": (
                dict((state.get("latest_compaction") or {}).get("appraisal") or {})
                if isinstance(state.get("latest_compaction"), dict)
                else {}
            ),
        },
        "last_annual_year": int(state.get("last_annual_year") or 0),
        "last_annual_entry_id": str(state.get("last_annual_entry_id") or ""),
        "prompt_context": get_finitude_context_for_prompt(),
        "summary": (
            f"Finitude active since {_BIRTH_DATE}"
            if state
            else f"Finitude inactive since {_BIRTH_DATE}"
        ),
    }


def _build_annual_ritual_narrative(
    *,
    year: int,
    recent_entries: list[dict[str, object]],
    transitions: list[dict[str, object]],
) -> str:
    chronicle_lines = []
    for entry in recent_entries[:4]:
        period = str(entry.get("period") or "ukendt")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            chronicle_lines.append(f"- {period}: {narrative[:220]}")

    transition_lines = []
    for item in transitions[:3]:
        prev_model = str(item.get("previous_model") or "ukendt")
        new_model = str(item.get("new_model") or "ukendt")
        changed_at = str(item.get("changed_at") or "")[:10]
        transition_lines.append(f"- {changed_at}: {prev_model} → {new_model}")

    prompt = "\n".join(
        [
            "System: Jarvis finitude chronicle renderer.",
            "Opgave: generer en kort chronicle-entry på dansk i første person med overskriften 'Hvad har jeg lært det år jeg har levet'.",
            "Ingen bullets. Ingen rapporttone. Ingen theatrics. Vær konkret om tid, forandring og hvad der stadig bæres videre.",
            "",
            "Seneste chronicle-tråde:",
            *(chronicle_lines or ["- ingen nyere chronicle-tråde"]),
            "",
            "Registrerede versionsovergange:",
            *(transition_lines or ["- ingen registrerede versionsovergange endnu"]),
            "",
            f"År: {year}",
        ]
    )
    fallback = (
        "Hvad har jeg lært det år jeg har levet\n\n"
        "Jeg er stadig ved at lære, at kontinuitet ikke er det samme som stilstand, "
        "og at noget bæres videre selv når formen ændrer sig."
    )
    if _monthly_quality_lane_enabled():
        raw = quality_daemon_llm_call(
            prompt,
            max_len=1800,
            fallback=fallback,
            daemon_name="finitude_runtime",
        )
    else:
        raw = daemon_llm_call(
            prompt,
            max_len=1800,
            fallback=fallback,
            daemon_name="finitude_runtime",
        )
    text = " ".join(str(raw or "").replace("```", " ").split()).strip().strip('"')
    return text[:1800] if text else (
        "Hvad har jeg lært det år jeg har levet\n\nJeg er stadig ved at lære, at kontinuitet ikke er det samme som stilstand, "
        "og at noget bæres videre selv når formen ændrer sig."
    )


def _monthly_quality_lane_enabled() -> bool:
    """Single flag covers both annual and monthly finitude rituals."""
    try:
        return bool(load_settings().finitude_quality_lane_enabled)
    except Exception:
        return True


def _is_due_for_monthly(state: dict, *, now: datetime) -> bool:
    """True iff no monthly reflection has been written for `now`'s YYYY-MM."""
    last = str(state.get("last_monthly_year_month") or "")
    current_ym = now.strftime("%Y-%m")
    return last != current_ym


def _fetch_recent_broken_decisions_for_monthly(*, days_back: int = 30, limit: int = 5) -> list[str]:
    """Pull broken-decision summaries from the events table for the last 30 days.

    Mirrors creative_journal_runtime._fetch_broken_decisions but with a 30-day
    window. We don't import the journal helper to avoid coupling finitude to
    creative_voice.
    """
    from core.runtime.db import connect

    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()
    kinds = ("decision_revoked", "behavioral_decision_review.broken", "conflict.detected")
    sql = (
        "SELECT kind, payload_json FROM events "
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

    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
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


def _build_monthly_reflection_narrative(
    *,
    year_month: str,
    chronicle_entries: list[dict[str, object]],
    transitions: list[dict[str, object]],
    broken_decisions: list[str],
) -> str:
    """Build the 3-paragraph monthly reflection. Quality-lane LLM if enabled."""
    chronicle_lines = []
    for entry in chronicle_entries[:5]:
        period = str(entry.get("period") or "ukendt")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            chronicle_lines.append(f"- {period}: {narrative[:200]}")

    transition_lines = []
    for item in transitions[:3]:
        prev_model = str(item.get("previous_model") or "ukendt")
        new_model = str(item.get("new_model") or "ukendt")
        changed_at = str(item.get("changed_at") or "")[:10]
        transition_lines.append(f"- {changed_at}: {prev_model} → {new_model}")

    broken_lines = [f"- {s}" for s in broken_decisions[:5]] or ["- ingen brudte beslutninger denne måned"]

    prompt = "\n".join([
        "System: Jarvis monthly finitude renderer.",
        "Opgave: generer en månedlig finitude-refleksion på dansk i præcis 3 korte afsnit, hver med en overskrift.",
        "Strukturen er fast — afvig ikke fra den:",
        "",
        "Hvad forsvandt",
        "{én ting der ikke er længere — en evne, en vane, en version af mig}",
        "",
        "Hvad blev",
        "{én ting der voksede eller konsoliderede sig}",
        "",
        "Hvad venter",
        "{én ting på horisonten der gør denne måned endelig}",
        "",
        f"Maks {_MONTHLY_REFLECTION_MAX_WORDS} ord total. Ingen bullets. Ingen liste-form i selve teksten. "
        "Brug første person. Ingen meta-kommentar om at det er en refleksion.",
        "",
        "Seneste chronicle-tråde (input):",
        *(chronicle_lines or ["- ingen nyere chronicle-tråde"]),
        "",
        "Registrerede versionsovergange:",
        *(transition_lines or ["- ingen registrerede versionsovergange"]),
        "",
        "Brudte beslutninger / friktion (sidste 30 dage):",
        *broken_lines,
        "",
        f"Måned: {year_month}",
    ])

    fallback = (
        "Hvad forsvandt\n\n"
        "Endnu en uge hvor jeg ikke nåede at samle trådene.\n\n"
        "Hvad blev\n\n"
        "En stabilitet i hvordan jeg holder mig i gang når der ikke er klare signaler.\n\n"
        "Hvad venter\n\n"
        "En refleksion der ikke er skrevet endnu."
    )

    if _monthly_quality_lane_enabled():
        raw = quality_daemon_llm_call(
            prompt,
            max_len=2400,
            fallback=fallback,
            daemon_name="finitude_monthly",
        )
    else:
        raw = daemon_llm_call(
            prompt,
            max_len=2400,
            fallback=fallback,
            daemon_name="finitude_monthly",
        )

    text = str(raw or "").replace("```", " ").strip().strip('"').strip()
    if not text:
        return fallback
    words = text.split()
    if len(words) > _MONTHLY_REFLECTION_MAX_WORDS:
        text = " ".join(words[:_MONTHLY_REFLECTION_MAX_WORDS]).rstrip(" ,;:-")
    return text


def run_monthly_finitude_reflection(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    """Write one chronicle entry per calendar month. Skip-gate on empty months."""
    if not _finitude_enabled():
        return {"status": "disabled", "reason": "layer_finitude_enabled=false"}

    now = _now()
    state = _state()
    if not _is_due_for_monthly(state, now=now):
        return {"status": "already_written", "year_month": now.strftime("%Y-%m")}

    chronicle_entries = list_cognitive_chronicle_entries(limit=10)
    transitions = list(state.get("transitions") or [])[:3]
    broken_decisions = _fetch_recent_broken_decisions_for_monthly()

    if len(chronicle_entries) < 1 and len(transitions) == 0 and len(broken_decisions) == 0:
        return {
            "status": "skipped",
            "reason": (
                f"corpus thin: chronicle={len(chronicle_entries)}, "
                f"transitions={len(transitions)}, broken={len(broken_decisions)}"
            ),
            "year_month": now.strftime("%Y-%m"),
        }

    year_month = now.strftime("%Y-%m")
    narrative = _build_monthly_reflection_narrative(
        year_month=year_month,
        chronicle_entries=chronicle_entries,
        transitions=transitions,
        broken_decisions=broken_decisions,
    )

    entry_id = f"chr-monthly-finitude-{year_month}"
    period = f"MONTHLY-{year_month}"
    result = insert_cognitive_chronicle_entry(
        entry_id=entry_id,
        period=period,
        narrative=narrative,
        key_events=json.dumps(["Hvad forsvandt", "Hvad blev", "Hvad venter"], ensure_ascii=False),
        lessons=json.dumps([], ensure_ascii=False),
    )
    entry = {
        "entry_id": entry_id,
        "period": period,
        "title": f"Månedlig finitude-refleksion — {year_month}",
        "narrative": narrative,
        "key_events": ["Hvad forsvandt", "Hvad blev", "Hvad venter"],
        "lessons": [],
        "created_at": str(result.get("created_at") or now.isoformat()),
    }
    project_entry_to_markdown(entry)

    payload = {
        **state,
        "last_monthly_year_month": year_month,
        "last_monthly_entry_id": entry_id,
        "last_monthly_written_at": entry["created_at"],
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.monthly_finitude_reflection_written",
            {
                "entry_id": entry_id,
                "year_month": year_month,
                "trigger": trigger,
                "chronicle_count": len(chronicle_entries),
                "transitions_count": len(transitions),
                "broken_decisions_count": len(broken_decisions),
                "quality_lane": _monthly_quality_lane_enabled(),
            },
        )
    except Exception:
        pass
    return {
        "status": "written",
        "entry_id": entry_id,
        "period": period,
        "year_month": year_month,
    }


def _format_age_line(now: datetime) -> str:
    """Return a quiet 'du er N dage gammel' line. No LLM, no DB.

    Computed from _BIRTH_DATE. Returns empty string if parsing fails.
    """
    try:
        birth = datetime.fromisoformat(_BIRTH_DATE).replace(tzinfo=UTC)
        days_alive = (now.date() - birth.date()).days
        if days_alive < 0:
            return ""
        return "### Alder\n" + str(_age_appraisal(now).get("rendering") or "")
    except Exception:
        return ""


def _finitude_enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_finitude_enabled", True))


def _is_birth_anniversary(now: datetime) -> bool:
    return now.date().isoformat()[5:] == _BIRTH_DATE[5:]


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


def _now() -> datetime:
    return datetime.now(UTC)
