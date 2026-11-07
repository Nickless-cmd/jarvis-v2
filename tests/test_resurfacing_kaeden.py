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
