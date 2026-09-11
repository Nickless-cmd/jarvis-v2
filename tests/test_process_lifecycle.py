"""Flaget der ikke fandtes — og som syv tabte runder hang på."""
from __future__ import annotations

import threading

from core.runtime import process_lifecycle as pl


def setup_function() -> None:
    pl.nulstil_til_test()


def test_starter_som_ikke_lukkende():
    assert pl.lukker_ned() is False
    assert pl.grund() == ""


def test_markering_holder():
    pl.markér_nedlukning("SIGTERM")
    assert pl.lukker_ned() is True
    assert pl.grund() == "SIGTERM"


def test_idempotent_foerste_grund_vinder():
    """Anden markering maa ikke overskrive hvorfor vi lukker."""
    pl.markér_nedlukning("SIGTERM")
    pl.markér_nedlukning("noget andet")
    assert pl.grund() == "SIGTERM"


def test_tom_grund_bliver_alligevel_til_noget_laesbart():
    pl.markér_nedlukning()
    assert pl.grund() == "shutdown"


def test_flere_traade_ser_det_samme():
    """Loekken koerer i en anden traad end lifespan-hooken."""
    set_af: list[bool] = []
    klar = threading.Event()

    def laeser() -> None:
        klar.wait(timeout=2)
        set_af.append(pl.lukker_ned())

    t = threading.Thread(target=laeser)
    t.start()
    pl.markér_nedlukning("SIGTERM")
    klar.set()
    t.join(timeout=3)
    assert set_af == [True]
