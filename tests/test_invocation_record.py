"""Durabel invokations-tilstand for kald ingen bliver spurgt om — Fase 3, K3.

MÅLT 9/9-2026: 1.086 værktøjskald i døgnet, de fleste LÆSNINGER. En
DB-skrivning pr. `ls` ville være samme fejl som en tråd pr. følelses-signal.
Så kun kald der faktisk ændrer noget.

Det der manglede var mellemklassen: auto-godkendte kald der stadig skriver.
De havde ingen post overhovedet, og et nedbrud dér efterlod et ægte ukendt
udfald — skete skrivningen, eller gjorde den ikke?
"""
from __future__ import annotations

import logging

import pytest

from core.runtime import db_approval_bridge as B
from core.services import invocation_record as R
from core.services.invocation_record import recorded


@pytest.fixture(autouse=True)
def _rene(isolated_runtime):
    R._nulstil_for_tests()
    yield
    R._nulstil_for_tests()


def _tilstand(iid):
    s = B.state(iid)
    return s["state"] if s else None


# ── den normale vej ──────────────────────────────────────────────────────

def test_et_lykkeligt_kald_ender_som_completed():
    with recorded("write_file", {"path": "/w/x.py"}) as iid:
        pass
    assert _tilstand(iid) == B.COMPLETED


def test_tilstanden_er_DISPATCHING_MENS_kaldet_koerer():
    """Posten skal staa FØR handlingen, ikke efter — ellers beviser den intet."""
    with recorded("write_file", {"path": "/w/x.py"}) as iid:
        assert _tilstand(iid) == B.DISPATCHING


def test_kaldet_faar_sit_eget_id():
    with recorded("write_file", {"path": "/w/x.py"}) as a:
        pass
    with recorded("write_file", {"path": "/w/x.py"}) as b:
        pass
    assert a != b


# ── forskellen posten findes for ─────────────────────────────────────────

def test_en_FEJL_undervejs_ender_som_failed():
    with pytest.raises(ValueError):
        with recorded("write_file", {"path": "/w/x.py"}) as iid:
            gemt = iid
            raise ValueError("disken er fuld")
    assert _tilstand(gemt) == B.FAILED


def test_et_NEDBRUD_efterlader_dispatching_altsaa_UKENDT():
    """«Skete skrivningen, eller gjorde den ikke?» — det er dét posten svarer
    på. Her efterlignes nedbruddet: ingen naaede at afslutte."""
    from core.services.invocation_record import _afslut
    with recorded("write_file", {"path": "/w/x.py"}) as iid:
        gemt = iid
        # efterlign at processen doer: fjern afslutningen
        R._afslut = lambda *a, **k: None
    R._afslut = _afslut
    assert _tilstand(gemt) == B.DISPATCHING
    assert B.abandon(gemt) == B.OUTCOME_UNKNOWN


def test_en_der_ALDRIG_blev_afsendt_er_noget_ANDET():
    """`prepared` betyder «det skete aldrig». Det er den skelnen K6 kraever."""
    iid = "inv-aldrig"
    B.prepare(iid, tool_name="write_file", arguments={"path": "/w/x.py"})
    assert B.abandon(iid) == B.ABORTED_BEFORE_DISPATCH


# ── den må aldrig vælte kaldet den beskriver ─────────────────────────────

def test_en_doed_bro_stopper_ikke_skrivningen(monkeypatch, caplog):
    monkeypatch.setattr(B, "prepare",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    kaldt = []
    with caplog.at_level(logging.WARNING):
        with recorded("write_file", {"path": "/w/x.py"}):
            kaldt.append(1)
    assert kaldt == [1] and R.taellere()["fejl"] == 1


def test_en_doed_bro_TIER_ikke(monkeypatch, caplog):
    """En durabel tilstand der stille holder op med at blive skrevet, er værre
    end ingen: man tror man kan rekonstruere, og man kan ikke."""
    monkeypatch.setattr(B, "prepare",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    with caplog.at_level(logging.WARNING):
        with recorded("write_file", {"path": "/w/x.py"}):
            pass
    assert "uden durabel tilstand" in caplog.text


def test_en_fejl_i_kaldet_boblet_op_selv_om_broen_er_doed(monkeypatch):
    """Registreringen må ikke sluge kalderens egen fejl."""
    monkeypatch.setattr(B, "prepare", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(ValueError):
        with recorded("write_file", {"path": "/w/x.py"}):
            raise ValueError("den ægte fejl")


# ── den er koblet paa den auto-godkendte skrivning ───────────────────────

def test_write_file_registrerer_sin_auto_godkendte_skrivning(tmp_path, monkeypatch):
    from core.tools import file_tools_exec as F
    monkeypatch.setattr(F, "PROJECT_ROOT", tmp_path, raising=False)
    R._nulstil_for_tests()
    F._exec_write_file({"path": str(tmp_path / "ny.txt"), "content": "hej"})
    t = R.taellere()
    assert t["forberedt"] >= 1 and t["afsluttet"] >= 1


def test_edit_file_registrerer_ogsaa(tmp_path, monkeypatch):
    """En edit er vaerre at miste end en skrivning: den er en DELVIS aendring,
    saa «skete den?» kan ikke besvares ved at se om filen findes."""
    from core.tools import file_tools_exec as F
    monkeypatch.setattr(F, "PROJECT_ROOT", tmp_path, raising=False)
    f = tmp_path / "e.txt"
    f.write_text("foer")
    R._nulstil_for_tests()
    F._exec_edit_file({"path": str(f), "old_text": "foer", "new_text": "efter"})
    t = R.taellere()
    assert t["forberedt"] >= 1 and t["afsluttet"] >= 1


# ── over bro-graensen ────────────────────────────────────────────────────

def test_en_fejl_dict_ender_som_failed_ikke_completed():
    """Vaerktoejer over broen KASTER ikke — de returnerer en fejl-dict. Uden
    `markaer_mislykket` ville et mislykket kald staa som `completed`, og saa
    beskriver posten ikke det den findes for."""
    from core.services.invocation_record import markaer_mislykket
    with recorded("operator_write_file", {"path": "/w/x.py"}) as iid:
        markaer_mislykket(iid)
    assert _tilstand(iid) == B.FAILED


def test_markaer_mislykket_afslutter_kun_EN_gang():
    """Ellers ville udgangen af blokken skrive `completed` oven i fejlen."""
    from core.services.invocation_record import markaer_mislykket
    with recorded("operator_write_file", {"path": "/w/x.py"}) as iid:
        markaer_mislykket(iid)
    assert _tilstand(iid) == B.FAILED
    # og naeste kald starter rent
    with recorded("operator_write_file", {"path": "/w/y.py"}) as b:
        pass
    assert _tilstand(b) == B.COMPLETED
