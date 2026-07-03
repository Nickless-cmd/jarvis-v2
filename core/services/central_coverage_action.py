"""core/services/central_coverage_action.py

§11 #5 (spec 2026-07-03) — DEL 2: gør Centralens strukturelle blindhed HANDLINGS-udløsende.

`central_coverage.structural_coverage()` gør blindheden runtime-KENDT (Del 1). Men et blindheds-kort
uden konsekvens er stadig ren observation. Her lukkes hullet: når den STRUKTURELLE dækning er lav,
ELLER en DARK-family (som Centralen ikke ser) bærer meget LIVE signal, foreslås en governed hypotese
— men bag et reversibelt flag, shadow-først.

⚖️ FLAGET (runtime-state kv `central_coverage_action_mode`, default "off"):
  * off    → INTET beregnes handlings-mæssigt (0 adfærdsændring — nuværende tilstand).
  * shadow → beregn HVAD den VILLE flagge (kandidat-hypoteser) + observér tælleren egress-frit,
             men opret INTET. Ren skygge (det spec kalder "reaktion i skygge").
  * on     → opret faktisk governede hypoteser via central_hypothesis_generator (den EKSISTERENDE
             mekanisme — ingen ny hypotese-livscyklus). Governance-invarianten holder: hver hypotese
             er pre-registreret og KAN DØ via central_hypothesis_governance (§8).

GOVERNANCE-INVARIANT: vi genopfinder IKKE hypotese-hjemmet. Kandidaterne formuleres som fuldt
pre-registrerede hypoteser (statement/prediction/null/success_criterion/sample_size/ttl/provenance)
og registreres gennem `register_governed_hypothesis`, som validerer pre-registrering og tildeler
dødsmekanismen. En hypotese der ikke bekræftes af friske samples dør (TTL/falsifikation).

Alt self-safe, kaster ALDRIG. Egress-frit (kun record_private + owner-lokal trace).
"""
from __future__ import annotations

from typing import Any

# Flag + tærskler.
_MODE_KEY = "central_coverage_action_mode"       # off | shadow | on   (default off)
_STRUCTURAL_LOW = 0.35    # strukturel dækning under dette = "lav" (i dag ~0.30 → udløser)
_DARK_SIGNAL_MIN = 5      # en dark-family der bærer ≥ så mange LIVE events i vinduet = "varm blind plet"
_MAX_CANDIDATES = 6       # loft pr. tick (multiple-comparisons-disciplin + ingen spam)
_DEFAULT_SAMPLE_SIZE = 5
_DEFAULT_TTL_S = 14 * 24 * 3600   # strukturelle blindhed-hypoteser lever længere (langsomt-bevægende)


def get_mode() -> str:
    """Læs handlings-tilstanden fra runtime-state kv. Default "off" → ingen adfærdsændring. Self-safe."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_MODE_KEY, "off")
        v = str(v or "off").strip().lower()
        return v if v in ("off", "shadow", "on") else "off"
    except Exception:
        return "off"


def _dark_family_live_signal(top_dark_families: list[dict[str, Any]], *,
                             window: int) -> list[dict[str, Any]]:
    """Kryds de strukturelt-mørke families med hvad der FAKTISK flyder i event-vinduet: en dark-family
    der bærer meget live-signal er en VARM blind plet (Centralen går glip af aktiv information, ikke
    bare død kode). Self-safe → [] ved fejl."""
    dark_names = {str(d.get("family")) for d in (top_dark_families or []) if d.get("family")}
    if not dark_names:
        return []
    seen: dict[str, int] = {}
    try:
        from core.eventbus.bus import event_bus
        for ev in event_bus.recent(limit=int(window)):
            fam = str(ev.get("kind") or "").split(".", 1)[0]
            if fam in dark_names:
                seen[fam] = seen.get(fam, 0) + 1
    except Exception:
        return []
    hot = [{"family": f, "live_events": n} for f, n in seen.items() if n >= _DARK_SIGNAL_MIN]
    hot.sort(key=lambda x: x["live_events"], reverse=True)
    return hot


def _formulate_structural_blindness_hypothesis(sc: dict[str, Any]) -> dict[str, Any]:
    """Lav strukturel dækning → fuldt pre-registreret hypotese om at de mørke filer bærer signal der
    ville ændre Centralens beslutninger hvis den så det. Falsificerbar (§8)."""
    total = int(sc.get("total") or 0)
    dark = int(sc.get("dark") or 0)
    ratio = sc.get("structural_ratio")
    return {
        "source": "structural_coverage",
        "statement": f"Centralen er strukturelt blind for {dark} af {total} filer "
                     f"(dækning {ratio}) — nogle af de mørke filer bærer beslutnings-relevant signal",
        "prediction": "Når en i dag DARK event-family kobles til Centralen, ændrer den mindst ét "
                      "verdikt/en prioritering den ellers ville have truffet i blinde",
        "null_hypothesis": "De mørke filer er rent inaktive/redundante — at koble dem ændrer intet "
                           "verdikt (dækningen er lav men uden konsekvens)",
        "success_criterion": f">= {_DEFAULT_SAMPLE_SIZE} jordede observationer hvor et nyligt koblet "
                             f"signal ændrede et udfald",
        "sample_size": _DEFAULT_SAMPLE_SIZE,
        "ttl_seconds": _DEFAULT_TTL_S,
        "provenance": {"mechanism": "structural_coverage",
                       "family": f"structural_blindness:{dark}/{total}",
                       "cursor_id": dark},
        "confidence": 0.3,
    }


def _formulate_dark_family_hypothesis(hot: dict[str, Any]) -> dict[str, Any]:
    """En VARM dark-family (bærer live-signal Centralen ikke ser) → fuldt pre-registreret hypotese."""
    fam = str(hot.get("family"))
    n = int(hot.get("live_events") or 0)
    return {
        "source": "dark_family_signal",
        "statement": f"Family '{fam}' er strukturelt DARK men bar {n} live-events i vinduet — "
                     f"Centralen går glip af aktivt signal, ikke bare død kode",
        "prediction": f"Events i '{fam}' korrelerer med udfald Centralen i dag forklarer dårligt; "
                      f"at route '{fam}' hæver forklarings-/forudsigelses-evnen målbart",
        "null_hypothesis": f"'{fam}'-events er uafhængige af ethvert udfald Centralen bryr sig om "
                           f"(volumen uden betydning)",
        "success_criterion": f">= {_DEFAULT_SAMPLE_SIZE} jordede samples hvor '{fam}' forudgik et "
                             f"relevant udfald",
        "sample_size": _DEFAULT_SAMPLE_SIZE,
        "ttl_seconds": _DEFAULT_TTL_S,
        "provenance": {"mechanism": "dark_family_signal", "family": f"dark:{fam}", "cursor_id": n},
        "confidence": 0.3,
    }


def compute_candidates(*, window: int = 2000) -> list[dict[str, Any]]:
    """Beregn HVAD blindheden VILLE udløse (uafhængigt af flag): pre-registrerede hypotese-kandidater
    fra (a) lav strukturel dækning og (b) varme dark-families. Ren beregning — opretter INTET. Self-safe."""
    from core.services import central_coverage as cov
    candidates: list[dict[str, Any]] = []
    try:
        sc = cov.structural_coverage()
    except Exception:
        return []
    if not sc.get("available"):
        return []
    ratio = sc.get("structural_ratio")
    if isinstance(ratio, (int, float)) and ratio < _STRUCTURAL_LOW:
        candidates.append(_formulate_structural_blindness_hypothesis(sc))
    for hot in _dark_family_live_signal(sc.get("top_dark_families") or [], window=window):
        candidates.append(_formulate_dark_family_hypothesis(hot))
    return candidates[:_MAX_CANDIDATES]


def run_coverage_action_tick(*, trigger: str = "cadence",
                             last_visible_at: str = "") -> dict[str, object]:
    """Handlings-tick (§11 #5): beregn kandidater → agér EFTER flag. Self-safe, kaster aldrig.

    off    → returnér straks (0 arbejde ud over flag-læsning).
    shadow → beregn + observér egress-frit HVOR mange den VILLE flagge; opret intet.
    on     → registrér kandidaterne som governede hypoteser (de kan dø via §8-governance).
    """
    mode = get_mode()
    if mode == "off":
        return {"status": "ok", "mode": "off", "candidates": 0, "registered": 0}

    try:
        candidates = compute_candidates()
    except Exception:
        candidates = []

    registered, rejected, dup = 0, 0, 0
    if mode == "on":
        try:
            from core.services import central_hypothesis_generator as hg
            for hyp in candidates:
                res = hg.register_governed_hypothesis(hyp)
                st = res.get("status")
                if st == "registered":
                    registered += 1
                elif st == "rejected":
                    rejected += 1
                elif st in ("duplicate",):
                    dup += 1
        except Exception:
            pass

    # Egress-fri observe (kun tællere — self-safe). I shadow ser Bjørn HVAD den ville have flagget
    # uden at noget faktisk oprettes.
    try:
        from core.services.central_private_observe import record_private
        record_private("system", "coverage_action",
                       value=float(len(candidates)),
                       meta={"mode": mode, "candidates": len(candidates),
                             "registered": registered, "rejected": rejected, "duplicate": dup})
    except Exception:
        pass

    return {"status": "ok", "mode": mode, "candidates": len(candidates),
            "registered": registered, "rejected": rejected, "duplicate": dup,
            "would_register": (len(candidates) if mode == "shadow" else registered)}


def register_coverage_action_producer() -> None:
    """Registrér handlings-tricket som cadence-producer (~hvert 60 min, lav prioritet). Flag=off
    default → producer'en er billig no-op indtil Bjørn flipper flaget."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_coverage_action",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=run_coverage_action_tick,
        priority=7,
    ))


def build_central_coverage_action_surface() -> dict[str, object]:
    """Mission Control surface — read-only: nuværende mode + hvad blindheden VILLE flagge lige nu.
    Viser kandidat-statements uden at oprette noget (shadow-transparens)."""
    mode = get_mode()
    try:
        cands = compute_candidates()
    except Exception:
        cands = []
    return {"active": True, "mode": mode,
            "candidate_count": len(cands),
            "candidates": [{"source": c.get("source"), "statement": c.get("statement")} for c in cands],
            "note": "off=intet · shadow=beregn+observér · on=opret governede (dødelige) hypoteser"}
