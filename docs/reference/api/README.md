# Codebase API reference

Generated per-package reference for `core/`+`apps/`+`scripts/`. 16105 functions/methods, 52% with docstrings. Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).

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
- [`core.runtime.01`](core.runtime.01.md) — `__init__` … `db_governance`
- [`core.runtime.02`](core.runtime.02.md) — `db_governance_ledger` … `jarvisx_auth`
- [`core.runtime.03`](core.runtime.03.md) — `ollamafreeapi_provider` … `ws_auth`
- [`core.services.01`](core.services.01.md) — `__init__` … `agent_transcript`
- [`core.services.02`](core.services.02.md) — `agent_wake_intentions` … `autonomous_goals`
- [`core.services.03`](core.services.03.md) — `autonomous_lease` … `candidate_review_digest`
- [`core.services.04`](core.services.04.md) — `candidate_tracking` … `central_exile`
- [`core.services.05`](core.services.05.md) — `central_existence_feel` … `central_output_conservation`
- [`core.services.06`](core.services.06.md) — `central_persephone` … `central_twins`
- [`core.services.07`](core.services.07.md) — `central_valence` … `cluster_daemon_families`
- [`core.services.08`](core.services.08.md) — `cluster_family_scheduler` … `conversation_rhythm`
- [`core.services.09`](core.services.09.md) — `conversation_topics` … `decision_adherence_gate`
- [`core.services.10`](core.services.10.md) — `decision_enforcement` … `docs_drift_watchdog`
- [`core.services.11`](core.services.11.md) — `dream_action_executor` … `encryption`
- [`core.services.12`](core.services.12.md) — `end_of_run_memory_consolidation` … `gate_adapters`
- [`core.services.13`](core.services.13.md) — `gate_auth` … `habits_pipeline`
- [`core.services.14`](core.services.14.md) — `hallucination_guard` … `initiative_accumulator`
- [`core.services.15`](core.services.15.md) — `initiative_queue` … `llm_json`
- [`core.services.16`](core.services.16.md) — `llm_pricing` … `meta_learning_hypotheses`
- [`core.services.17`](core.services.17.md) — `meta_learning_retrospective` … `nudge_broend`
- [`core.services.18`](core.services.18.md) — `oauth_flow` … `policy_abstraction`
- [`core.services.19`](core.services.19.md) — `post_tool_answer_guard` … `prompt_relevance_backend`
- [`core.services.20`](core.services.20.md) — `prompt_section_impact` … `reflective_critic_tracking`
- [`core.services.21`](core.services.21.md) — `regret_engine` … `runtime_action_outcome_tracking`
- [`core.services.22`](core.services.22.md) — `runtime_action_registry` … `self_model_distiller`
- [`core.services.23`](core.services.23.md) — `self_model_history` … `session_view`
- [`core.services.24`](core.services.24.md) — `session_wakeup` … `spaced_repetition`
- [`core.services.25`](core.services.25.md) — `spatial_entity_ledger` … `thought_action_proposal_daemon`
- [`core.services.26`](core.services.26.md) — `thought_leak_guard` … `upload_sandbox`
- [`core.services.27`](core.services.27.md) — `user_activity` … `visible_run_recovery_coordinator`
- [`core.services.28`](core.services.28.md) — `visible_run_recovery_dispatcher` … `workspace_trust`
- [`core.services.29`](core.services.29.md) — `world_facts` … `world_model_signal_tracking`
- [`core.services.decision_triggers`](core.services.decision_triggers.md)
- [`core.services.prompt_sections`](core.services.prompt_sections.md)
- [`core.services.trading`](core.services.trading.md)
- [`core.services.visible_runs_sections`](core.services.visible_runs_sections.md)
- [`core.skills`](core.skills.md)
- [`core.skills.voice`](core.skills.voice.md)
- [`core.tools.01`](core.tools.01.md) — `__init__` … `jc_tool_catalog`
- [`core.tools.02`](core.tools.02.md) — `kaldt_vaerktoej` … `semantic_search_tools`
- [`core.tools.03`](core.tools.03.md) — `sensory_tools` … `workspace_capabilities`
- [`core.tools.04`](core.tools.04.md) — `workspace_capabilities_approval` … `world_model_tools`
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
