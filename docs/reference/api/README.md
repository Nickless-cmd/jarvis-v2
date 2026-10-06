# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16109 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `chat_stream_v2`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `chat_workspace_trust` … `notifikationer`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `notifikations_valg` … `workbench`
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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_governance_ledger`
- [`core.runtime.02`](core.runtime.02.md) — `db_heartbeat` … `ollamafreeapi_provider`
- [`core.runtime.03`](core.runtime.03.md) — `operational_preference_alignment` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agentic_tool_cache`
- [`core.services.02`](core.services.02.md) — `agentic_working_conclusions` … `autonomous_run_digest`
- [`core.services.03`](core.services.03.md) — `autonomous_run_failures` … `central_absorb`
- [`core.services.04`](core.services.04.md) — `central_adaptation` … `central_ghost`
- [`core.services.05`](core.services.05.md) — `central_glitch` … `central_profiles`
- [`core.services.06`](core.services.06.md) — `central_projection_cache` … `central_xproc`
- [`core.services.07`](core.services.07.md) — `channel_inbound` … `code_aesthetic_daemon`
- [`core.services.08`](core.services.08.md) — `cognitive_architecture_surface` … `copilot_catalogue`
- [`core.services.09`](core.services.09.md) — `cost_optimization_daemon` … `decision_adherence_gate`
- [`core.services.10`](core.services.10.md) — `decision_enforcement` … `docs_drift_watchdog`
- [`core.services.11`](core.services.11.md) — `dream_action_executor` … `encryption`
- [`core.services.12`](core.services.12.md) — `end_of_run_memory_consolidation` … `gate_adapters`
- [`core.services.13`](core.services.13.md) — `gate_auth` … `hallucination_guard`
- [`core.services.14`](core.services.14.md) — `handover_tools` … `initiative_queue`
- [`core.services.15`](core.services.15.md) — `inner_dialectic_engine` … `llm_json`
- [`core.services.16`](core.services.16.md) — `llm_pricing` … `meta_learning_retrospective`
- [`core.services.17`](core.services.17.md) — `meta_reflection_daemon` … `oauth_flow`
- [`core.services.18`](core.services.18.md) — `oauth_store` … `post_tool_answer_guard`
- [`core.services.19`](core.services.19.md) — `precision_bias` … `prompt_section_impact`
- [`core.services.20`](core.services.20.md) — `prompt_section_reevaluation` … `regret_engine`
- [`core.services.21`](core.services.21.md) — `regulation_homeostasis_signal_tracking` … `runtime_action_registry`
- [`core.services.22`](core.services.22.md) — `runtime_awareness_signal_tracking` … `self_model_history`
- [`core.services.23`](core.services.23.md) — `self_model_predictive` … `session_wakeup`
- [`core.services.24`](core.services.24.md) — `settlement_shadow` … `spatial_entity_ledger`
- [`core.services.25`](core.services.25.md) — `spild` … `thought_leak_guard`
- [`core.services.26`](core.services.26.md) — `thought_stream_daemon` … `user_activity`
- [`core.services.27`](core.services.27.md) — `user_contradiction_tracker` … `visible_run_recovery_dispatcher`
- [`core.services.28`](core.services.28.md) — `visible_run_segment_exit` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `kaldt_vaerktoej`
- [`core.tools.02`](core.tools.02.md) — `kommando_beskrivelse` … `session_search`
- [`core.tools.03`](core.tools.03.md) — `simple_tools` … `workspace_capabilities_exec`
- [`core.tools.04`](core.tools.04.md) — `workspace_capabilities_execute` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `install_git_hooks`
- [`scripts.02`](scripts.02.md) — `installer_desk_appimage` … `phase6_analyze`
- [`scripts.03`](scripts.03.md) — `phase6_collect` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
