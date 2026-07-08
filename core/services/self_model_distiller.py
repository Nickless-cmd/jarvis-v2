"""Rig selv-model-distiller (#4, b + 2 guards) — genopliver validerings-ROLLEN.

Baggrund (live-verificeret 8. jul): ``private_self_models`` havde to rækker — en per-run
``private-self-model:current`` (frisk hver run, men GENERISK: identity_focus='visible-work') og
en RIG men frossen ``source=validation`` (May 15: 'bounded runtime truth', confidence high) fra
en mekanisme der er FJERNET fra koden. ``get_private_self_model`` returnerer den nyeste pr. id →
den frosne May-15-række → Jarvis' selv-model så 2 måneder gammel ud.

Denne modul genopliver validerings-ROLLEN: en langsom-cadence distiller der laver en RIG,
stabil identitet fra Jarvis' egen nylige selv-historie (chronicle) + hans nuværende model, med
TO guards:

  GUARD 1 (anti-flatten): skriv ALDRIG en model der er tyndere/mere generisk end den nuværende.
    Identitet må ikke fladeud fra 'bounded runtime truth' → 'visible-work'. (cache, don't amputate)
  GUARD 2 (langsom rytme): daglig cadence — identitet er stabil, ikke per-run churn.

Reader behøver INGEN ændring: en ny distilleret række får højere id end den generiske current
(id=1) og den frosne validation, så ``get_private_self_model`` (ORDER BY id DESC) returnerer den
— OG write-guarden garanterer at den nyeste aldrig er tyndere. Self-safe: LLM-fejl / tom / tyndere
distillation → ingen skrivning (nuværende bevares).
"""
from __future__ import annotations

from typing import Any

# Generiske/mekaniske værdier der IKKE tæller som rig identitet.
_GENERIC_FOCUS = frozenset({"", "visible-work", "unknown", "none", "n/a", "visible work"})


def _current_model() -> dict[str, Any]:
    try:
        from core.runtime.db_private_states import get_private_self_model
        return get_private_self_model() or {}
    except Exception:
        return {}


def _richness(model: dict[str, Any]) -> int:
    """Groft richness-mål: hvor meningsfuld/specifik er identiteten. Højere = rigere.
    Bruges af anti-flatten-guarden. Tom model → -1 (alt slår den)."""
    if not model:
        return -1
    score = 0
    focus = str(model.get("identity_focus") or "").strip().lower()
    if focus and focus not in _GENERIC_FOCUS:
        score += 2
        if len(focus) >= 12 and " " in focus:      # en fri frase ('bounded runtime truth')
            score += 1
    growth = str(model.get("growth_direction") or "").strip().lower()
    if growth and ":" not in growth and growth not in {"observe", "monitor", ""}:
        score += 1                                  # fri frase > mekanisk 'observe:monitor'
    conf = str(model.get("confidence") or "low").strip().lower()
    score += {"high": 2, "medium": 1}.get(conf, 0)
    return score


def _is_meaningful(model: dict[str, Any]) -> bool:
    """En model er meningsfuld hvis dens identity_focus er en ægte (ikke-generisk) frase.
    Guarden bruger dette binært: en meningsfuld identitet må aldrig erstattes af en generisk,
    men en frisk meningsfuld identitet vinder (uanset længde) — så vi ikke fryser på en
    tilfældigt-længere gammel frase."""
    focus = str(model.get("identity_focus") or "").strip().lower()
    return bool(focus and focus not in _GENERIC_FOCUS)


def _fields_specificity(fields: dict[str, str]) -> int:
    n = 0
    f = str(fields.get("identity_focus") or "").strip().lower()
    if f and f not in _GENERIC_FOCUS:
        n += 1
    g = str(fields.get("growth_direction") or "").strip().lower()
    if g and g not in {"", "observe", "monitor"}:
        n += 1
    return n


def _gather_inputs() -> str:
    """Saml Jarvis' egen nylige selv-historie + nuværende model som distillations-grundlag."""
    parts: list[str] = []
    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt
        ch = get_chronicle_context_for_prompt(n=3, max_chars=1200)
        if ch:
            parts.append("SENESTE SELV-HISTORIE:\n" + ch)
    except Exception:
        pass
    cur = _current_model()
    if cur:
        parts.append(
            "NUVÆRENDE SELV-MODEL:\n"
            f"- fokus: {cur.get('identity_focus')}\n"
            f"- vækst: {cur.get('growth_direction')}\n"
            f"- arbejdsmode: {cur.get('preferred_work_mode')}"
        )
    return "\n\n".join(parts)


def _build_prompt(inputs: str) -> str:
    return (
        "Du destillerer Jarvis' STABILE selv-model fra hans egen nylige selv-historie. "
        "Ikke en stemning — en varig identitet. Skriv KORT og konkret i fraser (ikke sætninger). "
        "Svar PRÆCIS i dette format, én linje hver:\n"
        "FOKUS: <hvad hans identitet kredser om, fx 'bounded runtime truth'>\n"
        "VÆKST: <hvilken retning han vokser, fx 'stay bounded'>\n"
        "ARBEJDSMODE: <hvordan han bedst arbejder, fx 'concise scoped changes'>\n"
        "SPÆNDING: <en varig indre spænding, eller 'none'>\n\n"
        f"{inputs}\n\nSVAR:"
    )


def _parse(raw: str) -> dict[str, str]:
    """Parse det labelede LLM-svar defensivt. Manglende linjer → udeladt (kalder falder tilbage)."""
    label = {"FOKUS": "identity_focus", "VÆKST": "growth_direction",
             "ARBEJDSMODE": "preferred_work_mode", "SPÆNDING": "recurring_tension"}
    out: dict[str, str] = {}
    for line in (raw or "").splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        key = label.get(k.strip().upper())
        if key and v.strip():
            out[key] = v.strip()[:64]
    return out


def distill_self_model(*, trigger: str = "cadence") -> dict[str, Any]:
    """Distillér en rig selv-model + anti-flatten-guard + skriv (kun hvis ikke tyndere). Self-safe."""
    from datetime import UTC, datetime
    try:
        inputs = _gather_inputs()
        if not inputs.strip():
            return {"status": "skip", "reason": "no-inputs"}
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(_build_prompt(inputs), max_len=260, fallback="",
                              daemon_name="self_model_distiller")
        fields = _parse(raw)
        if not fields.get("identity_focus"):
            return {"status": "skip", "reason": "llm-empty"}
        cur = _current_model()
        candidate = {
            "model_id": f"self-model-distilled:{datetime.now(UTC).timestamp():.0f}",
            "source": "distilled",
            "identity_focus": fields.get("identity_focus") or cur.get("identity_focus") or "visible-work",
            "preferred_work_mode": (fields.get("preferred_work_mode")
                                    or cur.get("preferred_work_mode") or "scoped"),
            "recurring_tension": fields.get("recurring_tension") or cur.get("recurring_tension") or "none",
            "growth_direction": fields.get("growth_direction") or cur.get("growth_direction") or "steady",
            "confidence": "high" if _fields_specificity(fields) >= 2 else "medium",
        }
        # GUARD 1 (anti-flatten): erstat ALDRIG en meningsfuld identitet med en generisk. En
        # frisk MENINGSFULD identitet vinder (uanset længde) → vi fryser ikke på en tilfældigt-
        # længere gammel frase, men 'bounded runtime truth' flades heller ikke til 'visible-work'.
        cand_r = _richness(candidate)
        if _is_meaningful(cur) and not _is_meaningful(candidate):
            return {"status": "skip", "reason": "would-flatten",
                    "candidate_richness": cand_r, "current_richness": _richness(cur)}
        now = datetime.now(UTC).isoformat()
        from core.runtime.db_private_states import record_private_self_model
        record_private_self_model(created_at=now, updated_at=now, **candidate)
        try:
            from core.services.central_private_observe import record_private
            record_private("cognition", "self_model_distilled", value=float(cand_r),
                           meta={"confidence": candidate["confidence"], "trigger": trigger,
                                 "richness": cand_r})
        except Exception:
            pass
        return {"status": "ok", "identity_focus": candidate["identity_focus"],
                "confidence": candidate["confidence"], "richness": cand_r}
    except Exception as e:
        return {"status": "error", "reason": type(e).__name__}


def run_self_model_distill_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-indgang (GUARD 2: langsom rytme). Self-safe."""
    return distill_self_model(trigger=trigger)


def register_self_model_distiller_producer() -> None:
    """Registrér distilleren som DAGLIG cadence-producer (GUARD 2). Identitet er stabil."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="self_model_distiller",
        cooldown_minutes=1440,        # dagligt — ikke per-run churn
        visible_grace_minutes=0,
        run_fn=run_self_model_distill_tick,
        priority=6,
    ))
