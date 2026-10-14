"""Tests for scripts/deferred_restart.py — den udskudte genstart.

13/10-2026: Bjørn: «den der checker om turen er slut foer genstart udvides..
du draebte lige en anden session.» Den foerste version ventede KUN paa det run
der bad om genstarten — men en genstart draeber ALLE koersler. I det oejeblik
mit run doede, faldt vagten, ogsaa selv om en anden session var midt i en tur.

Testene her maaler den NYE betingelse: mit run doedt OG ingen andre i live —
og at et loft ABBRYDER frem for at draebe.
"""
from __future__ import annotations

import pytest

from scripts import deferred_restart as dr


def _stram(monkeypatch, *, max_wait: float = 0.05) -> None:
    """Skru vinduet ned, saa testen maaler LOGIKKEN og ikke ventetiden."""
    monkeypatch.setattr(dr, "MAX_WAIT_S", max_wait)
    monkeypatch.setattr(dr, "POLL_INTERVAL_S", 0.0)


def _aktiv_tilstand(monkeypatch, run_id: str | None) -> None:
    monkeypatch.setattr(
        "core.services.visible_runs_sections.run_control_state."
        "_get_active_visible_run_state",
        lambda: ({"run_id": run_id} if run_id else {}),
    )


class TestAndreKoersler:
    def test_ser_det_aktive_run(self, monkeypatch):
        _aktiv_tilstand(monkeypatch, "visible-anden")
        monkeypatch.setattr("core.services.visible_runs.is_visible_run_alive",
                            lambda rid: True)
        assert dr._andre_lever("visible-min") == "visible-anden"

    def test_eget_run_taelles_ikke_som_andet(self, monkeypatch):
        _aktiv_tilstand(monkeypatch, "visible-min")
        monkeypatch.setattr("core.services.visible_runs.is_visible_run_alive",
                            lambda rid: True)
        assert dr._andre_lever("visible-min") == ""

    def test_doedt_run_taelles_ikke(self, monkeypatch):
        """Zombie-raekker maa ikke blokere en genstart i det uendelige."""
        _aktiv_tilstand(monkeypatch, "visible-zombie")
        monkeypatch.setattr("core.services.visible_runs.is_visible_run_alive",
                            lambda rid: False)
        assert dr._andre_lever("visible-min") == ""

    def test_tom_tilstand_er_ingen_andre(self, monkeypatch):
        _aktiv_tilstand(monkeypatch, None)
        assert dr._andre_lever("visible-min") == ""

    def test_ukendt_tilstand_svarer_spoergsmaalstegn(self, monkeypatch):
        """Kan kilden ikke laeses, VED vi det ikke — og saa venter vi."""
        monkeypatch.setattr(
            "core.services.visible_runs_sections.run_control_state."
            "_get_active_visible_run_state",
            lambda: (_ for _ in ()).throw(RuntimeError("db nede")),
        )
        assert dr._andre_lever("visible-min") == "?"


class TestVentTilIdle:
    def test_det_ER_regressionen_venter_paa_andre(self, monkeypatch):
        """KERNEN. Mit run er doedt — den gamle kode gik videre praecis HER.

        Uden den udvidede kontrol returnerede `wait_for_idle` «idle» i samme
        oejeblik mit eget run var vaek, og genstarten rev den anden session
        med. Det er den fejl Bjørn maalte, og den her test er dens vaern.
        """
        _stram(monkeypatch)
        monkeypatch.setattr(dr, "_run_is_alive", lambda rid: False)
        monkeypatch.setattr(dr, "_andre_lever", lambda rid: "visible-anden")

        _waited, grund = dr.wait_for_idle("visible-min", margin_s=0.0)

        assert grund, "genstarten ville vaere koert mens en anden session koerte"
        assert "koerer stadig" in grund

    def test_venter_til_den_andre_er_faerdig(self, monkeypatch):
        _stram(monkeypatch, max_wait=5.0)
        svar = ["visible-anden", "visible-anden", ""]
        kaldt = {"n": 0}

        def fake(rid: str) -> str:
            kaldt["n"] += 1
            return svar.pop(0) if svar else ""

        monkeypatch.setattr(dr, "_run_is_alive", lambda rid: False)
        monkeypatch.setattr(dr, "_andre_lever", fake)

        _waited, grund = dr.wait_for_idle("visible-min", margin_s=0.0)

        assert grund == ""
        assert kaldt["n"] >= 2, "den ventede ikke paa den anden koersel"

    def test_alt_doedt_gaar_igennem(self, monkeypatch):
        _stram(monkeypatch)
        monkeypatch.setattr(dr, "_run_is_alive", lambda rid: False)
        monkeypatch.setattr(dr, "_andre_lever", lambda rid: "")
        _waited, grund = dr.wait_for_idle("visible-min", margin_s=0.0)
        assert grund == ""

    def test_eget_run_der_lever_blokerer_stadig(self, monkeypatch):
        """Den oprindelige grund til at vente maa ikke forsvinde i udvidelsen."""
        _stram(monkeypatch)
        monkeypatch.setattr(dr, "_run_is_alive", lambda rid: True)
        monkeypatch.setattr(dr, "_andre_lever", lambda rid: "")
        _waited, grund = dr.wait_for_idle("visible-min", margin_s=0.0)
        assert "eget run" in grund

    def test_ukendt_tilstand_abryder_frem_for_at_draebe(self, monkeypatch):
        _stram(monkeypatch)
        monkeypatch.setattr(dr, "_run_is_alive", lambda rid: False)
        monkeypatch.setattr(dr, "_andre_lever", lambda rid: "?")
        _waited, grund = dr.wait_for_idle("visible-min", margin_s=0.0)
        assert "kunne ikke laese" in grund


class TestAfbryd:
    def test_rydder_den_ventende_fil_og_skriver_i_indbakken(
        self, monkeypatch, tmp_path
    ):
        """To ting, begge noedvendige.

        Filen skrives af `restart_self` FOER scriptet startes og sendes ved
        naeste api-opstart som «genstart gennemfoert». Bliver den liggende,
        LYVER den — der skete ingen genstart.
        """
        fil = tmp_path / "pending_restart_confirmation.json"
        fil.write_text("{}")
        monkeypatch.setattr(
            "core.tools.restart_self_tools.PENDING_RESTART_FILE", fil)
        kald: list[dict] = []
        monkeypatch.setattr("core.services.inbox_state._ejer_id", lambda: "bjorn")
        monkeypatch.setattr(
            "core.services.inbox_state.registrer_kilde",
            lambda **kw: kald.append(kw) or {"status": "ok"},
        )

        dr._afbryd(42.0, "run visible-ande koerer stadig", "visible-min")

        assert not fil.exists(), (
            "den ventende bekræftelses-fil laa tilbage — naeste opstart ville "
            "sende «genstart gennemfoert» om en genstart der ikke skete"
        )
        assert len(kald) == 1
        assert kald[0]["kildetype"] == "genstart"
        assert kald[0]["paastaaet_ejer"] == "huset"
        assert kald[0]["bruger_id"] == "bjorn"
        assert "UDSKUDT" in kald[0]["beskrivelse"]

    def test_kildetypen_kan_ikke_gate(self):
        """Posten skal være SYNLIG men aldrig naegte en mutation.

        Samme klasse som `run_closure`: huset informerer. Ellers kunne en
        udskudt genstart lamme det naeste vaerktoejskald.
        """
        from core.services.inbox_state import IKKE_GATENDE_KILDETYPER
        assert "genstart" in IKKE_GATENDE_KILDETYPER

    def test_taaler_at_indbakken_er_nede(self, monkeypatch, tmp_path):
        fil = tmp_path / "p.json"
        fil.write_text("{}")
        monkeypatch.setattr(
            "core.tools.restart_self_tools.PENDING_RESTART_FILE", fil)
        monkeypatch.setattr("core.services.inbox_state._ejer_id",
                            lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
        dr._afbryd(1.0, "grund", "rid")  # maa ikke kaste


class TestMain:
    def test_abryder_uden_at_genstarte(self, monkeypatch):
        monkeypatch.setattr(dr, "wait_for_idle",
                            lambda rid, margin_s=0.0: (12.0, "run x koerer stadig"))
        kaldt: list = []
        monkeypatch.setattr(
            dr.subprocess, "run",
            lambda *a, **k: kaldt.append(a) or type("R", (), {"returncode": 0})(),
        )
        afbrudt: list = []
        monkeypatch.setattr(dr, "_afbryd", lambda w, g, r: afbrudt.append((w, g, r)))

        rc = dr.main(["deferred_restart.py", "visible-min", "jarvis-api"])

        assert rc == 2, "afbrydelsen skal kunne ses i returkoden"
        assert not kaldt, "genstarten blev koert alligevel — en tur blev draebt"
        assert afbrudt and afbrudt[0][2] == "visible-min"

    def test_genstarter_naar_alt_er_doedt(self, monkeypatch):
        monkeypatch.setattr(dr, "wait_for_idle",
                            lambda rid, margin_s=0.0: (1.0, ""))
        kaldt: list = []
        monkeypatch.setattr(
            dr.subprocess, "run",
            lambda cmd, **k: kaldt.append(cmd) or type("R", (), {"returncode": 0})(),
        )
        rc = dr.main(["deferred_restart.py", "visible-min", "jarvis-api"])
        assert rc == 0
        assert kaldt and "jarvis-api" in kaldt[0]

    def test_fejlende_genstart_giver_returkode_1(self, monkeypatch):
        monkeypatch.setattr(dr, "wait_for_idle",
                            lambda rid, margin_s=0.0: (1.0, ""))
        monkeypatch.setattr(
            dr.subprocess, "run",
            lambda cmd, **k: type("R", (), {"returncode": 1, "stderr": "nej"})(),
        )
        assert dr.main(["deferred_restart.py", "visible-min", "jarvis-api"]) == 1


def test_pytest_kan_se_modulet():
    """Billig vagt: fejler importen, fejler alt andet med en kryptisk fejl."""
    assert callable(dr.wait_for_idle)
    assert callable(dr._andre_lever)
    assert callable(dr._afbryd)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
