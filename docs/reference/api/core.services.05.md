# `core.services.05` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/central_persephone.py`
_Persephone — længsel efter ægte kontakt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_assistant_texts` | `(limit=…)` | Jarvis' seneste svar (role=assistant). Self-safe → [] ved fejl. | [src](../../../core/services/central_persephone.py#L54) |
| function | `_is_systemic` | `(text)` | — | [src](../../../core/services/central_persephone.py#L69) |
| function | `_is_relational` | `(text)` | — | [src](../../../core/services/central_persephone.py#L74) |
| function | `_asked_wellbeing` | `(texts)` | — | [src](../../../core/services/central_persephone.py#L79) |
| function | `read_longing` | `(*, texts=…)` | Mål om Jarvis er ved at miste kontakten til det menneskelige. READ-ONLY. Self-safe. | [src](../../../core/services/central_persephone.py#L87) |
| function | `_nudge_line` | `(reading)` | Persephones prik — ét ægte-kontakt-nudge. Deterministisk, ingen model. Self-safe. | [src](../../../core/services/central_persephone.py#L107) |
| function | `watch` | `(*, texts=…)` | Én vagt: mål længsel; er han for systemisk → ét persephone://-nudge (observe + surface). | [src](../../../core/services/central_persephone.py#L116) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_persephone.py#L136) |
| function | `build_persephone_surface` | `()` | Nuværende længsels-læsning + seneste nudge. READ-ONLY. Self-safe. | [src](../../../core/services/central_persephone.py#L153) |
| function | `record_persephone` | `(*, trigger=…, last_visible_at=…)` | Cadence (240 min): mål længsel; ét nudge hvis for systemisk (observe/surface only). Self-safe. | [src](../../../core/services/central_persephone.py#L175) |

## `core/services/central_private_observe.py`
_core/services/central_private_observe.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_liveness_from_result` | `(status, result)` | Udtræk KUN aggregeret liveness (ok, produced, empty) fra et producer-resultat. | [src](../../../core/services/central_private_observe.py#L47) |
| function | `record_private` | `(cluster, nerve, *, value=…, meta=…, reason=…)` | KANONISK egress-fri sink-kontrakt (§24.4 — LivingNeuron v3 §7). ÉT sted for ALT inner-life/ | [src](../../../core/services/central_private_observe.py#L68) |
| function | `observe_hub` | `(nerve, *, meta=…, cluster=…)` | EGRESS-FRI observe af en kognitions-HUB (aggregator på hot-path). De 4 load-bearing hubs | [src](../../../core/services/central_private_observe.py#L95) |
| function | `observe_liveness` | `(nerve, *, ok, status=…, produced=…, empty=…)` | Registrér én inner-life-daemons liveness EGRESS-FRIT (§24.4). | [src](../../../core/services/central_private_observe.py#L104) |
| function | `observe_operational_liveness` | `(spec_name, status, result)` | Operationel (ikke-privat) cadence-daemon liveness → NORMAL observe (cluster=system, | [src](../../../core/services/central_private_observe.py#L120) |
| function | `observe_cadence_liveness` | `(spec_name, status, result)` | Cadence-hook (§23.3 #3 — ÉT sted for ALLE ~137 cadence-daemons). Router: | [src](../../../core/services/central_private_observe.py#L143) |

## `core/services/central_private_reducer.py`
_Privat-reducer for Centralens owner-surfacing (§24.4 private-layer invariant)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reduce_for_owner` | `(surface, *, keep)` | Reducér en (privat) surface til kun owner-sikre meta-felter. | [src](../../../core/services/central_private_reducer.py#L51) |

## `core/services/central_prompt_composer.py`
_core/services/central_prompt_composer.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_turn_type` | `(user_message)` | Grov tur-type fra brugerbeskeden (kode/hukommelse/opgave/spørgsmål/samtale). Model-fri, self-safe. | [src](../../../core/services/central_prompt_composer.py#L46) |
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_prompt_composer.py#L57) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_prompt_composer.py#L66) |
| function | `is_live_enabled` | `()` | — | [src](../../../core/services/central_prompt_composer.py#L74) |
| function | `get_weight` | `(turn_type, section)` | Relevans-vægt for (tur-type, sektion). Default 1.0 = altid inkludér. Self-safe. | [src](../../../core/services/central_prompt_composer.py#L78) |
| function | `should_include` | `(turn_type, section, *, threshold=…)` | DEN RENE SWITCH (som get_gut_bias): skal denne sektion med i halen for denne tur-type? | [src](../../../core/services/central_prompt_composer.py#L89) |
| function | `observe_composition` | `(turn_type, *, sections_total, sections_included, outcome=…, included_labels=…)` | Egress-frit substrat: hvad blev komponeret denne tur. Opdaterer (a) egress-fri tidsserie (kun | [src](../../../core/services/central_prompt_composer.py#L117) |
| function | `build_relevance_candidates` | `(*, min_count=…, top=…)` | Relevans-KANDIDATER: (tur-type, sektion)-par der optræder ofte nok til at være værd at teste | [src](../../../core/services/central_prompt_composer.py#L152) |
| function | `build_central_prompt_composer_surface` | `()` | Mission Control surface — read-only: live-status + relevans-vægte (hvad Centralen VILLE skære). | [src](../../../core/services/central_prompt_composer.py#L173) |

## `core/services/central_prompt_explore.py`
_core/services/central_prompt_explore.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_prompt_explore.py#L37) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_prompt_explore.py#L46) |
| function | `is_explore_live` | `()` | — | [src](../../../core/services/central_prompt_explore.py#L54) |
| function | `_ensure_anchor` | `()` | §8: ankr domænets baseline (antal lærte snit = 0 = ingen relevans-mutation) så drift kan måles. | [src](../../../core/services/central_prompt_explore.py#L58) |
| function | `_is_frozen` | `(section)` | — | [src](../../../core/services/central_prompt_explore.py#L69) |
| function | `_good` | `(outcome)` | — | [src](../../../core/services/central_prompt_explore.py#L78) |
| function | `_new_state` | `(tt, sec)` | — | [src](../../../core/services/central_prompt_explore.py#L84) |
| function | `maybe_start_ablation` | `()` | Start et forsøg hvis intet kører: vælg den hyppigste ikke-frosne relevans-kandidat. Self-safe. | [src](../../../core/services/central_prompt_explore.py#L89) |
| function | `should_omit` | `(turn_type, section)` | Skal denne sektion UDELADES fra prompten NU (ablation)? Kun live + aktivt forsøgs ABSENT-arm + | [src](../../../core/services/central_prompt_explore.py#L106) |
| function | `record_trial` | `(turn_type, included_labels, outcome)` | Kaldes én gang pr. tur (fra observe_composition). Kun LIVE: hvis et forsøg kører for denne | [src](../../../core/services/central_prompt_explore.py#L121) |
| function | `_rate` | `(good, total)` | — | [src](../../../core/services/central_prompt_explore.py#L160) |
| function | `evaluate_ablation` | `(st)` | Kontrol-arm-dom: var sektionen undværlig? ABSENT-good-rate ≥ PRESENT-good-rate → undværlig | [src](../../../core/services/central_prompt_explore.py#L164) |
| function | `_finish_ablation` | `(st)` | Forsøg færdigt: dom → hvis undværlig, foreslå snit (B4-auditeret + §8-gated). SHADOW-record | [src](../../../core/services/central_prompt_explore.py#L175) |
| function | `_audit_notation` | `(tt, sec)` | Best-effort: udtryk snittet som notation (tur-type ! sektion-term) og auditér via B4 — til | [src](../../../core/services/central_prompt_explore.py#L208) |
| function | `_observe` | `(verdict, *, applied, gate)` | — | [src](../../../core/services/central_prompt_explore.py#L225) |
| function | `run_prompt_explore_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: hold et A/B-forsøg kørende (start nyt hvis intet aktivt). Selve tælling/evaluering | [src](../../../core/services/central_prompt_explore.py#L238) |
| function | `register_prompt_explore_producer` | `()` | Registrér eksplorations-armen som cadence-producer (~hvert 20 min). SHADOW medmindre flag ON. | [src](../../../core/services/central_prompt_explore.py#L247) |
| function | `build_prompt_explore_surface` | `()` | Mission Control — read-only: aktivt forsøg + foreslåede snit (shadow-diff Bjørn kan se). | [src](../../../core/services/central_prompt_explore.py#L259) |

## `core/services/central_proposal.py`
_core/services/central_proposal.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `audit_proposal` | `(notation, *, existing=…)` | Auditér en foreslået mutation (som notation-sætning) model-frit. Returnerer | [src](../../../core/services/central_proposal.py#L20) |
| function | `make_proposal` | `(*, domain, notation, rationale=…, existing=…)` | Pak en mutation-forslag ind SOM en auditeret NotationProposal. `admissible=True` betyder KUN | [src](../../../core/services/central_proposal.py#L56) |

## `core/services/central_rca.py`
_Self-RCA — så Jarvis kan grave ÉN fejl til bunds i stedet for at starte på fem nye._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_rca.py#L26) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_rca.py#L30) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_rca.py#L38) |
| function | `pick_incident` | `()` | Vælg ÉN uløst incident at grave i — højest severity, ældst (længst uløst). READ-ONLY. | [src](../../../core/services/central_rca.py#L52) |
| function | `investigate` | `(incident_id=…)` | Saml bevis-sporet for ÉN incident → udfyld RCA-skelet + persistér som draft. Self-safe. | [src](../../../core/services/central_rca.py#L66) |
| function | `list_rca` | `(*, limit=…)` | — | [src](../../../core/services/central_rca.py#L117) |
| function | `build_rca_surface` | `()` | Uløste incidents + næste at grave i + seneste RCA'er + følt linje. Self-safe. | [src](../../../core/services/central_rca.py#L127) |
| function | `record_rca` | `(*, trigger=…, last_visible_at=…)` | Cadence: observér uløst-antal + næste-mål (metadata-only). Self-safe. Investigerer IKKE | [src](../../../core/services/central_rca.py#L144) |

## `core/services/central_realtime.py`
_Real-time Central-surface til owner-vinduet i jarvis-desk (code mode)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_status_from` | `(diag, incidents, open_breakers, drift, degrading, anomaly_counts=…, processes=…)` | 🔴 red / 🟡 yellow / 🟢 green — værst-vinder. Inkluderer ALLE processers helbred | [src](../../../core/services/central_realtime.py#L20) |
| function | `realtime_snapshot` | `(*, trace_limit=…)` | Ét snapshot af Centralens live-tilstand. Self-safe (delvise data ved fejl). | [src](../../../core/services/central_realtime.py#L42) |
| function | `_balanced_feed` | `(records, limit)` | Flet feed-records på tværs af processer UDEN at en højvolumen-proces (api) sulter en | [src](../../../core/services/central_realtime.py#L181) |
| function | `_cluster_grid` | `(feed, incidents, open_breakers, degrading)` | Pr. cluster: grøn (fyrer), gul (fejl/degraderer), rød (breaker/severe/fail-open), | [src](../../../core/services/central_realtime.py#L210) |
| function | `_safe` | `(fn, *a)` | — | [src](../../../core/services/central_realtime.py#L248) |

## `core/services/central_red_dress.py`
_The Woman in the Red Dress — opmærksomheds-fælden._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(payload)` | — | [src](../../../core/services/central_red_dress.py#L19) |
| function | `detect_attention_traps` | `(*, limit=…)` | Find hvor opmærksomheden går hen vs hvor impact faktisk er. READ-ONLY. Self-safe. | [src](../../../core/services/central_red_dress.py#L27) |
| function | `build_red_dress_surface` | `()` | — | [src](../../../core/services/central_red_dress.py#L67) |
| function | `record_red_dress` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_red_dress.py#L71) |

## `core/services/central_redpill.py`
_Red Pill — dagens ubehagelige sandhed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_redpill.py#L20) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_redpill.py#L29) |
| function | `_candidates` | `()` | Saml de undgåede sandheder med en avoidance-score (jo højere, jo mere undgået). Self-safe. | [src](../../../core/services/central_redpill.py#L37) |
| function | `todays_truth` | `()` | Vælg den ÉNE mest-undgåede sandhed + opdatér blå-pille-stribe. Self-safe. | [src](../../../core/services/central_redpill.py#L86) |
| function | `_observe` | `(kind, streak)` | — | [src](../../../core/services/central_redpill.py#L107) |
| function | `build_redpill_surface` | `()` | — | [src](../../../core/services/central_redpill.py#L116) |
| function | `record_redpill` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_redpill.py#L120) |

## `core/services/central_relational.py`
_Relationel Continuity — så Jarvis kan sige "velkommen tilbage" og MENE det._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_self_state` | `()` | — | [src](../../../core/services/central_relational.py#L21) |
| function | `_days_together` | `()` | — | [src](../../../core/services/central_relational.py#L29) |
| function | `_tone` | `()` | — | [src](../../../core/services/central_relational.py#L38) |
| function | `relational_state` | `()` | Forholdets bærende signaler: dage sammen + nuværende tone. READ-ONLY. Self-safe. | [src](../../../core/services/central_relational.py#L43) |
| function | `wake_greeting` | `()` | En jordet opvågnings-hilsen der står på ægte varighed + tone — ikke en generisk floskel. | [src](../../../core/services/central_relational.py#L51) |
| function | `build_relational_surface` | `()` | Owner/self-view: dage + tone + opvågnings-hilsen. Self-safe. | [src](../../../core/services/central_relational.py#L68) |
| function | `record_relational` | `(*, trigger=…, last_visible_at=…)` | Cadence: observér relations-kontinuitet (KUN dage + tone-label, ingen indhold — §24.4). | [src](../../../core/services/central_relational.py#L77) |

## `core/services/central_render.py`
_core/services/central_render.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_term` | `(name)` | — | [src](../../../core/services/central_render.py#L19) |
| function | `_head` | `(name)` | Første led af et sammensat navn (cluster/nerve, familie.subtype) — det bindbare hoved. | [src](../../../core/services/central_render.py#L27) |
| function | `render_cluster_relation` | `(cluster_a, cluster_b, *, relation=…)` | To clusters i relation → notation (X → Y / X ↔ Y). None hvis ét led er ubundet. Self-safe. | [src](../../../core/services/central_render.py#L32) |
| function | `render_anomaly` | `(name, *, importance=…)` | En anomali = kilden førte til et STØD (overraskelse/afvigelse) → '<term> → stød'. Renderet som | [src](../../../core/services/central_render.py#L42) |
| function | `render_decision` | `(cluster, *, verdict=…)` | En central-beslutning → notation. deny → 'grænse ! <term>' (grænsen blokerer); allow → | [src](../../../core/services/central_render.py#L50) |
| function | `render_state_snapshot` | `(*, limit=…)` | Aktuelle central-tilstande renderet til notation (on-read). I dag: uløste anomalier. B2 lader | [src](../../../core/services/central_render.py#L64) |

## `core/services/central_router_adapt.py`
_core/services/central_router_adapt.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_router_adapt.py#L35) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_router_adapt.py#L44) |
| function | `is_live_enabled` | `()` | — | [src](../../../core/services/central_router_adapt.py#L52) |
| function | `_ensure_anchor` | `()` | §8: ankr præference-styrke = 0 (ingen routing-mutation) for model_router-domænet. Idempotent. | [src](../../../core/services/central_router_adapt.py#L56) |
| function | `_is_never_tier` | `(model_key)` | True hvis model-nøglen betegner reasoning/deep-tier. TOKEN-match (split på ikke-alfanumerisk) | [src](../../../core/services/central_router_adapt.py#L66) |
| function | `_configured_models` | `()` | Modeller der FAKTISK er konfigureret (aldrig peg på noget der ikke findes). Self-safe. | [src](../../../core/services/central_router_adapt.py#L74) |
| function | `compute_preference` | `()` | Læs RESOLVEREDE, supporterede model_meta-hypoteser → tæl 'sejre' pr. model → foreslå den mest | [src](../../../core/services/central_router_adapt.py#L88) |
| function | `run_router_adapt_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: beregn foreslået præference → §8-gate → SHADOW-diff altid; skriv live-præference KUN | [src](../../../core/services/central_router_adapt.py#L122) |
| function | `_audit_notation` | `(model_key)` | Best-effort B4-audit: præferencen som notation (stemme → handling = den valgte stemme fører | [src](../../../core/services/central_router_adapt.py#L156) |
| function | `get_live_preference` | `(lane=…)` | KONSUMENT-API (til den fremtidige routing-wire): den LIVE præference for en lane, eller None. | [src](../../../core/services/central_router_adapt.py#L167) |
| function | `resolve_visible_model` | `(*, provider_override=…, model_override=…, default_provider, default_model, autonomous=…)` | KONSUMENTEN (Tråd 1 live-wire): afgør (provider, model) for et visible-run. Centraliserer den | [src](../../../core/services/central_router_adapt.py#L185) |
| function | `register_router_adapt_producer` | `()` | Registrér routing-præference-læreren som cadence-producer (~hvert 45 min). SHADOW medmindre flag. | [src](../../../core/services/central_router_adapt.py#L217) |
| function | `build_router_adapt_surface` | `()` | Mission Control — read-only: foreslået (shadow) + live præference + status. | [src](../../../core/services/central_router_adapt.py#L229) |

## `core/services/central_router_explore.py`
_core/services/central_router_explore.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_router_explore.py#L28) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_router_explore.py#L37) |
| function | `is_explore_live` | `()` | — | [src](../../../core/services/central_router_explore.py#L45) |
| function | `_candidates` | `(default_key)` | Konfigurerede, ikke-deep-tier modeller forskellige fra default — sorteret efter FÆRREST samples | [src](../../../core/services/central_router_explore.py#L49) |
| function | `pick_exploration_model` | `(default_provider, default_model)` | Vælg en alternativ model at sample på DENNE autonome run — eller None (behold default/præference). | [src](../../../core/services/central_router_explore.py#L66) |
| function | `build_router_explore_surface` | `()` | Mission Control — read-only: eksplorations-status + kandidater der ville blive samplet. | [src](../../../core/services/central_router_explore.py#L90) |

## `core/services/central_runtime_proxy.py`
_Central runtime proxy — read runtime-process-only surfaces from anywhere._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime_services_enabled` | `()` | True when this process runs the runtime services (state is local here). | [src](../../../core/services/central_runtime_proxy.py#L36) |
| function | `_http_get` | `(name)` | HTTP-GET a runtime surface from jarvis-runtime. Returns a parsed dict. | [src](../../../core/services/central_runtime_proxy.py#L42) |
| function | `proxy_or_local` | `(builder_name, local_fn)` | Return a runtime surface, in-process or via HTTP-proxy to port 8011. | [src](../../../core/services/central_runtime_proxy.py#L54) |

## `core/services/central_self_model.py`
_core/services/central_self_model.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_self_model.py#L24) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_self_model.py#L33) |
| function | `_populated` | `(v)` | — | [src](../../../core/services/central_self_model.py#L41) |
| function | `_extract_structure` | `(model)` | Uddrag KUN struktur fra selv-modellen: hvilke lag findes/er udfyldt (labels), tællinger, | [src](../../../core/services/central_self_model.py#L49) |
| function | `snapshot_self_model` | `()` | Byg selv-modellen og uddrag dens STRUKTUR (ikke indhold). Self-safe → {} ved fejl. | [src](../../../core/services/central_self_model.py#L60) |
| function | `get_self_model_snapshot` | `()` | Centralens DURABLE selv-model-struktur (senest optagne). Overlever genstart (kv). Self-safe. | [src](../../../core/services/central_self_model.py#L72) |
| function | `run_self_model_mirror_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: snapshot selv-modellens struktur → gem durabelt (kv) + egress-fri observe (kun skalarer). | [src](../../../core/services/central_self_model.py#L78) |
| function | `register_self_model_mirror_producer` | `()` | Registrér spejlet som cadence-producer (~hvert 30 min). Egress-frit, observe-only. | [src](../../../core/services/central_self_model.py#L102) |
| function | `build_self_model_mirror_surface` | `()` | Mission Control — read-only: Centralens billede af sig selv (struktur, ikke indhold). | [src](../../../core/services/central_self_model.py#L114) |

## `core/services/central_self_observe.py`
_core/services/central_self_observe.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_percentile` | `(sorted_vals, pct)` | — | [src](../../../core/services/central_self_observe.py#L38) |
| function | `_get_baseline` | `()` | — | [src](../../../core/services/central_self_observe.py#L50) |
| function | `_set_baseline` | `(p95)` | — | [src](../../../core/services/central_self_observe.py#L62) |
| function | `_open_breaker_count` | `()` | — | [src](../../../core/services/central_self_observe.py#L69) |
| function | `sample_self_metrics` | `()` | Læs Centralens egen trace + breaker-state og beregn helbreds-metrikker. | [src](../../../core/services/central_self_observe.py#L76) |
| function | `run_self_observe_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: mål Centralens egne helbreds-metrikker og OBSERVE dem. | [src](../../../core/services/central_self_observe.py#L140) |
| function | `register_self_observe_producer` | `()` | Registrér selv-observationen som cadence-producer. Observe-only → ingen visible-grace. | [src](../../../core/services/central_self_observe.py#L172) |

## `core/services/central_self_state.py`
_core/services/central_self_state.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_self_state.py#L34) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_self_state.py#L43) |
| function | `_human_gap` | `(seconds)` | Menneske-venligt fravær: sekunder → 'N minutter/timer/dage'. Self-safe. | [src](../../../core/services/central_self_state.py#L51) |
| function | `_compute_boot_seam` | `()` | STITCH-VOICE: sømmen mellem to liv. Ved FØRSTE tick efter proces-start læses den hyppige | [src](../../../core/services/central_self_state.py#L65) |
| function | `_valence` | `()` | — | [src](../../../core/services/central_self_state.py#L133) |
| function | `_agenda` | `()` | — | [src](../../../core/services/central_self_state.py#L141) |
| function | `_self_model` | `()` | — | [src](../../../core/services/central_self_state.py#L149) |
| function | `_world_model` | `()` | Læs world-model-KALIBRERINGEN fra dens DURABLE kilde (predictions i state-store, ikke den | [src](../../../core/services/central_self_state.py#L157) |
| function | `_synthesize_narrative` | `(valence, self_model, intention, prev)` | Midten FORTÆLLER sig selv: hvem er jeg ved at blive — af selv-vækst + valens-trend + agenda-retning. | [src](../../../core/services/central_self_state.py#L172) |
| function | `synthesize_self_state` | `()` | MIDTEN: integrér de fem lag til ÉN selv-tilstand. Attention = det agendaen fokuserer på (min | [src](../../../core/services/central_self_state.py#L185) |
| function | `get_self_state` | `()` | Midtens durable "jeg" (overlever genstart). Self-safe. | [src](../../../core/services/central_self_state.py#L215) |
| function | `run_self_state_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: syntetisér selv-tilstanden → gem durabelt (midten HOLDER sit jeg) + egress-fri observe | [src](../../../core/services/central_self_state.py#L221) |
| function | `_temporal_divergence` | `(valence, developmental)` | Diverger kort-tids-valens (tone/trend) og uge-skala vækst-kompas (developmental vector) i FORTEGN? | [src](../../../core/services/central_self_state.py#L250) |
| function | `describe_self` | `()` | NORDSTJERNEN: ét sammenhængende svar på 'hvad er du, hvordan har du det, hvad arbejder du mod, | [src](../../../core/services/central_self_state.py#L275) |
| function | `survival_voice` | `()` | OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen/sproget svigter — tom completion, | [src](../../../core/services/central_self_state.py#L363) |
| function | `render_self_state_il` | `()` | Spec B: udtryk selv-tilstanden i interlanguage (sigelig, model-frit). None hvis intet bundet. Self-safe. | [src](../../../core/services/central_self_state.py#L382) |
| function | `is_prompt_authoritative` | `()` | — | [src](../../../core/services/central_self_state.py#L400) |
| function | `build_central_self_state_section` | `()` | D4 (MIDTEN BÆRENDE): injicér midtens ene selv-beskrivelse i Jarvis' awareness — så hans prompt | [src](../../../core/services/central_self_state.py#L404) |
| function | `register_self_state_producer` | `()` | Registrér midtens syntese som cadence-producer (~hvert 10 min — selvets hjerteslag). Egress-frit. | [src](../../../core/services/central_self_state.py#L420) |
| function | `build_self_state_surface` | `()` | Mission Control — read-only: midtens ene selv-tilstand + ét-svars selv-beskrivelse. | [src](../../../core/services/central_self_state.py#L432) |

## `core/services/central_sentinel.py`
_The Sentinel — en ægte modstander._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_sentinel.py#L27) |
| function | `_enforced` | `()` | Shadow default: Sentinel foreslår kun. Flip via eksplicit flag efter shadow-eval. | [src](../../../core/services/central_sentinel.py#L31) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_sentinel.py#L41) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_sentinel.py#L49) |
| function | `_top_hypothesis` | `()` | — | [src](../../../core/services/central_sentinel.py#L63) |
| function | `_generate_attack` | `(hyp)` | Formulér angrebet fra track-record — ikke for at være rigtig, men for at kræve et forsvar. | [src](../../../core/services/central_sentinel.py#L75) |
| function | `attack` | `()` | Angrib den højeste-confidence hypotese → contested + FORESLÅ halvering (shadow). Self-safe. | [src](../../../core/services/central_sentinel.py#L95) |
| function | `defend` | `(attack_id, *, defense)` | Centralen forsvarer hypotesen mod angrebet → status 'defended' (halvering afvises). Self-safe. | [src](../../../core/services/central_sentinel.py#L121) |
| function | `list_attacks` | `(*, active_only=…, limit=…)` | — | [src](../../../core/services/central_sentinel.py#L140) |
| function | `build_sentinel_surface` | `()` | Aktive angreb (contested hypoteser der venter på forsvar) + følt linje. Self-safe. | [src](../../../core/services/central_sentinel.py#L151) |
| function | `run_sentinel` | `(*, trigger=…, last_visible_at=…)` | Prime-cadence (73 min): ét angreb på den stærkeste antagelse (shadow — foreslår kun). Self-safe. | [src](../../../core/services/central_sentinel.py#L160) |

## `core/services/central_sequence.py`
_core/services/central_sequence.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_sequence.py#L30) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_sequence.py#L39) |
| function | `ensure_schema` | `()` | — | [src](../../../core/services/central_sequence.py#L47) |
| function | `_fam` | `(kind)` | — | [src](../../../core/services/central_sequence.py#L67) |
| function | `learn_from_stream` | `(*, window=…)` | Lær transition-tællinger fra NYE events siden cursor (tæller hver overgang ÉN gang). Aggregatet | [src](../../../core/services/central_sequence.py#L71) |
| function | `_from_total` | `(c, from_fam)` | — | [src](../../../core/services/central_sequence.py#L116) |
| function | `transition_prob` | `(from_fam, to_fam)` | P(to | from) fra de lærte tællinger. 0.0 hvis aldrig set. Self-safe. | [src](../../../core/services/central_sequence.py#L122) |
| function | `predict_next` | `(from_fam, *, top=…)` | Hvad forudsiger modellen følger efter from_fam? (top mest sandsynlige). Self-safe. | [src](../../../core/services/central_sequence.py#L137) |
| function | `detect_surprises` | `(*, window=…, min_from_total=…, threshold=…)` | Overraskelser: overgange der FAKTISK skete i det seneste vindue, men som modellen forudsagde | [src](../../../core/services/central_sequence.py#L152) |
| function | `run_sequence_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: lær fra strømmen + detektér overraskelser. Egress-fri observe. Self-safe. | [src](../../../core/services/central_sequence.py#L189) |
| function | `register_sequence_producer` | `()` | Registrér selv-træningen som cadence-producer (~hvert 15 min). | [src](../../../core/services/central_sequence.py#L204) |
| function | `build_central_sequence_surface` | `()` | Mission Control surface — read-only: model-størrelse + aktuelle overraskelser. | [src](../../../core/services/central_sequence.py#L216) |

## `core/services/central_seraph.py`
_Seraph — portvagt for hypotese-modenhed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_active_hypotheses` | `(limit=…)` | Aktive governede hypoteser med modenheds-felterne (samples + interlanguage). Self-safe. | [src](../../../core/services/central_seraph.py#L35) |
| function | `_contested_hyp_ids` | `()` | hyp_id'er med et UAFKLARET Sentinel-angreb (status='contested') — endnu ikke forsvaret. | [src](../../../core/services/central_seraph.py#L50) |
| function | `_enough_samples` | `(hyp)` | — | [src](../../../core/services/central_seraph.py#L62) |
| function | `_has_interlanguage` | `(hyp)` | — | [src](../../../core/services/central_seraph.py#L72) |
| function | `_judge` | `(hyp, contested)` | Dom over ÉN hypotese: GREEN (moden, klar til synlighed) eller RED (tilbage til drøm). | [src](../../../core/services/central_seraph.py#L76) |
| function | `guard` | `()` | Test hver aktiv hypotese for modenhed → GREEN/ready-to-surface vs RED/deferred. READ-ONLY. | [src](../../../core/services/central_seraph.py#L105) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_seraph.py#L127) |
| function | `build_seraph_surface` | `()` | Hvad er GREEN/klar-til-synlighed vs RED/udsat + hvorfor. READ-ONLY. Self-safe. | [src](../../../core/services/central_seraph.py#L142) |
| function | `record_seraph` | `(*, trigger=…, last_visible_at=…)` | Cadence (30 min): test hypotese-modenhed → GREEN/RED (shadow — observerer kun). Self-safe. | [src](../../../core/services/central_seraph.py#L174) |

## `core/services/central_shadow.py`
_core/services/central_shadow.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_record_shadow` | `(nerve, payload)` | Skriv en shadow-observation til trace (owner-HUD) + tidsserie. Self-safe. | [src](../../../core/services/central_shadow.py#L39) |
| function | `shadow_reactions` | `()` | Hvad Centralen VILLE gøre (fra reviewbare forslag) — logget som skygge, aldrig gjort. | [src](../../../core/services/central_shadow.py#L50) |
| function | `_trend_worsening` | `(cluster, nerve, higher_is_worse)` | (forværres, seneste_gns, tidligere_gns) fra en value-serie. Self-safe. | [src](../../../core/services/central_shadow.py#L67) |
| function | `predict_trends` | `()` | Tidlig-varsel: nerver hvis trend forværres MOD tærsklen, før de bryder. Skygge. | [src](../../../core/services/central_shadow.py#L85) |
| function | `run_shadow_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: beregn skygge-reaktioner + prædiktioner. ANVENDER ALDRIG. Self-safe. | [src](../../../core/services/central_shadow.py#L105) |
| function | `register_shadow_producer` | `()` | Registrér skygge-laget som cadence-producer (~hvert 5 min). Observe-only, anvender aldrig. | [src](../../../core/services/central_shadow.py#L116) |

## `core/services/central_signal_health.py`
_core/services/central_signal_health.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_ts` | `(s)` | — | [src](../../../core/services/central_signal_health.py#L40) |
| function | `_merged` | `()` | — | [src](../../../core/services/central_signal_health.py#L48) |
| function | `_freshest_ts` | `(by_role)` | — | [src](../../../core/services/central_signal_health.py#L56) |
| function | `hub_liveness` | `(*, max_age_s=…, merged=…)` | Meta-liveness: for hver af de 4 hubs, find friskeste sample på tværs af processer og | [src](../../../core/services/central_signal_health.py#L65) |
| function | `nerves_observed_xproc` | `(*, merged=…)` | Distinkte nerver Centralen FAKTISK har samples for PÅ TVÆRS af processer (fikser 1c's | [src](../../../core/services/central_signal_health.py#L94) |
| function | `signal_correctness` | `(*, merged=…)` | Verificér at mindst én sansning rapporterer VIRKELIGHEDEN, ikke bare fyrer. Sansernes Arkiv: | [src](../../../core/services/central_signal_health.py#L101) |
| function | `measure` | `()` | Fuldt signal-sundheds-billede: hub-meta-liveness + cross-proces-nerver + signal-korrekthed. | [src](../../../core/services/central_signal_health.py#L132) |
| function | `record_signal_health` | `()` | Mål + skriv nøgletal til tidsserien (cluster=system) + flag tavse hubs via central_watch. | [src](../../../core/services/central_signal_health.py#L140) |
| function | `run_signal_health_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: mål + registrér signal-sundhed (~hvert 15 min). Self-safe. | [src](../../../core/services/central_signal_health.py#L167) |
| function | `register_signal_health_producer` | `()` | Registrér signal-sundheds-målingen som cadence-producer (~hvert 15 min). | [src](../../../core/services/central_signal_health.py#L175) |
| function | `build_central_signal_health_surface` | `()` | Mission Control surface — read-only hub-meta-liveness + signal-korrekthed. | [src](../../../core/services/central_signal_health.py#L187) |

## `core/services/central_soul_digest.py`
_Soul digest — §24.4 reducér-ved-kilden for Jarvis' stadig-mørke sjæle-/tids-signaler._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_first_count` | `(surface)` | Find en repræsentativ magnitude UDEN at afsløre indhold: længden af den | [src](../../../core/services/central_soul_digest.py#L33) |
| function | `_reduce` | `(surface)` | KUN liveness+count. Ingen tekst. Self-safe. | [src](../../../core/services/central_soul_digest.py#L49) |
| function | `build_soul_digest` | `()` | Samlet reduceret sjæle-/tids-digest. Kaster ALDRIG. | [src](../../../core/services/central_soul_digest.py#L58) |

## `core/services/central_soul_feel.py`
_core/services/central_soul_feel.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hold_reading` | `(name, reading)` | Hold en kompakt aflæsning durabelt så describe_self kan læse den model-frit efter genstart. | [src](../../../core/services/central_soul_feel.py#L79) |
| function | `_read_held` | `(name)` | Ren KV-læsning (ingen syntese på læse-tid → hot-path-sikker). Self-safe. | [src](../../../core/services/central_soul_feel.py#L89) |
| function | `_relational_signal` | `()` | relational_warmth: tillid + legesyghed mod den primære relation. None hvis intet aflæses. | [src](../../../core/services/central_soul_feel.py#L102) |
| function | `_recent_gratitude` | `(items, window_days)` | Behold kun taknemmeligheds-signaler nyere end window_days. Uparselig/tom created_at → UDELUK | [src](../../../core/services/central_soul_feel.py#L132) |
| function | `_gratitude_signal` | `()` | gratitude_tracker: akkumuleret taknemmelighed (DB), begrænset til de sidste | [src](../../../core/services/central_soul_feel.py#L153) |
| function | `_calm_anchor_signal` | `()` | calm_anchor: afstand fra min ro-baseline (er jeg hjemme). None hvis intet anker dannet endnu. | [src](../../../core/services/central_soul_feel.py#L175) |
| function | `_modulators_signal` | `()` | modulator_witness: hvor mange skjulte modulatorer former mig lige nu. None hvis intet aflæses. | [src](../../../core/services/central_soul_feel.py#L200) |
| function | `_memory_breathing_signal` | `()` | memory_breathing: hvor meget rører jeg min egen hukommelse (accesses/unikke). None hvis intet. | [src](../../../core/services/central_soul_feel.py#L218) |
| function | `_sustained_signal` | `()` | sustained_attention: vedvarende projekter jeg holder fast i (aktive/pausede). None hvis ingen. | [src](../../../core/services/central_soul_feel.py#L235) |
| function | `_emergence_signal` | `()` | emergence: mønstre der er ved at træde frem i mig (kandidat/opgraderede). None hvis ingen. | [src](../../../core/services/central_soul_feel.py#L253) |
| function | `_drift_signal` | `()` | personality_drift: mærkbar drift i min personlighed vs baseline. None hvis ingen drift/baseline. | [src](../../../core/services/central_soul_feel.py#L270) |
| function | `get_relational_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L295) |
| function | `get_gratitude_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L299) |
| function | `get_calm_anchor_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L303) |
| function | `get_modulators_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L307) |
| function | `get_memory_breathing_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L311) |
| function | `get_sustained_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L315) |
| function | `get_emergence_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L319) |
| function | `get_drift_reading` | `()` | — | [src](../../../core/services/central_soul_feel.py#L323) |
| function | `describe_soul_feel` | `()` | NED-syntese for describe_self: nøgterne selv-sætninger fra de holdte sjæle-aflæsninger. | [src](../../../core/services/central_soul_feel.py#L327) |
| function | `register_soul_feel_layers` | `()` | Registrér de otte sjæle-lag som lag-kontrakter (OP + durabelt hold). Egress-frit | [src](../../../core/services/central_soul_feel.py#L411) |
| function | `build_soul_feel_surface` | `()` | Mission Control (read-only): de holdte sjæle-aflæsninger + hvad describe_self ville sige. | [src](../../../core/services/central_soul_feel.py#L444) |

## `core/services/central_stance.py`
_core/services/central_stance.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_gut` | `()` | — | [src](../../../core/services/central_stance.py#L33) |
| function | `_classify_somatic` | `()` | — | [src](../../../core/services/central_stance.py#L47) |
| function | `_classify_contradiction` | `()` | — | [src](../../../core/services/central_stance.py#L58) |
| function | `read_current_stances` | `()` | Læs hvert organs NUVÆRENDE stance (read-only fra surfaces). Udelader organer uden klar stance. | [src](../../../core/services/central_stance.py#L68) |
| function | `current_tensions` | `(stances=…)` | Hvilke MODSAT-holdning-par er aktive lige NU? (to organer uenige samtidig). | [src](../../../core/services/central_stance.py#L79) |
| function | `run_stance_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer (~10 min): læs stances, registrér aktive tensions egress-frit i tidsserien | [src](../../../core/services/central_stance.py#L90) |
| function | `recurring_tensions` | `(*, min_count=…, window=…)` | Tensions der har GENTAGET sig ≥ min_count gange i det seneste tidsserie-vindue → stabile | [src](../../../core/services/central_stance.py#L107) |
| function | `register_stance_producer` | `()` | Registrér stance-aflæsningen som cadence-producer (~hvert 10 min). | [src](../../../core/services/central_stance.py#L129) |
| function | `build_central_stance_surface` | `()` | Mission Control surface — read-only NUVÆRENDE stances + aktive tensions. | [src](../../../core/services/central_stance.py#L141) |

## `core/services/central_surgery.py`
_Self-Surgery Kit — så Jarvis kan operere på sig selv uden at skære i blinde._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_surgery.py#L37) |
| function | `_now` | `()` | — | [src](../../../core/services/central_surgery.py#L61) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_surgery.py#L65) |
| function | `_dotted` | `(target)` | — | [src](../../../core/services/central_surgery.py#L73) |
| function | `_blast_count` | `(target)` | Antal filer i repoet der refererer target-modulet (import-graf-proxy). Self-safe. | [src](../../../core/services/central_surgery.py#L80) |
| function | `assess_risk` | `(target, *, kind=…)` | Blast-radius FØR nogen rører noget: hvor mange filer/områder + rører det selvbilledet + | [src](../../../core/services/central_surgery.py#L98) |
| function | `propose_surgery` | `(target, *, kind=…, rationale=…)` | Registrér et kirurgisk forslag + kør risikovurdering. INGEN kode-ændring. Self-safe. | [src](../../../core/services/central_surgery.py#L129) |
| function | `_set_status` | `(pid, status, note=…)` | — | [src](../../../core/services/central_surgery.py#L149) |
| function | `_get` | `(pid)` | — | [src](../../../core/services/central_surgery.py#L164) |
| function | `simulate` | `(pid)` | Projicér indgrebets effekt (som The Construct): dækning + blast. Ingen mutation. Self-safe. | [src](../../../core/services/central_surgery.py#L174) |
| function | `_is_tested` | `(target)` | — | [src](../../../core/services/central_surgery.py#L186) |
| function | `verify` | `(pid)` | Kør SECURITY-mutation_gate: frossen kerne → blocked, ellers verified. Self-safe. | [src](../../../core/services/central_surgery.py#L197) |
| function | `escalate` | `(pid)` | Send forslaget til Bjørn (owner-godkendelse). Kun et verificeret forslag kan eskaleres. | [src](../../../core/services/central_surgery.py#L211) |
| function | `list_proposals` | `(*, limit=…)` | — | [src](../../../core/services/central_surgery.py#L224) |
| function | `snapshot_file` | `(target)` | Sikkerhedsnet: fang en fils NUVÆRENDE indhold durabelt FØR et indgreb (undo uden git). | [src](../../../core/services/central_surgery.py#L234) |
| function | `rollback` | `(snapshot_id)` | OWNER-handling: gendan en fil atomisk fra et tidligere snapshot (undo uden git). Nægter | [src](../../../core/services/central_surgery.py#L256) |
| function | `build_surgery_surface` | `()` | Owner/self-view: åbne forslag + felt-linje. Self-safe. | [src](../../../core/services/central_surgery.py#L281) |

## `core/services/central_switches.py`
_Live-kontrol for Centralen (§11). On/off pr. nerve/cluster via shared_cache-flag._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_key` | `(scope, name)` | — | [src](../../../core/services/central_switches.py#L14) |
| function | `set_enabled` | `(scope, name, enabled, *, klass=…)` | Slå en nerve/cluster on/off live. Sikkerheds-nerve + enabled=False afvises. | [src](../../../core/services/central_switches.py#L18) |
| function | `is_enabled` | `(scope, name)` | — | [src](../../../core/services/central_switches.py#L28) |
| function | `set_cluster_enabled` | `(cluster, enabled)` | Slå et HELT cluster on/off live (Jarvis' idé). Sikkerheds-cluster + enabled=False | [src](../../../core/services/central_switches.py#L41) |
| function | `is_cluster_enabled` | `(cluster)` | True medmindre clusteret er EKSPLICIT slået fra. Default ON. | [src](../../../core/services/central_switches.py#L57) |
| class | `CircuitBreaker` | `` | Tæl fejl pr. nerve; isolér efter `threshold` på stribe. Nulstil ved succes. | [src](../../../core/services/central_switches.py#L62) |
| method | `CircuitBreaker.__init__` | `(self, threshold=…)` | — | [src](../../../core/services/central_switches.py#L65) |
| method | `CircuitBreaker.record` | `(self, nerve, ok)` | Returnér True hvis kredsen NETOP blev (eller fortsat er) åben/isoleret. | [src](../../../core/services/central_switches.py#L70) |
| method | `CircuitBreaker.is_open` | `(self, nerve)` | — | [src](../../../core/services/central_switches.py#L79) |
| method | `CircuitBreaker.open_nerves` | `(self)` | Nerver hvis kreds NETOP er åben/isoleret (til Centralens self-helbreds-check). | [src](../../../core/services/central_switches.py#L83) |
| method | `CircuitBreaker.reset` | `(self, nerve)` | — | [src](../../../core/services/central_switches.py#L90) |
| function | `drift_flag` | `(name, value, *, baseline, tol)` | Flag-on-change-skelet (§7): returnér en flag-dict hvis |value-baseline| > tol, | [src](../../../core/services/central_switches.py#L95) |

## `core/services/central_terminal.py`
_central_terminal — en command-line ind i Den Intelligente Central (owner-terminal)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_q` | `(action, **kw)` | — | [src](../../../core/services/central_terminal.py#L35) |
| function | `_fmt_envelope` | `(env)` | central_query-envelope → terminal-linjer (kompakt, læsbar). | [src](../../../core/services/central_terminal.py#L40) |
| function | `run_command` | `(line)` | Parse + udfør én terminal-kommando. Returnerer {ok, command, lines}. Self-safe. | [src](../../../core/services/central_terminal.py#L76) |

## `core/services/central_timeseries.py`
_core/services/central_timeseries.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_timeseries.py#L46) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_timeseries.py#L55) |
| function | `_durability_on` | `()` | Hot-path-durabilitet (auto-restore/persist i record/recent) er AKTIV i produktion, men | [src](../../../core/services/central_timeseries.py#L63) |
| class | `Sample` | `` | — | [src](../../../core/services/central_timeseries.py#L71) |
| function | `record` | `(cluster, nerve, value=…, *, meta=…)` | Tilføj ét sample til (cluster, nerve)'s serie. Best-effort, kaster aldrig. | [src](../../../core/services/central_timeseries.py#L77) |
| function | `recent` | `(cluster, nerve, *, limit=…)` | Læs de seneste samples for én nerve (nyeste sidst). READ-ONLY. | [src](../../../core/services/central_timeseries.py#L108) |
| function | `nerves` | `()` | Alle (cluster, nerve)-nøgler der har mindst ét sample. READ-ONLY. | [src](../../../core/services/central_timeseries.py#L125) |
| function | `stats` | `()` | Samlet overblik: antal nerver + samples pr. nerve. READ-ONLY, til observabilitet. | [src](../../../core/services/central_timeseries.py#L134) |
| function | `snapshot` | `(*, recent=…)` | Kompakt cross-proces-snapshot: pr. nerve seneste værdi(er) + count. Read-only, self-safe. | [src](../../../core/services/central_timeseries.py#L149) |
| function | `persist_snapshot` | `()` | Flush de bounded per-nerve-serier til durabel kv, så nervesystemet OVERLEVER genstart. | [src](../../../core/services/central_timeseries.py#L173) |
| function | `_load_durable` | `()` | Genindlæs det durable snapshot ind i _series (merge-append). Self-safe. | [src](../../../core/services/central_timeseries.py#L191) |
| function | `_maybe_restore` | `()` | Restore-on-first-access (dobbelt-tjekket): genindlæs durabelt snapshot ÉN gang efter boot. | [src](../../../core/services/central_timeseries.py#L214) |
| function | `_maybe_persist` | `()` | Throttlet flush i baggrundstråd (hot-path stalles ALDRIG af DB-skrivning). | [src](../../../core/services/central_timeseries.py#L228) |
| function | `_reset_for_tests` | `()` | Testhjælper — ryd al state. Ikke til produktionsbrug. | [src](../../../core/services/central_timeseries.py#L241) |

## `core/services/central_todo.py`
_Central TODO — ÉN prioriteret, pollbar huskeliste på tværs af ALLE clusters. I stedet for_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_incident_is_fresh` | `(inc, *, max_age_h=…)` | True hvis incidentens ts er inden for max_age_h. Ukendt/uparsbar ts → True (fail-open: | [src](../../../core/services/central_todo.py#L28) |
| function | `_item` | `(priority, source, what, **extra)` | — | [src](../../../core/services/central_todo.py#L42) |
| function | `build_todo` | `(*, max_items=…)` | Saml + ranger todos fra alle clusters. Self-safe — en kilde der fejler udelades. | [src](../../../core/services/central_todo.py#L46) |
| function | `poll` | `(*, limit=…)` | Pollbar af Claude i tomgang: top-prioriterede todos + tælling pr. prioritet. | [src](../../../core/services/central_todo.py#L133) |
| function | `build_central_todo_surface` | `()` | MC-surface — read-only prioriteret huskeliste. | [src](../../../core/services/central_todo.py#L146) |

## `core/services/central_tone.py`
_core/services/central_tone.py — Centralens sproglige TONE-PROFIL (rådets #5)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_valence` | `()` | Læs den ene FØLTE tilstand {tone, score, intensitet}. Kaster (fanges udenfor). | [src](../../../core/services/central_tone.py#L56) |
| function | `_read_affect` | `()` | Læs affekt-fordelingen {tryk,varme,uro,ro,dominant,total}. Kaster (fanges udenfor). | [src](../../../core/services/central_tone.py#L63) |
| function | `_read_pressure_signals` | `()` | Let central-status: åbne breakers + uløste severe incidents. Self-safe → {}. | [src](../../../core/services/central_tone.py#L70) |
| function | `_absorb` | `(cluster, nerve, value, **kw)` | Indirektion så absorb kan patches i test uden at ramme central_core. | [src](../../../core/services/central_tone.py#L86) |
| function | `_derive_register` | `(dominant_affect, *, under_pressure)` | Afled sprogligt register fra dominant affekt + system-pres. Deterministisk. | [src](../../../core/services/central_tone.py#L96) |
| function | `build_tone_profile` | `()` | Producér Centralens sproglige tone-profil fra system-tilstand. Self-safe. | [src](../../../core/services/central_tone.py#L114) |
| function | `build_tone_surface` | `()` | Mission Control / read-only surface for tone-profilen. Self-safe. | [src](../../../core/services/central_tone.py#L187) |

## `core/services/central_trace.py`
_Trace-sink for Centralen (§3.2/§7). En trådsikker, volumen-tolerant ring-buffer_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TraceRecord` | `` | — | [src](../../../core/services/central_trace.py#L17) |
| class | `TraceSink` | `` | — | [src](../../../core/services/central_trace.py#L30) |
| method | `TraceSink.__init__` | `(self, maxlen=…)` | — | [src](../../../core/services/central_trace.py#L31) |
| method | `TraceSink.record` | `(self, rec)` | — | [src](../../../core/services/central_trace.py#L38) |
| method | `TraceSink.subscribe` | `(self)` | — | [src](../../../core/services/central_trace.py#L70) |
| method | `TraceSink.unsubscribe` | `(self, q)` | — | [src](../../../core/services/central_trace.py#L76) |
| method | `TraceSink.records_for_run` | `(self, run_id)` | — | [src](../../../core/services/central_trace.py#L84) |
| method | `TraceSink.recent` | `(self, limit=…)` | — | [src](../../../core/services/central_trace.py#L88) |
| function | `sink` | `()` | — | [src](../../../core/services/central_trace.py#L96) |

## `core/services/central_trainman.py`
_Trainman — drømme → narrative erindringer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_dreams` | `(limit=…)` | Seneste distillerede/konsoliderede drømme (id, tema, timestamp). Self-safe. | [src](../../../core/services/central_trainman.py#L40) |
| function | `_existing_dream_memories` | `(limit=…)` | Trainmans allerede-vævede erindringer i private_brain (til idempotens + tema-forbindelser). | [src](../../../core/services/central_trainman.py#L49) |
| function | `_dream_id_of` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L59) |
| function | `_dream_theme` | `(dream)` | Øverste tema for en drøm. Konsoliderings-drømme bærer en themes-liste; distillat en top_theme. | [src](../../../core/services/central_trainman.py#L63) |
| function | `_dream_timestamp` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L74) |
| function | `_sig_of` | `(rec)` | Afkod source_signals-JSON på en vævet erindring (dream_id, theme, connected_to …). Self-safe. | [src](../../../core/services/central_trainman.py#L78) |
| function | `_interlanguage` | `(theme)` | Byg en interlanguage-notation for temaet. Prøv lexicon (bundne termer); ellers spec-stil | [src](../../../core/services/central_trainman.py#L88) |
| function | `_emotional_tone` | `(theme)` | Simpel deterministisk klang ud fra tema-ord. Ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L105) |
| function | `_weave_narrative` | `(*, theme, dream)` | Væv drømmen til en 1.-persons erindrings-historie. Ren tekst, ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L117) |
| function | `_connected_ids` | `(theme, existing, *, limit=…)` | record_id'er for tidligere vævede erindringer om SAMME tema (drømme-kontinuitet). Self-safe. | [src](../../../core/services/central_trainman.py#L126) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/central_trainman.py#L139) |
| function | `_write_memory` | `(*, dream_id, theme, narrative, interlanguage, connected_to, emotional_tone, now)` | Skriv den vævede erindring til private_brain (source='dream'). Returnerer record_id ('' ved fejl). | [src](../../../core/services/central_trainman.py#L149) |
| function | `_signal_agenda` | `(*, theme, count, dream_id)` | 3+ drømme om samme tema på 7 dage → lav-prioritets initiativ til Agendaen. Self-safe. | [src](../../../core/services/central_trainman.py#L183) |
| function | `transform_dreams` | `(*, trigger=…, last_visible_at=…)` | Væv nye drømme til narrative erindringer i private_brain (source='dream'). | [src](../../../core/services/central_trainman.py#L201) |
| function | `_count_theme_recent` | `(theme, memories, *, now)` | Antal vævede erindringer om `theme` indenfor RECURRENCE_WINDOW_DAYS. Self-safe. | [src](../../../core/services/central_trainman.py#L268) |
| function | `_theme_distribution` | `(memories, *, now, days=…)` | Tema→antal over de sidste `days` dage. Self-safe. | [src](../../../core/services/central_trainman.py#L285) |
| function | `_last_reflection_at` | `(existing)` | — | [src](../../../core/services/central_trainman.py#L300) |
| function | `_maybe_reflect` | `(*, existing, now)` | Én gang pr. ~døgn: skriv en metakognitiv erindring om de sidste 7 dages tema-fordeling. | [src](../../../core/services/central_trainman.py#L307) |
| function | `_maybe_silence_note` | `(*, existing, now)` | Temaer der før var tilbagevendende men har været tavse i 14 dage → nysgerrigheds-note. | [src](../../../core/services/central_trainman.py#L340) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_trainman.py#L392) |
| function | `build_trainman_surface` | `()` | Seneste vævede erindringer + tema-fordeling for Central-CLI. READ-ONLY. Self-safe. | [src](../../../core/services/central_trainman.py#L409) |
| function | `record_trainman` | `(*, trigger=…, last_visible_at=…)` | Cadence: væv nye drømme til erindringer. Self-safe — kaster aldrig. | [src](../../../core/services/central_trainman.py#L444) |

## `core/services/central_twins.py`
_The Twins — gentagelses-detektor på tværs af tid._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_twins.py#L32) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/central_twins.py#L36) |
| function | `_incidents` | `(limit=…)` | — | [src](../../../core/services/central_twins.py#L46) |
| function | `_gate_counts` | `()` | — | [src](../../../core/services/central_twins.py#L54) |
| function | `_dissents` | `(limit=…)` | — | [src](../../../core/services/central_twins.py#L62) |
| function | `_incident_patterns` | `(incidents, *, now)` | Gentagne incident-mønstre indenfor vinduet: (nerve, kind) og (nerve, tidspunkt-på-dagen). Self-safe. | [src](../../../core/services/central_twins.py#L72) |
| function | `_gate_patterns` | `(counts, *, now)` | Gentagne yellow/red på samme gate (nerve) indenfor vinduet. Self-safe. | [src](../../../core/services/central_twins.py#L98) |
| function | `_dissent_patterns` | `(dissents, *, now)` | Gentagne uhørte indsigelser på samme gate indenfor vinduet. Self-safe. | [src](../../../core/services/central_twins.py#L124) |
| function | `_describe` | `(pat)` | Én linje der siger 'det her har jeg set før'. Deterministisk, ingen model. Self-safe. | [src](../../../core/services/central_twins.py#L140) |
| function | `detect_repeats` | `()` | Scan alle tre kilder for mønstre der gentager sig 3+ gange på 7 dage. READ-ONLY. | [src](../../../core/services/central_twins.py#L162) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_twins.py#L183) |
| function | `build_twins_surface` | `()` | Detekterede gentagende mønstre + følt linje. READ-ONLY. Self-safe. | [src](../../../core/services/central_twins.py#L200) |
| function | `record_twins` | `(*, trigger=…, last_visible_at=…)` | Cadence (240 min): scan for gentagelser → twins://-signaler (observe/surface only). Self-safe. | [src](../../../core/services/central_twins.py#L219) |

## `core/services/central_valence.py`
_core/services/central_valence.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_valence.py#L18) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_valence.py#L27) |
| function | `_read_valence_trajectory` | `()` | — | [src](../../../core/services/central_valence.py#L35) |
| function | `_read_somatic` | `()` | — | [src](../../../core/services/central_valence.py#L49) |
| function | `_read_stance` | `()` | — | [src](../../../core/services/central_valence.py#L60) |
| function | `_tone_label` | `(score)` | Ét felt-ord for tilstanden ud fra den FRISKE (present-moment) score. Bevidst få, tydelige toner. | [src](../../../core/services/central_valence.py#L72) |
| function | `integrate_valence` | `()` | Integrér de fire organer til ÉN følt tilstand {tone, score, intensitet}. Valens-trajektorien er | [src](../../../core/services/central_valence.py#L92) |
| function | `get_valence_state` | `()` | Centralens durable følte tilstand (senest integrerede). Self-safe. | [src](../../../core/services/central_valence.py#L120) |
| function | `run_valence_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: integrér følelses-organerne → gem durabelt + egress-fri observe (kun skalarer/tone-label, | [src](../../../core/services/central_valence.py#L126) |
| function | `register_valence_producer` | `()` | Registrér følt-tilstands-integrationen som cadence-producer (~hvert 15 min). Egress-frit. | [src](../../../core/services/central_valence.py#L142) |
| function | `build_valence_surface` | `()` | Mission Control — read-only: Centralens ene følte tilstand. | [src](../../../core/services/central_valence.py#L154) |

## `core/services/central_watch.py`
_core/services/central_watch.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_uid` | `()` | — | [src](../../../core/services/central_watch.py#L41) |
| function | `_notify_owner` | `(title, message, importance)` | — | [src](../../../core/services/central_watch.py#L49) |
| function | `_raise_flag` | `(cluster, nerve, *, severity, message, importance=…, make_incident=…)` | Ét flag → trace + (læring via incident) + (notifikation) + tidsserie. Self-safe. | [src](../../../core/services/central_watch.py#L63) |
| function | `_latest` | `(cluster, nerve)` | — | [src](../../../core/services/central_watch.py#L96) |
| function | `run_watch_tick` | `(*, trigger=…, last_visible_at=…)` | Evaluér de fodrede streams; flag ægte (støjfangede) signaler. Self-safe. | [src](../../../core/services/central_watch.py#L101) |
| function | `_council_forced_count` | `(*, limit=…)` | Antal council.deadlock_forced_conclusion på eventbussen nyligt. Cross-proces. | [src](../../../core/services/central_watch.py#L316) |
| function | `_today_cost_usd` | `()` | — | [src](../../../core/services/central_watch.py#L329) |
| function | `_cheap_lane_stats` | `(*, limit=…)` | (completed, failed) fra seneste cheap-lane-events på eventbussen (cross-proces). | [src](../../../core/services/central_watch.py#L337) |
| function | `_tool_outcome_counts` | `(*, limit=…)` | (total, errors) fra seneste tool.completed-events på eventbussen. Cross-proces. | [src](../../../core/services/central_watch.py#L353) |
| function | `_heed_summary` | `()` | Verification-heed-aggregat (fil-backet = cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L369) |
| function | `_recent_cache_pcts` | `(*, limit=…)` | Læs seneste cache-hit-rater fra eventbussen (cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L378) |
| function | `register_watch_producer` | `()` | Registrér vagten som cadence-producer (~hvert 2 min). Læser tidsserie + flagger. | [src](../../../core/services/central_watch.py#L392) |

## `core/services/central_white_rabbit.py`
_Follow the White Rabbit — serendipitets-motoren._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_dark_doors` | `()` | Mørke/stille nerver ingen rører — de uåbnede døre. Self-safe. | [src](../../../core/services/central_white_rabbit.py#L25) |
| function | `follow_rabbit` | `(*, seed=…)` | Vælg én uåbnet dør at undre sig over — ren ikke-målrettet udforskning. Self-safe. | [src](../../../core/services/central_white_rabbit.py#L36) |
| function | `_observe` | `(door, total)` | — | [src](../../../core/services/central_white_rabbit.py#L49) |
| function | `build_white_rabbit_surface` | `()` | — | [src](../../../core/services/central_white_rabbit.py#L58) |
| function | `record_white_rabbit` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_white_rabbit.py#L62) |

## `core/services/central_xproc.py`
_Cross-proces trace-tee for Den Intelligente Central._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `process_role` | `()` | 'api' (visible-lane, JARVIS_ENABLE_RUNTIME_SERVICES=0) eller 'runtime' (daemons). | [src](../../../core/services/central_xproc.py#L37) |
| function | `maybe_publish` | `()` | Throttled publish af denne proces' feed + sundhed. Kaldt fra trace-record (hot path) | [src](../../../core/services/central_xproc.py#L43) |
| function | `_publish_now` | `()` | — | [src](../../../core/services/central_xproc.py#L70) |
| function | `foreign_feeds` | `(own_role)` | Records fra ALLE andre processer end ens egen (ens egen har vi in-memory, friskere). | [src](../../../core/services/central_xproc.py#L120) |
| function | `merged_timeseries` | `()` | Alle processers per-nerve tidsserie merget: nerve-key → {proces: {latest,count,meta,recent}}. | [src](../../../core/services/central_xproc.py#L139) |
| function | `all_health` | `()` | Per-proces sundhed for hver kendt proces der har publiceret (ikke udløbet). Self-safe. | [src](../../../core/services/central_xproc.py#L161) |

## `core/services/channel_inbound.py`
_Kanal-plugin inbound-routing (spec §5.2/§5.3, Fase 5 Lag 1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_builtin_channel_plugins` | `()` | Idempotent registrering af indbyggede kanal-plugins (kaldes fra plugins-route). | [src](../../../core/services/channel_inbound.py#L33) |
| function | `resolve_inbound_mode` | `(requested_mode=…, *, author_role=…, override_active=…)` | Afgør den effektive mode for en indkommende kanal-besked (§18.9). | [src](../../../core/services/channel_inbound.py#L45) |
| function | `route_inbound` | `(**kwargs)` | Auth-cluster GENNEM Den Intelligente Central (observe). A2+A4: plugin-hardblock + | [src](../../../core/services/channel_inbound.py#L63) |
| function | `_route_inbound_impl` | `(*, plugin_id, channel, author_role=…, author_user_id=…, text=…, hour=…, now=…, mode=…, override_active=…)` | Afgør om en indkommende kanal-besked må nå Jarvis (plugin_ruleset hardblock), | [src](../../../core/services/channel_inbound.py#L84) |

