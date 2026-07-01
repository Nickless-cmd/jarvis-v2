"""procedure_bank feed (LivingNeuron Fase B) — anti-skrald + navngiven optagelse."""
from core.services import procedure_bank_pipeline as pb


def test_feed_skips_too_few_tools(isolated_runtime):
    assert pb.maybe_record_procedure_from_run(session_id="s", tool_calls=["web_search"]) is None


def test_feed_skips_without_topic(isolated_runtime):
    # nok tools men intet meningsfuldt session-topic → skip (undgå støj-procedurer)
    assert pb.maybe_record_procedure_from_run(session_id="no-topic", tool_calls=["a", "b"]) is None


def test_feed_records_named_procedure(isolated_runtime, monkeypatch):
    # med topic + ≥2 distinkte tools → navngiven procedure gemmes
    monkeypatch.setattr(pb, "load_session_topics",
                        lambda sid: [{"label": "netværks-fejlfinding"}], raising=False)
    # load_session_topics importeres lokalt i funktionen → patch kilden
    import core.services.session_topic_tracker as st
    monkeypatch.setattr(st, "load_session_topics", lambda sid: [{"label": "netværks-fejlfinding"}])
    rec = pb.maybe_record_procedure_from_run(session_id="s1", tool_calls=["ping", "traceroute", "ping"])
    assert rec is not None
    assert "netværks-fejlfinding" in rec["name"]
    assert "→" in rec["procedure"]  # tool-sekvens
