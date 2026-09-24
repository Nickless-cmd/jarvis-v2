# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 15400 functions/methods, 51% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_heartbeat`
- [`core.runtime.02`](core.runtime.02.md) — `db_instrument` … `opmaerksomhed`
- [`core.runtime.03`](core.runtime.03.md) — `plugin_graph` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agentic_tool_cache`
- [`core.services.02`](core.services.02.md) — `agentic_working_conclusions` … `autonomous_run_failures`
- [`core.services.03`](core.services.03.md) — `autonomous_sessions` … `central_agents_surface`
- [`core.services.04`](core.services.04.md) — `central_analyst` … `central_hypothesis_generator`
- [`core.services.05`](core.services.05.md) — `central_hypothesis_governance` … `central_realtime`
- [`core.services.06`](core.services.06.md) — `central_red_dress` … `cheap_lane_dashboard`
- [`core.services.07`](core.services.07.md) — `cheap_lane_diagnostics` … `communication_guard`
- [`core.services.08`](core.services.08.md) — `communication_guard_daemon` … `counterfactual_predictions`
- [`core.services.09`](core.services.09.md) — `counterfactual_self_simulation` … `decision_weight`
- [`core.services.10`](core.services.10.md) — `decisions_journal` … `dream_influence_runtime`
- [`core.services.11`](core.services.11.md) — `dream_insight_daemon` … `experience_correction_listener`
- [`core.services.12`](core.services.12.md) — `experience_episodes` … `gate_truth`
- [`core.services.13`](core.services.13.md) — `gate_verdict_ledger` … `identity_drift_guard`
- [`core.services.14`](core.services.14.md) — `identity_drift_proposer` … `learning_pipeline_orchestrator`
- [`core.services.15`](core.services.15.md) — `learning_policy_engine` … `memory_recall_engine`
- [`core.services.16`](core.services.16.md) — `memory_recall_telemetry` … `non_visible_rate_cap`
- [`core.services.17`](core.services.17.md) — `notes_connector` … `personal_project`
- [`core.services.18`](core.services.18.md) — `personality_drift` … `prompt_evolution`
- [`core.services.19`](core.services.19.md) — `prompt_evolution_runtime` … `recursion_guard`
- [`core.services.20`](core.services.20.md) — `reflection_cycle_daemon` … `runtime_action_outcome_tracking`
- [`core.services.21`](core.services.21.md) — `runtime_action_registry` … `self_model_history`
- [`core.services.22`](core.services.22.md) — `self_model_predictive` … `shadow_experiment_registry`
- [`core.services.23`](core.services.23.md) — `shadow_ledger_writer` … `state_file_retention`
- [`core.services.24`](core.services.24.md) — `state_flag_store` … `tool_calling_evidence`
- [`core.services.25`](core.services.25.md) — `tool_catalog` … `user_theory_of_mind`
- [`core.services.26`](core.services.26.md) — `user_understanding_signal_tracking` … `visible_runs_watchdog`
- [`core.services.27`](core.services.27.md) — `visible_self_state_summary` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `math_tools`
- [`core.tools.02`](core.tools.02.md) — `memory_tools` … `simple_tools_native`
- [`core.tools.03`](core.tools.03.md) — `simple_tools_operator` … `worktree_tools`
- [`core.tools.04`](core.tools.04.md) — `world_model_tools` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `interlanguage_structural_classifier`
- [`scripts.02`](scripts.02.md) — `jarvis` … `signal_noise_cleanup`
- [`scripts.03`](scripts.03.md) — `smoke_test_startup` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
