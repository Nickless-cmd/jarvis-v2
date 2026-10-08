# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16599 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.services.07`](core.services.07.md) — `central_router_adapt` … `cheap_lane_history`
- [`core.services.08`](core.services.08.md) — `cheap_lane_payloads` … `compass_engine`
- [`core.services.09`](core.services.09.md) — `completion_satisfaction` … `creative_impulse_daemon`
- [`core.services.10`](core.services.10.md) — `creative_instinct_daemon` … `delegation_advisor`
- [`core.services.11`](core.services.11.md) — `delete_policy` … `dream_insight_daemon`
- [`core.services.12`](core.services.12.md) — `dream_motif_daemon` … `experience_episodes`
- [`core.services.13`](core.services.13.md) — `experience_substrate` … `gate_skill`
- [`core.services.14`](core.services.14.md) — `gate_truth` … `hf_connector`
- [`core.services.15`](core.services.15.md) — `hollow_promise_census` … `invocation_record`
- [`core.services.16`](core.services.16.md) — `irony_daemon` … `mcp_registry`
- [`core.services.17`](core.services.17.md) — `mcp_trust` … `mood_dialer`
- [`core.services.18`](core.services.18.md) — `mood_oscillator` … `override_store`
- [`core.services.19`](core.services.19.md) — `paid_lane_guard` … `proactive_question_gate_tracking`
- [`core.services.20`](core.services.20.md) — `proactivity_bridge` … `published_files`
- [`core.services.21`](core.services.21.md) — `push_dispatcher` … `research_orchestrator`
- [`core.services.22`](core.services.22.md) — `research_prompt_context` … `runtime_self_model_builder`
- [`core.services.23`](core.services.23.md) — `runtime_self_model_identity` … `self_surprise_expectation`
- [`core.services.24`](core.services.24.md) — `self_system_code_awareness` … `signal_delta_trigger`
- [`core.services.25`](core.services.25.md) — `signal_network_visualizer` … `surprise_daemon`
- [`core.services.26`](core.services.26.md) — `surprise_detector` … `tool_intent_approval_runtime`
- [`core.services.27`](core.services.27.md) — `tool_intent_runtime` … `versioneret_json_svar`
- [`core.services.28`](core.services.28.md) — `veto_gate` … `visible_runs_outcomes`
- [`core.services.29`](core.services.29.md) — `visible_runs_sse_v2` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `identity_sketch_tools`
- [`core.tools.02`](core.tools.02.md) — `inbox_tools` … `restart_self_tools`
- [`core.tools.03`](core.tools.03.md) — `screen_tool` … `web_cache`
- [`core.tools.04`](core.tools.04.md) — `web_scrape_tool` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `install_git_hooks`
- [`scripts.02`](scripts.02.md) — `installer_desk_appimage` … `phase5_collect`
- [`scripts.03`](scripts.03.md) — `phase6_analyze` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
