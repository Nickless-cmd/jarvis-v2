# `apps.central_cli.central_cli` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/central_cli/central_cli/__init__.py`

_(no top-level classes or functions)_

## `apps/central_cli/central_cli/client.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CentralError` | `` | CLI-vendt fejl med kategori (connection/permission/auth/server/client). | [src](../../../apps/central_cli/central_cli/client.py#L8) |
| method | `CentralError.__init__` | `(self, category, message, status=…)` | — | [src](../../../apps/central_cli/central_cli/client.py#L10) |
| function | `_categorize` | `(status)` | — | [src](../../../apps/central_cli/central_cli/client.py#L16) |
| class | `CentralClient` | `` | — | [src](../../../apps/central_cli/central_cli/client.py#L26) |
| method | `CentralClient.__init__` | `(self, *, base_url, token, timeout=…, _transport=…)` | — | [src](../../../apps/central_cli/central_cli/client.py#L27) |
| method | `CentralClient._check` | `(self, resp)` | — | [src](../../../apps/central_cli/central_cli/client.py#L33) |
| method | `CentralClient.get_json` | `(self, path, params=…)` | — | [src](../../../apps/central_cli/central_cli/client.py#L39) |
| method | `CentralClient.post_json` | `(self, path, body)` | — | [src](../../../apps/central_cli/central_cli/client.py#L46) |
| method | `CentralClient.iter_sse` | `(self, path)` | Yield parsed `data:` JSON-linjer fra en SSE-stream. Self-safe pr. linje. | [src](../../../apps/central_cli/central_cli/client.py#L53) |
| method | `CentralClient.close` | `(self)` | — | [src](../../../apps/central_cli/central_cli/client.py#L70) |

## `apps/central_cli/central_cli/commands.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CommandSpec` | `` | — | [src](../../../apps/central_cli/central_cli/commands.py#L7) |
| function | `_cost_command` | `(args)` | WS3: `jc cost` → GET /central/cost (owner-gated cost-aggregat). | [src](../../../apps/central_cli/central_cli/commands.py#L78) |
| function | `resolve_command` | `(verb, args)` | Map (verb, args) → CommandSpec. Writes markeres write=True (til confirm-guard). | [src](../../../apps/central_cli/central_cli/commands.py#L113) |

## `apps/central_cli/central_cli/config.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `resolve_base_url` | `(*, remote)` | --remote > env CENTRAL_CLI_API_URL > default (jc-tunnel). Remote-først. | [src](../../../apps/central_cli/central_cli/config.py#L10) |
| function | `resolve_token` | `()` | env CENTRAL_CLI_TOKEN > jc's ~/.config/jarvis-owner-token. None hvis ingen. | [src](../../../apps/central_cli/central_cli/config.py#L20) |

## `apps/central_cli/central_cli/datasource.py`
_Data layer for the Central HUD._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_spark` | `(vals)` | Render a small float list as a unicode block sparkline. | [src](../../../apps/central_cli/central_cli/datasource.py#L18) |
| function | `_realtime` | `(client)` | — | [src](../../../apps/central_cli/central_cli/datasource.py#L28) |
| function | `overview` | `(client)` | Top-level status summary from /central/realtime. | [src](../../../apps/central_cli/central_cli/datasource.py#L33) |
| function | `affect` | `(client)` | Affektiv fordeling fra /central/affect (rådets #4). Self-safe. | [src](../../../apps/central_cli/central_cli/datasource.py#L49) |
| function | `tone` | `(client)` | Centralens sproglige tone-profil fra /central/tone (rådets #5). Self-safe. | [src](../../../apps/central_cli/central_cli/datasource.py#L68) |
| function | `_incident_set` | `(client)` | (cluster, nerve) pairs with error/critical severity. | [src](../../../apps/central_cli/central_cli/datasource.py#L93) |
| function | `nerves` | `(client)` | Per-nerve rows from /central/timeseries, with derived state + sparkline. | [src](../../../apps/central_cli/central_cli/datasource.py#L105) |
| function | `clusters` | `(client)` | Per-cluster summary rows. | [src](../../../apps/central_cli/central_cli/datasource.py#L157) |
| function | `incidents` | `(client)` | Incident list from /central/realtime (as-is). | [src](../../../apps/central_cli/central_cli/datasource.py#L207) |
| function | `diagnostics` | `(client)` | Diagnostics payload from /central/diagnostics (as-is). | [src](../../../apps/central_cli/central_cli/datasource.py#L214) |
| function | `connections` | `(client)` | API-forbindelses-presence fra /central/connections (hvem/hvad rammer API'et). | [src](../../../apps/central_cli/central_cli/datasource.py#L220) |
| function | `excess` | `(client)` | Gartner-sans fra /central/excess (Centralens egen vægt/bloat). Self-safe. | [src](../../../apps/central_cli/central_cli/datasource.py#L227) |
| function | `decentralization` | `(client)` | Chokepoint-skat fra /central/decentralization (hvor meget er unødvendig flaskehals). Self-safe. | [src](../../../apps/central_cli/central_cli/datasource.py#L233) |
| function | `users` | `(client)` | Bruger-aktivitet fra /central/users (hvem sidst aktiv, via hvad). Self-safe. | [src](../../../apps/central_cli/central_cli/datasource.py#L239) |
| function | `anomalies` | `(client)` | Anomalies from /central/diagnostics, shaped for the Anomalies view. | [src](../../../apps/central_cli/central_cli/datasource.py#L245) |
| function | `governance` | `(client)` | Governance flags from /central/governance. | [src](../../../apps/central_cli/central_cli/datasource.py#L274) |
| function | `healers` | `(client)` | Healers payload from /central/healers (as-is). | [src](../../../apps/central_cli/central_cli/datasource.py#L280) |
| function | `feed` | `(client)` | Decision feed from /central/realtime, collapsing identical rows. | [src](../../../apps/central_cli/central_cli/datasource.py#L286) |
| function | `_short_sig` | `(signature)` | Stable 8-hex-char id derived from a signature string. | [src](../../../apps/central_cli/central_cli/datasource.py#L314) |
| function | `incident_detail` | `(client, incident)` | Enrich a realtime incident with joined root-cause / correlation / heal / | [src](../../../apps/central_cli/central_cli/datasource.py#L319) |
| function | `agents` | `(client)` | Agent roster from /central/agents, shaped for the Agents view. | [src](../../../apps/central_cli/central_cli/datasource.py#L453) |
| function | `balancer` | `(client)` | Cheap-lane balancer snapshot from /mc/cheap-balancer-state. | [src](../../../apps/central_cli/central_cli/datasource.py#L510) |
| function | `self_snapshot` | `(client)` | Jarvis' reduced self from /central/self, shaped for the Mind & Self view. | [src](../../../apps/central_cli/central_cli/datasource.py#L555) |
| function | `cost_today` | `(client)` | Today's total cost in USD from /central/costs-daily, or None if unavailable. | [src](../../../apps/central_cli/central_cli/datasource.py#L572) |
| function | `council` | `(client)` | Council/swarm sessions from /central/council. Self-safe → []. | [src](../../../apps/central_cli/central_cli/datasource.py#L590) |
| function | `scheduled` | `(client)` | Pending scheduled tasks from /central/queues/scheduled. Self-safe → []. | [src](../../../apps/central_cli/central_cli/datasource.py#L601) |
| function | `runs` | `(client, limit=…)` | Recent visible runs from /central/runs. Self-safe → []. | [src](../../../apps/central_cli/central_cli/datasource.py#L612) |
| function | `run_detail` | `(client, run_id)` | One run detail from /central/runs/{run_id}. Self-safe → {}. | [src](../../../apps/central_cli/central_cli/datasource.py#L623) |
| function | `autonomy` | `(client)` | Autonomy proposal queue from /central/autonomy. Self-safe → | [src](../../../apps/central_cli/central_cli/datasource.py#L634) |
| function | `initiative` | `(client)` | Gated initiativ-stige fra /central/initiative. Self-safe → | [src](../../../apps/central_cli/central_cli/datasource.py#L650) |
| function | `events` | `(client, family=…, limit=…)` | Recent eventbus items from /central/events. Self-safe → []. | [src](../../../apps/central_cli/central_cli/datasource.py#L681) |
| function | `memory_health` | `(client)` | Memory-pipeline health from /central/memory-health. Self-safe → | [src](../../../apps/central_cli/central_cli/datasource.py#L698) |
| function | `inner_life` | `(client)` | Jarvis' reducerede living-mind + experiment-digest fra /central/inner-life. | [src](../../../apps/central_cli/central_cli/datasource.py#L715) |
| function | `soul` | `(client)` | Jarvis' mørke sjæle-/tids-signaler fra /central/soul. | [src](../../../apps/central_cli/central_cli/datasource.py#L736) |
| function | `dark_products` | `(client)` | Jarvis' mørke daemon-PRODUKTER fra /central/dark-products. | [src](../../../apps/central_cli/central_cli/datasource.py#L756) |
| function | `costs_daily` | `(client)` | Daily cost time-series from /central/costs-daily, shaped for the CLI. | [src](../../../apps/central_cli/central_cli/datasource.py#L776) |
| function | `attention` | `(client)` | Attention-budget-surface fra /central/attention. Self-safe → {}. | [src](../../../apps/central_cli/central_cli/datasource.py#L808) |
| function | `skills` | `(client)` | Skill-engine + skill-contract-registry fra /central/skills. Self-safe → | [src](../../../apps/central_cli/central_cli/datasource.py#L820) |
| function | `integrity` | `(client)` | Self-deception-guard-surface fra /central/integrity. Self-safe → {}. | [src](../../../apps/central_cli/central_cli/datasource.py#L838) |
| function | `experiments` | `(client)` | Cognitive-core-experiments-surface fra /central/experiments. Self-safe → {}. | [src](../../../apps/central_cli/central_cli/datasource.py#L850) |
| function | `execution` | `(client)` | Visible-execution-config (whitelisted flags) fra /central/execution. | [src](../../../apps/central_cli/central_cli/datasource.py#L862) |

## `apps/central_cli/central_cli/feed.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FeedLine` | `` | — | [src](../../../apps/central_cli/central_cli/feed.py#L11) |
| function | `feed_line_from_event` | `(ev)` | — | [src](../../../apps/central_cli/central_cli/feed.py#L19) |
| class | `FeedBuffer` | `` | Bounded, nyeste-først feed-buffer (live nerve-firings). | [src](../../../apps/central_cli/central_cli/feed.py#L29) |
| method | `FeedBuffer.__init__` | `(self, cap=…)` | — | [src](../../../apps/central_cli/central_cli/feed.py#L31) |
| method | `FeedBuffer.add` | `(self, line)` | — | [src](../../../apps/central_cli/central_cli/feed.py#L34) |
| method | `FeedBuffer.recent` | `(self)` | — | [src](../../../apps/central_cli/central_cli/feed.py#L37) |

## `apps/central_cli/central_cli/hud.py`
_Central HUD — J.A.R.V.I.S-style Textual UI, built 1:1 to the mockup._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CentralHud` | `` | The Central HUD app shell (mockup-faithful). | [src](../../../apps/central_cli/central_cli/hud.py#L82) |
| method | `CentralHud.__init__` | `(self, *, client=…, live=…)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L229) |
| method | `CentralHud.compose` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L264) |
| method | `CentralHud.on_mount` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L289) |
| method | `CentralHud._prime` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L307) |
| method | `CentralHud._tick_pulse` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L335) |
| method | `CentralHud._keep_focus` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L339) |
| method | `CentralHud.show_tab` | `(self, name)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L347) |
| method | `CentralHud._apply_tab_visibility` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L353) |
| method | `CentralHud._populate_active_tab` | `(self, force=…)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L365) |
| method | `CentralHud.refresh_data` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L454) |
| method | `CentralHud._render_header` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L486) |
| method | `CentralHud._render_tabs` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L520) |
| method | `CentralHud._render_cmd` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L531) |
| function | `run_hud` | `(ns)` | — | [src](../../../apps/central_cli/central_cli/hud.py#L549) |

## `apps/central_cli/central_cli/hud_actions.py`
_Central HUD — action handlers + command/write layer (``_ActionMixin``)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_ActionMixin` | `` | Action-side of the Central HUD: key handlers, command line, writes. | [src](../../../apps/central_cli/central_cli/hud_actions.py#L24) |
| method | `_ActionMixin.action_show` | `(self, name)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L28) |
| method | `_ActionMixin.action_help` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L31) |
| method | `_ActionMixin._table` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L35) |
| method | `_ActionMixin._refresh_detail_for_current` | `(self)` | Render the detail panel for whichever row the cursor is on (used after | [src](../../../apps/central_cli/central_cli/hud_actions.py#L44) |
| method | `_ActionMixin._after_cursor_move` | `(self, t)` | Refresh the detail panel for the newly-selected row (robust — does not | [src](../../../apps/central_cli/central_cli/hud_actions.py#L56) |
| method | `_ActionMixin._active_panel` | `(self)` | Det synlige panel (#hud-panel) hvis en panel-fane (overview/mind/ | [src](../../../apps/central_cli/central_cli/hud_actions.py#L64) |
| method | `_ActionMixin.action_nav_up` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L77) |
| method | `_ActionMixin.action_nav_down` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L87) |
| method | `_ActionMixin.action_nav_pageup` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L97) |
| method | `_ActionMixin.action_nav_pagedown` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L107) |
| method | `_ActionMixin._cycle_tab` | `(self, step)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L117) |
| method | `_ActionMixin.action_next_tab` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L126) |
| method | `_ActionMixin.action_prev_tab` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L129) |
| method | `_ActionMixin.action_cancel` | `(self)` | Esc: clear a half-typed command, else cancel a pending confirm. | [src](../../../apps/central_cli/central_cli/hud_actions.py#L132) |
| method | `_ActionMixin.on_input_submitted` | `(self, event)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L149) |
| method | `_ActionMixin._run_command` | `(self, line)` | Parse + execute a command via the shared resolve_command layer. | [src](../../../apps/central_cli/central_cli/hud_actions.py#L183) |
| method | `_ActionMixin._show_feel` | `(self, data)` | Render Jarvis' somatic snapshot as his own voice in the detail panel. | [src](../../../apps/central_cli/central_cli/hud_actions.py#L214) |
| method | `_ActionMixin._show_command_output` | `(self, line, data)` | Render a read command's FULL result into the detail panel (scrollable). | [src](../../../apps/central_cli/central_cli/hud_actions.py#L236) |
| method | `_ActionMixin._drill_incident` | `(self, index)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L257) |
| method | `_ActionMixin.on_data_table_row_highlighted` | `(self, event)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L261) |
| method | `_ActionMixin.on_data_table_row_selected` | `(self, event)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L268) |
| method | `_ActionMixin._drill_row` | `(self, index)` | Enter/select on a row: governance toggles, approvals arms godkend/afvis, | [src](../../../apps/central_cli/central_cli/hud_actions.py#L275) |
| method | `_ActionMixin._begin_approval` | `(self, index)` | Enter på et forslag: armér en godkend/afvis-bekræftelse. Bekræftes via | [src](../../../apps/central_cli/central_cli/hud_actions.py#L286) |
| method | `_ActionMixin._resolve_approval` | `(self, approve)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L304) |
| method | `_ActionMixin._next_value` | `(self, flag)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L327) |
| method | `_ActionMixin._toggle_governance_row` | `(self, index)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L341) |
| method | `_ActionMixin._set_governance` | `(self, key, value)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L351) |
| method | `_ActionMixin._toggle_healer_row` | `(self, index)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L361) |
| method | `_ActionMixin._set_healer` | `(self, name, enabled)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L372) |
| method | `_ActionMixin._write_path` | `(self, kind)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L382) |
| method | `_ActionMixin._write_desc` | `(self, kind, payload)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L386) |
| method | `_ActionMixin._handle_write_response` | `(self, kind, payload, resp)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L391) |
| method | `_ActionMixin._confirm_line` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L405) |
| method | `_ActionMixin.action_toggle` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L411) |
| method | `_ActionMixin.action_confirm_yes` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L420) |
| method | `_ActionMixin.action_confirm_no` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L440) |
| method | `_ActionMixin._flash` | `(self, markup)` | — | [src](../../../apps/central_cli/central_cli/hud_actions.py#L446) |

## `apps/central_cli/central_cli/hud_populate.py`
_Central HUD — read-side rendering (``_PopulateMixin``)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_PopulateMixin` | `` | Read-side of the Central HUD: table population + detail/panel painting. | [src](../../../apps/central_cli/central_cli/hud_populate.py#L29) |
| method | `_PopulateMixin._sync_header` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L32) |
| method | `_PopulateMixin._sync_tabs` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L38) |
| method | `_PopulateMixin._set_paneh` | `(self, text)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L44) |
| method | `_PopulateMixin._set_side_paneh` | `(self, text)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L50) |
| method | `_PopulateMixin._reset_columns` | `(self, table, *cols)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L56) |
| method | `_PopulateMixin._populate_nerves` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L62) |
| method | `_PopulateMixin._render_feed` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L94) |
| method | `_PopulateMixin._detail_incident` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L121) |
| method | `_PopulateMixin._render_detail_panel` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L128) |
| method | `_PopulateMixin._populate_clusters` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L194) |
| method | `_PopulateMixin._populate_incidents` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L223) |
| method | `_PopulateMixin._populate_connections` | `(self)` | Hvem/hvad er forbundet til API'et: ip · user · endpoint · antal · fejl · aktiv. | [src](../../../apps/central_cli/central_cli/hud_populate.py#L250) |
| method | `_PopulateMixin._populate_users` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L296) |
| method | `_PopulateMixin._populate_excess` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L325) |
| method | `_PopulateMixin._populate_decentral` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L352) |
| method | `_PopulateMixin._populate_anomalies` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L379) |
| method | `_PopulateMixin._render_anomaly_detail` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L405) |
| method | `_PopulateMixin._render_row_detail` | `(self, row)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L450) |
| method | `_PopulateMixin._render_nerve_detail` | `(self, row)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L471) |
| method | `_PopulateMixin._render_cluster_detail` | `(self, row)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L503) |
| method | `_PopulateMixin._render_gov_detail` | `(self, row)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L532) |
| method | `_PopulateMixin._render_overview_panel` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L566) |
| method | `_PopulateMixin._render_diagnostics_panel` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L659) |
| method | `_PopulateMixin._populate_governance` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L720) |
| method | `_PopulateMixin._populate_runs` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L745) |
| method | `_PopulateMixin._render_run_detail` | `(self, row)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L784) |
| method | `_PopulateMixin._populate_approvals` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L829) |
| method | `_PopulateMixin._populate_agents` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L865) |
| method | `_PopulateMixin._render_agent_detail` | `(self, row)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L928) |
| method | `_PopulateMixin._populate_balancer` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L989) |
| method | `_PopulateMixin._render_balancer_detail` | `(self, row)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L1060) |
| method | `_PopulateMixin._render_mind_self_panel` | `(self)` | Render Jarvis' reduced self as HIS presence in the Central — warm, | [src](../../../apps/central_cli/central_cli/hud_populate.py#L1126) |
| method | `_PopulateMixin._rel_age` | `(iso)` | ISO timestamp → short relative age (2s / 4m / 3t / 2d). '—' on failure. | [src](../../../apps/central_cli/central_cli/hud_populate.py#L1350) |
| method | `_PopulateMixin._fmt_value` | `(value)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L1370) |
| method | `_PopulateMixin._healer_flag_name` | `(self, healer)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L1381) |
| method | `_PopulateMixin._render_healing_panel` | `(self)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L1384) |
| method | `_PopulateMixin._render_placeholder_panel` | `(self, name)` | — | [src](../../../apps/central_cli/central_cli/hud_populate.py#L1422) |

## `apps/central_cli/central_cli/hud_theme.py`
_Central HUD palette, status-maps and the ``_esc`` markup guard._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_esc` | `(value)` | Escape live/user data before it goes into a Rich-markup string, so a | [src](../../../apps/central_cli/central_cli/hud_theme.py#L16) |

## `apps/central_cli/central_cli/main.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_arg_parser` | `()` | — | [src](../../../apps/central_cli/central_cli/main.py#L8) |
| function | `main` | `(argv=…)` | — | [src](../../../apps/central_cli/central_cli/main.py#L20) |

## `apps/central_cli/central_cli/renderer.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `render_status` | `(data)` | — | [src](../../../apps/central_cli/central_cli/renderer.py#L13) |
| function | `render_generic` | `(data)` | — | [src](../../../apps/central_cli/central_cli/renderer.py#L27) |

## `apps/central_cli/central_cli/script_runner.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `execute` | `(client, *, verb, args, as_json)` | Kør én kommando mod klienten. Returnerer (output_tekst, exit_code). | [src](../../../apps/central_cli/central_cli/script_runner.py#L11) |
| function | `run_script` | `(ns)` | — | [src](../../../apps/central_cli/central_cli/script_runner.py#L30) |

## `apps/central_cli/central_cli/tui.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CentralApp` | `` | — | [src](../../../apps/central_cli/central_cli/tui.py#L13) |
| method | `CentralApp.__init__` | `(self, *, base_url, token, live=…)` | — | [src](../../../apps/central_cli/central_cli/tui.py#L20) |
| method | `CentralApp.compose` | `(self)` | — | [src](../../../apps/central_cli/central_cli/tui.py#L27) |
| method | `CentralApp.on_mount` | `(self)` | — | [src](../../../apps/central_cli/central_cli/tui.py#L34) |
| method | `CentralApp._poll_feed` | `(self)` | — | [src](../../../apps/central_cli/central_cli/tui.py#L38) |
| method | `CentralApp.on_input_submitted` | `(self, event)` | — | [src](../../../apps/central_cli/central_cli/tui.py#L52) |
| method | `CentralApp._run_command` | `(self, line)` | — | [src](../../../apps/central_cli/central_cli/tui.py#L56) |
| function | `run_tui` | `(ns)` | — | [src](../../../apps/central_cli/central_cli/tui.py#L74) |

