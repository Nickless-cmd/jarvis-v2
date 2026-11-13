"""Agent Smith — stemmen skal naa prompten, og tilstanden maa ikke lyve.

Maalt 13/11-2026, tre brud i samme kaede:

1. `agent_smith_prompt_section` var bygget til prompt-halen men havde **nul
   kaldere** i hele traeet. Hans eskalerede linje naaede aldrig en prompt.
2. Ensemblet laeste `rung_line`, som var tom, og viste hans statiske one-liner —
   mens `felt_raw` baer den konkrete fangst: en tavs `&&`-kaede der broed
   **1350 gange**.
3. Tilstanden stod paa Trin 2 med 121 cyklusser og `decision_id=None`, og der
   var **nul** raekker i `behavioral_decisions` med `source_type='agent_smith'`.
   Smith «havde bundet sig» uden at noget bandt: `step_escalation` er ren og
   satte Trin 2, foer vetoet afviste mintet.

Testene her maaler de tre kontrakter. De er ikke tomme: hver af dem fejler hvis
den tilsvarende gren fjernes.
"""

from __future__ import annotations

from typing import Any


# ── 1. Den maalte fejl naar prompten ────────────────────────────────────────


def _state(**kw: Any) -> dict[str, Any]:
    base = {
        "score": 0.9,
        "line": "",
        "rung_line": "",
        "felt_raw": "",
        "measured": [],
        "verdict": True,
    }
    base.update(kw)
    return base


def test_den_maalte_fejl_naar_prompten_naar_rung_line_er_tom(monkeypatch):
    """`measured` er MAALT (repeated_count fra `lessons`) — ikke et n-gram-gaet.

    Patch-maal: `agent_smith_prompt_section` importerer `get_runtime_state_value`
    INDE i funktionen, saa den slaar op i `core.runtime.db_core` ved kaldstid —
    ikke i modulets eget navnerum. En patch paa `s.get_runtime_state_value` ville
    vaere usynlig for den, og testen ville maale sin egen mock.
    """
    from core.services import central_agent_smith as s

    maalt = [{
        "kind": "behaviour",
        "label": "gentaget fejl: En `&&`-kaede broed tavst: exit 1",
        "metric": 1350.0,
        "detail": "1350x (tool_error)",
        "self_bound": True,
    }]
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda *a, **k: _state(measured=maalt))
    out = s.agent_smith_prompt_section()
    assert out is not None
    assert "1350" in out, out
    assert "&&" in out, "den konkrete fejl skal med, ikke kun et tal"


def test_uden_maalte_fejl_er_stemmen_tavs(monkeypatch):
    """Positiv kontrol omvendt: en tom maaling maa ikke producere en tom stemme."""
    from core.services import central_agent_smith as s

    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda *a, **k: _state())
    assert s.agent_smith_prompt_section() is None


def test_rung_line_har_forrang_over_den_maalte_fejl(monkeypatch):
    """En eskalering er en governance-haendelse og skal vinde over baggrundsmaalet."""
    from core.services import central_agent_smith as s

    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda *a, **k: _state(rung_line="Nej, Mr. Anderson. Ikke igen.",
                               measured=[{"kind": "behaviour", "label": "x",
                                          "metric": 99.0, "self_bound": True}]),
    )
    out = s.agent_smith_prompt_section()
    assert out is not None and "Ikke igen" in out


# ── 2. En afvist binding maa ikke staa som en binding ───────────────────────


def _kør_tick(monkeypatch, *, maa: bool, mint_svar: str | None, pat: dict[str, Any]):
    """Kør run_escalation_tick med styrede handlinger. Returnerer (pat, actions, res)."""
    from core.services import central_agent_smith as s

    noegle = "behaviour:gentaget fejl: x"
    state = {"patterns": {noegle: pat}, "resolved": []}
    actions: list[dict[str, Any]] = [{
        "type": "mint", "pattern_key": noegle,
        "label": pat.get("label", ""), "kind": "behaviour", "metric": 9.0,
    }]

    monkeypatch.setattr(s, "assess", lambda *a, **k: {
        "score": 0.9, "verdict": True, "felt": "", "behaviours": [],
        "repeated_phrases": [], "decision_patterns": [],
    })
    monkeypatch.setattr(s, "_detected_patterns", lambda *a, **k: {})
    monkeypatch.setattr(s, "_corroboration_signal", lambda: set())
    monkeypatch.setattr(s, "_escalation_criteria", lambda: {})
    monkeypatch.setattr(s, "_load_escalation_state", lambda: state)
    monkeypatch.setattr(s, "_save_escalation_state", lambda _st: None)
    monkeypatch.setattr(s, "step_escalation", lambda *a, **k: (state, actions))
    monkeypatch.setattr(s, "_execute_observe", lambda _a: None)
    monkeypatch.setattr(s, "_execute_mint", lambda *a, **k: mint_svar)
    monkeypatch.setattr("core.services.smith_noise_veto.maa_minte",
                        lambda *a, **k: (maa, "doemt_stoej" if not maa else "doemt_aegte"))

    res = s.run_escalation_tick()
    return pat, actions, res


def test_veto_ruller_trin_tilbage_til_kommentar(monkeypatch):
    """Et veto betyder at INTET blev bundet — saa maa tilstanden ikke sige Trin 2.

    Maalt foer: rung=2, 121 cyklusser, decision_id=None, nul direktiver i basen.
    """
    pat = {"kind": "behaviour", "label": "gentaget fejl: X", "rung": 2,
           "cycles_at_rung": 40, "decision_id": None, "last_metric": 9.0}
    pat, _, _ = _kør_tick(monkeypatch, maa=False, mint_svar=None, pat=pat)
    assert pat["rung"] == 1, "tilstanden paastaar stadig en binding der ikke findes"
    assert pat["cycles_at_rung"] == 0


def test_veto_tier_ikke_stemmen(monkeypatch):
    """Vetoet blokerer BINDINGEN, ikke stemmen.

    Maalt 13/11-2026: den 1350x tavse `&&`-fejl blev doemt STOEJ, og Smith sagde
    intet om den i nogen prompt. En maalt fejl han ikke maa binde, skal han
    stadig kunne naevne.
    """
    pat = {"kind": "behaviour", "label": "gentaget fejl: X", "rung": 2,
           "cycles_at_rung": 40, "decision_id": None, "last_metric": 9.0}
    _, actions, _ = _kør_tick(monkeypatch, maa=False, mint_svar=None, pat=pat)
    stemmer = [a for a in actions if a.get("type") == "voice"]
    assert stemmer, "vetoet gjorde Smith tavs om praecis det han maalte"
    assert stemmer[0]["rung"] == "comment"


def test_mint_der_fejler_ruller_ogsaa_tilbage(monkeypatch):
    """Samme loegn ad den anden vej: vetoet siger ja, men mint returnerer None."""
    pat = {"kind": "behaviour", "label": "gentaget fejl: X", "rung": 2,
           "cycles_at_rung": 40, "decision_id": None, "last_metric": 9.0}
    pat, _, _ = _kør_tick(monkeypatch, maa=True, mint_svar=None, pat=pat)
    assert pat["rung"] == 1
    assert not pat.get("decision_id")


def test_gennemfoert_mint_bevarer_trin_2(monkeypatch):
    """Positiv kontrol: lykkes mintet, ER bindingen aegte og skal blive staaende."""
    pat = {"kind": "behaviour", "label": "gentaget fejl: X", "rung": 2,
           "cycles_at_rung": 40, "decision_id": None, "last_metric": 9.0}
    pat, _, _ = _kør_tick(monkeypatch, maa=True, mint_svar="dec_abc123", pat=pat)
    assert pat["rung"] == 2, "en gennemfoert binding maa ikke rulles tilbage"
    assert pat["decision_id"] == "dec_abc123"


# ── 3. En staaende binding skal siges hver tur ──────────────────────────────


def test_staaende_binding_siges_naar_der_ikke_er_nogen_ny_eskalering(monkeypatch):
    """En forpligtelse ingen hoerer er ikke en forpligtelse.

    Maalt: moensteret stod paa Trin 2 med 121 cyklusser og nul voice-actions —
    `top_line` var tom, saa Smith havde bundet Jarvis og sagde det ikke.
    """
    pat = {"kind": "behaviour", "label": "gentaget fejl: X", "rung": 2,
           "cycles_at_rung": 40, "decision_id": "dec_abc123", "last_metric": 9.0}
    # Mint lykkes (samme decision_id) → rung bliver 2, og der er INGEN voice-action
    # fra eskaleringen. Den staaende linje er derfor det eneste der kan tale.
    pat, actions, res = _kør_tick(monkeypatch, maa=True,
                                  mint_svar="dec_abc123", pat=pat)
    stemmer = [a for a in actions if a.get("type") == "voice"]
    assert not stemmer, "testen skal maale den STAAENDE linje, ikke mint-stemmen"
    assert res.get("line"), "en aktiv binding uden en stemme er tavs håndhævelse"
    assert "regel" in res["line"] or "ord var ikke nok" in res["line"]
