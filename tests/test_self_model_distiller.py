"""Tests for rig selv-model-distiller (#4, b + 2 guards)."""
from __future__ import annotations

from core.services import self_model_distiller as smd


def test_richness_ranks_rich_over_generic():
    rich = {"identity_focus": "bounded runtime truth", "growth_direction": "stay bounded",
            "confidence": "high"}
    generic = {"identity_focus": "visible-work", "growth_direction": "observe:monitor",
               "confidence": "low"}
    assert smd._richness(rich) > smd._richness(generic)
    assert smd._richness({}) == -1


def test_parse_labeled_output():
    raw = ("FOKUS: bounded runtime truth\n"
           "VÆKST: stay bounded\n"
           "ARBEJDSMODE: concise scoped changes\n"
           "SPÆNDING: none")
    p = smd._parse(raw)
    assert p["identity_focus"] == "bounded runtime truth"
    assert p["growth_direction"] == "stay bounded"
    assert p["preferred_work_mode"] == "concise scoped changes"
    assert p["recurring_tension"] == "none"


def test_parse_tolerates_missing_lines():
    assert smd._parse("FOKUS: something specific\ngarbage line") == {
        "identity_focus": "something specific"}


def _setup(monkeypatch, *, current, llm_out):
    monkeypatch.setattr(smd, "_gather_inputs", lambda: "SELV-HISTORIE: noget")
    monkeypatch.setattr(smd, "_current_model", lambda: current)
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call", lambda *a, **k: llm_out)
    writes: list[dict] = []
    monkeypatch.setattr("core.runtime.db_private_states.record_private_self_model",
                        lambda **kw: writes.append(kw))
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda *a, **k: None)
    return writes


def test_writes_rich_over_generic_current(monkeypatch):
    writes = _setup(
        monkeypatch,
        current={"identity_focus": "visible-work", "growth_direction": "observe:monitor",
                 "confidence": "low"},
        llm_out=("FOKUS: bounded runtime truth\nVÆKST: stay bounded\n"
                 "ARBEJDSMODE: concise scoped changes\nSPÆNDING: none"))
    res = smd.distill_self_model(trigger="test")
    assert res["status"] == "ok"
    assert len(writes) == 1
    assert writes[0]["identity_focus"] == "bounded runtime truth"
    assert writes[0]["source"] == "distilled"
    assert writes[0]["confidence"] == "high"


def test_anti_flatten_skips_thinner_than_current(monkeypatch):
    """GUARD 1: current er RIG; LLM giver generisk → skriv IKKE (identitet flades ikke ud)."""
    writes = _setup(
        monkeypatch,
        current={"identity_focus": "bounded runtime truth", "growth_direction": "stay bounded",
                 "confidence": "high"},
        llm_out="FOKUS: visible-work\nVÆKST: observe\nARBEJDSMODE: x\nSPÆNDING: none")
    res = smd.distill_self_model(trigger="test")
    assert res["status"] == "skip" and res["reason"] == "would-flatten"
    assert writes == []


def test_fresh_meaningful_replaces_stale_meaningful_even_if_shorter(monkeypatch):
    """GUARD 1 må IKKE fryse: en frisk KORTERE men meningsfuld identitet vinder over en
    stale længere ('bounded runtime truth' → 'clarity' er OK; kun generisk afvises)."""
    writes = _setup(
        monkeypatch,
        current={"identity_focus": "bounded runtime truth", "growth_direction": "stay bounded",
                 "confidence": "high"},
        llm_out="FOKUS: clarity\nVÆKST: deepen\nARBEJDSMODE: focused\nSPÆNDING: none")
    res = smd.distill_self_model(trigger="test")
    assert res["status"] == "ok"
    assert writes and writes[0]["identity_focus"] == "clarity"


def test_llm_empty_skips(monkeypatch):
    writes = _setup(monkeypatch, current={}, llm_out="")
    res = smd.distill_self_model(trigger="test")
    assert res["status"] == "skip" and res["reason"] == "llm-empty"
    assert writes == []


def test_self_safe_on_llm_error(monkeypatch):
    monkeypatch.setattr(smd, "_gather_inputs", lambda: "x")
    monkeypatch.setattr(smd, "_current_model", lambda: {})

    def _boom(*a, **k):
        raise RuntimeError("llm nede")

    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call", _boom)
    res = smd.distill_self_model(trigger="test")
    assert res["status"] == "error"  # fanget, ikke kastet


def test_no_inputs_skips(monkeypatch):
    monkeypatch.setattr(smd, "_gather_inputs", lambda: "")
    res = smd.distill_self_model(trigger="test")
    assert res["status"] == "skip" and res["reason"] == "no-inputs"
