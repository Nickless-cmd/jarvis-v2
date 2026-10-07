"""Tests for db_instrument — central_instrument's fund-persistens + scan-cache."""
from __future__ import annotations

from core.runtime import db_instrument as dbi


def test_filehash_roundtrip(isolated_runtime):
    assert dbi.get_file_hash("core/x.py") is None
    dbi.set_file_hash("core/x.py", "abc123", 3)
    assert dbi.get_file_hash("core/x.py") == "abc123"


def test_replace_and_list_findings(isolated_runtime):
    dbi.replace_file_findings("core/x.py", [
        {"signature": "bare_except:aaa", "line": 5, "kind": "bare_except",
         "severity": "critical", "score": 5, "function": "f", "snippet": "except:"},
        {"signature": "todo:bbb", "line": 9, "kind": "todo",
         "severity": "low", "score": 0, "function": "", "snippet": "# TODO"},
    ])
    rows = dbi.list_findings(status="open", min_score=0, limit=10)
    assert len(rows) == 2
    # højeste score først
    assert rows[0]["score"] >= rows[-1]["score"]
    # min_score filtrerer
    assert all(r["score"] >= 3 for r in dbi.list_findings(min_score=3))


def test_replace_removes_fixed_findings(isolated_runtime):
    dbi.replace_file_findings("core/y.py", [
        {"signature": "s1", "line": 1, "kind": "bare_except", "severity": "critical",
         "score": 5, "function": "f", "snippet": "x"},
    ])
    assert len(dbi.list_findings(limit=10)) >= 1
    # næste scan: koden er rettet → ingen fund for filen
    dbi.replace_file_findings("core/y.py", [])
    assert all(r["file"] != "core/y.py" for r in dbi.list_findings(limit=50))


def test_summary_counts(isolated_runtime):
    dbi.replace_file_findings("core/z.py", [
        {"signature": "h1", "line": 1, "kind": "except_silent", "severity": "high",
         "score": 4, "function": "f", "snippet": "x"},
    ])
    s = dbi.summary()
    assert s["high"] >= 1 and s["total"] >= 1 and s["proposals"] >= 1


def test_set_finding_status_lukker_hagen(isolated_runtime):
    """Et accepteret fund forsvinder fra open-listen — så daemonen ikke genindsender."""
    dbi.replace_file_findings("core/w.py", [
        {"signature": "sig-w", "line": 1, "kind": "except_silent", "severity": "high",
         "score": 5, "function": "f", "snippet": "x"},
    ])
    assert any(r["signature"] == "sig-w" for r in dbi.list_findings(status="open", limit=10))

    assert dbi.set_finding_status("sig-w", "accepted") is True
    assert not any(r["signature"] == "sig-w" for r in dbi.list_findings(status="open", limit=10))

    # ukendt signatur + tom input → False (self-safe)
    assert dbi.set_finding_status("findes-ikke", "accepted") is False
    assert dbi.set_finding_status("", "accepted") is False


def test_accepted_fund_overlever_naeste_scan(isolated_runtime):
    """replace_file_findings bevarer 'accepted' — lukningen ruller ikke tilbage."""
    dbi.replace_file_findings("core/v.py", [
        {"signature": "sig-v", "line": 1, "kind": "except_silent", "severity": "high",
         "score": 5, "function": "f", "snippet": "x"},
    ])
    assert dbi.set_finding_status("sig-v", "accepted") is True
    # næste scan finder samme mønster igen
    dbi.replace_file_findings("core/v.py", [
        {"signature": "sig-v", "line": 1, "kind": "except_silent", "severity": "high",
         "score": 5, "function": "f", "snippet": "x"},
    ])
    assert not any(r["signature"] == "sig-v" for r in dbi.list_findings(status="open", limit=10))
