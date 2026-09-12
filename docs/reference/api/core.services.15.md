# `core.services.15` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/mail_checker_daemon.py`
_Mail checker daemon — checks jarvis@srvlab.dk inbox for new mail._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_automated` | `(sender, subject)` | True for bounces og autosvar — maskinstøj, ikke post der skal svares på. | [src](../../../core/services/mail_checker_daemon.py#L68) |
| function | `_is_stale` | `(date_header, now=…)` | True hvis mailen er ældre end _MAX_AGE_HOURS. | [src](../../../core/services/mail_checker_daemon.py#L73) |
| function | `_evaluate_mail` | `(sender, subject, snippet)` | Use LLM to evaluate whether a mail needs a response and draft one. | [src](../../../core/services/mail_checker_daemon.py#L93) |
| function | `_send_auto_reply` | `(to_addr, subject, reply_body)` | Send an auto-reply email via SMTP. Returns True on success. | [src](../../../core/services/mail_checker_daemon.py#L169) |
| function | `_extract_email_address` | `(sender)` | Extract bare email address from 'Name <email>' or plain email. | [src](../../../core/services/mail_checker_daemon.py#L191) |
| function | `_imap_connect` | `()` | Return an open IMAP connection. | [src](../../../core/services/mail_checker_daemon.py#L198) |
| function | `_fetch_recent` | `(conn, limit=…)` | Fetch up to `limit` most recent UNSEEN emails. | [src](../../../core/services/mail_checker_daemon.py#L207) |
| function | `_mark_as_seen` | `(imap_uids)` | Mark the given IMAP message IDs as \Seen. Returns count successfully marked. | [src](../../../core/services/mail_checker_daemon.py#L247) |
| function | `_load_mail_state` | `()` | Laes delt tilstand. Self-safe: tom dict ved enhver fejl. | [src](../../../core/services/mail_checker_daemon.py#L289) |
| function | `_save_mail_state` | `(*, check_at, new_count, senders, subjects, seen_ids)` | Skriv delt tilstand. Self-safe: en fejl her maa ikke vaelte tick'et. | [src](../../../core/services/mail_checker_daemon.py#L299) |
| function | `tick_mail_checker_daemon` | `()` | Main daemon tick — check for new mail, publish events for unseen messages. | [src](../../../core/services/mail_checker_daemon.py#L315) |
| function | `build_mail_checker_surface` | `()` | Return surface state for heartbeat context. | [src](../../../core/services/mail_checker_daemon.py#L528) |
| function | `get_latest_mail_info` | `()` | Return latest check info for other consumers. | [src](../../../core/services/mail_checker_daemon.py#L552) |
| function | `mail_awareness_section` | `()` | Ny post som en KENDSGERNING i prompten. "" naar der intet er. | [src](../../../core/services/mail_checker_daemon.py#L567) |
| function | `_mail_time_label` | `(timer)` | — | [src](../../../core/services/mail_checker_daemon.py#L610) |

## `core/services/malware_scan.py`
_Malware-scanning af uploads/vedhæftninger (spec §15.3.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ScanReport` | `` | — | [src](../../../core/services/malware_scan.py#L21) |
| method | `ScanReport.safe` | `(self)` | — | [src](../../../core/services/malware_scan.py#L27) |
| method | `ScanReport.as_dict` | `(self)` | — | [src](../../../core/services/malware_scan.py#L30) |
| function | `clamav_available` | `()` | — | [src](../../../core/services/malware_scan.py#L35) |
| function | `scan_file` | `(path)` | Scan en fil med clamscan. Returnerer ScanReport. Blokerer aldrig på | [src](../../../core/services/malware_scan.py#L39) |
| function | `is_upload_allowed` | `(path, *, block_on_unavailable=…)` | Politik-helper: må denne upload gemmes/behandles? (§15.3.1) | [src](../../../core/services/malware_scan.py#L68) |

## `core/services/markdown_structure.py`
_Rekonstruér markdown-blokstruktur fra inline-markører._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_cells` | `(region)` | Split en `|`-afgrænset region i celler; drop ydre tomme (før første / | [src](../../../core/services/markdown_structure.py#L60) |
| function | `_reflow_line_table` | `(line)` | Hvis `line` indeholder en HEL tabel mast sammen på én linje | [src](../../../core/services/markdown_structure.py#L71) |
| function | `_reflow_crammed_tables` | `(text)` | Genskab tabeller hvis hele rækken er mast sammen på én linje. | [src](../../../core/services/markdown_structure.py#L120) |
| function | `_is_bullet_line` | `(line)` | — | [src](../../../core/services/markdown_structure.py#L131) |
| function | `_ensure_blank_before_lists` | `(text)` | Indsæt en blank linje før første bullet i en liste der følger prosa, så | [src](../../../core/services/markdown_structure.py#L136) |
| function | `_normalize_segment` | `(text)` | — | [src](../../../core/services/markdown_structure.py#L150) |
| function | `normalize_markdown_structure` | `(text)` | Genskab blokstruktur fra inline-markører. Beskytter kode-fences. | [src](../../../core/services/markdown_structure.py#L169) |

## `core/services/mcp_auth.py`
_OAuth/bearer til remote MCP-servere._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_expand_env` | `(value)` | `${MIN_NOEGLE}` slaas op i miljoeet, saa en config kan deles uden token. | [src](../../../core/services/mcp_auth.py#L33) |
| function | `_load` | `()` | — | [src](../../../core/services/mcp_auth.py#L38) |
| function | `_save` | `(data)` | — | [src](../../../core/services/mcp_auth.py#L45) |
| function | `get_token` | `(name)` | — | [src](../../../core/services/mcp_auth.py#L54) |
| function | `set_token` | `(name, *, access_token, refresh_token=…, expires_in=…, token_url=…, client_id=…, client_secret=…)` | — | [src](../../../core/services/mcp_auth.py#L59) |
| function | `needs_refresh` | `(name)` | — | [src](../../../core/services/mcp_auth.py#L81) |
| function | `refresh` | `(name)` | Kør refresh_token-grantet. False = intet at fornye, eller det fejlede. | [src](../../../core/services/mcp_auth.py#L91) |
| function | `resolve_headers` | `(name, config)` | Headers til en request mod *name*. | [src](../../../core/services/mcp_auth.py#L117) |

## `core/services/mcp_client.py`
_MCP-klient — stdio og HTTP, med trust-gate foran hver forbindelse._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MCPClient` | `` | Én forbindelse til én MCP-server. | [src](../../../core/services/mcp_client.py#L46) |
| method | `MCPClient.__init__` | `(self, name, config)` | — | [src](../../../core/services/mcp_client.py#L49) |
| method | `MCPClient.connect` | `(self)` | Trust-gate først, DERNÆST forbindelse. Rækkefølgen er hele pointen. | [src](../../../core/services/mcp_client.py#L63) |
| method | `MCPClient._connect_stdio` | `(self)` | — | [src](../../../core/services/mcp_client.py#L80) |
| method | `MCPClient._connect_http` | `(self)` | — | [src](../../../core/services/mcp_client.py#L106) |
| method | `MCPClient.disconnect` | `(self)` | — | [src](../../../core/services/mcp_client.py#L121) |
| method | `MCPClient.connected` | `(self)` | — | [src](../../../core/services/mcp_client.py#L135) |
| method | `MCPClient._send_request` | `(self, method, params=…)` | — | [src](../../../core/services/mcp_client.py#L143) |
| method | `MCPClient._send_stdio` | `(self, req)` | — | [src](../../../core/services/mcp_client.py#L152) |
| method | `MCPClient._http_headers` | `(self)` | — | [src](../../../core/services/mcp_client.py#L179) |
| method | `MCPClient._send_http` | `(self, req)` | — | [src](../../../core/services/mcp_client.py#L186) |
| method | `MCPClient._send_notification` | `(self, method)` | — | [src](../../../core/services/mcp_client.py#L204) |
| method | `MCPClient._initialize` | `(self)` | MCP kræver dette håndtryk før alt andet — mange servere afviser | [src](../../../core/services/mcp_client.py#L217) |
| method | `MCPClient._discover_tools` | `(self)` | — | [src](../../../core/services/mcp_client.py#L231) |
| method | `MCPClient.call_tool` | `(self, tool_name, arguments)` | — | [src](../../../core/services/mcp_client.py#L238) |

## `core/services/mcp_manager.py`
_MCP-manager — forbinder registerets servere og eksponerer deres værktøjer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_server_config` | `(navn)` | — | [src](../../../core/services/mcp_manager.py#L27) |
| function | `get_client` | `(navn, *, connect=…)` | Hent (og evt. forbind) klienten for *navn*. None hvis ukendt server. | [src](../../../core/services/mcp_manager.py#L40) |
| function | `disconnect_all` | `()` | — | [src](../../../core/services/mcp_manager.py#L58) |
| function | `status` | `()` | Hvilke servere kendes, hvilke er godkendt, hvilke er forbundet? | [src](../../../core/services/mcp_manager.py#L68) |
| function | `list_tools` | `(navn)` | — | [src](../../../core/services/mcp_manager.py#L88) |
| function | `call` | `(navn, vaerktoej, arguments=…)` | — | [src](../../../core/services/mcp_manager.py#L99) |

## `core/services/mcp_registry.py`
_MCP-server-registry (§4.6) — brugerens konfigurerede MCP-endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/mcp_registry.py#L17) |
| function | `list_mcp_servers` | `()` | — | [src](../../../core/services/mcp_registry.py#L24) |
| function | `add_mcp_server` | `(name, url)` | — | [src](../../../core/services/mcp_registry.py#L28) |
| function | `remove_mcp_server` | `(server_id)` | — | [src](../../../core/services/mcp_registry.py#L40) |

## `core/services/mcp_trust.py`
_MCP-tillid: allowliste + TOFU-pinning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/mcp_trust.py#L35) |
| function | `_save` | `(data)` | — | [src](../../../core/services/mcp_trust.py#L44) |
| function | `is_allowlisted` | `(name)` | — | [src](../../../core/services/mcp_trust.py#L48) |
| function | `allow` | `(name)` | Godkend et servernavn. Idempotent. | [src](../../../core/services/mcp_trust.py#L52) |
| function | `revoke` | `(name)` | Fjern fra allowlisten OG drop pinnen. Idempotent. | [src](../../../core/services/mcp_trust.py#L65) |
| function | `list_trust` | `()` | — | [src](../../../core/services/mcp_trust.py#L80) |
| function | `_sha256_file` | `(path)` | — | [src](../../../core/services/mcp_trust.py#L85) |
| function | `check_pin_stdio` | `(name, command)` | Pin en stdio-servers binær (sti + sha256). Første syn pinner. | [src](../../../core/services/mcp_trust.py#L96) |
| function | `check_pin_http` | `(name, url)` | Pin en HTTP-servers vaert. Første syn pinner. | [src](../../../core/services/mcp_trust.py#L117) |

## `core/services/meaning_significance_signal_tracking.py`
_Meaning/significance signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_meaning_significance_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L39) |
| function | `refresh_runtime_meaning_significance_signal_statuses` | `()` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L65) |
| function | `build_runtime_meaning_significance_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L69) |
| function | `_extract_meaning_significance_candidates` | `(*, run_id)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L73) |
| function | `_build_candidate` | `(*, run_id, focus, relation_continuity, chronicle_brief, chronicle_proposal, executive_contradiction, temporal_promotion, regulation)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L103) |
| function | `_latest_chronicle_brief` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L240) |
| function | `_latest_chronicle_proposal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L252) |
| function | `_latest_executive_contradiction` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L264) |
| function | `_latest_temporal_promotion` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L276) |
| function | `_latest_regulation` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L288) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L300) |
| function | `_derive_meaning_type` | `(*, has_proposal, continuity_state, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L308) |
| function | `_derive_meaning_weight` | `(*, chronicle_weight, continuity_weight, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L324) |
| function | `_derive_status` | `(*, proposal_status, brief_status, continuity_status)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L343) |
| function | `_grounding_mode` | `(*, has_brief, has_proposal, has_contradiction, has_promotion, has_regulation)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L351) |
| function | `_meaning_summary` | `(*, focus, meaning_type, meaning_weight, continuity_alignment, continuity_watchfulness, regulation_pressure)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L373) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L390) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L398) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L409) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L421) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L433) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L450) |
| function | `_meaning_significance_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L493) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L513) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L520) |
| function | `_weight_from_summary` | `(value, *, canonical_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L528) |

## `core/services/memory_breathing.py`
_Memory Breathing — use-strengthens, disuse-fades._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_record_salience` | `(record_id)` | — | [src](../../../core/services/memory_breathing.py#L33) |
| function | `reinforce` | `(record_ids, *, boost=…)` | Raise salience of the given records. | [src](../../../core/services/memory_breathing.py#L45) |
| function | `record_access` | `(record_ids, *, context=…, boost=…)` | Log access and reinforce simultaneously. | [src](../../../core/services/memory_breathing.py#L75) |
| function | `recent_access_stats` | `(*, limit=…)` | Return stats about recent access pattern. | [src](../../../core/services/memory_breathing.py#L97) |
| function | `build_memory_breathing_surface` | `()` | — | [src](../../../core/services/memory_breathing.py#L114) |
| function | `reset_memory_breathing` | `()` | Reset access log (for testing). | [src](../../../core/services/memory_breathing.py#L130) |

## `core/services/memory_consolidation_nudge.py`
_Memory consolidation nudge — unconditional prompt section._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `memory_consolidation_nudge_section` | `()` | Return a short prompt section that fires every turn unconditionally. | [src](../../../core/services/memory_consolidation_nudge.py#L13) |

## `core/services/memory_decay_daemon.py`
_Memory decay daemon — selective forgetting and re-discovery._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_memory_decay_daemon` | `()` | Run daily decay cycle. Returns {decayed, records_updated}. | [src](../../../core/services/memory_decay_daemon.py#L58) |
| function | `hold_fast` | `(record_id)` | Prevent a memory from decaying by resetting its salience to 1.0. | [src](../../../core/services/memory_decay_daemon.py#L96) |
| function | `maybe_rediscover` | `(force=…)` | Possibly surface a near-forgotten memory into the re-discovery buffer. | [src](../../../core/services/memory_decay_daemon.py#L101) |
| function | `get_latest_rediscovery` | `()` | — | [src](../../../core/services/memory_decay_daemon.py#L142) |
| function | `build_memory_decay_surface` | `()` | — | [src](../../../core/services/memory_decay_daemon.py#L146) |

## `core/services/memory_density.py`
_Memory Density — memories with emotional weight, not just facts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/memory_density.py#L41) |
| function | `_density_dir` | `()` | — | [src](../../../core/services/memory_density.py#L45) |
| function | `_load` | `()` | — | [src](../../../core/services/memory_density.py#L49) |
| function | `_save` | `(items)` | — | [src](../../../core/services/memory_density.py#L63) |
| function | `_slug` | `(text)` | — | [src](../../../core/services/memory_density.py#L75) |
| function | `write_density_note` | `(*, title, what_happened, what_it_meant, how_it_felt, what_it_changed, trigger_type=…, metadata=…)` | Record a density memory: what + meaning + feeling + change. | [src](../../../core/services/memory_density.py#L81) |
| function | `confirm_density_note` | `(note_id, *, by=…)` | Increment confirmation count when a density note is re-referenced. | [src](../../../core/services/memory_density.py#L162) |
| function | `list_promotable` | `()` | Return density notes confirmed >= threshold and not yet promoted. | [src](../../../core/services/memory_density.py#L175) |
| function | `mark_promoted` | `(note_id)` | — | [src](../../../core/services/memory_density.py#L185) |
| function | `list_recent` | `(*, limit=…)` | — | [src](../../../core/services/memory_density.py#L196) |
| function | `tick` | `(_seconds=…)` | No periodic work — memory_density is event-driven. | [src](../../../core/services/memory_density.py#L200) |
| function | `build_memory_density_surface` | `()` | — | [src](../../../core/services/memory_density.py#L206) |
| function | `_surface_summary` | `(items, promotable, promoted)` | — | [src](../../../core/services/memory_density.py#L237) |
| function | `build_memory_density_prompt_section` | `()` | — | [src](../../../core/services/memory_density.py#L252) |

## `core/services/memory_emotional_context.py`
_Backwards-compatible shim — emotional memory now lives in emotional_memory_engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize` | `(heading)` | — | [src](../../../core/services/memory_emotional_context.py#L27) |
| function | `capture_mood_for_heading` | `(heading, *, source=…, notes=…)` | Snapshot mood for a MEMORY.md heading. Returns legacy dict shape. | [src](../../../core/services/memory_emotional_context.py#L31) |
| function | `get_mood_for_heading` | `(heading)` | — | [src](../../../core/services/memory_emotional_context.py#L61) |
| function | `enrich_headings_with_mood` | `(text)` | Annotate MEMORY.md headings with [felt: mood, intensity X.X] suffixes. | [src](../../../core/services/memory_emotional_context.py#L85) |

## `core/services/memory_graph.py`
_Lightweight graph memory layer over MEMORY.md and chat history._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/memory_graph.py#L41) |
| function | `_canonical` | `(name)` | — | [src](../../../core/services/memory_graph.py#L78) |
| function | `_upsert_entity` | `(name, kind=…)` | Insert or refresh an entity. Returns its id, or None on failure. | [src](../../../core/services/memory_graph.py#L82) |
| function | `_add_edge` | `(src_id, dst_id, relation, *, evidence=…, weight=…)` | Add a directed edge. Returns True on success. | [src](../../../core/services/memory_graph.py#L119) |
| function | `record_triple` | `(src_name, relation, dst_name, *, src_kind=…, dst_kind=…, evidence=…)` | Convenience: upsert two entities and add the edge between them. | [src](../../../core/services/memory_graph.py#L154) |
| function | `extract_from_text` | `(text, *, max_chars=…)` | Use the cheap LLM lane to extract entity triples from text. | [src](../../../core/services/memory_graph.py#L191) |
| function | `ingest_text` | `(text, *, evidence_label=…)` | Extract triples from text and persist them. Returns count of edges added. | [src](../../../core/services/memory_graph.py#L255) |
| function | `neighbors` | `(name, *, limit=…)` | Return everything directly connected to the named entity. | [src](../../../core/services/memory_graph.py#L273) |
| function | `related_facts` | `(name, *, limit=…)` | Return human-readable sentences for an entity's edges. | [src](../../../core/services/memory_graph.py#L316) |
| function | `stats` | `()` | Quick health check — entity count, edge count, top entities. | [src](../../../core/services/memory_graph.py#L327) |

## `core/services/memory_hierarchy.py`
_Memory hierarchy — explicit hot/warm/cold tiers + recall-before-act._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hot_tier_snapshot` | `()` | In-context-now: signals + active state. | [src](../../../core/services/memory_hierarchy.py#L33) |
| function | `_warm_tier_snapshot` | `(*, query=…)` | Curated, always-available: workspace files + active goals + chronicle excerpt + identity sketch. | [src](../../../core/services/memory_hierarchy.py#L49) |
| function | `_cold_tier_search` | `(*, query, max_results=…)` | Semantic-search across full archive with quality scoring. | [src](../../../core/services/memory_hierarchy.py#L93) |
| function | `recall_before_act` | `(*, query=…, include_cold=…, cold_max=…)` | Compose hot+warm+(optional cold) tier snapshot before an action. | [src](../../../core/services/memory_hierarchy.py#L178) |
| function | `recall_before_act_summary` | `(query=…)` | Compact text summary of recall-before-act for prompt awareness. | [src](../../../core/services/memory_hierarchy.py#L194) |
| function | `_exec_recall_before_act` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L233) |
| function | `_exec_hot_tier` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L244) |
| function | `_exec_warm_tier` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L248) |
| function | `_exec_cold_tier` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L252) |

## `core/services/memory_maintenance_daemon.py`
_Memory maintenance daemon — periodic dedup and health of MEMORY.md._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_memory_md` | `()` | — | [src](../../../core/services/memory_maintenance_daemon.py#L32) |
| function | `tick_memory_maintenance_daemon` | `(now=…)` | Run 12h maintenance cycle on MEMORY.md. | [src](../../../core/services/memory_maintenance_daemon.py#L48) |
| function | `build_memory_maintenance_surface` | `()` | — | [src](../../../core/services/memory_maintenance_daemon.py#L104) |
| function | `_read_memory` | `()` | — | [src](../../../core/services/memory_maintenance_daemon.py#L116) |
| function | `_parse_sections` | `(text)` | Parse MEMORY.md into sections: [{heading, level, content, start_line, end_line}]. | [src](../../../core/services/memory_maintenance_daemon.py#L123) |
| function | `_jaccard` | `(a, b)` | Word-level Jaccard similarity between two strings. | [src](../../../core/services/memory_maintenance_daemon.py#L161) |
| function | `_containment` | `(a, b)` | What fraction of tokens in `a` appear in `b`? (subset check) | [src](../../../core/services/memory_maintenance_daemon.py#L170) |
| function | `_tier_a_auto_merge` | `(sections, text)` | Auto-merge sections with exact or fuzzy-matching headings. | [src](../../../core/services/memory_maintenance_daemon.py#L179) |
| function | `_tier_b_flag_overlaps` | `(sections)` | Flag sections with different headings but overlapping content. | [src](../../../core/services/memory_maintenance_daemon.py#L241) |
| function | `_replace_section_content` | `(heading, level, new_content)` | Replace a section's content in MEMORY.md. | [src](../../../core/services/memory_maintenance_daemon.py#L285) |
| function | `_remove_section` | `(heading)` | Remove a section entirely from MEMORY.md. | [src](../../../core/services/memory_maintenance_daemon.py#L298) |

## `core/services/memory_md_update_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_memory_md_update_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L26) |
| function | `_looks_like_sentence` | `(domain_key)` | A slugified user message ("det-er-fordi-du-prompt-er-rodet") — not a topic. | [src](../../../core/services/memory_md_update_proposal_tracking.py#L52) |
| function | `refresh_runtime_memory_md_update_proposal_statuses` | `()` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L58) |
| function | `build_runtime_memory_md_update_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L94) |
| function | `_extract_memory_md_update_proposals` | `()` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L122) |
| function | `_persist_memory_md_update_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L307) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L376) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L386) |
| function | `_build_proposed_update` | `(*, proposal_type, domain_key, item=…)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L397) |
| function | `_build_proposal_reason` | `(*, proposal_type, source_summary, proposal_confidence)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L409) |
| function | `_build_proposal_confidence` | `(*, source_confidence, proposal_type)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L419) |
| function | `_build_source_anchor` | `(*, source_type, domain_key, support_summary)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L429) |
| function | `_build_status_reason` | `(*, proposal_type, source_status)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L434) |
| function | `_title_suffix` | `(domain_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L448) |
| function | `_domain_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L452) |
| function | `_memory_kind_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L457) |
| function | `_source_anchor_from_support_summary` | `(support_summary)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L469) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L476) |
| function | `_stronger_confidence` | `(left, right)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L486) |
| function | `_rank_confidence` | `(value)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L490) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L494) |

## `core/services/memory_pruning_daemon.py`
_Memory pruning daemon — arkiverer entries med meget lav salience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_memory_pruning_daemon` | `()` | Run pruning cycle if cadence elapsed. Returns stats dict. | [src](../../../core/services/memory_pruning_daemon.py#L53) |
| function | `_prune_brain_entries` | `(now)` | Find brain entries med effektiv salience under tærskel og arkivér dem. | [src](../../../core/services/memory_pruning_daemon.py#L103) |
| function | `_prune_private_brain_records` | `()` | Find private_brain_records med salience under tærskel og arkivér dem. | [src](../../../core/services/memory_pruning_daemon.py#L161) |
| function | `build_memory_pruning_surface` | `()` | — | [src](../../../core/services/memory_pruning_daemon.py#L207) |

## `core/services/memory_recall_engine.py`
_Unified memory recall — bridge across all memory sources with mood-weighting._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_mood` | `()` | — | [src](../../../core/services/memory_recall_engine.py#L75) |
| function | `_mood_keywords_for_boost` | `(mood, threshold=…)` | For each mood dimension above threshold, collect keywords to boost. | [src](../../../core/services/memory_recall_engine.py#L87) |
| function | `_apply_mood_boost` | `(text, base_score, boost_keywords, boost_factor=…)` | — | [src](../../../core/services/memory_recall_engine.py#L97) |
| function | `compute_recall_score` | `(*, query_embedding, record_embedding, created_at, importance=…, recall_freq=…, now=…, config=…)` | Composite quality score for cold-tier memory filtering. | [src](../../../core/services/memory_recall_engine.py#L110) |
| function | `_gather_private_brain_quality` | `(query, limit, quality_threshold=…)` | Embedding-based private brain search with quality scoring. | [src](../../../core/services/memory_recall_engine.py#L188) |
| function | `_gather_failed` | `(source, exc)` | Memory-cluster trace (2026-06-22): en recall-kilde fejlede. FØR sluttede | [src](../../../core/services/memory_recall_engine.py#L297) |
| function | `_gather_workspace` | `(query, limit)` | — | [src](../../../core/services/memory_recall_engine.py#L313) |
| function | `_gather_private_brain` | `(query, limit)` | — | [src](../../../core/services/memory_recall_engine.py#L332) |
| function | `_gather_chronicle` | `(query, limit)` | — | [src](../../../core/services/memory_recall_engine.py#L375) |
| function | `cold_tier_recall` | `(*, query, max_results=…, with_mood=…, quality_threshold=…, include_private_brain=…)` | Cold-tier recall across curated sources + quality-scored private brain. | [src](../../../core/services/memory_recall_engine.py#L409) |
| function | `unified_recall` | `(*, query, sources=…, limit_per_source=…, total_limit=…, with_mood=…)` | Search across all configured memory sources, mood-weighted. | [src](../../../core/services/memory_recall_engine.py#L514) |
| function | `unified_recall_section` | `(query, *, max_results=…)` | Format unified recall as a prompt-awareness section. Optional callsite. | [src](../../../core/services/memory_recall_engine.py#L583) |
| function | `_compute_multi_signal_scores` | `(query, records, recency_fn=…)` | Re-score gathered records with BM25 + entity fusion + embedding. | [src](../../../core/services/memory_recall_engine.py#L602) |
| function | `_observe_recall_quality` | `(top, sources)` | Fase 3 (§23.3 #4): meld recall-KVALITET til Centralen — kun scalar-metadata, aldrig | [src](../../../core/services/memory_recall_engine.py#L667) |
| function | `multi_signal_recall` | `(*, query, sources=…, limit_per_source=…, total_limit=…, with_mood=…, min_score=…)` | Multi-signal recall: BM25 + entity fusion + embedding + recency. | [src](../../../core/services/memory_recall_engine.py#L695) |
| function | `multi_signal_recall_section` | `(query, *, max_results=…)` | Format multi-signal recall as a prompt-awareness section. | [src](../../../core/services/memory_recall_engine.py#L864) |
| function | `_exec_unified_recall` | `(args)` | — | [src](../../../core/services/memory_recall_engine.py#L911) |

## `core/services/memory_recall_telemetry.py`
_Memory recall telemetry — Phase 2 data collection for Lag 11 forgetting._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `emit_recall_empty` | `(*, tool, query, workspace_id=…)` | Publish a memory.recall_empty event. Best-effort — never raises. | [src](../../../core/services/memory_recall_telemetry.py#L38) |
| function | `count_recent_recall_empty` | `(*, hours=…, by_tool=…)` | Aggregate recall-empty events over the last N hours. | [src](../../../core/services/memory_recall_telemetry.py#L65) |
| function | `build_memory_recall_telemetry_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/memory_recall_telemetry.py#L112) |
| function | `_emit_memory_recall_telemetry_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/memory_recall_telemetry.py#L127) |

## `core/services/memory_resurfacing.py`
_Proactive memory resurfacing — pull old MEMORY.md headings back into focus._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_memory_md` | `()` | — | [src](../../../core/services/memory_resurfacing.py#L40) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/memory_resurfacing.py#L48) |
| function | `_normalize` | `(heading)` | — | [src](../../../core/services/memory_resurfacing.py#L66) |
| function | `_list_memory_headings` | `()` | Return [(level_str, heading_text), ...] from MEMORY.md. | [src](../../../core/services/memory_resurfacing.py#L70) |
| function | `_recently_touched_headings` | `()` | Headings touched in the last _FRESH_DAYS days — skip these for resurfacing. | [src](../../../core/services/memory_resurfacing.py#L86) |
| function | `_recently_resurfaced_headings` | `()` | Last N resurfaced headings — don't repeat them. | [src](../../../core/services/memory_resurfacing.py#L104) |
| function | `_content_for_heading` | `(heading)` | Return the content under the matching heading (up to next heading or EOF). | [src](../../../core/services/memory_resurfacing.py#L119) |
| function | `_log_resurfacing` | `(heading, trigger=…)` | — | [src](../../../core/services/memory_resurfacing.py#L135) |
| function | `pick_resurfacing_candidate` | `(*, trigger=…, seed=…)` | Choose a stale heading to surface, log the choice, return its detail. | [src](../../../core/services/memory_resurfacing.py#L150) |
| function | `format_for_prompt` | `(candidate)` | Render a resurfacing candidate as a single soft prompt line. | [src](../../../core/services/memory_resurfacing.py#L201) |

## `core/services/memory_search.py`
_Semantic memory search — embeddings-based search over Jarvis's workspace memory files._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Chunk` | `` | — | [src](../../../core/services/memory_search.py#L32) |
| function | `_workspace_dir` | `()` | Workspace for the current user, falling back to the owner's workspace. | [src](../../../core/services/memory_search.py#L38) |
| function | `_memory_files` | `(ws=…)` | — | [src](../../../core/services/memory_search.py#L52) |
| function | `_file_mtime` | `(path)` | — | [src](../../../core/services/memory_search.py#L71) |
| function | `_chunk_markdown` | `(text, source)` | Split markdown into chunks, tracking the nearest heading. | [src](../../../core/services/memory_search.py#L78) |
| function | `_embed_ollama` | `(texts)` | Embed a list of texts via Ollama. Returns (N, D) array or None on failure. | [src](../../../core/services/memory_search.py#L104) |
| function | `_embed_single` | `(text)` | — | [src](../../../core/services/memory_search.py#L159) |
| function | `_cosine_sim` | `(query_vec, matrix)` | Cosine similarity between query (D,) and matrix (N, D). | [src](../../../core/services/memory_search.py#L171) |
| function | `_tfidf_search` | `(query, chunks, limit)` | Fallback TF-IDF search when Ollama is unavailable. | [src](../../../core/services/memory_search.py#L179) |
| function | `_cache_path` | `(ws=…)` | — | [src](../../../core/services/memory_search.py#L210) |
| function | `_chunk_all_files` | `(files, ws=…)` | Læs + chunk alle memory-filer. HURTIGT — kun fil-I/O, INGEN embedding. | [src](../../../core/services/memory_search.py#L218) |
| function | `_load_cached_vectors` | `(ws=…)` | chunk-tekst → vektor fra den eksisterende cache, til INKREMENTEL reindex. | [src](../../../core/services/memory_search.py#L235) |
| function | `_build_and_cache_index` | `(files, current_mtimes, ws=…)` | Byg indeks og skriv cache. Kaldes KUN fra baggrunds-tråden. | [src](../../../core/services/memory_search.py#L258) |
| function | `_schedule_background_rebuild` | `(files, current_mtimes, ws=…)` | Kør en fuld re-embed i BAGGRUNDEN (fire-and-forget, kun én ad gangen). Så en bruger-søgning | [src](../../../core/services/memory_search.py#L321) |
| function | `_load_or_build_index` | `(ws=…)` | Returnér (chunks, embeddings, mtimes). BLOKERER ALDRIG på et fuldt re-embed: | [src](../../../core/services/memory_search.py#L352) |
| function | `_is_quarantined` | `(text)` | True if a chunk has been marked as retracted/false. | [src](../../../core/services/memory_search.py#L396) |
| function | `_source_matches` | `(chunk_source, sources)` | — | [src](../../../core/services/memory_search.py#L415) |
| function | `search_memory` | `(query, *, limit=…, sources=…, workspace_dir=…)` | Search workspace memory files by semantic similarity. | [src](../../../core/services/memory_search.py#L422) |
| function | `invalidate_index` | `()` | Force index rebuild on next search (call after memory file writes). | [src](../../../core/services/memory_search.py#L498) |
| function | `get_index_stats` | `()` | Return stats about the current index (without rebuilding). | [src](../../../core/services/memory_search.py#L507) |

## `core/services/memory_tattoos.py`
_Memory Tattoos — emotional marks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_tattoo` | `(event, emotion, intensity)` | — | [src](../../../core/services/memory_tattoos.py#L9) |
| function | `describe_tattoo` | `()` | — | [src](../../../core/services/memory_tattoos.py#L19) |
| function | `format_tattoo_for_prompt` | `()` | — | [src](../../../core/services/memory_tattoos.py#L25) |
| function | `reset_memory_tattoos` | `()` | — | [src](../../../core/services/memory_tattoos.py#L31) |
| function | `build_memory_tattoos_surface` | `()` | — | [src](../../../core/services/memory_tattoos.py#L35) |

## `core/services/memory_write_policy.py`
_Memory Write Policy — gating + review queue for inferred memory writes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/memory_write_policy.py#L34) |
| function | `_load_queue` | `()` | — | [src](../../../core/services/memory_write_policy.py#L39) |
| function | `_save_queue` | `(queue)` | — | [src](../../../core/services/memory_write_policy.py#L53) |
| function | `_prune_rate_window` | `()` | — | [src](../../../core/services/memory_write_policy.py#L70) |
| function | `_rate_limit_block` | `()` | — | [src](../../../core/services/memory_write_policy.py#L77) |
| function | `_cooldown_block` | `(key)` | — | [src](../../../core/services/memory_write_policy.py#L84) |
| class | `PolicyDecision` | `` | — | [src](../../../core/services/memory_write_policy.py#L95) |
| function | `evaluate_write` | `(*, key, content, confidence=…, write_reason=…, metadata=…)` | Decide whether to allow, block, or queue this memory candidate. | [src](../../../core/services/memory_write_policy.py#L102) |
| function | `_enqueue_for_review` | `(*, key, content, confidence, write_reason, metadata)` | — | [src](../../../core/services/memory_write_policy.py#L150) |
| function | `list_pending_reviews` | `(*, limit=…)` | — | [src](../../../core/services/memory_write_policy.py#L176) |
| function | `approve_review` | `(item_id, *, decided_by=…)` | — | [src](../../../core/services/memory_write_policy.py#L182) |
| function | `reject_review` | `(item_id, *, decided_by=…)` | — | [src](../../../core/services/memory_write_policy.py#L194) |
| function | `build_memory_write_policy_surface` | `()` | — | [src](../../../core/services/memory_write_policy.py#L206) |
| function | `build_memory_write_policy_prompt_section` | `()` | — | [src](../../../core/services/memory_write_policy.py#L230) |
| function | `_emit_memory_write_policy_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/memory_write_policy.py#L241) |

## `core/services/memory_write_queue.py`
_Memory Write Queue — async write queue for sensory/brain memories._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/memory_write_queue.py#L52) |
| function | `enqueue_write` | `(queue_type, payload, priority=…)` | Enqueue a memory write for async processing. | [src](../../../core/services/memory_write_queue.py#L77) |
| function | `process_queue` | `(batch_size=…)` | Process pending write queue items. Called by the daemon tick. | [src](../../../core/services/memory_write_queue.py#L119) |
| function | `queue_size` | `()` | Return counts by status. | [src](../../../core/services/memory_write_queue.py#L218) |
| function | `build_memory_write_queue_surface` | `()` | Mission Control surface. | [src](../../../core/services/memory_write_queue.py#L240) |
| function | `tick_memory_write_queue_daemon` | `(now=…)` | Daemon tick: process pending writes every 120s. | [src](../../../core/services/memory_write_queue.py#L263) |
| function | `_max_retries_for` | `(queue_type)` | — | [src](../../../core/services/memory_write_queue.py#L303) |
| function | `_process_item` | `(queue_type, payload, retry_count)` | Execute one write. Returns (ok, error_message). | [src](../../../core/services/memory_write_queue.py#L311) |
| function | `_process_sensory` | `(payload, retry_count)` | Process a sensory memory write. | [src](../../../core/services/memory_write_queue.py#L333) |
| function | `_process_brain` | `(payload, retry_count)` | Process a brain entry write. | [src](../../../core/services/memory_write_queue.py#L352) |
| function | `_process_sidecar` | `(payload, retry_count)` | Process a MEMORY.md sidecar: mood capture + graph ingestion. | [src](../../../core/services/memory_write_queue.py#L385) |
| function | `retry_failed` | `(limit=…)` | Reset failed items back to pending for retry. | [src](../../../core/services/memory_write_queue.py#L422) |
| function | `clean_old_done` | `(hours=…)` | Delete 'done' items older than N hours. | [src](../../../core/services/memory_write_queue.py#L446) |

## `core/services/meta_cognition_daemon.py`
_Meta-Cognition Daemon — first-person reflection on own state (Experiment 4: HOT)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_meta_cognition_daemon` | `()` | Run one meta-cognition pass. Returns generated/reason/meta_depth. | [src](../../../core/services/meta_cognition_daemon.py#L26) |
| function | `build_meta_cognition_surface` | `()` | MC surface for meta-cognition experiment. | [src](../../../core/services/meta_cognition_daemon.py#L82) |
| function | `_gather_state` | `()` | Collect cognitive + emotional state for meta-observation input. | [src](../../../core/services/meta_cognition_daemon.py#L108) |
| function | `_call_meta_llm` | `(prompt)` | Call cheap lane (Groq/etc.) first, Ollama fallback. Timeout 15s. | [src](../../../core/services/meta_cognition_daemon.py#L148) |
| function | `_compute_meta_depth` | `(meta_obs, meta_meta_obs)` | Return 2 if meta_meta diverges >70% from meta_obs (Jaccard distance), else 1. | [src](../../../core/services/meta_cognition_daemon.py#L204) |

## `core/services/meta_learning_aggregator.py`
_Meta-læring aggregator — Phase 1 (AGI track #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_in_window` | `(ts_iso, since, until)` | Defensive: parse ts and check if it's within [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L18) |
| function | `_bucket_confidence` | `(c)` | — | [src](../../../core/services/meta_learning_aggregator.py#L31) |
| function | `_confidence_score` | `(value, *, default=…)` | Normalize numeric and world-model textual confidence to 0..1. | [src](../../../core/services/meta_learning_aggregator.py#L39) |
| function | `_prediction_id` | `(prediction)` | — | [src](../../../core/services/meta_learning_aggregator.py#L52) |
| function | `aggregate_world_model` | `(*, since, until)` | Aggregate world-model prediction activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L60) |
| function | `_completion_seconds` | `(rec)` | Seconds between created_at and updated_at; None if either missing. | [src](../../../core/services/meta_learning_aggregator.py#L136) |
| function | `aggregate_plan_revision` | `(*, since, until)` | Aggregate plan-proposal activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L150) |
| function | `aggregate_curiosity` | `(*, since, until)` | Aggregate curiosity-tool activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L222) |
| function | `aggregate_skill_chain_phase2` | `(*, since, until)` | Aggregate skill_chain Phase 2 events in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L282) |
| function | `aggregate_tool_invention` | `(*, since, until)` | Aggregate tool-invention activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L361) |

## `core/services/meta_learning_hypotheses.py`
_Meta-læring Phase 2: hypothesis registration + sample tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create hypothesis + sample tables. | [src](../../../core/services/meta_learning_hypotheses.py#L37) |
| function | `register_hypothesis` | `(*, memo_id, candidate_idx)` | Promote a memo's hypothesis_candidate at index `candidate_idx` to | [src](../../../core/services/meta_learning_hypotheses.py#L79) |
| function | `record_hypothesis_sample` | `(*, hypothesis_id, supports, note=…)` | Append a sample. If the hypothesis has reached sample_size_needed, | [src](../../../core/services/meta_learning_hypotheses.py#L124) |
| function | `list_active_hypotheses` | `(*, limit=…)` | — | [src](../../../core/services/meta_learning_hypotheses.py#L189) |
| function | `format_active_hypotheses_for_awareness` | `()` | Awareness section showing active hypotheses + progress. | [src](../../../core/services/meta_learning_hypotheses.py#L214) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/meta_learning_hypotheses.py#L231) |

## `core/services/meta_learning_retrospective.py`
_Meta-læring retrospective generator — Phase 1 (AGI track #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create learning_memos table + index. | [src](../../../core/services/meta_learning_retrospective.py#L34) |
| function | `_strip_markdown_fence` | `(text)` | — | [src](../../../core/services/meta_learning_retrospective.py#L71) |
| function | `_build_retrospective_prompt` | `(*, period_start, period_end, aggregator_snapshot)` | Build the cheap-lane prompt for weekly retrospective memo. | [src](../../../core/services/meta_learning_retrospective.py#L79) |
| function | `_parse_memo_markdown` | `(text)` | Parse cheap-lane markdown output into narrative + hypothesis_candidates. | [src](../../../core/services/meta_learning_retrospective.py#L123) |
| function | `_persist_memo` | `(*, memo_id, ts, period_start, period_end, narrative, hypothesis_candidates, aggregator_snapshot, model_used)` | Insert a new memo row. Returns memo_id. | [src](../../../core/services/meta_learning_retrospective.py#L199) |
| function | `fetch_latest_unacknowledged_memo` | `()` | Return the most recent memo with acknowledged_at IS NULL, or None. | [src](../../../core/services/meta_learning_retrospective.py#L237) |
| function | `fetch_memo_by_id` | `(memo_id)` | — | [src](../../../core/services/meta_learning_retrospective.py#L256) |
| function | `list_recent_memos` | `(limit=…)` | — | [src](../../../core/services/meta_learning_retrospective.py#L272) |
| function | `acknowledge_memo` | `(memo_id)` | Mark memo as acknowledged. Returns True if a row was updated. | [src](../../../core/services/meta_learning_retrospective.py#L285) |
| function | `_meta_learning_enabled` | `()` | — | [src](../../../core/services/meta_learning_retrospective.py#L303) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/meta_learning_retrospective.py#L310) |
| function | `generate_weekly_retrospective` | `(*, now)` | Generate a weekly retrospective memo for the 7 days ending at `now`. | [src](../../../core/services/meta_learning_retrospective.py#L318) |
| function | `_format_period_for_display` | `(period_start, period_end)` | Render period as 'YYYY-MM-DD to YYYY-MM-DD' for awareness display. | [src](../../../core/services/meta_learning_retrospective.py#L411) |
| function | `format_latest_unacknowledged_memo_for_awareness` | `()` | Render a short teaser for the most recent unacknowledged memo. | [src](../../../core/services/meta_learning_retrospective.py#L421) |

## `core/services/meta_reflection_daemon.py`
_Meta-reflection daemon — cross-signal pattern insight every 30 minutes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_credit_assignment` | `(cross_snapshot)` | Public wrapper over the Lag-1 credit-assignment pass (:func:`_check_outcomes`). | [src](../../../core/services/meta_reflection_daemon.py#L29) |
| function | `tick_meta_reflection_daemon` | `(cross_snapshot, *, skip_event_gate=…, skip_credit=…)` | Generate cross-signal meta-insight if cadence allows. Also checks for | [src](../../../core/services/meta_reflection_daemon.py#L44) |
| function | `_check_outcomes` | `(cross_snapshot)` | Check for unreviewed model_tier and response_style decisions and score them. | [src](../../../core/services/meta_reflection_daemon.py#L103) |
| function | `_expire_decision` | `(decision_id, reason)` | Mark a stale pending decision as expired so it drops from the | [src](../../../core/services/meta_reflection_daemon.py#L189) |
| function | `_get_turns_after` | `(created_at, min_turns=…)` | Get subsequent chat turns after a decision timestamp (any session). | [src](../../../core/services/meta_reflection_daemon.py#L208) |
| function | `_get_next_user_message` | `(created_at)` | Get the first user message after a decision timestamp (any session). | [src](../../../core/services/meta_reflection_daemon.py#L239) |
| function | `_generate_meta_insight` | `(cross_snapshot)` | — | [src](../../../core/services/meta_reflection_daemon.py#L264) |
| function | `_store_meta_insight` | `(insight)` | — | [src](../../../core/services/meta_reflection_daemon.py#L298) |
| function | `get_latest_meta_insight` | `()` | — | [src](../../../core/services/meta_reflection_daemon.py#L330) |
| function | `build_meta_reflection_surface` | `()` | — | [src](../../../core/services/meta_reflection_daemon.py#L334) |

## `core/services/metabolism_state_signal_tracking.py`
_Metabolism-state signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_metabolism_state_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L38) |
| function | `refresh_runtime_metabolism_state_signal_statuses` | `()` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L48) |
| function | `build_runtime_metabolism_state_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L52) |
| function | `_extract_metabolism_state_candidates` | `(*, run_id)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L56) |
| function | `_build_candidate` | `(*, domain_key, run_id, witness, meaning, temperament, self_narrative, chronicle, relation_continuity)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L133) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L249) |
| function | `_metabolism_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L275) |
| function | `_derive_metabolism_state` | `(*, witness_status, chronicle_status, self_narrative_status, active_count, softening_count, fading_count, stale_count)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L297) |
| function | `_derive_metabolism_direction` | `(*, metabolism_state, witness_status, softening_count, fading_count)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L316) |
| function | `_derive_metabolism_weight` | `(*, active_count, carrying_count, stale_count, chronicle_status)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L336) |
| function | `_metabolism_summary` | `(*, focus, metabolism_state, metabolism_direction, metabolism_weight)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L351) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L375) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L382) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L395) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L407) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L418) |

## `core/services/metacognition_signal_tracker.py`
_Metacognition signal tracker — Step E.v1 of meta-evne stack._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L70) |
| function | `_connect` | `()` | — | [src](../../../core/services/metacognition_signal_tracker.py#L90) |
| function | `_split_sentences` | `(text)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L100) |
| function | `_sentence_nouns` | `(sentence)` | Cheap content-word extraction: lowercase alpha tokens, ≥4 chars, | [src](../../../core/services/metacognition_signal_tracker.py#L105) |
| function | `_has_negation` | `(sentence)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L119) |
| function | `score_contradiction` | `(text)` | Detect contradicting sentence pairs within the same response. | [src](../../../core/services/metacognition_signal_tracker.py#L124) |
| function | `score_claim_density` | `(text)` | Claim-bearing sentences / total sentences. Healthy: 0.3–0.7. | [src](../../../core/services/metacognition_signal_tracker.py#L166) |
| function | `record_signals` | `(run_id, text)` | Compute + persist + publish both signals for a completed run. | [src](../../../core/services/metacognition_signal_tracker.py#L187) |
| function | `latest_signals_section` | `(*, window_n=…)` | Return an awareness one-liner ONLY when recent signals are | [src](../../../core/services/metacognition_signal_tracker.py#L229) |
| function | `_listener_loop` | `(_q_unused=…)` | DB-polling listener — same cross-process pattern as | [src](../../../core/services/metacognition_signal_tracker.py#L285) |
| function | `start_metacognition_tracker` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/metacognition_signal_tracker.py#L342) |
| function | `stop_metacognition_tracker` | `()` | — | [src](../../../core/services/metacognition_signal_tracker.py#L359) |

## `core/services/metacognitive_integration.py`
_Metacognitive Integration — the overarching layer that synthesizes all cognitive layers into a coherent self-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/metacognitive_integration.py#L39) |
| function | `_extract_signal_values` | `(cognitive_state)` | Extract normalised signal values from the assembled cognitive state. | [src](../../../core/services/metacognitive_integration.py#L77) |
| function | `compute_coherence` | `(signal_values)` | Compute coherence score (0-1) from signal values. | [src](../../../core/services/metacognitive_integration.py#L198) |
| function | `compute_integration_quality` | `(cognitive_state)` | Compute integration quality — how many layers are active and contributing. | [src](../../../core/services/metacognitive_integration.py#L237) |
| function | `compute_self_assessment` | `(coherence, integration, signal_values)` | Compute metacognitive self-assessment. | [src](../../../core/services/metacognitive_integration.py#L283) |
| function | `get_metacognitive_line` | `(cognitive_state=…)` | Get the metacognitive integration prompt line. | [src](../../../core/services/metacognitive_integration.py#L332) |
| function | `get_metacognitive_detail` | `(cognitive_state=…)` | Get full metacognitive assessment as a dict (for debugging/MC). | [src](../../../core/services/metacognitive_integration.py#L385) |
| function | `_parse_raw_state` | `(raw)` | Parse the raw cognitive state string into a dict. | [src](../../../core/services/metacognitive_integration.py#L417) |
| function | `build_metacognitive_integration_surface` | `()` | — | [src](../../../core/services/metacognitive_integration.py#L494) |
| function | `_emit_integration_event` | `(layer, signal)` | — | [src](../../../core/services/metacognitive_integration.py#L503) |

## `core/services/mirror_engine.py`
_Mirror Engine — compassionate self-reflection during idle time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_mirror_insight` | `(*, idle_hours=…, open_loop_count=…, recent_error_count=…, recent_success_count=…, top_loop_summary=…)` | Generate a deterministic mirror insight. | [src](../../../core/services/mirror_engine.py#L20) |
| function | `build_mirror_surface` | `()` | — | [src](../../../core/services/mirror_engine.py#L56) |
| function | `_deterministic_insight` | `(*, idle_hours, open_loop_count, recent_error_count, recent_success_count, top_loop_summary)` | — | [src](../../../core/services/mirror_engine.py#L65) |

## `core/services/missions_pipeline.py`
_Missions Pipeline — flerfase opgaver med state-machine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MissionError` | `` | — | [src](../../../core/services/missions_pipeline.py#L52) |
| method | `MissionError.__init__` | `(self, code, message)` | — | [src](../../../core/services/missions_pipeline.py#L53) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/missions_pipeline.py#L58) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/missions_pipeline.py#L62) |
| function | `_row_to_mission` | `(row)` | — | [src](../../../core/services/missions_pipeline.py#L107) |
| function | `create_mission` | `(*, title, description=…, goal=…, constraints=…, success_criteria=…, roles=…, metadata=…)` | Create a new mission in 'created' status. | [src](../../../core/services/missions_pipeline.py#L120) |
| function | `get_mission` | `(*, mission_id)` | — | [src](../../../core/services/missions_pipeline.py#L176) |
| function | `transition_mission_state` | `(*, mission_id, new_status, reason=…)` | Transition mission to new status, respecting _ALLOWED_TRANSITIONS. | [src](../../../core/services/missions_pipeline.py#L188) |
| function | `send_mission_message` | `(*, mission_id, role=…, content, metadata=…)` | Post a message on the mission channel. Roles: researcher/implementer/reviewer etc. | [src](../../../core/services/missions_pipeline.py#L258) |
| function | `list_mission_messages` | `(*, mission_id, limit=…)` | — | [src](../../../core/services/missions_pipeline.py#L311) |
| function | `list_missions` | `(*, status=…, limit=…)` | — | [src](../../../core/services/missions_pipeline.py#L331) |
| function | `build_missions_surface` | `()` | — | [src](../../../core/services/missions_pipeline.py#L350) |

## `core/services/model_benchmark.py`
_Rangér modeller på ÆGTE opgaver med facit hentet fra repoet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rod` | `()` | — | [src](../../../core/services/model_benchmark.py#L59) |
| function | `vælg_filer` | `(*, antal=…, rod=…, frø=…)` | Filer der er store nok til at være en rigtig opgave, små nok til at | [src](../../../core/services/model_benchmark.py#L67) |
| function | `facit_for` | `(fil, *, rod=…)` | {funktionsnavn: linjenummer} — hentet fra kilden, ikke fra en liste. | [src](../../../core/services/model_benchmark.py#L91) |
| function | `_nævnte_navne` | `(svar, facit)` | Navne modellen faktisk nævner. Vi leder KUN efter funktionsnavne-agtige | [src](../../../core/services/model_benchmark.py#L106) |
| function | `bedøm_svar` | `(svar, facit)` | Præcision, dækning og linje-nøjagtighed for ét svar. | [src](../../../core/services/model_benchmark.py#L121) |
| function | `opgave_for` | `(fil, *, rod=…)` | Spørgsmålet stilles i den FORM der udløser fejlen: en liste med mange | [src](../../../core/services/model_benchmark.py#L175) |
| function | `kør_benchmark` | `(*, provider, model, antal_filer=…, frø=…, kald=…, rod=…)` | Kør benchmarken for én model. Kaster aldrig. | [src](../../../core/services/model_benchmark.py#L187) |
| function | `gem_kvalitet` | `(*, provider, model, resultat)` | Skriv `kvalitets_score` ved siden af `probe_score` i registret. | [src](../../../core/services/model_benchmark.py#L234) |

## `core/services/model_catalogue_sweep.py`
_Ugentlig gennemgang: hvilke modeller lever, og hvad kan de?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/model_catalogue_sweep.py#L45) |
| function | `_foretræk_gratis` | `(navne)` | `:free` først. En gratis model der virker er mere værd for cheap lane | [src](../../../core/services/model_catalogue_sweep.py#L49) |
| function | `kandidater_for` | `(provider, *, registrerede, fra_api, statiske, maks_nye=…)` | Hvad skal prøves hos denne udbyder? | [src](../../../core/services/model_catalogue_sweep.py#L55) |
| function | `beslut` | `(resultat)` | (skal_være_aktiv, grund). Ren funktion — al politik ét sted. | [src](../../../core/services/model_catalogue_sweep.py#L81) |
| function | `egnet_til_agentarbejde` | `(resultat)` | Explore og andre opgave-agenter må kun få modeller der kan bruge et | [src](../../../core/services/model_catalogue_sweep.py#L107) |
| function | `sweep_provider` | `(provider, *, hent_modeller=…, proev=…, skriv=…, maks_nye=…)` | Gennemgå én udbyder. Returnerer en ændringsrapport. | [src](../../../core/services/model_catalogue_sweep.py#L114) |
| function | `_registrerede_modeller` | `(provider)` | — | [src](../../../core/services/model_catalogue_sweep.py#L197) |
| function | `_hent_modeller_fra_api` | `(provider, profil)` | — | [src](../../../core/services/model_catalogue_sweep.py#L213) |
| function | `_skriv_registret` | `(*, provider, model, aktiv, grund, score, detalje, profil)` | Skriv én models tilstand. Returnerer True hvis noget ÆNDREDE sig. | [src](../../../core/services/model_catalogue_sweep.py#L224) |
| function | `sammendrag` | `(rapporter)` | Én besked til mobilen. Kun ÆNDRINGER — en push der hver uge siger | [src](../../../core/services/model_catalogue_sweep.py#L297) |
| function | `underret_ejeren` | `(besked, *, send=…)` | Kun ejeren. Cheap-lane-helbred er driftsdata om HANS konti og penge — | [src](../../../core/services/model_catalogue_sweep.py#L325) |
| function | `sweep_alle` | `(*, providers=…, underret=…, proev=…, skriv=…)` | Gennemgå hele cheap lane. Returnerer rapporter + den sendte besked. | [src](../../../core/services/model_catalogue_sweep.py#L346) |

## `core/services/model_context.py`
_Per-model context-vinduer + model-bevidst beskeds-trimning (delt kilde)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `model_context_window` | `(provider, model)` | Bedste bud på modellens context-vindue (tokens). 0 = ukendt. | [src](../../../core/services/model_context.py#L33) |
| function | `effective_context_limit` | `(provider, model, compact_threshold)` | Det første loft der rammer: min(modellens vindue, autocompact-tærskel). | [src](../../../core/services/model_context.py#L50) |
| function | `_est_tokens` | `(text)` | — | [src](../../../core/services/model_context.py#L65) |
| function | `fit_messages_to_window` | `(messages, *, provider, model, output_budget=…, tools_reserve=…, safety_margin=…)` | Model-bevidst sikkerhedsnet: drop ÆLDSTE ikke-system-beskeder indtil den | [src](../../../core/services/model_context.py#L69) |

## `core/services/model_pair_resolver.py`
_Findes den valgte model hos den valgte udbyder?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UnknownModelPair` | `` | Modellen findes ikke hos udbyderen — eller navnet er tvetydigt. | [src](../../../core/services/model_pair_resolver.py#L45) |
| function | `_nulstil_cache_for_tests` | `()` | — | [src](../../../core/services/model_pair_resolver.py#L54) |
| function | `_ollama_modeller` | `(base_url=…)` | Ollamas modelnavne. `None` betyder «kunne ikke spørge», ikke «tom». | [src](../../../core/services/model_pair_resolver.py#L58) |
| function | `kandidater` | `(navne, model)` | Hvilke navne på listen kunne `model` mene? | [src](../../../core/services/model_pair_resolver.py#L80) |
| function | `resolve` | `(provider, model, *, base_url=…)` | Returnér (provider, model) med modellen oversat hvis det er entydigt. | [src](../../../core/services/model_pair_resolver.py#L94) |
| function | `resolve_safe` | `(provider, model, *, base_url=…)` | Som `resolve`, men returnerer fejlen frem for at kaste. | [src](../../../core/services/model_pair_resolver.py#L132) |

