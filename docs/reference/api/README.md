# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 15617 functions/methods, 51% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.services.03`](core.services.03.md) — `autonomous_sessions` … `central_agent_smith_escalation`
- [`core.services.04`](core.services.04.md) — `central_agents_surface` … `central_hub`
- [`core.services.05`](core.services.05.md) — `central_hypothesis_generator` … `central_rca`
- [`core.services.06`](core.services.06.md) — `central_realtime` … `cheap_lane_control`
- [`core.services.07`](core.services.07.md) — `cheap_lane_dashboard` … `collective_pulse_daemon`
- [`core.services.08`](core.services.08.md) — `commit_attribution` … `council_settlement`
- [`core.services.09`](core.services.09.md) — `counterfactual_engine` … `decision_signal_staging`
- [`core.services.10`](core.services.10.md) — `decision_signal_telemetry` … `dream_hypothesis_generator`
- [`core.services.11`](core.services.11.md) — `dream_hypothesis_judge` … `events_retention`
- [`core.services.12`](core.services.12.md) — `executive_contradiction_signal_tracking` … `gate_proactivity`
- [`core.services.13`](core.services.13.md) — `gate_review` … `hollow_promise_guard`
- [`core.services.14`](core.services.14.md) — `hollow_promise_round` … `jarvisx_bridge`
- [`core.services.15`](core.services.15.md) — `jc_tool_telemetry` … `memory_density`
- [`core.services.16`](core.services.16.md) — `memory_emotional_context` … `narrative_summary_daemon`
- [`core.services.17`](core.services.17.md) — `negotiation_engine` … `pattern_counterfactual_daemon`
- [`core.services.18`](core.services.18.md) — `pdf_connector` … `projection_drift`
- [`core.services.19`](core.services.19.md) — `projection_guard` … `reasoning_prefilter`
- [`core.services.20`](core.services.20.md) — `reasoning_store` … `round_budget_notice`
- [`core.services.21`](core.services.21.md) — `rule_definitions` … `self_authored_prompt_proposal_tracking`
- [`core.services.22`](core.services.22.md) — `self_compassion` … `session_persistence_flag`
- [`core.services.23`](core.services.23.md) — `session_prewarm` … `somatic_daemon`
- [`core.services.24`](core.services.24.md) — `somatic_runtime_body` … `theory_of_mind_engine`
- [`core.services.25`](core.services.25.md) — `thought_action_proposal_daemon` … `user_activity`
- [`core.services.26`](core.services.26.md) — `user_contradiction_tracker` … `visible_runs`
- [`core.services.27`](core.services.27.md) — `visible_runs_approvals` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `mail_tools`
- [`core.tools.02`](core.tools.02.md) — `math_tools` … `simple_tools_explore`
- [`core.tools.03`](core.tools.03.md) — `simple_tools_native` … `workspace_capability_decl`
- [`core.tools.04`](core.tools.04.md) — `worktree_tools` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `interlanguage_drift_classifier`
- [`scripts.02`](scripts.02.md) — `interlanguage_llm_judge` … `rewrite_legacy_memory_provenance`
- [`scripts.03`](scripts.03.md) — `seed_cognitive_state` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
