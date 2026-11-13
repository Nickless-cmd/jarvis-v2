"""Karaktererne skal have en AFLÆSNING og en KONSEKVENS — ikke kun en stemme.

Målt 13/11-2026, anden runde. Første runde koblede sentinel, dissent og redpill
på `central_consequence`. Denne runde fandt to nye defekter af samme form:

1. **Analysten ødelagde sit eget signal.** `central_ghost.analyze` runder
   `avg_sentence_len` til 1 decimal. 12,04 og 11,96 blev begge 12,0, så
   divergensen blev 0,0 % og karakteren konkluderede «jeg er den samme, om du
   ser på eller ej» — mens de rå data var forskellige (2.659 vs 3.147 sætninger,
   std 9,7 vs 8,4). En karakter der runder sit signal væk før den konkluderer,
   lyver uden at vide det.

2. **Støj-vetoet gjorde `land_decision` til en død gren.** Seks forskellige
   karakter-fund blev dømt STØJ i træk; kun dissent slap igennem, og det var
   tilfældigt — ordet «adlyde» ramte den risikable liste. Vetoet er bygget til
   Smiths FORMULEREDE mønstre. Et karakter-fund er MÅLT og bærer et tal.
   Derfor: evidens med et tal springer vetoet over, uden tal kører det som før.

3. **`logger` brugt i moduler uden en logger.** Ramt tre gange samme dag
   (sentinel, redpill, dissent, analyst, red_dress). En `logger.warning` inde i
   en `except`-gren kaster `NameError` — så fejlhåndteringen fejler højere end
   fejlen den skulle håndtere.
"""

from __future__ import annotations

import sqlite3
from unittest import mock

import pytest

from core.services import central_consequence as cc


# ── 1. Signalet må ikke rundes væk ──────────────────────────────────────────


class TestRaaAkser:
    def test_analyze_giver_raa_felter(self):
        from core.services.central_ghost import analyze
        prof = analyze(["En kort sætning. En noget længere sætning her. Kort."])
        assert "avg_sentence_len_exact" in prof, "divergens kan ikke regnes på en visningsværdi"
        assert "sentence_len_std_exact" in prof

    def test_raa_vaerdi_er_ikke_afrundet(self):
        from core.services.central_ghost import analyze
        # 4 ord + 5 ord + 6 ord = 15/3 = 5.0; med 4+5+6+7 = 22/4 = 5.5
        prof = analyze(["aa bb cc dd. ee ff gg hh ii. jj kk ll mm nn oo. pp qq rr ss tt uu vv."])
        assert prof["avg_sentence_len_exact"] == pytest.approx(5.5)
        # visningsfeltet må gerne være afrundet — men det er IKKE det samme felt
        assert prof["avg_sentence_len"] == 5.5


class TestDivergensenErAegte:
    def test_to_forskellige_tekstsæt_giver_ikke_nul(self, monkeypatch):
        """Kernen: 0,0 % var en falsk nul fordi begge grene blev rundet til 12,0."""
        from core.services import central_analyst as ca

        korte = ["En. To. Tre. Fire. Fem."] * 5
        lange = ["Dette er en meget længere sætning med mange ord i sig. " * 3] * 5
        monkeypatch.setattr(ca, "_texts", lambda *, autonomous, limit=60: (korte if not autonomous else lange))
        monkeypatch.setattr(ca, "_observe", lambda div: None)
        r = ca.measure_observer_effect()
        assert r["divergence_pct"] is not None
        assert r["divergence_pct"] > 0, "to forskellige tekster må ikke give 0,0 % divergens"

    def test_divergensen_baeres_af_den_stoerste_akse(self, monkeypatch):
        from core.services import central_analyst as ca
        monkeypatch.setattr(ca, "_texts", lambda *, autonomous, limit=60: (
            ["Kort. Meget kort."] if not autonomous
            else ["En lang og indviklet sætning med rigtig mange ord i sig som fortsætter og fortsætter."] * 3))
        monkeypatch.setattr(ca, "_observe", lambda div: None)
        r = ca.measure_observer_effect()
        assert r["bearing_axis"] in ("saetningslaengde", "variation")
        assert r["axes"][r["bearing_axis"]] == r["divergence_pct"]


# ── 2. Spor vs. forpligtelse ────────────────────────────────────────────────


class TestSporIkkeForpligtelse:
    def test_observer_effekt_skriver_spor_ikke_forpligtelse(self, monkeypatch):
        """Dommeren har ret: en sproglig observation er ikke en adfærdsregel.

        Målt: fire formuleringer af observer-effekten blev dømt STØJ, og det er
        korrekt — «en ren sproglig gentagelse er aldrig ægte». Fundet skal derfor
        i et reviderbart spor, ikke tvinges ind i en bindende forpligtelse.
        """
        from core.services import central_analyst as ca
        kaldt: list[str] = []
        monkeypatch.setattr(ca, "_texts", lambda *, autonomous, limit=60: (
            ["Kort."] if not autonomous else ["En meget længere sætning med mange ord i sig her."] * 3))
        monkeypatch.setattr(ca, "_observe", lambda div: None)
        monkeypatch.setattr(cc, "record", lambda cid, subj, **kw: kaldt.append("record") or {"applied": False})
        monkeypatch.setattr(cc, "land_decision", lambda *a, **kw: kaldt.append("decision") or {})
        ca.measure_observer_effect()
        assert "decision" not in kaldt, "en sproglig observation må ikke blive en bindende regel"


# ── 3. Vetoet må ikke gøre landingen til en død gren ────────────────────────


class TestVetoIkkeDoedGren:
    def test_evidens_med_tal_springer_vetoet_over(self, monkeypatch):
        """Målt: seks karakter-fund dømt STØJ i træk. Vetoet ser FORM, ikke MÅLING.

        (13/11-2026) Opdateret: en måling kræver nu OGSÅ en navngivet kilde —
        se `test_bart_ciffer_er_ikke_maalt`. Uden kilden er `severity=2` blot
        en sætning med et lighedstegn i.
        """
        from core.services import smith_noise_veto
        monkeypatch.setattr(smith_noise_veto, "maa_minte", lambda *a, **kw: (False, "doemt_stoej"))
        r = cc.land_decision(
            "red_dress", "Undersøg X nu — severity 2, kun 0 kig",
            subject="quiet_fire:X", evidence="severity=2 volume=0",
            evidence_source="central_red_dress")
        assert "veto" not in str(r.get("reason") or ""), r

    def test_uden_evidens_koerer_vetoet_som_foer(self, monkeypatch):
        """Værnet skal stadig virke for formulerede mønstre uden en måling."""
        from core.services import smith_noise_veto
        monkeypatch.setattr(smith_noise_veto, "maa_minte", lambda *a, **kw: (False, "doemt_stoej"))
        r = cc.land_decision("smith", "Et løst formuleret mønster uden tal")
        assert r["applied"] is False
        assert "veto" in str(r["reason"])

    def test_evidens_uden_tal_taeller_ikke_som_evidens(self, monkeypatch):
        from core.services import smith_noise_veto
        monkeypatch.setattr(smith_noise_veto, "maa_minte", lambda *a, **kw: (False, "doemt_stoej"))
        r = cc.land_decision("red_dress", "Undersøg noget", evidence="det braender")
        assert "veto" in str(r["reason"])


# ── 4. Red dress: en stille brand er en undvigelse ──────────────────────────


class TestStilleBrandLander:
    def test_quiet_fire_bliver_en_forpligtelse(self, monkeypatch):
        from core.services import central_red_dress as rd
        monkeypatch.setattr(rd, "detect_attention_traps", lambda **kw: {
            "red_dresses": [{"nerve": "hoej_volumen", "volume": 500}],
            "quiet_fires": [{"nerve": "braender", "severity": 2, "volume": 0}],
            "felt": "Du kigger på den røde kjole. Imens brænder braender i det stille.",
        })
        kaldt: dict = {}

        def _fake_land(cid, directive, **kw):
            kaldt.update({"cid": cid, "directive": directive, **kw})
            return {"applied": True, "decision_id": "dec_x"}

        monkeypatch.setattr(cc, "land_decision", _fake_land)
        r = rd.record_red_dress()
        assert r["landing"]["applied"] is True
        assert kaldt["cid"] == "red_dress"
        assert "braender" in kaldt["directive"]
        assert "severity=2" in kaldt["evidence"], "fundet skal bære den målte evidens"

    def test_ren_laesning_muterer_ikke(self, monkeypatch):
        """Surfacen læses ved HVERT prompt-build — den må ikke skrive en forpligtelse."""
        from core.services import central_red_dress as rd
        monkeypatch.setattr(rd, "detect_attention_traps", lambda **kw: {
            "red_dresses": [], "quiet_fires": [{"nerve": "braender", "severity": 2, "volume": 0}],
            "felt": "x"})
        kaldt: list = []
        monkeypatch.setattr(cc, "land_decision", lambda *a, **kw: kaldt.append(1) or {})
        rd.build_red_dress_surface()
        assert kaldt == [], "en læsning må ikke producere en mutation"

    def test_ingen_brand_lander_intet(self, monkeypatch):
        from core.services import central_red_dress as rd
        monkeypatch.setattr(rd, "detect_attention_traps", lambda **kw: {
            "red_dresses": [], "quiet_fires": [], "felt": "Ingen fælde."})
        r = rd.record_red_dress()
        assert r["landing"] is None


# ── 5. Logger-vagten: fejlhåndtering må ikke selv fejle ─────────────────────


class TestLoggerFindes:
    """Ramt tre gange 13/11-2026: `logger.warning` i et modul uden `logger`.

    Det gør `except`-grenen til en `NameError`, altså fejler højere end den fejl
    den skulle håndtere — og kun i fejlsituationen, hvor ingen test kigger.
    """

    @pytest.mark.parametrize("modul", [
        "core.services.central_consequence",
        "core.services.central_analyst",
        "core.services.central_red_dress",
        "core.services.central_sentinel",
        "core.services.central_redpill",
        "core.services.central_dissent",
    ])
    def test_modul_der_bruger_logger_har_en(self, modul):
        import importlib
        m = importlib.import_module(modul)
        if "logger." in open(m.__file__, encoding="utf-8").read():
            assert hasattr(m, "logger"), f"{modul} bruger logger. men har ingen logger"
