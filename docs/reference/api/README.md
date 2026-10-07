# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16387 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_embeddings`
- [`core.runtime.02`](core.runtime.02.md) — `db_emotional_memory` … `db_users`
- [`core.runtime.03`](core.runtime.03.md) — `db_view_requests` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_runtime`
- [`core.services.02`](core.services.02.md) — `agent_runtime_base` … `arc_rule_extractor`
- [`core.services.03`](core.services.03.md) — `assembly_load_probe` … `boundary_awareness`
- [`core.services.04`](core.services.04.md) — `bounded_action_continuity_runtime` … `central_construct`
- [`core.services.05`](core.services.05.md) — `central_continuity_healer` … `central_lexicon`
- [`core.services.06`](core.services.06.md) — `central_llm_egress` … `central_sentinel`
- [`core.services.07`](core.services.07.md) — `central_sequence` … `cheap_provider_catalogue`
- [`core.services.08`](core.services.08.md) — `cheap_provider_reasoning_budget` … `concept_baseline_tracker`
- [`core.services.09`](core.services.09.md) — `config_drift` … `cross_session_threads`
- [`core.services.10`](core.services.10.md) — `cross_signal_analysis` … `development_narrative_daemon`
- [`core.services.11`](core.services.11.md) — `development_ritual` … `egress_guard`
- [`core.services.12`](core.services.12.md) — `egress_routing` … `fabricated_tool_result_gate`
- [`core.services.13`](core.services.13.md) — `fact_gate` … `global_workspace`
- [`core.services.14`](core.services.14.md) — `gmail_connector` … `identity_drift_guard`
- [`core.services.15`](core.services.15.md) — `identity_drift_proposer` … `jobs_engine`
- [`core.services.16`](core.services.16.md) — `kerne_curator` … `memory_emotional_context`
- [`core.services.17`](core.services.17.md) — `memory_graph` … `narrative_summary_daemon`
- [`core.services.18`](core.services.18.md) — `negotiation_engine` … `pattern_counterfactual_daemon`
- [`core.services.19`](core.services.19.md) — `pdf_connector` … `producer_novelty`
- [`core.services.20`](core.services.20.md) — `projection_chat_messages` … `raesonnering_eksperiment`
- [`core.services.21`](core.services.21.md) — `read_before_write_guard` … `retention_coverage`
- [`core.services.22`](core.services.22.md) — `retry_admissibility` … `scheduled_job_windows`
- [`core.services.23`](core.services.23.md) — `scheduled_task_runner` … `semantic_memory`
- [`core.services.24`](core.services.24.md) — `sensory_archive` … `silence_detector`
- [`core.services.25`](core.services.25.md) — `silence_listener` … `telegram_gateway`
- [`core.services.26`](core.services.26.md) — `telemetry_gate` … `tool_round_label`
- [`core.services.27`](core.services.27.md) — `tool_router` … `visible_followup_results`
- [`core.services.28`](core.services.28.md) — `visible_inner_life` … `visible_tool_exec`
- [`core.services.29`](core.services.29.md) — `visible_tool_labels` … `world_model_signal_tracking`
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
