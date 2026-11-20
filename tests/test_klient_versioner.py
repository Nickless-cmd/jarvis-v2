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


class TestBuildId:
    """Build-id'et er svaret på «kører klienten det build jeg udgav?».

    25/10-2026 var `__DESK_VERSION__` 0.6.263 i BÅDE det gamle og det nye
    build, så versionsnummeret kunne ikke afgøre det. 20/11-2026 blev headeren
    stadig kastet væk i serveren. Det er den brist testene her holder lukket.
    """

    def test_build_gemmes_sammen_med_versionen(self):
        assert kv.noter("desk", "0.6.397", "fea235c3c") is True
        assert kv.alle()["desk"]["build"] == "fea235c3c"

    def test_nyt_build_med_samme_version_er_en_ny_klient(self):
        """Præcis fejlen fra 25/10: samme version, to forskellige builds."""
        kv.noter("desk", "0.6.263", "aaaa11111")
        foerst = kv.alle()["desk"]["foerst_set"]
        kv.noter("desk", "0.6.263", "bbbb22222")
        post = kv.alle()["desk"]
        assert post["build"] == "bbbb22222", "det nye build blev ikke noteret"
        assert post["foerst_set"] >= foerst, "et nyt build skal starte forfra"

    def test_samme_build_igen_flytter_kun_sidst_set(self):
        kv.noter("desk", "0.6.397", "fea235c3c")
        foerst = kv.alle()["desk"]["foerst_set"]
        kv.noter("desk", "0.6.397", "fea235c3c")
        assert kv.alle()["desk"]["foerst_set"] == foerst

    def test_build_uden_for_tegn_afvises_men_versionen_gemmes(self):
        """Build er brugerdata og gaar gennem samme skranke som versionen."""
        assert kv.noter("desk", "0.6.397", "<script>") is True
        assert "build" not in kv.alle()["desk"]

    def test_en_klient_uden_build_nulstilles_ikke_ved_hvert_kald(self):
        """Mobilen sender ikke build; dens post maa ikke starte forfra hver gang."""
        kv.noter("mobile", "0.2.209 (310)")
        foerst = kv.alle()["mobile"]["foerst_set"]
        kv.noter("mobile", "0.2.209 (310)")
        assert kv.alle()["mobile"]["foerst_set"] == foerst


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

    def test_middlewaren_laeser_build_hovedet(self):
        """AST, ikke grep: en omtale i en kommentar maa ikke gøre vagten grøn."""
        import ast
        rod = Path(__file__).resolve().parents[1]
        traeet = ast.parse((rod / "apps/api/jarvis_api/app.py").read_text(encoding="utf-8"))
        laeste = set()
        for n in ast.walk(traeet):
            if (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "get"
                and n.args
                and isinstance(n.args[0], ast.Constant)
                and isinstance(n.args[0].value, str)
            ):
                laeste.add(n.args[0].value.lower())
        assert "x-jarvis-build" in laeste, (
            "middlewaren læser ikke X-Jarvis-Build — så kan versionen ikke "
            "skelne to builds, og spørgsmålet er igen et gæt"
        )

