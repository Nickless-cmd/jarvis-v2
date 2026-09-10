# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 14203 functions/methods, 50% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.runtime.02`](core.runtime.02.md) — `db_private_signals` … `token_renewal`
- [`core.runtime.03`](core.runtime.03.md) — `workspace_paths` … `workspace_paths`
- [`core.services.01`](core.services.01.md) — `__init__` … `agents`
- [`core.services.02`](core.services.02.md) — `agreement_streak` … `autonomous_work_daemon`
- [`core.services.03`](core.services.03.md) — `autonomy_budget` … `central_body_mood_feel`
- [`core.services.04`](core.services.04.md) — `central_brain_link` … `central_inner_life_digest`
- [`core.services.05`](core.services.05.md) — `central_inner_salience` … `central_router_explore`
- [`core.services.06`](core.services.06.md) — `central_runtime_proxy` … `child_authority`
- [`core.services.07`](core.services.07.md) — `child_failure_signal` … `consolidation_judge_daemon`
- [`core.services.08`](core.services.08.md) — `consolidation_target_signal_tracking` … `daemon_manager`
- [`core.services.09`](core.services.09.md) — `daemon_memory_safeguard` … `dispatch_guards`
- [`core.services.10`](core.services.10.md) — `dispatch_status` … `emotional_memory_engine`
- [`core.services.11`](core.services.11.md) — `encryption` … `gate_auth`
- [`core.services.12`](core.services.12.md) — `gate_commit` … `heartbeat_provider_fallback`
- [`core.services.13`](core.services.13.md) — `heartbeat_runtime` … `interruption_notice`
- [`core.services.14`](core.services.14.md) — `invocation_record` … `mcp_registry`
- [`core.services.15`](core.services.15.md) — `mcp_trust` … `mood_regulator_subscriber`
- [`core.services.16`](core.services.16.md) — `mortality_awareness` … `pdf_connector`
- [`core.services.17`](core.services.17.md) — `perceptual_event_engine` … `promise_ledger`
- [`core.services.18`](core.services.18.md) — `prompt_cache_probe` … `reflection_cycle_daemon`
- [`core.services.19`](core.services.19.md) — `reflection_signal_tracking` … `runtime_operational_memory`
- [`core.services.20`](core.services.20.md) — `runtime_resource_signal` … `self_review_signal_tracking`
- [`core.services.21`](core.services.21.md) — `self_review_unified` … `signal_surface_router`
- [`core.services.22`](core.services.22.md) — `signal_tracking_framework` … `temporal_body`
- [`core.services.23`](core.services.23.md) — `temporal_context` … `turn_trace`
- [`core.services.24`](core.services.24.md) — `ui_panel_store` … `visible_runs_cognitive`
- [`core.services.25`](core.services.25.md) — `visible_runs_error_messaging` … `world_model_signal_tracking`
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
