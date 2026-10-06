"""Baggrundsjob-vagten: ét faerdigt job, én melding, den rigtige vej.

Vigtigst her er `test_koldstart_melder_INTET` og
`test_bro_der_tier_markerer_intet`. Begge daekker et udfald hvor det RIGTIGE
er at tie, og hvor en naiv implementering goer skade: en byge af gamle jobs
ved deploy, eller et tabt job fordi en doed bro blev laest som «ingen jobs».
"""

from __future__ import annotations

import pytest

from core.services import baggrundsjob_vagt as V


def _job(jid: str, *, status: str = "exited", kode: int | None = 0,
         sek: int = 90, kommando: str = "npm run build", titel: str = "") -> dict:
    """Samme form som `background_jobs._operator_jobs` producerer.

    `navn` beregnes som DÉR (`titel or kommando or fallback`) og saettes ALDRIG
    til job-id'et: en melding der sagde «bg_ny er faerdig» ville vaere ulaeselig,
    og en fixture der opfinder sin egen form kan ikke fange det
    ([[pin_feltnavne_mod_produktion]]).
    """
    return {"id": jid, "kilde": "operator",
            "navn": titel or kommando or "(baggrunds-shell)",
            "titel": titel, "kommando": kommando,
            "status": status, "pid": 1234, "sekunder": sek, "exit_code": kode}


@pytest.fixture
def rig(monkeypatch, tmp_path, isolated_runtime):
    """Ejer, bro og leverings-veje — alle som soemme testen styrer.

    `state_store._STATE_DIR` saettes EKSPLICIT. Den er en modul-konstant der
    beregnes ved import (`Path.home() / ".jarvis-v2" / "state"`), saa
    `isolated_runtime`s HOME-patch flytter den ikke: modulet importeres foerst
    under den foerste test, og ALLE senere tests deler saa den foerste tests
    mappe. Symptomet var at anden koldstart returnerede "ok" — staten var
    allerede initialiseret af naboen. Den rigtige state_store bruges stadig
    (atomisk skrivning og alt), kun mappen er testens.
    """
    import core.runtime.state_store as ss
    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path / "state")
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(V, "_ejer_uid", lambda: "ejer-1")
    tilstand = {
        "jobs": [],
        "bridge_ok": True,
        "sendt": [],
        "vaekninger": [],
        "send_svar": {"status": "queued"},
        "vaekning_svar": {"status": "ok", "wakeup_id": "wake-1"},
    }

    def fake_operator_jobs(uid, exec_fn):
        assert uid == "ejer-1"
        if not tilstand["bridge_ok"]:
            from core.services.background_jobs import BroTier
            raise BroTier("broen svarede ikke")
        return list(tilstand["jobs"])

    def fake_send(tekst, *, source="", urgent=False):
        tilstand["sendt"].append((tekst, source))
        return dict(tilstand["send_svar"])

    def fake_wake(**kw):
        tilstand["vaekninger"].append(kw)
        return dict(tilstand["vaekning_svar"])

    monkeypatch.setattr("core.services.background_jobs._operator_jobs", fake_operator_jobs)
    monkeypatch.setattr("core.services.notification_bridge.send_session_notification", fake_send)
    monkeypatch.setattr("core.services.self_wakeup.schedule_self_wakeup", fake_wake)
    return tilstand


def test_uden_ejer_sker_der_ingenting(monkeypatch, tmp_path, isolated_runtime):
    import core.runtime.state_store as ss
    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(V, "_ejer_uid", lambda: "")
    assert V.tick_baggrundsjob_vagt() == {"status": "ingen_ejer"}


def test_koldstart_melder_INTET(rig):
    """Foerste tick efter deploy: de gamle jobs skrives som meldt UDEN at sende.
    Uden den regel leverer featuren en byge i samme oejeblik den gaar live."""
    rig["jobs"] = [_job("bg_a"), _job("bg_b"), _job("bg_c", status="running", kode=None)]
    ud = V.tick_baggrundsjob_vagt()
    assert ud == {"status": "koldstart", "tavse": 2}
    assert rig["sendt"] == []
    assert rig["vaekninger"] == []


def test_nyt_faerdigt_job_meldes_én_gang(rig):
    rig["jobs"] = [_job("bg_a")]
    assert V.tick_baggrundsjob_vagt()["status"] == "koldstart"

    rig["jobs"] = [_job("bg_a"), _job("bg_ny", kode=0, sek=125)]
    ud = V.tick_baggrundsjob_vagt()
    assert ud["status"] == "ok" and ud["meldt"] == 1 and ud["fejlede"] == 0
    assert len(rig["sendt"]) == 1
    tekst, kilde = rig["sendt"][0]
    assert "npm run build" in tekst and "2m 5s" in tekst and kilde == "baggrundsjob-vagt"

    # Samme tick igen: intet nyt.
    ud2 = V.tick_baggrundsjob_vagt()
    assert ud2["meldt"] == 0
    assert len(rig["sendt"]) == 1, "et job maa ikke meldes to gange"


def test_aktiv_tur_bruger_inboxen_og_vaekker_IKKE(rig):
    rig["jobs"] = []
    V.tick_baggrundsjob_vagt()                      # koldstart
    rig["send_svar"] = {"status": "queued"}         # queued = sessionen var aktiv
    rig["jobs"] = [_job("bg_1")]
    ud = V.tick_baggrundsjob_vagt()
    assert ud["maader"] == ["inbox"]
    assert rig["vaekninger"] == [], "han er vaagen — en vaekning ville vaere raabet ind ad doeren"


def test_ingen_aktiv_tur_booker_en_vaekning(rig):
    rig["jobs"] = []
    V.tick_baggrundsjob_vagt()
    rig["send_svar"] = {"status": "ok"}             # ok = ingen aktiv tur
    rig["jobs"] = [_job("bg_2", kode=1, kommando="pytest -q")]
    ud = V.tick_baggrundsjob_vagt()
    assert ud["maader"] == ["vaekning"]
    assert len(rig["vaekninger"]) == 1
    kw = rig["vaekninger"][0]
    assert kw["delay_seconds"] == 60
    assert "pytest -q" in kw["prompt"] and "exit 1" in kw["prompt"]
    assert kw["reason"] == "baggrundsjob faerdigt"


def test_bro_der_tier_markerer_intet(rig):
    """En doed bro betyder «vi ved ikke», ikke «ingen jobs». Jobbet skal stadig
    meldes naar broen kommer tilbage."""
    rig["jobs"] = []
    V.tick_baggrundsjob_vagt()
    rig["bridge_ok"] = False
    rig["jobs"] = [_job("bg_3")]
    assert V.tick_baggrundsjob_vagt() == {"status": "bro_tier"}
    assert rig["sendt"] == []

    rig["bridge_ok"] = True
    ud = V.tick_baggrundsjob_vagt()
    assert ud["meldt"] == 1, "jobbet maa ikke vaere tabt fordi broen tav"


def test_mislykket_levering_markerer_ikke_jobbet(rig):
    rig["jobs"] = []
    V.tick_baggrundsjob_vagt()
    rig["send_svar"] = {"status": "blocked"}
    rig["jobs"] = [_job("bg_4")]
    ud = V.tick_baggrundsjob_vagt()
    assert ud["meldt"] == 0 and ud["fejlede"] == 1

    rig["send_svar"] = {"status": "ok"}
    ud2 = V.tick_baggrundsjob_vagt()
    assert ud2["meldt"] == 1, "en fejlet levering skal proeves igen, ikke tabes"


def test_vaekning_der_fejler_taber_ikke_meldingen(rig):
    """Loftet paa pending wakeups er naaet. Beskeden ER skrevet, saa jobbet
    taeller som meldt — men svaret skal sige at vaekningen manglede."""
    rig["jobs"] = []
    V.tick_baggrundsjob_vagt()
    rig["send_svar"] = {"status": "ok"}
    rig["vaekning_svar"] = {"status": "error", "error": "max 20 pending wakeups"}
    rig["jobs"] = [_job("bg_5")]
    ud = V.tick_baggrundsjob_vagt()
    assert ud["meldt"] == 1
    assert ud["maader"] == ["skrevet_uden_vaekning:max 20 pending wakeups"]


@pytest.mark.parametrize("kode,sek,forventet_i", [
    (0, 90, ["✅", "exit 0", "1m 30s"]),
    (1, 5, ["❌", "exit 1", "5s"]),
    (137, 3700, ["❌", "exit 137", "1t 1m"]),
    (None, 10, ["⏹", "ingen exit-kode"]),
    (0, 0, ["✅", "exit 0"]),
])
def test_beskedtekst_siger_udfaldet_foerst(kode, sek, forventet_i):
    tekst = V.beskedtekst(_job("bg_x", kode=kode, sek=sek))
    for bid in forventet_i:
        assert bid in tekst, f"{bid!r} mangler i {tekst!r}"


def test_en_proces_uden_rc_kaldes_ikke_lykkedes():
    """exit_code=None er UKENDT. At skrive 0 ville vaere en loegn om et job der
    maaske blev draebt."""
    tekst = V.beskedtekst(_job("bg_y", kode=None))
    assert "exit 0" not in tekst and "faerdigt" not in tekst


def test_titlen_foretraekkes_over_kommandoen_i_meldingen(rig):
    """«Bygger APK 280 (kun arm64)» siger mere end 70 tegn af en afkortet
    `cd … && gradle …`. Begge felter var tomme indtil 6/10-2026."""
    rig["jobs"] = []
    V.tick_baggrundsjob_vagt()
    rig["jobs"] = [_job("bg_t", titel="Bygger APK 280 (kun arm64)",
                        kommando="cd /x && ./gradlew assembleRelease")]
    V.tick_baggrundsjob_vagt()
    tekst = rig["sendt"][0][0]
    assert "Bygger APK 280 (kun arm64)" in tekst
    assert "gradlew" not in tekst


def test_meldingen_viser_ALDRIG_bare_et_job_id(rig):
    rig["jobs"] = []
    V.tick_baggrundsjob_vagt()
    rig["jobs"] = [_job("bg_02c8cfc248ea", titel="", kommando="")]
    V.tick_baggrundsjob_vagt()
    tekst = rig["sendt"][0][0]
    assert "bg_02c8cfc248ea" not in tekst
    assert "(baggrunds-shell)" in tekst
