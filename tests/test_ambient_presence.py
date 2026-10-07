"""Jarvis' egne tilstandssignaler — på event-bussen, aldrig i Bjørns lomme.

## Hvorfor modulet ser sådan ud (målt 7/10-2026)

Indtil den dag sendte hvert ambient-signal en ntfy-notifikation til telefonen:
«træder ind i legetilstand», «vender tilbage til arbejde», plus et ensomt «·» i
timen. Målt i beskedhistorikken: **14 af 31 beskeder på ét døgn var denne
interne støj.** Bjørn spurgte selv: «Det er nogen sjove ting jeg får på ntfy…
lege tilstand??»

Signalet er ægte og værd at have. Det hører bare i Centralen, hvor Jarvis kan
se det, ikke på en telefon der ringer.

## Hvorfor DENNE fil findes

`ambient_presence.py` blev committet uden test, og `enforce-test-coverage`
kigger på staged filer. Hver eneste fletning der rørte modulet faldt derfor
over gaten — og blev lukket med `SKIP`. En gate alle springer over er ikke en
gate. Testene her lukker den for alvor.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import ambient_presence as ap


@pytest.fixture(autouse=True)
def _nulstil_og_fang(monkeypatch):
    """Nulstil modulets globaler og fang det der publiceres.

    Globalerne er modul-niveau; uden nulstilling arver hver test den forrige
    tests rate-limit og fase.
    """
    monkeypatch.setattr(ap, "_LAST_SIGNAL_AT", None)
    monkeypatch.setattr(ap, "_LAST_RHYTHM_AT", None)
    monkeypatch.setattr(ap, "_LAST_PHASE", None)
    monkeypatch.setattr(ap, "_LAST_PLAY_MODE", False)
    sendt: list[tuple[str, dict]] = []
    monkeypatch.setattr(ap.event_bus, "publish",
                        lambda navn, nyttelast=None, **k: sendt.append((navn, nyttelast or {})))
    return sendt


# ── grænsen der blev flyttet ────────────────────────────────────────────────

def test_signalet_gaar_KUN_paa_event_bussen(_nulstil_og_fang, monkeypatch):
    """Kernen i 7/10-rettelsen. Rammer en ntfy-vej igen, er de 14 af 31
    beskeder tilbage i Bjørns lomme."""
    import core.services.alarm_ud as alarm
    import core.services.ntfy_gateway as ntfy

    monkeypatch.setattr(ntfy, "send_notification",
                        lambda **k: pytest.fail("ambient-signal gik til telefonen"),
                        raising=False)
    monkeypatch.setattr(alarm, "send_alert",
                        lambda **k: pytest.fail("ambient-signal gik gennem alarm-routeren"),
                        raising=False)

    assert ap.emit_ambient_signal(kind="play_mode", detail="leg") is True
    assert [navn for navn, _ in _nulstil_og_fang] == ["runtime.ambient_presence_signal"]


def test_kilde_vagt_modulet_naevner_ingen_notifikations_vej():
    """En import tilbage ville ikke blive fanget af testen ovenfor hvis den lå
    i en gren der ikke køres. Kilden må slet ikke kende vejen."""
    import inspect

    kilde = inspect.getsource(ap)
    for forbudt in ("ntfy_gateway", "send_notification", "alarm_ud", "send_alert"):
        # Docstringen MÅ nævne hvorfor vejen blev fjernet — derfor kun kode.
        kode = "\n".join(l for l in kilde.splitlines() if not l.strip().startswith("#"))
        kode = kode.split('"""')[0] + '"""'.join(kode.split('"""')[2:])
        assert forbudt not in kode, f"{forbudt} er tilbage i koden"


# ── rate-limit ──────────────────────────────────────────────────────────────

def test_andet_signal_inden_30_min_afvises(_nulstil_og_fang):
    assert ap.emit_ambient_signal(kind="play_mode") is True
    assert ap.emit_ambient_signal(kind="dream") is False, "rate-limit holdt ikke"
    assert len(_nulstil_og_fang) == 1


def test_signalet_slipper_igennem_naar_de_30_min_er_gaaet(_nulstil_og_fang, monkeypatch):
    assert ap.emit_ambient_signal(kind="play_mode") is True
    monkeypatch.setattr(ap, "_LAST_SIGNAL_AT",
                        datetime.now(UTC) - ap._MIN_INTERVAL - timedelta(seconds=1))
    assert ap.emit_ambient_signal(kind="dream") is True
    assert len(_nulstil_og_fang) == 2


def test_rytmen_har_sit_EGET_ur(_nulstil_og_fang):
    """Ellers ville ét tilstandsskift kunne tie timepulsen i en halv time —
    eller omvendt."""
    assert ap.emit_ambient_signal(kind="play_mode") is True
    assert ap.emit_presence_rhythm() is True
    assert [navn for navn, _ in _nulstil_og_fang] == [
        "runtime.ambient_presence_signal", "runtime.ambient_presence_rhythm"]


def test_rytmen_er_rate_limited_paa_en_time(_nulstil_og_fang):
    assert ap.emit_presence_rhythm() is True
    assert ap.emit_presence_rhythm() is False


# ── kun ÆGTE skift ──────────────────────────────────────────────────────────

def test_samme_fase_to_gange_giver_INTET_tilstandssignal(_nulstil_og_fang, monkeypatch):
    """Foerste udgave af denne test paastod at det andet tick giver en rytme.
    Det goer det ikke: det FOERSTE tick fyrer allerede en, og rytmen er
    timebegraenset. Koden havde ret, forventningen var forkert.

    Paastanden her er den rigtige: uden et faseskift kommer der intet
    TILSTANDSSIGNAL. Rytmens eget ur proeves for sig.
    """
    ap.maybe_emit_phase_signal({"phase": "active"})
    _nulstil_og_fang.clear()
    ap.maybe_emit_phase_signal({"phase": "active"})
    assert "runtime.ambient_presence_signal" not in [n for n, _ in _nulstil_og_fang]

    # Og med rytme-uret nulstillet kommer pulsen — men stadig intet skift.
    monkeypatch.setattr(ap, "_LAST_RHYTHM_AT", None)
    _nulstil_og_fang.clear()
    ap.maybe_emit_phase_signal({"phase": "active"})
    assert [n for n, _ in _nulstil_og_fang] == ["runtime.ambient_presence_rhythm"]


def test_et_aegte_faseskift_giver_et_signal_med_etiket(_nulstil_og_fang):
    ap.maybe_emit_phase_signal({"phase": "active"})
    _nulstil_og_fang.clear()
    ap.maybe_emit_phase_signal({"phase": "dream"})
    assert len(_nulstil_og_fang) == 1
    navn, p = _nulstil_og_fang[0]
    assert navn == "runtime.ambient_presence_signal"
    assert p["kind"] == "dream"
    assert p["detail"], "skiftet skal baere en etiket, ikke et tomt felt"


def test_play_mode_vinder_over_et_samtidigt_faseskift(_nulstil_og_fang):
    """Begge ændrer sig i samme tick; kun ét signal maa ud."""
    ap.maybe_emit_phase_signal({"phase": "active", "play_mode": False})
    _nulstil_og_fang.clear()
    ap.maybe_emit_phase_signal({"phase": "dream", "play_mode": True})
    assert len(_nulstil_og_fang) == 1
    assert _nulstil_og_fang[0][1]["kind"] == "play_mode"


def test_FOERSTE_tick_giver_ikke_et_falsk_skift(_nulstil_og_fang):
    """`_LAST_PHASE` er None ved opstart. Talte det som «skift fra None»,
    ville hver genstart fyre et signal der ikke svarer til noget."""
    ap.maybe_emit_phase_signal({"phase": "dream"})
    assert [navn for navn, _ in _nulstil_og_fang] == ["runtime.ambient_presence_rhythm"]


# ── self-safe ───────────────────────────────────────────────────────────────

def test_en_doed_eventbus_vaelter_ikke_heartbeat(_nulstil_og_fang, monkeypatch):
    def _sprael(*a, **k):
        raise RuntimeError("bussen er nede")

    monkeypatch.setattr(ap.event_bus, "publish", _sprael)
    assert ap.emit_ambient_signal(kind="play_mode") is False
    assert ap.emit_presence_rhythm() is False
    ap.maybe_emit_phase_signal({"phase": "dream"})  # maa ikke kaste
    ap.emit_insight_signal("en indsigt")            # maa ikke kaste


def test_detaljen_afkortes_saa_en_lang_indsigt_ikke_fylder_bussen(_nulstil_og_fang):
    ap.emit_ambient_signal(kind="insight", detail="x" * 500)
    assert len(_nulstil_og_fang[0][1]["detail"]) == 80
