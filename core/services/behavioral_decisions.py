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

import json
import logging
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
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

#: Spor til drift. MAALT 24/11-2026: journalen indeholdt NUL linjer fra
#: `jarvis-runtime` over 15 minutter — tjenesten skriver ikke der, saa
#: `logger.info` fra denne proces kan ikke laeses bagefter. Uden et spor kan
#: «gaten afviste» kun maales i en test, aldrig i den koerende proces.
#: Samme moenster som `cache_telemetry`: én jsonl-linje pr. valg.
_GATE_SPOR = Path.home() / ".jarvis-v2" / "logs" / "relevans_gate.jsonl"
#: Skrives KUN naar spor-filen ikke kunne skrives. Filens eksistens er svaret paa
#: «fejlede telemetrien?» — et spoer der ikke kan skrives, maa ikke forsvinde i en
#: logger der (maalt 23/11-2026) ikke skriver til journalen overhovedet.
_GATE_SPOR_FEJL = Path.home() / ".jarvis-v2" / "logs" / "relevans_gate_fejl.jsonl"


def _spor_gate(
    basis: str,
    valgt: int,
    ialt: int,
    ctx: str,
    ord_: list[str] | None = None,
    valgte: list[dict[str, Any]] | None = None,
) -> None:
    """Skriv ét spor pr. valg. Self-safe — maa aldrig vaelte prompt-stien.

    24/11-2026: sporet bar kun ANTALLET valgte, ikke hvilke. «basis=relevance,
    valgt=4» kunne derfor ikke efterproeves — man vidste at fire blev valgt, men
    ikke hvilke eller hvorfor de vandt. Nu baerer hver post id, score og den
    korte begrundelse pr. valgt beslutning, saa et valg kan revideres bagefter.

    Fejlhåndteringen skriver til `_GATE_SPOR_FEJL`, ikke til `logger.debug`:
    den logger blev maalt usynlig i `jarvis-runtime`s journal (nul INFO-linjer
    overhovedet), saa en tavs telemetri-fejl kunne ikke skelnes fra «gaten blev
    ikke kaldt». En fil der findes eller ikke findes kan skelnes.
    """
    try:
        _GATE_SPOR.parent.mkdir(parents=True, exist_ok=True)
        post: dict[str, Any] = {
            "at": datetime.now(UTC).isoformat(),
            "basis": basis,
            "valgt": int(valgt),
            "ialt": int(ialt),
            # HELE konteksten, ikke et snit (24/11-2026, tredje gang samme fejl):
            # foerst 160 tegn, saa 400 — begge gange blev de ord der AFGJORDE
            # valget skaaret vaek, og sporet kunne ikke reproducere sig selv.
            # Maalt: `loop_runtime.items[].title` ligger sidst i konteksten, saa
            # et snit paa 400 fjernede praecis de aabne loops der bar valget.
            # `ctx_len` goer et snit SYNLIGT hvis en fremtidig graense indfoeres.
            "ctx": str(ctx or ""),
            "ctx_len": len(str(ctx or "")),
            # HELE ord-saettet, ikke et snit (24/11-2026, FJERDE gang samme fejl
            # i denne fil inden for en time): `[:12]` skar 82 ord ned til 12, og
            # de 12 var de ALFABETISK foerste — saa alt fra e og frem var
            # usynligt. Maalt: heartbeat-konteksten har 82 ord, sporet viste 12.
            # Det gjorde netop de ord der afgjorde valget usynlige, og var
            # aarsagen til at jeg fejlagtigt konkluderede at to kald var
            # «gaten der afviser», da de i virkeligheden var to forskellige
            # kontekster. `ord_antal` goer et fremtidigt snit synligt.
            "ord": sorted(ord_ or []),
            "ord_antal": len(ord_ or []),
        }
        if valgte:
            post["valgte"] = [
                {
                    "id": str(d.get("decision_id") or ""),
                    "score": float((d.get("_relevans") or {}).get("score") or 0.0),
                    "hvorfor": str((d.get("_relevans") or {}).get("hvorfor") or "")[:120],
                }
                for d in valgte[:8]
            ]
        with _GATE_SPOR.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(post, ensure_ascii=False) + "\n")
    except Exception as exc:
        try:
            _GATE_SPOR_FEJL.parent.mkdir(parents=True, exist_ok=True)
            with _GATE_SPOR_FEJL.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "at": datetime.now(UTC).isoformat(),
                            "basis": basis,
                            "fejl": f"{type(exc).__name__}: {exc}"[:300],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception:  # sidste udvej: kan fejlfilen ikke skrives, er der intet sted at melde det
            pass


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


#: Maskinens EGEN statusbeskrivelse — ord der staar i hver eneste heartbeat-tur.
#:
#: HVORFOR (maalt i DRIFT 24/11-2026). Gaten valgte de SAMME fem beslutninger i
#: 16 heartbeat-ticks over 95 minutter, mens kontekstens tal aendrede sig
#: (1578 -> 1560 foreslaaede). Aarsagen var maalbar: de fem vandt paa `file`,
#: `main`, `memory`, `signal` — tokens der staar i statuslinjerne hver gang.
#: `dec_f1047a72079f` ramte UDELUKKENDE `file` + `memory` og scorede 4,31.
#:
#: Listen er ikke gaettet: den er udledt af de literaler der GENERERER
#: statuslinjerne (`heartbeat_runtime.py:2390-2520`) — «scheduled heartbeat
#: interval is currently due», «recent governed file writes exist for continuity
#: review», «private signal pressure is …» — plus de workflow-labels
#: (`Preference Updates`, `Memory Promotions`, `Chronicle Drafts`) og
#: `tool_intent`-beskrivelsen (`inspect-working-tree main`). Alle er maalt
#: tilstede i den levende kontekst. Et token herfra kan sagtens vaere en SAG i en
#: anden tur; derfor fjernes de ikke (som `_RELEVANS_STOPORD` goer), de vejes
#: lavere og kan ikke baere beviset alene.
#:
#: IKKE paa listen: `success` (rammer beslutningen om applied/ok/success-felter),
#: loop-titlenes fagord (`kørende`, `proces`, `prompten`, `relevans`) — de staar
#: ogsaa i alle 16 kontekster, men fordi loop-titlerne ikke aendrede sig, ikke
#: fordi de er maskinstatus — og TILSTANDSBESKRIVELSERNE (`signal`, `pressure`,
#: `high`, `initiative`, `tension`, `feel`). Skellet er maalt: foerste version
#: havde dem med, og saa fejlede en eksisterende test med rette — «private signal
#: pressure is high» er INFORMATION om turen, ikke en taeller. En beslutning om
#: signal-pres ER relevant naar presset er hoejt. Det er taellerne
#: («has 1560 proposed items») og identiteten («main», «inspect-working-tree»)
#: der ikke baerer en sag.
_STRUKTURELLE_ORD = frozenset({
    # heartbeat_runtime.py:2402-2516 — statuslinjernes taeller-vokabular
    "manual", "trigger", "requested", "mission", "control",
    "scheduled", "heartbeat", "interval", "currently",
    "capabilities", "still", "require", "approval",
    "proposed", "items", "approved", "awaiting", "apply",
    "recent", "governed", "file", "writes", "exist", "continuity", "review",
    "contract", "available", "context", "latest", "visible", "preview", "carry",
    # workflow-labels der taeller op i hver tur
    "preference", "updates", "memory", "promotions", "chronicle", "drafts",
    # tool_intent — hvilken slags tur det er, ikke hvad sagen er
    "inspect", "working", "tree", "main", "repo",
})

#: Hvor meget et strukturelt ord vejer i scoren, relativt til sin IDF.
#:
#: 0,35 er maalt, ikke valgt: ved 0,5 faldt `dec_f1047a72079f` (file+memory) ud
#: af de fem, og ved 0,35 stod rangordenen stabilt derefter. Faktoren kan ikke
#: ALENE goere en ren strukturel match harmloes — den scorer 0,647 selv ved 0,15,
#: altsaa stadig over gulvet 0,32; foerst ved ~0,07 ville den falde under, og det
#: er fjernelse, ikke vaegtning. Derfor er det BEVISKRAVET nedenfor den baerende
#: regel, og denne faktor kun den sekundaere.
_STRUKTUREL_VAEGT = 0.35


def _relevans_ord(tekst: str) -> set[str]:
    """Betydningsbaerende ord i en tekst — lowercase, >=4 tegn, uden stopord.

    23/11-2026 (maalt): foerste version splittede paa bindestreg, saa
    «prompt-sektionen» blev til «prompt» + «sektionen» og ALDRIG matchede den
    samme sammensatte form i en beslutning. Sammensatte ord bevares derfor som
    ét token, og delene tilfoejes OGSAA — saa baade «prompt-sektionen» og
    «sektionen» kan ramme.
    """
    tekst = str(tekst or "").lower()
    # 24/11-2026 (maalt i DRIFT, ikke i en test): en filsti er ikke et signal.
    # Heartbeats `last_action` baerer stier, og den foerste produktionslinje
    # (21:17:39) valgte 5 af 137 paa ord fra
    # `/tmp/pytest-of-bs/pytest-419/test_approved_sudo_exec_become0/workspaces/default/to`
    # — 9 af 15 tokens kom fra stien alene («pytest-of-bs», «become0»,
    # «workspaces», «default»). Det er samme fejlklasse som «active»: et token
    # der ikke baerer en sag. Stier fjernes derfor FOER tokenisering; et ord som
    # «chmod» uden for en sti bliver tilbage, fordi det KAN vaere en sag.
    tekst = re.sub(r"/\S*", " ", tekst)
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
        vaegt = _idf(ord_, freq, n) if freq else 1.0
        # Strukturelle tokens (maskinens egen statusbeskrivelse) vejes lavere end
        # fagord. Se `_STRUKTURELLE_ORD` for hvorfor og hvordan listen er udledt.
        return vaegt * _STRUKTUREL_VAEGT if ord_ in _STRUKTURELLE_ORD else vaegt

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
    #
    # 24/11-2026 (maalt i DRIFT, 141 beslutninger x heartbeat-konteksten): den
    # foerste version dividerede med `maal` og straffede dermed PRAECISION.
    # `bekraeftet, file, main` (3 ramte ord, maal 29) scorede 1,239, mens en
    # 4-ords match paa `efter, foelg, hele, signal` (maal 34) scorede 0,642 —
    # den grundige beslutning tabte til den korte, udelukkende fordi den var
    # laengere at beskrive. Delingen er derfor sqrt(maal): dobbelt saa mange
    # ord straffes 1,41x i stedet for 2x.
    #
    # Maalt paa samme kontekst: raekkefoelgen bliver 5-ord, 4-ord, saa de
    # svage, og springet ved snittet (nr. 5 -> nr. 6) gaar fra 5,0 % til 12,8 %.
    # De fem valgte er de SAMME i dag — det er reglen ved fremtidige
    # populationer der aendrer sig, ikke dagens valg. Det skal siges, fordi
    # «beviseligt bedre» ellers let laeses som «giver et andet svar nu».
    maal = max(1, len(cue_ord) + len(dir_ord))
    normaliseret = score / math.sqrt(maal)

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
#: altsaa den sekundaere vagt, ikke den baerende.
#:
#: 24/11-2026: normaliseringen blev sqrt(maal), saa SKALAEN flyttede sig — den
#: gamle graense 0,06 paa len-skalaen ville naesten intet afvise paa den nye
#: (scorerne ligger nu 0,3-9,3). Graensen er derfor maalt frem igen, ikke
#: gaettet: paa den levende heartbeat-kontekst (141 beslutninger, 842 tegn)
#: accepterer 0,32 praecis de SAMME 74 som 0,06 gjorde paa len-skalaen, mens
#: 0,33 fravælger to (0,31 giver ogsaa 74, men uden margin ned til den sag
#: gulvet findes for). Den afviste sag er `uden` alene — ét ord, som to-ord-
#: reglen ogsaa fanger; gulvet er stadig kun den sekundaere vagt.
_RELEVANS_GULV = 0.32

#: Et ENKELT ord maa kun baere en beslutning alene hvis det er saa sjaeldent at
#: det identificerer sagen. Maalt 23/11-2026 over 138 beslutninger: et ord i 1
#: beslutning har IDF 4,24, i 2 har 3,84, i 3 har 3,55, i 4 har 3,33. Taersklen
#: 3,4 betyder derfor «ordet staar i hoejst TRE beslutninger» — ellers kraeves der
#: to uafhaengige ord. (En tidligere kommentar her sagde 3,8 og «hoejst to»; det
#: var den foerste vaerdi jeg maalte mig frem til, ikke den der staar i koden.)
_ENKELTORD_IDF = 3.4


#: Hvor gammel maa «turens kontekst» vaere foer den ikke laengere beskriver turen?
#:
#: HVORFOR (maalt i DRIFT 24/11-2026, 74 ticks): `tool_intent.last_action_at` stod
#: paa 2026-05-15 — seks maaneder gammel — og kaldestedet sendte den alligevel ind
#: som turens kontekst. Gaten scorede dermed korrekt paa en situation der ikke
#: laengere fandtes, og valgte de SAMME fem beslutninger med de SAMME scorer i hver
#: tick (10:20, 10:35, 10:54, 11:11 — identiske). Det er praecis den adfaerd gaten
#: skulle afskaffe, blot med en anden aarsag end priority: ikke «de fem hoejeste
#: prioriteter», men «de fem der passede til en kontekst fra maj».
#:
#: Graensen er to heartbeat-intervaller (tick hvert 15. minut), altsaa 1800 s: en
#: kontekst fra denne eller sidste cyklus er stadig turen. Er den aeldre, er den
#: historie — og gaten maa sige det i stedet for at gaette.
_KONTEKST_MAX_ALDER_SEK = 1800.0


def select_relevant_decisions(
    *,
    max_items: int = 5,
    context_text: str = "",
    context_tools: tuple[str, ...] = (),
    context_age_seconds: float | None = None,
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

    # 24/11-2026 (maalt i DRIFT, 74 ticks): en kontekst der er aeldre end to
    # tick-intervaller beskriver ikke turen — den er historie. Foer denne gren
    # fandtes, scorede gaten korrekt paa `last_action_at = 2026-05-15` og valgte
    # de samme fem beslutninger i hver tick. Den falder tilbage til priority, men
    # MELDER det, saa en foraeldet kontekst ikke kan forveksles med en vurdering.
    if context_age_seconds is not None and context_age_seconds > _KONTEKST_MAX_ALDER_SEK:
        valgte = sorted(alle, key=lambda d: -int(d.get("priority") or 0))[:max_items]
        for d in valgte:
            d["_selection_basis"] = "priority-fallback-stale-context"
            d["_relevans"] = {
                "score": 0.0,
                "raa_score": 0.0,
                "alder_sekunder": int(context_age_seconds),
                "hvorfor": (
                    f"konteksten er {int(context_age_seconds)}s gammel "
                    f"(> {int(_KONTEKST_MAX_ALDER_SEK)}s) — priority-raekkefoelge"
                ),
                "cue_hit": [],
                "tool_hit": [],
                "dir_hit": [],
            }
        _spor_gate(
            "stale-context",
            len(valgte),
            len(alle),
            f"[alder={int(context_age_seconds)}s] {context_text}",
            valgte=valgte,
        )
        return valgte

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
            _spor_gate("no-signal", 0, len(alle), context_text)
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
        _spor_gate("priority-fallback", len(valgte), len(alle), "", valgte=valgte)
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
        # 24/11-2026 (maalt i DRIFT): beviskravet taeller kun FAGORD. Et strukturelt
        # token staar i hver heartbeat-kontekst og kan derfor ikke skelne en sag —
        # `file` + `memory` er to ord men NUL signaler. Vaegten i scoren (0,35) kan
        # ikke alene afvise dem: en ren strukturel match scorer 0,647 selv ved 0,15,
        # altsaa over gulvet. Derfor er det her, i beviskravet, vaernet sidder.
        fag = unikke - _STRUKTURELLE_ORD
        if len(fag) < 2:
            eneste = next(iter(fag), "")
            if not eneste or _idf(eneste, freq, antal) < _ENKELTORD_IDF:
                continue
            # 24/11-2026 (maalt i DRIFT): et enkelt ord i det lange `directive` er
            # ikke en situationsbeskrivelse. `dec_8e5784fcde71` slap igennem med
            # score 0,10 udelukkende fordi «output» stod i dens directive — mens
            # turens «output» var review af en sudo-kommando. `trigger_cue` er
            # beslutningens SITUATION; `directive` er dens handling. Et ord der kun
            # rammer handlingen maa derfor ikke baere beslutningen alene — saa skal
            # der mindst to ord til, uanset hvor sjaeldent det ene er.
            if not (v["cue_hit"] or v["tool_hit"]):
                continue
        valgte.append(d)
        if len(valgte) >= max_items:
            break
    for d in valgte:
        d["_selection_basis"] = "relevance"
    _spor_gate(
        "relevance",
        len(valgte),
        len(alle),
        context_text,
        sorted(_kontekst_ord),
        valgte=valgte,
    )
    return valgte


def format_active_decisions_for_heartbeat(
    *,
    max_items: int = 3,
    context_text: str = "",
    context_tools: tuple[str, ...] = (),
    context_age_seconds: float | None = None,
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
        context_age_seconds=context_age_seconds,
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
    # 24/11-2026: `_selection_basis` blev sat paa dict'en men naaede ALDRIG den
    # tekst modellen laeser — saa en priority-fallback kunne ikke skelnes fra en
    # relevansvurdering i prompten. Den staar nu som praefiks, fordi forskellen
    # er semantisk: «valgt fordi den var hoejest prioriteret» er ikke det samme
    # som «valgt fordi den passede til turen».
    basis = str(decisions[0].get("_selection_basis") or "")
    if basis == "priority-fallback-no-context":
        return (
            "[valgt paa priority — ingen tur-kontekst at vurdere relevans mod] "
            + " | ".join(parts)
        )
    # 24/11-2026: en FORÆLDET kontekst er ikke det samme som ingen kontekst.
    # Maalt i drift: `last_action_at` var seks maaneder gammel, og uden denne
    # gren saa valget ud som en relevansvurdering af den aktuelle tur.
    if basis == "priority-fallback-stale-context":
        try:
            sek = int((decisions[0].get("_relevans") or {}).get("alder_sekunder") or 0)
        except (TypeError, ValueError):
            sek = 0
        alder = f" ({sek // 60} min gammel)" if sek else ""
        return (
            f"[valgt paa priority — tur-konteksten var foraeldet{alder}, "
            "saa den blev ikke brugt som relevansgrundlag] " + " | ".join(parts)
        )
    return " | ".join(parts)


def get_stats() -> dict[str, Any]:
    return {
        "active": count_decisions(status="active"),
        "paused": count_decisions(status="paused"),
        "revoked": count_decisions(status="revoked"),
        "fulfilled": count_decisions(status="fulfilled"),
        "total": count_decisions(),
    }
