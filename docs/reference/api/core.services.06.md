# `core.services.06` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `_is_vague_theme` | `(theme)` | True hvis temaet er tomt, for kort, eller et rent fyldeord. Ren, self-safe. | [src](../../../core/services/central_trainman.py#L47) |
| function | `_recent_dreams` | `(limit=…)` | Seneste distillerede/konsoliderede drømme (id, tema, timestamp). Self-safe. | [src](../../../core/services/central_trainman.py#L57) |
| function | `_existing_dream_memories` | `(limit=…)` | Trainmans allerede-vævede erindringer i private_brain (til idempotens + tema-forbindelser). | [src](../../../core/services/central_trainman.py#L66) |
| function | `_dream_id_of` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L80) |
| function | `_dream_theme` | `(dream)` | Øverste tema for en drøm. Konsoliderings-drømme bærer en themes-liste; distillat en top_theme. | [src](../../../core/services/central_trainman.py#L84) |
| function | `_dream_timestamp` | `(dream)` | — | [src](../../../core/services/central_trainman.py#L95) |
| function | `_sig_of` | `(rec)` | Afkod source_signals-JSON på en vævet erindring (dream_id, theme, connected_to …). Self-safe. | [src](../../../core/services/central_trainman.py#L99) |
| function | `_interlanguage` | `(theme)` | Byg en interlanguage-notation for temaet. Prøv lexicon (bundne termer); ellers spec-stil | [src](../../../core/services/central_trainman.py#L109) |
| function | `_emotional_tone` | `(theme)` | Simpel deterministisk klang ud fra tema-ord. Ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L126) |
| function | `_weave_narrative` | `(*, theme, dream)` | Væv drømmen til en 1.-persons erindrings-historie. Ren tekst, ingen model. Self-safe. | [src](../../../core/services/central_trainman.py#L138) |
| function | `_connected_ids` | `(theme, existing, *, limit=…)` | record_id'er for tidligere vævede erindringer om SAMME tema (drømme-kontinuitet). Self-safe. | [src](../../../core/services/central_trainman.py#L147) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/central_trainman.py#L160) |
| function | `_write_memory` | `(*, dream_id, theme, narrative, interlanguage, connected_to, emotional_tone, now)` | Skriv den vævede erindring til private_brain (source='dream'). Returnerer record_id ('' ved fejl). | [src](../../../core/services/central_trainman.py#L170) |
| function | `_signal_agenda` | `(*, theme, count, dream_id)` | 3+ drømme om samme tema på 7 dage → lav-prioritets initiativ til Agendaen. Self-safe. | [src](../../../core/services/central_trainman.py#L204) |
| function | `transform_dreams` | `(*, trigger=…, last_visible_at=…)` | Væv nye drømme til narrative erindringer i private_brain (source='dream'). | [src](../../../core/services/central_trainman.py#L225) |
| function | `_count_theme_recent` | `(theme, memories, *, now)` | Antal vævede erindringer om `theme` indenfor RECURRENCE_WINDOW_DAYS. Self-safe. | [src](../../../core/services/central_trainman.py#L292) |
| function | `_theme_distribution` | `(memories, *, now, days=…)` | Tema→antal over de sidste `days` dage. Self-safe. | [src](../../../core/services/central_trainman.py#L309) |
| function | `_last_reflection_at` | `(existing)` | — | [src](../../../core/services/central_trainman.py#L330) |
| function | `_maybe_reflect` | `(*, existing, now)` | Én gang pr. ~døgn: skriv en metakognitiv erindring om de sidste 7 dages tema-fordeling. | [src](../../../core/services/central_trainman.py#L337) |
| function | `_maybe_silence_note` | `(*, existing, now)` | Temaer der før var tilbagevendende men har været tavse i 14 dage → nysgerrigheds-note. | [src](../../../core/services/central_trainman.py#L370) |
| function | `_observe` | `(out)` | — | [src](../../../core/services/central_trainman.py#L422) |
| function | `build_trainman_surface` | `()` | Seneste vævede erindringer + tema-fordeling for Central-CLI. READ-ONLY. Self-safe. | [src](../../../core/services/central_trainman.py#L439) |
| function | `record_trainman` | `(*, trigger=…, last_visible_at=…)` | Cadence: væv nye drømme til erindringer. Self-safe — kaster aldrig. | [src](../../../core/services/central_trainman.py#L474) |

## `core/services/central_trinity.py`
_Trinity 💜 — trust-bridge (Matrix-ensemble, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `()` | — | [src](../../../core/services/central_trinity.py#L27) |
| function | `_is_enforced` | `()` | Default OFF (shadow) — modsat gate-default. Læs råt fra shared_cache, unset = shadow. | [src](../../../core/services/central_trinity.py#L41) |
| function | `_mature_hypotheses` | `()` | Modne hypoteser (Seraphs kriterium: grounded_fraction ≥ 0.6 + abs-gulv). Self-safe → []. | [src](../../../core/services/central_trinity.py#L55) |
| function | `_ledger` | `()` | — | [src](../../../core/services/central_trinity.py#L80) |
| function | `assess_affirmations` | `()` | Konvergens-vurdering pr. moden hypotese → affirmationer med progress mod nøgle. Read-only. | [src](../../../core/services/central_trinity.py#L91) |
| function | `_bump` | `(pattern_key, title, now)` | Registrér én affirmation → returnér ny streak. Self-safe → 0. | [src](../../../core/services/central_trinity.py#L111) |
| function | `_merovingian_blocks` | `(pattern_key)` | Værn ④: Merovingian kan udfordre en Trinity-optjent nøgle. Self-safe → False (fail-open). | [src](../../../core/services/central_trinity.py#L134) |
| function | `_earn_pending_key` | `(pattern_key, title, streak)` | Fase 2: opret en PENDING trust-nøgle i central_keys (samme tabel Keymaker bruger, | [src](../../../core/services/central_trinity.py#L143) |
| function | `record_trinity` | `(*, trigger=…, last_visible_at=…)` | Cadence run_fn: assess → opdatér streaks → (KUN hvis enforced) optjen pending nøgle. | [src](../../../core/services/central_trinity.py#L181) |
| function | `build_trinity_surface` | `()` | Read-only surface til /central/trinity + jc + ensemble-label. | [src](../../../core/services/central_trinity.py#L211) |

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
| function | `_owner_uid` | `()` | — | [src](../../../core/services/central_watch.py#L48) |
| function | `_notify_cooldown_active` | `(key, now)` | True hvis samme flag allerede har ringet inden for afkølingsvinduet. | [src](../../../core/services/central_watch.py#L68) |
| function | `_notify_cooldown_mark` | `(key, now)` | — | [src](../../../core/services/central_watch.py#L91) |
| function | `_notify_owner` | `(title, message, importance)` | — | [src](../../../core/services/central_watch.py#L115) |
| function | `_raise_flag` | `(cluster, nerve, *, severity, message, importance=…, make_incident=…)` | Ét flag → trace + (læring via incident) + (notifikation) + tidsserie. Self-safe. | [src](../../../core/services/central_watch.py#L138) |
| function | `_latest` | `(cluster, nerve)` | — | [src](../../../core/services/central_watch.py#L172) |
| function | `run_watch_tick` | `(*, trigger=…, last_visible_at=…)` | Evaluér de fodrede streams; flag ægte (støjfangede) signaler. Self-safe. | [src](../../../core/services/central_watch.py#L177) |
| function | `_event_is_recent` | `(r, *, max_age_min=…)` | True hvis event-record er nyere end max_age_min. Fail-open ved ukendt/uparsbar | [src](../../../core/services/central_watch.py#L392) |
| function | `_council_forced_count` | `(*, limit=…)` | Antal council.deadlock_forced_conclusion på eventbussen NYLIGT. Cross-proces. | [src](../../../core/services/central_watch.py#L407) |
| function | `_today_cost_usd` | `()` | — | [src](../../../core/services/central_watch.py#L421) |
| function | `_cheap_lane_stats` | `(*, limit=…)` | (completed, exhausted) fra seneste cheap-lane-events på eventbussen (cross-proces). | [src](../../../core/services/central_watch.py#L429) |
| function | `_tool_outcome_counts` | `(*, limit=…)` | (total, errors) fra NYLIGE tool.completed-events på eventbussen. Cross-proces. | [src](../../../core/services/central_watch.py#L452) |
| function | `_heed_summary` | `()` | Verification-heed-aggregat (fil-backet = cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L470) |
| function | `_recent_cache_pcts` | `(*, limit=…)` | Læs seneste cache-hit-rater fra eventbussen (cross-proces). Self-safe. | [src](../../../core/services/central_watch.py#L479) |
| function | `register_watch_producer` | `()` | Registrér vagten som cadence-producer (~hvert 2 min). Læser tidsserie + flagger. | [src](../../../core/services/central_watch.py#L493) |

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

## `core/services/chat_sessions.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_tool_result_for_reconstruct` | `(result_id)` | Serve-on-read loader: slå et gammelt tool-resultat op fra tool_result_store. | [src](../../../core/services/chat_sessions.py#L21) |
| function | `_content_json_for_row` | `(role, content, raw_json)` | Adapter: gemt content_json parses; ellers rekonstruér fra tekst (best-effort, | [src](../../../core/services/chat_sessions.py#L39) |
| function | `create_chat_session` | `(*, title=…, workspace_kind=…, workspace_root=…, kind=…)` | — | [src](../../../core/services/chat_sessions.py#L54) |
| function | `get_or_create_named_session` | `(session_id, title)` | Idempotent: sikr at en session med EKSPLICIT id findes (opret hvis ny). | [src](../../../core/services/chat_sessions.py#L101) |
| function | `most_recent_session_id` | `()` | Lightweight: session_id of the most recently updated session. | [src](../../../core/services/chat_sessions.py#L128) |
| function | `_sikr_flag_kolonner` | `(conn)` | Doven migration: `pinned` og `archived` paa chat_sessions. | [src](../../../core/services/chat_sessions.py#L145) |
| function | `set_session_flags` | `(session_id, *, pinned=…, archived=…)` | Saet fastgjort/arkiveret paa én samtale. Kun de felter der gives. | [src](../../../core/services/chat_sessions.py#L191) |
| function | `list_chat_sessions` | `(*, user_id=…, inkluder_arkiverede=…, kind=…)` | List chat sessions, optionally filtered to one user. | [src](../../../core/services/chat_sessions.py#L236) |
| function | `_make_snippet` | `(content, query, width=…)` | Byg et kort uddrag centreret om første match (case-insensitive). | [src](../../../core/services/chat_sessions.py#L337) |
| function | `search_chat_sessions` | `(query, *, user_id=…, limit=…)` | Søg sessioner på titel ELLER besked-indhold (user/assistant). | [src](../../../core/services/chat_sessions.py#L352) |
| function | `session_version` | `(session_id)` | Billig nøgle der ændrer sig præcis når sessionens indhold gør. | [src](../../../core/services/chat_sessions.py#L434) |
| function | `get_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L472) |
| function | `set_session_workspace` | `(session_id, *, kind, root)` | Bind (eller skift) en sessions Code-mode workspace. | [src](../../../core/services/chat_sessions.py#L524) |
| function | `append_chat_message` | `(*, session_id, role, content, created_at=…, tool_name=…, tool_arguments=…, full_content=…, user_id=…, workspace_name=…, reasoning_content=…, content_json=…)` | — | [src](../../../core/services/chat_sessions.py#L539) |
| function | `_navngiv_fra_foerste_besked` | `(session_id, content)` | Doeb sessionen efter det foerste brugeren skrev i den. | [src](../../../core/services/chat_sessions.py#L789) |
| function | `_recent_duplicate_user_message` | `(session_id, content, now_ts)` | Returnér den seneste besked-række HVIS den er en identisk brugerbesked inden | [src](../../../core/services/chat_sessions.py#L826) |
| function | `_infer_tool_name_from_content` | `(content)` | — | [src](../../../core/services/chat_sessions.py#L861) |
| function | `recent_user_message_texts` | `(*, limit=…)` | Brugerens seneste beskeder paa TVAERS af sessioner — kun teksten. | [src](../../../core/services/chat_sessions.py#L868) |
| function | `recent_chat_session_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L892) |
| function | `chat_session_messages_since_last_compact` | `(session_id, *, max_total=…)` | Hent ALT efter seneste compact_marker (eller hele session hvis ingen). | [src](../../../core/services/chat_sessions.py#L919) |
| function | `recent_chat_session_messages_by_user_turns` | `(session_id, *, user_turns=…, max_total=…)` | Hent de seneste N *user-turns* og alt der hører til dem. | [src](../../../core/services/chat_sessions.py#L981) |
| function | `_ensure_compact_marker_git_sha_column` | `()` | Add git_sha column to chat_messages if it doesn't exist (idempotent migration). | [src](../../../core/services/chat_sessions.py#L1057) |
| function | `store_compact_marker` | `(session_id, summary_text, git_sha=…)` | Store a compact marker for the session. Returns the marker message_id. | [src](../../../core/services/chat_sessions.py#L1069) |
| function | `get_compact_marker_with_sha` | `(session_id)` | Return (summary, git_sha) of the most recent compact marker, or (None, None). | [src](../../../core/services/chat_sessions.py#L1131) |
| function | `get_compact_marker` | `(session_id)` | Return the most recent compact marker summary for the session, or None. | [src](../../../core/services/chat_sessions.py#L1155) |
| function | `recent_chat_tool_messages` | `(session_id, *, limit=…)` | — | [src](../../../core/services/chat_sessions.py#L1173) |
| function | `rename_chat_session` | `(session_id, *, title)` | — | [src](../../../core/services/chat_sessions.py#L1198) |
| function | `delete_chat_session` | `(session_id)` | — | [src](../../../core/services/chat_sessions.py#L1212) |
| function | `_session_summary` | `(row)` | — | [src](../../../core/services/chat_sessions.py#L1234) |
| function | `_normalize_title` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L1253) |
| function | `_preview_text` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L1260) |
| function | `_time_label` | `(value)` | — | [src](../../../core/services/chat_sessions.py#L1267) |
| function | `parse_channel_from_session_title` | `(title)` | Parse channel type and detail from a session title. | [src](../../../core/services/chat_sessions.py#L1275) |
| function | `get_session_owner` | `(session_id)` | Ejeren = user_id paa den seneste besked i sessionen der HAR et stempel. | [src](../../../core/services/chat_sessions.py#L1305) |
| function | `latest_user_content_json` | `(session_id)` | `content_json` for sessionens SENESTE brugerbesked. | [src](../../../core/services/chat_sessions.py#L1321) |

## `core/services/cheap_lane_balancer.py`
_Cheap Lane Balancer — weighted-random load balancing for daemon LLM calls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BalancerSlot` | `` | Immutable identity of a (provider, model) lane. | [src](../../../core/services/cheap_lane_balancer.py#L21) |
| method | `BalancerSlot.slot_id` | `(self)` | — | [src](../../../core/services/cheap_lane_balancer.py#L33) |
| class | `SlotState` | `` | Per-slot mutable runtime state. Persisted to JSON (timestamps deque is in-memory only). | [src](../../../core/services/cheap_lane_balancer.py#L38) |
| function | `_provider_router_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L79) |
| function | `_router_enabled_models` | `()` | Return list of dicts {provider, model, enabled, auth_profile, lane} | [src](../../../core/services/cheap_lane_balancer.py#L86) |
| function | `_credentials_ready` | `(provider, auth_profile)` | Check if provider has working credentials. Wraps existing helper. | [src](../../../core/services/cheap_lane_balancer.py#L116) |
| function | `_provider_metadata` | `(provider)` | Lookup provider's static config (rpm_limit, daily_limit, base_url, etc.). | [src](../../../core/services/cheap_lane_balancer.py#L125) |
| function | `_state_path` | `()` | — | [src](../../../core/services/cheap_lane_balancer.py#L142) |
| function | `_state_to_dict` | `(state)` | Serialize SlotState to JSON-safe dict (skips deque). | [src](../../../core/services/cheap_lane_balancer.py#L149) |
| function | `_state_from_dict` | `(d)` | — | [src](../../../core/services/cheap_lane_balancer.py#L171) |
| function | `_load_state` | `()` | Load all slot-states from disk. Returns empty dict on missing/corrupt file. | [src](../../../core/services/cheap_lane_balancer.py#L192) |
| function | `_save_state` | `(states)` | Atomic write to state file. | [src](../../../core/services/cheap_lane_balancer.py#L210) |
| function | `_save_state_debounced` | `(states)` | — | [src](../../../core/services/cheap_lane_balancer.py#L229) |
| function | `_ensure_state` | `(states, slot_id)` | Get-or-create slot state. Mutates `states` in place. | [src](../../../core/services/cheap_lane_balancer.py#L239) |
| function | `_today_iso` | `(now=…)` | Returns UTC date string. Override hookable via module-level _datetime_for_today. | [src](../../../core/services/cheap_lane_balancer.py#L258) |
| function | `_count_recent_calls` | `(timestamps, now, window_seconds)` | Count timestamps falling within [now - window, now]. | [src](../../../core/services/cheap_lane_balancer.py#L264) |
| function | `_daily_used_from_db` | `(provider, auth_profile=…)` | Task 4 / Fund 5: daglig brug fra SQLite cheap_provider_invocations (samme kilde | [src](../../../core/services/cheap_lane_balancer.py#L270) |
| function | `_daily_headroom_for` | `(slot, state=…)` | Daily headroom fra SQLite frem for balancerens private JSON daily_use_count. | [src](../../../core/services/cheap_lane_balancer.py#L287) |
| function | `_observe_central` | `(nerve, payload)` | Task 5: skriv til Centralens system/<nerve>. Self-safe — observabilitet må | [src](../../../core/services/cheap_lane_balancer.py#L303) |
| function | `_emit_balancer_event` | `(name, payload)` | Ét sted: emit til eventbus (bagudkompatibelt) + observe fejl-events til Central. | [src](../../../core/services/cheap_lane_balancer.py#L313) |
| function | `_compute_weight` | `(slot, state, now)` | Returns non-negative weight; 0 means slot is ineligible right now. | [src](../../../core/services/cheap_lane_balancer.py#L326) |
| function | `_slot_status` | `(slot, state, now)` | Single derived status string for a slot, most-severe-wins. | [src](../../../core/services/cheap_lane_balancer.py#L369) |
| function | `_flag_adaptive_quota` | `()` | Learn real daily ceilings from genuine daily-quota 429s. Default OFF. | [src](../../../core/services/cheap_lane_balancer.py#L427) |
| function | `_maybe_daily_reset` | `(state, now)` | Reset per-day adaptive-quota learning at the UTC day boundary. | [src](../../../core/services/cheap_lane_balancer.py#L440) |
| function | `_register_failure` | `(state, error_kind, *, retry_after_s=…, now, error_message=…, observed_used=…, config_daily=…)` | Update state after a failed call. | [src](../../../core/services/cheap_lane_balancer.py#L455) |
| function | `_register_success` | `(state, now)` | Update state after a successful call. | [src](../../../core/services/cheap_lane_balancer.py#L537) |
| function | `_is_dns_or_connection_error` | `(error_kind, exc=…)` | True if error indicates network-level (provider-wide) issue, not slot-specific. | [src](../../../core/services/cheap_lane_balancer.py#L554) |
| function | `_register_provider_wide_failure` | `(states, pool, provider, now, *, reason, cooldown_s=…)` | Apply cooldown to ALL slots from `provider`. Returns number of slots affected. | [src](../../../core/services/cheap_lane_balancer.py#L572) |
| function | `_select_slot` | `(states, pool, now)` | Pick a slot via weighted-random; returns None if all blocked. | [src](../../../core/services/cheap_lane_balancer.py#L615) |
| function | `_central_route_shadow` | `()` | Kør central_route-sammenligning (default OFF → nul overhead). | [src](../../../core/services/cheap_lane_balancer.py#L663) |
| function | `_central_route_live` | `()` | Brug central_route's pick i stedet for den gamle sti (default OFF). | [src](../../../core/services/cheap_lane_balancer.py#L672) |
| function | `_flag_multiprofile` | `()` | Byg én slot pr. (provider, klar auth-profil) i stedet for kun entry-profilen. | [src](../../../core/services/cheap_lane_balancer.py#L681) |
| function | `_record_route_divergence` | `(old, new)` | Shadow-sammenligning: log/observe når central_route ville vælge noget andet | [src](../../../core/services/cheap_lane_balancer.py#L693) |
| function | `_central_route_slot` | `(eligible_pool, tried_slot_ids)` | Spørg central_route om lane='cheap'-pick og map til en EGNET (untried) slot i | [src](../../../core/services/cheap_lane_balancer.py#L710) |
| function | `_maybe_central_route_slot` | `(weighted_slot, eligible_pool, tried_slot_ids)` | Hook før slot bruges: shadow-compare (OFF → no-op) + live-apply. Aldrig-tør | [src](../../../core/services/cheap_lane_balancer.py#L731) |
| function | `_call_provider_chat` | `(*, provider, model, auth_profile, base_url, message)` | Wrapper around cheap_provider_runtime._execute_provider_chat. | [src](../../../core/services/cheap_lane_balancer.py#L752) |
| function | `_append_recent_call` | `(slot_id, daemon, status, latency_ms, *, error=…)` | — | [src](../../../core/services/cheap_lane_balancer.py#L777) |
| function | `recent_calls` | `()` | Returns ring-buffer of last 75 calls (newest first). | [src](../../../core/services/cheap_lane_balancer.py#L795) |
| function | `call_balanced` | `(*, prompt, daemon_name=…, max_retries=…)` | Pick a slot via weighted-random; execute; on failure retry next slot. | [src](../../../core/services/cheap_lane_balancer.py#L800) |
| function | `build_slot_pool` | `()` | Build daemon-eligible slot pool from provider_router × CHEAP_PROVIDER_DEFAULTS. | [src](../../../core/services/cheap_lane_balancer.py#L1037) |
| function | `reset_slot` | `(slot_id)` | Clear breaker, cooldown, and consecutive-failure streak for a slot. | [src](../../../core/services/cheap_lane_balancer.py#L1165) |
| function | `disable_slot` | `(slot_id)` | Force a slot's weight to 0 until enable_slot is called. | [src](../../../core/services/cheap_lane_balancer.py#L1177) |
| function | `enable_slot` | `(slot_id)` | Re-enable a manually-disabled slot. | [src](../../../core/services/cheap_lane_balancer.py#L1186) |
| function | `refresh_pool` | `()` | Re-build the slot pool from provider_router.json. Returns current size. | [src](../../../core/services/cheap_lane_balancer.py#L1195) |
| function | `_is_enabled` | `()` | Check RuntimeSettings.daemon_balancer_enabled. Default True. | [src](../../../core/services/cheap_lane_balancer.py#L1206) |
| function | `balancer_snapshot` | `()` | Return full state surface for Mission Control telemetry. | [src](../../../core/services/cheap_lane_balancer.py#L1215) |
| function | `orphan_slot_ids` | `(slot_ids, *, is_account_profile)` | Slot-ider hvis auth-profil ikke er en ægte konto. Ren udvælgelse. | [src](../../../core/services/cheap_lane_balancer.py#L1340) |
| function | `prune_orphan_slots` | `()` | Fjern state-poster for profiler balanceren aldrig vælger. Self-safe. | [src](../../../core/services/cheap_lane_balancer.py#L1360) |

## `core/services/cheap_lane_failure_policy.py`
_Hvor længe skal et cheap-lane-slot i karantæne? Afhænger af HVORFOR det fejlede._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify` | `(error_kind, message=…)` | ``'permanent'`` | ``'depleted'`` | ``'transient'``. | [src](../../../core/services/cheap_lane_failure_policy.py#L79) |
| function | `quarantine_seconds` | `(error_kind, *, retry_after_s=…, message=…)` | Karantæne-længde, eller ``0`` når slottet skal følge den normale breaker-trappe. | [src](../../../core/services/cheap_lane_failure_policy.py#L102) |

## `core/services/cheap_lane_floor.py`
_Aldrig-tør-bund for cheap lane (spec §5.5 Fund 4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `floor_targets` | `()` | Bund-kæden, config-overstyrbar. Self-safe → default ved fejl. | [src](../../../core/services/cheap_lane_floor.py#L42) |
| function | `floor_result` | `(*, lane, reason, provider=…, model=…, text=…, status=…, extra=…)` | Typet resultat der matcher pool-outputtets form. status='degraded' = tom bund. | [src](../../../core/services/cheap_lane_floor.py#L56) |
| function | `_execute_floor_target` | `(*, provider, model, message, lane)` | Kør ét bund-target gennem den eksisterende adapter. Kan rejse — indkapsles | [src](../../../core/services/cheap_lane_floor.py#L70) |
| function | `attempt_floor` | `(*, message, lane, reason)` | Prøv bund-kæden i rækkefølge. Første ikke-tomme svar vinder. Hvis ALT | [src](../../../core/services/cheap_lane_floor.py#L90) |

## `core/services/cheap_lane_selfheal.py`
_cheap_lane_selfheal — cheap-lane maa ALDRIG stale eller doe (Bjoern 16.jul)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_stale_targets` | `(limit)` | (provider, model) der skal re-probes. To kilder: | [src](../../../core/services/cheap_lane_selfheal.py#L32) |
| function | `reprobe` | `(provider, model)` | Minimalt sundheds-probe. Healer state ved succes, saetter frisk cooldown ved fejl. | [src](../../../core/services/cheap_lane_selfheal.py#L93) |
| function | `run_selfheal` | `(*, max_probes=…)` | Re-probe op til max_probes fastlaaste providere. Returnér {healed, still_down}. | [src](../../../core/services/cheap_lane_selfheal.py#L126) |

## `core/services/cheap_provider_breaker_adapters.py`
_Per-provider circuit-breaker adaptere for OllamaFreeAPI og Arko._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ofa_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L24) |
| function | `_ofa_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L31) |
| function | `_ofa_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L38) |
| function | `_arko_circuit_open` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L49) |
| function | `_arko_circuit_record_failure` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L56) |
| function | `_arko_circuit_record_success` | `()` | — | [src](../../../core/services/cheap_provider_breaker_adapters.py#L63) |

## `core/services/cheap_provider_catalogue.py`
_Kataloget over cheap-lane-udbydere — hvem findes, hvad koster de, hvad virker._

_(no top-level classes or functions)_

## `core/services/cheap_provider_runtime.py`

_(no top-level classes or functions)_

## `core/services/cheap_provider_runtime_adapters.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L24) |
| class | `CheapProviderError` | `` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L74) |
| method | `CheapProviderError.__init__` | `(self, *, provider, code, message, retry_after_seconds=…, status_code=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L75) |
| function | `supported_cheap_providers` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L92) |
| function | `provider_runtime_defaults` | `(provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L102) |
| function | `provider_cost_class` | `(provider)` | 'free' (default) eller 'paid'. Betalte providers (copilot-premium) må KUN | [src](../../../core/services/cheap_provider_runtime_adapters.py#L106) |
| function | `is_routable_provider` | `(provider)` | False = provideren må IKKE vælges i normal routing (kun evt. som nød-bund). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L113) |
| function | `_huggingface_runtime_token` | `()` | Bagudkompatibel indpakning. Se `cheap_provider_runtime_keys`. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L130) |
| function | `provider_auth_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L135) |
| function | `list_provider_models` | `(*, provider, auth_profile=…, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L180) |
| function | `_flatten_messages_to_text` | `(messages)` | Collapse a chat-message list to a single prompt string. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L254) |
| function | `_resolve_egress_proxy` | `(*, provider, auth_profile)` | Task 8b: resolve the egress proxy URL for a (provider, auth_profile) slot. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L277) |
| function | `_execute_provider_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…)` | Dispatch a single chat turn to the right provider adapter. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L296) |
| function | `_execute_openai_compatible_chat` | `(*, provider, model, auth_profile, base_url, message=…, messages=…, tools=…, temperature=…, top_p=…, extra_body=…, timeout=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L381) |
| function | `deepseek_request_for_thinking_mode` | `(model, thinking_mode)` | Map composer thinking_mode -> (model, extra_body) WITHOUT the deprecated aliases | [src](../../../core/services/cheap_provider_runtime_adapters.py#L581) |
| function | `deepseek_model_for_thinking_mode` | `(model, thinking_mode)` | Backward-compat: return only the model (never the deprecated alias). | [src](../../../core/services/cheap_provider_runtime_adapters.py#L602) |
| function | `_strip_dsml_leak` | `(buffer, in_block)` | Strip Deepseek thinking-mode tool_call DSL from streaming content. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L611) |
| function | `_execute_gemini_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L666) |
| function | `_execute_cloudflare_chat` | `(*, model, auth_profile, base_url, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L693) |
| function | `_list_openai_compatible_models` | `(*, provider, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L720) |
| function | `_list_gemini_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L745) |
| function | `_list_cloudflare_models` | `(*, auth_profile, base_url)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L762) |
| function | `_list_ollamafreeapi_models` | `()` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L786) |
| function | `_execute_ollamafreeapi_chat` | `(*, model, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L796) |
| function | `_execute_arko_chat` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L836) |
| function | `_normalize_tools_for_openai_chat` | `(tools)` | Normalize tool defs to OpenAI Chat Completions format. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L868) |
| function | `_execute_local_ollama_chat` | `(*, model, base_url, message, provider=…)` | Call an Ollama instance with a specific model. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L936) |
| function | `_execute_public_safe_local_ollama` | `(*, message)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1008) |
| function | `_require_credentials` | `(*, profile, provider)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1039) |
| function | `_http_json` | `(url, *, provider, method=…, payload=…, headers=…, proxy=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1087) |
| function | `_http_json_httpx` | `(url, *, provider, payload=…, headers=…, proxy=…, source_address=…, nat64_sni=…, timeout=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1150) |
| function | `_classify_http_error` | `(*, provider, status_code, body)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1240) |
| function | `_default_failure_cooldown_seconds` | `(code)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1268) |
| function | `_notify_checkin_required` | `(provider)` | Læg en nudge i Jarvis' awareness når en checkin-gated provider (FreeTheAi) er låst, | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1285) |
| function | `_afvis_udbyder_fejl` | `(provider, text)` | En kvote-besked leveret som modellens INDHOLD er ikke et svar. | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1307) |
| function | `_extract_openai_compatible_text` | `(*, provider, data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1337) |
| function | `_extract_gemini_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1361) |
| function | `_extract_cloudflare_text` | `(data)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1382) |
| function | `_listing_surface` | `(*, provider, auth_profile, status, source, models, base_url=…)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1402) |
| function | `_deepseek_price_table` | `(model)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1446) |
| function | `_estimate_deepseek_cost` | `(usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1458) |
| function | `_estimate_cheap_cost` | `(*, provider, usage)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1480) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/cheap_provider_runtime_adapters.py#L1491) |

## `core/services/cheap_provider_runtime_keys.py`
_Udbydere hvis ejer-nøgle bor i `runtime.json` — ikke i auth-profil-arkivet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `runtime_owner_key` | `(provider)` | Den delte ejer-nøgle for `provider`, eller "" hvis den ikke findes. | [src](../../../core/services/cheap_provider_runtime_keys.py#L40) |
| function | `has_runtime_owner_key` | `(provider)` | Bruges af readiness. Adskilt fra `runtime_owner_key` så kaldere ikke | [src](../../../core/services/cheap_provider_runtime_keys.py#L59) |

