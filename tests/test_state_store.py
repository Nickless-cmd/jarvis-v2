from __future__ import annotations

import os

import pytest

from core.runtime import state_store


def test_save_json_strict_propagates_atomic_replace_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)

    def fail_replace(source, destination):
        raise OSError("disk unavailable")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="disk unavailable"):
        state_store.save_json_strict("recovery", {"run": "r1"})


def test_save_json_remains_self_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(
        state_store,
        "save_json_strict",
        lambda name, data: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    state_store.save_json("recovery", {"run": "r1"})


def test_aendret_ns_er_nul_for_fil_der_ikke_findes():
    from core.runtime import state_store

    assert state_store.aendret_ns("findes-slet-ikke") == 0


def test_aendret_ns_rykker_naar_filen_skrives():
    from core.runtime import state_store

    foer = state_store.aendret_ns("mtime-proeve")
    state_store.save_json("mtime-proeve", {"a": 1})
    efter = state_store.aendret_ns("mtime-proeve")

    assert foer == 0
    assert efter > 0


# ── Skrive- og laeseFEJL skal vaere SYNLIGE (17/10-2026) ────────────────────
# Driften koerer INFO, mens begge stier loggede paa `debug`. En fejlet
# skrivning var derfor 100 % usynlig: 80 wakeups forsvandt uden et eneste spor.


def test_fejlet_skrivning_logges_som_warning(tmp_path, monkeypatch, caplog):
    """En fejlet skrivning skal staa i loggen paa driftsniveau, ikke debug."""
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(
        state_store,
        "save_json_strict",
        lambda name, data: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    with caplog.at_level("INFO", logger="core.runtime.state_store"):
        state_store.save_json("recovery", {"run": "r1"})

    advarsler = [r for r in caplog.records if r.levelname == "WARNING"]
    assert advarsler, "en fejlet skrivning efterlod INGEN advarsel paa INFO-niveau"
    assert "recovery" in advarsler[0].getMessage()


def test_fejlet_skrivning_registreres_i_anomali_kanalen(tmp_path, monkeypatch):
    """WARNING'en alene er ikke nok — Centralen skal ogsaa se fejlen."""
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(
        state_store,
        "save_json_strict",
        lambda name, data: (_ for _ in ()).throw(OSError("disk unavailable")),
    )
    kald = []

    import core.services.central_anomaly as ca

    monkeypatch.setattr(
        ca, "record_anomaly", lambda **kw: kald.append(kw), raising=True
    )

    state_store.save_json("recovery", {"run": "r1"})

    assert kald, "anomali-kanalen blev aldrig kaldt"
    assert kald[0]["exc_type"] == "OSError"
    assert "recovery" in kald[0]["message"]


def test_anomali_kanal_i_stykker_vaelter_ikke_skrivestien(tmp_path, monkeypatch):
    """At rapportere en fejl maa aldrig selv fejle — WARNING'en staar tilbage."""
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(
        state_store,
        "save_json_strict",
        lambda name, data: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    import core.services.central_anomaly as ca

    def spræng(**kw):
        raise RuntimeError("anomali-kanalen er nede")

    monkeypatch.setattr(ca, "record_anomaly", spræng, raising=True)

    # Kontrakten: ingen exception ud til de 83 kaldesteder.
    state_store.save_json("recovery", {"run": "r1"})


def test_korrupt_fil_logges_som_warning(tmp_path, monkeypatch, caplog):
    """En korrupt fil er en fejl — laeseren maa ikke stiltiende se default."""
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)
    (tmp_path / "oedelagt.json").write_text("{ikke json", encoding="utf-8")

    with caplog.at_level("INFO", logger="core.runtime.state_store"):
        svar = state_store.load_json("oedelagt", {"fallback": True})

    assert svar == {"fallback": True}
    assert [r for r in caplog.records if r.levelname == "WARNING"], (
        "en korrupt fil blev laest uden en advarsel"
    )


def test_manglende_fil_logges_IKKE(tmp_path, monkeypatch, caplog):
    """Filen findes ikke = normal drift. Stoej her ville goere signalet vaerdiloest."""
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)

    with caplog.at_level("INFO", logger="core.runtime.state_store"):
        svar = state_store.load_json("findes-ikke", {"fallback": True})

    assert svar == {"fallback": True}
    assert not [r for r in caplog.records if r.levelname == "WARNING"]
