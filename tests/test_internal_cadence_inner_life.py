"""Kontrakten for de indre-liv-producenter i kadence-motoren.

Filen registrerer de daemons der kører på Jarvis' EGEN rytme — ikke på en
brugers. Hver producer er en `ProducerSpec` med navn, cooldown og en `run_fn`
der kaldes med keyword-argumenter.

Testene her maaler kontrakten, ikke implementeringen: at alle producers
registreres, at hver `run_fn` kan kaldes med den signatur motoren bruger, at
cooldowns er positive, og at navnene er unikke. En producer der registreres
med et navn der allerede findes, vinder den sidste tavst — det er praecis den
fejl der blev maalt i `daemon_manager` (memory_safeguard stod to gange).
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.internal_cadence import ProducerSpec  # noqa: E402
from core.services.internal_cadence_inner_life import (  # noqa: E402
    register_inner_life_producers,
)


def _specs() -> dict[str, ProducerSpec]:
    """Registrér i en fangst-dict — uden at røre den globale motor-tilstand."""
    ud: dict[str, ProducerSpec] = {}
    register_inner_life_producers(lambda s: ud.__setitem__(s.name, s))
    return ud


def test_alle_producenter_registreres():
    """17 producers er filens kontrakt; et fald betyder en tavst droppet daemon."""
    specs = _specs()
    assert len(specs) == 17, f"forventede 17 producers, fik {len(specs)}: {sorted(specs)}"


def test_navnene_er_unikke():
    """To producers med samme navn: den sidste vinder tavst. Det skal fanges her."""
    navne: list[str] = []
    register_inner_life_producers(lambda s: navne.append(s.name))
    assert len(navne) == len(set(navne)), (
        f"dublerede producer-navne: {sorted(n for n in navne if navne.count(n) > 1)}"
    )


def test_hver_producer_har_en_kaldbar_run_fn_med_motorens_signatur():
    """Motoren kalder `run_fn(trigger=..., last_visible_at=...)` — keyword-only."""
    fejl: list[str] = []
    for navn, spec in _specs().items():
        if not callable(spec.run_fn):
            fejl.append(f"{navn}: run_fn er ikke kaldbar")
            continue
        try:
            params = inspect.signature(spec.run_fn).parameters
        except (TypeError, ValueError) as exc:
            fejl.append(f"{navn}: signaturen kunne ikke laeses ({exc})")
            continue
        if "trigger" not in params:
            fejl.append(f"{navn}: mangler 'trigger'")
        if "last_visible_at" not in params:
            fejl.append(f"{navn}: mangler 'last_visible_at'")
    assert not fejl, "run_fn-signaturer bryder motorens kontrakt:\n  " + "\n  ".join(fejl)


def test_cooldowns_er_positive():
    """Cooldown 0 eller negativ ville koere produceren hvert tik."""
    daarlige = {n: s.cooldown_minutes for n, s in _specs().items() if s.cooldown_minutes <= 0}
    assert not daarlige, f"ikke-positive cooldowns: {daarlige}"


def test_prioriteter_er_heltal():
    """Prioritet bruges til raekkefoelge; en streng ville fejle sent og tavst."""
    daarlige = {n: s.priority for n, s in _specs().items() if not isinstance(s.priority, int)}
    assert not daarlige, f"ikke-heltallige prioriteter: {daarlige}"


def test_depends_on_peger_paa_registrerede_navne():
    """En afhaengighed paa et navn der ikke findes blokerer produceren for altid.

    Maalt 7/11-2026: `brain_continuity` er IKKE i denne fils gruppe — den
    registreres i en anden gruppe. Kontrakten er derfor mod HELE motoren, ikke
    mod denne fil alene. At tjekke kun her ville vaere en falsk positiv, som
    foerste version af denne test var.
    """
    from core.services import internal_cadence as ic
    from core.services.internal_cadence_core import register_core_producers

    register_inner_life_producers(ic.register_producer)
    try:
        register_core_producers(ic.register_producer)
    except Exception:  # gruppen kan kraeve anden opsaetning; livsgruppen er nok til at maale
        pass

    specs = _specs()
    alle = set(ic._producers) | set(specs)
    ukendte: list[str] = []
    for navn, spec in specs.items():
        for dep in spec.depends_on or []:
            if dep not in alle:
                ukendte.append(f"{navn} -> {dep}")
    assert not ukendte, f"depends_on peger paa uregistrerede producers: {ukendte}"


# ── resurfacing: den ene producer der blev tilfoejet 7/11-2026 ────────────────

def test_memory_resurfacing_koerer_hver_time():
    """Docstringen sagde «once an hour» — nu er det ogsaå kadencen i koden."""
    spec = _specs().get("memory_resurfacing")
    assert spec is not None, "memory_resurfacing er ikke registreret"
    assert spec.cooldown_minutes == 60


def test_memory_resurfacing_kalder_kandidaten_og_viderebringer_overskriften(monkeypatch):
    """Uden denne kobling er produceren en tom skal der melder «koert»."""
    from core.services import memory_resurfacing as mr

    kaldt: list[str] = []

    def _fake(*, trigger="heartbeat", seed=None):
        kaldt.append(trigger)
        return {"heading": "En gammel tråd"}

    monkeypatch.setattr(mr, "pick_resurfacing_candidate", _fake)
    res = _specs()["memory_resurfacing"].run_fn(trigger="cadence", last_visible_at="")

    assert kaldt == ["cadence"], f"kandidaten blev ikke kaldt: {kaldt}"
    assert res.get("resurfaced") is True
    assert res.get("heading") == "En gammel tråd"


def test_memory_resurfacing_melder_aerligt_naar_der_intet_er_at_genfinde(monkeypatch):
    """Ingen kandidat er ikke en fejl — men det maa ikke se ud som succes."""
    from core.services import memory_resurfacing as mr

    monkeypatch.setattr(mr, "pick_resurfacing_candidate", lambda **kw: None)
    res = _specs()["memory_resurfacing"].run_fn(trigger="cadence", last_visible_at="")

    assert res.get("resurfaced") is False
    assert res.get("reason"), "en tom koersel skal sige HVORFOR den var tom"
