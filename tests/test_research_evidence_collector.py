from core.services import research_evidence_collector as collector


def test_observer_is_noop_outside_research():
    assert collector.observe_web_result("web_search", {"status": "ok", "results": []}) == 0


def test_structured_results_are_captured_and_deduplicated(monkeypatch):
    saved = []
    monkeypatch.setattr(
        "core.services.research_store.add_source",
        lambda run_id, source, task_id="": saved.append((run_id, source, task_id)) or {"id": str(len(saved))},
    )
    result = {
        "status": "ok",
        "results": [
            {"url": "https://example.com/a", "title": "A", "content": "one"},
            {"url": "https://example.com/a#fragment", "title": "A duplicate"},
            {"url": "https://example.org/b", "title": "B"},
        ],
    }
    with collector.collecting_for("r1", task_id="t1"):
        assert collector.observe_web_result("web_search", result) == 2
    assert [entry[1].canonical_url for entry in saved] == [
        "https://example.com/a", "https://example.org/b",
    ]


def test_fetch_captures_explicit_url_without_parsing_prose(monkeypatch):
    saved = []
    monkeypatch.setattr("core.services.research_store.add_source", lambda *args, **kwargs: saved.append(args) or {"id": "s"})
    with collector.collecting_for("r1"):
        count = collector.observe_web_result(
            "web_fetch", {"status": "ok", "url": "https://docs.example/x", "text": "body"},
        )
    assert count == 1
    assert saved[0][1].canonical_url == "https://docs.example/x"
