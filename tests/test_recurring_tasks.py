"""Tests for recurring_tasks channel-felt (notif-routing Phase 3)."""
from datetime import UTC, datetime, timedelta

import pytest
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()
    rt._ensure_table()


def test_channel_column_defaults_auto_and_set_channel(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="morgenbriefing", interval_minutes=1440)
    tid = t["task_id"]
    # default-kanal
    with db.connect() as c:
        ch = c.execute("SELECT channel FROM recurring_tasks WHERE task_id=?", (tid,)).fetchone()[0]
    assert ch == "auto"
    # sæt eksplicit kanal
    assert rt.set_channel(tid, "mobile") is True
    with db.connect() as c:
        ch = c.execute("SELECT channel FROM recurring_tasks WHERE task_id=?", (tid,)).fetchone()[0]
    assert ch == "mobile"


def test_set_channel_rejects_invalid(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        rt.set_channel("whatever", "smoke-signal")


def _minutter_til(iso: str) -> float:
    return (datetime.fromisoformat(iso) - datetime.now(UTC)).total_seconds() / 60


def test_delay_minutes_slaar_intervallet_for_foerste_affyring(tmp_path, monkeypatch):
    """Regression 18/9-2026: en eksplicit kort forsinkelse blev slugt af intervallet.

    Foer: ``first_fire = now + max(delay_minutes, interval_minutes)``. Satte man
    interval=365 dage for at lave en engangs-paamindelse og delay=13 dage, vandt
    intervallet — og foerste affyring landede ET AAR ude i fremtiden. Maalt i
    produktion da en moede-paamindelse blev sat til 2027 i stedet for 1. oktober.
    """
    _fresh(tmp_path, monkeypatch)
    # 365 dage interval (engangs-brug), 13 dages eksplicit forsinkelse.
    t = rt.create_recurring_task(
        focus="engangs-paamindelse", interval_minutes=525600, delay_minutes=19158
    )
    delta = _minutter_til(t["next_fire_at"])
    assert 19150 < delta < 19170, f"forventede ~19158 min, fik {delta:.0f}"


def test_delay_nul_giver_uaendret_foerste_affyring_efter_et_interval(tmp_path, monkeypatch):
    """Bagudkompatibilitet: delay=0 (alle eksisterende tasks) = efter ét interval."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="daglig", interval_minutes=1440)
    delta = _minutter_til(t["next_fire_at"])
    assert 1435 < delta < 1445, f"forventede ~1440 min, fik {delta:.0f}"


# ── Ugedage ───────────────────────────────────────────────────────────────────
# Bjoern 28/9-2026: «begraens medicin-paamindelserne til hverdage». Foer denne
# dag fandtes der ingen ugedags-begreb i planlaeggeren: en daglig opgave fyrede
# alle ugens dage, ogsaa loerdag og soendag.


def test_weekdays_default_er_alle_dage(tmp_path, monkeypatch):
    """Bagudkompatibilitet: en raekke uden ugedage fyrer som foer."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="daglig", interval_minutes=1440)
    with db.connect() as c:
        ud = c.execute(
            "SELECT weekdays FROM recurring_tasks WHERE task_id=?", (t["task_id"],)
        ).fetchone()[0]
    assert ud == ""


def test_parse_weekdays_tager_det_man_skriver():
    assert rt.parse_weekdays("man-fre") == "1,2,3,4,5"
    assert rt.parse_weekdays("1,2,3,4,5") == "1,2,3,4,5"
    assert rt.parse_weekdays("mon,wed,fri") == "1,3,5"
    assert rt.parse_weekdays("weekend") == "6,7"
    assert rt.parse_weekdays("alle") == ""
    assert rt.parse_weekdays("") == ""
    assert rt.parse_weekdays(None) == ""


def test_parse_weekdays_kaster_paa_tastefejl():
    """En tastefejl maa ikke TAVST blive til «alle dage» — saa fyrer
    paamindelsen i weekenden alligevel, og fejlen er usynlig for alle."""
    with pytest.raises(ValueError):
        rt.parse_weekdays("torsdagsagtigt")
    with pytest.raises(ValueError):
        rt.parse_weekdays("9")


def test_naeste_tid_springer_weekenden_over():
    """Fredag -> naeste bliver loerdag. Loerdag er ikke en hverdag, saa den
    skal videre til mandag — og klokkeslaettet skal staa stille imens."""
    fredag = datetime(2026, 10, 2, 4, 15, tzinfo=UTC)
    assert fredag.isoweekday() == 5
    naeste = rt._naeste_tid(
        fredag.isoformat(), 1440, fredag + timedelta(days=1), {1, 2, 3, 4, 5}
    )
    assert naeste.isoweekday() == 1
    assert (naeste.hour, naeste.minute) == (4, 15)


def test_uden_ugedage_er_naeste_tid_uaendret():
    """Vagten maa ikke roere opgaver der fyrer alle dage.

    Uden ugedage lander naeste paa SOENDAG, ikke loerdag: `_naeste_tid` springer
    frem i hele intervaller til et tidspunkt der ligger i fremtiden, saa fra
    fredag bliver det fredag + to doegn. Det er den gamle opfoersel — og praecis
    den vagten ikke maa aendre.
    """
    fredag = datetime(2026, 10, 2, 4, 15, tzinfo=UTC)
    naeste = rt._naeste_tid(fredag.isoformat(), 1440, fredag + timedelta(days=1))
    assert naeste.isoweekday() == 7


def test_ugedags_opgave_fyrer_IKKE_paa_en_dag_den_ikke_har_valgt(tmp_path, monkeypatch):
    """Selve fejlen Bjoern bad om at undgaa: en paamindelse der fyrer loerdag
    fordi maskinen var nede fredag. Ugedagene vaelges som «alle undtagen i dag»,
    saa vagten med sikkerhed skal slaa til uanset hvornaar testen koeres."""
    _fresh(tmp_path, monkeypatch)
    kaldt: list[dict] = []
    import core.services.visible_runs as vr
    monkeypatch.setattr(vr, "start_autonomous_run", lambda **kw: kaldt.append(kw))

    nu = datetime.now(UTC)
    andre = ",".join(str(d) for d in range(1, 8) if d != nu.isoweekday())
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440, weekdays=andre)
    # Tving den forfalden.
    with db.connect() as c:
        c.execute("UPDATE recurring_tasks SET next_fire_at=? WHERE task_id=?",
                  ((nu - timedelta(days=1)).replace(hour=6, minute=15, second=0,
                                                    microsecond=0).isoformat(),
                   t["task_id"]))
        c.commit()

    rt._fire_due()

    assert kaldt == [], "en opgave fyrede paa en ugedag den ikke havde valgt"
    with db.connect() as c:
        nf = c.execute("SELECT next_fire_at FROM recurring_tasks WHERE task_id=?",
                       (t["task_id"],)).fetchone()[0]
    naeste = datetime.fromisoformat(nf)
    assert str(naeste.isoweekday()) in andre.split(",")
    assert (naeste.hour, naeste.minute) == (6, 15), "klokkeslaettet flyttede sig"


def test_ugedags_opgave_fyrer_naar_dagen_ER_valgt(tmp_path, monkeypatch):
    """Det modsatte maa ogsaa gaelde — ellers var «begraens» bare «sluk»."""
    _fresh(tmp_path, monkeypatch)
    kaldt: list[dict] = []
    import core.services.visible_runs as vr
    monkeypatch.setattr(vr, "start_autonomous_run", lambda **kw: kaldt.append(kw))

    nu = datetime.now(UTC)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440,
                                 weekdays=str(nu.isoweekday()))
    with db.connect() as c:
        c.execute("UPDATE recurring_tasks SET next_fire_at=? WHERE task_id=?",
                  ((nu - timedelta(minutes=5)).isoformat(), t["task_id"]))
        c.commit()

    rt._fire_due()

    assert len(kaldt) == 1, "en opgave paa en valgt ugedag fyrede ikke"


def test_set_weekdays_rammer_kun_fremad(tmp_path, monkeypatch):
    """Den planlagte tid staar hvor den staar — at saette ugedage maa ikke
    rykke klokkeslaettet. Det er naeste _advance der springer udenom."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440)
    foer = t["next_fire_at"]
    assert rt.set_weekdays(t["task_id"], "man-fre") is True
    with db.connect() as c:
        r = c.execute("SELECT weekdays, next_fire_at FROM recurring_tasks WHERE task_id=?",
                      (t["task_id"],)).fetchone()
    assert r[0] == "1,2,3,4,5"
    assert r[1] == foer


def test_ukendt_ugedag_efterlader_raekken_uaendret(tmp_path, monkeypatch):
    """Fejler kaldet, maa raekken ikke staa halvt aendret."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440)
    with pytest.raises(ValueError):
        rt.set_weekdays(t["task_id"], "torsdagsagtigt")
    with db.connect() as c:
        ud = c.execute("SELECT weekdays FROM recurring_tasks WHERE task_id=?",
                       (t["task_id"],)).fetchone()[0]
    assert ud == ""


# ── Indbakke-flag (15/10-2026) ───────────────────────────────────────────────

def test_inbox_flag_default_er_0(tmp_path, monkeypatch):
    """Raekker fra foer kolonnen har flaget 0 — uaendret adfaerd."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440)
    assert t["inbox_on_complete"] == 0
    assert rt.skal_i_indbakken(t["task_id"]) is False


def test_set_inbox_on_complete_taender_og_slaar_fra(tmp_path, monkeypatch):
    """Flaget er sandheden i DB — det SLAAS OP, det gaettes ikke."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="inspektion", interval_minutes=360)
    assert rt.set_inbox_on_complete(t["task_id"], True) is True
    assert rt.skal_i_indbakken(t["task_id"]) is True
    assert rt.set_inbox_on_complete(t["task_id"], False) is True
    assert rt.skal_i_indbakken(t["task_id"]) is False


def test_create_med_flag_saetter_det_ved_foedslen(tmp_path, monkeypatch):
    """Opgaven kan oprettes med levering fra start — ikke kun efter et set."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="arkiv", interval_minutes=1440,
                                 inbox_on_complete=True)
    assert t["inbox_on_complete"] == 1
    assert rt.skal_i_indbakken(t["task_id"]) is True


def test_ukendt_task_id_svarer_false(tmp_path, monkeypatch):
    """Fail-soft: en ukendt/slettet opgave maa ikke vaelte opslaget."""
    _fresh(tmp_path, monkeypatch)
    assert rt.skal_i_indbakken("rec-findes-ikke") is False
    assert rt.skal_i_indbakken("") is False
    assert rt.set_inbox_on_complete("rec-findes-ikke", True) is False


def test_flaget_overlever_en_ugedags_affyring(tmp_path, monkeypatch):
    """Flaget hoerer paa raekken — ugedags-gaten maa ikke røre det."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="arkiv", interval_minutes=1440,
                                 weekdays="man-fre")
    rt.set_inbox_on_complete(t["task_id"], True)
    rt.set_weekdays(t["task_id"], "1,2,3")
    assert rt.skal_i_indbakken(t["task_id"]) is True


# ── focus-graensen klippede tavst (15/10-2026) ──────────────────────────────
#
# `focus` er ikke en titel. Den bliver BRUGERBESKEDEN til det autonome run
# (`start_autonomous_run(message=focus)`), altsaa selve instruktionen. Den
# gamle linje `focus[:300]` klippede uden et ord: natrutinens instruktion stod
# med praecis 300 tegn og sluttede midt i "4. **recall", saa source-linjen laa
# efter graensen og blev aldrig laest.

def test_focus_paa_301_tegn_kommer_hel_igennem(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    instruktion = "x" * 301
    t = rt.create_recurring_task(focus=instruktion, interval_minutes=1440)
    assert len(t["focus"]) == 301
    with db.connect() as c:
        gemt = c.execute(
            "SELECT focus FROM recurring_tasks WHERE task_id=?", (t["task_id"],)
        ).fetchone()[0]
    assert gemt == instruktion


def test_focus_over_graensen_klippes_men_logges(tmp_path, monkeypatch, caplog):
    _fresh(tmp_path, monkeypatch)
    instruktion = "y" * (rt._FOCUS_MAX + 50)
    with caplog.at_level("WARNING", logger="core.services.recurring_tasks"):
        t = rt.create_recurring_task(focus=instruktion, interval_minutes=1440)
    assert len(t["focus"]) == rt._FOCUS_MAX
    assert any("klippet" in r.message for r in caplog.records)


# ── Ejerbevis (19/10-2026) ───────────────────────────────────────────────────
# Routine-migrationen kraever et STRUKTURERET ejerbevis for at flytte en
# opgave. `recurring_tasks` havde ingen saadan kolonne, saa alle 13 levende
# opgaver faldt i karantaene med `missing_structured_owner`. Disse tests
# vogter baade at kolonnen findes OG at den ikke giver ejerskab af sig selv.


def test_verified_owner_defaults_tomt_og_giver_ikke_ejerskab(tmp_path, monkeypatch):
    """En ny opgave maa IKKE kunne migreres: tomt bevis = ingen ejer."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="inspektion", interval_minutes=360)
    with db.connect() as c:
        v = c.execute(
            "SELECT verified_owner_user_id FROM recurring_tasks WHERE task_id=?",
            (t["task_id"],),
        ).fetchone()[0]
    assert v == ""

    from core.services.routine_migration import _classify

    owner, reason, evidence = _classify({
        "source_kind": "recurring",
        "task_id": t["task_id"],
        "user_id": "",                 # ingen skaber heller
        "verified_owner_user_id": "",  # intet bevis
        "focus": "inspektion",
    })
    assert owner is None
    assert reason == "missing_structured_owner"
    assert "no_authoritative_recipient" in evidence


def test_set_verified_owner_skriver_og_afviser_tomt(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="arkiv", interval_minutes=1440)
    tid = t["task_id"]

    assert rt.set_verified_owner(tid, "canonical-user") is True
    with db.connect() as c:
        v = c.execute(
            "SELECT verified_owner_user_id FROM recurring_tasks WHERE task_id=?", (tid,),
        ).fetchone()[0]
    assert v == "canonical-user"

    with pytest.raises(ValueError):
        rt.set_verified_owner(tid, "   ")


def test_migrationen_laeser_kolonnen_naar_den_findes(tmp_path, monkeypatch):
    """Ledningen skal vaere forbundet: `_source_rows` skal baere beviset med."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="arkiv", interval_minutes=1440)
    rt.set_verified_owner(t["task_id"], "canonical-user")

    from core.runtime.db_core import connect
    from core.services.routine_migration import _source_rows

    with connect() as c:
        rows = [r for r in _source_rows(c) if r["source_kind"] == "recurring"]
    assert rows, "migrationen fandt ingen recurring-raekker"
    assert rows[0]["verified_owner_user_id"] == "canonical-user"
