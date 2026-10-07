# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16417 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_dream_bias`
- [`core.runtime.02`](core.runtime.02.md) — `db_embeddings` … `db_user_temperature`
- [`core.runtime.03`](core.runtime.03.md) — `db_users` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_relay`
- [`core.services.02`](core.services.02.md) — `agent_result_inbox` … `approval_runtime`
- [`core.services.03`](core.services.03.md) — `arc_rule_extractor` … `boredom_engine`
- [`core.services.04`](core.services.04.md) — `boundary_awareness` … `central_causal_quality`
- [`core.services.05`](core.services.05.md) — `central_construct` … `central_learning`
- [`core.services.06`](core.services.06.md) — `central_lexicon` … `central_self_state`
- [`core.services.07`](core.services.07.md) — `central_sentinel` … `cheap_provider_breaker_adapters`
- [`core.services.08`](core.services.08.md) — `cheap_provider_catalogue` … `computer_use_samtykke`
- [`core.services.09`](core.services.09.md) — `concept_baseline_tracker` … `cross_session_gate`
- [`core.services.10`](core.services.10.md) — `cross_session_threads` … `development_focus_tracking`
- [`core.services.11`](core.services.11.md) — `development_narrative_daemon` … `effective_policy`
- [`core.services.12`](core.services.12.md) — `egress_guard` … `explore_claim_check`
- [`core.services.13`](core.services.13.md) — `fabricated_tool_result_gate` … `github_connector`
- [`core.services.14`](core.services.14.md) — `global_workspace` … `identity_drift_daemon`
- [`core.services.15`](core.services.15.md) — `identity_drift_guard` … `jarvisx_bridge`
- [`core.services.16`](core.services.16.md) — `jobs_engine` … `memory_density`
- [`core.services.17`](core.services.17.md) — `memory_emotional_context` … `narrative_identity`
- [`core.services.18`](core.services.18.md) — `narrative_summary_daemon` … `paste_store`
- [`core.services.19`](core.services.19.md) — `pattern_counterfactual_daemon` … `process_watcher`
- [`core.services.20`](core.services.20.md) — `producer_novelty` … `r2_5_haandhaevelse`
- [`core.services.21`](core.services.21.md) — `raesonnering_eksperiment` … `retention`
- [`core.services.22`](core.services.22.md) — `retention_coverage` … `rupture_repair`
- [`core.services.23`](core.services.23.md) — `scheduled_job_windows` … `semantic_indexer`
- [`core.services.24`](core.services.24.md) — `semantic_memory` … `signal_tracking_framework`
- [`core.services.25`](core.services.25.md) — `silence_detector` … `taste_profile`
- [`core.services.26`](core.services.26.md) — `telegram_gateway` … `tool_result_store`
- [`core.services.27`](core.services.27.md) — `tool_round_label` … `visible_followup_lean`
- [`core.services.28`](core.services.28.md) — `visible_followup_results` … `visible_thinking_trace`
- [`core.services.29`](core.services.29.md) — `visible_tool_exec` … `world_model_signal_tracking`
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
