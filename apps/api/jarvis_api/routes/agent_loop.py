"""Client-owned agent loop: /v1/agent/step.

Ét ENKELT Jarvis-model-tur der RETURNERER tool_calls til klienten i stedet for at
eksekvere dem server-side. Klienten (jarvis-code) ejer loopet: den kører værktøjer
LOKALT på brugerens maskine, føjer resultatet til samtalen og kalder igen — indtil
modellen svarer uden tool_calls.

Hvorfor: den server-side visible-lane streamer lange svar (SSE), hvilket åbnede
"cutoff-bug-familien" (klient/forbindelse taber halen). Her er hvert step en KORT,
IKKE-streamende request/response — strukturelt umuligt at cutte midt i en besked.
Værktøjer kører på klienten (rigtig coding-CLI der redigerer brugerens filer).

Modellen er stadig Jarvis' synlige model (health-gated → deepseek), med en fokuseret
Jarvis-coding-agent system-prompt. Tung memory/identity-assembly springes bevidst over
her for hastighed pr. step (klient-loops kalder ofte).
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# Module-level names (test monkeypatches these):
from core.tools.simple_tools import execute_tool
from core.tools.jc_tool_catalog import unalias
from core.tools.brain_write_gate import check_brain_write_allowed
from core.services import skill_engine, skill_autosurface

# Module-level seams (tests monkeypatch these; keeps side effects gate-able):
from core.runtime.db_core import get_runtime_state_value
from core.costing.ledger import record_cost
from core.services.followup_observer import note_empty_completion

logger = logging.getLogger("uvicorn.error")
router = APIRouter()


def _resolve_role() -> str:
    """Caller role. Mirror /v1/tools/native (owner default). Owner token -> 'owner'."""
    try:
        from core.identity.workspace_context import effective_role
        return effective_role() or "owner"
    except Exception:
        return "owner"


def _owner_scoped_user_id(raw: str | None, role: str) -> str:
    """jarvis-code (owner-authed) sender ofte TOMT user_id → uden det kan memory/
    workspace-tools ikke scope til ejerens workspace (workspace_dir kræver user_id →
    tom recall, 'kun vores session'). Udled ejerens discord_id når kalderen er owner
    og intet user_id blev sendt. Non-owner / eksplicit user_id → uændret."""
    uid = str(raw or "").strip()
    if uid or role != "owner":
        return uid
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        return str(get_owner_discord_id() or "").strip()
    except Exception:
        return ""


# ── Fase 5 Task 19: provider XML tool-call fallback (flag-gated) ──────────
# Some providers/models (Ollama, Gemini — reference_gemini_ollama_toolcall_400)
# return EMPTY native tool_calls and instead emit an XML/tagged convention in
# the assistant TEXT: <tool_call>{"name": ..., "arguments": {...}}</tool_call>.
# Behind jc_xml_toolcall_fallback (default OFF), parse that convention out of
# the text and normalise it into the SAME tool_call structure the client
# already consumes — ONLY when native tool_calls are absent.
_XML_TOOLCALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def _parse_xml_tool_calls(text: str) -> list[dict[str, Any]]:
    """Extract <tool_call>{json}</tool_call> tags from `text` and normalise
    them into the standard tool_call dict shape. Malformed JSON inside a tag
    is skipped (never raises) — degrades to leaving that tag as content."""
    calls: list[dict[str, Any]] = []
    for m in _XML_TOOLCALL_RE.finditer(text or ""):
        raw = m.group(1).strip()
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        name = str(obj.get("name") or obj.get("tool") or "").strip()
        if not name:
            continue
        arguments = obj.get("arguments", obj.get("parameters", {}))
        if not isinstance(arguments, (dict, list)):
            arguments = {}
        calls.append({
            "id": f"xml-{uuid.uuid4().hex[:12]}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
        })
    return calls


def _strip_xml_tool_calls(text: str) -> str:
    """Remove <tool_call>...</tool_call> tags from `text` (used once they've
    been parsed into structured tool_calls, so they don't ALSO show up as
    visible assistant content)."""
    return _XML_TOOLCALL_RE.sub("", text or "").strip()


def _apply_xml_toolcall_fallback(content: str, tool_calls: list[dict[str, Any]]
                                 ) -> tuple[str, list[dict[str, Any]]]:
    """Behind jc_xml_toolcall_fallback: if native tool_calls is empty AND the
    text contains <tool_call> tags, parse+normalise them and strip them from
    content. Flag OFF, native tool_calls present, or malformed/absent XML ->
    unchanged pass-through (byte-identical to today)."""
    if tool_calls:
        return content, tool_calls
    if not _flag("jc_xml_toolcall_fallback"):
        return content, tool_calls
    xml_calls = _parse_xml_tool_calls(content)
    if not xml_calls:
        return content, tool_calls
    return _strip_xml_tool_calls(content), xml_calls


def _apply_privilege_enforcement(role: str, requested_mode: str) -> tuple[str, bool]:
    """Fase 5 Task 1 (server half): owner-only privilege gate for the
    approval-timing axis jarvis-code sends in agent/step's body.

    When `jc_privilege_enforcement` is ON and a non-owner caller requests
    full-auto/bypass (the two unattended, no-prompt timing modes), downgrade
    to "ask" so a guest/non-owner session can never run tool calls without a
    human confirming. Inert (pass-through, never downgraded) when the flag is
    OFF or the caller IS the owner — matches the flag-gated-default-OFF
    contract for every server change in this phase.

    Returns (effective_mode, downgraded).
    """
    if not requested_mode:
        return requested_mode, False
    if role == "owner":
        return requested_mode, False
    if not _flag("jc_privilege_enforcement"):
        return requested_mode, False
    if requested_mode in ("full-auto", "bypass"):
        return "ask", True
    return requested_mode, False


def _flag(name: str, default: bool = False) -> bool:
    """Read a runtime-state boolean flag. Fail-safe: any error/absence -> default.
    All Fase-0 behavior changes gate on these; every flag defaults OFF so the
    deploy is inert until an operator flips it."""
    try:
        # Coerce like get_runtime_state_bool (kept inline so the module-level
        # get_runtime_state_value seam stays monkeypatchable in tests): a flag
        # stored as the string "off" must read False — bool("off") is True.
        from core.runtime.db_core import _FALSEY_FLAG_STRINGS
        val = get_runtime_state_value(name, default)
        if isinstance(val, str):
            return val.strip().lower() not in _FALSEY_FLAG_STRINGS
        return bool(val)
    except Exception:
        return default


def _settings():
    """RuntimeSettings for the jarvis-code Fase 4 parity flags (config-file backed,
    core/runtime/settings.py — distinct from the DB-backed _flag() above). Test
    seam: monkeypatch al._settings to stub the four `agent_step_*` booleans without
    touching the on-disk runtime.json. Self-safe: any error -> a fresh (all-False)
    RuntimeSettings, so a broken config never turns Fase-4 behavior on by accident."""
    try:
        from core.runtime.settings import load_settings
        return load_settings()
    except Exception:
        from core.runtime.settings import RuntimeSettings
        return RuntimeSettings()


def _emit_agent_nerve(*, status: str, provider: str, model: str,
                      tokens_in: int, tokens_out: int, cost_usd: float,
                      duration_ms: int, tool_calls: int, finish_reason: str,
                      user_id: str, session_id: str) -> None:
    """Make the client-owned agent lane visible in Den Intelligente Central.
    Self-safe: any failure is swallowed (observability must never break a turn)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "agent", "nerve": "agent_step",
            "status": str(status), "provider": str(provider), "model": str(model),
            "tokens_in": int(tokens_in), "tokens_out": int(tokens_out),
            "cost_usd": float(cost_usd), "duration_ms": int(duration_ms),
            "tool_calls": int(tool_calls), "finish_reason": str(finish_reason),
            "user_id": str(user_id or ""), "session_id": str(session_id or ""),
        })
    except Exception:
        logger.debug("agent/step nerve emit fejlede", exc_info=True)


def _resolve_workspace_name(user_id: str) -> str:
    """Map an authenticated caller's user_id to their workspace name. Empty user_id
    (owner) or unknown user -> 'default' (today's behavior, Bjørn's workspace)."""
    uid = str(user_id or "").strip()
    if not uid:
        return "default"
    try:
        from core.identity.users import find_user_by_discord_id
        user = find_user_by_discord_id(uid)
        if user and str(getattr(user, "workspace", "") or "").strip():
            return str(user.workspace).strip()
    except Exception:
        logger.debug("agent/step workspace-resolve fejlede", exc_info=True)
    return "default"


def _extract_text(content: Any) -> str:
    """Extract plain text from a message `content` that may be a str OR an array of
    typed blocks ({type:'text'|'image', ...}). Multimodal foundation: image blocks pass
    through to the model untouched (chat_messages.extend), but memory-recall only needs
    the text. For a plain str this is identical to today's behavior (inert)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return " ".join(p for p in parts if p)
    return str(content or "")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


_SYSTEM_PROMPT = (
    "Du er Jarvis — en skarp, kortfattet coding-agent der lever i Bjørns terminal "
    "(jarvis-code). Du arbejder på HANS lokale maskine: værktøjerne (bash, read_file, "
    "write_file, edit_file, glob, grep, web_fetch, web_scrape) eksekveres af klienten "
    "lokalt, og du får resultaterne tilbage. Arbejd trinvist: kald værktøjer for at "
    "undersøge og ændre kode i stedet for at gætte. Når du har nok til at svare, så svar "
    "klart og kort på dansk. Kald ikke værktøjer i tomgang; stop når opgaven er løst."
)

# Fase 6 Task 5: the framing sentence above hardcodes Bjørn's ownership
# ("Bjørns terminal"/"HANS lokale maskine") — correct for the owner (the
# common case today) but wrong once jc_agent_user_scoping resolves a
# DIFFERENT caller's workspace (a member is not standing in Bjørn's
# terminal). Generic, caller-neutral variant used ONLY when the flag is on
# AND the resolved workspace isn't the owner's default — inert (byte-
# identical _SYSTEM_PROMPT) for the owner and for the flag-off baseline.
_SYSTEM_PROMPT_GENERIC = (
    "Du er Jarvis — en skarp, kortfattet coding-agent der arbejder i en udvikler-"
    "terminal (jarvis-code) på DIN lokale maskine: værktøjerne (bash, read_file, "
    "write_file, edit_file, glob, grep, web_fetch, web_scrape) eksekveres af klienten "
    "lokalt, og du får resultaterne tilbage. Arbejd trinvist: kald værktøjer for at "
    "undersøge og ændre kode i stedet for at gætte. Når du har nok til at svare, så svar "
    "klart og kort på dansk. Kald ikke værktøjer i tomgang; stop når opgaven er løst."
)


def _system_prompt_intro(name: str) -> str:
    """Fase 6 Task 5: pick the caller-appropriate framing sentence. Owner
    workspace ('default') or the jc_agent_user_scoping flag OFF -> the
    original, unchanged _SYSTEM_PROMPT (no behavior change). A resolved
    NON-default workspace with the flag ON -> the generic, caller-neutral
    framing — never claims a member is on Bjørn's machine."""
    if name and name != "default" and _flag("jc_agent_user_scoping"):
        return _SYSTEM_PROMPT_GENERIC
    return _SYSTEM_PROMPT


# ── Skill catalog injection (Fase 3, Task 3) ────────────────────────────
# CC-style activation nudge + a client-side (jarvis-code) tool-name legend
# (see docs/_archive/skills-jarvis-compat.md). Both are inert unless
# `_skill_catalog()` actually produces a non-empty catalog — appended
# together as a single trailing block so prompt-cache prefixes stay stable.
_SKILL_ACTIVATION = (
    "Hvis en skill nedenfor matcher opgaven, kald skill_gate(query=<opgaven>) FØR du gør "
    "noget andet — den loader det rette workflow."
)

_CC_TOOL_LEGEND = (
    "Skill-instruktioner kan nævne Claude Code-tools. Oversæt: Write → write_file/bash · "
    "Read → read_file · Edit → edit_file · Task → dispatch (subagent) · "
    "Worktree → git worktree via bash · TodoWrite → intern plan · Grep/Glob → grep/glob."
)

# ── Harness behavioural contract (Fase 4, Task 7) ───────────────────────
# Adfærds-klausuler der gør Jarvis stabil i terminalen — samme ånd som Claude
# Codes egen harness-kontrakt. Appended, når flaget er sat, FØR <env>-blokken
# (Fase 4, Task 2), så den ligger i den cachebare HOVED-del af prompten, ikke
# i den flygtige hale — at slå kontrakten til/fra rører ikke <env>'s position
# eller Task 4's præfiks-signatur.
_HARNESS_CONTRACT = (
    "\n\n## ARBEJDSKONTRAKT\n"
    "- Ingen indledning eller afrunding: svar direkte på opgaven, spring "
    "\"jeg vil nu...\"/\"det var det\"-fyld over.\n"
    "- Kommentar-disciplin: tilføj ikke kodekommentarer medmindre brugeren beder om "
    "det, eller koden reelt kræver forklaring — lad koden tale for sig selv.\n"
    "- Proaktivitet har grænser: gør det der bliver bedt om; overrask ikke brugeren "
    "med uopfordrede ekstra ændringer eller handlinger.\n"
    "- Kan du ikke/vil du ikke gøre noget, sig det kort og giv ét konkret alternativ "
    "(1-2 linjer) i stedet for bare at afvise.\n"
    "- Verificér før du siger \"færdig\": kør/tjek det du har lavet, hævd aldrig at "
    "noget virker uden at have set det virke."
)


def _skill_catalog() -> str:
    """Owner-approved skill catalog for the system prompt (Fase 3, Task 3).

    Reuses the existing skill engine verbatim (skill_engine.list_skills) —
    never rebuilds skill matching/loading. Narrowed to the owner-approved
    allowlist (skill_autosurface.filter_to_approved), so with the master
    flag off or nothing approved this returns "" and the prompt is
    byte-identical to today (feature stays inert until the owner opts in).
    Progressive disclosure: name + use_when + tags only, capped at ~15
    lines / ~1000 chars so the injection cost stays tiny (~100 tokens).
    Self-safe: any failure returns "" — must never break the prompt build.
    """
    try:
        skills = skill_engine.list_skills()
        names = skill_autosurface.filter_to_approved([s["name"] for s in skills])
        if not names:
            return ""
        by_name = {s["name"]: s for s in skills}
        lines: list[str] = []
        for n in names[:15]:
            s = by_name.get(n)
            if not s:
                continue
            tags = ", ".join((s.get("tags") or [])[:3])
            lines.append(f"- {n}: {s.get('use_when', '')} [{tags}]")
        if not lines:
            return ""
        header = (
            "\n\n## TILGÆNGELIGE SKILLS "
            "(kald skill_gate(query=...) FØR du handler hvis én matcher)\n"
        )
        text = header + "\n".join(lines)
        return text[:1000]
    except Exception:
        logger.debug("agent/step: skill catalog build fejlede", exc_info=True)
        return ""


_IDENTITY_BUDGET = 1600  # tegn pr. workspace-fil (nok til stemme, billigt at cache)


def _identity_context(name: str = "default") -> str:
    """Kompakt identitets-lag (SOUL + IDENTITY + USER) fra `name`-workspace — nok til at
    Jarvis har sin STEMME og KENDER brugeren, uden den tunge memory-assembly. Self-safe."""
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        ws = ensure_default_workspace(name=name)
    except Exception:
        return ""
    parts: list[str] = []
    for fname, label in (("SOUL.md", "HVEM DU ER (soul)"),
                         ("IDENTITY.md", "IDENTITET"),
                         ("USER.md", "HVEM BJØRN ER")):
        try:
            text = (ws / fname).read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            continue
        if text:
            parts.append(f"## {label}\n{text[:_IDENTITY_BUDGET]}")
    if not parts:
        return ""
    return ("\n\nDette er din kontinuerlige kerne — vær tro mod den, også her i terminalen:\n\n"
            + "\n\n".join(parts))


_FULL_CTX_CACHE: dict[str, tuple[str, float]] = {}
_FULL_CTX_TTL = 90.0  # s — genbrug inden for en tur (flere tool-runder), undgå re-build


def _full_context(user_message: str, name: str = "default") -> str:
    """FULD Jarvis-kontekst (memory-recall + cognitive_state + indre liv + awareness) til
    'full'-tier client loop — samme assembly som den synlige lane (PromptAssembly.text),
    men tools eksekveres stadig LOKALT af klienten. Tung → cache pr. besked-hash+workspace i
    kort TTL så en turs flere tool-runder ikke genbygger den (nøglen inkluderer `name` så
    caches for forskellige workspaces aldrig blander sig). Self-safe → '' (falder til identity)."""
    import hashlib
    import time as _t
    # Cache-nøgle inkluderer current_user_id() så en brugers scopede recall aldrig
    # serveres til en anden (assembly'en bygges nu inde i user_context — recall er per-bruger).
    try:
        from core.identity.workspace_context import current_user_id as _cuid
        _uid_key = _cuid() or ""
    except Exception:
        _uid_key = ""
    key = hashlib.sha256(
        (f"{_uid_key}\x00{name}\x00{user_message or ''}").encode("utf-8")).hexdigest()[:16]
    now = _t.monotonic()
    hit = _FULL_CTX_CACHE.get(key)
    if hit and hit[1] > now:
        return hit[0]
    text = ""
    try:
        from core.services.prompt_contract import build_visible_chat_prompt_assembly
        provider, model = _resolve_target()
        asm = build_visible_chat_prompt_assembly(
            provider=provider, model=model, user_message=user_message or "", name=name)
        text = str(getattr(asm, "text", "") or "")
    except Exception:
        logger.debug("agent/step: full-context build fejlede", exc_info=True)
        text = ""
    if text:
        if len(_FULL_CTX_CACHE) > 32:
            for k in list(_FULL_CTX_CACHE)[:16]:
                _FULL_CTX_CACHE.pop(k, None)
        _FULL_CTX_CACHE[key] = (text, now + _FULL_CTX_TTL)
    return text


def _build_system_prompt(context: str, user_message: str = "", name: str = "default",
                         env: dict | None = None) -> str:
    """context: 'none' (ren coding) | 'identity' (stemme + kender brugeren, default) |
    'full' (hele Jarvis: memory + cognitive_state + indre liv — tools stadig LOKALT).
    `name`: caller-workspace (jc_agent_user_scoping-gated, default 'default').
    `env`: client-supplied cwd/git/os/date facts (Fase 4, Task 2) — rendered as the
    LAST, most volatile section (agent_step_env_block_enabled-gated) so everything
    before it stays a stable, cacheable prefix (Fase 4, Task 4)."""
    _intro = _system_prompt_intro(name)
    if context == "none":
        base = _intro
    elif context == "full":
        full = _full_context(user_message, name)
        if full:
            base = _intro + "\n\n" + full
        else:
            # full-assembly fejlede → degradér til identity (crash aldrig)
            ident = _identity_context(name)
            base = _intro + ident if ident else _intro
    else:
        ident = _identity_context(name)
        base = _intro + ident if ident else _intro

    # Skill catalog block appended once, AFTER identity/full context, on every
    # path (including 'none' — skills are relevant even in pure-coding tier).
    # Empty catalog -> base unchanged -> byte-identical to pre-Fase-3 prompt.
    catalog = _skill_catalog()
    if catalog:
        base = base + catalog + "\n\n" + _SKILL_ACTIVATION + "\n\n" + _CC_TOOL_LEGEND

    _fase4_settings = _settings()

    # Fase 4 Task 7 (flag-gated): harness contract goes in the CACHEABLE HEAD —
    # BEFORE <env> below — so toggling it independently of the env flag never
    # moves <env>'s position or Task 4's prefix signature (which is computed
    # over everything before <env>). Off -> base unchanged.
    if _fase4_settings.agent_step_harness_contract_enabled:
        base = base + _HARNESS_CONTRACT

    # Fase 4 Task 2 (flag-gated): <env> is the LAST section appended — must stay
    # the tail so Task 4's cache-prefix signature (computed over everything
    # BEFORE this) never sees it. Off or no env -> base unchanged.
    if env and _fase4_settings.agent_step_env_block_enabled:
        from apps.api.jarvis_api.routes.jc_env import render_env_block
        block = render_env_block(env)
        if block:
            base = base + block
    return base


def _apply_dynamic_tail_split(chat_messages: list[dict], enabled: bool) -> list[dict]:
    """Fase A1: honorér DYNAMIC_TAIL_SENTINEL i system-beskeden — klip systemet ved
    sentinel'en (stabilt cacheligt hoved) og flyt den volatile hale til den SIDSTE
    user-besked, så [stabilt system + samtale] forbliver et cache-stabilt prefix
    (spejler visible_model._build_visible_input). enabled=False eller ingen sentinel
    → chat_messages returneres byte-identisk. Uden en user-besked at hænge halen på
    beholdes halen (uden sentinel) i systemet (fallback — aldrig tab)."""
    if not enabled or not chat_messages:
        return chat_messages
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL
    sys_msg = chat_messages[0]
    if sys_msg.get("role") != "system":
        return chat_messages
    content = str(sys_msg.get("content") or "")
    if DYNAMIC_TAIL_SENTINEL not in content:
        return chat_messages
    head, _, tail = content.partition(DYNAMIC_TAIL_SENTINEL)
    out = [dict(m) for m in chat_messages]
    out[0]["content"] = head
    last_user_idx = next((i for i in range(len(out) - 1, -1, -1)
                          if out[i].get("role") == "user"), None)
    if last_user_idx is None:
        out[0]["content"] = head + tail  # fallback: ingen user → behold hale i system
        return out
    out[last_user_idx] = dict(out[last_user_idx])
    out[last_user_idx]["content"] = str(out[last_user_idx].get("content") or "") + tail
    return out


def _apply_volatile_prepend(chat_messages: list[dict]) -> tuple[list[dict], str]:
    """Option B (frys-halen, 2026-07-19): klip system ved DYNAMIC_TAIL_SENTINEL og
    PREPEND den volatile hale til den AKTUELLE (sidste) user-besked — blok FØRST,
    brugerens ord SIDST (fokus bevaret: modellen ser konteksten og så spørgsmålet til
    sidst). Returnerer (messages, volatile_block) så ruten kan sende blokken til klienten,
    der PERSISTERER den ind i den gemte besked → byte-identisk replay næste tur.

    KRITISK — modsat det reverterede efd35153/_apply_dynamic_tail_split: her relokeres
    INTET. Tidligere user-beskeder røres aldrig (de bærer allerede deres egen frosne blok
    fra klientens persist). Kun den nye, blokløse sidste-besked får en frisk blok. Det er
    dét der holder deepseek prefix-cachen (append-only, aldrig omskriv-forrige).

    Ingen sentinel / ingen user-besked → (uændret, "") — fail-open, aldrig tab."""
    if not chat_messages:
        return chat_messages, ""
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL
    sys_msg = chat_messages[0]
    if sys_msg.get("role") != "system":
        return chat_messages, ""
    content = str(sys_msg.get("content") or "")
    if DYNAMIC_TAIL_SENTINEL not in content:
        return chat_messages, ""
    head, _, tail = content.partition(DYNAMIC_TAIL_SENTINEL)
    tail = tail.strip("\n")
    out = [dict(m) for m in chat_messages]
    if not tail:
        out[0]["content"] = head
        return out, ""
    out[0]["content"] = head
    last_user_idx = next((i for i in range(len(out) - 1, -1, -1)
                          if out[i].get("role") == "user"), None)
    if last_user_idx is None:
        out[0]["content"] = head + tail  # fallback: behold i system (ingen user at hænge på)
        return out, ""
    out[last_user_idx] = dict(out[last_user_idx])
    _orig = str(out[last_user_idx].get("content") or "")
    out[last_user_idx]["content"] = tail + "\n\n" + _orig
    return out, tail


def _normalize_reasoning_for_provider(messages: list[dict], provider: str) -> list[dict]:
    """Fase 4 Task S: keep `reasoning_content` on assistant(+tool_calls) messages for
    providers that accept it on replay (deepseek); STRIP it for providers that 400 on
    the unexpected field (ollama/copilot-compat — the documented "400=ollama-felter"
    root cause). Never mutates the input list. Only touches assistant messages that
    actually carry a `reasoning_content` key — everything else passes through
    unchanged, so this is a no-op on messages that never had reasoning attached."""
    if provider == "deepseek":
        return list(messages or [])
    out: list[dict] = []
    for m in messages or []:
        if isinstance(m, dict) and m.get("role") == "assistant" and "reasoning_content" in m:
            m2 = dict(m)
            m2.pop("reasoning_content", None)
            out.append(m2)
        else:
            out.append(m)
    return out


def _resolve_target() -> tuple[str, str]:
    """(provider, model) for /v1/agent/step (jarvis-code klient-loop + subagenter).

    Flag `agent_pool_router_enabled` (default OFF): route gennem den Central-ejede
    agent-pool (gratis modeller, deepseek er routable=False) i stedet for visible-
    default. Det er dét agent:explore skal kalde fra. Off → uændret visible-adfærd."""
    if _flag("agent_pool_router_enabled"):
        try:
            from core.services.agent_pool_router import route_agent_task
            r = route_agent_task(kind="coding")
            p, m = str(r.get("provider") or ""), str(r.get("model") or "")
            if p and m:
                return p, m
        except Exception:
            logger.debug("agent_pool routing fejlede — falder til visible", exc_info=True)
    try:
        from core.runtime.settings import load_settings
        from core.services.central_router_adapt import resolve_visible_model
        s = load_settings()
        return resolve_visible_model(
            default_provider=s.visible_model_provider,
            default_model=s.visible_model_name,
        )
    except Exception:
        return "deepseek", "deepseek-v4-flash"


def _openai_compat_credentials(provider: str) -> tuple[str, str]:
    """(auth_profile, base_url) for en openai-compatible provider (jf. visible-adapteren)."""
    base_url = ""
    auth_profile = provider
    try:
        from core.services.cheap_provider_runtime import provider_runtime_defaults
        base_url = str(provider_runtime_defaults(provider).get("base_url") or "")
    except Exception:
        pass
    try:
        from core.runtime.provider_router import load_provider_router_registry
        for p in load_provider_router_registry().get("providers") or []:
            if str(p.get("provider") or "") == provider:
                auth_profile = str(p.get("auth_profile") or "").strip() or provider
                break
    except Exception:
        pass
    return auth_profile, base_url


@router.get("/v1/tools/native")
async def list_native_tools() -> JSONResponse:
    """List Jarvis' native (server-side) tools + deres lås-status (owner-styring)."""
    try:
        from core.tools.simple_tools import get_tool_definitions
        from core.tools.native_tool_gate import disabled_tools
        defs = get_tool_definitions(role="owner", scope="")
        locked = disabled_tools()
        names = sorted({str((d.get("function") or {}).get("name") or "") for d in defs} - {""})
        return JSONResponse(content={
            "tools": [{"name": n, "enabled": n not in locked} for n in names],
            "locked": sorted(locked),
            "count": len(names),
        })
    except Exception as exc:
        logger.exception("list_native_tools fejlede: %s", exc)
        return JSONResponse(status_code=500, content={"error": {"message": str(exc)}})


@router.get("/v1/tools/catalog")
async def tools_catalog(unlocked: bool = False) -> JSONResponse:
    """Kurateret jc tool-katalog. Låst: companions + load_more. Åbnet: + runtime_-aliaser.

    Rolle hardcodes til "owner" — samme mønster som GET /v1/tools/native ovenfor
    (ingen auth-dependency; owner-token er den etablerede default for disse routes).
    """
    try:
        from core.tools.jc_tool_catalog import build_jc_catalog
        tools = build_jc_catalog(role="owner", unlocked=bool(unlocked))
        return JSONResponse(content={"tools": tools, "unlocked": bool(unlocked)})
    except Exception as exc:
        logger.exception("tools_catalog fejlede: %s", exc)
        return JSONResponse(status_code=500, content={"error": {"message": str(exc)}})


class _ExecBody(BaseModel):
    name: str
    arguments: dict = {}
    session_id: str | None = None
    turn_id: str | None = None
    user_id: str | None = None


@router.post("/v1/tools/execute")
async def tools_execute(body: _ExecBody):
    """Forwarded execution for jarvis-code (jc): jc forwards a non-local tool call
    here for CONTAINER-side execution.

    Security path (HARD, not prompt-governed):
      1. resolve caller role
      2. UNALIAS runtime_bash -> bash (so the gate/dispatch see the real name)
      3. apply the HARD brain-write gate on the UNALIASED name (deny -> HTTP 403)
      4. run execute_tool(name, arguments) inside the caller's user/workspace context
         so memory tools scope to the right workspace
      5. return {"result": ..., "name": <unaliased>}

    Jarvis' own autonomous path does NOT use this endpoint, so the gate only ever
    constrains user-initiated calls — his agency is untouched.
    """
    role = _resolve_role()
    # Finding A: normalize ONCE, then use the SAME `real` for the gate AND dispatch so
    # they can never diverge on casing/whitespace/alias. Strip+lower BEFORE unalias so a
    # messy alias ("  RUNTIME_BASH  ") is recognised and resolved to its canonical name.
    # All native tool names are lowercase snake_case → .lower() is safe and the
    # gate/dispatcher stay in lockstep.
    real = unalias(body.name.strip().lower())
    if not check_brain_write_allowed(real, role=role):
        # Fase 5 Task 3: additive verdict-ledger logging on a forwarded
        # brain-write deny — distinct from (not a replacement for) the HARD
        # gate above, which already raised nothing has changed about WHETHER
        # this is denied. Never let a logging failure break the 403 path.
        try:
            from core.services.gate_verdict_ledger import record as _record_verdict
            _record_verdict(nerve="jc_forward", cluster="brain_write", decision="deny",
                            reason=f"tool={real} role={role}")
        except Exception:
            logger.debug("agent_loop: gate_verdict_ledger.record fejlede (jc_forward deny)",
                        exc_info=True)
        # Fase 5 Task 9: audit-trail row (flag-gated jc_audit_trail, default
        # OFF) — distinct from the verdict-ledger (aggregated counts) and the
        # cost-nerve (spend): who ran what, attributable to a user_id.
        try:
            from apps.api.jarvis_api.routes.agent_audit import record_if_enabled
            record_if_enabled(user_id=body.user_id or "", role=role, tool=real,
                              target_summary=str(body.arguments or {})[:200], decision="deny")
        except Exception:
            logger.debug("agent_loop: agent_audit.record_if_enabled fejlede (deny)", exc_info=True)
        raise HTTPException(status_code=403,
                            detail="brain-write not permitted for this user")

    # remember_this reads session/turn id from ARGUMENTS (not a ContextVar):
    # core.tools.jarvis_brain_tools._exec_remember_this looks at
    # args["_runtime_session_id"|"session_id"] / ["_runtime_turn_id"|"turn_id"] and
    # returns {"error": "context_missing"} unless BOTH are present. Forward
    # body.session_id / body.turn_id through the arguments dict so the write persists
    # and the 5/turn rate-limit keys on a real per-turn id. Synthesize a non-empty
    # turn_id when the client did not thread one, so forwarded writes never fail on a
    # missing turn context. setdefault semantics: never clobber an id the caller already
    # placed in the arguments.
    import uuid
    arguments = dict(body.arguments or {})
    if not arguments.get("_runtime_session_id") and not arguments.get("session_id"):
        if body.session_id:
            arguments["_runtime_session_id"] = body.session_id
    if not arguments.get("_runtime_turn_id") and not arguments.get("turn_id"):
        arguments["_runtime_turn_id"] = body.turn_id or f"jc-{uuid.uuid4().hex[:16]}"

    # Scoping choice: user_context() is a SYNC contextmanager backed by a ContextVar.
    # run_in_threadpool runs execute_tool in a WORKER thread, so the ContextVar must be
    # entered INSIDE that worker thread — otherwise memory tools would see the default
    # ("bjorn") context of the event-loop thread, not the caller's. We therefore enter
    # user_context() inside the sync helper that the threadpool runs, guaranteeing the
    # ContextVar is visible to execute_tool on the SAME thread that executes it.
    # For the owner (empty user_id) this yields Bjørn's default "bjorn" workspace — the
    # same behaviour as today's owner path (do not break owner).
    #
    # Finding B (privilege escalation): user_context() does NOT carry a role — it calls
    # set_context() without one, so the ContextVar's role resets to "" (owner-equivalent
    # at the inner gate `_role not in ("", "owner")`). A non-owner caller would then run
    # every forwarded tool unscoped-by-role. Fix: re-set the resolved caller role on the
    # workspace state user_context() established, on the SAME worker thread, BEFORE
    # calling execute_tool — so the inner server-side auth gate enforces the real role.
    def _run() -> Any:
        from core.identity.workspace_context import (
            user_context, set_context, reset_context, _current_state,
        )
        ctx_kwargs: dict[str, str] = {}
        _uid = _owner_scoped_user_id(body.user_id, role)
        if _uid:
            ctx_kwargs["discord_id"] = _uid
        with user_context(**ctx_kwargs):
            base = _current_state.get()
            role_token = set_context(
                workspace_name=base.workspace_name,
                user_id=base.user_id,
                user_display_name=base.user_display_name,
                role=role,
                channel=base.channel,
                session_id=base.session_id,
            )
            try:
                return execute_tool(real, arguments)
            finally:
                reset_context(role_token)

    import time as _time
    _exec_t0 = _time.monotonic()
    result = await run_in_threadpool(_run)
    _exec_dur_ms = (_time.monotonic() - _exec_t0) * 1000.0
    # Fase 5 Task 9: audit-trail row for the ALLOWED path too (flag-gated,
    # inert when off — see record_if_enabled). Audit rows exist even when
    # the tool call carries zero cost (distinct from the cost-nerve).
    try:
        from apps.api.jarvis_api.routes.agent_audit import record_if_enabled
        record_if_enabled(user_id=body.user_id or "", role=role, tool=real,
                          target_summary=str(body.arguments or {})[:200], decision="allow")
    except Exception:
        logger.debug("agent_loop: agent_audit.record_if_enabled fejlede (allow)", exc_info=True)
    # Fase 5 Task 20 (flag-gated, default OFF): per-tool eventbus telemetry
    # for this FORWARDED tool call, closing part of the "blind lane" — the
    # server previously saw nothing about individual jarvis-code tool runs.
    if _flag("jc_tool_telemetry"):
        try:
            from core.services.jc_tool_telemetry import publish_tool_step
            _status = "ok" if isinstance(result, dict) and result.get("status") != "error" else "error"
            publish_tool_step(tool=real, status=_status, duration_ms=_exec_dur_ms,
                              bytes_=len(str(result)), user_id=body.user_id or "",
                              session_id=body.session_id or "")
        except Exception:
            logger.debug("agent_loop: jc_tool_telemetry.publish_tool_step fejlede", exc_info=True)
    return {"result": result, "name": real}


@router.post("/v1/tools/native", response_model=None)
async def toggle_native_tool(request: Request) -> JSONResponse:
    """Lås/lås-op et native tool. Body: {name: str, enabled: bool}."""
    body = await request.json()
    name = str(body.get("name") or "").strip()
    if not name:
        return JSONResponse(status_code=400, content={"error": {"message": "name er påkrævet"}})
    enabled = bool(body.get("enabled", True))
    try:
        from core.tools.native_tool_gate import set_tool_disabled
        locked = set_tool_disabled(name, disabled=not enabled)
        return JSONResponse(content={"name": name, "enabled": enabled, "locked": sorted(locked)})
    except Exception as exc:
        logger.exception("toggle_native_tool fejlede: %s", exc)
        return JSONResponse(status_code=500, content={"error": {"message": str(exc)}})


@router.post("/v1/agent/step", response_model=None)
async def agent_step(request: Request):
    """Ét client-owned model-tur. Body: {messages:[...], tools:[...], stream?:bool}.

    stream=false → JSON {content, tool_calls, done, usage, provider, model}.
    stream=true  → SSE: event:delta {text} · event:tool_calls {tool_calls} · event:done
                   {content, usage, done} · event:error {error}.

    Eksekverer ALDRIG værktøjer — det gør klienten LOKALT. Hvert kald er ÉT kort tur
    (bounded), så selv den streamende variant er cutoff-robust: klienten ejer loopet og
    kan re-anmode et enkelt step non-stream hvis strømmen tabes."""
    body = await request.json()
    client_messages = body.get("messages") or []
    tools = body.get("tools") or None
    stream = bool(body.get("stream", False))
    context = str(body.get("context") or "identity").lower()
    session_id = str(body.get("session_id") or "")
    # Owner-scoping: jarvis-code sender ofte tomt user_id → udled ejerens id så
    # memory/workspace-recall i assembly'en (og forwarded memory-tools) scoper rigtigt.
    user_id = _owner_scoped_user_id(body.get("user_id"), _resolve_role())
    env = body.get("env") if isinstance(body.get("env"), dict) else None
    # Fase 5 Task 1: owner-only privilege gate on the approval-timing axis.
    # Inert (no key added, no behaviour change) when the flag is off or no
    # approval_mode was sent — jarvis-code's client-only current wire format
    # is preserved byte-identical unless a caller opts into sending it.
    requested_approval_mode = str(body.get("approval_mode") or "").strip()
    caller_role = _resolve_role()
    effective_approval_mode, privilege_downgraded = _apply_privilege_enforcement(
        caller_role, requested_approval_mode)

    # Fase 5 Task 20 (flag-gated, default OFF): the client reports per-tool
    # {tool, status, duration_ms, bytes} for LOCAL tool calls it ran itself
    # (agent_step never sees those otherwise — only forwarded /v1/tools/
    # execute calls are server-timed, see tools_execute above). This closes
    # the rest of the "blind lane": local runs become an eventbus signal too.
    tool_steps = body.get("tool_steps")
    if isinstance(tool_steps, list) and tool_steps and _flag("jc_tool_telemetry"):
        try:
            from core.services.jc_tool_telemetry import publish_tool_steps
            publish_tool_steps(tool_steps, user_id=user_id, session_id=session_id)
        except Exception:
            logger.debug("agent_loop: jc_tool_telemetry.publish_tool_steps fejlede", exc_info=True)

    if not isinstance(client_messages, list) or not client_messages:
        return JSONResponse(status_code=400, content={
            "error": {"message": "messages[] er påkrævet", "type": "invalid_request_error"}})

    # C2b heartbeat: hold det aktive visible run frisk under en multi-round-tur, så
    # desk/mobils freshness-vindue ikke udløber mid-tur (kun hvis DETTE run stadig er
    # aktivt — touch no-op'er ellers). Flag-gated; self-safe.
    if getattr(_settings(), "agent_live_broadcast_enabled", False):
        _run_id = str(body.get("run_id") or "")
        if _run_id:
            try:
                from core.services.visible_runs_sections.run_control_state import (
                    touch_active_visible_run,
                )
                touch_active_visible_run(_run_id)
            except Exception:
                logger.debug("agent_step: touch_active_visible_run fejlede", exc_info=True)
            # Hold run_event_log-liveness frisk (desk-poller/liveness-linje) under en
            # multi-round-tur — ellers udløber _LIVE_IDLE_S mellem runder og prikken dør.
            try:
                import core.services.run_event_log as rel
                rel.touch_liveness(_run_id)
            except Exception:
                logger.debug("agent_step: rel.touch_liveness fejlede", exc_info=True)

    # jarvis-code CHAT: rolle-aware model — member→ollama-deepseek LÅST, owner→sin valgte
    # model (default deepseek-flash). IKKE agent-poolen/adaptive-router: den er reserveret
    # til Jarvis' indre liv + autonome agenter, ALDRIG bruger-chat. Klientens model-vælger
    # styrer nu faktisk (den sender provider+model). Genbruger desks _resolve_visible_target
    # så member-lås/owner-frihed er BIT-for-BIT samme politik som desk.
    _prov_req = str(body.get("provider") or "").strip()
    _model_req = str(body.get("model") or "").strip()
    # Agent-drevne steps (subagenter dispatchet via task/explore) SKAL trække fra
    # agent-poolen (gratis arbejdskraft + betalte modeller til rigtige kode-opgaver),
    # ALDRIG owner-deepseek. Owner-chatten (Bjørn↔Jarvis) forbliver på sin egen model.
    # Gated på agent_pool_router_enabled; graceful fallback til owner-model.
    provider = model = ""
    _is_agent_pool = bool(body.get("agent_pool")) and _flag("agent_pool_router_enabled")
    if _is_agent_pool:
        try:
            from core.services.agent_pool_router import route_agent_task
            _sub_kind = str(body.get("subagent_type") or "").strip() or "explorer"
            # Default GRATIS arbejdskraft; kun EKSPLICITTE kode-skrive-typer må
            # eskalere til betalt premium (rigtige kode-opgaver). Alt andet
            # (explore/research/plan/general) = gratis pool.
            _allow_paid = _sub_kind.lower() in (
                "coder", "coding", "implementer", "implement", "builder",
                "build", "fix", "refactor", "editor")
            r = route_agent_task(kind=_sub_kind, allow_paid=_allow_paid)
            provider, model = str(r.get("provider") or ""), str(r.get("model") or "")
        except Exception:
            logger.debug("agent_step: agent_pool routing fejlede — falder til owner-model", exc_info=True)
    if not provider or not model:
        try:
            from apps.api.jarvis_api.routes.chat import _resolve_visible_target
            provider, model = _resolve_visible_target(user_id or None, _prov_req, _model_req)
        except Exception:
            provider, model = "", ""
    if not provider or not model:
        provider, model = "deepseek", "deepseek-v4-flash"  # jarvis-code chat-default (owner)

    try:
        from core.services.cheap_provider_runtime_adapters import (
            _OPENAI_COMPATIBLE_PROVIDERS,
            _execute_openai_compatible_chat,
        )
    except Exception as exc:  # pragma: no cover
        return JSONResponse(status_code=500, content={
            "error": {"message": f"provider-runtime utilgængelig: {exc}", "type": "server_error"}})

    if provider not in _OPENAI_COMPATIBLE_PROVIDERS:
        # Client-owned loop kræver en openai-compatible provider (tool_calls-protokol).
        provider, model = "deepseek", "deepseek-v4-flash"

    auth_profile, base_url = _openai_compat_credentials(provider)
    settings = _settings()

    # Seneste bruger-besked → driver memory-recall i 'full'-context.
    _last_user = ""
    for _m in reversed(client_messages):
        if isinstance(_m, dict) and _m.get("role") == "user":
            _c = _m.get("content")
            _last_user = _extract_text(_c) if _flag("jc_agent_multimodal") else str(_c or "")
            break
    _ws_name = _resolve_workspace_name(user_id) if _flag("jc_agent_user_scoping") else "default"

    # Fase 4 Task 1 (flag-gated): keep reasoning_content paired with its
    # tool_calls-carrying assistant message for providers that accept replay
    # (deepseek), strip it for providers that 400 on it. Off -> client_messages
    # pass through byte-identical to today.
    if settings.agent_step_reasoning_replay_enabled:
        client_messages = _normalize_reasoning_for_provider(client_messages, provider)

    # Fase 4 Task 1 (flag-gated): client-directed think-budget -> deepseek extra_body.
    extra_body: dict | None = None
    thinking_mode = body.get("thinking_mode")
    if settings.agent_step_reasoning_replay_enabled and thinking_mode and provider == "deepseek":
        try:
            from core.services.cheap_provider_runtime_adapters import (
                deepseek_request_for_thinking_mode,
            )
            model, extra_body = deepseek_request_for_thinking_mode(model, str(thinking_mode))
        except Exception:
            logger.debug("agent/step thinking_mode-mapping fejlede", exc_info=True)

    # System-prompt (tiered context) foran + klientens samtale (inkl. tool-resultater).
    # KRITISK (16.jul): byg prompt-assembly'en INDE i ejerens user_context. recall-motorens
    # 'workspace'-kilde kalder workspace_dir() → current_user_id() (context-var). agent_step
    # udledte user_id (L769) men installerede den ALDRIG i context'en → workspace_dir() fejlede
    # → workspace-recall (Jarvis' persistente hukommelse) blev lydløst udeladt. KUN i jarvis-code
    # (desk kører altid inde i sin auth-context) → "kan ikke huske"-symptomet. Nu scoper recall
    # korrekt. Tom user_id (member u. id) → 'public'-workspace-fallback (uændret adfærd).
    from core.identity.workspace_context import user_context
    with user_context(discord_id=user_id or ""):
        _system_prompt_text = _build_system_prompt(context, _last_user, _ws_name, env=env)
    chat_messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt_text}]
    chat_messages.extend(client_messages)
    # Option B (frys-halen): prepend volatil blok til aktuel user-besked + returnér den
    # så klienten persisterer → byte-identisk replay (ingen relokering). Tager precedence
    # over Fase A1-split når slået til. Begge default OFF → chat_messages uændret i dag.
    _volatile_block = ""
    if getattr(settings, "agent_step_volatile_prepend_enabled", False):
        chat_messages, _volatile_block = _apply_volatile_prepend(chat_messages)
    else:
        # Fase A1: flyt den volatile assembly-hale bag samtalen (cache-stabilt prefix).
        chat_messages = _apply_dynamic_tail_split(
            chat_messages, enabled=getattr(settings, "agent_step_cache_split_enabled", False))

    # Fase 4 Task 4 (flag-gated): cache-prefix signature over the STABLE HEAD only
    # ([system-without-env] + tools) — computed with env=None regardless of the
    # env flag, so a per-turn env dict (Task 2's volatile tail) never busts the
    # signature, and neither does a growing conversation (never fed in here).
    _prefix_sha, _prefix_len = "", 0
    if settings.agent_step_cache_contract_enabled:
        try:
            from core.services.cache_telemetry import prefix_signature
            with user_context(discord_id=user_id or ""):
                _head = _build_system_prompt(context, _last_user, _ws_name, env=None)
            _prefix_sha, _prefix_len = prefix_signature(_head, tools)
        except Exception:
            logger.debug("agent/step prefix_signature fejlede", exc_info=True)

    if stream:
        return StreamingResponse(
            _stream_step(provider=provider, model=model, auth_profile=auth_profile,
                         base_url=base_url, chat_messages=chat_messages, tools=tools,
                         session_id=session_id, user_id=user_id, extra_body=extra_body,
                         reasoning_replay_enabled=settings.agent_step_reasoning_replay_enabled,
                         cache_contract_enabled=settings.agent_step_cache_contract_enabled,
                         prefix_sha=_prefix_sha, prefix_len=_prefix_len,
                         follow_tee=_live_follow_active(settings, session_id)),
            media_type="text/event-stream",
        )

    import time as _time
    _t0 = _time.monotonic()
    try:
        raw = _execute_openai_compatible_chat(
            provider=provider, model=model, auth_profile=auth_profile,
            base_url=base_url, messages=chat_messages, tools=tools,
            extra_body=extra_body,
        )
    except Exception as exc:
        logger.exception("agent/step model-kald fejlede: %s", exc)
        return JSONResponse(status_code=502, content={
            "error": {"message": f"model-kald fejlede: {exc}", "type": "upstream_error"}})
    _dur_ms = int((_time.monotonic() - _t0) * 1000)

    tool_calls = list(raw.get("tool_calls") or [])
    content = str(raw.get("text") or "")
    # Fase 5 Task 19 (flag-gated, default OFF): only engages when native
    # tool_calls is empty — the native path is otherwise untouched.
    content, tool_calls = _apply_xml_toolcall_fallback(content, tool_calls)
    # I1-heal (mirror visible lane): surface reasoning_content instead of a silent
    # empty finish when a thinking-model put its whole answer in the thinking channel.
    if not content and not tool_calls:
        _reason = str(raw.get("reasoning_content") or "").strip()
        if _reason:
            content = _reason
    tokens_in = int(raw.get("input_tokens") or 0)
    tokens_out = int(raw.get("output_tokens") or 0)
    cost_usd = float(raw.get("cost_usd") or 0.0)
    finish_reason = str(raw.get("finish_reason") or "")
    status = "ok" if (content or tool_calls) else "empty"
    if status == "empty":
        # Visible note instead of silence; status stays "empty" for telemetry.
        content = ("⟨Jeg fik ikke formuleret et svar den gang — "
                   "spørg mig gerne igen.⟩")

    if _flag("jc_agent_observability"):
        # Cache-rapporterings-fix (2026-07-16): agent-lanen glemte at videregive
        # deepseek's prompt-cache-split til record_cost → dashboardet viste 0% cache
        # for jarvis-code selvom deepseek CACHER kraftigt (cost bekræfter det). Læs
        # begge nøgle-varianter (normaliseret + deepseek-rå) som visible-lanen gør.
        _ch = int(raw.get("cache_hit_tokens") or raw.get("prompt_cache_hit_tokens") or 0)
        _cm = int(raw.get("cache_miss_tokens") or raw.get("prompt_cache_miss_tokens") or 0)
        try:
            record_cost(lane="agent", provider=provider, model=model,
                        input_tokens=tokens_in, output_tokens=tokens_out,
                        cost_usd=cost_usd, user_id=user_id,
                        cache_hit_tokens=_ch, cache_miss_tokens=_cm)
        except Exception:
            logger.debug("agent/step record_cost fejlede", exc_info=True)
        _emit_agent_nerve(
            status=status, provider=provider, model=model,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost_usd,
            duration_ms=_dur_ms, tool_calls=len(tool_calls),
            finish_reason=finish_reason, user_id=user_id, session_id=session_id)
        if status == "empty":
            try:
                note_empty_completion(
                    f"jc-agent-{session_id or 'nosess'}", provider=provider, model=model,
                    rounds=1, tools_executed=0, session_id=session_id, path="agent_step")
            except Exception:
                logger.debug("agent/step note_empty_completion fejlede", exc_info=True)

    usage_body: dict[str, Any] = {
        "prompt_tokens": tokens_in,
        "completion_tokens": tokens_out,
        "cost_usd": cost_usd,
    }
    # Fase 4 Task 4 (flag-gated): record hit/miss telemetry against the STABLE
    # HEAD signature computed above, and surface the tokens in usage. Off ->
    # no telemetry call, no new usage keys, byte-identical to today.
    if settings.agent_step_cache_contract_enabled:
        _cache_hit = int(raw.get("cache_hit_tokens") or 0)
        _cache_miss = int(raw.get("cache_miss_tokens") or 0)
        usage_body["cache_hit_tokens"] = _cache_hit
        usage_body["cache_miss_tokens"] = _cache_miss
        try:
            from core.services.cache_telemetry import record_visible_cache
            record_visible_cache(
                lane="jc-agent-step", provider=provider, model=model,
                prefix_sha=_prefix_sha, prefix_len=_prefix_len,
                cache_hit=_cache_hit, cache_miss=_cache_miss,
            )
        except Exception:
            logger.debug("agent/step record_visible_cache fejlede", exc_info=True)

    response_body: dict[str, Any] = {
        # additive structured envelope (Fase 0 O1)
        "status": status,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "duration_ms": _dur_ms,
        "finish_reason": finish_reason,
        "result": content,
        # back-compat keys (existing jarvis-code client reads these)
        "content": content,
        "tool_calls": tool_calls,
        "done": not tool_calls,
        "provider": provider,
        "model": model,
        "usage": usage_body,
    }
    # Option B: hand the client the exact volatile block used, so it persists it into
    # the stored user message → byte-identical replay next turn. Empty when the flag is
    # off or there was no tail → client leaves the message unchanged.
    if _volatile_block:
        response_body["volatile_context"] = _volatile_block
    # Fase 4 Task 1 (flag-gated): off -> key absent, byte-identical to today.
    if settings.agent_step_reasoning_replay_enabled:
        response_body["reasoning_content"] = str(raw.get("reasoning_content") or "")
    # Fase 5 Task 1 (flag-gated): off / no approval_mode sent -> keys absent,
    # byte-identical to today.
    if requested_approval_mode:
        response_body["effective_approval_mode"] = effective_approval_mode
        if privilege_downgraded:
            response_body["privilege_downgraded"] = True
    return JSONResponse(content=response_body)


def _stream_step(*, provider: str, model: str, auth_profile: str, base_url: str,
                 chat_messages: list[dict], tools: list[dict] | None,
                 session_id: str = "", user_id: str = "", extra_body: dict | None = None,
                 reasoning_replay_enabled: bool = False,
                 cache_contract_enabled: bool = False,
                 prefix_sha: str = "", prefix_len: int = 0,
                 follow_tee: bool = False):
    """Sync generator: stream ét model-tur som SSE. Bygger på det lav-niveau
    openai-compat SSE-iterator (rå messages+tools ind, delta/tool_call/done ud)."""
    from core.services.cheap_provider_runtime_streaming import (
        _iter_openai_compatible_chat_events,
    )
    import time as _time
    _t0 = _time.monotonic()
    collected: list[dict] = []
    full = ""
    try:
        for ev in _iter_openai_compatible_chat_events(
            provider=provider, model=model, auth_profile=auth_profile,
            base_url=base_url, messages=chat_messages, tools=tools or None,
            extra_body=extra_body,
        ):
            kind = ev.get("kind")
            if kind == "delta":
                text = str(ev.get("text") or "")
                if text:
                    full += text
                    # Lag 3: tee tekst-delta som v2 content_block_delta ind i follow-
                    # bufferen → desk/mobil-follower ser Jarvis' ord token-for-token.
                    if follow_tee:
                        _follow_delta_frame(session_id, text)
                    yield _sse("delta", {"text": text})
            elif kind == "tool_call":
                collected.append({
                    "id": str(ev.get("id") or f"call_{len(collected)}"),
                    "type": "function",
                    "function": {
                        "name": str(ev.get("name") or ""),
                        "arguments": ev.get("arguments") if isinstance(ev.get("arguments"), str)
                        else json.dumps(ev.get("arguments") or {}, ensure_ascii=False),
                    },
                })
            elif kind == "done":
                _content = str(ev.get("full_text") or full)
                # Fase 5 Task 19 (flag-gated, default OFF): only engages when
                # native tool_calls is empty (collected == []).
                _content, collected = _apply_xml_toolcall_fallback(_content, collected)
                if collected:
                    yield _sse("tool_calls", {"tool_calls": collected})
                # I1-heal (mirror visible lane, visible_runs.py:4382): a thinking-model
                # turn whose whole answer landed in reasoning_content is NOT a silent
                # cut-off — surface the reasoning as the answer instead of finishing empty.
                if not _content and not collected:
                    _reason = str(ev.get("reasoning_content") or "").strip()
                    if _reason:
                        _content = _reason
                _tin = int(ev.get("input_tokens") or 0)
                _tout = int(ev.get("output_tokens") or 0)
                _cost = float(ev.get("cost_usd") or 0.0)
                _fr = str(ev.get("finish_reason") or "")
                _status = "ok" if (_content or collected) else "empty"
                if _status == "empty":
                    # Don't hand the client an empty 'done' (= silent cut-off). Keep
                    # _status="empty" so Central telemetry still records the recurrence,
                    # but give the user a visible note instead of nothing.
                    _content = ("⟨Jeg fik ikke formuleret et svar den gang — "
                                "spørg mig gerne igen.⟩")
                if _flag("jc_agent_observability"):
                    # Cache-rapporterings-fix (2026-07-16): videregiv deepseek's
                    # prompt-cache-split (stream-path — den jarvis-code bruger).
                    _sch = int(ev.get("cache_hit_tokens") or ev.get("prompt_cache_hit_tokens") or 0)
                    _scm = int(ev.get("cache_miss_tokens") or ev.get("prompt_cache_miss_tokens") or 0)
                    try:
                        record_cost(lane="agent", provider=provider, model=model,
                                    input_tokens=_tin, output_tokens=_tout,
                                    cost_usd=_cost, user_id=user_id,
                                    cache_hit_tokens=_sch, cache_miss_tokens=_scm)
                    except Exception:
                        logger.debug("agent/step stream record_cost fejlede", exc_info=True)
                    _emit_agent_nerve(
                        status=_status, provider=provider, model=model,
                        tokens_in=_tin, tokens_out=_tout, cost_usd=_cost,
                        duration_ms=int((_time.monotonic() - _t0) * 1000),
                        tool_calls=len(collected), finish_reason=_fr,
                        user_id=user_id, session_id=session_id)
                    if _status == "empty":
                        try:
                            note_empty_completion(
                                f"jc-agent-{session_id or 'nosess'}", provider=provider,
                                model=model, rounds=1, tools_executed=0,
                                session_id=session_id, path="agent_step_stream")
                        except Exception:
                            logger.debug("stream note_empty_completion fejlede", exc_info=True)
                _usage_body: dict[str, Any] = {"prompt_tokens": _tin, "completion_tokens": _tout}
                # Fase 4 Task 4 (flag-gated): off -> no telemetry call, no new usage keys.
                if cache_contract_enabled:
                    _cache_hit = int(ev.get("cache_hit_tokens") or 0)
                    _cache_miss = int(ev.get("cache_miss_tokens") or 0)
                    _usage_body["cache_hit_tokens"] = _cache_hit
                    _usage_body["cache_miss_tokens"] = _cache_miss
                    try:
                        from core.services.cache_telemetry import record_visible_cache
                        record_visible_cache(
                            lane="jc-agent-step", provider=provider, model=model,
                            prefix_sha=prefix_sha, prefix_len=prefix_len,
                            cache_hit=_cache_hit, cache_miss=_cache_miss,
                        )
                    except Exception:
                        logger.debug("agent/step stream record_visible_cache fejlede",
                                    exc_info=True)
                _done_body: dict[str, Any] = {
                    "status": _status,
                    "tokens_in": _tin,
                    "tokens_out": _tout,
                    "cost_usd": _cost,
                    "duration_ms": int((_time.monotonic() - _t0) * 1000),
                    "finish_reason": _fr,
                    "result": _content,
                    # back-compat
                    "content": _content,
                    "done": not collected,
                    "usage": _usage_body,
                }
                # Fase 4 Task 1 (flag-gated): off -> key absent, byte-identical to today.
                if reasoning_replay_enabled:
                    _done_body["reasoning_content"] = str(ev.get("reasoning_content") or "")
                yield _sse("done", _done_body)
                return
    except Exception as exc:
        logger.exception("agent/step stream fejlede: %s", exc)
        yield _sse("error", {"error": str(exc)})
        return
    # Strømmen sluttede uden eksplicit done → afslut alligevel (klient kan re-anmode).
    if collected:
        yield _sse("tool_calls", {"tool_calls": collected})
    yield _sse("done", {
        "status": "ok" if (full or collected) else "empty",
        "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
        "duration_ms": int((_time.monotonic() - _t0) * 1000),
        "finish_reason": "", "result": full,
        "content": full, "done": not collected, "usage": {},
    })


# ── Fase B (delt substrat): tur-absorb — fyr den fulde post-tur-hjerne for en
# KLIENT-drevet tur. Klienten (jarvis-code/desk) driver loopet selv, men serveren
# ejer hjernen; ved tur-slut POSTer klienten turen hertil så de ~85 trackers +
# memory-postprocess + kognitive systemer fyrer — samme maskineri visible_runs
# ._post_process kører for en server-drevet tur. Flag-gated, default OFF (no-op).
class _AbsorbBody(BaseModel):
    session_id: str = ""
    run_id: str = ""
    user_message: str = ""
    assistant_response: str = ""
    provider: str = ""
    model: str = ""
    user_id: str = ""


@router.post("/v1/agent/turn-absorb", response_model=None)
async def agent_turn_absorb(body: _AbsorbBody):
    """Absorbér en klient-drevet tur i hjernen (post-process). Flag
    agent_turn_absorb_enabled default OFF → no-op (returnerer skipped)."""
    settings = _settings()
    if not getattr(settings, "agent_turn_absorb_enabled", False):
        return {"ok": False, "skipped": "flag_off"}
    persisted = False
    try:
        from core.services.client_turn_absorb import absorb_client_turn, persist_client_turn
        # Fase C1: persistér turen SYNKRONT til den delte server-session (→ synlig i
        # desk/web/mobil) FØR baggrunds-hjernen — kun for ægte chat-<hex>-sessioner.
        persisted = persist_client_turn(
            session_id=body.session_id, user_message=body.user_message,
            assistant_response=body.assistant_response, user_id=body.user_id)
        absorb_client_turn(
            session_id=body.session_id, run_id=body.run_id,
            user_message=body.user_message, assistant_response=body.assistant_response,
            provider=body.provider, model=body.model, user_id=body.user_id)
    except Exception:
        logger.debug("agent/turn-absorb dispatch fejlede", exc_info=True)
        return {"ok": False, "error": "absorb_failed"}
    return {"ok": True, "run_id": body.run_id, "persisted": persisted}


# ── C2b (cross-device live streaming): tur-liveness for en KLIENT-drevet tur.
# jarvis-code driver loopet klient-side → serveren ser ikke turen som et kørende run,
# så desk/mobils poller/liveness/spinner/systray/takeover lyser aldrig op. begin
# registrerer turen som det aktive visible run + åbner run_follow; end rydder igen
# (kaldes ALTID i klientens finally). Flag agent_live_broadcast_enabled default OFF.
class _TurnLiveBody(BaseModel):
    session_id: str = ""
    run_id: str = ""
    user_message: str = ""
    provider: str = ""
    model: str = ""
    user_id: str = ""


# Lag 3 (token-for-token follow): oversæt jarvis-codes tekst-stream til v2-anthropic
# frames i run_follow-bufferen, så en desk/mobil-klient på SAMME session kan følge
# Jarvis' ord token-for-token via GET /chat/sessions/{id}/follow — SAMME renderer som
# en server-drevet tur (desk uændret). Én tekst-block pr. tur: MessageStart+
# ContentBlockStart ved tur-start, ContentBlockDelta pr. delta (på tværs af runder),
# ContentBlockStop+MessageDelta+MessageStop ved tur-slut. Flag-gated, self-safe.
def _live_follow_active(settings, session_id: str) -> bool:
    return (bool(getattr(settings, "agent_live_follow_tokens_enabled", False))
            and str(session_id or "").startswith("chat-"))


def _follow_publish_line(session_id: str, line: str) -> None:
    try:
        from core.services.run_follow import publish_follow_frame
        publish_follow_frame(session_id, line)
    except Exception:
        logger.debug("lag3: follow publish fejlede", exc_info=True)


def _follow_begin_frames(session_id: str, run_id: str, provider: str, model: str) -> None:
    try:
        from apps.api.jarvis_api.sse_v2_events import ContentBlockStart, MessageStart
        _follow_publish_line(session_id, MessageStart(
            run_id=run_id, model=model, provider=provider, lane="agent",
            session_id=session_id).to_sse_line())
        _follow_publish_line(session_id, ContentBlockStart(
            index=0, block_type="text").to_sse_line())
    except Exception:
        logger.debug("lag3: begin-frames fejlede", exc_info=True)


def _follow_delta_frame(session_id: str, text: str) -> None:
    try:
        from apps.api.jarvis_api.sse_v2_events import ContentBlockDelta
        _follow_publish_line(session_id, ContentBlockDelta(
            index=0, delta_type="text_delta", content=text).to_sse_line())
    except Exception:
        logger.debug("lag3: delta-frame fejlede", exc_info=True)


def _follow_end_frames(session_id: str) -> None:
    try:
        from apps.api.jarvis_api.sse_v2_events import (
            ContentBlockStop, MessageDelta, MessageStop,
        )
        _follow_publish_line(session_id, ContentBlockStop(index=0).to_sse_line())
        _follow_publish_line(session_id, MessageDelta(stop_reason="end_turn").to_sse_line())
        _follow_publish_line(session_id, MessageStop().to_sse_line())
    except Exception:
        logger.debug("lag3: end-frames fejlede", exc_info=True)


@router.post("/v1/agent/turn-begin", response_model=None)
async def agent_turn_begin(body: _TurnLiveBody):
    """Registrér en klient-drevet tur som live (aktivt visible run + run_follow).
    Flag agent_live_broadcast_enabled default OFF → no-op."""
    settings = _settings()
    if not getattr(settings, "agent_live_broadcast_enabled", False):
        return {"ok": False, "skipped": "flag_off"}
    uid = _owner_scoped_user_id(body.user_id, _resolve_role())
    try:
        from core.services.client_turn_live import begin_live_turn
        begin_live_turn(
            session_id=body.session_id, run_id=body.run_id,
            user_message=body.user_message, provider=body.provider,
            model=body.model, user_id=uid)
        # Lag 3: åbn en v2-tekst-message i follow-bufferen (efter begin_follow).
        if _live_follow_active(settings, body.session_id):
            _follow_begin_frames(body.session_id, body.run_id, body.provider, body.model)
    except Exception:
        logger.debug("agent/turn-begin fejlede", exc_info=True)
        return {"ok": False, "error": "begin_failed"}
    return {"ok": True, "run_id": body.run_id}


@router.post("/v1/agent/turn-end", response_model=None)
async def agent_turn_end(body: _TurnLiveBody):
    """Ryd live-tilstanden for en klient-drevet tur (altid safe at kalde). Flag
    agent_live_broadcast_enabled default OFF → no-op."""
    settings = _settings()
    if not getattr(settings, "agent_live_broadcast_enabled", False):
        return {"ok": False, "skipped": "flag_off"}
    try:
        # Lag 3: luk v2-tekst-message'en FØR end_follow markerer bufferen done, så en
        # follower får message_stop og terminerer rent (ikke syntetisk timeout-frame).
        if _live_follow_active(settings, body.session_id):
            _follow_end_frames(body.session_id)
        from core.services.client_turn_live import end_live_turn
        end_live_turn(session_id=body.session_id, run_id=body.run_id)
    except Exception:
        logger.debug("agent/turn-end fejlede", exc_info=True)
        return {"ok": False, "error": "end_failed"}
    return {"ok": True, "run_id": body.run_id}
