"""Efemer staging af decision-signals til model-kontekst (2026-07-04 runaway-fix).

Baggrund (sort på hvidt i et run 4. jul, 129s, kimi-lane): fyrede decision-signals
blev `append`et til den synlige svar-buffer (`_a_parts`) i visible_runs. Det:
  (a) persisterede nag'en i det synlige svar (20.291 tegn støj), OG
  (b) forgiftede resolution-exit-tjekket der læste SAMME buffer.
`backend_unresolved_3_calls` har `cooldown_seconds=0` og fyrer hver agentiske runde
mens en backend-streak er uløst. Exit-betingelsen ("stop når der er resolution-tekst")
tjekkes mod `recent_assistant_text = "".join(_a_parts)[-2000:]` — den buffer nag'en
selv fylder. Så snart markørerne fyldte de sidste 2000 tegn, kunne triggeren ALDRIG
se en resolution → uendelig selv-forstærkende injektion. Modellen (der fik samme
buffer som sin forrige tur) degenererede og ekkoede hele sit input med token-drift.

Fix: decision-signalet holdes i en efemer dedup-dict (max N distinkte, erstat pr.
decision-id, aldrig akkumulér) og injiceres KUN i exchange-teksten til modellen —
aldrig i `_a_parts`. Dermed forbliver både det persisterede svar og resolution-tjekket
rene. Disse funktioner er rene + testbare; visible_runs bruger dem.
"""
from __future__ import annotations


def compose_signal_note(decision_id: str, trigger_name: str, context_summary: str) -> str:
    """Den efemere note modellen ser næste runde (omgivet af blanke linjer)."""
    return (
        f"\n\n[decision-signal: {decision_id} "
        f"({trigger_name}: {context_summary})]\n\n"
    )


def stage_signal(
    active: dict[str, str], decision_id: str, note: str, *, cap: int = 3
) -> None:
    """Dedup pr. decision-id (erstat, akkumulér ALDRIG) + cap antal distinkte
    decisions. Muterer `active` in-place. Self-safe.

    Dette er runaway-bæltet: uanset hvor mange gange samme decision fyrer, findes
    der højst ÉN note for den — så en cooldown-0-trigger ikke kan bloate konteksten.
    """
    active[str(decision_id)] = note
    if len(active) > cap:
        # behold de `cap` senest indsatte distinkte decisions
        for _k in list(active.keys())[:-cap]:
            active.pop(_k, None)


def compose_exchange_text(base_parts: list[str], active: dict[str, str]) -> str:
    """Assistant-turen til næste rundes model-input = det ægte svar (`base_parts`)
    + evt. efemere decision-noter. `base_parts` selv røres ALDRIG — persist +
    resolution-exit-tjek læser den rå og ren.
    """
    base = "".join(base_parts) if base_parts else ""
    if not active:
        return base
    notes = "".join(active.values())
    return (base + notes) if base else notes.strip()
