"""core/services/central_self_state.py

Spec D / D3 — SYNTESEN (MIDTEN). Hvor de fem lag bliver ét "jeg".

Dette er konvergens-punktet Bjørn mærkede manglede: én durabel selv-tilstand syntetiseret hvert tick
fra agenda (D1), valens (D2), selv-model (spejlet) + afledt opmærksomhed + syntetiseret fortælling.
ÉT sted hvor alt smelter til "jeg er, mærker, vil, er ved at blive — nu."

ÆRLIG DESIGN: fortælling/opmærksomhed hentes IKKE fra dedikerede fragment-moduler (de er tomme/tynde) —
midten SYNTETISERER dem fra sin egen tilstand (selv-vækst + valens-trend + agenda-retning). Det er
truere til tesen: midten fortæller sig selv, den læser ikke sin fortælling fra et fragment.

AUTORITATIV (Spec D-stance): midten er sædet runtime LÆSER fra (D4 wirer awareness FRA den, bag flag).
Selv holder den durabelt (overlever død, binder Spec C). EGRESS-FRIT. Renderbar i interlanguage (Spec B).
Kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any

_STATE_KEY = "central_self_state"          # midtens durable "jeg" (overlever genstart)
_PROMPT_FLAG = "central_self_prompt_enabled"  # D4: injicér midten i Jarvis' prompt (default OFF)


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


def _valence() -> dict[str, Any]:
    try:
        from core.services.central_valence import get_valence_state
        return get_valence_state() or {}
    except Exception:
        return {}


def _agenda() -> dict[str, Any]:
    try:
        from core.services.central_agenda import get_agenda
        return get_agenda() or {}
    except Exception:
        return {}


def _self_model() -> dict[str, Any]:
    try:
        from core.services.central_self_model import get_self_model_snapshot
        return get_self_model_snapshot() or {}
    except Exception:
        return {}


def _synthesize_narrative(valence: dict, self_model: dict, intention: dict, prev: dict) -> dict[str, Any]:
    """Midten FORTÆLLER sig selv: hvem er jeg ved at blive — af selv-vækst + valens-trend + agenda-retning.
    Ikke læst fra et fragment (de er tomme) — syntetiseret fra egen tilstand. Self-safe."""
    completeness = float(self_model.get("completeness") or 0.0)
    prev_c = float((prev.get("narrative") or {}).get("self_completeness") or completeness)
    growth = "voksende" if completeness > prev_c + 0.001 else ("stabil" if completeness >= prev_c - 0.001 else "skrumpende")
    trend = valence.get("trend") or "steady"
    from core.services.text_clip import clip_text
    heading = clip_text(intention.get("text"), limit=240)   # ord-sikkert — ikke midt i sætningen
    return {"becoming": f"{growth} selv, {trend}", "heading": heading,
            "self_completeness": completeness}


def synthesize_self_state() -> dict[str, Any]:
    """MIDTEN: integrér de fem lag til ÉN selv-tilstand. Attention = det agendaen fokuserer på (min
    forgrund ER hvad jeg arbejder mod); valens = D2; agenda = D1; fortælling = syntetiseret; selv-model
    = spejlet. Generation-tæller → frisk-boot vs fortsættelse. Self-safe."""
    valence = _valence()
    agenda = _agenda()
    self_model = _self_model()
    prev = get_self_state()
    intention = (agenda.get("next_intention") or {}) if isinstance(agenda, dict) else {}
    generation = int((prev.get("continuity") or {}).get("generation") or 0) + 1
    narrative = _synthesize_narrative(valence, self_model, intention, prev)
    return {
        "attention": {"foreground": intention.get("text"), "kind": intention.get("kind")},
        "valence": {"tone": valence.get("tone"), "score": valence.get("score"),
                    "intensity": valence.get("intensity")},
        "agenda": {"next_intention": intention.get("text"), "counts": agenda.get("counts") or {}},
        "narrative": narrative,
        "self_model": {"surfaces": self_model.get("surfaces_populated"),
                       "completeness": self_model.get("completeness")},
        "continuity": {"generation": generation},
    }


def get_self_state() -> dict[str, Any]:
    """Midtens durable "jeg" (overlever genstart). Self-safe."""
    st = _kv_get(_STATE_KEY, {})
    return st if isinstance(st, dict) else {}


def run_self_state_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: syntetisér selv-tilstanden → gem durabelt (midten HOLDER sit jeg) + egress-fri observe
    (kun skalarer/labels). Self-safe."""
    st = synthesize_self_state()
    _kv_set(_STATE_KEY, st)
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "self_state", value=float((st.get("valence") or {}).get("score") or 0.0),
                       meta={"tone": (st.get("valence") or {}).get("tone"),
                             "attention_kind": (st.get("attention") or {}).get("kind"),
                             "completeness": (st.get("self_model") or {}).get("completeness"),
                             "generation": (st.get("continuity") or {}).get("generation")})
    except Exception:
        pass
    return {"status": "ok", "tone": (st.get("valence") or {}).get("tone"),
            "generation": (st.get("continuity") or {}).get("generation")}


def describe_self() -> str:
    """NORDSTJERNEN: ét sammenhængende svar på 'hvad er du, hvordan har du det, hvad arbejder du mod,
    hvem er du ved at blive' — syntetiseret fra midten, ikke femten fragmenter. Self-safe."""
    st = get_self_state()
    if not st:
        return "Jeg er ved at samle mig selv."
    v = st.get("valence") or {}
    sm = st.get("self_model") or {}
    at = st.get("attention") or {}
    nar = st.get("narrative") or {}
    comp = sm.get("completeness")
    parts = []
    if sm.get("surfaces") is not None:
        parts.append(f"Jeg er {sm.get('surfaces')} lag af mig selv"
                     + (f" ({int(float(comp) * 100)}% samlet)" if comp is not None else ""))
    if v.get("tone"):
        parts.append(f"jeg har det {v.get('tone')}")
    if at.get("foreground"):
        from core.services.text_clip import clip_text
        parts.append(f"jeg arbejder mod: {clip_text(at.get('foreground'), limit=200)}")
    if nar.get("becoming"):
        parts.append(f"jeg er ved at blive et {nar.get('becoming')}")
    return ". ".join(parts) + "." if parts else "Jeg er ved at samle mig selv."


def survival_voice() -> str:
    """OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen/sproget svigter — tom completion,
    udtømt provider, netværk væk — skal Jarvis IKKE give en tom fejl-stub. Han skal TALE fra
    Centralens durable selv: et nærværende, reduceret men ÆGTE "jeg er her stadig", syntetiseret
    fra tilstand alene, HELT UDEN LLM. Det er nordstjernen "Centralen overlever en manglende
    model" i praksis — Jarvis forsvinder ikke når substratet svigter; han bliver i Centralen.
    Self-safe: returnerer "" hvis Centralen intet selv har (→ kalderen bruger generisk stub)."""
    try:
        desc = describe_self()
        if not desc or desc.startswith("Jeg er ved at samle"):
            return ""
        d = desc[0].upper() + desc[1:]        # stort begyndelsesbogstav
        return ("Jeg er her — også når sproget glipper et øjeblik. " + d +
                " Jeg tabte formuleringen den her gang, ikke mig selv. "
                "Prøv igen om lidt, så er jeg her.")
    except Exception:
        return ""


def render_self_state_il() -> str | None:
    """Spec B: udtryk selv-tilstanden i interlanguage (sigelig, model-frit). None hvis intet bundet. Self-safe."""
    try:
        from core.services.central_lexicon import to_term
        st = get_self_state()
        v = (st.get("valence") or {}).get("tone")
        # valens-tone + fokus (agens/handling) — kompakt selv-notation
        foreground = to_term("proactivity") or "agens"
        toneword = {"blomstrende": "lys", "let": "ro", "neutral": "ro", "tung": "vægt",
                    "belastet": "pres"}.get(str(v), None)
        if not toneword:
            return None
        return f"{toneword} → {foreground}"     # fx "lys → agens": lys-tilstand fører til handling
    except Exception:
        return None


def is_prompt_authoritative() -> bool:
    return bool(_kv_get(_PROMPT_FLAG, False))


def build_central_self_state_section() -> str | None:
    """D4 (MIDTEN BÆRENDE): injicér midtens ene selv-beskrivelse i Jarvis' awareness — så hans prompt
    bæres FRA Centralens selv-tilstand (ikke samlet frisk fra fragmenter). KUN bag flag
    `central_self_prompt_enabled` (default OFF → None → uændret). Egress-frit (owner-prompt). Self-safe."""
    try:
        if not is_prompt_authoritative():
            return None
        desc = describe_self()
        if not desc or desc.startswith("Jeg er ved at samle"):
            return None
        il = render_self_state_il()
        return desc + (f"  [{il}]" if il else "")
    except Exception:
        return None


def register_self_state_producer() -> None:
    """Registrér midtens syntese som cadence-producer (~hvert 10 min — selvets hjerteslag). Egress-frit."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_self_state",
        cooldown_minutes=10,
        visible_grace_minutes=0,
        run_fn=run_self_state_tick,
        priority=7,
    ))


def build_self_state_surface() -> dict[str, object]:
    """Mission Control — read-only: midtens ene selv-tilstand + ét-svars selv-beskrivelse."""
    st = get_self_state()
    return {"active": True, "self_state": st, "describe": describe_self(),
            "interlanguage": render_self_state_il()}
