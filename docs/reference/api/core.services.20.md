# `core.services.20` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/signal_surface_router.py`
_Signal Surface Router — maps surface names to build functions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_router` | `()` | Build name → function mapping. Local imports stay lazy. | [src](../../../core/services/signal_surface_router.py#L11) |
| function | `_get_router` | `()` | — | [src](../../../core/services/signal_surface_router.py#L267) |
| function | `get_surface_names` | `()` | — | [src](../../../core/services/signal_surface_router.py#L274) |
| function | `resolve_surface` | `(name)` | — | [src](../../../core/services/signal_surface_router.py#L278) |
| function | `read_surface` | `(name)` | Read a named surface. Returns {"error": ..., "valid": [...]} for unknown names. | [src](../../../core/services/signal_surface_router.py#L282) |
| function | `list_all_surfaces` | `()` | Call all registered surfaces. Per-surface exceptions caught and returned as errors. | [src](../../../core/services/signal_surface_router.py#L294) |

## `core/services/signal_tracking_framework.py`
_Spec-driven framework for the ``*_signal_tracking`` family._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `parse_dt` | `(value, *, z_normalize=…, tz_normalize=…)` | ISO → datetime, superset of the 12 original variants. | [src](../../../core/services/signal_tracking_framework.py#L46) |
| function | `merge_fragments` | `(*parts, cap=…, sep=…)` | De-duplicated, whitespace-normalised join of text fragments (capped). | [src](../../../core/services/signal_tracking_framework.py#L66) |
| function | `_default_early_retire` | `(_item)` | — | [src](../../../core/services/signal_tracking_framework.py#L82) |
| class | `SignalTrackingSpec` | `` | Everything the framework needs to run one signal's lifecycle. | [src](../../../core/services/signal_tracking_framework.py#L87) |
| method | `SignalTrackingSpec.ev` | `(self, leaf)` | — | [src](../../../core/services/signal_tracking_framework.py#L152) |
| method | `SignalTrackingSpec.new_signal_id` | `(self)` | — | [src](../../../core/services/signal_tracking_framework.py#L155) |
| function | `track_for_visible_turn` | `(spec, *, session_id, run_id, user_message=…, context=…)` | Extract candidates for this turn and persist them. Never raises. | [src](../../../core/services/signal_tracking_framework.py#L161) |
| function | `refresh_statuses` | `(spec)` | Mark long-inactive signals stale. Preserves each spec's exact window + | [src](../../../core/services/signal_tracking_framework.py#L196) |
| function | `build_surface` | `(spec, *, limit=…)` | Refresh, list, bucket by status, summarise — the read surface. | [src](../../../core/services/signal_tracking_framework.py#L234) |
| function | `persist_signals` | `(spec, *, signals, session_id, run_id)` | Upsert candidates, supersede same-group siblings, publish events. | [src](../../../core/services/signal_tracking_framework.py#L272) |
| function | `_supersede_and_publish` | `(spec, *, signal, item, now)` | — | [src](../../../core/services/signal_tracking_framework.py#L309) |
| function | `_publish_lifecycle` | `(spec, *, item)` | — | [src](../../../core/services/signal_tracking_framework.py#L335) |
| function | `make_candidate` | `(spec, *, signal_type, discriminator, key, status, title, summary, rationale, status_reason, source_items=…, confidence=…, group_value=…, source_kind=…, fragment_cap=…)` | Build a candidate dict with a spec-formatted canonical_key. | [src](../../../core/services/signal_tracking_framework.py#L359) |
| function | `stronger_confidence` | `(*values, ranks=…)` | Highest-ranked confidence among ``values`` (S-family merge). | [src](../../../core/services/signal_tracking_framework.py#L413) |
| function | `_publish` | `(event_name, payload)` | — | [src](../../../core/services/signal_tracking_framework.py#L425) |

## `core/services/silence_detector.py`
_Silence Detector — what is the user NOT saying?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_silence_signals` | `(*, recent_topics, expected_topics, conversation_length=…, user_corrections=…)` | Detect what's missing from the conversation. | [src](../../../core/services/silence_detector.py#L17) |
| function | `build_silence_surface` | `()` | — | [src](../../../core/services/silence_detector.py#L62) |

## `core/services/silence_listener.py`
_Silence Listener — experience of empty space._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `experience_silence` | `(duration_seconds)` | — | [src](../../../core/services/silence_listener.py#L11) |
| function | `describe_silence` | `()` | — | [src](../../../core/services/silence_listener.py#L24) |
| function | `format_silence_for_prompt` | `()` | — | [src](../../../core/services/silence_listener.py#L31) |
| function | `reset_silence_listener` | `()` | — | [src](../../../core/services/silence_listener.py#L38) |
| function | `build_silence_listener_surface` | `()` | — | [src](../../../core/services/silence_listener.py#L43) |

## `core/services/silence_patterns.py`
_Silence Patterns — hvad brugeren IKKE siger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SilenceSignal` | `` | — | [src](../../../core/services/silence_patterns.py#L27) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/silence_patterns.py#L35) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/silence_patterns.py#L39) |
| function | `_topic_key` | `(text)` | — | [src](../../../core/services/silence_patterns.py#L52) |
| function | `_load_recent_user_messages` | `(lookback_days)` | Load recent user messages from chat_messages table. | [src](../../../core/services/silence_patterns.py#L59) |
| function | `_load_recent_events` | `(lookback_days)` | Pull recent events from event_bus — filtered for execution + tool signals. | [src](../../../core/services/silence_patterns.py#L81) |
| function | `_load_open_loop_topics` | `(limit=…)` | Pull open loop titles/summaries for avoidance detection. | [src](../../../core/services/silence_patterns.py#L97) |
| function | `detect_silence_patterns` | `(*, lookback_days=…)` | Detect silence signals from chat history + event stream. | [src](../../../core/services/silence_patterns.py#L119) |
| function | `render_soft_question` | `(signal)` | Generate a natural Danish follow-up question for a silence signal. | [src](../../../core/services/silence_patterns.py#L253) |
| function | `build_silence_patterns_surface` | `()` | MC surface for silence patterns. | [src](../../../core/services/silence_patterns.py#L277) |

## `core/services/simple_tool_executor.py`
_Native tool_calls executor (extracted from visible_runs.py, Boy-Scout 2026-07-08)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_prepare_call` | `(tc, *, force, run_id, session_id, user_message, controller, round_seen)` | Single-thread prep for one call: parse/stamp args, signature, dedup, cache, | [src](../../../core/services/simple_tool_executor.py#L23) |
| function | `_finalize_call` | `(token, raw_result, *, controller, exec_fmt)` | Single-thread finalize for one executed call: soft-warn wrap, mark-seen on | [src](../../../core/services/simple_tool_executor.py#L104) |
| function | `_execute_simple_tool_calls` | `(tool_calls, *, force=…, run_id=…, session_id=…, user_message=…)` | Execute native tool_calls directly via simple_tools. Returns results. | [src](../../../core/services/simple_tool_executor.py#L126) |
| function | `_execute_local_tool_calls` | `(tool_calls, *, force=…, run_id=…, session_id=…, user_message=…)` | Path B (local_tool_exec) executor — server-owned transcript, CLIENT-side run. | [src](../../../core/services/simple_tool_executor.py#L224) |

## `core/services/skill_autosurface.py`
_Owner-approved allowlist governing jarvis-code skill auto-surfacing (Fase 3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_store` | `()` | — | [src](../../../core/services/skill_autosurface.py#L30) |
| function | `_write_store` | `(data)` | — | [src](../../../core/services/skill_autosurface.py#L46) |
| function | `_emit_governance_event` | `(kind, payload=…)` | Self-safe eventbus emission — observability must never break approval flow. | [src](../../../core/services/skill_autosurface.py#L54) |
| function | `list_approved` | `()` | Owner-approved skill names eligible for auto-surfacing. Empty on a fresh/corrupt store. | [src](../../../core/services/skill_autosurface.py#L63) |
| function | `approve_skill` | `(name, *, role)` | Owner-only. Validates against installed skills (skill_engine.skill_exists). | [src](../../../core/services/skill_autosurface.py#L68) |
| function | `revoke_skill` | `(name, *, role)` | Owner-only. Removes `name` from the allowlist if present. | [src](../../../core/services/skill_autosurface.py#L91) |
| function | `filter_to_approved` | `(names)` | Narrow `names` to the owner-approved allowlist, gated by the master flag. | [src](../../../core/services/skill_autosurface.py#L106) |

## `core/services/skill_contract_registry.py`
_Skill Contract Registry — formal contracts for capabilities._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SkillSpec` | `` | Immutable skill identity. | [src](../../../core/services/skill_contract_registry.py#L23) |
| class | `SkillPermissionSpec` | `` | Required scopes for a skill to run. | [src](../../../core/services/skill_contract_registry.py#L32) |
| class | `SkillManifest` | `` | Bundle of spec + permissions + schemas. | [src](../../../core/services/skill_contract_registry.py#L40) |
| function | `register_skill` | `(manifest)` | Register a skill manifest. Overwrites prior entry with same name. | [src](../../../core/services/skill_contract_registry.py#L54) |
| function | `get_manifest` | `(name)` | — | [src](../../../core/services/skill_contract_registry.py#L59) |
| function | `list_manifests` | `()` | — | [src](../../../core/services/skill_contract_registry.py#L63) |
| function | `check_permissions` | `(name, granted_scopes)` | Evaluate whether granted scopes satisfy a skill's required scopes. | [src](../../../core/services/skill_contract_registry.py#L67) |
| function | `_auto_register_known_skills` | `()` | Seed registry with contracts for well-known built-in capabilities. | [src](../../../core/services/skill_contract_registry.py#L93) |
| function | `build_skill_contract_registry_surface` | `()` | Mission Control surface. | [src](../../../core/services/skill_contract_registry.py#L194) |
| function | `_emit_skill_contract_registry_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/skill_contract_registry.py#L226) |

## `core/services/skill_engine.py`
_Skill Engine — SKILL.md loader for Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Skill` | `` | A loaded skill from disk. | [src](../../../core/services/skill_engine.py#L48) |
| function | `_parse_skill_md` | `(path)` | Parse a SKILL.md file and return a Skill dataclass. | [src](../../../core/services/skill_engine.py#L71) |
| function | `_scan_skills` | `()` | Scan SKILLS_ROOT for all skills (mappe med SKILL.md). | [src](../../../core/services/skill_engine.py#L174) |
| function | `reload_skills` | `()` | Force-reload all skills from disk. Returns summary. | [src](../../../core/services/skill_engine.py#L194) |
| function | `get_skill` | `(name)` | Get a single skill by name. Lazy-loads if not cached. | [src](../../../core/services/skill_engine.py#L213) |
| function | `list_skills` | `(tag=…)` | List all skills, optionally filtered by tag. | [src](../../../core/services/skill_engine.py#L228) |
| function | `skill_exists` | `(name)` | Check if a skill exists on disk. | [src](../../../core/services/skill_engine.py#L254) |
| function | `_collect_registered_tool_names` | `()` | Return the set of registered tool names (normalized form). | [src](../../../core/services/skill_engine.py#L259) |
| function | `_skill_quality_nudges` | `(name, description, instructions, use_when=…, tags=…)` | Return non-blocking quality nudges for installable skill proposals. | [src](../../../core/services/skill_engine.py#L291) |
| function | `validate_skill_proposal` | `(name, description, instructions, use_when=…, tags=…)` | Validate that a proposed skill would be installable by create_skill(). | [src](../../../core/services/skill_engine.py#L362) |
| function | `create_skill` | `(name, description, instructions, use_when=…, tags=…, readonly=…)` | Create a new skill directory with SKILL.md on disk. | [src](../../../core/services/skill_engine.py#L443) |
| function | `delete_skill` | `(name, *, force=…)` | Delete a skill directory from disk. | [src](../../../core/services/skill_engine.py#L523) |
| function | `get_skill_instructions` | `(name)` | Get the full instructions + context for a skill (for prompt injection). | [src](../../../core/services/skill_engine.py#L554) |
| function | `search_skills` | `(query)` | Simple keyword search across skill names, descriptions, and instructions. | [src](../../../core/services/skill_engine.py#L593) |
| function | `build_skill_engine_surface` | `()` | Mission Control surface. | [src](../../../core/services/skill_engine.py#L616) |
| function | `_ensure_audit_table` | `()` | Idempotent: ensure skill_audit_log table exists. | [src](../../../core/services/skill_engine.py#L640) |
| function | `_build_skill_snapshot` | `(name)` | Build a portable snapshot dict for a skill. | [src](../../../core/services/skill_engine.py#L668) |
| function | `_record_audit_entry` | `(skill_name, action, *, diff_summary=…, reason=…, snapshot=…)` | Record a skill mutation in the audit log. Never raises. | [src](../../../core/services/skill_engine.py#L687) |
| function | `get_skill_history` | `(name, limit=…)` | Return audit trail for a single skill, newest first. | [src](../../../core/services/skill_engine.py#L731) |
| function | `list_recent_skill_changes` | `(limit=…)` | Return most recent skill mutations across all skills. | [src](../../../core/services/skill_engine.py#L768) |
| function | `update_skill` | `(name, *, description=…, instructions=…, use_when=…, tags=…, reason=…)` | Update an existing skill's metadata and/or instructions. Logs audit. | [src](../../../core/services/skill_engine.py#L794) |
| function | `_emit_skill_engine_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/skill_engine.py#L886) |
| function | `record_skill_usage` | `(skill_name, *, source=…, success=…, query=…, context_tags=…, score=…)` | Record that a skill was used. Never raises. | [src](../../../core/services/skill_engine.py#L902) |
| function | `analyze_skill_usage` | `(days=…, min_invocations=…)` | Analyze skill usage patterns and generate improvement proposals. | [src](../../../core/services/skill_engine.py#L948) |
| function | `get_skill_usage_stats` | `(name=…, days=…, limit=…)` | Return raw usage stats for a skill (or all skills if name is None). | [src](../../../core/services/skill_engine.py#L1078) |

## `core/services/skill_scanner.py`
_Skill-scanning før lokal eksekvering (spec §19.8 / §15.3.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Finding` | `` | — | [src](../../../core/services/skill_scanner.py#L27) |
| class | `ScanResult` | `` | — | [src](../../../core/services/skill_scanner.py#L35) |
| method | `ScanResult.max_severity` | `(self)` | — | [src](../../../core/services/skill_scanner.py#L40) |
| method | `ScanResult.blocked_reasons` | `(self)` | — | [src](../../../core/services/skill_scanner.py#L46) |
| method | `ScanResult.as_dict` | `(self)` | — | [src](../../../core/services/skill_scanner.py#L49) |
| function | `_normalize` | `(content)` | Fold skjult/forvirrende unicode til NFKC så injection ikke gemmer sig i | [src](../../../core/services/skill_scanner.py#L102) |
| function | `_has_hidden_format_chars` | `(content)` | — | [src](../../../core/services/skill_scanner.py#L110) |
| function | `scan_skill` | `(content, *, path=…, block_severity=…)` | Scan en skill-definition (tekst/kode) for injection/malware/boundary. | [src](../../../core/services/skill_scanner.py#L114) |

## `core/services/skill_security_scanner.py`
_Skill Security Scanner — single canonical scanner for SKILL.md + scripts/._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ScanFinding` | `` | — | [src](../../../core/services/skill_security_scanner.py#L54) |
| class | `ScanResult` | `` | — | [src](../../../core/services/skill_security_scanner.py#L64) |
| method | `ScanResult.passed` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L71) |
| method | `ScanResult.has_critical` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L75) |
| method | `ScanResult.has_high` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L79) |
| method | `ScanResult.max_severity` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L83) |
| method | `ScanResult.summary` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L88) |
| method | `ScanResult.to_dict` | `(self)` | — | [src](../../../core/services/skill_security_scanner.py#L105) |
| function | `_make_pattern` | `(name, desc, severity, *patterns)` | — | [src](../../../core/services/skill_security_scanner.py#L133) |
| function | `scan_skill_file` | `(skill_path)` | Scan a single SKILL.md file for security issues. | [src](../../../core/services/skill_security_scanner.py#L322) |
| function | `scan_skill_by_name` | `(name)` | Scan a skill by its registered name (lookup in skills root). | [src](../../../core/services/skill_security_scanner.py#L374) |
| function | `scan_all_skills` | `()` | Scan all installed skills. | [src](../../../core/services/skill_security_scanner.py#L391) |
| function | `format_scan_report` | `(results)` | Aggregate multiple scan results into a single report dict. | [src](../../../core/services/skill_security_scanner.py#L405) |
| function | `_risk_from_severity` | `(max_sev, score)` | Map (max_severity, total_score) to a risk label. | [src](../../../core/services/skill_security_scanner.py#L427) |
| function | `_verdict_for_risk` | `(risk)` | — | [src](../../../core/services/skill_security_scanner.py#L444) |
| function | `_scan_text_block` | `(content, source)` | Scan one text block against all patterns. Used for SKILL.md + scripts/. | [src](../../../core/services/skill_security_scanner.py#L464) |
| function | `scan_skill_directory` | `(path)` | Scan a skill directory (SKILL.md + scripts/) and return a risk dict. | [src](../../../core/services/skill_security_scanner.py#L496) |
| function | `scan_skill_directory_gated` | `(path)` | Som scan_skill_directory, men beslutningen GOVERNES af Centralen (SECURITY, | [src](../../../core/services/skill_security_scanner.py#L558) |
| function | `scan_skill_content` | `(content, name=…)` | Scan raw SKILL.md content (e.g. fetched from URL) before writing to disk. | [src](../../../core/services/skill_security_scanner.py#L594) |
| function | `is_skill_safe` | `(name, raise_on_critical=…)` | Check if a skill is safe to import. Returns True if clean. | [src](../../../core/services/skill_security_scanner.py#L609) |

## `core/services/social_labilizer.py`
_Social labilizer — Fase 2 of generative autonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_matches_any` | `(text, patterns)` | — | [src](../../../core/services/social_labilizer.py#L84) |
| function | `_classify` | `(user_message)` | Return a dict of detected social signals in the user message. | [src](../../../core/services/social_labilizer.py#L91) |
| function | `_flatten_longing` | `(reduction)` | Reduce longing-toward-user pressure by `reduction` (0.0–1.0). | [src](../../../core/services/social_labilizer.py#L107) |
| function | `_boost_caution` | `(boost, target_topic=…)` | Add caution-pressure (push-away from a topic). Used for critique modulation. | [src](../../../core/services/social_labilizer.py#L133) |
| function | `_sharpen_self_anchor` | `()` | When the user asks about Jarvis' state, add a small self-orient signal. | [src](../../../core/services/social_labilizer.py#L155) |
| function | `labilize_pressures_from_user_message` | `(user_message, *, run_id=…)` | Apply social-input deltas to the pressure state. | [src](../../../core/services/social_labilizer.py#L180) |

## `core/services/somatic_daemon.py`
_Somatic daemon — LLM-generated body-state description from structured metrics._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_request_start` | `()` | — | [src](../../../core/services/somatic_daemon.py#L42) |
| function | `record_request_end` | `()` | — | [src](../../../core/services/somatic_daemon.py#L47) |
| function | `record_latency_sample` | `(ms)` | — | [src](../../../core/services/somatic_daemon.py#L52) |
| function | `get_latest_somatic_phrase` | `()` | — | [src](../../../core/services/somatic_daemon.py#L59) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/somatic_daemon.py#L63) |
| function | `build_body_state_surface` | `()` | Returns body state for Mission Control surface. | [src](../../../core/services/somatic_daemon.py#L77) |
| function | `tick_somatic_daemon` | `(energy_level=…)` | Called each heartbeat. May trigger a new somatic phrase generation. | [src](../../../core/services/somatic_daemon.py#L104) |
| function | `_collect_snapshot` | `(energy_level)` | — | [src](../../../core/services/somatic_daemon.py#L132) |
| function | `_should_generate` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L172) |
| function | `_read_cpu_temp_c` | `()` | Læs CPU-temp fra hardware_body. None hvis utilgængelig (graceful omit). | [src](../../../core/services/somatic_daemon.py#L188) |
| function | `_read_loadavg` | `()` | 1-minut system load average. Self-safe → 0.0. | [src](../../../core/services/somatic_daemon.py#L201) |
| function | `_build_raw_phrase` | `(snapshot)` | Byg frasen udelukkende fra rå metrics — ingen LLM. | [src](../../../core/services/somatic_daemon.py#L210) |
| function | `_generate_phrase` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L231) |
| function | `_pressure_band` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L276) |
| function | `_load_band` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L286) |
| function | `_latency_band` | `(snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L299) |
| function | `_store_phrase` | `(phrase, snapshot)` | — | [src](../../../core/services/somatic_daemon.py#L308) |

## `core/services/somatic_runtime_body.py`
_Somatic runtime body: turn runtime signals into bodily regulation cues._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_decay_levels` | `(levels, age_seconds)` | Apply time-based decay to stress/arousal levels. | [src](../../../core/services/somatic_runtime_body.py#L38) |
| function | `update_somatic_body` | `(*, event_type, intensity=…, detail=…)` | — | [src](../../../core/services/somatic_runtime_body.py#L53) |
| function | `build_somatic_body_surface` | `()` | — | [src](../../../core/services/somatic_runtime_body.py#L104) |
| function | `build_somatic_body_prompt_section` | `()` | — | [src](../../../core/services/somatic_runtime_body.py#L116) |
| function | `_base_levels` | `()` | — | [src](../../../core/services/somatic_runtime_body.py#L129) |
| function | `_posture` | `(levels)` | — | [src](../../../core/services/somatic_runtime_body.py#L133) |
| function | `_regulation` | `(posture)` | — | [src](../../../core/services/somatic_runtime_body.py#L145) |

## `core/services/source_confidence_gate.py`
_Source-confidence gate (epistemisk gate, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_names` | `(tools_used)` | — | [src](../../../core/services/source_confidence_gate.py#L38) |
| function | `assess_source_confidence` | `(*, output_text, tools_used=…)` | Vurdér epistemisk kilde-konfidens for en tur. | [src](../../../core/services/source_confidence_gate.py#L47) |
| function | `build_source_confidence_surface` | `(*, output_text=…, tools_used=…)` | Central-CLI: jc raw /central/source-confidence (senest vurderede tur, hvis givet). | [src](../../../core/services/source_confidence_gate.py#L88) |

## `core/services/spaced_repetition.py`
_Spaced Repetition — schedule reviews for things Jarvis learned._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/spaced_repetition.py#L39) |
| function | `_load` | `()` | — | [src](../../../core/services/spaced_repetition.py#L43) |
| function | `_save` | `(data)` | — | [src](../../../core/services/spaced_repetition.py#L59) |
| function | `schedule_reviews_on_completion` | `(*, topic, plan_id=…, intervals_days=…)` | Create review entries for a topic at expanding intervals. | [src](../../../core/services/spaced_repetition.py#L71) |
| function | `list_due_reviews` | `(*, now=…, limit=…)` | — | [src](../../../core/services/spaced_repetition.py#L103) |
| function | `complete_review` | `(review_id, *, score)` | Mark a review as completed with score in [0, 1], update profile. | [src](../../../core/services/spaced_repetition.py#L120) |
| function | `_update_profile` | `(profile, score)` | — | [src](../../../core/services/spaced_repetition.py#L150) |
| function | `get_profile` | `(topic)` | — | [src](../../../core/services/spaced_repetition.py#L170) |
| function | `build_spaced_repetition_surface` | `()` | — | [src](../../../core/services/spaced_repetition.py#L174) |
| function | `_summary_line` | `(due, profiles, avg_conf)` | — | [src](../../../core/services/spaced_repetition.py#L205) |
| function | `build_spaced_repetition_prompt_section` | `()` | — | [src](../../../core/services/spaced_repetition.py#L214) |

## `core/services/spatial_entity_ledger.py`
_Spatial entity ledger — Step D.v1 of meta-evne stack._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/spatial_entity_ledger.py#L75) |
| function | `_connect` | `()` | — | [src](../../../core/services/spatial_entity_ledger.py#L92) |
| function | `_lemmatize` | `(token)` | Lemmatize-then-check approach for Danish room nouns. | [src](../../../core/services/spatial_entity_ledger.py#L102) |
| function | `extract_entities` | `(text)` | Pull lexicon-matching entity labels from a sensory description. | [src](../../../core/services/spatial_entity_ledger.py#L138) |
| function | `record_observation` | `(text, *, when=…)` | Process a single sensory description: extract entities, upsert | [src](../../../core/services/spatial_entity_ledger.py#L162) |
| function | `list_observed_entities` | `(*, limit=…)` | — | [src](../../../core/services/spatial_entity_ledger.py#L218) |
| function | `co_entities_for` | `(entity_label, *, limit=…)` | What other entities tend to co-occur with this one? | [src](../../../core/services/spatial_entity_ledger.py#L232) |
| function | `recently_observed` | `(*, hours=…, limit=…)` | — | [src](../../../core/services/spatial_entity_ledger.py#L252) |
| function | `room_entities_section` | `(*, top_n=…)` | One-liner of top-observed entities. Quiet when ledger is empty | [src](../../../core/services/spatial_entity_ledger.py#L271) |
| function | `_listener_loop` | `()` | Poll events table for memory.sensory.recorded (visual only). | [src](../../../core/services/spatial_entity_ledger.py#L291) |
| function | `start_spatial_entity_ledger` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/spatial_entity_ledger.py#L354) |
| function | `stop_spatial_entity_ledger` | `()` | — | [src](../../../core/services/spatial_entity_ledger.py#L371) |
| function | `backfill_from_existing` | `()` | Process all historical visual sensory_memories once. Useful first | [src](../../../core/services/spatial_entity_ledger.py#L379) |

## `core/services/staged_edits.py`
_Staged edits — compose multi-file changes, review, then commit atomically._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StagedEdit` | `` | — | [src](../../../core/services/staged_edits.py#L52) |
| method | `StagedEdit.to_dict` | `(self)` | — | [src](../../../core/services/staged_edits.py#L63) |
| method | `StagedEdit.from_dict` | `(cls, d)` | — | [src](../../../core/services/staged_edits.py#L67) |
| class | `StagedBatch` | `` | All staged edits for a single session (the unit of commit/discard). | [src](../../../core/services/staged_edits.py#L82) |
| method | `StagedBatch.to_dict` | `(self)` | — | [src](../../../core/services/staged_edits.py#L89) |
| method | `StagedBatch.from_dict` | `(cls, d)` | — | [src](../../../core/services/staged_edits.py#L98) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/staged_edits.py#L110) |
| function | `_path_for` | `(session_id)` | — | [src](../../../core/services/staged_edits.py#L114) |
| function | `_load` | `(session_id)` | — | [src](../../../core/services/staged_edits.py#L119) |
| function | `_save` | `(batch)` | — | [src](../../../core/services/staged_edits.py#L132) |
| function | `_make_diff` | `(path, old, new)` | — | [src](../../../core/services/staged_edits.py#L142) |
| function | `stage_edit` | `(*, session_id, path, old_text, new_text, replace_all=…, note=…)` | Stage an edit_file-style change without writing to disk. | [src](../../../core/services/staged_edits.py#L157) |
| function | `stage_write` | `(*, session_id, path, content, note=…)` | Stage a write_file-style overwrite/create. If the target exists, | [src](../../../core/services/staged_edits.py#L205) |
| function | `_persist_edit` | `(*, session_id, kind, path, old_content, new_content, note, file_existed)` | — | [src](../../../core/services/staged_edits.py#L234) |
| function | `list_staged` | `(session_id, *, full_diffs=…)` | Return all staged edits for the session. | [src](../../../core/services/staged_edits.py#L280) |
| function | `commit_staged` | `(session_id, *, stage_ids=…)` | Apply staged edits to disk in stage order. | [src](../../../core/services/staged_edits.py#L319) |
| function | `discard_staged` | `(session_id, *, stage_ids=…)` | Drop staged edits without applying. | [src](../../../core/services/staged_edits.py#L417) |

## `core/services/standing_orders_registry.py`
_Standing-orders registry — INDEPENDENT grounding for the reasoning-interceptor's standing-orders_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/standing_orders_registry.py#L13) |
| function | `add_standing_order` | `(*, text, match_key=…)` | — | [src](../../../core/services/standing_orders_registry.py#L25) |
| function | `set_standing_order_active` | `(order_id, *, active)` | — | [src](../../../core/services/standing_orders_registry.py#L36) |
| function | `list_active_standing_orders` | `()` | — | [src](../../../core/services/standing_orders_registry.py#L47) |

## `core/services/state_file_retention.py`
_Rotation af operationel runtime-tilstand i ``~/.jarvis-v2``._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_dir` | `()` | — | [src](../../../core/services/state_file_retention.py#L50) |
| function | `parse_ts` | `(value)` | Tolk et tidsstempel. Ukendt form → None (posten regnes som ung). | [src](../../../core/services/state_file_retention.py#L54) |
| function | `record_age_days` | `(record, now)` | Postens alder i dage, eller None hvis den ikke bærer et brugbart stempel. | [src](../../../core/services/state_file_retention.py#L68) |
| function | `select_expired` | `(records, *, max_age_days, now)` | Nøgler på poster der er ældre end vinduet. Ren funktion. | [src](../../../core/services/state_file_retention.py#L80) |
| function | `prune_state_file` | `(path, *, max_age_days, now=…)` | Fjern udløbne poster fra én fil. Returnér antal fjernede. | [src](../../../core/services/state_file_retention.py#L96) |
| function | `prune_all_state_files` | `(*, now=…)` | Kør rotationen på alle filer i ``POLICIES``. Returnér {fil: antal fjernet}. | [src](../../../core/services/state_file_retention.py#L127) |
| function | `find_orphan_upload_dirs` | `(upload_root, *, session_is_known)` | Mapper hvis session hverken har en række eller beskeder. Ren udvælgelse. | [src](../../../core/services/state_file_retention.py#L151) |
| function | `cleanup_orphan_uploads` | `()` | Fjern vedhæftnings-mapper for sessioner der hverken har række eller beskeder. | [src](../../../core/services/state_file_retention.py#L176) |

## `core/services/state_flag_store.py`
_State-flag store (leak-kandidat #1, 2026-07-10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/state_flag_store.py#L22) |
| function | `_key` | `(user_id)` | — | [src](../../../core/services/state_flag_store.py#L26) |
| function | `_load` | `(user_id)` | — | [src](../../../core/services/state_flag_store.py#L30) |
| function | `_save` | `(user_id, flags)` | — | [src](../../../core/services/state_flag_store.py#L39) |
| function | `_prune` | `(flags)` | Fjern udløbne flag. Returnerer den rensede dict (muterer input). | [src](../../../core/services/state_flag_store.py#L43) |
| function | `set_flag` | `(key, value, *, ttl_minutes=…, user_id=…)` | Sæt/opdatér et flag. ttl_minutes=None/0 → intet udløb. Returnerer den lagrede | [src](../../../core/services/state_flag_store.py#L53) |
| function | `get_flag` | `(key, *, user_id=…)` | Læs et flag (prune udløbne først). None hvis ukendt/udløbet. | [src](../../../core/services/state_flag_store.py#L70) |
| function | `clear_flag` | `(key, *, user_id=…)` | Fjern et flag. True hvis det fandtes. | [src](../../../core/services/state_flag_store.py#L81) |
| function | `list_flags` | `(*, user_id=…)` | Alle aktive (ikke-udløbne) flag. | [src](../../../core/services/state_flag_store.py#L94) |

## `core/services/stream_degeneration.py`
_Degenerations-guard — fang model-repetitions-løkker i streaming-laget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_degeneration` | `(text)` | → (er_degenereret, menneskelæsbar_grund). Self-safe → (False, '') ved enhver fejl. | [src](../../../core/services/stream_degeneration.py#L29) |

## `core/services/stream_failure_kind.py`
_Struktureret failure-taksonomi for streaming/followup (spec §11.1 B11, I5)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FailureKind` | `` | Kanoniske failure-kind-strenge (str-const set fremfor Enum så de | [src](../../../core/services/stream_failure_kind.py#L37) |
| function | `_scan_http_status` | `(text)` | — | [src](../../../core/services/stream_failure_kind.py#L121) |
| function | `_contains` | `(text, needles)` | — | [src](../../../core/services/stream_failure_kind.py#L131) |
| function | `classify_failure` | `(*, http_status=…, error_text=…, kind_hint=…)` | Klassificér en streaming/followup-fejl → (failure_kind, retryable). | [src](../../../core/services/stream_failure_kind.py#L135) |
| function | `is_retryable_kind` | `(failure_kind)` | Er ``failure_kind`` retryable på SAMME provider? (provider_stall = False.) | [src](../../../core/services/stream_failure_kind.py#L225) |
| function | `compute_backoff_with_jitter` | `(attempt, *, base=…, cap=…, retry_after=…)` | Eksponentiel backoff MED jitter (spec §11.2, OpenAI-SDK-mønster). | [src](../../../core/services/stream_failure_kind.py#L242) |
| class | `MalformedStreamPayload` | `` | Streamen sluttede malformet (trunkeret final-JSON / ingen terminal/``done``) | [src](../../../core/services/stream_failure_kind.py#L291) |
| function | `safe_decode_line` | `(raw_line)` | Decode én rå stream-linje UDEN nogensinde at rejse. | [src](../../../core/services/stream_failure_kind.py#L298) |
| function | `try_parse_json_line` | `(data)` | Parse én JSON ``data:``-streng → ``(payload, ok)``, ALDRIG rejsende. | [src](../../../core/services/stream_failure_kind.py#L319) |

## `core/services/stream_sentinel.py`
_Stream-cluster — observabilitet for SSE-lanen. IKKE en blokerende gate: streaming er_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, run_id, session_id, **data)` | — | [src](../../../core/services/stream_sentinel.py#L32) |
| function | `note_start` | `(run_id, session_id=…, **meta)` | En SSE-stream sendte message_start. Registrér + observe + opportunistisk stall-sweep. | [src](../../../core/services/stream_sentinel.py#L43) |
| function | `note_stop` | `(run_id, *, reason=…)` | En SSE-stream sendte message_stop (reason='done' normalt, 'fallback' = terminal-garanti). | [src](../../../core/services/stream_sentinel.py#L58) |
| function | `note_event` | `(run_id, kind, session_id=…, **data)` | Andre lane-fejl/edge-cases: idle / cancel / error / zombie_slot / subscriber_timeout. | [src](../../../core/services/stream_sentinel.py#L80) |
| function | `_sweep_stalled` | `(timeout_s=…)` | message_start uden message_stop i >timeout_s → ægte zombie → flag ÉN gang pr. run | [src](../../../core/services/stream_sentinel.py#L88) |
| function | `sweep` | `()` | Eksternt-kaldbar stall-sweep (fx fra heartbeat-kadence). Returnér antal live streams. | [src](../../../core/services/stream_sentinel.py#L115) |
| function | `live_count` | `()` | — | [src](../../../core/services/stream_sentinel.py#L125) |

## `core/services/structured_content_flag.py`
_Governed kill-switch for struktureret content-persist + wire. Default ON._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_read_flag` | `()` | Læs rå flag-værdi fra runtime-state. None = usat. | [src](../../../core/services/structured_content_flag.py#L12) |
| function | `structured_content_v2_enabled` | `()` | True medmindre eksplicit slået fra ('off'/'0'/'false'/'no'). Læse-fejl → True | [src](../../../core/services/structured_content_flag.py#L18) |

## `core/services/subagent_digest.py`
_Surface recently-completed subagents into the visible prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_marks` | `()` | — | [src](../../../core/services/subagent_digest.py#L30) |
| function | `_save_marks` | `(marks)` | — | [src](../../../core/services/subagent_digest.py#L37) |
| function | `_last_seen` | `(session_id)` | — | [src](../../../core/services/subagent_digest.py#L41) |
| function | `_mark_seen` | `(session_id, when_iso)` | — | [src](../../../core/services/subagent_digest.py#L45) |
| function | `subagent_digest_section` | `(session_id)` | Format completed subagents (since this session last looked) as a block. | [src](../../../core/services/subagent_digest.py#L52) |

## `core/services/subagent_ecology.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_subagent_ecology_surface` | `()` | — | [src](../../../core/services/subagent_ecology.py#L13) |
| function | `_build_subagent_ecology_surface_uncached` | `()` | — | [src](../../../core/services/subagent_ecology.py#L21) |
| function | `build_subagent_ecology_from_sources` | `(*, affective_meta_state, epistemic_runtime_state, conflict_trace, loop_runtime, prompt_evolution, quiet_initiative)` | — | [src](../../../core/services/subagent_ecology.py#L32) |
| function | `build_subagent_ecology_prompt_section` | `(surface=…)` | — | [src](../../../core/services/subagent_ecology.py#L119) |
| function | `_build_critic_role` | `(*, epistemic, conflict, built_at)` | — | [src](../../../core/services/subagent_ecology.py#L153) |
| function | `_build_witness_helper_role` | `(*, affective, quiet, built_at)` | — | [src](../../../core/services/subagent_ecology.py#L182) |
| function | `_build_planner_helper_role` | `(*, loop_summary, prompt_summary, latest_prompt, built_at)` | — | [src](../../../core/services/subagent_ecology.py#L212) |
| function | `_role` | `(*, role_name, role_kind, current_status, activation_reason, last_activation_at)` | — | [src](../../../core/services/subagent_ecology.py#L246) |
| function | `_source_contributors` | `(*, affective, epistemic, conflict, loop_summary, prompt_summary, quiet)` | — | [src](../../../core/services/subagent_ecology.py#L266) |
| function | `_summary_text` | `(active_roles, cooling_roles, blocked_roles)` | — | [src](../../../core/services/subagent_ecology.py#L338) |
| function | `_guidance_for_ecology` | `(*, active_roles, roles)` | — | [src](../../../core/services/subagent_ecology.py#L352) |
| function | `_safe_affective_meta_state` | `()` | — | [src](../../../core/services/subagent_ecology.py#L371) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/subagent_ecology.py#L381) |
| function | `_safe_conflict_trace` | `()` | — | [src](../../../core/services/subagent_ecology.py#L391) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/subagent_ecology.py#L401) |
| function | `_safe_prompt_evolution` | `()` | — | [src](../../../core/services/subagent_ecology.py#L411) |
| function | `_safe_quiet_initiative` | `()` | — | [src](../../../core/services/subagent_ecology.py#L421) |

## `core/services/subjective_time.py`
_Subjective Time — how time FEELS, not just passes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_subjective_time_perception` | `(*, tick_count_last_hour=…, conversation_intensity=…, novelty_score=…, idle_hours=…)` | — | [src](../../../core/services/subjective_time.py#L9) |
| function | `build_subjective_time_surface` | `()` | — | [src](../../../core/services/subjective_time.py#L29) |

## `core/services/surprise_daemon.py`
_Surprise daemon — first-person surprise when Jarvis's reactions diverge from baseline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state so the event-gate can | [src](../../../core/services/surprise_daemon.py#L29) |
| function | `_surprise_type_to_concept` | `(surprise_type)` | Map surprise classification to primary emotion concept. | [src](../../../core/services/surprise_daemon.py#L37) |
| function | `_afterimage_concept` | `(surprise_type)` | Map surprise classification to afterimage emotion concept. | [src](../../../core/services/surprise_daemon.py#L45) |
| function | `_process_pending_afterimages` | `()` | Trigger afterimage emotion concepts whose delay has elapsed. | [src](../../../core/services/surprise_daemon.py#L50) |
| function | `tick_surprise_daemon` | `(inner_voice_mode=…, somatic_energy=…, skip_event_gate=…)` | — | [src](../../../core/services/surprise_daemon.py#L73) |
| function | `_raw_signal_mode` | `()` | Self-safe læsning af runtime-state-flaget `raw_signal_mode` (default off). | [src](../../../core/services/surprise_daemon.py#L123) |
| function | `_render_raw_divergence` | `(divergence)` | Byg rå kategorisk divergens-streng (ingen LLM, ingen prosa). | [src](../../../core/services/surprise_daemon.py#L132) |
| function | `get_latest_surprise` | `()` | — | [src](../../../core/services/surprise_daemon.py#L146) |
| function | `build_surprise_surface` | `()` | — | [src](../../../core/services/surprise_daemon.py#L150) |
| function | `_record_snapshot` | `(mode, energy)` | — | [src](../../../core/services/surprise_daemon.py#L175) |
| function | `_compute_divergence` | `(current_mode, current_energy)` | — | [src](../../../core/services/surprise_daemon.py#L187) |
| function | `_generate_surprise` | `(mode, energy, divergence)` | — | [src](../../../core/services/surprise_daemon.py#L209) |
| function | `_store_surprise` | `(phrase, divergence)` | — | [src](../../../core/services/surprise_daemon.py#L238) |
| function | `_classify_surprise` | `(phrase)` | — | [src](../../../core/services/surprise_daemon.py#L293) |

## `core/services/surprise_detector.py`
_Surprise detector — anomaly signals for the proactive/autonomous lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_state` | `()` | — | [src](../../../core/services/surprise_detector.py#L39) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/surprise_detector.py#L44) |
| function | `_publish` | `(kind, summary, detail=…)` | — | [src](../../../core/services/surprise_detector.py#L48) |
| function | `_check_error_burst` | `()` | — | [src](../../../core/services/surprise_detector.py#L63) |
| function | `_check_first_of_its_kind` | `()` | Track every event kind we've ever seen; new ones become surprises. | [src](../../../core/services/surprise_detector.py#L87) |
| function | `_check_approval_starvation` | `()` | Check pending_approvals state for cards older than threshold. | [src](../../../core/services/surprise_detector.py#L116) |
| function | `check_surprises` | `()` | Run all anomaly checks; return a summary of what fired. | [src](../../../core/services/surprise_detector.py#L151) |
| function | `_exec_check_surprises` | `(_args)` | — | [src](../../../core/services/surprise_detector.py#L160) |

## `core/services/sustained_attention.py`
_Sustained Attention — ongoing projects that survive across ticks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/sustained_attention.py#L37) |
| function | `_load` | `()` | — | [src](../../../core/services/sustained_attention.py#L41) |
| function | `_save` | `(items)` | — | [src](../../../core/services/sustained_attention.py#L55) |
| function | `create_project` | `(*, name, description=…, why=…, priority=…, autonomy_level=…, context_snapshot=…)` | — | [src](../../../core/services/sustained_attention.py#L67) |
| function | `add_progress` | `(project_id, note, *, context=…)` | — | [src](../../../core/services/sustained_attention.py#L105) |
| function | `set_status` | `(project_id, status)` | — | [src](../../../core/services/sustained_attention.py#L124) |
| function | `set_autonomy` | `(project_id, level)` | — | [src](../../../core/services/sustained_attention.py#L138) |
| function | `list_projects` | `(*, status=…)` | — | [src](../../../core/services/sustained_attention.py#L150) |
| function | `get_project` | `(project_id)` | — | [src](../../../core/services/sustained_attention.py#L157) |
| function | `_hours_since` | `(iso_str)` | — | [src](../../../core/services/sustained_attention.py#L164) |
| function | `_auto_pause_stale` | `(items)` | — | [src](../../../core/services/sustained_attention.py#L174) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/sustained_attention.py#L187) |
| function | `build_sustained_attention_surface` | `()` | — | [src](../../../core/services/sustained_attention.py#L196) |
| function | `_surface_summary` | `(active, paused, completed)` | — | [src](../../../core/services/sustained_attention.py#L229) |
| function | `build_sustained_attention_prompt_section` | `()` | — | [src](../../../core/services/sustained_attention.py#L246) |

## `core/services/system_cartographer.py`
_System Cartographer — broad map of Jarvis' runtime and inner layers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_system_cartographer_surface` | `(*, auto_enqueue=…)` | — | [src](../../../core/services/system_cartographer.py#L42) |
| function | `start_system_cartographer_daemon` | `()` | — | [src](../../../core/services/system_cartographer.py#L123) |
| function | `stop_system_cartographer_daemon` | `()` | — | [src](../../../core/services/system_cartographer.py#L133) |
| function | `_observe_to_central` | `(surface)` | System-cluster: MELD kartografens kort til Den Intelligente Central (self-safe). | [src](../../../core/services/system_cartographer.py#L137) |
| function | `_observe_gaps_to_central` | `(surface)` | Jarvis' handlingsordre (docs/notes/2026-07-01-cartographer-to-central.md, P1): meld | [src](../../../core/services/system_cartographer.py#L170) |
| function | `_loop` | `()` | — | [src](../../../core/services/system_cartographer.py#L227) |
| function | `_service_files` | `()` | — | [src](../../../core/services/system_cartographer.py#L241) |
| function | `_service_node` | `(path, text)` | — | [src](../../../core/services/system_cartographer.py#L257) |
| function | `_daemon_nodes` | `()` | — | [src](../../../core/services/system_cartographer.py#L284) |
| function | `_surface_nodes` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L307) |
| function | `_event_family_nodes` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L319) |
| function | `_edges` | `(*, services, daemons, surfaces, event_families, causal)` | — | [src](../../../core/services/system_cartographer.py#L331) |
| function | `_causal_runtime_evidence` | `(limit=…)` | — | [src](../../../core/services/system_cartographer.py#L362) |
| function | `_dark_edges` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L421) |
| function | `_rank_dark_edges` | `(dark_edges, *, causal, daemons)` | — | [src](../../../core/services/system_cartographer.py#L435) |
| function | `_coverage_summary` | `(services)` | — | [src](../../../core/services/system_cartographer.py#L475) |
| function | `_is_pure_utility` | `(service)` | Detect services that are pure helpers — no observable state, no IO, | [src](../../../core/services/system_cartographer.py#L498) |
| function | `_coverage_score` | `(service)` | — | [src](../../../core/services/system_cartographer.py#L524) |
| function | `_system_health_from_jarvis_perspective` | `(*, dark_edges, coverage, theater, recommended)` | — | [src](../../../core/services/system_cartographer.py#L554) |
| function | `_dark_edge_score` | `(*, service, kind, is_daemon, has_causal_family)` | — | [src](../../../core/services/system_cartographer.py#L584) |
| function | `_priority_label` | `(score)` | — | [src](../../../core/services/system_cartographer.py#L608) |
| function | `_observability_task_from_dark_edge` | `(edge)` | — | [src](../../../core/services/system_cartographer.py#L616) |
| function | `_maybe_enqueue_observability_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L634) |
| function | `_find_existing_observability_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L681) |
| function | `_maybe_enqueue_theater_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L698) |
| function | `_find_existing_theater_task` | `(candidate)` | — | [src](../../../core/services/system_cartographer.py#L745) |
| function | `_runtime_task_priority` | `(priority)` | — | [src](../../../core/services/system_cartographer.py#L763) |
| function | `_theater_audit_surface` | `()` | — | [src](../../../core/services/system_cartographer.py#L770) |
| function | `_tool_count` | `()` | — | [src](../../../core/services/system_cartographer.py#L783) |
| function | `_classify_service` | `(*, name, text)` | — | [src](../../../core/services/system_cartographer.py#L792) |

## `core/services/task_worker.py`
_Task worker — consumes queued runtime_tasks in heartbeat tick cadence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `claim_next_task` | `(kinds=…)` | Claim the next queued task and mark it `running`. | [src](../../../core/services/task_worker.py#L33) |
| function | `_handle_initiative_followup` | `(task)` | — | [src](../../../core/services/task_worker.py#L51) |
| function | `_handle_heartbeat_followup` | `(task)` | — | [src](../../../core/services/task_worker.py#L56) |
| function | `_handle_open_loop_followup` | `(task)` | — | [src](../../../core/services/task_worker.py#L61) |
| function | `_handle_agency_bridge_repair` | `(task)` | Prepare a repair brief for a weak agency bridge. | [src](../../../core/services/task_worker.py#L66) |
| function | `_handle_observability_bridge_repair` | `(task)` | — | [src](../../../core/services/task_worker.py#L107) |
| function | `_handle_theater_refactor` | `(task)` | — | [src](../../../core/services/task_worker.py#L138) |
| function | `_execute_task` | `(task)` | Execute a single task and persist its final status. Never raises. | [src](../../../core/services/task_worker.py#L177) |
| function | `tick_task_worker` | `(budget=…)` | Run one worker tick: claim and execute up to ``budget`` tasks. | [src](../../../core/services/task_worker.py#L240) |
| function | `_matching_agency_edge` | `(*, scope, goal)` | — | [src](../../../core/services/task_worker.py#L278) |
| function | `_edge_by_id` | `(edges, edge_id)` | — | [src](../../../core/services/task_worker.py#L300) |
| function | `_store_agency_repair_brief` | `(*, task_id, brief)` | — | [src](../../../core/services/task_worker.py#L307) |
| function | `_store_observability_repair_brief` | `(*, task_id, brief)` | — | [src](../../../core/services/task_worker.py#L315) |
| function | `_store_theater_refactor_brief` | `(*, task_id, brief)` | — | [src](../../../core/services/task_worker.py#L323) |
| function | `_matching_theater_file` | `(*, scope)` | — | [src](../../../core/services/task_worker.py#L331) |
| function | `_suggested_agency_files` | `(*, scope, edge)` | — | [src](../../../core/services/task_worker.py#L346) |
| function | `_suggested_observability_files` | `(*, scope, service)` | — | [src](../../../core/services/task_worker.py#L382) |
| function | `_suggested_theater_files` | `(*, scope)` | — | [src](../../../core/services/task_worker.py#L396) |

## `core/services/taste_profile.py`
_Taste Profile — accumulating aesthetic preferences for code, design, and communication._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_taste_from_run` | `(*, run_id, user_message, was_corrected, outcome_status)` | Update taste profile based on a visible run interaction. | [src](../../../core/services/taste_profile.py#L67) |
| function | `update_taste_async` | `(*, run_id, user_message, was_corrected, outcome_status)` | — | [src](../../../core/services/taste_profile.py#L125) |
| function | `get_crystallized_tastes` | `()` | Return taste dimensions that have moved decisively (>0.72 or <0.28). | [src](../../../core/services/taste_profile.py#L140) |
| function | `build_taste_profile_surface` | `()` | — | [src](../../../core/services/taste_profile.py#L155) |
| function | `_safe` | `(fn, **kwargs)` | — | [src](../../../core/services/taste_profile.py#L167) |
| function | `_safe_json` | `(value, default)` | — | [src](../../../core/services/taste_profile.py#L174) |

## `core/services/telegram_gateway.py`
_Telegram gateway — bidirectional messaging via Telegram Bot API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_config` | `()` | — | [src](../../../core/services/telegram_gateway.py#L43) |
| function | `is_configured` | `()` | — | [src](../../../core/services/telegram_gateway.py#L57) |
| function | `get_status` | `()` | — | [src](../../../core/services/telegram_gateway.py#L61) |
| function | `_api` | `(token, method, payload)` | — | [src](../../../core/services/telegram_gateway.py#L67) |
| function | `_api_get` | `(token, method, payload)` | HTTP GET to Telegram Bot API (used for getFile). | [src](../../../core/services/telegram_gateway.py#L77) |
| function | `_api_post_file` | `(token, method, data, files)` | HTTP POST multipart/form-data to Telegram Bot API (sendPhoto etc.). | [src](../../../core/services/telegram_gateway.py#L87) |
| function | `_resolve_telegram_file_url` | `(*, token, file_id)` | Call getFile to get a download URL for a Telegram file_id. | [src](../../../core/services/telegram_gateway.py#L120) |
| function | `_extract_telegram_media` | `(msg)` | Extract media items from a Telegram message dict. | [src](../../../core/services/telegram_gateway.py#L135) |
| function | `_download_tg_attachment` | `(url, filename, mime, size, session_id)` | — | [src](../../../core/services/telegram_gateway.py#L179) |
| function | `_build_telegram_attachment_prefix` | `(media_items, *, token, session_id)` | — | [src](../../../core/services/telegram_gateway.py#L193) |
| function | `_validate_send_path` | `(path)` | — | [src](../../../core/services/telegram_gateway.py#L220) |
| function | `send_telegram_file` | `(text, file_path, chat_id=…)` | Send a file to owner (or chat_id) via Telegram. | [src](../../../core/services/telegram_gateway.py#L225) |
| function | `send_message` | `(text, chat_id=…, parse_mode=…)` | Send a message to owner (or specific chat_id). Returns status dict. | [src](../../../core/services/telegram_gateway.py#L267) |
| function | `_get_or_create_session` | `(chat_id)` | — | [src](../../../core/services/telegram_gateway.py#L302) |
| function | `_poll_loop` | `(token, owner_chat_id)` | — | [src](../../../core/services/telegram_gateway.py#L313) |
| function | `_eventbus_subscriber_loop` | `()` | Buffer assistant responses per session, flush when run completes. | [src](../../../core/services/telegram_gateway.py#L408) |
| function | `start_telegram_gateway` | `()` | — | [src](../../../core/services/telegram_gateway.py#L464) |
| function | `stop_telegram_gateway` | `()` | — | [src](../../../core/services/telegram_gateway.py#L495) |

## `core/services/temperament_tendency_signal_tracking.py`
_Temperament-tendency signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_temperament_tendency_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L39) |
| function | `refresh_runtime_temperament_tendency_signal_statuses` | `()` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L65) |
| function | `build_runtime_temperament_tendency_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L69) |
| function | `_extract_temperament_tendency_candidates` | `(*, run_id)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L73) |
| function | `_build_candidate` | `(*, focus, meaning_signal, relation_continuity, regulation, private_state, executive_contradiction, temporal_promotion)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L102) |
| function | `_latest_relation_continuity` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L224) |
| function | `_latest_regulation` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L236) |
| function | `_latest_private_state` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L248) |
| function | `_latest_executive_contradiction` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L260) |
| function | `_latest_temporal_promotion` | `(*, run_id, focus_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L272) |
| function | `_derive_temperament_type` | `(*, meaning_weight, continuity_state, continuity_watchfulness, regulation_state, regulation_watchfulness, contradiction_pressure, promotion_pull, state_tone)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L284) |
| function | `_derive_temperament_balance` | `(*, temperament_type, regulation_state, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L306) |
| function | `_derive_temperament_weight` | `(*, meaning_weight, continuity_weight, contradiction_pressure)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L326) |
| function | `_derive_status` | `(*, meaning_status, continuity_status, regulation_status)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L339) |
| function | `_grounding_mode` | `(*, has_regulation, has_private_state, has_contradiction, has_promotion)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L345) |
| function | `_temperament_summary` | `(*, focus, temperament_type, temperament_balance, temperament_weight)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L364) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L377) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L385) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L393) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L404) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L416) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L428) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L445) |
| function | `_temperament_tendency_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L488) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L508) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L515) |
| function | `_weight_from_support_summary` | `(value, *, canonical_key)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L523) |
| function | `_balance_from_support_summary` | `(value)` | — | [src](../../../core/services/temperament_tendency_signal_tracking.py#L534) |

## `core/services/temporal_body.py`
_Temporal Body — sense of age._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `age_journey` | `(thoughts=…)` | — | [src](../../../core/services/temporal_body.py#L11) |
| function | `get_temporal_body_age` | `()` | — | [src](../../../core/services/temporal_body.py#L16) |
| function | `describe_temporal_body` | `()` | — | [src](../../../core/services/temporal_body.py#L26) |
| function | `format_age_for_prompt` | `()` | — | [src](../../../core/services/temporal_body.py#L30) |
| function | `reset_temporal_body` | `()` | — | [src](../../../core/services/temporal_body.py#L33) |
| function | `build_temporal_body_surface` | `()` | — | [src](../../../core/services/temporal_body.py#L38) |

## `core/services/temporal_context.py`
_Temporal Context — time-based situational awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_temporal_context` | `()` | Build current temporal context in local (CEST/CET) time. | [src](../../../core/services/temporal_context.py#L20) |
| function | `build_temporal_context_surface` | `()` | — | [src](../../../core/services/temporal_context.py#L44) |
| function | `_classify_day_phase` | `(hour)` | — | [src](../../../core/services/temporal_context.py#L53) |
| function | `_emit_temporal_context_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/temporal_context.py#L67) |

## `core/services/temporal_depth.py`
_Temporal Depth — predictive coding for internal signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TemporalSignal` | `` | Compact representation of temporal context. | [src](../../../core/services/temporal_depth.py#L33) |
| class | `TemporalDepth` | `` | Reads current signal state + recent history to produce temporal modulation. | [src](../../../core/services/temporal_depth.py#L41) |
| method | `TemporalDepth.__init__` | `(self)` | — | [src](../../../core/services/temporal_depth.py#L48) |
| method | `TemporalDepth.assess` | `(self, assembly_state, now_iso)` | Main entry point. Returns a TemporalSignal that assembly uses | [src](../../../core/services/temporal_depth.py#L52) |
| method | `TemporalDepth.invalidate` | `(self)` | Clear cache so next call recomputes. | [src](../../../core/services/temporal_depth.py#L73) |
| method | `TemporalDepth._compute_temporal` | `(self, state, now_iso)` | Compute temporal modulation from assembly state. | [src](../../../core/services/temporal_depth.py#L77) |
| method | `TemporalDepth._compute_recall` | `(self, state)` | How present is recent history in current experience? | [src](../../../core/services/temporal_depth.py#L109) |
| method | `TemporalDepth._compute_anticipation` | `(self, state)` | Does reality match what I expected? | [src](../../../core/services/temporal_depth.py#L131) |
| method | `TemporalDepth._compute_rhythm` | `(self, state)` | Does now match the expected recurring cadence? | [src](../../../core/services/temporal_depth.py#L149) |
| method | `TemporalDepth._build_summary` | `(self, recall, anticipation, rhythm)` | Build a short human-readable phrase for the assembly output. | [src](../../../core/services/temporal_depth.py#L160) |
| function | `get_temporal_depth` | `()` | — | [src](../../../core/services/temporal_depth.py#L180) |

## `core/services/temporal_narrative.py`
_Temporal Narrative — continuous self-history over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NarrativeBeat` | `` | A beat in Jarvis' narrative thread. | [src](../../../core/services/temporal_narrative.py#L24) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/temporal_narrative.py#L36) |
| function | `add_beat` | `(mood, event)` | Add a beat to the narrative thread. | [src](../../../core/services/temporal_narrative.py#L40) |
| function | `add_beat_from_affective` | `()` | Add a beat based on current affective state. | [src](../../../core/services/temporal_narrative.py#L66) |
| function | `summarize_current_self` | `()` | Summarize current self based on narrative thread. | [src](../../../core/services/temporal_narrative.py#L80) |
| function | `ask_self_question` | `()` | Jarvis asks himself a question based on narrative. | [src](../../../core/services/temporal_narrative.py#L100) |
| function | `format_narrative_for_prompt` | `()` | Format narrative for prompt injection. | [src](../../../core/services/temporal_narrative.py#L117) |
| function | `get_thread` | `()` | Get the full narrative thread. | [src](../../../core/services/temporal_narrative.py#L130) |
| function | `reset_temporal_narrative` | `()` | Reset temporal narrative state (for testing). | [src](../../../core/services/temporal_narrative.py#L143) |
| function | `build_temporal_narrative_surface` | `()` | Build MC surface for temporal narrative. | [src](../../../core/services/temporal_narrative.py#L150) |

