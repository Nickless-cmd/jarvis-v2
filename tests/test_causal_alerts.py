"""En alarm må ikke annoncere sin egen tomhed.

Målt 18. aug 2026: hele `causal_alerts`-sektionen (234 tegn) bestod af pladsholdere —
"🔗 Kausalkæde — recent failure: ROOT: … <ingen edges fundet>". Sektionen fortalte at
den havde fundet en kausalkæde, og derefter at den ikke havde. Den er blacklistet som
diagnostisk støj, og det var den også: støjen var selvskabt.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.prompt_sections.causal_alerts as ca

_FAIL = {"id": 42, "kind": "runtime.cheap_lane_provider_failed",
         "created_at": "2026-08-18T20:54:03Z", "payload_json": "{}"}


def _chain(steps):
    return {"chain": steps}


class TestTomKaedeTier:
    def test_ingen_kanter_giver_tom_streng(self):
        with patch("core.services.causal_graph.query_causal_chain",
                   return_value=_chain([])):
            assert ca._format_chain_for_failure(_FAIL) == ""

    def test_pladsholderen_findes_ikke_laengere(self):
        with patch("core.services.causal_graph.query_causal_chain",
                   return_value=_chain([])):
            out = ca._format_chain_for_failure(_FAIL)
        assert "ingen edges" not in out and "Kausalkæde" not in out

    def test_sektionen_bliver_helt_tom_naar_alle_kaeder_er_tomme(self):
        """Før: headeren stod alene ×N. Nu: sektionen udsendes slet ikke."""
        with patch.object(ca, "_fetch_recent_failures", return_value=[_FAIL, _FAIL]), \
             patch("core.services.causal_graph.query_causal_chain",
                   return_value=_chain([])):
            assert ca.causal_alerts_section() == ""


class TestÆgteKaedeBevares:
    def test_kaede_med_kanter_udsendes(self):
        steps = [{"event": {"kind": "runtime.agentic_round_start",
                            "created_at": "2026-08-18T20:53:00Z"}}]
        with patch("core.services.causal_graph.query_causal_chain",
                   return_value=_chain(steps)):
            out = ca._format_chain_for_failure(_FAIL)
        assert "Kausalkæde" in out
        assert "ROOT: runtime.cheap_lane_provider_failed" in out
        assert "runtime.agentic_round_start" in out

    def test_blandet_tom_og_aegte_beholder_kun_den_aegte(self):
        steps = [{"event": {"kind": "runtime.tool_failed", "created_at": "2026-08-18T20:00:00Z"}}]
        calls = {"n": 0}

        def _q(**kw):
            calls["n"] += 1
            return _chain(steps if calls["n"] == 1 else [])

        with patch.object(ca, "_fetch_recent_failures", return_value=[_FAIL, _FAIL]), \
             patch("core.services.causal_graph.query_causal_chain", side_effect=_q):
            out = ca.causal_alerts_section()
        assert out.count("Kausalkæde") == 1, "kun den kæde der faktisk har kanter"


class TestSelvSikker:
    def test_ingen_fejl_giver_tom_sektion(self):
        with patch.object(ca, "_fetch_recent_failures", return_value=[]):
            assert ca.causal_alerts_section() == ""

    def test_fetch_fejl_kaster_ikke_ind_i_prompten(self):
        with patch.object(ca, "_fetch_recent_failures", side_effect=RuntimeError("db")):
            assert ca.causal_alerts_section() == ""
