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
    def test_default_er_live(self):
        """2026-09-04 (blok E): var shadow "bevis før tillid" — men i shadow
        skrives der ingen rækker, så beviset kunne aldrig opstå:
        central_dream_actions har haft NUL rækker siden filen blev skrevet.
        Vinduet er stadig smalt (én mekanisme, tre pr. tick, auto-stop efter
        fem fejl) — det kan bare måles nu."""
        with patch("core.runtime.db.get_runtime_state_value", return_value=None):
            assert ex.mode() == "live"

    def test_ukendt_vaerdi_falder_til_live(self):
        with patch("core.runtime.db.get_runtime_state_value", return_value="banan"):
            assert ex.mode() == "live"

    def test_db_fejl_falder_til_live(self):
        with patch("core.runtime.db.get_runtime_state_value", side_effect=RuntimeError):
            assert ex.mode() == "live"

    def test_shadow_kan_stadig_vaelges(self):
        """Kill-switchen virker begge veje — sæt nøglen til shadow eller off."""
        with patch("core.runtime.db.get_runtime_state_value", return_value="shadow"):
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


class TestKontrakten:
    """Hypotesens EGEN præregistrerede påstand går forud for P-tærsklen.

    Målt 4/11-2026: 392/392 handlinger havde en udfyldt kontrakt, 392/392 sagde
    "gentager sig over baseline", og 306 opfyldte den allerede — men dommeren
    målte om overgangen var blevet 5 % af ALLE overgange fra X. En hypotese kan
    ikke afgøres af en måling den ikke fremsatte.
    """

    def _adj(self, prob, total, kontrakt=None):
        with patch("core.services.central_sequence.transition_prob", return_value=prob), \
             patch("core.services.central_sequence._from_total", return_value=total), \
             patch("core.runtime.db.connect"):
            return ex.adjudicate("a", "b", kontrakt=kontrakt)

    def test_opfyldt_kontrakt_doemmes_ikke_som_stoej(self):
        """P siger 0.005 — den gamle dom ville være 'noise'. Kontrakten siger 5/5."""
        v = self._adj(0.005, 583, {"krav": 5, "jordet": 5})
        assert v["verdict"] == "contract_met", v
        assert v["prob"] == 0.005, "P skal bevares som sekundær kontekst"

    def test_uopfyldt_kontrakt_giver_undecided_ikke_stoej(self):
        """4/5 er ikke 'det var støj' — det er 'kriteriet er ikke nået endnu'."""
        v = self._adj(0.005, 583, {"krav": 5, "jordet": 4})
        assert v["verdict"] == "undecided", v
        assert "4/5" in v["reason"]

    def test_kontrakten_slaar_ogsaa_regime(self):
        """Også en 'regime'-dom må vige: kontrakten er hypotesens egen påstand."""
        assert self._adj(0.12, 583, {"krav": 5, "jordet": 4, "modsagt": 0})["verdict"] == "undecided"

    def test_modbevist_kontrakt_doemmes_som_contradicted(self):
        """Fem jordede MODSIGELSER er lige så afgørende som fem bekræftelser.

        Målt 4/11-2026: 580 hypoteser havde fuld modsigende evidens og blev aldrig
        dømt — de blev hængende i 'undecided' indtil TTL udløb. En dommer der kun
        kan sige 'ja' og 'ved det ikke' kan ikke falsificere noget.
        """
        v = self._adj(0.005, 583, {"krav": 5, "jordet": 0, "modsagt": 5,
                                   "modsigelse_praeregistreret": True})
        assert v["verdict"] == "contradicted", v
        assert "5" in v["reason"] and "modsig" in v["reason"]

    def test_modsigelse_uden_praeregistrering_doemmer_ikke(self):
        """Modsigelses-reglen skal være PRÆREGISTRERET, ikke en overraskelse.

        Målt 4/11-2026: kun 11 af 586 aktive kontrakter nævner en modsigelse som
        kriterium. De øvrige 575 kræver blot N støttende observationer og siger
        intet om hvad der sker ved N modsigelser — så dommeren må ikke opfinde
        den regel for dem. Ellers får 96 % en dom de aldrig fremsatte.
        """
        v = self._adj(0.005, 583, {"krav": 5, "jordet": 0, "modsagt": 5,
                                   "modsigelse_praeregistreret": False})
        assert v["verdict"] == "undecided", v

    def test_modsigelser_under_kravet_er_stadig_undecided(self):
        """4 modsigelser af 5 er ikke nok til at dræbe hypotesen — endnu."""
        v = self._adj(0.005, 583, {"krav": 5, "jordet": 0, "modsagt": 4,
                                   "modsigelse_praeregistreret": True})
        assert v["verdict"] == "undecided", v

    def test_stoettende_vejer_foerst_naar_begge_naar_kravet(self):
        """Er begge sider på kravet, er hypotesen modbevist — ellers kunne en
        hypotese med 5 modsigelser overleve på 5 bekræftelser."""
        v = self._adj(0.005, 583, {"krav": 5, "jordet": 5, "modsagt": 5,
                                   "modsigelse_praeregistreret": True})
        assert v["verdict"] == "contradicted", v

    def test_flere_stoettende_end_modsigende_er_opfyldt(self):
        """Kontrakten siger 'UDEN LIGE SÅ MANGE der modsiger' — 7 mod 5 opfylder den.

        Reglen var tidligere 'modsagt >= krav', som dømte denne hypotese modbevist
        på et kriterium dens egen kontrakt kalder opfyldt. Målt 4/11-2026: ingen
        aktiv hypotese ramte tilfældet, men reglen var forkert.
        """
        v = self._adj(0.005, 583, {"krav": 5, "jordet": 7, "modsagt": 5,
                                   "modsigelse_praeregistreret": True})
        assert v["verdict"] == "contract_met", v

    def test_flag_kraever_den_relationelle_formel(self):
        """Flaget må ikke sættes på et løst ord-match.

        'modsigelser registreres separat' nævner modsigelse uden at gøre den til et
        falsifikationskriterium. Kun 'uden lige så mange' (eller en eksplicit
        falsificer-hvis-formel) hjemler contradicted-dommen.
        """
        loest = ex._kontrakt_af({"sample_size": "5", "success_criterion":
                                 "5 støttende observationer; modsigelser registreres separat",
                                 "jordede_samples": {"stottende": 5, "modsigende": 0}})
        assert loest is not None and loest["modsigelse_praeregistreret"] is False, loest

        praecis = ex._kontrakt_af({"sample_size": "5", "success_criterion":
                                   "mindst 5 observationer der understøtter forudsigelsen, "
                                   "uden lige så mange der modsiger den.",
                                   "jordede_samples": {"stottende": 5, "modsigende": 0}})
        assert praecis is not None and praecis["modsigelse_praeregistreret"] is True, praecis

    def test_uden_kontrakt_er_dommen_uaendret(self):
        """Bagudkompatibel: hypoteser uden læsbar kontrakt dømmes som før."""
        assert self._adj(0.005, 583)["verdict"] == "noise"
        assert self._adj(0.12, 583)["verdict"] == "regime"

    def test_ugyldig_kontrakt_falder_til_frekvensdom(self):
        for k in (None, {}, {"krav": 0, "jordet": 5}, {"krav": 5, "jordet": None},
                  {"krav": "5", "jordet": 5}):
            assert self._adj(0.005, 583, k)["verdict"] == "noise", k

    def test_kontrakt_laeses_fra_sample_size_og_jordede(self):
        assert ex._kontrakt_af({"sample_size": "5",
                                "jordede_samples": {"stottende": 4, "modsigende": 1}}) == \
            {"krav": 5, "jordet": 4, "modsagt": 1, "modsigelse_praeregistreret": False}
        assert ex._kontrakt_af({"sample_size": "5"}) is None
        assert ex._kontrakt_af({"sample_size": None,
                                "jordede_samples": {"stottende": 4, "modsigende": 0}}) is None
        assert ex._kontrakt_af({"sample_size": "0",
                                "jordede_samples": {"stottende": 4, "modsigende": 0}}) is None
        # Den gamle form (et rent tal) må ikke læses som en kontrakt: uden
        # opdelingen kan dommeren ikke se om evidensen støtter eller modsiger.
        assert ex._kontrakt_af({"sample_size": "5", "jordede_samples": 4}) is None

    def test_modsigelses_reglen_laeses_fra_kontrakten(self):
        """Flaget må ikke gættes — det skal stå i hypotesens eget kriterium.

        Målt 4/11-2026: 560 af 586 aktive kontrakter kræver blot N støttende
        observationer og nævner ingen modsigelse. Kun 11 gør. Dommeren må kun
        anvende modsigelses-reglen for dem der selv har skrevet den.
        """
        uden = ex._kontrakt_af({
            "sample_size": "5", "success_criterion":
                ">= 5 jordede observationer af at overgangen gentager sig over baseline",
            "jordede_samples": {"stottende": 0, "modsigende": 5}})
        assert uden["modsigelse_praeregistreret"] is False

        med = ex._kontrakt_af({
            "sample_size": "5", "success_criterion":
                "mindst 5 observationer der understøtter forudsigelsen, uden lige så "
                "mange der modsiger den",
            "jordede_samples": {"stottende": 0, "modsigende": 5}})
        assert med["modsigelse_praeregistreret"] is True

    def test_jordede_samples_taeller_kun_jordede(self, isolated_runtime):
        """Feltet `grounded_samples` tæller ALLE samples (målt 698/698 rækker).
        Denne funktion tæller kun dem der faktisk er jordet — og deler dem op i
        støttende og modsigende, så dommen kan sige begge veje."""
        import core.services.central_dream_action as cda
        from core.runtime.db_core import connect
        with connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS central_hypothesis_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT, hyp_id TEXT, supports INTEGER,
                falsifies INTEGER, source TEXT, ground_ref TEXT, triggered_by TEXT,
                created_at TEXT)""")
            for sup, fal, ref in ((1, 0, "r1"), (1, 0, "r2"), (0, 1, "r3"),
                                  (1, 0, ""), (1, 0, None)):
                c.execute("INSERT INTO central_hypothesis_samples "
                          "(hyp_id, supports, falsifies, ground_ref, created_at) "
                          "VALUES (?,?,?,?,'x')", ("h1", sup, fal, ref))
            c.commit()
            assert cda._jordede_samples(c, "h1") == {"stottende": 2, "modsigende": 1}
            assert cda._jordede_samples(c, "findes-ikke") == {"stottende": 0, "modsigende": 0}

    def test_jordede_samples_gaetter_ikke_naar_det_ikke_kan_maales(self, isolated_runtime):
        """Kan tabellen ikke læses, er svaret None — ikke 0. Et gæt på 0 ville
        se ud som 'kontrakten er langt fra opfyldt'."""
        import core.services.central_dream_action as cda
        from core.runtime.db_core import connect
        with connect() as c:
            assert cda._jordede_samples(c, "h1") is None


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


class TestProvenanceNaarFrem:
    """Uden mekanismen kan allowlisten ikke skelne — og filtrerer så ALT fra.

    Målt 19. aug 2026: eksekutoren overvejede 12 kandidater og handlede på 0, fordi
    `select_actionable()` ikke hentede `provenance_json` i sin SELECT. Filteret virkede
    perfekt; det havde bare intet at filtrere på. En tavs nul-linje der lignede
    "ingen modne" i stedet for "jeg kan ikke se dem".
    """

    def test_select_actionable_henter_provenance(self):
        import inspect

        from core.services.central_dream_action import select_actionable
        src = inspect.getsource(select_actionable)
        assert "provenance_json" in src, (
            "uden provenance_json kan ingen forbruger se hypotesens mekanisme"
        )

    def test_executor_laeser_provenance_som_json_streng(self):
        """Rækken kommer fra DB som en JSON-STRENG, ikke et dict."""
        h = {"hyp_id": "h9", "confidence": 0.58, "grounded_samples": 4, "status": "active",
             "provenance_json": '{"mechanism": "prediction_error", "family": "x->y"}'}
        with patch.object(ex, "mode", return_value="live"), \
             patch("core.services.central_dream_action.select_actionable", return_value=[h]), \
             patch("core.services.central_dream_action.record_action",
                   return_value={"ok": True}) as rec, \
             patch.object(ex, "adjudicate",
                          return_value={"verdict": "regime", "prob": 0.2, "from_total": 50,
                                        "reason": "r"}), \
             patch.object(ex, "_observe_incident"):
            r = ex.run_once()
        assert r["acted"] == 1 and rec.call_count == 1
        assert r["results"][0]["from"] == "x" and r["results"][0]["to"] == "y"
