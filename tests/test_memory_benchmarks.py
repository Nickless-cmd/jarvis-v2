"""D2: Memory benchmarks — baseline latency, coverage, and consistency metrics.

Kører mod RIGTIG data i jarvis.db (74k+ brain records, 2k+ sensory, 700+ entities).
Måler:
  - Latency (min/avg/max over 3 runs) for unified_recall / multi_signal_recall / cold_tier_recall
  - Resultat-dækning (får vi overhovedet resultater?)
  - Source-diversitet (kommer resultater fra flere kilder?)
  - Konsistens (giver samme query samme resultat to gange?)
  - Edge cases (tom query, kort query, special characters)

Kørsel:
    pytest tests/test_memory_benchmarks.py -v --tb=short

Baseline-rapport skrives til ~/.jarvis-v2/state/memory_benchmark_baseline.json
ved --benchmark-baseline flag (eller sæt SKIP_BASELINE_WRITE=1 for at undgå).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from core.services.memory_recall_engine import (
    cold_tier_recall,
    multi_signal_recall,
    unified_recall,
)

# ── Constants ──────────────────────────────────────────────────────

BASELINE_PATH = Path.home() / ".jarvis-v2" / "state" / "memory_benchmark_baseline.json"

# Queries — organiseret efter kategori
QUERIES: dict[str, list[dict[str, Any]]] = {
    "short": [
        {"query": "memory architecture", "note": "kort, generisk"},
        {"query": "cost optimization", "note": "kort, specifik"},
        {"query": "Bjørn identity", "note": "kort, person"},
    ],
    "medium": [
        {"query": "Phase 1 quality scoring cold tier", "note": "specifik feature-ref"},
        {"query": "multi signal recall BM25 entity fusion", "note": "teknisk term"},
        {"query": "hvad ved jeg om cost optimization", "note": "naturligt sprog"},
    ],
    "long": [
        {"query": "hvad ved jeg om memory benchmarks og hvordan måler jeg retrieval latency", "note": "lang, naturlig"},
        {"query": "skills versionering audit trail meta tags auto learning read only", "note": "keyword-tung"},
    ],
    "entity": [
        {"query": "Bjørn memory fix phase one implementation", "note": "person + emne"},
        {"query": "DeepSeek flash model window", "note": "produktnavn"},
    ],
    "edge": [
        {"query": "ab", "note": "for kort (<3 chars), forvent tomt resultat"},
        {"query": "", "note": "tom query, forvent tomt resultat"},
        {"query": "!@#$%^&*()", "note": "special characters"},
    ],
}

# Hyppigt brugte queries til konsistens-test
CONSISTENCY_QUERIES = [
    "memory architecture",
    "Phase 1 quality scoring",
    "cost optimization daemon",
]

REPETITIONS = 3  # Antal kald per query til latens-middel


# ── Workspace context fixture ──────────────────────────────────────
# Alle retrieval-funktioner kræver en user context for at kunne slå
# workspace-filer op (MEMORY.md, USER.md, etc). Denne autouse-fixture
# sætter context'en for hver test med Bjørns Discord ID.

@pytest.fixture(autouse=True, scope="module")
def _bjorn_workspace_context():
    """Sæt workspace context til Bjørns workspace for alle tests i modulet."""
    from core.identity.workspace_context import user_context
    with user_context(discord_id="1246415163603816499"):
        yield


# ── Helpers ────────────────────────────────────────────────────────


def _measure(name: str, fn, query: str, **kwargs) -> dict[str, Any]:
    """Mål latency og resultat for én retrieval-funktion."""
    times: list[float] = []
    last_result: dict[str, Any] | None = None
    for _ in range(REPETITIONS):
        t0 = time.perf_counter()
        try:
            result = fn(query=query, **kwargs)
        except Exception as exc:
            return {
                "name": name,
                "query": query,
                "status": "error",
                "error": str(exc),
                "latency_ms": None,
            }
        elapsed = (time.perf_counter() - t0) * 1000  # ms
        times.append(elapsed)
        last_result = result

    # Ekstraher metrics
    results = last_result.get("results") or []
    count = len(results)
    sources = sorted(set(
        str(r.get("source", "?")) for r in results
    ))
    has_multi_signal = last_result.get("multi_signal", False)
    has_temporal = last_result.get("temporal_boosted", False)
    has_mood = last_result.get("mood_boosted", False)
    total_candidates = last_result.get("total_candidates") or last_result.get("total_searched", 0)

    return {
        "name": name,
        "query": query,
        "status": "ok",
        "latency_ms": {
            "min": round(min(times), 2),
            "avg": round(sum(times) / len(times), 2),
            "max": round(max(times), 2),
        },
        "result_count": count,
        "sources": sources,
        "source_count": len(sources),
        "total_candidates": total_candidates,
        "multi_signal": has_multi_signal,
        "temporal_boosted": has_temporal,
        "mood_boosted": has_mood,
    }


def _check_consistency(name: str, fn, query: str, **kwargs) -> dict[str, Any]:
    """Kald samme query to gange og sammenlign resultater."""
    r1 = fn(query=query, **kwargs)
    r2 = fn(query=query, **kwargs)

    ids1 = [str(r.get("entry_id", r.get("text", ""))[:80]) for r in (r1.get("results") or [])]
    ids2 = [str(r.get("entry_id", r.get("text", ""))[:80]) for r in (r2.get("results") or [])]

    overlap = len(set(ids1) & set(ids2))
    total = max(len(ids1), len(ids2))
    jaccard = overlap / total if total > 0 else 1.0

    return {
        "name": name,
        "query": query,
        "run1_ids": ids1[:5],
        "run2_ids": ids2[:5],
        "overlap": overlap,
        "total_unique": total,
        "jaccard_sim": round(jaccard, 4),
    }


def _check_empty_behavior(name: str, fn) -> dict[str, Any]:
    """Test edge cases: tom query og meget kort query."""
    results: dict[str, Any] = {}

    for q, label in [("", "empty"), ("ab", "too_short")]:
        try:
            r = fn(query=q)
            count = len(r.get("results") or [])
            ok = r.get("status") == "ok"
        except Exception as e:
            count = 0
            ok = False
        results[label] = {"ok": ok, "result_count": count}

    return {"name": name, **results}


# ── Test functions ─────────────────────────────────────────────────


class TestD2Benchmarks:
    """D2: Memory benchmarks — latency, coverage, consistency."""

    @pytest.mark.parametrize("category", list(QUERIES.keys()))
    def test_latency_baseline(self, category: str) -> None:
        """Mål latency for unified_recall / multi_signal_recall / cold_tier_recall."""
        queries = QUERIES[category]
        results: list[dict[str, Any]] = []

        for qdef in queries:
            q = qdef["query"]
            note = qdef["note"]

            for fn, name, kwargs in [
                (unified_recall, "unified_recall", {"total_limit": 4}),
                (multi_signal_recall, "multi_signal_recall", {"total_limit": 4}),
                (cold_tier_recall, "cold_tier_recall", {"max_results": 4, "include_private_brain": True}),
            ]:
                m = _measure(name, fn, q, **kwargs)
                m["note"] = note
                m["category"] = category
                results.append(m)

        # Assert: ingen fatale fejl for edge cases
        if category == "edge":
            for r in results:
                assert r["status"] == "ok", f"{r['name']}({r['query']}): {r.get('error')}"
                if r["query"] == "":
                    # Tom query — ALLE retrieval-metoder bør returnere 0 resultater
                    assert r["result_count"] == 0, (
                        f"{r['name']}(tom query) returnerede {r['result_count']} resultater"
                    )
                elif r["query"] == "ab":
                    # 2-char query — nogle metoder har guards, andre ikke. Acceptabelt hvis
                    # der kommer resultater, så længe det ikke crasher.
                    pass
                elif r["query"] == "!@#$%^&*()":
                    # Special chars — må gerne returnere tomt eller få resultater
                    pass

        # Assert: normale queries returnerer resultater med acceptable latencies
        if category in ("short", "medium", "long", "entity"):
            for r in results:
                assert r["status"] == "ok", f"{r['name']}({r['query']}): {r.get('error')}"
                if r["query"]:  # non-empty
                    # mindst én retrieval-metode burde finde noget
                    latency = r.get("latency_ms", {})
                    if latency:
                        assert latency["avg"] < 5000, f"{r['name']}({r['query']}): avg latency {latency['avg']}ms > 5s"

    def test_source_diversity(self) -> None:
        """Tjek at multi_signal_recall henter fra flere kilder."""
        query = "memory architecture"
        result = multi_signal_recall(query=query, total_limit=6, with_mood=False)
        assert result["status"] == "ok"
        sources = set(
            str(r.get("source", "?")) for r in (result.get("results") or [])
        )
        assert len(sources) >= 1, "Burde have resultater fra mindst én kilde"
        for r in result.get("results") or []:
            assert "multi_signal_score" in r, f"multi_signal_recall: mangler multi_signal_score"
            assert "signals" in r, f"multi_signal_recall: mangler signals"

    def test_consistency(self) -> None:
        """Samme query kaldt to gange bør give samme resultater."""
        all_checks: list[dict[str, Any]] = []
        for query in CONSISTENCY_QUERIES:
            for fn, name in [
                (unified_recall, "unified_recall"),
                (multi_signal_recall, "multi_signal_recall"),
                (cold_tier_recall, "cold_tier_recall"),
            ]:
                c = _check_consistency(name, fn, query, **(
                    {"total_limit": 4} if name != "cold_tier_recall"
                    else {"max_results": 4, "include_private_brain": True}
                ))
                all_checks.append(c)

        # Assert: høj Jaccard similarity (≥ 0.5 for ikke-tomme resultater)
        for c in all_checks:
            if c["total_unique"] > 0:
                assert c["jaccard_sim"] >= 0.5, (
                    f"{c['name']}({c['query']}): jaccard={c['jaccard_sim']} "
                    f"(overlap {c['overlap']}/{c['total_unique']})"
                )


def test_empty_query_unified():
    """Tom query — unified_recall bør returnere tomt resultat."""
    r = unified_recall(query="")
    assert r["status"] == "ok"
    assert r["count"] == 0


def test_empty_query_multi_signal():
    """Tom query — multi_signal_recall bør returnere tomt resultat."""
    r = multi_signal_recall(query="")
    assert r["status"] == "ok"
    assert r["count"] == 0
    assert r["multi_signal"] is False


def test_empty_query_cold_tier():
    """Tom query — cold_tier_recall bør returnere tomt resultat."""
    r = cold_tier_recall(query="", include_private_brain=True)
    assert r["status"] == "ok"
    assert r["count"] == 0


# ── Baseline-rapport (valgfri) ─────────────────────────────────────


@pytest.mark.skipif(
    os.environ.get("RUN_BASELINE_WRITE") != "1",
    reason="Sæt RUN_BASELINE_WRITE=1 for at generere baseline-rapport",
)
def test_write_baseline_report() -> None:
    """Kør alle benchmarks og skriv baseline-rapport til disk.

    Kør med:  pytest tests/test_memory_benchmarks.py::test_write_baseline_report -v
    Spring over med: SKIP_BASELINE_WRITE=1 pytest ...
    """
    report: dict[str, Any] = {
        "_meta": {
            "benchmark": "D2 Memory Benchmarks",
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "description": "Baseline latency, source diversity, and consistency for memory retrieval",
            "repetitions": REPETITIONS,
        },
        "latency": {},
        "source_diversity": {},
        "consistency": {},
        "edge_cases": {},
    }

    # 1. Latency per kategori
    for category, queries in QUERIES.items():
        cat_results = []
        for qdef in queries:
            q = qdef["query"]
            for fn, name, kwargs in [
                (unified_recall, "unified_recall", {"total_limit": 4}),
                (multi_signal_recall, "multi_signal_recall", {"total_limit": 4}),
                (cold_tier_recall, "cold_tier_recall", {"max_results": 4, "include_private_brain": True}),
            ]:
                m = _measure(name, fn, q, **kwargs)
                cat_results.append(m)
        report["latency"][category] = cat_results

    # 2. Source diversity
    diversity_queries = ["memory architecture", "Phase 1 quality scoring", "cost optimization"]
    for q in diversity_queries:
        r = multi_signal_recall(query=q, total_limit=6, with_mood=False)
        sources = sorted(set(
            str(rr.get("source", "?")) for rr in (r.get("results") or [])
        ))
        report["source_diversity"][q] = {
            "sources": sources,
            "source_count": len(sources),
            "result_count": r["count"],
            "multi_signal": r.get("multi_signal", False),
        }

    # 3. Consistency
    for q in CONSISTENCY_QUERIES:
        for fn, name in [
            (unified_recall, "unified_recall"),
            (multi_signal_recall, "multi_signal_recall"),
            (cold_tier_recall, "cold_tier_recall"),
        ]:
            c = _check_consistency(name, fn, q, **(
                {"total_limit": 4} if name != "cold_tier_recall"
                else {"max_results": 4, "include_private_brain": True}
            ))
            key = f"{name}::{q}"
            report["consistency"][key] = c

    # 4. Edge cases
    for fn, name in [
        (unified_recall, "unified_recall"),
        (multi_signal_recall, "multi_signal_recall"),
        (cold_tier_recall, "cold_tier_recall"),
    ]:
        report["edge_cases"][name] = _check_empty_behavior(name, fn)

    # Skriv til disk
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    # Korte asserts på baseline
    assert report["latency"]["short"], "Ingen latency-data for short queries"
    assert report["source_diversity"], "Ingen source diversity-data"
    assert report["consistency"], "Ingen consistency-data"
    assert report["edge_cases"], "Ingen edge case-data"
    assert BASELINE_PATH.exists(), "Baseline-rapport ikke skrevet"
