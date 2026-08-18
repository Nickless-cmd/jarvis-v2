"""Selv-overraskelse skal kunne gå BEGGE veje — og ellers tie.

Rod (Bjørn 17. aug 2026): kaldsstedet sendte en hardkodet `expected_confidence=0.6`
ind i en gate der kræver `> 0.6`. Så `expected_success` var ALTID False → negativ
overraskelse (forventede succes, men fejlede) var matematisk umulig. DB: 19.698 af
19.698 overraskelser var `positive @ 0.6`.

Anden halvdel (18. aug): rettelsen gjorde negativ overraskelse mulig, men efterlod en
to-værdi-konstant uden død zone. `weak → 0.5` betød "jeg forventer at fejle", og da 98%
af alle runs lykkes, blev hver succes til en overraskelse — 54 nye på ét døgn, stadig
nul negative. Forventningen er nu empirisk, og midterfeltet er stumt.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.self_surprise_detection as ss


def _detect(**kw):
    # Undgå DB-skrivning: mock persist + eventbus.
    with patch.object(ss, "insert_cognitive_self_surprise", lambda **k: dict(k)), \
         patch.object(ss, "event_bus"):
        return ss.detect_self_surprise(**kw)


class TestBeggeRetninger:
    def test_negativ_overraskelse_er_mulig(self):
        """Høj forventning + fejl = negativ overraskelse (var umulig før 17. aug)."""
        r = _detect(expected_confidence=0.9, actual_outcome="error", domain="d")
        assert r is not None and r["surprise_type"] == "negative"

    def test_positiv_overraskelse_kraever_nu_aegte_fejlforventning(self):
        """0.5 var ikke en forventning om fejl — det var fravær af forventning."""
        assert _detect(expected_confidence=0.5, actual_outcome="completed") is None
        r = _detect(expected_confidence=0.2, actual_outcome="completed", domain="d")
        assert r is not None and r["surprise_type"] == "positive"

    def test_forventet_succes_giver_ingen_overraskelse(self):
        assert _detect(expected_confidence=0.9, actual_outcome="completed") is None

    def test_forventet_fejl_giver_ingen_overraskelse(self):
        assert _detect(expected_confidence=0.2, actual_outcome="error") is None

    def test_den_gamle_konstant_er_nu_stum_i_begge_retninger(self):
        """0.6 var buggens signatur. Den ligger nu midt i den døde zone."""
        assert _detect(expected_confidence=0.6, actual_outcome="error") is None
        assert _detect(expected_confidence=0.6, actual_outcome="completed") is None


class TestAfbrudteRuns:
    def test_afbrudt_run_overrasker_aldrig(self):
        """Bjørn trykker stop → hverken bevis eller overraskelse."""
        for status in ("cancelled", "interrupted", "aborted"):
            assert _detect(expected_confidence=0.95, actual_outcome=status) is None
            assert _detect(expected_confidence=0.05, actual_outcome=status) is None


class TestUdledtForventning:
    def test_forventningen_udledes_naar_den_ikke_gives(self):
        """Kaldsstedet sender `model`, ikke en konstant."""
        with patch.object(ss, "expected_success_rate", return_value=0.98) as m:
            r = _detect(model="glm-5.2:cloud", actual_outcome="failed", domain="d")
        m.assert_called_once_with("glm-5.2:cloud")
        assert r is not None and r["surprise_type"] == "negative"

    def test_udledt_forventning_i_doed_zone_tier(self):
        with patch.object(ss, "expected_success_rate", return_value=0.5):
            assert _detect(model="ny-model", actual_outcome="completed") is None

    def test_eksplicit_forventning_vinder_over_udledning(self):
        with patch.object(ss, "expected_success_rate", return_value=0.98) as m:
            assert _detect(expected_confidence=0.5, actual_outcome="failed") is None
        m.assert_not_called()


class TestOverflade:
    def _surface(self, rows):
        with patch.object(ss, "list_cognitive_self_surprises", lambda limit: rows):
            return ss.build_self_surprise_surface()

    def test_defekte_raekker_vises_ikke_som_nuvaerende_tilstand(self):
        """De 19.731 gamle 0.6-rækker må ikke fylde overfladen for evigt."""
        rows = [{"surprise_type": "positive", "expected_confidence": 0.6} for _ in range(30)]
        s = self._surface(rows)
        assert s["items"] == [] and s["active"] is False
        assert s["legacy_suppressed"] == 30

    def test_aegte_raekker_overlever_filteret(self):
        rows = [{"surprise_type": "negative", "expected_confidence": 0.94}]
        s = self._surface(rows)
        assert len(s["items"]) == 1 and s["negative_count"] == 1
        assert s["legacy_suppressed"] == 0

    def test_blandet_historik_viser_kun_de_aegte(self):
        rows = [{"surprise_type": "positive", "expected_confidence": 0.6} for _ in range(20)]
        rows.insert(0, {"surprise_type": "negative", "expected_confidence": 0.91})
        s = self._surface(rows)
        assert len(s["items"]) == 1 and s["items"][0]["surprise_type"] == "negative"
