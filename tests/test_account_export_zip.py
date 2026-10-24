"""ZIP-eksporten: samme bundt, anden emballage — og redaktionen må ikke kunne omgås.

Besluttet 24/10-2026: ZIP bygges, udløbende link forkastes. Et link der dør
efter 24 timer gør portabilitet til en tidsbegrænset rettighed; GDPR Art. 20
handler om at FÅ sine data. Derfor er arkivet streamet — ingen fil, intet link.
"""
from __future__ import annotations

import io
import json
import zipfile

from apps.api.jarvis_api.routes.account import build_export_zip


def _bundle(**extra):
    b = {
        "exported_for": "u_b",
        "profile": {"email": "b@x.dk"},
        "connectors": [{"id": "gmail", "connected": True}],
        "notes": [{"id": "n1", "text": "hej"}],
        "sessions": [{"id": "s1"}],
        "senses": [{"id": "se1"}],
        "brain": [{"id": "br1"}],
        "identity": {"name": "Bjørn"},
        "exported_at": "2026-10-24T08:00:00Z",
        "redaction": {"applied": True, "values_redacted": 50},
    }
    b.update(extra)
    return b


def test_arkivet_kan_aabnes_og_har_to_poster():
    arkiv = build_export_zip(_bundle())
    with zipfile.ZipFile(io.BytesIO(arkiv)) as zf:
        navne = sorted(zf.namelist())
        assert navne == ["README.txt", "data.json"]
        # ZIP'en skal være intakt — testzip() fanger en korrupt central directory
        assert zf.testzip() is None


def test_data_json_er_bundtet_ordret():
    b = _bundle()
    arkiv = build_export_zip(b)
    with zipfile.ZipFile(io.BytesIO(arkiv)) as zf:
        indlaest = json.loads(zf.read("data.json").decode("utf-8"))
    assert indlaest == b


def test_redaktionen_foelger_med_i_arkivet():
    """En ZIP må ikke være en vej uden om redaktøren.

    Bundtet kommer fra build_data_export, som allerede har skrubbet. Testen
    kræver at redaction-blokken står i arkivet — så modtageren kan se at der
    ER redigeret, og hvor meget.
    """
    arkiv = build_export_zip(_bundle())
    with zipfile.ZipFile(io.BytesIO(arkiv)) as zf:
        indlaest = json.loads(zf.read("data.json").decode("utf-8"))
    assert indlaest["redaction"]["applied"] is True
    assert indlaest["redaction"]["values_redacted"] == 50


def test_readme_forklarer_redaktionen():
    arkiv = build_export_zip(_bundle())
    with zipfile.ZipFile(io.BytesIO(arkiv)) as zf:
        readme = zf.read("README.txt").decode("utf-8")
    assert "GDPR Art. 20" in readme
    assert "fjernet" in readme
    assert "2026-10-24T08:00:00Z" in readme


def test_samme_bundt_giver_samme_arkiv():
    """Reproducerbart: ingen filsystem-tidsstempler i arkivet.

    Uden faste date_time-felter ville to kald på samme bundt give forskellige
    bytes, og en test kunne aldrig sammenligne dem.
    """
    b = _bundle()
    assert build_export_zip(b) == build_export_zip(b)


def test_tomt_bundt_er_stadig_et_gyldigt_arkiv():
    arkiv = build_export_zip({})
    with zipfile.ZipFile(io.BytesIO(arkiv)) as zf:
        assert zf.testzip() is None
        assert json.loads(zf.read("data.json").decode("utf-8")) == {}
