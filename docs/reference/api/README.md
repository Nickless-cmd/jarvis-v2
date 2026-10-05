# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16056 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.services.03`](core.services.03.md) — `autonomous_run_failures` … `central_adaptation`
- [`core.services.04`](core.services.04.md) — `central_affect` … `central_glitch`
- [`core.services.05`](core.services.05.md) — `central_governance` … `central_projection_cache`
- [`core.services.06`](core.services.06.md) — `central_prompt_composer` … `channel_inbound`
- [`core.services.07`](core.services.07.md) — `chat_crypto` … `cognitive_architecture_surface`
- [`core.services.08`](core.services.08.md) — `cognitive_chronicle` … `cost_optimization_daemon`
- [`core.services.09`](core.services.09.md) — `council_deliberation_controller` … `decision_enforcement`
- [`core.services.10`](core.services.10.md) — `decision_evidence` … `dream_action_executor`
- [`core.services.11`](core.services.11.md) — `dream_adoption_candidate_tracking` … `end_of_run_memory_consolidation`
- [`core.services.12`](core.services.12.md) — `endpoint_usage_store` … `gate_auth`
- [`core.services.13`](core.services.13.md) — `gate_commit` … `handover_tools`
- [`core.services.14`](core.services.14.md) — `hardware_body` … `inner_dialectic_engine`
- [`core.services.15`](core.services.15.md) — `inner_visible_support_signal_tracking` … `llm_pricing`
- [`core.services.16`](core.services.16.md) — `local_intent_gate` … `meta_reflection_daemon`
- [`core.services.17`](core.services.17.md) — `metabolism_state_signal_tracking` … `oauth_store`
- [`core.services.18`](core.services.18.md) — `offline_recomposition_engine` … `precision_bias`
- [`core.services.19`](core.services.19.md) — `prepared_request` … `prompt_support_signals`
- [`core.services.20`](core.services.20.md) — `prompt_variant_tracker` … `relation_dynamics`
- [`core.services.21`](core.services.21.md) — `relation_map` … `runtime_cognitive_conductor`
- [`core.services.22`](core.services.22.md) — `runtime_decision_engine` … `self_mutation_lineage`
- [`core.services.23`](core.services.23.md) — `self_narrative_continuity_signal_tracking` … `shadow_ledger_writer`
- [`core.services.24`](core.services.24.md) — `shadow_scan_daemon` … `state_file_retention`
- [`core.services.25`](core.services.25.md) — `state_flag_store` … `tiny_webchat_execution_pilot`
- [`core.services.26`](core.services.26.md) — `tool_batch_notice` … `user_model_daemon`
- [`core.services.27`](core.services.27.md) — `user_scope` … `visible_run_terminal_recovery`
- [`core.services.28`](core.services.28.md) — `visible_run_trace` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `kommando_beskrivelse`
- [`core.tools.02`](core.tools.02.md) — `load_more_tools` … `simple_tools`
- [`core.tools.03`](core.tools.03.md) — `simple_tools_definitions` … `workspace_capabilities_execute`
- [`core.tools.04`](core.tools.04.md) — `workspace_capabilities_memory` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `installer_desk_appimage`
- [`scripts.02`](scripts.02.md) — `interlanguage_analyze` … `phase7_build_probes`
- [`scripts.03`](scripts.03.md) — `phase7_collect` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
