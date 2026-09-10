# `core.services.05` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_is_never` | `(nerve)` | True hvis <nerve> ALDRIG må optjene/godkende en decentraliserings-nøgle: enten katalog- | [src](../../../core/services/central_keymaker.py#L40) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/central_keymaker.py#L53) |
| function | `_now` | `()` | — | [src](../../../core/services/central_keymaker.py#L72) |
| function | `_observe` | `(kind, payload)` | — | [src](../../../core/services/central_keymaker.py#L76) |
| function | `evaluate_keys` | `()` | Find dimensioner der har OPTJENT en nøgle (track-record over tærskel) og udsted en PENDING | [src](../../../core/services/central_keymaker.py#L84) |
| function | `_ejer_uid` | `()` | — | [src](../../../core/services/central_keymaker.py#L128) |
| function | `_varsl_ejer` | `(domain, track)` | Sig til naar en noegle er OPTJENT — den kan ikke bruges foer ejeren godkender. | [src](../../../core/services/central_keymaker.py#L136) |
| function | `_adfaerds_track_record` | `()` | Hans egen efterlevelse af sine forpligtelser. ``None`` hvis den ikke kan maales. | [src](../../../core/services/central_keymaker.py#L193) |
| function | `evaluate_behaviour_key` | `()` | Udsted en PENDING adfaerds-noegle naar HAN har fortjent den. Self-safe. | [src](../../../core/services/central_keymaker.py#L208) |
| function | `har_adfaerds_noegle` | `()` | True hvis han har en GYLDIG (godkendt + ikke udloebet) adfaerds-noegle. | [src](../../../core/services/central_keymaker.py#L247) |
| function | `list_keys` | `(*, include_expired=…)` | — | [src](../../../core/services/central_keymaker.py#L256) |
| function | `is_decentralized` | `(nerve)` | True hvis <nerve> har en GYLDIG optjent decentraliserings-nøgle: status='approved' OG endnu | [src](../../../core/services/central_keymaker.py#L267) |
| function | `approve_key` | `(key_id)` | OWNER-handling: godkend en pending nøgle → flip dens flag ON i TTL. Auto-reverterer ved udløb. | [src](../../../core/services/central_keymaker.py#L289) |
| function | `expire_due` | `()` | Cadence: reverter flag for udløbne nøgler (tilladelse mistes hvis ikke fornyet). Self-safe. | [src](../../../core/services/central_keymaker.py#L323) |
| function | `_mind_om_ventende` | `()` | Mind om noegler der har ventet paa godkendelse i mere end tre dage. | [src](../../../core/services/central_keymaker.py#L354) |
| function | `build_keymaker_surface` | `()` | Owner-view: aktive/afventende nøgler + fortjente dimensioner. Self-safe. | [src](../../../core/services/central_keymaker.py#L404) |

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
| function | `autonomous_reliability` | `(*, hours=…, incidents=…)` | Jarvis' autonome pålidelighed fra supervisions-verdikterne (cluster=autonomous nerve= | [src](../../../core/services/central_learning.py#L99) |
| function | `assess_autonomy` | `(*, hours=…, incidents=…)` | DETERMINISTISK vurdering: er Jarvis moden til autonome opgaver? Baseret på pålidelighed. | [src](../../../core/services/central_learning.py#L118) |
| function | `_signature` | `(message)` | Normalisér en incident-besked til en stabil signatur så GENTAGNE fejl grupperes: | [src](../../../core/services/central_learning.py#L143) |
| function | `root_causes` | `(*, hours=…, min_count=…, incidents=…)` | Gruppér incidents efter (cluster/nerve/signatur) → rangerede GENTAGNE rod-årsager | [src](../../../core/services/central_learning.py#L154) |
| function | `propose_adjustments` | `(*, incidents=…)` | DETERMINISTISKE, reviewbare FORSLAG (aldrig auto-anvendt — Bjørn: "forslag ikke | [src](../../../core/services/central_learning.py#L191) |
| function | `learning_summary` | `()` | — | [src](../../../core/services/central_learning.py#L239) |
| function | `observe_learning` | `()` | Kadence: beregn læring + observe + flag degraderende clusters + emit FORSLAG. | [src](../../../core/services/central_learning.py#L250) |
| function | `poll_proposals` | `(*, limit=…)` | Reviewbar liste af deterministiske lærings-forslag (til Bjørn/Claude/MC/Jarvis). | [src](../../../core/services/central_learning.py#L274) |

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

