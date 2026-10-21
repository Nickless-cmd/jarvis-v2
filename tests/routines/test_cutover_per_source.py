"""Per-kilde cutover: én opgave ad gangen, ikke alt-eller-intet.

Baggrund (19/10-2026, Bjørn): «Tænd Routine-cutover på én enkelt opgave som
prøve først». Det var ikke muligt: ``routine_cutover_enabled()`` læste kun
globale sandheds-ord, så en prøve på én recurring ville flytte alle 13 levende
recurrings plus alle scheduled jobs på én gang.

``cutover_allows(kind, id)`` er forgreningen. Recurring og scheduled vælges
per definition; systemarbejde vælges per stabil producent, fx
``system:heartbeat``. Den globale værdi er kun nødbremsens eksplicitte
alt-på-én-gang-form.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def adapters(monkeypatch):
    from core.services import routine_trigger_adapters as mod

    monkeypatch.delenv("JARVIS_ROUTINES_CUTOVER", raising=False)
    return mod


def _set(monkeypatch, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv("JARVIS_ROUTINES_CUTOVER", raising=False)
    else:
        monkeypatch.setenv("JARVIS_ROUTINES_CUTOVER", value)


def test_usat_env_slaar_intet_til(adapters, monkeypatch):
    _set(monkeypatch, None)
    assert adapters.routine_cutover_enabled() is False
    assert adapters.cutover_allows("recurring", "rec-x") is False


def test_tom_streng_slaar_intet_til(adapters, monkeypatch):
    _set(monkeypatch, "")
    assert adapters.routine_cutover_enabled() is False
    assert adapters.cutover_allows("recurring", "rec-x") is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " 1 "])
def test_globale_ord_slaar_alt_til(adapters, monkeypatch, value):
    _set(monkeypatch, value)
    assert adapters.routine_cutover_enabled() is True
    assert adapters.cutover_allows("recurring", "hvad-som-helst") is True
    assert adapters.cutover_allows("scheduled", "hvad-som-helst") is True


def test_enkelt_kilde_slaar_kun_den_til(adapters, monkeypatch):
    _set(monkeypatch, "recurring:rec-276ee9620d")
    assert adapters.cutover_allows("recurring", "rec-276ee9620d") is True
    # nabo i samme tabel er urørt
    assert adapters.cutover_allows("recurring", "rec-6456e88d03") is False
    # anden kildekategori er urørt
    assert adapters.cutover_allows("scheduled", "rec-276ee9620d") is False


def test_enkelt_kilde_holder_den_globale_vej_slukket(adapters, monkeypatch):
    """Kernen i prøven: de fem andre kaldesteder må ikke flytte sig."""
    _set(monkeypatch, "recurring:rec-276ee9620d")
    assert adapters.routine_cutover_enabled() is False


def test_flere_kilder_paa_liste(adapters, monkeypatch):
    _set(monkeypatch, "recurring:rec-a, recurring:rec-b ,scheduled:s-1")
    assert adapters.cutover_allows("recurring", "rec-a") is True
    assert adapters.cutover_allows("recurring", "rec-b") is True
    assert adapters.cutover_allows("scheduled", "s-1") is True
    assert adapters.cutover_allows("recurring", "rec-c") is False


def test_dispatch_recurring_bruger_forgreningen(adapters, monkeypatch):
    """dispatch_recurring skal læse cutover_allows, ikke den globale funktion."""
    _set(monkeypatch, "recurring:valgt")

    calls: list[str] = []

    class _FakeAdapters:
        def enqueue_recurring(self, source_id, *, occurrence_id=None):
            calls.append(source_id)
            return "enqueued"

    # valgt opgave -> Routine-vejen, legacy springes over
    out = adapters.dispatch_recurring(
        "valgt", legacy=lambda: calls.append("legacy"), adapters=_FakeAdapters(),
    )
    assert out == "enqueued"
    assert calls == ["valgt"]

    # ikke-valgt opgave -> legacy-vejen
    calls.clear()
    out = adapters.dispatch_recurring(
        "ikke-valgt", legacy=lambda: calls.append("legacy"), adapters=_FakeAdapters(),
    )
    assert out is None
    assert calls == ["legacy"]


def test_scheduled_og_system_kan_piloteres_uafhaengigt(adapters, monkeypatch):
    _set(monkeypatch, "scheduled:s-1,system:heartbeat")
    calls: list[str] = []

    class _FakeAdapters:
        def enqueue_scheduled(self, source_id):
            calls.append(f"scheduled:{source_id}")
            return "scheduled"

        def enqueue_system(self, producer, source_id, *, trigger_inputs=None):
            calls.append(f"system:{producer}:{source_id}")
            return "system"

    fake = _FakeAdapters()
    assert adapters.dispatch_scheduled(
        "s-1", legacy=lambda: calls.append("legacy-s1"), adapters=fake,
    ) == "scheduled"
    assert adapters.dispatch_scheduled(
        "s-2", legacy=lambda: calls.append("legacy-s2"), adapters=fake,
    ) is None
    assert adapters.dispatch_system(
        "heartbeat", "tick-1", trigger_inputs={},
        legacy=lambda: calls.append("legacy-heartbeat"), adapters=fake,
    ) == "system"
    assert adapters.dispatch_system(
        "dream", "dream-1", trigger_inputs={},
        legacy=lambda: calls.append("legacy-dream"), adapters=fake,
    ) is None
    assert calls == [
        "scheduled:s-1", "legacy-s2", "system:heartbeat:tick-1", "legacy-dream",
    ]
