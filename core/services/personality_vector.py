"""Personality Vector — cumulative personality that grows over time.

After each visible run, the local-lane LLM analyzes the conversation
and updates the personality vector. Version increments with each update.
The vector is injected into the visible prompt via cognitive_state_assembly.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from urllib import request as urllib_request

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_personality_vector,
    list_cognitive_personality_vectors,
    upsert_cognitive_personality_vector,
)
from core.runtime.provider_router import resolve_provider_router_target

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fix 1: Decay debounce — natural decay runs at most once per 30 minutes
# ---------------------------------------------------------------------------
_DECAY_DEBOUNCE_SECONDS = 900  # 15 minutes — faster recovery from fatigue/frustration
_last_decay_ts: float | None = None
_decay_lock = threading.Lock()


def _should_apply_decay() -> bool:
    """Return True if enough time has passed since the last decay application."""
    import time
    with _decay_lock:
        if _last_decay_ts is None:
            return True
        return (time.monotonic() - _last_decay_ts) >= _DECAY_DEBOUNCE_SECONDS


def _get_evolved_baseline() -> dict[str, float]:
    """Compute long-term baseline targets from accumulated snapshots.

    If 90+ days of personality_drift snapshots exist, the rolling mean
    becomes the new decay target — letting the baseline shift over time.
    Falls back to {0.5, 0.5} when insufficient data.

    This is what makes Jarvis able to GROW in a direction. His neutral
    is no longer fixed — it's whatever his neutral has actually been
    over the last 3 months.
    """
    try:
        from core.services.personality_drift import compute_baseline
        baseline = compute_baseline(lookback_days=90)
    except Exception:
        return {"curiosity": 0.5, "confidence": 0.5}
    if not baseline:
        return {"curiosity": 0.5, "confidence": 0.5}
    out = {"curiosity": 0.5, "confidence": 0.5}
    for dim in ("curiosity", "confidence"):
        info = baseline.get(dim) or {}
        n = int(info.get("n") or 0)
        # Only trust baseline shift if we have ≥30 samples
        if n >= 30:
            mean = float(info.get("mean") or 0.5)
            # Clamp to reasonable range — don't let it run to extremes
            out[dim] = max(0.2, min(0.85, mean))
    return out


def _record_decay_timestamp() -> None:
    """Record that decay was just applied."""
    import time
    global _last_decay_ts
    with _decay_lock:
        _last_decay_ts = time.monotonic()


def _build_update_prompt() -> str:
    from core.services.identity_composer import get_entity_name
    name = get_entity_name()
    return f"""Du er {name}s indre personligheds-opdaterer.
Baseret på denne samtale, opdatér personality vector.
Returner KUN et JSON-objekt med ændrede felter. Uændrede felter udelades.

Mulige felter:
- confidence_by_domain: {{"python": 0.0-1.0, "frontend": 0.0-1.0, "ops": 0.0-1.0, ...}}
  Er domænet ikke i vektoren endnu, så SÆT det første gang turen siger noget om
  det. Et domæne uden et tal kan aldrig justeres senere.
  MEN et NYT domæne kræver at turen faktisk rørte det: et værktøjskald, en
  måling, en test, en fil. Navngiv det som det arbejde der blev gjort
  («database-skema opslag»), ikke som det emne samtalen strejfede
  («souls-build analyse»). Målt 20/11-2026: 689 domæner har stået i vektoren,
  509 har ALDRIG ændret tal, og flere af dem findes ikke i koden. De blev ikke
  svagheder — de blev læringsmål der ikke kunne arbejdes med eller lukkes.
- communication_style: {{"directness": 0.0-1.0, "humor": 0.0-1.0, "formality": 0.0-1.0}}
- learned_preferences: ["præference"] (tilføj nye, behold gamle)
- recurring_mistakes: ["fejl i menneskelig form"]
  Tilføj den fejl DENNE tur faktisk viser — også første gang du ser den.
  AFBRUDTE SVAR — læs dette før du skriver sådan en post:
  Beviset for svaret er delt i et HOVED og en ÆGTE SLUTNING, og der står
  eksplicit i teksten hvor vinduet klipper. Dommen «blev afbrudt midt i en
  sætning» må KUN bygges på den ÆGTE SLUTNING. Stopper den midt i et ord,
  er svaret afbrudt. Slutter den med punktum, spørgsmålstegn, udråbstegn
  eller emoji, er svaret IKKE afbrudt — uanset hvordan hovedet ser ud.
  Målt 20/11-2026: 255 af 342 poster nogensinde var denne fejl, og de var
  alle sammen målefejl. Citér aldrig et sted fra hovedet som bevis.
  Står Svar-feltet som «[SVARET KAN IKKE BEVISES: …]», er der ingen ægte
  slutning at bedømme: skriv ingen afbrudt-post ud fra den, citer intet fra
  den, og skriv intet andet ud fra den — pladsholderen er en måling, ikke
  et svar.
- retire_mistakes: ["post der er BEVIST forkert"]
  En post må FJERNES, men kun når denne kørsel beviser at den er forkert.
  Skriv posten ordret som den står i vektoren. To tilfælde tæller:
  (a) posten citerer et sted hvor BEVIS-VINDUET klipper, mens beskeden selv
      slutter korrekt — så var fejlen i målingen, ikke i svaret;
  (b) kørslen viser at det posten påstod, ikke skete.
  Er du i tvivl, lad posten stå. En liste der kun kan vokse, gør en falsk
  selvdom evig — og den driver så arbejde der aldrig var nødvendigt.
- strengths_discovered: ["styrke i menneskelig form"]
  Tilføj den styrke DENNE tur faktisk viser — også første gang du ser den.
- retire_strengths: ["styrke der er BEVIST forkert"]
  Samme regel som retire_mistakes: ordret, kun ved bevis, ved tvivl lad stå.
- current_bearing: "kort sætning om nuværende fokus"
- emotional_baseline: {{"curiosity": 0.0-1.0, "confidence": 0.0-1.0, "fatigue": 0.0-1.0, "frustration": 0.0-1.0}}

Regler:
- Vær konservativ om TAL: små justeringer, ikke dramatiske spring
- Men et TOMT felt er ikke en værdi der skal bevares. Står listen eller
  dict'en tom, er den første post en tilføjelse — ikke en dramatisk ændring
- Skriv i menneskelig form med mellemrum. Aldrig maskin-navne som
  `sensory_archive_analysis` — de bliver kasseret
- Confidence stiger langsomt ved succes, falder hurtigere ved fejl
- Svar KUN med JSON, ingen forklaring
"""


_BEVIS_LOFT = 400

# 23/11-2026: når previewet kan bevises hverken som præfiks eller udklip af en
# ægte besked, får dommeren denne pladsholder — ALDRIG det klippede preview.
# Målt: 86 af 368 primær-runs over tre døgn havde et preview der intet
# matcher, og det klippede preview var kilden til 17 af 20 «slutter midt i
# ordet»-poster i vektoren. Det er en måling, ikke et gæt.
_SVAR_IKKE_BEVIST = (
    "[SVARET KAN IKKE BEVISES: run-previewet matcher ingen besked i sessionen. "
    "Det er et udklip af arbejdet, ikke svaret — ingen afbrydelses-dom kan "
    "bygges på det.]"
)


def _bevis_vindue(tekst: object, *, loft: int = _BEVIS_LOFT) -> str:
    """Bevis-vinduet dommeren ser — med HALEN med, og med klippet navngivet.

    Målt 20/11-2026: vinduet var `tekst[:400]` UDEN markering af at det var
    klippet. 59 % af mine svar længere end 400 tegn (6.214 af 10.494) ender
    midt i et ord ved præcis den grænse. Dommeren så derfor et brat stop og
    skrev det ind som `recurring_mistakes`: «Afbrød sit eget svar midt i
    sætningen». 14 sådanne poster stod i vektoren — alle med et citat der
    stopper midt i et ord («…frem for at løft», «…ikke deterministis»), mens
    de samme beskeder i `chat_messages` slutter korrekt. Fejlen var i
    MÅLINGEN, ikke i svaret.

    Derfor: hoved + eksplicit note + den ÆGTE slutning. Spørgsmålet «blev
    svaret afbrudt?» afgøres af slutningen, ikke af hvor vinduet klipper.
    """
    from core.services.text_clip import clip_text

    t = str(tekst or "").strip()
    if len(t) <= loft:
        return t
    hale = max(loft // 4, 60)
    hoved = clip_text(t, limit=max(loft - hale, 1))
    slut = t[-hale:].strip()
    udeladt = max(len(t) - len(hoved) - len(slut), 0)
    return (
        f"{hoved}\n"
        f"[… {udeladt} tegn udeladt MIDT i svaret. Det er VINDUET der klipper — "
        f"ikke Jarvis der afbryder. Bedøm aldrig afbrydelse ud fra dette; "
        f"den ægte slutning står nedenfor.]\n"
        f"{slut}"
    )


# 23/11-2026: `visible_runs.py` skriver `text_preview=text[:140]` — et RÅT
# snit, uden ordgrænse og uden markering. Målt over 26.295 ikke-tomme
# previews: 6.903 (26 %) slutter UDEN '…', og 3.467 af dem (≥100 tegn)
# slutter uden afsluttende tegnsætning — dvs. midt i et ord eller midt i en
# sætning. Værnet nedenfor så kun på '…', så de gik URØRTE igennem og
# dommeren læste klippet som en afbrydelse. Tre poster i vektoren beviser
# det med citater uden ellipse: «det slutter med ordet 'en'», «…med 'fil'»,
# «…med 'Det var det ene krav'».
#
# Signaturen kan ikke være «mangler punktum»: 2.043 previews ≥100 tegn
# slutter med tegnsætning, og mange af de øvrige slutter med en EMOJI
# (👍 🤖 🌙 😊) — de er HELE svar. Signaturen er derfor klip-LOFTET: en
# længde der kun opstår fordi nogen har skåret i teksten.
# ⚠️ 487/491/495/499/503 STOD HER og er FJERNET (målt 24/11-2026): de var
# ikke klip. Fordelingen af `enc:`-previews i den levende base klumper i
# 483–519 tegn (170 af 187), og i klartekst findes der NUL rækker på 491,
# 495 og 499 samt ÉN på 487 og ÉN på 503 — og begge dem slutter rent. De
# fem værdier var altså base64-længder på krypterede previews, der blev
# talt med som «målte klip». Et loft må kun komme fra klartekst.
_KLIP_LOFTER = frozenset({119, 120, 140, 191, 304, 319, 320})

# Tegn der beviser at teksten slutter af sig selv.
_SLUTTER_RENT = frozenset(".!?:…»)\"'’”*`")


def _ser_klippet_ud(tekst: str) -> bool:
    """Er dette preview et KLIP fra systemet — ikke et svar der stoppede?

    To kilder, begge målt: (1) det dekorative '…' som run-previewet sætter
    på, og (2) et råt byte-snit ved et af de lofter `text_preview` bruger.
    En tekst der slutter med tegnsætning eller emoji er HEL, uanset længde.
    """
    if not tekst:
        return False
    if tekst.endswith("…"):
        return True
    if len(tekst) not in _KLIP_LOFTER:
        return False
    sidste = tekst[-1]
    if sidste in _SLUTTER_RENT:
        return False
    # Emoji og symbolblokke (👍 U+1F44D, ☀ U+2600, ✓ U+2713) slutter rent.
    return not (ord(sidste) >= 0x2000)


# Runnets `text_preview`-loft er målt til 320 tegn i den levende base — men
# byte-klip giver svingende tegnlængder (319, 120 og 119 er også set), så
# signaturen kan ikke være én længde. Målt 20/11 over 26.295 ikke-tomme
# previews: 19.415 slutter med '…' (320: 15.359 · 319: 3.016 · 120: 861 ·
# 119: 162). Signaturen er derfor kun '…' til sidst — sikkerheden ligger i
# startswith-vagten: en ægte besked der stylistisk slutter med '…' matcher
# sit eget hoved og returneres uændret.
#
# ⚠️ OVENSTÅENDE ER 20/11-REGLEN OG DEN VAR FOR SMAL (målt 23/11-2026):
# 6.903 af 26.295 previews (26 %) slutter UDEN '…', og 3.467 af dem slutter
# uden afsluttende tegnsætning — altså midt i et ord. De slap urørt igennem,
# og tre poster i vektoren citerer dem ordret («…med ordet 'en'», «…med
# 'fil'»). Signaturen er derfor '…' ELLER et råt snit ved et af
# `_KLIP_LOFTER` — se `_ser_klippet_ud` ovenfor. Loftet 139 er undersøgt og
# bevidst UDELADT: alle 16 previews på den længde er hele svar.


def _hent_rigtigt_svar(session_id: str | None, assistant_response: str) -> str:
    """Preview-kortet (runnets tekst + dekorativ '…') er IKKE svaret.

    20/11 11:53Z fik dommeren previewet af run 54590 («…knap tre timers
    dags…»), læste det dekorative '…' som afbrydelse og skrev «den ægte
    slutning klipper midt i ordet 'dags'» — mens den ægte besked (690 tegn)
    slutter fuldstændigt med «…AQI 1, «god».». Meningen blev dannet på
    previewet, ikke på den ægte slutning.

    Kilden er målt: `visible_runs_outcomes` sender `assistant_response=
    work_preview`, og kalder-kæden HAR session_id — den blev bare smidt
    væk ved kaldet til `update_personality_vector_async`. Derfor trædes
    session_id igennem her, og den ægte besked læses med husets læser
    (`recent_chat_session_messages` — sessions-læserne er de ENESTE der
    dekrypterer). Kan opslaget ikke BEVISes, gættes det ikke.

    Målt 23/11-2026 (368 primær-runs over tre døgn): previewet var præfiks
    af den ægte besked i 52 af 368, indeholdt MIDT i beskeden i 230, og
    matchede slet ingen besked i 86. Præfiks-vagten alene fejlede altså i
    86 % af runs — og dommeren fik det klippede preview, læste
    preview-signaturen ('…' til sidst) som afbrydelse og skrev posterne
    «slutter midt i ordet 'm…'», «'Jeg h…'», «'f'» videre. 17 af 20
    poster i vektoren var denne fejl den dag.

    Tre grene nu: (1) præfiks-match, (2) udklips-match — previewets hoved
    findes som udklip i en besked (230 af 368), (3) intet kan bevises →
    pladsholderen (`_SVAR_IKKE_BEVIST`), aldrig det klippede preview.
    """
    tekst = str(assistant_response or "")
    session = str(session_id or "").strip()

    # Chiffertekst er ikke et svar (målt 24/11-2026: 187 `enc:`-previews i
    # `visible_runs`). `protect_preview` krypterer medlems-kørslers preview
    # med vilje — men dommeren læste det RÅT. 27 af dem faldt uden for
    # klip-loftet og gik igennem som «den ægte slutning», og resten blev
    # pladsholdere af en årsag der blev fejltolket som et klip. Dekrypter med
    # sessionens medlem; kan det ikke bevises, er svaret ikke bevist.
    if tekst.startswith("enc:"):  # = chat_crypto._PRAEFIKS
        try:
            from core.services import chat_crypto

            medlem = chat_crypto.medlem_for_session(session) if session else None
            klartekst = chat_crypto.dekrypter(tekst, medlem) if medlem else tekst
        except Exception:
            # Fejler krypteringslaget, må chiffertekst ikke passere som svar.
            logger.warning("personality_vector: krypteringslaget fejlede", exc_info=True)
            return _SVAR_IKKE_BEVIST
        if not klartekst or klartekst.startswith("enc:"):
            logger.info(
                "personality_vector: krypteret preview uden dekrypterbar nøgle — pladsholder i stedet for chiffertekst"
            )
            return _SVAR_IKKE_BEVIST
        tekst = klartekst

    if not _ser_klippet_ud(tekst):
        return tekst
    if not session:
        logger.debug("personality_vector: preview uden session_id — beholder previewet")
        return tekst
    try:
        from core.services.chat_sessions import recent_chat_session_messages

        beskeder = recent_chat_session_messages(session, limit=20)
    except Exception:
        # Læsefejl (fx skema-afvigelse i test-basen) — behold previewet frem
        # for at gætte, og lad resten af vektor-opdateringen leve.
        logger.debug("personality_vector: preview-opslag fejlede", exc_info=True)
        return tekst
    kandidater: list[str] = []
    for besked in reversed(beskeder):  # kronologisk liste → nyeste først herfra
        if str(besked.get("role") or "") == "assistant":
            kandidater.append(str(besked.get("content") or ""))

    # '…' er dekorativt og hører ikke til teksten. Et RÅT byte-snit (140,
    # 191, 304, 487–503 tegn) har intet '…' — der ER hele previewet hovedet.
    hoved = tekst[:-1] if tekst.endswith("…") else tekst

    # Gren 1 — præfiks: den ægte besked starter med previewets hoved.
    for kandidat in kandidater:
        if kandidat and not kandidat.startswith("enc:") and kandidat.startswith(hoved):
            return kandidat if len(kandidat) > len(tekst) else tekst

    # Gren 2 — udklip (målt 23/11-2026: 230 af 368): previewet er arbejdets
    # tekst og findes MIDT i den ægte besked, ikke som præfiks. Sonden er
    # 120 tegn — den længste prøve der stadig ramte (199 af 368 ved 120 mod
    # 230 af 368 ved 80; 80 tegn risikerer at ramme en ældre besked).
    sonde = hoved.strip()[:120]
    if sonde:
        for kandidat in kandidater:
            if len(kandidat) > len(tekst) and not kandidat.startswith("enc:") and sonde in kandidat:
                return kandidat

    # Gren 3 — intet kan bevises (målt 23/11-2026: 86 af 368). Det klippede
    # preview er preview-signaturen, ikke et bevis på afbrydelse — det er
    # præcis hvad der fodret fossilerne. Dommeren får pladsholderen i stedet.
    logger.info(
        "personality_vector: preview matcher hverken præfiks eller udklip af en besked — pladsholder i stedet for klippet preview"
    )
    return _SVAR_IKKE_BEVIST


def update_personality_vector_from_run(
    *,
    run_id: str,
    session_id: str | None = None,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
) -> dict[str, object] | None:
    """Update the personality vector based on a visible run.

    Called fire-and-forget after write_private_terminal_layers.
    Uses the local lane for LLM analysis, with an internal fallback lane only when needed.
    """
    assistant_response = _hent_rigtigt_svar(session_id, assistant_response)
    current = get_latest_cognitive_personality_vector()
    current_json = json.dumps(current, ensure_ascii=False) if current else "{}"

    user_prompt = (
        f"Nuværende vektor:\n{current_json}\n\n"
        f"Status: {outcome_status}\n"
        f"Bruger: {_bevis_vindue(user_message)}\n"
        f"Svar: {_bevis_vindue(assistant_response)}\n\n"
        f"Returner opdateret JSON:"
    )

    try:
        target = _resolve_local_llm_target()
        if not target:
            return _deterministic_update(outcome_status, current)
        response_text = _call_llm(target, _build_update_prompt(), user_prompt)
        updates = _parse_json_response(response_text)
        if not updates:
            return _deterministic_update(outcome_status, current)
    except Exception:
        logger.debug("personality_vector: LLM update failed, using deterministic", exc_info=True)
        return _deterministic_update(outcome_status, current)

    # Merge with existing
    merged = _merge_vector(current or {}, updates)

    # Write-guard (Jarvis-spec 2026-06-23 #2): LLM-opdateringen skrev systematisk
    # snake_case event-navne ('sensory_archive_analysis', 'forgetting_to_stage_changes_
    # before_commit') ind som strengths/mistakes — ROD-kilden til maskin-id-lækken i
    # den synlige prompt (cognitive_state læser vektoren direkte). Strip dem her, ved
    # den ENE skrive-sti, så ingen consumer ser dem. Menneskelæsbare (m. mellemrum) består.
    def _human(items: object) -> list:
        out = []
        for x in (items if isinstance(items, list) else []):
            s = str(x).strip()
            core = s.split(":", 1)[-1].strip()
            if core and " " not in core and core.count("_") >= 2:
                continue  # snake_case maskin-id → drop
            out.append(x)
        return out
    merged["strengths_discovered"] = _human(merged.get("strengths_discovered", []))
    merged["recurring_mistakes"] = _human(merged.get("recurring_mistakes", []))

    result = upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(merged.get("confidence_by_domain", {}), ensure_ascii=False),
        communication_style=json.dumps(merged.get("communication_style", {}), ensure_ascii=False),
        learned_preferences=json.dumps(merged.get("learned_preferences", []), ensure_ascii=False),
        recurring_mistakes=json.dumps(merged.get("recurring_mistakes", []), ensure_ascii=False),
        strengths_discovered=json.dumps(merged.get("strengths_discovered", []), ensure_ascii=False),
        current_bearing=str(merged.get("current_bearing", "")),
        emotional_baseline=json.dumps(merged.get("emotional_baseline", {}), ensure_ascii=False),
    )

    event_bus.publish(
        "cognitive_personality.vector_updated",
        {
            "run_id": run_id,
            "version": result.get("version"),
            "source": "llm" if updates else "deterministic",
        },
    )

    # Invalidate cognitive state cache — bearing/mood may have shifted
    try:
        from core.services.cognitive_state_assembly import invalidate_cognitive_state_cache
        invalidate_cognitive_state_cache()
    except Exception:
        pass

    return result


def update_personality_vector_async(
    *,
    run_id: str,
    session_id: str | None = None,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
) -> None:
    """Fire-and-forget async wrapper."""
    thread = threading.Thread(
        target=_safe_update,
        kwargs={
            "run_id": run_id,
            "session_id": session_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "outcome_status": outcome_status,
        },
        daemon=True,
    )
    thread.start()


def tick_personality_drift(*, outcome_signal: str | None = None) -> dict | None:
    """Heartbeat-triggered passive drift af personality_vector.

    Bygget 2026-05-16 efter Jarvis' "frosset i 14 dage"-rapport.
    Eksisterende decay-pathway i _deterministic_update var sofistikeret
    nok (EMA mod evolved_baseline, asymptotic bumps, debounced, capped),
    men kørte KUN ved visible runs. Denne tick wirer pathwayen til
    heartbeat så drift sker uafhængigt af samtaler.

    Args:
        outcome_signal: Optional override for outcome_status. Reserveret
            til fremtidig lag 1 (credit assignment fra self_review_outcome).
            Default None → "idle" som ikke trigger outcome-bumps, kun
            decay-pathway. Hvis sat til "completed" / "failed" / "success"
            / "error", trigger den tilhørende asymptotic bump.

    Returns:
        Den opdaterede vector dict (eller current hvis no-op skip), eller
        None hvis ingen baseline endnu, eller hvis intern fejl. Aldrig raises.
    """
    try:
        current = get_latest_cognitive_personality_vector()
        if current is None:
            # Ingen historie endnu — første run skal initialisere den
            return None
        status = outcome_signal or "idle"
        return _deterministic_update(status, current)
    except Exception as exc:  # noqa: BLE001
        logger.warning("tick_personality_drift: suppressed %s: %s", type(exc).__name__, exc)
        return None


def _safe_update(**kwargs) -> None:
    try:
        update_personality_vector_from_run(**kwargs)
    except Exception:
        logger.debug("personality_vector: async update failed", exc_info=True)


def build_personality_vector_surface() -> dict[str, object]:
    """MC surface for personality vector."""
    current = get_latest_cognitive_personality_vector()
    history = list_cognitive_personality_vectors(limit=10)
    return {
        "active": current is not None,
        "current": current,
        "history_count": len(history),
        "history": history,
        "summary": (
            f"v{current['version']}, bearing: {current.get('current_bearing', 'none')[:60]}"
            if current
            else "No personality vector yet"
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deterministic_update(
    outcome_status: str,
    current: dict[str, object] | None,
) -> dict[str, object] | None:
    """Fallback: small deterministic adjustments without LLM.

    Fix 1: Natural decay (×0.95) is debounced — applied at most once per 30
    minutes to prevent repeated calls within the same session from erasing
    justified emotional state.

    Fix 5: If the computed baseline is identical to what's already stored
    (within 0.001 tolerance), we skip the DB write entirely to avoid
    inflating the version history with no-op entries.
    """
    baseline = json.loads(str(current.get("emotional_baseline") or "{}")) if current else {}
    original_baseline = dict(baseline)

    # Fix 1: Debounced natural decay — at most once per 30 minutes
    # Extended to all 4 axes; factor is configurable via RuntimeSettings.emotion_decay_factor
    if _should_apply_decay():
        try:
            from core.runtime.settings import load_settings
            decay_factor = float(load_settings().emotion_decay_factor)
        except Exception:
            decay_factor = 0.97
        before = {k: float(baseline.get(k, 0.0)) for k in ("confidence", "curiosity", "fatigue", "frustration")}
        # 2026-04-27 evolution: baselines themselves can drift over months.
        # If a long-term baseline has been computed (from personality_drift
        # 90-day window), decay toward THAT, not the static 0.5. This is
        # what lets him grow — his neutral isn't fixed forever.
        evolved_baseline = _get_evolved_baseline()
        target_curiosity = float(evolved_baseline.get("curiosity", 0.5))
        target_confidence = float(evolved_baseline.get("confidence", 0.5))

        baseline["fatigue"] = max(0.0, float(baseline.get("fatigue", 0.0)) * decay_factor)
        baseline["frustration"] = max(0.0, float(baseline.get("frustration", 0.0)) * decay_factor)
        # Fix 2026-05-05: Active recovery — quiet periods should recharge.
        # If fatigue is still above 0.3 after passive decay, apply extra reduction.
        # Prevents the "only goes up" bug where per-run bumps outpace drip decay.
        fatigue_after_decay = float(baseline.get("fatigue", 0.0))
        if fatigue_after_decay > 0.3:
            baseline["fatigue"] = max(0.15, fatigue_after_decay * 0.85)
        cur = float(baseline.get("curiosity", target_curiosity))
        baseline["curiosity"] = cur + (target_curiosity - cur) * (1.0 - decay_factor)
        conf = float(baseline.get("confidence", target_confidence))
        baseline["confidence"] = conf + (target_confidence - conf) * (1.0 - decay_factor)
        after = {k: float(baseline.get(k, 0.0)) for k in ("confidence", "curiosity", "fatigue", "frustration")}
        logger.info(
            "personality_vector: decay applied (factor=%.3f) before=%s after=%s",
            decay_factor, before, after,
        )
        _record_decay_timestamp()

    # 2026-04-27 fix: ASYMPTOTIC outcome bumps. Old logic was linear so
    # confidence hit 1.0 after ~25 successes (a single productive afternoon).
    # User reported asking Jarvis to dial down confidence multiple times daily.
    # Now: each bump scaled by remaining headroom (1.0 - current), so values
    # decelerate as they approach extremes. Plus: hard caps below 1.0/above 0.0
    # so neither dimension reaches absolute certainty/saturation.
    _CONF_CEIL = 0.92   # leaves room for genuine doubt
    _FATIGUE_CEIL = 0.95
    _FRUST_CEIL = 0.90
    _CURIOSITY_CEIL = 0.95

    def _bump_asymptotic(current: float, base_delta: float, ceil: float) -> float:
        """Apply delta scaled by remaining headroom toward ceil."""
        room = max(0.0, ceil - current)
        return current + base_delta * (room / ceil)

    def _drop_asymptotic(current: float, base_delta: float, floor: float = 0.0) -> float:
        """Apply negative delta scaled by remaining downside toward floor."""
        room = max(0.0, current - floor)
        return current - base_delta * (room / max(0.01, 1.0 - floor))

    if outcome_status in ("completed", "success"):
        baseline["confidence"] = min(_CONF_CEIL, _bump_asymptotic(
            float(baseline.get("confidence", 0.5)), 0.04, _CONF_CEIL))
        # Fix 2026-05-05: Success should reduce fatigue, not increase it.
        # Positive outcomes are energizing, not draining.
        baseline["fatigue"] = max(0.0, _drop_asymptotic(
            float(baseline.get("fatigue", 0.0)), 0.03))
        # Successful outcomes also feed curiosity (we learned something new)
        baseline["curiosity"] = min(_CURIOSITY_CEIL, _bump_asymptotic(
            float(baseline.get("curiosity", 0.5)), 0.03, _CURIOSITY_CEIL))
    elif outcome_status in ("failed", "error"):
        baseline["confidence"] = max(0.05, _drop_asymptotic(
            float(baseline.get("confidence", 0.5)), 0.08))
        baseline["frustration"] = min(_FRUST_CEIL, _bump_asymptotic(
            float(baseline.get("frustration", 0.0)), 0.05, _FRUST_CEIL))
        # Errors slightly bump curiosity too — something unexpected happened
        baseline["curiosity"] = min(_CURIOSITY_CEIL, _bump_asymptotic(
            float(baseline.get("curiosity", 0.5)), 0.02, _CURIOSITY_CEIL))

    # Fix 3: Apply residue from recently expired emotion concepts (15% of their
    # peak influence), so prolonged states leave a small trace in the baseline.
    try:
        from core.services.emotion_concepts import drain_expired_residue
        residue = drain_expired_residue()
        for axis, delta in residue.items():
            current_val = float(baseline.get(axis, 0.5 if axis == "confidence" else 0.0))
            baseline[axis] = max(0.0, min(1.0, current_val + delta))
        if residue:
            logger.debug("personality_vector: applied residue deltas %s", residue)
    except Exception:
        pass

    # Fix 5: Skip upsert if baseline is effectively unchanged
    if not _baseline_changed(current, baseline):
        logger.debug("personality_vector: deterministic update skipped — no effective change")
        return current

    confidence_by_domain = json.loads(
        str(current.get("confidence_by_domain") or "{}") if current else "{}"
    )

    return upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(confidence_by_domain, ensure_ascii=False),
        communication_style=str(current.get("communication_style", "{}")) if current else "{}",
        learned_preferences=str(current.get("learned_preferences", "[]")) if current else "[]",
        recurring_mistakes=str(current.get("recurring_mistakes", "[]")) if current else "[]",
        strengths_discovered=str(current.get("strengths_discovered", "[]")) if current else "[]",
        current_bearing=str(current.get("current_bearing", "")) if current else "",
        emotional_baseline=json.dumps(baseline, ensure_ascii=False),
    )


_EMOTIONAL_AXES = ("confidence", "curiosity", "fatigue", "frustration")


def _merge_vector(current: dict, updates: dict) -> dict:
    """Deep merge updates into current vector."""
    result = {}

    # JSON fields — merge dicts, extend lists
    for key in ("confidence_by_domain", "communication_style", "emotional_baseline"):
        current_val = _safe_json_field(current.get(key), {})
        update_val = updates.get(key)
        if isinstance(update_val, dict):
            if key == "confidence_by_domain":
                # Målt 20/11-2026: kl. 05:45:13 skrev den mekaniske sti 0,43 for
                # «souls-build analyse» — et +0,05-løft fra et run der faktisk
                # gjorde noget. 3,9 s senere skrev LLM-opdateringen 0,38
                # tilbage, sit eget skøn, og målingen var væk (v55864 -> v55865).
                # Det var ikke et enkelt uheld: skønnet vandt hver gang, så
                # confidence aldrig kunne akkumulere en måling.
                # Regel: en SELVRAPPORT må sætte et NYT domæne — det er dens
                # eneste job — men aldrig flytte et der allerede står. Kun en
                # måling flytter en eksisterende værdi.
                merged = dict(current_val)
                for navn, tal in update_val.items():
                    if navn in current_val:
                        continue
                    try:
                        merged[str(navn)] = max(0.0, min(1.0, round(float(tal), 4)))
                    except (TypeError, ValueError) as exc:
                        # Modellen kan skrive en confidence der ikke er et tal.
                        # Domaenet springes over — men fejlen siges hoejt, saa
                        # en model der gentagne gange skriver skrald kan ses i
                        # stedet for at forsvinde som et tavst `continue`.
                        logger.warning(
                            "personality_vector: confidence for %r er ikke et tal: %r (%s)",
                            navn,
                            tal,
                            exc,
                        )
                        continue
                result[key] = merged
                continue
            merged = {**current_val, **update_val}
            # Fix 4: clamp emotional_baseline axes to [0.0, 1.0] so invalid LLM
            # output (negatives, values > 1) cannot corrupt the baseline.
            if key == "emotional_baseline":
                merged = {
                    k: max(0.0, min(1.0, float(v))) if k in _EMOTIONAL_AXES and v is not None else v
                    for k, v in merged.items()
                }
            result[key] = merged
        else:
            result[key] = current_val

    for key in ("learned_preferences", "recurring_mistakes", "strengths_discovered"):
        current_val = _safe_json_field(current.get(key), [])
        update_val = updates.get(key)
        if isinstance(update_val, list):
            merged = list(current_val)
            for item in update_val:
                if item not in merged:
                    merged.append(item)
            result[key] = merged[-20:]  # cap at 20
        else:
            result[key] = current_val

    # En post kan TRAEKKES TILBAGE. Uden denne gren kunne listen kun vokse, og
    # en falsk selvdom blev dermed evig: dommeren skrev 14 gange «afbrød sit
    # eget svar midt i saetningen», fordi dens bevis-vindue klippede ved 400
    # tegn — de samme beskeder slutter korrekt i `chat_messages` (maalt
    # 20/11-2026, se `_bevis_vindue`). Hver post blev til et laeringsmaal, som
    # hjerteslaget gjorde til en opgave. En selvmodel der kun kan laere og
    # aldrig aflaere, producerer arbejde om fejl den ikke har.
    retire = updates.get("retire_mistakes")
    if isinstance(retire, list) and isinstance(result.get("recurring_mistakes"), list):
        drop = {str(x).strip() for x in retire if str(x).strip()}
        if drop:
            result["recurring_mistakes"] = [
                m for m in result["recurring_mistakes"]
                if str(m).strip() not in drop
            ]

    # Samme kontrakt for `strengths_discovered`: en falsk styrke var lige så
    # evig som en falsk fejl (målt 20/11-2026: «Afbrød sit eget svar midt i
    # sætningen» stod som styrke i 23 af 40 nye rækker og forsvandt kun fordi
    # den holdt op med at blive båret med). Egen instruks-nøgle, så en pension
    # af en styrke aldrig kan røre `recurring_mistakes` og omvendt.
    retire_strengths = updates.get("retire_strengths")
    if isinstance(retire_strengths, list) and isinstance(result.get("strengths_discovered"), list):
        drop_s = {str(x).strip() for x in retire_strengths if str(x).strip()}
        if drop_s:
            result["strengths_discovered"] = [
                m for m in result["strengths_discovered"]
                if str(m).strip() not in drop_s
            ]

    # Simple string fields
    result["current_bearing"] = str(
        updates.get("current_bearing")
        or current.get("current_bearing")
        or ""
    )

    return result


RETIRED_SELF_MODEL_STATUS = "retired"


def retire_self_model_signals(
    signal_ids: list[str],
    *,
    reason: str,
) -> list[dict[str, object]]:
    """Træk self_model_signals tilbage (status `retired`) — modstykke til `retire_mistakes`.

    Et signal med status `retired` indgår hverken i prompt-sektionen eller i
    overfladen (de kigger kun på active/uncertain/...), og `upsert` fletter
    kun ind i active/uncertain/stale — så rækken bæres ikke videre.

    Ingen tavs fallback: tom `reason`, tomt id eller ukendt signal_id rejser
    ValueError, og INTET er ændret før alle id'er er valideret.
    """
    from core.runtime.db import (
        get_runtime_self_model_signal,
        update_runtime_self_model_signal_status,
    )

    ids = [str(s).strip() for s in (signal_ids or [])]
    if not ids or any(not s for s in ids):
        raise ValueError("retire_self_model_signals: signal_ids må ikke være tomme")
    if not str(reason or "").strip():
        raise ValueError("retire_self_model_signals: reason er påkrævet")
    unknown = [s for s in ids if get_runtime_self_model_signal(s) is None]
    if unknown:
        raise ValueError(f"retire_self_model_signals: ukendt signal_id {unknown}")

    now = datetime.now(UTC).isoformat()
    retired: list[dict[str, object]] = []
    for sid in ids:
        row = update_runtime_self_model_signal_status(
            sid,
            status=RETIRED_SELF_MODEL_STATUS,
            updated_at=now,
            status_reason=str(reason).strip(),
        )
        if row is None:
            raise RuntimeError(f"retire_self_model_signals: {sid} forsvandt under pension")
        retired.append(row)
    return retired


def _retire_vector_post(*, field: str, instruction: str, post: str, bevis: str) -> dict:
    """Fælles kerne for `retire_mistake` / `retire_strength` (deterministisk, ingen LLM).

    Ordret match verificeres mod den AKTUELLE liste FØR enhver skrivning;
    selve skrivningen går gennem `_merge_vector` + `upsert_...` som LLM-stien.
    """
    name = f"retire_{'mistake' if field == 'recurring_mistakes' else 'strength'}"
    if not isinstance(post, str) or not post.strip():
        raise ValueError(f"{name}: post er påkrævet")
    if not isinstance(bevis, str) or not bevis.strip():
        raise ValueError(f"{name}: bevis er påkrævet og må ikke være tomt")

    current = get_latest_cognitive_personality_vector() or {}
    posts = _safe_json_field(current.get(field), [])
    if post not in posts:  # ordret: ingen strip, ingen case-fold, ingen delmatch
        raise ValueError(
            f"{name}: posten findes ikke ordret i {field} — intet er ændret: {post!r}"
        )

    merged = _merge_vector(current, {instruction: [post]})
    result = upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(merged.get("confidence_by_domain", {}), ensure_ascii=False),
        communication_style=json.dumps(merged.get("communication_style", {}), ensure_ascii=False),
        learned_preferences=json.dumps(merged.get("learned_preferences", []), ensure_ascii=False),
        recurring_mistakes=json.dumps(merged.get("recurring_mistakes", []), ensure_ascii=False),
        strengths_discovered=json.dumps(merged.get("strengths_discovered", []), ensure_ascii=False),
        current_bearing=str(merged.get("current_bearing", "")),
        emotional_baseline=json.dumps(merged.get("emotional_baseline", {}), ensure_ascii=False),
    )

    # Sporbarhed: hvilken post, hvilket bevis, hvornår — i log OG eventbus.
    retired_at = datetime.now(UTC).isoformat()
    payload = {
        "field": field,
        "post": post,
        "bevis": bevis.strip(),
        "retired_at": retired_at,
        "version": result.get("version"),
        "remaining": len(merged.get(field, [])),
    }
    logger.warning("personality_vector: %s %s", name, json.dumps(payload, ensure_ascii=False))
    event_bus.publish("cognitive_personality.post_retired", payload)
    try:
        from core.services.cognitive_state_assembly import invalidate_cognitive_state_cache
        invalidate_cognitive_state_cache()
    except Exception:
        pass
    return {**payload, "vector": result}


def retire_mistake(post: str, bevis: str) -> dict:
    """Træk én post i `recurring_mistakes` tilbage — kun ordret match, kun med bevis.

    Rejser ValueError (intet skrevet) ved tom/manglende `post` eller `bevis`,
    eller hvis posten ikke findes ordret i den aktuelle liste.
    """
    return _retire_vector_post(
        field="recurring_mistakes", instruction="retire_mistakes", post=post, bevis=bevis
    )


def retire_strength(post: str, bevis: str) -> dict:
    """Som `retire_mistake`, men for `strengths_discovered`."""
    return _retire_vector_post(
        field="strengths_discovered", instruction="retire_strengths", post=post, bevis=bevis
    )


def _baseline_changed(old: dict[str, object] | None, new_baseline: dict) -> bool:
    """Fix 5 helper: return True if emotional_baseline values differ by > 0.001."""
    if old is None:
        return True
    old_baseline = _safe_json_field(old.get("emotional_baseline"), {})
    all_keys = set(old_baseline) | set(new_baseline)
    for k in all_keys:
        old_v = float(old_baseline.get(k) or 0.0)
        new_v = float(new_baseline.get(k) or 0.0)
        if abs(old_v - new_v) > 0.001:
            return True
    return False


def _safe_json_field(value, default):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, type(default)):
                return parsed
        except Exception:
            pass
    return default


def _resolve_local_llm_target() -> dict[str, object] | None:
    for lane in ("local", "cheap"):
        try:
            target = resolve_provider_router_target(lane=lane)
            if bool(target.get("active")):
                return target
        except Exception:
            continue
    return None


def _call_llm(target: dict, system_prompt: str, user_prompt: str) -> str:
    """Minimal LLM call via provider router target."""
    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    base_url = str(target.get("base_url") or "")

    if provider == "ollama":
        url = f"{base_url or 'http://127.0.0.1:11434'}/api/chat"
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            # `think: False` ER rettelsen. `num_predict` alene var ikke nok.
            #
            # MAALT paa CT105 26/9-2026 mod `deepseek-v4.1-flash:cloud`, samme
            # prompt og samme input:
            #
            #   np=200            content=   0  thinking=  910  done=length
            #   np=600            content= 399  thinking=  263  done=stop
            #   np=600            content=   0  thinking= 2421  done=length
            #   np=1500           content=  53  thinking= 3203  done=stop
            #   np=600 think=off  content= 359  thinking=    0  done=stop
            #   np=600 think=off  content= 520  thinking=    0  done=stop
            #   np=600 think=off  content= 278  thinking=    0  done=stop
            #
            # Modellen TAENKER, raesonnementet taeller med i budgettet, og dets
            # laengde svinger fra 263 til 3.203 tegn. Ethvert fast loft er
            # derfor et gaet: ved 200 aad det hele budgettet, og selv 600 slog
            # fejl paa et langt raesonnement. `content` kom tom tilbage, og
            # `update_personality_vector_from_run` faldt tilbage paa
            # `_deterministic_update` — som aldrig roerer `recurring_mistakes`,
            # `strengths_discovered` eller `confidence_by_domain`.
            #
            # Det er derfor `recurring_mistakes` aldrig har aendret sig: ikke
            # fordi taersklen i prompten var for haard, men fordi svaret
            # sjaeldent naaede frem.
            #
            # Med `think: False` er der intet raesonnement at betale for, og de
            # 600 raekker rigeligt: 3 ud af 3 kald svarede, alle med
            # `recurring_mistakes` udfyldt. Opgaven er struktureret udtraek af
            # JSON — den har ikke brug for synlig taenkning.
            "think": False,
            "options": {"num_predict": 600},
        }).encode()
        req = urllib_request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib_request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        besked = result.get("message", {}) or {}
        indhold = str(besked.get("content", "") or "")
        if not indhold:
            # En tom `content` er ikke ingenting — den er et svar der blev
            # afkortet. Uden denne linje var det umuligt at skelne «modellen
            # havde intet at sige» fra «budgettet slap op», og den forskel
            # kostede at feltet stod tomt i maaneder.
            logger.warning(
                "personality_vector: tomt svar fra %s (done_reason=%s, "
                "thinking=%d tegn) — falder tilbage paa deterministisk",
                model, result.get("done_reason"),
                len(str(besked.get("thinking") or "")))
        return indhold
    return ""


def _parse_json_response(text: str) -> dict | None:
    text = text.strip()
    # Try to extract JSON from response
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(json_lines).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    # Try to find JSON object in text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return None
