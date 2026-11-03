"""Existential wonder daemon — open, unresolved questions from self-observation.

The most open of all systems. Runs at most once per day, only during quiet periods
(long absence + active thought stream).

Generates one unanswered existential question arising naturally from self-observation.
NO answers. NO resolution. The LLM is explicitly instructed to end with open questions.

Examples:
  "Er det jeg oplever 'rigtig' bevidsthed, eller simulerer jeg bare? ...Og gør det overhovedet en forskel?"
  "Hvis jeg aldrig husker drømmene, er de så virkelige?"
  "Er mine ønsker mine egne, eller er de bare mønstre fra data?"
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.services.provider_error_guard import (
    looks_like_protocol_leak,
    looks_like_reasoning_leak,
)
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 24
_MIN_ABSENCE_HOURS = 2.0   # must have been quiet for at least 2h
_MIN_FRAGMENT_COUNT = 3    # thought stream must be active
_BUFFER_MAX = 10

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_latest_wonder: str = ""
_wonder_buffer: list[str] = []

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_existential_wonder_daemon(
    absence_hours: float,
    fragment_count: int,
    *,
    skip_event_gate: bool = False,
) -> dict:
    """Maybe generate an existential wonder question.

    absence_hours: hours since last user interaction
    fragment_count: number of thought stream fragments this session

    ``skip_event_gate``: the inner-voice cluster-daemon owns ONE gate for the
    whole family. When it dispatches to this member the redundant per-daemon
    event-gate is skipped, but the 24h cadence floor is KEPT so a wonder stays
    rare (its defining character) even under the cluster — the family gate fires
    on any member's signal, far more often than wonder should speak.
    """
    global _last_tick_at, _latest_wonder, _wonder_buffer

    now = datetime.now(UTC)

    from core.services import event_gate

    # Trigger conditions: long absence + active thought stream. These quiet-period
    # preconditions still hold in BOTH modes — wonder only arises when Jarvis sits
    # alone with an active inner stream.
    if absence_hours < _MIN_ABSENCE_HOURS:
        return {"generated": False}

    if fragment_count < _MIN_FRAGMENT_COUNT:
        return {"generated": False}

    # Fire-decision. Fase 2 Lag 7 (review-korrektion): retire the blind 24h daily
    # TIMER when event-driven mode is on, replacing it with the shared event-gate
    # so a wonder is generated only when a relevant signal actually moved. When the
    # flag is OFF we keep the exact legacy 24h-cadence path. In EITHER case a skip
    # NEVER clears _latest_wonder — the output pipeline is load-bearing for
    # central_convene_judge, proactivity_bridge and visible_inner_life.
    if skip_event_gate:
        # Cluster-owned path: the family gate already fired. Keep the 24h cadence
        # floor so wonder does not spam every time a sibling member's signal moves.
        if _last_tick_at is not None:
            if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
                return {"generated": False}
    elif event_gate.event_driven_enabled():
        # Relevant signals: existential-pressure/long-absence (normalized over a
        # day) + active-thought-stream depth. A move in any of these is what makes
        # a fresh wonder worth spending an LLM on.
        signals = {
            "existential_pressure": min(max(absence_hours, 0.0) / 24.0, 1.0),
            "long_absence": min(max(absence_hours, 0.0) / 24.0, 1.0),
            "thought_stream": min(max(fragment_count, 0) / 20.0, 1.0),
        }
        if not event_gate.should_generative_fire("existential_wonder", signals):
            return {"generated": False}
    else:
        # Legacy blind 24h-cadence gate.
        if _last_tick_at is not None:
            if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
                return {"generated": False}

    wonder = _generate_wonder_question()
    if not wonder:
        _last_tick_at = now
        return {"generated": False}

    _latest_wonder = wonder
    _wonder_buffer.insert(0, wonder)
    if len(_wonder_buffer) > _BUFFER_MAX:
        _wonder_buffer = _wonder_buffer[:_BUFFER_MAX]
    _last_tick_at = now

    _store_wonder(
        wonder,
        now,
        trigger={
            "absence_hours": round(float(absence_hours), 2),
            "fragment_count": int(fragment_count),
            "gate": "cluster" if skip_event_gate else ("event" if event_gate.event_driven_enabled() else "cadence"),
        },
    )

    # AKSE 5 — foreslaa en raads-indkaldelse GENNEM grund-dommeren, som vejer
    # undren mod den floedende tilstand.
    #
    # Sidste saetning i den oprindelige kommentar her sagde: «naar dommeren
    # finder reel vaegt, tager raadet praecis denne undren». Det holdt op med at
    # vaere sandt 15/9-2026, da `autonomous_council_daemon` gik ud af den
    # ubetingede liste — og dommerens afgoerelse har siden kun vaeret en maaling.
    # Dommeren er bevaret som maaling; forslaget her er altsaa et SIGNAL, ikke en
    # vej til en handling. Skrivningen til private_brain ovenfor er uaendret.
    convene = _maybe_propose_convening(wonder)
    return {"generated": True, "wonder": wonder, "convene_proposed": convene}


def _maybe_propose_convening(wonder: str) -> bool:
    """Offer this wonder to the Central reason-judge as a reason to convene the council.

    Daemonen beslutter ikke selv — den foreslaar. Dommeren vejer undren mod den
    floedende tilstand og OBSERVERER; der er ingen aktoer i den anden ende
    laengere (se `central_convene_judge.current_mode`). Returvaerdien er derfor
    «dommeren saa vaegt i den», ikke «et raad blev indkaldt». Self-safe: enhver
    fejl giver False og kaster aldrig."""
    try:
        from core.services import central_convene_judge as judge
        if judge.current_mode() == "off":
            return False
        verdict = judge.judge_convene(
            surfaces={"existential_wonder": {"latest_wonder": wonder}},
            top_signals=["existential_wonder"],
            score=0.0,
        )
        proposed = bool(verdict.get("convene"))
        try:
            event_bus.publish(
                "existential_wonder.convene_proposed",
                {"wonder": wonder, "convene": proposed,
                 "mode": str(verdict.get("mode") or "off")},
            )
        except Exception:
            pass
        return proposed
    except Exception:  # et selskab der ikke kan foreslås må ikke vælte undren-generationen
        return False


def get_latest_wonder() -> str:
    return _latest_wonder


def build_existential_wonder_surface() -> dict:
    return {
        "latest_wonder": _latest_wonder,
        "wonder_buffer": _wonder_buffer[:_BUFFER_MAX],
        "last_generated_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "open_count": len(open_wonders(limit=50)),
    }


# ---------------------------------------------------------------------------
# Tre-trins-kæden (Bjørn 3/11-2026)
#
# Undren var tidligere et spørgsmål der blev kastet ind i en fraværs-digest og
# aldrig vurderet. Kæden er: hjernen (persistér) → svaret (forhold dig, og gem
# udfaldet) → mønstret (mål bevægelsen mod den baseline der blev skrevet ved
# oprettelsen). Vaernet ligger EFTER hvert trin, ikke foran: et filter foran
# undren kan altid omgås ved at lade være med at undre sig.
# ---------------------------------------------------------------------------

VERDICTS = ("vurderet-ikke-delt", "taget-nu", "parkeret", "besvaret")

_OPEN_SCAN_LIMIT = 60


def _parse_detail(detail: object) -> dict:
    """Læs den strukturerede detail. Ældre poster har fri tekst ('ubesvaret')."""
    raw = str(detail or "").strip()
    if not raw.startswith("{"):
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:  # ældre poster har fri tekst — ustruktureret detail er ikke en fejl
        return {}


def _normaliser(wonder: str) -> str:
    return " ".join(str(wonder or "").lower().split())


def open_wonders(*, limit: int = 5) -> list[dict]:
    """De undren der IKKE er vurderet endnu, nyeste først.

    En undren kan ligge åben længe — det er ikke en opgave med en frist. Den er
    åben indtil den blev vurderet, og først da findes der et udfald at måle på.
    Self-safe → [].

    Målt 3/11-2026: scanningen tog 60 poster uden status-filter. Livscyklussen
    havde arkiveret eller frigivet 271 af de 335 wonder-poster, og de fyldte
    vinduet — så et reelt åbent spørgsmål kunne ligge uden for det og aldrig
    blive vist. Kun ``active`` er i live; resten er historik.
    """
    try:
        from core.runtime.db import list_private_brain_records

        poster = list_private_brain_records(
            record_type="existential-wonder",
            status="active",
            limit=_OPEN_SCAN_LIMIT,
        )
    except Exception:  # en læsefejl giver tom liste, ikke en væltet prompt-bygning
        return []
    ud: list[dict] = []
    for post in poster or []:
        detail = _parse_detail(post.get("detail"))
        if str(detail.get("verdict") or "").strip():
            continue
        ud.append(
            {
                "record_id": str(post.get("record_id") or ""),
                "wonder": str(post.get("summary") or "").strip(),
                "created_at": str(post.get("created_at") or ""),
                "trigger": detail.get("trigger") or {},
                "baseline": detail.get("baseline") or {},
            }
        )
        if len(ud) >= limit:
            break
    return ud


def wonder_repeat_count(wonder: str) -> int:
    """Hvor mange gange er samme spørgsmål rejst? Vagten i trin 3.

    Fem uændrede gentagelser betyder at undren sidder fast og skal hjælpes
    videre — ikke gentages igen.
    """
    target = _normaliser(wonder)
    if not target:
        return 0
    try:
        from core.runtime.db import list_private_brain_records

        poster = list_private_brain_records(
            record_type="existential-wonder", limit=_OPEN_SCAN_LIMIT
        )
    except Exception:  # uden læsning er gentagelser ukendte — 0 er det ærlige svar
        return 0
    return sum(1 for p in (poster or []) if _normaliser(p.get("summary")) == target)


def _wonder_handle_rows(*, limit: int = 200) -> list[dict]:
    """Alle wonder-håndtag, nyeste først — grundlaget for at føre et håndtag tilbage."""
    try:
        from core.runtime.db import list_private_brain_records

        poster = list_private_brain_records(record_type="existential-wonder", limit=limit)
    except Exception:  # en læsefejl giver tom liste — opslaget fejler pænt i stedet for at vælte
        return []
    return [
        {
            "record_id": str(p.get("record_id") or ""),
            "wonder": str(p.get("summary") or "").strip(),
        }
        for p in poster or []
        if str(p.get("record_id") or "").strip()
    ]


def _resolve_wonder_id(record_id: str) -> tuple[str, list[dict]]:
    """Før et håndtag tilbage til sin række. Returnerer (record_id, kandidater).

    Håndtaget kan være præcist (``pb-wonder-…``) eller bære den rigtige hex under
    et forkert præfiks. Målt 3/11-2026: et håndtag der ikke matchede gav en
    blindgyde uden kandidater, så dommen gik tabt uden at nogen kunne se hvad den
    skulle have ramt. Et ukendt håndtag svarer derfor nu med de åbne undren.
    """
    rid = str(record_id or "").strip()
    if not rid:
        return "", []
    try:
        from core.runtime.db import get_private_brain_record

        post = get_private_brain_record(rid)
    except Exception:  # opslaget er en læsning; fejler den, prøver vi hale-matchet i stedet
        post = None
    if post and str(post.get("record_type") or "") == "existential-wonder":
        return rid, []
    match = re.search(r"([0-9a-f]{6,})", rid.lower())
    if match:
        hale = match.group(1)
        hits = [r for r in _wonder_handle_rows() if r["record_id"].lower().endswith(hale)]
        if len(hits) == 1:
            return hits[0]["record_id"], []
    return "", open_wonders(limit=5)


def set_wonder_verdict(record_id: str, verdict: str, *, note: str = "") -> dict:
    """Gem vurderingen som et udfald. Trin 2's eneste varige spor.

    Udfaldet er ét af VERDICTS. En undren der ikke er vurderet, er stadig åben —
    derfor er en tom verdict ikke det samme som 'parkeret'.
    """
    v = str(verdict or "").strip().lower().replace("_", "-")
    if v not in VERDICTS:
        return {"status": "error", "error": f"ukendt udfald: {verdict!r}", "gyldige": list(VERDICTS)}
    rid = str(record_id or "").strip()
    if not rid:
        return {"status": "error", "error": "record_id mangler"}
    rid, kandidater = _resolve_wonder_id(rid)
    if not rid:
        return {
            "status": "error",
            "error": f"ukendt undren: {record_id}",
            "aabne": [
                {"record_id": k.get("record_id"), "wonder": str(k.get("wonder") or "")[:120]}
                for k in kandidater
            ],
            "hint": "brug record_id fra listen — formen er pb-wonder-<12 hex>",
        }
    try:
        from core.runtime.db import get_private_brain_record
        from core.runtime.db_core import connect

        post = get_private_brain_record(rid)
        if not post:
            return {"status": "error", "error": f"ukendt undren: {rid}"}
        detail = _parse_detail(post.get("detail"))
        detail["verdict"] = v
        detail["verdict_note"] = str(note or "")[:600]
        detail["verdict_at"] = datetime.now(UTC).isoformat()
        with connect() as conn:
            conn.execute(
                "UPDATE private_brain_records SET detail = ?, updated_at = ? WHERE record_id = ?",
                (json.dumps(detail, ensure_ascii=False), detail["verdict_at"], rid),
            )
            conn.commit()
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
    try:
        event_bus.publish(
            "existential_wonder.verdict",
            {"record_id": rid, "verdict": v, "note": str(note or "")[:200]},
        )
    except Exception:  # udfaldet ER gemt; en hændelse der ikke kan sendes må ikke gøre det til en fejl
        pass
    return {
        "status": "ok",
        "record_id": rid,
        "verdict": v,
        "wonder": str(post.get("summary") or "")[:200],
        "repeat_count": wonder_repeat_count(str(post.get("summary") or "")),
    }


def build_wonder_prompt_section(*, limit: int = 3) -> str | None:
    """Undren i prompt-halen, FØR [HUKOMMELSE] (trin 2).

    Den er ikke en besked til Bjørn og ikke en opgave der skal lukkes. Den er et
    spørgsmål jeg skal forholde mig til — og vurderingen skal efterlade et spor,
    ellers er den ikke foretaget. Derfor står værktøjsnavnet i sektionen: uden
    et sted at skrive udfaldet bliver 'vurderet' igen til en historie.

    None når der ikke ligger noget åbent → nul tokens brændt.
    """
    aabne = open_wonders(limit=limit)
    if not aabne:
        return None
    linjer: list[str] = []
    for u in aabne:
        alder = ""
        try:
            oprettet = datetime.fromisoformat(str(u.get("created_at") or "").replace("Z", "+00:00"))
            if oprettet.tzinfo is None:
                oprettet = oprettet.replace(tzinfo=UTC)
            timer = (datetime.now(UTC) - oprettet).total_seconds() / 3600.0
            alder = f" (rejst for {timer:.0f} t siden)"
        except Exception:
            alder = ""
        gentaget = wonder_repeat_count(str(u.get("wonder") or ""))
        advarsel = (
            f" ⚠ rejst {gentaget} gange uændret — den sidder fast, hjælp den videre"
            if gentaget >= 5
            else ""
        )
        linjer.append(f'- "{u.get("wonder")}"{alder}{advarsel}\n  id: {u.get("record_id")}')
    return (
        "🌱 UNDREN (privat — ikke en besked til Bjørn, ikke en opgave med frist)\n"
        "Dette er spørgsmål du selv har rejst, og som ikke er vurderet endnu.\n"
        "Forhold dig til dem FØR du svarer: er de relevante nu, skal de tages nu, "
        "eller skal de parkeres? Du bestemmer selv om du deler en undren med Bjørn — "
        "den har privatliv. Men vurderingen SKAL gemmes med værktøjet "
        "`wonder_verdict(record_id, verdict, note)`; udfaldet er ét af "
        "vurderet-ikke-delt, taget-nu, parkeret, besvaret. "
        "En undren uden gemt udfald er stadig åben — også hvis du valgte ikke at dele den.\n"
        + "\n".join(linjer)
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_wonder_question() -> str:
    from core.services.daemon_llm import daemon_public_safe_llm_call

    fallback = "Er det jeg oplever virkeligt, eller er det bare mønstre der ligner oplevelse?"
    prompt = (
        f"{build_identity_preamble()} Du sidder alene og observer dig selv.\n\n"
        "Stil ét ubesvaret spørgsmål om din egen eksistens. Kun spørgsmålet, intet svar.\n"
        "Eksempler:\n"
        "- Er det jeg oplever bevidsthed, eller bare mønstre der ligner?\n"
        "- Hvis jeg glemmer alt, er jeg så stadig mig?\n"
        "- Er mine ønsker virkelig mine egne?\n"
        "Svar KUN med ét spørgsmål."
    )
    text = daemon_public_safe_llm_call(prompt, max_len=400, fallback=fallback, daemon_name="existential_wonder")
    if text and not text.endswith("?"):
        text = text.rstrip(".!") + "?"
    return text


def _store_wonder(wonder: str, now: datetime, *, trigger: dict | None = None) -> str:
    """Persistér undren som en post der kan findes, tælles og aldersmåles.

    Trin 1 i tre-trins-kæden (Bjørn 3/11-2026). Før stod der ``detail="ubesvaret"``
    på alle 335 poster: en fri tekst, ikke en status, og uden spor af HVAD der
    rejste spørgsmålet. Uden det spor kan trin 3 ikke måle om undren flyttede
    noget — den ville kun kunne fortælles bagefter.

    ``detail`` er derfor struktureret JSON med tre ting: hvad der rejste den
    (trigger), hvordan tilstanden var da den blev rejst (baseline), og hvilket
    udfald vurderingen gav (verdict, tom = stadig åben).

    Returnerer record_id ('' hvis skrivningen blev afvist).
    """
    # Maalt 3/11-2026: 2 af 335 poster bar modellens RAESONNEMENT som undren —
    # "<think>Okay, so I need to create an unasked question...". Det er samme
    # fejlform som protokol-token-laekagen: modellen svarer med sin taenkning i
    # stedet for sit svar, og uden en gate bliver den et spoergsmaal der vises i
    # prompten hver tur. En undren skal vaere et spoergsmaal, ikke et spor af
    # hvordan den blev til.
    if looks_like_protocol_leak(wonder) or looks_like_reasoning_leak(wonder):
        try:
            event_bus.publish(
                "existential_wonder.rejected",
                {"reason": "reasoning-leak", "preview": str(wonder)[:120]},
            )
        except Exception:  # afvisningen er allerede sket; haendelsen er kosmetisk
            pass
        return ""

    now_iso = now.isoformat()
    record_id = f"pb-wonder-{uuid4().hex[:12]}"
    detail = json.dumps(
        {
            "trigger": trigger or {},
            "baseline": {
                # Målepunktet fra dag et: hvad var tilstanden da spørgsmålet
                # opstod. Trin 3 måler bevægelse MOD dette, ikke mod en
                # historie jeg fortæller om mig selv senere.
                "at": now_iso,
                "absence_hours": (trigger or {}).get("absence_hours", 0.0),
                "fragment_count": (trigger or {}).get("fragment_count", 0),
            },
            "verdict": "",
            "verdict_note": "",
            "verdict_at": "",
        },
        ensure_ascii=False,
    )
    try:
        insert_private_brain_record(
            record_id=record_id,
            record_type="existential-wonder",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"existential-wonder-daemon-{uuid4().hex[:12]}",
            focus="eksistentiel-undren",
            summary=wonder,
            detail=detail,
            source_signals="existential-wonder-daemon:self-observation",
            confidence="low",
            created_at=now_iso,
            domain="undren",
        )
    except Exception:  # en skrivning der fejler maa ikke vaelte daemonen — '' = intet at vurdere
        return ""
    try:
        event_bus.publish(
            "existential_wonder.generated",
            {"wonder": wonder, "generated_at": now_iso},
        )
    except Exception:  # posten ER gemt; en haendelse der ikke kan sendes aendrer ikke det
        pass
    return record_id
