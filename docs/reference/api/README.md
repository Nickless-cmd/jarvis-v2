# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16005 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `chat_workspace_trust`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `cheap_balancer` … `notifikations_valg`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `oauth` … `workbench`
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
- [`core.runtime.02`](core.runtime.02.md) — `db_heartbeat` … `ollamafreeapi_provider`
- [`core.runtime.03`](core.runtime.03.md) — `operational_preference_alignment` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agentic_tool_cache`
- [`core.services.02`](core.services.02.md) — `agentic_working_conclusions` … `autonomous_run_failures`
- [`core.services.03`](core.services.03.md) — `autonomous_sessions` … `central_affect`
- [`core.services.04`](core.services.04.md) — `central_agenda` … `central_governance`
- [`core.services.05`](core.services.05.md) — `central_growth_observe` … `central_prompt_composer`
- [`core.services.06`](core.services.06.md) — `central_prompt_explore` … `chat_crypto`
- [`core.services.07`](core.services.07.md) — `chat_sessions` … `cognitive_chronicle`
- [`core.services.08`](core.services.08.md) — `cognitive_core_experiments` … `council_deliberation_controller`
- [`core.services.09`](core.services.09.md) — `council_memory_daemon` … `decision_evidence`
- [`core.services.10`](core.services.10.md) — `decision_gate` … `dream_adoption_candidate_tracking`
- [`core.services.11`](core.services.11.md) — `dream_articulation` … `endpoint_usage_store`
- [`core.services.12`](core.services.12.md) — `env_block` … `gate_enforcement`
- [`core.services.13`](core.services.13.md) — `gate_eval` … `heartbeat_daemon_ticks`
- [`core.services.14`](core.services.14.md) — `heartbeat_delivery` … `inner_voice_notifier`
- [`core.services.15`](core.services.15.md) — `inner_voice_shadow` … `local_tool_broker`
- [`core.services.16`](core.services.16.md) — `long_arc_synthesizer` … `metacognitive_integration`
- [`core.services.17`](core.services.17.md) — `mirror_engine` … `ollama_visible_prompt`
- [`core.services.18`](core.services.18.md) — `open_loop_closure_proposal_tracking` … `priors_feedback`
- [`core.services.19`](core.services.19.md) — `private_initiative_tension_signal_tracking` … `proprioception_metrics`
- [`core.services.20`](core.services.20.md) — `prose_tool_calls` … `relational_warmth`
- [`core.services.21`](core.services.21.md) — `relationship_texture` … `runtime_hooks`
- [`core.services.22`](core.services.22.md) — `runtime_learning_signals` … `self_review_cadence_signal_tracking`
- [`core.services.23`](core.services.23.md) — `self_review_outcome_tracking` … `shared_language_extended`
- [`core.services.24`](core.services.24.md) — `shell_confinement_report` … `stream_settlement`
- [`core.services.25`](core.services.25.md) — `structured_content_flag` … `tool_contract_shadow`
- [`core.services.26`](core.services.26.md) — `tool_dansk_bro` … `valence_trajectory`
- [`core.services.27`](core.services.27.md) — `value_formation` … `visible_runs_error_messaging`
- [`core.services.28`](core.services.28.md) — `visible_runs_learning_signals` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `kommando_beskrivelse`
- [`core.tools.02`](core.tools.02.md) — `load_more_tools` … `simple_tools_definitions`
- [`core.tools.03`](core.tools.03.md) — `simple_tools_enforcement` … `workspace_capabilities_memory`
- [`core.tools.04`](core.tools.04.md) — `workspace_capabilities_results` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `installer_desk_appimage`
- [`scripts.02`](scripts.02.md) — `interlanguage_analyze` … `phase7_collect`
- [`scripts.03`](scripts.03.md) — `phase7_judge` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
