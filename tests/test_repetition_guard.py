"""Gentagelses-vagt: funktionen virker OG den kaldes fra produktionsstien.

Sidste gang byggede vi funktioner ingen kaldte. Derfor måler `TestKaldtFraProduktion`
selve `visible_runs.py` — fjern kaldet dér, og testen fejler.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.services import repetition_guard as rg

SVAR = (
    "Jeg har gennemgået sagen og intet er ændret siden sidst. Vi venter stadig på "
    "at godkendelsen kommer fra Bjørn, og indtil da kan jeg ikke komme videre med opgaven."
)
ANDET = (
    "Testsuiten kørte igennem uden fejl, og den nye gren er klar til at blive "
    "flettet ind når du har kigget på forskellen mellem de to versioner."
)


class TestIsRepetition:
    @pytest.mark.parametrize("final,prev,forventet", [
        (SVAR, [SVAR], True),                                  # identiske
        (SVAR, [ANDET, SVAR], True),                           # findes blandt de seneste
        (SVAR.upper() + "!", [SVAR], True),                    # kun case/tegnsætning
        (ANDET, [SVAR], False),                                # forskellige
        (SVAR, [], False),                                     # intet at sammenligne med
        ("", [SVAR], False),                                   # tomt
        ("Ja, det er gjort.", ["Ja, det er gjort."], False),   # for kort til at måle
        (SVAR + " Fil core/ny_fil.py er ny.", [SVAR], False),  # nyt filnavn
        (SVAR + " Det tog 42 sekunder.", [SVAR], False),       # nyt tal
        (SVAR + " Se commit 56a5078b1.", [SVAR], False),       # ny hash
    ])
    def test_tabel(self, final, prev, forventet):
        assert rg.is_repetition(final, prev) is forventet

    def test_kendt_information_er_stadig_gentagelse(self):
        medtal = SVAR + " Det er 42 sekunder siden, i core/a.py."
        assert rg.is_repetition(medtal, [medtal]) is True

    def test_kun_de_seneste_n_sammenlignes(self):
        assert rg.is_repetition(SVAR, [SVAR, ANDET, ANDET], window=2) is False
        assert rg.is_repetition(SVAR, [SVAR, ANDET, ANDET], window=3) is True

    def test_nudged_already_og_fejl_er_false(self):
        assert rg.is_repetition(SVAR, [SVAR], nudged_already=True) is False
        assert rg.is_repetition(SVAR, 5) is False  # type: ignore[arg-type]  # fail-safe

    def test_nudge_beder_om_alle_tre_udveje(self):
        assert "(a)" in rg.REPETITION_NUDGE and "(b)" in rg.REPETITION_NUDGE
        assert "(c)" in rg.REPETITION_NUDGE and "gentager" in rg.REPETITION_NUDGE


class TestFlag:
    def test_env_vinder(self, monkeypatch):
        monkeypatch.setenv("JARVIS_REPETITION_GUARD", "off")
        assert rg.repetition_guard_enabled() is False
        monkeypatch.setenv("JARVIS_REPETITION_GUARD", "1")
        assert rg.repetition_guard_enabled() is True

    def test_default_er_true(self, monkeypatch):
        monkeypatch.delenv("JARVIS_REPETITION_GUARD", raising=False)
        monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                            lambda key, default=None: default)
        assert rg.repetition_guard_enabled() is True

    def test_should_nudge_respekterer_flag_og_session(self, monkeypatch):
        monkeypatch.setattr(rg, "previous_assistant_texts", lambda sid: [SVAR])
        monkeypatch.setenv("JARVIS_REPETITION_GUARD", "1")
        assert rg.should_nudge(SVAR, "s1") is True
        monkeypatch.setenv("JARVIS_REPETITION_GUARD", "0")
        assert rg.should_nudge(SVAR, "s1") is False


class TestKaldtFraProduktion:
    """Mutationstest: fjern blokken i visible_runs.py → disse FEJLER."""

    @pytest.fixture(scope="class")
    def kilde(self):
        sti = Path(__file__).resolve().parents[1] / "core/services/visible_runs.py"
        return ast.parse(sti.read_text(encoding="utf-8"))

    @staticmethod
    def _kald(tree, attr):
        return [n for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == attr]

    def test_should_nudge_kaldes(self, kilde):
        assert self._kald(kilde, "should_nudge"), "visible_runs kalder aldrig vagten"

    def test_nudge_indlaeges_i_halen(self, kilde):
        indlagt = [c for c in self._kald(kilde, "tilfoej_naeste")
                   if any(isinstance(a, ast.Attribute) and a.attr == "REPETITION_NUDGE"
                          for a in c.args)]
        assert indlagt, "REPETITION_NUDGE indlægges aldrig via tilfoej_naeste"

    def test_kaldet_er_loftet_til_en_nudge(self, kilde):
        # Betingelsen der omslutter kaldet skal teste `_repetition_nudges < 1`.
        for node in ast.walk(kilde):
            if isinstance(node, ast.If) and any(
                isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "should_nudge"
                for c in ast.walk(node.test)
            ):
                assert "_repetition_nudges" in ast.unparse(node.test)
                assert any(isinstance(n, ast.AugAssign) and getattr(n.target, "id", "") == "_repetition_nudges"
                           for n in ast.walk(node))
                return
        pytest.fail("ingen betingelse omkring should_nudge")
