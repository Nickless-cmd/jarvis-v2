"""Forskelligt klokkeslæt pr. ugedag på en recurring task.

Baggrund (1/11-2026): Bjørn bad om morgenbrief + morgenmedicin samlet, sendt
06:15 på hverdage og 07:30 i weekenden. Skemaet kunne kun ÉT klokkeslæt:
``interval_minutes`` bevarer tidspunktet på dagen, og ``weekdays`` filtrerer
kun hvilke dage der må fyre. To tider krævede enten to opgaver med duplikeret
tekst — som driver fra hinanden — eller en ny kolonne.

Løsningen er ``weekday_times``: en JSON-kolonne med klokkeslæt pr. ugedag i
DANSK tid. Dansk tid er ikke en detalje: gemte man UTC, ville klokken flytte
sig en time ved sommertidsskiftet, og en påmindelse sat til 06:15 ville en dag
fyre 05:15.
"""
from datetime import UTC, datetime

import pytest

import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt
from core.util.timezone import DK_ZONE


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()
    rt._ensure_table()


def _dansk(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(DK_ZONE)


def _utc(dansk_iso: str) -> datetime:
    """'2026-11-02 06:15' i dansk tid -> aware UTC-datetime."""
    return datetime.fromisoformat(dansk_iso).replace(tzinfo=DK_ZONE).astimezone(UTC)


# ── Parsing og lagring ───────────────────────────────────────────────────────

def test_set_weekday_times_gemmer_og_læser_tilbage(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="morgen", interval_minutes=1440)
    tid = t["task_id"]

    assert rt.set_weekday_times(tid, {"man-fre": "06:15", "weekend": "07:30"}) is True

    with db.connect() as c:
        raw = c.execute(
            "SELECT weekday_times FROM recurring_tasks WHERE task_id=?", (tid,)
        ).fetchone()[0]
    # Normaliseret til ISO-ugedage — ikke den rå streng brugeren skrev.
    assert raw == '{"1": "06:15", "2": "06:15", "3": "06:15", "4": "06:15", "5": "06:15", "6": "07:30", "7": "07:30"}'


def test_tom_spec_nulstiller_og_giver_alle_dage_uaendret(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="morgen", interval_minutes=1440)
    tid = t["task_id"]
    rt.set_weekday_times(tid, {"man-fre": "06:15"})
    assert rt.set_weekday_times(tid, {}) is True
    with db.connect() as c:
        raw = c.execute(
            "SELECT weekday_times FROM recurring_tasks WHERE task_id=?", (tid,)
        ).fetchone()[0]
    assert raw == ""


def test_ugyldigt_klokkeslaet_kaster(tmp_path, monkeypatch):
    """En tastefejl må ikke tavst blive til «ingen tid» — så fyrer opgaven forkert."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="morgen", interval_minutes=1440)
    with pytest.raises(ValueError):
        rt.set_weekday_times(t["task_id"], {"man-fre": "25:99"})
    with pytest.raises(ValueError):
        rt.set_weekday_times(t["task_id"], {"man-fre": "klokken seks"})


# ── Tidsberegningen: den faktiske adfærd ─────────────────────────────────────

def test_naeste_tid_uden_weekday_times_er_uaendret(tmp_path, monkeypatch):
    """Bagudkompatibilitet: 13 levende opgaver har ingen weekday_times.

    Uden denne vagt kunne ændringen flytte klokkeslættet på ALT der kører i
    dag — og fejlen ville først vise sig som en manglende påmindelse.
    """
    planlagt = _utc("2026-11-02 06:15").isoformat()
    now = _utc("2026-11-02 07:00")
    naeste = rt._naeste_tid(planlagt, 1440, now)
    assert _dansk(naeste.isoformat()).strftime("%Y-%m-%d %H:%M") == "2026-11-03 06:15"


def test_hverdag_til_hverdag_beholder_0615(tmp_path, monkeypatch):
    tider = {1: (6, 15), 2: (6, 15), 3: (6, 15), 4: (6, 15), 5: (6, 15),
             6: (7, 30), 7: (7, 30)}
    planlagt = _utc("2026-11-02 06:15").isoformat()  # mandag
    now = _utc("2026-11-02 07:00")
    naeste = rt._naeste_tid(planlagt, 1440, now, None, tider)
    assert _dansk(naeste.isoformat()).strftime("%Y-%m-%d %H:%M") == "2026-11-03 06:15"


def test_fredag_til_loerdag_skifter_til_0730(tmp_path, monkeypatch):
    """Kernen i ønsket: weekenden får et ANDET klokkeslæt, ikke samme."""
    tider = {1: (6, 15), 2: (6, 15), 3: (6, 15), 4: (6, 15), 5: (6, 15),
             6: (7, 30), 7: (7, 30)}
    planlagt = _utc("2026-11-06 06:15").isoformat()  # fredag
    now = _utc("2026-11-06 07:00")
    naeste = rt._naeste_tid(planlagt, 1440, now, None, tider)
    assert _dansk(naeste.isoformat()).strftime("%Y-%m-%d %H:%M") == "2026-11-07 07:30"


def test_soendag_til_mandag_skifter_tilbage_til_0615(tmp_path, monkeypatch):
    tider = {1: (6, 15), 2: (6, 15), 3: (6, 15), 4: (6, 15), 5: (6, 15),
             6: (7, 30), 7: (7, 30)}
    planlagt = _utc("2026-11-08 07:30").isoformat()  # søndag
    now = _utc("2026-11-08 08:00")
    naeste = rt._naeste_tid(planlagt, 1440, now, None, tider)
    assert _dansk(naeste.isoformat()).strftime("%Y-%m-%d %H:%M") == "2026-11-09 06:15"


def test_sommertid_flytter_ikke_klokken_i_dansk_tid(tmp_path, monkeypatch):
    """Fælden: gemte man UTC, ville 06:15 blive 05:15 efter et skift.

    Juli er CEST (UTC+2), januar er CET (UTC+1). Klokkeslættet i dansk tid
    skal være 06:15 i BEGGE tilfælde, selv om UTC-timen er forskellig.
    """
    tider = {d: (6, 15) for d in range(1, 8)}

    sommer = rt._naeste_tid(
        _utc("2026-07-06 06:15").isoformat(), 1440, _utc("2026-07-06 07:00"), None, tider
    )
    vinter = rt._naeste_tid(
        _utc("2026-01-05 06:15").isoformat(), 1440, _utc("2026-01-05 07:00"), None, tider
    )
    assert _dansk(sommer.isoformat()).strftime("%H:%M") == "06:15"
    assert _dansk(vinter.isoformat()).strftime("%H:%M") == "06:15"
    # Og UTC-timen ER forskellig — ellers målte testen ingenting.
    assert sommer.hour != vinter.hour


def test_naeste_tid_landet_i_fortiden_rykker_en_dag_mere(tmp_path, monkeypatch):
    """Den farlige gren: 07:30 søndag -> 06:15 mandag kan ligge FØR 'now'.

    Uden dette led ville opgaven blive forfalden i samme sekund den blev
    rykket frem, og fyre en ekstra gang.
    """
    tider = {1: (6, 15), 2: (6, 15), 3: (6, 15), 4: (6, 15), 5: (6, 15),
             6: (7, 30), 7: (7, 30)}
    # Søndag aften — næste planlagte er mandag 07:30 (interval bevarer tiden),
    # men mandag skal fyre 06:15, som allerede er passeret kl. 08:00 søndag? Nej:
    # vi sætter now til MANDAG 06:20, altså efter dagens 06:15.
    planlagt = _utc("2026-11-08 07:30").isoformat()  # søndag
    now = _utc("2026-11-09 06:20")  # mandag, 5 min efter dagens tid
    naeste = rt._naeste_tid(planlagt, 1440, now, None, tider)
    assert _dansk(naeste.isoformat()).strftime("%Y-%m-%d %H:%M") == "2026-11-10 06:15"


def test_weekdays_og_weekday_times_spiller_sammen(tmp_path, monkeypatch):
    """En hverdagsoppgave må ikke få en weekend-tid den ikke fyrer på."""
    tider = {1: (6, 15), 2: (6, 15), 3: (6, 15), 4: (6, 15), 5: (6, 15),
             6: (7, 30), 7: (7, 30)}
    planlagt = _utc("2026-11-06 06:15").isoformat()  # fredag
    now = _utc("2026-11-06 07:00")
    naeste = rt._naeste_tid(planlagt, 1440, now, {1, 2, 3, 4, 5}, tider)
    # Fredag -> weekenden springes over -> mandag 06:15
    assert _dansk(naeste.isoformat()).strftime("%Y-%m-%d %H:%M") == "2026-11-09 06:15"


def test_hele_kaeden_fra_gemt_plan_til_beregning(tmp_path, monkeypatch):
    """DB -> ``_weekday_tider`` -> ``_naeste_tid``. Den gren ingen anden test ser.

    MÅLT 1/11-2026: mutationen «``_weekday_tider`` returnerer altid ``{}``»
    overlevede alle 10 tests. Grunden er at de øvrige tests sender planen
    direkte som parameter — så en plan der aldrig blev læst ud af DB'en ville
    bestå dem alle. Koden ville se ud som om den virkede, og tiden ville aldrig
    flytte sig i drift.
    """
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="morgen", interval_minutes=1440)
    tid = t["task_id"]
    rt.set_weekday_times(tid, {"man-fre": "06:15", "weekend": "07:30"})

    row = rt._get_one(tid)
    plan = rt._weekday_tider(row["weekday_times"])
    assert plan[1] == (6, 15)
    assert plan[6] == (7, 30)

    planlagt = _utc("2026-11-06 06:15").isoformat()  # fredag
    naeste = rt._naeste_tid(
        planlagt, 1440, _utc("2026-11-06 07:00"),
        rt._ugedage(row["weekdays"]), plan,
    )
    assert _dansk(naeste.isoformat()).strftime("%Y-%m-%d %H:%M") == "2026-11-07 07:30"
