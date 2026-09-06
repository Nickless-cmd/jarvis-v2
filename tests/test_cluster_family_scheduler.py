"""Familiernes løkke: kør de forfaldne, lad de andre være, og vælt aldrig på én."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import cluster_family_scheduler as CFS


class _Settings:
    def __init__(self, extra: dict) -> None:
        self.extra = extra


def _for_minutes_ago(minutes: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()


# ---------------------------------------------------------------------------
# Forfald
# ---------------------------------------------------------------------------


def test_aldrig_koert_er_forfalden():
    assert CFS._is_due("cluster_infra", 2.0, "") is True


def test_lige_koert_er_ikke_forfalden():
    assert CFS._is_due("cluster_infra", 5.0, _for_minutes_ago(1)) is False


def test_gammel_nok_er_forfalden():
    assert CFS._is_due("cluster_infra", 2.0, _for_minutes_ago(3)) is True


def test_ulaeseligt_tidsstempel_holder_ikke_familien_nede():
    """Et ødelagt tidsstempel må ikke kunne gøre en familie tavs for evigt."""
    assert CFS._is_due("cluster_infra", 2.0, "ikke-en-dato") is True


# ---------------------------------------------------------------------------
# Løkkens krop
# ---------------------------------------------------------------------------


@pytest.fixture
def _stubbet(monkeypatch):
    """Stub daemon_manager og frist-hjælperen, så intet rigtigt tick fyrer."""
    from core.services import daemon_manager as dm
    from core.services import heartbeat_runtime as hb

    kaldt: list[str] = []
    registreret: list[tuple[str, dict]] = []

    tilstande = [
        {"name": f, "enabled": True, "effective_cadence_minutes": 2,
         "last_run_at": _for_minutes_ago(30)}
        for f, _d in CFS._FAMILY_DEADLINES
    ]

    monkeypatch.setattr(dm, "get_all_daemon_states", lambda: list(tilstande))
    monkeypatch.setattr(dm, "is_enabled", lambda navn: True)
    monkeypatch.setattr(
        dm, "record_daemon_tick",
        lambda navn, res: registreret.append((navn, dict(res or {}))),
    )
    monkeypatch.setattr(
        hb, "_daemon_tick_with_deadline",
        lambda navn, fn, *a, **k: (kaldt.append(navn) or {"family": navn, "fired": True}),
    )
    monkeypatch.setattr(
        CFS, "_tick_functions",
        lambda: {f: (lambda: {"family": f}) for f, _d in CFS._FAMILY_DEADLINES},
    )
    monkeypatch.setattr(CFS, "_enabled", lambda: True)
    return kaldt, registreret, tilstande


def test_alle_forfaldne_familier_koeres(_stubbet):
    kaldt, registreret, _ = _stubbet
    ud = CFS.run_due_families()
    assert len(ud["ran"]) == len(CFS._FAMILY_DEADLINES)
    assert len(kaldt) == len(CFS._FAMILY_DEADLINES)
    assert len(registreret) == len(CFS._FAMILY_DEADLINES)
    assert not ud["failed"]


def test_familie_der_lige_har_koert_springes_over(_stubbet, monkeypatch):
    kaldt, _registreret, tilstande = _stubbet
    tilstande[0]["last_run_at"] = _for_minutes_ago(0.1)
    ud = CFS.run_due_families()
    assert CFS._FAMILY_DEADLINES[0][0] not in ud["ran"]
    assert len(ud["ran"]) == len(CFS._FAMILY_DEADLINES) - 1


def test_slukket_familie_roeres_ikke(_stubbet, monkeypatch):
    from core.services import daemon_manager as dm

    kaldt, _r, _t = _stubbet
    slukket = CFS._FAMILY_DEADLINES[2][0]
    monkeypatch.setattr(dm, "is_enabled", lambda navn: navn != slukket)
    ud = CFS.run_due_families()
    assert slukket not in ud["ran"]
    assert slukket not in kaldt


def test_killswitch_stopper_alt(_stubbet, monkeypatch):
    kaldt, _r, _t = _stubbet
    monkeypatch.setattr(CFS, "_enabled", lambda: False)
    ud = CFS.run_due_families()
    assert ud["skipped"] == "kill-switch"
    assert kaldt == []


def test_killswitch_laeses_fra_config(monkeypatch):
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _Settings({"cluster_family_scheduler_enabled": False}),
    )
    assert CFS._enabled() is False


def test_manglende_config_betyder_taendt(monkeypatch):
    """Kan config ikke læses, skal familierne køre — ikke gå i stå i tavshed."""
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: (_ for _ in ()).throw(RuntimeError("ingen config")),
    )
    assert CFS._enabled() is True


def test_en_familie_der_fejler_vaelter_ikke_de_andre(_stubbet, monkeypatch):
    from core.services import heartbeat_runtime as hb

    kaldt, _r, _t = _stubbet
    syg = CFS._FAMILY_DEADLINES[4][0]

    def _tick(navn, fn, *a, **k):
        if navn == syg:
            raise RuntimeError("provider nede")
        kaldt.append(navn)
        return {"family": navn}

    monkeypatch.setattr(hb, "_daemon_tick_with_deadline", _tick)
    ud = CFS.run_due_families()
    assert syg in ud["failed"]
    assert len(ud["ran"]) == len(CFS._FAMILY_DEADLINES) - 1


def test_manglende_tick_funktion_meldes_som_fejl(_stubbet, monkeypatch):
    monkeypatch.setattr(
        CFS, "_tick_functions",
        lambda: {f: (lambda: {}) for f, _d in CFS._FAMILY_DEADLINES[1:]},
    )
    ud = CFS.run_due_families()
    assert CFS._FAMILY_DEADLINES[0][0] in ud["failed"]


# ---------------------------------------------------------------------------
# Overflade
# ---------------------------------------------------------------------------


def test_overfladen_daekker_alle_familier(_stubbet):
    surface = CFS.build_cluster_family_scheduler_surface()
    assert len(surface["families"]) == len(CFS._FAMILY_DEADLINES)
    assert {f["family"] for f in surface["families"]} == {
        f for f, _d in CFS._FAMILY_DEADLINES
    }
    assert surface["interval_seconds"] == CFS.INTERVAL_SECONDS
    for felt in ("cadence_minutes", "deadline_seconds", "minutes_since_last_run"):
        assert felt in surface["families"][0]


def test_fristerne_er_de_samme_som_paa_den_gamle_sti():
    """Løkken må ikke opfinde nye frister — den flytter kun hvem der kalder."""
    forventet = {
        "cluster_somatic": 8.0, "cluster_innervoice": 25.0, "cluster_affect": 25.0,
        "cluster_narrative": 40.0, "cluster_cognition": 40.0, "cluster_memory": 60.0,
        "cluster_aesthetic": 20.0, "cluster_relation": 20.0,
        "cluster_projects": 30.0, "cluster_infra": 40.0,
    }
    assert dict(CFS._FAMILY_DEADLINES) == forventet
