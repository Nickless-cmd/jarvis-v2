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
