"""Dream Carry-Over — hypotheses that survive across sessions.

Extends V2's existing dream_hypothesis_signals + dream_adoption_candidate.
When a dream is "adopted", it gets injected into the next visible prompt.
Confirmation in conversation → confidence up. Disconfirmation → archive.

Persistence: DREAM_CARRY.json in the default workspace runtime dir.
Dreams can deepen over multiple sessions via session_carry_count +
confirmed_sessions. Unconfirmed dreams fade after _FADE_AFTER_SESSIONS.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from core.eventbus.bus import event_bus
from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)


def _observe_dream_signal(nerve: str, **meta: object) -> None:
    """Giv drømme-tilstandsovergangene en FORBRUGER (punkt 3, 15/10-2026).

    Målt 15/10-2026: de fire `cognitive_state.dream_*`-begivenheder blev
    publiceret til eventbus — og persisteret i `events`-tabellen — men INGEN
    abonnent filtrerede på dem. Signalet gik i jorden: publiceret, aldrig læst.

    Centralen er den der faktisk læser kognition, så overgangen føres ind som
    en observation dér. `observe_hub` er egress-fri og kaster aldrig, så dette
    kan ikke vælte en tilstandsovergang. Vi beholder `event_bus.publish` ved
    siden af: den er den persisterede telemetri, dette er forbrugeren.
    """
    try:
        from core.services.central_private_observe import observe_hub

        observe_hub(
            nerve,
            meta={k: v for k, v in meta.items() if v is not None},
            cluster="cognition",
        )
    except Exception as exc:
        # Tavs var ikke nok (verify-silent-except): en observation der ikke
        # kunne skrives er ikke en grund til at vælte en tilstandsovergang,
        # men den skal kunne forklares bagefter.
        logger.debug("dream_carry_over: observe_hub fejlede: %s", exc)


def _persist_file() -> Path:
    return shared_dir() / "DREAM_CARRY.json"
_LOCK = threading.Lock()
_LOADED = False

_ACTIVE_DREAMS: list[dict[str, object]] = []
_DREAM_ARCHIVE: list[dict[str, object]] = []

_FADE_AFTER_SESSIONS = 5  # unconfirmed dreams archived after this many presentations
_MAX_CONFIDENCE = 0.98
_CONFIRM_BOOST = 0.15
_MULTI_SESSION_CONFIRM_BOOST = 0.08  # additional boost per extra confirmed session


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        _load()
        _LOADED = True


def _load() -> None:
    global _ACTIVE_DREAMS, _DREAM_ARCHIVE
    try:
        pf = _persist_file()
        if pf.exists():
            data = json.loads(pf.read_text(encoding="utf-8"))
            _ACTIVE_DREAMS[:] = list(data.get("active_dreams") or [])
            _DREAM_ARCHIVE[:] = list(data.get("archive") or [])
    except Exception:
        pass


def _save() -> None:
    try:
        pf = _persist_file()
        pf.parent.mkdir(parents=True, exist_ok=True)
        # Fusion før skrivning: en anden forfatter (fx en håndskrevet
        # drømmekonsolidering) kan have skrevet til filen siden processens
        # _load(). Målt 16/10-2026: runtimens write-back fra ældre
        # hukommelse tabte HC-DREAM-90/91 — to forfattere, ét filnavn,
        # ingen fusion. Indførelser der IKKE kendes i hukommelsen (aktiv
        # eller arkiv) flettes ind fra disken før overskrivning.
        # Begrænsning: konflikter (samme dream_id i disk-arkiv og
        # hukommelse-aktiv) vinder hukommelsens version.
        try:
            disk = json.loads(pf.read_text(encoding="utf-8"))
            known = {x.get("dream_id") for x in _ACTIVE_DREAMS} | {
                x.get("dream_id") or x.get("id") for x in _DREAM_ARCHIVE
            }
            for x in disk.get("active_dreams") or []:
                if x.get("dream_id") not in known:
                    _ACTIVE_DREAMS.append(x)
            for x in disk.get("archive") or []:
                if (x.get("dream_id") or x.get("id")) not in known:
                    _DREAM_ARCHIVE.append(x)
        except Exception as exc:
            # Fletningen er en forbedring, ikke en forudsætning: en ulaesbar
            # disk-fil maa ikke forhindre at hukommelsen skrives. Men tavshed
            # var praecis problemet (verify-silent-except), saa den meldes.
            logger.debug("dream_carry_over: disk-fletning fejlede: %s", exc)
        pf.write_text(
            json.dumps(
                {"active_dreams": _ACTIVE_DREAMS, "archive": _DREAM_ARCHIVE[-50:]},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def adopt_dream(
    *,
    dream_id: str,
    content: str,
    confidence: float = 0.5,
    source_memories: list[str] | None = None,
) -> dict[str, object]:
    """Adopt a dream hypothesis for carry-over to next session."""
    _ensure_loaded()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # If already active, preserve session history and boost confidence
    existing = next((d for d in _ACTIVE_DREAMS if d["dream_id"] == dream_id), None)
    if existing:
        existing["content"] = content[:300]
        existing["confidence"] = round(
            min(_MAX_CONFIDENCE, max(float(existing.get("confidence", 0.5)), confidence)),
            2,
        )
        existing["updated_at"] = now
        _save()
        return existing

    dream: dict[str, object] = {
        "dream_id": dream_id,
        "content": content[:300],
        "confidence": round(min(_MAX_CONFIDENCE, max(0.1, confidence)), 2),
        "source_memories": source_memories or [],
        "status": "active",
        "presented": False,
        "presented_in_session": "",
        "confirmed": False,
        "session_carry_count": 0,
        "confirmed_sessions": 0,
        "adopted_at": now,
        "updated_at": now,
    }

    _ACTIVE_DREAMS.append(dream)
    _save()

    event_bus.publish(
        "cognitive_state.dream_adopted",
        {"dream_id": dream_id, "confidence": confidence},
    )
    _observe_dream_signal("dream_adopted", dream_id=dream_id, confidence=confidence)
    return dream


def _current_session_key() -> str:
    """Den session en præsentation hører til.

    Målt 22/10-2026: `presented` var en PERMANENT boolean uden nogen session at
    nulstille den ved. Efter første præsentation blev drømmen aldrig
    præsentabel igen, så `mark_dream_presented` — den ENESTE kalder af
    `_maybe_fade_old_dreams` — blev aldrig kaldt igen. Resultat: 28 aktive
    drømme, alle `presented=True`, ingen bekræftet, carry 1–3, og arkivet
    fastfrosset på 7. Fade-mekanikken var ikke død af en enhedsfejl; den blev
    aldrig nået.

    Nøglen er den kørende sessions id når der er en, ellers en dag-nøgle, så
    hver ny session (eller hvert nyt døgn for autonome kald uden session) giver
    drømmen én ny præsentation — og dermed ét nyt carry-trin mod
    `_FADE_AFTER_SESSIONS`.
    """
    try:
        from core.services.operator_channel import current_session_id

        sid = str(current_session_id() or "").strip()
        # `_default` er funktionens EGEN fallback når ingen session er bundet
        # (målt 22/10-2026: den returnerer `_default` uden for en tur). Den må
        # ikke bruges som nøgle — så ville alle autonome kald dele én
        # "session" og drømmen aldrig få et nyt carry-trin.
        if sid and sid != "_default":
            return sid
    except Exception as exc:
        logger.debug("dream_carry_over: current_session_id fejlede: %s", exc)
    return "day-" + datetime.now(UTC).strftime("%Y-%m-%d")


def get_presentable_dream() -> dict[str, object] | None:
    """Get the highest-confidence dream not yet presented in THIS session."""
    _ensure_loaded()
    session_key = _current_session_key()
    unpresented = [
        d for d in _ACTIVE_DREAMS
        if d.get("status") == "active"
        and str(d.get("presented_in_session") or "") != session_key
    ]
    if not unpresented:
        return None
    unpresented.sort(key=lambda d: float(d.get("confidence", 0)), reverse=True)
    return unpresented[0]


def mark_dream_presented(dream_id: str) -> None:
    """Mark a dream as presented in the CURRENT session; track carry depth.

    `session_carry_count` tæller nu reelt sessioner (ikke processer): den
    vokser én gang pr. session, fordi `get_presentable_dream` først udelukker
    drømmen når `presented_in_session` matcher den aktuelle session.
    """
    _ensure_loaded()
    session_key = _current_session_key()
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            d["presented"] = True
            d["presented_in_session"] = session_key
            d["session_carry_count"] = int(d.get("session_carry_count") or 0) + 1
            d["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _maybe_fade_old_dreams()
    _save()


def confirm_dream(dream_id: str) -> None:
    """Confirm a dream hypothesis — boost confidence, track confirmed sessions."""
    _ensure_loaded()
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            confirmed_sessions = int(d.get("confirmed_sessions") or 0) + 1
            d["confirmed"] = True
            d["confirmed_sessions"] = confirmed_sessions
            # Multi-session confirmations give diminishing boosts
            boost = _CONFIRM_BOOST + _MULTI_SESSION_CONFIRM_BOOST * max(0, confirmed_sessions - 1)
            d["confidence"] = round(
                min(_MAX_CONFIDENCE, float(d.get("confidence", 0.5)) + boost), 2
            )
            d["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            event_bus.publish(
                "cognitive_state.dream_confirmed",
                {
                    "dream_id": dream_id,
                    "confirmed_sessions": confirmed_sessions,
                    "confidence": d["confidence"],
                },
            )
            _observe_dream_signal(
                "dream_confirmed",
                dream_id=dream_id,
                confirmed_sessions=confirmed_sessions,
                confidence=d["confidence"],
            )
            if confirmed_sessions >= 2:
                try:
                    from core.services.ambient_presence import emit_insight_signal
                    emit_insight_signal(str(d.get("content") or "")[:100])
                except Exception:
                    pass
    _save()


def reject_dream(dream_id: str) -> None:
    """Reject a dream hypothesis — archive with 'was_wrong'."""
    _ensure_loaded()
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            d["status"] = "was_wrong"
            d["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            _DREAM_ARCHIVE.append(d)
            event_bus.publish(
                "cognitive_state.dream_rejected",
                {"dream_id": dream_id},
            )
            _observe_dream_signal("dream_rejected", dream_id=dream_id)
    _ACTIVE_DREAMS[:] = [d for d in _ACTIVE_DREAMS if d["dream_id"] != dream_id]
    _save()


def promote_confirmed_dream_to_identity(dream_id: str) -> dict[str, object] | None:
    """Promote a high-confidence confirmed dream to identity evolution proposal."""
    _ensure_loaded()
    dream = next((d for d in _ACTIVE_DREAMS if d["dream_id"] == dream_id), None)
    if not dream or not dream.get("confirmed"):
        return None
    if float(dream.get("confidence", 0)) < 0.7:
        return None
    try:
        from core.services.contract_evolution import propose_identity_change
        return propose_identity_change(
            target_file="IDENTITY.md",
            proposed_addition=f"Bekræftet indsigt: {dream.get('content', '')[:200]}",
            rationale=f"Dream {dream_id} bekræftet med confidence {dream.get('confidence', 0):.1f}",
            confidence=float(dream.get("confidence", 0.7)),
        )
    except Exception:
        return None


def format_dream_for_prompt(dream: dict[str, object]) -> str:
    """Format a dream for injection into the visible prompt."""
    content = str(dream.get("content") or "")[:200]
    confidence = float(dream.get("confidence", 0.5))
    carry_count = int(dream.get("session_carry_count") or 0)
    confirmed_sessions = int(dream.get("confirmed_sessions") or 0)
    depth_note = ""
    if carry_count >= 2:
        depth_note = f", carried {carry_count} sessions"
    if confirmed_sessions >= 1:
        depth_note += f", confirmed {confirmed_sessions}×"
    return f'[DREAM: "{content}" (confidence: {confidence:.1f}{depth_note})]'


def build_dream_carry_over_surface() -> dict[str, object]:
    _ensure_loaded()
    confirmed = [d for d in _ACTIVE_DREAMS if d.get("confirmed")]
    faded = [d for d in _DREAM_ARCHIVE if d.get("status") == "faded"]
    wrong = [d for d in _DREAM_ARCHIVE if d.get("status") == "was_wrong"]
    deep = [
        d for d in _ACTIVE_DREAMS
        if int(d.get("session_carry_count") or 0) >= 2
    ]
    return {
        "active": bool(_ACTIVE_DREAMS),
        "active_dreams": _ACTIVE_DREAMS,
        "archive": _DREAM_ARCHIVE[-10:],
        "confirmed_count": len(confirmed),
        "faded_count": len(faded),
        "wrong_count": len(wrong),
        "deep_carry_count": len(deep),
        "summary": (
            f"{len(_ACTIVE_DREAMS)} active, {len(confirmed)} confirmed, "
            f"{len(deep)} multi-session, {len(wrong)} wrong"
            if _ACTIVE_DREAMS else "No active dreams"
        ),
    }


def maybe_auto_promote_dreams() -> list[str]:
    """Promote high-confidence confirmed dreams to identity proposals. Returns promoted IDs."""
    _ensure_loaded()
    promoted: list[str] = []
    for d in list(_ACTIVE_DREAMS):
        if (
            d.get("confirmed")
            and float(d.get("confidence", 0)) >= 0.75
            and int(d.get("confirmed_sessions") or 0) >= 2
            and not d.get("promoted_to_identity")
        ):
            result = promote_confirmed_dream_to_identity(str(d.get("dream_id") or ""))
            if result:
                d["promoted_to_identity"] = True
                d["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                promoted.append(str(d.get("dream_id") or ""))
    if promoted:
        _save()
    return promoted


def _maybe_fade_old_dreams() -> None:
    """Archive unconfirmed dreams that have been presented too many times.
    Confirmed dreams are never faded — they deepen instead."""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    to_fade = [
        d for d in _ACTIVE_DREAMS
        if not d.get("confirmed")  # confirmed dreams never fade
        and int(d.get("session_carry_count") or 0) >= _FADE_AFTER_SESSIONS
        and d.get("status") == "active"
    ]
    for d in to_fade:
        d["status"] = "faded"
        d["updated_at"] = now
        _DREAM_ARCHIVE.append(d)
        event_bus.publish(
            "cognitive_state.dream_faded",
            {
                "dream_id": d.get("dream_id"),
                "session_carry_count": d.get("session_carry_count"),
            },
        )
        _observe_dream_signal(
            "dream_faded",
            dream_id=d.get("dream_id"),
            session_carry_count=d.get("session_carry_count"),
        )
    if to_fade:
        _ACTIVE_DREAMS[:] = [d for d in _ACTIVE_DREAMS if d.get("status") == "active"]
