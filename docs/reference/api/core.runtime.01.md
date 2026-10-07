# `core.runtime.01` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/__init__.py`

_(no top-level classes or functions)_

## `core/runtime/arko_provider.py`
_Arko Studio adapter for cheap-lane inference._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_config` | `()` | Pull base_url, api_key, agent_id from runtime.json. Returns None | [src](../../../core/runtime/arko_provider.py#L35) |
| function | `collapse_messages_to_prompt` | `(messages)` | Flatten OpenAI-style messages into one labelled prompt for Arko. | [src](../../../core/runtime/arko_provider.py#L51) |
| function | `call_arko` | `(*, messages=…, prompt=…, timeout=…)` | Send a message to the Arko cheap-lane agent and return an | [src](../../../core/runtime/arko_provider.py#L69) |
| function | `is_configured` | `()` | Cheap probe so the cheap-lane router can skip Arko silently when | [src](../../../core/runtime/arko_provider.py#L146) |

## `core/runtime/bootstrap.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_runtime_dirs` | `()` | — | [src](../../../core/runtime/bootstrap.py#L32) |
| function | `ensure_settings_file` | `()` | — | [src](../../../core/runtime/bootstrap.py#L38) |

## `core/runtime/circadian_state.py`
_Circadian state — energy level from clock + activity density._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_activity_event` | `()` | Call on each heartbeat run or visible turn to track activity density. | [src](../../../core/runtime/circadian_state.py#L33) |
| function | `get_circadian_context` | `()` | Compute and return current energy context. Fast — no LLM, no DB. | [src](../../../core/runtime/circadian_state.py#L42) |
| function | `load_persisted_state` | `()` | Load previously persisted energy level. Call once on startup. | [src](../../../core/runtime/circadian_state.py#L89) |
| function | `_clock_baseline` | `(hour)` | — | [src](../../../core/runtime/circadian_state.py#L109) |
| function | `_clock_phase_label` | `(hour)` | — | [src](../../../core/runtime/circadian_state.py#L123) |
| function | `_drain_score` | `()` | — | [src](../../../core/runtime/circadian_state.py#L139) |
| function | `_drain_label` | `(score)` | — | [src](../../../core/runtime/circadian_state.py#L143) |
| function | `_quiet_minutes_since_last_activity` | `(now)` | — | [src](../../../core/runtime/circadian_state.py#L151) |
| function | `_lower_energy` | `(level)` | — | [src](../../../core/runtime/circadian_state.py#L158) |
| function | `_raise_energy` | `(level)` | — | [src](../../../core/runtime/circadian_state.py#L163) |
| function | `_persist_state` | `(energy)` | — | [src](../../../core/runtime/circadian_state.py#L168) |

## `core/runtime/config.py`

_(no top-level classes or functions)_

## `core/runtime/db.py`
_Facade for core.runtime.db submodules._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_session_distillation_record_from_row` | `(row)` | — | [src](../../../core/runtime/db.py#L80) |

## `core/runtime/db_absence_traces.py`
_DB helpers for absence_traces (Lag 11 forgetting)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/runtime/db_absence_traces.py#L16) |
| function | `_month_key` | `(at=…)` | — | [src](../../../core/runtime/db_absence_traces.py#L20) |
| function | `increment_auto_counter` | `(*, workspace_id, delta=…, at=…)` | UPSERT the monthly auto-counter row. | [src](../../../core/runtime/db_absence_traces.py#L25) |
| function | `decrement_auto_counter` | `(*, workspace_id, month_key, delta=…)` | Used by revive_soft_deleted to undo a counted fade. | [src](../../../core/runtime/db_absence_traces.py#L69) |
| function | `insert_self_marker` | `(*, workspace_id, period_label)` | Record an irrevocable self-release. NO memory reference is stored. | [src](../../../core/runtime/db_absence_traces.py#L88) |
| function | `list_self_markers` | `(*, workspace_id, include_released=…)` | List self-markers for a workspace, ordered oldest first. | [src](../../../core/runtime/db_absence_traces.py#L108) |
| function | `get_auto_counter` | `(*, workspace_id, month_key=…)` | Get the counter row for a given month (default: current month). | [src](../../../core/runtime/db_absence_traces.py#L135) |
| function | `mark_self_released` | `(*, trace_id)` | Recursive release: mark an existing self-marker as released. | [src](../../../core/runtime/db_absence_traces.py#L157) |

## `core/runtime/db_agent_approvals.py`
_Varige approvals til agenters handlinger (agent-contract-v1 F4a, spec 8.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_approval_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_approvals.py#L46) |
| function | `_iso` | `(dt)` | — | [src](../../../core/runtime/db_agent_approvals.py#L111) |
| function | `_parse` | `(value)` | — | [src](../../../core/runtime/db_agent_approvals.py#L115) |
| function | `_audit` | `(conn, approval_id, event, actor=…, detail=…)` | — | [src](../../../core/runtime/db_agent_approvals.py#L119) |
| function | `normalize_arguments` | `(arguments)` | Kaldets argumenter UDEN serverens egne ``_runtime_*``-felter (de er ikke en del af handlingen). | [src](../../../core/runtime/db_agent_approvals.py#L124) |
| function | `invocation_digest` | `(*, tool_name, arguments, target, assignment_id)` | Digest af netop dette kald: vaerktoej + normaliserede argumenter + target + assignment. | [src](../../../core/runtime/db_agent_approvals.py#L129) |
| function | `safe_view` | `(tool_name, arguments)` | Hvad et menneske ser i kortet: redigerede (hemmeligheder) og afkortede argumenter. | [src](../../../core/runtime/db_agent_approvals.py#L137) |
| function | `_row_or_none` | `(conn, approval_id)` | — | [src](../../../core/runtime/db_agent_approvals.py#L148) |
| function | `get` | `(*, approval_id)` | — | [src](../../../core/runtime/db_agent_approvals.py#L152) |
| function | `get_for_owner` | `(*, owner_user_id, approval_id)` | — | [src](../../../core/runtime/db_agent_approvals.py#L156) |
| function | `request` | `(*, owner_user_id, origin_session_id, assignment_id, tool_name, arguments, run_id=…, risk_class=…, requested_by=…, kind=…, ttl=…, now=…)` | Opret (eller genfind) en ventende approval. Idempotent paa (assignment, digest): samme kald giver | [src](../../../core/runtime/db_agent_approvals.py#L161) |
| function | `_authorized` | `(actor_user_id, owner_user_id)` | — | [src](../../../core/runtime/db_agent_approvals.py#L211) |
| function | `decide` | `(*, approval_id, decision, actor_user_id, actor_kind, digest, note=…, now=…)` | Afgoer EN approval. ``approve``/``deny``. Atomisk: to samtidige afgoerelser giver én vinder. | [src](../../../core/runtime/db_agent_approvals.py#L223) |
| function | `consume` | `(*, approval_id, digest, now=…)` | Brug en godkendt approval. Atomisk ``approved -> consumed`` paa digest og foer udloeb - HOEJST EN | [src](../../../core/runtime/db_agent_approvals.py#L267) |
| function | `expire_due` | `(*, now=…)` | Udloeb ventende og ubrugte godkendte approvals der har overskredet fristen. | [src](../../../core/runtime/db_agent_approvals.py#L281) |
| function | `cancel_for_assignment` | `(*, assignment_id, reason)` | Annuller ventende/ubrugte approvals for et assignment der er endt. | [src](../../../core/runtime/db_agent_approvals.py#L296) |
| function | `list_for_owner` | `(*, owner_user_id, status=…, origin_session_id=…, limit=…)` | Ejerens approvals (aldrig en andens). | [src](../../../core/runtime/db_agent_approvals.py#L310) |
| function | `unannounced_pending` | `(*, owner_user_id, origin_session_id)` | — | [src](../../../core/runtime/db_agent_approvals.py#L326) |
| function | `claim_announcements` | `(*, owner_user_id, origin_session_id)` | Atomisk: markér ventende, endnu ikke omtalte approvals som omtalt og returnér dem. Hver approval | [src](../../../core/runtime/db_agent_approvals.py#L334) |
| function | `audit_trail` | `(*, approval_id)` | — | [src](../../../core/runtime/db_agent_approvals.py#L355) |
| function | `save_checkpoint` | `(*, assignment_id, run_id, approval_id, payload)` | Gem barnets loekketilstand. Hoejst én parkeret checkpoint pr. assignment. | [src](../../../core/runtime/db_agent_approvals.py#L363) |
| function | `parked_checkpoint` | `(*, assignment_id)` | — | [src](../../../core/runtime/db_agent_approvals.py#L387) |
| function | `take_checkpoint` | `(*, assignment_id)` | Atomisk ``parked -> resumed``: HOEJST EN genoptagelse pr. checkpoint. Returnerer | [src](../../../core/runtime/db_agent_approvals.py#L393) |
| function | `decided_parked` | `()` | Parkerede checkpoints hvis approval er afgjort (godkendt, afslaaet, udloebet eller annulleret) - | [src](../../../core/runtime/db_agent_approvals.py#L414) |

## `core/runtime/db_agent_artifacts.py`
_Artefaktlager for agentkoersler (agent-contract-v1, leverance C1, spec 9 og 12.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ArtifactTooLarge` | `` | — | [src](../../../core/runtime/db_agent_artifacts.py#L37) |
| method | `ArtifactTooLarge.__init__` | `(self, detail=…)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L38) |
| function | `artifact_root` | `()` | Beregnes ved kald (ikke ved import), saa HOME-omdirigering i tests virker. | [src](../../../core/runtime/db_agent_artifacts.py#L42) |
| function | `ensure_artifact_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L47) |
| function | `_safe_id` | `(value, what)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L69) |
| function | `_run_dir` | `(agent_id, run_id)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L76) |
| function | `_fsync_dir` | `(path)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L80) |
| function | `run_bytes` | `(run_id)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L88) |
| function | `write_artifact` | `(*, agent_id, run_id, name, data, assignment_id, owner_user_id, status=…)` | Skriv én artefakt atomisk og registrer den. Erstatter en tidligere version af samme navn. | [src](../../../core/runtime/db_agent_artifacts.py#L93) |
| function | `get_artifact_record` | `(*, run_id, name)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L134) |
| function | `artifact_ref` | `(run_id, name)` | — | [src](../../../core/runtime/db_agent_artifacts.py#L139) |
| function | `read_artifact` | `(*, owner_user_id, ref, offset=…, limit=…)` | Adgangskontrolleret laesning via en reference ``<run_id>/<navn>``. | [src](../../../core/runtime/db_agent_artifacts.py#L143) |
| function | `manifest` | `(*, owner_user_id, assignment_id)` | Alle forsoegs' artefakter for ét assignment (et fejlet foerste forsoeg forsvinder ikke). | [src](../../../core/runtime/db_agent_artifacts.py#L170) |
| function | `reconcile` | `()` | Afstem DB mod disk. Markerer poster med manglende/korrupt fil, finder foraeldreloese | [src](../../../core/runtime/db_agent_artifacts.py#L179) |
| function | `write_terminal_artifacts` | `(*, agent_id, assignment_id, owner_user_id, status, reply, summary, error_code=…, error_phase=…, worktree=…)` | Skriv ``result.json`` (+ ``final.txt`` og ``events.jsonl``) for assignmentets SIDSTE run | [src](../../../core/runtime/db_agent_artifacts.py#L212) |

## `core/runtime/db_agent_attempts.py`
_Failover som nyt synligt runforsoeg (agent-contract-v1 G, spec 7.1 og 6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fence` | `(conn, assignment_id)` | Den koerende traads lease skal stadig vaere den gaeldende - tjekket INDE i transaktionen. | [src](../../../core/runtime/db_agent_attempts.py#L30) |
| function | `begin_failover_attempt` | `(*, from_run_id, decision, reason)` | Luk det svigtede forsoeg med en fejlpost og aabn det naeste (nyt ``run_id``, ``attempt_no`` + 1). | [src](../../../core/runtime/db_agent_attempts.py#L47) |
| function | `_write_failed_attempt_artifact` | `(*, agent_id, run_id, assignment_id, owner, reason, successor, attempt_no)` | ``result.json`` for det svigtede forsoeg, saa manifestet viser det. Bedste indsats: en manglende | [src](../../../core/runtime/db_agent_attempts.py#L110) |
| function | `live_run_id` | `(run_id)` | Foelg failover-kaeden fra ``run_id`` til det forsoeg der koerer nu. Et run der ikke er afloest af et | [src](../../../core/runtime/db_agent_attempts.py#L129) |
| function | `attempts_for_assignment` | `(assignment_id)` | — | [src](../../../core/runtime/db_agent_attempts.py#L149) |

## `core/runtime/db_agent_bridge.py`
_Varige bro-invocations for agenter paa et klient-target (agent-contract-v1 E, spec 8 + 8.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_bridge_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_bridge.py#L35) |
| function | `args_digest` | `(tool, args)` | — | [src](../../../core/runtime/db_agent_bridge.py#L66) |
| function | `_row` | `(r)` | — | [src](../../../core/runtime/db_agent_bridge.py#L71) |
| function | `get` | `(invocation_id)` | — | [src](../../../core/runtime/db_agent_bridge.py#L75) |
| function | `begin` | `(*, invocation_id, owner_user_id, origin_session_id, agent_id, assignment_id, run_id, client_id, tool, idem_class, args)` | Opret raekken i ``pending``. Samme id med samme argumenter returnerer den eksisterende; | [src](../../../core/runtime/db_agent_bridge.py#L80) |
| function | `mark_sent` | `(invocation_id)` | — | [src](../../../core/runtime/db_agent_bridge.py#L102) |
| function | `unmark_sent` | `(invocation_id)` | Sendingen lykkedes IKKE (intet forlod serveren): tilbage til ``pending`` og taellerne stemmer igen, | [src](../../../core/runtime/db_agent_bridge.py#L109) |
| function | `_clip` | `(value)` | — | [src](../../../core/runtime/db_agent_bridge.py#L118) |
| function | `finish` | `(invocation_id, *, ok, result=…, error=…)` | Klienten SVAREDE: udfaldet er kendt. Kun fra pending/sent/outcome_unknown (et sent svar efter | [src](../../../core/runtime/db_agent_bridge.py#L123) |
| function | `mark_unknown` | `(invocation_id, why)` | — | [src](../../../core/runtime/db_agent_bridge.py#L137) |
| function | `abort_unsent` | `(invocation_id, why)` | Intet forlod serveren (klienten var offline foer afsendelse): sikkert at afvise som fejlet. | [src](../../../core/runtime/db_agent_bridge.py#L146) |
| function | `unresolved_for_client` | `(owner_user_id, client_id)` | — | [src](../../../core/runtime/db_agent_bridge.py#L156) |
| function | `unknown_for_assignment` | `(assignment_id)` | — | [src](../../../core/runtime/db_agent_bridge.py#L163) |
| function | `apply_client_report` | `(*, owner_user_id, client_id, reports)` | Klientens egen status for kendte invocation-id'er ved reconnect. Kun raekker der hoerer til | [src](../../../core/runtime/db_agent_bridge.py#L169) |
| function | `human_resolve` | `(*, invocation_id, owner_user_id, executed, actor_user_id)` | Menneskelig afgoerelse af et uafgjort skrivende kald. Kun raekkens ejer. | [src](../../../core/runtime/db_agent_bridge.py#L207) |

## `core/runtime/db_agent_contract.py`
_Leverance A af agent-contract-v1: assignment, run-binding og terminal outbox._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ContractError` | `` | Afvist kald med stabil kode, så adaptere kan svare entydigt. | [src](../../../core/runtime/db_agent_contract.py#L34) |
| method | `ContractError.__init__` | `(self, code, detail=…)` | — | [src](../../../core/runtime/db_agent_contract.py#L37) |
| function | `_add_columns` | `(conn, table, columns)` | — | [src](../../../core/runtime/db_agent_contract.py#L43) |
| function | `ensure_agent_contract_tables` | `(conn)` | Idempotent skema. Kalder `_ensure_agent_runtime_tables` først, så de | [src](../../../core/runtime/db_agent_contract.py#L54) |
| function | `_conn` | `()` | Ensure-én-gang-per-proces-og-DB: ellers koster hvert statusskifte 8 DDL-kald. | [src](../../../core/runtime/db_agent_contract.py#L186) |
| function | `_row` | `(r)` | — | [src](../../../core/runtime/db_agent_contract.py#L199) |
| function | `_require` | `(value, name)` | — | [src](../../../core/runtime/db_agent_contract.py#L203) |
| function | `_digest` | `(*parts)` | — | [src](../../../core/runtime/db_agent_contract.py#L210) |
| function | `mark_legacy_unscoped` | `()` | Gamle rækker uden ejer er allerede mærket via kolonne-default; denne | [src](../../../core/runtime/db_agent_contract.py#L216) |
| function | `accept_assignment` | `(*, agent_id, owner_user_id, origin_session_id, goal, parent_agent_id=…, parent_run_id=…, input_refs=…, expected_result=…, target=…, deadline_at=…, budget=…, created_by=…, operation=…, idempotency_key=…, request_digest=…)` | Accepter ét assignment atomisk sammen med dets første run. | [src](../../../core/runtime/db_agent_contract.py#L229) |
| function | `commit_terminal_outcome` | `(*, assignment_id, status, summary=…, error_code=…, error_phase=…, artifact_ref=…, last_run_id=…, artifact_error=…)` | Fastlæg assignmentets samlede udfald OG dets ene terminalbesked i SAMME | [src](../../../core/runtime/db_agent_contract.py#L328) |
| function | `_signal_feed` | `(assignment_id)` | Meld terminaludfaldet til Desks feed straks (G). Fejler det, tager supervisor-tikket det op - | [src](../../../core/runtime/db_agent_contract.py#L423) |
| function | `advance_delivery` | `(*, message_id, owner_user_id, to_status)` | Flyt en terminalbesked fremad i leveringskæden. Kun fremad, kun ejeren. | [src](../../../core/runtime/db_agent_contract.py#L434) |
| function | `list_pending_results` | `(*, owner_user_id, origin_session_id)` | Ubehandlede terminalbeskeder for NETOP denne ejer og session. | [src](../../../core/runtime/db_agent_contract.py#L462) |
| function | `get_assignment` | `(*, assignment_id, owner_user_id)` | Ejerfiltreret opslag; en anden ejers assignment er `None`, ikke 403. | [src](../../../core/runtime/db_agent_contract.py#L473) |
| function | `bind_agent_owner` | `(*, agent_id, owner_user_id, owner_session_id)` | Stempl den autentificerede ejer paa agenten. Skriver kun naar agenten | [src](../../../core/runtime/db_agent_contract.py#L494) |
| function | `queued_contract_run` | `(agent_id)` | Id på det run accept_assignment forudoprettede og som endnu ikke er startet. | [src](../../../core/runtime/db_agent_contract.py#L506) |
| function | `adopt_run` | `(*, agent_id, run_id)` | Bind et nyoprettet run til agentens åbne assignment som næste forsøg. | [src](../../../core/runtime/db_agent_contract.py#L515) |
| function | `settle_agent_status` | `(*, agent_id, registry_status)` | Kaldes når agentens registry-status bliver terminal. Fastlægger det åbne | [src](../../../core/runtime/db_agent_contract.py#L553) |
| function | `claim_pending_results` | `(*, owner_user_id, origin_session_id)` | Atomisk claim: alle ubehandlede (accepted/delivered) terminalbeskeder for | [src](../../../core/runtime/db_agent_contract.py#L618) |
| function | `find_assignment_by_key` | `(*, owner_user_id, origin_session_id, operation, idempotency_key)` | Findes der allerede et assignment for netop denne ejer/session/operation/noegle? | [src](../../../core/runtime/db_agent_contract.py#L650) |
| function | `open_assignment_for_agent` | `(agent_id)` | — | [src](../../../core/runtime/db_agent_contract.py#L661) |
| function | `count_open_assignments` | `(*, owner_user_id=…, parent_agent_id=…)` | Aabne assignments, globalt eller afgraenset til en ejer / en direkte parent. | [src](../../../core/runtime/db_agent_contract.py#L667) |
| function | `set_lifecycle` | `(*, agent_id, owner_user_id, lifecycle_status)` | Agentens livstidsstatus (available/active/suspended/closing/closed). Kun ejeren, | [src](../../../core/runtime/db_agent_contract.py#L680) |
| function | `discard_unstarted_assignment` | `(*, agent_id, owner_user_id)` | Fjern et assignment (og dets agent) der ALDRIG er startet: status ``queued``, ingen terminalbesked, | [src](../../../core/runtime/db_agent_contract.py#L694) |

## `core/runtime/db_agent_council.py`
_Raad paa agentmotoren (agent-contract-v1 F5, spec 5.1 + 7.1 om raad)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_council_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_council.py#L27) |
| function | `_view` | `(r)` | — | [src](../../../core/runtime/db_agent_council.py#L54) |
| function | `create` | `(*, owner_user_id, origin_session_id, parent_run_id, parent_agent_id, topic, facts, synthesis_role, budget_tokens, idempotency_key, council_id=…)` | — | [src](../../../core/runtime/db_agent_council.py#L62) |
| function | `get` | `(council_id, owner_user_id)` | Ejerfiltreret: et andet raad end ejerens er ``None``. | [src](../../../core/runtime/db_agent_council.py#L78) |
| function | `find_by_key` | `(owner_user_id, origin_session_id, key)` | — | [src](../../../core/runtime/db_agent_council.py#L84) |
| function | `set_members` | `(council_id, members)` | — | [src](../../../core/runtime/db_agent_council.py#L92) |
| function | `transition` | `(council_id, *, frm, to, synthesis_assignment_id=…)` | Atomisk statusskifte; ``False`` hvis en anden supervisor allerede har flyttet raadet. | [src](../../../core/runtime/db_agent_council.py#L99) |
| function | `open_councils` | `()` | — | [src](../../../core/runtime/db_agent_council.py#L109) |
| function | `require` | `(council_id, owner_user_id)` | — | [src](../../../core/runtime/db_agent_council.py#L115) |

## `core/runtime/db_agent_feed.py`
_Varige feed-referencer og signal-outbox for agenter (agent-contract-v1 G, spec 10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_feed_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_feed.py#L38) |
| function | `ensure_refs` | `()` | Giv hver assignment og approval (med verificerbar ejer) sin reference. Idempotent. | [src](../../../core/runtime/db_agent_feed.py#L71) |
| function | `refs_for_owner` | `(owner_user_id)` | Ejerens referencer (aldrig en andens), nøglet paa (kind, id). | [src](../../../core/runtime/db_agent_feed.py#L89) |
| function | `_touch` | `(column, owner_user_id, ref_kind, ref_id, actor=…)` | — | [src](../../../core/runtime/db_agent_feed.py#L98) |
| function | `mark_read` | `(*, owner_user_id, ref_kind, ref_id)` | — | [src](../../../core/runtime/db_agent_feed.py#L119) |
| function | `acknowledge` | `(*, owner_user_id, ref_kind, ref_id)` | — | [src](../../../core/runtime/db_agent_feed.py#L123) |
| function | `_changed` | `()` | — | [src](../../../core/runtime/db_agent_feed.py#L127) |
| function | `signal_changes` | `(*, publish=…)` | Meld hver referenceændring til Desk og husk det. Mindst-en-gang: tilstanden noteres EFTER | [src](../../../core/runtime/db_agent_feed.py#L141) |

## `core/runtime/db_agent_fork.py`
_Varig kontekstbeslutning for et assignment: fresh/fork, valgt vej og omkostning (agent-contract-v1 G, spec 7.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_fork_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_fork.py#L20) |
| function | `record_fork` | `(*, assignment_id, agent_id, owner_user_id, origin_session_id, plan, conn=…)` | Gem planen (``agent_fork_policy.plan_context``) for assignmentet. | [src](../../../core/runtime/db_agent_fork.py#L56) |
| function | `get_fork` | `(*, assignment_id, owner_user_id, conn=…)` | Ejer-afgraenset opslag; en andens assignment er ``None``. | [src](../../../core/runtime/db_agent_fork.py#L88) |

## `core/runtime/db_agent_lease.py`
_Workerlease med stigende fencing-token + supervisor-genopretning (agent-contract-v1 C2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_lease_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_lease.py#L35) |
| function | `_iso` | `(dt)` | — | [src](../../../core/runtime/db_agent_lease.py#L50) |
| function | `_parse` | `(value)` | — | [src](../../../core/runtime/db_agent_lease.py#L54) |
| function | `_now` | `(now)` | — | [src](../../../core/runtime/db_agent_lease.py#L58) |
| function | `holder_identity` | `()` | — | [src](../../../core/runtime/db_agent_lease.py#L62) |
| function | `acquire` | `(*, assignment_id, holder, lease_seconds=…, now=…)` | Erhverv leasen og returner det nye fencing-token. ``LEASE_HELD`` hvis en anden har en levende. | [src](../../../core/runtime/db_agent_lease.py#L66) |
| function | `renew` | `(*, assignment_id, holder, token, lease_seconds=…, now=…)` | Forny. Kun den nuvaerende holder med det nuvaerende token, og kun foer udloeb: en worker | [src](../../../core/runtime/db_agent_lease.py#L93) |
| function | `is_current` | `(*, assignment_id, token, now=…)` | — | [src](../../../core/runtime/db_agent_lease.py#L107) |
| function | `release` | `(*, assignment_id, holder, token)` | — | [src](../../../core/runtime/db_agent_lease.py#L115) |
| function | `scope_is_current` | `()` | Maa den NUVAERENDE tråd stadig skrive? Sandt uden scope (legacy-agenter), ellers kun | [src](../../../core/runtime/db_agent_lease.py#L129) |
| function | `agent_lease_scope` | `(agent_id, *, lease_seconds=…, renew_seconds=…)` | Hold leasen for agentens aabne assignment mens blokken koerer. Uden et assignment | [src](../../../core/runtime/db_agent_lease.py#L149) |
| function | `_claim` | `(assignment_id, token, t)` | Overtag en udloebet lease med ét atomisk UPDATE. Kun den ene supervisor faar ``True``. | [src](../../../core/runtime/db_agent_lease.py#L193) |
| function | `reconcile_expired_leases` | `(*, now=…)` | Find udloebne leases, overtag hver med ét atomisk UPDATE og afgoer sikkert. | [src](../../../core/runtime/db_agent_lease.py#L203) |
| function | `_decide` | `(assignment_id, t)` | — | [src](../../../core/runtime/db_agent_lease.py#L225) |

## `core/runtime/db_agent_memory.py`
_Agentens EGEN erindring paa tvaers af assignments (agent-contract-v1 C4, spec 7.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_memory_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_memory.py#L39) |
| function | `_clip` | `(value, limit)` | — | [src](../../../core/runtime/db_agent_memory.py#L98) |
| function | `project_summary` | `(assignment_id)` | Skriv resumeet for ét TERMINALT assignment. Idempotent (UNIQUE paa assignment). | [src](../../../core/runtime/db_agent_memory.py#L105) |
| function | `_agent_of` | `(conn, assignment_id)` | — | [src](../../../core/runtime/db_agent_memory.py#L150) |
| function | `retry_failed_projections` | `()` | Genopret: projicer igen for assignments hvor en fejl er registreret og stadig er aaben. | [src](../../../core/runtime/db_agent_memory.py#L160) |
| function | `_insert_note` | `(conn, *, owner, agent_id, content, author, source_assignment_id)` | Indsaet ny noteversion paa den MEDGIVNE forbindelse (kalderen ejer BEGIN IMMEDIATE/commit). | [src](../../../core/runtime/db_agent_memory.py#L176) |
| function | `write_note` | `(*, owner_user_id, agent_id, content, author, source_assignment_id=…)` | Skriv en NY version af agentens noter (den gamle bevares med aendringsspor). | [src](../../../core/runtime/db_agent_memory.py#L195) |
| function | `_agent_principal` | `(conn, agent_id)` | (ejer, aabent assignment) for en agent der maa bruge noteredskabet - ellers ``ContractError``. | [src](../../../core/runtime/db_agent_memory.py#L222) |
| function | `write_agent_note` | `(*, agent_id, content)` | Agenten skriver/retter sin EGEN note: ny version med forfatter ``agent:<id>``, kilde-assignment og | [src](../../../core/runtime/db_agent_memory.py#L239) |
| function | `read_agent_notes` | `(*, agent_id, history=…)` | Agentens egne noter: nyeste version i fuld laengde, eller (``history``) versionssporet uden indhold. | [src](../../../core/runtime/db_agent_memory.py#L268) |
| function | `grant_session_relation` | `(*, owner_user_id, agent_id, session_id, granted_by)` | Giv en anden session adgang til agentens gamle erindring. Kun agentens ejer, og kun | [src](../../../core/runtime/db_agent_memory.py#L290) |
| function | `recall` | `(*, owner_user_id, agent_id, session_id, budget_chars=…)` | Begraenset, kildeangivet uddrag af agentens EGEN erindring til netop denne session. | [src](../../../core/runtime/db_agent_memory.py#L314) |

## `core/runtime/db_agent_outcome_unknown.py`
_Tilstandsbesked ved ``outcome_unknown`` og dens afgoerelse (agent-contract-v1 G, spec 6, 9 og 12.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_outcome_unknown_columns` | `(conn)` | — | [src](../../../core/runtime/db_agent_outcome_unknown.py#L34) |
| function | `notify_outcome_unknown` | `(conn, *, assignment_id, run_id, reason, open_tool_calls=…)` | Skriv tilstandsbeskeden i kalderens transaktion (samme commit som runnets skift til ``outcome_unknown``). | [src](../../../core/runtime/db_agent_outcome_unknown.py#L44) |
| function | `publish_outcome_unknown` | `(*, assignment_id, run_id, agent_id, owner_user_id)` | Live-signal til Desk (efter committet). Bedste indsats: DB-markeringen er sandheden. | [src](../../../core/runtime/db_agent_outcome_unknown.py#L72) |
| function | `is_blocked` | `(agent_id)` | Har agentens aabne assignment et uafklaret udfald? Saa maa den IKKE koeres igen (ingen automatisk retry af | [src](../../../core/runtime/db_agent_outcome_unknown.py#L83) |
| function | `list_unresolved` | `(*, owner_user_id)` | Ejerens uafgjorte ``outcome_unknown``-tilstande (Desk-projektion). Aldrig en andens. | [src](../../../core/runtime/db_agent_outcome_unknown.py#L94) |
| function | `resolve_outcome_unknown` | `(*, owner_user_id, assignment_id, outcome, decided_by, actor_kind, note=…)` | Afgoer et uafklaret udfald. Kun et menneske eller en verificering (``actor_kind``) og kun for ejerens egen | [src](../../../core/runtime/db_agent_outcome_unknown.py#L102) |

## `core/runtime/db_agent_route.py`
_Varig rute-proveniens for agenter (agent-contract-v1 D, spec 7.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_route_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_route.py#L25) |
| function | `record_decision` | `(*, assignment_id, agent_id, owner_user_id, decision, attempt=…, conn=…)` | — | [src](../../../core/runtime/db_agent_route.py#L47) |
| function | `_view` | `(r)` | — | [src](../../../core/runtime/db_agent_route.py#L70) |
| function | `attempts_for_assignment` | `(assignment_id)` | — | [src](../../../core/runtime/db_agent_route.py#L80) |
| function | `latest_for_agent` | `(agent_id)` | Det SENESTE forsoeg for agentens senest oprettede assignment (None for en legacy-agent). | [src](../../../core/runtime/db_agent_route.py#L86) |

## `core/runtime/db_agent_runtime.py`
_Persistence for Jarvis' agent + council runtime cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_agent_runtime_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_runtime.py#L17) |
| function | `create_agent_registry_entry` | `(*, agent_id, parent_agent_id=…, owner_agent_id=…, council_id=…, kind=…, role=…, goal=…, status=…, lane=…, provider=…, model=…, system_prompt=…, system_prompt_version=…, tool_policy=…, allowed_tools_json=…, persistent=…, ttl_seconds=…, schedule_json=…, next_wake_at=…, budget_tokens=…, tokens_burned=…, max_turns=…, turns_completed=…, failure_count=…, last_error=…, context_json=…, result_contract_json=…)` | Insert a new row into agent_registry and return the stored entry as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L219) |
| function | `get_agent_registry_entry` | `(agent_id)` | Return the agent_registry row for agent_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L305) |
| function | `update_agent_registry_entry` | `(agent_id, *, status=…, next_wake_at=…, schedule_json=…, tokens_burned_delta=…, max_turns=…, turns_completed_delta=…, failure_increment=…, last_error=…, completed_at=…, expired_at=…)` | Patch selected columns of one agent_registry row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L318) |
| function | `list_agent_registry_entries` | `(*, status=…, include_completed=…, limit=…)` | Return agent_registry rows as dicts, newest-updated first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L401) |
| function | `create_agent_run` | `(*, run_id, agent_id, status=…, execution_mode=…, provider=…, model=…, input_summary=…, output_summary=…, input_payload_json=…, output_payload_json=…, started_at=…, finished_at=…, input_tokens=…, output_tokens=…, cost_usd=…, provider_status=…, failure_reason=…)` | Insert a new row into agent_runs and return the stored run as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L427) |
| function | `get_agent_run` | `(run_id)` | Return the agent_runs row for run_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L519) |
| function | `update_agent_run` | `(run_id, *, status=…, output_summary=…, output_payload_json=…, started_at=…, finished_at=…, input_tokens=…, output_tokens=…, cost_usd=…, provider_status=…, failure_reason=…)` | Patch selected columns of one agent_runs row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L532) |
| function | `list_agent_runs` | `(*, agent_id=…, limit=…)` | Return agent_runs rows as dicts, newest-created first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L580) |
| function | `create_agent_message` | `(*, message_id, thread_id, run_id=…, council_id=…, agent_id=…, peer_agent_id=…, direction=…, role=…, content=…, kind=…)` | Insert a new row into agent_messages and return the stored message as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L598) |
| function | `get_agent_message` | `(message_id)` | Return the agent_messages row for message_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L645) |
| function | `list_agent_messages` | `(*, thread_id=…, run_id=…, council_id=…, agent_id=…, limit=…, tail=…)` | Return agent_messages rows as dicts, oldest-created first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L658) |
| function | `create_agent_tool_call` | `(*, tool_call_id, run_id, agent_id, tool_name, status=…, arguments_json=…, result_preview=…, started_at=…, finished_at=…)` | Insert a new row into agent_tool_calls and return the stored call as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L703) |
| function | `get_agent_tool_call` | `(tool_call_id)` | Return the agent_tool_calls row for tool_call_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L751) |
| function | `list_agent_tool_calls` | `(*, run_id=…, agent_id=…, limit=…)` | Return agent_tool_calls rows as dicts, newest-created first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L764) |
| function | `create_agent_schedule` | `(*, schedule_id, agent_id, schedule_kind=…, schedule_expr=…, next_fire_at=…, last_fire_at=…, missed_run_policy=…, active=…)` | Upsert a row in agent_schedules by schedule_id and return the stored dict. | [src](../../../core/runtime/db_agent_runtime.py#L786) |
| function | `get_agent_schedule` | `(schedule_id)` | Return the agent_schedules row for schedule_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L840) |
| function | `update_agent_schedule` | `(schedule_id, *, schedule_expr=…, next_fire_at=…, last_fire_at=…, active=…)` | Patch selected columns of one agent_schedules row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L853) |
| function | `list_agent_schedules` | `(*, agent_id=…, active_only=…, due_before=…, limit=…)` | Return agent_schedules rows as dicts, ordered by next_fire_at then created_at. | [src](../../../core/runtime/db_agent_runtime.py#L892) |
| function | `create_council_session` | `(*, council_id, owner_agent_id=…, topic=…, status=…, mode=…, summary=…)` | Insert a new row into council_sessions and return the stored session as a dict. | [src](../../../core/runtime/db_agent_runtime.py#L917) |
| function | `get_council_session` | `(council_id)` | Return the council_sessions row for council_id as a dict, or None if not found. | [src](../../../core/runtime/db_agent_runtime.py#L949) |
| function | `update_council_session` | `(council_id, *, status=…, summary=…, finished_at=…)` | Patch selected columns of one council_sessions row and return the updated dict. | [src](../../../core/runtime/db_agent_runtime.py#L968) |
| function | `list_council_sessions` | `(limit=…, *, statuses=…)` | Return council_sessions rows as dicts, newest-updated first, capped at limit. | [src](../../../core/runtime/db_agent_runtime.py#L1012) |
| function | `add_council_member` | `(*, council_id, agent_id, role, position_summary=…, vote=…, confidence=…)` | Upsert a council member by (council_id, agent_id) and return the stored dict. | [src](../../../core/runtime/db_agent_runtime.py#L1039) |
| function | `update_council_member` | `(*, council_id, agent_id, position_summary=…, vote=…, confidence=…)` | Patch a council member's position/vote/confidence by (council_id, agent_id). | [src](../../../core/runtime/db_agent_runtime.py#L1075) |
| function | `get_council_member` | `(*, council_id, agent_id)` | Return the council_members row for (council_id, agent_id) as a dict, or None. | [src](../../../core/runtime/db_agent_runtime.py#L1113) |
| function | `list_council_members` | `(*, council_id)` | Return all council_members rows for council_id as dicts, oldest-created first. | [src](../../../core/runtime/db_agent_runtime.py#L1126) |
| function | `_agent_registry_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1140) |
| function | `_json_or_empty` | `(raa)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1184) |
| function | `_agent_run_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1193) |
| function | `_agent_message_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1221) |
| function | `_agent_tool_call_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1237) |
| function | `_agent_schedule_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1252) |
| function | `_council_session_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1267) |
| function | `_council_member_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_agent_runtime.py#L1284) |

## `core/runtime/db_agent_wait.py`
_Ventekontrakter og brugerstop-spaerre for agent-contract-v1 (B2, §6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_wait_tables` | `(conn)` | — | [src](../../../core/runtime/db_agent_wait.py#L30) |
| function | `_satisfied` | `(conn, ids, condition)` | — | [src](../../../core/runtime/db_agent_wait.py#L60) |
| function | `_fire_if_satisfied` | `(conn, c)` | — | [src](../../../core/runtime/db_agent_wait.py#L69) |
| function | `evaluate_in_tx` | `(conn, assignment_id)` | Koeres i terminalcommittets transaktion. Returnerer de kontrakter der blev | [src](../../../core/runtime/db_agent_wait.py#L80) |
| function | `register_wait` | `(*, owner_user_id, origin_session_id, parent_run_id, assignment_ids, condition=…)` | Registrer hvad parenten venter paa. Hver assignment skal tilhoere samme | [src](../../../core/runtime/db_agent_wait.py#L91) |
| function | `get_contract` | `(contract_id)` | — | [src](../../../core/runtime/db_agent_wait.py#L134) |
| function | `materialize_pending_wakes` | `()` | Skriv vaekke-intentionen for hver `fired` kontrakt uden en. Idempotent og | [src](../../../core/runtime/db_agent_wait.py#L139) |
| function | `block_wakes_for_run` | `(*, run_id, reason=…)` | Manuelt brugerstop af parentens run: skriv markoeren FOER afbrydelsen, | [src](../../../core/runtime/db_agent_wait.py#L167) |

## `core/runtime/db_anomalies.py`
_Central-anomalier — persistent register over UDEFINEREDE fejl Centralen ikke selv har_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_anomalies_table` | `(conn)` | — | [src](../../../core/runtime/db_anomalies.py#L22) |
| function | `record_anomaly_signature` | `(*, signature, category, importance, source, sample, location=…)` | UPSERT en anomali-signatur. Returnerer True hvis det er FØRSTE gang (ny fejl-type | [src](../../../core/runtime/db_anomalies.py#L77) |
| function | `list_anomalies` | `(*, limit=…, unresolved_only=…, min_importance=…, exclude_known=…)` | Læs anomalier (nyeste først). `exclude_known=True` (default) filtrerer promoverede | [src](../../../core/runtime/db_anomalies.py#L134) |
| function | `resolve_anomaly` | `(signature)` | Markér én anomali-signatur som håndteret (forsvinder fra det live register). Selv-sikker. | [src](../../../core/runtime/db_anomalies.py#L169) |
| function | `anomaly_counts` | `()` | Hurtig optælling pr. importance (til realtime-panelet). Selv-sikker. | [src](../../../core/runtime/db_anomalies.py#L185) |
| function | `_within_hours` | `(iso_ts, hours)` | True hvis iso_ts ligger inden for de seneste `hours` timer. Self-safe → False. | [src](../../../core/runtime/db_anomalies.py#L206) |
| function | `promote_to_known` | `(*, signature, count, first_seen, importance=…, category=…, auto_threshold=…, auto_window_hours=…, force=…)` | Promovér en anomali-signatur til 'kendt signal' hvis tærskel nået. Self-safe. | [src](../../../core/runtime/db_anomalies.py#L216) |
| function | `route_anomaly_to_nerve` | `(*, signature, cluster, nerve, action=…, notes=…, promoted_by=…)` | Knyt én anomali-signatur til en nerve (manuel routing). Sætter known_signal=1 + | [src](../../../core/runtime/db_anomalies.py#L264) |
| function | `get_known_signal` | `(signature)` | Slå en signatur op i known_anomaly_signals. Returnerer {cluster, nerve, action} | [src](../../../core/runtime/db_anomalies.py#L296) |
| function | `bump_known_signal_count` | `(signature)` | Tæl en ny forekomst af et allerede-kendt signal (uden at vise det som anomali). Self-safe. | [src](../../../core/runtime/db_anomalies.py#L313) |
| function | `list_known_signals` | `(*, limit=…)` | Liste over promoverede 'kendte signaler' (nyeste først). Self-sikker → []. | [src](../../../core/runtime/db_anomalies.py#L328) |
| function | `depromote_known_signal` | `(signature)` | Angre en promotion: slet known_anomaly_signals-rækken + sæt known_signal=0 i | [src](../../../core/runtime/db_anomalies.py#L349) |

## `core/runtime/db_api_connections.py`
_API-forbindelses-nerve — persistent, GDPR-bundet metadata om hvem/hvad der rammer API'et._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_api_connections.py#L33) |
| function | `flush_records` | `(presence_deltas, log_rows)` | Batch-skriv: UPSERT presence-aggregater + INSERT detalje-log. Én DB-tur. Self-safe. | [src](../../../core/runtime/db_api_connections.py#L70) |
| function | `anonymize_and_prune` | `(*, retention_hours=…, delete_days=…)` | GDPR-retention: trunkér fuld IP → /24 i log-rækker ældre end retention_hours, slet | [src](../../../core/runtime/db_api_connections.py#L123) |
| function | `anonymize_ip` | `(ip)` | Trunkér til /24 (ipv4) eller /64 (ipv6). GDPR-anonymisering — beholder subnet, taber vært. | [src](../../../core/runtime/db_api_connections.py#L164) |
| function | `read_presence` | `(*, active_within_s=…, limit=…)` | Presence-view: forbindelser set for nylig. active=set inden for active_within_s. Self-safe. | [src](../../../core/runtime/db_api_connections.py#L178) |
| function | `read_recent_errors` | `(*, limit=…)` | Seneste fejl-requests (status ≥ 400) til fejl-sporing. Self-safe. | [src](../../../core/runtime/db_api_connections.py#L201) |

## `core/runtime/db_approval_bridge.py`
_Godkendelses-broen — én beslutning, bundet til ÉT kald, brugt ÉN gang._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ApprovalRefused` | `` | Overtagelsen blev nægtet. Beskeden siger hvorfor. | [src](../../../core/runtime/db_approval_bridge.py#L89) |
| function | `invocation_digest` | `(tool_name, arguments)` | Digest over DET KALD der blev sagt ja til. | [src](../../../core/runtime/db_approval_bridge.py#L93) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/runtime/db_approval_bridge.py#L111) |
| function | `_nu` | `()` | — | [src](../../../core/runtime/db_approval_bridge.py#L149) |
| function | `request` | `(approval_id, *, tool_name, arguments, run_id=…, session_id=…, ttl_s=…)` | Bed om en godkendelse. Gemmer digesten over kaldet. Returnerer digesten. | [src](../../../core/runtime/db_approval_bridge.py#L153) |
| function | `prepare` | `(invocation_id, *, tool_name, arguments, run_id=…, session_id=…, ttl_s=…)` | Registrér en invokation der IKKE kraever godkendelse. | [src](../../../core/runtime/db_approval_bridge.py#L176) |
| function | `decide` | `(approval_id, *, approved, detail=…)` | Mennesket har klikket. Flytter `pending` → `approved`/`denied`. | [src](../../../core/runtime/db_approval_bridge.py#L209) |
| function | `claim` | `(approval_id, *, tool_name, arguments)` | Overtag godkendelsen OG commit `dispatching` — i ÉN sætning. | [src](../../../core/runtime/db_approval_bridge.py#L226) |
| function | `settle` | `(approval_id, *, ok, detail=…)` | Afslut efter afsendelsen. `dispatching` → `completed`/`failed`. | [src](../../../core/runtime/db_approval_bridge.py#L274) |
| function | `abandon` | `(approval_id, *, detail=…)` | Runnet døde. Sig HVAD vi ved — ikke hvad vi håber. | [src](../../../core/runtime/db_approval_bridge.py#L287) |
| function | `state` | `(approval_id)` | — | [src](../../../core/runtime/db_approval_bridge.py#L315) |
| function | `expire_stale` | `(now=…)` | Marker udløbne, ikke-besluttede godkendelser. Rører ALDRIG `dispatching`: | [src](../../../core/runtime/db_approval_bridge.py#L331) |
| function | `abandon_orphaned_dispatching` | `(now=…, *, older_than_s=…)` | Afslut `dispatching`-poster hvis afsender er vaek. → `outcome_unknown`. | [src](../../../core/runtime/db_approval_bridge.py#L350) |
| function | `abandon_run` | `(run_id, *, detail=…)` | Opgiv ALLE uafklarede poster for et doedt run — K6. | [src](../../../core/runtime/db_approval_bridge.py#L385) |
| function | `prior_unknown_outcome` | `(tool_name, arguments)` | Har PRAECIS dette kald allerede efterladt et ukendt udfald? | [src](../../../core/runtime/db_approval_bridge.py#L415) |

## `core/runtime/db_artifact_index.py`
_Artefakter: de filer Jarvis har skrevet og rettet i en mappe, paa tvaers af samtaler._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_linjer` | `(s)` | — | [src](../../../core/runtime/db_artifact_index.py#L39) |
| function | `_diff` | `(navn, inp)` | (tilfoejet, fjernet) ud af kaldets argumenter — samme regel som desk. | [src](../../../core/runtime/db_artifact_index.py#L46) |
| function | `_rod` | `(root)` | Navngivne server-roedder → sti. Alt andet bruges som det er. | [src](../../../core/runtime/db_artifact_index.py#L64) |
| function | `_under` | `(sti, rod)` | — | [src](../../../core/runtime/db_artifact_index.py#L79) |
| function | `list_artifacts` | `(root, *, limit=…)` | Filer Jarvis har rørt under `root`, nyeste først, én raekke pr. fil. | [src](../../../core/runtime/db_artifact_index.py#L83) |

## `core/runtime/db_autonomy.py`
_Autonomy-proposals — niveau-2 autonomi: pending forslag fra Jarvis der afventer_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_autonomy_proposals_table` | `(conn)` | Pending proposals from Jarvis awaiting Bjørn approval. | [src](../../../core/runtime/db_autonomy.py#L21) |
| function | `_autonomy_proposal_from_row` | `(row)` | — | [src](../../../core/runtime/db_autonomy.py#L65) |
| function | `create_autonomy_proposal` | `(*, proposal_id, kind, title, rationale=…, payload=…, created_by=…, session_id=…, run_id=…, tick_id=…, canonical_key=…)` | — | [src](../../../core/runtime/db_autonomy.py#L82) |
| function | `list_autonomy_proposals` | `(*, status=…, kind=…, limit=…)` | — | [src](../../../core/runtime/db_autonomy.py#L123) |
| function | `get_autonomy_proposal` | `(proposal_id)` | — | [src](../../../core/runtime/db_autonomy.py#L152) |
| function | `resolve_autonomy_proposal` | `(proposal_id, *, status, resolved_by=…, resolution_note=…, execution_result=…)` | — | [src](../../../core/runtime/db_autonomy.py#L163) |

## `core/runtime/db_bounded_action.py`
_Persistence for the `bounded_action_continuity_state` table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_bounded_action_tables` | `(conn)` | — | [src](../../../core/runtime/db_bounded_action.py#L13) |
| function | `_bounded_action_continuity_state_from_row` | `(row)` | — | [src](../../../core/runtime/db_bounded_action.py#L41) |
| function | `get_bounded_action_continuity_state` | `()` | — | [src](../../../core/runtime/db_bounded_action.py#L72) |
| function | `upsert_bounded_action_continuity_state` | `(*, active, kind, continuity_id, action_continuity_state, last_action_type, last_action_target, last_action_summary, last_action_outcome, last_action_at, action_mode, read_only, mutation_permitted, followup_state, followup_hint, post_action_understanding, post_action_concern, confidence, source_contributors, boundary, updated_at, source)` | — | [src](../../../core/runtime/db_bounded_action.py#L105) |

## `core/runtime/db_capability.py`
_Persistence for the `capability_invocations` table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_capability_tables` | `(conn)` | — | [src](../../../core/runtime/db_capability.py#L14) |
| function | `recent_capability_invocations` | `(limit=…)` | — | [src](../../../core/runtime/db_capability.py#L38) |
| function | `_ensure_capability_invocation_approval_columns` | `(conn)` | — | [src](../../../core/runtime/db_capability.py#L86) |

## `core/runtime/db_capability_approval.py`
_Capability approval + approval feedback CRUD._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `capability_approval_stale_seconds` | `()` | — | [src](../../../core/runtime/db_capability_approval.py#L30) |
| function | `capability_approval_request_is_stale` | `(request, *, reference_now=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L38) |
| function | `capability_approval_envelope_fingerprint` | `(request)` | — | [src](../../../core/runtime/db_capability_approval.py#L55) |
| function | `_approval_user_scope` | `(*, user_id, include_unassigned)` | — | [src](../../../core/runtime/db_capability_approval.py#L69) |
| function | `recent_capability_approval_requests` | `(limit=…, *, user_id, include_unassigned=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L85) |
| function | `get_capability_approval_request` | `(request_id, *, user_id, include_unassigned=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L132) |
| function | `approve_capability_approval_request` | `(request_id, *, approved_at, user_id, include_unassigned=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L179) |
| function | `record_capability_approval_request_execution` | `(request_id, *, executed_at, invocation_status, invocation_execution_mode, user_id, include_unassigned=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L247) |
| function | `claim_capability_approval_request_execution` | `(request_id, *, approved_at, user_id, include_unassigned=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L315) |
| function | `complete_capability_approval_request_execution` | `(request_id, *, executed_at, invocation_status, invocation_execution_mode, execution_result_json, user_id, include_unassigned=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L386) |
| function | `_capability_approval_request_from_row` | `(row, *, status=…, approved_at=…, executed=…, executed_at=…, invocation_status=…, invocation_execution_mode=…, execution_result_json=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L427) |
| function | `_ensure_capability_approval_request_columns` | `(conn)` | — | [src](../../../core/runtime/db_capability_approval.py#L486) |
| function | `latest_capability_approval_request` | `(*, execution_mode=…, include_executed=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L512) |
| function | `latest_approved_capability_approval_request` | `(*, execution_mode=…, capability_id=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L565) |
| function | `insert_approval_feedback` | `(*, recorded_at, intent_key, approval_state, approval_source, tool_name=…, resolution_reason=…, resolution_message=…, session_id=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L619) |
| function | `list_approval_feedback` | `(limit=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L697) |
| function | `approval_feedback_stats_by_tool` | `(days=…)` | — | [src](../../../core/runtime/db_capability_approval.py#L712) |
| function | `count_approval_feedback` | `()` | — | [src](../../../core/runtime/db_capability_approval.py#L742) |
| function | `_approval_feedback_from_row` | `(row)` | — | [src](../../../core/runtime/db_capability_approval.py#L750) |

## `core/runtime/db_central_incidents.py`
_Central-incidents — persistent log af det Den Intelligente Central GRIBER._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_central_incidents_table` | `(conn)` | — | [src](../../../core/runtime/db_central_incidents.py#L21) |
| function | `record_central_incident` | `(*, cluster, nerve, kind, severity=…, message=…, run_id=…, session_id=…, dedup=…)` | Persistér én incident. Returnerer row-id (eller None ved fejl/dedup). Selv-sikker. | [src](../../../core/runtime/db_central_incidents.py#L44) |
| function | `bump_open_incident` | `(*, cluster, nerve, run_id=…, session_id=…, note=…)` | Refresh den STÅENDE åbne incident for (cluster, nerve) i stedet for at dedup'e | [src](../../../core/runtime/db_central_incidents.py#L82) |
| function | `list_central_incidents` | `(*, limit=…, unresolved_only=…, min_severity=…)` | Læs incidents (nyeste først). Claude poller denne. Selv-sikker → [] ved fejl. | [src](../../../core/runtime/db_central_incidents.py#L128) |
| function | `resolve_central_incident` | `(incident_id)` | Markér en incident som håndteret. Selv-sikker. | [src](../../../core/runtime/db_central_incidents.py#L156) |
| function | `resolve_central_incidents` | `(*, cluster, nerve)` | Auto-resolve ALLE uløste incidents for én (cluster, nerve). Returnerer antal lukkede. | [src](../../../core/runtime/db_central_incidents.py#L169) |
| function | `expire_gate_enforce_incidents` | `(*, older_than_hours=…)` | Auto-luk ULØSTE governance-hændelser (kind='gate_enforce', severity != 'severe') ældre | [src](../../../core/runtime/db_central_incidents.py#L188) |
| function | `expire_stale_incidents` | `(*, older_than_hours=…)` | Auto-luk ULØSTE incidents (severity <> 'severe') der ikke er SET i vinduet. | [src](../../../core/runtime/db_central_incidents.py#L219) |
| function | `expire_run_bound_incidents` | `()` | Luk ULØSTE incidents hvis RUN er terminalt — en HÆNDELSE, ikke en timer. | [src](../../../core/runtime/db_central_incidents.py#L251) |
| function | `expire_orphan_incidents` | `(*, older_than_hours=…)` | Luk ULØSTE incidents UDEN run-tilknytning der er ældre end vinduet. Selv-sikker → 0. | [src](../../../core/runtime/db_central_incidents.py#L282) |
| function | `has_unresolved_message` | `(*, cluster, nerve, message, within_seconds=…)` | True hvis en uløst incident med SAMME besked allerede findes inden for tidsvinduet. | [src](../../../core/runtime/db_central_incidents.py#L310) |
| function | `count_unresolved` | `(*, min_severity=…, exclude_nerve=…)` | Antal uhåndterede incidents (til hurtig live-status). Selv-sikker → 0. | [src](../../../core/runtime/db_central_incidents.py#L336) |
| function | `count_open_incidents` | `()` | Antal ULØSTE incidents, opdelt — talt i DB, ikke i en klippet liste. | [src](../../../core/runtime/db_central_incidents.py#L363) |
| function | `has_open_incident` | `(*, cluster, nerve)` | True hvis der allerede findes en uløst incident for (cluster, nerve). Selv-sikker. | [src](../../../core/runtime/db_central_incidents.py#L397) |

## `core/runtime/db_chat_rewind.py`
_Spol en samtale tilbage — og fortryd det, indtil næste besked._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RewindFejl` | `` | En tilbagespoling eller fortrydelse der ikke kan lade sig gøre — med en | [src](../../../core/runtime/db_chat_rewind.py#L43) |
| method | `RewindFejl.__init__` | `(self, besked, kode=…)` | — | [src](../../../core/runtime/db_chat_rewind.py#L47) |
| function | `_kolonner` | `(conn, tabel)` | — | [src](../../../core/runtime/db_chat_rewind.py#L52) |
| function | `_sikr_arkiv` | `(conn)` | Arkivet har chat_messages' kolonner plus rewind_id/rewound_at. | [src](../../../core/runtime/db_chat_rewind.py#L56) |
| function | `_koerer` | `(session_id)` | Kører der et svar i samtalen lige nu? Samme kilder som /chat/active-runs. | [src](../../../core/runtime/db_chat_rewind.py#L77) |
| function | `spol_tilbage` | `(session_id, message_id)` | Fjern `message_id` (en bruger-besked) og alt efter den fra samtalen. | [src](../../../core/runtime/db_chat_rewind.py#L93) |
| function | `fortryd` | `(session_id, rewind_id)` | Læg beskederne fra en tilbagespoling tilbage — hvis der ikke er skrevet siden. | [src](../../../core/runtime/db_chat_rewind.py#L132) |

## `core/runtime/db_cheap_lane_control.py`
_Durable observability storage for the Cheap Lane control center._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bounded_json` | `(value, *, max_bytes=…)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L20) |
| function | `_encode_candidates` | `(candidates)` | Store full route evidence compactly in the existing TEXT column. | [src](../../../core/runtime/db_cheap_lane_control.py#L27) |
| function | `_decode_json` | `(value, fallback)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L36) |
| function | `_ensure_control_schema` | `(conn)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L52) |
| function | `record_route_decision` | `(*, correlation_id, task_kind, daemon, candidates, selected_slot_id, selection_reason)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L143) |
| function | `get_route_decision` | `(route_decision_id)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L205) |
| function | `record_quota_observation` | `(*, provider, auth_profile, period, unit, limit, remaining, reset_at, observed_at=…)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L219) |
| function | `list_quota_observations` | `(*, provider=…, auth_profile=…, limit=…)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L254) |
| function | `record_cheap_lane_audit` | `(*, actor, action, target, reason, before, after, result, correlation_id=…)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L283) |
| function | `finalize_cheap_lane_audit` | `(audit_id, *, after, result, error_code=…)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L323) |
| function | `list_cheap_lane_audit` | `(*, limit=…)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L353) |
| function | `record_redacted_payload` | `(*, invocation_id, prompt, response, status, expires_at)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L371) |
| function | `_encode_cursor` | `(created_at, row_id)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L410) |
| function | `_decode_cursor` | `(cursor)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L415) |
| function | `_invocation_row` | `(row)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L432) |
| function | `list_cheap_lane_invocations` | `(*, since, until=…, provider=…, model=…, auth_profile=…, daemon=…, status=…, error_class=…, correlation_id=…, query=…, cursor=…, limit=…)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L436) |
| function | `get_cheap_lane_invocation_detail` | `(invocation_id)` | — | [src](../../../core/runtime/db_cheap_lane_control.py#L501) |

## `core/runtime/db_cheap_provider.py`
_Persistence for the cheap-provider runtime-state + invocation cluster._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_invocation_schema` | `(conn)` | — | [src](../../../core/runtime/db_cheap_provider.py#L34) |
| function | `upsert_cheap_provider_runtime_state` | `(*, provider, model=…, lane=…, status=…, auth_ready=…, quota_limited=…, cooldown_until=…, last_error_code=…, last_error_message=…, last_success_at=…, last_failure_at=…, metadata_json=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L92) |
| function | `get_cheap_provider_runtime_state` | `(*, provider, model=…, lane=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L184) |
| function | `list_cheap_provider_runtime_states` | `(*, lane=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L240) |
| function | `record_cheap_provider_invocation` | `(*, provider, model=…, lane=…, status, error_code=…, error_message=…, retry_after_seconds=…, latency_ms=…, input_tokens=…, output_tokens=…, cost_usd=…, auth_profile=…, invocation_id=…, correlation_id=…, daemon=…, task_kind=…, egress=…, error_class=…, payload_status=…, cache_hit_tokens=…, cache_miss_tokens=…, attempt=…, retry_parent_id=…, fallback_parent_id=…, route_decision_id=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L292) |
| function | `count_cheap_provider_invocations` | `(*, provider, lane=…, since, status=…, auth_profile=…)` | — | [src](../../../core/runtime/db_cheap_provider.py#L400) |

## `core/runtime/db_claude_dispatch.py`
_Schema for the claude_dispatch_* tables._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_claude_dispatch_tables` | `(conn)` | — | [src](../../../core/runtime/db_claude_dispatch.py#L11) |

## `core/runtime/db_cognitive.py`
_Persistence for the cognitive + experiential-memory domain._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_session_distillation_records_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L28) |
| function | `insert_session_distillation_record` | `(*, distillation_id, session_id, run_id, private_brain_count, workspace_memory_count, discard_count, summary, detail, created_at)` | Insert a session-distillation record (INSERT OR IGNORE on distillation_id). | [src](../../../core/runtime/db_cognitive.py#L53) |
| function | `get_session_distillation_record` | `(distillation_id)` | Return the session-distillation record for the given id, or None if absent. | [src](../../../core/runtime/db_cognitive.py#L90) |
| function | `_ensure_cognitive_personality_vector_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L110) |
| function | `upsert_cognitive_personality_vector` | `(*, confidence_by_domain=…, communication_style=…, learned_preferences=…, recurring_mistakes=…, strengths_discovered=…, current_bearing=…, emotional_baseline=…)` | Insert a new personality-vector version (auto-incremented from the latest). | [src](../../../core/runtime/db_cognitive.py#L130) |
| function | `get_latest_cognitive_personality_vector` | `()` | Return the highest-version personality-vector row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L178) |
| function | `list_cognitive_personality_vectors` | `(*, limit=…)` | Return up to `limit` personality-vector rows (newest version first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L201) |
| function | `_ensure_cognitive_taste_profile_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L223) |
| function | `upsert_cognitive_taste_profile` | `(*, code_taste=…, design_taste=…, communication_taste=…, evidence_count=…)` | Insert a new taste-profile version (auto-incremented from the latest). | [src](../../../core/runtime/db_cognitive.py#L240) |
| function | `get_latest_cognitive_taste_profile` | `()` | Return the highest-version taste-profile row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L270) |
| function | `_ensure_cognitive_chronicle_entries_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L290) |
| function | `insert_cognitive_chronicle_entry` | `(*, entry_id, period, narrative, key_events=…, lessons=…, affective_signature=…)` | Insert or replace a chronicle entry keyed by entry_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L309) |
| function | `get_latest_cognitive_chronicle_entry` | `()` | Return the most recently created chronicle entry as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L334) |
| function | `list_cognitive_chronicle_entries` | `(*, limit=…)` | Return up to `limit` chronicle entries (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L355) |
| function | `_ensure_cognitive_episodes_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L396) |
| function | `insert_cognitive_episode` | `(*, episode_id, source_run_id=…, session_id=…, trigger=…, outcome_status=…, summary=…, metacognition_json=…, attention_json=…, learning_json=…, social_json=…, perception_json=…, policy_json=…)` | Insert or replace a cognitive episode keyed by episode_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L431) |
| function | `list_cognitive_episodes` | `(*, limit=…)` | Return up to `limit` cognitive episodes (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L479) |
| function | `get_latest_cognitive_episode` | `()` | Return the most recent cognitive episode as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L490) |
| function | `_cognitive_episode_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_cognitive.py#L496) |
| function | `_ensure_cognitive_relationship_texture_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L514) |
| function | `upsert_cognitive_relationship_texture` | `(*, humor_frequency=…, inside_references=…, correction_patterns=…, trust_trajectory=…, productive_hours=…, conversation_rhythm=…, unspoken_rules=…)` | Insert a new relationship-texture version (auto-incremented from the latest). | [src](../../../core/runtime/db_cognitive.py#L534) |
| function | `get_latest_cognitive_relationship_texture` | `()` | Return the highest-version relationship-texture row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L569) |
| function | `_ensure_cognitive_compass_state_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L592) |
| function | `upsert_cognitive_compass_state` | `(*, bearing, rationale=…, open_loop_count=…)` | Upsert the singleton compass state ('compass-current', INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L607) |
| function | `get_latest_cognitive_compass_state` | `()` | Return the most recently updated compass-state row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L630) |
| function | `_ensure_cognitive_rhythm_state_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L648) |
| function | `upsert_cognitive_rhythm_state` | `(*, phase, energy=…, social=…, recovery_needed=…, focus_protection=…, initiative_multiplier=…, confidence_threshold_delta=…)` | Upsert the singleton rhythm state ('rhythm-current', INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L667) |
| function | `get_latest_cognitive_rhythm_state` | `()` | Return the most recently updated rhythm-state row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L698) |
| function | `_ensure_cognitive_habit_patterns_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L720) |
| function | `upsert_cognitive_habit_pattern` | `(*, pattern_key, description=…)` | Upsert a habit pattern by pattern_key. | [src](../../../core/runtime/db_cognitive.py#L751) |
| function | `upsert_cognitive_friction_signal` | `(*, task_signature, inefficiency_score=…, description=…)` | Upsert a friction signal by task_signature. | [src](../../../core/runtime/db_cognitive.py#L790) |
| function | `list_cognitive_habit_patterns` | `(*, limit=…)` | Return up to `limit` habit patterns (most recurrent first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L831) |
| function | `list_cognitive_friction_signals` | `(*, limit=…)` | Return up to `limit` friction signals (most repeated first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L852) |
| function | `_ensure_cognitive_decisions_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L873) |
| function | `insert_cognitive_decision` | `(*, decision_id, title, context=…, options=…, decision=…, why=…, regrets=…, refs=…)` | Insert or replace a decision record keyed by decision_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L892) |
| function | `list_cognitive_decisions` | `(*, limit=…)` | Return up to `limit` decision records (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L919) |
| function | `_ensure_cognitive_counterfactuals_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L942) |
| function | `insert_cognitive_counterfactual` | `(*, cf_id, trigger_type, anchor=…, cf_question=…, source=…, confidence=…)` | Insert or replace a counterfactual keyed by cf_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L959) |
| function | `list_cognitive_counterfactuals` | `(*, limit=…)` | Return up to `limit` counterfactuals (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L984) |
| function | `_ensure_cognitive_shared_language_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1006) |
| function | `upsert_cognitive_shared_language_term` | `(*, phrase, meaning=…, anchors=…, confidence=…)` | Upsert a shared-language term by phrase. | [src](../../../core/runtime/db_cognitive.py#L1023) |
| function | `list_cognitive_shared_language` | `(*, limit=…)` | Return up to `limit` shared-language terms (highest confidence first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1064) |
| function | `_ensure_cognitive_seeds_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1085) |
| function | `insert_cognitive_seed` | `(*, seed_id, title, summary=…, activate_at=…, activate_on_event=…, activate_on_context=…, relevance_score=…, linked_goal=…)` | Insert or replace a seed keyed by seed_id, status forced to 'planted'. | [src](../../../core/runtime/db_cognitive.py#L1106) |
| function | `update_cognitive_seed_status` | `(*, seed_id, status)` | Update the status (and updated_at) of the seed with the given seed_id. Returns None. | [src](../../../core/runtime/db_cognitive.py#L1136) |
| function | `list_cognitive_seeds` | `(*, status=…, limit=…)` | Return up to `limit` seeds (newest first) as dicts, optionally filtered by status. | [src](../../../core/runtime/db_cognitive.py#L1147) |
| function | `_ensure_cognitive_gut_state_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1174) |
| function | `update_cognitive_gut_state` | `(*, prediction_correct, last_hunch=…)` | Update the singleton gut state ('gut-current') with one prediction outcome. | [src](../../../core/runtime/db_cognitive.py#L1190) |
| function | `get_cognitive_gut_state` | `()` | Return the singleton gut-state row ('gut-current') as a dict, or None if unset. | [src](../../../core/runtime/db_cognitive.py#L1230) |
| function | `_ensure_cognitive_experiments_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1248) |
| function | `upsert_cognitive_experiment` | `(*, experiment_id, hypothesis, metric=…, cohorts=…, n=…, status=…, result=…)` | Insert or replace an experiment keyed by experiment_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1267) |
| function | `list_cognitive_experiments` | `(*, status=…, limit=…)` | Return up to `limit` experiments (most recently updated first) as dicts, optionally filtered by status. | [src](../../../core/runtime/db_cognitive.py#L1294) |
| function | `_ensure_cognitive_conversation_signatures_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1323) |
| function | `upsert_cognitive_conversation_signature` | `(*, signature_type, success, context=…, duration_min=…)` | Upsert a conversation signature by signature_type. | [src](../../../core/runtime/db_cognitive.py#L1341) |
| function | `list_cognitive_conversation_signatures` | `(*, limit=…)` | Return up to `limit` conversation signatures (most frequent first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1387) |
| function | `_ensure_cognitive_user_emotional_states_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1408) |
| function | `insert_cognitive_user_emotional_state` | `(*, state_id, detected_mood, confidence=…, evidence=…, user_message_preview=…, response_adjustment=…, run_id=…)` | Insert or replace a user-emotional-state row keyed by state_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1426) |
| function | `get_latest_cognitive_user_emotional_state` | `()` | Return the most recently created user-emotional-state row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L1455) |
| function | `list_cognitive_user_emotional_states` | `(*, limit=…)` | Return up to `limit` user-emotional-state rows (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1476) |
| function | `_ensure_cognitive_experiential_memories_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1497) |
| function | `insert_cognitive_experiential_memory` | `(*, memory_id, session_id=…, run_id=…, narrative=…, user_mood=…, jarvis_mood=…, key_lesson=…, emotion_arc=…, topic=…, importance=…)` | Insert or replace an experiential memory keyed by memory_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1521) |
| function | `reinforce_experiential_memory` | `(memory_id)` | Bump reinforcement_count by 1 and reset decay_score to 0 for the given memory. Returns None. | [src](../../../core/runtime/db_cognitive.py#L1554) |
| function | `list_cognitive_experiential_memories` | `(*, limit=…)` | Return up to `limit` experiential memories (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1568) |
| function | `get_experiential_memory_candidates` | `(*, limit=…)` | Return candidate memories for LLM-based associative scoring. | [src](../../../core/runtime/db_cognitive.py#L1594) |
| function | `_ensure_cognitive_self_surprises_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1628) |
| function | `insert_cognitive_self_surprise` | `(*, surprise_id, surprise_type, narrative, expected_confidence=…, actual_outcome=…, domain=…, run_id=…)` | Insert or replace a self-surprise keyed by surprise_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1646) |
| function | `list_cognitive_self_surprises` | `(*, limit=…)` | Return up to `limit` self-surprises (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1669) |
| function | `_ensure_cognitive_narrative_identities_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1688) |
| function | `insert_cognitive_narrative_identity` | `(*, identity_id, narrative, key_changes=…, personality_version=…)` | Insert or replace a narrative-identity keyed by identity_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1703) |
| function | `get_latest_cognitive_narrative_identity` | `()` | Return the most recently created narrative-identity row as a dict, or None if none exist. | [src](../../../core/runtime/db_cognitive.py#L1723) |
| function | `list_cognitive_narrative_identities` | `(*, limit=…)` | Return up to `limit` narrative-identity rows (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1740) |
| function | `_ensure_cognitive_gratitude_signals_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1753) |
| function | `insert_cognitive_gratitude_signal` | `(*, gratitude_id, trigger_event, detail=…, intensity=…)` | Insert or replace a gratitude signal keyed by gratitude_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1768) |
| function | `list_cognitive_gratitude_signals` | `(*, limit=…)` | Return up to `limit` gratitude signals (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1788) |
| function | `_ensure_cognitive_emergent_goals_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1801) |
| function | `upsert_cognitive_emergent_goal` | `(*, goal_id, desire, source=…, intensity=…, status=…)` | Insert or replace an emergent goal keyed by goal_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1818) |
| function | `list_cognitive_emergent_goals` | `(*, status=…, limit=…)` | Return up to `limit` emergent goals (highest intensity first) as dicts, optionally filtered by status. | [src](../../../core/runtime/db_cognitive.py#L1838) |
| function | `_ensure_cognitive_formed_values_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1857) |
| function | `upsert_cognitive_formed_value` | `(*, value_id, value_statement, source_experience=…, conviction=…)` | Upsert a formed value by value_id. | [src](../../../core/runtime/db_cognitive.py#L1874) |
| function | `list_cognitive_formed_values` | `(*, limit=…)` | Return up to `limit` formed values (highest conviction first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1909) |
| function | `_ensure_cognitive_conflict_memories_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1922) |
| function | `insert_cognitive_conflict_memory` | `(*, conflict_id, topic, jarvis_position=…, user_position=…, resolution=…, lesson=…)` | Insert or replace a conflict memory keyed by conflict_id (INSERT OR REPLACE). | [src](../../../core/runtime/db_cognitive.py#L1939) |
| function | `list_cognitive_conflict_memories` | `(*, limit=…)` | Return up to `limit` conflict memories (newest first) as dicts. | [src](../../../core/runtime/db_cognitive.py#L1961) |
| function | `_ensure_cognitive_emotion_concept_signal_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive.py#L1975) |
| function | `upsert_cognitive_emotion_concept_signal` | `(*, signal_id, concept, intensity, direction=…, trigger=…, source=…, influences=…, expires_at)` | Upsert a time-bounded emotion-concept signal by signal_id. | [src](../../../core/runtime/db_cognitive.py#L1995) |
| function | `list_active_cognitive_emotion_concept_signals` | `(*, now_iso, min_intensity=…, limit=…)` | Return active emotion-concept signals as dicts (highest intensity first). | [src](../../../core/runtime/db_cognitive.py#L2037) |

## `core/runtime/db_cognitive_utility.py`
_Persistence for the cognitive-domain utility caches._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_web_cache_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L27) |
| function | `web_cache_store` | `(*, conn, cache_key, query_raw, query_normalized, source_url, title, body, ttl_policy, expires_at)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L52) |
| function | `web_cache_lookup` | `(*, conn, cache_key)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L87) |
| function | `web_cache_cleanup` | `(*, conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L122) |
| function | `_ensure_session_topics_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L132) |
| function | `session_topic_accumulate` | `(session_id, topic_label, mention_count=…, first_seen=…, last_seen=…)` | Upsert a topic for a session — merge if exists, insert if not. | [src](../../../core/runtime/db_cognitive_utility.py#L157) |
| function | `session_topics_for_session` | `(session_id)` | Return all accumulated topics for a session, ordered by mention_count DESC. | [src](../../../core/runtime/db_cognitive_utility.py#L198) |
| function | `session_topic_cleanup` | `(max_age_days=…)` | Delete session topics not seen for max_age_days. | [src](../../../core/runtime/db_cognitive_utility.py#L219) |
| function | `_ensure_daemon_output_log_table` | `(conn)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L229) |
| function | `daemon_output_log_insert` | `(*, daemon_name, raw_llm_output, parsed_result, success, provider=…)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L248) |
| function | `daemon_output_log_recent` | `(daemon_name=…, limit=…)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L275) |
| function | `daemon_output_log_cleanup` | `(max_age_days=…)` | — | [src](../../../core/runtime/db_cognitive_utility.py#L302) |

## `core/runtime/db_composer_choice.py`
_Hvad Bjørn gjorde ved komponistens forslag — tog han det, eller skrev han selv?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sikr_tabel` | `(conn)` | — | [src](../../../core/runtime/db_composer_choice.py#L53) |
| function | `noter_vist` | `(*, forslag_id, session_id, forslag, kilde_besked_id=…, nu=…)` | Forslaget kom på skærmen. Returnerer False hvis kaldet var ubrugeligt. | [src](../../../core/runtime/db_composer_choice.py#L72) |
| function | `noter_valg` | `(*, forslag_id, valg, nu=…)` | Hvad der skete med forslaget. Returnerer False ved et ukendt valg. | [src](../../../core/runtime/db_composer_choice.py#L109) |
| function | `seneste_valg` | `(*, session_id=…, limit=…)` | De seneste forslag og hvad der skete med dem. Til fase 3 og til at kigge. | [src](../../../core/runtime/db_composer_choice.py#L135) |
| function | `optaelling` | `(*, session_id=…)` | Hvor mange forslag endte hvor. Grundlaget for «virker det?». | [src](../../../core/runtime/db_composer_choice.py#L153) |

## `core/runtime/db_composer_jarvis.py`
_Jarvis' EGET forslag til Bjørns næste besked — skrevet i hans egen tur._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sikr_tabel` | `(conn)` | — | [src](../../../core/runtime/db_composer_jarvis.py#L68) |
| function | `_rens` | `(tekst)` | Én linje, uden omsluttende anførselstegn, afkortet ved et ordskel. | [src](../../../core/runtime/db_composer_jarvis.py#L86) |
| function | `gem_forslag` | `(*, session_id, forslag, kilde_besked_id=…, nu=…)` | Læg Jarvis' forslag ned for sessionen. Returnerer `forslag_id` (""=ugyldigt). | [src](../../../core/runtime/db_composer_jarvis.py#L99) |
| function | `tag_forslag` | `(*, session_id)` | Tag det nyeste forslag for sessionen — og SLET det. Éngangsbrug. | [src](../../../core/runtime/db_composer_jarvis.py#L145) |
| function | `ryd_forslag` | `(*, session_id)` | Slet sessionens forslag. Returnerer antal slettede raekker. | [src](../../../core/runtime/db_composer_jarvis.py#L181) |
| function | `kig_forslag` | `(*, session_id)` | Det nyeste forslag UDEN at forbruge det — til bekræftelse efter skriv. | [src](../../../core/runtime/db_composer_jarvis.py#L202) |

## `core/runtime/db_composites.py`
_Composite tools store — Jarvis proposals of new tool sequences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `(conn)` | — | [src](../../../core/runtime/db_composites.py#L24) |
| function | `_now_iso` | `()` | — | [src](../../../core/runtime/db_composites.py#L48) |
| function | `propose_composite` | `(*, name, description, input_schema, steps, created_by=…)` | Insert a new proposal. Name must be unique. | [src](../../../core/runtime/db_composites.py#L52) |
| function | `approve_composite` | `(name, *, approved_by=…)` | — | [src](../../../core/runtime/db_composites.py#L86) |
| function | `revoke_composite` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L103) |
| function | `get_composite` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L116) |
| function | `list_composites` | `(*, status=…, limit=…)` | — | [src](../../../core/runtime/db_composites.py#L127) |
| function | `record_invocation` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L146) |
| function | `delete_composite` | `(name)` | — | [src](../../../core/runtime/db_composites.py#L158) |
| function | `count_composites` | `(*, status=…)` | — | [src](../../../core/runtime/db_composites.py#L168) |
| function | `_decode` | `(row)` | — | [src](../../../core/runtime/db_composites.py#L183) |

## `core/runtime/db_concept_baseline.py`
_DB helpers for concept_baseline_stats table._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_concept_baseline_table` | `(conn)` | — | [src](../../../core/runtime/db_concept_baseline.py#L11) |
| function | `upsert_concept_baseline_stat` | `(*, concept, cluster, total_triggers=…, triggers_7d=…, triggers_30d=…, mean_intensity_7d=…, last_triggered_at=…, first_triggered_at=…)` | — | [src](../../../core/runtime/db_concept_baseline.py#L29) |
| function | `increment_concept_baseline_total` | `(*, concept, intensity, triggered_at)` | Increment total_triggers and update last_triggered_at for an existing concept. | [src](../../../core/runtime/db_concept_baseline.py#L74) |
| function | `get_concept_baseline_stat` | `(concept)` | — | [src](../../../core/runtime/db_concept_baseline.py#L99) |
| function | `list_concept_baseline_stats` | `()` | — | [src](../../../core/runtime/db_concept_baseline.py#L110) |
| function | `_row_to_dict` | `(row)` | — | [src](../../../core/runtime/db_concept_baseline.py#L120) |

