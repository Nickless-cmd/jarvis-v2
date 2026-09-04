from __future__ import annotations

from scripts.memory_probe import FIXTURE, format_report, load_probes, run_probes, score_probe


def test_fixture_has_twenty_probes_with_expectations():
    probes = load_probes(FIXTURE)
    assert len(probes) == 20
    assert all(p.get("query") and p.get("expect") for p in probes)


def test_score_probe_is_case_insensitive_any_of():
    assert score_probe(["PfSense-nøglen ligger i .ENV"], ["pfsense", "xyz"])
    assert not score_probe(["noget andet"], ["pfsense"])


def test_run_probes_counts_hits_and_isolates_errors():
    probes = [
        {"id": "a", "query": "pfsense", "expect": ["pfsense"]},
        {"id": "b", "query": "mikrofon", "expect": ["nos x500"]},
    ]

    def good(q, n):
        return ["pfSense i .env"] if "pfsense" in q else ["intet"]

    def boom(q, n):
        raise RuntimeError("index down")

    out = run_probes(probes, sources={"good": good, "boom": boom}, limit=3)
    assert out["hit_at_n"]["good"] == {"hits": 1, "rate": 0.5}
    assert out["hit_at_n"]["boom"] == {"hits": 0, "rate": 0.0}
    assert out["rows"][0]["errors"]["boom"].startswith("index down")
    report = format_report(out)
    assert "hit@3" in report and "good" in report
