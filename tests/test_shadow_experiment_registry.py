"""Påmindelsen om modne skygge-eksperimenter — og hvorfor den tav to gange.

Modulet findes ordret fordi «BÅDE Bjørn og Claude glemmer at komme tilbage og
evaluere dem». Den blev selv glemt to gange:

1. **18/9-2026:** `tick_shadow_review_reminder` havde NUL kaldere. Fire
   eksperimenter stod modne i 65-71 dage. Rettet ved at hænge den på
   hjerteslaget: `_HEARTBEAT_TICK_COUNTER % 60 == 0`.
2. **2/10-2026:** den trigger kunne i praksis ikke fyre. Tælleren er en
   modul-global der nulstilles ved hver genstart, og hjerteslaget tikker målt
   ~9 gange på 6 timer — altså ~40 TIMER til 60 tik. Med tre genstarter på ét
   døgn nåede den aldrig derop. Otte eksperimenter stod forfaldne i op til 78
   dage, `event_trigger` med et 24-TIMERS vindue.

Og selv hvis den fyrede, gik den kun til `central().observe()`, som lander i en
2.000-pladsers deque i hukommelsen der dør ved næste genstart.

Rettelsen har to dele, og testene her måler dem begge: beslutningen ligger i en
DURABEL klokke (så en genstart ikke kan nulstille den, og to triggere ikke kan
påminde dobbelt), og beskeden går gennem daemon-vagten, så den faktisk ankommer
uden at kunne afbryde ham midt i en sætning.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from core.services import shadow_experiment_registry as reg

TIME = 1_700_000_000.0


@pytest.fixture
def kv(monkeypatch):
    """Et KV i hukommelsen, så testene ikke rører den rigtige base."""
    lager: dict[str, object] = {}

    class _DB:
        @staticmethod
        def get_runtime_state_value(key, default=None):
            return lager.get(key, default)

        @staticmethod
        def set_runtime_state_value(key, value):
            lager[key] = value

    import core.runtime.db_core as db_core
    monkeypatch.setattr(db_core, "get_runtime_state_value", _DB.get_runtime_state_value)
    monkeypatch.setattr(db_core, "set_runtime_state_value", _DB.set_runtime_state_value)
    return lager


@pytest.fixture
def sendte(monkeypatch):
    """Opsaml hvad der blev sendt gennem daemon-vagten."""
    ud: list[dict] = []
    import core.services.notification_bridge as nb
    monkeypatch.setattr(nb, "send_session_notification",
                        lambda tekst, **kw: ud.append({"tekst": tekst, **kw})
                        or {"status": "ok"})
    monkeypatch.setattr(nb, "delivery_succeeded", lambda r: True)
    return ud


def _modent(kv, *, navn="event_trigger", vindue=24.0, alder_timer=200.0):
    """Læg ét forfaldent eksperiment i KV."""
    kv["shadow_experiments"] = {
        navn: {"name": navn, "started_ts": TIME - alder_timer * 3600.0,
               "review_after_hours": vindue, "note": "proeve", "reviewed": False},
    }


def test_et_forfaldent_eksperiment_udloeser_en_besked(kv, sendte):
    """Kernen. Uden dette er registret en liste ingen læser."""
    _modent(kv)
    svar = reg.tick_shadow_review_reminder(now_ts=TIME)
    assert svar["notified"] is True, svar
    assert len(sendte) == 1, sendte
    assert "event_trigger" in sendte[0]["tekst"]
    assert sendte[0]["source"] == "shadow-review-due"


def test_beskeden_er_ikke_akut_og_pusher_ikke(kv, sendte):
    """Den må ikke bryde ind midt i en sætning, og den må ikke blive en ny
    daglig telefon-push — det var det Bjørn netop fik ryddet op i."""
    _modent(kv)
    reg.tick_shadow_review_reminder(now_ts=TIME)
    assert sendte[0].get("urgent", False) is False
    assert sendte[0].get("push") is False


def test_intet_modent_giver_ingen_besked(kv, sendte):
    """Et eksperiment inde i sit vindue er ikke forfaldent."""
    _modent(kv, vindue=500.0, alder_timer=10.0)
    svar = reg.tick_shadow_review_reminder(now_ts=TIME)
    assert svar["notified"] is False
    assert sendte == []


def test_klokken_er_DURABEL_saa_en_genstart_ikke_nulstiller_den(kv, sendte):
    """Fejlen fra 2/10: triggeren var `_HEARTBEAT_TICK_COUNTER % 60`, og den
    tæller nulstilles ved genstart. Klokken skal ligge i KV — altså overleve at
    modulet importeres forfra."""
    _modent(kv)
    assert reg.tick_shadow_review_reminder(now_ts=TIME)["notified"] is True
    assert "shadow_review_last_reminder" in kv, (
        "klokken blev ikke gemt durabelt — en genstart ville påminde igen straks"
    )
    # Genindlæs modulet: alle modul-globaler nulstilles, som ved en genstart.
    import importlib
    friskt = importlib.reload(reg)
    try:
        svar = friskt.tick_shadow_review_reminder(now_ts=TIME + 60.0)
        assert svar["notified"] is False, (
            "påmindte igen efter en genstart — klokken sad i hukommelsen"
        )
    finally:
        importlib.reload(reg)


def test_to_triggere_paaminder_ikke_dobbelt(kv, sendte):
    """Både hjerteslaget og det periodiske job kalder ticket. Beslutningen bor
    ÉT sted, så det andet kald skal tie."""
    _modent(kv)
    foerste = reg.tick_shadow_review_reminder(now_ts=TIME)
    anden = reg.tick_shadow_review_reminder(now_ts=TIME + 300.0)
    assert foerste["notified"] is True
    assert anden["notified"] is False, anden
    assert len(sendte) == 1, sendte


def test_den_paaminder_igen_naar_intervallet_er_gaaet(kv, sendte):
    """Ellers ville ét svar på ét døgn lukke munden på den for altid."""
    _modent(kv)
    reg.tick_shadow_review_reminder(now_ts=TIME)
    senere = TIME + reg.PAAMINDELSE_INTERVAL_TIMER * 3600.0 + 1.0
    assert reg.tick_shadow_review_reminder(now_ts=senere)["notified"] is True
    assert len(sendte) == 2


def test_beskeden_naevner_hvor_forfalden_og_hvor_man_ser_resten(kv, sendte):
    """«Noget er modent» er ikke handlingsanvisende. Et tal og en adresse er."""
    _modent(kv, vindue=24.0, alder_timer=24.0 + 78.0 * 24.0)
    reg.tick_shadow_review_reminder(now_ts=TIME)
    tekst = sendte[0]["tekst"]
    assert "78 dage forfalden" in tekst, tekst
    assert "/central/shadow-review" in tekst, tekst


def test_en_afvist_levering_stempler_IKKE_klokken(kv, monkeypatch):
    """Ellers ville en enkelt fejlet levering koste et helt døgns tavshed."""
    _modent(kv)
    import core.services.notification_bridge as nb
    monkeypatch.setattr(nb, "send_session_notification",
                        lambda t, **k: {"status": "blocked"})
    monkeypatch.setattr(nb, "delivery_succeeded", lambda r: False)
    svar = reg.tick_shadow_review_reminder(now_ts=TIME)
    assert svar["notified"] is False
    assert "shadow_review_last_reminder" not in kv, (
        "stemplede klokken på en afvist levering"
    )


def test_jobbet_er_KOBLET_til_den_durable_planlaegger():
    """En påmindelse ingen kalder er død kode — det var fejl nummer ét her.
    Kilde-vagt på begge ender: kadence OG handler."""
    kadence = pathlib.Path("core/services/periodic_jobs_scheduler.py").read_text()
    assert '"shadow_review_reminder"' in kadence, "ingen kadence for jobbet"

    bootstrap = pathlib.Path("core/services/governance_bootstrap.py").read_text()
    tree = ast.parse(bootstrap)
    navne = [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and n.value == "shadow_review_reminder"
    ]
    assert navne, "handleren er ikke registreret under sit jobnavn"
    assert "tick_shadow_review_reminder" in bootstrap, (
        "handleren kalder ikke ticket"
    )
