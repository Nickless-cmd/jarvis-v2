"""Review-løkken må ikke kunne give sig selv ret uden dækning.

Den 11/6-2026 gav decision_review Jarvis «kept» på hans egen beslutning «verify
before I narrate» — samtidig med at han hallucinerede tool-arbejde. Testene her
holder de to ting fast der gjorde det muligt: at dommen ikke blev holdt op mod
noget ydre, og at `evidence` bare var en kopi af modellens egen forklaring.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import decision_review_prompter as P


def _beslutning(decision_id: str = "dec-1") -> dict:
    return {
        "decision_id": decision_id,
        "directive": "Verificér før du fortæller",
        "reason": "Jeg har fabrikeret arbejde før",
        "recent_reviews": [],
    }


@pytest.fixture
def _stubbet(monkeypatch):
    """Stub hele omverdenen: beslutninger, LLM og skrivning."""
    from core.services import behavioral_decisions as BD

    skrevet: list[dict] = []
    monkeypatch.setattr(BD, "list_active_decisions", lambda limit=20: [_beslutning()])
    monkeypatch.setattr(BD, "get_decision_with_reviews", lambda did, **k: _beslutning(did))
    monkeypatch.setattr(
        BD, "review_decision",
        lambda **kw: (skrevet.append(dict(kw)) or {"decision_id": kw["decision_id"]}),
    )
    return skrevet


def _svar(verdict: str):
    return lambda prompt, **kw: "VERDICT: %s\nREASONING: Jeg mener bestemt jeg holdt den." % verdict


# ---------------------------------------------------------------------------
# Trin 3: evidence må ALDRIG være en kopi af note
# ---------------------------------------------------------------------------


def test_evidence_er_ikke_en_kopi_af_note(_stubbet, monkeypatch):
    """Var de to felter ens, var der aldrig ydre bevis — kun forklaring."""
    from core.services import daemon_llm

    monkeypatch.setattr(daemon_llm, "quality_daemon_llm_call", _svar("kept"))
    monkeypatch.setattr(
        P, "gather_evidence",
        lambda **kw: {"has_evidence": True, "window_hours": 24.0,
                      "summary": "Værktøjer kørt (4 kald): bash×3, read_file×1 · Commits: ingen"},
    )
    P.review_pending_decisions()

    assert _stubbet, "der blev slet ikke skrevet en dom"
    post = _stubbet[0]
    assert post["note"] != post["evidence"], (
        "evidence er en kopi af note — så er der intet ydre bevis, kun modellens ord"
    )
    assert "bash×3" in post["evidence"], "evidence skal bære regnskabet"
    assert "mener bestemt" in post["note"], "note skal bære modellens begrundelse"


# ---------------------------------------------------------------------------
# Trin 2: positiv dom uden ydre spor må ikke løfte scoren
# ---------------------------------------------------------------------------


def test_kept_uden_spor_skrives_som_unknown(_stubbet, monkeypatch):
    from core.services import daemon_llm

    monkeypatch.setattr(daemon_llm, "quality_daemon_llm_call", _svar("kept"))
    monkeypatch.setattr(
        P, "gather_evidence",
        lambda **kw: {"has_evidence": False, "window_hours": 24.0,
                      "summary": "Værktøjer kørt: ingen · Commits: ingen"},
    )
    ud = P.review_pending_decisions()

    assert _stubbet[0]["verdict"] == "unknown"
    assert ud["downgraded_no_evidence"] == 1


def test_kept_med_spor_staar_ved_magt(_stubbet, monkeypatch):
    from core.services import daemon_llm

    monkeypatch.setattr(daemon_llm, "quality_daemon_llm_call", _svar("kept"))
    monkeypatch.setattr(
        P, "gather_evidence",
        lambda **kw: {"has_evidence": True, "window_hours": 24.0, "summary": "Commits (1): abc1234 fix"},
    )
    ud = P.review_pending_decisions()

    assert _stubbet[0]["verdict"] == "kept"
    assert ud["downgraded_no_evidence"] == 0


def test_broken_nedgraderes_aldrig(_stubbet, monkeypatch):
    """Et brud må stå selv når intet skete — fraværet af handling ER bruddet."""
    from core.services import daemon_llm

    monkeypatch.setattr(daemon_llm, "quality_daemon_llm_call", _svar("broken"))
    monkeypatch.setattr(
        P, "gather_evidence",
        lambda **kw: {"has_evidence": False, "window_hours": 24.0, "summary": "intet"},
    )
    P.review_pending_decisions()
    assert _stubbet[0]["verdict"] == "broken"


# ---------------------------------------------------------------------------
# Prompten
# ---------------------------------------------------------------------------


def test_regnskabet_staar_i_prompten():
    prompt = P._build_review_prompt(
        _beslutning(),
        {"summary": "Værktøjer kørt (2 kald): bash×2 · Commits: ingen", "window_hours": 12.0},
    )
    assert "bash×2" in prompt
    assert "REGNSKAB" in prompt
    assert "ikke fra din hukommelse" in prompt
    assert "REASONING:" in prompt


def test_parseren_taaler_baade_reasoning_og_gammel_evidence():
    """Ældre modelsvar skriver stadig EVIDENCE: — teksten skal ende i note uanset."""
    assert P._parse_review("VERDICT: kept\nREASONING: fordi X") == ("kept", "fordi X")
    assert P._parse_review("VERDICT: broken\nEVIDENCE: fordi Y") == ("broken", "fordi Y")
    assert P._parse_review("noget uden dom") is None


def test_vinduet_starter_ved_sidste_review(_stubbet, monkeypatch):
    """Regnskabet skal dække tiden SIDEN sidste dom, ikke et fast døgn."""
    from core.services import behavioral_decisions as BD
    from core.services import daemon_llm

    sidst = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    besl = _beslutning()
    besl["recent_reviews"] = [{"created_at": sidst}]
    monkeypatch.setattr(BD, "get_decision_with_reviews", lambda did, **k: besl)
    monkeypatch.setattr(daemon_llm, "quality_daemon_llm_call", _svar("broken"))

    set_vindue: list = []

    def _fanget(**kw):
        set_vindue.append(kw.get("since"))
        return {"has_evidence": True, "window_hours": 3.0, "summary": "x"}

    monkeypatch.setattr(P, "gather_evidence", _fanget)
    monkeypatch.setattr(P, "_dedup_gate_enabled", lambda: False)
    P.review_pending_decisions()

    assert set_vindue, "gather_evidence blev aldrig kaldt"
    alder = (datetime.now(UTC) - set_vindue[0]).total_seconds() / 3600
    assert 2.5 < alder < 3.5, "vinduet skulle starte ved sidste review (~3t siden)"
