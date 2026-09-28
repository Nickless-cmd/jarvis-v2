"""Hvilken sti kan en klient HENTE billedet på?

Målt på telefonen 28/9-2026: Jarvis beskar et skærmbillede til `/tmp/ss_mid.png`
og analyserede det. Ventefladen viste navnet, men rammen stod tom — ruten
svarede 403, fordi `/tmp` ikke er hvidlistet og aldrig skal blive det.

    tilladt_sti('/tmp/ss_mid.png')  ->  None

Løsningen er ikke at åbne hvidlisten, men at give klienten en sti der ligger
inden for den. `jarvisx-vision-`-præfikset er allerede betroet.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core.services import vision_preview as vp

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


@pytest.fixture(autouse=True)
def hjem_og_temp(tmp_path, monkeypatch):
    """Flyt BEGGE rødder ned i tmp_path, så testen ikke rører de rigtige."""
    hjem = tmp_path / "hjem"
    temp = tmp_path / "temp"
    hjem.mkdir()
    temp.mkdir()
    monkeypatch.setattr(vp, "JARVIS_HOME", hjem)
    monkeypatch.setattr(vp.tempfile, "gettempdir", lambda: str(temp))
    return hjem, temp


def _skriv(sti: Path, data: bytes = PNG) -> Path:
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_bytes(data)
    return sti


class TestReglen:
    """Samme regel som ruten havde — den er bare flyttet, ikke ændret."""

    def test_under_jarvis_hjem_maa_vises(self, hjem_og_temp):
        hjem, _ = hjem_og_temp
        fil = _skriv(hjem / "uploads" / "a.png")
        assert vp.maa_vises(str(fil)) == fil.resolve()

    def test_jarvis_eget_skaermbillede_maa_vises(self, hjem_og_temp):
        _, temp = hjem_og_temp
        fil = _skriv(temp / "jarvisx-screenshot-1.png")
        assert vp.maa_vises(str(fil)) == fil.resolve()

    def test_en_bar_temp_fil_maa_IKKE_vises(self, hjem_og_temp):
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        assert vp.maa_vises(str(fil)) is None

    @pytest.mark.parametrize("sti", ["", "uploads/a.png", "/etc/passwd", "/tmp/a.txt"])
    def test_alt_andet_afvises(self, sti):
        assert vp.maa_vises(sti) is None


class TestKopien:
    def test_en_sti_der_maa_vises_kopieres_IKKE(self, hjem_og_temp):
        """Alt uploadet ligger under JARVIS_HOME. Kopierede vi dét, ville vi
        fordoble hver eneste vedhæftning uden at vinde noget."""
        hjem, temp = hjem_og_temp
        fil = _skriv(hjem / "uploads" / "a.png")
        assert vp.visnings_sti(str(fil)) == str(fil)
        assert list(temp.glob("jarvisx-vision-*")) == []

    def test_en_bar_temp_fil_faar_en_hvidlistet_kopi(self, hjem_og_temp):
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        ud = vp.visnings_sti(str(fil))
        assert ud and ud != str(fil)
        kopi = Path(ud)
        assert kopi.name.startswith("jarvisx-vision-")
        assert kopi.read_bytes() == PNG
        # Og — hele pointen — kopien må vises.
        assert vp.maa_vises(ud) == kopi.resolve()

    def test_samme_billede_to_gange_giver_SAMME_kopi(self, hjem_og_temp):
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        assert vp.visnings_sti(str(fil)) == vp.visnings_sti(str(fil))
        assert len(list(temp.glob("jarvisx-vision-*"))) == 1

    def test_samme_sti_med_NYT_indhold_giver_en_ny_kopi(self, hjem_og_temp):
        """En sti kan genbruges. Navngav vi kopien efter stien alene, ville
        anden runde vise det FØRSTE billede."""
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        foerste = vp.visnings_sti(str(fil))
        import os
        _skriv(fil, PNG + b"anderledes")
        os.utime(fil, (0, 0))
        anden = vp.visnings_sti(str(fil))
        assert anden != foerste
        assert Path(anden).read_bytes() == PNG + b"anderledes"

    def test_for_stort_billede_faar_ingen_kopi(self, hjem_og_temp, monkeypatch):
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        monkeypatch.setattr(vp, "LOFT", 8)
        assert vp.visnings_sti(str(fil)) == ""

    @pytest.mark.parametrize("navn", ["ss_mid.txt", "ss_mid.zip"])
    def test_noget_der_ikke_er_et_billede_kopieres_ikke(self, hjem_og_temp, navn):
        _, temp = hjem_og_temp
        fil = _skriv(temp / navn)
        assert vp.visnings_sti(str(fil)) == ""

    def test_en_fil_der_ikke_findes_giver_tom_streng(self, hjem_og_temp):
        _, temp = hjem_og_temp
        assert vp.visnings_sti(str(temp / "findes-ikke.png")) == ""

    def test_tom_ind_giver_tom_ud(self):
        assert vp.visnings_sti("") == ""
        assert vp.visnings_sti("   ") == ""

    def test_en_afbrudt_skrivning_efterlader_ingen_hentbar_fil(self, hjem_og_temp,
                                                              monkeypatch):
        """Kopien skrives ved siden af og FLYTTES på plads.

        Skrev vi direkte på måladressen, ville en klient der henter midt i
        skrivningen få et halvt billede — og næste kald ville se filen
        eksistere og aldrig skrive den færdig. Testen afbryder skrivningen og
        kræver at måladressen stadig er tom.
        """
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png", PNG * 40)
        ægte = Path.write_bytes

        def halvvejs(self, data, *a, **kw):
            ægte(self, data[: len(data) // 2])
            raise OSError("disken løb tør")

        monkeypatch.setattr(Path, "write_bytes", halvvejs)
        assert vp.visnings_sti(str(fil)) == ""
        monkeypatch.undo()
        # Intet må ligge tilbage — hverken en hentbar kopi eller en rest.
        rester = list(temp.glob("jarvisx-vision-*"))
        assert rester == [], f"efterladt efter afbrudt skrivning: {rester}"
        # Og under alle omstændigheder må en halv fil ikke kunne VISES.
        for r in temp.glob("*"):
            if r.name.startswith("jarvisx-vision-"):
                assert vp.maa_vises(str(r)) is None

    def test_kopien_ligger_ikke_og_flyder_som_delvis(self, hjem_og_temp):
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        vp.visnings_sti(str(fil))
        assert list(temp.glob("*.delvis")) == []


class TestRutenBrugerSammeRegel:
    """Reglen må ikke findes to steder. Ruten låner den — den ejer den ikke."""

    def test_ruten_eksporterer_praecis_denne_funktion(self):
        from apps.api.jarvis_api.routes import visning
        assert visning.tilladt_sti is vp.maa_vises


class TestAnnonceringenBaererStien:
    """Ventefladen får sine argumenter fra `working_step`, som bygges FØR
    kaldet kører. Er stien ikke med dér, har kortet intet at hente."""

    def test_analyze_image_faar_en_visnings_sti(self, hjem_og_temp):
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        from core.services.visible_tool_exec import _vis_argumenter
        ud = _vis_argumenter("analyze_image", {"image_path": str(fil), "prompt": "x"})
        assert ud["visning_sti"].startswith(str(temp / "jarvisx-vision-"))
        # Etiketten skal stadig vise det RIGTIGE filnavn, ikke kopiens.
        assert ud["image_path"] == str(fil)

    def test_en_sti_der_allerede_maa_vises_baeres_uaendret(self, hjem_og_temp):
        hjem, _ = hjem_og_temp
        fil = _skriv(hjem / "uploads" / "a.png")
        from core.services.visible_tool_exec import _vis_argumenter
        ud = _vis_argumenter("analyze_image", {"image_path": str(fil)})
        assert ud["visning_sti"] == str(fil)

    def test_andre_vaerktoejer_faar_ingen_visnings_sti(self, hjem_og_temp):
        """Vagten står på NAVNET. Uden den ville ethvert værktøj med et felt
        der ligner en billedsti udløse en kopi — og kun analyse-kortet har
        brug for den. Billedet her er ægte, så det kun er navnet der holder
        den ude."""
        _, temp = hjem_og_temp
        fil = _skriv(temp / "ss_mid.png")
        from core.services.visible_tool_exec import _vis_argumenter
        ud = _vis_argumenter("bash", {"command": "ls", "image_path": str(fil)})
        assert "visning_sti" not in ud
        assert ud["command"] == "ls"
        assert list(temp.glob("jarvisx-vision-*")) == [], "der blev kopieret alligevel"

    def test_interne_noegler_fjernes_stadig(self, hjem_og_temp):
        """`_vis_argumenter` afløste `trim_arguments` på kaldestedet — den må
        ikke have tabt dens opgave undervejs."""
        from core.services.visible_tool_exec import _vis_argumenter
        ud = _vis_argumenter("analyze_image", {
            "image_path": "/findes/ikke.png", "_runtime_user_id": "hemmelig",
            "session_id": "s", "prompt": "x",
        })
        assert "_runtime_user_id" not in ud and "session_id" not in ud
        assert ud["prompt"] == "x"

    def test_en_umulig_sti_giver_ingen_noegle_frem_for_en_tom(self, hjem_og_temp):
        """En tom `visning_sti` ville få klienten til at hente ingenting og
        vente forgæves. Så er det bedre at nøglen ikke er der."""
        from core.services.visible_tool_exec import _vis_argumenter
        ud = _vis_argumenter("analyze_image", {"image_path": "/findes/ikke.png"})
        assert "visning_sti" not in ud

    def test_annonceringen_kalder_faktisk_hjaelperen(self):
        """En navne-søgning i kilden ville bestå selv om kaldet blev til `pass`
        — derfor AST. Se `source_guards_need_ast`."""
        import ast
        import inspect
        import core.services.visible_tool_exec as vte
        traeet = ast.parse(inspect.getsource(vte))
        kald = [n for n in ast.walk(traeet)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_vis_argumenter"]
        assert kald, "annonceringen bruger ikke _vis_argumenter"
