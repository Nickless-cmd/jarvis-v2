"""Den anden halvdel af overraskelses-buggen: en forventning uden død zone.

Rettelsen 17. aug gjorde negativ overraskelse mulig, men efterlod en to-værdi-konstant.
`weak → 0.5` mod gaten `> 0.6` betød "jeg forventer at fejle" — så hver eneste succes
(98% af alle runs) blev en "positiv overraskelse". DB pr. 18. aug: 19.785 positive,
NUL negative, heraf 54 nye på ét døgn efter den halve rettelse.

Her testes at forventningen nu er (a) empirisk og varierende, (b) har en død zone hvor
INTET kan overraske, og (c) ikke tæller uafgjorte udfald som bevis.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.self_surprise_expectation as ex


class TestKlassifikation:
    def test_succes_og_fejl_genkendes(self):
        assert ex.classify_outcome("completed") == "success"
        assert ex.classify_outcome("failed") == "failure"
        assert ex.classify_outcome("error") == "failure"

    def test_afbrudt_er_uafgjort_ikke_fejl(self):
        """Bjørn trykker stop → det siger intet om min kompetence."""
        for s in ("cancelled", "interrupted", "aborted", ""):
            assert ex.classify_outcome(s) == "indecisive"

    def test_ukendt_status_bliver_aldrig_til_en_fejl(self):
        """En status vi ikke forstår må ikke blive til en anklage."""
        assert ex.classify_outcome("noget_helt_nyt") == "indecisive"


class TestDoedZone:
    """Kernen i rettelsen: uden en skarp forudsigelse er intet overraskende."""

    def test_midterfeltet_kan_ikke_overraske_i_nogen_retning(self):
        for p in (0.36, 0.5, 0.6, 0.74):
            assert ex.expectation_verdict(p, "success") is None, p
            assert ex.expectation_verdict(p, "failure") is None, p

    def test_den_gamle_weak_konstant_er_nu_stum(self):
        """0.5 + succes var kilden til 54 falske overraskelser på ét døgn."""
        assert ex.expectation_verdict(0.5, "success") is None

    def test_sikker_succes_der_fejler_er_negativ(self):
        assert ex.expectation_verdict(0.98, "failure") == "negative"

    def test_sikker_fejl_der_lykkes_er_positiv(self):
        assert ex.expectation_verdict(0.2, "success") == "positive"

    def test_uafgjort_udfald_overrasker_aldrig(self):
        assert ex.expectation_verdict(0.98, "indecisive") is None
        assert ex.expectation_verdict(0.1, "indecisive") is None


class TestEmpiriskRate:
    def _rate(self, rows, *, strength="weak"):
        with patch.object(ex, "_recent_outcomes", lambda m, lookback: rows), \
             patch("core.services.model_trust.model_strength", lambda m: strength):
            return ex.expected_success_rate("m")

    def test_uden_historik_staar_prior_alene(self):
        assert self._rate((0, 0), strength="weak") == 0.5
        assert self._rate((0, 0), strength="strong") == 0.85

    def test_ukendt_svag_model_lander_i_doed_zone(self):
        """En model uden track-record må ikke kunne overraske mig endnu."""
        p = self._rate((0, 0), strength="weak")
        assert ex.CONFIDENT_FAILURE < p < ex.CONFIDENT_SUCCESS

    def test_empirien_overtager_med_bevis(self):
        """55/55 rene runs (glm-5.2:cloud, live) → sikker forventning om succes."""
        assert self._rate((55, 55), strength="strong") >= ex.CONFIDENT_SUCCESS

    def test_vedholdende_fejl_giver_sikker_fejlforventning(self):
        assert self._rate((2, 50), strength="weak") <= ex.CONFIDENT_FAILURE

    def test_raten_varierer_med_bevis(self):
        """Ikke længere to værdier — den bevæger sig monotont med historikken."""
        rates = [self._rate((k, 20)) for k in (0, 5, 10, 15, 20)]
        assert rates == sorted(rates) and len(set(rates)) == 5

    def test_db_fejl_falder_tilbage_paa_prior_uden_at_kaste(self):
        with patch.object(ex, "_recent_outcomes", side_effect=RuntimeError("db nede")):
            pass  # side_effect på lambda-erstatning testes via _recent_outcomes selv
        with patch("core.runtime.db_core.connect", side_effect=RuntimeError("db nede")):
            assert ex._recent_outcomes("m", lookback=10) == (0, 0)


class TestLegacyFilter:
    def test_den_defekte_signatur_genkendes(self):
        """0.6 kan pr. konstruktion aldrig udsendes igen → alle 0.6-rækker er gamle."""
        assert ex.is_legacy_degenerate(0.6) is True

    def test_den_doede_zone_kan_ikke_udsende_0_6(self):
        assert ex.expectation_verdict(0.6, "success") is None
        assert ex.expectation_verdict(0.6, "failure") is None

    def test_aegte_raekker_filtreres_ikke_væk(self):
        for p in (0.2, 0.5, 0.85, 0.98):
            assert ex.is_legacy_degenerate(p) is False

    def test_uparsbar_vaerdi_filtreres_ikke(self):
        assert ex.is_legacy_degenerate("ikke et tal") is False
