"""Fuzzy tekst-match til fil-redigering (porteret fra jarvis-code).

Baggrund: `operator_edit_file` var en ren gennemstikning til broen med eksakt
strengmatch. Målt på produktionsdata: 56 % fejl på edit, 44 % på write — mod
`operator_bash` på 1,2 %. Eksakt match fejler så snart indrykning eller
mellemrum afviger med ét tegn.
"""
from __future__ import annotations

import pytest

from core.tools.fuzzy_edit import resolve_edit


class TestStigen:
    def test_1_eksakt(self):
        ud, n, strat = resolve_edit("a\nhej\nb\n", "hej", "dav")
        assert ud == "a\ndav\nb\n" and n == 1 and strat == "exact"

    def test_2_whitespace_afviger(self):
        """Modellen gengiver sjældent mellemrum præcist."""
        ud, _, strat = resolve_edit("def f( x ):\n", "def f(x):", "def g(x):")
        assert ud == "def g(x):\n" and strat == "whitespace"

    def test_3_indrykning_afviger(self):
        c = "class A:\n    def f(self):\n        return 1\n"
        ud, _, _ = resolve_edit(c, "def f(self):\n    return 1",
                                "def f(self):\n    return 2")
        assert ud == "class A:\n    def f(self):\n        return 2\n"

    def test_4_difflib_paa_naesten_ens_tekst(self):
        c = "def beregn(a, b):\n    # summen\n    return a + b\n"
        ud, _, strat = resolve_edit(
            c, "def beregn(a, b):\n    # sumen\n    return a + b",
            "def beregn(a, b):\n    return a + b")
        assert "difflib" in strat and "# summen" not in ud


class TestFejlerHoejt:
    """En stille forkert redigering er værre end en der ikke sker."""

    def test_tekst_der_ikke_findes(self):
        with pytest.raises(ValueError, match="ikke fundet"):
            resolve_edit("abc def ghi", "zzz qqq", "y")

    def test_flertydigt_uden_replace_all(self):
        with pytest.raises(ValueError, match="2 gange"):
            resolve_edit("x\nx\n", "x", "y")

    def test_tom_soegetekst(self):
        with pytest.raises(ValueError):
            resolve_edit("abc", "", "y")

    def test_replace_all_rammer_alle(self):
        ud, n, _ = resolve_edit("x\nx\n", "x", "y", replace_all=True)
        assert ud == "y\ny\n" and n == 2


class TestIndrykningsKorruption:
    """FEJL FUNDET UNDER PORTEN. Strategi 2 kollapser ALT whitespace — også
    indrykning — og indsatte kalderens egen. På et flerlinje-match brækkede den
    koden i stilhed:

        før   '        return 1'   (8 mellemrum)
        efter '    return 2'       (4 — forkert blok)

    jarvis-codes egen kommentar siger at flerlinje-drift hører til strategi 3,
    men 2 rammer først. Porten retter det."""

    def test_flerlinje_bevarer_filens_indrykning(self):
        c = "class A:\n    def f(self):\n        return 1\n"
        ud, _, strat = resolve_edit(c, "def f(self):\n    return 1",
                                    "def f(self):\n    return 2")
        assert "        return 2" in ud, "indrykningen gik tabt"
        assert strat == "whitespace+indent"

    def test_relativ_indrykning_i_erstatningen_bevares(self):
        c = "class A:\n    def f(self):\n        if x:\n            return 1\n"
        ud, _, _ = resolve_edit(
            c, "def f(self):\n    if x:\n        return 1",
            "def f(self):\n    if x:\n        return 2")
        assert "            return 2" in ud

    def test_enkeltlinje_roeres_ikke_af_rettelsen(self):
        ud, _, strat = resolve_edit("def f( x ):\n", "def f(x):", "def g(x):")
        assert ud == "def g(x):\n" and strat == "whitespace"


class TestRenKerne:
    def test_ingen_afhaengigheder_ud_over_stdlib(self):
        """Hele pointen med at den kunne flyttes ordret."""
        import ast
        import pathlib
        kilde = pathlib.Path("core/tools/fuzzy_edit.py").read_text()
        for node in ast.walk(ast.parse(kilde)):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("core."), node.module
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert not a.name.startswith("core."), a.name
