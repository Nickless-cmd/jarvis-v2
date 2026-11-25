"""Continuation skal arve opgavens id fra posten den fortsaetter.

Uden id'et faldt `stempl_aktiv_kaede` tilbage til `aktiv_kaede`, der laeser
samtalens NYESTE post. Saa kunne en anden opgave laane sit kaedenummer ud, og
en frisk post med `recovery_attempt: 0` nulstillede loftet midt i en kaede.
Posten for den koersel der fortsaettes baerer svaret — den skal bare laeses.
"""

import core.services.in_flight_runs as ifr
import core.services.visible_runs_memory as vrm


def test_opgavens_id_laeses_fra_posten(monkeypatch):
    monkeypatch.setattr(
        ifr, "get_record",
        lambda rid: {"run_id": rid, "task_id": "opg-1"},
    )
    assert vrm._arvet_opgave("r1") == "opg-1"


def test_ukendt_post_giver_tomt_ikke_et_gaet(monkeypatch):
    """En post der ikke findes maa ikke give et opfundet id."""
    monkeypatch.setattr(ifr, "get_record", lambda rid: None)
    assert vrm._arvet_opgave("r1") == ""


def test_tomt_run_id_slaar_intet_op(monkeypatch):
    kaldt: list = []
    monkeypatch.setattr(ifr, "get_record", lambda rid: kaldt.append(rid) or None)
    assert vrm._arvet_opgave("") == ""
    assert kaldt == []


def test_kastende_opslag_giver_tomt(monkeypatch):
    """Et fejlende opslag maa ikke draebe continuation — men heller ikke gaette."""
    def _kaster(rid):
        raise RuntimeError("journalen er nede")

    monkeypatch.setattr(ifr, "get_record", _kaster)
    assert vrm._arvet_opgave("r1") == ""


def test_post_uden_task_id_giver_tomt(monkeypatch):
    monkeypatch.setattr(ifr, "get_record", lambda rid: {"run_id": rid})
    assert vrm._arvet_opgave("r1") == ""
