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


def test_scriptet_LYVER_ikke_naar_det_overstyrer():
    """Linjen «ingen aktive kørsler» stod UBETINGET efter løkken.

    Maalt 13/9-2026: en `VENT=0`-koersel skrev baade «genstarter alligevel» OG
    «ingen aktive koersler» — og draebte en koersel. En besked der siger noget
    andet end det der skete, er praecis den fejlklasse hele dagen gik med.
    """
    kilde = SCRIPT.read_text()
    assert 'tvunget' in kilde, "der er ingen markering af en overstyring"
    assert 'genstarter TRODS aktive kørsler' in kilde
    # og den ubetingede paastand maa ikke staa alene
    i = kilde.index('ingen aktive kørsler — genstarter')
    foran = kilde[max(0, i - 200):i]
    assert 'else' in foran, "«ingen aktive» staar stadig ubetinget"


def test_noedudgangen_siger_hvad_den_KOSTER():
    """Jeg brugte VENT=0 af vane faa minutter efter at have bygget vaernet, og
    draebte en fjerde koersel. Linjen skal naevne konsekvensen ved navn."""
    kilde = SCRIPT.read_text()
    assert "Forsæt" in kilde, "noedudgangen naevner ikke hvad den koster"
