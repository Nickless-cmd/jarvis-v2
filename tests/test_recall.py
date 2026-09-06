"""Task 4 (memory repair 2026-09-04): one recall path, one fused ranking."""
from __future__ import annotations

from unittest.mock import patch

from core.services import recall as R


def _stub(source: str, items: list[tuple[str, float]]):
    def _f(query: str, limit: int):
        return [{"source": source, "score": s, "text": t, "ref": f"{source}-{i}"} for i, (t, s) in enumerate(items)]
    return _f


def test_fuse_orders_by_native_and_bm25_and_dedupes():
    cands = [
        {"source": "workspace", "score": 0.9, "text": "§ pfSense nøgle: pfsense api-nøglen flyttet til .env via env_override", "ref": "a"},
        {"source": "brain", "score": 0.95, "text": "NOS X500 mikrofon installeret, USB ID 0a67:d159", "ref": "b"},
        {"source": "chronicle", "score": 0.4, "text": "§ pfSense nøgle: pfsense api-nøglen flyttet til .env via env_override", "ref": "dup"},
    ]
    out = R.fuse("pfsense nøgle .env", cands)
    assert [o["ref"] for o in out] == ["a", "b"], "dup text removed, query-matching text first"
    assert out[0]["score"] > out[1]["score"]
    assert "bm25" in out[0] and "native_score" in out[0]


def test_recall_merges_sources_and_is_failsoft():
    def _boom(query, limit):
        raise RuntimeError("index down")

    funcs = {
        "workspace": _stub("workspace", [("§ pfSense nøgle: flyttet til .env", 0.8)]),
        "brain": _boom,
        "session_summary": _stub("session_summary", [("[2026-09-03] Emne: pfsense nøgle i .env", 0.6)]),
    }
    with patch.dict(R.SOURCE_FUNCS, funcs, clear=True):
        out = R.recall("pfsense nøgle", sources=["workspace", "brain", "session_summary"], limit=5)
    assert out["status"] == "ok"
    assert out["count"] == 2
    assert {r["source"] for r in out["results"]} == {"workspace", "session_summary"}
    assert "brain" in out["errors"]
    assert out["text"].startswith("Hukommelse for «pfsense nøgle»")


def test_recall_empty_has_message_and_emits_event():
    calls: list[dict] = []
    funcs = {"workspace": _stub("workspace", [])}
    with patch.dict(R.SOURCE_FUNCS, funcs, clear=True), \
         patch("core.services.memory_recall_telemetry.emit_recall_empty", lambda **kw: calls.append(kw)):
        out = R.recall("noget der ikke findes", sources=["workspace"])
    assert out["count"] == 0
    assert out["text"] == R.empty_message("noget der ikke findes")
    assert calls and calls[0]["tool"] == "recall"


def test_recall_rejects_empty_query():
    assert R.recall("   ")["status"] == "error"


def test_default_sources_exclude_chat_and_unknown_sources_ignored():
    with patch.dict(R.SOURCE_FUNCS, {k: _stub(k, []) for k in R.ALL_SOURCES}, clear=True):
        out = R.recall("x y z", sources=["nope", "chat"])
        assert out["sources"] == ["chat"]
        out2 = R.recall("x y z")
        assert "chat" not in out2["sources"]


def test_context_questions_include_chat_by_default():
    with patch.dict(R.SOURCE_FUNCS, {k: _stub(k, []) for k in R.ALL_SOURCES}, clear=True):
        out = R.recall("hvad besluttede vi om Kai og jarvis-ai?")
    assert "chat" in out["sources"]


def test_fuse_promotes_exact_low_native_history_over_irrelevant_high_native():
    cands = [
        {
            "source": "brain",
            "score": 0.95,
            "text": "ChiefOne er Proxmox host med Home Assistant og pfSense",
            "ref": "brain-noise",
        },
        {
            "source": "chat",
            "score": 0.10,
            "text": "Kai var forgængeren i jarvis-ai og analysen pegede på selvstyring.",
            "ref": "chat-hit",
        },
    ]
    out = R.fuse("hvad lærte vi af forgængeren Kai jarvis-ai?", cands)
    assert out[0]["ref"] == "chat-hit"


def test_fts_sources_use_rank_scores_and_pool_is_wide():
    """2026-09-04: bm25-afledte 0,05-scorer kunne aldrig konkurrere; puljen pr. kilde var 3."""
    seen: dict = {}

    def stub(query, limit):
        seen["limit"] = limit
        return []

    with patch.dict(R.SOURCE_FUNCS, {"workspace": stub}, clear=True):
        R.recall("samfundstjeneste", sources=["workspace"], limit=3)
    assert seen["limit"] >= 10
    with patch("core.runtime.db_fts.search_session_summaries", return_value=[{"summary": "a", "created_at": "2026-09-03", "session_id": "s", "score": 0.08}, {"summary": "b", "created_at": "2026-09-03", "session_id": "s", "score": 0.07}]):
        rows = R._source_session_summary("x", 5)
    assert [r["score"] for r in rows] == [1.0, 0.9]
