"""Transcript rendering + session compaction for prompts.

Udskilt fra core/services/prompt_contract.py (Boy Scout-split, ren
kode-flytning, 0 logik-ændring). Re-importeret i prompt_contract under de
oprindelige navne, så orchestratoren + eksterne call-sites (chat.py's
_pc._compact_inflight) + tests' monkeypatch/set-mutation af
prompt_contract.<navn> fortsat rammer de SAMME objekter. Kun ren flytning.
"""
from __future__ import annotations

import threading as _threading_mod

from core.services.tool_result_store import render_tool_result_for_prompt


# Hentere fra chat_sessions + db routes via prompt_contract-facaden, IKKE direkte.
# Grund (monkeypatch-søm): tests patcher fx
# `prompt_contract.chat_session_messages_since_last_compact` /
# `prompt_contract.visible_session_continuity` og forventer at disse (nu
# udskilte) transcript-byggere ser patchen. Ville vi importere navnene direkte
# her, ville bare-navn-opslaget ramme DETTE moduls globale og patchen på
# prompt_contract-navnet ville være usynlig → tavs regression. Ved at slå op på
# facade-modulet ved kald-tid honoreres patchen; upatched er de byte-identiske
# med de oprindelige funktioner (prompt_contract re-eksporterer dem forrest).
def chat_session_messages_since_last_compact(*args, **kwargs):
    from core.services import prompt_contract as _pc
    return _pc.chat_session_messages_since_last_compact(*args, **kwargs)


def _lifecycle_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "tool_result_lifecycle_enabled", False))
    except Exception:
        return False


def _cold_floor_for(session_id: str) -> int:
    try:
        from core.context.tool_result_lifecycle import get_cold_floor
        return get_cold_floor(session_id)
    except Exception:
        return 0


def recent_chat_session_messages(*args, **kwargs):
    from core.services import prompt_contract as _pc
    return _pc.recent_chat_session_messages(*args, **kwargs)


def recent_chat_session_messages_by_user_turns(*args, **kwargs):
    from core.services import prompt_contract as _pc
    return _pc.recent_chat_session_messages_by_user_turns(*args, **kwargs)


def visible_session_continuity(*args, **kwargs):
    from core.services import prompt_contract as _pc
    return _pc.visible_session_continuity(*args, **kwargs)


def _visible_session_continuity_instruction() -> str | None:
    continuity = visible_session_continuity()
    if not continuity["active"]:
        return None

    parts = [
        f"latest_status={continuity.get('latest_status') or 'unknown'}",
        f"latest_finished_at={continuity.get('latest_finished_at') or 'unknown'}",
    ]
    if continuity.get("latest_capability_id"):
        parts.append(f"latest_capability={continuity['latest_capability_id']}")
    lines = [
        "Visible session continuity:",
        "- " + " | ".join(parts),
    ]

    # Add conversation-level topic summary from recent messages
    # so Jarvis knows WHAT was discussed, not just that something happened.
    try:
        from core.services.chat_sessions import (
            list_chat_sessions,
        )
        _sessions = list_chat_sessions(limit=1)
        if _sessions:
            _latest_title = str(_sessions[0].get("title") or "").strip()
            if _latest_title and _latest_title != "New chat":
                lines.append(f"Last conversation topic: {_latest_title[:120]}")
    except Exception:
        pass

    # Inject LLM-generated session summaries for genuine cross-session memory
    try:
        from core.services.session_distillation import (
            build_previous_session_summaries,
        )

        prev_summaries = build_previous_session_summaries(limit=3)
        if prev_summaries:
            lines.append(prev_summaries)
    except Exception:
        pass

    recent_runs = list(continuity.get("recent_run_summaries") or [])[:3]
    if recent_runs:
        lines.append("Recent visible carry-over (newest first):")
        for item in recent_runs:
            run_parts = [
                f"status={item.get('status') or 'unknown'}",
                f"finished_at={item.get('finished_at') or 'unknown'}",
            ]
            if item.get("capability_id"):
                run_parts.append(f"cap={item.get('capability_id')}")
            lines.append("- " + " | ".join(run_parts))
    return "\n".join(lines)

def _recent_transcript_section(
    session_id: str | None,
    *,
    limit: int,
    include: bool,
) -> str | None:
    """Legacy flat-text fallback — used only when structured messages are not viable."""
    if not session_id or not include:
        return None
    # 2026-06-09: growing-window (cache-fix). Se kommentar i
    # _build_structured_transcript_messages.
    history = chat_session_messages_since_last_compact(session_id, max_total=4000)
    if not history:
        history = recent_chat_session_messages_by_user_turns(
            session_id, user_turns=max(limit, 1), max_total=4000,
        )
    if not history:
        return None
    lines = [
        "Recent transcript slice:",
        "Newest line is last.",
        "Tool lines are internal Jarvis-only observations, not user-visible chat.",
    ]
    window = history
    # CACHE-FIX (2026-06-30): recency-UAFHÆNGIG rendering (samme rod-årsag som
    # _build_structured_transcript_messages — se dér). Alle tool-results: stabil
    # summary, ét fast budget → byte-identiske tur efter tur → cachen holder.
    try:
        from core.runtime.settings import load_settings as _ls_render
        _tool_hist_cap = int(getattr(_ls_render(), "tool_result_history_max_chars", 1500))
    except Exception:
        _tool_hist_cap = 1500
    for index, item in enumerate(window):
        raw_role = item["role"]
        if raw_role == "user":
            role = "User"
        elif raw_role == "tool":
            role = "Internal tool result"
        else:
            from core.services.identity_composer import get_entity_name as _gnr
            role = _gnr()
        content = render_tool_result_for_prompt(
            str(item.get("content") or ""),
            expand=False,
            max_chars=_tool_hist_cap,
        )
        lines.append(f"{role}: {content}")
    return "\n".join(lines)

_SPEAKER_CACHE: dict[str, str] = {}

_ROLE_LABELS = {"member": "medlem", "guest": "gæst"}

def _resolve_speaker_display(user_id: str) -> str:
    """Map a chat_messages.user_id (Discord ID, etc.) to et afsender-præfiks med
    navn + rolle (Spor D, 16. jun).

    - Owner → kun navn ("Bjørn") — han ved det er sig selv.
    - Member/anden kendt rolle → "Navn (medlem)".
    - Ukendt user_id (ikke i users.json) → "Gæst (ukendt)" — så Jarvis VED at en
      fremmed taler i en fælleskanal (genkendelse + tillids-kalibrering; Spor A's
      lås forhindrer at gæsten kan få ham til at handle).
    - Tom user_id → "" (intet præfiks).

    Cached in-process. Bruges kun til multi-user prompt-bevidsthed i fælleskanaler;
    persisteres aldrig i selve chat-historikken.
    """
    if not user_id:
        return ""
    if user_id in _SPEAKER_CACHE:
        return _SPEAKER_CACHE[user_id]
    label = ""
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(user_id)
        if u is None:
            label = "Gæst (ukendt)"
        else:
            name = (getattr(u, "name", "") or "").strip()
            role = (getattr(u, "role", "") or "").strip().lower()
            if not name:
                label = "Gæst (ukendt)"
            elif role and role != "owner":
                label = f"{name} ({_ROLE_LABELS.get(role, role)})"
            else:
                label = name
    except Exception:
        label = ""
    _SPEAKER_CACHE[user_id] = label
    return label

def _build_structured_transcript_messages(
    session_id: str | None,
    *,
    limit: int,
    include: bool,
) -> list[dict[str, str]]:
    """Build structured chat messages from recent transcript.

    Returns list of {"role": "user"|"assistant", "content": "..."} dicts.
    Tool messages are compressed into the preceding assistant message as
    a short summary line, so they don't consume separate message slots.
    """
    if not session_id or not include:
        return []
    # 2026-06-09 (cache-fix revision): switched to growing-window since-compact.
    #
    # The user-turn-anchored fetch (committed earlier in the day) garanterer
    # at "60 user-turns" betyder 60 reelle samtale-runder, ikke 60 tool-rows.
    # MEN den er en *sliding* window — hver ny besked drop'er den ældste, så
    # transcript-prefix er ALDRIG identisk turn-til-turn. Det dræbte DeepSeek
    # prompt-cache (live hit rate 3-5% observeret) fordi ~90% af input-tokens
    # er transcript.
    #
    # Growing-window er den korrekte tradeoff: transcript vokser indtil
    # compact-marker rammer (200K-tærskel), og imellem er prefix stabilt så
    # cachen rammer ~80%+. Compact-systemet håndterer trimming.
    #
    # Fallback til paired-fetch kun hvis growing returnerer ingenting
    # (defensive).
    history = chat_session_messages_since_last_compact(session_id, max_total=4000)
    if not history:
        # "Siden compact" er tomt. To tilfælde:
        #  (a) Sessionen ER compacted (et compact_marker findes) men intet ligger EFTER det —
        #      markøren skrives med højeste id, så lige efter compaction er vinduet tomt. Her må
        #      vi IKKE loade hele 60-user-turn-vinduet: summary'en (prepended nedenfor) dækker
        #      det gamle, og et ubundet load er cache-uvenligt + redundant (Bjørn 2026-06-23).
        #      Load kun et lille bundet recent-vindue (2× keep_recent verbatim-turns).
        #  (b) Aldrig-compacted session → behold det fulde 60-turn-fallback.
        from core.services.chat_sessions import get_compact_marker
        _keep_recent = 20
        try:
            from core.runtime.settings import load_settings as _ls_keep
            _keep_recent = int(_ls_keep().context_keep_recent or 20)
        except Exception:
            pass
        if get_compact_marker(session_id):
            history = recent_chat_session_messages(session_id, limit=2 * _keep_recent)
        else:
            history = recent_chat_session_messages_by_user_turns(
                session_id, user_turns=max(limit, 1), max_total=4000,
            )
    if not history:
        return []

    # Phase 1: Merge consecutive tool messages into the preceding assistant turn.
    # Tool results become a short "[tool_name: status/summary]" annotation.
    window = history
    # ── CACHE-FIX (2026-06-30): recency-UAFHÆNGIG tool-result-rendering ───────
    # FØR (2026-06-09): seneste 20 tool-results fik expand=True/4000 tegn, ældre
    # expand=False/1200. Et resultat der gled fra "seneste 20" → "ældre" (bare
    # fordi samtalen voksede én tur) gen-renderedes fra 4000→1200 → DE SAMME
    # historik-bytes ændrede sig hver tur → DeepSeek-cache-prefixet brækkede fra
    # det punkt (verificeret rod-årsag: tool-tunge sessioner ~28% hit vs ~90% loft).
    # NU: ALLE historiske tool-results renderes ens (stabil summary, ét fast
    # budget) → byte-identiske tur efter tur → cachen holder. Fuldt resultat er på
    # disk (read_tool_result); nuværende turs resultater er fulde via followup-
    # exchanges. Append-only-immutabilitet = forskningskonsensus (Manus/Anthropic/
    # arXiv "Don't Break the Cache"). Budget er tunbart via settings.
    try:
        from core.runtime.settings import load_settings as _ld_trh
        _tool_hist_cap = int(getattr(_ld_trh(), "tool_result_history_max_chars", 1500))
    except Exception:
        _tool_hist_cap = 1500
    # ── COLD-TIER (flag-gated): tool-results below the session's cold_floor
    # render as a one-line stub (from the reference string only, never disk).
    # Read ONCE per build so _cold_floor is constant through the loop → each
    # historical tool item renders byte-identically turn-to-turn until the floor
    # discretely advances at run-end (a different subsystem). Same cache-safety
    # invariant as the warm path above.
    _cold_on = _lifecycle_enabled()
    _cold_floor = _cold_floor_for(session_id) if _cold_on else 0
    merged: list[dict[str, str]] = []
    for index, item in enumerate(window):
        raw_role = str(item.get("role") or "")
        # render_tool_result_for_prompt was being called for *all* roles with
        # max_chars=240, which silently chopped any user/assistant message
        # over 240 chars (Mini-Jarvis's 467-char replies showed up to Jarvis
        # as "tjekke nær…"). The tool-summary truncation only makes sense for
        # actual tool messages — apply it only there. User/assistant text
        # gets normal whitespace normalization and the per-role cap below.
        raw_content = str(item.get("content") or "")
        if raw_role == "tool":
            _mid = int(item.get("id", 0) or 0)
            # cold = id <= floor (warm = id > floor) — matches the lifecycle
            # module's accounting convention (compute_new_floor: warm=id>floor,
            # _candidate_by_tokens returns the ceiling-crossing id as cold).
            if _cold_on and _mid and _mid <= _cold_floor:
                content = render_tool_result_for_prompt(
                    raw_content, expand=False, stub=True,
                )
            else:
                content = render_tool_result_for_prompt(
                    raw_content,
                    expand=False,            # stabil summary-form (fuldt på disk)
                    max_chars=_tool_hist_cap,  # recency-UAFHÆNGIGT fast budget
                )
        else:
            content = " ".join(raw_content.split()).strip()
        if not content:
            continue

        if raw_role == "tool":
            # Compress tool result into a short annotation (samme faste cap)
            tool_summary = content[:_tool_hist_cap]
            if merged and merged[-1]["role"] == "assistant":
                # Append as annotation to previous assistant message
                merged[-1]["content"] += f"\n({tool_summary})"
            else:
                # No preceding assistant message — attach to a synthetic one
                merged.append({"role": "assistant", "content": f"({tool_summary})"})
            continue

        if raw_role == "user":
            # Truncate user messages. 8000 chars (~2000 tokens) per message —
            # bumped 2026-06-09 fra 2400 nu hvor visible lane kører 1M context.
            # Giver Bjørn rigelig plads til multi-paragraph briefs uden silent
            # chopping; selv 60 turns × 8000 chars = 480k chars = ~120k tokens,
            # langt under 1M-budget.
            if len(content) > 8000:
                content = content[:7997].rstrip() + "…"
            # Multi-user awareness: when a user_id is recorded for the message,
            # resolve to display name and prefix the content. Without this, in a
            # shared channel (Discord public, multi-member workspace) the model
            # cannot tell which human is speaking — Bjørn vs Michelle look
            # identical to it. The prefix is plain prose, not a marker.
            uid = str(item.get("user_id") or "").strip()
            if uid:
                speaker = _resolve_speaker_display(uid)
                if speaker:
                    content = f"{speaker}: {content}"
            merged.append({"role": "user", "content": content})
        else:
            # assistant — symmetric 8000-char cap (bumped 2026-06-09 fra 2400)
            # så Jarvis' egne tidligere svar ikke truncates mid-sentence i hans
            # egen working memory. Samme rationale som user-cap: 1M context har
            # rigelig headroom.
            if len(content) > 8000:
                content = content[:7997].rstrip() + "…"
            assistant_msg: dict[str, str] = {"role": "assistant", "content": content}
            # Thinking-mode replay: Deepseek v4-pro/reasoner kræver at
            # reasoning_content fra prior assistant-turns sendes med tilbage.
            # Vi gemmer det nu pr. message i chat_messages.reasoning_content;
            # threades her ind i transcript-output så API'et får det.
            r_content = str(item.get("reasoning_content") or "").strip()
            if r_content:
                # Capper også reasoning ved 2400 så vi ikke pumper kæmpe
                # context tilbage. Deepseek bryder sig ikke om hvor langt det
                # er, kun at det er der.
                if len(r_content) > 8000:
                    r_content = r_content[:7997].rstrip() + "…"
                assistant_msg["reasoning_content"] = r_content
            merged.append(assistant_msg)

    # Phase 2: Ensure alternating user/assistant turns (required by some models).
    # Drop messages that break alternation rather than fabricating filler.
    result: list[dict[str, str]] = []
    expected_role = None  # None means either is fine
    for msg in merged:
        role = msg["role"]
        if expected_role is None:
            result.append(msg)
            expected_role = "assistant" if role == "user" else "user"
        elif role == expected_role:
            result.append(msg)
            expected_role = "assistant" if role == "user" else "user"
        else:
            # Same role twice — merge with previous if possible
            if result and result[-1]["role"] == role:
                result[-1]["content"] += "\n" + msg["content"]
            else:
                result.append(msg)
                expected_role = "assistant" if role == "user" else "user"

    # ── Compact marker injection ───────────────────────────────────────────
    if session_id:
        # Facade-opslag (monkeypatch-søm): tests patcher
        # prompt_contract._get_compact_marker_for_transcript /
        # ._maybe_auto_compact_session og forventer at denne (udskilte) bygger
        # ser patchen. Bare-navn ville ramme dette moduls global → usynlig patch.
        from core.services import prompt_contract as _pc
        marker_summary = _pc._get_compact_marker_for_transcript(session_id)
        if marker_summary:
            result = [
                {
                    "role": "user",
                    "content": f"[Komprimeret historik fra tidligere i samtalen:\n{marker_summary}]",
                },
                {"role": "assistant", "content": "Forstået."},
            ] + result

        # ── Auto-compact check ─────────────────────────────────────────────
        try:
            from core.runtime.settings import load_settings as _load_compact_settings
            _compact_settings = _load_compact_settings()
            _pc._maybe_auto_compact_session(session_id, result, _compact_settings)
        except Exception:
            pass

    return result

def _get_compact_marker_for_transcript(session_id: str) -> str | None:
    """Fetch the most recent compact marker for this session (monkeypatchable).

    Lag D: Before returning, runs compact-mismatch detection on recent user
    messages. If the user has corrected a compaction claim, auto-regenerates
    the marker and returns the corrected version.
    """
    try:
        from core.services.chat_sessions import get_compact_marker
        from core.context.compact_ground_truth import (
            detect_compact_mismatch_in_chat,
            auto_regenerate_compact_marker,
        )

        # Check if user messages contradict the compact marker
        mismatches = detect_compact_mismatch_in_chat(session_id)
        if mismatches:
            high_confidence = any(m.get("confidence") == "high" for m in mismatches)
            if high_confidence:
                import logging as _lg
                _lg.getLogger(__name__).info(
                    "compact_heal: session=%s has %d high-confidence mismatches — regenerating",
                    session_id, sum(1 for m in mismatches if m.get("confidence") == "high"),
                )
                auto_regenerate_compact_marker(session_id)

        # Return the (possibly regenerated) marker
        return get_compact_marker(session_id)
    except Exception:
        return None

# Dedup: kun én baggrunds-compaction ad gangen pr. session.

_compact_inflight: set[str] = set()

_compact_inflight_lock = _threading_mod.Lock()

def _ground_truth_for(session_id: str) -> str:
    """Best-effort VERIFIED-facts block (git HEAD, recent commits, key files) for the session,
    anchoring the summariser against invention. Self-safe → '' on any error."""
    try:
        from core.context.compact_ground_truth import (
            collect_compact_ground_truth, format_ground_truth_block,
        )
        return format_ground_truth_block(collect_compact_ground_truth(session_id))
    except Exception:
        return ""


def _make_structured_summariser(focus: str | None = None, *, session_id: str | None = None):
    """Build a summarise_fn(old_messages)->str for compact_session_history.

    2-stage + fault-tolerant (2026-07-18 live-compaction spec):
      Stage-A: fold OLD tool-results to stubs so the (cheap) summariser sees prose, not raw
               tool dumps — mitigates cheap-model degradation on tool-heavy history.
      Stage-B: structured, thread-preserving 9-section summary via the cheap lane
               (call_compact_llm — non-Groq cheap providers first).
      Quality gate: if the LLM summary is empty/too-short/broken, fall back to a
               deterministic mechanical join so compaction NEVER produces an empty marker
               (store_compact_marker rejects empty) and never hard-fails the turn."""
    from core.context.compact_llm import call_compact_llm
    from core.context.compaction_policy import (
        build_structured_summary_prompt,
        extract_summary,
        fold_old_tool_results,
        summary_looks_valid,
    )

    _gt = _ground_truth_for(session_id) if session_id else ""

    def _summarise(old_msgs: list[dict]) -> str:
        folded, _ = fold_old_tool_results(old_msgs, keep=0)  # prose for the summariser
        # Cap input (head+tail) so a free/cheap model isn't handed ~69k tokens → hangs.
        prompt = build_structured_summary_prompt(
            folded, focus=focus, ground_truth=_gt, max_transcript_chars=60_000,
        )
        # HARD timeout (2026-07-18 hang-fix): the cheap-lane call has no internal timeout,
        # so a slow/dead free provider could hang compaction for MINUTES. Bound it in a
        # worker future; on timeout → deterministic mechanical fallback below. Zombie provider
        # thread may linger, but the user-visible compaction is bounded.
        import concurrent.futures as _cf
        raw = ""
        try:
            with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                _fut = _ex.submit(call_compact_llm, prompt, max_tokens=2500)
                raw = str(_fut.result(timeout=45) or "")
        except _cf.TimeoutError:
            import logging as _lg
            _lg.getLogger(__name__).warning(
                "compaction summary timed out (>45s, slow cheap-lane) — mechanical fallback"
            )
            raw = ""
        except Exception as _exc:
            import logging as _lg
            _lg.getLogger(__name__).warning("compaction summary raised (%s) — fallback", _exc)
            raw = ""
        text = extract_summary(raw)  # strip <thinking>, pull <summary>…</summary>
        if summary_looks_valid(text):
            return text
        # Deterministic fallback — mechanical, never empty (thread still traceable via
        # the raw messages kept under the marker in the DB). Improved 2026-07-23:
        # the old version truncated EVERY message to 200 chars, so a failed summariser
        # collapsed the whole arc into stubs (the "200-char fake summary"). Now:
        #  - USER turns kept much fuller (up to 800 chars) — they carry the intent/asks
        #    that must survive; the assistant can be reconstructed from them.
        #  - assistant turns kept to 400 chars (the gist), tool noise already folded.
        #  - larger total budget so the fallback is a real (if rough) record, not stubs.
        def _clip(role: str, content: str) -> str:
            c = " ".join(str(content or "").split())
            cap = 800 if role == "user" else 400
            return f"[{role}] {c[:cap]}{'…' if len(c) > cap else ''}"
        parts = [_clip(str(m.get("role", "?")), m.get("content") or "") for m in old_msgs]
        joined = "\n".join(p for p in parts if p.strip())
        return (
            "<summary>[Mechanical fallback — the summariser model returned nothing usable, "
            "so this is a truncated but faithful record of the arc (user turns kept fuller). "
            "Full raw messages remain in the session DB under the compact marker.]\n"
            + joined[:18000] + "</summary>"
        )

    return _summarise


def _run_session_compaction(
    session_id: str,
    keep_recent: int,
    *,
    low_water_tokens: int = 15_000,
    focus: str | None = None,
) -> None:
    """Selve summariserings-arbejdet (baggrundstråd). Skriver compact_marker via det
    eksisterende session_compact-system. Round-atomisk + struktureret 2-trins. Self-safe."""
    try:
        from core.context.session_compact import compact_session_history
        import logging as _log
        _log.getLogger(__name__).info(
            "prompt_contract: auto-compact (baggrund) for session %s (low_water=%d)",
            session_id, low_water_tokens,
        )
        # Kept tail budget: lidt under low-water så summary + tail ≈ low-water.
        _tail_budget = max(int(low_water_tokens * 0.8), 4_000)
        result = compact_session_history(
            session_id,
            keep_recent_tokens=_tail_budget,
            summarise_fn=_make_structured_summariser(focus, session_id=session_id),
        )
        if result is not None:
            try:
                from core.services.finitude_runtime import note_context_compaction
                note_context_compaction(
                    session_id=session_id,
                    freed_tokens=int(result.freed_tokens or 0),
                    summary_text=str(result.summary_text or ""),
                )
            except Exception:
                pass
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).warning("auto_compact_session failed: %s", exc)
    finally:
        with _compact_inflight_lock:
            _compact_inflight.discard(session_id)

def _maybe_auto_compact_session(
    session_id: str,
    current_messages: list[dict],
    settings,
) -> None:
    """Trigger session compact hvis transcript-tokens overstiger tærsklen — i BAGGRUNDEN.

    2026-06-23 (Bjørn): summariserings-LLM-kaldet kørte FØR synkront på prompt-assembly-
    hot-path → blokerede brugerens tur i flere sekunder når det udløstes. Nu spawnes det i
    en baggrundstråd (deduppet pr. session): den nuværende tur fortsætter uændret (trimmen
    beskytter den), og den NÆSTE tur nyder godt af det skrevne compact_marker.
    """
    from core.context.token_estimate import estimate_messages_tokens
    from core.context.compaction_policy import compaction_decision
    from core.services.model_context import model_context_window

    # Model-BEVIDST beslutning (2026-07-18 live-compaction spec):
    #  PRIMÆR   = absolut opmærksomheds-budget (35k), model-UAFHÆNGIG → holder Jarvis skarp
    #             selv på deepseek-flash's 1M-vindue (den gamle max(130k, frac×1M)=650k fyrede
    #             ALDRIG → hele historikken blev sendt hver tur).
    #  SIKKERHED = model-vindue × safety_fraction (backstop; skalerer glm-5.1 256k / flash 1M).
    _budget = int(getattr(settings, "context_attention_budget_tokens", 35_000) or 35_000)
    _low = int(getattr(settings, "context_attention_low_water_tokens", 15_000) or 15_000)
    _safety = float(getattr(settings, "context_compact_safety_fraction", 0.85) or 0.85)
    decision = compaction_decision(
        estimate_messages_tokens(current_messages),
        provider=str(getattr(settings, "visible_model_provider", "") or ""),
        model=str(getattr(settings, "visible_model_name", "") or ""),
        attention_budget=_budget,
        low_water=_low,
        safety_fraction=_safety,
        model_window_fn=model_context_window,
    )
    if not decision.should_compact:
        return
    with _compact_inflight_lock:
        if session_id in _compact_inflight:
            return
        _compact_inflight.add(session_id)
    try:
        # Facade-opslag (monkeypatch-søm): tests patcher
        # prompt_contract._run_session_compaction og forventer at baggrundstråden
        # kalder patchen. Bare-navn ville ramme dette moduls global.
        from core.services import prompt_contract as _pc
        _threading_mod.Thread(
            target=_pc._run_session_compaction,
            args=(session_id, int(getattr(settings, "context_keep_recent", 20) or 20)),
            kwargs={"low_water_tokens": decision.low_water_target},
            name=f"compact-{str(session_id)[:12]}", daemon=True,
        ).start()
    except Exception:
        with _compact_inflight_lock:
            _compact_inflight.discard(session_id)
