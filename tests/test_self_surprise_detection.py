"""Selv-overraskelse skal kunne gå BEGGE veje.

Rod (Bjørn 17. aug 2026): kaldsstedet sendte en hardkodet `expected_confidence=0.6`
ind i en gate der kræver `> 0.6`. Så `expected_success` var ALTID False → negativ
overraskelse (forventede succes, men fejlede) var matematisk umulig. DB: 19.698 af
19.698 overraskelser var `positive @ 0.6`. Fixet giver kalderen en ægte, varierende
forventning (model-styrke: strong→0.8, weak→0.5), så begge retninger kan fyre.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.self_surprise_detection as ss


def _detect(**kw):
    # Undgå DB-skrivning: mock persist + eventbus.
    with patch.object(ss, "insert_cognitive_self_surprise", lambda **k: dict(k)), \
         patch.object(ss, "event_bus") as _bus:
        return ss.detect_self_surprise(**kw)


class TestBeggeRetninger:
    def test_negativ_overraskelse_er_mulig(self):
        """Høj forventning + fejl = negativ overraskelse (var umulig før fixet)."""
        r = _detect(expected_confidence=0.8, actual_outcome="error", domain="d")
        assert r is not None and r["surprise_type"] == "negative"

    def test_positiv_overraskelse_stadig_mulig(self):
        r = _detect(expected_confidence=0.5, actual_outcome="completed", domain="d")
        assert r is not None and r["surprise_type"] == "positive"

    def test_forventet_succes_giver_ingen_overraskelse(self):
        assert _detect(expected_confidence=0.8, actual_outcome="completed") is None

    def test_forventet_fejl_giver_ingen_overraskelse(self):
        assert _detect(expected_confidence=0.4, actual_outcome="error") is None

    def test_den_gamle_konstant_kan_kun_gaa_positivt(self):
        """Dokumentér buggen: med expected=0.6 (gaten er `> 0.6`) kan KUN positiv fyre.
        Dette er grunden til at kalderen ikke længere må sende en konstant på grænsen."""
        assert _detect(expected_confidence=0.6, actual_outcome="error") is None  # negativ umulig
        assert _detect(expected_confidence=0.6, actual_outcome="completed")["surprise_type"] == "positive"
