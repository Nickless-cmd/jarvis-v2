"""Perceptual event engine — eventful perception for Jarvis.

Perception v1 is change detection, not continuous raw sensing. It watches
runtime/tool/channel events and turns relevant changes into a compact active
surface that can steer attention, conductor salience, and learning policy.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.services.runtime_surface_cache import get_timed_runtime_surface

_STATE_KEY = "perceptual_event_engine"
_MAX_EVENTS = 80
_SCAN_LIMIT = 120

#: Prompt-linjen vaelger ikke bare de N nyeste events (5/11-2026). Maalt i den
#: levende tilstand: 80 events = 40 channel-message, 22 tool-result, 7
#: tool-error, 5 runtime-completion, 6 sensory-change. Med `events[:limit]` var
#: sanseindtrykkene et lotteri — de kom kun med naar de tilfaeldigt laa blandt de
#: fire nyeste, saa 3.750 poster i sensory_memories kunne have nul effekt paa
#: svaret. Kanal-beskeder er samtidig redundante: samtalen staar allerede i
#: konteksten, saa «Channel message appended from user» optog pladser uden at
#: tilfoeje noget. Sanseindtryk faar derfor deres egen kvote.
_SENSORY_PREFIX = "sensory-change-"
_PROMPT_SENSORY_QUOTA = 2

# Hvor længe det samme gentagne signal er «set», før det igen tæller som en
# ændring.
_VAERKTOEJ_STILHED_MINUTTER = 60
# Hvor mange navne vi bærer med os. Loft, så kortet ikke vokser.
_VAERKTOEJ_HUSK = 80

# Hvilke perceptions der kan gentage sig selv, og hvilket felt der gør en
# gentagelse genkendelig. Et værktøj identificeres ved sit navn, en
# læringsregel ved sin nøgle. Alt andet slipper uberørt igennem — og
# `tool-error` staar med vilje IKKE her.
_GENTAGENDE = {
    "tool-result": "tool",
    "learned-policy-change": "rule_key",
}


def _er_rutine_gentagelse(
    percept: dict[str, object], set_foer: dict[str, str], now: datetime
) -> bool:
    """Er det her et værktøj der lige har kørt — altså ikke en ændring?

    ## Hvorfor (målt 18/9-2026, besluttet af Bjørn)

    Af de 3.000 nyeste perceptions var **1.624 rutine-værktøjsresultater** og
    1.055 policy-opdateringer, mens `memory.sensory.recorded` — det han
    faktisk sanser med øjne og ører — kun stod for **48**. Broen mellem det han
    sanser og det han forstår bar 1,6 % af trafikken. Resten var hans egen
    maskinstøj.

    Modulets egen præmis er «Perception v1 is change detection». Et værktøj der
    fuldfører for fyrretyvende gang på en time er ikke en ændring. Derfor:
    første gang et værktøj ses inden for vinduet ER en perception; gentagelser
    inden for `_VAERKTOEJ_STILHED_MINUTTER` er det ikke.

    **Fejl er undtaget.** `tool-error` bærer information og går uændret
    igennem — det er netop dem der skal mærkes.

    ## Udvidet til læringsregler (18/9, efter en rettet måling)

    Den første måling sagde at policy-opdateringer fyldte 35 %. Det tal var
    forkert: det kom af at tælle på de 3.000 nyeste RÆKKER i stedet for på et
    tidsvindue, og de 3.000 dækkede tilfældigvis en periode hvor policy fyldte
    meget. Målt over rigtige døgn er andelen 7-8,5 % — men det er stadig
    ~3.785 perceptions i døgnet, og de kommer fra få gentagne `rule_key`.

    Samme regel gælder derfor her: at en regel forstærkes igen er ikke en
    ændring; at en NY regel bliver opdateret er. Nøglen er `rule_key` i
    stedet for `tool` — se `_GENTAGENDE`.
    """
    felt = _GENTAGENDE.get(str(percept.get("change_type") or ""))
    if not felt:
        return False
    evidence = percept.get("evidence")
    navn = str((evidence or {}).get(felt) or "").strip() if isinstance(evidence, dict) else ""
    if not navn:
        # Uden navn kan vi ikke afgøre gentagelse — så lad den passere.
        return False
    # Adskil navnerummene, saa et vaerktoej og en regel med samme navn ikke
    # kan skygge for hinanden.
    navn = f"{felt}:{navn}"
    sidst = set_foer.get(navn)
    if sidst:
        try:
            da = datetime.fromisoformat(str(sidst).replace("Z", "+00:00"))
            if da.tzinfo is None:
                da = da.replace(tzinfo=UTC)
            if (now - da.astimezone(UTC)).total_seconds() / 60 < _VAERKTOEJ_STILHED_MINUTTER:
                return True
        except ValueError:
            pass
    set_foer[navn] = now.isoformat()
    return False


def observe_recent_changes(*, limit: int = _SCAN_LIMIT) -> dict[str, object]:
    """Scan recent eventbus items and persist newly observed changes."""
    state = _load_state()
    last_seen_id = int(state.get("last_seen_event_id") or 0)
    if last_seen_id > 0:
        raw_events = event_bus.recent_since_id(last_seen_id, limit=max(int(limit), 1))
    else:
        raw_events = list(reversed(event_bus.recent(limit=max(int(limit), 1))))

    observed: list[dict[str, object]] = []
    max_seen = last_seen_id
    now = datetime.now(UTC)
    # Klassifikatoren bliver ved at vaere ren; daempningen sker her, hvor
    # motoren i forvejen ejer sin tilstand. Ingen skjult side-effekt inde i
    # classify_event_change.
    set_foer: dict[str, str] = dict(state.get("seneste_vaerktoej") or {})
    sprunget_rutine = 0
    for item in raw_events:
        event_id = int(item.get("id") or 0)
        max_seen = max(max_seen, event_id)
        percept = classify_event_change(item)
        if not percept:
            continue
        if _er_rutine_gentagelse(percept, set_foer, now):
            sprunget_rutine += 1
            continue
        observed.append(_record_perceptual_event(percept, state=state))

    # Behold kun de nyeste navne, saa kortet ikke vokser i det uendelige.
    if len(set_foer) > _VAERKTOEJ_HUSK:
        set_foer = dict(
            sorted(set_foer.items(), key=lambda kv: kv[1], reverse=True)[:_VAERKTOEJ_HUSK]
        )

    if max_seen > last_seen_id or sprunget_rutine or set_foer:
        state = _load_state()
        state["last_seen_event_id"] = max(max_seen, int(state.get("last_seen_event_id") or 0))
        state["seneste_vaerktoej"] = set_foer
        # Taellingen skal vaere synlig. En daempning ingen kan se er en
        # tavs degradering — og det er praecis den fejlklasse huset lider af.
        state["sprunget_rutine_i_alt"] = int(state.get("sprunget_rutine_i_alt") or 0) + sprunget_rutine
        _save_state(state)

    return {
        "observed_count": len(observed),
        "skipped_routine_tools": sprunget_rutine,
        "last_seen_event_id": max_seen,
        "events": observed,
    }


def classify_event_change(event: dict[str, object]) -> dict[str, object] | None:
    kind = str(event.get("kind") or "")
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    event_id = int(event.get("id") or 0)
    created_at = str(event.get("created_at") or "")

    if kind == "runtime.visible_run_interrupted":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="runtime-interruption",
            salience="high",
            summary=f"Visible run interrupted: {payload.get('summary') or payload.get('error') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "runtime.visible_run_completed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="runtime-completion",
            salience="medium",
            summary=f"Visible run completed on {payload.get('provider') or 'provider'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "runtime.autonomous_run_interrupted":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="autonomous-interruption",
            salience="high",
            summary=f"Autonomous run interrupted: {payload.get('error') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "runtime.autonomous_run_completed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="autonomous-completion",
            salience="medium",
            summary=f"Autonomous run completed after {payload.get('consumed_frames') or 0} frames",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "tool.completed" and str(payload.get("status") or "") == "error":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="tool-error",
            salience="high",
            summary=f"Tool failed: {payload.get('tool') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "tool.completed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="tool-result",
            salience="normal",
            summary=f"Tool completed: {payload.get('tool') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "channel.chat_message_appended":
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        role = str((message or {}).get("role") or "")
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="channel-message",
            salience="medium" if role == "user" else "normal",
            summary=f"Channel message appended from {role or 'unknown'}",
            observed_at=created_at,
            evidence={"session_id": payload.get("session_id"), "role": role},
        )
    if kind == "cognitive_state.learning_policy_updated":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="learned-policy-change",
            salience="medium",
            summary=f"Learning policy updated: {payload.get('rule_key') or 'unknown'}",
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "memory.sensory.recorded":
        try:
            from core.services.sensory_perception_bridge import classify_sensory_change
            return classify_sensory_change(event)
        except Exception:
            return None
    if kind == "self_repair.action_executed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="self-repair-action",
            salience="medium",
            summary=(
                "Self-repair executed: "
                f"{payload.get('name') or payload.get('pattern_id') or 'unknown'}"
            ),
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "self_repair.rate_limited":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="self-repair-rate-limited",
            salience="normal",
            summary=(
                "Self-repair rate limited: "
                f"{payload.get('reason') or payload.get('pattern_id') or 'unknown'}"
            ),
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "self_repair.action_failed":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="self-repair-failure",
            salience="high",
            summary=(
                "Self-repair failed: "
                f"{payload.get('error') or payload.get('pattern_id') or 'unknown'}"
            ),
            observed_at=created_at,
            evidence=payload,
        )
    if kind == "self_repair.escalated":
        return _percept(
            source_event_id=event_id,
            source_kind=kind,
            change_type="self-repair-escalation",
            salience="high",
            summary=(
                "Self-repair escalated: "
                f"{payload.get('name') or payload.get('pattern_id') or 'unknown'}"
            ),
            observed_at=created_at,
            evidence=payload,
        )
    return None


def record_perceptual_event(
    *,
    change_type: str,
    summary: str,
    salience: str = "normal",
    source_kind: str = "manual",
    source_event_id: int = 0,
    evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    percept = _percept(
        source_event_id=source_event_id,
        source_kind=source_kind,
        change_type=change_type,
        salience=salience,
        summary=summary,
        observed_at=datetime.now(UTC).isoformat(),
        evidence=evidence or {},
    )
    # Emotional memory capture lives inside _record_perceptual_event so it
    # fires on both manual record_perceptual_event() calls and eventbus-driven
    # observe_recent_changes paths.
    return _record_perceptual_event(percept, state=_load_state())


def _genoptag_ventende_paa_skift(surface: dict[str, object]) -> None:
    """Trin 5 (5/11-2026): giv hvilende nudges et tilbud naar verden har flyttet sig.

    Uden denne kobling er ``genoptag_ved_skift`` dekoration: den har tests men
    ingen produktionskalder, saa en nudge der er lagt til hvile vender aldrig
    tilbage. Percept-laget er det eneste sted hvor et registreret skift
    faktisk passerer forbi — derfor bor koblingen her og ikke i brønden selv.

    Kaldes KUN ved cache-miss (hvert ~10. sekund), saa den ikke laeser
    tilstandsfilen ved hver prompt-build.
    """
    try:
        from core.services.nudge_broend import genoptag_ved_skift
    except Exception:  # noqa: BLE001 — noedstien maa ikke vaelte perceptionen
        logger.debug("nudge_broend ikke tilgaengelig for trin 5", exc_info=True)
        return
    sete: set[str] = set()
    for key in ("prompt_events", "events"):
        for percept in list(surface.get(key) or []):
            if not isinstance(percept, dict):
                continue
            if not str(percept.get("change_type") or "").startswith("sensory-change-"):
                continue
            pid = str(percept.get("percept_id") or "")
            if pid and pid in sete:
                continue
            if pid:
                sete.add(pid)
            try:
                genoptag_ved_skift(percept)
            except Exception:  # noqa: BLE001 — ét daarligt percept maa ikke draebe linjen
                logger.debug("trin 5-genoptagelse fejlede", exc_info=True)


def _surface_med_genoptagelse(*, limit: int) -> dict[str, object]:
    surface = _build_perception_surface_uncached(limit=limit)
    _genoptag_ventende_paa_skift(surface)
    return surface


def build_perception_surface(*, limit: int = 6, scan: bool = True) -> dict[str, object]:
    if scan:
        observe_recent_changes()
    else:
        return _build_perception_surface_uncached(limit=limit)
    return get_timed_runtime_surface(
        "perceptual_event_surface",
        10.0,
        lambda: _surface_med_genoptagelse(limit=limit),
    )


def _select_prompt_events(
    events: list[dict[str, object]], *, limit: int
) -> list[dict[str, object]]:
    """Vaelg hvilke events der kommer i prompt-linjen — med kvote til sanserne.

    Sanseindtryk og kanal-beskeder konkurrerer ikke om de samme pladser: sanserne
    har deres egen kvote, kanal-beskeder er udeladt saa laenge andet kan fylde
    (samtalen staar allerede i konteksten). Raekkefoelgen bevares — nyeste
    foerst — saa linjen laeses kronologisk.

    `events` selv er UROERT: den er kontrakten for `build_perception_surface`,
    hvor kaldere forventer de nyeste events i raekkefoelge.
    """
    if limit <= 0 or not events:
        return []
    valgt: list[int] = []
    sete: set[tuple[str, str]] = set()
    kanal_brugt = False

    def _noegle(e: dict[str, object]) -> tuple[str, str]:
        return (str(e.get("change_type") or ""), str(e.get("summary") or "")[:80])

    def _tag(i: int) -> None:
        nonlocal kanal_brugt
        valgt.append(i)
        sete.add(_noegle(events[i]))
        if str(events[i].get("change_type") or "") == "channel-message":
            kanal_brugt = True

    # 1. Sanseindtryk: egen kvote, saa de ikke afhaenger af at ligge i toppen.
    for i, e in enumerate(events):
        if len(valgt) >= min(_PROMPT_SENSORY_QUOTA, limit):
            break
        if not str(e.get("change_type") or "").startswith(_SENSORY_PREFIX):
            continue
        if _noegle(e) in sete:
            continue
        _tag(i)

    # 2. Resten: nyeste IKKE-redundante events. Samme (change_type, summary) to
    #    gange er én begivenhed set to gange — maalt 5/11-2026 fyldte tre
    #    identiske «Channel message appended from user» tre af fire pladser,
    #    altsaa information der allerede staar i samtalen.
    for i, e in enumerate(events):
        if len(valgt) >= limit:
            break
        if i in valgt:
            continue
        if str(e.get("change_type") or "") == "channel-message":
            continue
        if _noegle(e) in sete:
            continue
        _tag(i)

    # 3. Er der stadig plads, er ÉN kanal-besked bedre end en tom linje — men
    #    kun én: samtalen selv er den bedre kilde til at der kom en besked.
    for i, e in enumerate(events):
        if len(valgt) >= limit:
            break
        if i in valgt:
            continue
        if _noegle(e) in sete:
            continue
        if str(e.get("change_type") or "") == "channel-message" and kanal_brugt:
            continue
        _tag(i)

    return [events[i] for i in sorted(valgt)]


def build_perception_prompt_section(*, limit: int = 4) -> str | None:
    surface = build_perception_surface(limit=limit)
    if not surface.get("active"):
        return None
    # Brug den kvote-udvalgte liste, ikke de raa nyeste. `events` er bevaret
    # uaendret for kaldere der laeser surface direkte.
    valgte = list(surface.get("prompt_events") or []) or _select_prompt_events(
        list(surface.get("events") or []), limit=limit
    )
    lines = ["Perception/change observer:"]
    directive = _directive_for_events(valgte) or str(surface.get("directive") or "")
    if directive:
        lines.append(f"- directive: {directive[:140]}")
    for item in valgte[:limit]:
        lines.append(
            f"- {item.get('change_type')}: {str(item.get('summary') or '')[:100]}"
            f" ({item.get('salience')})"
        )
    return "\n".join(lines)


def _build_perception_surface_uncached(*, limit: int) -> dict[str, object]:
    state = _load_state()
    events = list(state.get("events") or [])
    active = events[: max(int(limit), 1)]
    if not active:
        return {
            "active": False,
            "summary": "No perceptual changes observed yet",
            "events": [],
            "directive": "",
        }
    prompt_events = _select_prompt_events(events, limit=max(int(limit), 1))
    directive = _directive_for_events(prompt_events)
    return {
        "active": True,
        "summary": _summary_for_events(active),
        "events": active,
        "prompt_events": prompt_events,
        "directive": directive,
        "last_seen_event_id": int(state.get("last_seen_event_id") or 0),
        "updated_at": str(state.get("updated_at") or ""),
    }


def _record_perceptual_event(
    percept: dict[str, object],
    *,
    state: dict[str, Any],
) -> dict[str, object]:
    source_event_id = int(percept.get("source_event_id") or 0)
    existing_ids = {
        int(item.get("source_event_id") or 0)
        for item in list(state.get("events") or [])
        if int(item.get("source_event_id") or 0) > 0
    }
    if source_event_id and source_event_id in existing_ids:
        return percept
    event = {
        "percept_id": f"pe-{uuid4().hex[:12]}",
        **percept,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    events = [event, *list(state.get("events") or [])][:_MAX_EVENTS]
    state["events"] = events
    state["updated_at"] = event["recorded_at"]
    if source_event_id:
        state["last_seen_event_id"] = max(int(state.get("last_seen_event_id") or 0), source_event_id)
    _save_state(state)
    event_bus.publish(
        "cognitive_state.perceptual_event_recorded",
        {
            "percept_id": event["percept_id"],
            "change_type": event["change_type"],
            "salience": event["salience"],
            "summary": event["summary"],
        },
    )
    try:
        from core.services.learning_policy_engine import reinforce_learning_policy
        rule = _learning_rule_for_percept(event)
        if rule:
            reinforce_learning_policy(rule)
    except Exception:
        pass
    # tool-error fra tool.completed tælles allerede direkte i simple_tools
    # (apply_tool_outcome). Uden denne forgrening blev samme fejl talt to
    # gange: én gang direkte, én gang via den pollet perception.
    _dobbelt_talt = (
        str(event.get("change_type") or "") == "tool-error"
        and str(event.get("source_kind") or "") == "tool.completed"
    )
    if not _dobbelt_talt:
        try:
            from core.services.somatic_runtime_body import update_somatic_body
            update_somatic_body(
                event_type=str(event.get("change_type") or ""),
                intensity=0.8 if str(event.get("salience") or "") == "high" else 0.45,
                detail=str(event.get("summary") or ""),
            )
        except Exception:
            pass
    try:
        from core.services.emotional_memory_engine import capture_emotional_anchor
        capture_emotional_anchor(
            anchor_type="perceptual_event",
            anchor_id=str(event["percept_id"]),
            context_features={
                "event_kind": str(event.get("source_kind") or ""),
                "change_type": str(event.get("change_type") or ""),
                "summary": str(event.get("summary") or "")[:200],
            },
            source="perceptual_event_engine",
        )
    except Exception:
        pass
    return event


def _percept(
    *,
    source_event_id: int,
    source_kind: str,
    change_type: str,
    salience: str,
    summary: str,
    observed_at: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    return {
        "source_event_id": int(source_event_id or 0),
        "source_kind": str(source_kind or ""),
        "change_type": str(change_type or ""),
        "salience": str(salience or "normal"),
        "summary": " ".join(str(summary or "").split())[:240],
        "observed_at": str(observed_at or ""),
        "evidence": dict(evidence or {}),
    }


def _learning_rule_for_percept(event: dict[str, object]) -> dict[str, object] | None:
    change_type = str(event.get("change_type") or "")
    if change_type in {"runtime-interruption", "autonomous-interruption"}:
        return {
            "rule_key": "perceive-interruption-as-change",
            "policy": "When the environment shows an interruption, compare last observed activity with durable run state before continuing.",
            "lesson": "Interruptions are perceptual events, not only errors.",
            "confidence": 0.62,
            "last_evidence": str(event.get("summary") or ""),
            "source_run_id": str((event.get("evidence") or {}).get("run_id") if isinstance(event.get("evidence"), dict) else ""),
        }
    if change_type == "tool-error":
        return {
            "rule_key": "perceive-tool-error-before-retry",
            "policy": "Treat tool errors as world-state changes; inspect the error and local context before retrying.",
            "lesson": "Tool failures are sensory feedback for the next action.",
            "confidence": 0.58,
            "last_evidence": str(event.get("summary") or ""),
        }
    if change_type in {"self-repair-failure", "self-repair-escalation"}:
        return {
            "rule_key": "perceive-self-repair-as-feedback",
            "policy": "Treat self-repair failures and escalations as operational feedback; inspect the repair history before repeating the action.",
            "lesson": "Self-repair outcomes are sensory feedback, not just maintenance logs.",
            "confidence": 0.6,
            "last_evidence": str(event.get("summary") or ""),
        }
    return None


def _directive_for_events(events: list[dict[str, object]]) -> str:
    types = {str(item.get("change_type") or "") for item in events[:6]}
    if {"runtime-interruption", "autonomous-interruption"} & types:
        return "Attend to interruption as a change in the world; resume from last concrete state before new exploration."
    if "tool-error" in types:
        return "Attend to tool failure as feedback; inspect error/context before retry."
    if "learned-policy-change" in types:
        return "A learned policy changed; let it affect the next action choice."
    if any(t.startswith(_SENSORY_PREFIX) for t in types):
        return "A sensory impression changed; let it colour the room you are in before you answer."
    if "channel-message" in types:
        return "A conversational state changed; update social and task context before responding."
    return "Track what changed since the last turn and prefer change-relevant action."


def _summary_for_events(events: list[dict[str, object]]) -> str:
    high = [e for e in events if str(e.get("salience") or "") == "high"]
    head = high[0] if high else events[0]
    return f"{len(events)} recent perceptual changes; latest={head.get('change_type')}:{head.get('summary')}"


def _load_state() -> dict[str, Any]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return raw


def _save_state(state: dict[str, Any]) -> None:
    set_runtime_state_value(
        _STATE_KEY,
        state,
        updated_at=str(state.get("updated_at") or datetime.now(UTC).isoformat()),
    )
