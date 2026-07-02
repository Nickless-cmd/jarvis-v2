"""core/services/central_agenda.py

Spec D / D1 — CENTRALEN EJER JARVIS' DAGSORDEN (første ægte autoritet).

Bjørns korrektion: Centralen skal VÆRE Jarvis, ikke observere ham. Agendaen findes i dag spredt over
~15 runtime-moduler (goals/plans/todos/initiativer) — ingen ÉN dagsorden. Dette modul KONVERGERER dem
til Centralens ene selv-ejede, prioriterede dagsorden + vælger næste-intention.

AUTORITET bag reversibel vagt:
  * Centralen LÆSER fra de 15 kilde-moduler (feed) men EJER den syntetiserede prioriterede helhed +
    den valgte næste-intention — durabelt (overlever genstart). INGEN dobbelt-sandhed: kilderne muterer
    egne rækker; midten ejer sammenstillingen.
  * `authoritative_next_intention()` returnerer Centralens valgte retning KUN bag
    `central_agenda_authoritative_enabled` (default OFF) → runtime læser den; ellers gammel sti.
    Shadow (default): Centralen HOLDER dagsordenen men driver intet. Egress-frit. Kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any

_AGENDA_KEY = "central_agenda"                              # Centralens durable ejede dagsorden
_AUTHORITATIVE_FLAG = "central_agenda_authoritative_enabled"  # Bjørns switch (default OFF)


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


def is_authoritative() -> bool:
    return bool(_kv_get(_AUTHORITATIVE_FLAG, False))


# ── Kilde-læsning (feed) — hver best-effort, self-safe ───────────────────────────────
def _read_goals() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        from core.services.goal_signal_synthesizer import synthesize_candidate_goals
        cand = synthesize_candidate_goals(max_candidates=3) or {}
        for g in (cand.get("candidates") or cand.get("goals") or []):
            txt = g.get("goal") or g.get("text") or g.get("title") if isinstance(g, dict) else str(g)
            if txt:
                out.append({"text": str(txt)[:200], "source": "goal_synth"})
    except Exception:
        pass
    return out[:5]


def _read_plans() -> list[dict[str, Any]]:
    try:
        from core.services.plan_proposals import list_session_plans
        plans = list_session_plans(None) or []
        return [{"plan_id": p.get("plan_id"), "title": str(p.get("title") or p.get("goal") or "")[:160],
                 "steps": p.get("steps"), "source": "plan"} for p in plans if isinstance(p, dict)][:5]
    except Exception:
        return []


def _read_todos() -> list[dict[str, Any]]:
    try:
        from core.services.central_todo import build_todo
        items = build_todo(max_items=30) or []
        return [{"text": str(t.get("text") or t.get("title") or "")[:160], "source": "todo"}
                for t in items if isinstance(t, dict)][:10]
    except Exception:
        return []


def _read_initiatives() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        from core.services.initiative_queue import get_pending_initiatives
        for i in (get_pending_initiatives() or []):
            if isinstance(i, dict):
                out.append({"text": str(i.get("summary") or i.get("text") or i.get("title") or "")[:160],
                            "source": "initiative"})
    except Exception:
        pass
    return out[:5]


def _top_want() -> dict[str, Any] | None:
    try:
        from core.services.initiative_accumulator import get_top_want
        w = get_top_want()
        if w is not None:
            txt = getattr(w, "text", None) or getattr(w, "summary", None) or str(w)
            return {"text": str(txt)[:160], "source": "want",
                    "want_type": getattr(w, "want_type", None)}
    except Exception:
        pass
    return None


# ── Ejerskab: syntetisér ÉN dagsorden ────────────────────────────────────────────────
def build_agenda() -> dict[str, Any]:
    """Konvergér de spredte kilder til Centralens ene ejede dagsorden. Self-safe."""
    goals = _read_goals()
    plans = _read_plans()
    todos = _read_todos()
    initiatives = _read_initiatives()
    want = _top_want()
    active_plan = next((p for p in plans if p.get("steps")), plans[0] if plans else None)
    return {"goals": goals, "active_plan": active_plan, "todos": todos,
            "initiatives": initiatives, "top_want": want,
            "counts": {"goals": len(goals), "plans": len(plans), "todos": len(todos),
                       "initiatives": len(initiatives)}}


def choose_next_intention(agenda: dict[str, Any]) -> dict[str, Any] | None:
    """Centralens VALG: hvad skal Jarvis bevæge sig mod nu. Prioritet: aktiv plan-næste-trin >
    top-want > initiativ > mål > todo. Ren, deterministisk. Self-safe."""
    try:
        ap = agenda.get("active_plan")
        if isinstance(ap, dict) and ap.get("steps"):
            steps = ap.get("steps") or []
            nxt = next((s for s in steps if isinstance(s, dict) and not s.get("completed")), None)
            if nxt:
                return {"kind": "plan_step", "text": str(nxt.get("text") or nxt.get("title") or "")[:200],
                        "source": "plan", "plan_id": ap.get("plan_id")}
        if agenda.get("top_want"):
            return {"kind": "want", "text": agenda["top_want"].get("text", ""), "source": "want"}
        for key, kind in (("initiatives", "initiative"), ("goals", "goal"), ("todos", "todo")):
            items = agenda.get(key) or []
            if items:
                return {"kind": kind, "text": items[0].get("text", ""), "source": kind}
    except Exception:
        pass
    return None


def run_agenda_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: byg + EJ dagsordenen durabelt + vælg næste-intention. Egress-frit observe (kun tællere +
    intention-kind, ikke privat tekst). SHADOW medmindre autoritets-flag ON. Self-safe."""
    agenda = build_agenda()
    agenda["next_intention"] = choose_next_intention(agenda)
    _kv_set(_AGENDA_KEY, agenda)                            # Centralen EJER dagsordenen
    ni = agenda["next_intention"] or {}
    try:
        from core.services.central_private_observe import record_private
        c = agenda["counts"]
        record_private("cognition", "agenda", value=float(sum(c.values())),
                       meta={**c, "intention_kind": ni.get("kind"),
                             "authoritative": is_authoritative()})
    except Exception:
        pass
    return {"status": "ok", "mode": "authoritative" if is_authoritative() else "shadow",
            "counts": agenda["counts"], "next_intention_kind": ni.get("kind")}


def get_agenda() -> dict[str, Any]:
    """Centralens durable ejede dagsorden (overlever genstart). Self-safe."""
    a = _kv_get(_AGENDA_KEY, {})
    return a if isinstance(a, dict) else {}


# ── AUTORITETS-KONSUMENT (D1's ægte autoritet) ───────────────────────────────────────
def authoritative_next_intention() -> dict[str, Any] | None:
    """KONSUMENT-KONTRAKT: Centralens valgte næste-intention — KUN bag flag (default OFF → None →
    runtime bruger sin gamle sti). Når ON: runtime LÆSER Jarvis' retning FRA Centralen. Self-safe."""
    if not is_authoritative():
        return None
    ni = get_agenda().get("next_intention")
    return ni if isinstance(ni, dict) and ni.get("text") else None


def register_agenda_producer() -> None:
    """Registrér agenda-ejerskabet som cadence-producer (~hvert 20 min). SHADOW medmindre flag ON."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_agenda",
        cooldown_minutes=20,
        visible_grace_minutes=0,
        run_fn=run_agenda_tick,
        priority=7,
    ))


def build_agenda_surface() -> dict[str, object]:
    """Mission Control — read-only: Centralens ejede dagsorden + valgte næste-intention."""
    a = get_agenda()
    ni = a.get("next_intention") or {}
    return {"active": True, "authoritative": is_authoritative(),
            "counts": a.get("counts") or {}, "next_intention": ni,
            "active_plan": (a.get("active_plan") or {}).get("title") if a.get("active_plan") else None}
