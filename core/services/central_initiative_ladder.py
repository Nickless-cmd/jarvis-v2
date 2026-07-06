"""central_initiative_ladder — den gradvise, gatede initiativ-stige (rådets #3).

Delene fandtes men var ikke en STIGE: initiative_accumulator (wants),
autonomy_proposal_queue (forslag) og generative_autonomy (udførelse) levede
side om side uden et fælles trin-flow med gates imellem. Dette lag MODELLERER
flowet — det bygger IKKE ny autonomi-eksekvering. Det læser eksisterende
tilstand og afleder for det stærkeste initiativ HVILKET trin det er på, og om
gaten til næste trin er åben.

    OBSERVE  → (gate: er der et vedvarende want?)          → PROPOSE
    PROPOSE  → (gate: er forslaget godkendt/sikkert?)       → EXECUTE
    EXECUTE  → (gate: kørte det?)                           → LEARN
    LEARN    → (feed udfald tilbage)

Gates er OBSERVE-ONLY. De UDFØRER intet — de RAPPORTERER om trinnet må løftes.
Ingen gate auto-godkender et forslag; PROPOSE→EXECUTE læser proposal-status
(pending-godkendt = allerede godkendt af Bjørn), den godkender aldrig selv.

§24.4 (reducér ved kilden): evaluate_ladder returnerer KUN skalarer og korte
labels — aldrig rå want-tekst, rå rationale eller andet privat indhold. Topic/
kind bruges kun til at bygge et kort, ufølsomt label.

SELF-SAFE ende-til-ende: hver aflæsning i eget try/except; tom tilstand giver
OBSERVE + lukket gate uden crash. evaluate_ladder kaster aldrig.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class InitiativeStage(Enum):
    """De fire trin et initiativ stiger igennem."""

    OBSERVE = "observe"
    PROPOSE = "propose"
    EXECUTE = "execute"
    LEARN = "learn"


# Tærskel for hvornår et top-want er "vedvarende/stærkt nok" til at gaten
# OBSERVE→PROPOSE åbner. Bevidst konservativ (deterministisk, læsbar).
_SALIENCE_THRESHOLD = 0.5

# Proposal-statusser der betyder "godkendt af Bjørn og klar til/udført
# eksekvering" — dvs. gaten PROPOSE→EXECUTE er åben. "pending" er IKKE her:
# et pending-forslag afventer stadig godkendelse (gaten lukket).
_APPROVED_STATUSES = {"approved", "executed"}

# Proposal-statusser der betyder "kørte færdigt" — gaten EXECUTE→LEARN åben.
_COMPLETED_STATUSES = {"executed", "failed"}


def _label_for_want(top_want: dict[str, Any] | None) -> str:
    """Byg et kort, ufølsomt label for det stærkeste initiativ.

    Bruger kun want_type (kategori) — ALDRIG rå topic-fritekst som privat
    indhold. want_type er en fast enum-agtig kategori (insight/meaning/…), så
    den er sikker at vise. Self-safe.
    """
    if not isinstance(top_want, dict):
        return "—"
    want_type = str(top_want.get("want_type") or "").strip()
    return want_type or "—"


def _read_accumulator_state() -> dict[str, Any]:
    """Læs initiative-accumulator-tilstand. Self-safe → tomt."""
    try:
        from core.services.initiative_accumulator import (
            get_initiative_accumulator_state,
        )

        state = get_initiative_accumulator_state()
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _read_proposal_surface() -> dict[str, Any]:
    """Læs autonomy-proposal-surfacen. Self-safe → tomt."""
    try:
        from core.services.autonomy_proposal_queue import (
            build_autonomy_proposal_surface,
        )

        surface = build_autonomy_proposal_surface(limit=20)
        return surface if isinstance(surface, dict) else {}
    except Exception:
        return {}


def _proposals_from_surface(surface: dict[str, Any]) -> list[dict[str, Any]]:
    """Uddrag proposal-listen fra surfacen (items eller recent). Self-safe."""
    if not isinstance(surface, dict):
        return []
    raw = surface.get("items") or surface.get("proposals") or surface.get("recent") or []
    if not isinstance(raw, list):
        return []
    return [p for p in raw if isinstance(p, dict)]


def _stage_counts(
    accumulator: dict[str, Any], proposals: list[dict[str, Any]]
) -> dict[str, int]:
    """Tæl hvor mange initiativer der pt. sidder på hvert trin.

    - observe: wants der endnu ikke er blevet forslag
    - propose: pending forslag (afventer godkendelse)
    - execute: godkendte forslag (approved — klar/i gang)
    - learn:   færdigkørte forslag (executed/failed)
    """
    try:
        want_count = int(accumulator.get("want_count") or 0)
    except Exception:
        want_count = 0

    propose = 0
    execute = 0
    learn = 0
    for p in proposals:
        status = str(p.get("status") or "").strip().lower()
        if status == "pending":
            propose += 1
        elif status == "approved":
            execute += 1
        elif status in ("executed", "failed"):
            learn += 1

    # OBSERVE-tælleren = wants der ikke allerede er forslag. Vi kan ikke
    # matche 1:1 (accumulator er in-memory wants, proposals er DB), så vi
    # rapporterer wants som observe-trin — det er trinnet de bor på.
    observe = want_count

    return {
        "observe": observe,
        "propose": propose,
        "execute": execute,
        "learn": learn,
    }


def _gate_observe_to_propose(accumulator: dict[str, Any]) -> tuple[bool, str]:
    """Gate: er der et vedvarende/stærkt nok want til at foreslå?"""
    top = accumulator.get("top_want")
    if not isinstance(top, dict):
        return False, "intet want at foreslå"
    try:
        strength = float(top.get("strength") or 0.0)
    except Exception:
        strength = 0.0
    if strength >= _SALIENCE_THRESHOLD:
        return True, f"want stærkt nok (salience {strength:.2f} ≥ {_SALIENCE_THRESHOLD})"
    return False, f"want for svagt (salience {strength:.2f} < {_SALIENCE_THRESHOLD})"


def _gate_propose_to_execute(
    proposals: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Gate: er et forslag godkendt/sikkert (læser status, auto-godkender IKKE)?"""
    approved = [
        p for p in proposals
        if str(p.get("status") or "").strip().lower() in _APPROVED_STATUSES
    ]
    if approved:
        return True, "et forslag er godkendt af Bjørn"
    pending = [
        p for p in proposals
        if str(p.get("status") or "").strip().lower() == "pending"
    ]
    if pending:
        return False, "forslag afventer godkendelse"
    return False, "intet forslag klar"


def _gate_execute_to_learn(
    proposals: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Gate: kørte det seneste initiativ-forslag færdigt?"""
    completed = [
        p for p in proposals
        if str(p.get("status") or "").strip().lower() in _COMPLETED_STATUSES
    ]
    if completed:
        return True, "seneste forslag kørte færdigt"
    return False, "intet forslag har kørt endnu"


def _strongest_stage(
    accumulator: dict[str, Any], proposals: list[dict[str, Any]]
) -> InitiativeStage:
    """Afled hvilket trin det STÆRKESTE initiativ er nået til.

    Vi vælger det HØJESTE trin der har mindst ét initiativ, fordi det
    repræsenterer hvor langt Jarvis' initiativ faktisk er nået. Rækkefølge:
    LEARN > EXECUTE > PROPOSE > OBSERVE. Tom tilstand → OBSERVE.
    """
    statuses = {str(p.get("status") or "").strip().lower() for p in proposals}
    if statuses & _COMPLETED_STATUSES:
        return InitiativeStage.LEARN
    if "approved" in statuses:
        return InitiativeStage.EXECUTE
    if "pending" in statuses:
        return InitiativeStage.PROPOSE
    return InitiativeStage.OBSERVE


def evaluate_ladder() -> dict[str, Any]:
    """Afled initiativ-stigens tilstand fra eksisterende runtime-state.

    Returnerer KUN skalarer/korte labels (§24.4 — ingen rå want/rationale-tekst):

        {
          "stage": <navn>,             # aktuelt trin for stærkeste initiativ
          "gate_open": bool,           # er gaten til NÆSTE trin åben?
          "gate_reason": str,          # kort, deterministisk begrundelse
          "top_initiative": str,       # kort label (want_type/kategori)
          "counts": {observe, propose, execute, learn},
        }

    Self-safe: tom tilstand → OBSERVE + lukket gate, ingen crash.
    """
    accumulator = _read_accumulator_state()
    surface = _read_proposal_surface()
    proposals = _proposals_from_surface(surface)

    counts = _stage_counts(accumulator, proposals)
    stage = _strongest_stage(accumulator, proposals)
    top_label = _label_for_want(accumulator.get("top_want"))

    # Gaten der rapporteres er den fra det AKTUELLE trin til det næste.
    if stage is InitiativeStage.OBSERVE:
        gate_open, gate_reason = _gate_observe_to_propose(accumulator)
    elif stage is InitiativeStage.PROPOSE:
        gate_open, gate_reason = _gate_propose_to_execute(proposals)
    elif stage is InitiativeStage.EXECUTE:
        gate_open, gate_reason = _gate_execute_to_learn(proposals)
    else:  # LEARN — sidste trin, ingen gate opad; udfald fodres tilbage
        gate_open, gate_reason = False, "sidste trin — udfald fodres tilbage"

    return {
        "stage": stage.value,
        "gate_open": bool(gate_open),
        "gate_reason": str(gate_reason),
        "top_initiative": top_label,
        "counts": counts,
    }


def absorb_ladder() -> dict[str, Any]:
    """Evaluér stigen og absorbér den som en levende central-nerve.

    Fuld behandling via central_absorb.absorb (observe+trace+flag+læring).
    Flag rejses hvis et initiativ er nået til et trin men gaten er lukket
    (dvs. det er "stuck" og venter — værd for Centralen at bemærke). §24.4:
    kun de skalarer evaluate_ladder allerede returnerer. Self-safe.
    """
    result = evaluate_ladder()
    try:
        from core.services.central_absorb import absorb

        absorb(
            "initiative",
            "ladder",
            {
                "stage": result["stage"],
                "gate_open": result["gate_open"],
                "top_initiative": result["top_initiative"],
                "counts": result["counts"],
            },
            flag_if=lambda v: not v["gate_open"]
            and v["stage"] != InitiativeStage.OBSERVE.value,
            flag_reason="initiativ venter — gate lukket",
            learn_key="initiative:ladder",
        )
    except Exception:
        pass
    return result
