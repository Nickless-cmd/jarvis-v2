"""Værktøjs-pumpen — annoncér, kør, flet resultater.

`PreToolUse` kobles her fordi det er det ENESTE sted i flowet hvor et kald endnu
ikke er sket, og «block» derfor kan honoreres. Et blokeret kald må ikke bare
forsvinde: rækkefølgen betyder noget, fordi kald og resultater læses parvis
længere oppe, og modellen skal have at vide HVORFOR frem for at vente på et svar
der aldrig kommer.
"""
from __future__ import annotations

import pathlib

import pytest

from core.services import visible_tool_exec as vte


class TestModulet:
    def test_har_en_logger(self):
        """Except-grenene i pumpen logger. Uden en logger ville de kaste
        NameError og gøre hookene tavse — den fejl blev fanget under
        bygningen, ikke af en test."""
        assert hasattr(vte, "logger")

    def test_pumpen_er_en_async_generator(self):
        import inspect
        assert inspect.isasyncgenfunction(vte.run_tool_batch)


class TestHookKobling:
    """Erklæring er ikke nok — koden skal faktisk kalde dem."""

    @pytest.fixture
    def kilde(self):
        return pathlib.Path("core/services/visible_tool_exec.py").read_text()

    def test_pretooluse_fyres_foer_eksekvering(self, kilde):
        pre = kilde.index('"PreToolUse"')
        exe = kilde.index("_exec_fn,")
        assert pre < exe, "PreToolUse skal fyre FØR eksekveringen"

    def test_kun_ikke_blokerede_kald_eksekveres(self, kilde):
        assert "_kald_til_exec = [tc for i, tc in enumerate(tool_calls)" in kilde
        assert "_exec_fn,\n                _kald_til_exec," in kilde

    def test_blokeret_kald_faar_sit_eget_resultat(self, kilde):
        assert "blokeret af hook" in kilde
        assert '"status": "blocked"' in kilde

    def test_resultater_flettes_paa_oprindelig_plads(self, kilde):
        """Appendes de bagest, går par-visningen af kald og resultater i stykker."""
        assert "for _i, _tc in enumerate(tool_calls):" in kilde
        assert "_flettet" in kilde

    def test_blokeret_kald_annonceres_stadig(self, kilde):
        """Ellers ser det ud som om modellen aldrig bad om værktøjet."""
        assert '"status": "blocked",' in kilde

    def test_posttooluse_fyres_EFTER_resultaterne(self, kilde):
        post = kilde.index('"PostToolUse"')
        res = kilde.index("_results = await _tool_task")
        assert post > res, "PostToolUse skal først kunne se resultatet"

    def test_posttooluse_blokerer_ikke(self, kilde):
        """Værktøjet HAR kørt — der er intet at blokere, kun at tilføje."""
        efter = kilde[kilde.index('"PostToolUse"'):]
        assert 'action") == "inject"' in efter
        assert 'action") == "block"' not in efter
