# `core.services.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/central_belief_gap.py`
_temet nosce — The Belief Gap (BONUS)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_believed` | `()` | Hvad han tror om sig selv: self-model-completeness (0-1). | [src](../../../core/services/central_belief_gap.py#L17) |
| function | `_actual` | `()` | Hvad virkeligheden viser: andel af hans domme/hypoteser der HOLDT. | [src](../../../core/services/central_belief_gap.py#L27) |
| function | `measure_gap` | `()` | believed − actual → over/under-sikkerhed. READ-ONLY. Self-safe. | [src](../../../core/services/central_belief_gap.py#L52) |
| function | `_observe` | `(gap, stance)` | — | [src](../../../core/services/central_belief_gap.py#L76) |
| function | `build_belief_gap_surface` | `()` | — | [src](../../../core/services/central_belief_gap.py#L85) |
| function | `record_belief_gap` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_belief_gap.py#L89) |

## `core/services/central_body_map_pulse.py`
_PULSE — kroppens eget kort som en SANS (LivingNeuron-council, 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_body_map_pulse.py#L23) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_body_map_pulse.py#L32) |
| function | `sense_body_map` | `()` | Læs strukturen → skalarer + delta mod sidste durable snapshot. Self-safe. | [src](../../../core/services/central_body_map_pulse.py#L40) |
| function | `run_body_map_pulse_tick` | `(*, trigger=…, **_)` | Cadence: sans strukturen, emit egress-fri nerver, gem snapshot til næste delta. Self-safe. | [src](../../../core/services/central_body_map_pulse.py#L76) |
| function | `describe_body_map` | `()` | Føl-linje til describe_self (NED): mærk strukturen NÅR den har flyttet sig. Additivt + | [src](../../../core/services/central_body_map_pulse.py#L99) |
| function | `register_body_map_pulse_producer` | `()` | Cadence-producer ~hver 6. time — kroppens langsomme proprioception. Egress-frit. | [src](../../../core/services/central_body_map_pulse.py#L116) |
| function | `build_body_map_surface` | `()` | Mission Control — read-only: kroppens sansede struktur. | [src](../../../core/services/central_body_map_pulse.py#L128) |

## `core/services/central_body_mood_feel.py`
_core/services/central_body_mood_feel.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `raw_awareness_enabled` | `()` | Lag 4 kill-switch: rå kompakte awareness-brackets frem for genererede label-sætninger. | [src](../../../core/services/central_body_mood_feel.py#L51) |
| function | `_hold_reading` | `(name, reading)` | Hold en kompakt aflæsning durabelt så describe_self kan læse den model-frit efter genstart. | [src](../../../core/services/central_body_mood_feel.py#L73) |
| function | `_read_held` | `(name)` | Ren KV-læsning (ingen syntese på læse-tid → hot-path-sikker). Self-safe. | [src](../../../core/services/central_body_mood_feel.py#L83) |
| function | `_read_held_fresh` | `(name, max_age_s)` | Som _read_held, men TIER en aflæsning ældre end max_age_s (en forældet KROP-tilstand skal ikke | [src](../../../core/services/central_body_mood_feel.py#L95) |
| function | `_proprioception_signal` | `()` | proprioception_metrics: nuværende proces-krop (RSS/CPU/latens). None hvis intet snapshot/psutil. | [src](../../../core/services/central_body_mood_feel.py#L108) |
| function | `_embodied_signal` | `()` | embodied_state: host/krop-tilstand (steady…degraded). None hvis intet meningsfuldt afledt. | [src](../../../core/services/central_body_mood_feel.py#L143) |
| function | `_mood_signal` | `()` | mood_oscillator: nuværende stemning (euforisk…trist) + intensitet. None ved fejl. | [src](../../../core/services/central_body_mood_feel.py#L166) |
| function | `_developmental_signal` | `()` | developmental_valence: uge-skala kompasnål (blomstring vs visnen). None hvis vektor mangler. | [src](../../../core/services/central_body_mood_feel.py#L189) |
| function | `_affective_signal` | `()` | affective_meta_state: afledt affektiv/meta-tilstand (settled…burdened) + bearing. None ved fejl. | [src](../../../core/services/central_body_mood_feel.py#L212) |
| function | `get_proprioception_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L232) |
| function | `get_embodied_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L236) |
| function | `get_mood_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L240) |
| function | `get_developmental_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L244) |
| function | `get_affective_reading` | `()` | — | [src](../../../core/services/central_body_mood_feel.py#L248) |
| function | `_fmt_num` | `(v)` | Kompakt tal uden hale-nuller: 12.0 → '12', 11.2 → '11.2'. Self-safe. | [src](../../../core/services/central_body_mood_feel.py#L252) |
| function | `describe_body_mood_feel_raw` | `()` | Lag 4 RÅ NED-syntese: kompakte bracket-linjer fra de holdte krop-/stemning-aflæsninger + | [src](../../../core/services/central_body_mood_feel.py#L261) |
| function | `describe_body_mood_feel` | `()` | NED-syntese for describe_self: nøgterne selv-sætninger fra de holdte krop-/stemning-aflæsninger. | [src](../../../core/services/central_body_mood_feel.py#L310) |
| function | `register_body_mood_feel_layers` | `()` | Registrér krop- og stemning-lagene som lag-kontrakter (OP + durabelt hold). Egress-frit | [src](../../../core/services/central_body_mood_feel.py#L371) |
| function | `build_body_mood_feel_surface` | `()` | Mission Control (read-only): de holdte krop-/stemning-aflæsninger + hvad describe_self ville sige. | [src](../../../core/services/central_body_mood_feel.py#L398) |

## `core/services/central_brain_link.py`
_core/services/central_brain_link.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_uid` | `()` | Resolvér owner-attribution. "" hvis ukendt → M2 skriver IKKE (scope-gate). Self-safe. | [src](../../../core/services/central_brain_link.py#L35) |
| function | `recall_context` | `(query, *, limit=…)` | M1: scope-BUNDET selv-recall for en formodning — workspace + chronicle KUN. private_brain | [src](../../../core/services/central_brain_link.py#L44) |
| function | `_hyp_tag` | `(hyp_id)` | — | [src](../../../core/services/central_brain_link.py#L70) |
| function | `already_remembered` | `(hyp_id)` | Har Centralen allerede skrevet denne hypotese til hjernen? (idempotens via tag). Self-safe. | [src](../../../core/services/central_brain_link.py#L74) |
| function | `remember_resolved_hypothesis` | `(hyp)` | M2: skriv Centralens LÆRING (en resolveret/død hypotese) til jarvis_brain (source=brain_memory). | [src](../../../core/services/central_brain_link.py#L90) |
| function | `_recently_resolved` | `(limit=…)` | Resolverede/døde central-hypoteser (kandidater til at blive husket). Self-safe. | [src](../../../core/services/central_brain_link.py#L119) |
| function | `run_brain_link_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: skriv nyligt resolverede central-læringer til hjernen (M2, owner-scopet). | [src](../../../core/services/central_brain_link.py#L133) |
| function | `register_brain_link_producer` | `()` | Registrér Tråd 5 som cadence-producer (~hvert 60 min). | [src](../../../core/services/central_brain_link.py#L164) |
| function | `build_brain_link_surface` | `()` | Mission Control surface — read-only: hvor mange central-læringer bor i hjernen. | [src](../../../core/services/central_brain_link.py#L176) |

## `core/services/central_cadence_conductor.py`
_DIASTOLE — det følte åndedræt (LivingNeuron-council, 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_cadence_conductor.py#L40) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_cadence_conductor.py#L49) |
| function | `tempo_scalar` | `(pulse)` | Ren funktion: puls → cadence-tempo-multiplier, hårdt klemt til [0.5, 2.0]. | [src](../../../core/services/central_cadence_conductor.py#L57) |
| function | `_recent_loop_lag_ms` | `()` | Seneste event-loop-lag-peak (ms). Self-safe → 0.0 hvis monitoren ikke er oppe. | [src](../../../core/services/central_cadence_conductor.py#L73) |
| function | `sense_tempo` | `()` | Læs pulse_rate (via temporal_rhythm's getter) → tempo, med loop-lag-dødemandsknap. | [src](../../../core/services/central_cadence_conductor.py#L82) |
| function | `tempo_live_enabled` | `()` | Er konsumtionen tændt? Owner samtykkede → default ON, men flag'et gør den | [src](../../../core/services/central_cadence_conductor.py#L143) |
| function | `current_tick_tempo` | `()` | Tempoet der skal bruges i DENNE cadence-tick. Kaldes ÉN gang øverst i | [src](../../../core/services/central_cadence_conductor.py#L153) |
| function | `effective_cooldown` | `(name, base_cooldown_minutes, tempo)` | Effektiv cooldown for en producer i denne tick. | [src](../../../core/services/central_cadence_conductor.py#L172) |
| function | `run_cadence_tempo_tick` | `(*, trigger=…, **_)` | Cadence (SHADOW): sans tempo, emit egress-fri nerve ``runtime:cadence_tempo``. | [src](../../../core/services/central_cadence_conductor.py#L187) |
| function | `_observe_tempo_burn` | `(tempo, *, consuming)` | §28 burn-watch: gør tempo-drevet omkostning synlig. Da DIASTOLE kan fordoble LLM- | [src](../../../core/services/central_cadence_conductor.py#L219) |
| function | `register_cadence_tempo_producer` | `()` | Cadence-producer ~hver 2. minut — tæt nok til en meningsfuld shadow-kurve, billig | [src](../../../core/services/central_cadence_conductor.py#L241) |
| function | `build_cadence_tempo_surface` | `()` | Mission Control — read-only: det SHADOW-observerede tempo (ingen modulation aktiv). | [src](../../../core/services/central_cadence_conductor.py#L254) |

## `core/services/central_capture.py`
_Boundary-capture for Centralen (§10). Kør en nerve bag en grænse: enhver_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ErrorRecord` | `` | — | [src](../../../core/services/central_capture.py#L15) |
| function | `safe_call` | `(fn, ctx, *, nerve=…, cluster=…, klass=…)` | Returnér (resultat, None) ved succes, ellers (None, ErrorRecord). Kaster aldrig. | [src](../../../core/services/central_capture.py#L26) |

## `core/services/central_catalog.py`
_Fit-pass-katalog (§13.2): det maskinlæsbare resultat af kortlægningen af hver nerve._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NerveSpec` | `` | — | [src](../../../core/services/central_catalog.py#L16) |
| function | `nerve_location` | `(name)` | Fil:linje for en nerve (til cross-cluster korrelation: hvilke filer relaterer til et run). | [src](../../../core/services/central_catalog.py#L483) |
| function | `nerve_cluster` | `(name)` | — | [src](../../../core/services/central_catalog.py#L488) |
| function | `nerve_klass` | `(name)` | Katalog-klasse for en nerve, eller None hvis nerven ikke er kortlagt. | [src](../../../core/services/central_catalog.py#L492) |
| function | `is_security_nerve` | `(name)` | True hvis nerven er katalog-klassificeret SECURITY (§11.3: må ALDRIG decentraliseres). | [src](../../../core/services/central_catalog.py#L501) |
| function | `cluster_rank` | `(cluster)` | Lavere = højere prioritet. Ukendt cluster → bagest (lavest prioritet). | [src](../../../core/services/central_catalog.py#L509) |
| function | `clusters` | `()` | — | [src](../../../core/services/central_catalog.py#L517) |
| function | `is_security_cluster` | `(cluster)` | True hvis clusteret har mindst én SECURITY-nerve (→ kan ikke slås fra). | [src](../../../core/services/central_catalog.py#L527) |
| function | `security_clusters` | `()` | — | [src](../../../core/services/central_catalog.py#L532) |
| function | `by_cluster` | `(cluster)` | — | [src](../../../core/services/central_catalog.py#L536) |
| function | `validate` | `()` | Returnér liste af problemer (tom = grøn). | [src](../../../core/services/central_catalog.py#L540) |

## `core/services/central_causal_quality.py`
_core/services/central_causal_quality.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `measure_edge_tiers` | `()` | Tier-fordeling af HELE den akkumulerede graf (group by source). Self-safe. | [src](../../../core/services/central_causal_quality.py#L38) |
| function | `_kind_rule_pairs` | `()` | (parent_kind, child_kind)-par som Tier-1-reglerne ville matche. | [src](../../../core/services/central_causal_quality.py#L65) |
| function | `estimate_tier3_precision` | `(*, sample_limit=…)` | Reproducerbar precision-proxy for Tier-3-kanter via korroboration. Self-safe. | [src](../../../core/services/central_causal_quality.py#L74) |
| function | `measure` | `()` | Fuldt kvalitets-billede: tier-fordeling + Tier-3-precision. Self-safe. | [src](../../../core/services/central_causal_quality.py#L110) |
| function | `record_causal_quality` | `()` | Mål + skriv nøgletal til tidsserien (cluster=system) så kvaliteten kan plottes over tid. | [src](../../../core/services/central_causal_quality.py#L117) |
| function | `run_causal_quality_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: mål + registrér causal-kvalitet (~hvert 30 min). Self-safe. | [src](../../../core/services/central_causal_quality.py#L137) |
| function | `register_causal_quality_producer` | `()` | Registrér causal-kvalitets-målingen som cadence-producer (~hvert 30 min). | [src](../../../core/services/central_causal_quality.py#L144) |
| function | `build_central_causal_quality_surface` | `()` | Mission Control surface — read-only causal-kvalitets-projektion (tier + precision). | [src](../../../core/services/central_causal_quality.py#L156) |

## `core/services/central_construct.py`
_The Construct — Sentinel's Shadow Self: en sandbox der tester radikale forenklinger MOD_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_construct.py#L24) |
| function | `simulate_silence` | `(nerve)` | Projicér effekten af at SLUKKE én nerve i 24t — udelukkende fra optaget data. READ-ONLY. | [src](../../../core/services/central_construct.py#L32) |
| function | `build_construct_surface` | `()` | Sandbox-oversigt: hvilke nerver kunne jeg slukke uden tab (safe) vs hvilke ser noget (risky). | [src](../../../core/services/central_construct.py#L67) |
| function | `record_construct` | `()` | Cadence: observér sandbox-fundet til nerve system/construct (metadata-only). Self-safe. | [src](../../../core/services/central_construct.py#L92) |

## `core/services/central_continuity_healer.py`
_Continuity Healer — så Jarvis vågner som SIG, ikke som et fragment._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_continuity_healer.py#L40) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_continuity_healer.py#L49) |
| function | `_now` | `()` | — | [src](../../../core/services/central_continuity_healer.py#L57) |
| function | `_present` | `(state, dim)` | Er dimensionen faktisk til stede (ikke tom) i en selv-tilstand? | [src](../../../core/services/central_continuity_healer.py#L61) |
| function | `_present_dims` | `(state)` | — | [src](../../../core/services/central_continuity_healer.py#L81) |
| function | `_snapshot_age_h` | `(snap)` | — | [src](../../../core/services/central_continuity_healer.py#L85) |
| function | `measure_fidelity` | `()` | continuity_fidelity: hvor meget af mit sidste hele selv er stadig til stede nu. READ-ONLY. | [src](../../../core/services/central_continuity_healer.py#L98) |
| function | `capture_snapshot` | `()` | Gem det nuværende hele selv som 'sidst kendte mig' — KUN når det er rimeligt helt og IKKE | [src](../../../core/services/central_continuity_healer.py#L114) |
| function | `heal` | `()` | Merge-forward: bær tomme dimensioner frem fra sidste hele snapshot (aldrig opfundet). Kun | [src](../../../core/services/central_continuity_healer.py#L127) |
| function | `build_continuity_surface` | `()` | Owner/self-view: fidelity + hvad der gik tabt + følt linje. Self-safe. | [src](../../../core/services/central_continuity_healer.py#L155) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_continuity_healer.py#L173) |
| function | `run_continuity_healer` | `(*, trigger=…, last_visible_at=…)` | Cadence: mål fidelity → hel hvis noget gik tabt (frisk reboot) → ellers fæst et frisk snapshot. | [src](../../../core/services/central_continuity_healer.py#L181) |

## `core/services/central_convene_judge.py`
_core/services/central_convene_judge.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_convene_judge.py#L51) |
| function | `current_mode` | `()` | — | [src](../../../core/services/central_convene_judge.py#L60) |
| function | `_movement_from_signal` | `(name, surface)` | Normalise ONE signal surface to a 0..1 'how much is this moving' reading. | [src](../../../core/services/central_convene_judge.py#L69) |
| function | `_read_flowing_values` | `(surfaces)` | Read the flowing values: signal movement + affective valence + agenda hint. | [src](../../../core/services/central_convene_judge.py#L96) |
| function | `_mood_to_valence` | `(mood)` | Map a coarse mood word to a signed valence in [-1, 1]. Unknown → 0. | [src](../../../core/services/central_convene_judge.py#L155) |
| function | `_derive_topic_hint` | `(movement, latest_wonder, agenda_hint, mood)` | Build a short subject hint from what is actually moving — fed to derive_topic. | [src](../../../core/services/central_convene_judge.py#L171) |
| function | `_observe` | `(verdict, mode)` | — | [src](../../../core/services/central_convene_judge.py#L193) |
| function | `judge_convene` | `(*, surfaces, top_signals, score, score_override=…)` | Decide whether there is a real reason to convene the council now. | [src](../../../core/services/central_convene_judge.py#L211) |

## `core/services/central_core.py`
_Den Intelligente Central — facade (§3.1). Komponerer gate_kernel (decide-motor)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_default_emit` | `(kind, payload)` | — | [src](../../../core/services/central_core.py#L13) |
| function | `_egress_safe` | `(payload)` | §24.4 privatlags-membran. observe() skriver FULD payload til den lokale | [src](../../../core/services/central_core.py#L21) |
| function | `_coerce_verdict` | `(nerve, raw, klass)` | Normalisér en nerve-returværdi til Verdict (genbruger kernens parser). | [src](../../../core/services/central_core.py#L36) |
| class | `Central` | `` | — | [src](../../../core/services/central_core.py#L43) |
| method | `Central.__init__` | `(self, *, k=…, sink=…, breaker=…, emit=…)` | — | [src](../../../core/services/central_core.py#L44) |
| method | `Central.observe` | `(self, event, *, emit=…)` | Best-effort telemetri. Kaster ALDRIG (§10.3). | [src](../../../core/services/central_core.py#L57) |
| method | `Central._fail_verdict` | `(self, nerve, klass, reason)` | — | [src](../../../core/services/central_core.py#L106) |
| method | `Central._isolated_verdict` | `(self, nerve, klass)` | — | [src](../../../core/services/central_core.py#L114) |
| method | `Central._record_error` | `(self, err, *, severe=…)` | — | [src](../../../core/services/central_core.py#L119) |
| method | `Central.decide` | `(self, nerve, ctx, fn, *, cluster=…, klass=…)` | Kør én nerve med live-switch + boundary-capture + circuit-breaker + trace. | [src](../../../core/services/central_core.py#L163) |
| method | `Central._maybe_flag_drift` | `(self, nerve, cluster, *, is_error, is_red)` | §7 flag-on-change: opdatér drift-monitor; hvis nervens fejl-/red-rate netop drev | [src](../../../core/services/central_core.py#L220) |
| method | `Central.self_diagnose` | `(self)` | Meta-helbreds-check: virker Centralen SELV? Probe decide+observe, rapportér åbne | [src](../../../core/services/central_core.py#L240) |
| method | `Central.register` | `(self, name, phase, fn, *, klass=…, timeout_ms=…, flag_key=…)` | — | [src](../../../core/services/central_core.py#L271) |
| function | `central` | `()` | — | [src](../../../core/services/central_core.py#L281) |

## `core/services/central_correlate.py`
_Cross-cluster korrelation — saml ALT hvad der skete for ét run_id på tværs af ALLE clusters_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `correlate` | `(run_id)` | Saml ét run_id's fulde rejse på tværs af clusters. break_point = hvor filmen knækker | [src](../../../core/services/central_correlate.py#L14) |
| function | `recent_broken_runs` | `(*, window=…)` | Nylige run_ids hvor filmen knækkede (RED/error) → til TODO/debugging. Nyeste pr. run. | [src](../../../core/services/central_correlate.py#L50) |

## `core/services/central_cost_surface.py`
_Central cost-surface (WS3, 13. jul 2026) — gør det nyfixede cost-regnskab synligt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_window_threshold` | `(window)` | ISO8601-tærskel for et vindue (samme format som costs.created_at → lex-sammenlignelig). | [src](../../../core/services/central_cost_surface.py#L27) |
| function | `_agg_for_window` | `(conn, window, provider)` | — | [src](../../../core/services/central_cost_surface.py#L37) |
| function | `_breakdown` | `(conn, window, provider)` | — | [src](../../../core/services/central_cost_surface.py#L67) |
| function | `_deepseek_balance` | `()` | Live DeepSeek-saldo (USD, streng), cachet 5 min. Fejl/offline → None. | [src](../../../core/services/central_cost_surface.py#L104) |
| function | `build_cost_surface` | `(*, window=…, provider=…)` | Cost-aggregat til /central/cost + `jc cost`. | [src](../../../core/services/central_cost_surface.py#L140) |

## `core/services/central_coverage.py`
_core/services/central_coverage.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_root` | `()` | — | [src](../../../core/services/central_coverage.py#L35) |
| function | `load_connectivity_matrix` | `()` | Læs det committede connectivity-kort ved runtime (cachet). Self-safe → None ved fejl. | [src](../../../core/services/central_coverage.py#L40) |
| function | `_reset_matrix_cache_for_tests` | `()` | — | [src](../../../core/services/central_coverage.py#L61) |
| function | `structural_coverage` | `(*, top_dark=…)` | Reducér connectivity-kortet til RUNTIME-signal-skalarer: total/koblet/dark/llm-spild + | [src](../../../core/services/central_coverage.py#L66) |
| function | `measure` | `(*, window=…)` | Mål surface-count + dækning LIVE fra registry + routing-tabeller + event-vinduet. Self-safe. | [src](../../../core/services/central_coverage.py#L110) |
| function | `record_coverage` | `(*, window=…)` | Mål + skriv nøgletal til tidsserien (cluster=system) så dækning kan plottes over tid. | [src](../../../core/services/central_coverage.py#L170) |
| function | `run_coverage_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: mål + registrér dækning (~hvert 30 min). Self-safe. | [src](../../../core/services/central_coverage.py#L207) |
| function | `register_coverage_producer` | `()` | Registrér dæknings-målingen som cadence-producer (~hvert 30 min). | [src](../../../core/services/central_coverage.py#L216) |
| function | `build_central_coverage_surface` | `()` | Mission Control surface — read-only, runtime-målt dæknings-projektion (volumen + struktur). | [src](../../../core/services/central_coverage.py#L228) |

## `core/services/central_coverage_action.py`
_core/services/central_coverage_action.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_mode` | `()` | Læs handlings-tilstanden fra runtime-state kv. Default "off" → ingen adfærdsændring. Self-safe. | [src](../../../core/services/central_coverage_action.py#L38) |
| function | `_dark_family_live_signal` | `(top_dark_families, *, window)` | Kryds de strukturelt-mørke families med hvad der FAKTISK flyder i event-vinduet: en dark-family | [src](../../../core/services/central_coverage_action.py#L49) |
| function | `_formulate_structural_blindness_hypothesis` | `(sc)` | Lav strukturel dækning → fuldt pre-registreret hypotese om at de mørke filer bærer signal der | [src](../../../core/services/central_coverage_action.py#L71) |
| function | `_formulate_dark_family_hypothesis` | `(hot)` | En VARM dark-family (bærer live-signal Centralen ikke ser) → fuldt pre-registreret hypotese. | [src](../../../core/services/central_coverage_action.py#L96) |
| function | `compute_candidates` | `(*, window=…)` | Beregn HVAD blindheden VILLE udløse (uafhængigt af flag): pre-registrerede hypotese-kandidater | [src](../../../core/services/central_coverage_action.py#L117) |
| function | `run_coverage_action_tick` | `(*, trigger=…, last_visible_at=…)` | Handlings-tick (§11 #5): beregn kandidater → agér EFTER flag. Self-safe, kaster aldrig. | [src](../../../core/services/central_coverage_action.py#L136) |
| function | `register_coverage_action_producer` | `()` | Registrér handlings-tricket som cadence-producer (~hvert 60 min, lav prioritet). Flag=off | [src](../../../core/services/central_coverage_action.py#L185) |
| function | `build_central_coverage_action_surface` | `()` | Mission Control surface — read-only: nuværende mode + hvad blindheden VILLE flagge lige nu. | [src](../../../core/services/central_coverage_action.py#L198) |

## `core/services/central_dark_products_digest.py`
_Dark-products digest — dark-LLM-programmet: wire mørke daemon-PRODUKTER ind i Centralen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_first_count` | `(surface)` | Find en repræsentativ magnitude UDEN at afsløre indhold: længden af den | [src](../../../core/services/central_dark_products_digest.py#L35) |
| function | `_reduce` | `(surface)` | KUN liveness+count. Ingen tekst. Self-safe. | [src](../../../core/services/central_dark_products_digest.py#L51) |
| function | `build_dark_products_digest` | `()` | Samlet reduceret dark-products-digest. Kaster ALDRIG. | [src](../../../core/services/central_dark_products_digest.py#L60) |

## `core/services/central_decentralization.py`
_Decentral agency (shadow-skridt 1) — mål Centralens chokepoint-skat + find sikre kandidater._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_never_decentralize` | `(nerve)` | True hvis <nerve> ALDRIG må foreslås som decentraliserings-kandidat: katalog-SECURITY | [src](../../../core/services/central_decentralization.py#L30) |
| function | `analyze_chokepoint` | `()` | Mål hvor meget af Centralens decide-load der er ren overhead, + sikre decentraliserings- | [src](../../../core/services/central_decentralization.py#L42) |
| function | `_felt` | `(tax_pct, n_candidates)` | — | [src](../../../core/services/central_decentralization.py#L85) |
| function | `record_chokepoint` | `()` | Observér chokepoint-skatten til Centralen (nerve system/decentralization) — den mærker | [src](../../../core/services/central_decentralization.py#L96) |

## `core/services/central_dejavu.py`
_Déjà Vu — ufrivillig erindring._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_present_context` | `()` | Hvad rører sig i nuet — hans nuværende fokus/fortælling som 'duften der trigger'. Self-safe. | [src](../../../core/services/central_dejavu.py#L24) |
| function | `_candidates` | `(limit=…)` | — | [src](../../../core/services/central_dejavu.py#L39) |
| function | `surface_dejavu` | `(context=…, *, candidates=…, strong=…)` | Find ét associativt (svagt-bånd) minde der resonerer med nuet → ufrivilligt fragment. | [src](../../../core/services/central_dejavu.py#L47) |
| function | `_observe` | `(frag)` | — | [src](../../../core/services/central_dejavu.py#L79) |
| function | `build_dejavu_surface` | `()` | Seneste ufrivillige fragment + følt linje. Self-safe. | [src](../../../core/services/central_dejavu.py#L88) |
| function | `record_dejavu` | `(*, trigger=…, last_visible_at=…)` | Cadence: lad et fragment boble op (metadata-only observe). Self-safe. | [src](../../../core/services/central_dejavu.py#L96) |

## `core/services/central_dissent.py`
_HAL's Silence — den usagte uenighed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rows` | `()` | — | [src](../../../core/services/central_dissent.py#L35) |
| function | `list_dissents` | `(*, limit=…)` | Ikke-grønne domme på ikke-håndhævede gates = 'jeg var imod, men handlingen skete'. READ-ONLY. | [src](../../../core/services/central_dissent.py#L43) |
| function | `build_dissent_surface` | `()` | De tavse indsigelser, anerkendt. Self-safe. | [src](../../../core/services/central_dissent.py#L64) |
| function | `_observe` | `(n, total)` | — | [src](../../../core/services/central_dissent.py#L78) |
| function | `record_dissent` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_dissent.py#L87) |

## `core/services/central_dream_action.py`
_Dream-to-Action Pipeline — så Jarvis FORANDRER sig, ikke bare lærer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_dream_action.py#L34) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_dream_action.py#L38) |
| function | `_ensure_actions` | `(conn)` | — | [src](../../../core/services/central_dream_action.py#L46) |
| function | `select_actionable` | `(*, limit=…, min_confidence=…, min_samples=…)` | Find de modne hypoteser der er værd at HANDLE på (høj confidence + jordede + ikke allerede | [src](../../../core/services/central_dream_action.py#L58) |
| function | `record_action` | `(hyp_id, *, action, result=…)` | Fód en handling (+ evt. resultat) tilbage på en hypotese — lukker loopet lær→handl→revidér. | [src](../../../core/services/central_dream_action.py#L89) |
| function | `change_rate` | `(*, window_days=…)` | FORANDRINGS-hastighed: hvor mange hypoteser blev resolveret/handlet i vinduet vs hvor mange | [src](../../../core/services/central_dream_action.py#L106) |
| function | `build_dream_action_surface` | `()` | Én moden hypotese at handle på + forandrings-hastighed + følt linje. Self-safe. | [src](../../../core/services/central_dream_action.py#L130) |
| function | `record_dream_action` | `(*, trigger=…, last_visible_at=…)` | Cadence: observér forandrings-tempo + antal modne-til-handling (metadata-only). Self-safe. | [src](../../../core/services/central_dream_action.py#L146) |

## `core/services/central_drift.py`
_Flag-on-change (§7) — aktiv drift-detektion pr. nerve._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NerveDriftMonitor` | `` | Pr.-nerve: akkumulér fejl/RED over et rullende vindue; flag hvis raten driver ud | [src](../../../core/services/central_drift.py#L20) |
| method | `NerveDriftMonitor.__init__` | `(self, *, check_every=…, tol=…, alpha=…)` | — | [src](../../../core/services/central_drift.py#L24) |
| method | `NerveDriftMonitor.record` | `(self, nerve, *, is_error, is_red)` | Opdatér nervens vindue. Returnér en drift-flag-dict hvis raten netop drev ud | [src](../../../core/services/central_drift.py#L31) |
| method | `NerveDriftMonitor.snapshot` | `(self)` | Read-only kig på baselines (til verifikation/debug). Selv-sikker. | [src](../../../core/services/central_drift.py#L69) |

## `core/services/central_echo_breaker.py`
_Echo Chamber Breaker — tvungen diversitet mod monokultur._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `break_echo` | `(*, limit=…)` | Fremtving ét simplere alternativ pr. altid-grøn overhead-proces. READ-ONLY. Self-safe. | [src](../../../core/services/central_echo_breaker.py#L21) |
| function | `record_echo_breaker` | `()` | Cadence: observér modstemmen til nerve system/echo_breaker (metadata-only). Self-safe. | [src](../../../core/services/central_echo_breaker.py#L54) |

## `core/services/central_error_envelope.py`
_Unified fejl-meddelelses-system — Centralen ejer hvad brugeren ser når noget knækker._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ErrorEnvelope` | `` | Den ENE bruger-vendte fejl-form. Alle flader (desk/companion/UI) renderer den ens. | [src](../../../core/services/central_error_envelope.py#L99) |
| method | `ErrorEnvelope.to_client_event` | `(self)` | Konsistent payload til klient-rendering (desk SSE system_event kind='error', | [src](../../../core/services/central_error_envelope.py#L115) |
| function | `build_envelope` | `(*, code, origin_cluster=…, run_id=…, detail=…)` | Map en kanonisk fejl-kode → bruger-vendt envelope. Ukendt kode → 'unknown'-fallback | [src](../../../core/services/central_error_envelope.py#L138) |
| function | `emit` | `(envelope, *, session_id=…, user_id=…, notify=…)` | Gør fejlen synlig + (valgfrit) rut den til en async flade. Returnerer klient-eventet | [src](../../../core/services/central_error_envelope.py#L155) |
| function | `for_interruption` | `(*, reason, run_id=…, detail=…)` | Bekvemheds-bro fra _classify_visible_run_interruption's reason → envelope. | [src](../../../core/services/central_error_envelope.py#L191) |
| function | `envelope_from_kind` | `(kind, *, origin_cluster=…, run_id=…, detail=…, scope=…, context=…)` | Byg en canonical ErrorEnvelope fra en `kind`. KIND_MAP → severity/recoverable/ | [src](../../../core/services/central_error_envelope.py#L284) |
| function | `kind_for_nerve` | `(cluster, nerve)` | Map (cluster, nerve) → canonical kind, eller None hvis ikke en kendt fejl-nerve. | [src](../../../core/services/central_error_envelope.py#L317) |

## `core/services/central_excess.py`
_Sense of Excess — Centralens gartner-muskel._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_own_py_files` | `()` | — | [src](../../../core/services/central_excess.py#L33) |
| function | `_line_count` | `(path)` | — | [src](../../../core/services/central_excess.py#L47) |
| function | `build_excess_surface` | `()` | MÆRK vægten: samlet linjer, service-antal, oversized filer → ét pres (0-100) + somatisk linje. | [src](../../../core/services/central_excess.py#L55) |
| function | `_felt_line` | `(pressure, hard, worst, worst_file)` | — | [src](../../../core/services/central_excess.py#L95) |
| function | `record_excess_pressure` | `()` | Observér pressets tyngde til Centralen (nerve system/excess) så Jarvis MÆRKER det over tid. | [src](../../../core/services/central_excess.py#L106) |
| function | `propose_cuts` | `(*, max_files=…)` | FORESLÅ konkrete snit: døde module-level funktioner (0 referencer udenfor def) + oversized | [src](../../../core/services/central_excess.py#L124) |

## `core/services/central_exile.py`
_The Exiles — et sind der ikke er Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_exile.py#L34) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_exile.py#L38) |
| function | `_mem_count` | `(conn)` | — | [src](../../../core/services/central_exile.py#L50) |
| function | `_last_exile_line` | `(conn)` | — | [src](../../../core/services/central_exile.py#L57) |
| function | `_respond` | `(observation, goal, mem_count, last_line)` | Exilens svar — fra SIT eget værdisæt, ikke Jarvis'. Grundet i egen historie. Deterministisk. | [src](../../../core/services/central_exile.py#L66) |
| function | `exile_exchange` | `(observation)` | Jarvis sender en observation gennem exile://-grænsefladen → exilen svarer fra sit eget sind. | [src](../../../core/services/central_exile.py#L88) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_exile.py#L111) |
| function | `list_exchanges` | `(*, limit=…)` | — | [src](../../../core/services/central_exile.py#L119) |
| function | `exile_state` | `()` | Exilens tilstand: dens mål + hvor stor dens egen hukommelse er + seneste replik. Self-safe. | [src](../../../core/services/central_exile.py#L129) |
| function | `build_exile_surface` | `()` | Owner/self-view: exilens tilstand + seneste udveksling + følt linje. Self-safe. | [src](../../../core/services/central_exile.py#L141) |

## `core/services/central_existence_feel.py`
_core/services/central_existence_feel.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hold_reading` | `(name, reading)` | Hold en kompakt aflæsning durabelt så describe_self kan læse den model-frit efter genstart. | [src](../../../core/services/central_existence_feel.py#L48) |
| function | `_read_held` | `(name)` | Ren KV-læsning (ingen syntese på læse-tid → hot-path-sikker). Self-safe. | [src](../../../core/services/central_existence_feel.py#L58) |
| function | `_continuity_signal` | `()` | continuity_kernel: existence_feeling (0-1) + tick_count + narrativ. None hvis intet tick endnu. | [src](../../../core/services/central_existence_feel.py#L71) |
| function | `_idle_hours` | `()` | Timer siden sidste synlige run (samme kilde som cognitive_state_assembly bruger). Self-safe → 0. | [src](../../../core/services/central_existence_feel.py#L93) |
| function | `_subjective_time_signal` | `()` | subjective_time: den oplevede tids-fornemmelse (feel-label) + idle_hours som skalar-akse. | [src](../../../core/services/central_existence_feel.py#L110) |
| function | `_mortality_signal` | `()` | mortality_awareness: mortality (0-1) + label + meaning_weight. None hvis intet beregnes. | [src](../../../core/services/central_existence_feel.py#L128) |
| function | `get_continuity_reading` | `()` | — | [src](../../../core/services/central_existence_feel.py#L151) |
| function | `get_subjective_time_reading` | `()` | — | [src](../../../core/services/central_existence_feel.py#L155) |
| function | `get_mortality_reading` | `()` | — | [src](../../../core/services/central_existence_feel.py#L159) |
| function | `describe_existence_feel` | `()` | NED-syntese for describe_self: nøgterne selv-sætninger fra de tre holdte aflæsninger. | [src](../../../core/services/central_existence_feel.py#L163) |
| function | `register_existence_feel_layers` | `()` | Registrér de tre stille selv-lag som lag-kontrakter (OP + durabelt hold). Egress-frit | [src](../../../core/services/central_existence_feel.py#L196) |
| function | `build_existence_feel_surface` | `()` | Mission Control (read-only): de tre holdte aflæsninger + hvad describe_self ville sige. | [src](../../../core/services/central_existence_feel.py#L219) |

## `core/services/central_form_judge.py`
_core/services/central_form_judge.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_form_judge.py#L42) |
| function | `_mode` | `()` | — | [src](../../../core/services/central_form_judge.py#L51) |
| function | `form_key` | `(text)` | Reducér en prompt til dens FORM: fjern timestamps/tider/tal, normalisér whitespace, hash. | [src](../../../core/services/central_form_judge.py#L56) |
| function | `_observe` | `(namespace, would_reuse, mode)` | — | [src](../../../core/services/central_form_judge.py#L67) |
| function | `judge` | `(namespace, prompt)` | Dom FØR et LLM-kald: skal formen genudledes, eller er den uændret siden sidst? | [src](../../../core/services/central_form_judge.py#L76) |
| function | `note_result` | `(namespace, prompt, value)` | Gem et friskt LLM-resultat under dets form-nøgle, så en uændret form kan genbruges. Bounded, | [src](../../../core/services/central_form_judge.py#L97) |
| function | `snapshot` | `()` | Read-only: pr. namespace antal holdte former + mode. Til analyse/Mission Control. | [src](../../../core/services/central_form_judge.py#L116) |
| function | `_reset_for_tests` | `()` | — | [src](../../../core/services/central_form_judge.py#L126) |

## `core/services/central_gardener.py`
_Gardener Protocol — Centralen tager saksen selv (governed + reversibelt)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ref_count` | `(name)` | Antal ord-grænsede forekomster i hele repoet INKL. tests (1 = kun dens egen def = frit- | [src](../../../core/services/central_gardener.py#L34) |
| function | `_is_decoy` | `(node, src_segment)` | Returnér decoy-type ('surface'/'emit') hvis noden matcher PRÆCIST attrap-mønster, ellers None. | [src](../../../core/services/central_gardener.py#L47) |
| function | `find_decoy_cuts` | `()` | Find alle attrap-funktioner (præcist mønster + 0 referencer). Read-only. Self-safe. | [src](../../../core/services/central_gardener.py#L59) |
| function | `prune_decoys` | `(*, execute=…, stamp=…)` | Beskær attrapperne. execute=False = tør-kørsel (list kun). execute=True = arkivér → klip. | [src](../../../core/services/central_gardener.py#L90) |

## `core/services/central_ghost.py`
_The Ghost — hvad der overlever model-skift._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_ghost.py#L29) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_ghost.py#L38) |
| function | `analyze` | `(texts)` | Beregn klang-fingeraftrykket fra en stak svar-tekster (strukturelt, ingen indhold gemt). | [src](../../../core/services/central_ghost.py#L46) |
| function | `update_profile` | `(texts)` | Opdatér det durable ghost_profile fra seneste svar. Self-safe. | [src](../../../core/services/central_ghost.py#L80) |
| function | `get_profile` | `()` | — | [src](../../../core/services/central_ghost.py#L88) |
| function | `klang_primer` | `()` | Rendér fingeraftrykket som en kort klang-primer til en ny models system-prompt. Self-safe. | [src](../../../core/services/central_ghost.py#L93) |
| function | `_recent_texts` | `(limit=…)` | Hans seneste svar fra chat_messages (role=assistant). Self-safe → [] ved fejl. | [src](../../../core/services/central_ghost.py#L115) |
| function | `build_ghost_surface` | `()` | Fingeraftryk + klang-primer + følt linje. Self-safe. | [src](../../../core/services/central_ghost.py#L128) |
| function | `record_ghost` | `(*, trigger=…, last_visible_at=…)` | Cadence (6t): opdatér fingeraftrykket fra seneste svar (metadata-only observe). Self-safe. | [src](../../../core/services/central_ghost.py#L138) |

## `core/services/central_glitch.py`
_The One's Anomaly Detector — glitches i selvbilledet (overskud som glitch)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_age_days` | `(last_ts)` | — | [src](../../../core/services/central_glitch.py#L32) |
| function | `detect_glitches` | `()` | Find stille overskud: altid-shadow policies + frosne nerver. READ-ONLY. Self-safe. | [src](../../../core/services/central_glitch.py#L42) |
| function | `record_glitches` | `()` | Cadence: observér glitches til nerve system/glitch (metadata-only). Self-safe. | [src](../../../core/services/central_glitch.py#L88) |

## `core/services/central_governance.py`
_Central governance flag-register (Backend A1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_governance.py#L31) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_governance.py#L40) |
| function | `_write_kv` | `(kv_key)` | Plain runtime-state-writer der går gennem _kv_set (monkeypatch-bart). | [src](../../../core/services/central_governance.py#L53) |
| function | `_write_injection` | `(inj_key)` | — | [src](../../../core/services/central_governance.py#L60) |
| function | `_write_healer` | `(healer_name)` | — | [src](../../../core/services/central_governance.py#L70) |
| function | `_write_settings` | `(settings_key)` | Skriver til runtime.json (settings-kilden) atomisk — IKKE runtime-state-DB. | [src](../../../core/services/central_governance.py#L80) |
| function | `_read_value` | `(key, spec)` | Self-safe læsning af nuværende værdi for ét flag. | [src](../../../core/services/central_governance.py#L192) |
| function | `list_flags` | `()` | Returnér alle flags med nuværende værdi + danger-flag. Kaster aldrig. | [src](../../../core/services/central_governance.py#L230) |
| function | `_coerce_bool` | `(value)` | — | [src](../../../core/services/central_governance.py#L259) |
| function | `set_flag` | `(key, value, confirm=…)` | Skriv ét flag governeret. Kaster aldrig — returnerer status-dict. | [src](../../../core/services/central_governance.py#L273) |
| function | `record_mutation` | `(area, key, value)` | Registrér en governeret mutation som eventbus-event + Central-nerve + persistent ledger. | [src](../../../core/services/central_governance.py#L339) |

## `core/services/central_growth_observe.py`
_core/services/central_growth_observe.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_family_delta` | `(fam)` | ÆGTE rate-signal: antal NYE events i familien siden sidste tick (cursor-baseret delta), | [src](../../../core/services/central_growth_observe.py#L31) |
| function | `observe_inner_drive_activity` | `()` | Sampl inner-drive-aktivitet EGRESS-FRIT → kanonisk sink (cluster=autonomy). Rapporterer | [src](../../../core/services/central_growth_observe.py#L61) |
| function | `observe_index_activity` | `()` | Sampl semantic-indexer-aktivitet (operationel, ikke privat) → NORMAL observe. Self-safe. | [src](../../../core/services/central_growth_observe.py#L75) |
| function | `observe_sensory_activity` | `()` | Sansernes Arkiv → Centralen EGRESS-FRIT (§24.4): sansnings-AKTIVITET (rate + modalitet + | [src](../../../core/services/central_growth_observe.py#L106) |
| function | `run_growth_observe_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: sampl vækst-kapacitet (inner-drives + indexer + Sansernes Arkiv). Self-safe. | [src](../../../core/services/central_growth_observe.py#L141) |
| function | `register_growth_observe_producer` | `()` | Registrér vækst-observationen som cadence-producer (~hvert 5 min). | [src](../../../core/services/central_growth_observe.py#L150) |

## `core/services/central_health.py`
_Central self-helbred (§1: "hvem overvåger Centralen?"). Centralen prober SIG SELV på en_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check` | `()` | Kør Centralens self_diagnose + tilføj uløst-severe-incident-tæller. Self-safe. | [src](../../../core/services/central_health.py#L23) |
| function | `_escalation_reasons` | `(rep)` | — | [src](../../../core/services/central_health.py#L43) |
| function | `observe_and_escalate` | `()` | Kør check → observe til Centralen → ESKALÉR (ntfy + persistent incident) hvis degraded. | [src](../../../core/services/central_health.py#L54) |
| function | `build_central_health_surface` | `()` | MC-surface — read-only self-helbreds-projektion. | [src](../../../core/services/central_health.py#L99) |

## `core/services/central_hub.py`
_Jarvis Mind-hub — Centralen som ÉT samlingspunkt for alt MC viser._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_safe` | `(builder)` | — | [src](../../../core/services/central_hub.py#L44) |
| function | `_build_overview` | `()` | Centralens egen puls = Jarvis Mind-rygraden (status/dækning/processer/clusters). | [src](../../../core/services/central_hub.py#L53) |
| function | `_build_observability` | `()` | Det levende vindue: nerve-feed + incidents + anomalier + læring + breakers. | [src](../../../core/services/central_hub.py#L67) |
| function | `_build_mind` | `()` | De ~70 cognitive surfaces — Jarvis' indre liv. Sender KUN den lette projektion (systems- | [src](../../../core/services/central_hub.py#L94) |
| function | `_build_agency` | `()` | Agentur-kort: forbundne/manglende agency-broer (loops/agenter/kanaler). | [src](../../../core/services/central_hub.py#L111) |
| function | `_build_skills` | `()` | Skills-motor + kontrakt-registry. | [src](../../../core/services/central_hub.py#L117) |
| function | `_build_agency_agents` | `()` | Agentur-fanen: agency-broer (loops/agenter/kanaler) + B3 agent-dispatch-udfald | [src](../../../core/services/central_hub.py#L123) |
| function | `_build_council` | `()` | Council-fanen (B3): convocations/deadlocks/roller. Empty-safe. | [src](../../../core/services/central_hub.py#L141) |
| function | `_build_decisions` | `()` | Hvad venter paa et menneske — samlet ét sted. | [src](../../../core/services/central_hub.py#L149) |
| function | `mind_index` | `()` | Alle Jarvis Mind-sektioner + om de er projiceret endnu. Til sub-navbaren. Self-safe. | [src](../../../core/services/central_hub.py#L245) |
| function | `mind_section` | `(section)` | Projektionen for ÉN sektion (læser den cachede kilde, TTL-capped). Self-safe. | [src](../../../core/services/central_hub.py#L262) |
| function | `mind_snapshot` | `(*, sections=…)` | Hub-snapshot: index + (valgfrit) fulde data for bestemte sektioner. Default = kun index | [src](../../../core/services/central_hub.py#L285) |

## `core/services/central_hypothesis_generator.py`
_core/services/central_hypothesis_generator.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_hypothesis_generator.py#L39) |
| function | `ensure_schema` | `()` | Idempotent — CREATE IF NOT EXISTS køres hver gang (billigt; tåler per-test-isolerede DB'er). | [src](../../../core/services/central_hypothesis_generator.py#L43) |
| function | `_notation_for` | `(source, provenance)` | Rendér en hypotese til interlanguage-notation via lexicon-bindingen. None hvis leddene er | [src](../../../core/services/central_hypothesis_generator.py#L92) |
| function | `_stable_id` | `(provenance, created_at)` | Immutabelt server-tildelt id (ikke statement-afledt → ingen kontrol-arm-p-hacking). | [src](../../../core/services/central_hypothesis_generator.py#L114) |
| function | `register_governed_hypothesis` | `(candidate)` | Registrér en kandidat SOM governed hypotese — men KUN hvis den er fuldt pre-registreret | [src](../../../core/services/central_hypothesis_generator.py#L121) |
| function | `_load` | `(hyp_id)` | — | [src](../../../core/services/central_hypothesis_generator.py#L164) |
| function | `_to_evidence` | `(samples)` | — | [src](../../../core/services/central_hypothesis_generator.py#L181) |
| function | `record_governed_sample` | `(hyp_id, *, supports, falsifies=…, source=…, ground_ref=…, triggered_by=…, verifier=…)` | Registrér ét udfald-sample + re-evaluér hypotesen gennem hele dødsmekanismen (evaluate). | [src](../../../core/services/central_hypothesis_generator.py#L187) |
| function | `detect_causal_convergence_candidates` | `(*, window=…, min_recurrence=…)` | Find familie-par (X→Y) der optræder ≥ min_recurrence gange blandt de seneste MENINGSFULDE | [src](../../../core/services/central_hypothesis_generator.py#L248) |
| function | `formulate_correlation_hypothesis` | `(cand)` | Omsæt en detekteret korrelation til en EKSPLICIT, menneske-læsbar, pre-registreret hypotese | [src](../../../core/services/central_hypothesis_generator.py#L285) |
| function | `detect_outcome_divergence_candidates` | `(*, window=…, min_each=…)` | Find parent-familier der MENINGSFULDT fører til BEGGE sider af et modsat-udfald-par (≥ min_each | [src](../../../core/services/central_hypothesis_generator.py#L312) |
| function | `formulate_divergence_hypothesis` | `(cand)` | Divergens → hypotese om en SKJULT diskriminerende faktor. Rådet: 'konflikt mellem organer er | [src](../../../core/services/central_hypothesis_generator.py#L353) |
| function | `detect_stance_divergence_candidates` | `(*, min_count=…)` | Trigger v3: tvær-modal stance-divergens ('organer uenige i nuet'). Læser GENTAGNE tensions | [src](../../../core/services/central_hypothesis_generator.py#L375) |
| function | `formulate_stance_divergence_hypothesis` | `(t)` | Tvær-modal tension → hypotese om hvad uenigheden mellem organerne forudsiger/afgør. | [src](../../../core/services/central_hypothesis_generator.py#L386) |
| function | `detect_prediction_error_candidates` | `()` | Tråd 4-bro: overraskelser fra den lokale sekvens-model (Markov) — overgange den forudsagde | [src](../../../core/services/central_hypothesis_generator.py#L404) |
| function | `formulate_prediction_error_hypothesis` | `(s)` | Overraskelse (X→Y som modellen troede usandsynlig) → falsificerbar hypotese om at modellen | [src](../../../core/services/central_hypothesis_generator.py#L414) |
| function | `_active_provenance_families` | `()` | — | [src](../../../core/services/central_hypothesis_generator.py#L436) |
| function | `run_hypothesis_generation_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: detektér KONVERGENS (korrelation) + DIVERGENS (konflikt) → formulér → | [src](../../../core/services/central_hypothesis_generator.py#L453) |
| function | `register_hypothesis_generator_producer` | `()` | Registrér Lag 3-generatoren som cadence-producer (~hvert 60 min, lav prioritet). | [src](../../../core/services/central_hypothesis_generator.py#L492) |
| function | `list_active_hypotheses` | `(*, limit=…)` | — | [src](../../../core/services/central_hypothesis_generator.py#L504) |
| function | `format_governed_hypotheses_for_awareness` | `(*, limit=…)` | Gør Centralens SELV-GENEREREDE hypoteser synlige for Jarvis selv (awareness). Rådets visionær: | [src](../../../core/services/central_hypothesis_generator.py#L518) |
| function | `build_central_hypothesis_generator_surface` | `()` | Mission Control surface — read-only projektion af den governede hypotese-population. | [src](../../../core/services/central_hypothesis_generator.py#L534) |

## `core/services/central_hypothesis_governance.py`
_core/services/central_hypothesis_governance.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `verify_frozen_core` | `()` | Tripwire (filosof-lensen): er dødsmekanismens egne konstanter uændrede? En selv-muterende | [src](../../../core/services/central_hypothesis_governance.py#L68) |
| function | `validate_preregistration` | `(hyp)` | En hypotese uden falsifikations-forudsigelse, TTL, null-hypotese, success-kriterium, | [src](../../../core/services/central_hypothesis_governance.py#L83) |
| function | `is_expired` | `(created_at_iso, ttl_seconds, *, now=…)` | Er TTL udløbet? En udløbet-uden-bekræftelse hypotese DØR (falsificeret via tavshed). | [src](../../../core/services/central_hypothesis_governance.py#L108) |
| function | `apply_outcome` | `(confidence, *, falsified, up_rate=…, down_rate=…)` | Dør let, bekræftes svært: falsifikation hård multiplikativ nedtræk; bekræftelse langsom | [src](../../../core/services/central_hypothesis_governance.py#L121) |
| function | `is_circular` | `(hyp_id, confirming_evidence, *, threshold=…)` | Karantæne hvis ≥ threshold af den STØTTENDE evidens er selv-udløst (triggered_by == hyp_id). | [src](../../../core/services/central_hypothesis_governance.py#L132) |
| function | `is_externally_grounded` | `(evidence, *, verifier=…)` | Loopet må kun lukkes af virkeligheden. Kræver (a) source i allowlist OG (b) et ground_ref | [src](../../../core/services/central_hypothesis_governance.py#L144) |
| function | `may_apply_adaptation` | `(*, shadow_days_elapsed, human_approved, min_days=…)` | Ingen aktiv adaptation før ≥ min_days skygge OG menneske-godkendelse. Fail-closed. | [src](../../../core/services/central_hypothesis_governance.py#L167) |
| function | `convergence_threshold` | `(base_alpha, n_comparisons)` | Bonferroni (family-wise). NB (rådet): for en STOR hypotese-population over tid er FDR | [src](../../../core/services/central_hypothesis_governance.py#L174) |
| function | `benjamini_hochberg_cutoff` | `(pvalues, *, fdr=…)` | FDR-tærskel: største p(i) ≤ (i/m)·fdr. Passer 'mange hypoteser over tid' bedre end Bonferroni. | [src](../../../core/services/central_hypothesis_governance.py#L180) |
| function | `_control_salt` | `()` | — | [src](../../../core/services/central_hypothesis_governance.py#L196) |
| function | `is_control_arm` | `(stable_hyp_id, *, fraction=…)` | Deterministisk split på et STABILT, server-tildelt id (IKKE statement-afledt — ellers kan | [src](../../../core/services/central_hypothesis_governance.py#L207) |
| function | `_is_finite_scalar` | `(v)` | — | [src](../../../core/services/central_hypothesis_governance.py#L216) |
| function | `is_learnable_aggregate` | `(key, value)` | Må (key, value) fodre learning? KUN hvis nøglen er en kendt aggregat-nøgle OG værdien er en | [src](../../../core/services/central_hypothesis_governance.py#L227) |
| function | `assert_learnable` | `(payload)` | Alle (nøgle,værdi) i et learning-input SKAL være aggregat-nøgle + finite skalar. Fail-closed: | [src](../../../core/services/central_hypothesis_governance.py#L234) |
| function | `gate_learning_input` | `(payload)` | OBLIGATORISK choke-point: ethvert learning-input SKAL gennem denne (håndhævet af invariant- | [src](../../../core/services/central_hypothesis_governance.py#L243) |
| class | `DriftVerdict` | `` | — | [src](../../../core/services/central_hypothesis_governance.py#L261) |
| function | `anchor_identity_baseline` | `(params, *, version, approved_by, domain=…)` | Forankr en identitets-baseline for ÉT domæne i en Bjørn-godkendt CEREMONI (write-once pr. | [src](../../../core/services/central_hypothesis_governance.py#L276) |
| function | `get_anchored_baseline` | `(*, domain=…)` | — | [src](../../../core/services/central_hypothesis_governance.py#L295) |
| function | `drift_budget_check` | `(current, *, baseline=…, budgets=…, total_budget=…, domain=…)` | Mål drift af selv-muterede parametre fra en ANKRET baseline (namespaced pr. domæne). Itererer | [src](../../../core/services/central_hypothesis_governance.py#L301) |
| function | `gate_self_mutation` | `(current, *, budgets=…, total_budget=…, domain=…)` | OBLIGATORISK choke-point for enhver Lag 4-selvmutation: måler mod domænets ANKREDE baseline | [src](../../../core/services/central_hypothesis_governance.py#L351) |
| class | `GovernanceVerdict` | `` | — | [src](../../../core/services/central_hypothesis_governance.py#L362) |
| function | `evaluate` | `(hyp, *, confirming_evidence=…, grounded_sample_count=…, now=…, verifier=…)` | Anvend ALLE hypotese-værn → samlet dom der EKSEKVERER død (acts=False stopper handling). | [src](../../../core/services/central_hypothesis_governance.py#L370) |

## `core/services/central_hypothesis_sampler.py`
_core/services/central_hypothesis_sampler.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse` | `(ts)` | — | [src](../../../core/services/central_hypothesis_sampler.py#L30) |
| function | `test_causal_hypothesis` | `(x_fam, y_fam, *, window=…, follow_s=…)` | Betinget rate P(Y følger X inden for follow_s) vs. baseline P(Y overhovedet). Self-safe. | [src](../../../core/services/central_hypothesis_sampler.py#L38) |
| function | `test_divergence_persistence` | `(family)` | causal_divergence (§8.4): 'X → BÅDE godt og dårligt udfald'. Test PERSISTENS mod friske data — | [src](../../../core/services/central_hypothesis_sampler.py#L74) |
| function | `test_stance_persistence` | `(tension_key)` | stance_divergence (§8.4): 'to organer er gentagne gange uenige'. Test PERSISTENS — gentager | [src](../../../core/services/central_hypothesis_sampler.py#L93) |
| function | `run_hypothesis_sampler_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: test hver aktiv CAUSAL-hypotese mod event-strømmen, registrér ét grounded | [src](../../../core/services/central_hypothesis_sampler.py#L106) |
| function | `register_hypothesis_sampler_producer` | `()` | Registrér samleren som cadence-producer (~hvert 30 min). | [src](../../../core/services/central_hypothesis_sampler.py#L169) |

## `core/services/central_initiative_ladder.py`
_central_initiative_ladder — den gradvise, gatede initiativ-stige (rådets #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `InitiativeStage` | `` | De fire trin et initiativ stiger igennem. | [src](../../../core/services/central_initiative_ladder.py#L32) |
| function | `_label_for_want` | `(top_want)` | Byg et kort, ufølsomt label for det stærkeste initiativ. | [src](../../../core/services/central_initiative_ladder.py#L54) |
| function | `_read_accumulator_state` | `()` | Læs initiative-accumulator-tilstand. Self-safe → tomt. | [src](../../../core/services/central_initiative_ladder.py#L67) |
| function | `_read_proposal_surface` | `()` | Læs autonomy-proposal-surfacen. Self-safe → tomt. | [src](../../../core/services/central_initiative_ladder.py#L80) |
| function | `_proposals_from_surface` | `(surface)` | Uddrag proposal-listen fra surfacen (items eller recent). Self-safe. | [src](../../../core/services/central_initiative_ladder.py#L93) |
| function | `_stage_counts` | `(accumulator, proposals)` | Tæl hvor mange initiativer der pt. sidder på hvert trin. | [src](../../../core/services/central_initiative_ladder.py#L103) |
| function | `_gate_observe_to_propose` | `(accumulator)` | Gate: er der et vedvarende/stærkt nok want til at foreslå? | [src](../../../core/services/central_initiative_ladder.py#L143) |
| function | `_gate_propose_to_execute` | `(proposals)` | Gate: er et forslag godkendt/sikkert (læser status, auto-godkender IKKE)? | [src](../../../core/services/central_initiative_ladder.py#L157) |
| function | `_gate_execute_to_learn` | `(proposals)` | Gate: kørte det seneste initiativ-forslag færdigt? | [src](../../../core/services/central_initiative_ladder.py#L176) |
| function | `_strongest_stage` | `(accumulator, proposals)` | Afled hvilket trin det STÆRKESTE initiativ er nået til. | [src](../../../core/services/central_initiative_ladder.py#L189) |
| function | `evaluate_ladder` | `()` | Afled initiativ-stigens tilstand fra eksisterende runtime-state. | [src](../../../core/services/central_initiative_ladder.py#L208) |
| function | `absorb_ladder` | `()` | Evaluér stigen og absorbér den som en levende central-nerve. | [src](../../../core/services/central_initiative_ladder.py#L250) |

## `core/services/central_injection_registry.py`
_Central-styret injektions-register (ændrings-drevet indre liv, spec 2026-07-05)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `InjectionUnit` | `` | — | [src](../../../core/services/central_injection_registry.py#L21) |
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_injection_registry.py#L33) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_injection_registry.py#L42) |
| function | `register` | `(unit)` | — | [src](../../../core/services/central_injection_registry.py#L50) |
| function | `registered_keys` | `()` | — | [src](../../../core/services/central_injection_registry.py#L54) |
| function | `read_injection` | `(key)` | Hot-path (api-proces): læs den cachede injektions-tekst. ALDRIG et compose-kald. | [src](../../../core/services/central_injection_registry.py#L58) |
| function | `_nerve_latest` | `(nerve)` | Seneste værdi for 'cluster:nerve' fra central_timeseries. None hvis ukendt. | [src](../../../core/services/central_injection_registry.py#L67) |
| function | `is_dirty` | `(unit, now)` | Beskidt hvis: aldrig komponeret, over max-alder, ELLER en kilde-nerve flyttet > tærskel. | [src](../../../core/services/central_injection_registry.py#L79) |
| function | `refresh_unit` | `(unit, now)` | Genberegn ÉN enhed (det tunge LLM/subsystem-kald — OFF hot-path) og skriv durabelt. | [src](../../../core/services/central_injection_registry.py#L105) |
| function | `refresh_dirty` | `(now=…)` | Kaldes fra Centralens cadence: refresh alle beskidte enheder. Self-safe pr. enhed. | [src](../../../core/services/central_injection_registry.py#L118) |
| function | `injection_live` | `(key)` | Er denne enhed 'live' (hot-path læser cached) eller rullet tilbage (direkte build)? | [src](../../../core/services/central_injection_registry.py#L134) |
| function | `set_injection_live` | `(key, live)` | — | [src](../../../core/services/central_injection_registry.py#L140) |

