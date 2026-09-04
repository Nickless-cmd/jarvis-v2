# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 13242 functions/methods, 49% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `internal_errors`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `internal_runtime_surface` … `tts`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `users` … `users`
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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_runtime_browser`
- [`core.runtime.02`](core.runtime.02.md) — `db_runtime_chronicle` … `workspace_paths`
- [`core.services.01`](core.services.01.md) — `__init__` … `agreement_streak`
- [`core.services.02`](core.services.02.md) — `ambient_presence` … `body_memory`
- [`core.services.03`](core.services.03.md) — `boredom_curiosity_bridge` … `central_convene_judge`
- [`core.services.04`](core.services.04.md) — `central_core` … `central_loop_lag`
- [`core.services.05`](core.services.05.md) — `central_machines` … `central_shadow`
- [`core.services.06`](core.services.06.md) — `central_signal_health` … `code_aesthetic_daemon`
- [`core.services.07`](core.services.07.md) — `cognitive_architecture_surface` … `council_runtime`
- [`core.services.08`](core.services.08.md) — `counterfactual_engine` … `decision_signals`
- [`core.services.09`](core.services.09.md) — `decision_weight` … `dream_insight_daemon`
- [`core.services.10`](core.services.10.md) — `dream_motif_daemon` … `fabricated_tool_result_gate`
- [`core.services.11`](core.services.11.md) — `fact_gate` … `gratitude_tracker`
- [`core.services.12`](core.services.12.md) — `ground_truth_registry` … `inner_voice_shadow`
- [`core.services.13`](core.services.13.md) — `interlanguage_practice` … `memory_decay_daemon`
- [`core.services.14`](core.services.14.md) — `memory_density` … `network_health`
- [`core.services.15`](core.services.15.md) — `non_visible_fallback` … `precision_bias`
- [`core.services.16`](core.services.16.md) — `pressure_threshold_gate` … `provider_self_heal`
- [`core.services.17`](core.services.17.md) — `push_dispatcher` … `run_follow`
- [`core.services.18`](core.services.18.md) — `runtime_action_executor` … `self_model_predictive`
- [`core.services.19`](core.services.19.md) — `self_model_signal_tracking` … `signal_decay_daemon`
- [`core.services.20`](core.services.20.md) — `signal_delta_trigger` … `telegram_gateway`
- [`core.services.21`](core.services.21.md) — `temperament_tendency_signal_tracking` … `ui_panel_store`
- [`core.services.22`](core.services.22.md) — `unconscious_modulation` … `visible_runs_outcomes`
- [`core.services.23`](core.services.23.md) — `visible_runs_sse_v2` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `notification_tools`
- [`core.tools.02`](core.tools.02.md) — `notify_out_tools` … `tiktok_analytics_tools`
- [`core.tools.03`](core.tools.03.md) — `tiktok_content_tools` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `mint_jarvisx_token`
- [`scripts.02`](scripts.02.md) — `peer_models` … `verify_fase_a`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
