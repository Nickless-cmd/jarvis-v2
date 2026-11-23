"""Behavioral decisions — closing the reflection→behavior loop.

A reflection says "I should stop X". A decision is the durable
commitment: "from now on, when Y happens, do Z." This service:

- Lets Jarvis record, review, and revoke commitments via tools.
- Publishes events (decision.created/.updated/.reviewed/.revoked)
  so MC can project adherence.
- Surfaces active decisions in the heartbeat prompt every cycle,
  so Jarvis actually feels his own commitments instead of forgetting
  them the moment the conversation ends.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_decisions import (
    append_review,
    count_decisions,
    create_decision as _db_create,
    delete_decision as _db_delete,
    get_decision as _db_get,
    list_decisions as _db_list,
    list_reviews,
    set_status as _db_set_status,
    update_decision as _db_update_decision,
)

logger = logging.getLogger(__name__)


def _normalize_directive(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _commit_observe(outcome: str, decision_id: Any) -> None:
    """Commit-cluster instrument: decision_create → central observe (best-effort)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "commit", "nerve": "decision_create",
            "outcome": outcome, "decision_id": str(decision_id or ""),
        })
    except Exception:
        pass


# Hvor længe efter en revoke et direktiv stadig er lukket for genoprettelse.
#
# Revoke SKAL frigive direktivet — ellers kan en beslutning aldrig
# genoprettes. Men det åbnede et loop: en auto-generator kunne skrive
# opret → revoke → opret i det uendelige, og samme sætning endte med at
# stå 27 gange i tabellen (3/5 → 9/7-2026). Inden for vinduet dedupes der
# mod den revokede række i stedet for at oprette en ny.
_REVOKE_REOPEN_COOLDOWN = timedelta(hours=24)


def _recently_revoked(normalized: str) -> dict[str, Any] | None:
    """En revokeret beslutning med samme direktiv, revokeret for nylig."""
    cutoff = (datetime.now(UTC) - _REVOKE_REOPEN_COOLDOWN).isoformat()
    for existing in _db_list(status="revoked", limit=None):
        if _normalize_directive(str(existing.get("directive") or "")) != normalized:
            continue
        if str(existing.get("updated_at") or "") >= cutoff:
            return existing
    return None


def _dedup_result(
    existing: dict[str, Any], reason: str, source_type: str | None
) -> dict[str, Any]:
    """Returnér den række der allerede dækker direktivet — uden at oprette."""
    deduped = dict(existing)
    deduped["deduped"] = True
    deduped["dedupe_reason"] = reason
    try:
        event_bus.publish(
            "decision.deduped",
            {
                "decision_id": deduped.get("decision_id"),
                "directive": deduped.get("directive"),
                "priority": deduped.get("priority"),
                "source_type": source_type,
                "reason": reason,
            },
        )
    except Exception as exc:
        logger.debug("behavioral_decisions: publish deduped failed: %s", exc)
    _commit_observe("deduped", deduped.get("decision_id"))
    return deduped


def create_decision(
    *,
    directive: str,
    rationale: str | None = None,
    trigger_cue: str | None = None,
    priority: int = 50,
    source_record_id: str | None = None,
    source_type: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_directive(directive)

    # Ingen loft her. Et limit=100 var aldrig en semantisk grænse — den slap
    # igennem som default, og når tabellen voksede forbi loftet så dedup'en
    # ikke længere alle aktive, så samme direktiv blev oprettet i dublet.
    for existing in _db_list(status="active", limit=None):
        if _normalize_directive(str(existing.get("directive") or "")) == normalized:
            return _dedup_result(existing, "active-directive-already-exists", source_type)

    recent = _recently_revoked(normalized)
    if recent is not None:
        return _dedup_result(recent, "directive-revoked-within-cooldown", source_type)

    decision = _db_create(
        directive=directive,
        rationale=rationale,
        trigger_cue=trigger_cue,
        priority=priority,
        source_record_id=source_record_id,
        source_type=source_type,
        created_by=created_by,
    )
    try:
        event_bus.publish(
            "decision.created",
            {
                "decision_id": decision.get("decision_id"),
                "directive": decision.get("directive"),
                "priority": decision.get("priority"),
                "source_type": decision.get("source_type"),
            },
        )
    except Exception as exc:
        logger.debug("behavioral_decisions: publish created failed: %s", exc)
    _commit_observe("created", decision.get("decision_id"))
    return decision


def review_decision(
    *,
    decision_id: str,
    verdict: str,
    note: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any] | None:
    result = append_review(
        decision_id=decision_id,
        verdict=verdict,
        note=note,
        evidence=evidence,
    )
    if not result:
        return None
    try:
        event_bus.publish(
            "decision.reviewed",
            {
                "decision_id": result.get("decision_id"),
                "directive": result.get("directive"),
                "verdict": verdict,
                "adherence_score": result.get("adherence_score"),
            },
        )
    except Exception as exc:
        logger.debug("behavioral_decisions: publish reviewed failed: %s", exc)

    # Beslutnings-sporet. `decision_ghosts` havde INGEN kalder, selv om
    # `record_reaffirmed_decision`s egen docstring sagde «Called from
    # behavioral_decision_review when verdict is kept or partial» (25/9-2026).
    #
    # Her er de rigtige tal: dommen og `adherence_score`. Modulet trak dem af
    # en terning foer — `random.uniform(0.1, 0.6)` — og valgte saa den «mest
    # saliente» fortrydelse ved det hoejeste kast.
    try:
        from core.services import decision_ghosts as _spor
        _score = result.get("adherence_score")
        _titel = str(result.get("directive") or "")
        _id = str(result.get("decision_id") or "")
        if verdict in {"kept", "partial", "fulfilled"}:
            _spor.record_reaffirmed_decision(_id, _titel, verdict, adherence_score=_score)
        elif verdict == "broken":
            _spor.record_broken_decision(_id, _titel, adherence_score=_score,
                                         note=str(note or ""))
    except Exception as exc:  # et spor maa aldrig kunne vaelte en gennemgang
        logger.debug("decision_ghosts: sporet kunne ikke gemmes: %s", exc)
    return result


def update_decision(
    decision_id: str,
    *,
    directive: str | None = None,
    rationale: str | None = None,
    trigger_cue: str | None = None,
    trigger_name: str | None = None,
    priority: int | None = None,
    status: str | None = None,
    revoked_reason: str | None = None,
    revoked_evidence: str | None = None,
) -> dict[str, Any] | None:
    """Update a decision's mutable fields (None = unchanged, "" = cleared).

    Thin wrapper over the store that publishes ``decision.updated`` so
    downstream (MC projections, commitment instruments) stay in sync.

    Sættes ``status='revoked'`` kræves ``revoked_reason`` — ellers kan en
    politik forsvinde ud af prompten uden at nogen kan se hvorfor (målt
    30/10-2026: 144 revokationer uden spor).
    """
    if status == "revoked" and not str(revoked_reason or "").strip():
        raise ValueError(
            "update_decision: status='revoked' kræver revoked_reason — "
            "en revokation uden grund gør politik-før og politik-efter usammenlignelige"
        )
    updated = _db_update_decision(
        decision_id,
        directive=directive,
        rationale=rationale,
        trigger_cue=trigger_cue,
        trigger_name=trigger_name,
        priority=priority,
        status=status,
        revoked_reason=revoked_reason,
        revoked_evidence=revoked_evidence,
    )
    if not updated:
        return None
    try:
        event_bus.publish(
            "decision.updated",
            {
                "decision_id": updated.get("decision_id"),
                "directive": updated.get("directive"),
                "status": updated.get("status"),
                "priority": updated.get("priority"),
            },
        )
    except Exception as exc:
        logger.debug("behavioral_decisions: publish updated failed: %s", exc)
    return updated


def change_status(
    decision_id: str,
    new_status: str,
    *,
    reason: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any] | None:
    if new_status == "revoked" and not str(reason or "").strip():
        raise ValueError(
            "change_status: 'revoked' kræver reason — ellers forsvinder politikken uden spor"
        )
    updated = _db_set_status(decision_id, new_status, reason=reason, evidence=evidence)
    if not updated:
        return None
    try:
        event_bus.publish(
            "decision.updated",
            {
                "decision_id": updated.get("decision_id"),
                "directive": updated.get("directive"),
                "status": updated.get("status"),
            },
        )
    except Exception:
        pass
    return updated


def revoke_decision(
    decision_id: str,
    *,
    reason: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any] | None:
    """Træk en beslutning tilbage — MED sin grund.

    Grunden er ikke valgfri. Målt 30/10-2026: 144 rækker med status='revoked'
    og nul spor af hvorfor. `reason` fandtes i signaturen hele tiden, men blev
    kun sendt til en ephemeral event; Agent Smith kaldte den med en rigtig grund
    (`central_agent_smith.py:526`) og grunden forsvandt i det samme.

    En revokation uden grund gør adaptation umulig at måle: man kan se at
    politikken er væk, ikke hvad der fjernede den, og ikke hvad den ville have
    gjort hvis den havde stået der.
    """
    if not str(reason or "").strip():
        raise ValueError(
            "revoke_decision: reason er påkrævet — en revokation uden grund "
            "efterlader ingen spor af hvorfor politikken blev fjernet"
        )
    updated = _db_set_status(decision_id, "revoked", reason=reason, evidence=evidence)
    if not updated:
        return None
    try:
        event_bus.publish(
            "decision.revoked",
            {
                "decision_id": updated.get("decision_id"),
                "directive": updated.get("directive"),
                "reason": reason,
                "evidence": evidence,
            },
        )
    except Exception:
        pass
    return updated


def delete_decision(decision_id: str) -> bool:
    ok = _db_delete(decision_id)
    if ok:
        try:
            event_bus.publish("decision.deleted", {"decision_id": decision_id})
        except Exception:
            pass
    return ok


def get_decision(decision_id: str) -> dict[str, Any] | None:
    return _db_get(decision_id)


def get_decision_with_reviews(
    decision_id: str, *, review_limit: int = 10
) -> dict[str, Any] | None:
    d = _db_get(decision_id)
    if not d:
        return None
    d = dict(d)
    d["recent_reviews"] = list_reviews(decision_id, limit=review_limit)

    # Decision-signals metadata (added 2026-05-07): trigger_name comes from
    # the SELECT * already; last_fired_at lives in runtime_state_kv where
    # the signal-pipeline writes it on each fire.
    d.setdefault("trigger_name", None)
    try:
        from core.runtime.db import connect
        with connect() as c:
            row = c.execute(
                "SELECT value FROM runtime_state_kv WHERE key = ?",
                (f"decision_signal_last_fired:{decision_id}",),
            ).fetchone()
        d["last_fired_at"] = str(row["value"]) if row else None
    except Exception:
        d["last_fired_at"] = None

    return d


def list_active_decisions(*, limit: int = 20) -> list[dict[str, Any]]:
    return _db_list(status="active", limit=limit)


def list_all_decisions(*, limit: int = 100) -> list[dict[str, Any]]:
    return _db_list(status="all", limit=limit)


# ── Relevans-gaten (23/11-2026) ─────────────────────────────────────────────
#
# HVORFOR (maalt 23/11-2026). Udvaelgelsen var `_db_list(status="active",
# limit=max_items)` = `ORDER BY priority DESC, updated_at DESC`. Med 138 aktive
# beslutninger og 5 pladser betoed det at de FEM HOEJESTE prioriteter altid vandt,
# uanset hvad turen handlede om. Maalt: beslutningen om forventning-og-modbevisning
# (priority 90) laa nr. 5 og blev ALDRIG injiceret, mens en med priority 94 gjorde.
# Det er en talraekkefoelge, ikke en vurdering — og den kan ikke afvise noget.
#
# Forskellen fra `decision_gate` er med vilje: den gate BLOKERER (og gav maalt 20
# falske blokeringer paa citater). Denne gate RANGERER. En forkert vurdering koster
# en daarlig raekkefoelge, ikke en blokeret handling — derfor maa den gerne vaere
# grov, men den maa ikke vaere tavs.
#
# Signalet er ord-overlap mellem beslutningens EGEN tekst (directive + trigger_cue)
# og turens kontekst. Det er ikke semantik; det er et billigt, forklarligt signal.
# Derfor baerer hver vurdering ogsaa HVORFOR den fik sin score, saa valget kan
# efterproeves frem for at skulle troes.

# Ord der ikke baerer betydning paa tvaers af beslutninger og ture.
#
# 23/11-2026: foerste version havde kun pronominer og konjunktioner. Maalt gav det
# falske hit: en HILSEN («hej Bjorn hvordan gaar det») vakte fire beslutninger,
# fordi «hvordan» staar i 4 af 138 beslutninger og derfor fik HOEJ IDF — sjaelden
# og betydningsloes paa samme tid. IDF kan ikke skelne de to; kun en liste kan.
# Derfor er spoergeord, hoeflighedsfraser og tidsvendinger ekskluderet her.
_RELEVANS_STOPORD = frozenset({
    # pronominer, konjunktioner, praepositioner
    "jeg", "det", "der", "som", "og", "at", "en", "et", "den", "de", "til",
    "for", "med", "fra", "skal", "kan", "ikke", "naar", "hvad", "hvor",
    "min", "mit", "mine", "sig", "sin", "sine", "har", "have", "var", "blev",
    "bliver", "vaere", "vaeret", "ogsaa", "kun", "men", "eller", "saa", "hvis",
    "denne", "dette", "disse", "man", "selv", "op", "ud", "ind", "ned",
    "the", "and", "with", "that", "this", "not", "are", "was", "have",
    # spoergeord og meta-ord — de beskriver samtalen, ikke sagen
    "hvordan", "hvorfor", "hvornaar", "hvilken", "hvilket", "hvilke",
    "gerne", "lige", "godt", "sadan", "vaere", "bliver", "siger", "sige",
    "synes", "tror", "ved", "kender", "handler", "gaelder", "drejer",
    # hoeflighed og hilsner
    "hej", "tak", "mojn", "godmorgen", "godaften", "velkommen",
    # tidsvendinger uden fagligt indhold
    "idag", "igaar", "imorgen", "aften", "morgen", "natten", "ugen",
    "maaned", "aaret", "timen", "gang", "igen", "stadig", "allerede",
    # Maskinelle tilstandstokens (24/11-2026, maalt i heartbeat-stien).
    # Heartbeat scorer IKKE mod en brugerbesked men mod `tool_intent` og
    # `loop_runtime` — korte, maskinelle strenge som «idle active 2». Maalt:
    # «active» staar i 1 af 138 beslutninger og fik derfor IDF 4,24, hvilket
    # lod den passere enkeltords-reglen. Resultatet var at de SAMME to
    # beslutninger (`active_dreams`, `bgActive`) blev valgt paa hver eneste
    # kontekst — en falsk forbindelse paa et strukturelt token. Det er samme
    # fejlklasse som «hvordan» i en hilsen: sjaelden OG betydningsloes.
    # `success` er BEHOLDT: den rammer beslutningen der netop handler om
    # `applied`/`ok`/`success`-felter, saa dér er ordet et ægte signal.
    "active", "idle", "executed", "completed", "none", "standby",
    "dispatched", "noop", "true", "false",
})


def _relevans_ord(tekst: str) -> set[str]:
    """Betydningsbaerende ord i en tekst — lowercase, >=4 tegn, uden stopord.

    23/11-2026 (maalt): foerste version splittede paa bindestreg, saa
    «prompt-sektionen» blev til «prompt» + «sektionen» og ALDRIG matchede den
    samme sammensatte form i en beslutning. Sammensatte ord bevares derfor som
    ét token, og delene tilfoejes OGSAA — saa baade «prompt-sektionen» og
    «sektionen» kan ramme.
    """
    tekst = str(tekst or "").lower()
    ord_: set[str] = set()
    for token in re.findall(r"[a-zæøå0-9_-]{4,}", tekst):
        if token in _RELEVANS_STOPORD:
            continue
        ord_.add(token)
        # Bindestreg og understregning: tilfoej delene, saa en sammensat form
        # ogsaa matcher naar modparten skriver den ene halvdel.
        if "-" in token or "_" in token:
            for del_ in re.split(r"[-_]", token):
                if len(del_) >= 4 and del_ not in _RELEVANS_STOPORD:
                    ord_.add(del_)
    return ord_


def _ord_frekvens(beslutninger: list[dict[str, Any]]) -> dict[str, int]:
    """Hvor mange beslutninger indeholder hvert ord?

    HVORFOR (maalt 23/11-2026). Foerste version vaegtede alle ord lige. Maalt gav
    det falske hit: «hvordan» og «faktisk» bandt beslutninger til en hilsen, fordi
    de staar i 11-14 af de 138 beslutninger. Et ord der staar i en tiendedel af
    alle beslutninger kan ikke skelne noget — det er baggrund, ikke signal.
    """
    freq: dict[str, int] = {}
    for d in beslutninger:
        tekst = f"{d.get('directive') or ''} {d.get('trigger_cue') or ''}"
        for o in _relevans_ord(tekst):
            freq[o] = freq.get(o, 0) + 1
    return freq


def _idf(ord_: str, freq: dict[str, int], antal: int) -> float:
    """Invers dokument-frekvens: sjældne ord vejer tungt, hyppige vejer næsten intet.

    23/11-2026 (maalt): uden et gulv giver en lille population NUL signal. Med
    kun én beslutning i tabellen bliver IDF for hvert ord log(2/2) = 0, saa
    scoren blev 0 for ALT — ogsaa et perfekt match. Gulvet paa 1.0 betyder at et
    ord altid vejer mindst som et almindeligt ord, uanset populationens stoerrelse.
    Det er den rigtige retning: en lille tabel maa ikke goere gaten tandloes.
    """
    import math

    n = freq.get(ord_, 0)
    if not antal:
        return 1.0
    return max(1.0, math.log((antal + 1) / (n + 1)))


def score_decision_relevance(
    decision: dict[str, Any],
    *,
    context_text: str = "",
    context_tools: tuple[str, ...] = (),
    ord_frekvens: dict[str, int] | None = None,
    antal_beslutninger: int = 0,
) -> dict[str, Any]:
    """Hvor relevant er denne beslutning for den aktuelle tur — og hvorfor?

    Returnerer ALTID en forklaring. En score paa 0 er et gyldigt svar og skal
    kunne skelnes fra «ikke vurderet» — derfor baerer returen baade `score` og
    `hvorfor`.
    """
    directive = str(decision.get("directive") or "")
    cue = str(decision.get("trigger_cue") or "")

    # Beslutningens egne ord. `trigger_cue` vejer tungere: den beskriver netop
    # den situation beslutningen gaelder for, mens directive beskriver handlingen.
    dir_ord = _relevans_ord(directive)
    cue_ord = _relevans_ord(cue)

    tur_ord = _relevans_ord(context_text)
    vaerktoej_ord: set[str] = set()
    for t in context_tools:
        vaerktoej_ord |= _relevans_ord(str(t).replace("_", " "))

    dir_hit = dir_ord & tur_ord
    cue_hit = cue_ord & tur_ord
    tool_hit = (dir_ord | cue_ord) & vaerktoej_ord

    freq = ord_frekvens or {}
    n = antal_beslutninger or 0

    def _vaegt(ord_: str) -> float:
        return _idf(ord_, freq, n) if freq else 1.0

    # Vaegtning: trigger_cue er det staerkeste signal (den beskriver situationen),
    # vaerktoejsnavne det naeststaerkeste (de er konkrete handlinger), directive det
    # svageste (den beskriver forpligtelsen, ikke situationen). Hvert hit vejes
    # desuden med sin IDF, saa et sjældent ord slår et almindeligt.
    score = (
        3 * sum(_vaegt(o) for o in cue_hit)
        + 2 * sum(_vaegt(o) for o in tool_hit)
        + 1 * sum(_vaegt(o) for o in dir_hit)
    )

    # Normalér mod beslutningens stoerrelse, saa en lang beslutning ikke vinder
    # blot fordi den har flere ord at ramme med. Uden dette vandt de laengste
    # direktiver systematisk — samme fejl som priority-loftet, bare med tekst.
    maal = max(1, len(cue_ord) + len(dir_ord))
    normaliseret = score / maal

    if cue_hit:
        hvorfor = f"trigger matcher turen: {', '.join(sorted(cue_hit)[:4])}"
    elif tool_hit:
        hvorfor = f"vaerktoej matcher: {', '.join(sorted(tool_hit)[:4])}"
    elif dir_hit:
        hvorfor = f"direktiv matcher turen: {', '.join(sorted(dir_hit)[:4])}"
    else:
        hvorfor = "ingen overlap med turen"

    return {
        "score": round(normaliseret, 4),
        "raa_score": round(score, 4),
        "hvorfor": hvorfor,
        "cue_hit": sorted(cue_hit),
        "tool_hit": sorted(tool_hit),
        "dir_hit": sorted(dir_hit),
    }


#: Under denne normaliserede score er en beslutning IKKE relevant for turen.
#: Uden en saadan graense er gaten bare et nyt loft: den ville altid fylde alle
#: pladser, ogsaa naar intet passede.
#:
#: HVOR MEGET BETYDER DEN? Maalt 23/11-2026 over 138 beslutninger x 12 ture
#: (1.656 vurderinger): gulvet stoppede PRAECIS ÉN vurdering som to-ord-reglen
#: nedenfor ellers ville slippe igennem, og to-ord-reglen afviste 1.642. Gulvet er
#: altsaa den sekundaere vagt, ikke den baerende — den bliver staaende, fordi den
#: ene sag er en ægte falsk positiv, men kommentaren maa ikke paastaa mere end
#: maalingen. Ægte match ligger maalt paa 0,09-0,89, ikke i det smalle baand en
#: tidligere version af denne kommentar angav.
_RELEVANS_GULV = 0.06

#: Et ENKELT ord maa kun baere en beslutning alene hvis det er saa sjaeldent at
#: det identificerer sagen. Maalt 23/11-2026 over 138 beslutninger: et ord i 1
#: beslutning har IDF 4,24, i 2 har 3,84, i 3 har 3,55, i 4 har 3,33. Taersklen
#: 3,4 betyder derfor «ordet staar i hoejst TRE beslutninger» — ellers kraeves der
#: to uafhaengige ord. (En tidligere kommentar her sagde 3,8 og «hoejst to»; det
#: var den foerste vaerdi jeg maalte mig frem til, ikke den der staar i koden.)
_ENKELTORD_IDF = 3.4


def select_relevant_decisions(
    *,
    max_items: int = 5,
    context_text: str = "",
    context_tools: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Vælg de mest relevante aktive beslutninger for den aktuelle tur.

    Uden kontekst falder den tilbage til priority-raekkefoelgen — men den falder
    tilbage AABENT: `_selection_basis` siger hvilken vej der blev brugt, saa en
    tom kontekst ikke kan forveksles med en vurdering.

    Med kontekst kan den returnere FAERRE end `max_items` — eller slet ingen.
    Det er med vilje: en gate der altid fylder alle pladser kan ikke afvise noget,
    og saa er den ikke en gate.
    """
    alle = _db_list(status="active", limit=None)
    if not alle:
        return []

    _kontekst_ord = _relevans_ord(context_text)
    har_kontekst = bool(_kontekst_ord) or bool(context_tools)
    # 24/11-2026 (maalt): «ingen kontekst givet» og «kontekst givet, men uden
    # fagsignal» er TO FORSKELLIGE SVAR og blev blandet sammen. Heartbeat sender
    # `tool_intent`/`loop_runtime` som «idle active 2» — efter stopord-filteret
    # staar der intet tilbage, og den gamle gren faldt dermed tilbage til
    # priority og fyldte fem pladser. Maalt: de SAMME fem hver gang. Det er
    # praecis den adfaerd gaten skulle afskaffe. Er der sendt kontekst, er
    # resultatet «intet relevant» — ikke «ingen vurdering».
    _gav_kontekst = bool(str(context_text or "").strip()) or bool(context_tools)

    if not har_kontekst:
        if _gav_kontekst:
            return []
        valgte = sorted(alle, key=lambda d: -int(d.get("priority") or 0))[:max_items]
        for d in valgte:
            d["_selection_basis"] = "priority-fallback-no-context"
            d["_relevans"] = {
                "score": 0.0,
                "raa_score": 0.0,
                "hvorfor": "ingen tur-kontekst — priority-raekkefoelge",
                "cue_hit": [],
                "tool_hit": [],
                "dir_hit": [],
            }
        return valgte

    freq = _ord_frekvens(alle)
    antal = len(alle)

    scored: list[dict[str, Any]] = []
    for d in alle:
        vurdering = score_decision_relevance(
            d,
            context_text=context_text,
            context_tools=context_tools,
            ord_frekvens=freq,
            antal_beslutninger=antal,
        )
        scored.append({**d, "_relevans": vurdering})

    # Relevans foerst; priority KUN som tie-breaker mellem lige relevante.
    scored.sort(
        key=lambda d: (
            -float(d["_relevans"]["score"]),
            -int(d.get("priority") or 0),
        )
    )

    # Den negative gren: under gulvet er beslutningen ikke relevant, uanset
    # priority. Det er dét der goer gaten til en gate frem for et loft.
    #
    # 23/11-2026 (maalt): foerste version slap ALT igennem der ramte ét ord.
    # Maalt vandt 11 af 138 beslutninger paa ordet «tilstand» alene, og 8 paa
    # «fejl» alene — et ordopslag, ikke en vurdering. Derfor kraeves nu mindst
    # TO uafhaengige ord, medmindre det ene ord er saa sjaeldent at det i sig
    # selv identificerer sagen (IDF over `_ENKELTORD_IDF`).
    valgte: list[dict[str, Any]] = []
    for d in scored:
        v = d["_relevans"]
        if float(v["score"]) < _RELEVANS_GULV:
            continue
        unikke = set(v["cue_hit"]) | set(v["tool_hit"]) | set(v["dir_hit"])
        if len(unikke) < 2:
            eneste = next(iter(unikke), "")
            if not eneste or _idf(eneste, freq, antal) < _ENKELTORD_IDF:
                continue
        valgte.append(d)
        if len(valgte) >= max_items:
            break
    for d in valgte:
        d["_selection_basis"] = "relevance"
    return valgte


def format_active_decisions_for_heartbeat(
    *,
    max_items: int = 3,
    context_text: str = "",
    context_tools: tuple[str, ...] = (),
) -> str:
    """Compact line of the most RELEVANT active commitments for this turn.

    Erstatter priority-loftet (23/11-2026). Se `select_relevant_decisions` for
    hvorfor. Signaturen er bagudkompatibel: uden kontekst opfoerer den sig som
    foer, men melder det i `_selection_basis`.
    """
    decisions = select_relevant_decisions(
        max_items=max_items,
        context_text=context_text,
        context_tools=context_tools,
    )
    if not decisions:
        return ""
    parts: list[str] = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        cue = str(d.get("trigger_cue") or "").strip()
        adherence = d.get("adherence_score")
        chunk = directive
        if cue:
            chunk = f"{directive} (when: {cue})"
        if adherence is not None:
            chunk += f" [adherence={adherence:.2f}]"
        parts.append(chunk)
    return " | ".join(parts)


def get_stats() -> dict[str, Any]:
    return {
        "active": count_decisions(status="active"),
        "paused": count_decisions(status="paused"),
        "revoked": count_decisions(status="revoked"),
        "fulfilled": count_decisions(status="fulfilled"),
        "total": count_decisions(),
    }
