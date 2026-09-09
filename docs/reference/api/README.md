# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 14082 functions/methods, 50% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.services.07`](core.services.07.md) — `claim_scanner` … `continuity_kernel`
- [`core.services.08`](core.services.08.md) — `contract_evolution` … `decision_adherence_gate`
- [`core.services.09`](core.services.09.md) — `decision_enforcement` … `dream_articulation`
- [`core.services.10`](core.services.10.md) — `dream_bias_engine` … `epistemics`
- [`core.services.11`](core.services.11.md) — `error_healers` … `gate_memory`
- [`core.services.12`](core.services.12.md) — `gate_mutation` … `hollow_promise_census`
- [`core.services.13`](core.services.13.md) — `hollow_promise_guard` … `jc_tool_telemetry`
- [`core.services.14`](core.services.14.md) — `jobs_engine` … `memory_graph`
- [`core.services.15`](core.services.15.md) — `memory_hierarchy` … `network_health`
- [`core.services.16`](core.services.16.md) — `non_visible_fallback` … `pfsense_syslog`
- [`core.services.17`](core.services.17.md) — `phone_wake` … `prompt_section_impact`
- [`core.services.18`](core.services.18.md) — `prompt_section_reevaluation` … `relation_state_signal_tracking`
- [`core.services.19`](core.services.19.md) — `relational_warmth` … `runtime_tasks`
- [`core.services.20`](core.services.20.md) — `rupture_repair` … `session_boot_reconciler`
- [`core.services.21`](core.services.21.md) — `session_continuity` … `smith_noise_veto`
- [`core.services.22`](core.services.22.md) — `social_labilizer` … `thought_action_proposal_daemon`
- [`core.services.23`](core.services.23.md) — `thought_leak_guard` … `user_temperature_runtime`
- [`core.services.24`](core.services.24.md) — `user_theory_of_mind` … `voice_anchor`
- [`core.services.25`](core.services.25.md) — `voice_curator` … `world_model_signal_tracking`
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
