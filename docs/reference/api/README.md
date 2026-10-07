# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16327 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `cheap_balancer`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `cheap_lane_control` … `openai_auth`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `openai_compat` … `workbench`
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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_emotional_memory`
- [`core.runtime.02`](core.runtime.02.md) — `db_fts` … `db_view_requests`
- [`core.runtime.03`](core.runtime.03.md) — `db_visible` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_runtime_spawn`
- [`core.services.02`](core.services.02.md) — `agent_runtime_surfaces` … `attachment_blocks`
- [`core.services.03`](core.services.03.md) — `attachment_service` … `bounded_workspace_write_runtime`
- [`core.services.04`](core.services.04.md) — `brain_edge_worker` … `central_correlate`
- [`core.services.05`](core.services.05.md) — `central_cost_surface` … `central_matrix_ensemble`
- [`core.services.06`](core.services.06.md) — `central_membrane_watch` … `central_signal_health`
- [`core.services.07`](core.services.07.md) — `central_soul_digest` … `cheap_provider_runtime_keys`
- [`core.services.08`](core.services.08.md) — `cheap_provider_runtime_selection` … `conflict_resolution`
- [`core.services.09`](core.services.09.md) — `connections` … `curiosity_consolidation`
- [`core.services.10`](core.services.10.md) — `curiosity_daemon` … `device_pairing`
- [`core.services.11`](core.services.11.md) — `device_presence` … `emergence`
- [`core.services.12`](core.services.12.md) — `emergent_bridge` … `file_awareness_daemon`
- [`core.services.13`](core.services.13.md) — `file_links` … `goal_signal_tracking`
- [`core.services.14`](core.services.14.md) — `good_enough_gate` … `identity_sketch`
- [`core.services.15`](core.services.15.md) — `idle_consolidation` … `layer_tension_daemon`
- [`core.services.16`](core.services.16.md) — `learning_pipeline_orchestrator` … `memory_md_update_proposal_tracking`
- [`core.services.17`](core.services.17.md) — `memory_pruning_daemon` … `network_health`
- [`core.services.18`](core.services.18.md) — `non_visible_fallback` … `perceptual_event_engine`
- [`core.services.19`](core.services.19.md) — `periodic_jobs_scheduler` … `projection_runtime`
- [`core.services.20`](core.services.20.md) — `projection_tool_router` … `reasoning_escalation`
- [`core.services.21`](core.services.21.md) — `reasoning_interceptor` … `role_model_resolver`
- [`core.services.22`](core.services.22.md) — `role_registry` … `secret_redaction`
- [`core.services.23`](core.services.23.md) — `security_guard` … `session_boot_reconciler`
- [`core.services.24`](core.services.24.md) — `session_context_resolve` … `skill_autosurface`
- [`core.services.25`](core.services.25.md) — `skill_contract_registry` … `temporal_context`
- [`core.services.26`](core.services.26.md) — `temporal_depth` … `tool_usage_store`
- [`core.services.27`](core.services.27.md) — `tool_world_change` … `visible_model_observe`
- [`core.services.28`](core.services.28.md) — `visible_model_ollama` … `visible_work_surfaces`
- [`core.services.29`](core.services.29.md) — `vision_backend` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `inbox_tools`
- [`core.tools.02`](core.tools.02.md) — `jarvis_brain_tools` … `screen_tool`
- [`core.tools.03`](core.tools.03.md) — `security_predicates` … `web_scrape_tool`
- [`core.tools.04`](core.tools.04.md) — `webhook_tools` … `world_model_tools`
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
