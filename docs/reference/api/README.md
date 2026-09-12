# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 14389 functions/methods, 50% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.runtime.02`](core.runtime.02.md) — `db_private_signals` … `settings`
- [`core.runtime.03`](core.runtime.03.md) — `state_store` … `workspace_paths`
- [`core.services.01`](core.services.01.md) — `__init__` … `agentic_working_conclusions`
- [`core.services.02`](core.services.02.md) — `agents` … `autonomous_stream_run`
- [`core.services.03`](core.services.03.md) — `autonomous_supervisor` … `central_architect`
- [`core.services.04`](core.services.04.md) — `central_belief_gap` … `central_injection_registry`
- [`core.services.05`](core.services.05.md) — `central_injection_units` … `central_route`
- [`core.services.06`](core.services.06.md) — `central_route_headroom` … `cheap_provider_runtime_keys`
- [`core.services.07`](core.services.07.md) — `cheap_provider_runtime_selection` … `connections`
- [`core.services.08`](core.services.08.md) — `connectors` … `curiosity_consolidation`
- [`core.services.09`](core.services.09.md) — `curiosity_daemon` … `diagnosis_gate`
- [`core.services.10`](core.services.10.md) — `diary_synthesis_signal_tracking` … `emotion_concepts`
- [`core.services.11`](core.services.11.md) — `emotion_concepts_channel_triggers` … `followup_observer`
- [`core.services.12`](core.services.12.md) — `followup_output_budget` … `gut_engine`
- [`core.services.13`](core.services.13.md) — `habit_tracker` … `internal_cadence`
- [`core.services.14`](core.services.14.md) — `internal_cadence_central_wiring` … `loyalty_gradient_signal_tracking`
- [`core.services.15`](core.services.15.md) — `mail_checker_daemon` … `model_pair_resolver`
- [`core.services.16`](core.services.16.md) — `model_probe` … `paid_lane_guard`
- [`core.services.17`](core.services.17.md) — `paradox_tracker` … `procedure_bank_pipeline`
- [`core.services.18`](core.services.18.md) — `process_identity` … `reasoning_classifier`
- [`core.services.19`](core.services.19.md) — `reasoning_detectors` … `role_model_resolver`
- [`core.services.20`](core.services.20.md) — `role_registry` … `selective_consolidation_daemon`
- [`core.services.21`](core.services.21.md) — `selective_forgetting_candidate_tracking` … `session_tool_pin`
- [`core.services.22`](core.services.22.md) — `session_topic_tracker` … `spaced_repetition`
- [`core.services.23`](core.services.23.md) — `spatial_entity_ledger` … `tiny_webchat_execution_pilot`
- [`core.services.24`](core.services.24.md) — `tool_calling_evidence` … `valence_trajectory`
- [`core.services.25`](core.services.25.md) — `value_formation` … `voice_daemon`
- [`core.services.26`](core.services.26.md) — `wakeup_dispatcher` … `world_model_signal_tracking`
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
- [`scripts.01`](scripts.01.md) — `__init__` … `ledger_rehearsal`
- [`scripts.02`](scripts.02.md) — `link_google_email` … `verify_fase_a`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
