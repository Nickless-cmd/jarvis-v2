"""Hvilken udgave af appen kører der?

28/9-2026 gik der en time med at afgøre om en telefon kørte 218 eller 219.
Manifestet sagde hvad der var UDGIVET; ingen kunne sige hvad der var
INSTALLERET. Appen ved det selv — den skal bare sige det.

Hovedet er BRUGERDATA. Testene her holder især skranken fast: uden den kunne
hvem som helst skrive hvad som helst ind i runtime-tilstanden.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core.services import klient_versioner as kv


@pytest.fixture(autouse=True)
def eget_state(tmp_path, monkeypatch):
    """Skriv i tmp_path — ikke i den rigtige runtime-tilstand."""
    import core.runtime.state_store as st
    monkeypatch.setattr(st, "_path", lambda navn: tmp_path / f"{navn}.json")
    return tmp_path


class TestSkranken:
    @pytest.mark.parametrize("klient", ["hacker", "", "MOBILE", "mobile ekstra"])
    def test_ukendt_klient_afvises(self, klient):
        assert kv.noter(klient, "1.0") is False

    def test_en_tekstvaeg_afvises(self):
        assert kv.noter("mobile", "x" * 65) is False

    @pytest.mark.parametrize("version", ["", "   ", "<script>alert(1)</script>",
                                         "0.1\n0.2", "a;rm -rf /"])
    def test_uventede_tegn_afvises(self, version):
        assert kv.noter("mobile", version) is False

    def test_en_normal_version_gaar_igennem(self):
        assert kv.noter("mobile", "0.2.120 (220)") is True
        assert kv.alle()["mobile"]["version"] == "0.2.120 (220)"


class TestDenSenesteVinder:
    def test_en_ny_version_afloeser_den_gamle(self):
        kv.noter("mobile", "0.2.119 (219)")
        kv.noter("mobile", "0.2.120 (220)")
        post = kv.alle()["mobile"]
        assert post["version"] == "0.2.120 (220)"
        assert post["foerst_set"] == post["sidst_set"], "en NY version starter forfra"

    def test_samme_version_igen_flytter_kun_sidst_set(self):
        kv.noter("mobile", "0.2.120 (220)")
        foerst = kv.alle()["mobile"]["foerst_set"]
        kv.noter("mobile", "0.2.120 (220)")
        post = kv.alle()["mobile"]
        assert post["foerst_set"] == foerst, "foerst_set blev nulstillet"
        assert post["sidst_set"] >= foerst

    def test_klienterne_staar_side_om_side(self):
        kv.noter("mobile", "0.2.120 (220)")
        kv.noter("desk", "0.6.136")
        assert set(kv.alle()) == {"mobile", "desk"}

    def test_ingen_har_sagt_noget_endnu(self):
        assert kv.alle() == {}

    def test_en_oedelagt_tilstand_vaelter_ikke(self, eget_state):
        (eget_state / f"{kv.NOEGLE}.json").write_text("ikke json", encoding="utf-8")
        assert kv.alle() == {}
        assert kv.noter("mobile", "0.2.120 (220)") is True


class TestMiddlewarenLaeserHovederne:
    def test_navnene_staar_ens_i_server_og_klienter(self):
        """Tre steder skal bruge PRÆCIS samme to navne. En tastefejl ét sted
        ville gøre feltet tomt uden at noget fejlede."""
        rod = Path(__file__).resolve().parents[1]
        kilder = [
            rod / "apps/api/jarvis_api/app.py",
            rod / "apps/mobile/src/lib/apiClient.ts",
            rod / "apps/jarvis-desk/src/lib/api.ts",
        ]
        for f in kilder:
            tekst = f.read_text(encoding="utf-8").lower()
            assert "x-jarvis-klient" in tekst, f
            assert "x-jarvis-klientversion" in tekst, f

    def test_middlewaren_kalder_faktisk_noter(self):
        """En navne-søgning ville bestå selv om kaldet blev til `pass` — AST."""
        import ast
        rod = Path(__file__).resolve().parents[1]
        traeet = ast.parse((rod / "apps/api/jarvis_api/app.py").read_text(encoding="utf-8"))
        brugt = [n for n in ast.walk(traeet)
                 if isinstance(n, ast.Name) and n.id == "noter"]
        assert brugt, "middlewaren bruger ikke noter()"
