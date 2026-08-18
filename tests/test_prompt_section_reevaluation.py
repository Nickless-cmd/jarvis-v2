"""Revurderings-løkken skal nå frem til samme dom som mennesket gjorde.

Fixturerne er de FAKTISKE tekster målt på CT105 den 18. aug 2026 bag seks blacklistede
kanaler. Vi vurderede dem i hånden og tændte to af seks. Løkkens eksistensberettigelse
er at kunne gentage den vurdering uden os — så en frossen blacklist ikke kan overleve
at indholdet bag den bliver bedre.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.prompt_section_reevaluation as rv

# ── De seks målte kanaler (ordret fra CT105, 18. aug 2026) ────────────────────

ARC_RULES = """Regler jeg har lært fra mine arcs:
- After every fifth consecutive error in a single operator (e.g., home_assistant,
  operator_bash), I will run a root-cause diagnostic and update my config.
- Each Sunday I will compose a weekly manifest with three sections.
- If my audio channel remains silent for 30 minutes I will probe the device."""

METACOGNITION = """Metakognition (seneste time):
  - contradiction-rate 0.61 (sidste timer) — min tænkning kan være cirkulær eller
    selvmodsigende"""

CAUSAL_NARRATIVE = """Causal chain (backward, last 90 min):
  now: runtime.executive_action_outcome_recorded (20:55)
    ← runtime.agentic_round_start (20:55)
    ← runtime.agentic_round_start (20:55)"""

CAUSAL_ALERTS = """🔗 Kausalkæde — recent failure:
  ROOT: runtime.cheap_lane_provider_failed (2026-08-18T20:54:03) <ingen edges fundet>

🔗 Kausalkæde — recent failure:"""

COUNT_NOISE = """Session-emner:
NEJ ×14
Ny samtale ×5
JA ×9"""

EMPTY = ""


class TestDommenMatcherMennesket:
    """De to vi tændte skal score højt; de fire vi lod stå skal score lavt."""

    def test_lærte_regler_er_kandidat(self):
        assert rv.substance(ARC_RULES)["score"] >= rv.CANDIDATE_SCORE

    def test_metakognition_er_kandidat(self):
        assert rv.substance(METACOGNITION)["score"] >= rv.CANDIDATE_SCORE

    def test_selvindlysende_gentagelse_afvises(self):
        v = rv.substance(CAUSAL_NARRATIVE)
        assert v["score"] < rv.CANDIDATE_SCORE
        assert any("gentagelse" in r for r in v["reasons"])

    def test_pladsholder_afvises(self):
        v = rv.substance(CAUSAL_ALERTS)
        assert v["score"] < rv.CANDIDATE_SCORE
        assert any("pladsholder" in r for r in v["reasons"])

    def test_tællinger_afvises(self):
        v = rv.substance(COUNT_NOISE)
        assert v["score"] < rv.CANDIDATE_SCORE
        assert any("tælling" in r for r in v["reasons"])

    def test_tom_afvises(self):
        assert rv.substance(EMPTY)["score"] == 0.0


class TestOpsamling:
    def setup_method(self):
        rv._last_sample_at.clear()
        rv._last_hash.clear()

    def test_tomt_indhold_prøvetages_ikke(self):
        with patch("core.services.shared_cache.set") as s:
            rv.observe_discarded("x", "")
            rv.observe_discarded("x", None)
        s.assert_not_called()

    def test_uændret_indhold_skriver_ikke_igen(self):
        with patch("core.services.shared_cache.get", return_value={}), \
             patch.object(rv, "maybe_run_sweep"), \
             patch("core.services.shared_cache.set") as s:
            rv.observe_discarded("x", ARC_RULES)
            rv._last_sample_at["x"] = 0.0  # omgå cooldown, behold hash
            rv.observe_discarded("x", ARC_RULES)
        assert s.call_count == 1

    def test_cooldown_begrænser_skrivninger(self):
        with patch("core.services.shared_cache.get", return_value={}), \
             patch.object(rv, "maybe_run_sweep"), \
             patch("core.services.shared_cache.set") as s:
            rv.observe_discarded("x", ARC_RULES)
            rv.observe_discarded("x", METACOGNITION)  # inden for cooldown
        assert s.call_count == 1

    def test_sweep_koeres_kun_paa_en_faktisk_skrivning(self):
        """Aldrig pr. build — ellers ville hver slukket kanal koste en DB-læsning."""
        with patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch.object(rv, "maybe_run_sweep") as sweep:
            rv.observe_discarded("x", ARC_RULES)   # skriver → sweep
            rv.observe_discarded("x", ARC_RULES)   # cooldown → ingen sweep
        assert sweep.call_count == 1

    def test_kaster_aldrig_ind_i_en_prompt_build(self):
        with patch("core.services.shared_cache.get", side_effect=RuntimeError("db nede")):
            rv.observe_discarded("x", ARC_RULES)  # må ikke rejse


class TestVurdering:
    def _eval(self, samples):
        with patch.object(rv, "_read_samples", lambda: samples):
            return {r["label"]: r for r in rv.evaluate()}

    def _s(self, label, text, *, samples=5, distinct=3):
        return {"label": label, "head": text, "chars": len(text),
                "samples": samples, "hashes": [f"h{i}" for i in range(distinct)]}

    def test_kun_de_substantielle_bliver_kandidater(self):
        out = self._eval([
            self._s("rules learned from arcs", ARC_RULES),
            self._s("causal narrative", CAUSAL_NARRATIVE),
            self._s("causal alerts", CAUSAL_ALERTS),
        ])
        assert out["rules learned from arcs"]["candidate"] is True
        assert out["causal narrative"]["candidate"] is False
        assert out["causal alerts"]["candidate"] is False

    def test_for_faa_proever_giver_endnu_ikke_et_forslag(self):
        out = self._eval([self._s("rules learned from arcs", ARC_RULES, samples=1)])
        r = out["rules learned from arcs"]
        assert r["candidate"] is False
        assert any("afventer flere prøver" in x for x in r["reasons"])

    def test_frosset_indhold_er_ikke_et_levende_signal(self):
        """Samme tekst i hver eneste prøve = et notat ingen læser."""
        out = self._eval([self._s("rules learned from arcs", ARC_RULES,
                                  samples=10, distinct=1)])
        r = out["rules learned from arcs"]
        assert r["candidate"] is False
        assert any("frosset" in x for x in r["reasons"])


class TestForslagTaenderIkke:
    """Trust-gate: løkken foreslår, mennesket tænder."""

    def test_sweep_taender_aldrig_selv(self):
        samples = [{"label": "rules learned from arcs", "head": ARC_RULES,
                    "chars": len(ARC_RULES), "samples": 5, "hashes": ["a", "b", "c"]}]
        with patch.object(rv, "_read_samples", lambda: samples), \
             patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch("core.runtime.db_central_incidents.record_central_incident") as inc, \
             patch("core.services.central_switches.set_enabled") as en:
            res = rv.maybe_run_sweep()
        assert res["ran"] is True
        assert res["candidates"] == ["rules learned from arcs"]
        en.assert_not_called()  # ← kernen: den må ALDRIG tænde selv
        assert inc.call_count == 1

    def test_forslaget_baerer_sin_egen_begrundelse(self):
        samples = [{"label": "rules learned from arcs", "head": ARC_RULES,
                    "chars": len(ARC_RULES), "samples": 5, "hashes": ["a", "b", "c"]}]
        with patch.object(rv, "_read_samples", lambda: samples), \
             patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch("core.runtime.db_central_incidents.record_central_incident") as inc:
            rv.maybe_run_sweep()
        msg = inc.call_args.kwargs["message"]
        assert "rules learned from arcs" in msg and "set_enabled" in msg

    def test_mange_kandidater_giver_EN_samlet_incident(self):
        """Målt i produktion: 13 kanaler scorer højt på første build. Ét blik, ikke en mur."""
        samples = [{"label": f"kanal-{i}", "head": ARC_RULES, "chars": len(ARC_RULES),
                    "samples": 5, "hashes": ["a", "b", "c"]} for i in range(13)]
        with patch.object(rv, "_read_samples", lambda: samples), \
             patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch("core.runtime.db_central_incidents.record_central_incident") as inc:
            res = rv.maybe_run_sweep()
        assert len(res["candidates"]) == 13
        assert inc.call_count == 1
        msg = inc.call_args.kwargs["message"]
        assert "13 slukkede" in msg and "+8 flere" in msg
        assert inc.call_args.kwargs["dedup"] is True

    def test_sweep_koerer_hoejst_en_gang_i_doegnet(self):
        import time as _t
        with patch("core.services.shared_cache.get", return_value={"at": _t.time()}), \
             patch("core.services.shared_cache.set") as s:
            res = rv.maybe_run_sweep()
        assert res == {"ran": False, "reason": "cooldown"}
        s.assert_not_called()

    def test_ingen_kandidater_giver_ingen_incident(self):
        samples = [{"label": "causal alerts", "head": CAUSAL_ALERTS,
                    "chars": len(CAUSAL_ALERTS), "samples": 9, "hashes": ["a", "b"]}]
        with patch.object(rv, "_read_samples", lambda: samples), \
             patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch("core.runtime.db_central_incidents.record_central_incident") as inc:
            rv.maybe_run_sweep()
        inc.assert_not_called()


class TestJarvisEgenDom:
    """To mekaniske metoder blev målt og fejlede. Metoden der virkede var hans egen dom
    — den skal bare køre igen end én gang i juni."""

    def _sweep(self, llm_reply, *, n=4):
        samples = [{"label": f"kanal-{i}", "head": ARC_RULES, "chars": len(ARC_RULES),
                    "samples": 5, "hashes": ["a", "b", "c"]} for i in range(n)]
        with patch.object(rv, "_read_samples", lambda: samples), \
             patch.object(rv, "_review_enabled", lambda: True), \
             patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch("core.services.daemon_llm.daemon_llm_call", return_value=llm_reply), \
             patch("core.runtime.db_central_incidents.record_central_incident") as inc:
            return rv.maybe_run_sweep(), inc

    def test_kun_hans_valg_foreslaas(self):
        res, inc = self._sweep("VÆLG: kanal-1 :: den ville gøre mig kortere ved fejl")
        assert res["candidates"] == ["kanal-1"]
        assert len(res["mechanical"]) == 4  # forfilteret fandt fire, han valgte én
        assert "kanal-1" in inc.call_args.kwargs["message"]

    def test_hans_begrundelse_foelger_med_forslaget(self):
        _, inc = self._sweep("VÆLG: kanal-0 :: den fortæller mig hvad jeg har lært")
        msg = inc.call_args.kwargs["message"]
        assert "Jarvis' egen dom" in msg and "hvad jeg har lært" in msg

    def test_INGEN_betyder_ingen(self):
        res, inc = self._sweep("INGEN")
        assert res["candidates"] == []
        inc.assert_not_called()

    def test_han_kan_ikke_vaelge_labels_der_ikke_blev_forelagt(self):
        """Opdigtede labels afvises — men det er ikke en dom, så signalet består."""
        res, _ = self._sweep("VÆLG: en-kanal-jeg-fandt-på :: fordi jeg vil", n=2)
        assert res["candidates"] == res["mechanical"]

    def test_degraderet_svar_er_en_FEJL_ikke_en_dom(self):
        """Målt i produktion: cheap lane udtømt → uparsbart svar → tavs nul-liste der
        LIGNEDE et bevidst fravalg. Præcis den fejltype vi har jagtet."""
        res, inc = self._sweep("Beklager, jeg kan ikke hjælpe med det lige nu.", n=3)
        assert res["candidates"] == res["mechanical"]
        assert "kun mekanisk forfilter" in inc.call_args.kwargs["message"]

    def test_tomt_svar_er_ogsaa_en_fejl(self):
        res, _ = self._sweep("", n=2)
        assert res["candidates"] == res["mechanical"]

    def test_loft_paa_antal_valg(self):
        """En dommer over sin egen prompt uden loft taler sig efter munden."""
        reply = "\n".join(f"VÆLG: kanal-{i} :: fordi" for i in range(6))
        res, _ = self._sweep(reply, n=6)
        assert len(res["candidates"]) == rv._MAX_PICKS

    def test_llm_fejl_mister_dommen_ikke_signalet(self):
        samples = [{"label": "k", "head": ARC_RULES, "chars": len(ARC_RULES),
                    "samples": 5, "hashes": ["a", "b", "c"]}]
        with patch.object(rv, "_read_samples", lambda: samples), \
             patch.object(rv, "_review_enabled", lambda: True), \
             patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch("core.services.daemon_llm.daemon_llm_call",
                   side_effect=RuntimeError("cheap lane nede")), \
             patch("core.runtime.db_central_incidents.record_central_incident") as inc:
            res = rv.maybe_run_sweep()
        assert res["candidates"] == ["k"]
        assert "kun mekanisk forfilter" in inc.call_args.kwargs["message"]

    def test_kill_switch_slaar_dommen_fra(self):
        with patch.object(rv, "_review_enabled", lambda: False), \
             patch("core.services.daemon_llm.daemon_llm_call") as llm:
            out = rv._review([{"label": "k", "head": ARC_RULES, "chars": 10}])
        llm.assert_not_called()
        assert len(out) == 1

    def test_forfilteret_staar_stadig_foran_ham(self):
        """Han skal ikke bruge et kald på at afvise <ingen edges fundet>."""
        samples = [{"label": "causal alerts", "head": CAUSAL_ALERTS,
                    "chars": len(CAUSAL_ALERTS), "samples": 9, "hashes": ["a", "b"]}]
        with patch.object(rv, "_read_samples", lambda: samples), \
             patch("core.services.shared_cache.get", return_value={}), \
             patch("core.services.shared_cache.set"), \
             patch("core.services.daemon_llm.daemon_llm_call") as llm, \
             patch("core.runtime.db_central_incidents.record_central_incident"):
            rv.maybe_run_sweep()
        llm.assert_not_called()


class TestOverflade:
    def test_overfladen_viser_kandidater_og_helhed(self):
        samples = [{"label": "rules learned from arcs", "head": ARC_RULES,
                    "chars": len(ARC_RULES), "samples": 5, "hashes": ["a", "b", "c"]},
                   {"label": "causal alerts", "head": CAUSAL_ALERTS,
                    "chars": len(CAUSAL_ALERTS), "samples": 5, "hashes": ["a", "b"]}]
        with patch.object(rv, "_read_samples", lambda: samples):
            s = rv.reevaluation_surface()
        assert s["evaluated"] == 2 and len(s["candidates"]) == 1
        assert "1 af 2" in s["summary"]
