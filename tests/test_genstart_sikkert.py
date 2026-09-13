"""`scripts/genstart_sikkert.sh` — genstart kun når intet kører.

## Hvorfor scriptet findes

Målt 13/9-2026: **tre** af Bjørns kørsler døde af `api-nedlukning` på én dag,
alle fordi jeg genstartede midt i dem. Den tredje havde preview'et «Forsæt» —
altså præcis den besked han skriver *når* en kørsel er død. Jeg forårsagede det
jeg brugte dagen på at rette.

Efter den første sagde jeg at jeg ville tjekke først. Det gjorde jeg ikke; jeg
genstartede fire gange til. **Et løfte er ikke et værn.**

Testene her er billige — de læser scriptet — men de holder de tre egenskaber
der gør det til et værn frem for en vane.
"""
from __future__ import annotations

import pathlib
import stat

SCRIPT = pathlib.Path("scripts/genstart_sikkert.sh")


def test_scriptet_findes_og_er_koerbart():
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & stat.S_IXUSR, "ikke eksekverbart"


def test_det_SPOERGER_foer_det_genstarter():
    """Uden opslaget er scriptet bare `systemctl restart` med ekstra linjer."""
    kilde = SCRIPT.read_text()
    assert "status='running'" in kilde
    assert "finished_at IS NULL" in kilde
    # og opslaget skal ske FOER genstarten
    assert kilde.index("status='running'") < kilde.index("systemctl restart")


def test_det_VENTER_frem_for_at_draebe():
    """At opdage en koersel og genstarte alligevel ville vaere at maale uden at
    handle."""
    kilde = SCRIPT.read_text()
    assert "sleep 5" in kilde and "MAKS_VENT" in kilde


def test_der_ER_en_vej_udenom_men_den_kraever_et_VALG():
    """En vagt uden noedudgang bliver omgaaet paa den grimme maade. `VENT=0` er
    doeren — men den skal aabnes med vilje, og den siger hvad det koster."""
    kilde = SCRIPT.read_text()
    assert "VENT:-1" in kilde, "vagten er ikke slaaet til som standard"
    assert "VENT=0" in kilde
    assert "api-nedlukning" in kilde, "noedudgangen siger ikke hvad den koster"


def test_det_giver_op_frem_for_at_vente_i_evighed():
    """En genstart der haenger for evigt er ogsaa en genstart der ikke sker."""
    kilde = SCRIPT.read_text()
    assert "exit 1" in kilde
