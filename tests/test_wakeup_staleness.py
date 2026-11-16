"""Mærkningen oplyser — den beslutter ikke.

Bjørn 16/11-2026: «Ikke afbestil. Mærk. [...] mekanismen må gerne oplyse mig.
Den må ikke beslutte for mig når beslutningen kan tabe arbejde.»

Anledningen var målt samme dag: en vækning booket 15/11 kl. 16:40 med 24 timers
forsinkelse fyrede om en sag der var afgjort få timer efter bookingen. Posten
var sund; den pegede bare på et verdensbillede der ikke fandtes længere.

Testene værner tre ting, i den rækkefølge de betyder noget:

1. **Den kan ikke skrive.** `_save` er patch'et til at kaste, så enhver
   skrivevej — inklusive en fremtidig «hjælpsom» auto-afbestilling — fældes.
2. **Den fejler mod behold.** En post der ikke kan dateres, eller hvis kilder
   ikke kan læses, får INGEN mærkning og fyrer som den plejer.
3. **Den siger hvad den ved.** Alder, lukket side-opgave og «samtalen kom
   videre» står i teksten med tidspunkt — ellers er mærkningen selv gætteri.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import self_wakeup, wakeup_staleness


def _post(**kw) -> dict:
    grund = {
        "wakeup_id": "wake-test",
        "prompt": "Tjek om blæser-fixet virkede",
        "reason": "test",
        "status": "fired",
        "session_id": "chat-test",
        "scheduled_at": "2026-11-15T16:40:00+00:00",
        "fire_at": "2026-11-16T16:40:00+00:00",
    }
    grund.update(kw)
    return grund


@pytest.fixture
def ingen_skrivning(monkeypatch):
    """Enhver skrivevej i wakeup-lageret kaster — så kan den ikke snige sig ind."""

    def _nej(*a, **k):
        raise AssertionError("wakeup_staleness må ikke skrive til lageret")

    monkeypatch.setattr(self_wakeup, "_save", _nej)
    monkeypatch.setattr(self_wakeup, "cancel_wakeup", _nej)
    monkeypatch.setattr(self_wakeup, "mark_wakeup_consumed", _nej)


@pytest.fixture
def ingen_kilder(monkeypatch):
    """Alle tre kilder svarer «ved det ikke» — så testes alder-reglen alene."""
    monkeypatch.setattr(wakeup_staleness, "_side_opgave_fakta", lambda r: None)
    monkeypatch.setattr(wakeup_staleness, "_senere_post_fakta", lambda r: None)
    monkeypatch.setattr(wakeup_staleness, "_samtale_fakta", lambda r: None)


@pytest.fixture
def ét_faktum(monkeypatch):
    """Præcis ét faktum — så en skrivevej der gater på «der er fakta» NÅS.

    Målt 16/11-2026: den første version af `test_maerkning_skriver_intet` brugte
    `ingen_kilder`, så `fakta` var tom, og en indsat auto-afbestilling blev
    aldrig kaldt. Testen var grøn af den forkerte grund — en vagt der ikke kan
    nå den gren den værner, beviser intet om den.
    """
    monkeypatch.setattr(wakeup_staleness, "_side_opgave_fakta", lambda r: "Et faktum.")
    monkeypatch.setattr(wakeup_staleness, "_senere_post_fakta", lambda r: None)
    monkeypatch.setattr(wakeup_staleness, "_samtale_fakta", lambda r: None)


# ── 1. Den kan ikke skrive ────────────────────────────────────────────────


def test_maerkning_skriver_intet(ingen_skrivning, ét_faktum):
    """Kernen i Bjørns form: oplys, afbestil ikke."""
    post = _post()
    foer = dict(post)
    tekst = wakeup_staleness.maerk(post, nu=datetime(2026, 11, 16, 17, 0, tzinfo=UTC))
    assert tekst is not None
    assert "Et faktum." in tekst
    assert post == foer, "posten blev muteret — mærkningen må kun læse"


def test_posten_bliver_staaende_som_fired(ingen_skrivning, ét_faktum):
    """En mærket post skal stadig fyre. Mærkning er ikke en afbestilling."""
    post = _post()
    wakeup_staleness.maerk(post, nu=datetime(2026, 11, 16, 17, 0, tzinfo=UTC))
    assert post["status"] == "fired"


# ── 2. Den fejler mod behold ──────────────────────────────────────────────


def test_uden_bookningstid_ingen_maerkning(ingen_kilder):
    """Kan posten ikke dateres, kan vi ikke sige hvad der er sket siden."""
    post = _post(scheduled_at=None)
    assert wakeup_staleness.maerk(post, nu=datetime(2026, 11, 16, 17, 0, tzinfo=UTC)) is None


def test_ulaeselig_bookningstid_ingen_maerkning(ingen_kilder):
    post = _post(scheduled_at="i går engang")
    assert wakeup_staleness.maerk(post, nu=datetime(2026, 11, 16, 17, 0, tzinfo=UTC)) is None


def test_frisk_post_uden_fakta_bliver_umaerket(ingen_kilder):
    """Booket 5 minutter før: samme arbejdsgang, intet at advare om.

    Målt 16/11-2026: 65 af 69 poster havde under en times forsinkelse. Uden
    denne grænse ville hver eneste korte kontrol få en advarsel — og så
    lærer jeg at overse den.
    """
    post = _post(
        scheduled_at="2026-11-16T16:55:00+00:00",
        fire_at="2026-11-16T17:00:00+00:00",
    )
    assert wakeup_staleness.maerk(post, nu=datetime(2026, 11, 16, 17, 0, tzinfo=UTC)) is None


def test_doed_kilde_draeber_ikke_maerkningen(ingen_skrivning, monkeypatch):
    """Én utilgængelig kilde må ikke gøre hele mærkningen tavs."""
    monkeypatch.setattr(wakeup_staleness, "_side_opgave_fakta", lambda r: None)
    monkeypatch.setattr(wakeup_staleness, "_senere_post_fakta", lambda r: None)
    monkeypatch.setattr(wakeup_staleness, "_samtale_fakta", lambda r: None)
    tekst = wakeup_staleness.maerk(_post(), nu=datetime(2026, 11, 16, 17, 0, tzinfo=UTC))
    assert tekst is not None
    assert "MULIGVIS FORÆLDET" in tekst


# ── 3. Den siger hvad den ved ─────────────────────────────────────────────


def test_gammel_post_baerer_alderen(ingen_kilder):
    """24 timer gammel: alderen ER faktum, og den skal stå der."""
    tekst = wakeup_staleness.maerk(_post(), nu=datetime(2026, 11, 16, 16, 40, tzinfo=UTC))
    assert tekst is not None
    assert "24 timer" in tekst
    assert "15/11" in tekst  # booket-tidspunktet i dansk tid


def test_lukket_side_opgave_nævnes_med_tid(ingen_kilder, monkeypatch):
    """Bjørns eget eksempel: «sagen blev lukket 15/11 kl. 17:44»."""
    monkeypatch.setattr(
        wakeup_staleness,
        "_side_opgave_fakta",
        lambda r: "Side-opgaven side-abc blev lukket 15/11 17:44 (completed).",
    )
    tekst = wakeup_staleness.maerk(_post(), nu=datetime(2026, 11, 16, 17, 0, tzinfo=UTC))
    assert tekst is not None
    assert "side-abc" in tekst
    assert "17:44" in tekst


def test_åben_side_opgave_nævnes_ikke_som_lukket(ingen_kilder, monkeypatch):
    """En post der stadig er åben er ikke et bevis for at sagen er afgjort."""
    monkeypatch.setattr(
        "core.services.side_tasks.get",
        lambda sid: {"side_task_id": sid, "status": "pending"},
    )
    tekst = wakeup_staleness._side_opgave_fakta(_post(task_id="side-abc"))
    assert tekst is None


def test_lukket_side_opgave_læses_fra_lageret(monkeypatch):
    monkeypatch.setattr(
        "core.services.side_tasks.get",
        lambda sid: {
            "side_task_id": sid,
            "status": "dismissed",
            "resolved_at": "2026-11-15T16:44:00+00:00",
        },
    )
    tekst = wakeup_staleness._side_opgave_fakta(_post(task_id="side-abc"))
    assert tekst is not None
    assert "dismissed" in tekst
    assert "17:44" in tekst  # 16:44 UTC = 17:44 dansk (CET)


def test_senere_afviklet_post_om_samme_sag(monkeypatch):
    """En nyere post med samme indhold der allerede er afviklet."""
    monkeypatch.setattr(
        "core.services.self_wakeup.list_wakeups",
        lambda **kw: [
            {
                "wakeup_id": "wake-ny",
                "prompt": "TJEK om blæser-fixet virkede!",
                "status": "consumed",
                "consumed_at": "2026-11-16T12:00:00+00:00",
            }
        ],
    )
    tekst = wakeup_staleness._senere_post_fakta(_post())
    assert tekst is not None
    assert "13:00" in tekst  # 12:00 UTC = 13:00 dansk


def test_ældre_afviklet_post_tæller_ikke(monkeypatch):
    """Kun en post der kom EFTER bookingen siger noget om mellemtiden."""
    monkeypatch.setattr(
        "core.services.self_wakeup.list_wakeups",
        lambda **kw: [
            {
                "wakeup_id": "wake-gammel",
                "prompt": "Tjek om blæser-fixet virkede",
                "status": "consumed",
                "consumed_at": "2026-11-15T10:00:00+00:00",
            }
        ],
    )
    assert wakeup_staleness._senere_post_fakta(_post()) is None


def test_samtalen_kom_videre_tælles(monkeypatch):
    """Samme regel som stop-fixet: tilstanden afgør, ikke et flag."""

    class _FalskConn:
        def execute(self, sql, params):
            assert "chat_messages" in sql
            assert params[0] == "chat-test"

            class _R:
                def fetchone(self):
                    return (14,)

            return _R()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("core.runtime.db_core.connect", lambda: _FalskConn())
    tekst = wakeup_staleness._samtale_fakta(_post())
    assert tekst is not None
    assert "14" in tekst


def test_ingen_ture_siden_giver_intet_faktum(monkeypatch):
    class _FalskConn:
        def execute(self, sql, params):
            class _R:
                def fetchone(self):
                    return (0,)

            return _R()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("core.runtime.db_core.connect", lambda: _FalskConn())
    assert wakeup_staleness._samtale_fakta(_post()) is None


# ── 4. Den lander i den faktiske tekst ────────────────────────────────────


def test_maerkningen_lander_i_direktivet(ingen_skrivning, ingen_kilder):
    """Ende-til-ende: blokken skal stå i den tekst Jarvis faktisk får.

    En mærkning der kan formateres men aldrig når modellen er den teater-fejl
    Bjørn jager: mekanismen ser ud som om den virker, fordi den skriver noget.
    `direktiv_for` er eneste indgang for BÅDE dispatcheren og
    indbakke-vækkeren — så testen her dækker begge veje.
    """
    post = _post()
    post["scheduled_at"] = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    tekst = self_wakeup.direktiv_for(post)
    assert "MULIGVIS FORÆLDET" in tekst
    assert "Præmissen er IKKE efterprøvet" in tekst
    assert "[SELF-WAKEUP FIRED" in tekst  # den oprindelige ordre er stadig der


def test_frisk_post_faar_intet_flag_i_direktivet(ingen_skrivning, ingen_kilder):
    """Modsatte retning: en frisk post skal ikke støjes."""
    post = _post(scheduled_at=datetime.now(UTC).isoformat())
    tekst = self_wakeup.direktiv_for(post)
    assert "MULIGVIS FORÆLDET" not in tekst
    assert "[SELF-WAKEUP FIRED" in tekst


def test_maerkningsfejl_vaelter_ikke_fyringen(monkeypatch):
    """Kan mærkningen ikke bygges, skal vækningen fyre alligevel."""

    def _kaster(r):
        raise RuntimeError("kilden er nede")

    monkeypatch.setattr(wakeup_staleness, "maerk", _kaster)
    tekst = self_wakeup.direktiv_for(_post())
    assert "[SELF-WAKEUP FIRED" in tekst
    assert "Tjek om blæser-fixet virkede" in tekst
