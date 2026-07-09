# tests/test_central_agent_smith.py
from core.services import central_agent_smith as s


def test_repeated_phrases_catches_cross_message():
    msgs = ["jeg kører nu med det samme", "jeg kører nu igen", "helt andet emne her", "jeg kører nu tredje gang"]
    hits = s.repeated_phrases(msgs, min_msgs=3)
    assert any("jeg kører nu" in h["phrase"] for h in hits)


def test_repeated_phrases_ignores_unique():
    msgs = ["alfa beta gamma delta", "epsilon zeta eta theta", "en to tre fire fem"]
    assert s.repeated_phrases(msgs, min_msgs=3) == []


def test_cluster_similarity_high_vs_low():
    same = ["cache hit er 38 procent på flash"] * 4
    assert s.cluster_similarity(same) > 0.9
    diverse = ["alfa beta", "helt andre ord her", "tredje unikke sætning nu"]
    assert s.cluster_similarity(diverse) < 0.4


def test_decision_patterns_catches_repeated_sig():
    sigs = ["semantic_search", "semantic_search", "read_file", "semantic_search"]
    hits = s.decision_patterns(sigs, min_runs=3)
    assert hits and hits[0]["signature"] == "semantic_search" and hits[0]["in_runs"] == 3


def test_score_monotone_and_bounds():
    assert s.score([], 0.0, []) == 0.0
    hi = s.score([{"phrase": "x", "in_messages": 5}] * 5, 1.0, [{"signature": "y", "in_runs": 5}] * 3)
    assert 0.9 <= hi <= 1.0
    assert s.score([], 0.0, []) < hi


def test_smith_voice_points_at_top_repeat_when_high():
    v = s.smith_voice([{"phrase": "jeg kører nu", "in_messages": 9}], 0.7, [], 0.8)
    assert "jeg kører nu" in v and "Varier" in v
    low = s.smith_voice([], 0.0, [], 0.1)
    assert "Varier" not in low
