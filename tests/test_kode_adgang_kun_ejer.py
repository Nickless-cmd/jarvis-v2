"""Enheds-reglen gælder EJERENS enheder — ikke medlemmernes klienter.

Bjørn 31/10-2026, efter målingen: `enheder` har 5 rækker og ALLE er hans;
nul medlemmer har en enhed, og intet medlem har nogensinde haft en
`kind='code'`-samtale. Reglen spærrede derfor ikke fjernstyring af hans
maskine — den spærrede hele jarvis-code-klienten for alle andre.

Reglens formål er at binde et token til en enhed FØR det må køre kode på
Bjørns maskine. Et medlem der kører kode på sin EGEN maskine er ikke den
trussel reglen blev skrevet imod.

Kontrakten her er fire punkter, og det fjerde er det vigtige:
  1. medlem + regel tændt      -> tilladt, og registret spørges slet ikke
  2. ejer   + regel tændt      -> håndhæves (uændret adfærd)
  3. ejer   + aktiv enhed      -> tilladt
  4. ukendt ejer               -> håndhæv for ALLE (fail-closed)

Punkt 4 er ikke kosmetik: kan ejeren ikke slås op, må reglen ikke stille
og roligt holde op med at gælde for den ene person den findes for.
"""
from __future__ import annotations

import core.identity.owner_resolver as orr
import core.identity.workspace_context as wc
from core.identity import kode_adgang as ka
from core.runtime import db_devices as dd

EJER = "1246415163603816499"
MEDLEM = "238975101381378048"


def _regel_taendt(monkeypatch, bruger: str, *, enhed=("enh-x", "")):
    """Sæt scenariet op: reglen er tændt, og tokenet bærer `bruger`."""
    monkeypatch.setattr(dd, "kraev_aktivt", lambda: True)
    monkeypatch.setattr(wc, "current_user_id", lambda: bruger)
    monkeypatch.setattr(wc, "current_token_enhed", lambda: enhed)


def test_medlem_slipper_igennem_uden_at_registret_spoerges(monkeypatch):
    _regel_taendt(monkeypatch, MEDLEM)
    monkeypatch.setattr(orr, "owner_user_id", lambda: EJER)

    def boom(*a, **k):
        raise AssertionError("medlemmets klient må ikke gates af enheds-reglen")

    monkeypatch.setattr(dd, "maa_bruge_kode", boom)
    assert ka.kode_tilladt() is True


def test_ejeren_er_stadig_omfattet(monkeypatch):
    _regel_taendt(monkeypatch, EJER)
    monkeypatch.setattr(orr, "owner_user_id", lambda: EJER)
    monkeypatch.setattr(dd, "maa_bruge_kode", lambda *a, **k: False)
    assert ka.kode_tilladt() is False


def test_ejeren_slipper_igennem_med_en_aktiv_enhed(monkeypatch):
    _regel_taendt(monkeypatch, EJER, enhed=("enh-aktiv", "app-1"))
    monkeypatch.setattr(orr, "owner_user_id", lambda: EJER)
    set_kald = {}
    monkeypatch.setattr(
        dd,
        "maa_bruge_kode",
        lambda b, **k: set_kald.update({"bruger": b, **k}) or True,
    )
    assert ka.kode_tilladt() is True
    assert set_kald["bruger"] == EJER


def test_ukendt_ejer_haandhaever_for_alle(monkeypatch):
    """Kan ejeren ikke slås op, må undtagelsen ikke gælde nogen."""
    _regel_taendt(monkeypatch, MEDLEM)
    monkeypatch.setattr(orr, "owner_user_id", lambda: "")
    monkeypatch.setattr(dd, "maa_bruge_kode", lambda *a, **k: False)
    assert ka.kode_tilladt() is False


def test_ejeropslag_der_kaster_er_fail_closed(monkeypatch):
    _regel_taendt(monkeypatch, MEDLEM)

    def boom():
        raise RuntimeError("users.json utilgængelig")

    monkeypatch.setattr(orr, "owner_user_id", boom)
    monkeypatch.setattr(dd, "maa_bruge_kode", lambda *a, **k: False)
    assert ka.kode_tilladt() is False
