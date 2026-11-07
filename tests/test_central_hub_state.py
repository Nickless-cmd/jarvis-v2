"""Tilstand-sektionen i Jarvis Mind: de 35 central-flader der havde nul læsere.

MÅLT 7/11-2026: 202 `build_*_surface` i core/services kaldes aldrig fra `apps/`.
36 af dem er `central/*`. Jeg kaldte alle 36 — 35 leverer en ikke-tom dict.
`central_layer_contract.build_layer_surface` kræver et argument og er maskineri,
ikke tilstand, og er udeladt med vilje.

De 35 findes IKKE blandt `cognitive_architecture_surface()["surfaces"]` (målt:
0 af 35 blandt de 72), så Sind-fanen kunne ikke vise dem uanset hvor mange
undertabs den fik. Denne test holder den nye indgang.

Det vigtige er ikke at funktionerne virker — det gjorde de hele tiden. Det er at
de har en indgang der faktisk bliver kaldt.
"""
from __future__ import annotations

import pytest

from core.services import central_hub


def _alle_producenter() -> list[tuple[str, str, str]]:
    ud: list[tuple[str, str, str]] = []
    for gruppe in central_hub._STATE_PRODUCERS.values():
        ud.extend(gruppe)
    return ud


def test_tilstand_er_i_indekset_med_seks_undertabs() -> None:
    """Sektionen skal være synlig i sub-navbaren — ellers kan UI'et ikke vælge den."""
    idx = {s["section"]: s for s in central_hub.mind_index()}
    assert "state" in idx, "Tilstand mangler i mind_index — så findes fanen ikke i UI"
    sektion = idx["state"]
    assert sektion["label"] == "Tilstand"
    assert sektion["ready"] is True, "ready=False betyder at _BUILDERS ikke har den"
    tabs = [t["tab"] for t in sektion["tabs"]]
    assert tabs == ["sjaelestilstand", "krop", "rytme", "drom", "model", "agenda"]


def test_alle_fem_og_tredive_flader_er_registreret() -> None:
    """Antallet er kontrakten: 35 flader, fordelt på seks grupper."""
    producenter = _alle_producenter()
    assert len(producenter) == 35, f"forventede 35 producenter, fandt {len(producenter)}"
    navne = [n for n, _m, _f in producenter]
    assert len(set(navne)) == 35, f"dubletnavne i registret: {navne}"
    # Hver gruppe skal have mindst én, ellers er en undertab tom i UI'et.
    for gruppe, items in central_hub._STATE_PRODUCERS.items():
        assert items, f"gruppen {gruppe} er tom"


def test_hver_undertaB_svarer_med_kaldte_flader() -> None:
    """Den ægte kobling: undertaben skal returnere fladerne, ikke en tom dict."""
    for gruppe, items in central_hub._STATE_PRODUCERS.items():
        d = central_hub.mind_section("state", gruppe)
        surf = d.get("surfaces") or {}
        assert d.get("antal") == len(items), (
            f"{gruppe}: antal={d.get('antal')} men registret har {len(items)}"
        )
        for navn, _mod, _fn in items:
            assert navn in surf, f"{gruppe}: {navn} blev ikke kaldt"
        assert d.get("mangler") == [], f"{gruppe}: flader forsvandt: {d.get('mangler')}"


def test_en_kastende_flade_skjuler_ikke_de_andre(monkeypatch) -> None:
    """Self-safe pr. producent — samme kontrakt som central_tool_infra_surface."""
    gruppe = "krop"
    items = central_hub._STATE_PRODUCERS[gruppe]
    første_navn, første_mod, første_fn = items[0]

    original = central_hub._call_surface

    def _braekker(mod_path: str, fn_attr: str):
        if mod_path == første_mod and fn_attr == første_fn:
            raise RuntimeError("bevidst fejl i test")
        return original(mod_path, fn_attr)

    monkeypatch.setattr(central_hub, "_call_surface", _braekker)
    # Ryd TTL-cachen så mutationen faktisk rammer.
    central_hub._section_cache.clear()

    d = central_hub.mind_section("state", gruppe)
    surf = d.get("surfaces") or {}
    assert surf[første_navn].get("active") is False, "den kastende flade blev ikke isoleret"
    assert "error" in surf[første_navn]
    # De øvrige skal stadig være der — det er hele pointen.
    for navn, _m, _f in items[1:]:
        assert navn in surf, f"{navn} forsvandt fordi en anden flade kastede"


def test_fladerne_er_IKKE_i_cognitive_architecture() -> None:
    """Præmissen for hele sektionen, målt: 0 af 35 findes blandt de 72.

    Holder denne test op med at holde, er fladerne blevet en del af Sind-fanens
    kilde — og så skal de fjernes herfra i stedet for at stå to steder.
    """
    from core.services.cognitive_architecture_surface import (
        build_cognitive_architecture_surface,
    )

    surf = build_cognitive_architecture_surface().get("surfaces") or {}
    mine = {n for n, _m, _f in _alle_producenter()}
    overlap = mine & set(surf)
    assert not overlap, f"fladerne er nu også i cognitive_architecture: {sorted(overlap)}"


def test_ukendt_undertab_afvises_frem_for_at_blive_tom() -> None:
    """En tastefejl i UI'et må ikke ligne «fanen er tom»."""
    d = central_hub.mind_section("state", "finnes-ikke")
    assert d.get("active") is False
    assert "ukendt undertab" in str(d.get("error", ""))


def test_default_undertaB_er_sjaelestilstand() -> None:
    """Uden tab vælges den første — sjælestilstanden, ikke en tom projektion."""
    d = central_hub.mind_section("state")
    assert d.get("tab") == "sjaelestilstand"
    assert (d.get("antal") or 0) == len(central_hub._STATE_PRODUCERS["sjaelestilstand"])
