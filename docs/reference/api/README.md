# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16486 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `chat_workspace_trust`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `cheap_balancer` … `oauth`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `openai_auth` … `workbench`
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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_core`
- [`core.runtime.02`](core.runtime.02.md) — `db_credit_assignment` … `db_self_repair`
- [`core.runtime.03`](core.runtime.03.md) — `db_sensory` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_pool_router`
- [`core.services.02`](core.services.02.md) — `agent_pool_surface` … `approval_expiry_daemon`
- [`core.services.03`](core.services.03.md) — `approval_feedback_subscriber` … `besked_run_kobling`
- [`core.services.04`](core.services.04.md) — `body_memory` … `central_cadence_conductor`
- [`core.services.05`](core.services.05.md) — `central_capture` … `central_instrument`
- [`core.services.06`](core.services.06.md) — `central_keymaker` … `central_runtime_proxy`
- [`core.services.07`](core.services.07.md) — `central_self_model` … `cheap_lane_route_write`
- [`core.services.08`](core.services.08.md) — `cheap_lane_selfheal` … `composer_suggest`
- [`core.services.09`](core.services.09.md) — `composite_tools` … `creative_projects`
- [`core.services.10`](core.services.10.md) — `crisis_marker_detector` … `desire_daemon`
- [`core.services.11`](core.services.11.md) — `desktop_notifications` … `dreaming_session`
- [`core.services.12`](core.services.12.md) — `drive_arbitration_engine` … `experiential_memory`
- [`core.services.13`](core.services.13.md) — `experiential_runtime_context` … `ghost_networks`
- [`core.services.14`](core.services.14.md) — `git_actions` … `hollow_promise_round`
- [`core.services.15`](core.services.15.md) — `identity_canon` … `jarvis_brain_daemon`
- [`core.services.16`](core.services.16.md) — `jarvis_brain_reflection` … `memory_breathing`
- [`core.services.17`](core.services.17.md) — `memory_consolidation_nudge` … `mortality_awareness`
- [`core.services.18`](core.services.18.md) — `multi_signal_retrieval` … `paradoxes_capture`
- [`core.services.19`](core.services.19.md) — `parallel_selves` … `procedure_bank_pipeline`
- [`core.services.20`](core.services.20.md) — `process_identity` … `query_language_bridge`
- [`core.services.21`](core.services.21.md) — `quota_store` … `research_router`
- [`core.services.22`](core.services.22.md) — `research_store` … `runtime_self_model_surfaces`
- [`core.services.23`](core.services.23.md) — `runtime_surface_cache` … `selfhood_proposal_tracking`
- [`core.services.24`](core.services.24.md) — `selvmodel` … `signal_pressure_accumulator`
- [`core.services.25`](core.services.25.md) — `signal_surface_gc` … `svar_tempo`
- [`core.services.26`](core.services.26.md) — `system_cartographer` … `tool_observer`
- [`core.services.27`](core.services.27.md) — `tool_outcome_memory` … `visible_first_pass_pump`
- [`core.services.28`](core.services.28.md) — `visible_first_pass_text` … `visible_self_state_summary`
- [`core.services.29`](core.services.29.md) — `visible_stream_gate` … `world_model_signal_tracking`
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
