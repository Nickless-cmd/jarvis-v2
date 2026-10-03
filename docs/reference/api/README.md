# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 15828 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `cheap_balancer`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `cheap_lane_control` … `oauth`
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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_governance_ledger`
- [`core.runtime.02`](core.runtime.02.md) — `db_heartbeat` … `operational_preference_alignment`
- [`core.runtime.03`](core.runtime.03.md) — `opmaerksomhed` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agentic_tool_cache`
- [`core.services.02`](core.services.02.md) — `agentic_working_conclusions` … `autonomous_run_failures`
- [`core.services.03`](core.services.03.md) — `autonomous_sessions` … `central_agenda`
- [`core.services.04`](core.services.04.md) — `central_agent_smith` … `central_growth_observe`
- [`core.services.05`](core.services.05.md) — `central_health` … `central_prompt_explore`
- [`core.services.06`](core.services.06.md) — `central_proposal` … `chat_sessions`
- [`core.services.07`](core.services.07.md) — `cheap_lane_admission` … `cognitive_episodes`
- [`core.services.08`](core.services.08.md) — `cognitive_state_assembly` … `council_memory_service`
- [`core.services.09`](core.services.09.md) — `council_receipt` … `decision_ghosts`
- [`core.services.10`](core.services.10.md) — `decision_log` … `dream_carry_over`
- [`core.services.11`](core.services.11.md) — `dream_consolidation_daemon` … `epistemic_runtime_state`
- [`core.services.12`](core.services.12.md) — `epistemics` … `gate_kernel`
- [`core.services.13`](core.services.13.md) — `gate_loop` … `heartbeat_phases`
- [`core.services.14`](core.services.14.md) — `heartbeat_provider_fallback` … `internal_cadence_maintenance`
- [`core.services.15`](core.services.15.md) — `internal_cadence_matrix` … `malware_scan`
- [`core.services.16`](core.services.16.md) — `markdown_structure` … `model_probe`
- [`core.services.17`](core.services.17.md) — `model_trust` … `outcome_learning`
- [`core.services.18`](core.services.18.md) — `outcome_projector` … `proactive_candidates`
- [`core.services.19`](core.services.19.md) — `proactive_context_governor` … `provider_registry_admin`
- [`core.services.20`](core.services.20.md) — `provider_retry_policy` … `research_evidence_collector`
- [`core.services.21`](core.services.21.md) — `research_ledger` … `runtime_self_model_boundary`
- [`core.services.22`](core.services.22.md) — `runtime_self_model_builder` … `self_surprise_expectation`
- [`core.services.23`](core.services.23.md) — `self_system_code_awareness` … `signal_noise_guard`
- [`core.services.24`](core.services.24.md) — `signal_pressure_accumulator` … `system_cartographer`
- [`core.services.25`](core.services.25.md) — `tanke_resume` … `tool_outcome_memory`
- [`core.services.26`](core.services.26.md) — `tool_pattern_miner` … `visible_followup`
- [`core.services.27`](core.services.27.md) — `visible_followup_adapters` … `visible_thinking_trace`
- [`core.services.28`](core.services.28.md) — `visible_tool_exec` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `load_more_tools`
- [`core.tools.02`](core.tools.02.md) — `mail_tools` … `simple_tools_enforcement`
- [`core.tools.03`](core.tools.03.md) — `simple_tools_explore` … `workspace_capabilities_results`
- [`core.tools.04`](core.tools.04.md) — `workspace_capabilities_verdict` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `interlanguage_binary_jarvis_vs_ollama`
- [`scripts.02`](scripts.02.md) — `interlanguage_classifier_final` … `prompt_dump_readable`
- [`scripts.03`](scripts.03.md) — `prompt_dump_split` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
