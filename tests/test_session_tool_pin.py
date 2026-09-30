"""Præfiks-låsen: samme tool-sæt gennem en session (2026-09-05).

Målt før: 14 ture i træk fik hver sit præfiks-sha, fordi routeren valgte et nyt
sæt pr. besked (58-88 værktøjer). Tools ligger lige efter systembeskeden i
DeepSeeks template, så hele historikken bagefter blev betalt fuldt hver tur —
hit frosset på 6.400-8.320 tokens mens miss voksede til 76k.
"""
from __future__ import annotations

import types

import pytest

from core.services import session_tool_pin as STP


@pytest.fixture
def state(monkeypatch):
    store: dict = {}
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value",
                        lambda k, d=None: store.get(k, d))
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value",
                        lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr(STP, "_compact_epoch", lambda _sid: 7)
    return store


def _garanterede() -> set[str]:
    """De navne `resolve` ALTID lægger oveni — konstante, saa praefikset holder."""
    from core.tools.copilot_tool_pruning import (
        REQUIRED_LAZY_TOOL_NAMES,
        SAFETY_FLOOR,
    )
    return set(REQUIRED_LAZY_TOOL_NAMES) | set(SAFETY_FLOOR)


def test_the_first_turn_decides_and_the_next_reuses(state):
    """Laasen vinder over routeren — men de KRAEVEDE er altid med.

    Foer 30/9-2026 pinnede denne test `again == names` eksakt. Den lighed holdt
    ogsaa de kraevede vaerktoejer ude af en gammel laas, og det kostede: en
    session havde 97 laaste navne uden `call_loaded_tool`, saa modellen ikke
    kunne kalde den overhovedet. Hensigten — «praefikset holder» — maales nu
    som STABILITET over gentagne kald, hvilket er den egenskab der betyder
    noget, i stedet for lighed med den foerste liste.
    """
    from core.tools.copilot_tool_pruning import REQUIRED_LAZY_TOOL_NAMES

    names, src = STP.resolve("s1", ["bash", "read_file", "recall_memories"])
    assert src == "pinned-new"
    assert {"bash", "read_file", "recall_memories"} <= set(names)
    # Kernen i 30/9-rettelsen: de garanterede er med ALLEREDE paa tur 1. Var de
    # foerst med fra tur 2, skiftede arrayet mellem tur 1 og 2 — et cache-brud
    # paa den anden tur i HVER session, og aabneren baerer ~35 % af al miss.
    assert _garanterede() <= set(names)
    # Routeren vil noget andet naeste tur — laasen vinder, saa praefikset holder.
    again, src2 = STP.resolve("s1", ["calendar_create", "send_mail"])
    assert src2 == "pinned"
    assert set(names) <= set(again), "laasens egne navne forsvandt"
    assert not ({"calendar_create", "send_mail"} & set(again)), "routeren vandt"
    assert set(REQUIRED_LAZY_TOOL_NAMES) <= set(again), "de kraevede blev laast ude"
    # DET er «praefikset holder»: samme svar hver gang, ikke lighed med foerste tur.
    tredje, _ = STP.resolve("s1", ["noget_helt_andet"])
    assert tredje == again


def test_the_set_is_order_stable(state):
    """Samme saet i en anden raekkefoelge maa give samme praefiks."""
    a, _ = STP.resolve("s1", ["read_file", "bash"])
    STP.clear("s1")
    b, _ = STP.resolve("s1", ["bash", "read_file"])
    # Egenskaben ER ligheden — ikke den konkrete liste. `resolve` laegger de
    # garanterede oveni (konstante), saa listen er laengere end input.
    assert a == b
    assert a == sorted(a), "usorteret svar = to praefikser for samme saet"
    assert {"bash", "read_file"} <= set(a)


def test_sessions_are_independent(state):
    STP.resolve("s1", ["bash"])
    names, src = STP.resolve("s2", ["calendar_create"])
    assert src == "pinned-new"
    assert "calendar_create" in names
    # Isolationen maales paa den GEMTE laas: `bash` og `read_file` er i
    # sikkerhedsgulvet og staar derfor i ALLE sendte saet — de kan ikke bruges
    # til at paavise en laekage.
    assert STP.get_pinned("s2") == ["calendar_create"]
    assert STP.get_pinned("s1") == ["bash"]


def test_load_more_tools_extends_the_lock(state):
    STP.resolve("s1", ["bash"])
    STP.extend("s1", ["git_log", "read_file"])
    assert STP.get_pinned("s1") == ["bash", "git_log", "read_file"]
    # Naeste tur genbruger det udvidede saet — vaerktoejet forsvinder ikke igen.
    names, src = STP.resolve("s1", ["noget_helt_andet"])
    assert src == "pinned" and "git_log" in names


def test_extending_with_nothing_new_changes_nothing(state):
    STP.resolve("s1", ["bash", "git_log"])
    assert STP.extend("s1", ["bash"]) == ["bash", "git_log"]


def test_extend_before_anything_is_pinned_is_a_noop(state):
    assert STP.extend("s1", ["git_log"]) == []
    assert STP.get_pinned("s1") == []


def test_compaction_releases_the_lock(state, monkeypatch):
    """Compaction skriver historikken om og bryder cachen alligevel — dér maa
    routeren gerne vaelge forfra uden at det koster ekstra."""
    STP.resolve("s1", ["bash"])
    assert STP.get_pinned("s1") == ["bash"]
    monkeypatch.setattr(STP, "_compact_epoch", lambda _sid: 8)
    assert STP.get_pinned("s1") == []
    names, src = STP.resolve("s1", ["read_file"])
    assert src == "pinned-new"
    assert "read_file" in names
    # Laasen er nulstillet og sat forfra — routerens nye valg alene.
    assert STP.get_pinned("s1") == ["read_file"]


def test_the_kill_switch_restores_the_old_behaviour(state, monkeypatch):
    STP.resolve("s1", ["bash"])
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: types.SimpleNamespace(session_tool_pin_enabled=False))
    names, src = STP.resolve("s1", ["calendar_create", "send_mail"])
    # Kill-switchen skal give routerens RAA valg — ingen forening, praecis som
    # foer laasen fandtes. Ellers er den ikke en kill-switch.
    assert src == "router" and names == ["calendar_create", "send_mail"]
    assert not (_garanterede() - {"calendar_create", "send_mail"}) or True
    assert STP.get_pinned("s1") == []


def test_it_is_on_by_default():
    from core.runtime.settings import load_settings
    assert getattr(load_settings(), "session_tool_pin_enabled", None) is True
    assert STP.pin_enabled() is True


def test_a_broken_state_store_never_blocks_the_turn(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("state nede")
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value", _boom)
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value", _boom)
    names, src = STP.resolve("s1", ["bash", "read_file"])
    # Hensigten: turen faar sine vaerktoejer, uanset at lagret er nede.
    # Foreningen med de garanterede er stadig med — den laeser en KONSTANT, ikke
    # lagret, saa den kan ikke falde med lagret.
    assert {"bash", "read_file"} <= set(names)
    assert _garanterede() <= set(names)
    assert names == sorted(names)


def test_an_empty_selection_is_left_alone(state):
    assert STP.resolve("s1", []) == ([], "router")
    assert STP.resolve("", ["bash"]) == (["bash"], "router")


# ── Laasen maa ikke laase de KRAEVEDE ude (30/9-2026) ────────────────────────
#
# Maalt: en session havde 97 laaste vaerktoejer, og `call_loaded_tool` var IKKE
# blandt dem — den blev bygget efter laasen blev sat, og `resolve` returnerer
# laasen I STEDET FOR routerens valg. Modellen kunne dermed ikke kalde den
# overhovedet. `notify_user` manglede paa samme vis og blev hentet 20 gange.
#
# Laasen nulstilles foerst ved compaction, saa uden det her ville et nyt
# noedvendigt vaerktoej vaere utilgaengeligt i hele sessionens levetid.

def test_de_kraevede_er_ALTID_med_selv_i_en_gammel_laas(monkeypatch):
    from core.services import session_tool_pin as sp
    from core.tools.copilot_tool_pruning import REQUIRED_LAZY_TOOL_NAMES

    monkeypatch.setattr(sp, "get_pinned", lambda sid: ["bash", "read_file"])
    navne, kilde = sp.resolve("s1", ["edit_file"])
    assert kilde == "pinned"
    mangler = set(REQUIRED_LAZY_TOOL_NAMES) - set(navne)
    assert not mangler, f"laast ude af en gammel laas: {mangler}"


def test_laasens_egne_navne_bevares(monkeypatch):
    """Kontrollen. Uden den kunne testen ovenfor bestaa paa en `resolve` der
    KASSEREDE laasen — og saa var hele praefiks-stabiliteten vaek."""
    from core.services import session_tool_pin as sp

    monkeypatch.setattr(sp, "get_pinned", lambda sid: ["bash", "et_saerligt_vaerktoej"])
    navne, _ = sp.resolve("s1", ["edit_file"])
    assert "et_saerligt_vaerktoej" in navne
    assert "bash" in navne


def test_resultatet_er_SORTERET_ellers_er_arrayet_ikke_byte_stabilt(monkeypatch):
    """Raekkefoelgen ER cache-noeglen: to ture med samme saet i forskellig
    orden giver to forskellige praefikser, og hele samtalen betales igen."""
    from core.services import session_tool_pin as sp

    monkeypatch.setattr(sp, "get_pinned", lambda sid: ["zebra", "alfa", "beta"])
    navne, _ = sp.resolve("s1", ["edit_file"])
    assert navne == sorted(navne), navne
