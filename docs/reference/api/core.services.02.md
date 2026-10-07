# `core.services.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/agent_runtime_surfaces.py`
_Agent runtime — read surfaces (agent + council/swarm projections)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_agent_runtime_surface` | `(limit=…)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L30) |
| function | `enrich_agent_surface` | `(agent)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L62) |
| function | `build_agent_detail_surface` | `(agent_id)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L99) |
| function | `build_council_surface` | `(limit=…)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L106) |
| function | `enrich_council_surface` | `(session)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L130) |
| function | `build_council_detail_surface` | `(council_id)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L143) |
| function | `_progress_label` | `(*, agent, latest_run)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L150) |

## `core/services/agent_sandbox.py`
_bubblewrap-sandbox til en agent-worker (agent-contract-v1 C6b, spec 12.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SandboxUnavailable` | `` | Sandboxen kan ikke etableres - agentens loekke maa ikke koere usandboxet. | [src](../../../core/services/agent_sandbox.py#L27) |
| function | `bwrap_path` | `()` | — | [src](../../../core/services/agent_sandbox.py#L31) |
| function | `python_prefixes` | `()` | — | [src](../../../core/services/agent_sandbox.py#L38) |
| function | `build_bwrap_argv` | `(command, *, pass_fds=…, extra_env=…, worker_files=…, rw_binds=…, chdir=…)` | Byg ``bwrap``-kommandolinjen for ``command`` (som koeres INDE i sandboxen). | [src](../../../core/services/agent_sandbox.py#L46) |
| function | `resource_prefix` | `(*, address_space, cpu_seconds, open_files=…, file_size=…)` | ``prlimit`` foer bwrap: graenserne arves af workeren og kan ikke haeves derinde. | [src](../../../core/services/agent_sandbox.py#L75) |
| function | `spawn_in_sandbox` | `(command, *, pass_fds=…, stdout=…, stderr=…, address_space=…, cpu_seconds=…, extra_env=…, worker_files=…, rw_binds=…, chdir=…, stdin=…, file_size=…)` | Start ``command`` i sandboxen. Egen processgruppe, saa den kan draebes samlet. | [src](../../../core/services/agent_sandbox.py#L87) |
| function | `sandbox_usable` | `()` | Smoketest: kan et trivielt program koere i sandboxen? (ja/nej, grund) | [src](../../../core/services/agent_sandbox.py#L103) |

## `core/services/agent_self_evaluation.py`
_Agent self-evaluation — track quality, adherence, goal progress (READ-ONLY)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_trace_kinds_since` | `(since, until)` | Ikke-strukturelle event-arter skrevet i vinduet. Self-safe: [] ved fejl. | [src](../../../core/services/agent_self_evaluation.py#L76) |
| function | `_previous_eval` | `()` | — | [src](../../../core/services/agent_self_evaluation.py#L97) |
| function | `_score_traces` | `(antal)` | Bredden af spor. Trapper frem for lineær, så små udsving ikke støjer. | [src](../../../core/services/agent_self_evaluation.py#L108) |
| function | `_score_novelty` | `(nu, foer)` | Gav dette slag noget ANDET end det forrige? | [src](../../../core/services/agent_self_evaluation.py#L119) |
| function | `evaluate_tick_quality` | `(*, tick_result)` | Score et slag på hvad det EFTERLOD — ikke på hvilken form det havde. | [src](../../../core/services/agent_self_evaluation.py#L139) |
| function | `tick_quality_summary` | `(*, days=…)` | Aggregate stats over recent evaluations. | [src](../../../core/services/agent_self_evaluation.py#L235) |
| function | `detect_stale_goals` | `(*, stale_days=…)` | Find active goals with no recent progress signal. | [src](../../../core/services/agent_self_evaluation.py#L282) |
| function | `stale_goals_section` | `()` | — | [src](../../../core/services/agent_self_evaluation.py#L305) |
| function | `decision_adherence_summary` | `()` | Compute adherence over ACTIVE behavioral decisions (the curated kind). | [src](../../../core/services/agent_self_evaluation.py#L318) |
| function | `_normalize_decision_directive` | `(value)` | — | [src](../../../core/services/agent_self_evaluation.py#L407) |
| function | `_duplicate_decision_groups` | `(decisions)` | — | [src](../../../core/services/agent_self_evaluation.py#L411) |
| function | `_adherence_recovery_plan` | `(*, score, low_decisions, duplicate_groups, unreviewed)` | — | [src](../../../core/services/agent_self_evaluation.py#L441) |
| function | `self_evaluation_section` | `()` | Compact awareness section combining all trackers. | [src](../../../core/services/agent_self_evaluation.py#L469) |
| function | `_exec_tick_quality_summary` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L546) |
| function | `_exec_detect_stale_goals` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L550) |
| function | `_exec_decision_adherence` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L555) |

## `core/services/agent_skill_distiller.py`
_Agent skill distillation — turns observed outcomes into principles._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gather_recent_outcomes` | `(role, days=…)` | Pull recent runs/outcomes for this role from agent observations. | [src](../../../core/services/agent_skill_distiller.py#L24) |
| function | `_build_distill_prompt` | `(role, outcomes)` | — | [src](../../../core/services/agent_skill_distiller.py#L50) |
| function | `_parse_distillation` | `(text)` | — | [src](../../../core/services/agent_skill_distiller.py#L72) |
| function | `distill_skills_for_role` | `(role, *, days=…)` | Distill recent outcomes for a role into principles. Appends to skills.md. | [src](../../../core/services/agent_skill_distiller.py#L96) |
| function | `distill_all_known_roles` | `(*, days=…)` | — | [src](../../../core/services/agent_skill_distiller.py#L133) |

## `core/services/agent_skill_library.py`
_Agent Skill Library — per-role learned patterns + workflows._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_skills_path` | `(role)` | — | [src](../../../core/services/agent_skill_library.py#L48) |
| function | `_hash` | `(text)` | — | [src](../../../core/services/agent_skill_library.py#L53) |
| function | `get_skills` | `(role)` | Read the skills.md for a role. Returns {role, content, exists, path}. | [src](../../../core/services/agent_skill_library.py#L57) |
| function | `append_skill_observation` | `(*, role, section, observation, proposer=…)` | Append an observation to a section of the role's skills.md. | [src](../../../core/services/agent_skill_library.py#L74) |
| function | `_record_skill_mutation` | `(*, role, path, before, after, reason, proposer)` | — | [src](../../../core/services/agent_skill_library.py#L140) |
| function | `rollback_skill_mutation` | `(mutation_id)` | Restore a skills.md to its before-state from a logged mutation. | [src](../../../core/services/agent_skill_library.py#L180) |
| function | `list_skill_mutations` | `(*, role=…, limit=…)` | — | [src](../../../core/services/agent_skill_library.py#L217) |
| function | `list_known_roles` | `()` | Return all roles that have a skills.md file. | [src](../../../core/services/agent_skill_library.py#L242) |
| function | `_exec_get_agent_skills` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L255) |
| function | `_exec_append_skill` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L259) |
| function | `_exec_rollback_skill_mutation` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L268) |
| function | `_exec_list_skill_mutations` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L272) |
| function | `_exec_list_known_roles` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L282) |

## `core/services/agent_todos.py`
_Per-session todo tracker — Jarvis' working memory for "what am I doing right now"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `effective_status` | `(todo, now_iso)` | Udledt status: 'expired' hvis expires_at er passeret og todo'en ikke er | [src](../../../core/services/agent_todos.py#L38) |
| function | `_load_all` | `()` | — | [src](../../../core/services/agent_todos.py#L49) |
| function | `_save_all` | `(data)` | — | [src](../../../core/services/agent_todos.py#L60) |
| function | `_session_key` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L64) |
| function | `list_todos` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L68) |
| function | `set_todos` | `(session_id, items)` | Replace the entire todo list for this session. | [src](../../../core/services/agent_todos.py#L72) |
| function | `update_todo_status` | `(session_id, todo_id, new_status)` | — | [src](../../../core/services/agent_todos.py#L150) |
| function | `add_todo` | `(session_id, content)` | — | [src](../../../core/services/agent_todos.py#L196) |
| function | `create_from_plan` | `(*, plan_id, session_id, steps)` | Append pending todos for each plan step. Idempotent. | [src](../../../core/services/agent_todos.py#L215) |
| function | `_maybe_dismiss_orphaned_plan` | `(session_id, old_plan_ids, new_todos)` | Dismiss any awaiting_approval plan that no longer has linked todos. | [src](../../../core/services/agent_todos.py#L261) |
| function | `remove_todo` | `(session_id, todo_id)` | — | [src](../../../core/services/agent_todos.py#L307) |
| function | `add_cowork_todo` | `(content)` | Opret en todo i den delte cowork-session (Mission Control UI). | [src](../../../core/services/agent_todos.py#L333) |
| function | `_find_session_for_todo` | `(todo_id)` | — | [src](../../../core/services/agent_todos.py#L338) |
| function | `update_todo_status_anywhere` | `(todo_id, new_status)` | Skift status på en todo uanset hvilken session den lever i (cowork kender | [src](../../../core/services/agent_todos.py#L345) |
| function | `remove_todo_anywhere` | `(todo_id)` | Slet en todo uanset hvilken session den lever i. | [src](../../../core/services/agent_todos.py#L354) |
| function | `set_todo_expiry_anywhere` | `(todo_id, expires_at)` | Sæt/ryd udløbstidspunkt (ISO) på en todo uanset session. None = intet udløb. | [src](../../../core/services/agent_todos.py#L362) |
| function | `clear_session_todos` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L379) |
| function | `todos_prompt_section` | `(session_id)` | Format the active todo list as a prompt block, or None if empty. | [src](../../../core/services/agent_todos.py#L394) |

## `core/services/agent_transcript.py`
_Per-agent JSONL transcript persistence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_agent_dir` | `(agent_id)` | — | [src](../../../core/services/agent_transcript.py#L32) |
| function | `_ensure_dir` | `(agent_id)` | — | [src](../../../core/services/agent_transcript.py#L36) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/agent_transcript.py#L42) |
| function | `write_event` | `(agent_id, entry)` | Append one event-line to the agent's transcript.jsonl. | [src](../../../core/services/agent_transcript.py#L50) |
| function | `write_meta` | `(agent_id, meta)` | Write (or overwrite) the agent's metadata sidecar. | [src](../../../core/services/agent_transcript.py#L67) |
| function | `write_lifecycle` | `(agent_id, event, *, note=…)` | Convenience: write a lifecycle event (spawned/started/completed/failed/...). | [src](../../../core/services/agent_transcript.py#L75) |
| function | `write_prompt` | `(agent_id, prompt, *, run_id=…)` | Write the prompt sent to the model. | [src](../../../core/services/agent_transcript.py#L83) |
| function | `write_result` | `(agent_id, text, *, run_id=…, input_tokens=…, output_tokens=…, cost_usd=…)` | Write the model's result. | [src](../../../core/services/agent_transcript.py#L92) |
| function | `write_tool_call` | `(agent_id, tool_call_id, name, arguments, *, run_id=…)` | Write a tool call the model requested. | [src](../../../core/services/agent_transcript.py#L106) |
| function | `write_tool_result` | `(agent_id, tool_call_id, content, *, run_id=…)` | Write the result of a tool execution. | [src](../../../core/services/agent_transcript.py#L118) |
| function | `write_failure` | `(agent_id, error, *, run_id=…)` | Write a failure/error event. | [src](../../../core/services/agent_transcript.py#L129) |
| function | `load_transcript` | `(agent_id)` | Load ALL lines from transcript.jsonl as a list of dicts. | [src](../../../core/services/agent_transcript.py#L142) |
| function | `load_meta` | `(agent_id)` | Load metadata sidecar, or None if missing. | [src](../../../core/services/agent_transcript.py#L151) |
| function | `load_events_by_kind` | `(agent_id, kind)` | Return only events of a specific kind (e.g. ``"tool_call"``). | [src](../../../core/services/agent_transcript.py#L160) |
| function | `list_transcripts` | `(limit=…)` | List available agent transcripts with metadata, newest-first. | [src](../../../core/services/agent_transcript.py#L169) |
| function | `prune_old_transcripts` | `(max_age_days=…)` | Remove transcript directories older than *max_age_days*. | [src](../../../core/services/agent_transcript.py#L193) |
| function | `write_sidechain` | `(agent_id, role, goal)` | Write a human-readable sidechain.md for quick inspection. | [src](../../../core/services/agent_transcript.py#L215) |
| function | `resume_from_transcript` | `(agent_id)` | Build a prompt-context dict from the transcript for agent resume. | [src](../../../core/services/agent_transcript.py#L240) |
| function | `list_agents` | `(limit=…)` | Seneste agenter med transkript, nyeste foerst. | [src](../../../core/services/agent_transcript.py#L303) |
| function | `read_events` | `(agent_id)` | Alle events for én agent. Tom liste hvis intet transkript. | [src](../../../core/services/agent_transcript.py#L326) |
| function | `summarize` | `(agent_id, *, max_arg_chars=…, max_result_chars=…)` | Hvad gjorde agenten, og hvad kom der ud af det? | [src](../../../core/services/agent_transcript.py#L343) |

## `core/services/agent_wake_intentions.py`
_Varig fortsaettelsesintention for en parent der venter paa agenter (B2, §6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `wake_message` | `(*, condition, assignment_ids)` | Teksten der starter det vaagnede run. Maerket som fra systemet (staaende | [src](../../../core/services/agent_wake_intentions.py#L26) |
| function | `stage_wake` | `(*, task_id, session_id, owner_user_id, message, parent_run_id=…)` | Skriv intentionen. Idempotent paa `task_id`. Findes der allerede en anden | [src](../../../core/services/agent_wake_intentions.py#L39) |
| function | `cancel_pending_wake` | `(task_id, *, reason)` | Aflys en vaekning der endnu IKKE er startet. En allerede claimet (`running`) | [src](../../../core/services/agent_wake_intentions.py#L79) |

## `core/services/agent_worker_main.py`
_Entry for en sandboxet agent-worker (agent-contract-v1 C6b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RpcIO` | `` | LoopIO der sender hvert kald til brokeren og venter paa svaret. | [src](../../../core/services/agent_worker_main.py#L28) |
| method | `RpcIO.__init__` | `(self, sock, reader)` | — | [src](../../../core/services/agent_worker_main.py#L31) |
| method | `RpcIO.call` | `(self, op, **payload)` | — | [src](../../../core/services/agent_worker_main.py#L34) |
| method | `RpcIO.model` | `(self, *, messages, tools, requires_tools, provider, model)` | — | [src](../../../core/services/agent_worker_main.py#L48) |
| method | `RpcIO.tool` | `(self, tc)` | — | [src](../../../core/services/agent_worker_main.py#L53) |
| method | `RpcIO.after_tool` | `(self, tc, tool_out)` | — | [src](../../../core/services/agent_worker_main.py#L63) |
| method | `RpcIO.after_round` | `(self, rounds, tool_calls)` | — | [src](../../../core/services/agent_worker_main.py#L66) |
| function | `_apply_limits` | `(limits)` | Kun stramninger (en soft-graense under den arvede hard-graense); aldrig en haevning. | [src](../../../core/services/agent_worker_main.py#L71) |
| function | `main` | `(argv)` | — | [src](../../../core/services/agent_worker_main.py#L81) |

## `core/services/agent_worker_protocol.py`
_Wire-protokollen mellem serverens broker og en sandboxet agent-worker (C6b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ProtocolError` | `` | Misdannet eller for stor ramme. | [src](../../../core/services/agent_worker_protocol.py#L19) |
| class | `FrameTooLarge` | `` | — | [src](../../../core/services/agent_worker_protocol.py#L23) |
| function | `send` | `(sock, obj)` | — | [src](../../../core/services/agent_worker_protocol.py#L27) |
| class | `FrameReader` | `` | Laeser rammer ét ad gangen. ``read(timeout)`` giver ``None`` ved timeout, hæver ``EOFError`` | [src](../../../core/services/agent_worker_protocol.py#L34) |
| method | `FrameReader.__init__` | `(self, sock)` | — | [src](../../../core/services/agent_worker_protocol.py#L38) |
| method | `FrameReader.read` | `(self, timeout=…)` | — | [src](../../../core/services/agent_worker_protocol.py#L42) |

## `core/services/agent_worker_runner.py`
_Server-siden af en sandboxet agent-worker: spawn, broker og draeb (agent-contract-v1 C6b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `WorkerError` | `` | Workeren fejlede eller blev draebt. ``code`` er stabil. | [src](../../../core/services/agent_worker_runner.py#L50) |
| method | `WorkerError.__init__` | `(self, code, detail=…)` | — | [src](../../../core/services/agent_worker_runner.py#L53) |
| function | `worker_mode_enabled` | `()` | Fail-closed: enhver laesefejl er ``False`` (= den eksisterende in-process-vej). | [src](../../../core/services/agent_worker_runner.py#L58) |
| function | `set_worker_mode` | `(enabled, *, role=…)` | At TAENDE er en ejerbeslutning; at slukke er altid tilladt. | [src](../../../core/services/agent_worker_runner.py#L68) |
| function | `_require_sandbox` | `()` | — | [src](../../../core/services/agent_worker_runner.py#L77) |
| function | `_kill_group` | `(proc)` | — | [src](../../../core/services/agent_worker_runner.py#L87) |
| function | `_safe` | `(obj)` | — | [src](../../../core/services/agent_worker_runner.py#L103) |
| class | `_Broker` | `` | Politik ved sømmen: hvad en worker maa faa serveren til at goere. | [src](../../../core/services/agent_worker_runner.py#L107) |
| method | `_Broker.__init__` | `(self, *, agent, run_id, prompt, tools_payload, provider, model, max_tool_calls, resume=…)` | — | [src](../../../core/services/agent_worker_runner.py#L110) |
| method | `_Broker.handle` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L124) |
| method | `_Broker._model` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L144) |
| method | `_Broker._model_text` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L157) |
| method | `_Broker._tool` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L165) |
| function | `_agent_cancelled` | `(agent_id)` | — | [src](../../../core/services/agent_worker_runner.py#L183) |
| function | `_save_logs` | `(agent, run_id, out_path, err_path)` | — | [src](../../../core/services/agent_worker_runner.py#L192) |
| function | `run_agent_in_worker` | `(*, agent, prompt, requires_tools, run_id, tools_payload=…, timeout_s=…, max_tool_calls=…, address_space=…, worker_files=…, worker_command=…, resume=…)` | Koer agentens tur i en sandboxet worker og returner resultatet i SAMME form som in-process-vejen. | [src](../../../core/services/agent_worker_runner.py#L210) |

## `core/services/agent_worktree_exec.py`
_Skrivning i et agent-worktree - KUN gennem en sandbox (agent-contract-v1 C5b, spec 8.1 og 12.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ExecError` | `` | Kommandoen blev afvist foer den koerte (stabil ``code``). | [src](../../../core/services/agent_worktree_exec.py#L48) |
| method | `ExecError.__init__` | `(self, code, detail=…)` | — | [src](../../../core/services/agent_worktree_exec.py#L51) |
| function | `_active_worktree` | `(worktree_id)` | — | [src](../../../core/services/agent_worktree_exec.py#L56) |
| function | `_clip` | `(data)` | — | [src](../../../core/services/agent_worktree_exec.py#L69) |
| function | `_run` | `(wt, command, *, timeout_s, stdin_bytes=…)` | — | [src](../../../core/services/agent_worktree_exec.py#L74) |
| function | `run_in_worktree` | `(*, worktree_id, command, timeout_s=…)` | Koer en shell-kommando med worktree'et som /work. Kaster ``ExecError`` hvis den afvises. | [src](../../../core/services/agent_worktree_exec.py#L108) |
| function | `write_file_in_worktree` | `(*, worktree_id, path, content)` | Skriv en fil (relativ sti) i worktree'et. Stien loeses INDE i sandboxen og afvises hvis den | [src](../../../core/services/agent_worktree_exec.py#L116) |

## `core/services/agent_worktree_git.py`
_Git-operationer for agent-worktrees (agent-contract-v1 C5a, spec 8.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `GitError` | `` | — | [src](../../../core/services/agent_worktree_git.py#L25) |
| method | `GitError.__init__` | `(self, detail, *, returncode=…)` | — | [src](../../../core/services/agent_worktree_git.py#L26) |
| function | `_env` | `(extra=…)` | — | [src](../../../core/services/agent_worktree_git.py#L31) |
| function | `run_git` | `(args, *, cwd=…, env=…, timeout=…, check=…, input_bytes=…)` | — | [src](../../../core/services/agent_worktree_git.py#L39) |
| function | `safe_ref` | `(ref)` | — | [src](../../../core/services/agent_worktree_git.py#L52) |
| function | `safe_name` | `(name, what=…)` | — | [src](../../../core/services/agent_worktree_git.py#L59) |
| function | `validate_repo` | `(path, allowed_roots)` | Returner repoets toplevel (realpath) hvis det ligger under en tilladt rod og er et almindeligt | [src](../../../core/services/agent_worktree_git.py#L65) |
| function | `resolve_commit` | `(repo, ref=…)` | — | [src](../../../core/services/agent_worktree_git.py#L82) |
| function | `read_gitdir` | `(repo, path)` | Hovedrepoets administrationsmappe for et NYOPRETTET worktree, laest fra dets ``.git``-fil | [src](../../../core/services/agent_worktree_git.py#L87) |
| function | `add_worktree` | `(repo, path, branch, base_commit)` | — | [src](../../../core/services/agent_worktree_git.py#L100) |
| function | `_wt_env` | `(gitdir, path)` | — | [src](../../../core/services/agent_worktree_git.py#L105) |
| function | `stage_all` | `(gitdir, path)` | — | [src](../../../core/services/agent_worktree_git.py#L109) |
| function | `diff_against` | `(gitdir, path, base_commit)` | Hele agentens aendring ift. basen - ogsaa nye og slettede filer og commits (binaer-sikker). | [src](../../../core/services/agent_worktree_git.py#L113) |
| function | `changed_files` | `(gitdir, path, base_commit)` | — | [src](../../../core/services/agent_worktree_git.py#L120) |
| function | `commits_since` | `(gitdir, path, base_commit)` | — | [src](../../../core/services/agent_worktree_git.py#L128) |
| function | `make_bundle` | `(repo, branch, base_commit, dest)` | Bundle af agentens commits (``base..branch``). ``False`` naar der ingen commits er. | [src](../../../core/services/agent_worktree_git.py#L133) |
| function | `remove_worktree` | `(repo, path, branch)` | Fjern worktree + branch. Idempotent: et allerede fjernet worktree er ikke en fejl. | [src](../../../core/services/agent_worktree_git.py#L142) |
| function | `tree_size` | `(path)` | Samlet filstoerrelse (bytes) uden at foelge symlinks ud af traeet. | [src](../../../core/services/agent_worktree_git.py#L151) |
| function | `path_is_inside` | `(path, root)` | — | [src](../../../core/services/agent_worktree_git.py#L163) |
| function | `ensure_dir` | `(path)` | — | [src](../../../core/services/agent_worktree_git.py#L168) |

## `core/services/agent_worktrees.py`
_Worktrees til skrivende kodeagenter (agent-contract-v1 C5a, spec 8.1 og 12.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_worktree_tables` | `(conn)` | — | [src](../../../core/services/agent_worktrees.py#L49) |
| function | `worktree_root` | `()` | — | [src](../../../core/services/agent_worktrees.py#L79) |
| function | `allowed_workspace_roots` | `()` | — | [src](../../../core/services/agent_worktrees.py#L83) |
| function | `_iso` | `(dt)` | — | [src](../../../core/services/agent_worktrees.py#L88) |
| function | `_parse` | `(value)` | — | [src](../../../core/services/agent_worktrees.py#L92) |
| function | `_estimate_bytes` | `(repo, commit)` | — | [src](../../../core/services/agent_worktrees.py#L96) |
| function | `_free_floor` | `(path)` | — | [src](../../../core/services/agent_worktrees.py#L106) |
| function | `_holding_bytes` | `(conn, target)` | — | [src](../../../core/services/agent_worktrees.py#L111) |
| function | `_quota` | `(conn, target)` | Taellingerne paa en GIVEN forbindelse. VIGTIGT: ``connect()`` ruller en aaben transaktion tilbage | [src](../../../core/services/agent_worktrees.py#L117) |
| function | `quota_status` | `(*, target=…)` | — | [src](../../../core/services/agent_worktrees.py#L129) |
| function | `reserve` | `(*, owner_user_id, assignment_id, repo_path, base_ref=…, target=…)` | Reserver plads og en plads i kvoten ATOMISK. Intet er oprettet paa disk endnu. | [src](../../../core/services/agent_worktrees.py#L135) |
| function | `get` | `(*, worktree_id)` | — | [src](../../../core/services/agent_worktrees.py#L185) |
| function | `get_for_assignment` | `(*, owner_user_id, assignment_id)` | — | [src](../../../core/services/agent_worktrees.py#L189) |
| function | `_set` | `(worktree_id, **fields)` | — | [src](../../../core/services/agent_worktrees.py#L194) |
| function | `materialize` | `(*, worktree_id)` | Opret selve git-worktree'et. Alt-eller-intet: ved fejl ryddes det halve, og reservationen frigives. | [src](../../../core/services/agent_worktrees.py#L202) |
| function | `_discard_partial` | `(wt)` | — | [src](../../../core/services/agent_worktrees.py#L224) |
| function | `provision` | `(*, owner_user_id, assignment_id, repo_path, base_ref=…, target=…)` | reserve + materialize som ét skridt; ved fejl er intet efterladt og reservationen frigivet. | [src](../../../core/services/agent_worktrees.py#L232) |
| function | `writes_allowed` | `(*, worktree_id)` | — | [src](../../../core/services/agent_worktrees.py#L242) |
| function | `check_growth` | `(*, worktree_id)` | Maal diskforbruget. Over kvoten (eller for lidt ledig plads) stopper NYE skrivninger og bevarer | [src](../../../core/services/agent_worktrees.py#L247) |
| function | `snapshot_for_assignment` | `(*, assignment_id)` | Ved terminalt udfald: gem diff, aendrede filer og commits som artefakter, og bevar worktree'et | [src](../../../core/services/agent_worktrees.py#L263) |
| function | `decide` | `(*, owner_user_id, worktree_id, decision)` | Registrer ejerens/approverens beslutning om det bevarede arbejde. Selve integrationen i hovedgrenen | [src](../../../core/services/agent_worktrees.py#L307) |
| function | `_verified_remove` | `(wt)` | Fjern et worktree - KUN hvis posten, ejeren og stien hænger sammen. Returnerer om det lykkedes. | [src](../../../core/services/agent_worktrees.py#L322) |
| function | `_archive` | `(wt)` | Pak diff + commits (bundle) i checksumverificerede artefakter foer fysisk oprydning. | [src](../../../core/services/agent_worktrees.py#L343) |
| function | `sweep` | `(*, now=…)` | Retentionrunde. Afgjort + 7 dage -> fjernes. Ubehandlet: opmaerksomhed efter 14 dage, arkiveres | [src](../../../core/services/agent_worktrees.py#L365) |
| function | `reconcile` | `()` | Markér aktive/bevarede poster hvis worktree er forsvundet fra disken som ``unknown`` (ikke 'removed'). | [src](../../../core/services/agent_worktrees.py#L398) |

## `core/services/agentic_checkpoints.py`
_Durable checkpoints for visible agentic loops._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/agentic_checkpoints.py#L21) |
| function | `_load` | `()` | — | [src](../../../core/services/agentic_checkpoints.py#L25) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_checkpoints.py#L32) |
| function | `_tool_name` | `(tool_call)` | — | [src](../../../core/services/agentic_checkpoints.py#L43) |
| function | `_compact_tool_call` | `(tool_call)` | — | [src](../../../core/services/agentic_checkpoints.py#L50) |
| function | `_compact_result` | `(result)` | — | [src](../../../core/services/agentic_checkpoints.py#L60) |
| function | `compact_exchange` | `(exchange)` | — | [src](../../../core/services/agentic_checkpoints.py#L68) |
| function | `save_checkpoint` | `(*, run_id, session_id, user_message, provider, model, round_index, phase, exchanges, partial_text=…, exit_reason=…)` | — | [src](../../../core/services/agentic_checkpoints.py#L78) |
| function | `latest_for_session` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L113) |
| function | `clear_run` | `(run_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L124) |
| function | `clear_session` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L133) |
| function | `checkpoint_prompt_section` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L146) |

## `core/services/agentic_tool_cache.py`
_Small durable cache for read-only agentic tool results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/agentic_tool_cache.py#L31) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_tool_cache.py#L38) |
| function | `_file_fingerprint` | `(arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L45) |
| function | `_signature` | `(tool_name, arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L57) |
| function | `_is_stale` | `(rec)` | True hvis posten er ældre end _MAX_AGE_SECONDS — eller uden brugbart tidsstempel. | [src](../../../core/services/agentic_tool_cache.py#L78) |
| function | `get_cached_result` | `(tool_name, arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L92) |
| function | `store_result` | `(*, tool_name, arguments, result_text, status)` | — | [src](../../../core/services/agentic_tool_cache.py#L106) |

## `core/services/agentic_working_conclusions.py`
_Durable working conclusions for interrupted agentic runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/agentic_working_conclusions.py#L13) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_working_conclusions.py#L20) |
| function | `update_working_conclusion` | `(*, run_id, session_id, user_message, round_index, observation=…, next_step=…)` | — | [src](../../../core/services/agentic_working_conclusions.py#L27) |
| function | `latest_for_session` | `(session_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L55) |
| function | `clear_run` | `(run_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L66) |
| function | `working_conclusion_prompt_section` | `(session_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L73) |
| function | `build_round_observation` | `(*, text, tool_names, result_texts)` | — | [src](../../../core/services/agentic_working_conclusions.py#L90) |

## `core/services/agents.py`
_Agents-cluster — gør multi-agent-systemerne synlige i Den Intelligente Central: agent-pool_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, data)` | — | [src](../../../core/services/agents.py#L15) |
| function | `note_agent_spawn` | `(agent_id, role, *, parent=…, council_id=…, mode=…)` | En agent blev spawnet (pool/swarm). Metadata-only. | [src](../../../core/services/agents.py#L23) |
| function | `note_agent_error` | `(agent_id, error, **data)` | En agent fejlede → observe (synlig). | [src](../../../core/services/agents.py#L33) |
| function | `note_agent_result` | `(agent_id, status, *, tokens_in=…, tokens_out=…, cost_usd=…, duration_ms=…, tool_calls=…, role=…, provider=…, model=…, **data)` | En agent-dispatch afsluttede (succes ELLER fejl) → observe robusthedskonvolut | [src](../../../core/services/agents.py#L39) |
| function | `note_agent_blocked` | `(agent_id, status=…, *, reason=…, role=…, **data)` | En agent blev BLOKERET / mangler kontekst (typet ikke-fejl) → distinkt observe. | [src](../../../core/services/agents.py#L78) |
| function | `note_council` | `(topic, *, rounds=…, deadlocked=…, escalated=…, recruited=…)` | En council-deliberation kørte → observe udfald (rounds/deadlock/witness-escalation/ | [src](../../../core/services/agents.py#L91) |
| function | `agents_summary` | `(*, window=…)` | Read-only: nylig agent/council-aktivitet (til MC). Self-safe. | [src](../../../core/services/agents.py#L102) |
| function | `_build_roster` | `(*, window=…)` | Full agent roster: every unique (provider, model) from the cheap-lane pool as a | [src](../../../core/services/agents.py#L136) |
| function | `_iso` | `(ts)` | Epoch seconds → ISO-8601 UTC string; "" for a missing/zero timestamp. | [src](../../../core/services/agents.py#L221) |

## `core/services/agreement_streak.py`
_Agreement-streak substrate trigger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_opening_is_agreement` | `(text)` | Return the matched phrase if the text opens with agreement, else None. | [src](../../../core/services/agreement_streak.py#L46) |
| function | `detect_agreement_streak` | `(*, lookback=…, threshold=…)` | Pull last N assistant messages, return substrate dict if streak detected. | [src](../../../core/services/agreement_streak.py#L61) |
| function | `build_agreement_streak_section` | `()` | Prompt section — substrate, ikke domm. | [src](../../../core/services/agreement_streak.py#L112) |

## `core/services/alarm_ud.py`
_Én vej ud for driftsalarmer — gennem routeren, ikke direkte til telefonen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `send_alert` | `(*, titel, tekst, slags=…, importance=…, session_id=…)` | Send en driftsalarm gennem routeren. Returnerer True hvis den blev leveret. | [src](../../../core/services/alarm_ud.py#L42) |

## `core/services/ambient_presence.py`
_Ambient presence — Jarvis' egen tilstand, synlig for ham selv._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `emit_ambient_signal` | `(*, kind, detail=…, priority=…)` | Emit a quiet ambient presence signal. Rate-limited to 30 min. | [src](../../../core/services/ambient_presence.py#L63) |
| function | `emit_presence_rhythm` | `()` | Quiet hourly pulse — 'still here'. Separate rate limit from state signals. | [src](../../../core/services/ambient_presence.py#L95) |
| function | `emit_state_shift` | `(from_phase, to_phase)` | Signal a genuine phase transition with a descriptive message. | [src](../../../core/services/ambient_presence.py#L114) |
| function | `maybe_emit_phase_signal` | `(phase)` | Called from heartbeat when life phase is determined. | [src](../../../core/services/ambient_presence.py#L123) |
| function | `emit_insight_signal` | `(insight)` | Called when a dream is confirmed or a value crystallizes. | [src](../../../core/services/ambient_presence.py#L154) |

## `core/services/ambient_sound_daemon.py`
_Ambient Sound daemon — Layer 6½: background acoustic context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_ambient_sound_daemon` | `()` | Sample ambient audio level and classify. Runs 4x/day. | [src](../../../core/services/ambient_sound_daemon.py#L44) |
| function | `_capture_sample` | `(*, save_wav=…)` | Record 10 seconds of audio, classify, optionally save to temp WAV. | [src](../../../core/services/ambient_sound_daemon.py#L117) |
| function | `_save_wav` | `(samples)` | Write float32 mono samples to a temp 16-bit PCM WAV. Returns path or None. | [src](../../../core/services/ambient_sound_daemon.py#L154) |
| function | `_transcribe_sample` | `(wav_path)` | Transcribe a WAV via HF Whisper. Returns empty string on failure. | [src](../../../core/services/ambient_sound_daemon.py#L173) |
| function | `_ambient_transcribe_enabled` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L188) |
| function | `_classify` | `(mean, std, peak=…)` | Classify amplitude stats into acoustic category. No content analysis. | [src](../../../core/services/ambient_sound_daemon.py#L197) |
| function | `_store_sample` | `(sample, now)` | — | [src](../../../core/services/ambient_sound_daemon.py#L225) |
| function | `_archive_sensory` | `(sample, now)` | Mirror every ambient sample into Sansernes Arkiv. Silent on failure. | [src](../../../core/services/ambient_sound_daemon.py#L266) |
| function | `get_latest_ambient_sound_for_prompt` | `()` | Return a nuanced description of recent ambient sound for prompt injection. | [src](../../../core/services/ambient_sound_daemon.py#L298) |
| function | `build_ambient_sound_surface` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L335) |
| function | `_interpret_sound` | `(*, category, amplitude_mean, amplitude_std, now)` | Generate a nuanced Danish description from acoustic metadata via LLM. | [src](../../../core/services/ambient_sound_daemon.py#L372) |
| function | `_experiment_enabled` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L399) |
| function | `count_music_samples_last_hours` | `(hours=…)` | Return (music_count, total_count) for samples in the last `hours` hours. | [src](../../../core/services/ambient_sound_daemon.py#L408) |
| function | `_select_music_influence_phrase` | `(*, ratio)` | 3-tier rotating phrase based on music-to-total ratio. | [src](../../../core/services/ambient_sound_daemon.py#L445) |
| function | `get_music_accumulator_for_prompt` | `()` | Return prompt fragment if music threshold met, else empty string. | [src](../../../core/services/ambient_sound_daemon.py#L457) |
| function | `_state` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L480) |
| function | `_parse_iso` | `(s)` | — | [src](../../../core/services/ambient_sound_daemon.py#L485) |

## `core/services/anthropic_identity.py`
_Build Jarvis identity prefix from a workspace directory._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_signature` | `(workspace_dir)` | — | [src](../../../core/services/anthropic_identity.py#L20) |
| function | `build_identity_prefix` | `(workspace_dir)` | Return concatenated identity files for this workspace, or empty string. | [src](../../../core/services/anthropic_identity.py#L32) |
| function | `invalidate_cache` | `()` | — | [src](../../../core/services/anthropic_identity.py#L62) |

## `core/services/anthropic_sse_emitter.py`
_Anthropic Messages API SSE state machine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AnthropicSSEEmitter` | `` | Stateful emitter for one streamed message. | [src](../../../core/services/anthropic_sse_emitter.py#L13) |
| method | `AnthropicSSEEmitter.__init__` | `(self, *, message_id, model)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L25) |
| method | `AnthropicSSEEmitter._format` | `(event, data)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L35) |
| method | `AnthropicSSEEmitter.begin_message` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L38) |
| method | `AnthropicSSEEmitter._close_open_block` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L56) |
| method | `AnthropicSSEEmitter._open_text_block` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L67) |
| method | `AnthropicSSEEmitter.text_delta` | `(self, text)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L78) |
| method | `AnthropicSSEEmitter.tool_use_start` | `(self, tool_call_id, name)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L90) |
| method | `AnthropicSSEEmitter.tool_use_input_delta` | `(self, partial_json)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L107) |
| method | `AnthropicSSEEmitter.tool_result_block` | `(self, *, tool_use_id, status, content, is_error=…)` | Emit et første-klasses tool_result som content-blok (kanonisk wire-form). | [src](../../../core/services/anthropic_sse_emitter.py#L116) |
| method | `AnthropicSSEEmitter.end_message` | `(self, *, stop_reason, output_tokens=…)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L137) |
| method | `AnthropicSSEEmitter.ping` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L149) |
| method | `AnthropicSSEEmitter.error` | `(self, message)` | Emit a graceful error: close any open block, emit error stop. | [src](../../../core/services/anthropic_sse_emitter.py#L152) |

## `core/services/anthropic_translator.py`
_Translate between Anthropic Messages API format and Ollama /api/chat format._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `translate_request_to_ollama` | `(anthropic_body, *, identity_prefix, backend_model)` | Build an Ollama /api/chat payload from an Anthropic Messages request. | [src](../../../core/services/anthropic_translator.py#L13) |
| function | `_translate_message` | `(msg)` | Translate a single Anthropic message into 1-N Ollama messages. | [src](../../../core/services/anthropic_translator.py#L61) |
| function | `_stringify_tool_result_content` | `(content)` | Anthropic tool_result content can be string or list of blocks. | [src](../../../core/services/anthropic_translator.py#L130) |
| function | `drive_emitter_from_ollama_chunks` | `(emitter, chunks)` | Drive an AnthropicSSEEmitter from a stream of Ollama chat chunks. | [src](../../../core/services/anthropic_translator.py#L153) |
| function | `build_non_streaming_response` | `(*, message_id, model, text, tool_calls)` | Build the final Anthropic Messages response (non-streaming). | [src](../../../core/services/anthropic_translator.py#L200) |

## `core/services/anticipatory_action_daemon.py`
_Anticipatory Action Daemon — predict + pre-act._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L39) |
| function | `_load` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L43) |
| function | `_save` | `(data)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L60) |
| function | `_should_recompute` | `(data, now)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L72) |
| function | `_gather_contact_hours` | `()` | Collect contact hours from recent visible runs. | [src](../../../core/services/anticipatory_action_daemon.py#L83) |
| function | `_compute_peak_hours` | `(hour_counts)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L104) |
| function | `recompute_patterns` | `()` | Rebuild pattern signature from recent data. | [src](../../../core/services/anticipatory_action_daemon.py#L129) |
| function | `_local_now` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L141) |
| function | `_minutes_until_hour` | `(now_local, target_hour)` | Returns minutes until next occurrence of target_hour (always in [0, 1440)). | [src](../../../core/services/anticipatory_action_daemon.py#L146) |
| function | `_maybe_emit_anticipation` | `(peaks)` | Emit signals for peaks coming up within the anticipation window. | [src](../../../core/services/anticipatory_action_daemon.py#L156) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L184) |
| function | `build_anticipatory_action_surface` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L196) |
| function | `_surface_summary` | `(peaks, upcoming)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L223) |
| function | `build_anticipatory_action_prompt_section` | `()` | Surface imminent anticipated contact. | [src](../../../core/services/anticipatory_action_daemon.py#L235) |

## `core/services/anticipatory_context.py`
_Anticipatory Context — predict what the user will likely ask about next._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `predict_next_context` | `(*, recent_topics=…, hour=…, idle_hours=…, last_session_topic=…)` | Predict the most likely next context. | [src](../../../core/services/anticipatory_context.py#L17) |
| function | `build_anticipatory_context_surface` | `()` | — | [src](../../../core/services/anticipatory_context.py#L76) |

## `core/services/api_connection_nerve.py`
_API-forbindelses-nerve — Jarvis mærker hvem/hvad der forbinder til hans API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/api_connection_nerve.py#L41) |
| function | `record` | `(*, ip, method, path, status, latency_ms, user_id=…, session_id=…, error=…)` | Registrér én API-request (metadata-only). Billig, låst, kaster ALDRIG. | [src](../../../core/services/api_connection_nerve.py#L45) |
| function | `_maybe_flush_async` | `()` | Throttlet baggrunds-flush (api-proces ejer bufferen). Spawner en daemon-tråd så request- | [src](../../../core/services/api_connection_nerve.py#L99) |
| function | `_drain` | `()` | Snapshot dirty presence-deltas + log-buffer under lås; nulstil buffer + dirty-flag. | [src](../../../core/services/api_connection_nerve.py#L129) |
| function | `flush` | `()` | Batch-flush presence + log til DB (cadence). Self-safe. | [src](../../../core/services/api_connection_nerve.py#L147) |
| function | `retention_sweep` | `()` | GDPR-retention (cadence): anonymisér IP > 48t → /24, slet gammel log, prune presence. | [src](../../../core/services/api_connection_nerve.py#L158) |
| function | `presence_view` | `(*, active_within_s=…, limit=…)` | Hvem er forbundet til API'et? Fletter live in-memory + persistent DB. Self-safe. | [src](../../../core/services/api_connection_nerve.py#L166) |

## `core/services/apophenia_guard.py`
_Apophenia Guard — pattern skeptic that validates before elevation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_generate_assessment_rationale` | `(*, status, observation_count, adjusted_confidence, competitor_count, confounder_count)` | Generate a brief Danish explanation of the assessment. Falls back to empty string. | [src](../../../core/services/apophenia_guard.py#L21) |
| function | `assess_pattern` | `(*, observation_count, base_confidence, competing_explanations=…, confounders=…, include_rationale=…)` | Assess whether a pattern should be elevated or rejected. | [src](../../../core/services/apophenia_guard.py#L48) |
| function | `build_apophenia_guard_surface` | `()` | — | [src](../../../core/services/apophenia_guard.py#L120) |

## `core/services/app_dispatch_store.py`
_Pending runtime→app instruktioner (spec §18.5, Fase 2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/app_dispatch_store.py#L24) |
| function | `_save` | `(items)` | — | [src](../../../core/services/app_dispatch_store.py#L29) |
| function | `enqueue` | `(instruction)` | Validér + kø en app-instruktion. Returnerer record (med id/created_at) eller | [src](../../../core/services/app_dispatch_store.py#L33) |
| function | `list_pending` | `()` | Uafgjorte instruktioner i kø-rækkefølge (desk poller). | [src](../../../core/services/app_dispatch_store.py#L58) |
| function | `ack` | `(dispatch_id)` | Markér en instruktion som udført (consumeret af desk). | [src](../../../core/services/app_dispatch_store.py#L63) |

## `core/services/approval_bridge_shadow.py`
_Skygge for godkendelses-broen: ville den have sagt det samme?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taellere` | `()` | — | [src](../../../core/services/approval_bridge_shadow.py#L41) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/approval_bridge_shadow.py#L45) |
| function | `taellere_fra_cache` | `()` | Læs tællerne fra en anden proces — se `settlement_shadow` for hvorfor | [src](../../../core/services/approval_bridge_shadow.py#L56) |
| function | `_gem` | `()` | Deltaer, ikke totaler — se `shadow_counters` for hvorfor. | [src](../../../core/services/approval_bridge_shadow.py#L70) |
| function | `live` | `()` | Eksplicit opt-in. Husets `is_enabled` er fail-open og ville tænde en | [src](../../../core/services/approval_bridge_shadow.py#L76) |
| function | `note_requested` | `(approval_id, *, tool_name, arguments, run_id=…, session_id=…)` | Godkendelsen er bedt om. Registrér den i broen — ændrer intet. | [src](../../../core/services/approval_bridge_shadow.py#L87) |
| function | `note_decided` | `(approval_id, *, approved)` | Mennesket har klikket. | [src](../../../core/services/approval_bridge_shadow.py#L105) |
| function | `note_claim` | `(approval_id, *, tool_name, arguments, legacy_allowed)` | Ville broen have tilladt det samme som den kørende kode? | [src](../../../core/services/approval_bridge_shadow.py#L120) |
| function | `note_settled` | `(approval_id, *, ok)` | Luk den post skyggen selv aabnede. | [src](../../../core/services/approval_bridge_shadow.py#L178) |

## `core/services/approval_expiry_daemon.py`
_Fejeren for udløbne godkendelser — den kalder `expire_stale()`._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/approval_expiry_daemon.py#L51) |
| function | `tick_approval_expiry_daemon` | `(now=…)` | Fej udløbne godkendelser hvis kadencen er gået. Selv-sikker. | [src](../../../core/services/approval_expiry_daemon.py#L57) |
| function | `sidste_resultat` | `()` | Hvad fejeren sidst udrettede — så en læser kan se om den kører. | [src](../../../core/services/approval_expiry_daemon.py#L139) |

## `core/services/approval_feedback_subscriber.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_approval_feedback_subscriber` | `()` | — | [src](../../../core/services/approval_feedback_subscriber.py#L19) |
| function | `stop_approval_feedback_subscriber` | `()` | — | [src](../../../core/services/approval_feedback_subscriber.py#L36) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/approval_feedback_subscriber.py#L49) |

## `core/services/approval_outbox.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/approval_outbox.py#L19) |
| function | `ensure_approval_outbox_table` | `(conn)` | — | [src](../../../core/services/approval_outbox.py#L23) |
| function | `enqueue_approval_notification` | `(conn, *, request_id, user_id, envelope)` | — | [src](../../../core/services/approval_outbox.py#L48) |
| function | `pending_approval_notifications` | `(limit=…)` | — | [src](../../../core/services/approval_outbox.py#L68) |
| function | `make_approval_notification_due` | `(request_id)` | — | [src](../../../core/services/approval_outbox.py#L93) |
| function | `dispatch_pending_approval_notifications` | `(*, limit=…, deliver=…)` | — | [src](../../../core/services/approval_outbox.py#L106) |
| function | `_worker` | `()` | — | [src](../../../core/services/approval_outbox.py#L155) |
| function | `start_approval_outbox_dispatcher` | `()` | — | [src](../../../core/services/approval_outbox.py#L164) |

## `core/services/approval_runtime.py`
_Én doer ind og ud af en godkendelse — Fase 4's sidste stykke._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `new_id` | `()` | — | [src](../../../core/services/approval_runtime.py#L41) |
| function | `build_request` | `(*, tool_name, arguments, result, run, created_at=…)` | Byg et gyldigt godkendelses-kort. Det ENE sted formen bor. | [src](../../../core/services/approval_runtime.py#L45) |
| function | `pending_for_session` | `(session_id)` | Det ventende godkendelses-kort for ÉN samtale — eller ``None``. | [src](../../../core/services/approval_runtime.py#L71) |
| function | `pending_for_owner` | `(user_id)` | Det ventende kort for en EJER — uanset hvilken samtale det hører til. | [src](../../../core/services/approval_runtime.py#L104) |
| function | `alle_pending_for_owner` | `(user_id)` | ALLE ventende kort for en EJER — ikke kun det nyeste. | [src](../../../core/services/approval_runtime.py#L137) |
| function | `decide` | `(approval_id, *, approved, answered_by=…)` | Svar paa en godkendelse. Den ENE vej ind for enhver svarer. | [src](../../../core/services/approval_runtime.py#L172) |
| function | `state` | `(approval_id)` | Hvad ved vi om dette kort? None hvis det ikke findes. | [src](../../../core/services/approval_runtime.py#L186) |
| function | `sweep_expired` | `()` | Fjern udloebne kort. Returnerer hvad der blev fejet. | [src](../../../core/services/approval_runtime.py#L208) |

## `core/services/arc_rule_extractor.py`
_Arc rule extractor — turns narrative arcs into actionable rules._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rules_path` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L33) |
| function | `_arcs_dir` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L39) |
| function | `_build_extraction_prompt` | `(arc_text, period)` | — | [src](../../../core/services/arc_rule_extractor.py#L43) |
| function | `_parse_rules` | `(text)` | — | [src](../../../core/services/arc_rule_extractor.py#L59) |
| function | `extract_rules_from_arc` | `(arc_path)` | — | [src](../../../core/services/arc_rule_extractor.py#L74) |
| function | `_mark_processed` | `(arc_path)` | — | [src](../../../core/services/arc_rule_extractor.py#L138) |
| function | `_is_processed` | `(arc_name)` | — | [src](../../../core/services/arc_rule_extractor.py#L151) |
| function | `extract_rules_for_unprocessed_arcs` | `()` | — | [src](../../../core/services/arc_rule_extractor.py#L161) |
| function | `arc_rules_section` | `(*, max_lines=…)` | Retired 2026-09-04 (memory repair, R4): arc rules reach the prompt only | [src](../../../core/services/arc_rule_extractor.py#L180) |
| function | `_legacy_arc_rules_section` | `(*, max_lines=…)` | Pre-2026-09-04 renderer, kept for reference/tests of the file format. | [src](../../../core/services/arc_rule_extractor.py#L188) |

## `core/services/assembly_load_probe.py`
_Hvad lavede maskinen MENS prompten blev samlet?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_proces_cpu_sek` | `()` | Processens samlede CPU-tid (alle tråde) i sekunder. | [src](../../../core/services/assembly_load_probe.py#L60) |
| function | `start` | `()` | Åbn en måling. Returnerer en uigennemsigtig nøgle til `afslut`. | [src](../../../core/services/assembly_load_probe.py#L79) |
| function | `afslut` | `(start_token)` | Luk målingen og returnér felterne som ÉN streng til log-linjen. | [src](../../../core/services/assembly_load_probe.py#L84) |

## `core/services/assembly_prewarm.py`
_core/services/assembly_prewarm.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_max_created_at_real_deepseek` | `()` | Epoch seconds of the most recent NON-warmer deepseek call in costs. None if none. | [src](../../../core/services/assembly_prewarm.py#L36) |
| function | `_seconds_since_last_real_deepseek_call` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L54) |
| function | `_max_created_at_visible` | `()` | Epoch-sek. for seneste ÆGTE bruger↔Jarvis-aktivitet (visible-lanen). None hvis | [src](../../../core/services/assembly_prewarm.py#L59) |
| function | `_seconds_since_last_user_activity` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L76) |
| function | `_idle_window_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L85) |
| function | `is_prewarm_active` | `()` | True hvis den aktuelle tråd i øjeblikket kører en pre-warm-build. Self-safe. | [src](../../../core/services/assembly_prewarm.py#L109) |
| function | `assembly_prewarm_enabled` | `()` | Kill-switch. Default OFF (shadow) — flip via runtime-state. Self-safe → False. | [src](../../../core/services/assembly_prewarm.py#L114) |
| function | `_interval_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L124) |
| function | `_skip_if_recent_s` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L138) |
| function | `_seconds_since_last_prewarm` | `()` | Cross-process: seconds since ANY process last prewarmed. None if never. | [src](../../../core/services/assembly_prewarm.py#L147) |
| function | `_mark_prewarmed` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L157) |
| function | `_should_prewarm` | `()` | Event-drevet gate (15. jul — dræber 292M-tokens/13d-burnet). Warm KUN når det | [src](../../../core/services/assembly_prewarm.py#L165) |
| function | `_try_acquire_prewarm_lease` | `(interval_s)` | Atomisk cross-process: kun ÉN proces vinder retten til at warme pr. interval. | [src](../../../core/services/assembly_prewarm.py#L186) |
| function | `_record_stats` | `(elapsed_s, error=…)` | — | [src](../../../core/services/assembly_prewarm.py#L205) |
| function | `prewarm_once` | `()` | Byg én throwaway-assembly for at varme alle sektions-caches. Returnerer | [src](../../../core/services/assembly_prewarm.py#L220) |
| function | `_loop` | `()` | — | [src](../../../core/services/assembly_prewarm.py#L250) |
| function | `start_prewarm_loop` | `()` | Start baggrunds-pre-warm-loopet én gang pr. proces. Idempotent. Loopet kører | [src](../../../core/services/assembly_prewarm.py#L266) |

## `core/services/associative_recall.py`
_Associative Recall — dormant memories triggered by context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_strong_threshold` | `()` | — | [src](../../../core/services/associative_recall.py#L47) |
| function | `_get_weak_threshold` | `()` | — | [src](../../../core/services/associative_recall.py#L55) |
| function | `_get_max_active` | `()` | — | [src](../../../core/services/associative_recall.py#L63) |
| function | `_get_repetition_multiplier` | `()` | — | [src](../../../core/services/associative_recall.py#L71) |
| function | `_ensure_active_memories_table` | `()` | Create recall_active_memories table if it doesn't exist (lazy init). | [src](../../../core/services/associative_recall.py#L83) |
| function | `_persist_active_memory` | `(memory)` | Save an active memory to DB (upsert). | [src](../../../core/services/associative_recall.py#L108) |
| function | `_remove_persisted_memory` | `(memory_id)` | Remove a memory from the DB persistence table. | [src](../../../core/services/associative_recall.py#L133) |
| function | `_load_active_memories_from_db` | `()` | Restore active memories from DB on module load. | [src](../../../core/services/associative_recall.py#L148) |
| function | `_clear_persisted_memories` | `()` | Remove all active memories from DB. | [src](../../../core/services/associative_recall.py#L177) |
| function | `recall_for_session` | `(session_context)` | Run associative recall at session start. Populates up to 3 active memories. | [src](../../../core/services/associative_recall.py#L196) |
| function | `_observe_assoc_recall` | `(memories)` | Fase 3 (§23.3 #4): meld recall-KVALITET til Centralen — KUN scalar-metadata, aldrig | [src](../../../core/services/associative_recall.py#L252) |
| function | `recall_for_message` | `(message_text, emotional_state)` | Run associative recall for a user message. Adds up to 2 active memories. | [src](../../../core/services/associative_recall.py#L282) |
| function | `build_recall_prompt_section` | `()` | Format active memories as [ASSOCIATIONER] awareness section (Danish, compact). | [src](../../../core/services/associative_recall.py#L369) |
| function | `apply_weak_recall_to_emotions` | `(memories)` | Trigger emotion concepts from weak-scoring memories. | [src](../../../core/services/associative_recall.py#L391) |
| function | `clear_session_recall` | `()` | Reset all active memories and topic history. Call at session end. | [src](../../../core/services/associative_recall.py#L422) |
| function | `_add_to_active` | `(memory)` | Add memory to active set. Evicts weakest if at cap. Persists to DB. | [src](../../../core/services/associative_recall.py#L435) |
| function | `_record_topic` | `(topic)` | Record a topic in the sliding window history. | [src](../../../core/services/associative_recall.py#L449) |
| function | `_get_topic_multiplier` | `(topic)` | Return ×1.5 if topic appears ≥3 times in recent history, else ×1.0. | [src](../../../core/services/associative_recall.py#L454) |
| function | `_extract_keywords_llm` | `(text)` | Extract keywords via cheap-lane LLM. Returns empty list on failure. | [src](../../../core/services/associative_recall.py#L467) |
| function | `_extract_keywords_regex` | `(text)` | Regex fallback: capitalized words, technical terms, named entities. | [src](../../../core/services/associative_recall.py#L492) |
| function | `_extract_topic_hint` | `(text)` | Extract topic hints: LLM first, regex fallback, then simple fallback. | [src](../../../core/services/associative_recall.py#L522) |
| function | `_add_private_brain_candidates` | `(candidates, topic_hint, limit=…)` | Add private brain records as recall candidates. | [src](../../../core/services/associative_recall.py#L565) |
| function | `_add_sensory_candidates` | `(candidates, topic_hint, limit=…)` | Add recent sensory memories as recall candidates. | [src](../../../core/services/associative_recall.py#L597) |
| function | `_build_session_context_text` | `(session_context)` | Build a context description string for session-level scoring. | [src](../../../core/services/associative_recall.py#L629) |
| function | `build_associative_recall_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/associative_recall.py#L641) |
| function | `tick_associative_recall` | `()` | Heartbeat daemon tick — decay + periodic candidate scan. | [src](../../../core/services/associative_recall.py#L664) |

## `core/services/attachment_blocks.py`
_Vedhæftninger som blokke på brugerens besked._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_attachment_blocks` | `(metas)` | Lav content_json-blokke for en brugerbeskeds vedhæftninger. | [src](../../../core/services/attachment_blocks.py#L30) |
| function | `user_message_content_json` | `(metas)` | Serialisér blokkene til det felt `append_chat_message` tager. | [src](../../../core/services/attachment_blocks.py#L59) |
| function | `image_ids_on_message` | `(content_json)` | attachment_id'er for BILLEDER i en besked. Tom liste ved alt andet. | [src](../../../core/services/attachment_blocks.py#L88) |
| function | `image_content_blocks` | `(content_json, *, limit=…)` | `image_url`-blokke klar til prompten. Tom liste hvis intet kan læses. | [src](../../../core/services/attachment_blocks.py#L104) |

