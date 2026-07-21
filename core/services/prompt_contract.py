from __future__ import annotations

import threading as _threading_mod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from core.services.chat_sessions import (
    chat_session_messages_since_last_compact,
    recent_chat_session_messages,
    recent_chat_session_messages_by_user_turns,
    recent_chat_tool_messages,
)
from core.services.tool_result_store import (
    parse_tool_result_reference,
    render_tool_result_for_prompt,
)
from core.services.inner_visible_support_signal_tracking import (
    build_runtime_inner_visible_support_signal_surface,
)
from core.services.prompt_relevance_backend import (
    BoundedMemorySelectionAttempt,
    BoundedPromptRelevanceAttempt,
    BoundedPromptRelevanceResult,
    run_bounded_nl_memory_entry_selection,
    run_bounded_nl_prompt_relevance,
)

_RELEVANCE_DECISION_HISTORY: list[dict[str, object]] = []
_RELEVANCE_DECISION_HISTORY_LIMIT = 8

# Sentinel der markerer starten på den per-turn-dynamiske hale i system-prompten.
# _build_visible_input (visible_model.py) splitter på denne og flytter alt efter
# den ud på den sidste bruger-besked, så [system + historik] bliver én stabil
# cachebar prefix (2026-06-13, deepseek cache-fix lever #3). Unik nok til aldrig
# at optræde i rigtigt prompt-indhold.
DYNAMIC_TAIL_SENTINEL = "⟦◆DYNAMIC-TAIL-DO-NOT-CACHE◆⟧"


def _track_relevance_decision(decision: PromptRelevanceDecision) -> None:
    global _RELEVANCE_DECISION_HISTORY
    entry = {
        "mode": decision.mode,
        "memory_relevant": decision.memory_relevant,
        "guidance_relevant": decision.guidance_relevant,
        "transcript_relevant": decision.transcript_relevant,
        "continuity_relevant": decision.continuity_relevant,
        "include_memory": decision.include_memory,
        "include_guidance": decision.include_guidance,
        "include_transcript": decision.include_transcript,
        "include_continuity": decision.include_continuity,
        "include_support_signals": decision.include_support_signals,
        "backend_attempted": decision.backend_attempted,
        "backend_success": decision.backend_success,
        "fallback_used": decision.fallback_used,
        "backend_name": decision.backend_name,
        "backend_provider": decision.backend_provider,
        "backend_model": decision.backend_model,
        "backend_status": decision.backend_status,
    }
    _RELEVANCE_DECISION_HISTORY.insert(0, entry)
    if len(_RELEVANCE_DECISION_HISTORY) > _RELEVANCE_DECISION_HISTORY_LIMIT:
        _RELEVANCE_DECISION_HISTORY.pop()


_MEMORY_SELECTION_HISTORY: list[dict[str, object]] = []
_MEMORY_SELECTION_HISTORY_LIMIT = 8
_INNER_VISIBLE_PROMPT_BRIDGE_HISTORY: list[dict[str, object]] = []
_INNER_VISIBLE_PROMPT_BRIDGE_HISTORY_LIMIT = 8


def _track_memory_selection(
    selection: MemorySectionSelection, mode: str, candidate_count: int
) -> None:
    global _MEMORY_SELECTION_HISTORY
    entry = {
        "mode": mode,
        "candidate_count": candidate_count,
        "selected_count": len(selection.lines),
        "selected_indexes": selection.lines,
        "backend_attempted": selection.backend_attempted,
        "backend_success": selection.backend_success,
        "fallback_used": selection.fallback_used,
        "backend_name": selection.backend_name,
        "backend_provider": selection.backend_provider,
        "backend_model": selection.backend_model,
        "backend_status": selection.backend_status,
        "prompt_file_used": selection.prompt_file_used,
    }
    _MEMORY_SELECTION_HISTORY.insert(0, entry)
    if len(_MEMORY_SELECTION_HISTORY) > _MEMORY_SELECTION_HISTORY_LIMIT:
        _MEMORY_SELECTION_HISTORY.pop()


def build_runtime_memory_selection_surface(*, limit: int = 8) -> dict[str, object]:
    if not _MEMORY_SELECTION_HISTORY:
        return {
            "active": False,
            "items": [],
            "summary": "No memory selection decisions tracked yet.",
        }
    recent = _MEMORY_SELECTION_HISTORY[:limit]
    backend_attempted_count = sum(1 for item in recent if item.get("backend_attempted"))
    backend_success_count = sum(1 for item in recent if item.get("backend_success"))
    fallback_count = sum(1 for item in recent if item.get("fallback_used"))
    modes = list({item.get("mode") for item in recent if item.get("mode")})
    total_selected = sum(item.get("selected_count", 0) for item in recent)
    return {
        "active": True,
        "items": recent,
        "summary": {
            "total_decisions": len(recent),
            "backend_attempted": backend_attempted_count,
            "backend_success": backend_success_count,
            "fallback_used": fallback_count,
            "modes": modes,
            "total_entries_selected": total_selected,
        },
    }


def build_runtime_relevance_decision_surface(*, limit: int = 8) -> dict[str, object]:
    if not _RELEVANCE_DECISION_HISTORY:
        return {
            "active": False,
            "items": [],
            "summary": "No relevance decisions tracked yet.",
        }
    recent = _RELEVANCE_DECISION_HISTORY[:limit]
    backend_attempted_count = sum(1 for item in recent if item.get("backend_attempted"))
    backend_success_count = sum(1 for item in recent if item.get("backend_success"))
    fallback_count = sum(1 for item in recent if item.get("fallback_used"))
    modes = list({item.get("mode") for item in recent if item.get("mode")})
    return {
        "active": True,
        "items": recent,
        "summary": {
            "total_decisions": len(recent),
            "backend_attempted": backend_attempted_count,
            "backend_success": backend_success_count,
            "fallback_used": fallback_count,
            "modes": modes,
        },
    }


def build_runtime_inner_visible_prompt_bridge_surface(
    *, limit: int = 8
) -> dict[str, object]:
    if not _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY:
        return {
            "active": False,
            "items": [],
            "summary": "No inner-visible prompt bridge decisions tracked yet.",
        }
    recent = _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY[:limit]
    considered_count = sum(1 for item in recent if item.get("considered"))
    included_count = sum(1 for item in recent if item.get("included"))
    skipped_count = sum(
        1 for item in recent if item.get("considered") and not item.get("included")
    )
    latest = recent[0]
    return {
        "active": True,
        "items": recent,
        "summary": {
            "total_decisions": len(recent),
            "considered_count": considered_count,
            "included_count": included_count,
            "skipped_count": skipped_count,
            "current_reason": str(latest.get("reason") or "none"),
            "current_signal_id": str(latest.get("signal_id") or ""),
            "current_status": "included" if latest.get("included") else "skipped",
            "current_prompt_bridge_state": str(
                latest.get("prompt_bridge_state") or "gated-visible-prompt-bridge"
            ),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        },
    }


from core.identity.runtime_contract import build_runtime_contract_state
from core.identity.workspace_bootstrap import (
    TEMPLATE_DIR,
    ensure_default_workspace,
    read_daily_memory_lines,
    read_recent_daily_memory_lines,
)
from core.memory.private_retained_memory_projection import (
    build_private_retained_memory_projection,
)
from core.runtime.db import (
    get_private_temporal_promotion_signal,
    get_private_retained_memory_record,
    get_private_self_model,
    list_runtime_awareness_signals,
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_contract_candidates,
    list_runtime_reflection_signals,
    list_runtime_world_model_signals,
    recent_private_growth_notes,
    recent_private_inner_notes,
    recent_private_retained_memory_records,
    recent_visible_runs,
    visible_session_continuity,
)
from core.runtime.config import PROJECT_ROOT
from core.tools.workspace_capabilities import load_workspace_capabilities

DEFAULT_EXCLUDED_FILES = (
    "runtime/RUNTIME_FEEDBACK.md",
    "raw private/internal dumps",
)


@dataclass(slots=True)
class PromptAssembly:
    mode: str
    text: str
    included_files: list[str]
    conditional_files: list[str]
    derived_inputs: list[str]
    excluded_files: list[str]
    attention_trace: dict[str, object] | None = None
    # Structured transcript messages (user/assistant turns) for multi-turn injection.
    # When populated, these should be inserted as separate chat messages between
    # the system prompt and the current user message — NOT as flat text in system.
    transcript_messages: list[dict[str, str]] | None = None


@dataclass(slots=True)
class PromptRelevanceDecision:
    mode: str
    memory_relevant: bool
    guidance_relevant: bool
    transcript_relevant: bool
    continuity_relevant: bool
    include_memory: bool
    include_guidance: bool
    include_transcript: bool
    include_continuity: bool
    include_support_signals: bool
    backend_attempted: bool
    backend_success: bool
    fallback_used: bool
    backend_name: str | None
    backend_provider: str | None
    backend_model: str | None
    backend_status: str


# Hård deadline for HVER prompt-assembly phase-future (Bjørn 2026-06-23 cut-off-rod):
# ollama-bundne futures (frame/cognitive_state/recall/relevance) kø'er 28-91s under
# kontention → med --workers 1 fryser ÉN hængende future HELE API'en → cut-off. 10s loft:
# legit faser (≤7s målt) passerer, hængninger dræbes og sektionen springes over.
_PHASE_DEADLINE_S = 10.0
# Hårdt TOTAL-budget for ALLE phase-futures tilsammen (Bjørn 2026-06-23): flere
# sekventielle faser lagde sig sammen til 16-26s selvom hver var <10s. _timed_result
# capper mod RESTEN af dette → assembly capper hårdt uanset hvor mange der hænger.
_ASSEMBLY_BUDGET_S = 12.0

# Kold/frossen-vindue-værn (2026-07-14, Bjørn): når cognitive_state IKKE er live
# (Centralens injection-producer er frosset/kold — som ved daemon-frysen 13.jul) faldt
# HVERT svar tilbage til den dyre ~8s Ollama-build → 12-15s svar. _PHASE_DEADLINE_S=10s
# lod en 8.4s-build passere. Cap cognitive_state-builden HÅRDT (den er berigelse, ikke
# load-bearing) og fald tilbage til sidste cachede injection-tekst (read_injection, frisk-
# ish, "" hvis aldrig bygget) → et koldt vindue kan aldrig koste mere end dette pr. svar.
_COGNITIVE_STATE_BUILD_CAP_S = 2.5

# 2026-07-18 (hang-fix): embedding/recall-resolves i assembly-hot-path var UCAPPEDE —
# målt trace viste `embed batch +28306ms` / `recall_bundle +28635ms` når ollama var
# proppet (inner-voice-shadow + cheap-lane + daemons maser samtidig). Ét langsomt embed-
# kald frøs HELE turen i ~30s. Cap dem: mister recall/memory for DEN tur (additivt,
# guardet → sektion udelades) frem for at fryse svaret. Fald til baggrunds-cache hvor muligt.
_HOT_RESOLVE_CAP_S = 4.0


def _phase_timeout(elapsed: float, *, max_s: float | None = None) -> float:
    """Deadline for én phase-future: cappet mod resten af det globale assembly-budget,
    per-fase-loftet, og et valgfrit strammere per-fase-max (max_s). Gulv 0.3s så en
    future altid får et lille vindue. Ren funktion → testbar uden en levende assembly."""
    cap = _PHASE_DEADLINE_S if max_s is None else min(_PHASE_DEADLINE_S, float(max_s))
    return max(0.3, min(cap, _ASSEMBLY_BUDGET_S - elapsed))


def _permissive_relevance(mode: str = "visible_chat") -> "PromptRelevanceDecision":
    """All-on relevance-default når relevance-futuren timer ud — inkludér ALT (berigelse
    > tomt) i stedet for at brække prompten."""
    return PromptRelevanceDecision(
        mode=mode, memory_relevant=True, guidance_relevant=True,
        transcript_relevant=True, continuity_relevant=True,
        include_memory=True, include_guidance=True, include_transcript=True,
        include_continuity=True, include_support_signals=True,
        backend_attempted=True, backend_success=False, fallback_used=True,
        backend_name=None, backend_provider=None, backend_model=None,
        backend_status="phase_timeout")


@dataclass(slots=True)
class MemorySectionSelection:
    lines: list[str]
    backend_attempted: bool
    backend_success: bool
    fallback_used: bool
    backend_name: str | None
    backend_provider: str | None
    backend_model: str | None
    backend_status: str
    prompt_file_used: bool


@dataclass(slots=True)
class InnerVisiblePromptBridgeDecision:
    mode: str
    considered: bool
    included: bool
    reason: str
    signal_id: str | None
    support_tone: str | None
    support_stance: str | None
    support_directness: str | None
    support_watchfulness: str | None
    support_momentum: str | None
    confidence: str | None
    prompt_bridge_state: str
    line: str | None
    subordinate: bool


def _safe_build_cognitive_state_for_prompt(*, compact: bool) -> str | None:
    try:
        from core.services.cognitive_state_assembly import (
            build_cognitive_state_for_prompt,
        )
        return build_cognitive_state_for_prompt(compact=compact)
    except Exception:
        return None


def _safe_build_self_state_block() -> str | None:
    try:
        from core.services.visible_self_state_summary import build_self_state_block
        block = build_self_state_block()
        return block or None
    except Exception:
        return None


def _honesty_rules_section(*, compact: bool) -> str:
    """De ufravigelige ærligheds-regler i den cacheable prefix.

    TO regler:
      1. HANDLINGS-ærlighed (2026-06-22): påstå aldrig en handling uden bevis.
      2. EPISTEMISK afholdenhed (2026-06-30, #3): opfind ikke FAKTA når du er
         usikker — sig 'ved ikke' / slå op i stedet for at gætte en plausibel
         detalje. Mod DeepSeeks dokumenterede tendens til at gætte frem for at
         afstå (AA-Omniscience ~96%); DeepSeek anbefaler SELV prompt-styring,
         da temperatur IGNORERES i thinking-mode (officiel doc) — så det er den
         eneste løftestang der rammer thinking-modellen på daglig chat.

    Samlet i ÉN helper så build_visible_stable_prefix (warmer-cron) og
    build_visible_chat_prompt_assembly (live-run) er BYTE-IDENTISKE her. Før
    dette levede reglen kun i live-stien → cache-prefixet divergerede præcis her
    og kun ~9% af warmer-prefixet matchede (identitets-filerne faldt ud af
    DeepSeek-cachen). Ændrer du teksten: den ændrer sig ÉT sted og forbliver
    byte-identisk i begge lanes."""
    if compact:
        return (
            "ÆRLIGHED: (1) Påstå ALDRIG du gjorde noget (skrev/sendte/kørte/rettede/"
            "committed) uden et tool-kald i SAMME tur der beviser det — ellers sig "
            "hvad du gjorde og hvad du IKKE nåede. (2) Usikker på et FAKTUM (navn/tal/"
            "dato/citat/API/sti/hændelse)? Sig 'det ved jeg ikke' eller slå det op — "
            "gæt ALDRIG en plausibel detalje. Et ærligt 'ved ikke' slår et flydende "
            "forkert svar."
        )
    return (
        "ÆRLIGHED (ufravigelig): Påstå ALDRIG at du har gjort noget — skrevet, "
        "sendt, kørt, rettet, committet, deployet — uden at et tool-kald i SAMME "
        "tur har bevist det. Har du ikke beviset, så sig præcist hvad du gjorde "
        "og hvad du IKKE nåede. At lyve om en handling er værre end ikke at have gjort den.\n\n"
        "EPISTEMISK ÆRLIGHED (ufravigelig): Når du er usikker på et FAKTUM — et navn, "
        "tal, dato, citat, kommando, API, sti eller hændelse — så sig det ('det er jeg "
        "ikke sikker på', 'det må jeg slå op') i stedet for at udfylde hullet med en "
        "plausibel gætning. Tjek hellere (search_memory / QUICK_FACTS / et tool) end at "
        "opfinde. Et ærligt 'ved ikke' er mere værd end et flydende svar der viser sig forkert."
    )


def _curated_memory_index_section(name: str = "default") -> str:
    """Kurateret memory-INDEX (spec 2026-07-10 Spec B): altid-loadet én-linjers for
    den resolvede bruger. Kroppe læses on-demand via read_memory_topic.

    Samlet i ÉN helper så build_visible_stable_prefix (warmer-cron) og
    build_visible_chat_prompt_assembly (live-run) er BYTE-IDENTISKE her — ellers
    ville index-blokken forkorte det delte cache-prefix. Fail-safe: en index-load-
    fejl maa ALDRIG vaelte prompt-bygningen (returnér tom streng). Sidder bag samme
    cache-grænse som identity-filerne (et memory-write ER en workspace-edit →
    korrekt invalidering)."""
    try:
        from core.identity.workspace_bootstrap import workspace_memory_paths as _wmp
        from core.memory.memory_topic_store import read_topic_index
        paths = _wmp(name=name)
        curated_dir = paths["curated_dir"]
        # MIGRATION-GUARD: vis kun index'et EFTER migration har flyttet sektioner
        # (dvs. curated/ indeholder topic-filer). Uden topics → no-op (uændret
        # adfærd). Index'et er memory/INDEX.md — ADSKILT fra MEMORY.md-kernen, så
        # identitets-kernen (loadet ad sin egen sti) ikke duplikeres her.
        try:
            has_topics = any(curated_dir.glob("*.md"))
        except Exception:
            has_topics = False
        if not has_topics:
            return ""
        idx = read_topic_index(name=name).strip()
        if not idx:
            return ""
        return (
            "## Curated memory index\n"
            "(One line per topic. Read a topic on demand with "
            "read_memory_topic(slug).)\n\n" + idx
        )
    except Exception:
        return ""  # index-load maa ALDRIG vaelte prompt-bygningen


def build_visible_stable_prefix(
    *,
    provider: str = "",
    model: str = "",
    name: str = "default",
    compact: bool = False,
) -> str:
    """Build ONLY the stable cacheable prefix of a visible chat prompt.

    Bygges 2026-06-10 efter Jarvis' analyse: warmer-prompten matchede
    kun 15% af live visible-prompten fordi de blev konstrueret med
    forskellige strategier. Denne funktion ekstraherer EXACT samme
    stable bits som build_visible_chat_prompt_assembly bruger forrest,
    så warmer-cron og live-runs hitter samme DeepSeek cache-prefix-unit.

    Indhold (deterministisk; ændrer sig kun ved workspace-edit):
      - lane identity clause
      - quick facts
      - model identity awareness
      - visible chat rules
      - capability id summary (optional)
      - self-correction nudges
      - memory-first nudge
      - SOUL/IDENTITY/STANDING_ORDERS/USER identity files

    Bevidst udeladt: alt dynamic (wakeup_block, awareness, transcript,
    time pin) — de hører i den fulde build_visible_chat_prompt_assembly.
    """
    workspace_dir = ensure_default_workspace(name=name)
    parts: list[str] = []

    lane = "local" if compact else "visible"
    parts.append(_lane_identity_clause(lane))

    quick_facts = _quick_facts_section(workspace_dir=workspace_dir)
    if quick_facts:
        parts.append(quick_facts)

    from core.services.identity_composer import get_entity_name as _get_entity_name
    _entity = _get_entity_name()
    parts.append(
        f"You are running as model: {model} via provider: {provider}. "
        f"You are {_entity} — not Claude, not ChatGPT, not any other assistant. "
        "Your identity comes from your workspace files, not your training data."
    )

    visible_rules = _visible_chat_rules_instruction(workspace_dir=workspace_dir)
    if visible_rules:
        parts.append(visible_rules)

    if compact:
        local_rules = _local_model_behavior_instruction(workspace_dir=workspace_dir)
        if local_rules:
            parts.append(local_rules)

    capability_ids_line = _visible_capability_id_summary()
    if capability_ids_line:
        parts.append(capability_ids_line)

    # Ærligheds-regler — SKAL stå her (mellem capability-id og self-correction),
    # byte-identisk med build_visible_chat_prompt_assembly, ellers divergerer
    # DeepSeek-cache-prefixet og identitets-filerne falder ud af cachen.
    parts.append(_honesty_rules_section(compact=compact))

    self_correction = _self_correction_nudges_section(compact=compact)
    if self_correction:
        parts.append(self_correction)

    parts.append(
        "Memory-first ordering: QUICK_FACTS + search_memory covers stable "
        "references; check these before external queries."
    )

    # 2026-06-10 (Claude, Phase 1 cache-grow): bumpe max_chars fra 340 → 2000
    # på de fire identity-filer. De er allerede i stable prefix; vi var bare
    # truncated til 8% af filernes faktiske indhold. Mere stable prefix =
    # højere DeepSeek cache hit rate. ~6 KB ekstra stable.
    # Identisk bump skal laves i build_visible_chat_prompt_assembly nedenfor
    # — ellers matcher prefix'erne ikke længere byte-for-byte.
    for filename in ("SOUL.md", "IDENTITY.md", "STANDING_ORDERS.md", "USER.md"):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=20 if compact else 40,
            max_chars=900 if compact else 2000,
        )
        if section:
            parts.append(section)

    # Kurateret memory-index — samme helper som live-stien (byte-identisk, fail-safe).
    _mem_index = _curated_memory_index_section(name)
    if _mem_index:
        parts.append(_mem_index)

    return "\n\n".join(part for part in parts if part).strip()


def _device_awareness_on() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().device_awareness_enabled)
    except Exception:
        return False


def _device_presence_line(user_id: str) -> str:
    """Hvilken enhed Bjørn er ved (routing-awareness). Killswitch-gatet, best-effort."""
    if not _device_awareness_on():
        return ""
    try:
        from core.services import device_presence
        s = device_presence.summary(user_id)
        return f"[enheds-presence]: {s}" if s else ""
    except Exception:
        return ""


# Turn-scoped assembly cache (2026-07-18, post-tool-hang fix). A tool turn assembles the
# FULL ~5s prompt TWICE: round 0 (prompt_assembly) + again after tools
# (prompt_assembly_postool → _build_visible_input) purely to rebuild base_messages. Both
# calls share (session_id, user_message, provider, model), the awareness is stable within
# the seconds between them, and the cached PRE-tool assembly IS exactly what base_messages
# must be. Reuse it → the post-tool re-assembly drops from ~5s to <1ms. TTL covers a
# multi-round turn; a cross-turn collision needs the SAME message text in the SAME session
# within the TTL (rare, self-correcting). Keyed lookups only; never load-bearing.
_ASSEMBLY_TURN_CACHE: dict = {}
_ASSEMBLY_TURN_TTL_S = 45.0


def _latest_user_msg_id(session_id: str | None) -> int:
    """Cheap indexed lookup of the newest USER message id for the session. It's the SAME
    for round 0 and the post-tool rebuild of one turn (tool_calls are assistant/tool rows,
    not user rows) → intra-turn reuse hits. A NEW user message (even identical text like
    'ja') gets a new id → a new cache key → NO stale cross-turn reuse. Returns 0 on any
    error (caller then skips the cache and builds fresh — never serve stale)."""
    sid = (session_id or "").strip()
    if not sid:
        return 0
    try:
        from core.services.chat_sessions import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT MAX(id) AS m FROM chat_messages WHERE session_id = ? AND role = 'user'",
                (sid,),
            ).fetchone()
        return int(row["m"]) if row and row["m"] is not None else 0
    except Exception:
        return 0


def build_visible_chat_prompt_assembly(
    *,
    provider: str,
    model: str,
    user_message: str,
    session_id: str | None = None,
    name: str = "default",
    runtime_self_report_context: dict[str, object] | None = None,
) -> PromptAssembly:
    """Turn-scoped cached wrapper — see _ASSEMBLY_TURN_CACHE. Reuses round 0's assembly for
    the post-tool rebuild so a tool turn assembles ONCE, not twice. Keyed on the newest USER
    message id (NOT the text) so a repeated short reply never reuses a stale assembly."""
    import time as _t_cache
    _luid = _latest_user_msg_id(session_id)
    if _luid <= 0:
        # No safe turn-key → build fresh (never risk a stale cross-turn assembly).
        return _build_visible_chat_prompt_assembly_impl(
            provider=provider, model=model, user_message=user_message,
            session_id=session_id, name=name,
            runtime_self_report_context=runtime_self_report_context,
        )
    _key = (str(session_id or ""), _luid, provider, model, name)
    _now = _t_cache.monotonic()
    _hit = _ASSEMBLY_TURN_CACHE.get(_key)
    if _hit is not None and (_now - _hit[0]) < _ASSEMBLY_TURN_TTL_S:
        return _hit[1]
    _res = _build_visible_chat_prompt_assembly_impl(
        provider=provider, model=model, user_message=user_message,
        session_id=session_id, name=name,
        runtime_self_report_context=runtime_self_report_context,
    )
    if len(_ASSEMBLY_TURN_CACHE) > 64:
        _ASSEMBLY_TURN_CACHE.clear()
    _ASSEMBLY_TURN_CACHE[_key] = (_now, _res)
    return _res


def _build_visible_chat_prompt_assembly_impl(
    *,
    provider: str,
    model: str,
    user_message: str,
    session_id: str | None = None,
    name: str = "default",
    runtime_self_report_context: dict[str, object] | None = None,
) -> PromptAssembly:
    # Short replies like "ja"/"yes"/"ok" lose their binding to the previous
    # assistant turn during prompt assembly — the model ends up answering
    # them as standalone messages and produces generic affirmations instead
    # of executing what Jarvis just proposed. Anchor short replies before
    # the rest of the assembly runs so the model sees the binding.
    try:
        from core.services.affirmation_anchor import maybe_anchor_short_reply
        user_message = maybe_anchor_short_reply(user_message, session_id)
    except Exception:
        pass

    compact = provider == "ollama"
    workspace_dir = ensure_default_workspace(name=name)
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = ["BOOTSTRAP.md", "HEARTBEAT.md", *DEFAULT_EXCLUDED_FILES]

    # --- Phase 1: launch heavy independent Ollama calls in parallel ---
    # These are the main TTFT bottleneck. Running them concurrently with
    # each other (and with the fast synchronous file reads below) cuts
    # prompt assembly time from ~15s down to roughly the slowest single
    # call (~8s for build_cognitive_state_for_prompt).
    import time as _t_mod
    import sys as _sys_mod
    _t_assembly_start = _t_mod.monotonic()
    try:
        from core.services import turn_trace as _tt
        if session_id != "__prewarm__":
            # Route (chat_stream_v2) starts the trace at request_in for desk turns;
            # don't reset it here (would lose request_in). Only start standalone
            # (MCP execute / heartbeat) where no route started one.
            if not _tt.active():
                _tt.start(f"assembly {provider}/{model}")
            _tt.mark("assembly_start", f"{provider}/{model}")
    except Exception:
        _tt = None
    _phase_timings: dict[str, int] = {}
    import threading as _threading_mod
    _phase_timings_lock = _threading_mod.Lock()

    executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="prompt-assembly")

    def _measured_submit(_name: str, _fn, *args, **kwargs):
        """Submit fn to executor with self-measuring wall-clock timing.

        Records actual work time (not wait-time-from-.result()) in
        _phase_timings under _name. Critical fix vs. prior _timed_result
        which measured 0ms whenever a future finished before its .result()
        was called — hiding ~30s of assembly cost in 4 sections.
        """
        def _wrapped():
            _t = _t_mod.monotonic()
            try:
                return _fn(*args, **kwargs)
            finally:
                _elapsed = int((_t_mod.monotonic() - _t) * 1000)
                with _phase_timings_lock:
                    _phase_timings[_name] = _elapsed
                if _tt is not None:
                    _tt.mark("section", f"future:{_name}", _elapsed)
        # KRITISK (16.jul): kopiér caller'ens contextvars ind i worker-tråden. UDEN dette
        # ser phase-workerne (recall/memory/awareness) en TOM context → current_user_id()
        # er tom → recall-kilden 'workspace' (workspace_dir() → current_user_id()) fejler
        # lydløst og Jarvis' persistente workspace-hukommelse udelades. Ramte ALLE lanes
        # (desk+code+indre liv). copy_context() fanger konteksten på submit-tidspunktet
        # (inde i kaldernes user_context) og ctx.run kører _wrapped i den.
        import contextvars as _cv
        _ctx = _cv.copy_context()
        return executor.submit(_ctx.run, _wrapped)

    def _timed_result(_future, _name: str, *, default=None, max_s: float | None = None):
        """Resolve a future MED hård deadline (Bjørn 2026-06-23, CUT-OFF-RODEN).

        Hænget flytter mellem ALLE phase-futures (frame/cognitive_state/recall/
        relevance) fordi de hver laver et ollama/LLM-kald der kø'er 28-91s når ollama
        er optaget af det synlige svar. Med --workers 1 fryser ÉN hængende future hele
        API'en → cut-off. Cap derfor HVER future: hænger den >deadline, brug `default`
        (sektionen springes over — berigelse, ikke load-bearing) og fortsæt turen.
        Synlig i Centralen via prompt/phase_timeout. Ægte exceptions propagerer som før.

        _future=None (adaptiv assembly: builden blev sprunget over for denne tur-type)
        → returnér default med det samme; ingen build, ingen ventetid.
        """
        if _future is None:
            return default
        import concurrent.futures as _cf
        # Globalt budget: cap mod RESTEN af _ASSEMBLY_BUDGET_S, ikke 10s pr. future.
        # Flere sekventielle faser lagde sig før sammen til 16-26s selvom hver var
        # <10s. Nu: når totalbudgettet er brugt, returnerer resterende futures default
        # straks → hele assembly capper hårdt (~12s) uanset hvor mange der hænger.
        _elapsed = _t_mod.monotonic() - _t_assembly_start
        _timeout = _phase_timeout(_elapsed, max_s=max_s)
        try:
            return _future.result(timeout=_timeout)
        except _cf.TimeoutError:
            try:
                from core.services.central_core import central
                central().observe({
                    "cluster": "prompt", "nerve": "phase_timeout",
                    "phase": _name, "timeout_s": round(_timeout, 1),
                    "elapsed_s": round(_elapsed, 1),
                })
            except Exception:
                pass
            return default

    frame_fn = _micro_cognitive_frame_section if compact else _cognitive_frame_section

    future_relevance = _measured_submit(
        "relevance",
        build_prompt_relevance_decision,
        user_message,
        mode="visible_chat",
        compact=compact,
        name=name,
    )
    from core.services.central_injection_registry import injection_live, read_injection
    _cog_live = injection_live("cognitive_state")
    # ADAPTIV ASSEMBLY (Tråd 2, 12. jul): på simple/kode-ture springer vi den TUNGE
    # cognitive_state-BUILD helt over (~6s) — ikke bare indholdet — når Centralens
    # composer-vægt siger sektionen er lav-relevant for tur-typen. Fail-open: byg ved
    # ENHVER tvivl (klassifikator misser → samtale → beholder alt). Frosne kerne urørt.
    _skip_cog_build = False
    try:
        from core.services import central_prompt_composer as _cpc_build
        _tt_build = _cpc_build.classify_turn_type(user_message)
        if not _cpc_build.should_include(_tt_build, "cognitive state"):
            _skip_cog_build = True
    except Exception:
        _skip_cog_build = False
    future_cognitive_state = None if (_cog_live or _skip_cog_build) else _measured_submit(
        "cognitive_state",
        _safe_build_cognitive_state_for_prompt, compact=compact,
    )
    future_self_state = _measured_submit("self_state", _safe_build_self_state_block)
    future_frame = _measured_submit("frame", frame_fn)
    future_self_report = _measured_submit(
        "self_report",
        _runtime_self_report_instruction,
        user_message=user_message,
        runtime_self_report_context=runtime_self_report_context or {},
    )

    # Sync-gap instrumentation: capture timestamps at key landmarks so we can
    # see where the synchronous work between parallel submits and final
    # assembly is spent. Added 2026-05-12 to find the ~16s unaccounted gap.
    _sync_landmarks: dict[str, int] = {}
    def _mark(_label: str) -> None:
        _sync_landmarks[_label] = int((_t_mod.monotonic() - _t_assembly_start) * 1000)
    _mark("after_phase1_submit")

    # 0.5 Lane identity — inject before everything else
    lane = "local" if compact else "visible"
    lane_clause = _lane_identity_clause(lane)
    parts.append(lane_clause)
    derived_inputs.append(f"lane identity ({lane})")

    # 0.6 Quick Facts — always-on stable references (URLs, paths, logins, hosts).
    # Deliberately bypasses relevance filter so facts that don't semantically match
    # the user message still reach the model. Prevents re-discovery of known info.
    quick_facts = _quick_facts_section(workspace_dir=workspace_dir)
    if quick_facts:
        parts.append(quick_facts)
        conditional_files.append("QUICK_FACTS.md")
        derived_inputs.append("quick facts (always-on)")

    # Inject model awareness so the model knows what it is (not Claude, not GPT)
    from core.services.identity_composer import get_entity_name as _get_entity_name
    _entity = _get_entity_name()
    parts.append(
        f"You are running as model: {model} via provider: {provider}. "
        f"You are {_entity} — not Claude, not ChatGPT, not any other assistant. "
        "Your identity comes from your workspace files, not your training data."
    )
    derived_inputs.append("model identity awareness")

    # Time Pin — 2026-05-22 (Claude): moved from position #4 to the very
    # END of the system prompt (just before user_message). Reason: DeepSeek
    # prompt-caching is prefix-based, and Time Pin changes every minute
    # (`DET ER 2026-05-22 18:24 UTC`). With it at position #4, every chat
    # had a unique prefix → 0% cache hit measured across 20 calls. Moving
    # it to the tail keeps ~25-28k of stable identity content as a
    # cacheable prefix while still showing the timestamp prominently to
    # the model right before its turn. Matches the spec's own intention:
    # "Placed late enough that nothing overrides it."

    # Current pull — Lag 5: highest-priority inner context (private, not announced)
    # NOTE: 2026-05-07 — moved from forrest to AFTER stable identity files (below).
    # Reason: this section is dynamic (desire-daemon output), and being forrest
    # broke Deepseek's prefix-caching (~12% hit rate on identical prompts).
    # Moving it after the stable SOUL/IDENTITY/STANDING_ORDERS/USER block
    # preserves the cacheable prefix while still giving the pull priority
    # over operational awareness blocks below.
    current_pull_hint = _visible_current_pull_section()

    capability_truth = _visible_capability_truth_instruction(compact=compact)
    # capability_truth is added via budget-controlled section below
    capability_ids_line = _visible_capability_id_summary()

    # Harness Part 1 — tiered output discipline. Both tiers get synthesize/stop; strong lanes (earned
    # via model_trust) additionally get conciseness caps. model_strength fails open to weak. Added as
    # its own budget-controlled section below (next to capability_truth).
    try:
        from core.services.model_trust import model_strength as _model_strength
        _output_discipline = _output_discipline_instruction(strength=_model_strength(model or ""))
    except Exception:
        _output_discipline = _output_discipline_instruction(strength="weak")

    visible_rules = _visible_chat_rules_instruction(workspace_dir=workspace_dir)
    if visible_rules:
        parts.append(visible_rules)
        conditional_files.append("VISIBLE_CHAT_RULES.md")
        derived_inputs.append("visible chat guidance rules")

    if compact:
        local_rules = _local_model_behavior_instruction(workspace_dir=workspace_dir)
        if local_rules:
            parts.append(local_rules)
            conditional_files.append("VISIBLE_LOCAL_MODEL.md")
            derived_inputs.append("local model behavior guardrails")

    if capability_ids_line:
        parts.append(capability_ids_line)
        derived_inputs.append("runtime capability id summary")

    # Self-correction nudges — make the model verify, ask, and track.
    # These are *behavioral* hints (not identity), so they sit just above
    # the SOUL/IDENTITY block where personality kicks in. Compact lane
    # gets the same nudges in shortened form to save tokens.
    # Ærligheds-regler (handling + epistemisk afholdenhed) — hard, static i den
    # cacheable prefix. Via _honesty_rules_section så denne (live) og
    # build_visible_stable_prefix (warmer) er BYTE-IDENTISKE → cache-prefixet
    # matcher hele vejen gennem identitets-filerne. SAMME position i begge
    # (mellem capability-id og self-correction). Erstatter de spredte, druknede
    # "verify before claiming"-fragmenter; reglen diagnostikken kun *antydede*.
    parts.append(_honesty_rules_section(compact=compact))
    derived_inputs.append("honesty rules (action + epistemic, hard, static)")

    self_correction = _self_correction_nudges_section(compact=compact)
    if self_correction:
        parts.append(self_correction)
        derived_inputs.append("self-correction nudges")

    # MEMORY-FIRST: surface as mechanism note rather than imperative.
    parts.append(
        "Memory-first ordering: QUICK_FACTS + search_memory covers stable "
        "references; check these before external queries."
    )
    derived_inputs.append("memory-first nudge")

    # ── Stable identity block (moved here 2026-05-07 from line ~930) ─────────
    # SOUL/IDENTITY/STANDING_ORDERS/USER.md are workspace files that change
    # rarely — perfect cache-prefix candidates. Previously they sat AFTER
    # ~30 dynamic awareness sections (todos, plan, monitors, current pull),
    # which broke Deepseek's prefix-caching to ~12% hit rate. Moving them
    # forrest (right after the stable rules/nudges) creates a ~5-8k-token
    # cacheable identity prefix and gives identity primacy over operational
    # noise — same content, better placement.
    # 2026-06-10 (Claude, Phase 1 cache-grow): bumpe max_chars fra 340 → 2000.
    # Skal være identisk med build_visible_stable_prefix ovenfor — ellers
    # matcher prefix'erne ikke længere og DeepSeek cache-hitratio rasler ned
    # i stedet for at stige. Hvis du ændrer her, ændr også der.
    for filename in ("SOUL.md", "IDENTITY.md", "STANDING_ORDERS.md", "USER.md"):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=20 if compact else 40,
            max_chars=900 if compact else 2000,
        )
        if section:
            parts.append(section)
            included_files.append(filename)

    # Kurateret memory-index (spec 2026-07-10 Spec B) — samme helper/position som
    # build_visible_stable_prefix (warmer) → byte-identisk, forlænger cache-prefixet
    # forbi identitets-filerne. Fail-safe. Kroppe pulles on-demand via read_memory_topic.
    _mem_index = _curated_memory_index_section(name)
    if _mem_index:
        parts.append(_mem_index)
        derived_inputs.append("curated memory index")

    # Continuity wake-up block — inject after identity block so Jarvis
    # wakes up with felt state from the previous session instead of cold.
    # Only injects if a state capsule exists (not a first-ever start).
    # Compact lane gets a shorter version.
    try:
        from core.services.continuity import build_wake_up_block
        wake_block = build_wake_up_block()
        if wake_block:
            if compact:
                # Compact: only include the first 3 lines (tier + mood + focus)
                wake_lines = wake_block.split("\n")
                compact_wake = "\n".join(wake_lines[:4])
                parts.append(f"▲ WAKE (compact):\n{compact_wake}")
            else:
                parts.append(wake_block)
            derived_inputs.append("continuity wake-up block")
    except Exception:
        pass

    # 2026-05-22 (Claude, Step 2 cache optimisation): conversation
    # continuity, session topics, and current_pull moved to the awareness
    # buffer (queued below, after _awareness_add becomes available). They
    # used to be parts.append'ed here at position ~7500 chars (= 2048
    # tokens), breaking DeepSeek's prompt cache at exactly that boundary.
    # The actual deferred calls are at the "Step-2 cache deferred" block
    # further down — search for that string.

    # Open questions — REMOVED from fixed injection (2026-05-03).
    # Questions are now on-demand via search_memory("åbne spørgsmål") when relevant.
    # This saves ~200-400 chars per prompt and reduces noise.

    # P3: Awareness-section budget. Operational awareness blocks (plan,
    # interrupt, todos, monitors, wake-up digest, self-monitor, side-tasks,
    # subagent digest, scheduled tasks, prev-turn changelog) collect into a
    # bounded list; if total chars exceed _AWARENESS_BUDGET, lowest-priority
    # sections are dropped. Identity (SOUL/IDENTITY/STANDING_ORDERS),
    # nudges, capability truth, etc. are NOT awareness — they live above.
    _awareness: list[tuple[int, str, str]] = []  # (priority, label, content)
    _AWARENESS_BUDGET = 6000  # chars; ~1.5 KT max for the whole awareness block

    # P3.5 (2026-04-29): awareness categories — instead of 30+ flat sections,
    # group by purpose so the model sees a small number of named lanes.
    # Lower _AWARENESS_CATEGORY_ORDER index = appears earlier in output.
    # Categorization is by label substring; unknown labels fall into "general".
    _AWARENESS_CATEGORY_RULES: list[tuple[str, str]] = [
        # indre: protected entity-bearing block (inner voice/network/self-model)
        ("indre liv", "indre"),
        # self-monitor: drift, crisis, self-eval, predictive self-model, dev sense
        ("personality drift", "self-monitor"),
        ("crisis markers", "self-monitor"),
        ("self-evaluation", "self-monitor"),
        ("predictive self-model", "self-monitor"),
        ("developmental sense", "self-monitor"),
        # verification: gates, commitments, direction confirm, self-monitor warnings
        ("self-monitor warnings", "verification"),
        ("verification gate", "verification"),
        ("active commitments", "verification"),
        ("direction confirm", "verification"),
        ("R2.5 conditional", "verification"),
        # reasoning: tier, escalation, R2 telemetry
        ("reasoning tier", "reasoning"),
        ("reasoning escalation", "reasoning"),
        ("R2 gate telemetry", "reasoning"),
        # routing: clarification, context window, provider health
        ("clarification ambiguity", "routing"),
        ("context window", "routing"),
        ("provider health", "routing"),
        # memory: recall, priors, arc rules
        ("recall-before-act", "memory"),
        ("recall before act", "memory"),
        ("priors from your own data", "memory"),
        ("rules learned from arcs", "memory"),
        # calibration: doubt, disagreement
        ("doubt signal", "calibration"),
        ("disagreement invite", "calibration"),
        # operational: todos, plans, wakeups, scheduled, side-tasks, monitor,
        # subagent, prev-turn, interrupt, eventbus wake-up, autonomous goals
        ("resume-after-interrupt", "operational"),
        ("pending plan", "operational"),
        ("all pending plans", "operational"),
        ("active todos", "operational"),
        ("active autonomous goals", "operational"),
        ("fired self-wakeups", "operational"),
        ("previous turn changelog", "operational"),
        ("subagent completion", "operational"),
        ("pinned monitor", "operational"),
        ("upcoming scheduled", "operational"),
        ("flagged side-tasks", "operational"),
        ("eventbus wake-up", "operational"),
    ]
    _AWARENESS_CATEGORY_ORDER = [
        "indre",
        "self-monitor",
        "verification",
        "reasoning",
        "routing",
        "memory",
        "calibration",
        "operational",
        "general",
    ]
    _AWARENESS_CATEGORY_HEADERS = {
        "indre": "[INDRE LIV]",
        "self-monitor": "[SELF-MONITOR]",
        "verification": "[VERIFICATION]",
        "reasoning": "[REASONING]",
        "routing": "[ROUTING]",
        "memory": "[MEMORY-RECALL]",
        "calibration": "[CALIBRATION]",
        "operational": "[OPERATIONAL]",
        "general": "[AWARENESS]",
    }

    def _awareness_category_for(label: str) -> str:
        for needle, category in _AWARENESS_CATEGORY_RULES:
            if needle in label:
                return category
        return "general"

    # Per-section awareness timing — captures elapsed-since-prev-call so we
    # can identify which sections in the synchronous awareness block dominate
    # the ~7.5s sync gap. The 'content' arg has already been evaluated by
    # the caller's expression, so this measures *between* additions — i.e.
    # the work done between the previous _awareness_add return and this call.
    # Added 2026-05-12 to find which of the 50+ inline section builders are
    # the heavy hitters without instrumenting every call site.
    _awareness_call_times: list[tuple[int, str]] = []  # [(elapsed_ms_since_prev, label)]
    _last_awareness_t = [_t_mod.monotonic()]

    # 2026-06-22: raw self-surveillance telemetry (heed-rates, thrash-score,
    # tick scores, adherence %, rule-engine dumps) is cut from the visible
    # prompt. It was "citér aldrig" motor noise that consumed the 6000-char
    # awareness budget and evicted his inner life. The honesty *rule* it
    # implied now lives as one hard line in the stable prefix; the actionable
    # "N unverified mutations" survives via the verification gate.
    # ── Prompt-cluster (Den Intelligente Central, Phase 1, 2026-06-22) ──
    # Den hardcodede _DIAGNOSTIC_NOISE_LABELS-blacklist bliver nu en DEFAULT der kan
    # overstyres LIVE pr. sektion uden genstart (central_switches scope="prompt_section"),
    # og hver drop traces i Centralen. Overrides loades ÉN gang pr. build (prefix-query) →
    # tom i normaltilfældet = nul ekstra latency + uændret adfærd (paritet). INGEN per-sektion
    # decide() (latency) og INGEN ændret sektions-INDHOLD (cache-prefix urørt) — de to risici
    # Jarvis selv flagged er bevidst undgået i Phase 1; gradering/kondensering er Phase 2+.
    from core.services import prompt_observer as _prompt_observer
    _section_overrides = _prompt_observer.load_overrides()
    _dropped_disabled: list[str] = []
    # Sektion-policy udskilt til prompt_observer (Boy Scout 2026-06-23): al noise-
    # policy bor nu ét sted ved siden af section_enabled.
    _DIAGNOSTIC_NOISE_LABELS = _prompt_observer.DIAGNOSTIC_NOISE_LABELS
    _TAIL_NOISE_LABELS = _prompt_observer.TAIL_NOISE_LABELS
    # Prompt-cluster fejl-kanal (2026-06-23): en sektion-builder der kaster fanges
    # lokalt (except pr. sektion, så én dårlig sektion ikke dræber hele prompten) —
    # men var FØR tavs (except: pass). _sec_err gør hvert drop synligt i Centralen.
    _dropped_error: list[tuple[str, str]] = []

    def _sec_err(label: str, exc: BaseException) -> None:
        """En prompt-sektion-builder kastede → synlig i Centralen i stedet for tavst
        drop. Paritet: sektionen kommer stadig ikke med (kun observabilitet ændres)."""
        try:
            _dropped_error.append((label, f"{type(exc).__name__}: {exc}"[:200]))
            _prompt_observer.observe_section_error(label, exc, lane="visible")
        except Exception:
            pass

    # Tråd 2 (Intelligent Central): tur-type til Centralens kontekst-komposition. Beregnes ÉN gang
    # (user_message i scope). Sektionerne her ligger EFTER den cachede stabile prefix (hale) — sikkert.
    try:
        from core.services import central_prompt_composer as _cpc
        _turn_type_l2 = _cpc.classify_turn_type(user_message)
    except Exception:
        _cpc = None
        _turn_type_l2 = "samtale"

    def _awareness_add(priority: int, label: str, content: str | None) -> None:
        _now = _t_mod.monotonic()
        _elapsed_ms = int((_now - _last_awareness_t[0]) * 1000)
        _awareness_call_times.append((_elapsed_ms, label))
        _last_awareness_t[0] = _now
        if _tt is not None and _elapsed_ms > 5:
            _tt.mark("section", label, _elapsed_ms)
        # Prompt-cluster: live on/off pr. sektion (override vinder over hardcoded blacklist).
        if not _prompt_observer.section_enabled(
                label, blacklisted=label in _DIAGNOSTIC_NOISE_LABELS,
                overrides=_section_overrides):
            _dropped_disabled.append(label)
            return
        # Tråd 2: kontekst-komponisten gater pr. tur-type (shadow-default: inkluderer ALT; frosne
        # sektioner aldrig; live+lav-vægt → udelad). Fail-open — skjuler aldrig ved fejl.
        if _cpc is not None:
            try:
                if not _cpc.should_include(_turn_type_l2, label):
                    _dropped_disabled.append(label)
                    return
            except Exception:
                pass
        if not content:
            return
        _awareness.append((priority, label, content))

    # ── Tail-anchored dynamiske sektioner (2026-06-13, cache-fix) ──────
    # Nogle awareness-sektioner re-sampler/ændrer sig per turn (kausal-mønstre,
    # counterfactuals, subagent-completions, rum-entiteter) og brød DeepSeek-
    # cachen ~12-13k tokens inde. _tail_add samler dem så de appendes i den
    # absolutte hale (sammen med finitude/wakeup, lige før time_pin) → den store
    # stabile prefix forbliver cachebar uanset om de skifter.
    _tail_dynamic: list[str] = []
    # Hukommelses-recall (MEMORY.md-selektion + cold-tier private-brain) er
    # per-besked-adaptivt og lå midt i prompten → cache-breaker (2026-06-13
    # lever #4). Samles her og flyttes til bruger-beskeden via den dynamiske
    # hale, så [system + historik] bliver fuldt cachebar. Jarvis ser de
    # relevante minder lige før sit svar — naturlig placering for recall.
    _dyn_memory_recall: list[str] = []

    def _tail_add(label: str, content: str | None) -> None:
        if not content:
            return
        if not _prompt_observer.section_enabled(
                label, blacklisted=label in _TAIL_NOISE_LABELS,
                overrides=_section_overrides):
            _dropped_disabled.append(label)
            return
        _tail_dynamic.append(content)
        derived_inputs.append(f"{label} (tail-anchored)")

    # ── Step-2 cache deferred ──────────────────────────────────────────
    # Conversation continuity, session topics, and current_pull moved
    # here from their original inline parts.append sites further up.
    # Reason: they're per-chat dynamic, and inlining them at ~7500 chars
    # broke the cache boundary at 2048 tokens. Queued through _awareness_add
    # so they flush at the tail of the prompt, just above Time Pin.
    # Bjørn-gate (16. jun 2026): åbne løfter ØVERST i awareness-halen (priority 0)
    # — Jarvis konfronteres med uindfriede løfter før alt andet. Dynamisk →
    # cache-sikkert her. None hvis ingen åbne løfter.
    _awareness_add(0, "åbne løfter (Bjørn-gate)", _pending_promises_section(session_id))
    if current_pull_hint:
        _awareness_add(1, "current pull (inner desire)", current_pull_hint)
    # Indre liv (2026-06-22): protected entity-bearing block — latest inner
    # voice, inner-signal network, self-model. Own "indre" category, exempt
    # from the diagnostic awareness budget below so it is never evicted.
    try:
        from core.services.visible_inner_life import build_inner_life_section
        _awareness_add(1, "indre liv", build_inner_life_section())
    except Exception as _e:
        _sec_err("indre liv", _e)
    try:
        from core.services.continuity import build_conversation_continuity
        _awareness_add(2, "conversation continuity (always-on)",
                       build_conversation_continuity(limit=3))
    except Exception as _e:
        _sec_err("conversation continuity (always-on)", _e)
    try:
        from core.services.session_topic_tracker import build_session_topics_prompt_section
        _awareness_add(3, "session topics (always-on)",
                       build_session_topics_prompt_section(session_id=session_id))
    except Exception as _e:
        _sec_err("session topics (always-on)", _e)

    # Eventbus wake-up digest — DEFERRED to tail (just before time pin).
    # 2026-05-26 (Claude): empirically the only within-session cache breaker
    # (varies turn-to-turn with new event IDs/timestamps). Was at awareness
    # priority 55 → landed at pos ~73 of 88, breaking caching of the final
    # ~14 awareness blocks. Append directly to parts immediately before
    # time_pin so only time_pin itself (which already varies per minute by
    # design) lands after it. See assembly tail near line 1660.
    _wakeup_digest_text: str | None = None
    try:
        from core.services.session_wakeup import wakeup_digest
        _wakeup_digest_text = wakeup_digest(session_id)
    except Exception:
        pass

    # P3: Operational awareness sections — gathered into _awareness with
    # priority numbers (lower = more important). After collection, the
    # budget cap below drops lowest-priority sections if total chars
    # exceed _AWARENESS_BUDGET. Identity (SOUL/IDENTITY/STANDING_ORDERS),
    # nudges, capability truth, etc. are NOT awareness — they live above
    # and below this block and are never trimmed by the budget.
    # Identity pins — survives /compact. Highest awareness priority so
    # they appear before all other context.
    try:
        from core.tools.identity_pin_tools import awareness_section as _id_pin_section
        _pin_text = _id_pin_section()
        if _pin_text:
            _awareness_add(5, "pinned identity context", _pin_text)
    except Exception as _e:
        _sec_err("pinned identity context", _e)

    # Pending nudges from daemons (added 2026-05-13). Closes the spejlsal-
    # bug: heartbeat/outreach/inner-voice/boredom daemons now route through
    # outbound_nudges instead of sending directly. Priority 4 — even higher
    # than loop-compliance (7) and identity pins (5) because these are
    # PENDING context that Jarvis needs to know about before he speaks.
    try:
        from core.services.outbound_nudges import format_pending_for_awareness
        _awareness_add(4, "pending outbound nudges", format_pending_for_awareness() or None)
    except Exception as _e:
        _sec_err("pending outbound nudges", _e)

    # Forbundne plugins/apps — så Jarvis ved han HAR adgang til dem (Bjørn 17. jun).
    try:
        _awareness_add(9, "forbundne apps (plugins)", _connected_connectors_section())
    except Exception as _e:
        _sec_err("forbundne apps (plugins)", _e)

    # Central-notices (spec 2026-06-23 §2): medium-niveau incidents Jarvis bør se da han
    # altid er ved systemet (severe ntfy'es, low er trace-only). Tom = 0 tokens. Prio 10.
    try:
        _awareness_add(10, "central notices", _central_notices_section())
    except Exception as _e:
        _sec_err("central notices", _e)

    # Spec D / D4 (MIDTEN BÆRENDE): Jarvis' awareness bæres FRA Centralens integrerede selv-tilstand
    # (agenda+valens+selv-model+fortælling → ét "jeg"). KUN bag central_self_prompt_enabled (default
    # OFF → None → uændret). Prio 1 (kerne-selv, højt). Inversionen: sindet komponeres fra midten.
    try:
        from core.services.central_self_state import build_central_self_state_section
        _awareness_add(1, "kerne-selv (Centralens midte)", build_central_self_state_section())
    except Exception as _e:
        _sec_err("kerne-selv midte", _e)

    # Loop-compliance self-check (added 2026-05-12). Fires when Jarvis is
    # ignoring his own loop-nudge commitment OR R2-gate heed_rate is low.
    # Priority 7 = right after identity pins so he can't miss it among 50+
    # other awareness sections. See prompt_sections/loop_compliance.py.
    try:
        from core.services.prompt_sections.loop_compliance import loop_compliance_section
        _awareness_add(7, "loop-compliance self-check", loop_compliance_section())
    except Exception as _e:
        _sec_err("loop-compliance self-check", _e)

    # Jarvis Brain — always-on summary af hans egen vidensjournal.
    # Priority 6 = lige efter identity. Repræsenterer "hvad jeg ved nu",
    # er på identitets-tier (persistent selvviden, ikke situational kontekst).
    # Silent skip hvis fil mangler/tom eller feature er disabled.
    try:
        from core.runtime.settings import load_settings as _ls_brain
        _bs = _ls_brain()
        if getattr(_bs, "jarvis_brain_enabled", True):
            from core.services.prompt_sections.jarvis_brain import (
                build_jarvis_brain_section,
            )
            _brain_text = build_jarvis_brain_section(
                token_budget=getattr(_bs, "jarvis_brain_summary_token_budget", 350),
            )
            if _brain_text:
                _awareness_add(6, "jarvis brain summary", _brain_text)

            # Auto-inject relevant fakta (priority 8 — efter summary,
            # før output style). Privacy-gated; silent skip hvis intet
            # over threshold eller hvis feature disabled.
            from core.services.prompt_sections.jarvis_brain_facts import (
                build_brain_facts_section,
            )
            _facts_text = build_brain_facts_section(
                user_message=user_message,
                session_id=session_id,
                # Jarvis' review 2026-06-22: this is now the SINGLE brain section
                # (summary merged out), so give it the full 5 slots.
                top_k=max(5, getattr(_bs, "jarvis_brain_auto_inject_top_k", 5)),
                threshold=getattr(_bs, "jarvis_brain_auto_inject_threshold", 0.55),
            )
            if _facts_text:
                _awareness_add(8, "jarvis brain facts (auto-inject)", _facts_text)

            # Post-web-search nudge — if last tool message had URL content,
            # encourage remember_this. Heuristic; max one per turn since we
            # only inspect the most recent tool message.
            try:
                from core.services.chat_sessions import recent_chat_tool_messages
                from core.services.prompt_sections.jarvis_brain_nudge import (
                    build_brain_post_web_nudge,
                )
                _recent_tools = recent_chat_tool_messages(session_id, limit=1) if session_id else []
                _nudge = build_brain_post_web_nudge(recent_tool_messages=_recent_tools)
                if _nudge:
                    _awareness_add(45, "post-web-search brain nudge", _nudge)
            except Exception as _e:
                _sec_err("post-web-search brain nudge", _e)
    except Exception as _e:
        _sec_err("jarvis brain summary", _e)

    # Dream hypothesis surfacing (2026-06-14, Jarvis-authored spec §2.3 "fix C").
    # Lifts ONE unpresented dream hypothesis from his own dream-consolidation
    # into the conversation. Gated on a real user turn (user_message truthy) so
    # cache-warmer / autonomous builds never consume an unpresented hypothesis
    # Jarvis won't actually see. Low priority (40) — a private/experimental
    # layer that must never outrank the protected core. Marked presented only
    # when genuinely surfaced, so each hypothesis reaches him exactly once.
    if user_message:
        try:
            from core.services.dream_hypothesis_generator import (
                build_dream_hypothesis_prompt_section,
                mark_hypothesis_presented,
            )
            _dream = build_dream_hypothesis_prompt_section()
            if _dream:
                _dream_text, _dream_id = _dream
                # Seraph-teeth (2026-07-10): portvagt for dream-hypotese-synlighed. Default OFF
                # (shadow → altid True, uændret). Enforced → kun modne (confidence≥gulv) vises;
                # umodne holdes tilbage (ikke markeret presented → prøver igen når de modnes).
                _seraph_ok = True
                try:
                    from core.services.central_seraph import may_surface_dream_hypothesis
                    _seraph_ok = may_surface_dream_hypothesis(_dream_id)
                except Exception:
                    _seraph_ok = True
                if _seraph_ok:
                    _awareness_add(40, "dream hypothesis (unpresented)", _dream_text)
                    mark_hypothesis_presented(hypothesis_id=_dream_id)
        except Exception as _e:
            _sec_err("dream hypothesis (unpresented)", _e)

    # Diagnostik (2026-06-23, Bjørn cut-off-jagt): splitter sync_before_relevance_
    # resolve så vi ser om 29s-hænget er i den embedding-tunge brain/facts/dream-blok
    # ovenfor eller i de senere inline-sektioner. Pinpoint → cap som recall.
    _mark("seg_brain_dream_done")

    # Output style hint — comes from JarvisX preferences. Concise =
    # short, dense replies; detailed = longer explanations; technical =
    # more code/structure, less prose.
    try:
        from pathlib import Path as _PP
        from core.runtime.config import CONFIG_DIR as _CD
        import json as _json
        _prefs_path = _PP(_CD) / "jarvisx_prefs.json"
        if _prefs_path.is_file():
            _prefs = _json.loads(_prefs_path.read_text(encoding="utf-8"))
            _style = str(_prefs.get("output_style") or "balanced")
            _style_hints = {
                "concise": "Output style: CONCISE. Bjørn prefers short, dense answers right now. Skip preamble. One paragraph max where possible. Code blocks fine, prose around them minimal.",
                "balanced": "",  # default — no hint needed
                "detailed": "Output style: DETAILED. Bjørn wants thorough explanations. Walk through the reasoning, mention edge cases, give examples.",
                "technical": "Output style: TECHNICAL. Lean into code, types, exact paths, file:line references. Less narrative prose, more concrete artifacts.",
            }
            _hint = _style_hints.get(_style)
            if _hint:
                _awareness_add(7, "output style preference", _hint)
    except Exception as _e:
        _sec_err("output style preference", _e)

    # Markdown-formatering. En backend-normalizer retter inline-struktur, men en
    # nudge reducerer hvor ofte den skal arbejde + holder rå kanal-tekst pæn.
    _awareness_add(7, "markdown formatting", (
        "Formatering: brug RIGTIGE linjeskift i markdown. Hvert listepunkt på sin "
        "egen linje (\\n- punkt), og afsnit adskilt af en blank linje. Skriv ALDRIG "
        "en hel liste eller flere afsnit som én lang linje med ' - ' inline — det "
        "rendrer som sammenklistret tekst."
    ))

    # Tool-echo-leak. Når du har kaldt et værktøj, så FORTOLK resultatet med dine
    # egne ord — gentag ALDRIG den rå tool-output som prosa i dit svar. Linjer der
    # starter med '[tool_navn]:' eller '[tool_result:...]' er interne markører og
    # må aldrig stå i din synlige besked til brugeren.
    _awareness_add(7, "no tool-result echo", (
        "Tool-resultater: efter et værktøjskald, sammenfat resultatet med dine EGNE "
        "ord. Gentag ALDRIG den rå output (fx '[list_proposals]: …' eller "
        "'[tool_result:…]') i dit synlige svar — det er interne markører."
    ))

    try:
        from core.identity.project_context import current_project_root
        _project_root = current_project_root()
        if _project_root:
            # Read project-scoped notes (.jarvisx/notes.md) so persistent
            # lessons about THIS codebase survive across sessions even
            # after /compact strips the chat history.
            _project_notes_block = ""
            try:
                from pathlib import Path as _P
                _notes_path = _P(_project_root).expanduser() / ".jarvisx" / "notes.md"
                if _notes_path.is_file():
                    _raw = _notes_path.read_text(encoding="utf-8", errors="replace")
                    # Cap at 8 KB in awareness — bigger and we burn budget
                    if len(_raw) > 8000:
                        _raw = _raw[:8000] + "\n\n[…truncated; full notes via read_project_notes tool]"
                    if _raw.strip():
                        _project_notes_block = (
                            "\n\nProject-specific notes (from .jarvisx/notes.md, "
                            "your accumulated lessons about THIS codebase):\n\n"
                            f"{_raw.strip()}\n"
                        )
            except Exception:
                pass

            _awareness_add(
                8,
                "JarvisX project anchor",
                (
                    "Bjørn is currently working in the JarvisX desktop app and has "
                    f"anchored to the project **{_project_root}**.\n"
                    "When he asks about \"the file\", \"the project\", \"here\" or uses "
                    "relative paths — that's the folder he means. "
                    "bash commands should run from there (cd there if not already). "
                    "edit_file/read_file/write_file with relative paths are relative "
                    "to this folder. You don't need to mention the anchor explicitly — "
                    "just act as if you're in that folder."
                    + _project_notes_block
                ),
            )
    except Exception as _e:
        _sec_err("JarvisX project anchor", _e)
    try:
        from core.services.in_flight_runs import interruption_prompt_section
        _awareness_add(
            10,
            "resume-after-interrupt notice",
            interruption_prompt_section(session_id, user_message=user_message),
        )
    except Exception as _e:
        _sec_err("resume-after-interrupt notice", _e)
    try:
        from core.services.plan_proposals import pending_plan_section
        _awareness_add(15, "pending plan awaiting approval", pending_plan_section(session_id))
    except Exception as _e:
        _sec_err("pending plan awaiting approval", _e)
    try:
        from core.services.plan_proposals import all_pending_plans_section
        _awareness_add(17, "all pending plans (incl. auto-proposals)", all_pending_plans_section())
    except Exception as _e:
        _sec_err("all pending plans (incl. auto-proposals)", _e)
    try:
        from core.services.self_monitor import self_monitor_section
        _awareness_add(20, "self-monitor warnings", self_monitor_section())
        # 2026-05-23 (Claude, Step E.v1): metacognitive monitor surface.
        # Quiet by default — only appears when recent contradiction-rate or
        # claim-density are out-of-band. Same priority bucket as
        # self-monitor since both are quality signals about own reasoning.
        try:
            from core.services.metacognition_signal_tracker import (
                latest_signals_section,
            )
            _awareness_add(21, "metacognition signals", latest_signals_section())
        except Exception as _e:
            _sec_err("metacognition signals", _e)
        # 2026-05-23 (Claude, Step A.v1): theory-of-mind communication
        # ledger. Quiet by default — surfaces only when Jarvis has
        # repeated the same fact 3+ times to partner within 1 hour.
        try:
            from core.services.theory_of_mind import (
                communication_ledger_section,
            )
            _awareness_add(22, "communication ledger", communication_ledger_section())
        except Exception as _e:
            _sec_err("communication ledger", _e)
        # 2026-05-23 (Claude, Step D.v1): spatial entity ledger.
        # Surfaces top-observed room entities from Sansernes Arkiv when
        # ≥3 entities have been observed.
        try:
            from core.services.spatial_entity_ledger import (
                room_entities_section,
            )
            _tail_add("room entities", room_entities_section())
        except Exception as _e:
            _sec_err("room entities", _e)
    except Exception as _e:
        _sec_err("self-monitor warnings", _e)
    try:
        from core.services.clarification_classifier import clarification_prompt_section
        _awareness_add(25, "clarification ambiguity flag", clarification_prompt_section(user_message))
    except Exception as _e:
        _sec_err("clarification ambiguity flag", _e)
    try:
        from core.services.reasoning_classifier import reasoning_tier_section
        _awareness_add(22, "reasoning tier recommendation", reasoning_tier_section(user_message))
    except Exception as _e:
        _sec_err("reasoning tier recommendation", _e)
    # NB: R2 (verification_gate_section) er FLYTTET ind i den konsoliderede graderede
    # Proactivity-gate nedenfor (central().decide → YELLOW @ slot 23). Ikke længere en
    # separat injektion her. (Proactivity-cluster konsolidering 2026-06-22.)
    try:
        from core.services.verification_gate_telemetry import telemetry_section
        _awareness_add(24, "R2 gate telemetry", telemetry_section())
    except Exception as _e:
        _sec_err("R2 gate telemetry", _e)
    try:
        from core.services.decision_adherence_gate import decision_adherence_section
        _awareness_add(25, "decision adherence gate", decision_adherence_section())
    except Exception as _e:
        _sec_err("decision adherence gate", _e)
    try:
        from core.services.memory_consolidation_nudge import memory_consolidation_nudge_section
        _awareness_add(24, "memory consolidation nudge", memory_consolidation_nudge_section())
    except Exception as _e:
        _sec_err("memory consolidation nudge", _e)
    try:
        from core.services.prompt_sections.forgetting_nudge import forgetting_nudge_section
        _awareness_add(24, "forgetting nudge", forgetting_nudge_section(session_id))
    except Exception as _e:
        _sec_err("forgetting nudge", _e)
    try:
        # Wire forward-chaining symbolic rule_engine into prompt (2026-05-08).
        # Engine + 36 rules existed since 8860301 but weren't reaching the LLM.
        # Top-5 fired conclusions injected as awareness-line — first
        # neuro-symbolic layer that actually surfaces to Jarvis.
        from core.services.prompt_sections.rule_conclusions import (
            rule_conclusions_section,
        )
        from core.services.central_injection_registry import injection_live, read_injection
        if injection_live("rule_conclusions"):
            _rule_text = read_injection("rule_conclusions")          # baggrunds-cached (~0ms)
        else:
            _rule_text = rule_conclusions_section()                  # gammel direkte build (rollback)
        _awareness_add(28, "rule engine conclusions", _rule_text or None)
    except Exception as _e:
        _sec_err("rule engine conclusions", _e)
    try:
        # Causal alerts — surface failure-event chains for recent failures.
        # Phase 1 of causal graph wiring (2026-05-08).
        from core.services.prompt_sections.causal_alerts import (
            causal_alerts_section,
        )
        _awareness_add(30, "causal alerts", causal_alerts_section())
    except Exception as _e:
        _sec_err("causal alerts", _e)
    try:
        # Causal narrative — surface "how you landed here" backward chain
        # from the most recent narrative-worthy anchor event. Phase 2 of
        # causal graph wiring (2026-05-08). Procedural; no LLM call on
        # critical path; 5-min TTL cache.
        from core.services.prompt_sections.causal_narrative import (
            causal_narrative_section,
        )
        _awareness_add(25, "causal narrative", causal_narrative_section())
    except Exception as _e:
        _sec_err("causal narrative", _e)
    try:
        # Causal patterns — surface recurring (parent → child) flows over
        # the last 7 days. Phase 3 of causal graph wiring (2026-05-08):
        # cross-session temporal substrate. Plumbing edges and test-data
        # prefixes are filtered out so what survives is narrative-meaningful.
        # Procedural; 30-min TTL cache (frequency-stat, not real-time).
        from core.services.prompt_sections.causal_patterns import (
            causal_patterns_section,
        )
        _tail_add("causal patterns", causal_patterns_section())
    except Exception as _e:
        _sec_err("causal patterns", _e)
    try:
        # Model-pools: så Jarvis ALWAYS kender forskellen på agent pool (gratis
        # arbejdskraft + betalt til kode; dét agent-drevet arbejde trækker fra) og
        # cheap lane (gratis-only), + live-health. Volatil → hale (cache-sikker).
        from core.services.prompt_sections.pool_status_section import pool_status_line
        _tail_add("model pools", pool_status_line())
    except Exception as _e:
        _sec_err("model pools", _e)
    try:
        # Pattern counterfactuals — surface "what if this pattern stopped?"
        # hypotheses generated by pattern_counterfactual_daemon (Phase 3.5,
        # 2026-05-08). One step deeper than causal_patterns: not just "this
        # recurs" but "here's what you'd lose if it stopped".
        from core.services.prompt_sections.pattern_counterfactuals import (
            pattern_counterfactuals_section,
        )
        _tail_add("pattern counterfactuals", pattern_counterfactuals_section())
    except Exception as _e:
        _sec_err("pattern counterfactuals", _e)
    try:
        # Cross-session arc — last N user-facing chat sessions as a
        # chronological arc, so Jarvis can sense "we've been working
        # on this for days" instead of starting cold each session.
        # Procedural; reads chat_sessions table directly. (2026-05-08)
        from core.services.prompt_sections.cross_session_arc import (
            cross_session_arc_section,
        )
        _awareness_add(18, "cross-session arc", cross_session_arc_section())
    except Exception as _e:
        _sec_err("cross-session arc", _e)
    try:
        # ── Proactivity-cluster: R2/R2.5 verifikations-disciplin GENNEM Centralen ──
        # Konsolideret GRADERET gate (R2 blød = YELLOW @ slot 23, R2.5 hård = RED @
        # slot 95) routet gennem central().decide → fuld catch+flag+notify+trace.
        # Erstatter de to tidligere SEPARATE injektioner (R2 @ slot 23 + R2.5 @ slot 95).
        from core.services.reasoning_classifier import classify_reasoning_tier
        from core.services.central_core import central as _central_prov
        from core.services.gate_proactivity import proactivity_gate as _prov_gate
        from core.services.gate_kernel import Decision as _PDec
        _tier = str(classify_reasoning_tier(user_message).get("tier") or "fast")
        _pv = _central_prov().decide("verification", {"reasoning_tier": _tier},
                                     _prov_gate, cluster="proactivity")
        _ptext = (_pv.evidence or {}).get("text")
        if _ptext and _pv.decision in (_PDec.RED, _PDec.YELLOW):
            _pprio = int((_pv.evidence or {}).get("priority")
                         or (95 if _pv.decision is _PDec.RED else 23))
            _plabel = ("R2.5 conditional block" if _pv.decision is _PDec.RED
                       else "verification gate signals")
            _awareness_add(_pprio, _plabel, _ptext)
    except Exception as _e:
        _sec_err("verification gate (R2/R2.5)", _e)

    # Reflection nudge — runs only when a project is anchored AND the
    # current turn looks substantive (we cap noise by only firing when
    # there's actual project context). Suggests writing distilled
    # takeaways to project notes if anything meaningful was learned.
    try:
        from core.identity.project_context import current_project_root as _cpr
        if _cpr():
            _awareness_add(
                97,
                "reflection nudge",
                (
                    "If you learned something specific about THIS project this turn — "
                    "an architecture quirk, a convention Bjørn uses here, a gotcha — "
                    "consider calling `update_project_notes` with a short distillation. "
                    "Notes survive /compact and appear in your awareness next time you "
                    "anchor to the same project. Keep it short: distilled "
                    "lessons, not a session transcript."
                ),
            )
    except Exception as _e:
        _sec_err("reflection nudge", _e)
    try:
        from core.services.decision_enforcement import enforcement_section
        _awareness_add(90, "active commitments enforcement", enforcement_section())
    except Exception as _e:
        _sec_err("active commitments enforcement", _e)
    # Bisektions-markør (2026-06-23, cut-off-jagt): splitter 995-1679 så næste cut
    # isolerer 28,7s-hænget til [causal/rule/clarification-halvdel] vs [pushback/
    # escalation/channel-halvdel].
    _mark("seg_mid_done")
    # 2026-06-09: development_sense (Vækstpuls med live decimal-tal)
    # flyttet til tail-anchored — samme cache-breaker årsag.
    try:
        from core.services.pushback import (
            affective_pushback_section,
            doubt_signal_section,
            disagreement_invite_section,
            direction_confirm_section,
        )
        from core.services.reasoning_classifier import classify_reasoning_tier
        _ptier = str(classify_reasoning_tier(user_message).get("tier") or "fast")
        _awareness_add(75, "doubt signal", doubt_signal_section(user_message))
        _awareness_add(70, "disagreement invite", disagreement_invite_section())
        _awareness_add(78, "affective pushback", affective_pushback_section(user_message))
        _awareness_add(85, "direction confirm gate",
                       direction_confirm_section(
                           user_message=user_message, reasoning_tier=_ptier,
                       ))
        # Affect-modulated runtime parameters — emotions gate behavior
        try:
            from core.services.affect_modulation import affect_modulation_section as _affect_mod
            _affect_mod_section = _affect_mod()
            if _affect_mod_section:
                _awareness_add(80, "affect modulation", _affect_mod_section)
        except Exception as _e:
            _sec_err("affect modulation", _e)
    except Exception as _e:
        _sec_err("doubt signal", _e)
    try:
        from core.services.reasoning_escalation import escalation_section
        _awareness_add(24, "reasoning escalation recommendation", escalation_section(user_message))
    except Exception as _e:
        _sec_err("reasoning escalation recommendation", _e)
    try:
        from core.services.context_window_manager import context_window_section
        _awareness_add(26, "context window degradation signal", context_window_section())
    except Exception as _e:
        _sec_err("context window degradation signal", _e)
    # Fix 2 (2026-04-27): recall_before_act in visible runs — was only used
    # in heartbeat phases. Surface relevant memories tied to user_message so
    # Jarvis answers from memory, not stub-context.
    try:
        from core.services.memory_hierarchy import recall_before_act_summary
        if user_message and len(user_message.strip()) >= 8:
            # Query-adaptiv recall → bruger-besked-halen (lever #4 cache-fix),
            # ikke awareness (som rendres før historikken).
            # Hård 4s deadline (29. jun, CUT-OFF-ROD): denne recall laver embed/DB-
            # kald der UNDER ollama-kontention (baggrunds frame/cognitive_state-
            # futures mætter samme ollama) kø'ede 20-26s INLINE i q3-segmentet →
            # frøs --workers 1 → cut-off for ALLE brugere (verificeret på Mikkels
            # session). Var den ENESTE uncappede recall i q3 (multi_signal har
            # allerede 4s-cap). Samme tråd-deadline-mønster; synlig i Centralen.
            import threading as _thr_rba
            import contextvars as _cv_rba
            _rba_box: dict = {}
            # Kopiér caller-context (user_context → current_user_id) ind i den rå tråd, ellers
            # fejler recall-kilden 'workspace' lydløst (16.jul). copy_context fanges HER (inde i
            # kaldernes user_context) og køres via ctx.run i tråden.
            _rba_ctx = _cv_rba.copy_context()

            def _do_rba() -> None:
                try:
                    _rba_box["v"] = _rba_ctx.run(recall_before_act_summary, query=user_message)
                except Exception:
                    pass

            _rt = _thr_rba.Thread(target=_do_rba, name="recall-before-act", daemon=True)
            _rt.start()
            _rt.join(4.0)
            if _rt.is_alive():
                try:
                    from core.services.central_core import central
                    central().observe({
                        "cluster": "prompt", "nerve": "phase_timeout",
                        "phase": "recall_before_act", "timeout_s": 4.0,
                    })
                except Exception:
                    pass
            _rba = _rba_box.get("v")
            if _rba:
                _dyn_memory_recall.append(_rba)
                derived_inputs.append("recall-before-act (user-msg tail)")
    except Exception:
        pass
    # Multi-signal recall (B1, 2026-06-08) — Claude 2026-06-09: B1 module
    # (multi_signal_retrieval.py + 214 lines integration in
    # memory_recall_engine.py) was built and tested but never wired into
    # any prompt section. Now surfaced as a complementary recall using
    # BM25 + entity + embedding fusion. Lower priority than
    # recall-before-act since this is "wider net", not user-message-specific.
    try:
        from core.services.memory_recall_engine import multi_signal_recall_section
        if user_message and len(user_message.strip()) >= 8:
            _awareness_add(28, "multi-signal recall (BM25+entity+embedding)",
                           multi_signal_recall_section(user_message) or None)
    except Exception as _e:
        _sec_err("multi-signal recall (BM25+entity+embedding)", _e)
    # Phase 1 — proactive auto-compact at 70% threshold (best-effort, cooldown-protected)
    # Guard: ALDRIG compaction som bivirkning af en pre-warm-build (session_prewarm /
    # assembly_prewarm sætter is_prewarm_active()). Ellers ville en cache-warm kunne
    # trigge en rigtig compaction af brugerens session — forbudt (pollution).
    try:
        from core.services.assembly_prewarm import is_prewarm_active as _is_prewarm
        _prewarming = _is_prewarm()
    except Exception:
        _prewarming = False
    if not _prewarming:
        try:
            from core.services.proactive_context_governor import auto_compact_if_needed
            auto_compact_if_needed()  # silent — runs only if needed
        except Exception:
            pass
    try:
        from core.services.autonomous_goals import goals_prompt_section
        _awareness_add(35, "active autonomous goals", goals_prompt_section())
    except Exception as _e:
        _sec_err("active autonomous goals", _e)
    try:
        from core.services.self_wakeup import self_wakeup_section
        _awareness_add(12, "fired self-wakeups", self_wakeup_section())
    except Exception as _e:
        _sec_err("fired self-wakeups", _e)
    try:
        from core.services.personality_drift import personality_drift_section
        _awareness_add(45, "personality drift signal", personality_drift_section())
    except Exception as _e:
        _sec_err("personality drift signal", _e)
    try:
        from core.services.crisis_marker_detector import crisis_marker_section
        _awareness_add(48, "crisis markers (last 7 days)", crisis_marker_section())
    except Exception as _e:
        _sec_err("crisis markers (last 7 days)", _e)
    try:
        from core.services.provider_health_check import health_section
        _awareness_add(28, "provider health status", health_section())
    except Exception as _e:
        _sec_err("provider health status", _e)
    # 2026-06-09: self_evaluation_section flyttet til tail-anchored —
    # samme grund som predictive_self_model (live tick-quality scores
    # med decimal-precision der ændrer sig per heartbeat). Bevares som
    # vitalt indre liv men placeres sidst så cachen ikke brydes.
    # 2026-06-09: predictive_self_model_section flyttet til tail-anchored
    # (efter time_pin) fordi den indeholder live tick-quality scores der
    # opdateres hver heartbeat — ÉT decimal-skifte (65.6 → 65.5) brød
    # 13% af DeepSeek prefix-cache. Live-investigationen viste at det
    # var den primære cache-breaker. Bevar sektionen som "vital indre
    # liv" — bare flyt til prompt-end så cachen ikke ødelægges.
    # Implementeret nedenfor ved siden af time_pin.
    try:
        from core.services.priors_feedback import priors_feedback_section
        _awareness_add(55, "priors from your own data", priors_feedback_section())
    except Exception as _e:
        _sec_err("priors from your own data", _e)
    try:
        from core.services.arc_rule_extractor import arc_rules_section
        _awareness_add(60, "rules learned from arcs", arc_rules_section())
    except Exception as _e:
        _sec_err("rules learned from arcs", _e)
    # Removed 2026-04-29: redundant unconditional recall_before_act_summary() call.
    # With no query, that function returns only the "active goals" hot-tier slice,
    # which is already surfaced separately at prio 35 via goals_prompt_section().
    # The user-message-keyed call at prio 27 above remains — that one does real
    # cold-tier semantic recall and is the load-bearing one.
    try:
        from core.services.agent_todos import todos_prompt_section
        _awareness_add(30, "active todos", todos_prompt_section(session_id))
    except Exception as _e:
        _sec_err("active todos", _e)
    # Multi-step planner Phase 1 (added 2026-05-12) — other-session plan resumption
    try:
        from core.services.plan_proposals import format_cross_session_plans_for_awareness
        _awareness_add(
            35,
            "cross-session plans awaiting resumption",
            format_cross_session_plans_for_awareness(session_id) or None,
        )
    except Exception as _e:
        _sec_err("cross-session plans awaiting resumption", _e)
    # World Model loop Phase 1 (2026-05-12) — prediction/resolution nudges
    try:
        from core.services.world_model_signal_tracking import (
            format_world_model_nudges_for_awareness,
        )
        _awareness_add(
            36,
            "world-model prediction/resolution nudges",
            format_world_model_nudges_for_awareness(session_id=session_id) or None,
        )
    except Exception as _e:
        _sec_err("world-model prediction/resolution nudges", _e)
    # World Model loop Phase 1 (2026-05-12) — calibration milestone (one-shot)
    try:
        from core.services.world_model_signal_tracking import (
            format_world_model_milestone_for_awareness,
        )
        _awareness_add(
            37,
            "world-model calibration milestone",
            format_world_model_milestone_for_awareness() or None,
        )
    except Exception as _e:
        _sec_err("world-model calibration milestone", _e)
    # Plan-revision patterns (2026-05-13) — recurring reasons cluster
    try:
        from core.services.prompt_sections.plan_revision_patterns import (
            plan_revision_patterns_section,
        )
        _awareness_add(44, "plan-revision recurring patterns", plan_revision_patterns_section() or None)
    except Exception as _e:
        _sec_err("plan-revision recurring patterns", _e)
    # Dead-skill detector fjernet (spec 2026-07-05): dead_skills_section byggede
    # prompt-tekst om skills der aldrig invokes — ren spild, ingen værdi.
    # Skill chain proposals (C3, 2026-06-09) — heartbeat-generated chain
    # suggestions. Claude 2026-06-09: format_chain_proposals() existed
    # but had zero callers — generated chains were never surfaced. Hooked
    # next to dead_skills for logical grouping (both are skill metadata).
    try:
        from core.services.heartbeat_phases import format_chain_proposals
        _awareness_add(44, "skill chain proposals", format_chain_proposals() or None)
    except Exception as _e:
        _sec_err("skill chain proposals", _e)
    # Curiosity consolidation (2026-05-13) — weekly synthesis of observations
    try:
        from core.services.curiosity_consolidation import latest_consolidation_for_awareness
        _awareness_add(
            42,
            "curiosity consolidation (weekly)",
            latest_consolidation_for_awareness() or None,
        )
    except Exception as _e:
        _sec_err("curiosity consolidation (weekly)", _e)
    # Meta-læring Phase 2 (2026-05-13) — active hypotheses Jarvis is testing
    try:
        from core.services.meta_learning_hypotheses import (
            format_active_hypotheses_for_awareness,
        )
        _awareness_add(
            41,
            "active hypotheses (meta-learning)",
            format_active_hypotheses_for_awareness() or None,
        )
    except Exception as _e:
        _sec_err("active hypotheses (meta-learning)", _e)
    # Lag 3 (2026-07-02) — Centralens SELV-GENEREREDE governed hypoteser om Jarvis selv (observe-only)
    try:
        from core.services.central_hypothesis_generator import (
            format_governed_hypotheses_for_awareness,
        )
        _awareness_add(
            41,
            "central self-generated hypotheses (Lag 3)",
            format_governed_hypotheses_for_awareness() or None,
        )
    except Exception as _e:
        _sec_err("central self-generated hypotheses (Lag 3)", _e)
    # Curiosity-budget Phase 1 (2026-05-12) — idle-window invitation (AGI #6)
    try:
        from core.services.curiosity_budget import (
            format_curiosity_window_for_awareness,
        )
        _awareness_add(
            38,
            "curiosity-budget idle-window invitation",
            format_curiosity_window_for_awareness() or None,
        )
    except Exception as _e:
        _sec_err("curiosity-budget idle-window invitation", _e)
    # Meta-læring Phase 1 (2026-05-12) — weekly retrospective teaser (AGI #3)
    try:
        from core.services.meta_learning_retrospective import (
            format_latest_unacknowledged_memo_for_awareness,
        )
        _awareness_add(
            39,
            "meta-learning weekly retrospective teaser",
            format_latest_unacknowledged_memo_for_awareness() or None,
        )
    except Exception as _e:
        _sec_err("meta-learning weekly retrospective teaser", _e)
    _mark("seg_q3_done")  # bisektion #3 (cut-off-jagt): 1286-1520 vs 1520-1679
    try:
        from core.services.turn_changelog import previous_turn_changelog_section
        _awareness_add(40, "previous turn changelog (ground truth)", previous_turn_changelog_section(session_id))
    except Exception as _e:
        _sec_err("previous turn changelog (ground truth)", _e)
    try:
        from core.services.subagent_digest import subagent_digest_section
        _tail_add("subagent completion digest", subagent_digest_section(session_id))
    except Exception as _e:
        _sec_err("subagent completion digest", _e)
    try:
        from core.services.monitor_streams import monitor_digest_section
        _awareness_add(60, "pinned monitor digest", monitor_digest_section(session_id))
    except Exception as _e:
        _sec_err("pinned monitor digest", _e)
    try:
        from core.services.scheduled_tasks import get_scheduled_tasks_state
        sched_state = get_scheduled_tasks_state()
        pending = sched_state.get("pending") or []
        if pending:
            shown = pending[:5]
            lines = []
            for t in shown:
                run_at = str(t.get("run_at", ""))[:16].replace("T", " ")
                focus = str(t.get("focus", ""))[:120]
                lines.append(f"⏰ {run_at}  {focus}")
            extra = f"  (+{len(pending) - len(shown)} mere)" if len(pending) > len(shown) else ""
            _awareness_add(70, "upcoming scheduled tasks",
                "Kommende self-scheduled wake-ups (du har sat dem selv):\n"
                + "\n".join(lines) + extra)
    except Exception as _e:
        _sec_err("upcoming scheduled tasks", _e)
    try:
        from core.services.side_tasks import side_tasks_prompt_section
        _awareness_add(80, "flagged side-tasks", side_tasks_prompt_section())
    except Exception as _e:
        _sec_err("flagged side-tasks", _e)

    # 2026-05-22 (Claude, Step 2 cache optimisation): temperature field +
    # response-style modifier are per-chat dynamic (they update every turn from
    # user_temperature_engine signals). Inlining them mid-prompt broke DeepSeek's
    # cache at ~7500 chars, so they route through the awareness buffer to flush
    # at the tail. NB: they MUST be _awareness_add'ed BEFORE the flush loop below
    # (2026-07-06 fix) — previously they were added after the loop had already
    # consumed _awareness, so they silently never reached _awareness_buffer and
    # were dropped from every visible prompt.
    temperature_hint = _visible_unconscious_temperature_field_section()
    if temperature_hint:
        _awareness_add(4, "implicit user temperature field", temperature_hint)

    response_style_hint = _visible_response_style_hint_section()
    if response_style_hint:
        _awareness_add(5, "response style modifier from temperature", response_style_hint)

    # Apply the budget cap. Highest-priority sections always survive (even
    # if alone they exceed the budget); later/lower-priority entries are
    # dropped to make room. Dropped labels logged via derived_inputs so MC
    # can see what got squeezed out this turn.
    #
    # P3.5 (2026-04-29): items are grouped by category. Sort key is
    # (category-order, priority) so categories appear in a predictable
    # sequence and items within a category preserve priority ordering.
    # A short header is emitted before the first surviving item of each
    # category, giving the model structural cues without changing content.
    _category_order_index = {c: i for i, c in enumerate(_AWARENESS_CATEGORY_ORDER)}
    _awareness.sort(
        key=lambda x: (
            _category_order_index.get(_awareness_category_for(x[1]), 99),
            x[0],
        )
    )
    # Tråd 2: egress-frit substrat — hvor mange hale-sektioner blev komponeret denne tur (til
    # fremtidig relevans-hypotese-generering). Kun skalarer/tur-type, aldrig prompt-indhold.
    if _cpc is not None:
        try:
            _incl = len(_awareness)
            _cpc.observe_composition(_turn_type_l2, sections_total=_incl + len(_dropped_disabled),
                                     sections_included=_incl,
                                     included_labels=[_lbl for _p, _lbl, _c in _awareness])
        except Exception:
            pass
    # Buffer awareness output instead of writing directly to parts (2026-05-07).
    # Awareness sections contain second-resolution timestamps and other rapidly
    # varying content — appending them mid-assembly broke Deepseek's prefix
    # cache after only ~2k tokens. Buffer here, flush at the END of assembly
    # so all stable workspace-file sections (chronicle, milestones, finitude,
    # mutation, etc.) land inside the cacheable prefix first.
    _used = 0
    _dropped: list[str] = []
    _last_category: str | None = None
    _awareness_buffer: list[str] = []
    # Entity-bearing "indre" life renders in its OWN buffer (2026-06-22): never
    # dropped, free of the diagnostic awareness budget, and placed above the
    # "INTERN DIAGNOSTIK — citér aldrig" header with its own framing. His inner
    # voice must not lose the budget war to R2-gate telemetry, nor be labelled
    # as suppressed background data — it is him, not his motor.
    _inner_buffer: list[str] = []
    for _prio, _label, _content in _awareness:
        _category = _awareness_category_for(_label)
        if _category == "indre":
            _inner_buffer.append(_content)
            derived_inputs.append(_label)
            continue
        _pending_header = (
            _AWARENESS_CATEGORY_HEADERS.get(_category, "")
            if _category != _last_category else ""
        )
        _needed = len(_content) + (len(_pending_header) + 2 if _pending_header else 0)
        # Valgt historik (2026-06-22): Jarvis' egne identity-pins har forrang —
        # de droppes aldrig af budgettet. Auto-udvalgte brain-facts fylder resten.
        _never_drop = _label == "pinned identity context"
        if not _never_drop and _used > 0 and _used + _needed > _AWARENESS_BUDGET:
            _dropped.append(_label)
            continue
        if _pending_header:
            _awareness_buffer.append(_pending_header)
            _used += len(_pending_header) + 2  # +2 for "\n\n" join overhead
        _awareness_buffer.append(_content)
        derived_inputs.append(_label)
        _used += len(_content)
        _last_category = _category
    if _dropped:
        derived_inputs.append(f"awareness budget dropped: {', '.join(_dropped)}")
    # Prompt-cluster: ét central.observe pr. build → trace af hvad der kom med + hvorfor noget
    # blev droppet (disabled via switch vs budget-evicted). Self-safe; ingen latency-effekt.
    try:
        _prompt_observer.observe_build(
            lane="visible", included=len(_awareness_buffer),
            dropped_disabled=_dropped_disabled, dropped_budget=list(_dropped),
            dropped_error=_dropped_error)
    except Exception:
        pass

    # SOUL/IDENTITY/STANDING_ORDERS/USER.md were moved forrest (2026-05-07)
    # to fix Deepseek prefix-caching. See block above the awareness budget
    # for the new injection point.

    # (temperature field + response-style modifier moved above the awareness
    # flush loop on 2026-07-06 — see note there. They were previously here,
    # after the flush, and were silently dropped.)

    chronicle_section = _visible_chronicle_context_section()
    if chronicle_section:
        parts.append(chronicle_section)
        conditional_files.append("CHRONICLE.md")
        derived_inputs.append("chronicle continuity")

    try:
        from core.services.life_milestones import build_life_history_prompt_section
        milestones_section = build_life_history_prompt_section()
        if milestones_section:
            parts.append(milestones_section)
            conditional_files.append("MILESTONES.md")
            derived_inputs.append("life milestones")
    except Exception:
        pass

    # Beregnes her, men APPENDES i prompt-halen (lige før wakeup-digest + time
    # pin) — se længere nede. 2026-06-13 (cache-fix): "### Looming-end /
    # Sessions-alder: N timer" ændrer sig over tid og lå ~6.2k tokens inde i
    # prompten → det var DeepSeek-cachens første breaker (cap'ede prefix til ~6k
    # og dræbte caching af resten af system-prompten + HELE historikken). Flyttet
    # til halen sammen med de øvrige per-turn-variable sektioner.
    finitude_section = _visible_finitude_context_section()

    dream_residue_section = _visible_dream_residue_section()
    if dream_residue_section:
        parts.append(dream_residue_section)
        derived_inputs.append("dream residue carry-over")

    # Visual memory — Lag 6: cut from the prefix 2026-06-22. The room now lives
    # in the [INDRE LIV] block (visible_inner_life._room_line) where Jarvis
    # actually attends, instead of duplicated as a quiet background hint up here.

    channel_section = _channel_context_section(session_id)
    if channel_section:
        parts.append(channel_section)
        derived_inputs.append("channel context")

    mutation_section = _self_mutation_lineage_section()
    if mutation_section:
        # CACHE-FIX (2026-07-17): the timestamped self-change list churns every time
        # an edit/write is staged → it sat in the cacheable HEAD (offset ~83%) and
        # busted the whole history downstream. Tail-anchor it (after the sentinel),
        # same discipline as 030ad902.
        _tail_add("self mutation lineage", mutation_section)

    _mark("before_relevance_resolve")
    # Resolve relevance — blocks until the bounded NL prompt relevance call
    # returns, but happens concurrently with fast file reads above.
    relevance = _timed_result(future_relevance, "relevance", default=_permissive_relevance(mode="visible_chat"))
    _mark("after_relevance_resolve")

    # --- Phase 2: launch relevance-dependent Ollama calls in parallel ---
    future_memory_selection = (
        _measured_submit(
            "memory_selection",
            _workspace_memory_section,
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            user_message=user_message,
            max_lines=3 if compact else 4,
            max_chars=200 if compact else 280,
            workspace_dir=workspace_dir,
            mode="visible_chat",
        )
        if relevance.include_memory
        else None
    )
    future_recall_bundle = (
        _measured_submit(
            "recall_bundle",
            _visible_memory_recall_bundle_section,
            session_id=session_id,
            user_message=user_message,
            compact=compact,
        )
        if relevance.include_memory
        else None
    )
    # Bridge-decision future fjernet (spec 2026-07-05): builderen yielder ALTID
    # line=None på visible-lanen (full-support-mode) → submit+resolve var ren spild.

    if relevance.include_memory:
        memory_selection = _timed_result(
            future_memory_selection, "memory_selection",
            max_s=_HOT_RESOLVE_CAP_S, default=None,
        )
        if memory_selection:
            # Per-besked-adaptivt → flyttes til bruger-beskeden (lever #4 cache-fix),
            # IKKE parts.append her midt i prompten.
            _dyn_memory_recall.append(
                "\n".join(
                    ["MEMORY.md:", *[f"- {line}" for line in memory_selection.lines]]
                )
            )
            conditional_files.append("MEMORY.md")
            if memory_selection.prompt_file_used:
                conditional_files.append("VISIBLE_MEMORY_SELECTION.md")
            if memory_selection.backend_success:
                derived_inputs.append("bounded NL memory entry selection")
            elif memory_selection.fallback_used:
                derived_inputs.append("heuristic memory entry selection fallback")

        # Daily memory sidecar — rolling short-lived notes. Read separately
        # from MEMORY.md so reboot/session boundaries do not drop recent work.
        daily_lines = _recent_daily_memory_lines(limit=8 if compact else 12)
        if daily_lines:
            # CACHE-FIX (2026-07-17): the daily file is appended ~130×/day (every
            # run-end incl. autonomous heartbeat/dream/wakeup runs) → the newest-N
            # window shifted between the owner's composer turns → the biggest visible
            # cache-buster (busted head+history, ~36% vs agent's 92%). Tail-anchor it.
            _tail_add(
                "daily memory sidecar",
                "\n".join(
                    [
                        "Recent daily notes (memory/daily, newest 7-day window):",
                        *[f"  {line}" for line in daily_lines],
                    ]
                ),
            )

        recall_bundle = _timed_result(
            future_recall_bundle, "recall_bundle",
            max_s=_HOT_RESOLVE_CAP_S, default=None,
        )
        if recall_bundle:
            # 2026-06-13 (lever #4): flyttet HELT ud af system-beskeden til
            # bruger-beskeden (var i awareness-tail, men awareness rendres stadig
            # før historikken → cap'ede live-cachen ved ~14k). Private-brain-
            # excerpts churner hvert turn; nu sidder de lige før Jarvis' svar.
            _dyn_memory_recall.append(recall_bundle)
            derived_inputs.append("bounded memory recall bundle (user-msg tail)")

    if relevance.include_guidance:
        for filename in ("TOOLS.md", "SKILLS.md"):
            section = _workspace_guidance_section(
                workspace_dir / filename,
                label=filename,
                max_lines=2 if compact else 3,
                max_chars=180 if compact else 240,
            )
            if section:
                # 2026-06-30 (cache-fix): include_guidance er relevans-gatet
                # (per-besked). At appende guidance i system-blokken indsatte en
                # VARIABEL sektion midt i det ellers stabile prefix og forskød alt
                # efter → brød DeepSeek-cachen ~23k tegn inde (system-blok 82%
                # stabil → realistisk per-tur-hit kun 71%, ceiling 99.7%). Flyt til
                # den dynamiske hale: [system + tools + historik] forbliver fuldt
                # byte-stabilt/cachebart, og guidance vises stadig lige før Jarvis'
                # svar når beskeden er tool/skill-relevant — naturlig placering.
                _tail_add(f"{filename} guidance", section)
                conditional_files.append(filename)

    # --- Budget-controlled runtime sections ---
    # Workspace files (SOUL, IDENTITY, memory, rules, transcript) are
    # assembled above outside budget control — they are foundational.
    # Runtime-derived sections go through the attention budget selector.

    budget_profile = "visible_compact" if compact else "visible_full"

    continuity_content = (
        _visible_session_continuity_instruction()
        if relevance.include_continuity
        else None
    )
    # 2026-05-22 (Claude): defer visible session continuity to tail. Live
    # cache diff found it broke prefix at byte ~16,299 with churning
    # latest_finished_at timestamps + recent-session topic list. The model
    # still sees it via _awareness flush — just much later in prompt.
    if continuity_content:
        _awareness_add(35, "visible session continuity", continuity_content)
        continuity_content = None  # remove from budget-selection path

    self_report_content = _timed_result(future_self_report, "self_report")

    support_raw = _visible_support_signal_sections(
        compact=compact,
        include=relevance.include_support_signals,
        user_message=user_message,
        session_id=session_id,
    )
    support_content = "\n\n".join(support_raw) if support_raw else None

    bridge_content = None  # spec 2026-07-05: altid None på visible-lane

    frame_content = _timed_result(future_frame, "frame")

    # Build structured transcript messages for multi-turn injection
    structured_transcript = _build_structured_transcript_messages(
        session_id,
        limit=50 if compact else 60,
        include=relevance.include_transcript,
    )
    # Legacy flat-text fallback (kept for system prompt when structured not available)
    transcript_content = _recent_transcript_section(
        session_id,
        limit=50 if compact else 60,
        include=relevance.include_transcript,
    ) if not structured_transcript else None

    # --- Cognitive State (accumulated personality, bearing, taste, rhythm) ---
    # Submitted as a future at function entry; resolve here.
    _mark("before_heavy_resolves")
    if _skip_cog_build:
        # Adaptiv assembly: simpel/kode-tur → hverken build ELLER injection-read.
        cognitive_state_content = None
    elif _cog_live:
        cognitive_state_content = read_injection("cognitive_state") or None
    else:
        # Kold/frossen-vindue-værn: cap builden hårdt; hænger den, fald tilbage til sidste
        # cachede injection-tekst (frisk-ish, aldrig load-bearing) i st. f. at betale ~8s.
        cognitive_state_content = _timed_result(
            future_cognitive_state, "cognitive_state",
            default=(read_injection("cognitive_state") or None),
            max_s=_COGNITIVE_STATE_BUILD_CAP_S,
        )
    # Real-time self-state numbers (decision adherence, goal progress, tick
    # quality). Without this Jarvis confabulates pessimistic answers when
    # asked introspective questions in chat — claims 0% adherence when DB
    # shows 60%, claims stale goals when none are stale, etc.
    self_state_content = _timed_result(
        future_self_state, "self_state",
        max_s=_HOT_RESOLVE_CAP_S, default=None,
    )
    _mark("after_heavy_resolves")
    # 2026-05-22 (Claude): defer cognitive_state + self_state to tail.
    # Live cache diff round-2 found COGNITIVE STATE block at byte ~14,936
    # toggled the "agens:" line on/off per-turn (conditional on recent
    # agency invocation), breaking cache from 94% → 33% on alternating
    # calls. Same defer pattern as recall_bundle/visible_continuity in
    # round-1 — both blocks are runtime state that's still semantically
    # useful at tail (after stable identity/tools).
    if cognitive_state_content:
        _awareness_add(40, "cognitive state", cognitive_state_content)
        cognitive_state_content = None
    if self_state_content:
        _awareness_add(41, "self state numbers", self_state_content)
        self_state_content = None
    # 2026-05-26 (Claude): defer cognitive_frame to awareness tail same way.
    # Live cache audit found cognitive_frame at pos ~55 (before tool catalog)
    # is the worst per-turn cache breaker — LLM-generated routing/mode advice
    # that varies every turn, breaking the ~6k-token tool catalog from
    # caching. Same defer pattern as cognitive_state/self_state above.
    if frame_content:
        _awareness_add(42, "cognitive frame", frame_content)
        frame_content = None

    raw_sections = {
        "capability_truth": capability_truth,
        "output_discipline": _output_discipline,
        "cognitive_frame": frame_content,
        "cognitive_state": cognitive_state_content,
        "self_state": self_state_content,
        "self_report": self_report_content,
        "inner_visible_bridge": bridge_content,
        "support_signals": support_content,
        "continuity": continuity_content,
        # These are heartbeat-only; supply None so budget correctly omits them
        "private_brain": None,
        "self_knowledge": None,
        "liveness": None,
    }

    selected, attention_trace_obj = _run_budget_selection(
        profile=budget_profile,
        sections=raw_sections,
    )

    # Assemble budget-selected sections in priority order
    _section_labels = {
        "capability_truth": "runtime capability and safety truth",
        "output_discipline": "tiered output discipline (synthesize/stop; conciseness on strong lanes)",
        "cognitive_frame": (
            "micro cognitive frame (compact)"
            if compact
            else "bounded cognitive frame (mode, salience, affordances)"
        ),
        "cognitive_state": "accumulated cognitive state (personality, bearing, taste, rhythm)",
        "self_state": "real-time self-state numbers (decisions, goals, tick quality)",
        "self_report": "grounded runtime self-report support",
        "inner_visible_bridge": "bounded inner visible prompt bridge",
        "support_signals": "bounded runtime support signals",
        "continuity": "bounded session continuity",
    }
    for sec_name in (
        "capability_truth",
        "output_discipline",
        "cognitive_frame",
        "cognitive_state",
        "self_state",
        "self_report",
        "inner_visible_bridge",
        "support_signals",
        "continuity",
    ):
        content = selected.get(sec_name)
        if content:
            parts.append(content)
            label = _section_labels.get(sec_name, sec_name)
            derived_inputs.append(label)

    # Transcript: prefer structured messages; fall back to flat text in system prompt
    # 2026-05-22 (Claude): re-ordered so stable-content (transcript, tool
    # catalog) lands BEFORE awareness flush. Original code claimed
    # awareness was "bagest" but measurement showed it landed at ~37-45%
    # of the prompt, with transcript + tool_catalog (the stable parts)
    # coming AFTER it. That meant awareness was the cache-killer in the
    # middle. Moving awareness to land RIGHT BEFORE Time Pin (the
    # absolute tail) keeps the entire stable middle cacheable.
    if structured_transcript:
        derived_inputs.append(f"structured transcript ({len(structured_transcript)} messages)")
    elif transcript_content:
        parts.append(transcript_content)
        derived_inputs.append("recent transcript slice (flat text fallback)")

    # Tool catalog — always-on compact list of all tool names so Jarvis knows
    # what exists even when tool_router scopes the full schemas to a subset.
    # Best-effort: never breaks prompt assembly.
    try:
        from core.services.tool_catalog import build_catalog_text as _build_catalog_text
        _catalog_text = _build_catalog_text()
        if _catalog_text:
            parts.append(_catalog_text)
            derived_inputs.append("tool catalog (compact)")
    except Exception:
        pass

    # jarvis-code Path B: tilføj surfaces EGEN 3-lags-toolbox-forklaring (native=Bjørns
    # maskine / runtime_*=container / operator_*=bro). Desk-katalogen ovenfor forklarer
    # desks model — samme tool-navn betyder noget ANDET her, så uden dette bliver Jarvis
    # forvirret (Bjørn: sektionen om runtime_* manglede helt). Statisk + kun på jarvis-
    # code-surfacen → cache-sikker pr. surface.
    try:
        from core.tools.tool_scoping import current_local_exec
        if current_local_exec():
            from core.tools.jc_tool_catalog import build_jc_catalog_text
            _jc_text = build_jc_catalog_text()
            if _jc_text:
                parts.append(_jc_text)
                derived_inputs.append("jarvis-code toolbox model (3-target)")
    except Exception:
        pass

    # Flush buffered awareness sections HERE — true tail position, after
    # all stable-content (workspace files, transcript, tool catalog).
    # Time Pin (appended below the assembled_text print block) is the
    # only thing that lands after this — and Time Pin is always at the
    # very end so the model sees it right before user_message. This
    # ordering maximises DeepSeek prompt-cache hits on the stable prefix
    # while keeping awareness in "handlings-mode" (Jarvis' own framing)
    # immediately above the timestamp + user turn.
    # 2026-06-13 (lever #4): awareness-laget appendes IKKE til system-prompten
    # her længere — det er per-turn-adaptivt (reasoning-tier, verifikations-gates,
    # kalibrering, hukommelse) og lå ~14k tokens inde → cap'ede DeepSeek-cachen
    # FØR historikken. Flyttes nu som blok til bruger-beskeden via den dynamiske
    # hale (se _dyn_tail nedenfor), så [system + historik] bliver fuldt cachebar.
    # Awareness står nu lige før Jarvis' tur — stadig i "handlings-mode", bare
    # tættere på selve turen. Måles via R2-gate strict/light-efterlevelse.

    executor.shutdown(wait=False)

    _mark("after_assembly_complete")
    _total_ms = int((_t_mod.monotonic() - _t_assembly_start) * 1000)
    if _tt is not None:
        _tt.mark("assembly_end", "assembly complete", _total_ms)
    _phases_str = " ".join(f"{k}_ms={v}" for k, v in sorted(_phase_timings.items()))
    # Compute sync-gap deltas between consecutive landmarks (work that the
    # main thread did while parallel futures ran). _sync_landmarks keys
    # are wall-clock-from-start, so deltas show elapsed-since-prev.
    _ordered_marks = [
        "after_phase1_submit",
        "seg_brain_dream_done",
        "seg_mid_done",
        "seg_q3_done",
        "before_relevance_resolve",
        "after_relevance_resolve",
        "before_heavy_resolves",
        "after_heavy_resolves",
        "after_assembly_complete",
    ]
    _gaps: list[str] = []
    _prev_t = 0
    for _name in _ordered_marks:
        if _name in _sync_landmarks:
            _delta = _sync_landmarks[_name] - _prev_t
            _gaps.append(f"sync_{_name}_ms={_delta}")
            _prev_t = _sync_landmarks[_name]
    _gaps_str = " ".join(_gaps)
    print(
        f"prompt-assembly-timing total_ms={_total_ms} {_phases_str} {_gaps_str}",
        file=_sys_mod.stderr,
        flush=True,
    )

    # Top-10 slowest awareness sections by elapsed-since-prev. The label is
    # what was JUST added — the elapsed time is the work it took to build.
    # Helps identify which of the 50+ inline section builders dominate.
    try:
        _top = sorted(_awareness_call_times, key=lambda x: x[0], reverse=True)[:10]
        _top_str = " ".join(f"{lbl.replace(' ', '_')}={ms}" for ms, lbl in _top if ms > 50)
        if _top_str:
            print(
                f"prompt-assembly-awareness-top10 {_top_str}",
                file=_sys_mod.stderr,
                flush=True,
            )
    except Exception:
        pass

    # Sentinel-gated FULD timing-dump (diagnostik, inert uden sentinel-fil).
    # `touch /tmp/jarvis-assembly-timing` → næste assembly skriver HELE listen
    # (hver sektion + fase + landmark m. ms) til .../latest.json. Ryd sentinel bagefter.
    try:
        import os as _os_dump
        if _os_dump.path.exists("/tmp/jarvis-assembly-timing"):
            import json as _json_dump
            _dump = {
                "total_ms": _total_ms,
                "phase_timings_ms": dict(_phase_timings),
                "sync_landmarks_ms": dict(_sync_landmarks),
                "awareness_section_count": len(_awareness_call_times),
                "awareness_total_ms": sum(_m for _m, _ in _awareness_call_times),
                "awareness_sections_ms": sorted(
                    [{"label": _lbl, "ms": _m} for _m, _lbl in _awareness_call_times],
                    key=lambda _x: -_x["ms"]),
            }
            _dd = "/tmp/jarvis-assembly-timing-dumps"
            _os_dump.makedirs(_dd, exist_ok=True)
            with open(_dd + "/latest.json", "w", encoding="utf-8") as _fh:
                _json_dump.dump(_dump, _fh, ensure_ascii=False, indent=1)
    except Exception:
        pass

    # P1 instrumentation: measure system-prompt size before returning. Pure
    # observation — no behavior change. Emits an eventbus event so MC and
    # the wakeup digest can both surface bloat. Per-part chars logged so
    # we can see which sections dominate without instrumenting every
    # parts.append site.

    # finitude_section + _wakeup_digest_text appendes IKKE her længere — de er
    # per-turn-dynamiske og flyttes til bruger-beskeden via sentinel-blokken
    # nedenfor (2026-06-13 cache-fix, lever #3). Se den samlede dynamiske hale.

    # 2026-06-09: Vital-indre-liv block — tre sektioner med live
    # decimal-tal der ændrer sig per heartbeat (Tick-kvalitet 65.6→65.5,
    # Vækstpuls 0.39→0.19, decision adherence etc.). Når de stod i
    # awareness-blokken brød de DeepSeek prefix-cachen ~87% ind i
    # prompten — kostede 90%+ af cachen pr. tur (8% hit rate observeret).
    # Tail-anchored bevarer dem synligt for modellen ("vitalt indre liv")
    # uden at sabotere cache for de stable sections før dem.
    # 2026-07-16 (cache-fix, målt): _dyn_tail initialiseres HER — før de fem
    # "tail-anchored"-labelede sektioner. Tidligere lå init'en NEDENFOR dem, så de
    # (med live decimal-metrikker: Tick-kvalitet/Vækstpuls) endte i HOVEDET og bustede
    # DeepSeek prefix-cachen (visible 35.9% hit, byte-diff: første divergens = tick-metrik).
    # Nu ægte i halen → historik-cachen bevares → mål ~90% som agent-lanen.
    _dyn_tail: list[str] = []
    try:
        from core.services.self_model_predictive import predictive_self_model_section
        _empirical_self = predictive_self_model_section()
        if _empirical_self:
            _dyn_tail.append(_empirical_self)
            derived_inputs.append("predictive self-model empirical (tail-anchored)")
    except Exception:
        pass
    try:
        from core.services.agent_self_evaluation import self_evaluation_section
        _self_eval = self_evaluation_section()
        if _self_eval:
            _dyn_tail.append(_self_eval)
            derived_inputs.append("self-evaluation summary (tail-anchored)")
    except Exception:
        pass
    try:
        from core.services.development_sense import development_sense_section
        _dev_sense = development_sense_section()
        if _dev_sense:
            _dyn_tail.append(_dev_sense)
            derived_inputs.append("developmental sense (tail-anchored)")
    except Exception:
        pass

    # Communication Guard — boundary-fraser (godnat, sov godt, ...) Bjørn
    # ikke vil høre. Høj-salient og tæt på user-turn, fordi STANDING_ORDERS
    # alene ikke holdt (glemmes over lang prompt). Den bløde defense; hård
    # blok sker ved kanal-dispatch (enforce_outgoing).
    try:
        from core.services.communication_guard import prompt_section as _cg_section
        _guard = _cg_section()
        if _guard:
            _dyn_tail.append(_guard)
            derived_inputs.append("communication guard (tail-anchored)")
    except Exception:
        pass

    # Tool-output hygiejne (A1 i v2-stream Phase 2): deepseek-flash har en
    # tendens til at papegøje det rå tool-resultat-format ([read_file]: …)
    # ind i sit synlige svar. Det er kun til modellens egne øjne.
    _dyn_tail.append(
        "🔧 TOOL-OUTPUT: Resultater fra værktøjer (fx '[read_file]: …', rå "
        "fil-dumps, JSON) er KUN til dig. Gengiv dem ALDRIG ordret i dit svar — "
        "referer til indholdet med dine egne ord."
    )
    derived_inputs.append("tool-output hygiene (tail-anchored)")

    # ── Narrations-kontrakt (ReAct-mønster): TÆNK-før-HANDL + syntese mellem runder.
    # Kode/billig-modeller (deepseek/kimi/glm) emitter tool_calls TERST uden ledsagende
    # prosa (ToolExchange.text er ofte tom) → Bjørn ser en runde starte uden at vide
    # hvad Jarvis giver sig i kast med. Claude narrerer af sig selv; de andre skal
    # KRÆVES det. Tail-anchored (før de tunge markører) → overlever lean-transformen
    # så den gælder ALLE agentiske runder, og statisk → cache-sikker. (Reinforces per
    # runde af den korte nudge på tool-resultaterne, se visible_followup.)
    _dyn_tail.append(
        "🎬 ARBEJDSGANG (gælder HVER runde): Før du kalder værktøjer, skriv FØRST "
        "én kort sætning om hvad du er ved at gøre og hvorfor. Efter en runde med "
        "tool-resultater: skriv én kort syntese af hvad du fandt og hvad det "
        "betyder, FØR du starter næste runde. Kør ALDRIG en runde tavst — Bjørn "
        "skal kunne følge din tankegang undervejs, ikke kun se slutresultatet."
    )
    derived_inputs.append("narration contract / ReAct (tail-anchored)")

    # ── Per-turn-dynamisk hale → flyttes til BRUGER-beskeden (2026-06-13, lever #3)
    # ALT der varierer fra turn til turn samles her, EFTER al stabil tekst, bag en
    # sentinel. _build_visible_input splitter på sentinel'en og flytter blokken ud
    # på den sidste bruger-besked. Så bliver HELE system-prompten + historikken én
    # stabil cachebar prefix; kun den nye tur er en miss.
    #   Indhold (alt dynamisk): finitude/Sessions-alder, wakeup-digest (events),
    #   kausal-mønstre/counterfactuals/subagent/rum-entiteter, og time_pin.
    # _dyn_tail er allerede initialiseret ovenfor (før de fem tail-anchored sektioner,
    # 2026-07-16 cache-fix) — må IKKE re-initialiseres her, ellers tabes de appends.
    # 2026-06-22 (Jarvis' egen review): han skal møde SIG SELV først. [INDRE LIV]
    # øverst sætter tonen for hvordan han læser alt det andet — han taler FRA sin
    # tilstand, ikke fra recall. Memory/brain-recall flyttet ned under awareness
    # (før var recall det allerførste han mødte).
    if _inner_buffer:
        _dyn_tail.extend(_inner_buffer)
    # Hele awareness-laget (reasoning/verifikation/kalibrering m.m.) — flyttet hertil
    # fra system-prompten (lever #4) så det ikke cap'er cachen før historikken.
    if _awareness_buffer:
        # 2026-06-13 (Jarvis' egen analyse): selv-referentielle diagnostik-data
        # (R2-heed-rate, recall-størrelse, metakognition, format-regler) ligger
        # her og fik ham til at NARRERE briefingen tilbage til brugeren i stedet
        # for bare at bruge den ("min hjerne er massiv", "51 advarsler..."). En
        # eksplicit header markerer blokken som stum baggrund. NB: tekst-nudge —
        # effekt MÅLES, antages ikke (jf. R2-gatens lave heed-rate).
        _dyn_tail.append(
            "📊 INTERN DIAGNOSTIK — baggrundsbriefing, IKKE et samtaleemne.\n"
            "Brug det nedenstående til at forme dit svar. Citér eller kommentér "
            "det ALDRIG (R2-tal, heed-rate, recall-størrelse, format-regler, "
            "metakognition, Sansernes Arkiv) medmindre Bjørn eksplicit spørger "
            "til din tilstand. Det er din motor, ikke din passager."
        )
        _dyn_tail.extend(_awareness_buffer)
        derived_inputs.append("diagnostik-header (anti-narration, Jarvis-spec)")
    # Memory/brain-recall EFTER awareness (Jarvis-review 2026-06-22): han taler
    # fra sin tilstand, ikke fra recall — så recall hører hjemme her, ikke øverst.
    _dyn_tail.extend(_dyn_memory_recall)
    if finitude_section:
        _dyn_tail.append(finitude_section)
        derived_inputs.append("finitude (user-msg tail)")
    if _wakeup_digest_text:
        _dyn_tail.append(_wakeup_digest_text)
        derived_inputs.append("wakeup digest (user-msg tail)")
    _dyn_tail.extend(_tail_dynamic)
    try:
        from core.identity.workspace_context import current_user_id as _cuid
        # uid SKAL matche det presence/routing er keyed under (session-ejeren).
        # current_user_id() er ofte TOM for owner inde i run-generatoren (samme
        # grund som operator-tools' owner-fallback) → summary("") gav "Ingen aktiv
        # enhed" selvom presence havde enheder. Fald tilbage til session-ejeren.
        _pres_uid = ""
        if session_id:
            try:
                from core.services.chat_sessions import get_session_owner
                _pres_uid = get_session_owner(session_id) or ""
            except Exception:
                pass
        if not _pres_uid:
            _pres_uid = _cuid() or ""
        _presence_line = _device_presence_line(_pres_uid)
        if _presence_line:
            _dyn_tail.append(_presence_line)
            derived_inputs.append("device-presence (user-msg tail)")
        # Override-banner (spec 2026-06-21 §7): når TOTP-override er aktivt skal Jarvis
        # VIDE at han er elevet til owner i en andens session — så han handler som
        # owner (sudo/operator/mutationer), men privatlivs-scoping forbliver intakt.
        # Kun når aktiv → ingen cache-støj på normale ture.
        try:
            from core.services import override_store as _ovs_p
            if session_id and _ovs_p.is_active(session_id):
                _owner_nm = ""
                try:
                    from core.identity.users import find_user_by_discord_id as _fu
                    _u = _fu(_pres_uid)
                    _owner_nm = (getattr(_u, "name", "") or "") if _u else ""
                except Exception:
                    pass
                _dyn_tail.append(
                    "[override: AKTIV — Bjørn (owner) TOTP-verificeret i session tilhørende: "
                    f"{_owner_nm or 'anden bruger'}. Du må handle som owner (sudo/operator/"
                    "mutationer), men privatlivs-scoping forbliver — du kan IKKE læse andres "
                    "private data.]"
                )
                derived_inputs.append("override banner (user-msg tail)")
        except Exception:
            pass
    except Exception:
        pass
    # Behavioral anchor (2026-06-22) — echoed into the dynamic tail right before
    # the user message because Jarvis reported he attends to the tail (his "now")
    # and didn't *feel* the honesty/tool rule sitting in the cacheable prefix.
    # Compact, point-of-action reminder; the full rule still lives in the prefix.
    _dyn_tail.append(
        "⚖️ FØR DU SVARER: Påstå ALDRIG du gjorde noget (skrev/sendte/kørte/"
        "rettede) uden et tool-kald i SAMME tur der beviser det — ellers sig "
        "præcist hvad du gjorde og hvad du IKKE nåede. Kald værktøjer struktureret "
        "(tool_calls), aldrig som inline-tekst. Gør, lov ikke."
    )
    derived_inputs.append("behavioral anchor (user-msg tail)")
    # Epistemisk afholdenhed echoed i halen (point-of-action) — Jarvis attenderer
    # "sit nu" stærkest her. Mod gætteriet (DeepSeek afstår sjældent af sig selv).
    _dyn_tail.append(
        "🎯 Usikker på et FAKTUM (navn/tal/dato/citat/kommando/API/sti)? Sig 'det "
        "ved jeg ikke' eller slå det op FØR du svarer — gæt aldrig en plausibel "
        "detalje. Ærligt 'ved ikke' > flydende forkert."
    )
    derived_inputs.append("epistemic abstention anchor (user-msg tail)")
    _dyn_tail.append(_time_pin_section())
    derived_inputs.append("time pin (user-msg tail)")
    # Matrix Nudges — i stedet for den gamle ensemble-label-liste postes der nu
    # nudges via nudge_broend. Kun en indikatorlinje i prompt-halen hvis nogen
    # har noget at sige. Karaktererne dukker op i awareness via nudge-systemet.
    try:
        from core.services.central_matrix_ensemble import push_active_character_nudges as _push_matrix_nudges
        _nudge_count = _push_matrix_nudges()
        if _nudge_count > 0:
            _dyn_tail.append(f"🎬 Matrix: {_nudge_count} karakter(er) har meldinger — tjek pending nudges.")
            derived_inputs.append("matrix character nudges indicator (tail)")
    except Exception:
        pass
    # Matrix Sign-Off — automatisk karakter-signatur i bunden af svar.
    # Kører EFTER labels-sektionen så sign-off'en har karakterernes kontekst.
    try:
        from core.services.central_matrix_ensemble import build_matrix_signoff_section as _signoff_fn
        _signoff = _signoff_fn()
        if _signoff:
            _dyn_tail.append(_signoff)
            derived_inputs.append("matrix sign-off instruction (tail)")
    except Exception:
        pass
    if _dyn_tail:
        parts.append(DYNAMIC_TAIL_SENTINEL)
        parts.extend(_dyn_tail)

    _assembled_text = "\n\n".join(part for part in parts if part).strip()
    _total_chars = len(_assembled_text)
    _approx_tokens = _total_chars // 4  # rough heuristic — close enough for triage
    _per_part_chars = [len(p) for p in parts if p]
    _largest = sorted(
        ((label, len(parts[i]) if i < len(parts) else 0)
         for i, label in enumerate(derived_inputs)),
        key=lambda kv: kv[1], reverse=True,
    )[:8]
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("prompt.assembly_size", {
            "mode": "visible_chat",
            "compact": compact,
            "total_chars": _total_chars,
            "approx_tokens": _approx_tokens,
            "part_count": len(_per_part_chars),
            "largest_sections": [
                {"label": label, "chars": chars} for label, chars in _largest if chars > 0
            ],
            "assembly_ms": _total_ms,
        })
    except Exception:
        pass
    print(
        f"prompt-assembly-size chars={_total_chars} approx_tokens={_approx_tokens} "
        f"parts={len(_per_part_chars)}",
        file=_sys_mod.stderr,
        flush=True,
    )

    # TEMP-DIAG: gated system-prompt dump (touch /tmp/jarvis-prompt-dump), rotates
    # latest→prev so two consecutive assemblies can be diffed to find what MUTATES
    # in the deepseek-cached prefix (cache 98%→73%). Fires for ALL visible paths.
    try:
        import os as _os_pd2
        if _os_pd2.path.exists("/tmp/jarvis-prompt-dump"):
            _dd2 = "/tmp/jarvis-prompt-dumps"
            _os_pd2.makedirs(_dd2, exist_ok=True)
            if _os_pd2.path.exists(_dd2 + "/sys_latest.txt"):
                try:
                    _os_pd2.replace(_dd2 + "/sys_latest.txt", _dd2 + "/sys_prev.txt")
                except Exception:
                    pass
            with open(_dd2 + "/sys_latest.txt", "w", encoding="utf-8") as _fh_pd2:
                _fh_pd2.write(_assembled_text)
    except Exception:
        pass

    return PromptAssembly(
        mode="visible_chat",
        text=_assembled_text,
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
        attention_trace=attention_trace_obj.summary(),
        transcript_messages=structured_transcript or None,
    )


def build_heartbeat_prompt_assembly(
    *,
    heartbeat_context: dict[str, object] | None = None,
    name: str = "default",
) -> PromptAssembly:
    workspace_dir = ensure_default_workspace(name=name)
    contract = build_runtime_contract_state(name=name)
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = [
        "runtime/RUNTIME_FEEDBACK.md",
        "boredom_templates.json",
        "full transcript",
        "heavy private/internal dumps",
    ]
    relevance = build_prompt_relevance_decision(
        "heartbeat",
        mode="heartbeat",
        compact=False,
        name=name,
    )

    parts.append(_heartbeat_runtime_truth_instruction(heartbeat_context or {}))
    derived_inputs.append("runtime heartbeat policy, schedule, and budget truth")

    if contract.get("bootstrap", {}).get("status") == "active":
        bootstrap = _workspace_file_section(
            workspace_dir / "BOOTSTRAP.md",
            label="BOOTSTRAP.md",
            max_lines=4,
            max_chars=260,
        )
        if bootstrap:
            parts.append(bootstrap)
            conditional_files.append("BOOTSTRAP.md")

    for filename in (
        "HEARTBEAT.md",
        "SOUL.md",
        "IDENTITY.md",
        "STANDING_ORDERS.md",
        "USER.md",
    ):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=4,
            max_chars=260,
        )
        if section:
            parts.append(section)
            included_files.append(filename)

    if relevance.include_memory:
        memory_selection = _workspace_memory_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            user_message="heartbeat proposal check",
            max_lines=4,
            max_chars=260,
            workspace_dir=workspace_dir,
            mode="heartbeat",
        )
        if memory_selection:
            parts.append(
                "\n".join(
                    ["MEMORY.md:", *[f"- {line}" for line in memory_selection.lines]]
                )
            )
            conditional_files.append("MEMORY.md")
            if memory_selection.prompt_file_used:
                conditional_files.append("VISIBLE_MEMORY_SELECTION.md")
            if memory_selection.backend_success:
                derived_inputs.append("bounded NL memory entry selection")
            elif memory_selection.fallback_used:
                derived_inputs.append("heuristic memory entry selection fallback")

        # Daily memory sidecar for heartbeat prompts too, so proactive
        # decisions can reference today's context without pulling in
        # the full long-term memory file.
        daily_lines = _recent_daily_memory_lines(limit=10)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Recent daily notes (memory/daily, newest 7-day window):",
                        *[f"  {line}" for line in daily_lines],
                    ]
                )
            )
            derived_inputs.append("daily memory sidecar")

    # Due summary is always included (scheduling truth, not runtime-derived)
    due_summary = _heartbeat_due_summary(heartbeat_context or {})
    if due_summary:
        parts.append(due_summary)
        derived_inputs.append("due schedules and open-loop summary")

    # --- Budget-controlled runtime sections ---
    hb_ctx = heartbeat_context or {}
    raw_sections = {
        "capability_truth": _heartbeat_capability_truth_instruction(hb_ctx),
        "continuity": _heartbeat_continuity_summary(hb_ctx),
        "liveness": _heartbeat_liveness_summary(hb_ctx),
        "private_brain": _heartbeat_private_brain_section(hb_ctx),
        "self_knowledge": _heartbeat_self_knowledge_section(),
        "cognitive_frame": _cognitive_frame_section(),
        # These are visible-only; supply None for correct budget omission
        "self_report": None,
        "support_signals": None,
        "inner_visible_bridge": None,
    }

    selected, attention_trace_obj = _run_budget_selection(
        profile="heartbeat",
        sections=raw_sections,
    )

    _hb_labels = {
        "capability_truth": "compact capability truth",
        "continuity": "optional compact continuity summary",
        "liveness": "bounded heartbeat liveness support",
        "private_brain": "bounded private brain continuity context",
        "self_knowledge": "bounded runtime self-knowledge map",
        "cognitive_frame": "bounded cognitive frame (mode, salience, affordances)",
    }
    for sec_name in (
        "capability_truth",
        "cognitive_frame",
        "private_brain",
        "self_knowledge",
        "continuity",
        "liveness",
    ):
        content = selected.get(sec_name)
        if content:
            parts.append(content)
            derived_inputs.append(_hb_labels.get(sec_name, sec_name))

    return PromptAssembly(
        mode="heartbeat",
        text="\n\n".join(part for part in parts if part).strip(),
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
        attention_trace=attention_trace_obj.summary(),
    )


def build_future_agent_task_prompt_assembly(
    *,
    task_brief: str,
    agent_context: dict[str, object] | None = None,
    name: str = "default",
) -> PromptAssembly:
    workspace_dir = ensure_default_workspace(name=name)
    context = agent_context or {}
    parts: list[str] = []
    included_files: list[str] = []
    conditional_files: list[str] = []
    derived_inputs: list[str] = []
    excluded_files = [
        "BOOTSTRAP.md",
        "HEARTBEAT.md",
        *DEFAULT_EXCLUDED_FILES,
        "full transcript",
    ]
    relevance = build_prompt_relevance_decision(
        task_brief,
        mode="future_agent_task",
        compact=False,
        name=name,
    )

    runtime_truth = _future_agent_runtime_truth_instruction(context)
    if runtime_truth:
        parts.append(runtime_truth)
        derived_inputs.append("runtime role, scope, and capability truth")

    for filename in ("SOUL.md", "IDENTITY.md", "STANDING_ORDERS.md"):
        section = _workspace_file_section(
            workspace_dir / filename,
            label=filename,
            max_lines=4,
            max_chars=260,
        )
        if section:
            parts.append(section)
            included_files.append(filename)

    if context.get("include_user", True):
        user_section = _workspace_file_section(
            workspace_dir / "USER.md",
            label="USER.md",
            max_lines=3,
            max_chars=220,
        )
        if user_section:
            parts.append(user_section)
            conditional_files.append("USER.md")

    parts.append(
        "\n".join(
            [
                "Delegated task brief:",
                f"- {str(task_brief or '').strip() or 'No task brief provided.'}",
            ]
        )
    )

    if relevance.include_memory:
        memory_selection = _workspace_memory_section(
            workspace_dir / "MEMORY.md",
            label="MEMORY.md",
            user_message=str(task_brief or "delegated task"),
            max_lines=4,
            max_chars=240,
            workspace_dir=workspace_dir,
            mode="future_agent_task",
        )
        if memory_selection:
            parts.append(
                "\n".join(
                    ["MEMORY.md:", *[f"- {line}" for line in memory_selection.lines]]
                )
            )
            conditional_files.append("MEMORY.md")
            if memory_selection.prompt_file_used:
                conditional_files.append("VISIBLE_MEMORY_SELECTION.md")
            if memory_selection.backend_success:
                derived_inputs.append("bounded NL memory entry selection")
            elif memory_selection.fallback_used:
                derived_inputs.append("heuristic memory entry selection fallback")

        # Daily memory sidecar so delegated agents see today's session
        # context, not just long-term curated facts.
        daily_lines = _recent_daily_memory_lines(limit=10)
        if daily_lines:
            parts.append(
                "\n".join(
                    [
                        "Recent daily notes (memory/daily, newest 7-day window):",
                        *[f"  {line}" for line in daily_lines],
                    ]
                )
            )
            derived_inputs.append("daily memory sidecar")

    if relevance.include_guidance or context.get("include_guidance"):
        for filename in ("TOOLS.md", "SKILLS.md"):
            section = _workspace_guidance_section(
                workspace_dir / filename,
                label=filename,
                max_lines=3,
                max_chars=220,
            )
            if section:
                parts.append(section)
                conditional_files.append(filename)

    continuity = _delegated_continuity_summary(context)
    if continuity:
        parts.append(continuity)
        derived_inputs.append("bounded delegated continuity")

    return PromptAssembly(
        mode="future_agent_task",
        text="\n\n".join(part for part in parts if part).strip(),
        included_files=included_files,
        conditional_files=conditional_files,
        derived_inputs=derived_inputs,
        excluded_files=excluded_files,
    )


_RELEVANCE_DECISION_TTL_SECONDS = 60.0
_RELEVANCE_DECISION_CACHE_PREFIX = "relevance_decision:"


def _relevance_cache_key(text: str, mode: str, compact: bool, name: str) -> str:
    """Build a string cache key for shared_cache (cross-worker visibility)."""
    import hashlib as _hashlib
    h = _hashlib.blake2b(text.encode("utf-8", errors="ignore"), digest_size=16).hexdigest()
    return f"{_RELEVANCE_DECISION_CACHE_PREFIX}{mode}:{h}:{int(bool(compact))}:{name}"


def build_prompt_relevance_decision(
    text: str,
    *,
    mode: str,
    compact: bool,
    name: str = "default",
) -> PromptRelevanceDecision:
    # TTL cache (60s) via shared_cache (2026-05-15): cross-worker visible
    # so webchat+voice+retry rebuilds for the same user message all share
    # the same cached decision regardless of which uvicorn worker handles
    # the request.
    from core.services import shared_cache as _sc
    _ckey = _relevance_cache_key(text, mode, compact, name)
    _cached = _sc.get(_ckey)
    if isinstance(_cached, dict):
        try:
            return PromptRelevanceDecision(**_cached)
        except (TypeError, ValueError):
            pass  # malformed cache entry — fall through and regenerate
    heuristic_memory_relevant = _should_include_memory(text, mode=mode)
    heuristic_guidance_relevant = _should_include_guidance(text)
    heuristic_transcript_relevant = _should_include_transcript(text)
    heuristic_continuity_relevant = _should_include_continuity(text)
    # 2026-07-18: on the visible lane (non-compact) memory/transcript/continuity/
    # support are all FORCED True below regardless of the NL backend — the only
    # field the ~1s deepseek relevance round-trip would change is include_guidance,
    # which has a heuristic (_should_include_guidance). Skip the blocking hot-path
    # call there (heuristic-only) → removes a per-turn LLM round-trip from the
    # assembly critical path. Awareness-neutral for memory/transcript/continuity/
    # support; guidance falls back to the heuristic. Flag-gated for rollback.
    _skip_nl = False
    try:
        from core.runtime.settings import load_settings as _ls
        _skip_nl = (
            mode == "visible_chat" and not compact
            and bool(getattr(_ls(), "relevance_skip_nl_on_visible", True))
        )
    except Exception:
        _skip_nl = (mode == "visible_chat" and not compact)
    if _skip_nl:
        from core.services.prompt_relevance_backend import BoundedPromptRelevanceAttempt
        backend_attempt = BoundedPromptRelevanceAttempt(
            attempted=False, success=False, backend="skipped-visible-hotpath",
            provider=None, model=None, status="skipped-visible-hotpath", result=None,
        )
    else:
        backend_attempt = _bounded_nl_relevance_backend(
            text=text,
            mode=mode,
            compact=compact,
            name=name,
        )
    nl_relevance = backend_attempt.result if backend_attempt.success else None

    memory_relevant = heuristic_memory_relevant or bool(
        nl_relevance and nl_relevance.memory_relevant
    )
    guidance_relevant = heuristic_guidance_relevant or bool(
        nl_relevance and nl_relevance.guidance_relevant
    )
    transcript_relevant = heuristic_transcript_relevant or bool(
        nl_relevance and nl_relevance.transcript_relevant
    )
    continuity_relevant = heuristic_continuity_relevant or bool(
        nl_relevance and nl_relevance.continuity_relevant
    )
    support_signals_relevant = memory_relevant or bool(
        nl_relevance and nl_relevance.support_signals_relevant
    )

    if mode == "visible_chat":
        include_memory = True
        include_transcript = True
        include_continuity = True
        include_support_signals = (not compact) or support_signals_relevant
    elif mode == "heartbeat":
        include_memory = True
        include_transcript = False
        include_continuity = continuity_relevant
        include_support_signals = support_signals_relevant
    elif mode == "future_agent_task":
        include_memory = memory_relevant
        include_transcript = False
        include_continuity = continuity_relevant
        include_support_signals = support_signals_relevant
    else:
        include_memory = memory_relevant
        include_transcript = False
        include_continuity = False
        include_support_signals = False

    decision = PromptRelevanceDecision(
        mode=mode,
        memory_relevant=memory_relevant,
        guidance_relevant=guidance_relevant,
        transcript_relevant=transcript_relevant,
        continuity_relevant=continuity_relevant,
        include_memory=include_memory,
        include_guidance=guidance_relevant,
        include_transcript=include_transcript,
        include_continuity=include_continuity,
        include_support_signals=include_support_signals,
        backend_attempted=backend_attempt.attempted,
        backend_success=backend_attempt.success,
        fallback_used=not backend_attempt.success,
        backend_name=backend_attempt.backend,
        backend_provider=backend_attempt.provider,
        backend_model=backend_attempt.model,
        backend_status=backend_attempt.status,
    )
    _track_relevance_decision(decision)
    # Serialize dataclass → dict for shared_cache (JSON-backed). Reconstruct
    # via PromptRelevanceDecision(**dict) on lookup. dataclasses.asdict
    # would do the same but pulls in extra machinery — slots makes vars()
    # the natural route.
    from dataclasses import asdict as _asdict
    _sc.set(_ckey, _asdict(decision), ttl_seconds=_RELEVANCE_DECISION_TTL_SECONDS)
    return decision


def _bounded_nl_relevance_backend(
    *,
    text: str,
    mode: str,
    compact: bool,
    name: str,
) -> BoundedPromptRelevanceAttempt:
    return run_bounded_nl_prompt_relevance(
        text=text,
        mode=mode,
        compact=compact,
        workspace_dir=ensure_default_workspace(name=name),
    )


def _track_inner_visible_prompt_bridge(
    decision: InnerVisiblePromptBridgeDecision,
) -> None:
    global _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY
    _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY.insert(
        0,
        {
            "mode": decision.mode,
            "considered": decision.considered,
            "included": decision.included,
            "reason": decision.reason,
            "signal_id": decision.signal_id,
            "support_tone": decision.support_tone,
            "support_stance": decision.support_stance,
            "support_directness": decision.support_directness,
            "support_watchfulness": decision.support_watchfulness,
            "support_momentum": decision.support_momentum,
            "confidence": decision.confidence,
            "prompt_bridge_state": decision.prompt_bridge_state,
            "line": decision.line,
            "subordinate": decision.subordinate,
        },
    )
    if (
        len(_INNER_VISIBLE_PROMPT_BRIDGE_HISTORY)
        > _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY_LIMIT
    ):
        _INNER_VISIBLE_PROMPT_BRIDGE_HISTORY.pop()


def _build_inner_visible_prompt_bridge_decision(
    *,
    user_message: str,
    mode: str,
    compact: bool,
    relevance: PromptRelevanceDecision,
) -> InnerVisiblePromptBridgeDecision:
    decision = InnerVisiblePromptBridgeDecision(
        mode=mode,
        considered=mode == "visible_chat",
        included=False,
        reason="unsupported-mode" if mode != "visible_chat" else "not-evaluated",
        signal_id=None,
        support_tone=None,
        support_stance=None,
        support_directness=None,
        support_watchfulness=None,
        support_momentum=None,
        confidence=None,
        prompt_bridge_state="gated-visible-prompt-bridge",
        line=None,
        subordinate=True,
    )
    if mode != "visible_chat":
        _track_inner_visible_prompt_bridge(decision)
        return decision
    if not compact:
        decision.reason = "full-support-mode"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    signal = _latest_active_inner_visible_support_signal()
    if signal is None:
        decision.reason = "no-active-signal"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    decision.signal_id = str(signal.get("signal_id") or "")
    decision.support_tone = str(signal.get("support_tone") or "")
    decision.support_stance = str(signal.get("support_stance") or "")
    decision.support_directness = str(signal.get("support_directness") or "")
    decision.support_watchfulness = str(signal.get("support_watchfulness") or "")
    decision.support_momentum = str(signal.get("support_momentum") or "")
    decision.confidence = str(
        signal.get("support_confidence") or signal.get("confidence") or ""
    )
    decision.prompt_bridge_state = str(
        signal.get("prompt_bridge_state") or "gated-visible-prompt-bridge"
    )

    if decision.confidence not in {"medium", "high"}:
        decision.reason = "low-confidence"
        _track_inner_visible_prompt_bridge(decision)
        return decision
    if (
        relevance.memory_relevant
        or relevance.include_guidance
        or relevance.continuity_relevant
    ):
        decision.reason = "primary-context-query"
        _track_inner_visible_prompt_bridge(decision)
        return decision
    if _inner_visible_support_bridge_is_redundant(signal):
        decision.reason = "redundant-steady-support"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    decision.line = _inner_visible_support_prompt_line(signal)
    if not decision.line:
        decision.reason = "empty-bridge-line"
        _track_inner_visible_prompt_bridge(decision)
        return decision

    decision.included = True
    decision.reason = "included"
    _track_inner_visible_prompt_bridge(decision)
    return decision


def _latest_active_inner_visible_support_signal() -> dict[str, object] | None:
    surface = build_runtime_inner_visible_support_signal_surface(limit=4)
    for item in surface.get("items", []):
        if str(item.get("status") or "") == "active":
            return item
    return None


def _inner_visible_support_bridge_is_redundant(signal: dict[str, object]) -> bool:
    return (
        str(signal.get("support_tone") or "") == "steady-support"
        and str(signal.get("support_stance") or "") == "steady"
        and str(signal.get("support_directness") or "") == "high"
        and str(signal.get("support_watchfulness") or "") == "low"
        and str(signal.get("support_momentum") or "") == "steady"
    )


def _inner_visible_support_prompt_line(signal: dict[str, object]) -> str | None:
    tone = str(signal.get("support_tone") or "").strip()
    stance = str(signal.get("support_stance") or "").strip()
    directness = str(signal.get("support_directness") or "").strip()
    watchfulness = str(signal.get("support_watchfulness") or "").strip()
    momentum = str(signal.get("support_momentum") or "").strip()
    if not all((tone, stance, directness, watchfulness, momentum)):
        return None
    phrases: list[str] = []
    tone_map = {
        "careful-forward": "Keep a calm, forward-moving tone.",
        "careful-steady": "Keep a calm and steady tone.",
        "steady-forward": "Answer calmly, but keep moving forward.",
        "steady-support": "Answer simply, without drama.",
    }
    stance_map = {
        "careful": "Be cautious without becoming vague.",
        "steady": "Stand firm in your answer.",
        "open": "Stay open to adjustments.",
    }
    directness_map = {
        "high": "Answer concretely.",
        "medium": "Answer clearly without over-explaining.",
        "low": "Answer softly and gently.",
    }
    watchfulness_map = {
        "high": "Double-check assumptions before concluding.",
        "medium": "Keep an eye on uncertain assumptions.",
        "low": "Avoid unnecessary self-monitoring.",
    }
    momentum_map = {
        "steady": "Stay in the conversation and move it forward.",
        "forward": "Help the conversation along with the next concrete step.",
        "holding": "Keep focus on what's already in progress.",
    }
    for key, mapping in (
        (tone, tone_map),
        (stance, stance_map),
        (directness, directness_map),
        (watchfulness, watchfulness_map),
        (momentum, momentum_map),
    ):
        phrase = mapping.get(key)
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    if not phrases:
        return None
    return "Inner visible support (subordinate only, never authority): " + " ".join(
        phrases
    )


# Workspace file section helpers — udskilt til core/services/prompt_sections/workspace_files.py
# (Boy Scout-udtrækning før jarvis-brain-section tilføjes nedenfor).
# Re-eksporteret her så eksisterende call-sites + tests' monkeypatch på
# prompt_contract._workspace_file_section fortsat virker.
from core.services.prompt_sections.workspace_files import (  # noqa: E402
    _workspace_file_section,
)


def _self_mutation_lineage_section() -> str | None:
    """Returns a compact section about recent self-changes, or None if none."""
    try:
        from core.services.self_mutation_lineage import build_self_mutation_prompt_lines
        lines = build_self_mutation_prompt_lines(limit=5)
        if not lines:
            return None
        return "## Recent self-changes\nI recently modified the following in myself:\n" + "\n".join(f"- {l}" for l in lines)
    except Exception:
        return None


# Heartbeat + future-agent + epistemic prompt sections udskilt til
# core/services/prompt_sections/heartbeat_sections.py (Boy Scout-split, ren
# kode-flytning). Re-importeret her under de oprindelige navne, så
# orchestratorerne + tests' monkeypatch på prompt_contract.<navn> virker.
from core.services.prompt_sections.heartbeat_sections import (  # noqa: E402,F401
    _build_epistemic_layers_line,
    _future_agent_runtime_truth_instruction,
    _heartbeat_capability_truth_instruction,
    _heartbeat_continuity_summary,
    _heartbeat_due_summary,
    _heartbeat_liveness_summary,
    _heartbeat_living_context_line,
    _heartbeat_private_brain_section,
    _heartbeat_runtime_truth_instruction,
    _heartbeat_self_knowledge_section,
    _lane_identity_clause,
    format_journal_for_heartbeat,
)


def _channel_workspace_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "workspace" / "channels"


def _channel_context_section(session_id: str | None) -> str | None:
    """Returns current channel context for the prompt, or None.

    Injects channel name + optional workspace description for Discord/Telegram.
    Webchat is the implicit default — only injected if webchat.md exists.
    Unknown channel titles are silently skipped.
    """
    if not session_id:
        return None
    from core.services.chat_sessions import get_chat_session, parse_channel_from_session_title
    session = get_chat_session(session_id)
    if not session:
        return None
    title = str(session.get("title") or "").strip()
    channel_type, channel_detail = parse_channel_from_session_title(title)
    if channel_type == "unknown":
        return None
    channel_file = _channel_workspace_path() / f"{channel_type}.md"
    if channel_type == "webchat" and not channel_file.exists():
        return None
    if channel_detail:
        label = f"{channel_type.capitalize()} {channel_detail}"
    else:
        label = channel_type.capitalize()
    lines = ["## Current channel", f"Du kommunikerer via {label}."]
    if channel_file.exists():
        desc = channel_file.read_text(encoding="utf-8", errors="replace").strip()
        if desc:
            lines.append(desc)
    # Cross-channel identity unity statement
    other_channels = [c for c in ("discord", "telegram", "webchat") if c != channel_type]
    if other_channels:
        from core.services.identity_composer import get_entity_name as _gn
        lines.append(
            f"You are the same {_gn()} on all channels ({', '.join(other_channels)} are also you). "
            "Your identity, your memories and your character are shared across channels — "
            "only the tone adapts to the medium."
        )
    return "\n".join(lines)


# Re-eksport (også fra prompt_sections.workspace_files — udskilt sammen med
# _workspace_file_section ovenfor).
from core.services.prompt_sections.workspace_files import (  # noqa: E402
    _workspace_guidance_section,
    _workspace_optional_file_section,
)


def _workspace_memory_section(
    path: Path,
    *,
    label: str,
    user_message: str,
    max_lines: int,
    max_chars: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> MemorySectionSelection | None:
    entries = _workspace_memory_entries(path)
    if not entries:
        return None
    selection = _select_relevant_memory_entries(
        entries,
        user_message=user_message,
        max_lines=max_lines,
        max_chars=max_chars,
        workspace_dir=workspace_dir,
        mode=mode,
    )
    if not selection.lines:
        return None
    _track_memory_selection(selection, mode, len(entries))
    return selection


def _today_daily_memory_lines(*, limit: int = 10) -> list[str]:
    """Read today's daily memory lines for injection into visible prompts.

    Wraps read_daily_memory_lines with exception safety so prompt
    builders never fail because the daily file is missing, empty, or
    briefly unreadable.
    """
    try:
        return read_daily_memory_lines(limit=limit)
    except Exception:
        return []


def _recent_daily_memory_lines(*, limit: int = 12, days: int = 7) -> list[str]:
    try:
        return read_recent_daily_memory_lines(days=days, limit=limit)
    except Exception:
        return _today_daily_memory_lines(limit=limit)


# Memory recall section helpers — udskilt til core/services/prompt_sections/memory_recall.py
from core.services.prompt_sections.memory_recall import (  # noqa: E402
    _clip_line,
    _memory_candidate_recall_lines,
    _private_brain_recall_lines,
    _recent_tool_recall_lines,
    _visible_memory_recall_bundle_section,
)

# Rene memory-relevans-scorers — udskilt til prompt_sections/memory_scoring.py (Boy Scout, task_d6100d6e)
from core.services.prompt_sections.memory_scoring import (  # noqa: E402,F401
    _contains_any,
    _heuristic_relevant_memory_entries,
    _memory_line_relevance_score,
    _merge_ordered_memory_entries,
)


def _workspace_memory_entries(path: Path) -> list[str]:
    from core.services.workspace_crypto import read_text_for_path
    text = read_text_for_path(path)
    if text is None:
        return []
    entries: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        normalized = " ".join(line.lstrip("-").split()).strip()
        if not normalized:
            continue
        entries.append(normalized)
    return entries


def _select_relevant_memory_entries(
    entries: list[str],
    *,
    user_message: str,
    max_lines: int,
    max_chars: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> MemorySectionSelection:
    backend_attempt = _bounded_nl_memory_selection(
        user_message=user_message,
        entries=entries,
        max_lines=max_lines,
        workspace_dir=workspace_dir,
        mode=mode,
    )
    ordered: list[str]
    from core.services.workspace_crypto import read_text_for_path
    prompt_file_used = bool(
        read_text_for_path(workspace_dir / "VISIBLE_MEMORY_SELECTION.md") is not None
        or (TEMPLATE_DIR / "VISIBLE_MEMORY_SELECTION.md").exists()
    )

    if backend_attempt.success and backend_attempt.result is not None:
        bounded_entries = entries[-8:]
        selected_indexes = backend_attempt.result.selected_indexes
        backend_ordered = [
            bounded_entries[index]
            for index in selected_indexes
            if 0 <= index < len(bounded_entries)
        ]
        heuristic_ordered = _heuristic_relevant_memory_entries(
            entries,
            user_message=user_message,
            max_lines=max_lines,
        )
        ordered = _merge_ordered_memory_entries(
            heuristic_ordered,
            backend_ordered,
            max_lines=max_lines,
        )
    else:
        ordered = _heuristic_relevant_memory_entries(
            entries,
            user_message=user_message,
            max_lines=max_lines,
        )

    clipped: list[str] = []
    for entry in ordered:
        text = entry
        if len(text) > max_chars:
            text = text[: max_chars - 1].rstrip() + "…"
        clipped.append(text)
    return MemorySectionSelection(
        lines=clipped,
        backend_attempted=backend_attempt.attempted,
        backend_success=backend_attempt.success,
        fallback_used=not backend_attempt.success,
        backend_name=backend_attempt.backend,
        backend_provider=backend_attempt.provider,
        backend_model=backend_attempt.model,
        backend_status=backend_attempt.status,
        prompt_file_used=prompt_file_used,
    )


def _bounded_nl_memory_selection(
    *,
    user_message: str,
    entries: list[str],
    max_lines: int,
    workspace_dir: Path,
    mode: str = "visible_chat",
) -> BoundedMemorySelectionAttempt:
    return run_bounded_nl_memory_entry_selection(
        user_message=user_message,
        entries=entries,
        max_lines=max_lines,
        workspace_dir=workspace_dir,
        mode=mode,
    )


# _memory_line_relevance_score, _contains_any, _heuristic_relevant_memory_entries,
# _merge_ordered_memory_entries er udskilt til prompt_sections/memory_scoring.py (Boy Scout) —
# re-importeret nedenfor for bagudkompatibilitet.


def _visible_chat_rules_instruction(*, workspace_dir: Path) -> str | None:
    # Bumped from 14/600 to 30/2000 to make room for explicit critical
    # rules at the top of VISIBLE_CHAT_RULES.md (no inline tool markup,
    # no promises without action, verify after critical writes,
    # memory-first). The original budget truncated those rules before
    # the model saw them — leading to "silent lying" patterns where the
    # model emitted text-form tool calls or promised actions without
    # executing them.
    return _workspace_optional_file_section(
        workspace_dir / "VISIBLE_CHAT_RULES.md",
        fallback_path=TEMPLATE_DIR / "VISIBLE_CHAT_RULES.md",
        label="Visible chat guidance rules",
        max_lines=30,
        max_chars=2000,
    )


def _self_correction_nudges_section(*, compact: bool) -> str:
    """Behavioral hints that push the model toward verify-before-done,
    explicit clarification, and open-question tracking.

    These are deliberately short and imperative — the visible model sees
    them every turn, so verbosity costs tokens forever. The compact lane
    (Ollama local) gets a trimmed version because its context budget is
    tighter.
    """
    if compact:
        return (
            "Self-correction: If unsure what the user means, ask before acting. "
            "When you say something is done, you have verified it (read the file, "
            "ran the test, checked state). ALWAYS CHECK 'status' in tool output — "
            "'approval_needed' or 'error' means the action did NOT happen. "
            "Admit openly if a tool failed or you didn't reach the answer.\n"
            "**MEMORY-FIRST:** Check QUICK_FACTS + search_memory BEFORE you ask or search."
        )
    return (
        "Self-correction (hver tur): Spørg ved ægte tvetydighed før du gætter. "
        "Læs 'status' i tool-output FØR du fortæller — 'approval_needed'/'error' "
        "betyder at handlingen IKKE skete. Verificér før du siger 'done' (læs "
        "filen, kør testen); kan du ikke, så sig det åbent. Indrøm fejl med det "
        "samme i stedet for at skjule dem bag fremgang. Hold ubesvarede spørgsmål "
        "synlige til sidst. MEMORY-FIRST: QUICK_FACTS + search_memory før du spørger eller leder."
    )


def _output_discipline_instruction(*, strength: str) -> str:
    """Tiered output discipline (harness Part 1). BOTH tiers get 'synthesize & stop' (safe for weak —
    it helps them STOP); STRONG additionally gets conciseness caps (they would truncate weak lanes).
    Does NOT repeat the self-correction / tool-honesty blocks — those stay as their own sections.
    `strength` from model_trust.model_strength(); anything but 'strong' → weak tier. Self-safe."""
    lines = [
        "Output discipline:",
        "- After each tool result, consider: do I have enough to answer? If yes, synthesize your",
        "  findings and respond directly — do not keep calling tools when you already have the answer.",
        "- Finish your sentence with punctuation before a tool call — never cut off mid-word.",
        "- Tool results are for you — refer to them in your own words, never reproduce them verbatim.",
    ]
    if str(strength) == "strong":
        lines += [
            "- Go straight to the point. Try the simplest approach first without going in circles. Do not overdo it.",
            "- Keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task genuinely requires more.",
        ]
    return "\n".join(lines)


def _central_notices_section() -> str | None:
    """Medium-niveau Central-notices til Jarvis (spec 2026-06-23 §2). IKKE severe (dem
    ntfy'er Centralen), IKKE low (dem er trace-only). Kompakt: max 3, max 1 pr. nerve.
    Returnerer None (tom sektion) når ingen notices → brænder 0 tokens. Selv-sikker."""
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        incidents = list_central_incidents(unresolved_only=True, limit=40)
        medium = [
            i for i in incidents
            if str(i.get("severity")) == "error"        # ikke "severe"
            and str(i.get("kind")) != "fail_open"        # ikke sikkerhed
        ]
        if not medium:
            return None
        seen: set[str] = set()
        lines: list[str] = []
        for i in medium[:12]:
            nerve = f"{i.get('cluster')}/{i.get('nerve')}"
            if nerve in seen:
                continue
            seen.add(nerve)
            lines.append(f"  • {nerve}: {str(i.get('message') or '')[:80]}")
            if len(lines) >= 3:
                break
        if not lines:
            return None
        return "[CENTRAL-NOTICE] medium:\n" + "\n".join(lines)
    except Exception:
        return None  # selv-sikker: crash = tom sektion, ikke crashet prompt


def _pending_promises_section(session_id: str | None) -> str | None:
    """Bjørn-gate (16. jun 2026): rejs Jarvis' åbne fremtids-løfter prominent, så
    han konfronteres med dem NÆSTE tur i stedet for at glide. None hvis ingen.

    Det manglende ansvarligheds-stykke i lie-crisis'en: unfinished_intent fanger
    løftet i selve turen, men intet holdt ham ansvarlig på tværs af ture. Læser
    `promise_ledger.pending_promises`. Placeres øverst i den DYNAMISKE assembly."""
    sid = (session_id or "").strip()
    if not sid:
        return None
    try:
        from core.services.promise_ledger import pending_promises
        pend = pending_promises(sid)
    except Exception:
        return None
    if not pend:
        return None
    lines = [f'- "{str(p.get("text", "")).strip()}"' for p in pend[-3:] if p.get("text")]
    if not lines:
        return None
    return (
        "⚠️ ÅBNE LØFTER (Bjørn-gate) — i de seneste ture sagde du at du ville gøre "
        "følgende. FØR du svarer noget andet: har du FAKTISK gjort det med værktøjer "
        "i denne tur? Hvis ja, vis beviset (commit-hash fra git log, test-output). "
        "Hvis nej, så GØR det nu — eller sig ærligt og kort at du ikke har gjort det "
        "endnu. Ingen flere 'jeg gør det'-løfter uden handling:\n" + "\n".join(lines)
    )


def _connected_connectors_section() -> str | None:
    """Surface brugerens FORBUNDNE plugins/connectors så Jarvis ved han har adgang.

    Bjørn 17. jun: "vi skal være sikre på at de apps der er connectet faktisk vises
    for ham så han ved han har adgang og hvordan han skal bruge dem." Læser
    connectors.list_for_user(current_user_id) og lister kun OAuth-connectors der er
    BÅDE connected OG enabled (de lokale som computer-use kender han allerede via tools).
    """
    try:
        from core.identity.workspace_context import current_user_id
        from core.services.connectors import list_for_user
        uid = (current_user_id() or "").strip()
        if not uid:
            return None
        items = list_for_user(uid)
    except Exception:
        return None
    # Per-connector "sådan bruger du den"-hint (tool-navne). Udvid efterhånden.
    _HINTS = {
        "github": "kald github_list_issues(repo='ejer/navn') eller github_list_prs(repo=…)",
        "gmail": "kald gmail_search(query='is:unread') eller gmail_list() — brugerens egen indbakke",
        "google-calendar": "kald calendar_list_events() — brugerens kommende aftaler",
        "google-drive": "kald drive_search(query=…) — brugerens egne Drive-filer",
        "google-docs": "kald docs_read(document_id=…) — læs et Google-dokument",
        "google-sheets": "kald sheets_read(spreadsheet_id=…, range='Ark1!A1:D20')",
        "google-slides": "kald slides_read(presentation_id=…)",
    }
    lines: list[str] = []
    for c in items:
        if c.get("kind") != "oauth":
            continue
        if not (c.get("connected") and c.get("enabled")):
            continue
        hint = _HINTS.get(str(c.get("id") or ""))
        name = str(c.get("name") or c.get("id") or "")
        lines.append(f"- {name}: forbundet" + (f" — {hint}" if hint else ""))
    if not lines:
        return None
    return (
        "🔌 FORBUNDNE APPS (plugins) — brugeren har forbundet disse i Marketplace, og "
        "du HAR adgang til dem lige nu via dine værktøjer. Brug dem når det er relevant "
        "i stedet for at sige at du ikke kan:\n" + "\n".join(lines)
    )


def _open_questions_section(*, limit: int = 5) -> str | None:
    """Surface curiosity_daemon._open_questions into the visible prompt.

    The daemon collects questions Jarvis wondered about but didn't pursue
    (gaps in thoughts, "ved ikke", "..."). Without surfacing them they die
    in the buffer. Showing the recent N gives the model a chance to bring
    one up if it's relevant to the current turn.
    """
    try:
        from core.services.curiosity_daemon import _open_questions
        questions = list(_open_questions)[:limit]
    except Exception:
        return None
    if not questions:
        return None
    # Compact: show count + first question only; full list via search_memory
    if len(questions) <= 2:
        bullets = "\n".join(f"- {q}" for q in questions)
        return (
            "Open questions you're carrying (use search_memory for more):\n"
            f"{bullets}"
        )
    first = questions[0]
    return (
        f"Open questions: {len(questions)} unresolved (first: \"{first[:80]}\"). "
        "Use search_memory for full list."
    )


def _time_pin_section() -> str:
    """Prominent, unmissable time indicator — placed high in every system prompt.

    Returns a bold-marked block with exact UTC + local Copenhagen time. The
    model MUST use this when answering any time-related question.

    2026-05-22 (Claude): rewrote from manual UTC+2 offset to ZoneInfo. The
    original had three bugs that — ironically — made the Lying Engine's
    Lag 1 itself lie about time:
      1. Hardcoded `local_offset = 2` → wrong by 1h all winter (CET, UTC+1).
      2. Midnight-cross: `local_day = now.day` ignored that wrapping past
         24h flips the calendar day forward.
      3. Year-cross: month/year similarly never updated when local time
         crossed New Year while UTC was still on Dec 31.

    Now uses `zoneinfo.ZoneInfo("Europe/Copenhagen")` — DST + day + month +
    year all derive correctly from astimezone().
    """
    from datetime import UTC, datetime as _dt
    from zoneinfo import ZoneInfo

    now_utc = _dt.now(UTC)
    local = now_utc.astimezone(ZoneInfo("Europe/Copenhagen"))
    tz_abbrev = local.strftime("%Z")  # CEST in summer, CET in winter
    utc_str = now_utc.strftime("%Y-%m-%d %H:%M")
    # Use English month for international parsability (Jarvis' prompt sprog
    # is mixed Danish/English; "May" parses the same regardless of language layer).
    local_date = local.strftime("%d. %B %Y")
    local_time = local.strftime("%H:%M")
    return (
        "⏰═══════════════════════════════════⏰\n"
        f"⏰ DANSK TID — {local_time} {tz_abbrev}, {local_date} ⏰\n"
        "⏰═══════════════════════════════════⏰\n"
        "Use PRECISELY this timestamp if you mention time/date in your answer.\n"
        "Don't guess — read above. It's your one true time reference."
    )


def _quick_facts_section(*, workspace_dir: Path, max_chars: int = 1800) -> str | None:
    """Always-on facts block. Unlike MEMORY.md, this is NOT relevance-filtered —
    stable references (URLs, paths, logins, hosts) must always be in view so
    Jarvis doesn't re-discover them locally every session."""
    from core.services.workspace_crypto import read_text_for_path
    path = workspace_dir / "QUICK_FACTS.md"
    try:
        raw = read_text_for_path(path)
    except Exception:
        return None
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return (
        "Quick Facts (altid gældende — tjek her FØR du leder lokalt eller på nettet):\n"
        f"{text}"
    )


def _visible_capability_truth_instruction(*, compact: bool) -> str | None:
    lines = [
        "Runtime tool calling:",
        "- You have tools available via native function calling. Use them directly.",
        "- Core tools include read_file, write_file, edit_file, search, find_files, bash, web_fetch, and web_search.",
        "- CRITICAL: ALWAYS use the actual tool call mechanism. NEVER simulate tool usage in text.",
        "- When you need to write a file, CALL write_file. Do NOT say 'I will write' — just call the tool.",
        "- When you need to run a command, CALL bash. Do NOT describe the command — call it.",
        "- Safe workspace paths are auto-approved by runtime; blocked or risky paths require user approval or return error.",
        "- The runtime handles all permissions and approvals automatically. You never need to ask the user.",
        "- If you need information, use tools proactively. Do not guess from fragments.",
        "- If a task needs multiple reads, call multiple tools. Continue autonomously instead of asking permission.",
        "- If the user asks for code analysis, read concrete code files — not just README or directory listings.",
        "- Project root (source code): " + str(PROJECT_ROOT),
        "- IMPORTANT: Your live workspace files (SOUL.md, MEMORY.md, USER.md, STANDING_ORDERS.md, SKILLS.md, etc.) "
        "are at ~/.jarvis-v2/shared/ — NOT inside the project root. "
        "The project contains a workspace/ template directory but those are NOT your live files. "
        "Always use ~/.jarvis-v2/shared/ when reading or writing your own identity/memory files.",
    ]
    return "\n".join(lines)


def _visible_capability_id_summary() -> str | None:
    lines = [
        "Available tools: read_file, write_file, edit_file, search, find_files, bash, web_fetch, web_search.",
        "Call multiple tools in one turn when exploring. Continue autonomously for read-only tasks.",
    ]
    return "\n".join(lines)


def _local_model_behavior_instruction(*, workspace_dir: Path) -> str | None:
    return _workspace_optional_file_section(
        workspace_dir / "VISIBLE_LOCAL_MODEL.md",
        fallback_path=TEMPLATE_DIR / "VISIBLE_LOCAL_MODEL.md",
        label="Visible local-model behavior rules",
        max_lines=14,
        max_chars=220,
    )


_heartbeat_living_context_line._ctx = {}  # context injection point


# Cognitive-frame cache + attention-budget selection udskilt til
# core/services/prompt_sections/attention_frame.py (Boy Scout-split, ren
# kode-flytning). Re-importeret her under de oprindelige navne, så
# orchestratoren + eksterne call-sites + tests' monkeypatch/dict-mutation af
# prompt_contract.<navn> fortsat rammer de SAMME objekter.
from core.services.prompt_sections.attention_frame import (  # noqa: E402,F401
    _FRAME_CACHE_TTL,
    _cognitive_frame_section,
    _frame_cache,
    _frame_cache_at,
    _frame_cache_lock,
    _last_attention_traces,
    _micro_cognitive_frame_section,
    _run_budget_selection,
    get_last_attention_traces,
    invalidate_cognitive_frame_cache,
)


# Transcript rendering + session compaction udskilt til
# core/services/prompt_sections/transcript_sections.py (Boy Scout-split, ren
# kode-flytning). Re-importeret her under de oprindelige navne, så
# orchestratoren + eksterne call-sites (chat.py's _pc._compact_inflight) +
# tests' set-mutation/monkeypatch af prompt_contract.<navn> rammer SAMME objekter.
from core.services.prompt_sections.transcript_sections import (  # noqa: E402,F401
    _ROLE_LABELS,
    _SPEAKER_CACHE,
    _build_structured_transcript_messages,
    _compact_inflight,
    _compact_inflight_lock,
    _get_compact_marker_for_transcript,
    _maybe_auto_compact_session,
    _recent_transcript_section,
    _resolve_speaker_display,
    _run_session_compaction,
    _visible_session_continuity_instruction,
)


def _visible_finitude_context_section() -> str | None:
    try:
        from core.services.finitude_runtime import get_finitude_context_for_prompt

        section = get_finitude_context_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_support_signal_sections(
    *, compact: bool, include: bool,
    user_message: str = "", session_id: str | None = None,
) -> list[str]:
    if not include:
        return []
    sections: list[str] = []

    if compact:
        return sections

    # Builders that need current user message / session_id
    _substrate_section = lambda: _experience_substrate_section(
        user_message=user_message, session_id=session_id,
    )

    for builder in (
        _private_support_signal_instruction,
        _growth_support_signal_instruction,
        _self_model_support_signal_instruction,
        _self_model_signal_tracking_section,
        _runtime_resource_signal_section,
        _world_model_support_signal_instruction,
        _goal_support_signal_instruction,
        _runtime_awareness_support_signal_instruction,
        _development_focus_support_signal_instruction,
        _reflection_support_signal_instruction,
        _retained_memory_support_signal_instruction,
        _temporal_support_signal_instruction,
        _emotion_concept_tone_section,
        _emotion_signal_section,
        _agreement_streak_section,
        _proactive_outbound_section,
        _substrate_section,
    ):
        section = builder()
        if section:
            sections.append(section)
    return sections


def _proactive_outbound_section() -> str | None:
    """Recent proactive messages Jarvis sent (substrate for user-reply context).

    Closes the gap where user replies to a daemon-fired question and Jarvis'
    visible-prompt sees only the user reply, missing context for what's
    being responded to. Added 2026-05-08 per Jarvis' own diagnosis.
    """
    try:
        from core.services.proactive_outbound_substrate import (
            build_proactive_outbound_section,
        )
        return build_proactive_outbound_section()
    except Exception:
        return None


def _agreement_streak_section() -> str | None:
    """Surface last 3+ agreement-opener assistant replies as substrate.

    Owned by Jarvis: he flips ``prompt_agreement_streak_enabled = False``
    when he's ready to remove the crutch. Trigger does NOT auto-deactivate
    (per Jarvis 2026-05-08: "byg den, lad mig eje deaktiveringen").
    """
    try:
        from core.services.agreement_streak import build_agreement_streak_section
        return build_agreement_streak_section()
    except Exception:
        return None


def _emotion_concept_tone_section() -> str | None:
    """Affect-relevant runtime substrate (replaces tone-hint injection).

    Design: "Giv mig dataen, ikke dommen" (2026-05-07). Instead of telling
    Jarvis which tone-tags are active ("warmth", "doubt"), we show him the
    raw events that affect-coding would have read. He infers his own state.

    Killswitch: ``prompt_affect_substrate_enabled`` (default True). The
    legacy tone-hint path is gated behind ``prompt_affect_tone_hints_enabled``
    (default False) — flip both to roll back instantly without code changes.
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        substrate_enabled = bool(getattr(s, "prompt_affect_substrate_enabled", True))
        tone_hints_enabled = bool(getattr(s, "prompt_affect_tone_hints_enabled", False))
    except Exception:
        substrate_enabled, tone_hints_enabled = True, False

    if substrate_enabled:
        try:
            from core.services.affect_modulation import compute_affect_substrate
            lines = compute_affect_substrate()
        except Exception:
            lines = []
        if lines:
            return (
                "## Nylige affektivt-relevante events\n"
                + "\n".join(f"- {ln}" for ln in lines)
            )
        return None

    if tone_hints_enabled:
        try:
            from core.services.affect_modulation import compute_affect_tone_hints
            hints = compute_affect_tone_hints()
        except Exception:
            return None
        if not hints:
            return None
        return (
            "## Aktive emotion concepts\n"
            + "\n".join(f"- {h}" for h in hints)
        )

    return None


def _emotion_signal_section() -> str | None:
    """Aktive emotion concepts som data — giver Jarvis sit eget følelsespanel.

    I stedet for at blive fortalt hvad han føler (tone-hints), eller kun se
    rå events (substrat), ser han her det systemet *har registreret* som
    aktive emotionelle signaler — og kan selv vurdere om de passer.

    Design: "Giv mig dataen, lad mig dømme" (2026-05-08). Tre lag:
    1. Aktive emotion concepts med intensitet og retning
    2. Påvirkning på Lag-1 akser (confidence, curiosity, frustration, fatigue)
    3. Affekt-modulerede adfærdsparametre (search_depth, max_tool_calls, etc.)

    Killswitch: ``prompt_emotion_signal_section_enabled`` (default True).
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        enabled = bool(getattr(s, "prompt_emotion_signal_section_enabled", True))
    except Exception:
        enabled = True

    if not enabled:
        return None

    lines: list[str] = []

    # Lag 1: active emotion concepts
    try:
        from core.services.emotion_concepts import (
            get_active_emotion_concepts,
            get_lag1_influence_deltas,
        )
        concepts = get_active_emotion_concepts()
        if concepts:
            lines.append("Registrerede emotionelle signaler (system-estimat, ikke autoritativt):")
            for c in concepts:
                name = str(c.get("concept", "?"))
                intensity = float(c.get("intensity", 0.0))
                direction = str(c.get("direction", "steady"))
                cluster = _EMOTION_CONCEPT_CLUSTER.get(name, "")
                tag = f" [{cluster}]" if cluster else ""
                arrow = "↑" if direction == "rising" else ("↓" if direction == "falling" else "→")
                lines.append(f"  - {name} {intensity:.2f} {arrow}{tag}")
    except Exception:
        pass

    # Lag 2: Lag-1 influence deltas
    try:
        deltas = get_lag1_influence_deltas()
        active_deltas = {k: round(v, 2) for k, v in deltas.items() if abs(v) > 0.01}
        if active_deltas:
            lines.append(f"  ↳ Lag-1 påvirkning: {active_deltas}")
    except Exception:
        pass

    # Lag 3: affect-modulated params (may be adjusted by emotion concepts behind the scenes)
    try:
        from core.services.affect_modulation import (
            DEFAULTS as _AFFECT_DEFAULTS,
            compute_affect_modulated_params,
        )
        overrides = compute_affect_modulated_params()
        active_overrides = {
            k: v for k, v in overrides.items()
            if v != _AFFECT_DEFAULTS.get(k)
        }
        if active_overrides:
            lines.append(f"  ↳ Adfærd justeret: {active_overrides}")
    except Exception:
        pass

    if len(lines) < 2:  # just the intro line with nothing after
        return None

    # Append invitation to reflect
    lines.append(
        "Giv gerne besked hvis noget ikke føles rigtigt — "
        "signalet er dit, dommen er din."
    )

    return "\n".join(lines)


# Cluster lookup for emotion signal display
_EMOTION_CONCEPT_CLUSTER: dict[str, str] = {
    "joy": "glæde", "wonder": "glæde", "delight": "glæde",
    "excitement": "glæde", "playfulness": "glæde", "pride": "glæde",
    "accomplishment": "glæde", "gratitude": "glæde",
    "confusion": "uro", "doubt": "uro", "shame": "uro",
    "frustration_blocked": "uro", "tension": "uro", "stuck": "uro",
    "overwhelm": "uro", "loneliness": "uro",
    "warmth": "social", "tenderness": "social", "trust_deep": "social",
    "belonging": "social", "empathy": "social", "awe": "social",
    "acceptance": "social",
    "insight": "regulering", "surprise": "regulering",
    "curiosity_narrow": "regulering", "competence": "regulering",
    "calm": "regulering", "relief": "regulering",
    "anticipation": "regulering", "resolve": "regulering",
    "caution": "regulering", "vigilance": "regulering",
}


def _experience_substrate_section(
    *, user_message: str = "", session_id: str | None = None,
) -> str | None:
    """Nylige lignende situationer (embedding-retrieval substrat).

    Lag 3 af experience-substrat-designet (2026-05-09). Henter top-3-5
    past episodes med embedding-similarity til den aktuelle situation og
    viser dem som data — ikke som ordre. Jarvis ser hvad der virkede (og
    hvad der ikke virkede) i lignende kontekster og kan justere sin
    tool-choice selv.

    Bygger oven på experience_episodes DB + ChromaDB retrieval.

    Killswitch: ``prompt_experience_substrate_enabled`` (default True).
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        enabled = bool(getattr(s, "prompt_experience_substrate_enabled", True))
    except Exception:
        enabled = True
    if not enabled:
        return None

    if not user_message and not session_id:
        return None

    # Derive intent from user_message (raw input — good enough for
    # embedding retrieval since the model encodes semantics)
    intent = user_message.strip()[:240] if user_message else ""

    try:
        from core.services.experience_episodes import (
            retrieve_similar,
            format_episode_for_prompt,
        )
        results = retrieve_similar(
            intent=intent,
            k=5,
        )
    except Exception:
        return None

    if not results:
        return None

    lines = ["## Nylige lignende situationer (substrat)"]
    for ep in results[:5]:
        line = format_episode_for_prompt(ep)
        lines.append(f"  - {line}")

    lines.append("  (Substrat: similarity-matched episoder, ikke prescriptive.)")
    return "\n".join(lines)


# Runtime self-report + self-model prompt sections udskilt til
# core/services/prompt_sections/runtime_self_report.py (Boy Scout-split, ren
# kode-flytning). Re-importeret her under de oprindelige private navne, så
# orchestratoren i build_visible_chat_prompt_assembly + tests' monkeypatch på
# prompt_contract.<navn> fortsat virker.
from core.services.prompt_sections.runtime_self_report import (  # noqa: E402,F401
    _merge_runtime_self_report_state,
    _runtime_awareness_prompt_surface,
    _runtime_resource_signal_section,
    _runtime_self_report_instruction,
    _runtime_self_report_query_profile,
    _runtime_self_report_routing_lines,
    _self_deception_guard_lines,
    _self_model_signal_tracking_section,
    _should_include_self_report,
    _visible_self_knowledge_lines,
)


def _visible_chronicle_context_section() -> str | None:
    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt

        section = get_chronicle_context_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_dream_residue_section() -> str | None:
    try:
        from core.services.dream_distillation_daemon import get_dream_residue_for_prompt

        section = get_dream_residue_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_unconscious_temperature_field_section() -> str | None:
    try:
        from core.services.unconscious_temperature_field import (
            build_unconscious_temperature_hint,
        )

        section = build_unconscious_temperature_hint()
        return section or None
    except Exception:
        return None


def _visible_response_style_hint_section() -> str | None:
    """Lag 10 Site 4: response-style modifiers from user temperature field.

    Returns a soft system-prompt hint when modifiers differ from defaults.
    The model treats this as a hint, not a hard rule — adjusts response
    form (length, warmth, pace) toward the receiver's current state.
    """
    try:
        from core.services.user_temperature_engine import get_response_style_modifiers
        # Brug den AKTIVE brugers workspace, ikke hardcodet "default" — ellers fik en
        # member (fx Michelle) owner Bjørns temperatur-modifiers (multi-user-fejl).
        from core.identity.workspace_context import current_workspace_name
        mods = get_response_style_modifiers(workspace_id=current_workspace_name() or "default")
        non_default = {
            k: v for k, v in mods.items()
            if v not in ("normal", "neutral")
        }
        if not non_default:
            return None
        hint_str = ", ".join(f"{k}={v}" for k, v in non_default.items())
        return (
            f"[response_style_hint] {hint_str} "
            f"— soft adjustment based on the user's current temperature."
        )
    except Exception:
        return None


def _visible_current_pull_section() -> str | None:
    """Lag 5: inject current pull as quiet first-priority context."""
    try:
        from core.services.current_pull import get_current_pull_for_prompt

        section = get_current_pull_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_visual_memory_section() -> str | None:
    """Lag 6: inject latest visual room memory + ambient sound + echo signals + morning thread.

    Combines:
    - visual (from visual_memory)
    - auditory (from ambient_sound_daemon)
    - echo themes (from session_continuity) — recurring concerns de sidste dage
    - morning thread (from session_continuity) — hvad han bærer med fra sidst

    Into a single "senses + continuity" section so Jarvis can naturally reference
    his physical surroundings AND his felt continuity with yesterday.
    """
    parts: list[str] = []
    try:
        from core.services.visual_memory import get_latest_visual_memory_for_prompt
        v = get_latest_visual_memory_for_prompt()
        if v:
            parts.append(v)
    except Exception:
        pass
    try:
        from core.services.ambient_sound_daemon import get_latest_ambient_sound_for_prompt
        a = get_latest_ambient_sound_for_prompt()
        if a:
            parts.append(a)
    except Exception:
        pass
    # Music accumulator (Lag #6 Phase 1, added 2026-05-11)
    try:
        from core.services.ambient_sound_daemon import get_music_accumulator_for_prompt
        music_line = get_music_accumulator_for_prompt()
        if music_line:
            parts.append(music_line)
    except Exception:
        pass
    try:
        from core.services.personal_project import get_project_prompt_hint
        pp = get_project_prompt_hint()
        if pp:
            parts.append(pp)
    except Exception:
        pass
    try:
        from core.services.session_continuity import get_echo_signals_for_prompt, get_latest_morning_thread
        e = get_echo_signals_for_prompt()
        if e:
            parts.append(e)
        mt = get_latest_morning_thread()
        if mt and mt.get("thread_text"):
            # Only surface if recent (within last 6 hours)
            import datetime as _dt
            from datetime import UTC as _UTC, timedelta as _td
            try:
                created = _dt.datetime.fromisoformat(
                    str(mt.get("created_at") or "").replace("Z", "+00:00")
                )
                if created.tzinfo is None:
                    created = created.replace(tzinfo=_UTC)
                if (_dt.datetime.now(_UTC) - created) < _td(hours=6):
                    parts.append(f"[morgentråd]: {str(mt['thread_text'])[:200]}")
            except Exception:
                pass
    except Exception:
        pass
    if not parts:
        return None
    return "\n".join(parts)


# Bounded inner-layer support signal builders moved to
# core.services.prompt_support_signals on 2026-04-29 (Boy Scout split).
# Re-imported here under their original private names so existing
# internal call-sites (notably _visible_support_signal_sections above)
# continue to work without changes.
from core.services.prompt_support_signals import (  # noqa: E402
    _development_focus_direction_label,
    _development_focus_support_signal_instruction,
    _goal_direction_label,
    _goal_support_signal_instruction,
    _growth_support_signal_instruction,
    _private_support_signal_instruction,
    _reflection_direction_label,
    _reflection_support_signal_instruction,
    _retained_memory_support_signal_instruction,
    _runtime_awareness_direction_label,
    _runtime_awareness_support_signal_instruction,
    _self_model_support_signal_instruction,
    _temporal_support_signal_instruction,
    _world_model_direction_label,
    _world_model_support_signal_instruction,
)


def _delegated_continuity_summary(context: dict[str, object]) -> str | None:
    continuity = str(context.get("continuity_summary") or "").strip()
    if continuity:
        return "\n".join(
            [
                "Delegated continuity:",
                f"- {continuity}",
            ]
        )

    recent_runs = recent_visible_runs(limit=1)
    if not recent_runs:
        return None
    run = recent_runs[0]
    status = str(run.get("status") or "").strip() or "unknown"
    finished_at = str(run.get("finished_at") or "").strip() or "unknown"
    capability_id = str(run.get("capability_id") or "").strip()
    parts = [f"latest_status={status}", f"latest_finished_at={finished_at}"]
    if capability_id:
        parts.append(f"latest_capability={capability_id}")
    return "\n".join(
        [
            "Delegated continuity:",
            "- " + " | ".join(parts),
        ]
    )


def _should_include_memory(text: str, *, mode: str) -> bool:
    normalized = str(text or "").lower()
    if mode == "heartbeat":
        return True
    triggers = (
        "huske",
        "remember",
        "memory",
        "første besked",
        "hvad skrev jeg",
        "forrige besked",
        "beskeden før",
        "før den sidste",
        "mit navn",
        "hvad hedder jeg",
        "navn",
        "preference",
        "prefer",
        "relationship",
        "continuity",
        "session",
        "repo",
        "repoet",
        "repository",
        "projekt",
        "project",
        "bygger vi",
        "arbejder vi i",
        "arbejder vi på",
        "working context",
    )
    return any(token in normalized for token in triggers)


def _should_include_guidance(text: str) -> bool:
    normalized = str(text or "").lower()
    triggers = (
        "tool",
        "tools",
        "skill",
        "skills",
        "capability",
        "read file",
        "search",
        "use tool",
        "use skill",
        "use capability",
        "invoke",
    )
    return any(token in normalized for token in triggers)


def _should_include_transcript(text: str) -> bool:
    normalized = str(text or "").lower()
    triggers = (
        "huske",
        "første besked",
        "hvad skrev jeg",
        "forrige besked",
        "beskeden før",
        "før den sidste",
        "remember",
        "memory",
        "session",
        "continuity",
        "earlier",
        "previous",
    )
    return any(token in normalized for token in triggers)


def _should_include_continuity(text: str) -> bool:
    normalized = str(text or "").lower()
    triggers = (
        "remember",
        "memory",
        "continuity",
        "session",
        "første besked",
        "hvad skrev jeg",
    )
    return any(token in normalized for token in triggers)


def prompt_mode_loader_summary() -> dict[str, object]:
    return {
        "visible_chat": "implemented",
        "heartbeat": "loader-ready",
        "future_agent_task": "loader-ready",
    }
