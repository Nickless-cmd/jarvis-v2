"""Lærings-sløjfens tre bevis-niveauer (blok B, 2026-09-04).

Fejlen indtil nu: skriveren udsendte bevis-klasser gaten ikke kendte, så to af
tre niveauer kunne STRUKTURELT aldrig auto-anvendes — uanset hvor tydeligt
Bjørn havde sagt det. Disse tests holder de to ordlister sammen.
"""
from __future__ import annotations

import pytest

from core.identity import candidate_workflow as CW
from core.services import end_of_run_memory_consolidation as EOR


@pytest.mark.parametrize("raw,level", [
    ("explicit", "explicit"),
    ("explicit-user-statement", "explicit"),      # gammel værdi, samme betydning
    ("confirmed", "confirmed"),
    ("explicit-assistant-confirmation", "confirmed"),
    ("inferred", "inferred"),
    ("", "inferred"),
    ("noget-helt-andet", "inferred"),
])
def test_evidence_words_map_to_three_levels(raw, level):
    assert EOR._normalize_evidence(raw) == level


def test_writer_and_gate_agree_on_the_class_names():
    """Enhver klasse skriveren kan udsende skal gaten kende — ellers er
    niveauet dødt uden at nogen opdager det."""
    produced = {EOR._evidence_class_for_source(w) for w in ("explicit", "confirmed", "inferred")}
    produced.add("repeated_cross_session")  # sættes ved eskalering
    known = CW._AUTO_APPLY_EVIDENCE_CLASSES | {"runtime_inference"}
    assert produced <= known


def test_explicit_and_confirmed_are_written_now_inferred_is_only_counted():
    assert EOR._evidence_class_for_source("explicit") in CW._AUTO_APPLY_EVIDENCE_CLASSES
    assert EOR._evidence_class_for_source("confirmed") in CW._AUTO_APPLY_EVIDENCE_CLASSES
    assert EOR._evidence_class_for_source("inferred") not in CW._AUTO_APPLY_EVIDENCE_CLASSES
    assert "repeated_cross_session" in CW._AUTO_APPLY_EVIDENCE_CLASSES


def test_four_questions_produce_four_item_kinds():
    items = EOR._normalize_memory_items([
        {"target": "USER.md", "kind": "preference", "evidence": "explicit",
         "line": "- Bjørn vil have korte mellemregninger", "summary": "mellemregninger"},
        {"target": "REQUEST", "kind": "request", "evidence": "explicit",
         "request": "commit det færdige arbejde"},
        {"target": "USER.md", "kind": "correction", "evidence": "explicit",
         "line": "- Sig ikke 'det er ikke' — han har forbudt vendingen"},
        {"target": "MEMORY.md", "kind": "fact", "evidence": "inferred",
         "line": "- pfsense-nøglen ligger i .env"},
    ])
    assert [i["target"] for i in items] == ["USER.md", "REQUEST", "USER.md", "MEMORY.md"]
    assert items[1]["request"] == "commit det færdige arbejde"
    assert items[3]["evidence"] == "inferred"


def test_request_without_five_words_is_dropped():
    assert EOR._normalize_memory_items([{"target": "REQUEST", "request": ""}]) == []


def test_inferred_escalates_when_the_same_conclusion_returns_in_another_session(monkeypatch):
    rows = [{"canonical_key": "user-preference:llm:preference-abc", "session_id": "s-1"}]
    monkeypatch.setattr("core.runtime.db.list_runtime_contract_candidates",
                        lambda **kw: rows)
    assert EOR._seen_in_another_session(
        canonical_key="user-preference:llm:preference-abc", target="USER.md",
        candidate_type="preference_update", session_id="s-2") is True
    assert EOR._seen_in_another_session(
        canonical_key="user-preference:llm:preference-abc", target="USER.md",
        candidate_type="preference_update", session_id="s-1") is False
    assert EOR._seen_in_another_session(
        canonical_key="noget-andet", target="USER.md",
        candidate_type="preference_update", session_id="s-2") is False


def test_lookup_failure_never_escalates(monkeypatch):
    def _boom(**_kw):
        raise RuntimeError("db nede")
    monkeypatch.setattr("core.runtime.db.list_runtime_contract_candidates", _boom)
    assert EOR._seen_in_another_session(
        canonical_key="k", target="USER.md",
        candidate_type="preference_update", session_id="s") is False


def test_regex_detectors_are_off_by_default():
    from core.runtime.settings import load_settings
    from core.services.visible_runs_cognitive import _legacy_regex_detectors_enabled
    assert getattr(load_settings(), "legacy_regex_learning_detectors_enabled", None) is False
    assert _legacy_regex_detectors_enabled() is False
