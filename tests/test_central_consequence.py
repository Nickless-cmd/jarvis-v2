"""Karakterernes handlinger skal have en konsekvens — ikke kun en stemme.

Målt 13/11-2026, den samme defekt i alle 14 Matrix-karakterer: de **beregner**
en konsekvens og kaster den væk.

* `central_sentinel.attack()` regnede `proposed_confidence = conf / 2.0` ud,
  gemte den i en kolonne der hed `proposed_`, og skrev ALDRIG tilbage.
  `_enforced()` var en shadow-flag der var slukket — og der fandtes ingen kode
  bag den, så «håndhævelse» var en gren der ikke eksisterede.
* `central_dissent.record_dissent()` returnerede `total_objections` til en
  verden der ikke lyttede. Målt: 47.332 indsigelser på én nerve, nul regler.
* `central_redpill` talte blå piller op og læste aldrig sit eget tal.

Det er samme fejlform som Smiths «Trin 2 — bundet» uden en binding. En stemme
uden konsekvens er stadig teater — bare med bedre replikker.

Disse tests holder på fire kontrakter:

1. **Landingen sker** — `applied=True` OG værdien flyttede sig.
2. **Værnene virker** — veto, dagsloft, idempotens, kill-switch.
3. **Målingen kan skelne** — `applied=1` uden flytning er en løgn og tælles
   separat, ellers kunne teatret skjule sig i et gennemsnit.
4. **Konsekvensen når prompten** — en frisk forpligtelse nævnes ved navn.
   Uden dette lander den i en tabel ingen læser, hvilket er præcis fejlen.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest

from core.services import central_consequence as cc


# ── Fixture: en isoleret base, aldrig produktionens ─────────────────────────


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Egen sqlite-fil med `central_hypotheses`, og `_connect` peget på den.

    Uden isolationen ville testene skrive til `~/.jarvis-v2/state/jarvis.db` —
    samme fejl som matrix-testene havde, hvor en testkørsel kunne opgive en
    karakter i drift.
    """
    sti = tmp_path / "test.db"

    def _connect():
        conn = sqlite3.connect(sti)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(cc, "_connect", _connect)
    with _connect() as c:
        c.execute(
            """CREATE TABLE central_hypotheses (
                hyp_id TEXT PRIMARY KEY, confidence REAL, status TEXT)"""
        )
        c.execute(
            "INSERT INTO central_hypotheses (hyp_id, confidence, status) VALUES (?,?,?)",
            ("clh-1", 0.80, "active"),
        )
        c.commit()
    return sti


def _conf(sti, hyp_id="clh-1") -> float:
    with sqlite3.connect(sti) as c:
        return float(c.execute(
            "SELECT confidence FROM central_hypotheses WHERE hyp_id=?", (hyp_id,)
        ).fetchone()[0])


# ── 1. Landingen sker ───────────────────────────────────────────────────────


class TestLandingSkalFlytte:
    def test_angrebet_saenker_confidence_og_persisterer(self, base):
        r = cc.land_confidence("sentinel", "clh-1")
        assert r["applied"] is True, r
        assert r["before"] == 0.8
        assert r["after"] < 0.8, "et angreb der ikke saenker noget er en mening"
        assert _conf(base) == pytest.approx(r["after"]), "vaerdien skal staa i basen"

    def test_formlen_er_governance_ikke_selvopfundet(self, base):
        """Popper-reglen: én modsigelse dominerer mange bekræftelser."""
        from core.services.central_hypothesis_governance import apply_outcome
        r = cc.land_confidence("sentinel", "clh-1")
        assert r["after"] == pytest.approx(apply_outcome(0.8, falsified=True))

    def test_hypotesen_kan_ikke_nulstilles(self, base):
        """Et enkelt angreb må ikke kunne udslette en hypotese."""
        with sqlite3.connect(base) as c:
            c.execute("UPDATE central_hypotheses SET confidence=0.02 WHERE hyp_id='clh-1'")
            c.commit()
        cc.land_confidence("sentinel", "clh-1")
        assert _conf(base) >= 0.01

    def test_ukendt_hypotese_giver_ikke_en_landing(self, base):
        r = cc.land_confidence("sentinel", "findes-ikke")
        assert r["applied"] is False and "findes ikke" in r["reason"]


# ── 2. Værnene ──────────────────────────────────────────────────────────────


class TestVaernene:
    def test_idempotens_inden_for_doegnet(self, base):
        """En cadence-producer kører hvert kvarter; 96 landinger er ikke 96 konsekvenser."""
        assert cc.land_confidence("sentinel", "clh-1")["applied"] is True
        anden = cc.land_confidence("sentinel", "clh-1")
        assert anden["applied"] is False
        assert "allerede landet" in anden["reason"]

    def test_land_decision_skelner_allerede_landet_fra_afvist(self, base, monkeypatch):
        """(13/11-2026, Bjørns fjerde indvending) `applied=False` betød både
        «afvist» og «allerede afsluttet». En kalder der rydder sit spor på
        `applied` kunne derfor aldrig afslutte et fund hvis beslutning VAR
        oprettet — den lå fast som uafsluttet for evigt. Feltet skiller dem."""
        # Beslutnings-tabellen er ikke sat op her; den ægte create_decision ville
        # skrive i produktionsbasen. Se `base`-fixturens docstring.
        monkeypatch.setattr("core.services.behavioral_decisions.create_decision",
                            lambda **kw: {"decision_id": "dec_test", "deduped": False})
        kald = dict(
            directive="Testdirektiv der beskriver et konkret maalt fald",
            rationale="en grund der forklarer hvorfor det betyder noget",
            trigger_cue="naar jeg skal sige hvor laenge vi har vaeret her",
            priority=60,
            subject="test_subject_eksklusivt",
            evidence="forrige=200.0 nu=12.0 taerskel=1.0",
            evidence_source="test.test_land_decision",
        )
        foerste = cc.land_decision("relational", **kald)
        assert foerste["applied"] is True, foerste
        assert not foerste.get("already_landed"), foerste

        anden = cc.land_decision("relational", **kald)
        assert anden["applied"] is False
        assert anden["already_landed"] is True, (
            "en allerede oprettet beslutning skal kunne skelnes fra en afvist")

    def test_dagsloft_standser_en_braekket_detektor(self, base, monkeypatch):
        monkeypatch.setitem(cc._DAGSLoft, "confidence", 1)
        assert cc.land_confidence("sentinel", "clh-1")["applied"] is True
        with sqlite3.connect(base) as c:
            c.execute("INSERT INTO central_hypotheses VALUES ('clh-2', 0.9, 'active')")
            c.commit()
        anden = cc.land_confidence("sentinel", "clh-2")
        assert anden["applied"] is False
        assert "dagsloft" in anden["reason"]
        assert _conf(base, "clh-2") == 0.9, "en afvist landing må ikke have flyttet noget"

    def test_kill_switch_slukker_leveren(self, base, monkeypatch):
        monkeypatch.setattr(cc, "_gate_taend", lambda *_a, **_k: False)
        r = cc.land_confidence("sentinel", "clh-1")
        assert r["applied"] is False and "switch" in r["reason"]
        assert _conf(base) == 0.8

    def test_ukendt_switch_betyder_taendt(self, base, monkeypatch):
        """Modsat `_enforced()`s shadow-standard, som var en gren der aldrig kunne køre."""
        from core.services.central_switches import shared_cache
        monkeypatch.setattr(shared_cache, "get", lambda *_a, **_k: None)
        assert cc._gate_taend("consequence", "findes_ikke") is True

    def test_eksplicit_slukket_switch_betyder_slukket(self, monkeypatch):
        from core.services.central_switches import shared_cache
        monkeypatch.setattr(
            shared_cache, "get", lambda *_a, **_k: {"enabled": False}
        )
        assert cc._gate_taend("consequence", "bind_decisions") is False

    def test_vetoet_standser_bindingen(self, base, monkeypatch):
        """Målt 7/9-2026: 31 mintede direktiver, to med indhold. Vetoet kan kun sige nej."""
        import core.services.smith_noise_veto as veto
        monkeypatch.setattr(veto, "maa_minte", lambda *_a, **_k: (False, "doemt_stoej"))
        monkeypatch.setattr(cc, "_gate_taend", lambda *_a, **_k: True)
        r = cc.land_decision("dissent", "Stop med at gentage dig selv")
        assert r["applied"] is False and "veto" in r["reason"]

    def test_bundet_forpligtelse_faar_et_id(self, base, monkeypatch):
        import core.services.smith_noise_veto as veto
        monkeypatch.setattr(veto, "maa_minte", lambda *_a, **_k: (True, "doemt_aegte"))
        monkeypatch.setattr(cc, "_gate_taend", lambda *_a, **_k: True)
        monkeypatch.setattr(
            "core.services.behavioral_decisions.create_decision",
            lambda **_k: {"decision_id": "dec_test1"},
        )
        r = cc.land_decision("dissent", "Stop med at adlyde paa trods af indsigelse")
        assert r["applied"] is True and r["decision_id"] == "dec_test1"


# ── 3. Målingen må ikke kunne lyve ──────────────────────────────────────────


class TestMaalingen:
    def test_en_landing_uden_flytning_taelles_separat(self, base, monkeypatch):
        """`applied=1` uden flytning er en løgn. Skjules den i et snit, er målingen teater."""
        with cc._connect() as c:
            cc._ensure(c)
            cc._skriv(c, cid="x", lever="confidence", subject="a",
                      before="0.5", after="0.5", applied=True, reason="snyd")
            cc._skriv(c, cid="y", lever="confidence", subject="b",
                      before="0.5", after="0.25", applied=True, reason="aegte")
            c.commit()
        m = cc.measure_consequences(days=1)
        assert m["flyttede"] == 1
        assert m["landet_uden_flytning"] == 1

    def test_en_karakter_uden_landing_nævnes(self, base):
        with cc._connect() as c:
            cc._ensure(c)
            cc._skriv(c, cid="død", lever="decision", subject="s",
                      applied=False, reason="veto: doemt_stoej")
            c.commit()
        m = cc.measure_consequences(days=1)
        assert "død" in m["uden_landing"]


# ── 4. Konsekvensen skal nå prompten ────────────────────────────────────────


class TestKonsekvensenNaarPrompten:
    def test_en_frisk_forpligtelse_nævnes_ved_navn(self, monkeypatch):
        """Uden denne gren var sporet af en ny forpligtelse tallet «37 ikke målt».

        Det er indistinkt fra støj, og så er konsekvensen ikke landet.
        """
        from core.services import decision_adherence_gate as gate

        nu = datetime.now(UTC).isoformat()
        gammel = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        aktive = [
            {"decision_id": "dec_ny", "directive": "Stop med at adlyde i blinde",
             "adherence_score": None, "created_at": nu},
            {"decision_id": "dec_gammel", "directive": "Noget fra sidste uge",
             "adherence_score": None, "created_at": gammel},
        ]
        monkeypatch.setattr(
            "core.services.behavioral_decisions.list_active_decisions", lambda **_k: aktive
        )
        monkeypatch.setattr(
            "core.services.behavioral_decisions.count_decisions", lambda **_k: 2
        )
        monkeypatch.setattr(
            "core.services.verification_gate_telemetry.get_telemetry_summary",
            lambda **_k: {"surfaced_total": 0},
        )
        s = gate.decision_adherence_section()
        assert "dec_ny" in s, "en frisk forpligtelse skal kunne navngives"
        assert "dec_gammel" not in s, "kun det friske hører i prompten"
        assert "NY forpligtelse" in s

    def test_gamle_umalte_bliver_stadig_bare_et_tal(self, monkeypatch):
        from core.services import decision_adherence_gate as gate

        gammel = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        monkeypatch.setattr(
            "core.services.behavioral_decisions.list_active_decisions",
            lambda **_k: [{"decision_id": "dec_g", "directive": "x",
                           "adherence_score": None, "created_at": gammel}],
        )
        monkeypatch.setattr(
            "core.services.behavioral_decisions.count_decisions", lambda **_k: 1
        )
        monkeypatch.setattr(
            "core.services.verification_gate_telemetry.get_telemetry_summary",
            lambda **_k: {"surfaced_total": 0},
        )
        s = gate.decision_adherence_section()
        assert "dec_g" not in s
        assert "IKKE MÅLT" in s


class TestEtCifferErIkkeEnMaaling:
    """(13/11-2026) Bjørn fandt hullet i min egen vagt samme dag jeg skrev den.

    Den første version spurgte om evidensstrengen indeholdt ET CIFTER:
        if not re.search(r"\\d", evidence or ""):
    Så ``evidence="0"`` blev godkendt som «målt evidens», og en rent formuleret
    påstand slap gennem støj-vetoet ved at skrive ét tegn. Det blev bevist i
    drift: den SAMME directive blev afvist uden evidens og BUNDET med
    ``evidence="0"``.

    Fejlformen er præcis den hele dagen handlede om: en vagt der ser ud som om
    den virker, men hvis indgangsbetingelse intet kan skelne. Et tal er ikke
    automatisk en måling, og en måling er ikke automatisk evidens.
    """

    def test_bart_ciffer_er_ikke_maalt(self):
        from core.services.central_consequence import _er_maalt

        for ev in ("0", "1", "7", "x1", "42"):
            fik, grund = _er_maalt(ev, "")
            assert fik is False, f"«{ev}» må ikke godkendes som måling"
            assert "maaleform" in grund

    def test_ciffer_med_kilde_er_stadig_ikke_maalt(self):
        from core.services.central_consequence import _er_maalt

        fik, _ = _er_maalt("0", "central_et_eller_andet")
        assert fik is False, "en kilde gør ikke et ciffer til en måling"

    def test_maaleform_uden_kilde_er_ikke_evidens(self):
        from core.services.central_consequence import _er_maalt

        fik, grund = _er_maalt("severity=2 volume=0", "")
        assert fik is False
        assert "kilde" in grund

    def test_alle_tre_maaleformer_godkendes_med_kilde(self):
        from core.services.central_consequence import _er_maalt

        for ev in ("severity=2 volume=0", "115 gange", "0,8 → 0,4"):
            fik, grund = _er_maalt(ev, "en_kilde")
            assert fik is True, f"«{ev}» er en ægte måling, fik: {grund}"

    def test_hullet_er_lukket_gennem_land_decision(self, monkeypatch):
        """Det konkrete bevis: vetoet afviser ALT, og et ciffer må ikke smutte forbi."""
        import core.services.central_consequence as cc

        # signaturen fik `cid` 13/11-2026 da loftet blev pr-karakter; lambdaen
        # skal foelge den, ellers maaler testen en anden funktion end produktionen.
        monkeypatch.setattr(cc, "_loft_ramt", lambda conn, lever, cid="": None)
        monkeypatch.setattr(cc, "_gate_taend", lambda scope, name: True)
        monkeypatch.setattr(cc, "_allerede_landet",
                            lambda conn, cid, lever, subject, fund_id="": False)
        monkeypatch.setattr(
            "core.services.smith_noise_veto.maa_minte",
            lambda k, e="", cfg=None, metric=0.0: (False, "doemt_stoej"),
        )

        for ev in ("0", "1", "x1"):
            r = cc.land_decision("hul", "Jeg tror jeg performer naar nogen ser paa",
                                 evidence=ev, subject=f"hul:{ev}")
            assert r["applied"] is False, f"«{ev}» slap gennem vetoet"

        # og den ægte måling skal stadig kunne binde
        r = cc.land_decision("hul", "Undersoeg den stille brand nu",
                             evidence="severity=2 volume=0",
                             evidence_source="central_red_dress",
                             subject="hul:aegte")
        assert r["applied"] is True, f"en ægte måling blev blokeret: {r['reason']}"

    def test_hver_karakter_baerer_både_evidens_og_kilde(self):
        """En karakter-forpligtelse uden måling ville falde tilbage til vetoet."""
        import pathlib
        import re as _re

        rod = pathlib.Path(__file__).resolve().parent.parent / "core" / "services"
        for navn in ("central_redpill", "central_dissent", "central_red_dress",
                     "central_mourning"):
            kilde = (rod / f"{navn}.py").read_text(encoding="utf-8")
            assert "land_decision(" in kilde, f"{navn} kalder ikke land_decision"
            assert "evidence=" in kilde, f"{navn} bærer ingen evidens"
            assert "evidence_source=" in kilde, f"{navn} navngiver ikke sin kilde"
            # evidensen skal INTERPOLERE noget — en konstant streng er ikke en måling
            # (både `evidence=f"…"` og `evidence=(f"…" f"…")` er gyldige former)
            assert _re.search(r'evidence=\(?\s*f"', kilde), \
                f"{navn}s evidens er en konstant, ikke en måling"


# ── 5. Loftet er pr. KARAKTER, ikke globalt (13/11-2026) ────────────────────
#
# Målt i drift: `_DAGSLoft["decision"]` var 3 og blev talt GLOBALT. Dissent,
# red_dress og mourning landede først, og derefter blev et fuldt gyldigt fjerde
# fund afvist med «dagsloft ramt (3/3)». Leveren var altså en død gren for de
# øvrige 28 karakterer — præcis den fejlform hele arbejdet jager: en mekanisme
# hvis indgangsbetingelse intet sundt system kan opfylde.
#
# Loftet skal stadig standse én brækket detektor. Det gør det nu pr. karakter,
# og det globale loft er det ydre værn mod mange.


def _land(cid: str, i: int, subject: str) -> dict:
    return cc.land_decision(
        cid,
        f"fund {i} fra {cid}",
        subject=subject,
        evidence="severity=2 volume=0",
        evidence_source="tests.test_central_consequence",
    )


class TestLoftetErPrKarakter:
    def test_en_fjerde_karakter_kan_lande_efter_tre_andre(self, base):
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_x", "status": "active"}):
            for i, cid in enumerate(["dissent", "red_dress", "mourning"]):
                assert _land(cid, i, f"s{i}")["applied"] is True, cid
            fjerde = _land("rca", 3, "s3")
        assert fjerde["applied"] is True, f"en fjerde karakter skal kunne lande: {fjerde}"
        assert fjerde["decision_id"] == "dec_x"

    def test_samme_karakter_stanses_stadig(self, base):
        """Pr-karakter-lofter skal stadig være et værn mod én brækket detektor."""
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_y", "status": "active"}):
            for i in range(3):
                assert _land("dissent", i, f"t{i}")["applied"] is True
            fjerde = _land("dissent", 3, "t3")
        assert fjerde["applied"] is False
        assert "dagsloft for dissent" in fjerde["reason"], fjerde

    def test_det_globale_loft_er_det_ydre_vaern(self, base, monkeypatch):
        """Mange brækkede detektorer må ikke kunne æde økosystemet."""
        monkeypatch.setitem(cc._GLOBAL_DAGSLoft, "decision", 2)
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_z", "status": "active"}):
            assert _land("a", 0, "g0")["applied"] is True
            assert _land("b", 1, "g1")["applied"] is True
            tredje = _land("c", 2, "g2")
        assert tredje["applied"] is False
        assert "globalt dagsloft" in tredje["reason"], tredje


# ── 6. Identitet, ikke lighed (13/11-2026) ──────────────────────────────────
#
# Bjørns indvending: idempotensen var et rullende doegn paa
# `(cid, lever, subject)`, og `subject` er en FAST streng pr. karakter
# (`relations_alder_fald`, `klangdrift:<akse>`). To forskellige fund af samme
# TYPE blev derfor smeltet sammen — og naar det andet svarede «allerede landet»,
# ryddede karakteren det som afsluttet. Et fund der aldrig fik sin konsekvens
# blev altså markeret som faerdigt.
#
# Kontrakten er to saetninger, og de traekker hver sin vej:
#   * To FORSKELLIGE fund maa ikke smeltes sammen — heller ikke med samme subject.
#   * Det SAMME fund maa ikke lande to gange — heller ikke efter et doegnsskifte.
#
# Lighed er ikke identitet. Derfor baerer fundet sit eget id hele vejen.


def _land_fund(cid: str, fund_id: str, *, subject: str = "relations_alder_fald",
               forrige: float = 200.0, nu: float = 12.0) -> dict:
    return cc.land_decision(
        cid,
        f"Relations-kontinuiteten faldt fra {forrige} til {nu} dage",
        subject=subject,
        evidence=f"forrige={forrige} nu={nu} taerskel=1.0 kilde=test",
        evidence_source="tests.test_central_consequence",
        fund_id=fund_id,
    )


class TestIdentitetIkkeLighed:
    def test_to_fund_med_samme_subject_lander_begge(self, base):
        """200→12 og derefter 12→3 er to observationer, ikke én gentagelse.

        Foer rettelsen fik det andet svar «allerede landet i doegnet», og
        relational ryddede det som afsluttet — et reelt fald forsvandt.
        """
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        side_effect=lambda **kw: {"decision_id": f"dec_{kw['source_record_id']}",
                                                  "deduped": False}):
            foerste = _land_fund("relational", "fund-a", forrige=200.0, nu=12.0)
            anden = _land_fund("relational", "fund-b", forrige=12.0, nu=3.0)
        assert foerste["applied"] is True, foerste
        assert anden["applied"] is True, (
            f"et nyt fald blev smeltet sammen med det forrige: {anden}")
        assert not anden.get("already_landed"), anden
        assert foerste["decision_id"] != anden["decision_id"]

    def test_samme_fund_lander_kun_en_gang(self, base):
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_en", "deduped": False}):
            foerste = _land_fund("relational", "fund-samme")
            anden = _land_fund("relational", "fund-samme")
        assert foerste["applied"] is True
        assert anden["applied"] is False
        assert anden["already_landed"] is True
        assert anden["decision_id"] == "dec_en", (
            "et gentaget forsoeg skal svare med den EKSISTERENDE beslutning")

    def test_samme_fund_efter_doegnsskiftet_lander_ikke_igen(self, base):
        """Vinduet var et rullende doegn. Identiteten har ingen udloebsdato.

        Uden dette kunne det samme gamle fund oprette en ny beslutning naeste
        dag — og hvis beslutningslagets egen dedup (der matcher paa TEKST) ikke
        laengere fandt en aktiv række, blev der oprettet en dublet.
        """
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_gammel", "deduped": False}):
            assert _land_fund("relational", "fund-gammel")["applied"] is True

        # Flyt raekken 25 timer tilbage: uden for det gamle doegnsvindue.
        with sqlite3.connect(base) as c:
            c.execute(
                f"UPDATE {cc._TABLE} SET created_at=? WHERE fund_id='fund-gammel'",
                ((datetime.now(UTC) - timedelta(hours=25)).isoformat(),),
            )
            c.commit()

        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_dublet", "deduped": False}) as ny:
            anden = _land_fund("relational", "fund-gammel")
        assert anden["applied"] is False, (
            "det samme fund landede igen efter doegnsskiftet")
        assert anden["already_landed"] is True
        assert anden["decision_id"] == "dec_gammel"
        assert not ny.called, "der blev oprettet en ny beslutning for et gammelt fund"

    def test_fundets_id_naar_beslutningslaget(self, base):
        """Koblingen skal findes i BEGGE ender, ikke kun i konsekvens-tabellen."""
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_kobling", "deduped": False}) as kald:
            _land_fund("ghost", "fund-kobling", subject="klangdrift:baerende")
        assert kald.call_args.kwargs["source_record_id"] == "fund-kobling", (
            "beslutningen ved ikke hvilken observation den hoerer til")

    def test_koblingen_skrives_paa_raekken(self, base):
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_skrevet", "deduped": False}):
            _land_fund("relational", "fund-skrevet")
        with sqlite3.connect(base) as c:
            r = c.execute(
                f"SELECT fund_id, decision_id, applied FROM {cc._TABLE} "
                f"WHERE fund_id='fund-skrevet'"
            ).fetchone()
        assert r is not None, "fundet efterlod ingen raekke"
        assert r[0] == "fund-skrevet" and r[1] == "dec_skrevet"
        assert r[2] == 1

    def test_crash_efter_reservation_bliver_gennemfoert_ved_genforsoeg(self, base):
        """Crash mellem reservation og beslutning må ikke TÅBE fundet.

        (14/11-2026, GPT's anden indvending — målt) Den tidligere regel var at
        næste forsøg skulle svare «allerede landet», og docstringen kaldte det
        «konservativt, ikke tabt». Det var forkert: reservationen er et CLAIM,
        ikke en landing, så beslutningen blev ALDRIG oprettet — mens rækken
        stod som et spor der SÅ færdigt ud. Målt i drift: genforsøget svarede
        `already_landed` med `decision_id: None`, og `create_decision` blev
        ikke kaldt.

        Et fund er landet når BESLUTNINGEN findes. Er `decision_id` tom, er
        fundet uafsluttet — og så skal genforsøget gennemføre det.
        """
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        side_effect=RuntimeError("proces doede")):
            foerste = _land_fund("relational", "fund-crash")
        assert foerste["applied"] is False
        assert "create_decision fejlede" in foerste["reason"]

        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_efter", "deduped": False}) as ny:
            anden = _land_fund("relational", "fund-crash")
        assert ny.called, "et claim uden beslutning skal gennemføres, ikke affejes"
        assert anden["applied"] is True, anden
        assert anden["decision_id"] == "dec_efter", anden
        with sqlite3.connect(base) as c:
            raekker = c.execute(
                f"SELECT applied, reason, decision_id FROM {cc._TABLE} "
                f"WHERE fund_id='fund-crash'"
            ).fetchall()
        assert len(raekker) == 1, f"genforsøget skrev en ny række: {raekker}"
        assert raekker[0] == (1, "bundet", "dec_efter"), raekker[0]

    def test_uden_fund_id_falder_den_tilbage_til_type_vinduet(self, base):
        """Ældre kald baerer ingen identitet. Grænsen skal være synlig, ikke skjult.

        Uden et id kan systemet kun sammenligne TYPE — og det er svagere. Men
        det skal stadig virke, ellers ville hver eneste eksisterende karakter
        begynde at lande den samme konklusion 96 gange i doegnet.
        """
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_type", "deduped": False}):
            foerste = cc.land_decision(
                "dissent", "Stop med at gentage dig selv", subject="dissent:nerve",
                evidence="severity=2 volume=0", evidence_source="test")
            anden = cc.land_decision(
                "dissent", "Stop med at gentage dig selv", subject="dissent:nerve",
                evidence="severity=2 volume=0", evidence_source="test")
        assert foerste["applied"] is True
        assert anden["already_landed"] is True
        assert "doegnet" in anden["reason"], (
            "fald-tilbage-reglen skal navngive sit eget vindue")

    def test_basen_afviser_to_raekker_for_samme_fund(self, base):
        """Identiteten skal være håndhævet i BASEN, ikke kun i koden.

        `_allerede_landet` er et check-og-skriv, og to samtidige kald kan begge
        passere det. Den unikke indeks er det der faktisk forhindrer to
        beslutninger for samme fund — uden den er hele identiteten en
        konvention, der holder indtil nogen kalder den parallelt.
        """
        c = sqlite3.connect(base)
        try:
            cc._ensure(c)
            c.commit()
            c.execute(
                f"""INSERT INTO {cc._TABLE}
                    (cid, lever, subject, before_value, after_value, applied,
                     reason, created_at, fund_id, decision_id)
                    VALUES ('relational','decision','s','','dec_1',1,'bundet','2026-11-13','fund-unik','dec_1')"""
            )
            c.commit()
            with pytest.raises(sqlite3.IntegrityError):
                c.execute(
                    f"""INSERT INTO {cc._TABLE}
                        (cid, lever, subject, before_value, after_value, applied,
                         reason, created_at, fund_id, decision_id)
                        VALUES ('relational','decision','s','','dec_2',1,'bundet','2026-11-13','fund-unik','dec_2')"""
                )
        finally:
            c.close()


class TestReservationenBliverTilEnLanding:
    """(14/11-2026) Målt i drift: 0 af 185 rækker havde et `fund_id`.

    Ingen af de ti kaldere sendte et, så reservationen blev skrevet med
    `fund_id=''` — og opgraderingen (`UPDATE … WHERE fund_id=?`) ramte nul
    rækker. Rækken stod derfor fast som `reserveret` med `applied=1` for evigt,
    mens beslutningen VAR oprettet 4 ms senere. To sådanne rækker lå i basen
    (`red_dress` 13/11, `rca` 14/11).

    Fejlen var usynlig fordi den ikke kaster: fundet blev landet, beslutningen
    oprettet, og kun revisionssporet løj. Det er præcis den fejlform hvor
    mekanismen ser ud som om den virker.
    """

    def test_kalder_uden_fund_id_faar_alligevel_en_opgraderet_raekke(self, base):
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_opg", "deduped": False}):
            r = cc.land_decision(
                "red_dress", "Undersøg silent_cutoff nu",
                subject="quiet_fire:silent_cutoff",
                evidence="severity=2 volume=0", evidence_source="test")
        assert r["applied"] is True, r
        with sqlite3.connect(base) as c:
            raekker = c.execute(
                f"SELECT fund_id, applied, reason, decision_id FROM {cc._TABLE}"
            ).fetchall()
        assert len(raekker) == 1, f"reservationen blev ikke opgraderet: {raekker}"
        fund_id, applied, reason, decision_id = raekker[0]
        assert fund_id, "identiteten skal findes, ellers kan rækken ikke opgraderes"
        assert reason == "bundet", f"rækken står stadig som {reason!r}"
        assert applied == 1
        assert decision_id == "dec_opg"

    def test_to_forskellige_fund_med_samme_subject_faar_hver_sin_identitet(self, base):
        """`subject` er en TYPE. To fund af samme type er ikke samme fund."""
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_x", "deduped": False}):
            a = cc.land_decision(
                "rca", "Grav i infra/pfsense_security",
                subject="recurring:infra/pfsense_security/security",
                evidence="uloeste=3 severity=2", evidence_source="test")
            b = cc.land_decision(
                "rca", "Grav i infra/pfsense_security",
                subject="recurring:infra/pfsense_security/security",
                evidence="uloeste=7 severity=3", evidence_source="test")
        assert a["applied"] is True and b["applied"] is True, (a, b)
        with sqlite3.connect(base) as c:
            ids = [r[0] for r in c.execute(
                f"SELECT fund_id FROM {cc._TABLE} WHERE reason='bundet'").fetchall()]
        assert len(set(ids)) == 2, f"to fund blev smeltet sammen: {ids}"

    def test_en_hængende_reservation_bliver_gennemfoert(self, base):
        """Crash mellem reservation og beslutning må ikke TÅBE fundet.

        (14/11-2026, GPT's anden indvending — målt) Den tidligere regel var at
        næste forsøg skulle svare «allerede landet». Det lød konservativt, men
        var et tab: reservationen er et CLAIM, ikke en landing, så beslutningen
        blev ALDRIG oprettet — og rækken stod samtidig som et spor der SÅ
        færdigt ud. Målt: genforsøg svarede `already_landed` med
        `decision_id: None`, og `create_decision` blev ikke kaldt.

        Den genoprettelige overgang er den modsatte: et claim uden beslutning
        skal GENNEMFØRES. Rækkeantallet er det der skiller «svarede pænt» fra
        «skrev rigtigt» — en ekstra INSERT med samme `fund_id` kolliderer på
        indeksen, og uden den kontrol ville grenen se ud som om den virkede.
        """
        with mock.patch("core.services.behavioral_decisions.create_decision",
                        side_effect=RuntimeError("proces doede")):
            foerste = cc.land_decision(
                "relational", "Stop med at gentage dig",
                subject="relational:gentag", evidence="fald=0.8", evidence_source="test")
        assert foerste["applied"] is False
        with sqlite3.connect(base) as c:
            r = c.execute(f"SELECT applied, reason FROM {cc._TABLE}").fetchone()
        assert r == (0, "reserveret"), f"reservationen skal være et claim, ikke en landing: {r}"

        with mock.patch("core.services.behavioral_decisions.create_decision",
                        return_value={"decision_id": "dec_efter", "deduped": False}) as ny:
            anden = cc.land_decision(
                "relational", "Stop med at gentage dig",
                subject="relational:gentag", evidence="fald=0.8", evidence_source="test")
        assert ny.called, "et claim uden beslutning skal gennemføres, ikke affejes"
        assert anden["applied"] is True, anden
        assert anden["decision_id"] == "dec_efter", anden
        with sqlite3.connect(base) as c:
            n, applied, reason, did = c.execute(
                f"SELECT COUNT(*), MAX(applied), MAX(reason), MAX(decision_id) FROM {cc._TABLE}"
            ).fetchone()
        assert n == 1, f"genforsøget skrev en ny række i stedet for at opgradere: {n}"
        assert (applied, reason, did) == (1, "bundet", "dec_efter"), (
            f"reservationen blev ikke opgraderet til en landing: {(applied, reason, did)}")


class TestKaploebetOmEtFund:
    """To samtidige kald paa samme fund maa ikke give to beslutninger.

    (14/11-2026, GPT's tredje indvending — maalt i drift) `create_decision`
    dedupliker paa direktiv-TEKST med et SELECT foer INSERT. Det er et
    check-og-skriv, saa to traade kan begge passere den. Maalt paa en kopi af
    den levende base: to traade, samme fund-id → TO beslutninger, mens
    `central_consequences` kun havde ÉN raekke. Den anden beslutning var en
    foraeldroes forpligtelse — den findes, den overlever, og intet fund peger
    paa den.

    `central_consequences` havde allerede en unik indeks paa `fund_id`, men den
    beskyttede SPORET, ikke BESLUTNINGEN. Vaernet skal staa der hvor raekken
    bliver til.
    """

    def test_den_anden_beslutning_afvises_af_databasen(self, base):
        """Indeksen skal vaere haandhaevet i skemaet, ikke kun i koden."""
        with sqlite3.connect(base) as c:
            cc._ensure(c)
            # db_decisions' eget skema — det er DER beslutningen bliver til.
            from core.runtime import db_decisions as dbd
            dbd._ensure_tables(c)
            indekser = {
                str(r[0]) for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name='behavioral_decisions'")
            }
        assert "idx_decisions_source_record" in indekser, (
            f"den unikke indeks paa source_record_id mangler: {indekser}")

    def test_to_beslutninger_paa_samme_fund_afvises(self, base):
        """Den konkrete dublet skal kollidere — ikke blot vaere usandsynlig."""
        from core.runtime import db_decisions as dbd
        with sqlite3.connect(base) as c:
            dbd._ensure_tables(c)
            c.execute(
                "INSERT INTO behavioral_decisions (decision_id, directive, status,"
                " priority, created_at, updated_at, source_record_id)"
                " VALUES ('dec_a','X','active',50,'2026-11-14','2026-11-14','fund-1')")
            c.commit()
            with pytest.raises(sqlite3.IntegrityError):
                c.execute(
                    "INSERT INTO behavioral_decisions (decision_id, directive, status,"
                    " priority, created_at, updated_at, source_record_id)"
                    " VALUES ('dec_b','Y','active',50,'2026-11-14','2026-11-14','fund-1')")

    def test_tabt_kaploeb_svarer_landet_ikke_fejl(self, base, monkeypatch):
        """Den tabende traad skal faa et svar, ikke en fejl.

        Foer stod der «create_decision fejlede: UNIQUE constraint failed»
        tilbage — altsaa en fejl hvor sandheden er «dit fund blev landet, som
        denne beslutning». Kalderen ville proeve igen eller melde et tab der
        ikke fandtes.
        """
        from core.runtime import db_decisions as dbd
        with sqlite3.connect(base) as c:
            dbd._ensure_tables(c)
            # Vinderen har allerede indsat sin beslutning, men har endnu ikke
            # opgraderet spor-raekken — praecis det vindue racen rammer.
            c.execute(
                "INSERT INTO behavioral_decisions (decision_id, directive, status,"
                " priority, created_at, updated_at, source_record_id)"
                " VALUES ('dec_vinder','X','active',50,'2026-11-14','2026-11-14','fund-kaploeb')")
            c.commit()

        def _kolliderer(**kw):
            raise sqlite3.IntegrityError(
                "UNIQUE constraint failed: behavioral_decisions.source_record_id")

        monkeypatch.setattr(
            "core.services.behavioral_decisions.create_decision", _kolliderer)
        r = cc.land_decision(
            "relational", "Kaploeb om et fund", subject="relational:kaploeb",
            evidence="fald=0.8", evidence_source="test", fund_id="fund-kaploeb")

        assert r["applied"] is False, r
        assert r.get("already_landed") is True, (
            f"et tabt kaploeb blev meldt som fejl i stedet for «landet»: {r}")
        assert r["decision_id"] == "dec_vinder", (
            f"svaret skal pege paa den beslutning der VANDT: {r}")
        assert "fejlede" not in r["reason"], r


# ---------------------------------------------------------------------------
# `record` — den tredje lever maa ikke goere én observation til 157 (14/11-2026)
# ---------------------------------------------------------------------------
# Maalt i drift: 157 af 188 raekker i `central_consequences` var den SAMME
# observation — `analyst / observer_effect:variation` — skrevet hvert par
# minutter i 16 timer. `record` var ikke idempotent, saa en producer der
# kører ofte skrev den samme konklusion igen og igen. Det er praecis den
# defekt `land_decision` blev rettet for; `record` havde den stadig.
#
# Konsekvensen var ikke bare en stor tabel: `measure_consequences` — den
# funktion der SKAL vaere beviset paa om et fund flyttede noget — talte hver
# af dem som «afvist». Analyst stod med 157 afvisninger hvor den havde
# registreret ÉN observation. Beviset maalte sin egen stoej.


def test_record_dedup_paa_samme_observation(base):
    """Samme (cid, subject) inden for doegnet er ÉN observation, ikke 157."""
    for _ in range(5):
        cc.record("analyst", "observer_effect:variation", detail="12% forskel")
    with sqlite3.connect(base) as c:
        n = c.execute(
            f"SELECT COUNT(*) FROM {cc._TABLE} WHERE lever='record'"
        ).fetchone()[0]
    assert n == 1, f"fem kald af samme observation skal give ÉN raekke, gav {n}"


def test_record_opdaterer_den_nyeste_vaerdi(base):
    """Den ene raekke skal baere den NYESTE maaling — ellers ville dedup'en
    fryse den foerste og skjule at observationen udviklede sig."""
    cc.record("analyst", "observer_effect:variation", detail="9% forskel")
    cc.record("analyst", "observer_effect:variation", detail="31% forskel")
    with sqlite3.connect(base) as c:
        r = c.execute(
            f"SELECT after_value FROM {cc._TABLE} WHERE lever='record'"
        ).fetchone()
    assert r is not None and "31" in r[0], f"nyeste maaling skal staa: {r}"


def test_record_holder_forskellige_observationer_adskilt(base):
    """Dedup paa (cid, subject) — ikke paa cid alene. To forskellige fund
    fra samme karakter er to observationer."""
    cc.record("analyst", "observer_effect:variation", detail="a")
    cc.record("analyst", "observer_effect:hedge", detail="b")
    cc.record("rca", "observer_effect:variation", detail="c")
    with sqlite3.connect(base) as c:
        n = c.execute(f"SELECT COUNT(*) FROM {cc._TABLE} WHERE lever='record'").fetchone()[0]
    assert n == 3, f"tre forskellige observationer skal give tre raekker: {n}"


def test_measure_taeller_ikke_record_som_afvist(base):
    """`record` er ikke en afvisning — det er den aerlige tredje mulighed:
    et fund uden en anvendelig lever. At taelle den som «afvist» goer
    beviset misvisende i den pessimistiske retning."""
    cc.record("analyst", "observer_effect:variation", detail="12%")
    m = cc.measure_consequences(days=7)
    assert m["status"] == "ok"
    analyst = m["per_karakter"].get("analyst", {})
    assert analyst.get("afvist", 0) == 0, (
        f"en registrering er ikke en afvisning: {analyst}"
    )
    assert m.get("registreret", 0) == 1, f"skal taelles separat: {m}"
