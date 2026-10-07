# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16203 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \`<pkg>/<mod>.py\``. Each entry links back to the source at `file#Lline`.

## Pages

- [`apps.api.jarvis_api`](apps.api.jarvis_api.md)
- [`apps.api.jarvis_api.middleware`](apps.api.jarvis_api.middleware.md)
- [`apps.api.jarvis_api.routes.01`](apps.api.jarvis_api.routes.01.md) — `__init__` … `cheap_balancer`
- [`apps.api.jarvis_api.routes.02`](apps.api.jarvis_api.routes.02.md) — `cheap_lane_control` … `openai_auth`
- [`apps.api.jarvis_api.routes.03`](apps.api.jarvis_api.routes.03.md) — `openai_compat` … `workbench`
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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_fts`
- [`core.runtime.02`](core.runtime.02.md) — `db_gate_verdicts` … `db_visible`
- [`core.runtime.03`](core.runtime.03.md) — `db_world_self_truth` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_skill_distiller`
- [`core.services.02`](core.services.02.md) — `agent_skill_library` … `auto_improvement_proposer`
- [`core.services.03`](core.services.03.md) — `auto_remember_subscriber` … `cadence_producers`
- [`core.services.04`](core.services.04.md) — `calm_anchor` … `central_echo_breaker`
- [`core.services.05`](core.services.05.md) — `central_error_envelope` … `central_oneiric_loop`
- [`core.services.06`](core.services.06.md) — `central_oneiric_sampler` … `central_trace`
- [`core.services.07`](core.services.07.md) — `central_trainman` … `claim_scanner`
- [`core.services.08`](core.services.08.md) — `clarification_classifier` … `contract_evolution`
- [`core.services.09`](core.services.09.md) — `contradiction_engine` … `day_shape_memory`
- [`core.services.10`](core.services.10.md) — `db_sentinel` … `dispatch_guards`
- [`core.services.11`](core.services.11.md) — `dispatch_status` … `emotional_chords`
- [`core.services.12`](core.services.12.md) — `emotional_controls` … `forgetting_curve`
- [`core.services.13`](core.services.13.md) — `forgetting_engine` … `gut_calibration`
- [`core.services.14`](core.services.14.md) — `gut_engine` … `infra_sense`
- [`core.services.15`](core.services.15.md) — `infra_weather_daemon` … `liveness_registry`
- [`core.services.16`](core.services.16.md) — `living_executive` … `message_feedback`
- [`core.services.17`](core.services.17.md) — `meta_cognition_daemon` … `notifikations_opstart`
- [`core.services.18`](core.services.18.md) — `notifikations_valg` … `plan_proposals`
- [`core.services.19`](core.services.19.md) — `plugin_ruleset` … `prompt_memory_recall`
- [`core.services.20`](core.services.20.md) — `prompt_mutation_loop` … `reflection_cycle_daemon`
- [`core.services.21`](core.services.21.md) — `reflection_signal_tracking` … `run_message_provenance`
- [`core.services.22`](core.services.22.md) — `run_trailing` … `self_experiments`
- [`core.services.23`](core.services.23.md) — `self_history_grounding` … `session_spawn`
- [`core.services.24`](core.services.24.md) — `session_tool_pin` … `somatic_daemon`
- [`core.services.25`](core.services.25.md) — `somatic_runtime_body` … `theory_of_mind`
- [`core.services.26`](core.services.26.md) — `theory_of_mind_engine` … `unconscious_temperature_field`
- [`core.services.27`](core.services.27.md) — `unfinished_intent` … `visible_run_interruption`
- [`core.services.28`](core.services.28.md) — `visible_run_journal` … `widget_dokument`
- [`core.services.29`](core.services.29.md) — `witness_signal_tracking` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `jarvis_brain_tools`
- [`core.tools.02`](core.tools.02.md) — `jc_tool_catalog` … `security_predicates`
- [`core.tools.03`](core.tools.03.md) — `semantic_search_tools` … `webhook_tools`
- [`core.tools.04`](core.tools.04.md) — `widget_tools` … `world_model_tools`
- [`core.tools.agent_dispatch_tool`](core.tools.agent_dispatch_tool.md)
- [`core.tools.claude_dispatch`](core.tools.claude_dispatch.md)
- [`core.undo`](core.undo.md)
- [`core.util`](core.util.md)
- [`scripts.01`](scripts.01.md) — `__init__` … `install_git_hooks`
- [`scripts.02`](scripts.02.md) — `installer_desk_appimage` … `phase5_collect`
- [`scripts.03`](scripts.03.md) — `phase6_analyze` … `verify_vagt_graenser`
- [`scripts.acceptance`](scripts.acceptance.md)
- [`scripts.diagnostics`](scripts.diagnostics.md)
- [`scripts.pipelines`](scripts.pipelines.md)
