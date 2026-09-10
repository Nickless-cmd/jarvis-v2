# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 14297 functions/methods, 50% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `internal_errors`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `internal_runtime_surface` … `totp`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `transcribe` … `workbench`
- [`apps.api.jarvis_api.schemas`](apps.api.jarvis_api.schemas.md)
- [`apps.central_cli.central_cli`](apps.central_cli.central_cli.md)
- [`apps.desktop`](apps.desktop.md)
- [`core.auth`](core.auth.md)
- [`core.browser`](core.browser.md)
- [`core.channels`](core.channels.md)
- [`core.cli`](core.cli.md)
- [`core.coding_lane`](core.coding_lane.md)
- [`core.context`](core.context.md)
- [`core.costing`](core.costing.md)
- [`core.eventbus`](core.eventbus.md)
- [`core.identity`](core.identity.md)
- [`core.memory`](core.memory.md)
- [`core.plugins`](core.plugins.md)
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_private_notes`
- [`core.runtime.02`](core.runtime.02.md) — `db_private_signals` … `state_store`
- [`core.runtime.03`](core.runtime.03.md) — `token_renewal` … `workspace_paths`
- [`core.services.01`](core.services.01.md) — `__init__` … `agentic_working_conclusions`
- [`core.services.02`](core.services.02.md) — `agents` … `autonomous_supervisor`
- [`core.services.03`](core.services.03.md) — `autonomous_work_daemon` … `central_belief_gap`
- [`core.services.04`](core.services.04.md) — `central_body_map_pulse` … `central_injection_units`
- [`core.services.05`](core.services.05.md) — `central_inner_life_ablation` … `central_route_headroom`
- [`core.services.06`](core.services.06.md) — `central_router_adapt` … `cheap_provider_runtime_selection`
- [`core.services.07`](core.services.07.md) — `cheap_provider_runtime_streaming` … `connectors`
- [`core.services.08`](core.services.08.md) — `consent_registry` … `curiosity_daemon`
- [`core.services.09`](core.services.09.md) — `curiosity_hypothesis_debt` … `diary_synthesis_signal_tracking`
- [`core.services.10`](core.services.10.md) — `dictation` … `emotion_concepts_channel_triggers`
- [`core.services.11`](core.services.11.md) — `emotion_concepts_positive_triggers` … `followup_output_budget`
- [`core.services.12`](core.services.12.md) — `forced_tool_choice_probe` … `habit_tracker`
- [`core.services.13`](core.services.13.md) — `habits_pipeline` … `internal_cadence_central_wiring`
- [`core.services.14`](core.services.14.md) — `internal_cadence_core` … `mail_checker_daemon`
- [`core.services.15`](core.services.15.md) — `malware_scan` … `model_probe`
- [`core.services.16`](core.services.16.md) — `model_trust` … `paradox_tracker`
- [`core.services.17`](core.services.17.md) — `paradoxes_capture` … `process_identity`
- [`core.services.18`](core.services.18.md) — `process_supervisor` … `reasoning_prefilter`
- [`core.services.19`](core.services.19.md) — `reasoning_store` … `runtime_action_registry`
- [`core.services.20`](core.services.20.md) — `runtime_awareness_signal_tracking` … `self_model_predictive`
- [`core.services.21`](core.services.21.md) — `self_model_signal_tracking` … `shared_language_extended`
- [`core.services.22`](core.services.22.md) — `shell_confinement_report` … `subagent_digest`
- [`core.services.23`](core.services.23.md) — `subagent_ecology` … `tool_outcome_memory`
- [`core.services.24`](core.services.24.md) — `tool_pattern_miner` … `visible_model`
- [`core.services.25`](core.services.25.md) — `visible_model_adapters` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `mic_listen_tool`
- [`core.tools.02`](core.tools.02.md) — `monitor_tools` … `skill_chain_tool`
- [`core.tools.03`](core.tools.03.md) — `skill_engine_tools` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `measure_prompt_payload`
- [`scripts.02`](scripts.02.md) — `measure_turn_latency` … `verify_fase_a`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
