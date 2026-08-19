"""Den ende af dream→action der manglede — og lagene der gør den forsvarlig.

Målt 19. aug 2026: `record_action()` havde NUL kaldere i hele repoet.
`central_dream_actions` havde derfor 0 rækker siden filen blev skrevet, mens
`change_rate()` viste 374 hypoteser i backlog og 0 handlinger på 7 dage.

Bjørn valgte auto-handling ("C") med forbeholdet *"så længe vi kan se alt og gribe ind
hvis nødvendigt"*. Testene her beskytter netop de forbehold: shadow som default, snæver
allowlist, loft pr. tick, synlighed, auto-stop — og at eksekutoren ALDRIG rører
hypotese-tabellen, som governance ejer.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.dream_action_executor as ex


def _hyp(hyp_id="h1", mechanism="prediction_error", family="a->b"):
    return {"hyp_id": hyp_id, "statement": "s", "confidence": 0.58, "grounded_samples": 4,
            "status": "active", "provenance": {"mechanism": mechanism, "family": family}}


class TestTilstand:
    def test_default_er_shadow_ikke_live(self):
        """Bevis før tillid — samme trust-gate som self_repair_engine."""
        with patch("core.runtime.db.get_runtime_state_value", return_value=None):
            assert ex.mode() == "shadow"

    def test_ukendt_vaerdi_falder_til_shadow(self):
        with patch("core.runtime.db.get_runtime_state_value", return_value="banan"):
            assert ex.mode() == "shadow"

    def test_db_fejl_falder_til_shadow(self):
        with patch("core.runtime.db.get_runtime_state_value", side_effect=RuntimeError):
            assert ex.mode() == "shadow"

    def test_off_gør_intet(self):
        with patch.object(ex, "mode", return_value="off"), \
             patch("core.services.central_dream_action.select_actionable") as sel:
            r = ex.run_once()
        sel.assert_not_called()
        assert r["acted"] == 0


class TestDommen:
    def _adj(self, prob, total):
        with patch("core.services.central_sequence.transition_prob", return_value=prob), \
             patch("core.services.central_sequence._from_total", return_value=total), \
             patch("core.runtime.db.connect"):
            return ex.adjudicate("a", "b")

    def test_regime_naar_sandsynligheden_er_steget(self):
        v = self._adj(0.12, 50)
        assert v["verdict"] == "regime" and v["prob"] == 0.12

    def test_stoej_naar_den_stadig_er_lav(self):
        assert self._adj(0.01, 50)["verdict"] == "noise"

    def test_for_tyndt_grundlag_giver_undecided(self):
        """Vi handler ikke på et gæt."""
        assert self._adj(0.9, 3)["verdict"] == "undecided"

    def test_maalefejl_giver_undecided_ikke_en_paastand(self):
        with patch("core.services.central_sequence.transition_prob",
                   side_effect=RuntimeError("db")):
            assert ex.adjudicate("a", "b")["verdict"] == "undecided"


class TestSnaeverAllowlist:
    def _run(self, cands, mode="live"):
        with patch.object(ex, "mode", return_value=mode), \
             patch("core.services.central_dream_action.select_actionable", return_value=cands), \
             patch("core.services.central_dream_action.record_action",
                   return_value={"ok": True, "action_id": 1}) as rec, \
             patch.object(ex, "adjudicate",
                          return_value={"verdict": "regime", "prob": 0.2, "from_total": 50,
                                        "reason": "r"}), \
             patch.object(ex, "_observe_incident"):
            return ex.run_once(), rec

    def test_kun_prediction_error_handles_paa(self):
        r, rec = self._run([_hyp(mechanism="stance_divergence"),
                            _hyp(mechanism="causal_convergence")])
        assert r["acted"] == 0
        rec.assert_not_called()

    def test_prediction_error_handles_paa(self):
        r, rec = self._run([_hyp()])
        assert r["acted"] == 1 and rec.call_count == 1

    def test_ugyldig_family_springes_over(self):
        r, rec = self._run([_hyp(family="uden-pil")])
        assert r["acted"] == 0
        rec.assert_not_called()


class TestLoftOgSikkerhed:
    def test_loft_pr_tick_holdes(self):
        cands = [_hyp(hyp_id=f"h{i}") for i in range(20)]
        with patch.object(ex, "mode", return_value="live"), \
             patch("core.services.central_dream_action.select_actionable", return_value=cands), \
             patch("core.services.central_dream_action.record_action",
                   return_value={"ok": True}), \
             patch.object(ex, "adjudicate",
                          return_value={"verdict": "regime", "prob": 0.2, "from_total": 50,
                                        "reason": "r"}), \
             patch.object(ex, "_observe_incident"):
            r = ex.run_once(limit=3)
        assert r["acted"] == 3, "en løbsk løkke må ikke kunne tømme backloggen"

    def test_shadow_skriver_ALDRIG(self):
        with patch.object(ex, "mode", return_value="shadow"), \
             patch("core.services.central_dream_action.select_actionable",
                   return_value=[_hyp()]), \
             patch("core.services.central_dream_action.record_action") as rec, \
             patch.object(ex, "adjudicate",
                          return_value={"verdict": "regime", "prob": 0.2, "from_total": 50,
                                        "reason": "r"}), \
             patch.object(ex, "_observe_incident") as inc:
            r = ex.run_once()
        rec.assert_not_called()
        assert r["results"][0]["applied"] is False
        assert inc.called, "shadow skal stadig være SYNLIG — ellers kan vi ikke bevise noget"

    def test_undecided_udloeser_ingen_handling(self):
        with patch.object(ex, "mode", return_value="live"), \
             patch("core.services.central_dream_action.select_actionable",
                   return_value=[_hyp()]), \
             patch("core.services.central_dream_action.record_action") as rec, \
             patch.object(ex, "adjudicate",
                          return_value={"verdict": "undecided", "reason": "tyndt"}):
            r = ex.run_once()
        rec.assert_not_called()
        assert r["acted"] == 0

    def test_handling_er_klient_synlig(self):
        with patch.object(ex, "mode", return_value="live"), \
             patch("core.services.central_dream_action.select_actionable",
                   return_value=[_hyp()]), \
             patch("core.services.central_dream_action.record_action",
                   return_value={"ok": True}), \
             patch.object(ex, "adjudicate",
                          return_value={"verdict": "regime", "prob": 0.2, "from_total": 50,
                                        "reason": "r"}), \
             patch("core.runtime.db_central_incidents.record_central_incident") as inc:
            ex.run_once()
        assert inc.call_count == 1
        kw = inc.call_args.kwargs
        assert kw["nerve"] == "dream_action_executor" and "h1" in kw["message"]

    def test_kaster_aldrig_ud_i_kalderen(self):
        with patch.object(ex, "mode", return_value="live"), \
             patch("core.services.central_dream_action.select_actionable",
                   side_effect=RuntimeError("db nede")), \
             patch.object(ex, "_bump_errors"):
            r = ex.run_once()
        assert r["acted"] == 0 and "error" in r


class TestRoererIkkeHypoteseTabellen:
    """Governance ejer status/confidence/resolution. To sandheder = dobbelt-bogføring."""

    def test_ingen_skrivning_til_central_hypotheses(self):
        src = open(ex.__file__, encoding="utf-8").read()
        for forbudt in ("UPDATE central_hypotheses", "INSERT INTO central_hypotheses",
                        "resolved_at", "DELETE FROM central_hypotheses"):
            assert forbudt not in src, f"eksekutoren må ikke røre hypotesen: {forbudt!r}"

    def test_skriver_kun_via_record_action(self):
        src = open(ex.__file__, encoding="utf-8").read()
        assert "record_action" in src
        assert "INSERT INTO" not in src, "al skrivning skal gå gennem record_action()"
