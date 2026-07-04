"""Bölge 2 (spec 2026-07-03 §2/§4): de kognitive daemons der før kaldte cheap-lane/
provider DIREKTE — uden om daemon_llm-choke-pointet — er nu rutet IND i choke-pointet,
så form-dommeren + TTL-cachen dækker deres gentagelser.

Disse tests verificerer PRÆCIS routingen (ikke adfærd): hver rørt direkte-kalder kalder nu
`daemon_llm.daemon_llm_call` (privat cheap-lane) eller `daemon_public_safe_llm_call`
(public-safe) med det rette daemon_name, og bevarer output-kontrakten (rå tekst / parse /
fallback). Ingen netværk/LLM — choke-pointet mockes.
"""
from __future__ import annotations

import core.services.daemon_llm as dl


# ---------------------------------------------------------------------------
# meta_cognition_daemon._call_meta_llm → daemon_llm_call (privat cheap-lane)
# ---------------------------------------------------------------------------
def test_meta_cognition_routes_through_daemon_llm_call(monkeypatch):
    import core.services.meta_cognition_daemon as mcd

    captured = {}

    def _fake(prompt, *, max_len=200, fallback="", daemon_name=""):
        captured["daemon_name"] = daemon_name
        captured["prompt"] = prompt
        return "meta-observation i første person, tre sætninger her."

    monkeypatch.setattr(dl, "daemon_llm_call", _fake)
    out = mcd._call_meta_llm("Observér din tilstand.")
    assert captured["daemon_name"] == "meta_cognition"
    assert out.startswith("meta-observation")


def test_meta_cognition_falls_back_to_ollama_on_empty(monkeypatch):
    """daemon_llm_call giver "" → funktionen falder igennem til Ollama-stien (som før)."""
    import core.services.meta_cognition_daemon as mcd

    monkeypatch.setattr(dl, "daemon_llm_call", lambda *a, **k: "")
    # Ollama-router utilgængelig → funktionen returnerer "" uden at kaste.
    monkeypatch.setattr(
        "core.runtime.provider_router.resolve_provider_router_target",
        lambda **k: {"active": False},
    )
    assert mcd._call_meta_llm("x") == ""


# ---------------------------------------------------------------------------
# recurrence_loop_daemon._call_recurrence_llm → daemon_llm_call (privat cheap-lane)
# ---------------------------------------------------------------------------
def test_recurrence_routes_through_daemon_llm_call(monkeypatch):
    import core.services.recurrence_loop_daemon as rld

    captured = {}

    def _fake(prompt, *, max_len=200, fallback="", daemon_name=""):
        captured["daemon_name"] = daemon_name
        return "essensen af tanken, hvad den leder til."

    monkeypatch.setattr(dl, "daemon_llm_call", _fake)
    out = rld._call_recurrence_llm("Indre stemme-indhold")
    assert captured["daemon_name"] == "recurrence_loop"
    assert "essensen" in out


# ---------------------------------------------------------------------------
# world_model_auto_extraction → daemon_public_safe_llm_call (public-safe)
# ---------------------------------------------------------------------------
def test_world_model_extraction_routes_through_public_safe(monkeypatch):
    import core.services.world_model_auto_extraction as wm

    store: dict[str, object] = {}
    monkeypatch.setattr(wm, "load_json", lambda k, default=None: store.get(k, default))
    monkeypatch.setattr(wm, "save_json", lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr(wm, "_under_rate_limit", lambda: True)

    captured = {}

    def _fake(prompt, *, max_len=200, fallback="", daemon_name=""):
        captured["daemon_name"] = daemon_name
        return ('{"is_prediction": true, "subject": "deploy", '
                '"expectation": "virker", "confidence": "high"}')

    monkeypatch.setattr(dl, "daemon_public_safe_llm_call", _fake)
    import core.services.world_model_signal_tracking as wmst
    monkeypatch.setattr(wmst, "record_runtime_world_model_prediction",
                        lambda **kw: {"prediction_id": "p1"})
    import core.services.central_private_observe as cpo
    monkeypatch.setattr(cpo, "record_private", lambda *a, **k: True)

    res = wm.auto_extract_and_record(matched_phrase="jeg tror", context_excerpt="vi deployer")
    assert res["status"] == "ok" and res["subject"] == "deploy"
    assert captured["daemon_name"] == "world_model_auto_extraction"


# ---------------------------------------------------------------------------
# counterfactual_engine._generate_one_via_llm → daemon_public_safe_llm_call
# ---------------------------------------------------------------------------
def test_counterfactual_routes_through_public_safe(monkeypatch):
    import core.services.counterfactual_engine as ce

    captured = {}

    def _fake(prompt, *, max_len=200, fallback="", daemon_name=""):
        captured["daemon_name"] = daemon_name
        return '{"what_if": "hvad hvis X", "confidence": 0.7}'

    monkeypatch.setattr(dl, "daemon_public_safe_llm_call", _fake)

    trigger = ce.TriggerEvent(
        source_event_id=1, workspace_id="default", event_type="deploy",
        primary_key="k1", summary="vi deployer nu", payload={}, created_at="2026-07-04",
    )
    parsed = ce._generate_one_via_llm(trigger)
    assert captured["daemon_name"] == "counterfactual_engine"
    assert parsed is not None
    assert parsed["what_if"] == "hvad hvis X"
    assert parsed["llm_confidence"] == 0.7


def test_counterfactual_returns_none_on_empty(monkeypatch):
    """Tom tekst fra choke-pointet → None (uændret fallback-kontrakt)."""
    import core.services.counterfactual_engine as ce

    monkeypatch.setattr(dl, "daemon_public_safe_llm_call", lambda *a, **k: "")
    trigger = ce.TriggerEvent(
        source_event_id=1, workspace_id="default", event_type="deploy",
        primary_key="k1", summary="x", payload={}, created_at="2026-07-04",
    )
    assert ce._generate_one_via_llm(trigger) is None


# ---------------------------------------------------------------------------
# jarvis_brain_daemon._call_ollamafreeapi (public-safe sti) → public-safe choke-point
# ---------------------------------------------------------------------------
def test_jarvis_brain_public_safe_routes_through_choke_point(monkeypatch):
    import core.services.jarvis_brain_daemon as jbd

    captured = {}

    def _fake(prompt, *, max_len=200, fallback="", daemon_name=""):
        captured["daemon_name"] = daemon_name
        return '{"contradicts": false, "reason": "ok"}'

    monkeypatch.setattr(dl, "daemon_public_safe_llm_call", _fake)
    parsed = jbd._call_ollamafreeapi("A vs B?")
    assert captured["daemon_name"] == "jarvis_brain"
    assert parsed == {"contradicts": False, "reason": "ok"}


# ---------------------------------------------------------------------------
# experiential_memory._call_scoring_llm → daemon_public_safe_llm_call
# ---------------------------------------------------------------------------
def test_experiential_scoring_routes_through_public_safe(monkeypatch):
    import core.services.experiential_memory as em

    captured = {}

    def _fake(prompt, *, max_len=200, fallback="", daemon_name=""):
        captured["daemon_name"] = daemon_name
        return '{"exp-1": 0.8}'

    monkeypatch.setattr(dl, "daemon_public_safe_llm_call", _fake)
    out = em._call_scoring_llm({"provider": "x"}, "score these")
    assert captured["daemon_name"] == "experiential_memory"
    assert out == '{"exp-1": 0.8}'


# ---------------------------------------------------------------------------
# memory_graph backup path: invalid timeout= kwarg fjernet → routes to public-safe
# ---------------------------------------------------------------------------
def test_memory_graph_backup_routes_and_no_invalid_kwarg(monkeypatch):
    import core.services.memory_graph as mg

    # Primær OllamaFreeAPI fejler → backup skal ramme choke-pointet (før: TypeError
    # på timeout= → tom liste). Nu: daemon_public_safe_llm_call med daemon_name.
    def _boom(*a, **k):
        raise RuntimeError("free api down")

    monkeypatch.setattr(
        "core.runtime.ollamafreeapi_provider.call_ollamafreeapi", _boom
    )

    captured = {}

    def _fake(prompt, *, max_len=200, fallback="", daemon_name=""):
        captured["daemon_name"] = daemon_name
        return '[["a", "rel", "b"]]'

    monkeypatch.setattr(dl, "daemon_public_safe_llm_call", _fake)
    triples = mg.extract_from_text("Dette er en sætning der er lang nok til at trigge extraction.")
    assert captured["daemon_name"] == "memory_graph"
    assert triples == [("a", "rel", "b")]
