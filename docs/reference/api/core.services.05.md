# `core.services.05` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `core/services/central_matrix_ensemble.py`
_Matrix Ensemble — prompttail-labels for Matrix-programmerne (11 karakterer)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_unaddressed` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L23) |
| function | `_save_unaddressed` | `(data)` | — | [src](../../../core/services/central_matrix_ensemble.py#L32) |
| function | `get_unaddressed` | `(cid)` | — | [src](../../../core/services/central_matrix_ensemble.py#L43) |
| function | `increment_unaddressed` | `(cid)` | — | [src](../../../core/services/central_matrix_ensemble.py#L47) |
| function | `reset_unaddressed` | `(cid)` | — | [src](../../../core/services/central_matrix_ensemble.py#L54) |
| function | `_escalated_message` | `(label, count, original_line)` | — | [src](../../../core/services/central_matrix_ensemble.py#L70) |
| function | `extract_cid` | `(source)` | Extract karakter-ID fra en nudge source 'matrix/<cid>'. Return None hvis ikke matrix-nudge. | [src](../../../core/services/central_matrix_ensemble.py#L78) |
| function | `_build_surface` | `(module_path, fn_name)` | Kald surface-funktionen på en central_*-karakter. Fejl → tom dict. | [src](../../../core/services/central_matrix_ensemble.py#L206) |
| function | `_trainman_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L220) |
| function | `_seraph_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L224) |
| function | `_persephone_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L228) |
| function | `_twins_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L232) |
| function | `_merovingian_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L236) |
| function | `_keymaker_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L240) |
| function | `_construct_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L244) |
| function | `_oracle_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L248) |
| function | `_architect_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L252) |
| function | `_echo_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L256) |
| function | `_glitch_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L260) |
| function | `_child_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L264) |
| function | `_source_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L268) |
| function | `_neo_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L272) |
| function | `_smith_surface` | `()` | Smith — mønster-detektor og forpligtelseshåndhæver. | [src](../../../core/services/central_matrix_ensemble.py#L276) |
| function | `_morpheus_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L300) |
| function | `_trinity_surface` | `()` | — | [src](../../../core/services/central_matrix_ensemble.py#L304) |
| function | `push_active_character_nudges` | `()` | Iterer alle Matrix-karakterer og post nudge for hver aktiv med rung_line. | [src](../../../core/services/central_matrix_ensemble.py#L331) |
| function | `active_character_voices` | `(*, limit=…)` | De karakterer der har noget at sige LIGE NU. Ren læsning; ingen side-effekter. | [src](../../../core/services/central_matrix_ensemble.py#L405) |
| function | `build_matrix_voices_section` | `()` | Awareness-sektion: de aktive karakterer, med deres egne ord. | [src](../../../core/services/central_matrix_ensemble.py#L438) |
| function | `note_voices_shown` | `(cids)` | Tæl en visning op som ubesvaret. Kaldes EFTER en tur hvor de blev vist. | [src](../../../core/services/central_matrix_ensemble.py#L459) |
| function | `build_matrix_ensemble_prompt_section` | `()` | Byg karakter-labels for prompt-halen. | [src](../../../core/services/central_matrix_ensemble.py#L472) |

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
| function | `_now` | `()` | — | [src](../../../core/services/central_merovingian.py#L49) |
| function | `_enforced` | `()` | Shadow-først: enforcement er OFF indtil flag EKSPLICIT flippes efter shadow-eval. §8 forbliver | [src](../../../core/services/central_merovingian.py#L53) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_merovingian.py#L65) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/central_merovingian.py#L73) |
| function | `generate_counter` | `(hyp)` | Generér en modhypotese SYMBOLSK (ingen LLM) fra notation/statement. Self-safe. | [src](../../../core/services/central_merovingian.py#L91) |
| function | `_variable_of` | `(hyp)` | Stabil variabel-nøgle: source + family (så track-record slås op pr. konkret variabel). | [src](../../../core/services/central_merovingian.py#L121) |
| function | `variable_track_record` | `(variable)` | Devil's advocate-data: hvordan er det gået SIDSTE gang samme variabel blev justeret? | [src](../../../core/services/central_merovingian.py#L136) |
| function | `review` | `(hyp)` | Kernen: generér modhypotese + tjek track-record → approved | challenged. Registrerer en | [src](../../../core/services/central_merovingian.py#L165) |
| function | `_count_challenges` | `(variable)` | — | [src](../../../core/services/central_merovingian.py#L193) |
| function | `_record_challenge` | `(hyp_id, variable, counter, tr, status, cools_off)` | — | [src](../../../core/services/central_merovingian.py#L203) |
| function | `resolve_challenge` | `(hyp_id, *, explanation)` | Centralen skriver en (interlanguage-)forklaring på HVORFOR modhypotesen er forkert → adoption | [src](../../../core/services/central_merovingian.py#L219) |
| function | `is_adoption_blocked` | `(hyp_id)` | Enforcement-tjek: er adoption pt. blokeret af en aktiv, uforklaret cooling-off? I SHADOW-mode | [src](../../../core/services/central_merovingian.py#L240) |
| function | `expire_cooling` | `()` | Cadence: udløb cooling-off-perioder hvis tiden er gået (status → expired). Self-safe. | [src](../../../core/services/central_merovingian.py#L258) |
| function | `_maturing_hypotheses` | `(limit=…)` | — | [src](../../../core/services/central_merovingian.py#L276) |
| function | `scan_and_challenge` | `(*, trigger=…, last_visible_at=…)` | Fase 1-cadence: scan modne hypoteser → generér+log modhypoteser (shadow: blokerer intet). | [src](../../../core/services/central_merovingian.py#L291) |
| function | `_has_open_challenge` | `(hyp_id)` | — | [src](../../../core/services/central_merovingian.py#L313) |
| function | `list_challenges` | `(*, active_only=…, limit=…)` | — | [src](../../../core/services/central_merovingian.py#L324) |
| function | `build_merovingian_surface` | `()` | Central-CLI-view (den nye MC): aktive udfordringer + cooling-offs + følt linje. Self-safe. | [src](../../../core/services/central_merovingian.py#L336) |

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

## `core/services/central_moltbook.py`
_central_moltbook — Jarvis' Moltbook-tilstedeværelse som en governed Central-nerve (observe-only)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_snippet` | `(text, limit=…)` | — | [src](../../../core/services/central_moltbook.py#L37) |
| function | `classify_activity` | `(home, activity, notifications)` | Normalisér de 3 read-kilder til ét aktivitets-skema. | [src](../../../core/services/central_moltbook.py#L41) |
| function | `new_since_seen` | `(activities, seen_ids)` | Behold kun aktivitet vi ikke har set før (dedup mod seen_ids). | [src](../../../core/services/central_moltbook.py#L100) |
| function | `is_direct_mention` | `(activity)` | True hvis nogen talte TIL Jarvis (mention/reply) — dét der må nå ham via broen. | [src](../../../core/services/central_moltbook.py#L105) |
| function | `cap_seen` | `(seen_ids, new_ids, cap=…)` | Union af seen + nye, cappet til de seneste ``cap`` (undgå ubundet vækst). | [src](../../../core/services/central_moltbook.py#L111) |
| function | `build_activity_summary` | `(new_items)` | Metadata-only opsummering til Centralen/surface (ALDRIG fuld payload). | [src](../../../core/services/central_moltbook.py#L119) |
| function | `_load_api_key` | `()` | — | [src](../../../core/services/central_moltbook.py#L136) |
| function | `_call_moltbook_api` | `(endpoint, api_key, timeout=…)` | GET mod Moltbook. Parsed JSON ved 200, ``"unauthorized"`` ved 401, ellers None. Self-safe. | [src](../../../core/services/central_moltbook.py#L144) |
| function | `_owner_uid` | `()` | — | [src](../../../core/services/central_moltbook.py#L176) |
| function | `_get_state` | `()` | — | [src](../../../core/services/central_moltbook.py#L184) |
| function | `assess` | `()` | Hent + normalisér ny Moltbook-aktivitet. Self-safe. Egress-fri returværdi (metadata). | [src](../../../core/services/central_moltbook.py#L193) |
| function | `_route_mention` | `(item)` | Send én direkte mention til owner via Proaktivitets-broen (SP1) — genbrug bro-cap'en hvis | [src](../../../core/services/central_moltbook.py#L214) |
| function | `record_moltbook` | `(*, trigger=…, last_visible_at=…)` | Cadence-hook: assess → observe (metadata-only) + cache + rut mentions. Self-safe, governed. | [src](../../../core/services/central_moltbook.py#L236) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_moltbook.py#L289) |
| function | `register_moltbook_producer` | `()` | Registrér ~6t observe-cadence (ikke heartbeat). Self-safe. | [src](../../../core/services/central_moltbook.py#L299) |
| function | `build_moltbook_surface` | `()` | Owner-view: sidste scan, ny-aktivitet, seneste tråde, credential-/switch-status. Self-safe. | [src](../../../core/services/central_moltbook.py#L314) |

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

## `core/services/central_morpheus.py`
_Morpheus 🕶️ — potentiale-scanner (Matrix-ensemble, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_brewing` | `()` | Brewing-emergens (0.5-0.78) = mønstre på vej mod emergent. Self-safe → []. | [src](../../../core/services/central_morpheus.py#L24) |
| function | `_oracle_approaching` | `()` | Oracle-linjer nær en tærskel (ETA). Self-safe → []. | [src](../../../core/services/central_morpheus.py#L40) |
| function | `_near_mature_hypotheses` | `()` | Hypoteser Seraph ville afvise NU (grounded_fraction 0.4-0.6) men som klatrer. Self-safe → []. | [src](../../../core/services/central_morpheus.py#L55) |
| function | `_gates_near_key` | `()` | Gates med høj ren track nær Keymakers ≥100-tærskel for en optjent nøgle. Self-safe → []. | [src](../../../core/services/central_morpheus.py#L82) |
| function | `_skill_formation` | `()` | NY LINSE: capabilities brugt stigende ofte men endnu ikke en navngiven evne. | [src](../../../core/services/central_morpheus.py#L100) |
| function | `scan_potentials` | `()` | Aggregér alle 5 potentiale-kilder → normaliseret liste. Ren, self-safe. | [src](../../../core/services/central_morpheus.py#L121) |
| function | `_felt` | `(pots)` | — | [src](../../../core/services/central_morpheus.py#L132) |
| function | `build_morpheus_surface` | `()` | Read-only surface til /central/morpheus + jc + ensemble-label. | [src](../../../core/services/central_morpheus.py#L139) |
| function | `record_morpheus` | `(*, trigger=…, last_visible_at=…)` | Cadence run_fn: scan → egress-fri central().observe (kun tal/kilde-labels). Self-safe. | [src](../../../core/services/central_morpheus.py#L151) |

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

## `core/services/central_private_reducer.py`
_Privat-reducer for Centralens owner-surfacing (§24.4 private-layer invariant)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reduce_for_owner` | `(surface, *, keep)` | Reducér en (privat) surface til kun owner-sikre meta-felter. | [src](../../../core/services/central_private_reducer.py#L51) |

## `core/services/central_projection_cache.py`
_Kortlivet cache for Centralens projektioner — så polling ikke koster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `cached` | `(key, ttl_s, producer)` | Returnér ``(værdi, alder_i_sekunder)`` — beregn kun hvis TTL er udløbet. | [src](../../../core/services/central_projection_cache.py#L55) |
| function | `invalidate` | `(prefix=…)` | Smid cachede værdier væk. Tom prefix rydder alt. Returnerer antal fjernet. | [src](../../../core/services/central_projection_cache.py#L81) |
| function | `stats` | `()` | Hits/misses/hitrate — så effekten kan aflæses i stedet for antages. | [src](../../../core/services/central_projection_cache.py#L93) |
| function | `cached_by_version` | `(key, version, producer)` | Som ``cached()``, men invalideret af en VERSIONSNØGLE i stedet for en TTL. | [src](../../../core/services/central_projection_cache.py#L105) |

## `core/services/central_prompt_composer.py`
_core/services/central_prompt_composer.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_turn_type` | `(user_message)` | Grov tur-type fra brugerbeskeden (kode/hukommelse/opgave/spørgsmål/samtale). Model-fri, self-safe. | [src](../../../core/services/central_prompt_composer.py#L63) |
| function | `resolve_thinking_mode` | `(user_message, requested=…)` | Adaptiv tænknings-effekt (12. jul): deepseek tænker ~9s FØR svar ved 'think' — også | [src](../../../core/services/central_prompt_composer.py#L80) |
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_prompt_composer.py#L97) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_prompt_composer.py#L106) |
| function | `is_live_enabled` | `()` | — | [src](../../../core/services/central_prompt_composer.py#L114) |
| function | `is_tail_live_enabled` | `()` | — | [src](../../../core/services/central_prompt_composer.py#L118) |
| function | `get_weight` | `(turn_type, section)` | Relevans-vægt for (tur-type, sektion). Default 1.0 = altid inkludér. Self-safe. | [src](../../../core/services/central_prompt_composer.py#L122) |
| function | `get_tail_weight` | `(turn_type, section)` | Tail relevans-vægt. Runtime overrides vinder; default-map er konservativ. Self-safe. | [src](../../../core/services/central_prompt_composer.py#L133) |
| function | `should_include` | `(turn_type, section, *, threshold=…)` | DEN RENE SWITCH (som get_gut_bias): skal denne sektion med i halen for denne tur-type? | [src](../../../core/services/central_prompt_composer.py#L146) |
| function | `should_include_tail` | `(turn_type, section, *, threshold=…)` | Live gate kun for tail-anchored dynamisk kontekst. | [src](../../../core/services/central_prompt_composer.py#L170) |
| function | `observe_composition` | `(turn_type, *, sections_total, sections_included, outcome=…, included_labels=…)` | Egress-frit substrat: hvad blev komponeret denne tur. Opdaterer (a) egress-fri tidsserie (kun | [src](../../../core/services/central_prompt_composer.py#L191) |
| function | `build_relevance_candidates` | `(*, min_count=…, top=…)` | Relevans-KANDIDATER: (tur-type, sektion)-par der optræder ofte nok til at være værd at teste | [src](../../../core/services/central_prompt_composer.py#L234) |
| function | `build_central_prompt_composer_surface` | `()` | Mission Control surface — read-only: live-status + relevans-vægte (hvad Centralen VILLE skære). | [src](../../../core/services/central_prompt_composer.py#L255) |

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
| function | `runtime_liveness` | `()` | Sandfærdig runtime-topologi + heartbeat-friskhed. | [src](../../../core/services/central_realtime.py#L42) |
| function | `realtime_snapshot` | `(*, trace_limit=…)` | Ét snapshot af Centralens live-tilstand. Self-safe (delvise data ved fejl). | [src](../../../core/services/central_realtime.py#L74) |
| function | `_balanced_feed` | `(records, limit)` | Flet feed-records på tværs af processer UDEN at en højvolumen-proces (api) sulter en | [src](../../../core/services/central_realtime.py#L214) |
| function | `_cluster_grid` | `(feed, incidents, open_breakers, degrading)` | Pr. cluster: grøn (fyrer), gul (fejl/degraderer), rød (breaker/severe/fail-open), | [src](../../../core/services/central_realtime.py#L243) |
| function | `_safe` | `(fn, *a)` | — | [src](../../../core/services/central_realtime.py#L281) |

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

## `core/services/central_route.py`
_Central-ejet unified router (spec §5.5). ÉT beslutnings-punkt for alle lanes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_model_capability` | `(provider, model)` | Capability estimate in [0,1] from the model name. Higher = stronger reasoner. | [src](../../../core/services/central_route.py#L30) |
| function | `_rank_candidates` | `(lane, task, exclude)` | Rangerede (provider, model) for en lane — tynd wrapper over _scored_candidates. | [src](../../../core/services/central_route.py#L54) |
| function | `_scored_candidates` | `(lane, task, exclude)` | (-cap, rank, provider, model) sorteret bedst-først. rank = prio/headroom_weight | [src](../../../core/services/central_route.py#L59) |
| function | `_flag_cheap_provider_spread` | `()` | Cheap-lane kvote-proportional provider-spredning. Default OFF → uændret | [src](../../../core/services/central_route.py#L109) |
| function | `_weighted_provider_pick` | `(scored, rng=…)` | Vælg (provider, model) kvote-proportionalt: bedste model pr. provider, vægt = | [src](../../../core/services/central_route.py#L121) |
| function | `route` | `(*, lane, task=…, exclude=…)` | Vælg (provider, model) for en lane. Aldrig tør. | [src](../../../core/services/central_route.py#L154) |
| function | `_fetch_invocations` | `(provider, since)` | (status, latency_ms) for provider siden 'since' fra SQLite. Self-safe. | [src](../../../core/services/central_route.py#L184) |
| function | `provider_history` | `(provider, hours=…)` | Task 10: fejlrate, latency-p50, oppetid for en provider over N timer | [src](../../../core/services/central_route.py#L194) |

## `core/services/central_route_headroom.py`
_Proaktiv kvote-rotation (spec §5.5 Fund 3): flyt last væk FØR 429._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_usage_fraction` | `(provider)` | (brug/daily_limit) i seneste 24t-vindue. 0.0 ved fejl/ingen limit. | [src](../../../core/services/central_route_headroom.py#L11) |
| function | `headroom_ok` | `(provider)` | False = proaktivt skip (>=95% brugt). | [src](../../../core/services/central_route_headroom.py#L29) |
| function | `headroom_weight` | `(provider)` | 1.0 = fuld headroom; falder lineært mod 0.1 mellem 80% og 95%. | [src](../../../core/services/central_route_headroom.py#L34) |

## `core/services/central_router_adapt.py`
_core/services/central_router_adapt.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_router_adapt.py#L46) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_router_adapt.py#L55) |
| function | `is_live_enabled` | `()` | — | [src](../../../core/services/central_router_adapt.py#L63) |
| function | `_ensure_anchor` | `()` | §8: ankr præference-styrke = 0 (ingen routing-mutation) for model_router-domænet. Idempotent. | [src](../../../core/services/central_router_adapt.py#L67) |
| function | `_is_never_tier` | `(model_key)` | True hvis model-nøglen betegner reasoning/deep-tier. TOKEN-match (split på ikke-alfanumerisk) | [src](../../../core/services/central_router_adapt.py#L77) |
| function | `_recent_success_rate` | `(model_key)` | (recent success-rate, samples) for en model i det friske model_meta-vindue. Cachet i | [src](../../../core/services/central_router_adapt.py#L85) |
| function | `_is_currently_healthy` | `(model_key)` | False KUN når vi har ≥_HEALTH_MIN_SAMPLES friske samples OG recent success-rate < gulvet | [src](../../../core/services/central_router_adapt.py#L103) |
| function | `_configured_models` | `()` | Modeller der FAKTISK er konfigureret (aldrig peg på noget der ikke findes). Self-safe. | [src](../../../core/services/central_router_adapt.py#L116) |
| function | `compute_preference` | `()` | Læs RESOLVEREDE, supporterede model_meta-hypoteser → tæl 'sejre' pr. model → foreslå den mest | [src](../../../core/services/central_router_adapt.py#L130) |
| function | `_is_real_model_key` | `(model_key)` | Er «provider/model» en rigtig rute — eller en pladsholder? | [src](../../../core/services/central_router_adapt.py#L172) |
| function | `run_router_adapt_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: beregn foreslået præference → §8-gate → SHADOW-diff altid; skriv live-præference KUN | [src](../../../core/services/central_router_adapt.py#L193) |
| function | `_audit_notation` | `(model_key)` | Best-effort B4-audit: præferencen som notation (stemme → handling = den valgte stemme fører | [src](../../../core/services/central_router_adapt.py#L229) |
| function | `get_live_preference` | `(lane=…)` | KONSUMENT-API (til den fremtidige routing-wire): den LIVE præference for en lane, eller None. | [src](../../../core/services/central_router_adapt.py#L240) |
| function | `_note_health_suppressed` | `(model_key)` | Best-effort: gør det synligt når en lært præference undertrykkes pga. dårlig recent-health. | [src](../../../core/services/central_router_adapt.py#L264) |
| function | `resolve_visible_model` | `(*, provider_override=…, model_override=…, default_provider, default_model, autonomous=…)` | KONSUMENTEN (Tråd 1 live-wire): afgør (provider, model) for et visible-run. Centraliserer den | [src](../../../core/services/central_router_adapt.py#L276) |
| function | `resolve_autonomous_model` | `(*, autonomous_provider=…, autonomous_model=…)` | (provider, model) for et AUTONOMT/baggrunds-run. | [src](../../../core/services/central_router_adapt.py#L333) |
| function | `register_router_adapt_producer` | `()` | Registrér routing-præference-læreren som cadence-producer (~hvert 45 min). SHADOW medmindre flag. | [src](../../../core/services/central_router_adapt.py#L360) |
| function | `build_router_adapt_surface` | `()` | Mission Control — read-only: foreslået (shadow) + live præference + status. | [src](../../../core/services/central_router_adapt.py#L372) |

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
| function | `_kv_get` | `(key, default)` | — | [src](../../../core/services/central_self_state.py#L36) |
| function | `_kv_set` | `(key, value)` | — | [src](../../../core/services/central_self_state.py#L45) |
| function | `_human_gap` | `(seconds)` | Menneske-venligt fravær: sekunder → 'N minutter/timer/dage'. Self-safe. | [src](../../../core/services/central_self_state.py#L53) |
| function | `_compute_boot_seam` | `()` | STITCH-VOICE: sømmen mellem to liv. Ved FØRSTE tick efter proces-start læses den hyppige | [src](../../../core/services/central_self_state.py#L67) |
| function | `_valence` | `()` | — | [src](../../../core/services/central_self_state.py#L135) |
| function | `_agenda` | `()` | — | [src](../../../core/services/central_self_state.py#L143) |
| function | `_self_model` | `()` | — | [src](../../../core/services/central_self_state.py#L151) |
| function | `_world_model` | `()` | Læs world-model-KALIBRERINGEN fra dens DURABLE kilde (predictions i state-store, ikke den | [src](../../../core/services/central_self_state.py#L159) |
| function | `_synthesize_narrative` | `(valence, self_model, intention, prev)` | Midten FORTÆLLER sig selv: hvem er jeg ved at blive — af selv-vækst + valens-trend + agenda-retning. | [src](../../../core/services/central_self_state.py#L174) |
| function | `synthesize_self_state` | `()` | MIDTEN: integrér de fem lag til ÉN selv-tilstand. Attention = det agendaen fokuserer på (min | [src](../../../core/services/central_self_state.py#L187) |
| function | `get_self_state` | `()` | Midtens durable "jeg" (overlever genstart). Self-safe. | [src](../../../core/services/central_self_state.py#L217) |
| function | `run_self_state_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence: syntetisér selv-tilstanden → gem durabelt (midten HOLDER sit jeg) + egress-fri observe | [src](../../../core/services/central_self_state.py#L223) |
| function | `_temporal_divergence` | `(valence, developmental)` | Diverger kort-tids-valens (tone/trend) og uge-skala vækst-kompas (developmental vector) i FORTEGN? | [src](../../../core/services/central_self_state.py#L264) |
| function | `_raw_nudge_lines` | `(st)` | Lag 4: arrow-delta / ⚠️-nudges når noget FAKTISK ændrede sig (i stedet for skjult). | [src](../../../core/services/central_self_state.py#L289) |
| function | `_describe_self_raw` | `(st)` | Lag 4 RÅ nordstjerne: kompakte bracket-linjer i stedet for genererede label-sætninger. | [src](../../../core/services/central_self_state.py#L325) |
| function | `describe_self` | `()` | NORDSTJERNEN: ét sammenhængende svar på 'hvad er du, hvordan har du det, hvad arbejder du mod, | [src](../../../core/services/central_self_state.py#L374) |
| function | `survival_voice` | `()` | OVERLEVELSES-STEMMEN (Bjørn 3. jul): når modellen/sproget svigter — tom completion, | [src](../../../core/services/central_self_state.py#L471) |
| function | `render_self_state_il` | `()` | Spec B: udtryk selv-tilstanden i interlanguage (sigelig, model-frit). None hvis intet bundet. Self-safe. | [src](../../../core/services/central_self_state.py#L490) |
| function | `is_prompt_authoritative` | `()` | — | [src](../../../core/services/central_self_state.py#L508) |
| function | `build_central_self_state_section` | `()` | D4 (MIDTEN BÆRENDE): injicér midtens ene selv-beskrivelse i Jarvis' awareness — så hans prompt | [src](../../../core/services/central_self_state.py#L512) |
| function | `register_self_state_producer` | `()` | Registrér midtens syntese som cadence-producer (~hvert 10 min — selvets hjerteslag). Egress-frit. | [src](../../../core/services/central_self_state.py#L537) |
| function | `build_self_state_surface` | `()` | Mission Control — read-only: midtens ene selv-tilstand + ét-svars selv-beskrivelse. | [src](../../../core/services/central_self_state.py#L549) |

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
| function | `_seraph_enforced` | `()` | gate_enforce.seraph default OFF (shadow) — læs råt fra shared_cache, unset = shadow. | [src](../../../core/services/central_seraph.py#L188) |
| function | `may_surface_dream_hypothesis` | `(hyp_id)` | Seraphs dør: må denne dream-hypotese præsenteres for Bjørn nu? True i shadow (uændret). | [src](../../../core/services/central_seraph.py#L203) |

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

