# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16667 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `chat_stream_v2`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `chat_workspace_trust` … `notifikations_valg`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `oauth` … `workbench`
- [`apps.api.jarvis_api.schemas`](apps.api.jarvis_api.schemas.md)
- [`apps.central_cli.central_cli`](apps.central_cli.central_cli.md)
- [`apps.desktop`](apps.desktop.md)
- [`apps.voice_agent`](apps.voice_agent.md)
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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_composer_jarvis`
- [`core.runtime.02`](core.runtime.02.md) — `db_composites` … `db_runtime_temporal_memory_signals`
- [`core.runtime.03`](core.runtime.03.md) — `db_scheduled_tasks` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_parking`
- [`core.services.02`](core.services.02.md) — `agent_pool_router` … `apophenia_guard`
- [`core.services.03`](core.services.03.md) — `app_dispatch_store` … `baggrundsjob_vagt`
- [`core.services.04`](core.services.04.md) — `bash_sandbox` … `central_body_map_pulse`
- [`core.services.05`](core.services.05.md) — `central_body_mood_feel` … `central_inner_life_ablation`
- [`core.services.06`](core.services.06.md) — `central_inner_life_digest` … `central_route_headroom`
- [`core.services.07`](core.services.07.md) — `central_router_adapt` … `cheap_lane_health_reconcile`
- [`core.services.08`](core.services.08.md) — `cheap_lane_history` … `companion_presence`
- [`core.services.09`](core.services.09.md) — `compass_engine` … `creative_drift_daemon`
- [`core.services.10`](core.services.10.md) — `creative_impulse_daemon` … `deepseek_modelnavne`
- [`core.services.11`](core.services.11.md) — `delegation_advisor` … `dream_influence_runtime`
- [`core.services.12`](core.services.12.md) — `dream_insight_daemon` … `experience_correction_listener`
- [`core.services.13`](core.services.13.md) — `experience_episodes` … `gate_shadow`
- [`core.services.14`](core.services.14.md) — `gate_skill` … `hentede_vaerktoejer`
- [`core.services.15`](core.services.15.md) — `hf_connector` … `interruption_notice`
- [`core.services.16`](core.services.16.md) — `invocation_record` … `mcp_manager`
- [`core.services.17`](core.services.17.md) — `mcp_registry` … `monitor_streams`
- [`core.services.18`](core.services.18.md) — `mood_dialer` … `override_command`
- [`core.services.19`](core.services.19.md) — `override_store` … `proactive_outbound_substrate`
- [`core.services.20`](core.services.20.md) — `proactive_question_gate_tracking` … `provider_self_heal`
- [`core.services.21`](core.services.21.md) — `published_files` … `research_ledger`
- [`core.services.22`](core.services.22.md) — `research_orchestrator` … `runtime_self_model_boundary`
- [`core.services.23`](core.services.23.md) — `runtime_self_model_builder` … `self_surprise_detection`
- [`core.services.24`](core.services.24.md) — `self_surprise_expectation` … `signal_decay_daemon`
- [`core.services.25`](core.services.25.md) — `signal_delta_trigger` … `subjective_time`
- [`core.services.26`](core.services.26.md) — `suggest_standing_guard` … `tool_hunt_nudge`
- [`core.services.27`](core.services.27.md) — `tool_intent_approval_runtime` … `verification_gate_telemetry`
- [`core.services.28`](core.services.28.md) — `versioneret_json_svar` … `visible_runs_error_messaging`
- [`core.services.29`](core.services.29.md) — `visible_runs_learning_signals` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `identity_pin_tools`
- [`core.tools.02`](core.tools.02.md) — `identity_sketch_tools` … `recurring_scheduler_tools`
- [`core.tools.03`](core.tools.03.md) — `restart_self_tools` … `wake_word_tool`
- [`core.tools.04`](core.tools.04.md) — `web_cache` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `injection_richness_check`
- [`scripts.02`](scripts.02.md) — `install_git_hooks` … `perception_mix`
- [`scripts.03`](scripts.03.md) — `phase5_analyze` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
