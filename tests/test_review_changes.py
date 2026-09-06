"""Review-fladen: ejer-gate + at risikoflagene har en REGEL bag sig."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes import review as rv
from core.identity import workspace_context as wc


@pytest.mark.parametrize("rolle", ["owner", ""])
def test_ejer_og_ubundet_slipper_igennem(rolle, monkeypatch):
    monkeypatch.setattr(wc, "current_role", lambda: rolle)
    rv._kun_ejer()


@pytest.mark.parametrize("rolle", ["member", "guest"])
def test_andre_afvises(rolle, monkeypatch):
    monkeypatch.setattr(wc, "current_role", lambda: rolle)
    with pytest.raises(HTTPException) as ex:
        rv._kun_ejer()
    assert ex.value.status_code == 403


def test_gaten_sidder_paa_routeren_saa_nye_ruter_ikke_glemmer_den():
    assert rv._kun_ejer in [d.dependency for d in rv.router.dependencies]


def _app():
    app = FastAPI()
    app.include_router(rv.router)
    return TestClient(app)


def test_fastapi_haandhaever_gaten(monkeypatch, tmp_path):
    monkeypatch.setattr(rv, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(rv, "_kør", lambda *a: "")
    monkeypatch.setattr(wc, "current_role", lambda: "member")
    assert _app().get("/review/changes").status_code == 403
    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    assert _app().get("/review/changes").status_code == 200


def test_stor_core_fil_flages_med_reglen_bag(monkeypatch, tmp_path):
    """Et flag uden en regel bag sig er en fornemmelse forklædt som en måling."""
    (tmp_path / "core").mkdir()
    stor = tmp_path / "core" / "db.py"
    stor.write_text("x\n" * 2500)
    filer = [{"path": "core/db.py", "added": 3, "removed": 1, "binary": False}]
    r = rv._risici(tmp_path, filer, test_koert=True)
    assert len(r) == 1
    assert r[0]["regel"] == "over 2000 linjer"
    assert "Boy Scout" in r[0]["note"]
    assert filer[0]["lines"] == 2500


def test_lille_fil_flages_ikke(tmp_path):
    (tmp_path / "kort.py").write_text("x\n" * 40)
    filer = [{"path": "kort.py", "added": 1, "removed": 0, "binary": False}]
    assert rv._risici(tmp_path, filer, test_koert=True) == []


def test_manglende_testkoersel_flages_naar_der_ER_aendringer(tmp_path):
    (tmp_path / "kort.py").write_text("x\n")
    filer = [{"path": "kort.py", "added": 1, "removed": 0, "binary": False}]
    r = rv._risici(tmp_path, filer, test_koert=False)
    assert [x["regel"] for x in r] == ["ingen test kørt"]


def test_intet_flag_naar_der_slet_ingen_aendringer_er(tmp_path):
    assert rv._risici(tmp_path, [], test_koert=False) == []


# ── Lektier: løkken var halv ────────────────────────────────────────────────

def test_status_afviser_ukendte_vaerdier(monkeypatch):
    """En fri streng kunne parkere en lektion i en status ingen læser."""
    from core.runtime.db_lessons import set_lesson_status

    with pytest.raises(ValueError):
        set_lesson_status(1, "måske")


def test_lektier_deles_i_forslag_og_aktive(monkeypatch):
    kaldt = []

    def falsk(*, status=None, limit=30, source=None):
        kaldt.append(status)
        return [{"id": 1, "lesson": "x", "status": status, "evidence_count": 3,
                 "repeated_count": 2}]

    monkeypatch.setattr("core.runtime.db_lessons.list_lessons", falsk)
    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    d = _app().get("/review/lessons").json()
    assert kaldt == ["proposed", "active"]
    # Bevis-tallene skal med — de er forskellen på en anelse og et mønster.
    assert d["proposed"][0]["evidence_count"] == 3
    assert d["proposed"][0]["repeated_count"] == 2


def test_godkendelse_saetter_active(monkeypatch):
    sat = {}

    def falsk(lid, status):
        sat.update(id=lid, status=status)
        return {"id": lid, "status": status}

    monkeypatch.setattr("core.runtime.db_lessons.set_lesson_status", falsk)
    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    r = _app().post("/review/lessons/7", json={"status": "active"}).json()
    assert sat == {"id": 7, "status": "active"}
    assert r["status"] == "ok"


def test_ukendt_status_giver_en_fejl_ikke_en_tavs_succes(monkeypatch):
    def falsk(lid, status):
        raise ValueError("ukendt status")

    monkeypatch.setattr("core.runtime.db_lessons.set_lesson_status", falsk)
    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    r = _app().post("/review/lessons/7", json={"status": "vås"}).json()
    assert r["status"] == "error"


def test_lektier_er_ogsaa_ejer_gatet(monkeypatch):
    monkeypatch.setattr(wc, "current_role", lambda: "member")
    assert _app().get("/review/lessons").status_code == 403
