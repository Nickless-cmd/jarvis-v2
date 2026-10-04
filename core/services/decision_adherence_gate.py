"""Gate 1: Decision-adherence gate.

Inspects active decisions and their adherence scores.
Returns an escalated prompt section when adherence is low.

Escalation levels:
  - heed_rate >= 60%: no nudge (decision is being followed)
  - heed_rate 40-59%: advisory — "Husk at..."
  - heed_rate < 40%: imperative — "DU SKAL..." with explicit consequence
  - heed_rate < 25%: critical — highest priority, includes rollback warning

This module is imported lazily in prompt_contract.py to avoid circular imports.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Thresholds
_ADVISORY_THRESHOLD = 0.40   # below this → imperative
_CRITICAL_THRESHOLD = 0.25   # below this → critical
_GOOD_THRESHOLD = 0.60      # above this → no nudge

# Loft over hvor mange linjer gaten skriver. Rækkerne sorteres værste-først
# nedenfor, så det kritiske bånd aldrig skubbes ud af loftet — og resten
# tælles op i én linje frem for at forsvinde tavst (fix 2026-09-21).
_MAKS_LINJER = 12


def decision_adherence_section() -> str:
    """Build an escalation prompt section based on current decision adherence.

    Returns empty string if all decisions are above good threshold.
    """
    # Fix 2026-05-12: prior import was core.services.decision_runtime which
    # doesn't exist — this gate had been silently returning "" since its
    # creation. Real API lives in behavioral_decisions.list_active_decisions().
    # Result: low-adherence decisions (incl. loop-nudge compliance) never
    # reached Jarvis as awareness, even when score < 25%. Switched to the
    # correct module so escalation actually surfaces.
    try:
        from core.services.behavioral_decisions import (
            count_decisions,
            list_active_decisions,
        )
    except ImportError:
        logger.debug("decision_adherence_gate: behavioral_decisions not available")
        return ""

    # Fix 2026-09-21: gaten læste kun 20 af 44 aktive beslutninger — og i en
    # rækkefølge der gjorde det værre end tilfældigt, fordi lageret sorterer
    # efter priority/updated_at og IKKE efter adherence. Høj-prioritets-
    # beslutninger med høj adherence fortrængte de kritiske, som derfor
    # aldrig nåede frem til mig. Læs ALLE aktive og sortér efter score
    # nedenfor, så det kritiske bånd altid kommer med.
    try:
        active = list_active_decisions(limit=max(50, count_decisions(status="active")))
    except Exception as exc:
        logger.debug("decision_adherence_gate: list failed: %s", exc)
        return ""

    if not active:
        return ""

    # Live R2 heed-rate overlay (2026-05-13). adherence_score in DB only
    # updates on manual review_decision() — most decisions never get reviewed,
    # so the stored score stays at default (0.95+). Real behaviour is in R2
    # telemetry (surfaces vs heeded). For decisions about "follow warnings"
    # (loop_nudge, verification gate), R2 heed_rate is the truer signal.
    # If R2 rate is low + surfaced volume meaningful, fold it in as min(score, rate)
    # so gate fires when EITHER signal indicates a problem.
    r2_rate: float | None = None
    try:
        from core.services.verification_gate_telemetry import get_telemetry_summary
        s = get_telemetry_summary(hours=24)
        if int(s.get("surfaced_total") or 0) >= 5:
            r = s.get("heed_rate")
            if r is not None:
                r2_rate = float(r)
    except Exception as exc:
        logger.debug("decision_adherence_gate: r2 lookup failed: %s", exc)

    # Decision IDs whose adherence should be derived from R2 telemetry rather
    # than the stale stored score. Add new ones here when we identify them.
    _R2_LINKED_DECISIONS = {
        "dec_d56d89ceec24",  # loop-nudge commitment — tracked in R2 gate
    }

    # Saml alt under tærsklen først, sortér værste-først, og skriv så. Uden
    # sorteringen ville loftet kunne skjule en kritisk beslutning bag
    # advisory-støj — præcis den fejlklasse fixet 2026-09-21 retter.
    raekker: list[tuple[float, str, str]] = []
    for d in active:
        directive = d.get("directive", "")
        # Fix 2026-09-21: `d.get("adherence_score", 1.0) or 1.0` behandlede en
        # score på PRÆCIS 0.0 som falsy og løftede den til 1.0 — den værste
        # beslutning af alle blev læst som «doing fine» og sprunget over.
        # Kun None betyder «aldrig reviewet».
        raa = d.get("adherence_score")
        stored_score = float(raa) if raa is not None else 1.0
        dec_id = d.get("decision_id", "?")

        # Overlay R2 telemetry where applicable
        if r2_rate is not None and dec_id in _R2_LINKED_DECISIONS:
            score = min(stored_score, r2_rate)
        else:
            score = stored_score

        if score >= _GOOD_THRESHOLD:
            continue  # doing fine, no nudge needed

        raekker.append((score, dec_id, directive))

    if not raekker:
        return ""

    raekker.sort(key=lambda r: r[0])

    lines = ["\n[DECISION-ADHERENCE-GATE]"]
    # Handlingen skrives ÉN gang per bånd, ikke én gang per post.
    #
    # Målt 4/10-2026 på Bjørns levende samtale: blokken var 1.177 tokens — den
    # STØRSTE i hele den dynamiske hale, 17,4 % af den — og ~297 af dem (25 %)
    # var den samme sætning gentaget tolv gange. Handlingen er pr. BÅND, ikke
    # pr. beslutning; den var identisk hver gang fordi den aldrig kunne være
    # andet.
    #
    # Formen er ikke ændret: båndet eskalerer stadig i HANDLING, og en
    # beslutning slettes stadig ikke. Kun gentagelsen er væk.
    kritiske_vist = 0
    imperative_vist = 0
    for score, dec_id, directive in raekker[:_MAKS_LINJER]:
        if score < _CRITICAL_THRESHOLD:
            # Critical band — adherence below 25%.
            #
            # Rettet 26/9-2026 (Bjørn: «lad eskalering erstatte revoke»).
            # FØR stod der «ved fortsat lav adherence revokes decision
            # automatisk» — og det var ikke sandt. Ingen kode kalder
            # revoke_decision på en adherence-score; kun Agent Smith (når
            # mønstret er løst) og konsoliderings-dommeren revokerer, og
            # ingen af dem læser scoren. Truslen var pres uden mekanisme bag
            # — og den ramte netop de beslutninger der peger på ægte
            # svagheder. Et bånd der kan revoke, sletter systematisk de
            # svære og beholder de lette: den modsatte af læring.
            #
            # Nu eskalerer båndet i HANDLING i stedet: en beslutning der ikke
            # kan opfyldes som formuleret skal omformuleres, ikke slettes.
            lines.append(
                f"Adherence {score:.0%} (kritisk band) — {dec_id}: {directive}"
            )
            kritiske_vist += 1
        elif score < _ADVISORY_THRESHOLD:
            # Imperative band — adherence below 40%
            lines.append(
                f"Adherence {score:.0%} (imperativ band) — {dec_id}: {directive}"
            )
            imperative_vist += 1
        else:
            # Advisory band — adherence below good threshold
            lines.append(
                f"Adherence {score:.0%} (advisory band) — {dec_id}: {directive}"
            )

    # Handlingerne, én per bånd der faktisk har poster.
    if kritiske_vist:
        lines.append(
            f"  → De {kritiske_vist} i kritisk band kan ikke opfyldes som "
            "formuleret: omformulér hver til trigger → handling → bevis. "
            "De slettes ikke."
        )
    if imperative_vist:
        lines.append(
            f"  → De {imperative_vist} i imperativ band gentager bruddet — "
            "navngiv det eksplicit i næste svar."
        )

    skjulte = len(raekker) - _MAKS_LINJER
    if skjulte > 0:
        # Aldrig tavs: hellere sige hvor mange der ligger under tærsklen end
        # at lade dem forsvinde ud af prompten uden et spor.
        lines.append(f"… og {skjulte} flere under tærsklen (ikke vist her).")

    lines.append("[/DECISION-ADHERENCE-GATE]\n")
    return "\n".join(lines)

# ── Indbakken (4/10-2026) ───────────────────────────────────────────────────

def registrer_i_indbakken(bruger_id: str) -> dict[str, Any]:
    """Giv hver beslutning under tærsklen en post i indbakken.

    ## Hvorfor

    `_MAKS_LINJER` er et DISPLAY-loft, ikke et antal. Målt 4/10-2026: 75 aktive
    beslutninger, 34 under tærsklen, 19 af dem kritiske — og gaten viser 12.
    **Syv kritiske beslutninger står helt uden for prompten.**

    Gaten er ikke tavs om dem; den skriver «… og N flere under tærsklen (ikke
    vist her)». Men et tal uden id'er er ikke en adresse: man kan ikke lukke,
    omformulere eller slå op på noget man ikke kan navngive. Indbakken kan bære
    dem alle uden at vokse prompten, fordi `inbox` er et værktøj han KALDER.

    ## De gater ikke, og det er med vilje

    Posterne oprettes uden for et levende run, så `registrer_kilde` giver dem
    `verificeret_ejer="ukendt"` og `kraever_handling=False`. Det er det rigtige
    udfald: en beslutning er en forpligtelse Jarvis har givet sig selv, men den
    er ikke et stykke arbejde der venter — og skrive-kontrakten siger at kun
    verificerede, egne poster må nægte en mutation. Beslutnings-gaten har sin
    EGEN eskalering; indbakken skal ikke lægge en anden oven på.

    ## `drop` må ikke kunne tie en beslutning

    Gatens egen begrundelse fra 26/9 er utvetydig: «Et bånd der kan revoke,
    sletter systematisk de svære og beholder de lette: den modsatte af
    læring.» Derfor sættes `expires_at` på hver post: et `inbox_drop` lukker
    rækken, men ved næste registrering er posten tilbage, fordi beslutningen
    stadig står under tærsklen i kilden. Indbakken kan altså udsætte, ikke
    slette — og den beslutning den peger på er uberørt.
    """
    try:
        from core.services.behavioral_decisions import (
            count_decisions,
            list_active_decisions,
        )
        active = list_active_decisions(limit=max(50, count_decisions(status="active")))
    except Exception as exc:  # noqa: BLE001
        logger.warning("decision_adherence_gate: kunne ikke laese beslutninger: %s", exc)
        return {"status": "fejl", "error": str(exc)}

    from core.services.inbox_state import registrer_kilde

    oprettet = 0
    fejl = 0
    for d in active:
        raa = d.get("adherence_score")
        score = float(raa) if raa is not None else 1.0
        if score >= _GOOD_THRESHOLD:
            continue
        dec_id = str(d.get("decision_id") or "").strip()
        if not dec_id:
            continue
        baand = ("kritisk" if score < _CRITICAL_THRESHOLD
                 else "imperativ" if score < _ADVISORY_THRESHOLD else "advisory")
        r = registrer_kilde(
            bruger_id=bruger_id,
            kildetype="decision",
            kilde_id=dec_id,
            # Ingen `oprettende_run_id`: posten oprettes af en baggrundsvej,
            # og et flag ville vaere en paastand. `ukendt` er det aerlige svar.
            paastaaet_ejer="huset",
            beskrivelse=f"[{baand} {score:.0%}] {str(d.get('directive') or '')}",
        )
        if r.get("status") == "ok":
            oprettet += 1
        else:
            fejl += 1
    return {"status": "ok", "registreret": oprettet, "fejlede": fejl}
