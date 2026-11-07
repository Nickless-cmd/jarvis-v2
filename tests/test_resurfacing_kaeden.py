"""Resurfacing-kæden: kadence → kandidat → prompt-linje.

MÅLT 7/11-2026: `memory_resurfacing.pick_resurfacing_candidate` havde NUL
produktions-kaldere. Dens egen docstring sagde «once an hour (when called from
the heartbeat)», men hverken heartbeat eller initiativ-accumulatoren kaldte den.
Efter seks måneder stod der 3 poster i `memory_resurfacing_log`.

To fejl gjorde det muligt, og begge er målt:
1. Ingen kadence kaldte den — kun `resurface_old_memory`-værktøjet, som jeg
   skulle huske at bruge.
2. `_memory_md()` brugte `workspace_dir()`, som KASTER `NoUserContextError` når
   ingen bruger er bundet. I en autonom kadence-kørsel er det præcis tilstanden,
   så kaldet ville fejle selv om nogen kaldte det — og fejlen blev slugt til
   «ingen kandidater».

Testene her måler KOBLINGEN, ikke implementeringen: at produceren findes og
kalder kandidaten, at kilden virker uden brugerkontekst, og at linjen viser
SELVE mindet — ikke kun et tal.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── 1. kadence-koblingen ─────────────────────────────────────────────────────

def test_produceren_er_registreret_med_kadence():
    """Resurfacing skal køre af sig selv — ikke vente på at jeg husker et værktøj."""
    from core.services import internal_cadence as ic
    from core.services.internal_cadence_inner_life import register_inner_life_producers

    register_inner_life_producers(ic.register_producer)
    spec = ic._producers.get("memory_resurfacing_pick")
    assert spec is not None, (
        "memory_resurfacing_pick er ikke registreret som producer — så kaldes "
        "pick_resurfacing_candidate aldrig af sig selv (målt: 3 poster på 6 mdr.)"
    )
    assert spec.cooldown_minutes == 60, (
        f"forventede 60 min (docstringens «once an hour»), fik {spec.cooldown_minutes}"
    )


def test_produceren_kalder_kandidaten_og_viderebringer_overskriften(monkeypatch):
    """Producerens run_fn skal kalde kandidaten og rapportere HVAD der kom tilbage."""
    from core.services import internal_cadence_inner_life as il
    from core.services import memory_resurfacing as mr

    kaldt = []

    def _fake_pick(*, trigger="heartbeat", seed=None):
        kaldt.append(trigger)
        return {"heading": "En gammel tråd", "level": "##"}

    monkeypatch.setattr(mr, "pick_resurfacing_candidate", _fake_pick)

    specs = {}

    def _capture(spec):
        specs[spec.name] = spec

    il.register_inner_life_producers(_capture)
    res = specs["memory_resurfacing_pick"].run_fn(trigger="cadence", last_visible_at="")

    assert kaldt == ["cadence"], f"kandidaten blev ikke kaldt: {kaldt}"
    assert res.get("resurfaced") is True
    assert res.get("heading") == "En gammel tråd", (
        "produceren skal viderebringe overskriften — ellers kan resultatet ikke ses"
    )


def test_produceren_melder_aerligt_naar_der_ikke_er_en_kandidat(monkeypatch):
    """Ingen kandidat er ikke en fejl — men det skal siges, ikke skjules som succes."""
    from core.services import internal_cadence_inner_life as il
    from core.services import memory_resurfacing as mr

    monkeypatch.setattr(mr, "pick_resurfacing_candidate", lambda **kw: None)
    specs = {}
    il.register_inner_life_producers(lambda s: specs.__setitem__(s.name, s))

    res = specs["memory_resurfacing_pick"].run_fn(trigger="cadence", last_visible_at="")

    assert res.get("resurfaced") is False
    assert "reason" in res and res["reason"]


# ── 2. kilden virker uden brugerkontekst ─────────────────────────────────────

def test_memory_md_taaler_at_der_ingen_brugerkontekst_er(monkeypatch):
    """`workspace_dir()` kaster uden kontekst — kilden må ikke gøre det samme.

    Det var den anden halvdel af fejlen: selv med en kalder ville kaldet fejle i
    en autonom kørsel, fordi `_memory_md()` gik gennem den kontekst-bundne vej.
    """
    from core.runtime.workspace_paths import NoUserContextError
    from core.services import memory_resurfacing as mr

    def _kaster(*a, **kw):
        raise NoUserContextError("ingen kontekst")

    # Den kontekst-bundne resolver fejler — som i en autonom kørsel.
    monkeypatch.setattr("core.runtime.workspace_paths.workspace_dir", _kaster)

    # Kilden skal stadig svare (via owner/shared-fallbacken), ikke kaste.
    sti = mr._memory_md()
    assert isinstance(sti, Path)
    assert sti.name == "MEMORY.md"


def test_kilden_importerer_ikke_den_kontekst_bundne_resolver():
    """Strukturel vagt: `workspace_dir` (kaster) må ikke være den der bruges.

    Vagt­en parser AST'en i stedet for at grepe kildeteksten: en docstring der
    NAEVNER `workspace_dir()` er ikke et kald, og en grep-vagt ville både fange
    sin egen forklaring og misse et kald skrevet over to linjer.
    """
    import ast
    import inspect

    from core.services import memory_resurfacing as mr

    tree = ast.parse(inspect.getsource(mr))
    kaldte_navne: set[str] = set()
    importerede: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            kaldte_navne.add(node.func.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            kaldte_navne.add(node.func.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                importerede.add(alias.asname or alias.name)

    assert "workspace_dir_or_owner" in importerede, (
        f"kilden importerer ikke owner-fallbacken; importeret: {sorted(importerede)}"
    )
    assert "workspace_dir" not in importerede, (
        "kilden importerer stadig den kontekst-bundne resolver, som kaster i autonomi"
    )
    assert "workspace_dir" not in kaldte_navne, (
        f"kilden kalder workspace_dir() — det kaster uden brugerkontekst: {sorted(kaldte_navne)}"
    )


# ── 3. linjen viser mindet, ikke kun et tal ──────────────────────────────────

def test_linjen_viser_selve_mindet_ikke_bare_antallet(monkeypatch):
    """«4 glemte minder er kommet tilbage» er en statistik, ikke et minde."""
    from core.services import visible_inner_life as vil

    fake = {
        "active": True,
        "signals": {
            "resurfaced_total": 4,
            "distinct_headings": 4,
            "recent": [{"heading": "Desk-release + deploy — den fulde vej", "at": "2026-11-07"}],
        },
    }
    monkeypatch.setattr(
        "core.services.memory_resurfacing.build_memory_resurfacing_surface",
        lambda: fake,
    )

    line = vil._memory_resurfacing_line()

    assert line, "linjen er tavs trods en aktiv log"
    assert "Desk-release + deploy" in line, (
        f"linjen viser ikke mindet, kun tallet: {line!r}"
    )


def test_linjen_er_tavs_naar_loggen_er_tom(monkeypatch):
    """Tom log skal give None — ikke «0 glemte minder er kommet tilbage»."""
    from core.services import visible_inner_life as vil

    monkeypatch.setattr(
        "core.services.memory_resurfacing.build_memory_resurfacing_surface",
        lambda: {"active": False, "signals": {}, "reason": "loggen er tom"},
    )
    assert vil._memory_resurfacing_line() is None


def test_linjen_taaler_en_flade_uden_recent_felt(monkeypatch):
    """Faldet tilbage til tallet naar `recent` mangler — men maa ikke kaste."""
    from core.services import visible_inner_life as vil

    monkeypatch.setattr(
        "core.services.memory_resurfacing.build_memory_resurfacing_surface",
        lambda: {"active": True, "signals": {"resurfaced_total": 2, "distinct_headings": 2}},
    )
    line = vil._memory_resurfacing_line()
    assert line and "2 glemte minder" in line


# ── 4. sektionen: kontekst, ikke replik — og overlever chat-scope ─────────────
#
# MÅLT 7/11-2026: linjen stod i `[INDRE LIV]`, som har chat-vægt 0.1 mod
# tærsklen 0.3 og derfor skæres HELT i en ren samtaletur. Det er præcis den
# kanal hvor et gammelt minde er mest værd. Flyttet ud som egen sektion —
# samme flytning oppositionen fik 4/11.

def test_sektionen_overlever_chat_scope_hvor_indre_liv_skæres():
    """Den ægte forskel: egen sektion slipper igennem, blokken gør ikke."""
    from core.services import central_prompt_composer as cpc
    from core.tools import tool_scoping

    # Flaget er shadow i en testproces (intet skæres), men LIVE i drift. Uden
    # denne patch måler testen ingenting: den ville være grøn uanset vægte.
    tok = tool_scoping.set_tool_scope("chat")
    try:
        with patch.object(cpc, "is_live_enabled", return_value=True):
            assert cpc.should_include("samtale", "genfundet minde") is True, (
            "sektionen skæres i chat-scope — så er den ikke flyttet ud alligevel"
        )
            assert cpc.should_include("samtale", "indre liv") is False, (
                "forudsætningen er ændret: «indre liv» bliver ikke længere skåret "
                "i chat. Så er flytningen måske ikke nødvendig — mål det før du "
                "ændrer testen."
            )
    finally:
        tool_scoping.reset_tool_scope(tok)


def test_sektionen_er_KONTEKST_ikke_en_replik():
    """Et genfundet minde må ikke blive en mekanisk selvfortælling.

    Formen skal give indholdet og en note om at det er kontekst — ikke
    «jeg har genfundet …», som jeg så ville sige højt hver gang produceren kørte.
    """
    from core.services import visible_inner_life as vil

    with patch.object(vil, "build_resurfaced_memory_section", wraps=vil.build_resurfaced_memory_section):
        sec = vil.build_resurfaced_memory_section()
    if sec is None:
        pytest.skip("ingen resurfacing i loggen endnu")
    assert "kontekst" in sec.lower(), "sektionen siger ikke at det er kontekst"
    assert "lad det ligge" in sec.lower(), (
        "sektionen giver ikke muligheden for at tie — så er den en replik"
    )
    assert not sec.lower().startswith("jeg har genfundet"), (
        "sektionen er formuleret som noget jeg skal sige højt"
    )


def test_linjen_staar_IKKE_laengere_i_den_blok_der_skæres():
    """Regression: flyttes den tilbage i `[INDRE LIV]`, forsvinder den i chat."""
    from core.services import visible_inner_life as vil
    import inspect

    # AST, ikke grep: en kommentar der NÆVNER navnet er ikke et kald. Målt
    # 7/11-2026 — en grep-vagt fældede sin egen forklarende kommentar.
    tree = ast.parse(inspect.getsource(vil.build_inner_life_section).lstrip())
    kaldte = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "_memory_resurfacing_line" not in kaldte, (
        "resurfacing-linjen kaldes igen fra [INDRE LIV], som skæres i chat-scope"
    )


def test_sektionen_springer_test_triggers_over():
    """En test-trigger må ikke ende som kontekst i en rigtig prompt."""
    from core.services import visible_inner_life as vil

    fake = {
        "active": True,
        "signals": {"recent": [{"heading": "En test-overskrift", "at": "2026-11-07",
                                "trigger": "test-uden-kontekst"}]},
    }
    with patch("core.services.memory_resurfacing.build_memory_resurfacing_surface",
               return_value=fake):
        assert vil.build_resurfaced_memory_section() is None, (
            "en test-trigger blev injiceret i prompten som et ægte minde"
        )


def test_mindet_naar_FAKTISK_frem_til_modellen_i_en_chatprompt(isolated_runtime, monkeypatch):
    """Den ægte sidste meter — ikke at funktionen findes eller at gaten tillader
    sektionen, men at mindet står i den prompt modellen ser.

    Målt 7/11-2026: mutationen der fjernede `_awareness_add`-kaldet i
    prompt-bygningen blev IKKE fældet af de øvrige tests. De målte funktionen og
    gaten — ikke koblingen. Det er præcis fejlklassen vi jager: formen bevaret,
    indholdet tabt.
    """
    from core.services import central_prompt_composer as cpc
    from core.services import prompt_contract as pc
    from core.tools import tool_scoping

    UNIK = "Et afsnit der kun findes i denne test — genfundet minde"
    fake = {
        "active": True,
        "signals": {"recent": [{"heading": UNIK, "at": "2026-11-07",
                                "trigger": "cadence"}]},
    }
    monkeypatch.setattr(
        "core.services.memory_resurfacing.build_memory_resurfacing_surface",
        lambda: fake,
    )
    # Prompt-bygningen slår brain-facts op, som embedder via fastembed og henter
    # en model fra HuggingFace når Ollama ikke svarer. Det er ikke det denne test
    # måler — den måler om mindet står i den sammensatte prompt.
    monkeypatch.setattr(
        "core.services.jarvis_brain._embed_text", lambda text: [0.0] * 8, raising=False
    )
    cpc._kv_set(cpc._LIVE_FLAG, True)
    cpc._kv_set(cpc._WEIGHTS_KEY, {})

    token = tool_scoping.set_tool_scope("chat")
    try:
        tekst = pc._build_visible_chat_prompt_assembly_impl(
            provider="deepseek",
            model="deepseek-v4-flash",
            user_message="hvordan staar det til?",
            session_id="s-genfundet-minde",
        ).text
    finally:
        tool_scoping.reset_tool_scope(token)

    assert UNIK in tekst, (
        "mindet nåede ikke den byggede chat-prompt — sektionen er nomineret, "
        "ikke koblet"
    )
