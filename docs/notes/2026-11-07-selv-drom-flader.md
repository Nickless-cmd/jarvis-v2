# Selv- og drøm-flader (7/11-2026)

Aggregator: `core/services/self_dream_state_surface.py`, rute `GET /central/self-state` (owner-only, read-only, `asyncio.to_thread`).

## Måling

Alle 30 kandidater blev kaldt med `PYTHONPATH=. python` før de kom i listen. Resultat: **30/30** uden påkrævede argumenter, dict-svar, nul fejl, nul tomme. `active` er sat i 25 af 34 registrerede (se nedenfor); `self_mutation_lineage`, `dream_influence_runtime`, `dream_insight_daemon`, `dream_motif_daemon`, `central_dream_action`, `self_model_history` og `self_repair_engine` svarer med indhold men har ingen `active`-nøgle — det er ikke en fejl, derfor skelner aggregatoren `svarer` fra `active`.

Feltantal pr. flade (kandidatlisten): self_compassion 2, self_critique 5, self_deception_guard 4, self_experiments 5, self_mutation_lineage 6, self_review_unified 4, self_surprise 6, self_system_code_awareness 22, self_model_blind_spots 4, selfhood_proposals 3 (active=False), self_model_signals 3, self_narrative_continuity 6, self_review_cadence/outcome/record/run/signal 3 hver, self_authored_prompt_proposals 3, dream_articulation 13, dream_carry_over 8, dream_consolidation 5, dream_continuum 7, dream_distillation 8, dream_hypothesis 4 (active=False), dream_influence 14, dream_insight 3, dream_motif 4, dream_action 3.

## Rettelser til listen

Udeladt (allerede synlig, ellers to sandheder):
- `dreaming_session` — i `inner_state_surface`
- `dream_action_executor` — i `infra_state_surface`

Tilføjet (samme præfiks, målt, nul fejl, ikke synlig andre steder): `self_model_history`, `self_repair_engine`, `self_narrative_self_model_review_bridge`, `dream_adoption_candidate_tracking`, `dream_hypothesis_signal_tracking`, `dream_influence_proposal_tracking`.

Fundet i grep men ikke med: `self_model_predictive` er allerede i `inner_state_surface`.

Resultat: 34 producenter, 21 `selv` + 13 `drom`. Ingen blev udeladt på grund af argumenter eller undtagelser.

## Test og mutation

`tests/test_self_dream_state_surface.py` måler koblingen: hver producents funktion kaldes (fake import-modul registrerer kald), en kastende isoleres, tom/ikke-dict tælles tavs, ruten er monteret og kaldbar.

Mutation 1 — fjern `dream_motif` fra `_GROUPS`: 5 af 6 tests fejler. Mutation 2 — lad aggregatoren springe `dream_motif` over: 5 af 6 fejler. Uden mutation: 6/6 grønne.

Mørke flader efter denne: 315 − 34 = 281 (de to udeladte og `self_model_predictive` var allerede talt som synlige).
