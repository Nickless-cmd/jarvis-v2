"""Contextual tool pruning for GitHub Copilot / OpenAI-compatible providers.

OpenAI's chat completions API enforces a hard limit of 128 tools per request.
Jarvis currently exposes 162 tools. This module picks the best 128 per
request so nothing is silently dropped by the provider.

Strategy is deterministic (no LLM call):
  1. Tier 1 — core tools always included (~95)
  2. Tier 2 default "comfort" set — common channels/HA, always if budget allows
  3. Tier 2 keyword-matched tools — scored against user_message + recent usage
  4. Remainder filled lexicographically for stability

Only applied to Copilot paths (caller decides). Ollama and other providers
keep the full 162-tool catalog.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Iterable
import logging

logger = logging.getLogger(__name__)



MAX_TOOLS = 128
VISIBLE_MAX_TOOLS = 48
# Vaerktoejer der ALTID skal overleve kappen. `load_more_tools` er halen ind til
# de rare; de oevrige er tilfoejet 6/9-2026 efter en maaling: i cowork-scope er
# kataloget 452 og kappen 48, og Tier 1 (107 navne) har INGEN intern prioritet —
# den trunkeres i ankomstraekkefoelge. Derfor faldt netop de vaerktoejer ud som
# prompten og kataloget ellers peger paa. `explore` er det tydeligste tilfaelde:
# scope tillod det, kataloget naevnte det, prompten anbefalede det — og pruneren
# fjernede det fra selve tool-arrayet, saa det aldrig kunne kaldes.
#: Vaerktoejer hvis FRAVAER er en adfaerdsregression, ikke en latens-optimering:
#: tab af stemme, af godkendelsesvej, af hukommelse. Listen stod foer KUN i
#: `scripts/regenerate_tier1.py` og blev unioneret ind i `TIER_1_ALWAYS_ON` ved
#: regenerering — men Tier 1 er 118 navne mod et loft paa 48 og trunkeres i
#: ankomstraekkefoelge, saa gulvet var et krav ingen haandhaevede.
#:
#: Maalt 30/9-2026: 7 af de 28 registrerede gulv-navne blev IKKE sendt, heriblandt
#: `memory_upsert_section` med **157 kald** paa 30 dage. Byttet for at faestne
#: gulvet koster syv pladser, hvoraf fem har NUL kald i samme periode:
#:
#:   ud:  list_scheduled_tasks 7x, read_model_config 6x, og fem med 0 kald
#:   ind: memory_upsert_section 157x, git_log 22x, git_status 15x, git_diff 3x
#:
#: `propose_git_commit` stod i gulvet men findes ikke i kataloget — fjernet her
#: frem for at baere et navn ingen kan kalde.
SAFETY_FLOOR: tuple[str, ...] = (
    # Brugervendt kommunikation — mist aldrig hans stemme
    "notify_user", "send_webchat_message", "send_ntfy",
    # Godkendelse og politik
    "approve_proposal", "propose_source_edit", "list_proposals",
    # Selvindsigt
    "read_self_state", "read_mood", "read_self_docs", "read_chronicles",
    # Hukommelse
    "search_memory", "recall_memories", "memory_upsert_section",
    "memory_check_duplicate", "recall_before_act",
    # Filer
    "read_file", "write_file", "edit_file", "search", "find_files", "bash",
    # Web
    "web_fetch", "web_search",
    # Planlaegning
    "schedule_task", "list_initiatives",
    # Git
    "git_status", "git_log", "git_diff",
)


REQUIRED_LAZY_TOOL_NAMES: tuple[str, ...] = (
    "load_more_tools",
    # Side-opgaver skal kunne registreres og afsluttes i samme run, også når
    # den stabile synlige værktøjsliste rammer loftet.
    "flag_side_task", "activate_side_task", "dismiss_side_task",
    # ── De fire hyppigst HENTEDE (30/9-2026, maalt over 30 dage) ───────────
    #
    # Alle fire stod allerede i TIER_1_ALWAYS_ON — og blev alligevel hentet
    # 76 gange, fordi Tier 1 er 118 navne mod et loft paa 48 og trunkeres i
    # ankomstraekkefoelge: 77 af de 118 naaede aldrig arrayet. Medlemskab af
    # Tier 1 er altsaa ingen garanti; denne liste er.
    #
    # Prisen for at hente dem er maalt tre gange: én ny definition i arrayet
    # koster 8.704 tokens mod DeepSeeks API, fordi arrayet ligger foer hele
    # samtalen i praefikset. 76 hentninger paa 30 dage er ~660.000 tokens.
    #
    #   send_discord_dm          28 hentninger
    #   record_sensory_memory    18   (stod ikke engang i Tier 1)
    #   send_webchat_message     15
    #   recall_sensory_memories  15
    "send_discord_dm",
    "record_sensory_memory",
    "send_webchat_message",
    "recall_sensory_memories",
    # Vejen til de hentede vaerktoejer (30/9-2026). Uden den i arrayet kan et
    # hentet vaerktoej ikke kaldes — DeepSeek afviser et vaerktoej der ikke er
    # deklareret — og saa er den eneste vej tilbage at flette definitionen ind
    # i arrayet, hvilket koster hele samtalen. Se `kaldt_vaerktoej.py`.
    "call_loaded_tool",
    # ── FAST fra 3/10-2026: `skill_invoke` var BETINGET, og det kostede ──
    #
    # Pinnet 15/9 betinget af et skill-match, med den begrundelse at «en plads
    # ud af 48 ikke er gratis»: uden match ville `skill_invoke` vaere et
    # vaerktoej uden et navn at give det.
    #
    # Betingelsen gjorde arrayet BESKED-afhaengigt, og arrayet ligger foer hele
    # samtalen i praefikset. Det var usynligt indtil 3/10, fordi taersklen stod
    # paa 0,70 og matchede naesten alt — «hej hvordan går det?» matchede
    # `ui-ux-pro-max`. Pinnet var altsaa i praksis fast, og
    # `test_visible_tool_pool_is_cache_stable_across_user_messages` var groen
    # af den FORKERTE grund.
    #
    # Da Jarvis 3/10 hævede gulvet til primaer-taersklen (`ef8f7b0d5` — og det
    # var rigtigt; baandet var 88 % stoej), blev en naesten-konstant en aegte
    # variabel: en hilsen pinner ikke, en kodebesked goer, og arrayet skifter
    # mellem to ture. Vagten blev roed, og det var den foerste aegte maaling.
    #
    # Prisen er maalt tre gange og staar oeverst i denne liste: én aendring i
    # arrayet koster alt fra aendringspunktet og frem — 92 % -> 26 % hit,
    # +419 tegn -> 62.672 miss-tokens. Én plads ud af 48 er billigere end hele
    # praefikset hver gang en besked krydser taersklen anderledes end den
    # forrige. Derfor: fast.
    "skill_invoke",
    "scout_agent",
    # `spawn_agent_task` FJERNET 30/9-2026 (Bjoern: «den hedder scout idag»).
    #
    # Den var det dyreste enkeltvaerktoej i arrayet — 2.510 tegn, ~581 tokens
    # i HVER prompt — og den blev pinnet ind her fordi kataloget og prompten
    # pegede paa den, samme grund som `explore`.
    #
    # 23/9-2026 blev den ogsaa sat i INVENTARET, netop fordi han greb
    # `scout_agent` «fordi det var den han kunne SE». Det indgreb er nu maalt,
    # en uge efter:
    #
    #     scout_agent        35 kald (15 af dem siden 23/9)
    #     spawn_agent_task    0 kald — ingen taelling overhovedet i 30 dage
    #
    # Indgrebet virkede ikke. Han bruger scout, og scout BLIVER i inventaret
    # (verificeret i det byggede katalog, og en vagt holder det fast). Den
    # fjernede kan stadig naas: den staar i kataloget, hentes med
    # `load_more_tools` og kaldes med `call_loaded_tool` — hvilket er praecis
    # den vej de to mekanismer findes til.
    #
    # Samme spoergsmaal staar aabent for `dispatch_code_mode_task`, som ogsaa
    # har nul kald. Den roeres ikke her: kode-flaaden er Bjoerns beslutning.
    # Fast i hans flade (Bjørn 17/9-2026): kode-flåden. Jarvis: «de er ikke i min
    # standard-værktøjsflade, så jeg griber dem ikke af mig selv».
    "dispatch_code_mode_task",
    "read_attachment",
    "recall_memories",
    # Uden den kan han ikke AABNE kanalen til sin egen maskine — og saa er alt
    # arbejde derovre tilbage til ét operator_-kald ad gangen.
    "operator_channel",
    # Uden den er hele MCP-oekosystemet usynligt i cowork.
    "mcp",
    # En fortrydelse man ikke kan naa er ingen fortrydelse.
    "checkpoint",
    # ── Kontinuitetens to haandtag (4/10-2026, Bjoern: «de to vaerktoejer ──
    #    hoerer til i det faste saet»)
    #
    # `start_session` og `write_handover` blev bygget 4/10 og laa i
    # `_TOOL_HANDLERS`, men i INGEN af de to lister der afgoer hvad der
    # faktisk sendes. Maalt i drift samme dag:
    #
    #     scope=None -> 491 defs -> 48 sendt | begge: IKKE sendt
    #     scope=chat ->  65 defs -> 48 sendt | begge: IKKE sendt
    #
    # De var altsaa kaldbare og alligevel usynlige — samme moenster som
    # `read_attachment` (6/9) og billedvaerktoejerne (13/9): bygget, korrekt,
    # og naaet via `load_more_tools` hver eneste gang.
    #
    # Prisen er ikke bare en hentning. Session-laasen
    # (`services/session_tool_pin`) fryser saettet ved sessionens FOERSTE tur,
    # og `_med_garanterede` forener netop denne liste ind i laasen. Uden
    # medlemskab her staar et nyt vaerktoej udenfor i HELE sessionens levetid
    # — laasen nulstilles foerst ved compaction. Maalt 4/10: `auto-dream`
    # (laast 03:30) og `auto-recurring` (laast 05:00) bar ingen af dem, fordi
    # begge blev bygget senere samme dag.
    #
    # Begge hoerer her og ikke i `SAFETY_FLOOR`: gulvet er vaerktoejer hvis
    # FRAVAER er en adfaerdsregression. Disse to er snarere et haandtag der
    # skal kunne gripes i den tur hvor behovet opstaar — et run man vil saette
    # i gang, en overdragelse man vil skrive — og et haandtag man foerst skal
    # hente midt i turen er et haandtag man ikke griber.
    "start_session",
    "write_handover",
)


# Tier 1 — tools that are always included in the pruned set, regardless of
# user message or recent usage. Goal: cover Jarvis' daily-driver toolkit so
# pruning never hides something he reaches for routinely.
#
# Last regenerated: 2026-04-29 (data-driven from 30-day usage).
# Composition: tools used >= 3 times in the last 30 days, UNIONed with a
# safety floor (notify_user, approve_proposal, etc.) that must always be
# available regardless of past usage.
#
# To regenerate after Jarvis' tool habits drift:
#   conda activate ai
#   python scripts/regenerate_tier1.py [--apply]
#
# Trimmed from 185 -> 103 tools on 2026-04-29 (saved ~7,500 tokens / call).
# Fjernet 30/9-2026 efter maaling: `geolocation_lookup`, `geocode`,
# `reverse_geocode` og `nearby_search` blev kaldt **0 gange** paa 30 dage ud af
# 95.574 vaerktoejskald, men fyldte fire af de 48 pladser i HVER tur. De fire
# pladser er givet til de fire hyppigst HENTEDE (se REQUIRED_LAZY_TOOL_NAMES).
# Geo-vaerktoejerne er ikke vaek — de naas gennem `load_more_tools` naar de
# faktisk skal bruges, og det er praecis den handel den mekanisme findes til.
# I alt stod 21 af de 48 sendte vaerktoejer ubrugte i 30 dage; disse fire er de
# foerste der gav plads, ikke de sidste der kan.
TIER_1_ALWAYS_ON: frozenset[str] = frozenset({
    "adjust_mood", "analyze_image", "approve_proposal", "bash",
    "bash_session_open", "bash_session_run", "browser_click", "browser_navigate",
    "browser_read", "browser_screenshot", "browser_type", "cancel_agent",
    "cancel_task", "comfyui_history", "comfyui_objects", "comfyui_status",
    "comfyui_workflow", "compact_context", "control_daemon",
    "daemon_status", "db_query", "decision_create", "decision_list",
    "deep_analyze", "discord_channel", "discord_status", "edit_file",
    "edit_task", "eventbus_recent", "find_files", "get_news",
    "get_weather",
    "route_directions",
    "git_diff", "git_log", "git_status",
    "goal_create", "goal_list", "heartbeat_status", "hf_vision_analyze",
    "home_assistant", "internal_api", "list_agents", "list_events",
    "list_initiatives", "list_plans", "list_proposals", "list_recurring",
    "list_scheduled_tasks", "list_self_wakeups", "list_signal_surfaces", "look_around",
    # Indbakken (Opgave 5, 3/10-2026). Alle TRE skal sendes, og det er en
    # bevidst pris paa tre skemaer i det cachebare prefix.
    #
    # Grunden: naegtelsen fra `inbox_gate` siger «kald inbox» og «luk med
    # inbox_done/inbox_drop». Var de ikke sendt, skulle han hente dem midt
    # i turen — og en hentning midt i turen kostede MAALT 92 % -> 26 %
    # cache-hit, fordi tools staar FOER beskederne. En blokering man kun
    # kan komme ud af ved at buste sin egen cache er en blokering man
    # ikke kan komme ud af.
    "inbox", "inbox_done", "inbox_drop",
    "flag_side_task", "activate_side_task", "dismiss_side_task",
    "load_more_tools",  # escape-hatch til de ~316 ikke-sendte tools — SKAL altid være på
    # App-self-control: Jarvis styrer jarvis-desk indefra (skift mode, åbn paneler).
    # Kernede kontrol-værktøjer = altid native, så han aldrig skal loade+gætte schema.
    "request_app_action", "open_ui_panel",
    "desk_get_layout", "desk_show_pane", "desk_close_pane",
    # Jarvis' egen browser i desk (21/9-2026) — kernet, saa schema'et altid er native.
    "jarvis_browser_open", "jarvis_browser_navigate", "jarvis_browser_read",
    "jarvis_browser_click", "jarvis_browser_type", "jarvis_browser_screenshot",
    "jarvis_browser_tabs", "jarvis_browser_close",
    "mark_wakeup_consumed", "memory_check_duplicate", "memory_list_headings", "memory_upsert_section",
    "my_project_journal_write", "my_project_status", "notify_user", "propose_git_commit",
    "propose_source_edit", "publish_file", "push_initiative",
    "read_chronicles", "read_dreams", "read_file", "read_mail",
    "read_model_config", "read_mood", "read_self_docs", "read_self_state",
    "read_signal_surface", "read_tool_result", "read_visual_memory", "recall_before_act",
    "recall_memories", "recall_sensory_memories", "schedule_self_wakeup", "schedule_task",
    "search", "search_chat_history", "search_memory", "search_sessions",
    "semantic_search_code", "send_discord_dm", "send_ntfy", "send_webchat_message",
    "service_status", "smart_outline", "spawn_agent_task", "todo_update_status",
    "trigger_heartbeat_tick", "verify_file_contains", "web_fetch", "web_scrape",
    "web_search", "wolfram_query", "write_file",
})


TIER_2_COMFORT_DEFAULTS: tuple[str, ...] = (
    "discord_status", "send_discord_dm", "send_telegram_message", "send_mail",
    "home_assistant", "list_events", "create_event",
    "spawn_agent_task", "list_agents",
)


TIER_2_CATEGORIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "discord": (
        ("discord", "dm ", "direct message", "guild", "channel"),
        ("discord_status", "send_discord_dm", "discord_channel"),
    ),
    "telegram": (
        ("telegram",),
        ("send_telegram_message",),
    ),
    "email": (
        ("email", "mail", "inbox", "e-mail", "gmail"),
        ("send_mail", "read_mail"),
    ),
    "browser": (
        ("browser", "webpage", "navigate", "click", "screenshot", "website",
         "chromium", "playwright", "tab "),
        ("browser_navigate", "browser_read", "browser_click", "browser_type",
         "browser_submit", "browser_screenshot", "browser_find_tabs",
         "browser_switch_tab"),
    ),
    "voice": (
        ("voice", "mic", "lyt", "høre", "wake", "whisper", "speech"),
        ("mic_listen", "voice_journal", "wake_word"),
    ),
    "webcam_vision": (
        ("kamera", "webcam", "billede", "image", "foto", "photo", "vision",
         "se rummet", "look around", "analyse af billede", "analyse image"),
        ("look_around", "analyze_image", "hf_vision_analyze"),
    ),
    "comfyui": (
        ("comfyui", "comfy", "workflow", "stable diffusion", "sdxl"),
        ("comfyui_status", "comfyui_workflow", "comfyui_history",
         "comfyui_objects"),
    ),
    "pollinations": (
        ("pollinations", "generate image", "generate video", "generér billede",
         "lav video"),
        ("pollinations_image", "pollinations_video"),
    ),
    "openrouter_image": (
        ("openrouter image", "rediger billede", "edit image", "tegn", "ikon",
         "icon", "logo", "sharp image", "vektor", "vector"),
        ("openrouter_image", "openrouter_image_edit"),
    ),
    "hf": (
        ("hugging", "transcribe", "embed", "classify", "zero-shot"),
        ("hf_text_to_video", "hf_transcribe_audio", "hf_embed",
         "hf_zero_shot_classify"),
    ),
    "home_assistant": (
        ("home assistant", "homeassistant", "lamp", "lys ", "lyset",
         "light", "sensor", "switch", "dimmer", "termostat", "thermostat"),
        ("home_assistant",),
    ),
    "agents": (
        ("agent", "sub-agent", "subagent", "delegate", "spawn", "council"),
        ("spawn_agent_task", "send_message_to_agent", "list_agents",
         "relay_to_agent", "cancel_agent"),
    ),
    "daemon_control": (
        ("daemon", "restart", "disable", "enable", "cadence", "overdue"),
        ("control_daemon", "daemon_health_alert", "daemon_alert_status",
         "restart_overdue_daemons"),
    ),
    "webhooks": (
        ("webhook", "web-hook", "callback url"),
        ("webhook_register", "webhook_send", "webhook_list", "webhook_test",
         "webhook_delete"),
    ),
    "health": (
        ("health check", "uptime", "ping", "endpoint", "service status"),
        ("health_check", "health_register", "health_status", "health_history"),
    ),
    "notify_channels": (
        ("notify", "notification channel", "slack", "push notification"),
        ("notify_out", "notify_channel_add", "notify_channel_list",
         "notify_channel_delete"),
    ),
    "calendar": (
        ("calendar", "event", "møde", "appointment", "meeting", "kalender"),
        ("list_events", "create_event", "delete_event"),
    ),
    "recurring": (
        ("recurring", "gentagende", "hver dag", "hver uge", "every day",
         "every week", "interval"),
        ("schedule_recurring", "list_recurring", "cancel_recurring"),
    ),
}


_RECENT_USAGE: deque[tuple[float, str]] = deque(maxlen=200)
_USAGE_LOCK = threading.Lock()
_USAGE_WINDOW_SECONDS = 600.0


def record_tool_usage(tool_name: str) -> None:
    """Record a tool call timestamp for recent-usage boost. Best-effort."""
    with _USAGE_LOCK:
        _RECENT_USAGE.append((time.time(), tool_name))


def _recent_tool_counts() -> dict[str, int]:
    cutoff = time.time() - _USAGE_WINDOW_SECONDS
    counts: dict[str, int] = {}
    with _USAGE_LOCK:
        for ts, name in _RECENT_USAGE:
            if ts >= cutoff:
                counts[name] = counts.get(name, 0) + 1
    return counts


def _keyword_score_for_categories(user_message: str) -> dict[str, int]:
    """Return {tool_name: keyword_score} based on category keyword hits."""
    if not user_message:
        return {}
    haystack = user_message.lower()
    scores: dict[str, int] = {}
    for _category, (keywords, tool_names) in TIER_2_CATEGORIES.items():
        hits = sum(1 for kw in keywords if kw in haystack)
        if hits <= 0:
            continue
        boost = 10 + 2 * (hits - 1)
        for t in tool_names:
            scores[t] = scores.get(t, 0) + boost
    return scores


def select_tools_for_copilot(
    tools: list[dict],
    *,
    user_message: str = "",
    session_id: str | None = None,
    max_tools: int = MAX_TOOLS,
    stable_only: bool = False,
) -> list[dict]:
    """Return at most ``max_tools`` tool definitions, prioritised for this call.

    - Tier 1 tools are always included.
    - Comfort defaults fill first from Tier 2.
    - Remaining slots go to Tier 2 tools scored by user-message keywords
      and recent usage (last ~10 min).
    - If the full catalog already fits, returns it unchanged (order preserved).

    ``stable_only`` (2026-06-30, deepseek cache-fix): når True ignoreres de to
    DYNAMISKE scoring-inputs (keyword_scores fra user_message + _recent_tool_counts
    fra sidste ~10 min). Tier-2 fyldes da rent deterministisk (comfort-defaults +
    stabil katalog-rækkefølge), så det SENDTE tool-sæt er byte-identisk hver tur →
    den ~17k-token tool-blok forbliver i DeepSeeks cachebare prefix. Den keyword-
    routing var redundant med ``load_more_tools`` (Jarvis henter sjældne tools
    on-demand) men brød cachen på keyword-tunge ture (hit 92%→~30%). Brugt af den
    cache-følsomme visible-lane.
    """
    if len(tools) <= max_tools:
        return list(tools)

    by_name: dict[str, dict] = {}
    for tdef in tools:
        name = tdef.get("function", {}).get("name")
        if isinstance(name, str):
            by_name[name] = tdef

    selected_names: list[str] = []
    seen: set[str] = set()

    # Tier 1
    for name in by_name:
        if name in TIER_1_ALWAYS_ON and name not in seen:
            selected_names.append(name)
            seen.add(name)

    remaining = max_tools - len(selected_names)
    if remaining <= 0:
        selected_names = _faestn_kraevede(
            selected_names, seen, by_name, max_tools, user_message)
        # Katalog-raekkefoelge ogsaa her (6/9-2026). Den anden udgang nedenfor
        # har altid genoprettet den; DENNE returnerede i udvaelgelsesraekkefoelge,
        # saa de pinnede navne endte til sidst i arrayet. Det er den udgang der
        # tages naar Tier 1 alene spraenger kappen — altsaa cowork, hans rige
        # bane. Se test_visible_tool_pool_keeps_catalog_order_for_deepseek_cache.
        _kat = {n: i for i, n in enumerate(by_name)}
        selected_names.sort(key=lambda n: _kat.get(n, 1 << 30))
        return [by_name[n] for n in selected_names[:max_tools]]

    # Tier 2 scoring. In stable_only mode the two per-call-variable inputs
    # (keyword match on user_message + recent usage) are zeroed → the fill
    # reduces to comfort-default boost + stable catalog index = deterministic.
    keyword_scores = {} if stable_only else _keyword_score_for_categories(user_message)
    recent_counts = {} if stable_only else _recent_tool_counts()

    tier2_candidates: list[tuple[int, int, str]] = []
    for name in by_name:
        if name in seen or name in TIER_1_ALWAYS_ON:
            continue
        score = keyword_scores.get(name, 0)
        if name in TIER_2_COMFORT_DEFAULTS:
            score += 5
        usage_boost = min(recent_counts.get(name, 0), 3) * 4
        score += usage_boost
        # negative score because we sort ascending by (-score, name) via tuple
        tier2_candidates.append((-score, _stable_idx(name), name))

    tier2_candidates.sort()
    for _neg_score, _idx, name in tier2_candidates[:remaining]:
        selected_names.append(name)
        seen.add(name)

    # Ensure the lazy schema loader survives aggressive caps. If Tier 1 alone
    # exceeds the cap, the old slice could drop load_more_tools and strand every
    # omitted tool until the next user turn.
    selected_names = _faestn_kraevede(
        selected_names, seen, by_name, max_tools, user_message)

    # Preserve original catalog order for consistent caching/debug.
    original_order: dict[str, int] = {
        (t.get("function", {}).get("name") or ""): i
        for i, t in enumerate(tools)
    }
    selected_names.sort(key=lambda n: original_order.get(n, 10_000))

    return [by_name[n] for n in selected_names if n in by_name]


def _faestn_kraevede(
    selected_names: list[str], seen: set[str], by_name: dict[str, dict],
    max_tools: int, user_message: str,
) -> list[str]:
    """Saet de vaerktoejer ind der SKAL overleve kappen, og skaer resten.

    Laa foer i TO kopier i samme funktion — én i den tidlige udgang
    (``remaining <= 0``) og én efter Tier 2. Da atomaritets-reglen blev
    tilfoejet 15/9-2026, ramte den kun den ene, og fejlen saa ud som om
    rettelsen ikke virkede: Tier 1 spraenger kappen alene i cowork-scope, saa
    det er netop den TIDLIGE udgang der tages.

    To kopier af den samme beslutning er dobbelt sandhed. Nu er der én.
    """
    # Sikkerhedsgulvet faestnes SAMMEN med de kraevede (30/9-2026). Det stod
    # skrevet som «must always be available regardless of past usage» og var
    # ikke haandhaevet nogen steder — se kommentaren over `SAFETY_FLOOR`.
    kraevede = tuple(REQUIRED_LAZY_TOOL_NAMES) + tuple(SAFETY_FLOOR)
    # Intet pinnes BETINGET laengere (3/10-2026): et besked-afhaengigt array
    # koster hele praefikset, og `skill_invoke` staar nu fast ovenfor. Kaldet
    # her er KUN sporet matched -> surfaced -> tilgaengelig -> invoked; det
    # returnerer altid (), se `spor_skill_match`.
    spor_skill_match(user_message)
    for navn in kraevede:
        if navn in by_name and navn not in seen:
            selected_names.append(navn)
            seen.add(navn)
    if len(selected_names) > max_tools:
        paakraevet = set(kraevede)
        beholdt = [n for n in selected_names if n in paakraevet]
        oevrige = [n for n in selected_names if n not in paakraevet]
        selected_names = oevrige[: max(0, max_tools - len(beholdt))] + beholdt
    return selected_names


def spor_skill_match(user_message: str) -> tuple[str, ...]:
    """Spor at et skill matchede. Fæstner INGENTING — og det er hele rettelsen.

    ## Hvad den gjorde indtil 3/10-2026

    Hed `_betinget_kraevede` og returnerede `("skill_invoke",)` ved et match.
    Begrundelsen stod i dens egen docstring: «en plads ud af 48 er ikke gratis;
    uden et match ville `skill_invoke` være et værktøj uden et navn at give
    det».

    ## Hvorfor den ikke må fæstne noget

    Et betinget pin gør værktøjs-arrayet besked-afhængigt, og arrayet ligger
    FØR hele samtalen i præfikset. Prisen er målt tre gange: 92 % → 26 % hit,
    og +419 tegn → 62.672 miss-tokens.

    Det var usynligt fordi tærsklen stod på 0,70 og matchede næsten alt — «hej
    hvordan går det?» matchede `ui-ux-pro-max`. Pinnet var i praksis fast, og
    cache-vagten var grøn af den FORKERTE grund. Da gulvet 3/10 blev hævet til
    primær-tærsklen, blev en næsten-konstant en ægte variabel, og vagten blev
    rød. `skill_invoke` står nu fast i `REQUIRED_LAZY_TOOL_NAMES`.

    ## Hvorfor funktionen så stadig findes

    Logge-linjen er det eneste spor for kæden matched → surfaced → TILGÆNGELIG
    → invoked. Det andet spor, `cognitive_state.skill_invoked`, bærer kun
    `{"name": ...}` og hverken run- eller session-id, så man kan ikke engang
    skelne en ægte invokering fra en test. Uden dette led kan man ikke svare på
    «virkede rettelsen».

    Returnerer derfor altid `()`. Kaster aldrig: et spor må ikke kunne vælte
    en tur.
    """
    besked = str(user_message or "").strip()
    if not besked:
        return ()
    try:
        from core.services.skill_relevance_surface import matchede_skills
        navne = matchede_skills(besked)
        if navne:
            logger.info("[skill-atomaritet] match: %s — `skill_invoke` staar "
                        "FAST i arrayet, intet pinnes betinget",
                        ", ".join(navne[:3]))
    except Exception:
        logger.debug("kunne ikke afgoere om skills blev naevnt", exc_info=True)
    return ()


#: Bagudkompatibelt navn. De to kaldesteder (denne fil og `visible_runs`) kan
#: opdateres naturligt; indtil da peger det gamle navn på sporet, så ingen
#: import brækker. Boy Scout: ryd op når call-sites er fulgt med.
_betinget_kraevede = spor_skill_match


def _stable_idx(name: str) -> int:
    """Deterministic tiebreak — lexicographic by name."""
    return sum((ord(c) * (i + 1)) for i, c in enumerate(name[:16]))


def select_tools_for_visible(
    tools: list[dict],
    *,
    user_message: str = "",
    session_id: str | None = None,
    max_tools: int = VISIBLE_MAX_TOOLS,
) -> list[dict]:
    """Provider-neutral pruning wrapper for the visible lane.

    Same scoring as ``select_tools_for_copilot``. Cap history:
      - 140 (initial) — fitted Tier 1 + a small Tier 2 cushion
      - 200 (2026-04-27) — bumped because Tier 1 had grown to ~183 and
        the user noticed schedule_self_wakeup getting pruned
      - 128 (2026-04-29) — restored after Tier 1 was data-driven trimmed
        from 185 → 103 tools. The new Tier 1 already covers actually-used
        tools; the remaining 25 slots go to keyword-matched Tier 2 plus
        comfort defaults. Saves ~8K tokens per visible-chat call vs 200
        cap, while still leaving keyword-routed headroom.
      - 48 (2026-09-04) — CC-style small native pool. Rare tools are reached
        through load_more_tools, which is pinned into the cap.
    """
    # Dispatcheren laegges i INPUT, ikke oven paa resultatet: saa gaelder
    # loftet, pin-logikken og `REQUIRED_LAZY_TOOL_NAMES` for den som for
    # ethvert andet vaerktoej. Foerste forsoeg 30/9 lagde den ovenpaa og
    # sproengte loftet (49 mod 48); andet forsoeg afkortede halen og smed et
    # PINNED vaerktoej. Begge blev fanget af husets egne vagter.
    from core.tools.kaldt_vaerktoej import DEFINITION as _KALD_DEF, KALD_NAVN as _KALD_NAVN
    _ind = list(tools or [])
    if not any((d.get("function") or d).get("name") == _KALD_NAVN for d in _ind):
        _ind.append(_KALD_DEF)
    valgt = select_tools_for_copilot(
        _ind, user_message=user_message, session_id=session_id, max_tools=max_tools,
        stable_only=True,
    )
    # `call_loaded_tool` staar ALTID med, og den er KONSTANT — det er hele
    # pointen. Et hentet vaerktoej kaldes gennem den i stedet for at blive
    # flettet ind i arrayet, saa praefikset kan genbruges paa tvaers af ture.
    # Maalt: én ny definition i arrayet koster 8.704 tokens mod DeepSeeks API,
    # og 419 tegn kostede 62.672 miss i produktion. Se `kaldt_vaerktoej.py`.
    return valgt
