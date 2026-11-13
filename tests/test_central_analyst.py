"""The Analyst — observatør-effekten.

Målt 13/11-2026: karakteren målte 0,0 % divergens og konkluderede «jeg er den
samme, om du ser på eller ej». Det var ikke et fund — det var en afrunding.
`central_ghost.analyze` rundede sætningslængden til én decimal, så 12,04 og
11,96 begge blev 12,0, og divergensen blev regnet på de afrundede visningstal.

Disse tests værner om tre ting:
1. Divergensen regnes på RÅ akser, ikke på visningsværdier.
2. En ægte divergens giver en ægte sætning — ikke «jeg er den samme».
3. Et fund lander som SPOR, ikke som bindende forpligtelse. Støj-vetoet dømte
   fire formuleringer af observer-effekten som støj, og det er korrekt: en
   sproglig observation er ikke en adfærdsregel.
"""
from __future__ import annotations

import pytest

from core.services import central_analyst as ca


def _fingerprint(avg: float, std: float, question: float = 0.2) -> dict:
    """Fingeraftryk i den form central_ghost.analyze faktisk returnerer."""
    return {
        "avg_sentence_len": round(avg, 1),
        "avg_sentence_len_exact": avg,
        "sentence_len_std": round(std, 1),
        "sentence_len_std_exact": std,
        "markers_per_1k": {"question": question, "ellipsis": 0.1},
    }


class TestRaaAkser:
    def test_akse_laeser_exact_felt_frem_for_visningsfelt(self):
        """12,04 mod 11,96 er 0,0 % på visningstal og ~0,7 % på rå tal."""
        vis = _fingerprint(12.04, 9.7)
        aut = _fingerprint(11.96, 9.7)
        raa = ca._akse(vis, aut, "avg_sentence_len")
        visning = ca._akse(
            {"avg_sentence_len": vis["avg_sentence_len"]},
            {"avg_sentence_len": aut["avg_sentence_len"]},
            "avg_sentence_len",
        )
        assert visning == 0.0, "visningstallene er identiske — det var fejlen"
        assert raa is not None and raa > 0.5, f"rå akser skal se forskellen, fik {raa}"

    def test_akse_falder_tilbage_paa_visningsfelt_uden_exact(self):
        """Ældre fingeraftryk uden _exact må stadig kunne måles."""
        v = ca._akse({"avg_sentence_len": 10.0}, {"avg_sentence_len": 20.0}, "avg_sentence_len")
        assert v == pytest.approx(66.67, abs=0.1)

    def test_akse_returnerer_none_naar_feltet_mangler(self):
        assert ca._akse({}, {}, "avg_sentence_len") is None

    def test_akse_taaler_ikke_numerisk_vaerdi(self):
        assert ca._akse({"avg_sentence_len": "n/a"}, {"avg_sentence_len": 12.0},
                        "avg_sentence_len") is None


class TestDivergens:
    def _maaling(self, monkeypatch, vis: dict, aut: dict) -> dict:
        monkeypatch.setattr(ca, "_texts", lambda *, autonomous, limit=60: ["x"] * 3)
        # _texts giver samme liste i begge grene, så vi styrer fordelingen via
        # en tæller: første kald er den synlige kontekst, andet det autonome run.
        kald = {"n": 0}

        def _analyze(texts):
            kald["n"] += 1
            return vis if kald["n"] == 1 else aut

        monkeypatch.setattr("core.services.central_ghost.analyze", _analyze)
        return ca.measure_observer_effect()

    def test_raa_forskel_giver_ikke_nul(self, monkeypatch):
        """Kernefejlen: rå data er forskellige, visningstallene ens."""
        r = self._maaling(monkeypatch, _fingerprint(12.04, 9.7), _fingerprint(11.96, 8.4))
        assert r["divergence_pct"] is not None
        assert r["divergence_pct"] > 5.0, (
            f"variationen er 9,7 mod 8,4 — det er en ægte forskel, fik {r['divergence_pct']}"
        )
        assert r["bearing_axis"] == "variation"

    def test_identiske_kontekster_giver_lav_divergens(self, monkeypatch):
        r = self._maaling(monkeypatch, _fingerprint(12.0, 9.0), _fingerprint(12.0, 9.0))
        assert r["divergence_pct"] == 0.0
        assert "samme" in r["felt"]

    def test_baerende_akse_er_den_stoerste_ikke_et_gennemsnit(self, monkeypatch):
        """Et gennemsnit ville udvande et ægte signal med en akse der er ens."""
        r = self._maaling(monkeypatch, _fingerprint(12.0, 9.7), _fingerprint(12.0, 8.4))
        assert r["bearing_axis"] == "variation"
        assert r["divergence_pct"] == r["axes"]["variation"]

    def test_manglende_raa_felter_giver_none_ikke_nul(self, monkeypatch):
        """Nul betyder «målt ens» — det må ikke også betyde «kunne ikke måle»."""
        r = self._maaling(monkeypatch, {}, {})
        assert r["divergence_pct"] is None


class TestLanding:
    def test_fund_lander_som_spor_ikke_som_forpligtelse(self, monkeypatch):
        """Støj-vetoet har ret: en sproglig observation er ikke en adfærdsregel."""
        kald = {"n": 0}
        monkeypatch.setattr(ca, "_texts", lambda *, autonomous, limit=60: ["x"])
        monkeypatch.setattr(
            "core.services.central_ghost.analyze",
            lambda texts: _fingerprint(12.0, 9.7) if kald.__setitem__("n", kald["n"] + 1) or kald["n"] == 1
            else _fingerprint(12.0, 8.4),
        )
        setninger: list[tuple] = []
        monkeypatch.setattr(
            "core.services.central_consequence.record",
            lambda cid, subject, **kw: setninger.append((cid, subject, kw)) or {"applied": False},
        )
        monkeypatch.setattr(
            "core.services.central_consequence.land_decision",
            lambda *a, **kw: pytest.fail("analyst må ikke binde en forpligtelse"),
        )
        ca.measure_observer_effect()
        assert setninger, "et ægte fund skal efterlade et spor"
        assert setninger[0][0] == "analyst"
        assert setninger[0][1].startswith("observer_effect:")

    def test_lav_divergens_skriver_intet_spor(self, monkeypatch):
        kald = {"n": 0}
        monkeypatch.setattr(ca, "_texts", lambda *, autonomous, limit=60: ["x"])
        monkeypatch.setattr(
            "core.services.central_ghost.analyze",
            lambda texts: _fingerprint(12.0, 9.0),
        )
        setninger: list[tuple] = []
        monkeypatch.setattr(
            "core.services.central_consequence.record",
            lambda cid, subject, **kw: setninger.append((cid, subject)) or {"applied": False},
        )
        ca.measure_observer_effect()
        assert not setninger, "støj skal ikke efterlade spor"


class TestLoggerFindes:
    def test_modulet_har_en_logger(self):
        """Tre gange 13/11 blev logger.warning kaldt i et modul uden logger.

        Det kaster NameError inde i except-grenen — altså præcis når noget
        allerede er galt, og fejlen slår fejlhåndteringen ihjel.
        """
        assert hasattr(ca, "logger"), "central_analyst kalder logger.warning"

    def test_alle_log_kald_har_en_logger_bag_sig(self):
        import inspect
        import re

        src = inspect.getsource(ca)
        if re.search(r"\blogger\.(warning|debug|info|error)\(", src):
            assert hasattr(ca, "logger"), "log-kald uden logger i modulet"
