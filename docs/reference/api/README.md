# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 14039 functions/methods, 50% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.services.02`](core.services.02.md) — `agreement_streak` … `autonomy_proposal_queue`
- [`core.services.03`](core.services.03.md) — `avoidance_detector` … `central_capture`
- [`core.services.04`](core.services.04.md) — `central_catalog` … `central_keymaker`
- [`core.services.05`](core.services.05.md) — `central_layer_contract` … `central_self_observe`
- [`core.services.06`](core.services.06.md) — `central_self_state` … `chronicle_engine`
- [`core.services.07`](core.services.07.md) — `claim_scanner` … `contract_evolution`
- [`core.services.08`](core.services.08.md) — `contradiction_engine` … `decision_enforcement`
- [`core.services.09`](core.services.09.md) — `decision_evidence` … `dream_bias_engine`
- [`core.services.10`](core.services.10.md) — `dream_carry_over` … `error_healers`
- [`core.services.11`](core.services.11.md) — `event_gate` … `gate_mutation`
- [`core.services.12`](core.services.12.md) — `gate_pattern_learning` … `hollow_promise_guard`
- [`core.services.13`](core.services.13.md) — `hollow_promise_round` … `jobs_engine`
- [`core.services.14`](core.services.14.md) — `kerne_curator` … `memory_hierarchy`
- [`core.services.15`](core.services.15.md) — `memory_maintenance_daemon` … `non_visible_fallback`
- [`core.services.16`](core.services.16.md) — `non_visible_lane_execution` … `plan_proposals`
- [`core.services.17`](core.services.17.md) — `plugin_ruleset` … `prompt_variant_tracker`
- [`core.services.18`](core.services.18.md) — `proposal_classifier` … `release_marker_signal_tracking`
- [`core.services.19`](core.services.19.md) — `remembered_fact_signal_tracking` … `scheduled_tasks`
- [`core.services.20`](core.services.20.md) — `secret_redaction` … `session_milestones`
- [`core.services.21`](core.services.21.md) — `session_persistence_flag` … `spaced_repetition`
- [`core.services.22`](core.services.22.md) — `spatial_entity_ledger` … `tiny_webchat_execution_pilot`
- [`core.services.23`](core.services.23.md) — `tool_catalog` … `verification_gate`
- [`core.services.24`](core.services.24.md) — `verification_gate_telemetry` … `workspace_crypto`
- [`core.services.25`](core.services.25.md) — `workspace_trust` … `world_model_signal_tracking`
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
- [`scripts.01`](scripts.01.md) — `__init__` … `measure_prompt_payload`
- [`scripts.02`](scripts.02.md) — `measure_turn_latency` … `verify_fase_a`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
