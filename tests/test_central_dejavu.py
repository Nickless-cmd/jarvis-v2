"""Déjà Vu — karakteren der var stum i tre lag.

Målt 13/11-2026: `build_dejavu_surface()` svarede «Stille. Intet bobler op af sig
selv lige nu» — hver gang. Tre fejl lå oven på hinanden, og hver af dem lignede
et tomt resultat:

1. **Scope.** `get_experiential_memory_candidates()` kræver en eksplicit bruger og
   kaster `MissingRecallScope` fra cadence. Undtagelsen blev slugt → «ingen minder».
   Basen havde 319 minder under to andre ejere hele tiden.
2. **Returformat.** `score_memories_by_relevance()` returnerer `{memory_id: score}`,
   en dict. Koden itererede over den og kaldte `.get("score")` på en streng → kast →
   slugt → «ingen resonans».
3. **Feltnavn.** Kandidaterne bærer `narrative`, ikke `text`/`content`/`summary`.
   Fragmentet blev tomt mens resonansen var 0.65: karakteren HAVDE et fund og
   kastede det væk på et feltnavn.

Fælles form: en tavs undtagelse eller et forkert antaget format der er umuligt at
skelne fra en ægte tom måling.
"""
from __future__ import annotations

import pytest

from core.services import central_dejavu as dj


def _kandidat(mid: str, narrative: str, importance: float = 0.5) -> dict:
    return {"memory_id": mid, "narrative": narrative, "topic": "emne",
            "importance": importance, "decay_score": 0.0, "user_id": "u1"}


class TestKandidatkilden:
    def test_scope_fejl_giver_ikke_adgang_og_laeser_intet(self, monkeypatch):
        """Uden en autoritativ principal må private minder IKKE læses.

        (13/11-2026) Denne test krævede tidligere det MODSATTE: at koden faldt
        tilbage på «de faktiske ejere» — altså blandede forskellige brugeres
        private erindringer i én pulje, netop fordi policyen sagde nej. Testen
        kodificerede grænseovertrædelsen. Nu kræver den det modsatte: intet
        svar og ingen forbindelse til tabellen.
        """
        from core.runtime import db as dbmod
        from core.services.scoped_recall_policy import MissingRecallScope

        def raab(**kw):
            raise MissingRecallScope("private recall requires explicit user scope")

        monkeypatch.setattr(dbmod, "get_experiential_memory_candidates", raab)

        import core.runtime.db_core as dbc

        def _ingen_forbindelse(*a, **kw):
            raise AssertionError("connect() må ikke kaldes når scope mangler")

        monkeypatch.setattr(dbc, "connect", _ingen_forbindelse)

        ud = dj._candidates(limit=5)
        assert ud is None, "manglende adgang skal være None — ikke en tom liste"

    def test_manglende_adgang_kan_skelnes_fra_tomt(self, monkeypatch):
        """Fravær af adgang er ikke fravær af information. De to må ikke lyde ens."""
        monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")
        monkeypatch.setattr(dj, "_candidates", lambda limit=20: None)
        naegtet = dj.surface_dejavu()
        monkeypatch.setattr(dj, "_candidates", lambda limit=20: [])
        tomt = dj.surface_dejavu()
        assert naegtet["access"] == "denied" and tomt["access"] == "ok"
        assert naegtet["reason"] != tomt["reason"]

    def test_naegtet_adgang_siges_hoejt_i_surfacen(self, monkeypatch):
        """En læser må ikke kunne forveksle «jeg må ikke kigge» med «der er intet»."""
        monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")
        monkeypatch.setattr(dj, "_candidates", lambda limit=20: None)
        s = dj.build_dejavu_surface()
        assert s.get("access") == "denied"
        assert "må ikke kigge" in s["felt"] or "ikke fordi der intet er" in s["felt"]

    def test_ingen_kandidater_giver_ingen_undtagelse(self, monkeypatch):
        from core.runtime import db as dbmod
        monkeypatch.setattr(dbmod, "get_experiential_memory_candidates",
                            lambda **kw: [])
        assert dj._candidates(limit=5) == []


class TestScoringsformat:
    def test_dict_format_læses_som_dict(self, monkeypatch):
        """Returformatet er {memory_id: score} — ikke en liste af rækker."""
        import core.services.experiential_memory as em
        monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")
        monkeypatch.setattr(dj, "_candidates",
                            lambda limit=20: [_kandidat("exp-1", "et minde")])
        monkeypatch.setattr(em, "score_memories_by_relevance",
                            lambda **kw: {"exp-1": 0.55})
        d = dj.surface_dejavu()
        assert d["fragment"], "et minde i båndet skal boble op"
        assert d["resonance"] == pytest.approx(0.55)

    def test_score_over_strong_er_ikke_et_fragment(self, monkeypatch):
        """Et opslag er ikke en fornemmelse: over strong-båndet er det ikke déjà vu."""
        import core.services.experiential_memory as em
        monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")
        monkeypatch.setattr(dj, "_candidates",
                            lambda limit=20: [_kandidat("exp-1", "et minde")])
        monkeypatch.setattr(em, "score_memories_by_relevance",
                            lambda **kw: {"exp-1": 0.95})
        d = dj.surface_dejavu()
        assert d["fragment"] is None
        assert "båndet" in d["reason"]


class TestFeltnavn:
    def test_narrative_baeres_frem_som_fragment(self, monkeypatch):
        """Kandidaterne har `narrative` — ikke text/content/summary."""
        import core.services.experiential_memory as em
        monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")
        monkeypatch.setattr(dj, "_candidates",
                            lambda limit=20: [_kandidat("exp-1", "Bjørn var nysgerrig.")])
        monkeypatch.setattr(em, "score_memories_by_relevance",
                            lambda **kw: {"exp-1": 0.5})
        d = dj.surface_dejavu()
        assert d["fragment"] == "Bjørn var nysgerrig."

    def test_minde_uden_tekst_giver_ingen_tomt_fragment(self, monkeypatch):
        """Et tomt fragment må ikke se ud som et fund."""
        import core.services.experiential_memory as em
        monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")
        monkeypatch.setattr(dj, "_candidates",
                            lambda limit=20: [{"memory_id": "exp-1", "narrative": ""}])
        monkeypatch.setattr(em, "score_memories_by_relevance",
                            lambda **kw: {"exp-1": 0.5})
        d = dj.surface_dejavu()
        assert d["fragment"] is None
        assert d["reason"] == "minde uden tekstindhold"


class TestLoggerFindes:
    def test_modulet_har_en_logger(self):
        """Femte gang samme fælde: logger.warning i et modul uden logger → NameError
        inde i except-grenen, altså præcis når noget allerede er galt."""
        import inspect
        kilde = inspect.getsource(dj)
        assert "logger.warning" in kilde or "logger.debug" in kilde
        assert dj.logger is not None


class TestVisningsfladen:
    """(13/11-2026, syvende runde) To forbrugere af samme måling må ikke fortælle
    hver sin historie om resultatet.

    `record_dejavu` skelnede tre tilstande — `denied`, `error`, `ok` — men
    `build_dejavu_surface` kendte kun `denied` og lod ALT andet uden fragment ende
    i «Stille. Intet bobler op af sig selv lige nu». En teknisk fejl blev altså
    præsenteret som ro i præcis den flade nogen faktisk kigger på.
    """

    def test_teknisk_fejl_bliver_ikke_til_stilhed(self, monkeypatch):
        monkeypatch.setattr(dj, "surface_dejavu",
                            lambda **kw: {"fragment": None, "access": "error",
                                          "reason": "kandidatkilden fejlede: db nede"})
        s = dj.build_dejavu_surface()
        assert s["access"] == "error", "fejlen skal videreføres, ikke skjules"
        assert "kandidatkilden fejlede" in s["reason"]
        assert "Stille. Intet bobler" not in s["felt"]
        assert "kunne ikke kigge" in s["felt"]

    def test_tomt_fund_er_ikke_en_fejl(self, monkeypatch):
        """Den modsatte retning: et ægte tomt fund skal stadig måtte lyde stille."""
        monkeypatch.setattr(dj, "surface_dejavu",
                            lambda **kw: {"fragment": None, "access": "ok",
                                          "reason": "ingen resonans i déjà-vu-båndet"})
        s = dj.build_dejavu_surface()
        assert s["access"] == "ok" and s["reason"] == "ingen resonans i déjà-vu-båndet"
        assert "Stille" in s["felt"]

    def test_fragment_baerer_ogsaa_sin_tilstand(self, monkeypatch):
        monkeypatch.setattr(dj, "surface_dejavu",
                            lambda **kw: {"fragment": "et minde", "resonance": 0.55,
                                          "felt": "Noget minder mig om noget…",
                                          "access": "ok"})
        s = dj.build_dejavu_surface()
        assert s["fragment"] == "et minde" and s["access"] == "ok"

    def test_access_er_total_i_alle_grene(self, monkeypatch):
        """Enhver returvej skal bære sin egen tilstand — ellers må forbrugeren gætte."""
        import core.services.experiential_memory as em

        monkeypatch.setattr(dj, "_present_context", lambda: "")
        assert dj.surface_dejavu()["access"] == "ok", "intet nu"

        monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")
        monkeypatch.setattr(dj, "_candidates", lambda limit=20: [])
        assert dj.surface_dejavu()["access"] == "ok", "ingen kandidater"

        monkeypatch.setattr(dj, "_candidates",
                            lambda limit=20: [_kandidat("exp-1", "et minde")])
        monkeypatch.setattr(em, "score_memories_by_relevance", lambda **kw: {"exp-1": 0.95})
        assert dj.surface_dejavu()["access"] == "ok", "intet i båndet"

        monkeypatch.setattr(dj, "_candidates",
                            lambda limit=20: [{"memory_id": "exp-1", "narrative": ""}])
        monkeypatch.setattr(em, "score_memories_by_relevance", lambda **kw: {"exp-1": 0.5})
        assert dj.surface_dejavu()["access"] == "ok", "minde uden tekst"
