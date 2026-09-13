"""Én alarm pr. cooldown — paa tvaers af processer OG genstarter.

MAALT i Bjoerns `jarvis-heartbeat` natten til 13/9-2026. Cooldownen er seks
timer, men alarmerne kom 00:00, 00:21, 00:34, 01:36 og 02:25 — og 00:21, 00:34
og 01:36 kom hver TO gange i samme minut.

To aarsager, én rod: cooldownen var en modul-global.

  * Baade jarvis-api og jarvis-runtime koerer koden → hver proces sin egen
    taeller → to alarmer.
  * Hver genstart nulstillede taelleren → seks-timers-vinduet holdt aldrig.

Og udsendelsen sad i LAESE-stien (`get_weather`), saa enhver der byggede
infra-overfladen kunne komme til at ringe — blandt andet prompt-samlingen,
som koerer pr. tur.
"""
import inspect

import pytest

import core.services.infra_weather_daemon as iw


@pytest.fixture(autouse=True)
def _rent_bord(monkeypatch):
    lager: dict = {}
    import core.services.shared_cache as sc
    monkeypatch.setattr(sc, "get", lambda k: lager.get(k))
    monkeypatch.setattr(sc, "set", lambda k, v, *, ttl_seconds: lager.__setitem__(k, v))
    return lager


@pytest.fixture
def sendte(monkeypatch):
    ud: list = []
    import core.services.ntfy_gateway as ng
    monkeypatch.setattr(ng, "send_notification",
                        lambda msg, **kw: ud.append(msg) or {"status": "sent"})
    return ud


KRITISK = {"label": "critical", "reasons": ["api-cost=$59.58"]}


def test_anden_proces_faar_IKKE_lov_at_ringe_igen(sendte):
    """Dubletterne: to processer, samme minut, samme alarm."""
    iw._maybe_emit_critical(KRITISK)
    iw._maybe_emit_critical(KRITISK)     # «den anden proces»
    assert len(sendte) == 1


def test_en_genstart_re_armerer_ikke_alarmen(sendte, monkeypatch):
    """Modul-globalen doede med processen. Den delte noegle goer ikke."""
    iw._maybe_emit_critical(KRITISK)
    # Simulér genstart: modulets egne globaler nulstilles.
    monkeypatch.setattr(iw, "_last_state", None, raising=False)
    monkeypatch.setattr(iw, "_last_computed_ts", 0.0, raising=False)
    iw._maybe_emit_critical(KRITISK)
    assert len(sendte) == 1, "genstarten fik den til at ringe igen"


def test_ikke_kritisk_ringer_ikke(sendte):
    iw._maybe_emit_critical({"label": "ok", "reasons": []})
    assert sendte == []


def test_LAESE_stien_alarmerer_ikke():
    """«no hidden side effects» — husets egen regel. At bygge overfladen maa
    ikke kunne sende noget til hans telefon."""
    assert "_maybe_emit_critical" not in inspect.getsource(iw.get_weather)


def test_daemonens_slag_er_det_ENESTE_der_alarmerer():
    assert "_maybe_emit_critical" in inspect.getsource(iw.tick)


def test_utilgaengelig_delt_tilstand_giver_alarm_frem_for_tavshed(sendte, monkeypatch):
    """Tvivl skal falde ud til at Bjoern faar besked. Én alarm for meget er
    bedre end tavshed om at systemet er under kritisk pres."""
    import core.services.shared_cache as sc
    monkeypatch.setattr(sc, "get", lambda k: (_ for _ in ()).throw(RuntimeError("nede")))
    iw._maybe_emit_critical(KRITISK)
    assert len(sendte) == 1
