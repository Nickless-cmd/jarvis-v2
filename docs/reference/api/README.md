# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 13892 functions/methods, 50% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_private_signals`
- [`core.runtime.02`](core.runtime.02.md) — `db_private_states` … `workspace_paths`
- [`core.services.01`](core.services.01.md) — `__init__` … `agents`
- [`core.services.02`](core.services.02.md) — `agreement_streak` … `avoidance_detector`
- [`core.services.03`](core.services.03.md) — `background_resume` … `central_catalog`
- [`core.services.04`](core.services.04.md) — `central_causal_quality` … `central_layer_contract`
- [`core.services.05`](core.services.05.md) — `central_learning` … `central_self_state`
- [`core.services.06`](core.services.06.md) — `central_sentinel` … `claim_scanner`
- [`core.services.07`](core.services.07.md) — `clarification_classifier` … `contradiction_engine`
- [`core.services.08`](core.services.08.md) — `contradiction_resolver` … `decision_evidence`
- [`core.services.09`](core.services.09.md) — `decision_gate` … `dream_carry_over`
- [`core.services.10`](core.services.10.md) — `dream_consolidation_daemon` … `eventbus_central_bridge`
- [`core.services.11`](core.services.11.md) — `events_retention` … `gate_proactivity`
- [`core.services.12`](core.services.12.md) — `gate_review` … `identity_composer`
- [`core.services.13`](core.services.13.md) — `identity_drift_daemon` … `layer_tension_daemon`
- [`core.services.14`](core.services.14.md) — `learning_pipeline_orchestrator` … `memory_resurfacing`
- [`core.services.15`](core.services.15.md) — `memory_search` … `ntfy_gateway`
- [`core.services.16`](core.services.16.md) — `nudge_broend` … `pressure_threshold_gate`
- [`core.services.17`](core.services.17.md) — `priors_feedback` … `provider_self_heal`
- [`core.services.18`](core.services.18.md) — `push_dispatcher` … `rule_definitions`
- [`core.services.19`](core.services.19.md) — `rule_engine` … `self_critique_runtime`
- [`core.services.20`](core.services.20.md) — `self_deception_guard` … `shared_cache`
- [`core.services.21`](core.services.21.md) — `shared_language` … `subagent_digest`
- [`core.services.22`](core.services.22.md) — `subagent_ecology` … `tool_result_aging`
- [`core.services.23`](core.services.23.md) — `tool_result_store` … `visible_model_observe`
- [`core.services.24`](core.services.24.md) — `visible_model_ollama` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `monitor_tools`
- [`core.tools.02`](core.tools.02.md) — `native_tool_gate` … `skill_gate_tool`
- [`core.tools.03`](core.tools.03.md) — `smart_compact_tools` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `measure_turn_latency`
- [`scripts.02`](scripts.02.md) — `memory_md_dedupe_headings` … `verify_fase_a`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
