"""Tool-pruning for the visible/copilot lanes.

Cache regression: the visible lane keyword-routed the tool SET per user message
(keyword_scores + recent usage), so the ~17k-token tool block changed turn-to-turn
and broke DeepSeek's prefix cache on keyword-heavy turns. select_tools_for_visible
now passes stable_only=True → deterministic set every turn. load_more_tools must be
in the always-on core so Jarvis can still reach the long tail on demand.
"""
from __future__ import annotations

from core.tools import copilot_tool_pruning as ctp


def _make_tools(n_extra: int = 40) -> list[dict]:
    """Tier-1 tools + extra non-tier-1 tools, exceeding MAX_TOOLS so pruning runs."""
    tools = [{"function": {"name": name}} for name in sorted(ctp.TIER_1_ALWAYS_ON)]
    tools += [{"function": {"name": f"zz_extra_{i:02d}"}} for i in range(n_extra)]
    return tools


def _names(sel: list[dict]) -> list[str]:
    return [(t.get("function") or {}).get("name") for t in sel]


def test_load_more_tools_in_tier1():
    # Escape-hatch to the ~316 non-sent tools must always be available.
    assert "load_more_tools" in ctp.TIER_1_ALWAYS_ON


def test_visible_set_is_deterministic_across_messages():
    tools = _make_tools()
    assert len(tools) > ctp.MAX_TOOLS  # ensure pruning actually triggers
    a = ctp.select_tools_for_visible(tools, user_message="hej hvordan har du det", session_id="s")
    b = ctp.select_tools_for_visible(
        tools,
        user_message="searche google sende discord scheduled wakeup screenshot commit",
        session_id="s",
    )
    # Byte-identical selection regardless of (keyword-heavy) message → cacheable.
    assert _names(a) == _names(b)
    # Den synlige bane har sit eget loft (48), ikke det generelle 128.
    assert len(a) == ctp.VISIBLE_MAX_TOOLS


def test_stable_only_ignores_user_message():
    tools = _make_tools()
    a = ctp.select_tools_for_copilot(tools, user_message="weather forecast", stable_only=True)
    b = ctp.select_tools_for_copilot(tools, user_message="git commit push deploy", stable_only=True)
    assert _names(a) == _names(b)


def test_pinned_tools_survive_the_cap():
    """Tier 1 er 107 navne og kappen 48 — de kan ikke alle overleve.

    Foer 6/9-2026 paastod denne test det modsatte og havde vaeret roed siden
    kappen blev sat ned 4/9. Det der FAKTISK skal garanteres er de pinnede:
    uden dem fjerner pruneren vaerktoejer som prompten aktivt peger paa, og
    saa findes de uden at kunne kaldes.
    """
    # Pinning kan kun redde et vaerktoej der ER i kataloget — saa laeg dem i.
    tools = _make_tools() + [
        {"function": {"name": n}} for n in ctp.REQUIRED_LAZY_TOOL_NAMES
    ]
    sel = set(_names(ctp.select_tools_for_visible(tools, user_message="x", session_id="s")))
    for name in ctp.REQUIRED_LAZY_TOOL_NAMES:
        assert name in sel, name


def test_tier1_fills_the_rest_of_the_cap():
    tools = _make_tools()
    sel = _names(ctp.select_tools_for_visible(tools, user_message="x", session_id="s"))
    assert len(sel) == ctp.VISIBLE_MAX_TOOLS
    ikke_pinnet = [n for n in sel if n not in ctp.REQUIRED_LAZY_TOOL_NAMES]
    assert all(n in ctp.TIER_1_ALWAYS_ON for n in ikke_pinnet)


def test_full_catalog_under_cap_returned_unchanged():
    tools = [{"function": {"name": f"t{i}"}} for i in range(10)]
    out = ctp.select_tools_for_copilot(tools, user_message="anything", max_tools=128)
    assert _names(out) == _names(tools)


# ── De fire hyppigst hentede skal HAVE en plads (30/9-2026) ──────────────────
#
# Alle fire stod allerede i TIER_1_ALWAYS_ON og blev alligevel hentet 76 gange
# paa 30 dage, fordi Tier 1 er 118 navne mod et loft paa 48 og trunkeres i
# ankomstraekkefoelge — 77 af de 118 naaede aldrig arrayet. Medlemskab af
# Tier 1 er ingen garanti; `REQUIRED_LAZY_TOOL_NAMES` er.
#
# Hver hentning koster ~8.704 tokens (maalt mod DeepSeeks API), fordi
# vaerktoejsarrayet ligger foer hele samtalen i praefikset.

_HYPPIGST_HENTEDE = (
    "send_discord_dm",          # 28 hentninger paa 30 dage
    "record_sensory_memory",    # 18 — stod ikke engang i Tier 1
    "send_webchat_message",     # 15
    "recall_sensory_memories",  # 15
)


def test_de_hyppigst_hentede_naar_faktisk_arrayet():
    """Ikke «staar i Tier 1» — men «bliver rent faktisk sendt»."""
    import core.tools.copilot_tool_pruning as ctp
    from core.tools.simple_tools import get_tool_definitions

    valgt = ctp.select_tools_for_visible(get_tool_definitions(), user_message="", session_id=None)
    navne = {(d.get("function") or d).get("name") for d in valgt}
    mangler = [n for n in _HYPPIGST_HENTEDE if n not in navne]
    assert not mangler, f"hentes ofte, men sendes ikke: {mangler}"


def test_byttet_sproenger_ikke_loftet():
    """Kontrollen. Uden den kunne testen ovenfor bestaa ved at sende ALT —
    og et array der vokser er praecis det problem de fire skulle loese."""
    import core.tools.copilot_tool_pruning as ctp
    from core.tools.simple_tools import get_tool_definitions

    valgt = ctp.select_tools_for_visible(get_tool_definitions(), user_message="", session_id=None)
    assert len(valgt) == ctp.VISIBLE_MAX_TOOLS


def test_escape_vejene_overlever_byttet():
    """Begge veje ud til de ~320 oevrige skal blive: `load_more_tools` finder
    dem, `call_loaded_tool` kalder dem uden at roere arrayet."""
    import core.tools.copilot_tool_pruning as ctp
    from core.tools.simple_tools import get_tool_definitions

    navne = {(d.get("function") or d).get("name")
             for d in ctp.select_tools_for_visible(get_tool_definitions(),
                                                   user_message="", session_id=None)}
    assert {"load_more_tools", "call_loaded_tool"} <= navne


# ── Sikkerhedsgulvet skal HAANDHAEVES, ikke bare staa skrevet (30/9-2026) ────
#
# Gulvet stod i `scripts/regenerate_tier1.py` med teksten «must always be
# available regardless of past usage» og blev unioneret ind i TIER_1_ALWAYS_ON
# ved regenerering. Men Tier 1 er 118 navne mod et loft paa 48 og trunkeres i
# ankomstraekkefoelge — saa gulvet var et krav ingen haandhaevede.
#
# Maalt: 7 af de 28 registrerede gulv-navne blev ikke sendt, heriblandt
# `memory_upsert_section` med 157 kald paa 30 dage.

def test_hele_sikkerhedsgulvet_naar_arrayet():
    """Ikke «staar i en liste» — men «bliver rent faktisk sendt»."""
    import core.tools.copilot_tool_pruning as ctp
    from core.tools.simple_tools import get_tool_definitions

    alle = get_tool_definitions()
    registreret = {(d.get("function") or d).get("name") for d in alle}
    valgt = {(d.get("function") or d).get("name")
             for d in ctp.select_tools_for_visible(alle, user_message="", session_id=None)}
    mangler = (set(ctp.SAFETY_FLOOR) & registreret) - valgt
    assert not mangler, f"sikkerhedsgulvet naar ikke arrayet: {sorted(mangler)}"


def test_gulvet_navngiver_kun_vaerktoejer_der_FINDES():
    """`propose_git_commit` stod i gulvet uden at findes i kataloget. Et navn
    ingen kan kalde er ikke et sikkerhedsgulv — det er en stavefejl med
    autoritet."""
    import core.tools.copilot_tool_pruning as ctp
    from core.tools.simple_tools import get_tool_definitions

    registreret = {(d.get("function") or d).get("name") for d in get_tool_definitions()}
    ukendte = set(ctp.SAFETY_FLOOR) - registreret
    assert not ukendte, f"gulvet navngiver vaerktoejer der ikke findes: {sorted(ukendte)}"


def test_gulvet_har_ÉN_kilde():
    """Gulvet stod to steder og blev haandhaevet nul. Generatoren skal LAESE
    runtime-listen, ikke have sin egen."""
    from pathlib import Path

    kilde = Path("scripts/regenerate_tier1.py").read_text(encoding="utf-8")
    assert "from core.tools.copilot_tool_pruning import SAFETY_FLOOR" in kilde, (
        "generatoren har sin egen kopi af gulvet igen — dobbelt sandhed")
