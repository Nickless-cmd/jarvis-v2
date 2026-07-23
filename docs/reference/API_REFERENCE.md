# API_REFERENCE

> Generated 2026-07-23 from app.routes (live) — 527 routes. Regenerate: `python scripts/api_reference_gen.py`. DO NOT hand-edit.

| Method | Path | Response model | Source |
|---|---|---|---|
| GET | `/account/apps` | dict | account |
| PATCH | `/account/computer-use` | dict | account |
| POST | `/account/erase` | dict | account |
| GET | `/account/export` | dict | account |
| GET | `/account/jarvis` | dict | account |
| POST | `/account/jarvis/visible-model` | dict | account |
| PATCH | `/account/language` | dict | account |
| GET | `/account/mcp` | dict | account |
| POST | `/account/mcp` | dict | account |
| DELETE | `/account/mcp/{server_id}` | dict | account |
| GET | `/account/me` | dict | account |
| GET | `/account/memory` | dict | account |
| GET | `/account/memory/search` | dict | account |
| GET | `/account/permissions` | dict | account |
| GET | `/account/quota` | dict | account |
| GET | `/account/workspace` | dict | account |
| POST | `/anthropic/v1/messages` |  | anthropic_compat |
| GET | `/anthropic/v1/models` |  | anthropic_compat |
| GET | `/api/auth/google/link/start` |  | auth |
| GET | `/api/auth/google/result` |  | auth |
| GET | `/api/auth/google/start` |  | auth |
| POST | `/api/auth/issue` | dict | jarvisx_authtokens |
| POST | `/api/auth/login` |  | auth |
| POST | `/api/auth/pair/create` |  | auth |
| POST | `/api/auth/pair/redeem` |  | auth |
| GET | `/api/auth/pair/status` |  | auth |
| POST | `/api/auth/refresh` | dict | jarvisx_authtokens |
| POST | `/api/auth/register` |  | auth |
| GET | `/api/auth/verify-email` |  | auth |
| GET | `/api/auth/whoami-token` | dict | jarvisx_authtokens |
| GET | `/api/channels/state` | dict | jarvisx_channels |
| GET | `/api/chat/search` | dict | jarvisx_sessions |
| POST | `/api/chronicle` | dict | jarvisx_workspace |
| GET | `/api/connectors` |  | connectors |
| DELETE | `/api/connectors/{connector_id}` |  | connectors |
| POST | `/api/connectors/{connector_id}/enabled` |  | connectors |
| GET | `/api/dispatches` | dict | jarvisx_dispatches |
| GET | `/api/dispatches/budget` | dict | jarvisx_dispatches |
| GET | `/api/dispatches/{task_id}` | dict | jarvisx_dispatches |
| GET | `/api/dispatches/{task_id}/diff` | dict | jarvisx_dispatches |
| POST | `/api/identity-pins` | dict | jarvisx_workspace |
| DELETE | `/api/identity-pins/{pin_id}` | dict | jarvisx_workspace |
| POST | `/api/internal/discord/dispatch` | dict | internal_discord |
| POST | `/api/internal/errors/report` |  | internal_errors |
| POST | `/api/internal/jarvisx-bridge/dispatch` |  | jarvisx_bridge |
| GET | `/api/internal/runtime-surface/{name}` | dict | internal_runtime_surface |
| GET | `/api/mind/snapshot` | dict | jarvisx_workspace |
| GET | `/api/oauth/{provider}/callback` |  | oauth |
| GET | `/api/oauth/{provider}/start` |  | oauth |
| POST | `/api/operator/wakeup-fired` | dict | jarvisx_processes |
| GET | `/api/plans` | dict | jarvisx_sessions |
| POST | `/api/plans/{plan_id}/approve` | dict | jarvisx_sessions |
| POST | `/api/plans/{plan_id}/dismiss` | dict | jarvisx_sessions |
| GET | `/api/preferences` | dict | jarvisx_sessions |
| POST | `/api/preferences` | dict | jarvisx_sessions |
| GET | `/api/processes` | dict | jarvisx_processes |
| POST | `/api/processes` | dict | jarvisx_processes |
| DELETE | `/api/processes/{name}` | dict | jarvisx_processes |
| GET | `/api/processes/{name}/log` | dict | jarvisx_processes |
| POST | `/api/processes/{name}/stop` | dict | jarvisx_processes |
| GET | `/api/project/list` | dict | jarvisx_project |
| GET | `/api/project/notes` | dict | jarvisx_project |
| POST | `/api/project/notes` | dict | jarvisx_project |
| GET | `/api/project/read` | dict | jarvisx_project |
| GET | `/api/project/tree` | dict | jarvisx_project |
| POST | `/api/project/watch/add` | dict | jarvisx_project |
| POST | `/api/project/watch/clear` | dict | jarvisx_project |
| POST | `/api/project/watch/poll` | dict | jarvisx_project |
| GET | `/api/scheduling/state` | dict | jarvisx_channels |
| GET | `/api/sensory` | dict | sensory |
| POST | `/api/sensory` | dict | sensory |
| GET | `/api/sensory/search` | dict | sensory |
| GET | `/api/sensory/summary` | dict | sensory |
| GET | `/api/sensory/{memory_id}` | dict | sensory |
| POST | `/api/sessions/fork` | dict | jarvisx_sessions |
| GET | `/api/staged-edits` | dict | jarvisx_sessions |
| POST | `/api/staged-edits/commit` | dict | jarvisx_sessions |
| POST | `/api/staged-edits/discard` | dict | jarvisx_sessions |
| GET | `/api/todos` | dict | jarvisx_sessions |
| POST | `/api/todos/status` | dict | jarvisx_sessions |
| GET | `/api/tool-result/{result_id}` | dict | jarvisx_sessions |
| GET | `/api/tools/inventory` | dict | jarvisx_sessions |
| GET | `/api/trading/state` | dict | jarvisx_processes |
| POST | `/api/tts/synthesize` |  | tts |
| GET | `/api/tts/voices` | dict | tts |
| GET | `/api/users` |  | users |
| DELETE | `/api/users/{user_id}` |  | users |
| GET | `/api/users/{user_id}` |  | users |
| PATCH | `/api/users/{user_id}` |  | users |
| GET | `/api/whoami` | dict | jarvisx_workspace |
| GET | `/api/workspace/list` | dict | jarvisx_workspace |
| GET | `/api/workspace/read` | dict | jarvisx_workspace |
| GET | `/api/workspace/tree` | dict | jarvisx_workspace |
| GET | `/attachments/image/{attachment_id}` |  | attachments |
| GET | `/attachments/images` | dict | attachments |
| POST | `/attachments/upload` | dict | attachments |
| GET | `/attachments/{attachment_id}` |  | attachments |
| GET | `/auth/openai/callback/{profile}` |  | openai_auth |
| GET | `/auth/openai/launch` |  | openai_auth |
| POST | `/auth/totp/revoke` | dict | totp |
| POST | `/auth/totp/setup` | dict | totp |
| GET | `/auth/totp/status` | dict | totp |
| POST | `/billing/checkout` | dict | billing |
| GET | `/billing/status` | dict | billing |
| POST | `/billing/webhook` | dict | billing |
| GET | `/central/affect` | dict | central_affect |
| GET | `/central/agent-smith` | dict | central_agent_smith |
| GET | `/central/agents` | dict | central |
| GET | `/central/agents` | dict | central_absorb_routes |
| POST | `/central/agents/{agent_id}/cancel` | dict | central |
| POST | `/central/agents/{agent_id}/pause` | dict | central |
| GET | `/central/analyst` | dict | central_matrix |
| GET | `/central/architect` | dict | central_matrix |
| GET | `/central/attention` | dict | central_absorb_routes |
| GET | `/central/autonomous` | dict | central_autonomous |
| GET | `/central/autonomy` | dict | central_absorb_routes |
| GET | `/central/belief-gap` | dict | central_matrix |
| GET | `/central/body` | dict | central_affect |
| POST | `/central/breakers/{nerve:path}/reset` | dict | central_breakers |
| POST | `/central/command` | dict | central |
| GET | `/central/connections` | dict | central_connections |
| GET | `/central/construct` | dict | central_matrix |
| GET | `/central/continuity` | dict | central_matrix |
| GET | `/central/cost` | dict | central |
| GET | `/central/costs-daily` | dict | central_absorb_routes |
| GET | `/central/council` | dict | central |
| GET | `/central/council` | dict | central_absorb_routes |
| GET | `/central/dark-products` | dict | central_absorb_routes |
| GET | `/central/decentralization` | dict | central_decentralization |
| GET | `/central/dejavu` | dict | central_matrix |
| GET | `/central/diagnostics` | dict | central |
| GET | `/central/dissent` | dict | central_matrix |
| GET | `/central/docs-drift` | dict | central_docs_drift |
| GET | `/central/dream-action` | dict | central_matrix |
| GET | `/central/echo-breaker` | dict | central_matrix |
| GET | `/central/events` | dict | central_absorb_routes |
| GET | `/central/excess` | dict | central_excess |
| GET | `/central/execution` | dict | central_absorb_routes |
| GET | `/central/exile` | dict | central_matrix |
| POST | `/central/exile/exchange` | dict | central_matrix |
| GET | `/central/experiments` | dict | central_absorb_routes |
| GET | `/central/feel` | dict | central_feel |
| GET | `/central/ghost` | dict | central_matrix |
| GET | `/central/glitch` | dict | central_matrix |
| GET | `/central/governance` | dict | central_governance |
| POST | `/central/governance/set` | dict | central_governance |
| GET | `/central/healers` | dict | central_healers |
| POST | `/central/healers/flag` | dict | central_healers |
| GET | `/central/identity-canon` | dict | central_matrix |
| GET | `/central/initiative` | dict | central_absorb_routes |
| GET | `/central/inner-life` | dict | central_self |
| GET | `/central/integrity` | dict | central_absorb_routes |
| GET | `/central/keys` | dict | central_keys |
| POST | `/central/keys/{key_id}/approve` | dict | central_keys |
| GET | `/central/machines` | dict | central_matrix |
| GET | `/central/memory-health` | dict | central_absorb_routes |
| GET | `/central/merovingian` | dict | central_matrix |
| POST | `/central/merovingian/{hyp_id}/explain` | dict | central_matrix |
| GET | `/central/mind` | dict | central |
| GET | `/central/model-trust` | dict | central_matrix |
| GET | `/central/moltbook` | dict | central_moltbook |
| GET | `/central/mourning` | dict | central_matrix |
| GET | `/central/nerve/{nerve}` | dict | central |
| POST | `/central/nerve/{nerve}/toggle` | dict | central |
| GET | `/central/oracle` | dict | central_matrix |
| GET | `/central/permission-classifier` | dict | central_matrix |
| GET | `/central/persephone` | dict | central_matrix |
| GET | `/central/proactivity` | dict | central_proactivity |
| GET | `/central/providers` | dict | central |
| GET | `/central/queues/scheduled` | dict | central_absorb_routes |
| GET | `/central/rca` | dict | central_matrix |
| GET | `/central/realtime` | dict | central |
| GET | `/central/reasoning-interceptor` | dict | central_matrix |
| GET | `/central/red-dress` | dict | central_matrix |
| GET | `/central/redpill` | dict | central_matrix |
| GET | `/central/relational` | dict | central_matrix |
| GET | `/central/runs` | dict | central_absorb_routes |
| GET | `/central/runs/{run_id}` | dict | central_absorb_routes |
| GET | `/central/self` | dict | central_self |
| GET | `/central/sentinel` | dict | central_matrix |
| POST | `/central/sentinel/{attack_id}/defend` | dict | central_matrix |
| GET | `/central/seraph` | dict | central_matrix |
| GET | `/central/shadow-review` | dict | central |
| GET | `/central/skills` | dict | central_absorb_routes |
| GET | `/central/soul` | dict | central_absorb_routes |
| GET | `/central/stream` |  | central |
| GET | `/central/surgery` | dict | central_matrix |
| POST | `/central/surgery/propose` | dict | central_matrix |
| POST | `/central/surgery/rollback/{snapshot_id}` | dict | central_matrix |
| POST | `/central/surgery/{pid}/{step}` | dict | central_matrix |
| GET | `/central/timeseries` | dict | central |
| GET | `/central/tone` | dict | central_absorb_routes |
| GET | `/central/trainman` | dict | central_matrix |
| GET | `/central/twins` | dict | central_matrix |
| GET | `/central/users` | dict | central_users |
| GET | `/central/white-rabbit` | dict | central_matrix |
| GET | `/chat/active-file` | dict | chat |
| GET | `/chat/active-runs` | dict | chat |
| POST | `/chat/approvals/{approval_id}/approve` | dict | chat |
| POST | `/chat/approvals/{approval_id}/deny` | dict | chat |
| POST | `/chat/compact-now` | dict | chat |
| GET | `/chat/context-info` | dict | chat |
| GET | `/chat/context-usage` | dict | chat |
| GET | `/chat/file` | dict | chat |
| POST | `/chat/file` | dict | chat |
| POST | `/chat/file/commit` | dict | chat |
| POST | `/chat/file/commit-message` | dict | chat |
| GET | `/chat/git-status` | dict | chat |
| POST | `/chat/git/commit-all` | dict | chat |
| POST | `/chat/git/create-pr` | dict | chat |
| GET | `/chat/model-context` | dict | chat |
| GET | `/chat/ollama-models` | dict | chat |
| POST | `/chat/open-external` | dict | chat |
| POST | `/chat/runs/{run_id}/cancel` | dict | chat |
| POST | `/chat/runs/{run_id}/steer` | dict | chat |
| GET | `/chat/runs/{run_id}/subscribe` |  | chat |
| POST | `/chat/runs/{run_id}/tool-result` | dict | chat |
| GET | `/chat/session-milestones` | dict | chat |
| GET | `/chat/sessions` | dict | chat |
| POST | `/chat/sessions` | dict | chat |
| GET | `/chat/sessions/search` | dict | chat |
| DELETE | `/chat/sessions/{session_id}` | dict | chat |
| GET | `/chat/sessions/{session_id}` | dict | chat |
| POST | `/chat/sessions/{session_id}/cancel-active` | dict | chat |
| GET | `/chat/sessions/{session_id}/follow` |  | chat |
| GET | `/chat/sessions/{session_id}/live` |  | chat |
| PUT | `/chat/sessions/{session_id}/rename` | dict | chat |
| POST | `/chat/stream` |  | chat |
| POST | `/chat/stream/v2` |  | chat_stream_v2 |
| POST | `/chat/terminal/run` | dict | chat |
| POST | `/chat/tool_results` | dict | chat_stream_v2 |
| GET | `/chat/tree` | dict | chat |
| GET | `/chat/visible-providers` | dict | chat |
| POST | `/chat/warm` | dict | chat_stream_v2 |
| GET | `/chat/workspace-trust` | dict | chat |
| POST | `/chat/workspace-trust` | dict | chat |
| GET | `/cowork/agents` | dict | cowork |
| GET | `/cowork/app-dispatch/pending` | dict | cowork |
| POST | `/cowork/app-dispatch/{dispatch_id}/ack` | dict | cowork |
| GET | `/cowork/channels` | dict | cowork |
| GET | `/cowork/plans` | dict | cowork |
| GET | `/cowork/queue` | dict | cowork |
| POST | `/cowork/queue/{item_id}/approve` | dict | cowork |
| POST | `/cowork/queue/{item_id}/reject` | dict | cowork |
| GET | `/cowork/share-guard` | dict | cowork |
| POST | `/cowork/share-guard/{decision_id}/resolve` | dict | cowork |
| GET | `/cowork/todos` | dict | cowork |
| POST | `/cowork/todos` | dict | cowork |
| DELETE | `/cowork/todos/{todo_id}` | dict | cowork |
| POST | `/cowork/todos/{todo_id}/expiry` | dict | cowork |
| POST | `/cowork/todos/{todo_id}/status` | dict | cowork |
| GET | `/cowork/ui-panel/pending` | dict | cowork |
| POST | `/cowork/ui-panel/{request_id}/ack` | dict | cowork |
| GET | `/files/` | dict | files |
| GET | `/files/{filename}` |  | files |
| GET | `/health` | HealthResponse | health |
| GET | `/interlanguage-blind` |  | interlanguage_blind |
| GET | `/interlanguage-blind/` |  | interlanguage_blind |
| POST | `/interlanguage-blind/api/answer` |  | interlanguage_blind |
| GET | `/interlanguage-blind/api/confusion` |  | interlanguage_blind |
| POST | `/interlanguage-blind/api/finish` |  | interlanguage_blind |
| GET | `/interlanguage-blind/api/next` |  | interlanguage_blind |
| GET | `/interlanguage-blind/api/progress` |  | interlanguage_blind |
| POST | `/interlanguage-blind/api/start` |  | interlanguage_blind |
| GET | `/interlanguage-blind/phase4` |  | interlanguage_blind |
| GET | `/interlanguage-blind/phase4/` |  | interlanguage_blind |
| GET | `/invites` | dict | teams |
| POST | `/invites/{token}/accept` | dict | teams |
| GET | `/mc/absence-awareness` | dict | mission_control_introspection |
| GET | `/mc/absence-state` | dict | mission_control_living_mind |
| GET | `/mc/adaptive-learning` | dict | mission_control_runtime_config |
| GET | `/mc/adaptive-planner` | dict | mission_control_runtime_config |
| GET | `/mc/adaptive-reasoning` | dict | mission_control_runtime_config |
| GET | `/mc/aesthetics` | dict | mission_control_introspection |
| GET | `/mc/affective-meta-state` | dict | mission_control_jarvis_state |
| GET | `/mc/agency-map` | dict | mission_control_introspection |
| GET | `/mc/agent-lineage` | dict | mission_control_agents |
| GET | `/mc/agentic-guards-state` | dict | agentic_guards |
| GET | `/mc/agents` | dict | mission_control_agents |
| GET | `/mc/agents/{agent_id}` | dict | mission_control_agents |
| GET | `/mc/agents/{agent_id}/messages` | dict | mission_control_agents |
| GET | `/mc/agents/{agent_id}/runs` | dict | mission_control_agents |
| GET | `/mc/agents/{agent_id}/tool-calls` | dict | mission_control_agents |
| GET | `/mc/anticipatory-context` | dict | mission_control_introspection |
| GET | `/mc/apophenia-guard` | dict | mission_control_introspection |
| GET | `/mc/approval-feedback` | dict | mission_control_runtime_config |
| GET | `/mc/approvals` | dict | mission_control_runs_ops |
| GET | `/mc/attention-budget` | dict | mission_control_jarvis_state |
| GET | `/mc/attention-profile` | dict | mission_control_introspection |
| GET | `/mc/autonomy/proposals` | dict | mission_control_runs_ops |
| POST | `/mc/autonomy/proposals/{proposal_id}/approve` | dict | mission_control_runs_ops |
| POST | `/mc/autonomy/proposals/{proposal_id}/reject` | dict | mission_control_runs_ops |
| GET | `/mc/blind-spots` | dict | mission_control_introspection |
| GET | `/mc/body-state` | dict | mission_control_living_mind |
| GET | `/mc/boredom` | dict | mission_control_introspection |
| GET | `/mc/boundary-model` | dict | mission_control_introspection |
| GET | `/mc/cadence-producers` | dict | mission_control_introspection |
| POST | `/mc/capability-approval-requests/{request_id}/approve` | dict | mission_control_runtime_config |
| POST | `/mc/capability-approval-requests/{request_id}/execute` | dict | mission_control_runtime_config |
| GET | `/mc/cheap-balancer-state` | dict | cheap_balancer |
| POST | `/mc/cheap-balancer/refresh-pool` | dict | cheap_balancer |
| POST | `/mc/cheap-balancer/slot/{slot_id:path}/disable` | dict | cheap_balancer |
| POST | `/mc/cheap-balancer/slot/{slot_id:path}/enable` | dict | cheap_balancer |
| POST | `/mc/cheap-balancer/slot/{slot_id:path}/reset` | dict | cheap_balancer |
| GET | `/mc/chronicle` | dict | mission_control_introspection |
| GET | `/mc/code-aesthetic` | dict | mission_control_living_mind |
| GET | `/mc/cognitive-core-experiments` | dict | mission_control_introspection |
| GET | `/mc/cognitive-frame` | dict | mission_control_jarvis_state |
| GET | `/mc/cognitive-state-injection` | dict | mission_control_introspection |
| GET | `/mc/compass` | dict | mission_control_introspection |
| GET | `/mc/conflict-resolution` | dict | mission_control_jarvis_state |
| GET | `/mc/conflict-signal` | dict | mission_control_living_mind |
| GET | `/mc/contract-evolution` | dict | mission_control_introspection |
| GET | `/mc/conversation-rhythm` | dict | mission_control_introspection |
| GET | `/mc/costs` | dict | mission_control_runs_ops |
| GET | `/mc/costs/daily` | dict | mission_control_dashboard |
| GET | `/mc/council` | dict | mission_control_agents |
| GET | `/mc/council-activation-config` | dict | mission_control_agents |
| POST | `/mc/council-activation-config` | dict | mission_control_agents |
| GET | `/mc/council-model-config` | dict | mission_control_agents |
| POST | `/mc/council-model-config` | dict | mission_control_agents |
| GET | `/mc/council-runtime` | dict | mission_control_jarvis_state |
| GET | `/mc/council/{council_id}` | dict | mission_control_agents |
| GET | `/mc/council/{council_id}/messages` | dict | mission_control_agents |
| GET | `/mc/counterfactuals` | dict | mission_control_introspection |
| GET | `/mc/creative-drift` | dict | mission_control_living_mind |
| GET | `/mc/creative-journal` | dict | mission_control_jarvis_state |
| GET | `/mc/cross-signal-patterns` | dict | mission_control_introspection |
| GET | `/mc/curiosity-state` | dict | mission_control_living_mind |
| GET | `/mc/decisions` | dict | mission_control_introspection |
| GET | `/mc/decisions-journal` | dict | mission_control_introspection |
| GET | `/mc/deep-analyzer` | dict | mission_control_introspection |
| GET | `/mc/desires` | dict | mission_control_living_mind |
| POST | `/mc/development-focus/{focus_id}/complete` | dict | mission_control_runtime_config |
| GET | `/mc/development-narrative` | dict | mission_control_living_mind |
| GET | `/mc/dream-articulation` | dict | mission_control_jarvis_state |
| GET | `/mc/dream-carry-over` | dict | mission_control_introspection |
| GET | `/mc/dream-distillation` | dict | mission_control_jarvis_state |
| GET | `/mc/dream-hypotheses` | dict | mission_control_introspection |
| GET | `/mc/dream-influence` | dict | mission_control_jarvis_state |
| GET | `/mc/dream-insights` | dict | mission_control_living_mind |
| GET | `/mc/dream-motifs` | dict | mission_control_living_mind |
| GET | `/mc/embodied-state` | dict | mission_control_jarvis_state |
| GET | `/mc/emergent-goals` | dict | mission_control_introspection |
| GET | `/mc/emergent-signals` | dict | mission_control_jarvis_state |
| GET | `/mc/emotion-concepts` | dict | mission_control_jarvis_state |
| GET | `/mc/emotional-controls` | dict | mission_control_introspection |
| GET | `/mc/emotional-memory` | dict | mission_control_runtime_config |
| GET | `/mc/epistemic-runtime-state` | dict | mission_control_jarvis_state |
| GET | `/mc/epistemics` | dict | mission_control_introspection |
| GET | `/mc/events` | dict | mission_control_runs_ops |
| GET | `/mc/existential-wonder` | dict | mission_control_living_mind |
| GET | `/mc/experienced-time` | dict | mission_control_living_mind |
| GET | `/mc/experiential-memories` | dict | mission_control_introspection |
| GET | `/mc/experiential-runtime-context` | dict | mission_control_jarvis_state |
| GET | `/mc/experiments` | dict | mission_control_introspection |
| POST | `/mc/experiments/{experiment_id}/toggle` | dict | mission_control_introspection |
| GET | `/mc/finitude` | dict | mission_control_jarvis_state |
| GET | `/mc/flow-state` | dict | mission_control_introspection |
| GET | `/mc/forgetting-curve` | dict | mission_control_introspection |
| GET | `/mc/formed-values` | dict | mission_control_introspection |
| GET | `/mc/global-workspace` | dict | mission_control_introspection |
| GET | `/mc/gratitude` | dict | mission_control_introspection |
| GET | `/mc/guided-learning` | dict | mission_control_runtime_config |
| GET | `/mc/gut` | dict | mission_control_introspection |
| GET | `/mc/habits` | dict | mission_control_introspection |
| GET | `/mc/habits-pipeline` | dict | mission_control_introspection |
| GET | `/mc/hardening` | dict | mission_control_skills_hardening_lab |
| GET | `/mc/heartbeat` | dict | mission_control_runtime_config |
| POST | `/mc/heartbeat/tick` | dict | mission_control_runtime_config |
| GET | `/mc/idle-consolidation` | dict | mission_control_jarvis_state |
| GET | `/mc/idle-thinking` | dict | mission_control_introspection |
| GET | `/mc/initiatives` | dict | mission_control_runs_ops |
| POST | `/mc/initiatives/{initiative_id}/approve` | dict | mission_control_runs_ops |
| POST | `/mc/initiatives/{initiative_id}/reject` | dict | mission_control_runs_ops |
| GET | `/mc/inner-voice-daemon` | dict | mission_control_jarvis_state |
| GET | `/mc/internal-cadence` | dict | mission_control_jarvis_state |
| GET | `/mc/irony-state` | dict | mission_control_living_mind |
| GET | `/mc/jarvis` | dict | mission_control_jarvis_state |
| GET | `/mc/jarvis-agenda` | dict | mission_control_introspection |
| GET | `/mc/lab` | dict | mission_control_skills_hardening_lab |
| GET | `/mc/layer-tensions` | dict | mission_control_living_mind |
| GET | `/mc/layer-tensions` | dict | mission_control_introspection |
| GET | `/mc/learning-curriculum` | dict | mission_control_introspection |
| GET | `/mc/life-projects` | dict | mission_control_runs_ops |
| POST | `/mc/life-projects/{initiative_id}/abandon` | dict | mission_control_runs_ops |
| GET | `/mc/liveness` | dict | mission_control_runs_ops |
| GET | `/mc/living-executive` | dict | mission_control_introspection |
| GET | `/mc/living-heartbeat-cycle` | dict | mission_control_introspection |
| GET | `/mc/loop-runtime` | dict | mission_control_jarvis_state |
| GET | `/mc/main-agent-selection` | dict | mission_control_runtime_config |
| PUT | `/mc/main-agent-selection` | dict | mission_control_runtime_config |
| GET | `/mc/memory` | dict | mission_control_skills_hardening_lab |
| GET | `/mc/memory-decay` | dict | mission_control_living_mind |
| POST | `/mc/memory-decay/hold-fast/{record_id}` | dict | mission_control_living_mind |
| GET | `/mc/memory-pipeline` | dict | mission_control_runs_ops |
| GET | `/mc/meta-cognition` | dict | mission_control_introspection |
| GET | `/mc/meta-reflection` | dict | mission_control_living_mind |
| GET | `/mc/mirror` | dict | mission_control_introspection |
| GET | `/mc/missions-pipeline` | dict | mission_control_introspection |
| GET | `/mc/mood-dialer` | dict | mission_control_introspection |
| GET | `/mc/narrative-identity` | dict | mission_control_introspection |
| GET | `/mc/negotiation-pipeline` | dict | mission_control_introspection |
| GET | `/mc/negotiations` | dict | mission_control_introspection |
| GET | `/mc/ollama-models` | dict | mission_control_runtime_config |
| GET | `/mc/operations` | dict | mission_control_runs_ops |
| GET | `/mc/overview` | dict | mission_control_runs_ops |
| GET | `/mc/paradoxes` | dict | mission_control_introspection |
| GET | `/mc/paradoxes-capture` | dict | mission_control_introspection |
| GET | `/mc/personal-project` | dict | mission_control_introspection |
| GET | `/mc/personality-vector` | dict | mission_control_introspection |
| GET | `/mc/private-brain` | dict | mission_control_runtime_config |
| GET | `/mc/procedure-bank-pipeline` | dict | mission_control_introspection |
| GET | `/mc/procedures` | dict | mission_control_introspection |
| GET | `/mc/prompt-evolution` | dict | mission_control_jarvis_state |
| GET | `/mc/provider-models` | dict | mission_control_runtime_config |
| GET | `/mc/recurrence-state` | dict | mission_control_introspection |
| GET | `/mc/reflection-cycle` | dict | mission_control_living_mind |
| GET | `/mc/reflection-to-plan` | dict | mission_control_introspection |
| GET | `/mc/regret` | dict | mission_control_introspection |
| GET | `/mc/relationship-texture` | dict | mission_control_introspection |
| GET | `/mc/rhythm` | dict | mission_control_introspection |
| GET | `/mc/runs` | dict | mission_control_runs_ops |
| GET | `/mc/runs/{run_id}` | dict | mission_control_dashboard |
| GET | `/mc/runtime` | dict | mission_control_runtime_config |
| GET | `/mc/runtime-contract` | dict | mission_control_runtime_config |
| POST | `/mc/runtime-contract/candidates/{candidate_id}/apply` | dict | mission_control_runtime_config |
| POST | `/mc/runtime-contract/candidates/{candidate_id}/approve` | dict | mission_control_runtime_config |
| POST | `/mc/runtime-contract/candidates/{candidate_id}/reject` | dict | mission_control_runtime_config |
| GET | `/mc/runtime-self-model` | dict | mission_control_jarvis_state |
| POST | `/mc/runtime/agents/run-due` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/spawn` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/cancel` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/execute` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/expire` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/message` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/peer-message` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/promote` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/resume` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/schedule` | dict | mission_control_agents |
| POST | `/mc/runtime/agents/{agent_id}/suspend` | dict | mission_control_agents |
| POST | `/mc/runtime/council/spawn` | dict | mission_control_agents |
| POST | `/mc/runtime/council/{council_id}/message` | dict | mission_control_agents |
| POST | `/mc/runtime/council/{council_id}/run-round` | dict | mission_control_agents |
| POST | `/mc/runtime/swarm/spawn` | dict | mission_control_agents |
| POST | `/mc/runtime/swarm/{council_id}/run-round` | dict | mission_control_agents |
| GET | `/mc/rupture-repair` | dict | mission_control_introspection |
| GET | `/mc/scheduled-tasks` | dict | mission_control_dashboard |
| GET | `/mc/seeds` | dict | mission_control_introspection |
| GET | `/mc/self-code-changes` | dict | mission_control_jarvis_state |
| GET | `/mc/self-compassion` | dict | mission_control_introspection |
| GET | `/mc/self-critique` | dict | mission_control_jarvis_state |
| GET | `/mc/self-deception-guard` | dict | mission_control_jarvis_state |
| GET | `/mc/self-experiments` | dict | mission_control_introspection |
| GET | `/mc/self-knowledge` | dict | mission_control_jarvis_state |
| GET | `/mc/self-review-unified` | dict | mission_control_introspection |
| GET | `/mc/self-surprises` | dict | mission_control_introspection |
| GET | `/mc/self-system-code-awareness` | dict | mission_control_runtime_config |
| GET | `/mc/session-continuity` | dict | mission_control_introspection |
| GET | `/mc/shared-language` | dict | mission_control_introspection |
| GET | `/mc/shared-language-extended` | dict | mission_control_introspection |
| GET | `/mc/silence-patterns` | dict | mission_control_introspection |
| GET | `/mc/silence-signals` | dict | mission_control_introspection |
| GET | `/mc/skills` | dict | mission_control_skills_hardening_lab |
| GET | `/mc/subagent-ecology` | dict | mission_control_jarvis_state |
| GET | `/mc/surprise-state` | dict | mission_control_living_mind |
| GET | `/mc/system/git` | dict | system_health |
| POST | `/mc/system/git/commit` | dict | system_health |
| GET | `/mc/system/health` | dict | system_health |
| GET | `/mc/taste-profile` | dict | mission_control_introspection |
| GET | `/mc/taste-state` | dict | mission_control_living_mind |
| GET | `/mc/temporal-context` | dict | mission_control_introspection |
| GET | `/mc/thought-proposals` | dict | mission_control_living_mind |
| POST | `/mc/thought-proposals/{proposal_id}/resolve` | dict | mission_control_living_mind |
| GET | `/mc/thought-stream` | dict | mission_control_living_mind |
| GET | `/mc/tool-intent` | dict | mission_control_runtime_config |
| POST | `/mc/tool-intent/approve` | dict | mission_control_runtime_config |
| POST | `/mc/tool-intent/deny` | dict | mission_control_runtime_config |
| GET | `/mc/tool-router-state` | dict | tool_router |
| GET | `/mc/unconscious-temperature-field` | dict | mission_control_jarvis_state |
| GET | `/mc/user-emotional-resonance` | dict | mission_control_introspection |
| GET | `/mc/user-mental-model` | dict | mission_control_introspection |
| GET | `/mc/user-model` | dict | mission_control_living_mind |
| GET | `/mc/visible-execution` | dict | mission_control_runtime_config |
| PUT | `/mc/visible-execution` | dict | mission_control_runtime_config |
| GET | `/mc/watcher-lineage` | dict | mission_control_agents |
| GET | `/mc/witness-daemon` | dict | mission_control_jarvis_state |
| POST | `/mc/workspace-capabilities/{capability_id}/invoke` | dict | mission_control_runtime_config |
| GET | `/mobile/download` |  | mobile_update |
| GET | `/mobile/latest` | dict | mobile_update |
| POST | `/notifications/ack` | dict | presence |
| GET | `/notifications/pending` | dict | presence |
| GET | `/notifications/preferences` | dict | presence |
| POST | `/notifications/preferences` | dict | presence |
| POST | `/paste` | dict | paste |
| GET | `/paste/{paste_id}` | dict | paste |
| GET | `/plugins` | dict | plugins |
| POST | `/plugins/channel/{plugin_id}/inbound` | dict | plugins |
| GET | `/plugins/channel/{plugin_id}/response` | dict | plugins |
| POST | `/plugins/channel/{plugin_id}/status` | dict | plugins |
| GET | `/plugins/rulesets/{plugin_id}` | dict | plugins |
| PUT | `/plugins/rulesets/{plugin_id}` | dict | plugins |
| GET | `/presence/debug` | dict | presence |
| POST | `/presence/ping` | dict | presence |
| GET | `/presence/state` | dict | presence |
| POST | `/push/register` | dict | push |
| POST | `/push/unregister` | dict | push |
| GET | `/status` | dict | status |
| GET | `/teams` | dict | teams |
| POST | `/teams` | dict | teams |
| POST | `/teams/{team_id}/invite` | dict | teams |
| GET | `/teams/{team_id}/members` | dict | teams |
| DELETE | `/teams/{team_id}/members/{target_user_id}` | dict | teams |
| GET | `/teams/{team_id}/sessions` | dict | teams |
| POST | `/teams/{team_id}/sessions` | dict | teams |
| POST | `/transcribe` | dict | transcribe |
| GET | `/v1/agent/audit` | dict | agent_audit |
| POST | `/v1/agent/step` |  | agent_loop |
| POST | `/v1/agent/turn-absorb` |  | agent_loop |
| POST | `/v1/agent/turn-begin` |  | agent_loop |
| POST | `/v1/agent/turn-end` |  | agent_loop |
| POST | `/v1/chat/completions` |  | openai_compat |
| GET | `/v1/models` |  | openai_compat |
| GET | `/v1/tools/catalog` |  | agent_loop |
| POST | `/v1/tools/execute` |  | agent_loop |
| GET | `/v1/tools/native` |  | agent_loop |
| POST | `/v1/tools/native` |  | agent_loop |
