"""Tests for core.services.cross_signal_analysis.

Målt 20/10-2026: `analyze_cross_signals` var 100 % blokeret siden 14/10 —
43 forsøg, 0 succes. Kæden var:

    heartbeat_runtime → analyze_signal_patterns()
      → list_cognitive_experiential_memories(limit=20)   # ingen user_id
      → _scope(None) → require_private_scope() → MissingRecallScope

Og resultatet blev aldrig læst: `memories` blev tildelt og brugt nul gange.
Et dødt kald blokerede altså hele handlingen.

Målefælden her er værd at nævne: den første version af disse tests greppede
efter navnet i kilden — og fældede på den KOMMENTAR der forklarer hvorfor
kaldet er fjernet. En vagt der søger en streng i en fil måler tekst, ikke
kode. Derfor parses AST'en nu.
"""
from __future__ import annotations

import ast
import inspect

_NAVN = "list_cognitive_experiential_memories"


def _tomme(monkeypatch, modul) -> None:
    """De øvrige kilder gøres tomme, så kun det målte kald kan fejle."""
    for navn in (
        "list_cognitive_user_emotional_states",
        "list_cognitive_conversation_signatures",
        "list_cognitive_habit_patterns",
        "list_cognitive_personality_vectors",
    ):
        monkeypatch.setattr(modul, navn, lambda **k: [])


def _kaldte_navne(trae: ast.AST) -> set[str]:
    navne: set[str] = set()
    for knude in ast.walk(trae):
        if isinstance(knude, ast.Call):
            func = knude.func
            navn = getattr(func, "id", None) or getattr(func, "attr", None)
            if navn:
                navne.add(navn)
    return navne


def _importerede_navne(trae: ast.AST) -> set[str]:
    navne: set[str] = set()
    for knude in ast.walk(trae):
        if isinstance(knude, (ast.Import, ast.ImportFrom)):
            for alias in knude.names:
                navne.add(alias.name)
    return navne


class TestIngenBrugerScopedLaesning:
    def test_funktionen_kalder_ikke_den_bruger_scopede_laesning(self):
        """Kaldet er dødt — det skal ikke ske, for det er det der blokerer."""
        from core.services import cross_signal_analysis as csa

        trae = ast.parse(inspect.getsource(csa))
        assert _NAVN not in _kaldte_navne(trae), (
            "den bruger-scopede læsning kaldes — uden en bruger i scope rejser "
            "den MissingRecallScope og blokerer hele heartbeat-ticket"
        )

    def test_importerer_ikke_navnet(self):
        """Fjernes kaldet uden importen, fælder F401 lint-hooken i stedet."""
        from core.services import cross_signal_analysis as csa

        trae = ast.parse(inspect.getsource(csa))
        assert _NAVN not in _importerede_navne(trae), (
            "importen står tilbage som død kode efter kaldet blev fjernet"
        )

    def test_koerer_uden_at_den_scopede_laesning_bliver_kaldt(self, monkeypatch):
        """Adfærd: selv hvis navnet findes i modulet, må det ikke rammes."""
        from core.services import cross_signal_analysis as csa

        kaldt: list[str] = []

        def _boom(*a, **k):
            kaldt.append("kaldt")
            raise RuntimeError("bruger-scoped læsning blev kaldt")

        # raising=False: navnet findes ikke længere, og så er der intet at
        # patche — men hvis nogen genindfører det, fanger vi kaldet.
        monkeypatch.setattr(csa, _NAVN, _boom, raising=False)
        _tomme(monkeypatch, csa)

        csa.analyze_signal_patterns(limit_items=5)

        assert not kaldt
