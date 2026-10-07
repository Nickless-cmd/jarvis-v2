# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16309 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_self_evaluation`
- [`core.services.02`](core.services.02.md) — `agent_skill_distiller` … `attention_blink_test`
- [`core.services.03`](core.services.03.md) — `attention_budget` … `bridge_presence`
- [`core.services.04`](core.services.04.md) — `bro_broker` … `central_coverage_action`
- [`core.services.05`](core.services.05.md) — `central_dark_products_digest` … `central_model_meta`
- [`core.services.06`](core.services.06.md) — `central_moltbook` … `central_stance`
- [`core.services.07`](core.services.07.md) — `central_surgery` … `child_authority`
- [`core.services.08`](core.services.08.md) — `child_failure_signal` … `consent_registry`
- [`core.services.09`](core.services.09.md) — `consolidation_judge_daemon` … `current_pull`
- [`core.services.10`](core.services.10.md) — `daemon_health` … `diagnosis_gate`
- [`core.services.11`](core.services.11.md) — `diary_synthesis_signal_tracking` … `emergent_signal_tracking`
- [`core.services.12`](core.services.12.md) — `emitted_prefix` … `finalize_tool_policy`
- [`core.services.13`](core.services.13.md) — `finitude_runtime` … `google_login`
- [`core.services.14`](core.services.14.md) — `governance_bootstrap` … `impulse_executor`
- [`core.services.15`](core.services.15.md) — `in_flight_runs` … `ledger_canary`
- [`core.services.16`](core.services.16.md) — `ledger_recovery` … `memory_recall_telemetry`
- [`core.services.17`](core.services.17.md) — `memory_resurfacing` … `non_visible_rate_cap`
- [`core.services.18`](core.services.18.md) — `notes_connector` … `permission_classifier`
- [`core.services.19`](core.services.19.md) — `permission_engine` … `prompt_assembly_telemetri`
- [`core.services.20`](core.services.20.md) — `prompt_cache_probe` … `reasoning_store`
- [`core.services.21`](core.services.21.md) — `reboot_awareness_daemon` … `rule_definitions`
- [`core.services.22`](core.services.22.md) — `rule_engine` … `selective_attention`
- [`core.services.23`](core.services.23.md) — `selective_consolidation_daemon` … `session_distillation`
- [`core.services.24`](core.services.24.md) — `session_inbox` … `skill_gate_guard`
- [`core.services.25`](core.services.25.md) — `skill_relevance_surface` … `temporal_recurrence_signal_tracking`
- [`core.services.26`](core.services.26.md) — `temporal_rhythm` … `truth_gate_v2`
- [`core.services.27`](core.services.27.md) — `turens_vaerktoejer` … `visible_model_sse`
- [`core.services.28`](core.services.28.md) — `visible_model_types` … `visual_memory`
- [`core.services.29`](core.services.29.md) — `voice_anchor` … `world_model_signal_tracking`
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
