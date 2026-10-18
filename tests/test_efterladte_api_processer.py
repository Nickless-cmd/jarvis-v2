"""Vagt: efterladte API-processer maa ikke skrive i samme DB som den levende.

BAGGRUND (maalt 18/10-2026). En genstart startede en ny API-proces korrekt —
men draebte ikke den gamle. Den fortsatte med `PPID=1`, 172 traade, 261 aabne
DB-forbindelser og 18,6 % CPU, og skrev videre til den SAMME `jarvis.db` som
den nye. Den lyttede ikke paa porten og fik derfor ingen requests, saa intet
syntes galt. Det er en konkurrerende skriver, og det er praecis den slags der
giver «database is locked» og WAL-vaekst.

Aarsagen er `KillMode=process` i systemd-uniten: systemd draeber kun MainPID,
ikke hele cgroup'en.

TESTENE HER SPOerger IKKE MASKINEN DE KOERER PAA. `er_efterladt_api_proces`
er ren og faar sine data ind, saa betingelserne kan efterproeves uden at
efterlade en aegte proces bag sig. Det er med vilje: en vagt der kun kan
testes ved at forurene maskinen bliver ikke testet.
"""
from __future__ import annotations

import os

import pytest

from core.services.process_identity import (
    API_UNITS,
    efterladte_api_processer,
    er_efterladt_api_proces,
    foraeldre_kæde,
    systemd_main_pids,
)

#: En cmdline der ligner den API-processen faktisk koerer med.
API_CMD = (
    "/opt/conda/envs/ai/bin/python3.11 /home/bs/miniconda3/envs/ai/bin/uvicorn "
    "apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8080 --workers 1"
)
ANDEN_CMD = "/usr/sbin/sshd -D"


def _efterladt(**kw) -> bool:
    """Kald med fornuftige defaults; kun det der testes overskrives."""
    args = dict(
        pid=4242,
        cmdline=API_CMD,
        main_pids={1111},
        eget_pid=999,
        foraeldre_kæde=set(),
    )
    args.update(kw)
    return er_efterladt_api_proces(**args)


class TestDenEnkelteProces:
    """Seks betingelser — hver sin test, saa en fejl peger paa den rigtige."""

    def test_api_proces_som_systemd_ikke_ejer_er_efterladt(self):
        # Det målte tilfælde: 910568 var ikke MainPID for nogen unit.
        assert _efterladt(pid=910568) is True

    def test_mainpid_er_legitim(self):
        # Den kørende proces — systemd ejer den.
        assert _efterladt(pid=1111, main_pids={1111}) is False

    def test_begge_units_mainpids_er_legitime(self):
        # jarvis-api OG jarvis-runtime koerer samme app; begge er normale.
        assert _efterladt(pid=1111, main_pids={1111, 2222}) is False
        assert _efterladt(pid=2222, main_pids={1111, 2222}) is False

    def test_egen_proces_er_aldrig_efterladt(self):
        # Jeg er per definition i live og maa ikke doemme mig selv.
        assert _efterladt(pid=999, eget_pid=999) is False

    def test_forfader_er_ikke_efterladt(self):
        # Under en genstart kan den nye proces vaere startet af den gamle.
        assert _efterladt(pid=777, foraeldre_kæde={777, 1}) is False

    def test_proces_uden_api_cmdline_er_ligegyldig(self):
        assert _efterladt(cmdline=ANDEN_CMD) is False
        assert _efterladt(cmdline="") is False

    def test_init_og_ugyldige_pids(self):
        assert _efterladt(pid=1) is False
        assert _efterladt(pid=0) is False
        assert _efterladt(pid=-5) is False


class TestDenSamledeDetektor:
    """Detektoren paa den maskine den selv koerer paa — uden at forurene den."""

    def test_ingen_efterladte_naar_systemd_ejer_dem_alle(self):
        # Find hvad der ligner API-processer, og giv dem ALLE som MainPID.
        # Saa skal svaret vaere tomt — det beviser at main_pids respekteres.
        alle = efterladte_api_processer(main_pids=set())
        alle_pids = {int(p["pid"]) for p in alle} | {os.getpid()}
        assert efterladte_api_processer(main_pids=alle_pids) == []

    def test_returnerer_lister_med_de_forventede_felter(self):
        for post in efterladte_api_processer(main_pids=set()):
            assert set(post) == {"pid", "cmdline", "starttid", "ppid"}
            assert isinstance(post["pid"], int)
            assert "apps.api.jarvis_api" in str(post["cmdline"])

    def test_egen_proces_er_aldrig_i_resultatet(self):
        fund = efterladte_api_processer(main_pids=set())
        assert os.getpid() not in {int(p["pid"]) for p in fund}


class TestForaeldrekæde:
    def test_kaeden_indeholder_foraeldrene_men_ikke_mig(self):
        kaede = foraeldre_kæde()
        assert os.getpid() not in kaede
        # I en test har processen altid en foraelder (pytest eller shell).
        assert isinstance(kaede, set)
        assert all(pid > 1 for pid in kaede)

    def test_kaeden_terminerer(self):
        # Ingen uendelig løkke, heller ikke for en pid der ikke findes.
        assert foraeldre_kæde(999999) == set()


class TestSystemdMainPids:
    def test_feiler_aldrig_og_giver_et_saet(self):
        # Uanset om systemd findes paa maskinen.
        pids = systemd_main_pids()
        assert isinstance(pids, set)
        assert all(isinstance(p, int) and p > 1 for p in pids)

    def test_ukendt_unit_giver_ingen_pid(self):
        assert systemd_main_pids(("findes-ikke-som-unit-12345",)) == set()

    def test_units_er_de_to_der_koerer_appen(self):
        # Begge koerer `uvicorn apps.api.jarvis_api.app:app` — se modul-docstring.
        assert API_UNITS == ("jarvis-api", "jarvis-runtime")
