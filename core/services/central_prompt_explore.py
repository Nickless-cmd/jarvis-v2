"""core/services/central_prompt_explore.py

DEN MODIGE DEL — Tråd 2 (prompt-relevans), Fase 3-4. Eksplorations-armen: den ÆGTE kontrol-arm.

Spec §10 (ikke-forhandlelig): man kan ikke VIDE om en prompt-sektion er load-bearing uden at
UDELADE den occasionelt og sammenligne udfaldet. Denne modul kører et alternerende A/B-forsøg pr.
kandidat-(tur-type, sektion):
  * ABSENT-arm: sektionen udelades i N ture → mål udfald.
  * PRESENT-arm: sektionen med i N ture → mål udfald.
  * Hvis ABSENT ≥ PRESENT (sektionen hjælper ikke) → foreslå at nedvægte den (learned relevans),
    B4-auditeret + §8-drift-gated. Ellers: sektionen er load-bearing → rør den ikke.

SIKKERHED (alle ikke-forhandlelige):
  * FROSNE sektioner (soul/identity/user/security) udelades ALDRIG.
  * SHADOW som default: `prompt_relevance_explore_live_enabled=False` → should_omit returnerer ALTID
    False → INTET udelades, INTET skæres. Kun bag Bjørns flag begynder ægte ablation.
  * §8 gate_self_mutation(domain="prompt_relevance") bounder hvor aggressivt der må nedvægtes.
  * fail-open: enhver fejl → sektionen INKLUDERES (skjuler aldrig ved tvivl). Kaster ALDRIG.
"""
from __future__ import annotations

import contextvars
from typing import Any

from core.services import central_hypothesis_governance as gov

# ── UDFALDET FINDES IKKE VED PROMPT-BYGNINGEN (28/10-2026) ──────────────────────────
# `observe_composition` har altid haft `outcome: str = ""` som default, og den ENESTE
# kalder (prompt_contract.py:2302) udelader parameteren. Derfor ramte hver tur
# `if not outcome: return` i record_trial, og forsøget kunne ALDRIG samle ét datapunkt —
# det stod som et kørende forsøg i månedsvis uden en enkelt måling.
#
# Aarsagen er arkitektonisk, ikke en glemt parameter: prompten bygges FOER turen, saa
# udfaldet eksisterer ikke paa det tidspunkt. Løsningen er derfor to-faset — kompositionen
# gemmes her ved bygningen, og udfaldet sendes fra run-finalize (visible_runs.py) hvor
# `_outcome_state.status` faktisk findes. ContextVar fordi den følger turen, ikke processen:
# en global dict ville lade session A's udfald tælle paa session B's sektioner.
_sidste_komposition: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "prompt_explore_sidste_komposition", default=None
)
_MISSING_KEY = "prompt_ablation_missing_context"   # synligt bevis hvis koblingen brister

_EXPLORE_FLAG = "prompt_relevance_explore_live_enabled"   # Bjørns switch (default OFF)
_STATE_KEY = "prompt_ablation_state"                      # aktivt A/B-forsøg
_WEIGHTS_KEY = "prompt_relevance_weights"                 # samme som composer læser (live cut-vægte)
_SHADOW_KEY = "prompt_relevance_weights_shadow"           # foreslåede vægte (shadow-diff til Bjørn)
_DOMAIN = "prompt_relevance"
_TRIALS_PER_ARM = 15                 # ture pr. arm før sammenligning
_CUT_WEIGHT = 0.2                    # < composerens _INCLUDE_THRESHOLD (0.3) → sektionen skæres
_MAX_CUTS = 8                        # §8: drift-budget — aldrig mere end så mange lærte snit ad gangen
_MIN_MARGIN = 0.0                    # ABSENT-good-rate skal være ≥ PRESENT (ingen skade) for at skære


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def is_explore_live() -> bool:
    return bool(_kv_get(_EXPLORE_FLAG, False))


def _ensure_anchor() -> None:
    """§8: ankr domænets baseline (antal lærte snit = 0 = ingen relevans-mutation) så drift kan måles.
    Namespaced pr. domæne (kollisionsfri med Lag 4's gut-domæne). Idempotent, self-safe."""
    try:
        if gov.get_anchored_baseline(domain=_DOMAIN) is None:
            gov.anchor_identity_baseline({"cuts": 0.0}, version="prompt_explore_v1",
                                         approved_by="central_prompt_explore", domain=_DOMAIN)
    except Exception:
        pass


def _is_frozen(section: str) -> bool:
    try:
        from core.services.central_prompt_composer import FROZEN_SECTIONS
        sl = str(section or "").lower()
        return any(f in sl for f in FROZEN_SECTIONS)
    except Exception:
        return True                  # kan ikke afgøre → behandl som frossen (aldrig udelad)


def _good(outcome: str) -> bool:
    o = str(outcome or "").lower()
    return any(g in o for g in ("complet", "done", "ok", "success"))


# ── A/B-forsøgets tilstandsmaskine ───────────────────────────────────────────────────
def _new_state(tt: str, sec: str) -> dict[str, Any]:
    # SHADOW-BASELINE (28/10-2026): uden live-flag udelades intet, saa ABSENT-armen kan ikke
    # maales. Forsøget starter derfor paa PRESENT i shadow — den arm der FAKTISK sker — og
    # skifter først til absent naar flaget taendes. Ellers stod staten paa en arm der aldrig
    # kunne tælle, hvilket er præcis den slags "levende forsøg" der ikke maaler noget.
    return {"tt": tt, "sec": sec, "arm": "present" if not is_explore_live() else "absent",
            "left": _TRIALS_PER_ARM,
            "absent_good": 0, "absent_total": 0, "present_good": 0, "present_total": 0}


def maybe_start_ablation() -> dict[str, Any] | None:
    """Start et forsøg hvis intet kører: vælg den hyppigste ikke-frosne relevans-kandidat. Self-safe."""
    st = _kv_get(_STATE_KEY, None)
    if isinstance(st, dict) and st.get("tt"):
        # EN GAMMEL STATE KAN VÆRE DØD FRA FØDSLEN (28/10-2026). Staten her blev skrevet
        # 17/8 med `arm: "absent"`, mens flaget var slukket. I shadow udelades intet, saa
        # `record_trial` returnerer straks i absent-grenen — den kan ALDRIG tælle. Guarden
        # nedenfor gjorde derfor det modsatte af sit formaal: den værgede om et forsøg der
        # ikke kunne maale, og blokerede ethvert nyt i 72 dage. Maalt: `present_total` stod
        # paa 0 mens `prompt_section_freq` blev opdateret hver tur — kæden kørte halvt.
        # En state der er uforenelig med den nuværende flag-tilstand erstattes. Er flaget
        # TÆNDT, er absent-armen gyldig og staten bevares (dens data er ægte).
        if st.get("arm") == "absent" and not is_explore_live():
            st = None
        else:
            return st
    try:
        from core.services.central_prompt_composer import build_relevance_candidates
        for c in build_relevance_candidates():
            if not _is_frozen(c["section"]):
                st = _new_state(c["turn_type"], c["section"])
                _kv_set(_STATE_KEY, st)
                return st
    except Exception:
        pass
    return None


def should_omit(turn_type: str, section: str) -> bool:
    """Skal denne sektion UDELADES fra prompten NU (ablation)? Kun live + aktivt forsøgs ABSENT-arm +
    match + ALDRIG frossen. Default/shadow/fejl → False (inkludér). Kaldes fra composer.should_include."""
    try:
        if not is_explore_live() or _is_frozen(section):
            return False
        st = _kv_get(_STATE_KEY, None)
        if not isinstance(st, dict):
            return False
        return (st.get("arm") == "absent" and st.get("tt") == str(turn_type)
                and st.get("sec") == str(section))
    except Exception:
        return False                 # fail-open: aldrig skjul ved fejl


def record_trial(turn_type: str, included_labels: list[str] | None, outcome: str) -> None:
    """Kaldes én gang pr. tur (fra observe_composition). Kun LIVE: hvis et forsøg kører for denne
    tur-type, tæl udfaldet ind i den arm der FAKTISK skete (verificeret mod included_labels, så
    dataen ikke forurenes) → skift arm / evaluér når armen er fuld. Shadow → intet tælles. Self-safe."""
    try:
        st = _kv_get(_STATE_KEY, None)
        if not isinstance(st, dict) or st.get("tt") != str(turn_type):
            return
        if not outcome:
            return                   # uden udfald kan vi ikke score — spring over (tæller ikke)
        arm = st.get("arm")
        present_now = bool(included_labels) and st.get("sec") in (included_labels or [])
        good = _good(outcome)
        # SHADOW-BASELINE (28/10-2026). PRESENT-armen er gratis at maale: sektionen VAR med,
        # intet blev udeladt, ingen risiko for turen. Uden den er et ABSENT-resultat et tal
        # uden reference. Derfor tælles PRESENT ogsaa naar flaget er slukket — men ABSENT
        # gør ALDRIG: shadow udelader intet, saa en "absent"-taelling i shadow ville vaere
        # en løgn om hvad der skete. Den graense er det der gør baseline aerlig.
        live = is_explore_live()
        if arm == "absent":
            if not live:
                return               # shadow: intet blev udeladt → ingen ABSENT-data at hente
            if present_now:
                return               # inkonsistent (sektionen var MED i absent-armen) → forurener ikke
            st["absent_total"] += 1
            st["absent_good"] += 1 if good else 0
        else:
            if not present_now:
                return               # sektionen var FRAVÆRENDE i present-armen → forurener ikke
            st["present_total"] += 1
            st["present_good"] += 1 if good else 0
        st["left"] = int(st.get("left", 0)) - 1
        if st["left"] <= 0:
            if arm == "absent":
                st["arm"] = "present"    # skift til present-armen
                st["left"] = _TRIALS_PER_ARM
                _kv_set(_STATE_KEY, st)
            elif not live:
                # SHADOW-BASELINE: armen er fuld, men der er ingen ABSENT-data at sammenligne
                # med — et forsøg kan ikke afgøres paa halvdelen af sit grundlag. Staten
                # BEHOLDES (baseline-rate akkumulerer videre) og armen bliver staaende paa
                # 'present'. Rydder vi her, forsvinder den eneste baseline vi har.
                st["left"] = _TRIALS_PER_ARM
                _kv_set(_STATE_KEY, st)
            else:
                _finish_ablation(st)     # begge arme fulde → evaluér + afslut
                return
        _kv_set(_STATE_KEY, st)
    except Exception:
        pass


def note_composition(turn_type: str, included_labels: list[str] | None) -> None:
    """Gem HVAD der blev komponeret denne tur, så udfaldet kan sendes senere.

    To-faset kobling (28/10-2026): prompten bygges før turen kører, så `observe_composition`
    kan ikke kende udfaldet — den parameter var altid "" og forsøget målte derfor intet.
    Her gemmes kun det faktum der ER kendt på bygningstidspunktet; `record_turn_outcome`
    læser det ved run-finalize og sender udfaldet videre. Self-safe, kaster aldrig.
    """
    try:
        _sidste_komposition.set({
            "tt": str(turn_type or ""),
            "labels": list(included_labels or []),
        })
    except Exception:  # self-safe: kontekst-gemmelse maa ikke vaelte prompt-bygningen
        pass


def record_turn_outcome(outcome: str) -> None:
    """Send turens udfald til det A/B-forsøg der var aktivt i DENNE tur.

    Kaldes fra run-finalize (`visible_runs.py`) hvor `_outcome_state.status` findes —
    det er det eneste sted i kæden hvor 'completed'/'failed'/'interrupted' er kendt.

    Koblingen er bevidst IKKE stille når den brister: kører et forsøg (live-flag ON) og
    der ikke ligger en komposition i konteksten, tælles det i
    `prompt_ablation_missing_context` i stedet for at forsvinde. Et forsøg der tier om
    at det ikke måler, er præcis den fejl der holdt denne arm død i månedsvis.
    """
    try:
        komp = _sidste_komposition.get()
        if not isinstance(komp, dict):
            # Kun en FEJL hvis et forsøg faktisk kører live. I shadow er der intet forsøg,
            # og en manglende komposition er normal (fx en tur uden prompt-bygning).
            if is_explore_live():
                n = int(_kv_get(_MISSING_KEY, 0) or 0)
                _kv_set(_MISSING_KEY, n + 1)
            return
        _sidste_komposition.set(None)
        record_trial(str(komp.get("tt") or ""), komp.get("labels") or [], outcome)
    except Exception:  # self-safe: en maale-fejl maa ikke vaelte run-finalize
        pass


def _rate(good: int, total: int) -> float:
    return (good / total) if total else 0.0


def evaluate_ablation(st: dict[str, Any]) -> dict[str, Any]:
    """Kontrol-arm-dom: var sektionen undværlig? ABSENT-good-rate ≥ PRESENT-good-rate → undværlig
    (foreslå snit); ellers load-bearing (behold). Ren sammenligning, model-fri. Self-safe."""
    a, p = _rate(st.get("absent_good", 0), st.get("absent_total", 0)), \
           _rate(st.get("present_good", 0), st.get("present_total", 0))
    dispensable = (st.get("absent_total", 0) > 0 and st.get("present_total", 0) > 0
                   and a + _MIN_MARGIN >= p)
    return {"tt": st.get("tt"), "sec": st.get("sec"), "absent_rate": round(a, 3),
            "present_rate": round(p, 3), "dispensable": bool(dispensable)}


def _finish_ablation(st: dict[str, Any]) -> None:
    """Forsøg færdigt: dom → hvis undværlig, foreslå snit (B4-auditeret + §8-gated). SHADOW-record
    altid; skriv KUN live-vægt hvis explore-flag ON + §8-gate ok. Ryd forsøgs-state. Self-safe."""
    verdict = evaluate_ablation(st)
    tt, sec = str(verdict["tt"]), str(verdict["sec"])
    proposed_key = f"{tt}|{sec}"
    applied = False
    gate_action = "none"
    if verdict["dispensable"] and not _is_frozen(sec):
        # SHADOW-diff: foreslået vægt (altid synlig for Bjørn)
        shadow = _kv_get(_SHADOW_KEY, {}) or {}
        if isinstance(shadow, dict):
            shadow[proposed_key] = _CUT_WEIGHT
            _kv_set(_SHADOW_KEY, shadow)
        # §8-gate: hvor mange lærte snit ville der være i alt? drift mod ankret 0.
        live = _kv_get(_WEIGHTS_KEY, {}) or {}
        n_cuts = sum(1 for v in (live.values() if isinstance(live, dict) else [])
                     if isinstance(v, (int, float)) and float(v) < 0.3) + 1
        _ensure_anchor()
        verdict_gate = gov.gate_self_mutation({"cuts": float(n_cuts)},
                                              budgets={"cuts": float(_MAX_CUTS)}, domain=_DOMAIN)
        gate_action = verdict_gate.action
        # B4-audit (best-effort notation, til inspektbarhed) + §8-gate + Bjørns flag → skriv live-vægt
        if is_explore_live() and verdict_gate.action != "rollback":
            _audit_notation(tt, sec)
            if isinstance(live, dict):
                live[proposed_key] = _CUT_WEIGHT
                _kv_set(_WEIGHTS_KEY, live)
                applied = True
    _observe(verdict, applied=applied, gate=gate_action)
    _kv_set(_STATE_KEY, {})          # ryd → næste tick starter nyt forsøg


def _audit_notation(tt: str, sec: str) -> dict[str, Any] | None:
    """Best-effort: udtryk snittet som notation (tur-type ! sektion-term) og auditér via B4 — til
    inspektbarhed. Sektioner uden term rendres ikke (blokerer IKKE snittet; §8 er den hårde gate)."""
    try:
        from core.services.central_lexicon import to_term, _ACTIVE_TERMS
        # find et kendt term i sektions-labelen (labels er fraser)
        sec_term = next((t for t in _ACTIVE_TERMS if t in str(sec).lower()), None)
        tt_term = to_term(tt) or tt
        if not sec_term:
            return None
        from core.services.central_proposal import make_proposal
        return make_proposal(domain=_DOMAIN, notation=f"{tt_term} ! {sec_term}",
                             rationale=f"ablation: {sec} undværlig for {tt}")
    except Exception:
        return None


def _observe(verdict: dict[str, Any], *, applied: bool, gate: str) -> None:
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "prompt_explore", value=1.0 if verdict.get("dispensable") else 0.0,
                       meta={"tt": verdict.get("tt"), "sec": str(verdict.get("sec"))[:40],
                             "absent_rate": verdict.get("absent_rate"),
                             "present_rate": verdict.get("present_rate"),
                             "dispensable": verdict.get("dispensable"),
                             "applied": applied, "gate": gate, "live": is_explore_live()})
    except Exception:
        pass


def run_prompt_explore_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: hold et A/B-forsøg kørende (start nyt hvis intet aktivt). Selve tælling/evaluering
    sker i record_trial (pr. tur). SHADOW medmindre explore-flag ON. Self-safe."""
    st = maybe_start_ablation()
    return {"status": "ok", "mode": "live" if is_explore_live() else "shadow",
            "active_experiment": {"tt": st.get("tt"), "sec": st.get("sec"), "arm": st.get("arm")}
            if isinstance(st, dict) and st.get("tt") else None}


def register_prompt_explore_producer() -> None:
    """Registrér eksplorations-armen som cadence-producer (~hvert 20 min). SHADOW medmindre flag ON."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_prompt_explore",
        cooldown_minutes=20,
        visible_grace_minutes=0,
        run_fn=run_prompt_explore_tick,
        priority=8,
    ))


def build_prompt_explore_surface() -> dict[str, object]:
    """Mission Control — read-only: aktivt forsøg + foreslåede snit (shadow-diff Bjørn kan se)."""
    st = _kv_get(_STATE_KEY, {}) or {}
    shadow = _kv_get(_SHADOW_KEY, {}) or {}
    baseline = None
    if isinstance(st, dict) and st.get("tt"):
        # Baseline-rate: hvad er PRESENT-armens gode-udfald i drift? Uden den er et
        # ABSENT-resultat et tal uden reference. Synlig ogsaa i shadow.
        baseline = {"present_good": int(st.get("present_good", 0)),
                    "present_total": int(st.get("present_total", 0)),
                    "present_rate": round(_rate(st.get("present_good", 0),
                                                st.get("present_total", 0)), 3)}
    return {"active": True, "explore_live": is_explore_live(),
            "experiment": st if isinstance(st, dict) and st.get("tt") else None,
            "baseline": baseline,
            "missing_context": int(_kv_get(_MISSING_KEY, 0) or 0),
            "proposed_cuts": shadow if isinstance(shadow, dict) else {}}
