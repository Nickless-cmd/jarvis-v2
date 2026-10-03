# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 15863 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.services.03`](core.services.03.md) — `autonomous_sessions` … `central_affect`
- [`core.services.04`](core.services.04.md) — `central_agenda` … `central_governance`
- [`core.services.05`](core.services.05.md) — `central_growth_observe` … `central_prompt_composer`
- [`core.services.06`](core.services.06.md) — `central_prompt_explore` … `chat_crypto`
- [`core.services.07`](core.services.07.md) — `chat_sessions` … `cognitive_core_experiments`
- [`core.services.08`](core.services.08.md) — `cognitive_episodes` … `council_memory_daemon`
- [`core.services.09`](core.services.09.md) — `council_memory_service` … `decision_gate`
- [`core.services.10`](core.services.10.md) — `decision_ghosts` … `dream_bias_engine`
- [`core.services.11`](core.services.11.md) — `dream_carry_over` … `epistemic_pragmatic`
- [`core.services.12`](core.services.12.md) — `epistemic_runtime_state` … `gate_execution`
- [`core.services.13`](core.services.13.md) — `gate_kernel` … `heartbeat_manage_runtime_work`
- [`core.services.14`](core.services.14.md) — `heartbeat_phases` … `internal_cadence_inner_life`
- [`core.services.15`](core.services.15.md) — `internal_cadence_maintenance` … `mail_checker_daemon`
- [`core.services.16`](core.services.16.md) — `malware_scan` … `model_pair_resolver`
- [`core.services.17`](core.services.17.md) — `model_probe` … `outbound_nudges`
- [`core.services.18`](core.services.18.md) — `outcome_learning` … `private_temporal_promotion_signal_tracking`
- [`core.services.19`](core.services.19.md) — `proactive_candidates` … `provider_model_epochs`
- [`core.services.20`](core.services.20.md) — `provider_registry_admin` … `research_contract`
- [`core.services.21`](core.services.21.md) — `research_evidence_collector` … `runtime_self_model_affect`
- [`core.services.22`](core.services.22.md) — `runtime_self_model_boundary` … `self_surprise_detection`
- [`core.services.23`](core.services.23.md) — `self_surprise_expectation` … `signal_delta_trigger`
- [`core.services.24`](core.services.24.md) — `signal_network_visualizer` … `surprise_detector`
- [`core.services.25`](core.services.25.md) — `sustained_attention` … `tool_lexical_match`
- [`core.services.26`](core.services.26.md) — `tool_observer` … `visible_first_pass_pump`
- [`core.services.27`](core.services.27.md) — `visible_first_pass_text` … `visible_stream_gate`
- [`core.services.28`](core.services.28.md) — `visible_terminal_policy` … `world_model_signal_tracking`
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
