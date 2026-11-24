"""Persistent initiative queue — bridges inner voice thoughts to heartbeat actions.

When inner voice detects an initiative ("I should check on X", "worth revisiting Y"),
it pushes to this queue. Heartbeat can then see pending initiatives and decide to act.

Design constraints:
- SQLite-backed, bounded
- Observable in Mission Control
- Thread-safe
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime import db as runtime_db
from core.runtime.db import approve_runtime_initiative, reject_runtime_initiative

_MAX_QUEUE_SIZE = 8
_EXPIRE_MINUTES = 90
# 2026-09-04 (blok E): 90 minutter gjaldt ALLE prioriteter. En lav-prioritets
# nysgerrighed opstaar sjaeldent i det vindue hvor den ogsaa kan handles paa —
# maalt over 30 dage udloeb 782 af 985 initiativer. Lav prioritet lever nu et
# doegn; medium/high er uaendret, saa det haastende stadig er haastende.
_EXPIRE_MINUTES_LOW = 24 * 60
_RETRY_DELAY_MINUTES = 10
#: Loft paa antal forsoeg uden udfoerelse. MAALT 1/11-2026: samme maal blev
#: gentaget 306 gange over 50 dage fordi intet stoppede det. Uden dette loft
#: erstatter `mark_attempted` blot én loekke med en langsommere.
_MAX_ATTEMPTS = 3
_LONG_TERM_REASSESS_DAYS = 14
_MAX_ACTIVE_LONG_TERM_INTENTIONS = 3
_QUEUE_LOCK = threading.Lock()


# ── Kvalitetsport: er dette et initiativ, eller er det promptens eget indhold? ──
#
# Målt 2026-09-05: køen havde 48 poster — 6 ventende, 26 udløbet uden svar, og
# NUL nogensinde godkendt eller afvist. Da vi læste de seks ventende, var kun ÉN
# et rigtigt initiativ:
#
#   "Choose initiative only if there's a genuine next step."   ← instruksen
#   "Use JSON format with thought, initiative (null if...)."   ← output-formatet
#   "What might the next move be?"                             ← et spørgsmål
#   "Or since mode is clarify and there's an inner-conflict…"   ← tankefragment
#   "Tråden er stadig i opstartsfase efter pausen…"             ← statusbemærkning
#   "Slå det seneste bash-run op og sammenhold det med…"        ← ÆGTE
#
# Det er samme sygdom som ramte de indre stemmer og curiosity-gælden: modellen
# svarer med opgaven i stedet for at løse den, og det bliver gemt som indhold.
# Her gør det mere skade, fordi køen er noget MENNESKER skal tage stilling til.
# En kø fuld af promptens eget format er værre end en tom kø.
#
# Porten er bevidst konservativ. Den afviser kun det der beviseligt ikke er et
# forslag; tvivlstilfælde slipper igennem.

_IKKE_ET_FORSLAG_PREFIX = ("or ", "eller ", "men ", "and ", "så måske ", "maybe ")

#: Serialiseret tomhed. Målt 3/11-2026: den indre stemme svarede med JSON
#: `"initiative": null`, og `str(initiative)` gjorde det til den fire tegn lange
#: streng "null" — som er sand, ikke tom, og derfor gik gennem både sanitizeren
#: og `if not tekst`. Resultatet var en post i køen uden indhold
#: (init-d5e4fcffe8, focus="null"). En tom indskydelse er ikke en opgave.
_TOMTE_FOKUS_ORDS = frozenset(("null", "none", "undefined", "nil", "n/a", "-"))


def _er_ikke_et_initiativ(focus: str) -> str:
    """Returnér en grund hvis dette ikke er et forslag. Tom streng = behold."""
    tekst = str(focus or "").strip()
    if not tekst:
        return "tom"
    if tekst.lower() in _TOMTE_FOKUS_ORDS:
        return "tom"

    try:
        from core.services.visible_inner_life import _is_instruction_echo
        if _is_instruction_echo(tekst):
            return "instruks-ekko"
    except Exception:
        pass

    try:
        from core.services.provider_error_guard import looks_like_provider_error
        if looks_like_provider_error(tekst):
            return "udbyder-fejl"
    except Exception:
        pass

    # Et spørgsmål er ikke et forslag. «What might the next move be?» beder om
    # et svar; den beder ikke om lov til at handle.
    if tekst.rstrip().endswith("?"):
        return "spørgsmål"

    # En TILSTAND er ikke en opgave. Målt 24/11-2026 over ugens 133
    # inner-voice-initiativer: cirka halvdelen var selvbeskrivelser —
    # «Jeg bliver her lidt uden at presse en plan ud af det», «Jeg mærker en
    # lingering spænding», «Der er ingen reel næste drift lige nu». De peger
    # ikke på noget der kan gøres, og hvert af dem blev alligevel til et run
    # der brugte 40.000-90.000 input-tokens på at konkludere at der ikke var
    # noget at lave.
    #
    # Kilden er prompten selv: INNER_VOICE.md beder modellen om at levere et
    # `initiative`-felt med mindre den aktivt sætter det til null — så en
    # beskrivelse af en tilstand bliver til «noget jeg bør gøre».
    # En ægte indskydelse starter med et verbum (søg, afklar, mål, tjek).
    lav_start = tekst.lower()
    # Men sætningsstarten er kun et INDICIE, ikke en regel: en refleksion der
    # peger på noget konkret («Jeg vil tjekke initiative_queue.py») er en
    # handlingshensigt. Findes der anker + handling, er det ikke en tilstand.
    if lav_start.startswith(("jeg ", "der er ", "der findes ")):
        from core.services.work_coordination import has_independent_work_signal

        if not has_independent_work_signal(tekst):
            return "tilstandsbeskrivelse"

    # Et fragment der starter med en konjunktion er et stykke ræsonnement der er
    # revet ud af sin sammenhæng.
    lav = tekst.lower()
    if any(lav.startswith(p) for p in _IKKE_ET_FORSLAG_PREFIX):
        return "tankefragment"

    return ""


# ── Gentagelses-port: samme PÅSTAND i ny ordlyd ──
#
# Målt 2026-10-30 og bekræftet 2/11-2026: 249 initiativer siden 29. maj handlede
# om "den afbrudte kørsel" — og 60+ alene siden 1/11, hvor præmissen var målt
# FALSK (ingen afbrudt kørsel fandtes). Dedup'en i push_initiative matcher
# `find_pending_runtime_initiative_by_focus`, altså EKSAKT tekst, mens den indre
# stemme omformulerer den samme påstand hver gang. Median ord-overlap mellem ti
# på hinanden følgende: 0,14 — men alle delte kerneordene "afbrudt" og "kørsel".
#
# Porten kræver derfor ikke ens ordlyd men SAMME EMNE: mindst to fælles
# indholdsord mod et initiativ fra samme kilde inden for 6 timer. Den rammer
# kun `inner-voice`; menneske-godkendte forslag og long_term_intentions går fri,
# og tekster med under to indholdsord slipper igennem som før.

# Vinduet er 24 timer, ikke 6: målt på de 59 faktiske inner-voice-initiativer
# siden 1/11 stoppede 6 timer 38 af dem, mens 24 timer stoppede 43. Et initiativ
# lever selv op til et døgn (se _EXPIRE_MINUTES_LOW) — porten skal dække den
# levetid, ellers kan den samme påstand rejses igen efter midnat.
_GENTAGELSE_VINDUE_TIMER = 24
_GENTAGELSE_MIN_FAELLES = 2
#: Mindste længde for delstreng-match. Dansk sammensætter ("værktøjskørsel"
#: bærer "kørsel"), så hele ord alene tabte gentagelser der var samme emne.
_GENTAGELSE_MIN_DEL = 5
_GENTAGELSE_STOPORD = frozenset("""
    den det der som for foer hvad hvor om paa til og at er en et af med uden
    kun ikke lige skal bliver blive se efter find finde laes tjek tjekke
    afklar afklare inspicer inspicere noget nogen faktisk eller fra ved
    dette disse saadan vaere have har varer vaeret goer goere foerste foer
""".split())


def _kerneord(tekst: str) -> set[str]:
    """Indholdsord i en fokus-tekst — til emne-sammenligning, ikke til visning."""
    renset = str(tekst or "").lower()
    for tegn in ".,;:!?()[]{}'\"—-/\\|*":
        renset = renset.replace(tegn, " ")
    return {o for o in renset.split() if len(o) >= 4 and o not in _GENTAGELSE_STOPORD}


def _faelles_emneord(nye: set[str], gamle: set[str]) -> set[str]:
    """Ord der bærer samme emne — også når det ene er en sammensætning."""
    faelles = nye & gamle
    for nyt in nye - faelles:
        for gammelt in gamle - faelles:
            if (
                len(nyt) >= _GENTAGELSE_MIN_DEL
                and len(gammelt) >= _GENTAGELSE_MIN_DEL
                and (nyt in gammelt or gammelt in nyt)
            ):
                faelles.add(nyt)
                break
    return faelles


def _gentaget_paastand(focus: str, *, source: str) -> str:
    """Returnér en grund hvis samme emne allerede ligger i køen. Tom = behold."""
    if source != "inner-voice":
        return ""
    nye = _kerneord(focus)
    if len(nye) < _GENTAGELSE_MIN_FAELLES:
        return ""
    graense = datetime.now(UTC) - timedelta(hours=_GENTAGELSE_VINDUE_TIMER)
    for status in ("pending", "acted"):
        try:
            poster = runtime_db.list_runtime_initiatives(
                status=status, initiative_type="initiative", limit=40,
            )
        except Exception:  # db-fejl må ikke blokere en ægte indskydelse — slip hellere igennem
            continue
        for post in poster or []:
            ts = _parse_iso(str(post.get("detected_at") or ""))
            if not ts or ts < graense:
                continue
            # Samme emne er ikke samme arbejde: to initiativer med hver sin
            # konkrete handling på samme anker bevares begge (koordinering).
            from core.services.work_coordination import er_forskellig_handling

            if er_forskellig_handling(focus, str(post.get("focus") or "")):
                continue
            faelles = _faelles_emneord(nye, _kerneord(str(post.get("focus") or "")))
            if len(faelles) >= _GENTAGELSE_MIN_FAELLES:
                return f"gentaget-paastand ({', '.join(sorted(faelles)[:3])})"
    return ""


# ── Aktiv-tur-port: køen må ikke sende mig på arbejde mens jeg taler ──
#
# Målt 24/11-2026: initiativet «Søg Gmail målrettet efter Ollama-usage-mailen»
# blev dannet 17:59:24 og kørt 18:01:00 — 0 minutter efter en synlig tur, mens
# den synlige tur besvarede præcis det samme. `_gentaget_paastand` kunne ikke se
# det: den læser KUN `runtime_initiatives`, altså sin egen kø.
#
# To signaler blev prøvet og forkastet samme dag, begge med måling:
#   * Ord-overlap mod assistent-svar: 10 af 14 afvist — men 6 af dem tilfældige,
#     fordi «ingen», «står», «plan» og «lidt» står i ethvert svar; og 2 ægte
#     gentagelser slap igennem. Strammet til kun ord >=6 tegn: 6 af 14, hvoraf
#     halvdelen stadig var støj.
#   * FTS (`search_chat_messages`): 0 match af 14, fordi en hel sætning som
#     forespørgsel kræver at ALLE led matcher.
#
# Tiden skiller derimod rent: målt over ugens 133 inner-voice-initiativer ligger
# 48% inden for 30 minutter efter en synlig tur. Et initiativ der opstår midt i
# eller lige efter en aktiv samtale er en gentagelse af samtalen — uanset ordlyd.
_AKTIV_TUR_MINUTTER = 30


def _aktiv_synlig_tur() -> str:
    """Returnér en grund hvis en synlig tur lige har været aktiv. Tom = behold.

    Kaldes kun for ``inner-voice``: et menneske-godkendt forslag må ikke kunne
    afvises af at Jarvis tilfældigvis talte med nogen.
    """
    graense = (datetime.now(UTC) - timedelta(minutes=_AKTIV_TUR_MINUTTER)).isoformat()
    try:
        from core.runtime.db import connect

        with connect() as conn:
            r = conn.execute(
                "SELECT COUNT(*) FROM visible_runs"
                " WHERE started_at >= ? AND run_id NOT LIKE 'autonomous-%'",
                (graense,),
            ).fetchone()
    except Exception:  # db-fejl må ikke blokere en ægte indskydelse — slip igennem
        return ""
    antal = int(r[0] or 0) if r else 0
    if antal > 0:
        return f"aktiv-synlig-tur ({antal} ture inden for {_AKTIV_TUR_MINUTTER} min)"
    return ""


def push_initiative(
    *,
    focus: str,
    source: str = "inner-voice",
    source_id: str = "",
    priority: str = "medium",
    session_id: str = "",
    user_id: str | None = None,
) -> str:
    """Push a new initiative to the queue. Returns the initiative_id.

    Mood dialer gating:
    - level 0 (distressed): nedgraderer til low (slettede foer 2026-09-04)
    - level 1 (melancholic): downgrader priority til low
    - level 2 (neutral): passerer uændret
    - level 3-4 (content/euphoric): kan upgradere low→medium
    """
    now = datetime.now(UTC)
    initiative_id = f"init-{uuid4().hex[:10]}"
    if user_id is None:
        try:
            from core.identity.workspace_context import current_user_id

            user_id = current_user_id() or None
        except Exception:
            user_id = None
    _bruger = user_id
    normalized_focus = focus[:200].strip()
    if not normalized_focus:
        normalized_focus = "Follow up on unspecified initiative"

    # Porten: en kø som mennesker skal svare på, må ikke fyldes med promptens
    # eget indhold. Afvisningen er synlig i eventbussen — vi taber ikke noget
    # i tavshed, vi holder det bare ude af det der ligner en beslutning.
    _afvist = _er_ikke_et_initiativ(normalized_focus)
    if _afvist:
        try:
            event_bus.publish("heartbeat.initiative_rejected", {
                "focus": normalized_focus[:120], "reason": _afvist, "source": source,
            })
        except Exception:
            pass
        return ""

    # Gentagelses-porten: samme PÅSTAND i ny ordlyd er ikke en ny indskydelse.
    # Uden den blev "den afbrudte kørsel" rejst 60+ gange på to døgn, selv efter
    # præmissen var målt falsk — hver gang i en ny formulering der slap gennem
    # den eksakte tekst-dedup.
    _gentaget = _gentaget_paastand(normalized_focus, source=source)
    if _gentaget:
        try:
            event_bus.publish("heartbeat.initiative_rejected", {
                "focus": normalized_focus[:120], "reason": _gentaget, "source": source,
            })
        except Exception:  # observabilitet, ikke kontrol — afvisningen gælder uanset
            pass
        return ""

    # Aktiv-tur-porten: den kø-interne dedup kan kun se sin EGEN tabel. Er jeg
    # midt i eller lige færdig med en synlig samtale, er der ingen næste
    # handling — kun en gentagelse af arbejde der allerede er betalt for.
    if source == "inner-voice":
        # KOORDINERING FØR UNDERTRYKKELSE: dækkes handlingen allerede af en
        # opgave, en agent eller en synlig samtale (konkrete relationer, samme
        # bruger) → koordinér med den. Ellers er aktivitet ikke konflikt.
        from core.services.work_coordination import (
            find_covering_work, has_independent_work_signal, record_decision,
        )

        _dæk = find_covering_work(normalized_focus, user_id=_bruger)
        if _dæk:
            _aarsag = (
                f"dækket-af-eksisterende-arbejde ({_dæk['kind']} {_dæk['ref']}"
                f" {_dæk['state']}: {_dæk['why']})"
            )
            record_decision(decision="coordinated", reason=_aarsag,
                            subject=normalized_focus, covering=_dæk, user_id=_bruger)
            try:
                event_bus.publish("heartbeat.initiative_rejected", {
                    "focus": normalized_focus[:120], "reason": _aarsag, "source": source,
                })
            except Exception:  # observabilitet, ikke kontrol — koordineringen gælder uanset (og record_decision har logget den)
                pass
            return ""
        # Tidsporten er en NØDBREMSE for initiativer vi ikke kan dømme (intet
        # anker/ingen handling). Et konkret, uafhængigt initiativ passerer.
        _aktiv = "" if has_independent_work_signal(normalized_focus) else _aktiv_synlig_tur()
        if _aktiv:
            try:
                event_bus.publish("heartbeat.initiative_rejected", {
                    "focus": normalized_focus[:120], "reason": _aktiv, "source": source,
                })
            except Exception:  # observabilitet, ikke kontrol — afvisningen gælder uanset
                pass
            return ""

    normalized_priority = (
        priority.strip().lower() if priority.strip().lower() in {"low", "medium", "high"} else "medium"
    )

    # Mood dialer gate — kun hvis initiative ikke er explicitly "high"
    if normalized_priority != "high":
        try:
            from core.services.mood_dialer import derive_from_v2_mood
            params = derive_from_v2_mood()
            if params.mood_level == 0:
                # 2026-09-04 (blok E): distressed SLETTEDE impulsen — den blev
                # aldrig set igen, og ingen kunne se hvad der forsvandt. En
                # dårlig dag er ikke det samme som en dårlig idé. Nu nedgraderes
                # den til low i stedet, så den kan hentes frem når humøret vender.
                normalized_priority = "low"
                event_bus.publish("heartbeat.initiative_gated", {
                    "focus": normalized_focus[:100], "reason": "mood_distressed",
                    "mood_level": 0, "action": "downgraded_to_low",
                })
            elif params.mood_level == 1 and normalized_priority == "medium":
                normalized_priority = "low"
            elif params.mood_level >= 3 and normalized_priority == "low":
                normalized_priority = "medium"
        except Exception:
            pass

    with _QUEUE_LOCK:
        _expire_stale(now)
        existing = runtime_db.find_pending_runtime_initiative_by_focus(
            normalized_focus,
            initiative_type="initiative",
        )
        if not existing:
            from core.services.work_coordination import find_pending_initiative_same_work

            _samme = find_pending_initiative_same_work(normalized_focus, user_id=_bruger)
            if _samme:
                existing = runtime_db.get_runtime_initiative(_samme)
        if existing:
            existing_id = str(existing.get("initiative_id") or "")
            existing_priority = str(existing.get("priority") or "medium")
            runtime_db.update_runtime_initiative(
                existing_id,
                detected_at=now.isoformat(),
                next_attempt_at=now.isoformat(),
                priority=(
                    normalized_priority
                    if normalized_priority == "high" or existing_priority != "high"
                    else existing_priority
                ),
                blocked_reason="",
                updated_at=now.isoformat(),
            )
            return existing_id
        from core.services.session_binding import bind_session

        runtime_db.create_runtime_initiative(
            initiative_id=initiative_id,
            initiative_type="initiative",
            focus=normalized_focus,
            why_text="",
            source=source,
            source_id=source_id,
            status="pending",
            priority=normalized_priority,
            detected_at=now.isoformat(),
            first_seeded_at=now.isoformat(),
            next_attempt_at=now.isoformat(),
            updated_at=now.isoformat(),
            session_id=bind_session(session_id),
            scheduled_for_user_id=_bruger or None,
            initiated_by=f"user:{_bruger}" if _bruger else "jarvis-self",
        )
        _trim_pending(now)
        queue_size = len(
            runtime_db.list_runtime_initiatives(
                status="pending",
                limit=_MAX_QUEUE_SIZE + 20,
            )
        )

    event_bus.publish(
        "heartbeat.initiative_pushed",
        {
            "initiative_id": initiative_id,
            "focus": normalized_focus[:100],
            "source": source,
            "priority": normalized_priority,
            "queue_size": queue_size,
        },
    )

    return initiative_id


def seed_long_term_intention(
    *,
    title: str,
    why: str,
    source: str = "life-project",
    source_id: str = "",
    priority: str = "medium",
) -> str:
    """Create or refresh a long-term intention owned by Jarvis."""
    now = datetime.now(UTC)
    normalized_title = str(title or "").strip()[:200]
    if not normalized_title:
        raise ValueError("title is required")
    normalized_why = str(why or "").strip()[:400]
    if not normalized_why:
        raise ValueError("why is required")
    normalized_priority = (
        priority.strip().lower() if priority.strip().lower() in {"low", "medium", "high"} else "medium"
    )
    initiative_id = f"life-{uuid4().hex[:10]}"

    with _QUEUE_LOCK:
        _expire_stale(now)
        existing = _find_active_long_term_intention_by_title(normalized_title)
        if existing:
            existing_id = str(existing.get("initiative_id") or "")
            runtime_db.update_runtime_initiative(
                existing_id,
                why_text=normalized_why,
                detected_at=now.isoformat(),
                next_attempt_at=now.isoformat(),
                blocked_reason="",
                updated_at=now.isoformat(),
            )
            return existing_id
        active = list_active_long_term_intentions(limit=_MAX_ACTIVE_LONG_TERM_INTENTIONS + 2)
        if len(active) >= _MAX_ACTIVE_LONG_TERM_INTENTIONS:
            raise RuntimeError("max active life projects reached")
        runtime_db.create_runtime_initiative(
            initiative_id=initiative_id,
            initiative_type="long_term_intention",
            focus=normalized_title,
            why_text=normalized_why,
            source=source,
            source_id=source_id,
            status="pending",
            priority=normalized_priority,
            detected_at=now.isoformat(),
            first_seeded_at=now.isoformat(),
            next_attempt_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

    event_bus.publish(
        "heartbeat.initiative_pushed",
        {
            "initiative_id": initiative_id,
            "focus": normalized_title[:100],
            "source": source,
            "priority": normalized_priority,
            "initiative_type": "long_term_intention",
        },
    )
    return initiative_id


def get_pending_initiatives() -> list[dict[str, object]]:
    """Return all pending (non-expired, non-acted) initiatives."""
    now = datetime.now(UTC)
    with _QUEUE_LOCK:
        _expire_stale(now)
        due_items = [
            item
            for item in runtime_db.list_runtime_initiatives(
                status="pending",
                limit=_MAX_QUEUE_SIZE + 20,
            )
            if _initiative_due(item, now)
        ]
        due_items.sort(key=_initiative_sort_key)
        return due_items[:_MAX_QUEUE_SIZE]


def mark_acted(
    initiative_id: str,
    *,
    action_summary: str = "",
) -> bool:
    """Mark an initiative as acted upon. Returns True if found."""
    now = datetime.now(UTC).isoformat()
    with _QUEUE_LOCK:
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("status") or "") != "pending":
            return False
        if str(existing.get("initiative_type") or "initiative") == "long_term_intention":
            reassess_at = (
                datetime.fromisoformat(now) + timedelta(days=_LONG_TERM_REASSESS_DAYS)
            ).isoformat()
            runtime_db.update_runtime_initiative(
                initiative_id,
                status="pending",
                disposition="acted",
                disposition_reason="",
                last_action_at=now,
                acted_at=now,
                next_attempt_at=reassess_at,
                blocked_reason="",
                action_summary=action_summary[:200],
                updated_at=now,
            )
            event_bus.publish(
                "heartbeat.initiative_acted",
                {
                    "initiative_id": initiative_id,
                    "focus": str(existing.get("focus") or "")[:100],
                    "action_summary": action_summary[:100],
                    "initiative_type": "long_term_intention",
                    "reassess_at": reassess_at,
                },
            )
            return True
        runtime_db.update_runtime_initiative(
            initiative_id,
            status="acted",
            disposition="acted",
            disposition_reason="",
            acted_at=now,
            next_attempt_at="",
            blocked_reason="",
            action_summary=action_summary[:200],
            updated_at=now,
        )
        event_bus.publish(
            "heartbeat.initiative_acted",
            {
                "initiative_id": initiative_id,
                "focus": str(existing.get("focus") or "")[:100],
                "action_summary": action_summary[:100],
            },
        )
        return True


_CLAIM_LEASE_MINUTES = 15


def claim_initiative(initiative_id: str, *, holder: str) -> bool:
    """Atomisk accept: kun ÉN worker vinder et ventende, forfaldent initiativ.

    Compare-and-set i selve databasen (ikke `_QUEUE_LOCK`, som kun er en
    tråd-lås og ikke holder mellem processer): `next_attempt_at` rykkes frem som
    lease, og kun rækken der faktisk ændres (rowcount == 1) ejer det. Dør
    holderen, udløber leasen af sig selv og initiativet kan overtages — ingen
    manuel oprydning, ingen emne-lås.
    """
    from core.runtime.db import connect

    now = datetime.now(UTC)
    lease = (now + timedelta(minutes=_CLAIM_LEASE_MINUTES)).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE runtime_initiatives SET next_attempt_at=?, blocked_reason=?, updated_at=?"
            " WHERE initiative_id=? AND status='pending'"
            " AND (next_attempt_at='' OR next_attempt_at<=?)",
            (lease, f"claimed-by:{holder}"[:120], now.isoformat(), initiative_id, now.isoformat()),
        )
        conn.commit()
        return cur.rowcount == 1


def decline_initiative(initiative_id: str, *, reason: str) -> bool:
    """Close a pending initiative because Jarvis chose not to act on it.

    This is Jarvis' own disposition, not the owner's consent decision handled
    by ``reject_initiative``. A reason is mandatory so a terminal decline can
    never look like an action, an expiry, or an unexplained disappearance.
    """
    normalized_reason = str(reason or "").strip()
    if not normalized_reason:
        return False
    now = datetime.now(UTC).isoformat()
    with _QUEUE_LOCK:
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("status") or "") != "pending":
            return False
        updated = runtime_db.update_runtime_initiative(
            initiative_id,
            status="declined",
            disposition="declined",
            disposition_reason=normalized_reason[:300],
            next_attempt_at="",
            blocked_reason="",
            acted_at="",
            action_summary="",
            updated_at=now,
        )
    if not updated:
        return False
    event_bus.publish(
        "heartbeat.initiative_declined",
        {
            "initiative_id": initiative_id,
            "focus": str(existing.get("focus") or "")[:100],
            "reason": normalized_reason[:120],
            "disposition": "declined",
        },
    )
    return True


def close_acted_without_outcome(*, limit: int = 5000) -> dict[str, object]:
    """Luk `acted`-poster der aldrig fik et outcome.

    HVORFOR (maalt 8/11-2026): 1.042 af 1.114 `acted`-poster havde tomt
    `outcome` — de aeldste fra 10. april. `acted` er ikke en lukket tilstand:
    `_expire_stale` roerer kun `pending`, og der fandtes ingen vej ud af
    `acted`. Kommentaren i `initiatives_prompt_section` beskriver hvorfor
    puljen voksede: «76 markeret `acted` = postet til en proaktivitets-kanal
    ingen laeste» — impulsen blev genereret, aldrig laest tilbage, og derfor
    genereret igen. `acted` betyder altsaa «sendt afsted», ikke «behandlet».

    HVORFOR IKKE ET OUTCOME: domaenet er `approved`/`rejected`/`resolved`/
    `completed`, og ingen af dem er sande om en impuls der blev postet uden
    at nogen laeste den. At saette `completed` ville vaere den form for
    teater hvor et felt ser rigtigt ud uden at vaere det.

    HVAD DER SAETTES: `abandoned_at` (koden bruger den allerede som «ude af
    spil» — se `_gentaget_paastand` og `list_active_long_term_intentions`),
    status `expired` (den terminale status der findes), og den faktiske
    `action_summary` bevaret i `blocked_reason` saa informationen ikke tabes.

    Idempotent: kun poster med tomt `outcome` OG tom `abandoned_at` roeres.
    """
    now = datetime.now(UTC).isoformat()
    lukket = 0
    set_i_alt = 0
    with _QUEUE_LOCK:
        poster = runtime_db.list_runtime_initiatives(status="acted", limit=limit)
        set_i_alt = len(poster or [])
        for post in poster or []:
            if str(post.get("outcome") or "").strip():
                continue
            if str(post.get("abandoned_at") or "").strip():
                continue
            iid = str(post.get("initiative_id") or "")
            if not iid:
                continue
            handling = str(post.get("action_summary") or "").strip()
            grund = (
                f"lukket {now[:10]}: acted uden outcome"
                + (f" — {handling}" if handling else "")
            )[:120]
            runtime_db.update_runtime_initiative(
                iid,
                status="expired",
                abandoned_at=now,
                blocked_reason=grund,
                updated_at=now,
            )
            lukket += 1
    if lukket:
        event_bus.publish(
            "heartbeat.initiatives_closed",
            {"antal": lukket, "grund": "acted uden outcome"},
        )
    return {"status": "ok", "lukket": lukket, "set": set_i_alt}


def mark_attempted(
    initiative_id: str,
    *,
    blocked_reason: str = "",
    retry_delay_minutes: int = _RETRY_DELAY_MINUTES,
    action_summary: str = "",
) -> bool:
    """Record a bounded attempt and schedule a retry if still pending."""
    now = datetime.now(UTC)
    retry_at = now + timedelta(minutes=max(retry_delay_minutes, 1))
    with _QUEUE_LOCK:
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("status") or "") != "pending":
            return False
        if str(existing.get("initiative_type") or "initiative") == "long_term_intention":
            retry_at = now + timedelta(days=_LONG_TERM_REASSESS_DAYS)
        attempt_count = int(existing.get("attempt_count") or 0) + 1
        if attempt_count >= _MAX_ATTEMPTS:
            # Loftet: forsoegt nok gange uden at nogen kunne udfoere det. Udløb
            # frem for endnu et forsoeg — ellers er det samme loekke, blot
            # langsommere (maalt: 306 gentagelser over 50 dage).
            runtime_db.update_runtime_initiative(
                initiative_id,
                attempt_count=attempt_count,
                last_attempt_at=now.isoformat(),
                status="expired",
                next_attempt_at="",
                blocked_reason=(
                    f"udloebet efter {attempt_count} forsoeg uden udfoerelse"
                )[:120],
                updated_at=now.isoformat(),
            )
            event_bus.publish(
                "heartbeat.initiative_expired",
                {
                    "initiative_id": initiative_id,
                    "focus": str(existing.get("focus") or "")[:100],
                    "attempt_count": attempt_count,
                },
            )
            return True
        runtime_db.update_runtime_initiative(
            initiative_id,
            attempt_count=attempt_count,
            last_attempt_at=now.isoformat(),
            next_attempt_at=retry_at.isoformat(),
            blocked_reason=blocked_reason[:120],
            action_summary=(
                action_summary[:200]
                if action_summary
                else str(existing.get("action_summary") or "")[:200]
            ),
            updated_at=now.isoformat(),
        )
        event_bus.publish(
            "heartbeat.initiative_attempted",
            {
                "initiative_id": initiative_id,
                "focus": str(existing.get("focus") or "")[:100],
                "attempt_count": attempt_count,
                "blocked_reason": blocked_reason[:120],
                "next_attempt_at": retry_at.isoformat(),
            },
        )
        return True


def approve_initiative(initiative_id: str, *, note: str = "") -> dict[str, object] | None:
    """Mark an initiative as user-approved. Returns the updated record or None if not found."""
    now = datetime.now(UTC).isoformat()
    result = approve_runtime_initiative(initiative_id, outcome_note=note, updated_at=now)
    if result:
        event_bus.publish(
            "heartbeat.initiative_approved",
            {
                "initiative_id": initiative_id,
                "focus": str(result.get("focus") or "")[:100],
                "note": note[:120],
            },
        )
    return result


def reject_initiative(initiative_id: str, *, note: str = "") -> dict[str, object] | None:
    """Mark an initiative as user-rejected and expire it. Returns updated record or None."""
    now = datetime.now(UTC).isoformat()
    result = reject_runtime_initiative(initiative_id, outcome_note=note, updated_at=now)
    if result:
        event_bus.publish(
            "heartbeat.initiative_rejected",
            {
                "initiative_id": initiative_id,
                "focus": str(result.get("focus") or "")[:100],
                "note": note[:120],
            },
        )
    return result


def get_initiative_queue_state() -> dict[str, object]:
    """Return full queue state for MC observability."""
    now = datetime.now(UTC)
    with _QUEUE_LOCK:
        _expire_stale(now)
        all_items = runtime_db.list_runtime_initiatives(limit=_MAX_QUEUE_SIZE + 40)
        pending = [i for i in all_items if i["status"] == "pending"]
        acted = [i for i in all_items if i["status"] == "acted"]
        declined = [i for i in all_items if i["status"] == "declined"]
        expired = [i for i in all_items if i["status"] == "expired"]
        long_term = [
            i for i in all_items
            if str(i.get("initiative_type") or "") == "long_term_intention"
            and not str(i.get("abandoned_at") or "").strip()
        ]

    approved = [i for i in all_items if str(i.get("outcome") or "") == "approved"]
    rejected = [i for i in all_items if str(i.get("outcome") or "") == "rejected"]

    return {
        "queue_size": len(all_items),
        "pending_count": len(pending),
        "acted_count": len(acted),
        "declined_count": len(declined),
        "expired_count": len(expired),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "pending": pending,
        "recent_acted": acted[:3],
        "recent_declined": declined[:3],
        "recent_approved": approved[:3],
        "recent_rejected": rejected[:3],
        "life_projects": long_term[:_MAX_ACTIVE_LONG_TERM_INTENTIONS],
        "life_project_count": len(long_term),
        "long_term_reassess_days": _LONG_TERM_REASSESS_DAYS,
        "max_queue_size": _MAX_QUEUE_SIZE,
        "expire_minutes": _EXPIRE_MINUTES,
        "retry_delay_minutes": _RETRY_DELAY_MINUTES,
    }


def _expire_stale(now: datetime) -> None:
    """Expire initiatives older than _EXPIRE_MINUTES. Must hold _QUEUE_LOCK."""
    cutoff = now - timedelta(minutes=_EXPIRE_MINUTES)
    cutoff_low = now - timedelta(minutes=_EXPIRE_MINUTES_LOW)
    for item in runtime_db.list_runtime_initiatives(
        status="pending",
        limit=_MAX_QUEUE_SIZE + 100,
    ):
        if str(item.get("initiative_type") or "initiative") == "long_term_intention":
            continue
        detected = _parse_iso(str(item.get("detected_at") or ""))
        item_cutoff = (
            cutoff_low if str(item.get("priority") or "medium") == "low" else cutoff
        )
        if detected is not None and detected < item_cutoff:
            runtime_db.update_runtime_initiative(
                str(item.get("initiative_id") or ""),
                status="expired",
                updated_at=now.isoformat(),
            )


def _trim_pending(now: datetime) -> None:
    pending = runtime_db.list_runtime_initiatives(
        status="pending",
        limit=_MAX_QUEUE_SIZE + 100,
    )
    pending = [
        item
        for item in pending
        if str(item.get("initiative_type") or "initiative") != "long_term_intention"
    ]
    pending.sort(key=_initiative_sort_key)
    for item in pending[_MAX_QUEUE_SIZE:]:
        runtime_db.update_runtime_initiative(
            str(item.get("initiative_id") or ""),
            status="expired",
            blocked_reason="queue-trimmed",
            updated_at=now.isoformat(),
        )


def _parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _initiative_due(initiative: dict[str, object], now: datetime) -> bool:
    next_attempt = str(initiative.get("next_attempt_at") or "").strip()
    if not next_attempt:
        return True
    due_at = _parse_iso(next_attempt)
    if due_at is None:
        return True
    return due_at <= now


def _initiative_sort_key(initiative: dict[str, object]) -> tuple[int, int, str]:
    priority_rank = {"high": 0, "medium": 1, "low": 2}.get(
        str(initiative.get("priority") or "medium"),
        1,
    )
    return (
        priority_rank,
        int(initiative.get("attempt_count") or 0),
        str(initiative.get("detected_at") or ""),
    )


def list_active_long_term_intentions(*, limit: int = 3) -> list[dict[str, object]]:
    items = runtime_db.list_runtime_initiatives(
        initiative_type="long_term_intention",
        limit=max(limit, 1) + 20,
    )
    active = [
        item
        for item in items
        if str(item.get("status") or "") == "pending"
        and not str(item.get("abandoned_at") or "").strip()
    ]
    active.sort(key=lambda item: str(item.get("first_seeded_at") or item.get("detected_at") or ""))
    return active[: max(limit, 1)]


def abandon_long_term_intention(initiative_id: str, *, note: str = "") -> dict[str, object] | None:
    now = datetime.now(UTC).isoformat()
    with _QUEUE_LOCK:
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("initiative_type") or "") != "long_term_intention":
            return None
        updated = runtime_db.update_runtime_initiative(
            initiative_id,
            status="expired",
            abandoned_at=now,
            blocked_reason=note[:120],
            updated_at=now,
        )
    if updated:
        event_bus.publish(
            "heartbeat.initiative_rejected",
            {
                "initiative_id": initiative_id,
                "focus": str(updated.get("focus") or "")[:100],
                "initiative_type": "long_term_intention",
                "note": note[:120],
            },
        )
    return updated


def endorse_long_term_intention(initiative_id: str, *, note: str = "") -> dict[str, object] | None:
    """Bjørn siger «det er i orden» til et livsprojekt.

    Bjørn 5/9-2026: «i mobil arbejds rum kan jeg kun vælge læg den fra dig …
    mangler det er iorden knap». Et livsprojekt er ikke en anmodning om lov —
    det er noget han HAR sat sig for. Da den eneste knap var «læg den fra dig»,
    kunne man kun forholde sig afvisende til hans langsigtede hensigter.

    Modsat abandon ændres status IKKE: projektet lever videre. Det der sættes er
    `user_approved_at` — feltet fandtes i forvejen — så det er registreret at et
    menneske har set det og sagt god for det.
    """
    now = datetime.now(UTC).isoformat()
    with _QUEUE_LOCK:
        existing = runtime_db.get_runtime_initiative(initiative_id)
        if not existing or str(existing.get("initiative_type") or "") != "long_term_intention":
            return None
        # MÅLT 7/11-2026: her blev KUN `user_approved_at` sat. `_initiative_due`
        # læser `next_attempt_at`, og `mark_attempted` skubber et livsprojekt
        # `_LONG_TERM_REASSESS_DAYS` (14) frem — så en godkendelse forkortede
        # ventetiden med nul. Feltet blev derefter kun læst i `central_hub`,
        # hvor det SKJULER spørgsmålet for Bjørn. Han godkendte de samme tre
        # livsprojekter mange gange, og det eneste der skete var at de holdt op
        # med at blive vist, indtil de dukkede op igen 14 dage senere. En
        # godkendelse er en instruks om at gå i gang nu, ikke en etiket.
        updated = runtime_db.update_runtime_initiative(
            initiative_id,
            user_approved_at=now,
            next_attempt_at=now,
            outcome_note=note[:120],
            updated_at=now,
        )
    if updated:
        event_bus.publish(
            "heartbeat.initiative_approved",
            {
                "initiative_id": initiative_id,
                "focus": str(updated.get("focus") or "")[:100],
                "initiative_type": "long_term_intention",
                "note": note[:120],
            },
        )
    return updated


def _find_active_long_term_intention_by_title(title: str) -> dict[str, object] | None:
    normalized = str(title or "").strip().lower()
    if not normalized:
        return None
    for item in runtime_db.list_runtime_initiatives(
        initiative_type="long_term_intention",
        limit=_MAX_ACTIVE_LONG_TERM_INTENTIONS + 20,
    ):
        if str(item.get("status") or "") != "pending":
            continue
        if str(item.get("abandoned_at") or "").strip():
            continue
        if str(item.get("focus") or "").strip().lower() == normalized:
            return item
    return None


# ── Awareness: hans EGNE initiativer i den synlige samtale ────────────────
_RECURRING_AFTER_DAYS = 3      # ældre end dette = han vender tilbage til det
_MAX_IN_PROMPT = 2             # hold sektionen lille (latens + cache)
_PRIO_RANK = {"high": 0, "medium": 1, "low": 2}


def initiatives_prompt_section() -> str | None:
    """Awareness-sektion: de impulser han SELV har rejst, men aldrig fik sagt.

    Rod (Bjørn, 17. aug 2026): initiativer blev kun injiceret i HEARTBEAT-prompten
    (``_heartbeat_living_context_line`` → ``[INITIATIV: …]``) — altså kun i autonome
    runs, hvor Bjørn ikke er til stede. I den faktiske samtale vidste Jarvis intet
    om sine egne initiativer. Bjørne-drømme-initiativet blev derfor rejst 130 gange
    på fire måneder (76 markeret ``acted`` = postet til en proaktivitets-kanal ingen
    læste) uden nogensinde at blive til en samtale: impulsen blev genereret, aldrig
    læst tilbage, og derfor genereret igen. Samme mønster som mål-runaway'en og
    hukommelses-ekkoet.

    ``first_seeded_at`` bærer gentagelses-signalet gratis: er den markant ældre end
    ``detected_at``, er det ikke en ny indskydelse — det er noget han bliver ved at
    vende tilbage til. Det er værd at vide FOR ham, ikke kun om ham.

    Bevidst formuleret som awareness, ikke ordre: han vælger selv om det passer nu.
    Self-safe → None ved enhver fejl (må aldrig vælte prompt-assembly).
    """
    try:
        items = get_pending_initiatives() or []
    except Exception:
        return None
    if not items:
        return None

    items = sorted(items, key=lambda i: _PRIO_RANK.get(str(i.get("priority") or "medium"), 1))
    lines: list[str] = []
    long_term_seen = False
    impulse_seen = False
    for it in items[:_MAX_IN_PROMPT]:
        focus = str(it.get("focus") or "").strip()
        if not focus:
            continue
        suffix = ""
        if str(it.get("initiative_type") or "initiative") == "long_term_intention":
            long_term_seen = True
            suffix = "  [livsprojekt — en retning, ikke en opgave]"
        else:
            impulse_seen = True
        first = str(it.get("first_seeded_at") or "").strip()
        last = str(it.get("detected_at") or "").strip()
        f_dt = _parse_iso(first) if first else None
        l_dt = _parse_iso(last) if last else None
        if f_dt and l_dt and (l_dt - f_dt) >= timedelta(days=_RECURRING_AFTER_DAYS):
            suffix += f"  [du har vendt tilbage til denne siden {f_dt.date().isoformat()}]"
        lines.append(f"  • {focus}{suffix}")

    if not lines:
        return None
    tail = ""
    if impulse_seen:
        tail += (
            "\n\nPasser en post ikke — fordi præmissen er væk, eller fordi den ikke kan "
            "efterprøves — så afvis den med `decline_initiative(id, reason=...)` og skriv "
            "grunden. Det er et gyldigt udfald, ikke en fiasko: en post der bliver liggende "
            "uden grund vender tilbage som en ny."
        )
    if long_term_seen:
        tail += (
            "\n\nEt livsprojekt er noget andet: en retning der ikke kan køres færdigt "
            "og lukkes som en task. Bærer du den ikke videre, så læg den fra dig med "
            "`abandon_initiative(id, reason=...)` og skriv grunden — det sætter samme "
            "terminale status som dommeren selv ville sætte, men med din egen "
            "begrundelse i stedet for en generisk. `decline_initiative` hører ikke her: "
            "den stempler posten som forkert, og et livsprojekt der ikke blev løftet er "
            "ikke det samme som et der ikke duede."
        )
    return (
        "Noget du selv har villet tage op (du vælger om det passer ind her):\n"
        + "\n".join(lines)
        + tail
    )
