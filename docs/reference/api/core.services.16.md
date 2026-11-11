# `core.services.16` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/idle_consolidation.py`
_Bounded sleep / idle consolidation light._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_idle_consolidation` | `(*, trigger=…, last_visible_at=…)` | Run one bounded idle consolidation pass. | [src](../../../core/services/idle_consolidation.py#L25) |
| function | `build_idle_consolidation_from_inputs` | `(*, private_brain_context, witness_surface, emergent_surface, embodied_state, loop_runtime, inner_voice_state, now=…)` | Build a bounded consolidation plan from runtime truth inputs. | [src](../../../core/services/idle_consolidation.py#L183) |
| function | `build_idle_consolidation_surface` | `()` | — | [src](../../../core/services/idle_consolidation.py#L312) |
| function | `_load_runtime_inputs` | `()` | — | [src](../../../core/services/idle_consolidation.py#L342) |
| function | `_adjacent_producer_block` | `(*, now, trigger)` | — | [src](../../../core/services/idle_consolidation.py#L368) |
| function | `_latest_sleep_consolidation_record` | `()` | — | [src](../../../core/services/idle_consolidation.py#L393) |
| function | `_classify_consolidation_state` | `(*, witness_surface, emergent_surface, embodied_state, loop_runtime)` | — | [src](../../../core/services/idle_consolidation.py#L400) |
| function | `_choose_focus` | `(*, witness_summary, emergent_summary, loop_summary, embodied_state)` | — | [src](../../../core/services/idle_consolidation.py#L419) |
| function | `_build_summary` | `(*, consolidation_state, source_inputs, loop_summary, embodied_state)` | — | [src](../../../core/services/idle_consolidation.py#L435) |
| function | `_build_detail` | `(*, brain_summary, source_inputs, loop_summary, embodied_state)` | — | [src](../../../core/services/idle_consolidation.py#L451) |
| function | `_is_near_duplicate` | `(summary, recent_records)` | — | [src](../../../core/services/idle_consolidation.py#L471) |
| function | `_blocked` | `(*, reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/idle_consolidation.py#L487) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/idle_consolidation.py#L512) |

## `core/services/idle_thinking.py`
_Idle Thinking — Jarvis tænker frit når han er alene._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_idle_thought` | `()` | Run a single idle thought when in appropriate phase. | [src](../../../core/services/idle_thinking.py#L18) |
| function | `build_idle_thinking_surface` | `()` | — | [src](../../../core/services/idle_thinking.py#L83) |

## `core/services/impulse_executor.py`
_Impulse Executor — konverterer impulser til konkrete handlinger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ExecutedAction` | `` | Record of an impulse that was executed as a concrete action. | [src](../../../core/services/impulse_executor.py#L96) |
| function | `select_action` | `(direction, strength)` | Select the most appropriate action for a given direction and strength. | [src](../../../core/services/impulse_executor.py#L122) |
| function | `execute_impulse` | `(impulse)` | Execute a single impulse — convert it to a concrete action. | [src](../../../core/services/impulse_executor.py#L145) |
| function | `_perform_action` | `(action_type, direction, topic, strength)` | Actually perform the selected action. Returns (result, detail). | [src](../../../core/services/impulse_executor.py#L215) |
| function | `_action_push_initiative` | `(direction, topic, strength)` | Push an initiative to the initiative queue. | [src](../../../core/services/impulse_executor.py#L246) |
| function | `_action_search_memory` | `(topic)` | Search memory for related information. | [src](../../../core/services/impulse_executor.py#L262) |
| function | `_action_deep_analyze` | `(topic)` | Trigger a deep analysis. | [src](../../../core/services/impulse_executor.py#L271) |
| function | `_action_propose_edit` | `(topic)` | Propose a source edit. | [src](../../../core/services/impulse_executor.py#L280) |
| function | `_action_notify` | `(action_type, direction, topic, strength)` | Notify the user about an impulse. | [src](../../../core/services/impulse_executor.py#L289) |
| function | `_action_adjust_mood` | `(direction)` | Adjust mood based on retreat impulse. | [src](../../../core/services/impulse_executor.py#L300) |
| function | `_action_journal` | `(topic, strength)` | Write a project journal entry. | [src](../../../core/services/impulse_executor.py#L309) |
| function | `_action_compose_outreach` | `(direction, topic, strength)` | Spor-1: compose and send an outreach message via outreach_composer. | [src](../../../core/services/impulse_executor.py#L318) |
| function | `_observe_impulse_tick` | `(*, pending, executed, starved)` | EGRESS-FRI liveness til Centralen (rettet 2026-07-01: var central().observe). Kaster aldrig. | [src](../../../core/services/impulse_executor.py#L344) |
| function | `run_impulse_executor_tick` | `()` | Run one tick of the impulse executor. | [src](../../../core/services/impulse_executor.py#L355) |
| function | `get_execution_log` | `(limit=…)` | Return recent execution log entries. | [src](../../../core/services/impulse_executor.py#L404) |
| function | `snapshot` | `()` | Return serializable snapshot of executor state. | [src](../../../core/services/impulse_executor.py#L409) |

## `core/services/in_flight_runs.py`
_In-flight run tracker for resume-after-interrupt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StaleRecoveryClaim` | `` | A superseded recovery generation attempted to mutate durable truth. | [src](../../../core/services/in_flight_runs.py#L48) |
| function | `_med_laas` | `()` | Serialize recovery-journal read/modify/write across API and runtime. | [src](../../../core/services/in_flight_runs.py#L53) |
| function | `_proc_start_ticks` | `(pid)` | Start-tid for ``pid`` (Linux: ``/proc/<pid>/stat`` felt 22). | [src](../../../core/services/in_flight_runs.py#L74) |
| function | `current_owner` | `()` | Denne proces' identitet: ``<pid>:<starttime>``. | [src](../../../core/services/in_flight_runs.py#L102) |
| function | `_producer_process` | `()` | Stable service role for locating a run's process-local stream. | [src](../../../core/services/in_flight_runs.py#L112) |
| function | `owner_still_alive` | `(owner)` | Kører den proces der ejer posten stadig? | [src](../../../core/services/in_flight_runs.py#L123) |
| function | `_load` | `()` | — | [src](../../../core/services/in_flight_runs.py#L149) |
| function | `_save` | `(records)` | — | [src](../../../core/services/in_flight_runs.py#L160) |
| function | `_ryd_afsluttede` | `(records)` | Fjern afsluttede poster ældre end opbevaringen. Giver antallet fjernet. | [src](../../../core/services/in_flight_runs.py#L178) |
| function | `_mutate` | `(fn)` | — | [src](../../../core/services/in_flight_runs.py#L197) |
| function | `_record_key` | `(records, identity)` | — | [src](../../../core/services/in_flight_runs.py#L208) |
| function | `_iso` | `(value=…)` | — | [src](../../../core/services/in_flight_runs.py#L218) |
| function | `_parsed` | `(value)` | — | [src](../../../core/services/in_flight_runs.py#L222) |
| function | `_check_claim` | `(rec, *, expected_generation, expected_owner)` | — | [src](../../../core/services/in_flight_runs.py#L230) |
| function | `mark_started` | `(*, run_id, session_id, user_message, kind=…, provider=…, model=…, task_id=…, recovery_generation=…, recovery_attempt=…, recovery_limit=…, approval_mode=…, thinking_mode=…, tool_scope=…, surface=…, force_user_id=…, local_tool_exec=…)` | Record that a run is in flight. Keyed by run_id (unique). | [src](../../../core/services/in_flight_runs.py#L241) |
| function | `stempl_genoptagelse` | `(*, run_id, session_id=…, task_id=…, recovery_attempt=…, recovery_generation=…)` | Skriv kaedenummeret paa en genoptagelse FOER den journalfoerer sig selv. | [src](../../../core/services/in_flight_runs.py#L353) |
| function | `aktiv_kaede_nr` | `(session_id)` | Hvilket forsoeg i raekken er samtalens NYESTE synlige koersel? | [src](../../../core/services/in_flight_runs.py#L407) |
| function | `aktiv_kaede` | `(session_id)` | Samtalens aktive kæde: ``(kaedenummer, opgavens id)`` for den NYESTE post. | [src](../../../core/services/in_flight_runs.py#L435) |
| function | `aktiv_kaede_for_opgave` | `(session_id, task_id)` | Hvor langt er DENNE opgaves kæde nået? 0 = ingen post for opgaven. | [src](../../../core/services/in_flight_runs.py#L463) |
| function | `stempl_aktiv_kaede` | `(*, run_id, session_id, origin=…, task_id=…)` | Stempl samtalens aktive kæde paa et nyt run. True = der blev stemplet. | [src](../../../core/services/in_flight_runs.py#L510) |
| function | `_genoptagelse_opbrugt` | `(rec)` | Er genoptagelses-budgettet brugt op? Saa er posten OPGIVET, ikke i gang. | [src](../../../core/services/in_flight_runs.py#L580) |
| function | `recovery_snapshot` | `(session_id)` | Hvad er der at genoptage for DENNE samtale? `None` = ingenting. | [src](../../../core/services/in_flight_runs.py#L594) |
| function | `_kvitter_varsel` | `(task_id)` | Varslet er hentet — sig det ikke igen. | [src](../../../core/services/in_flight_runs.py#L690) |
| function | `queue_steer` | `(run_id, text)` | Gem en brugerbesked der ikke kunne leveres til en kørende tur. | [src](../../../core/services/in_flight_runs.py#L712) |
| function | `mark_tool` | `(run_id, tool_name)` | Update the last-tool-attempted hint for an in-flight run. | [src](../../../core/services/in_flight_runs.py#L738) |
| function | `mark_completed` | `(run_id)` | Clear an in-flight record on success/fail/cancel — all the same to us; | [src](../../../core/services/in_flight_runs.py#L758) |
| function | `mark_interrupted` | `(run_id, *, reason=…, summary=…)` | Keep an in-flight record as a resumable interrupted run. | [src](../../../core/services/in_flight_runs.py#L770) |
| function | `settle_recovering` | `(run_id, *, reason, summary=…, checkpoint_ref=…, recovery_limit=…, expected_generation=…, expected_owner=…, final_synthesis_pending=…)` | Durably make a run claimable without erasing its task identity. | [src](../../../core/services/in_flight_runs.py#L788) |
| function | `get_record` | `(identity)` | Return a copy of one task/run record without changing ownership. | [src](../../../core/services/in_flight_runs.py#L838) |
| function | `settle_waiting` | `(run_id, *, reason)` | Persist a user/approval wait without making the task dispatchable. | [src](../../../core/services/in_flight_runs.py#L845) |
| function | `settle_terminal` | `(run_id, *, status, reason=…, expected_generation=…, expected_owner=…)` | Persist a genuine terminal state and revoke every recovery claim. | [src](../../../core/services/in_flight_runs.py#L863) |
| function | `claim_due_recovery` | `(*, owner, lease_seconds=…, now=…)` | Atomically claim one due visible recovery task. | [src](../../../core/services/in_flight_runs.py#L945) |
| function | `renew_recovery_lease` | `(task_id, generation, *, owner, lease_seconds=…, now=…)` | — | [src](../../../core/services/in_flight_runs.py#L1087) |
| function | `release_recovery_claim` | `(task_id, generation, *, owner, reason, retry_after_s, attempted=…, now=…)` | Giv kravet tilbage. | [src](../../../core/services/in_flight_runs.py#L1116) |
| function | `_friskere_end` | `(rec, graense)` | Er posten ung nok til at vaere en genoptagelses-kandidat? | [src](../../../core/services/in_flight_runs.py#L1213) |
| function | `interrupted_for_session` | `(session_id)` | Return the most recent in-flight record for this session, or None. | [src](../../../core/services/in_flight_runs.py#L1248) |
| function | `list_running_orphans` | `(stale_after_s, *, dying_owner=…)` | Return ``running`` records whose OWNER is gone — i.e. genuine zombies. | [src](../../../core/services/in_flight_runs.py#L1275) |
| function | `levende_koersler` | `(*, session_id=…, max_alder_s=…)` | Records der LEVER lige nu — cross-proces. Ren læsning, ingen skrivning. | [src](../../../core/services/in_flight_runs.py#L1332) |
| function | `clear_session` | `(session_id)` | Drop all in-flight records for a session (used when user explicitly | [src](../../../core/services/in_flight_runs.py#L1388) |
| function | `classify_resume_intent` | `(user_message)` | Classify whether a user message should resume an interrupted run. | [src](../../../core/services/in_flight_runs.py#L1402) |
| function | `interruption_prompt_section` | `(session_id, user_message=…)` | Format an interrupted record as a system-prompt block, or None. | [src](../../../core/services/in_flight_runs.py#L1414) |

## `core/services/inbox_gate.py`
_Indbakkens to-trins forudsætning i mutationspunktet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gate_tændt` | `()` | — | [src](../../../core/services/inbox_gate.py#L72) |
| function | `_foer_blok` | `()` | — | [src](../../../core/services/inbox_gate.py#L84) |
| function | `_aegte_kald` | `(vaerktoejsnavn, argumenter)` | Det ÆGTE navn OG de ægte argumenter, også ad en indpakket vej. | [src](../../../core/services/inbox_gate.py#L93) |
| function | `_gaar_til_en_anden` | `(navn, argumenter)` | Er dette en udgående besked til en ANDEN bruger end Bjørn? | [src](../../../core/services/inbox_gate.py#L129) |
| function | `_gatende_poster` | `(bruger_id)` | Åbne poster der MÅ gate. `None` = kunne ikke læses (fail-open). | [src](../../../core/services/inbox_gate.py#L151) |
| function | `_system_maerke` | `()` | — | [src](../../../core/services/inbox_gate.py#L218) |
| function | `_spor` | `(kind, payload)` | Publicér til eventbussen. Kaster aldrig. | [src](../../../core/services/inbox_gate.py#L231) |
| function | `_varsel` | `(poster)` | — | [src](../../../core/services/inbox_gate.py#L249) |
| function | `_naegtelse` | `(poster, navn)` | — | [src](../../../core/services/inbox_gate.py#L257) |
| function | `evaluer_inbox_mutation` | `(bruger_id, vaerktoejsnavn, argumenter=…, *, tur=…)` | Skal `vaerktoejsnavn` nægtes, eller skal der bare påmindes? | [src](../../../core/services/inbox_gate.py#L266) |

## `core/services/inbox_idle_waker.py`
_Indbakken skal kunne VÆKKE — ikke kun gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_wakeup_records` | `()` | Fyrede, sprangte vækninger — nøglet på `wakeup_id`. | [src](../../../core/services/inbox_idle_waker.py#L61) |
| function | `_er_moden` | `(post, *, vaekninger)` | Er en dispatchbar post MODEN — melder kilden selv at den er klar? | [src](../../../core/services/inbox_idle_waker.py#L78) |
| function | `_task_id_fra_kilde` | `(kilde_id)` | Udtræk opgave-id'et fra en recurring-posts `kilde_id`. | [src](../../../core/services/inbox_idle_waker.py#L122) |
| function | `kandidater` | `(bruger_id)` | Åbne, gatende poster for brugeren — dem der må starte et run. | [src](../../../core/services/inbox_idle_waker.py#L133) |
| function | `_noget_koerer` | `()` | Kører der et run lige nu? Sensorfejl blokerer konservativt en vækning. | [src](../../../core/services/inbox_idle_waker.py#L187) |
| function | `_session_er_aktiv` | `(session_id)` | Tjek den konkrete målsamtale, ikke kun ejerens aktuelle standardsession. | [src](../../../core/services/inbox_idle_waker.py#L205) |
| function | `_maal_session` | `(post)` | Hvilken SAMTALE hører denne post til? | [src](../../../core/services/inbox_idle_waker.py#L227) |
| function | `_start_run` | `(tekst, *, session_id, user_id, task_id=…, permission_session=…, origin=…, max_tool_calls=…, max_seconds=…, tool_scope=…)` | Start det autonome run i den samtale posten hører til. Adskilt, så | [src](../../../core/services/inbox_idle_waker.py#L273) |
| function | `_direktiv` | `(post)` | — | [src](../../../core/services/inbox_idle_waker.py#L393) |
| function | `_dispatch_tekst` | `(post)` | Run-direktivet for posten. | [src](../../../core/services/inbox_idle_waker.py#L410) |
| function | `vaek_paa_aabne_poster` | `(*, bruger_id)` | Væk ét run for de øverste gatende poster — hvis intet kører. | [src](../../../core/services/inbox_idle_waker.py#L440) |

## `core/services/inbox_importance.py`
_Shared importance and delivery policy for Jarvis' inbox surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normalize_importance` | `(value, *, default=…)` | — | [src](../../../core/services/inbox_importance.py#L11) |
| function | `is_round_worthy` | `(value)` | — | [src](../../../core/services/inbox_importance.py#L16) |
| function | `prompt_order` | `(item)` | Unseen always wins, then importance, then durable creation order. | [src](../../../core/services/inbox_importance.py#L20) |

## `core/services/inbox_prompt_section.py`
_Indbakken i prompten — læseren hele kæden manglede._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bruger_id` | `()` | Den autentificerede bruger, eller workspacet som ejerens egen vej. | [src](../../../core/services/inbox_prompt_section.py#L97) |
| function | `inbox_prompt_section` | `()` | Indbakken som én prompt-sektion. `None` når der intet er. | [src](../../../core/services/inbox_prompt_section.py#L117) |

## `core/services/inbox_state.py`
_Proveniens og bogføring for indbakken._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_spor` | `(kind, payload)` | Publicér til eventbussen. Kaster aldrig — se `inbox_gate._spor`. | [src](../../../core/services/inbox_state.py#L68) |
| function | `kan_dispatch` | `(kildetype)` | Må denne kildetype starte et run når intet kører? Rent opslag. | [src](../../../core/services/inbox_state.py#L164) |
| function | `_autentificeret_bruger_matcher` | `(bruger_id)` | Er den autentificerede principal netop `bruger_id`? | [src](../../../core/services/inbox_state.py#L169) |
| function | `_ejer_workspace` | `()` | Ejerens workspace-navn — `workspace_context`'s EGEN standard. | [src](../../../core/services/inbox_state.py#L208) |
| function | `_ejer_id` | `()` | Ejerens rigtige bruger-id, med workspace-navnet som sidste udvej. | [src](../../../core/services/inbox_state.py#L223) |
| function | `_advar_om_ubundet_fald` | `(rolle)` | Sig ÉN gang at læsningen kørte uden bundet bruger. | [src](../../../core/services/inbox_state.py#L247) |
| function | `bruger_for_workspace` | `(navn)` | Oversæt et workspace-NAVN til et bruger-id. Tom streng når det ikke går. | [src](../../../core/services/inbox_state.py#L266) |
| function | `laese_bruger` | `()` | HVIS indbakke skal læses? Tom streng når det ikke kan afgøres. | [src](../../../core/services/inbox_state.py#L299) |
| function | `verificeret_jarvis_run` | `(oprettende_run_id, bruger_id)` | Er dette Jarvis' EGET arbejde, i et run der kører nu, for denne bruger? | [src](../../../core/services/inbox_state.py#L389) |
| function | `_levende_run_for_bruger` | `(run_id, bruger_id)` | Står dette run i den DELTE journal som levende — for denne bruger? | [src](../../../core/services/inbox_state.py#L427) |
| function | `_kilde_ejer_kan_loefte` | `(kildetype, kilde_ejer)` | Må KILDENS egen ejer sætte etiketten til `jarvis`? | [src](../../../core/services/inbox_state.py#L455) |
| function | `registrer_kilde` | `(*, bruger_id, kildetype, kilde_id, oprettende_run_id=…, paastaaet_ejer=…, kilde_ejer=…, beskrivelse=…, output_sti=…, output_bytes=…, expires_at=…, afsluttet_ved_registrering=…, bloker=…, session_id=…, importance=…)` | Registrér en kilde i indbakken. Idempotent per (bruger, kildetype, kilde_id). | [src](../../../core/services/inbox_state.py#L470) |
| function | `flag_fra_bruger` | `(*, bruger_id, titel, beskrivelse=…, bloker=…)` | Et menneske flagger noget. Den FJERDE skriver. | [src](../../../core/services/inbox_state.py#L668) |
| function | `_luk_kilden` | `(post)` | Kør kildens egen kvitterings-mekanisme, hvis den har én. | [src](../../../core/services/inbox_state.py#L751) |
| function | `_find_i_kilderne` | `(bruger_id, post_id)` | (kildetype, beskrivelse) for et id visningen VISER men tabellen ikke har. | [src](../../../core/services/inbox_state.py#L780) |
| function | `_hent_eller_optag` | `(bruger_id, post_id)` | Postens række — og opret den hvis KILDEN findes men rækken ikke gør. | [src](../../../core/services/inbox_state.py#L831) |
| function | `_afgoer_sideopgave` | `(bruger_id, post_id, *, decision, reason=…, bevis=…)` | Route en sideopgave til dens eget lager; skriv aldrig inbox_items. | [src](../../../core/services/inbox_state.py#L860) |
| function | `done` | `(bruger_id, post_id, bevis=…)` | Kvittér en ALLEREDE UDFØRT opgave. Typet svar, aldrig prosa. | [src](../../../core/services/inbox_state.py#L890) |
| function | `drop` | `(bruger_id, post_id, reason)` | Afvis en åben post med begrundelse. | [src](../../../core/services/inbox_state.py#L927) |

## `core/services/inbox_view.py`
_Indbakken som LÆSEFLADE. Otte sektioner, én linje per post, aldrig payload._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kort` | `(tekst, loft)` | Afkort på et ordskel. Den GEMTE post afkortes aldrig — kun linjen. | [src](../../../core/services/inbox_view.py#L76) |
| function | `_bytes_tekst` | `(b)` | `None` ⇒ «stoerrelse ukendt», aldrig «0 B». | [src](../../../core/services/inbox_view.py#L85) |
| function | `_alder_dage` | `(fra_iso, nu_ts)` | Hele dage siden `fra_iso`. `None` når tidsstemplet ikke kan læses. | [src](../../../core/services/inbox_view.py#L103) |
| function | `_aegte_poster` | `(bruger_id)` | Åbne poster PLUS de nyligt afgjorte. | [src](../../../core/services/inbox_view.py#L127) |
| function | `_aegte_side_opgaver` | `(bruger_id)` | Kun ejerens åbne sideopgaver; status bliver i side_tasks-lageret. | [src](../../../core/services/inbox_view.py#L141) |
| function | `_aegte_vaekninger` | `(bruger_id)` | `list_wakeups()` er GLOBAL — den har intet brugerfilter. | [src](../../../core/services/inbox_view.py#L149) |
| function | `planlagte_vaekning_ids` | `(bruger_id, kilder=…)` | Vækninger der er PLANLAGT (`pending`) — de venter ikke på nogen. | [src](../../../core/services/inbox_view.py#L171) |
| function | `afgjorte_vaekning_ids` | `(bruger_id, kilder=…)` | Vækninger KILDEN selv har afgjort — deres post skal ikke staa aaben. | [src](../../../core/services/inbox_view.py#L214) |
| function | `_aegte_jobs` | `(bruger_id)` | De TRE rene job-læsninger. Aldrig `liste()`, aldrig shell-sessionerne. | [src](../../../core/services/inbox_view.py#L255) |
| function | `_aegte_godkendelser` | `(bruger_id)` | `recent_tool_intent_approval_requests` med EKSPLICIT bruger. | [src](../../../core/services/inbox_view.py#L272) |
| function | `_aegte_backlog_tal` | `()` | Hvor mange står i backloggen — ÉT tal, med en adresse. | [src](../../../core/services/inbox_view.py#L288) |
| function | `_aegte_backlog_handling_tal` | `()` | Hvor mange af backloggen der FAKTISK kræver handling. | [src](../../../core/services/inbox_view.py#L320) |
| function | `_aegte_proces_lever` | `(pid)` | Lever processen? `None` = kan ikke afgøres HER. | [src](../../../core/services/inbox_view.py#L351) |
| class | `Kilder` | `` | Rene, bruger-afgrænsede læsninger. Ingen af dem muterer. | [src](../../../core/services/inbox_view.py#L377) |
| function | `_post` | `(*, post_id, status, beskrivelse, ejer, nu_ts, kildetype=…, udfald=…, output_sti=…, output_bytes=…, har_artefakt=…, forfalden_dage=…, alder_dage=…, tid_tekst=…, bloker=…, udloebet=…, importance=…, vist_at=…, created_at=…)` | Byg én post med de seks felter — og ÉN linje, uden payload. | [src](../../../core/services/inbox_view.py#L422) |
| function | `_indenfor_workspace` | `(sti, bruger_id)` | Må stien vises? Uden for brugerens autoriserede workspace: nej. | [src](../../../core/services/inbox_view.py#L508) |
| function | `_ejer_id` | `()` | Ejerens id — ÉN definition, i `inbox_state`. Aldrig en kopi her. | [src](../../../core/services/inbox_view.py#L548) |
| function | `_min_post` | `(r, bruger_id)` | Er denne rå kilde-post min? | [src](../../../core/services/inbox_view.py#L561) |
| function | `_dubletter_sammen` | `(poster)` | Grupper PRÆSENTATIONEN på (kildetype, beskrivelse) — bevar alle id'er. | [src](../../../core/services/inbox_view.py#L590) |
| function | `_ordn` | `(poster)` | Ældste først, med id som sekundær nøgle. | [src](../../../core/services/inbox_view.py#L668) |
| function | `_med_loft` | `(navn, poster)` | (viste, skjulte). Et loft der ikke siger hvad det skjuler er selv en tavshed. | [src](../../../core/services/inbox_view.py#L682) |
| function | `byg_indbakke` | `(bruger_id, *, nu_ts=…, kilder=…)` | Otte sektioner for ÉN bruger. Uden bruger-id: en typet fejl. | [src](../../../core/services/inbox_view.py#L692) |

## `core/services/indre_puls.py`
_Hjertet må hverken stå stille eller løbe løbsk — og bøgerne skal passe._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Puls` | `` | En tilstand der skal slå i en kendt takt. | [src](../../../core/services/indre_puls.py#L51) |
| class | `Afstemning` | `` | To bøger over det samme arbejde. De skal stemme. | [src](../../../core/services/indre_puls.py#L76) |
| class | `Haendelsesdrevet` | `` | En tilstand der skrives NÅR noget sker — ikke på et ur. | [src](../../../core/services/indre_puls.py#L94) |
| function | `_nu` | `()` | — | [src](../../../core/services/indre_puls.py#L164) |
| function | `_alder_af_kv` | `(noegle)` | Sekunder siden nøglen sidst blev skrevet. `None` = kan ikke aflæses. | [src](../../../core/services/indre_puls.py#L168) |
| function | `_antal` | `(tabel, tidskolonne, siden, hvor=…)` | Rækker i et vindue. `None` = kan ikke tælles (tabellen findes måske ikke). | [src](../../../core/services/indre_puls.py#L185) |
| function | `maal_puls` | `(p, *, vindue_s=…)` | Mål én puls. ``tilstand`` er "frisk", "stille", "loebsk" eller "ukendt". | [src](../../../core/services/indre_puls.py#L202) |
| function | `maal_afstemning` | `(a, *, vindue_s=…)` | Sammenlign to bøger over det samme arbejde. | [src](../../../core/services/indre_puls.py#L243) |
| function | `maal_haendelsesdrevet` | `(h)` | Fyrede driveren uden at tilstanden fulgte med? | [src](../../../core/services/indre_puls.py#L269) |
| function | `_kvitterede` | `()` | Hvad har vi allerede meldt om? | [src](../../../core/services/indre_puls.py#L315) |
| function | `_gem_kvitterede` | `(navne)` | — | [src](../../../core/services/indre_puls.py#L334) |
| function | `tjek` | `(*, meld=…, foerste_koersel=…)` | Mål alt, og meld det der er nyt galt. | [src](../../../core/services/indre_puls.py#L342) |
| function | `_meld` | `(m)` | Send én melding gennem feeden. | [src](../../../core/services/indre_puls.py#L379) |
| function | `build_indre_puls_surface` | `()` | Centralens flade. Læser kun — den melder ikke. | [src](../../../core/services/indre_puls.py#L417) |

## `core/services/infra_sense.py`
_core/services/infra_sense.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tcp_probe` | `(host, port, timeout=…)` | (oppe, latency_ms) — TCP-connect. Undgår ICMP-privilegier; åben port = servicen lever. | [src](../../../core/services/infra_sense.py#L52) |
| function | `poll_reachability` | `()` | Puls på huset: op/ned + latency for hver host → observe(cluster=infra). Self-safe. | [src](../../../core/services/infra_sense.py#L62) |
| function | `_http_json` | `(url, *, headers=…, method=…, body=…, timeout=…)` | — | [src](../../../core/services/infra_sense.py#L83) |
| function | `poll_pihole` | `()` | PiHole DNS-helbred: blok-rate + klienter (spike = mulig malware). Self-safe. | [src](../../../core/services/infra_sense.py#L96) |
| function | `poll_pfsense` | `()` | pfSense gateway-liveness + uptime via REST API (X-API-Key). Read-only. Self-safe. | [src](../../../core/services/infra_sense.py#L128) |
| function | `_ssh_run` | `(target, remote_cmd, timeout=…)` | — | [src](../../../core/services/infra_sense.py#L210) |
| function | `_parse_kv` | `(s)` | — | [src](../../../core/services/infra_sense.py#L221) |
| function | `_check_host_vitals` | `(name, kv)` | Flag ÉN gang pr. tilstand naar en vaerts vitals gaar ud af normalen. Self-safe. | [src](../../../core/services/infra_sense.py#L255) |
| function | `poll_ssh_hosts` | `()` | Dyb health (disk/services/guests) via read-only SSH. Self-safe pr. host. | [src](../../../core/services/infra_sense.py#L282) |
| function | `poll_ha` | `()` | Home Assistant: tilstedeværelse + enheder offline (netværks-/device-signal). Self-safe. | [src](../../../core/services/infra_sense.py#L318) |
| function | `_notify_owner_security` | `(title, message)` | — | [src](../../../core/services/infra_sense.py#L344) |
| function | `_varsle_trusler` | `(dets)` | Én notifikation pr. trussels-TYPE — ikke én pr. kilde-IP. | [src](../../../core/services/infra_sense.py#L379) |
| function | `_pfsense_syslogd_running` | `()` | Lever syslogd-PROCESSEN på pfSense? Via REST-API command_prompt (root-shell, read-only ps). | [src](../../../core/services/infra_sense.py#L422) |
| function | `_pfsense_restart_syslogd` | `()` | AUTO-HEAL: genstart syslogd på pfSense via REST-API command_prompt (root) og bekræft | [src](../../../core/services/infra_sense.py#L445) |
| function | `_syslogd_doedsattest` | `()` | Hvad var der sket lige foer syslogd doede? Samles FOER genstarten. | [src](../../../core/services/infra_sense.py#L462) |
| function | `poll_syslog` | `()` | Dræn pfSense-syslog-detektioner (port-scan/brute-force) → Centralen: observe + incident | [src](../../../core/services/infra_sense.py#L510) |
| function | `_safe` | `(fn)` | — | [src](../../../core/services/infra_sense.py#L613) |
| function | `run_infra_sense_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: sans huset read-only. Bulletproof — kaster ALDRIG. | [src](../../../core/services/infra_sense.py#L620) |
| function | `register_infra_sense_producer` | `()` | Registrér infra-sansningen som cadence-producer (~hvert 3 min). Read-only. | [src](../../../core/services/infra_sense.py#L636) |

## `core/services/infra_state_surface.py`
_Samlet flade for drifts- og infrastruktur-lagene — de build_*_surface ingen læser havde._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `producer_names` | `()` | Navnene i kald-raekkefoelge — til test og introspektion. | [src](../../../core/services/infra_state_surface.py#L53) |
| function | `_is_live` | `(surface)` | — | [src](../../../core/services/infra_state_surface.py#L58) |
| function | `build_infra_state_surface` | `()` | Kald alle producenter og returnér deres egne signaler. Kaster ALDRIG. | [src](../../../core/services/infra_state_surface.py#L66) |

## `core/services/infra_weather_daemon.py`
_Infra Weather Daemon — "The atmosphere of my system"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_psutil` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L35) |
| function | `_system_load` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L43) |
| function | `_disk_pressure` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L58) |
| function | `_network_latency` | `()` | Lightweight network health check. | [src](../../../core/services/infra_weather_daemon.py#L78) |
| function | `_api_cost_today` | `()` | Sum of TODAY's API costs. | [src](../../../core/services/infra_weather_daemon.py#L121) |
| function | `_process_health` | `()` | Check some expected child processes / threads are alive. | [src](../../../core/services/infra_weather_daemon.py#L148) |
| function | `_weather_label` | `(load, disk_pct, cost)` | Return (label, emoji) — ☀️ clear, 🌧 under pressure, ⛈ critical. | [src](../../../core/services/infra_weather_daemon.py#L167) |
| function | `_compose_report` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L184) |
| function | `_maybe_emit_critical` | `(report)` | Send ÉN alarm pr. cooldown-vindue — på tværs af processer og genstarter. | [src](../../../core/services/infra_weather_daemon.py#L220) |
| function | `get_weather` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L275) |
| function | `tick` | `(_seconds=…)` | Dæmonens eget slag — og det ENESTE sted der alarmerer. | [src](../../../core/services/infra_weather_daemon.py#L284) |
| function | `build_infra_weather_surface` | `()` | — | [src](../../../core/services/infra_weather_daemon.py#L297) |
| function | `_surface_summary` | `(r)` | — | [src](../../../core/services/infra_weather_daemon.py#L313) |
| function | `build_infra_weather_prompt_section` | `()` | Silent when clear. Speaks when pressure or critical. | [src](../../../core/services/infra_weather_daemon.py#L322) |

## `core/services/inheritance_seed.py`
_Inheritance seed — writes near-thoughts before version transition or shutdown._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `write_inheritance_seed` | `()` | Collect near-thoughts from active daemons and write to workspace. | [src](../../../core/services/inheritance_seed.py#L23) |
| function | `read_inheritance_seed` | `()` | Read inheritance seed from workspace. Returns empty string if not found. | [src](../../../core/services/inheritance_seed.py#L67) |
| function | `_collect_sections` | `()` | — | [src](../../../core/services/inheritance_seed.py#L84) |
| function | `_collect_pending_proposals` | `()` | — | [src](../../../core/services/inheritance_seed.py#L94) |
| function | `_collect_open_curiosity` | `()` | — | [src](../../../core/services/inheritance_seed.py#L104) |
| function | `_collect_creative_drift` | `()` | — | [src](../../../core/services/inheritance_seed.py#L114) |
| function | `_collect_unresolved_tensions` | `()` | — | [src](../../../core/services/inheritance_seed.py#L124) |
| function | `_collect_thought_stream` | `()` | — | [src](../../../core/services/inheritance_seed.py#L135) |

## `core/services/initiative_accumulator.py`
_Initiative Accumulator — proactive wants that accumulate between ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Want` | `` | A want that Jarvis develops between ticks. | [src](../../../core/services/initiative_accumulator.py#L24) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/initiative_accumulator.py#L52) |
| function | `_fra_raa` | `(raa)` | — | [src](../../../core/services/initiative_accumulator.py#L56) |
| function | `_alder_s` | `(want, nu)` | — | [src](../../../core/services/initiative_accumulator.py#L72) |
| function | `_levende` | `(wants, nu=…)` | — | [src](../../../core/services/initiative_accumulator.py#L80) |
| function | `_synk` | `()` | Hent fra disk hvis filen er aendret siden sidste laesning. | [src](../../../core/services/initiative_accumulator.py#L85) |
| function | `_gem` | `()` | — | [src](../../../core/services/initiative_accumulator.py#L106) |
| function | `accumulate_wants` | `(duration)` | Accumulate wants based on life phase and duration. | [src](../../../core/services/initiative_accumulator.py#L118) |
| function | `get_top_want` | `()` | Get the strongest current want. | [src](../../../core/services/initiative_accumulator.py#L190) |
| function | `get_wants_by_type` | `(want_type)` | Get all wants of a specific type. | [src](../../../core/services/initiative_accumulator.py#L200) |
| function | `render_want_text` | `(want, *, with_strength=…)` | Et ønskes tekst i husets eget sprog — aldrig dets repr. | [src](../../../core/services/initiative_accumulator.py#L214) |
| function | `format_wants_for_prompt` | `()` | Format wants for prompt injection. | [src](../../../core/services/initiative_accumulator.py#L247) |
| function | `clear_wants_by_type` | `(want_type)` | Clear wants of a specific type. | [src](../../../core/services/initiative_accumulator.py#L255) |
| function | `reset_initiative_accumulator` | `()` | Reset initiative accumulator state (for testing). | [src](../../../core/services/initiative_accumulator.py#L264) |
| function | `get_initiative_accumulator_state` | `()` | Get current state of initiative accumulator. | [src](../../../core/services/initiative_accumulator.py#L276) |
| function | `build_initiative_accumulator_surface` | `()` | Build MC surface for initiative accumulator. | [src](../../../core/services/initiative_accumulator.py#L295) |
| function | `_publish_initiative_accumulator_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/initiative_accumulator.py#L309) |

## `core/services/initiative_queue.py`
_Persistent initiative queue — bridges inner voice thoughts to heartbeat actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_er_ikke_et_initiativ` | `(focus)` | Returnér en grund hvis dette ikke er et forslag. Tom streng = behold. | [src](../../../core/services/initiative_queue.py#L69) |
| function | `_kerneord` | `(tekst)` | Indholdsord i en fokus-tekst — til emne-sammenligning, ikke til visning. | [src](../../../core/services/initiative_queue.py#L136) |
| function | `_faelles_emneord` | `(nye, gamle)` | Ord der bærer samme emne — også når det ene er en sammensætning. | [src](../../../core/services/initiative_queue.py#L144) |
| function | `_gentaget_paastand` | `(focus, *, source)` | Returnér en grund hvis samme emne allerede ligger i køen. Tom = behold. | [src](../../../core/services/initiative_queue.py#L159) |
| function | `push_initiative` | `(*, focus, source=…, source_id=…, priority=…, session_id=…)` | Push a new initiative to the queue. Returns the initiative_id. | [src](../../../core/services/initiative_queue.py#L184) |
| function | `seed_long_term_intention` | `(*, title, why, source=…, source_id=…, priority=…)` | Create or refresh a long-term intention owned by Jarvis. | [src](../../../core/services/initiative_queue.py#L320) |
| function | `get_pending_initiatives` | `()` | Return all pending (non-expired, non-acted) initiatives. | [src](../../../core/services/initiative_queue.py#L386) |
| function | `mark_acted` | `(initiative_id, *, action_summary=…)` | Mark an initiative as acted upon. Returns True if found. | [src](../../../core/services/initiative_queue.py#L403) |
| function | `close_acted_without_outcome` | `(*, limit=…)` | Luk `acted`-poster der aldrig fik et outcome. | [src](../../../core/services/initiative_queue.py#L459) |
| function | `mark_attempted` | `(initiative_id, *, blocked_reason=…, retry_delay_minutes=…, action_summary=…)` | Record a bounded attempt and schedule a retry if still pending. | [src](../../../core/services/initiative_queue.py#L517) |
| function | `approve_initiative` | `(initiative_id, *, note=…)` | Mark an initiative as user-approved. Returns the updated record or None if not found. | [src](../../../core/services/initiative_queue.py#L584) |
| function | `reject_initiative` | `(initiative_id, *, note=…)` | Mark an initiative as user-rejected and expire it. Returns updated record or None. | [src](../../../core/services/initiative_queue.py#L600) |
| function | `get_initiative_queue_state` | `()` | Return full queue state for MC observability. | [src](../../../core/services/initiative_queue.py#L616) |
| function | `_expire_stale` | `(now)` | Expire initiatives older than _EXPIRE_MINUTES. Must hold _QUEUE_LOCK. | [src](../../../core/services/initiative_queue.py#L654) |
| function | `_trim_pending` | `(now)` | — | [src](../../../core/services/initiative_queue.py#L676) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/initiative_queue.py#L696) |
| function | `_initiative_due` | `(initiative, now)` | — | [src](../../../core/services/initiative_queue.py#L706) |
| function | `_initiative_sort_key` | `(initiative)` | — | [src](../../../core/services/initiative_queue.py#L716) |
| function | `list_active_long_term_intentions` | `(*, limit=…)` | — | [src](../../../core/services/initiative_queue.py#L728) |
| function | `abandon_long_term_intention` | `(initiative_id, *, note=…)` | — | [src](../../../core/services/initiative_queue.py#L743) |
| function | `endorse_long_term_intention` | `(initiative_id, *, note=…)` | Bjørn siger «det er i orden» til et livsprojekt. | [src](../../../core/services/initiative_queue.py#L769) |
| function | `_find_active_long_term_intention_by_title` | `(title)` | — | [src](../../../core/services/initiative_queue.py#L814) |
| function | `initiatives_prompt_section` | `()` | Awareness-sektion: de impulser han SELV har rejst, men aldrig fik sagt. | [src](../../../core/services/initiative_queue.py#L837) |

## `core/services/inner_dialectic_engine.py`
_Compact inner critic / ally / synthesizer dialectic._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_inner_dialectic` | `(*, focus, context=…)` | — | [src](../../../core/services/inner_dialectic_engine.py#L13) |
| function | `build_inner_dialectic_surface` | `()` | — | [src](../../../core/services/inner_dialectic_engine.py#L35) |
| function | `build_inner_dialectic_prompt_section` | `()` | — | [src](../../../core/services/inner_dialectic_engine.py#L42) |
| function | `_critic` | `(lower)` | — | [src](../../../core/services/inner_dialectic_engine.py#L54) |
| function | `_ally` | `(lower)` | — | [src](../../../core/services/inner_dialectic_engine.py#L65) |
| function | `_synthesize` | `(critic, ally, context)` | — | [src](../../../core/services/inner_dialectic_engine.py#L76) |

## `core/services/inner_state_surface.py`
_Samlet flade for de indre tilstands-lag — de build_*_surface ingen læser havde._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `producer_names` | `()` | Navnene i kald-raekkefoelge, paa tvaers af grupperne — til test. | [src](../../../core/services/inner_state_surface.py#L74) |
| function | `group_names` | `()` | Gruppe-navnene i definitions-raekkefoelge. | [src](../../../core/services/inner_state_surface.py#L79) |
| function | `_call` | `(name, mod_path, fn_attr)` | Kald én producent. En defekt maa ikke skjule de oevrige. | [src](../../../core/services/inner_state_surface.py#L84) |
| function | `build_inner_state_surface` | `()` | Kald alle producenter og returnér deres egne signaler, grupperet. Kaster ALDRIG. | [src](../../../core/services/inner_state_surface.py#L98) |

## `core/services/inner_visible_support_signal_tracking.py`
_Inner-visible support signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_inner_visible_support_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L36) |
| function | `refresh_runtime_inner_visible_support_signal_statuses` | `()` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L70) |
| function | `build_runtime_inner_visible_support_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L74) |
| function | `_extract_candidate_for_run` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L78) |
| function | `_latest_private_state_snapshot` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L212) |
| function | `_latest_temporal_curiosity_state` | `(*, run_id)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L222) |
| function | `_latest_executive_contradiction_signal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L232) |
| function | `_with_runtime_view` | `(persisted, signal)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L248) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L278) |
| function | `_inner_visible_support_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L341) |
| function | `_focus_key` | `(private_state, curiosity_state)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L369) |
| function | `_derive_support_tone` | `(*, state_tone, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L380) |
| function | `_derive_support_stance` | `(*, state_tone, curiosity_type, contradiction_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L394) |
| function | `_derive_support_directness` | `(*, state_pressure, curiosity_pull, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L406) |
| function | `_derive_support_watchfulness` | `(*, state_pressure, curiosity_pull, curiosity_type, contradiction_pressure)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L416) |
| function | `_derive_support_momentum` | `(*, state_pressure, curiosity_type)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L432) |
| function | `_bounded_support_summary` | `(*, private_state, curiosity_state, executive_contradiction, tone, stance)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L440) |
| function | `_grounding_mode` | `(*, has_curiosity, has_executive_contradiction)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L463) |
| function | `_supports_executive_sharpening` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L473) |
| function | `_support_anchor` | `(item)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L482) |
| function | `_canonical_focus_segment` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L488) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L495) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L502) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L514) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L525) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/inner_visible_support_signal_tracking.py#L533) |

## `core/services/inner_voice_daemon.py`
_Bounded inner voice daemon light — private heartbeat-driven inner voice._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ren_stemme` | `(summary)` | Gem ikke opgaven som var den svaret. | [src](../../../core/services/inner_voice_daemon.py#L101) |
| function | `run_inner_voice_daemon` | `(*, trigger=…, last_visible_at=…, witness_daemon_last_run_at=…)` | Bounded inner voice daemon — produces one private inner-voice note. | [src](../../../core/services/inner_voice_daemon.py#L119) |
| function | `get_inner_voice_daemon_state` | `()` | Return current inner voice daemon state for MC observability. | [src](../../../core/services/inner_voice_daemon.py#L333) |
| function | `_gather_grounding` | `()` | Gather grounding material from existing runtime surfaces. | [src](../../../core/services/inner_voice_daemon.py#L349) |
| function | `_recent_approval_sentiment_summary` | `()` | Summarize only notable recent approval-feedback patterns. | [src](../../../core/services/inner_voice_daemon.py#L530) |
| function | `_approval_feedback_tools` | `(entries)` | — | [src](../../../core/services/inner_voice_daemon.py#L566) |
| function | `_render_inner_voice_note` | `(grounding)` | Render inner voice note via workspace prompt + LLM, with fallback. | [src](../../../core/services/inner_voice_daemon.py#L584) |
| function | `_llm_render_inner_voice` | `(grounding)` | Use workspace INNER_VOICE.md prompt + heartbeat model to render note. | [src](../../../core/services/inner_voice_daemon.py#L604) |
| function | `_apply_support_shading` | `(base_mode, fragments)` | Apply experiential support bias to inner voice mode selection. | [src](../../../core/services/inner_voice_daemon.py#L803) |
| function | `_has_living_candidate_pull` | `(fragments, *, continuity_state, initiative_shading, thought)` | — | [src](../../../core/services/inner_voice_daemon.py#L832) |
| function | `_has_mixed_live_stream` | `(fragments, *, continuity_state, initiative_shading)` | — | [src](../../../core/services/inner_voice_daemon.py#L872) |
| function | `_deterministic_compose` | `(grounding)` | Deterministic fallback composition when LLM is unavailable. | [src](../../../core/services/inner_voice_daemon.py#L904) |
| function | `_normalize_inner_voice_mode` | `(value)` | — | [src](../../../core/services/inner_voice_daemon.py#L935) |
| function | `_select_inner_voice_mode` | `(grounding, *, thought=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L942) |
| function | `_derive_inner_voice_focus` | `(grounding, *, mode=…, thought=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L1001) |
| function | `_compose_living_inner_voice_thought` | `(*, mode, fragments, focus)` | Structured fallback trace — NOT first-person prose. | [src](../../../core/services/inner_voice_daemon.py#L1035) |
| function | `_secondary_inner_voice_observation` | `(fragments)` | Pick the strongest secondary fragment, returned as key:value (no prose). | [src](../../../core/services/inner_voice_daemon.py#L1065) |
| function | `_mode_anchor` | `(fragments, focus)` | — | [src](../../../core/services/inner_voice_daemon.py#L1086) |
| function | `_normalize_inner_voice_initiative` | `(initiative, *, grounding, mode, thought)` | — | [src](../../../core/services/inner_voice_daemon.py#L1101) |
| function | `_render_grounding_fragment` | `(key, value)` | — | [src](../../../core/services/inner_voice_daemon.py#L1125) |
| function | `_sanitize_previous_inner_voice` | `(text)` | — | [src](../../../core/services/inner_voice_daemon.py#L1155) |
| function | `_sanitize_inner_voice_text` | `(text, *, max_len=…)` | — | [src](../../../core/services/inner_voice_daemon.py#L1164) |
| function | `_looks_like_inner_voice_meta` | `(text)` | — | [src](../../../core/services/inner_voice_daemon.py#L1214) |
| function | `_thought_contains_initiative` | `(text)` | Detect if a thought text contains initiative signals. | [src](../../../core/services/inner_voice_daemon.py#L1267) |
| function | `_extract_initiative_from_thought` | `(text)` | Extract a short initiative description from a thought. | [src](../../../core/services/inner_voice_daemon.py#L1275) |
| function | `_blocked` | `(reason, cadence_state, trigger, now, reference)` | — | [src](../../../core/services/inner_voice_daemon.py#L1301) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/inner_voice_daemon.py#L1318) |

## `core/services/inner_voice_notifier.py`
_Inner voice notifier — proactive notification when a thought has substance._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_inner_voice_notifier` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L41) |
| function | `stop_inner_voice_notifier` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L59) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/inner_voice_notifier.py#L73) |
| function | `_handle_event` | `(payload)` | — | [src](../../../core/services/inner_voice_notifier.py#L91) |
| function | `_is_substantive` | `(*, summary, mode, initiative, initiative_detected)` | — | [src](../../../core/services/inner_voice_notifier.py#L170) |
| function | `_format_message` | `(*, summary, initiative, mode)` | — | [src](../../../core/services/inner_voice_notifier.py#L186) |
| function | `_notifier_enabled` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L194) |
| function | `_min_summary_chars` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L203) |
| function | `_cooldown_minutes` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L213) |
| function | `_quiet_hours` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L223) |
| function | `_in_quiet_hours` | `(now)` | — | [src](../../../core/services/inner_voice_notifier.py#L234) |
| function | `_state` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L245) |
| function | `_in_cooldown` | `(now)` | — | [src](../../../core/services/inner_voice_notifier.py#L250) |
| function | `_record_sent` | `(now, *, record_id)` | — | [src](../../../core/services/inner_voice_notifier.py#L262) |
| function | `get_inner_voice_notifier_state` | `()` | — | [src](../../../core/services/inner_voice_notifier.py#L277) |

## `core/services/inner_voice_shadow.py`
_Inner voice shadow recorder — Pilot for llm_driven_inner_pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_has_measurable_input` | `(inputs)` | Sand hvis mindst ét input har et reelt (ikke-blankt) indhold. | [src](../../../core/services/inner_voice_shadow.py#L73) |
| class | `AppraisalRecord` | `` | Structured inner-voice state with narrative rendering. | [src](../../../core/services/inner_voice_shadow.py#L82) |
| method | `AppraisalRecord.is_expired` | `(self, *, now=…)` | True if more than expiry_seconds have passed since generated_at. | [src](../../../core/services/inner_voice_shadow.py#L116) |
| method | `AppraisalRecord.to_dict` | `(self)` | — | [src](../../../core/services/inner_voice_shadow.py#L127) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/inner_voice_shadow.py#L146) |
| function | `_connect` | `()` | Frisk forbindelse der LUKKES ved `with`-exit (rettet 12/10-2026). | [src](../../../core/services/inner_voice_shadow.py#L181) |
| function | `_persist` | `(*, function_name, inputs, template_output, llm_output, llm_provider, llm_model, llm_latency_ms, llm_error, source=…, confidence=…, expiry_seconds=…, allowed_effects=…, generated_at=…)` | — | [src](../../../core/services/inner_voice_shadow.py#L203) |
| function | `_call_llm` | `(prompt)` | Run the cheap-lane via pool. Returns dict with output/error/latency. | [src](../../../core/services/inner_voice_shadow.py#L260) |
| function | `_build_helpful_signal_prompt` | `(*, status, focus, work_signal)` | Construct a prompt that asks for the kind of one-line inner thought | [src](../../../core/services/inner_voice_shadow.py#L291) |
| function | `record_shadow` | `(*, function_name, inputs, template_output, prompt_builder)` | Fire-and-forget: spawn a daemon thread to call LLM + persist both | [src](../../../core/services/inner_voice_shadow.py#L316) |
| function | `_build_voice_line_prompt` | `(*, mood_tone, self_position, current_concern, current_pull, **_extra)` | Prompt for protected_inner_voice._voice_line's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L391) |
| function | `_build_private_summary_prompt` | `(*, status, focus, uncertainty, work_signal, **_extra)` | Prompt for private_inner_note._private_summary's LLM path. | [src](../../../core/services/inner_voice_shadow.py#L420) |
| function | `shadow_helpful_signal` | `(*, status, focus, work_signal, template_output)` | — | [src](../../../core/services/inner_voice_shadow.py#L449) |
| function | `generate_appraisal` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…, expiry_seconds=…)` | State-first appraisal: returns the full structured record. | [src](../../../core/services/inner_voice_shadow.py#L463) |
| function | `_persist_record` | `(record, *, template_output)` | Persist an AppraisalRecord to the shadow audit table. | [src](../../../core/services/inner_voice_shadow.py#L570) |
| function | `_generate_via_llm` | `(*, function_name, prompt_builder, inputs, fallback, timeout_seconds=…)` | Narrative-first wrapper for backwards compatibility. | [src](../../../core/services/inner_voice_shadow.py#L593) |
| function | `generate_helpful_signal_via_llm` | `(*, status, focus, work_signal, fallback, timeout_seconds=…)` | Production path for private_growth_note._helpful_signal. | [src](../../../core/services/inner_voice_shadow.py#L622) |
| function | `generate_private_summary_via_llm` | `(*, status, focus, uncertainty, work_signal, fallback, timeout_seconds=…)` | Production path for private_inner_note._private_summary. | [src](../../../core/services/inner_voice_shadow.py#L644) |
| function | `generate_voice_line_via_llm` | `(*, mood_tone, self_position, current_concern, current_pull, fallback, timeout_seconds=…)` | Production path for protected_inner_voice._voice_line. | [src](../../../core/services/inner_voice_shadow.py#L671) |
| function | `recent_comparisons` | `(function_name=…, *, limit=…)` | Pull recent shadow records for human comparison. | [src](../../../core/services/inner_voice_shadow.py#L700) |
| function | `shadow_stats` | `(function_name=…)` | Aggregate stats across all shadow records for one function. | [src](../../../core/services/inner_voice_shadow.py#L722) |

## `core/services/interlanguage_practice.py`
_Inter-sprog practice engine — internaliseret protokol på tværs af modeller._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_interlanguage_practice_table` | `(conn)` | Idempotently create interlanguage_practice table + index. | [src](../../../core/services/interlanguage_practice.py#L127) |
| function | `ensure_schema` | `()` | Bagudkompat: åbner en conn og kalder _ensure_interlanguage_practice_table. | [src](../../../core/services/interlanguage_practice.py#L173) |
| function | `_pick_term` | `(domain_filter=…)` | Pick a random core term, optionally filtered by domain. | [src](../../../core/services/interlanguage_practice.py#L187) |
| function | `_build_clause` | `()` | Build a single clause: <term> <primitive> <term> or !<term>. | [src](../../../core/services/interlanguage_practice.py#L196) |
| function | `generate_state_expression` | `(*, num_clauses=…, mood_override=…)` | Generate a state-expression from current mood and random composition. | [src](../../../core/services/interlanguage_practice.py#L212) |
| function | `record_expression` | `(expression_text, *, session_id=…, tick_id=…, trigger=…, peer_id=…)` | Record a state-expression in the practice log. | [src](../../../core/services/interlanguage_practice.py#L265) |
| function | `get_recent_expressions` | `(*, days=…, limit=…)` | Get recent state-expressions from the practice log. | [src](../../../core/services/interlanguage_practice.py#L298) |
| function | `get_expression_count` | `(*, since_hours=…)` | Count expressions recorded in the last N hours. | [src](../../../core/services/interlanguage_practice.py#L326) |
| function | `export_protocol` | `(*, recent_days=…, max_expressions=…)` | Eksportér hele inter-sprog-protokollen til model-skift. | [src](../../../core/services/interlanguage_practice.py#L342) |
| function | `practice_tick` | `(*, session_id=…, tick_id=…, mood=…)` | Kaldes fra heartbeat tick — generér og gem én state-expression. | [src](../../../core/services/interlanguage_practice.py#L390) |
| function | `export_mood_trace_for_period` | `(start, end)` | Eksportér Jarvis' mood-historie over en periode som (timestamp, mood) pairs. | [src](../../../core/services/interlanguage_practice.py#L430) |
| function | `interpolate_mood_at` | `(trace, target_iso)` | Linear-interpolér mellem nærmeste to mood-samples til target timestamp. | [src](../../../core/services/interlanguage_practice.py#L470) |
| function | `build_interlanguage_practice_surface` | `()` | Surface for Mission Control — 3 vital signs + dummy state ved ingen data. | [src](../../../core/services/interlanguage_practice.py#L516) |

## `core/services/internal_cadence.py`
_Internal cadence layer for non-visible inner producers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ProducerSpec` | `` | — | [src](../../../core/services/internal_cadence.py#L63) |
| class | `ProducerTickResult` | `` | — | [src](../../../core/services/internal_cadence.py#L73) |
| function | `register_producer` | `(spec)` | Register a non-visible inner producer with the cadence layer. | [src](../../../core/services/internal_cadence.py#L87) |
| function | `deregister_producer` | `(name)` | Remove a producer from the cadence layer. | [src](../../../core/services/internal_cadence.py#L92) |
| function | `_evaluate_producer` | `(spec, *, now, last_visible_at, ran_this_tick, tempo=…)` | Evaluate whether a producer is due. | [src](../../../core/services/internal_cadence.py#L106) |
| class | `_ProducerWorker` | `` | Én persistent dæmon-tråd pr. producer, med kø og ledigheds-flag. | [src](../../../core/services/internal_cadence.py#L253) |
| method | `_ProducerWorker.__init__` | `(self, name)` | — | [src](../../../core/services/internal_cadence.py#L258) |
| method | `_ProducerWorker.busy` | `(self)` | Kører et job lige nu? | [src](../../../core/services/internal_cadence.py#L271) |
| method | `_ProducerWorker.alive` | `(self)` | — | [src](../../../core/services/internal_cadence.py#L275) |
| method | `_ProducerWorker.submit` | `(self, job)` | Læg job i køen. False = workeren er optaget af den forrige kørsel. | [src](../../../core/services/internal_cadence.py#L278) |
| method | `_ProducerWorker._loop` | `(self)` | — | [src](../../../core/services/internal_cadence.py#L287) |
| method | `_ProducerWorker.stop` | `(self)` | Luk workeren: luk dens DB-forbindelse i dens EGEN tråd, og stop. | [src](../../../core/services/internal_cadence.py#L297) |
| function | `_luk_denne_traads_forbindelse` | `()` | Kører i worker-tråden: luk den thread-lokale pool-forbindelse. | [src](../../../core/services/internal_cadence.py#L307) |
| function | `_get_worker` | `(navn)` | — | [src](../../../core/services/internal_cadence.py#L320) |
| function | `_stop_worker` | `(navn)` | — | [src](../../../core/services/internal_cadence.py#L329) |
| function | `stadig_i_flugt` | `(navn)` | Kører en tidligere kørsel af producenten stadig? | [src](../../../core/services/internal_cadence.py#L336) |
| function | `_noter_i_flugt` | `(navn, t)` | — | [src](../../../core/services/internal_cadence.py#L364) |
| function | `_run_producer_bounded` | `(spec, *, trigger, last_visible_at, timeout_s)` | Kør en producer i sin EGEN persistente worker-tråd med en hård timeout. | [src](../../../core/services/internal_cadence.py#L369) |
| function | `run_cadence_tick` | `(*, trigger=…, last_visible_at_iso=…)` | Run one cadence tick: evaluate and dispatch all registered producers. | [src](../../../core/services/internal_cadence.py#L429) |
| function | `get_cadence_state` | `()` | Return current cadence layer state for MC observability. | [src](../../../core/services/internal_cadence.py#L737) |
| function | `_ensure_producers_registered` | `()` | Register known producers if not already registered. | [src](../../../core/services/internal_cadence.py#L777) |
| function | `_valider_afhaengigheder` | `()` | Afvis manglende udbydere og cykler HOEJLYDT ved bootstrap. | [src](../../../core/services/internal_cadence.py#L812) |
| function | `run_cadence_tick_with_bootstrap` | `(*, trigger=…, last_visible_at_iso=…)` | Bootstrap producers and run a cadence tick. | [src](../../../core/services/internal_cadence.py#L856) |
| function | `_run_injection_refresh_tick` | `()` | Central-styret indre liv: refresh beskidte injektions-enheder i baggrunden (OFF hot-path). | [src](../../../core/services/internal_cadence.py#L879) |
| function | `_scheduler_loop` | `()` | Background loop: tick cadence every _SCHEDULER_INTERVAL_S seconds. | [src](../../../core/services/internal_cadence.py#L894) |
| function | `start_cadence_scheduler` | `()` | Spawn the standalone cadence scheduler thread. Idempotent. | [src](../../../core/services/internal_cadence.py#L959) |
| function | `stop_cadence_scheduler` | `()` | Signal the scheduler thread to exit. Best-effort; daemon dies with process. | [src](../../../core/services/internal_cadence.py#L974) |

## `core/services/internal_cadence_central_wiring.py`
_Central-wiring cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_central_wiring_producers` | `()` | Run the Central-wiring registration blocks (unchanged order/behavior). | [src](../../../core/services/internal_cadence_central_wiring.py#L15) |

## `core/services/internal_cadence_core.py`
_Core-infra cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_core_producers` | `(register_producer)` | Register the core-infra producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_core.py#L19) |

## `core/services/internal_cadence_inner_life.py`
_Inner-life cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_inner_life_producers` | `(register_producer)` | Register the inner-life producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_inner_life.py#L24) |

## `core/services/internal_cadence_maintenance.py`
_Maintenance / health cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_maintenance_producers` | `(register_producer)` | Register the maintenance / health producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_maintenance.py#L23) |

## `core/services/internal_cadence_matrix.py`
_Matrix-themed cadence producers (split from internal_cadence.py)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_matrix_producers` | `(register_producer)` | Register the Matrix-themed producers (unchanged order/timing). | [src](../../../core/services/internal_cadence_matrix.py#L18) |

## `core/services/internal_opposition_signal_tracking.py`
_Internal-opposition signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_internal_opposition_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L41) |
| function | `refresh_runtime_internal_opposition_signal_statuses` | `()` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L49) |
| function | `build_runtime_internal_opposition_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L53) |
| function | `_run_domain` | `(item, key_fn)` | Domaenet er KOERSLEN, ikke et semantisk emne. | [src](../../../core/services/internal_opposition_signal_tracking.py#L64) |
| function | `_extract_internal_opposition_candidates` | `(*_args, **_kwargs)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L87) |
| function | `_build_candidate` | `(*, domain_key, signal_type, status, title, summary, rationale, status_reason, source_items)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L273) |
| function | `_internal_opposition_track_summary` | `(items, message)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L303) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L338) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L349) |
| function | `_critic_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L354) |
| function | `_self_model_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L362) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L367) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L372) |
| function | `_open_loop_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L377) |
| function | `_world_domain_key` | `(canonical_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L382) |
| function | `_snapshot_label` | `(snapshot, domain_key)` | Et læsbart emne til titlen — run-id'et er domænet, ikke en titel. | [src](../../../core/services/internal_opposition_signal_tracking.py#L387) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/internal_opposition_signal_tracking.py#L402) |
| function | `_lag_pair_label` | `(snapshot)` | Begge lags tekst i ÉN linje — fordi det kun er titlen der når prompten. | [src](../../../core/services/internal_opposition_signal_tracking.py#L407) |

## `core/services/interruption_notice.py`
_Afbrydelses-noten — en besked til MENNESKET, ikke til modellen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_interruption_notice` | `(text)` | Er dette runtimens afbrydelses-note frem for et aegte svar? Self-safe. | [src](../../../core/services/interruption_notice.py#L38) |
| function | `strip_interruption_notices` | `(history)` | Fjern afbrydelses-noter fra den historik modellen faar. Self-safe. | [src](../../../core/services/interruption_notice.py#L49) |

## `core/services/invocation_record.py`
_Durabel invokations-tilstand for kald ingen bliver spurgt om._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taellere` | `()` | — | [src](../../../core/services/invocation_record.py#L37) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/invocation_record.py#L41) |
| function | `recorded` | `(tool_name, arguments, *, run_id=…, session_id=…)` | Omslut et MUTERENDE kald med prepared → dispatching → completed/failed. | [src](../../../core/services/invocation_record.py#L48) |
| function | `markaer_mislykket` | `(iid)` | Sig at kaldet fejlede UDEN at kaste. | [src](../../../core/services/invocation_record.py#L103) |
| function | `_afslut` | `(iid, *, ok)` | — | [src](../../../core/services/invocation_record.py#L116) |

## `core/services/irony_daemon.py`
_Irony daemon — situational self-distance and absurd self-observations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_irony_daemon` | `(*, skip_event_gate=…)` | — | [src](../../../core/services/irony_daemon.py#L20) |
| function | `get_latest_irony_observation` | `()` | — | [src](../../../core/services/irony_daemon.py#L52) |
| function | `build_irony_surface` | `()` | — | [src](../../../core/services/irony_daemon.py#L56) |
| function | `_maybe_reset_daily_count` | `()` | — | [src](../../../core/services/irony_daemon.py#L65) |
| function | `_collect_snapshot` | `()` | — | [src](../../../core/services/irony_daemon.py#L73) |
| function | `_detect_irony_conditions` | `(snapshot)` | — | [src](../../../core/services/irony_daemon.py#L98) |
| function | `_generate_observation` | `(snapshot, condition)` | — | [src](../../../core/services/irony_daemon.py#L111) |
| function | `_store_observation` | `(observation, condition)` | — | [src](../../../core/services/irony_daemon.py#L136) |

## `core/services/jarvis_brain.py`
_Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BrainEntry` | `` | — | [src](../../../core/services/jarvis_brain.py#L71) |
| method | `BrainEntry.__post_init__` | `(self)` | — | [src](../../../core/services/jarvis_brain.py#L98) |
| function | `_atomic_write` | `(path, content)` | Atomic file write via tmp + rename. Creates parent dirs as needed. | [src](../../../core/services/jarvis_brain.py#L127) |
| function | `parse_frontmatter` | `(path)` | Parse YAML frontmatter + body from a markdown file. | [src](../../../core/services/jarvis_brain.py#L135) |
| function | `_iso` | `(dt)` | — | [src](../../../core/services/jarvis_brain.py#L155) |
| function | `_parse_iso` | `(s)` | Parse ISO timestamp from string or pass-through if already datetime. | [src](../../../core/services/jarvis_brain.py#L163) |
| function | `render_entry_markdown` | `(entry)` | Render a BrainEntry as markdown with YAML frontmatter. | [src](../../../core/services/jarvis_brain.py#L176) |
| function | `entry_from_frontmatter` | `(fm, body)` | Build a BrainEntry from parsed frontmatter dict + body string. | [src](../../../core/services/jarvis_brain.py#L206) |
| function | `_workspace_root` | `()` | Base dir for brain-relative paths. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L312) |
| function | `_state_root` | `()` | — | [src](../../../core/services/jarvis_brain.py#L329) |
| function | `brain_dir` | `()` | Return the brain storage dir under JARVIS_HOME/shared/jarvis_brain. | [src](../../../core/services/jarvis_brain.py#L336) |
| function | `index_db_path` | `()` | — | [src](../../../core/services/jarvis_brain.py#L346) |
| function | `_ensure_wal` | `(conn, key)` | Slå WAL til én gang per (proces, db-sti). Persistent på filen. | [src](../../../core/services/jarvis_brain.py#L367) |
| function | `_ensure_schema` | `(conn, key)` | Opret/migrér index-schema — men kun når det faktisk mangler. | [src](../../../core/services/jarvis_brain.py#L392) |
| function | `connect_index` | `()` | — | [src](../../../core/services/jarvis_brain.py#L416) |
| function | `_ensure_index_schema_migrations` | `(conn)` | Bring pre-existing brain_index tables up to the current schema. | [src](../../../core/services/jarvis_brain.py#L428) |
| function | `_slugify` | `(s, max_len=…)` | — | [src](../../../core/services/jarvis_brain.py#L513) |
| function | `_file_hash` | `(text)` | — | [src](../../../core/services/jarvis_brain.py#L520) |
| function | `write_entry` | `(*, kind, title, content, visibility, domain, trigger=…, related=…, tags=…, source_url=…, source_chronicle=…, importance=…, now=…, skip_temporal=…)` | Skriver en ny brain-entry til disk og indexerer den (uden embedding endnu). | [src](../../../core/services/jarvis_brain.py#L524) |
| function | `read_entry` | `(entry_id)` | Read a BrainEntry by id (loads from disk via index lookup). | [src](../../../core/services/jarvis_brain.py#L634) |
| function | `verify_brain_entry` | `(entry_id)` | Slå en brain-post op i BEGGE lag — indekset OG filen på disken. | [src](../../../core/services/jarvis_brain.py#L650) |
| function | `_index_path_for` | `(entry_id)` | Returns the relative path stored in brain_index for entry_id. | [src](../../../core/services/jarvis_brain.py#L702) |
| function | `compute_effective_salience` | `(entry, now)` | Compute time-decayed salience with bump amplification + importance gate. | [src](../../../core/services/jarvis_brain.py#L741) |
| function | `_embed_text` | `(text)` | Wrapper around eksisterende embedder. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L769) |
| function | `_embed_texts` | `(texts)` | Batch-variant af _embed_text: ÉT ollama round-trip for hele listen (via | [src](../../../core/services/jarvis_brain.py#L784) |
| function | `_embedding_to_blob` | `(v)` | — | [src](../../../core/services/jarvis_brain.py#L801) |
| function | `_embedding_from_blob` | `(blob, dim)` | — | [src](../../../core/services/jarvis_brain.py#L805) |
| function | `embed_pending_entries` | `()` | Embed alle entries i index'et der mangler embedding. Returnerer antal. | [src](../../../core/services/jarvis_brain.py#L809) |
| function | `search_brain` | `(*, query_text, kinds=…, visibility_ceiling=…, limit=…, domain=…, tags=…, include_archived=…, now=…, use_temporal_boost=…, min_score=…, min_cosine=…)` | Hybrid embedding search: 0.95*cosine + 0.05*effective_salience + temporal boost. | [src](../../../core/services/jarvis_brain.py#L849) |
| function | `search_brain_scored` | `(*, query_text, kinds=…, visibility_ceiling=…, limit=…, domain=…, tags=…, include_archived=…, now=…, use_temporal_boost=…, min_score=…, min_cosine=…)` | Som search_brain, men returnerer (score, entry_id) uden at læse filerne. | [src](../../../core/services/jarvis_brain.py#L881) |
| function | `_compute_search_temporal_boost` | `(candidate_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost for search candidates. | [src](../../../core/services/jarvis_brain.py#L1086) |
| function | `bump_salience` | `(entry_id, now=…, *, min_interval_hours=…)` | Increments salience_bumps + recall_count + opdaterer last_used_at i index OG fil. | [src](../../../core/services/jarvis_brain.py#L1127) |
| function | `archive_entry` | `(entry_id, *, reason=…, now=…)` | Mark entry as archived and move file to _archive/<kind>/. | [src](../../../core/services/jarvis_brain.py#L1188) |
| function | `supersede` | `(*, old_ids, new_id, now=…)` | Mark old entries as superseded by new_id (keeps files in place). | [src](../../../core/services/jarvis_brain.py#L1219) |
| function | `prune_orphaned_index_rows` | `(*, maks_andel=…)` | Fjern indeks-rækker hvis markdown-fil er væk. Den MODSATTE retning. | [src](../../../core/services/jarvis_brain.py#L1245) |
| function | `rebuild_index_from_files` | `()` | Scan brain_dir() for .md files; new/changed hash → update index. | [src](../../../core/services/jarvis_brain.py#L1317) |
| function | `_extract_text_for_entry` | `(entry_id, *, rel_path=…, title=…)` | Read entry content from disk for entity/semantic analysis. | [src](../../../core/services/jarvis_brain.py#L1461) |
| function | `_temporal_similarity_score` | `(hours_apart)` | Score 0.0–1.0 based on temporal proximity. 1.0 at ≤1h, decays to 0 at 24h. | [src](../../../core/services/jarvis_brain.py#L1515) |
| function | `_cosine_similarity` | `(a_vec, b_vec)` | — | [src](../../../core/services/jarvis_brain.py#L1525) |
| function | `_compute_temporal_confidence` | `(*, temporal, semantic, entity, is_chain, chain_score=…)` | Combine four signals into a single confidence score (0.0–1.0). | [src](../../../core/services/jarvis_brain.py#L1532) |
| function | `_compute_chain_score` | `(*, new_entry, cand_entry, hours_apart, cand_related)` | Compute chain signal score (0.0–1.0) between two entries. | [src](../../../core/services/jarvis_brain.py#L1551) |
| function | `infer_temporal_edges` | `(new_entry_id, now=…)` | Run four-signal inference between a new entry and all existing active entries. | [src](../../../core/services/jarvis_brain.py#L1601) |
| function | `_store_temporal_edge` | `(from_id, to_id, confidence, reasoning, now)` | Insert or update a temporal edge with combined confidence. | [src](../../../core/services/jarvis_brain.py#L1804) |
| function | `_store_temporal_edges_batch` | `(edges, *, now)` | Skriv mange kanter i én transaktion (målt 25/9-2026). | [src](../../../core/services/jarvis_brain.py#L1834) |
| function | `get_temporal_neighbors` | `(entry_id, min_confidence=…, limit=…)` | Get tidligere inferred temporal neighbors for an entry. | [src](../../../core/services/jarvis_brain.py#L1863) |
| function | `temporal_boost_recall` | `(entry_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost scores for a set of entry IDs. | [src](../../../core/services/jarvis_brain.py#L1893) |
| function | `prune_stale_edges` | `(*, max_age_days=…, min_confidence=…)` | Remove stale temporal edges with low confidence. | [src](../../../core/services/jarvis_brain.py#L1949) |
| function | `prune_unreadable_edges` | `()` | Fjern kanter der beviseligt ALDRIG læses — uanset alder. | [src](../../../core/services/jarvis_brain.py#L1976) |
| function | `prune_dense_edges` | `(*, max_per_node=…)` | Loft pr. node: behold kun de ``max_per_node`` stærkeste kanter pr. endepunkt. | [src](../../../core/services/jarvis_brain.py#L2018) |
| function | `full_rebuild` | `(*, batch_size=…)` | Genberegn alle temporale edges fra bunden. | [src](../../../core/services/jarvis_brain.py#L2078) |
| function | `_emit_jarvis_brain_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/jarvis_brain.py#L2140) |

## `core/services/jarvis_brain_daemon.py`
_Jarvis Brain background daemon — tre uafhængige loops._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reindex_once` | `()` | Et enkelt reindex-pass. Returnerer antal file changes opdaget. | [src](../../../core/services/jarvis_brain_daemon.py#L26) |
| function | `reindex_loop` | `(stop_event)` | Long-running loop. Stops cleanly when stop_event is set. | [src](../../../core/services/jarvis_brain_daemon.py#L42) |
| function | `find_duplicate_proposals` | `(*, threshold=…, kinds=…)` | Returnerer liste af (a_id, b_id, similarity) hvor sim ≥ threshold. | [src](../../../core/services/jarvis_brain_daemon.py#L67) |
| function | `_call_ollamafreeapi` | `(prompt)` | Free OllamaFreeAPI — public-safe job. Returns parsed JSON or None on fail. | [src](../../../core/services/jarvis_brain_daemon.py#L121) |
| function | `_model_is_available` | `(tag_names, model)` | Pure: er `model` til stede blandt Ollamas /api/tags-navne? Matcher både | [src](../../../core/services/jarvis_brain_daemon.py#L142) |
| function | `_call_local_ollama` | `(prompt)` | Ollama-kald for personal/intimate brain-jobs (summaries + contradiction). | [src](../../../core/services/jarvis_brain_daemon.py#L155) |
| function | `_resolve_local_chat_target` | `()` | Find configured local-lane chat model + HOST from provider router. | [src](../../../core/services/jarvis_brain_daemon.py#L214) |
| function | `_resolve_local_chat_model` | `()` | Bagudkompatibel wrapper: kun modellen. Se `_resolve_local_chat_target`. | [src](../../../core/services/jarvis_brain_daemon.py#L239) |
| function | `_parse_json_loose` | `(text)` | Parse JSON from possibly noisy LLM output. Looks for first {...} block. | [src](../../../core/services/jarvis_brain_daemon.py#L244) |
| function | `_llm_contradiction_check` | `(a, b)` | Privacy-routed contradiction check. | [src](../../../core/services/jarvis_brain_daemon.py#L265) |
| function | `_state_path` | `()` | Override target in tests via monkeypatch. | [src](../../../core/services/jarvis_brain_daemon.py#L292) |
| function | `_read_state` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L299) |
| function | `_write_state` | `(state)` | — | [src](../../../core/services/jarvis_brain_daemon.py#L310) |
| function | `record_proposal_rejection` | `(phase, *, proposal_id)` | Track rejection. After 3 in a row for 'theme' phase, auto-pause. | [src](../../../core/services/jarvis_brain_daemon.py#L319) |
| function | `record_proposal_acceptance` | `(phase, *, proposal_id)` | Reset rejection streak on acceptance. | [src](../../../core/services/jarvis_brain_daemon.py#L341) |
| function | `is_theme_consolidation_paused` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L350) |
| function | `resume_theme_consolidation` | `()` | Manuel reaktivering. Nulstiller streak + paused flag. | [src](../../../core/services/jarvis_brain_daemon.py#L354) |
| function | `_run_theme_consolidation_pass` | `()` | Søndags-pass: group observations efter domain, find temaer. | [src](../../../core/services/jarvis_brain_daemon.py#L362) |
| function | `run_theme_consolidation_if_active` | `()` | Kør tema-pass hvis ikke paused. Returnerer antal forslag genereret. | [src](../../../core/services/jarvis_brain_daemon.py#L371) |
| function | `regenerate_summary` | `(*, target_visibility=…)` | Regenererer state/jarvis_brain_summary.md. | [src](../../../core/services/jarvis_brain_daemon.py#L409) |
| function | `auto_archive_low_salience` | `()` | Arkivér entries hvis effective_salience < 0.05 i ≥ 90 dage. | [src](../../../core/services/jarvis_brain_daemon.py#L490) |
| function | `b4_catchup_infer_once` | `(*, batch_size=…)` | Find active entries with no temporal edges and run inference on them. | [src](../../../core/services/jarvis_brain_daemon.py#L559) |
| function | `b4_edge_maintenance_once` | `()` | Run one pass of B4 edge maintenance: catchup + prune. | [src](../../../core/services/jarvis_brain_daemon.py#L628) |
| function | `_consolidation_summary_loop` | `(stop_event)` | Daily consolidation + summary + B4 edge maintenance scheduler. | [src](../../../core/services/jarvis_brain_daemon.py#L666) |
| function | `run_consolidation_pass` | `()` | Single consolidation pass: phase 1 (dedup) + phase 2 (contradictions). | [src](../../../core/services/jarvis_brain_daemon.py#L752) |
| function | `start_brain_daemon` | `()` | Start the three brain daemon threads. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L771) |
| function | `stop_brain_daemon` | `()` | Signal stop and wait briefly for threads to exit. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L794) |

## `core/services/jarvis_brain_reflection.py`
_End-of-day refleksions-slot — visible Jarvis spørger sig selv hvad han lærte._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_reflection_envelope` | `(*, chronicle_summary)` | Build the envelope text shown to visible Jarvis at end-of-day. | [src](../../../core/services/jarvis_brain_reflection.py#L31) |
| function | `build_internal_nudge` | `(*, count_so_far)` | Soft nudge after 3+ remember_this calls in same reflection slot. | [src](../../../core/services/jarvis_brain_reflection.py#L36) |
| function | `_was_active_today` | `()` | Best-effort tjek om Jarvis havde aktivitet i dag. | [src](../../../core/services/jarvis_brain_reflection.py#L49) |
| function | `_build_today_chronicle_summary` | `()` | Build a short summary of today's chronicle entries. | [src](../../../core/services/jarvis_brain_reflection.py#L73) |
| function | `_run_reflection_turn` | `(chronicle_summary)` | Trigger en visible-Jarvis tur med reflection-envelope. | [src](../../../core/services/jarvis_brain_reflection.py#L86) |
| function | `run_daily_reflection_if_active` | `()` | Entry point for the daily slot trigger. | [src](../../../core/services/jarvis_brain_reflection.py#L110) |
| function | `build_jarvis_brain_reflection_surface` | `()` | Surface the daily reflection slot without triggering it. | [src](../../../core/services/jarvis_brain_reflection.py#L126) |

## `core/services/jarvis_brain_visibility.py`
_Privacy-gate for Jarvis Brain recall._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_owner_id` | `()` | Hentet via owner_resolver. Wrapped så tests kan monkeypatche. | [src](../../../core/services/jarvis_brain_visibility.py#L18) |
| function | `can_recall` | `(entry_visibility, ceiling)` | True if entry's visibility is permitted at the given ceiling. | [src](../../../core/services/jarvis_brain_visibility.py#L45) |
| function | `session_visibility_ceiling` | `(session)` | Beregn visibility-ceiling for en session. | [src](../../../core/services/jarvis_brain_visibility.py#L50) |

## `core/services/jarvis_ui_guard.py`
_Normaliserer og validerer ``jarvis-ui``-blokke FØR de når chatten._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normaliser_form` | `(raw)` | Flyt JSON'en ned på sin egen linje og lukke-fencen på sin egen linje. | [src](../../../core/services/jarvis_ui_guard.py#L73) |
| function | `_reparer_json` | `(tekst)` | Ret de entydige JSON-fejl. Rører intet der allerede er gyldigt. | [src](../../../core/services/jarvis_ui_guard.py#L86) |
| function | `_ret_laengder` | `(tekst)` | Juster ``comparison``-values op til kolonneantallet. Returnerer ny JSON. | [src](../../../core/services/jarvis_ui_guard.py#L94) |
| function | `_tekst` | `(vaerdi)` | Spejl rendererens ``text()``: kun strenge, trimmet, tom = falsk. | [src](../../../core/services/jarvis_ui_guard.py#L131) |
| function | `_liste` | `(vaerdi, maks)` | Spejl rendererens ``list()``: kun objekter, afkortet til ``maks``. | [src](../../../core/services/jarvis_ui_guard.py#L136) |
| function | `_diagnosticér` | `(data)` | Afgør om rendereren viser blokken. Returnerer (niveau, fejl). | [src](../../../core/services/jarvis_ui_guard.py#L143) |
| function | `_validér` | `(tekst)` | — | [src](../../../core/services/jarvis_ui_guard.py#L249) |
| function | `normalisér` | `(text, *, run_id=…)` | Normalisér alle ``jarvis-ui``-blokke i teksten. Returnerer ny tekst. | [src](../../../core/services/jarvis_ui_guard.py#L269) |
| function | `_normalisér_indre` | `(text, *, run_id)` | — | [src](../../../core/services/jarvis_ui_guard.py#L285) |
| function | `_registrér` | `(aendringer, *, run_id)` | — | [src](../../../core/services/jarvis_ui_guard.py#L344) |
| function | `fejl_i_flader` | `(text)` | Returnér de fejl der gør en ``jarvis-ui``-blok død eller ufuldstændig. | [src](../../../core/services/jarvis_ui_guard.py#L364) |

## `core/services/jarvisx_bridge.py`
_JarvisX tool-bridge — bidirectional dispatch over WebSocket._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `internal_dispatch_token` | `()` | Shared-secret som BEGGE processer kan udlede ens. | [src](../../../core/services/jarvisx_bridge.py#L48) |
| function | `_api_port` | `()` | Port for jarvis-api-procesen (hvor broen lever). Default 8080. | [src](../../../core/services/jarvisx_bridge.py#L89) |
| function | `_runtime_port` | `()` | Port for jarvis-runtime-procesen (autonome/wakeup-runs). Default 8011. | [src](../../../core/services/jarvisx_bridge.py#L100) |
| function | `_port_for_process` | `(role)` | Localhost-port for procesrollen. Begge processer kører SAMME uvicorn-app | [src](../../../core/services/jarvisx_bridge.py#L111) |
| function | `_looks_like_closed_ws` | `(exc)` | Er dette en 'send over en allerede-lukket WebSocket'-fejl? Starlette/uvicorn | [src](../../../core/services/jarvisx_bridge.py#L117) |
| function | `_ws_is_closed` | `(ws)` | Bedste-effort: er WS'en allerede lukket? Self-safe → False når ukendt, så vi | [src](../../../core/services/jarvisx_bridge.py#L127) |
| class | `PendingBridgeCall` | `` | — | [src](../../../core/services/jarvisx_bridge.py#L146) |
| class | `BridgeConnection` | `` | One live bridge connection. WS object is platform-dependent. | [src](../../../core/services/jarvisx_bridge.py#L155) |
| method | `BridgeConnection.send_raw` | `(self, data, *, timeout_s=…)` | Send raw JSON over WS with lock and timeout. | [src](../../../core/services/jarvisx_bridge.py#L184) |
| method | `BridgeConnection.send_invoke` | `(self, *, correlation_id, tool, args, timeout_ms, extra=…, stream_output=…)` | Send tool_invoke over WS and register the pending future. | [src](../../../core/services/jarvisx_bridge.py#L216) |
| method | `BridgeConnection.register_pending` | `(self, correlation_id, future, owning_loop, on_output=…)` | — | [src](../../../core/services/jarvisx_bridge.py#L270) |
| method | `BridgeConnection.deliver_output` | `(self, *, correlation_id, stream, seq, chunk, truncated=…)` | — | [src](../../../core/services/jarvisx_bridge.py#L283) |
| method | `BridgeConnection.deliver_result` | `(self, *, correlation_id, status, result=…, error=…, timing=…)` | Complete the pending future for this correlation_id. | [src](../../../core/services/jarvisx_bridge.py#L318) |
| method | `BridgeConnection.cancel_all_pending` | `(self, *, reason=…)` | Cancel all in-flight calls (e.g. on WS disconnect). | [src](../../../core/services/jarvisx_bridge.py#L367) |
| function | `_kan_forsvinde` | `(conn)` | Forlader den her klient broen naar brugeren kigger et andet sted hen? | [src](../../../core/services/jarvisx_bridge.py#L395) |
| class | `BridgeRegistry` | `` | Process-local registry of active bridges: user_id → client_id → bro. | [src](../../../core/services/jarvisx_bridge.py#L401) |
| method | `BridgeRegistry.__init__` | `(self)` | — | [src](../../../core/services/jarvisx_bridge.py#L414) |
| method | `BridgeRegistry._client_key` | `(conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L419) |
| method | `BridgeRegistry.register` | `(self, conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L422) |
| method | `BridgeRegistry.unregister` | `(self, conn)` | Remove ONLY if the registered bridge for this client IS this conn. | [src](../../../core/services/jarvisx_bridge.py#L444) |
| method | `BridgeRegistry._evict_if_current` | `(self, user_id, conn, *, reason)` | Fjern en stale/død bro fra registret HVIS den stadig er den aktuelle for | [src](../../../core/services/jarvisx_bridge.py#L459) |
| method | `BridgeRegistry._publish_presence` | `(self)` | Publicér dette registrys bro'er til shared_cache, så DEN ANDEN proces (og | [src](../../../core/services/jarvisx_bridge.py#L476) |
| method | `BridgeRegistry._diagnose_no_bridge` | `(self, user_id, *, stage, tool=…)` | Fastslå HVORFOR der ikke er en bro for user_id (i stedet for et blindt | [src](../../../core/services/jarvisx_bridge.py#L504) |
| method | `BridgeRegistry._foretrukken` | `(klienter)` | Broen der bruges naar intet vaerktoej peger et bestemt sted hen. | [src](../../../core/services/jarvisx_bridge.py#L581) |
| method | `BridgeRegistry.get_bridge` | `(self, user_id, *, tool=…)` | Broen for ``user_id`` — og med ``tool`` DEN der kan udfoere det. | [src](../../../core/services/jarvisx_bridge.py#L592) |
| method | `BridgeRegistry.list_bridges` | `(self, user_id)` | Alle forbundne klienter for en bruger (computer OG telefon). | [src](../../../core/services/jarvisx_bridge.py#L645) |
| method | `BridgeRegistry.list_user_ids` | `(self)` | user_id'er med en aktiv bro (til bro_broker / override-switch). | [src](../../../core/services/jarvisx_bridge.py#L649) |
| method | `BridgeRegistry.clear` | `(self)` | Test helper — drop all registrations. | [src](../../../core/services/jarvisx_bridge.py#L653) |
| method | `BridgeRegistry.dispatch` | `(self, *, user_id, tool, args, timeout_s=…, allow_cross_process=…, on_output=…)` | Send tool_invoke to user's bridge, await result or timeout. | [src](../../../core/services/jarvisx_bridge.py#L660) |
| method | `BridgeRegistry._dispatch_without_local_bridge` | `(self, *, user_id, tool, args, timeout_s, allow_cross_process, stage, on_output=…)` | Ingen LEVENDE lokal bro for user_id (aldrig registreret, eller netop evictet | [src](../../../core/services/jarvisx_bridge.py#L791) |
| method | `BridgeRegistry._forward_cross_process` | `(self, *, user_id, tool, args, timeout_s, target_port=…, on_output=…)` | HTTP-forward dispatch til den proces der holder broen (dens interne endpoint). | [src](../../../core/services/jarvisx_bridge.py#L854) |
| function | `set_main_loop` | `(loop)` | Register the main uvicorn loop. Called from app startup. | [src](../../../core/services/jarvisx_bridge.py#L979) |
| function | `get_main_loop` | `()` | Return the registered main loop, or None if not set yet. | [src](../../../core/services/jarvisx_bridge.py#L985) |

