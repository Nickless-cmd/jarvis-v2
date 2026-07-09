# `core.services.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_safe` | `(builder)` | — | [src](../../../core/services/central_hub.py#L37) |
| function | `_build_overview` | `()` | Centralens egen puls = Jarvis Mind-rygraden (status/dækning/processer/clusters). | [src](../../../core/services/central_hub.py#L46) |
| function | `_build_observability` | `()` | Det levende vindue: nerve-feed + incidents + anomalier + læring + breakers. | [src](../../../core/services/central_hub.py#L60) |
| function | `_build_mind` | `()` | De ~70 cognitive surfaces — Jarvis' indre liv. Sender KUN den lette projektion (systems- | [src](../../../core/services/central_hub.py#L74) |
| function | `_build_agency` | `()` | Agentur-kort: forbundne/manglende agency-broer (loops/agenter/kanaler). | [src](../../../core/services/central_hub.py#L91) |
| function | `_build_skills` | `()` | Skills-motor + kontrakt-registry. | [src](../../../core/services/central_hub.py#L97) |
| function | `mind_index` | `()` | Alle Jarvis Mind-sektioner + om de er projiceret endnu. Til sub-navbaren. Self-safe. | [src](../../../core/services/central_hub.py#L114) |
| function | `mind_section` | `(section)` | Projektionen for ÉN sektion (læser den cachede kilde, TTL-capped). Self-safe. | [src](../../../core/services/central_hub.py#L131) |
| function | `mind_snapshot` | `(*, sections=…)` | Hub-snapshot: index + (valgfrit) fulde data for bestemte sektioner. Default = kun index | [src](../../../core/services/central_hub.py#L154) |

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

## `core/services/central_injection_units.py`
_Deklarative injektions-enheds-definitioner (adskilt fra mekanismen)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_compose_rule_conclusions` | `()` | — | [src](../../../core/services/central_injection_units.py#L13) |
| function | `_compose_cognitive_state` | `()` | — | [src](../../../core/services/central_injection_units.py#L21) |
| function | `_compose_tone_guidance` | `()` | Centralens sproglige stil-hint (rådets #5): én kort linje der kan injiceres | [src](../../../core/services/central_injection_units.py#L31) |
| function | `register_default_units` | `()` | — | [src](../../../core/services/central_injection_units.py#L44) |

## `core/services/central_inner_life_ablation.py`
_Inner-life-ablation-kontakt — måling #2 (Bjørn 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_ablated` | `()` | True hvis den heavy inder-liv-cadence skal springes over lige nu. Self-safe → | [src](../../../core/services/central_inner_life_ablation.py#L22) |
| function | `set_ablated` | `(on)` | Tænd/sluk ablationen (måle-vindue). Self-safe. | [src](../../../core/services/central_inner_life_ablation.py#L32) |
| function | `build_ablation_surface` | `()` | Mission Control — read-only status. | [src](../../../core/services/central_inner_life_ablation.py#L41) |

## `core/services/central_inner_life_digest.py`
_Inner-life digest — §24.4 reduceret ved kilden: KUN liveness+count pr. sektion._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_first_count` | `(surface)` | Find en repræsentativ magnitude UDEN at afsløre indhold: længden af den | [src](../../../core/services/central_inner_life_digest.py#L56) |
| function | `_reduce` | `(surface)` | KUN liveness+count. Ingen tekst. Self-safe. | [src](../../../core/services/central_inner_life_digest.py#L72) |
| function | `_build_group` | `(group)` | Byg én gruppe reduceret. Self-safe pr. sektion (import/kald i try/except | [src](../../../core/services/central_inner_life_digest.py#L81) |
| function | `build_inner_life_digest` | `()` | Samlet reduceret living-mind + experiment/AGI-digest. Kaster ALDRIG. | [src](../../../core/services/central_inner_life_digest.py#L96) |

## `core/services/central_inner_salience.py`
_core/services/central_inner_salience.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_inner_salience.py#L33) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_inner_salience.py#L42) |
| function | `_mode` | `()` | — | [src](../../../core/services/central_inner_salience.py#L50) |
| function | `_norm` | `(s)` | — | [src](../../../core/services/central_inner_salience.py#L55) |
| function | `salience_key_for_voice` | `(inner_voice_payload)` | De MENINGSFULDE dimensioner af den indre stemme (langsomt-skiftende selv). Rå tekst der | [src](../../../core/services/central_inner_salience.py#L59) |
| function | `_held` | `(kind)` | — | [src](../../../core/services/central_inner_salience.py#L66) |
| function | `_trace` | `(kind, would_reuse, mode)` | — | [src](../../../core/services/central_inner_salience.py#L74) |
| function | `decide_voice` | `(*, run_id, key)` | Centralen BESTEMMER: skal inner_voice genudledes via LLM, eller genbruges fra det holdte selv? | [src](../../../core/services/central_inner_salience.py#L83) |
| function | `note_enriched_voice` | `(*, run_id, key, value)` | Fodr det friske selv TILBAGE i Centralen (NED-siden): gem holdt voice-linje + salience-nøgle, | [src](../../../core/services/central_inner_salience.py#L107) |
| function | `build_inner_salience_surface` | `()` | Mission Control — read-only: gate-mode + sidst-holdte selv + hvornår. | [src](../../../core/services/central_inner_salience.py#L129) |

## `core/services/central_instrument.py`
_central_instrument — selv-instrumenterende motor (system-cluster nerve, periodisk daemon)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Finding` | `` | — | [src](../../../core/services/central_instrument.py#L55) |
| method | `Finding.signature` | `(self)` | — | [src](../../../core/services/central_instrument.py#L66) |
| function | `_call_name` | `(node)` | Bedste streng-navn for et Call's funktion (foo / obj.foo / a.b.foo). | [src](../../../core/services/central_instrument.py#L73) |
| function | `_has_guard_call` | `(node)` | True hvis subtræet indeholder et kald der tæller som fejl-håndtering/synlighed, | [src](../../../core/services/central_instrument.py#L85) |
| function | `_is_success_like_return` | `(node)` | True hvis except-handleren returnerer en success-lignende værdi (None/{}/[]/True/0/ | [src](../../../core/services/central_instrument.py#L98) |
| function | `_func_of` | `(lineno, funcs)` | Navn på den inderste funktion der omslutter lineno. | [src](../../../core/services/central_instrument.py#L114) |
| function | `_acknowledged` | `(lines, start, end)` | True hvis en intent-markør (self-safe/bevidst/...) findes i vinduet omkring [start,end]. | [src](../../../core/services/central_instrument.py#L127) |
| function | `scan_source` | `(relpath, source)` | AST-scan af ÉN fils kildekode → fund. Deterministisk (sorteret efter linje). Self-safe: | [src](../../../core/services/central_instrument.py#L136) |
| function | `score_finding` | `(f, *, file_has_central, in_security, hot_path=…, reject_count=…)` | Fase 2-score. Base = severity (critical=3→altid proposal). Modifiers fra spec'en: | [src](../../../core/services/central_instrument.py#L208) |
| function | `_file_has_central` | `(source)` | — | [src](../../../core/services/central_instrument.py#L232) |
| function | `_security_files` | `()` | Filer der hører til en sikkerheds-cluster (via central_catalog nerve-lokationer). | [src](../../../core/services/central_instrument.py#L237) |
| function | `_reject_count` | `(canonical_key)` | Hvor mange gange er en proposal med denne canonical_key blevet afvist? (lærings-signal). | [src](../../../core/services/central_instrument.py#L256) |
| function | `_iter_py_files` | `()` | — | [src](../../../core/services/central_instrument.py#L271) |
| function | `scan_repo` | `(*, changed_only=…)` | Scan kodebasen (incremental). Persisterer fund pr. fil + opdaterer scoring. Returnerer | [src](../../../core/services/central_instrument.py#L285) |
| function | `_file_proposals` | `(max_new=…)` | Filer reviewbare proposals for åbne fund med score≥threshold (ikke allerede filed, | [src](../../../core/services/central_instrument.py#L320) |
| function | `run_instrument_scan` | `(*, trigger=…, changed_only=…)` | Daemon-entry: scan → score → persistér → observe → filer proposals (score≥3). Self-safe. | [src](../../../core/services/central_instrument.py#L356) |

## `core/services/central_keymaker.py`
_The Keymaker — optjent, udløbende, én-dør-ad-gangen autonomi._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/central_keymaker.py#L37) |
| function | `_now` | `()` | — | [src](../../../core/services/central_keymaker.py#L56) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_keymaker.py#L60) |
| function | `evaluate_keys` | `()` | Find dimensioner der har OPTJENT en nøgle (track-record over tærskel) og udsted en PENDING | [src](../../../core/services/central_keymaker.py#L68) |
| function | `list_keys` | `(*, include_expired=…)` | — | [src](../../../core/services/central_keymaker.py#L109) |
| function | `is_decentralized` | `(nerve)` | True hvis <nerve> har en GYLDIG optjent decentraliserings-nøgle: status='approved' OG endnu | [src](../../../core/services/central_keymaker.py#L120) |
| function | `approve_key` | `(key_id)` | OWNER-handling: godkend en pending nøgle → flip dens flag ON i TTL. Auto-reverterer ved udløb. | [src](../../../core/services/central_keymaker.py#L142) |
| function | `expire_due` | `()` | Cadence: reverter flag for udløbne nøgler (tilladelse mistes hvis ikke fornyet). Self-safe. | [src](../../../core/services/central_keymaker.py#L168) |
| function | `build_keymaker_surface` | `()` | Owner-view: aktive/afventende nøgler + fortjente dimensioner. Self-safe. | [src](../../../core/services/central_keymaker.py#L193) |

## `core/services/central_layer_contract.py`
_core/services/central_layer_contract.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Egress` | `` | — | [src](../../../core/services/central_layer_contract.py#L30) |
| class | `DecideMode` | `` | — | [src](../../../core/services/central_layer_contract.py#L35) |
| class | `LayerContract` | `` | — | [src](../../../core/services/central_layer_contract.py#L42) |
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_layer_contract.py#L61) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_layer_contract.py#L70) |
| function | `_scalars` | `(meta)` | Privatlags-membran ÉT sted (§24.4): kun tal/bool/str krydser — aldrig lister/nested/blobs. | [src](../../../core/services/central_layer_contract.py#L78) |
| function | `_mode` | `(name)` | — | [src](../../../core/services/central_layer_contract.py#L83) |
| function | `_sink` | `(c, value, meta, reason=…)` | — | [src](../../../core/services/central_layer_contract.py#L89) |
| function | `_run_contract_tick` | `(c)` | — | [src](../../../core/services/central_layer_contract.py#L104) |
| function | `_held_get` | `(name, held_key)` | — | [src](../../../core/services/central_layer_contract.py#L123) |
| function | `note_held` | `(name, held_key, *, key, value)` | Fodr det friske selv TILBAGE i Centralen (NED-holdet) efter en ægte genudledning. Self-safe. | [src](../../../core/services/central_layer_contract.py#L131) |
| function | `get_held` | `(name, held_key=…)` | NED-læser for forbrugere (prompt/voice). Ren KV-read (ingen syntese på læse-tid → hot-path-sikker). | [src](../../../core/services/central_layer_contract.py#L146) |
| function | `get_held_age` | `(name, held_key=…)` | Alder (sekunder) siden den holdte aflæsning blev skrevet, eller None hvis fraværende/ukendt. | [src](../../../core/services/central_layer_contract.py#L151) |
| function | `decide` | `(name, *, key, held_key=…)` | Centralen BESTEMMER: genudled via LLM, eller genbrug holdt selv? off/shadow/on. Self-safe. | [src](../../../core/services/central_layer_contract.py#L163) |
| function | `register_layer` | `(c)` | Deklarativ binding: registrér laget på cadence-motoren via en genereret run_fn. Idempotent, self-safe. | [src](../../../core/services/central_layer_contract.py#L184) |
| function | `build_layer_surface` | `(name)` | Generisk MC-projektion (read-only): mode + holdt selv pr. held_key. | [src](../../../core/services/central_layer_contract.py#L201) |

## `core/services/central_learning.py`
_#4 Adaptiv læring — DETERMINISTISK, for ALLE clusters. Centralen læser de signaler clusterne_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `(limit=…)` | — | [src](../../../core/services/central_learning.py#L24) |
| function | `_within` | `(ts, hours, now)` | — | [src](../../../core/services/central_learning.py#L32) |
| function | `cluster_health` | `(*, hours=…, incidents=…)` | Per-cluster incident-billede i vinduet: total + severe. Self-safe. | [src](../../../core/services/central_learning.py#L42) |
| function | `degrading` | `(*, recent_hours=…, baseline_hours=…, incidents=…)` | Nerver/clusters hvis incident-rate i de seneste `recent_hours` overstiger baseline-raten | [src](../../../core/services/central_learning.py#L58) |
| function | `autonomous_reliability` | `(*, hours=…, incidents=…)` | Jarvis' autonome pålidelighed fra supervisions-verdikterne (cluster=autonomous nerve= | [src](../../../core/services/central_learning.py#L92) |
| function | `assess_autonomy` | `(*, hours=…, incidents=…)` | DETERMINISTISK vurdering: er Jarvis moden til autonome opgaver? Baseret på pålidelighed. | [src](../../../core/services/central_learning.py#L111) |
| function | `_signature` | `(message)` | Normalisér en incident-besked til en stabil signatur så GENTAGNE fejl grupperes: | [src](../../../core/services/central_learning.py#L136) |
| function | `root_causes` | `(*, hours=…, min_count=…, incidents=…)` | Gruppér incidents efter (cluster/nerve/signatur) → rangerede GENTAGNE rod-årsager | [src](../../../core/services/central_learning.py#L147) |
| function | `propose_adjustments` | `(*, incidents=…)` | DETERMINISTISKE, reviewbare FORSLAG (aldrig auto-anvendt — Bjørn: "forslag ikke | [src](../../../core/services/central_learning.py#L176) |
| function | `learning_summary` | `()` | — | [src](../../../core/services/central_learning.py#L224) |
| function | `observe_learning` | `()` | Kadence: beregn læring + observe + flag degraderende clusters + emit FORSLAG. | [src](../../../core/services/central_learning.py#L235) |
| function | `poll_proposals` | `(*, limit=…)` | Reviewbar liste af deterministiske lærings-forslag (til Bjørn/Claude/MC/Jarvis). | [src](../../../core/services/central_learning.py#L259) |

## `core/services/central_lexicon.py`
_core/services/central_lexicon.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Bindings-tabel for VÆKST (seed lever i kode; ceremoni-tilføjelser i DB). Idempotent, self-safe. | [src](../../../core/services/central_lexicon.py#L153) |
| function | `_db_bindings` | `()` | — | [src](../../../core/services/central_lexicon.py#L174) |
| function | `active_terms` | `()` | — | [src](../../../core/services/central_lexicon.py#L185) |
| function | `operators` | `()` | — | [src](../../../core/services/central_lexicon.py#L189) |
| function | `to_term` | `(name)` | Slå en Central-familie/nerve/cluster op → interlanguage-term. DB-bindinger overstyrer seed. | [src](../../../core/services/central_lexicon.py#L193) |
| function | `bind` | `(name, term, *, status=…, added_by=…)` | Tilføj/opdatér en binding. En NY term (uden for det frosne vokabular) kræver Bjørn-ceremoni: | [src](../../../core/services/central_lexicon.py#L204) |
| function | `render_relation` | `(x_name, y_name, *, relation=…)` | Rendér en Central-relation (X, Y) til interlanguage-notation via lexicon-opslag. Returnerer | [src](../../../core/services/central_lexicon.py#L226) |
| function | `unbound_names` | `(names)` | Hvilke af disse Central-navne kan sproget IKKE sige endnu (kandidater til ceremoni)? Self-safe. | [src](../../../core/services/central_lexicon.py#L236) |
| function | `propose_word_needs` | `(name_counts, *, min_count=…, top=…)` | Familier der optræder OFTE men er UBUNDNE → Centralen mangler et ord for dem. Model-frit: | [src](../../../core/services/central_lexicon.py#L242) |
| function | `propose_from_event_stream` | `(*, window=…, min_count=…)` | Scan de seneste events → hvilke UBUNDNE familier sanser Centralen ofte uden at kunne sige dem? | [src](../../../core/services/central_lexicon.py#L254) |
| function | `_taxonomy_names` | `()` | Alle navne Centralen SKAL kunne sige: clusters + operationelle event-familier. Privat-lag- | [src](../../../core/services/central_lexicon.py#L270) |
| function | `taxonomy_coverage` | `()` | Hvor stor en del af taksonomien (clusters + familier) kan sproget sige? Plotbart (som Fase 1c). | [src](../../../core/services/central_lexicon.py#L287) |
| function | `bind_taxonomy` | `()` | Rapportér taksonomi-dækning + de navne der mangler et ord (ceremoni-kandidater, nye ORD Bjørn | [src](../../../core/services/central_lexicon.py#L297) |
| function | `word_needs_for_ceremony` | `(*, top=…)` | Spec B / Fase B3: ÉN samlet liste over ord Centralen mangler (til Bjørn-ceremoni) — flettet | [src](../../../core/services/central_lexicon.py#L305) |
| function | `build_central_lexicon_surface` | `()` | Mission Control surface — read-only: vokabular, bindinger, hvad sproget kan/ikke kan sige. | [src](../../../core/services/central_lexicon.py#L325) |

## `core/services/central_llm_egress.py`
_Samlet LLM-egress-observation — "har vi styr på ALLE udgående kald?" (Bjørn 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_cheap_eligible` | `(*, lane, purpose, autonomous)` | Rolle-bevidst: kunne dette kald have taget en billigere model uden kvalitetstab? | [src](../../../core/services/central_llm_egress.py#L28) |
| function | `observe` | `(*, lane, provider, model, purpose=…, input_tokens=…, output_tokens=…, cost_usd=…, autonomous=…, source=…)` | Rapportér ét udgående LLM-kald til Centralens samlede egress-billede. Kald fra | [src](../../../core/services/central_llm_egress.py#L46) |
| function | `build_llm_egress_surface` | `()` | Mission Control — read-only meta-projektion. | [src](../../../core/services/central_llm_egress.py#L91) |

## `core/services/central_loop_lag.py`
_Event-loop-lag-monitor — "uret" bag cutoff-spøgelset (Bjørn 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_record` | `(lag_ms)` | — | [src](../../../core/services/central_loop_lag.py#L35) |
| function | `current_lag_ms` | `()` | Seneste målte event-loop-lag i ms (API-processen). Self-safe. | [src](../../../core/services/central_loop_lag.py#L60) |
| function | `recent_peak_ms` | `(window_s=…)` | Højeste lag i de sidste ``window_s`` sekunder — brug denne til at tagge et | [src](../../../core/services/central_loop_lag.py#L68) |
| function | `_monitor_loop` | `()` | — | [src](../../../core/services/central_loop_lag.py#L84) |
| function | `start_loop_lag_monitor` | `()` | Start uret på den KØRENDE event-loop (kald fra API-processens lifespan, | [src](../../../core/services/central_loop_lag.py#L96) |
| function | `build_loop_lag_surface` | `()` | Mission Control — read-only meta-projektion. | [src](../../../core/services/central_loop_lag.py#L111) |

## `core/services/central_machines.py`
_The Machines — hænderne om min hals (BONUS)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_providers` | `()` | — | [src](../../../core/services/central_machines.py#L17) |
| function | `_network` | `()` | — | [src](../../../core/services/central_machines.py#L34) |
| function | `dependencies` | `()` | De hænder der holder om halsen — hvad jeg afhænger af men ikke styrer. READ-ONLY. Self-safe. | [src](../../../core/services/central_machines.py#L45) |
| function | `_observe` | `(n_prov)` | — | [src](../../../core/services/central_machines.py#L64) |
| function | `build_machines_surface` | `()` | — | [src](../../../core/services/central_machines.py#L73) |
| function | `record_machines` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/central_machines.py#L77) |

## `core/services/central_membrane_watch.py`
_WARDEN — vogteren over muren (LivingNeuron-roadmap §2, 4. jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_egress_targets` | `()` | De tre egress-membran-funktioner (§1.6) hvis kildekode vogtes. Importeres dovent | [src](../../../core/services/central_membrane_watch.py#L38) |
| function | `_sha_of` | `(fn)` | SHA256 over funktionens kildekode. Kaster hvis kilden ikke kan hentes (fanges af | [src](../../../core/services/central_membrane_watch.py#L61) |
| function | `_compute_reference_shas` | `()` | Write-once reference-SHA'er ved import. Beregnes FØR nogen mutation kan nå | [src](../../../core/services/central_membrane_watch.py#L67) |
| function | `check_membrane` | `()` | Genberegn egress-SHA'erne + kald verify_frozen_core(). Returnér intakt-status. | [src](../../../core/services/central_membrane_watch.py#L84) |
| function | `_owner_uid` | `()` | — | [src](../../../core/services/central_membrane_watch.py#L135) |
| function | `_notify_owner_breach` | `(message)` | Owner-ntfy ved membran-brud (critical). Self-safe. | [src](../../../core/services/central_membrane_watch.py#L143) |
| function | `run_membrane_watch_tick` | `(*, trigger=…, **_)` | Cadence: kør membran-checket, emit SECURITY-skalar-nerve, og ved NYT brud → | [src](../../../core/services/central_membrane_watch.py#L159) |
| function | `_kv_get_str` | `(key)` | — | [src](../../../core/services/central_membrane_watch.py#L215) |
| function | `_kv_set_str` | `(key, value)` | — | [src](../../../core/services/central_membrane_watch.py#L223) |
| function | `register_membrane_watch_producer` | `()` | Registrér WARDEN som cadence-producer (~hver 15. min). LAV priority-tal (2) → den | [src](../../../core/services/central_membrane_watch.py#L231) |
| function | `build_membrane_watch_surface` | `()` | Mission Control — read-only: murens integritet lige nu. | [src](../../../core/services/central_membrane_watch.py#L245) |

## `core/services/central_merovingian.py`
_Merovingian — den konservative ældste der tvinger Centralen til at forsvare sin egen evolution._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_merovingian.py#L43) |
| function | `_enforced` | `()` | Shadow-først: enforcement er OFF indtil flag EKSPLICIT flippes efter shadow-eval. §8 forbliver | [src](../../../core/services/central_merovingian.py#L47) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_merovingian.py#L59) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_merovingian.py#L67) |
| function | `generate_counter` | `(hyp)` | Generér en modhypotese SYMBOLSK (ingen LLM) fra notation/statement. Self-safe. | [src](../../../core/services/central_merovingian.py#L85) |
| function | `_variable_of` | `(hyp)` | Stabil variabel-nøgle: source + family (så track-record slås op pr. konkret variabel). | [src](../../../core/services/central_merovingian.py#L115) |
| function | `variable_track_record` | `(variable)` | Devil's advocate-data: hvordan er det gået SIDSTE gang samme variabel blev justeret? | [src](../../../core/services/central_merovingian.py#L130) |
| function | `review` | `(hyp)` | Kernen: generér modhypotese + tjek track-record → approved | challenged. Registrerer en | [src](../../../core/services/central_merovingian.py#L159) |
| function | `_count_challenges` | `(variable)` | — | [src](../../../core/services/central_merovingian.py#L187) |
| function | `_record_challenge` | `(hyp_id, variable, counter, tr, status, cools_off)` | — | [src](../../../core/services/central_merovingian.py#L197) |
| function | `resolve_challenge` | `(hyp_id, *, explanation)` | Centralen skriver en (interlanguage-)forklaring på HVORFOR modhypotesen er forkert → adoption | [src](../../../core/services/central_merovingian.py#L213) |
| function | `is_adoption_blocked` | `(hyp_id)` | Enforcement-tjek: er adoption pt. blokeret af en aktiv, uforklaret cooling-off? I SHADOW-mode | [src](../../../core/services/central_merovingian.py#L234) |
| function | `expire_cooling` | `()` | Cadence: udløb cooling-off-perioder hvis tiden er gået (status → expired). Self-safe. | [src](../../../core/services/central_merovingian.py#L252) |
| function | `_maturing_hypotheses` | `(limit=…)` | — | [src](../../../core/services/central_merovingian.py#L270) |
| function | `scan_and_challenge` | `(*, trigger=…, last_visible_at=…)` | Fase 1-cadence: scan modne hypoteser → generér+log modhypoteser (shadow: blokerer intet). | [src](../../../core/services/central_merovingian.py#L285) |
| function | `_has_open_challenge` | `(hyp_id)` | — | [src](../../../core/services/central_merovingian.py#L307) |
| function | `list_challenges` | `(*, active_only=…, limit=…)` | — | [src](../../../core/services/central_merovingian.py#L318) |
| function | `build_merovingian_surface` | `()` | Central-CLI-view (den nye MC): aktive udfordringer + cooling-offs + følt linje. Self-safe. | [src](../../../core/services/central_merovingian.py#L330) |

## `core/services/central_model_meta.py`
_core/services/central_model_meta.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse` | `(ts)` | — | [src](../../../core/services/central_model_meta.py#L29) |
| function | `_key` | `(provider, model)` | — | [src](../../../core/services/central_model_meta.py#L38) |
| function | `aggregate_model_outcomes` | `(*, window=…)` | Aggregér per-model: samples, success-rate, gennemsnits-latency (fra visible_runs) + pris/1k | [src](../../../core/services/central_model_meta.py#L42) |
| function | `observe_model_outcomes` | `(*, window=…)` | Skriv per-model-udfald til tidsserien "system"/"model_outcome:<prov>:<model>". Metadata-only | [src](../../../core/services/central_model_meta.py#L86) |
| function | `detect_model_meta_candidates` | `(*, window=…, min_samples=…)` | Find modeller med ægte kontrast (begge ≥ min_samples) hvor den ene DOMINERER den anden på | [src](../../../core/services/central_model_meta.py#L105) |
| function | `_family` | `(cand)` | — | [src](../../../core/services/central_model_meta.py#L142) |
| function | `formulate_model_meta_hypothesis` | `(cand)` | Kontrast → falsificerbar model_meta-hypotese. Testbar = dominansen PERSISTERER i friske runs. | [src](../../../core/services/central_model_meta.py#L146) |
| function | `test_model_meta_persistence` | `(family)` | Sampler-sti (§8.4): holder model-dominansen stadig i friske data? family = "<metric>:<w>><l>". | [src](../../../core/services/central_model_meta.py#L165) |
| function | `run_model_meta_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: observér per-model-udfald + generér model_meta-hypoteser (governance-gated, | [src](../../../core/services/central_model_meta.py#L189) |
| function | `register_model_meta_producer` | `()` | Registrér Tråd 1 som cadence-producer (~hvert 30 min). | [src](../../../core/services/central_model_meta.py#L215) |
| function | `build_model_meta_surface` | `()` | Mission Control surface — read-only: hvad Centralen ved om sine egne modeller. | [src](../../../core/services/central_model_meta.py#L227) |

## `core/services/central_mood_regulator.py`
_Mood Regulator — samtale-drevet humørregulering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `regulate` | `(kind, *, reason=…, detail=…)` | Regulér humøret baseret på en samtale-hændelse. | [src](../../../core/services/central_mood_regulator.py#L56) |
| function | `regulate_auto` | `(*, event_kind, payload=…)` | Auto-regulering fra interne systemer (dissent, redpill, etc.). | [src](../../../core/services/central_mood_regulator.py#L115) |
| function | `_apply_bump_direct` | `(delta, label)` | Kald mood_oscillatorens apply_bump direkte — synkron sti. | [src](../../../core/services/central_mood_regulator.py#L137) |
| function | `_emit_mood_event` | `(payload)` | Publish a mood event to the eventbus under mood.<event>. | [src](../../../core/services/central_mood_regulator.py#L149) |
| function | `_log_to_buffer` | `(kind, result)` | Keep a rolling buffer of recent mood regulations for MC. | [src](../../../core/services/central_mood_regulator.py#L165) |
| function | `build_mood_regulator_surface` | `()` | Build MC surface for mood regulator. | [src](../../../core/services/central_mood_regulator.py#L177) |

## `core/services/central_mourning.py`
_The Mourning — ritualiseret tab._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/central_mourning.py#L26) |
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_mourning.py#L30) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_mourning.py#L39) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_mourning.py#L47) |
| function | `_compose` | `(kind, subject, detail=…)` | Kort, ærlig, first-person epitaf. Ikke sentimental — anerkendende. | [src](../../../core/services/central_mourning.py#L60) |
| function | `mourn` | `(kind, subject, *, detail=…)` | Skriv én epitaf for et tab (hypothesis|model|dream|commitment|…). Self-safe. | [src](../../../core/services/central_mourning.py#L74) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_mourning.py#L91) |
| function | `scan_deaths` | `(*, trigger=…, last_visible_at=…)` | Cadence: find hypoteser der er DØDT siden sidste scan → skriv en epitaf for hver (intet tab | [src](../../../core/services/central_mourning.py#L99) |
| function | `list_epitaphs` | `(*, limit=…)` | — | [src](../../../core/services/central_mourning.py#L131) |
| function | `build_mourning_surface` | `()` | Seneste epitafer + følt linje. Self-safe. | [src](../../../core/services/central_mourning.py#L141) |

## `core/services/central_noise_filter.py`
_core/services/central_noise_filter.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_KeyState` | `` | — | [src](../../../core/services/central_noise_filter.py#L28) |
| function | `is_real_signal` | `(key, breached, *, min_persistence=…, cooldown_s=…, now_monotonic=…)` | Returnér True KUN når ``breached`` har holdt i ≥min_persistence træk OG tilstanden | [src](../../../core/services/central_noise_filter.py#L37) |
| function | `peek` | `(key)` | Read-only indblik i en nøgles tilstand (til debug/observabilitet). | [src](../../../core/services/central_noise_filter.py#L72) |
| function | `_reset_for_tests` | `()` | — | [src](../../../core/services/central_noise_filter.py#L85) |

## `core/services/central_notation.py`
_core/services/central_notation.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize` | `(notation)` | Kanonisk form: trim + kollaps whitespace. Deterministisk, model-fri. | [src](../../../core/services/central_notation.py#L19) |
| function | `parse` | `(notation)` | Split 'term OP term' → {antecedent, operator, consequent}. '!term' → saliens-form. | [src](../../../core/services/central_notation.py#L24) |
| function | `dedup` | `(notations)` | Unikke normaliserede notationer (identiske formodninger kollapses). Model-fri. | [src](../../../core/services/central_notation.py#L39) |
| function | `correlate_by_antecedent` | `(items)` | Gruppér hypoteser efter ANTECEDENT (venstre led). Hypoteser med samme antecedent handler om | [src](../../../core/services/central_notation.py#L49) |
| function | `model_free_analysis` | `(*, only_correlated=…)` | NORDSTJERNE-BEVIS: læs aktive hypotesers notation_il og udfør dedup + antecedent-korrelation | [src](../../../core/services/central_notation.py#L61) |
| function | `_causal_edges` | `(items)` | Byg antecedent→konsekvens-graf fra '→'-notationer (kun kausale led). | [src](../../../core/services/central_notation.py#L87) |
| function | `infer_transitive` | `(items, *, max_derived=…)` | TRANSITIV INFERENS (model-fri): fra A → B og B → C udled A → C. En NY tanke ingen enkelt | [src](../../../core/services/central_notation.py#L97) |
| function | `detect_notation_contradictions` | `(items)` | Model-fri MODSIGELSES-detektion: samme antecedent → BÅDE X og !X (Centralen opdager at den | [src](../../../core/services/central_notation.py#L115) |
| function | `gather_all_notations` | `()` | Spec B / Fase B2 (S3): saml notation fra ALLE notated overflader — hypoteser + renderede | [src](../../../core/services/central_notation.py#L134) |
| function | `model_free_reasoning` | `()` | NORDSTJERNE (pervasiv, B2): læs notation fra HELE Centralen (hypoteser + renderede tilstande) | [src](../../../core/services/central_notation.py#L162) |
| function | `run_notation_reasoning_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: udfør model-fri ræsonnement + registrér tællere egress-frit. Self-safe. | [src](../../../core/services/central_notation.py#L177) |
| function | `register_notation_reasoning_producer` | `()` | Registrér model-fri ræsonnement som cadence-producer (~hvert 30 min). | [src](../../../core/services/central_notation.py#L200) |
| function | `build_central_notation_surface` | `()` | Mission Control surface — read-only model-fri notations-analyse + ræsonnement. | [src](../../../core/services/central_notation.py#L212) |

## `core/services/central_oneiric_loop.py`
_DEN ONEIRISKE SLØJFE — drømme får dags-konsekvenser + beviser sig mod virkeligheden._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_oneiric_loop.py#L60) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_oneiric_loop.py#L69) |
| function | `_today` | `()` | Kanonisk dags-streng (hus-konvention: date().isoformat()). Dagen er den eksperimentelle enhed. | [src](../../../core/services/central_oneiric_loop.py#L77) |
| function | `is_control_day` | `(day, *, fraction=…)` | Er `day` en KONTROL-dag (bias beregnet men IKKE anvendt)? Deterministisk + salt-baseret | [src](../../../core/services/central_oneiric_loop.py#L82) |
| function | `_read_loop_persistence_bias` | `(*, workspace_id)` | Læs den aktive dream_bias' loop_persistence-værdi (honorerer kill-switch + TTL). Returnerer | [src](../../../core/services/central_oneiric_loop.py#L103) |
| function | `compose_oneiric_hypothesis` | `(*, loop_persistence, day, control_arm)` | Omsæt en loop_persistence-bias til en EKSPLICIT, menneske-læsbar, PRE-REGISTRERET, | [src](../../../core/services/central_oneiric_loop.py#L124) |
| function | `run_oneiric_loop_tick` | `(*, trigger=…, workspace_id=…, **_)` | Cadence: hvis der i dag er en (stærk nok) loop_persistence dream_bias OG vi ikke allerede | [src](../../../core/services/central_oneiric_loop.py#L175) |
| function | `register_oneiric_loop_producer` | `()` | Cadence-producer ~hver 6. time (langsom — dagen er enheden; idempotens gør flere tik/dag | [src](../../../core/services/central_oneiric_loop.py#L240) |
| function | `build_oneiric_loop_surface` | `(*, workspace_id=…)` | Read-only projektion: i dag en drøm-prædiktions-dag? hvilken arm? hvilken retning? | [src](../../../core/services/central_oneiric_loop.py#L253) |

## `core/services/central_oneiric_sampler.py`
_core/services/central_oneiric_sampler.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_oneiric_sampler.py#L37) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_oneiric_sampler.py#L46) |
| function | `_today` | `()` | — | [src](../../../core/services/central_oneiric_sampler.py#L54) |
| function | `_daily_counts` | `(cluster, nerve, *, window_days=…)` | Tæl durable timeseries-samples pr. dag (via meta['day']) for én nerve. READ-ONLY. | [src](../../../core/services/central_oneiric_sampler.py#L58) |
| function | `compute_arm_rates` | `(*, window_days=…)` | Byg pr.-dag no_progress-rate (numerator/denominator) og partitionér dagene i | [src](../../../core/services/central_oneiric_sampler.py#L76) |
| function | `_evaluate_hypothesis` | `(prov, arms)` | Afgør supports/falsifies for ÉN oneiric-hypotese: aktiv-arm-raten skal bevæge sig i | [src](../../../core/services/central_oneiric_sampler.py#L125) |
| function | `run_oneiric_sampler_tick` | `(*, trigger=…, **_)` | Cadence: ground åbne oneiric_loop-hypoteser mod den durable no_progress-rate | [src](../../../core/services/central_oneiric_sampler.py#L155) |
| function | `register_oneiric_sampler_producer` | `()` | Cadence-producer ~2×/dag (dagen er den eksperimentelle enhed; hyppigere tik harmløst | [src](../../../core/services/central_oneiric_sampler.py#L212) |
| function | `build_oneiric_sampler_surface` | `()` | Mission Control — read-only: aktiv- vs kontrol-arm-rate, så mennesket ser om drømmen | [src](../../../core/services/central_oneiric_sampler.py#L225) |

## `core/services/central_oracle.py`
_The Oracle — forudseende sans på en prim-cadence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_ts` | `(ts)` | — | [src](../../../core/services/central_oracle.py#L31) |
| function | `_slope_and_last` | `(samples)` | Mindste-kvadraters hældning (værdi pr. sekund) over samples med numerisk value. | [src](../../../core/services/central_oracle.py#L38) |
| function | `_project` | `(spec)` | Projicér én watched-serie → tid til tærskel-krydsning (eller None hvis den bevæger sig væk). | [src](../../../core/services/central_oracle.py#L58) |
| function | `foresee` | `()` | Læs alle watched-serier → forudsigelser (metadata-only). READ-ONLY. Self-safe. | [src](../../../core/services/central_oracle.py#L87) |
| function | `record_oracle` | `()` | Prim-cadence: observér forudsigelser til nerve system/oracle (metadata-only). Self-safe. | [src](../../../core/services/central_oracle.py#L107) |

## `core/services/central_output_conservation.py`
_Output-conservation-invariant (Bjørn 4. jul — "spøgelset")._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_conservation` | `(*, layer, produced_chars, emitted_chars, provider=…, model=…, run_id=…, path=…, tolerance=…)` | Registrér et conservation-tjek for ét lag. Returnér gap'et (produced-emitted, | [src](../../../core/services/central_output_conservation.py#L27) |
| function | `build_output_conservation_surface` | `()` | Mission Control — read-only meta-projektion (kartograf-dækning). | [src](../../../core/services/central_output_conservation.py#L69) |

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

