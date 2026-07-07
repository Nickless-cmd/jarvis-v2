from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType


def test_deep_analyzer_builds_scoped_findings(tmp_path):
    from core.services import deep_analyzer as analyzer

    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "src"
    target.mkdir()
    (target / "mail_checker.py").write_text(
        "def mail_checker():\n    return 'mail checker bug'\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("mail_checker scope note\n", encoding="utf-8")

    result = analyzer.run_deep_analysis(
        goal="find mail_checker bug",
        scope="repo",
        paths=["src"],
        question_set=["where is mail_checker failing?"],
        repo_root=str(repo),
        max_files=4,
        max_file_bytes=10_000,
        max_total_bytes=50_000,
        max_sections=6,
    )

    assert result["findings"]
    assert result["analysis_meta"]["selected_files_count"] >= 1
    assert result["analysis_meta"]["plan_outline"][0].startswith("Mål:")
    assert analyzer.evidence_paths_exist(result, repo_root=str(repo)) is True


def test_monitor_streams_digests_file_source(tmp_path, monkeypatch):
    from core.services import monitor_streams as monitor

    state: dict[str, dict[str, object]] = {}

    def load_json(_key, default):
        return dict(state) if state else dict(default)

    def save_json(_key, monitors):
        state.clear()
        state.update(monitors)

    monkeypatch.setattr(monitor, "load_json", load_json)
    monkeypatch.setattr(monitor, "save_json", save_json)

    log_file = tmp_path / "run.log"
    log_file.write_text("boot\n", encoding="utf-8")

    created = monitor.open_monitor(
        session_id="sess-1",
        source=f"file:{log_file}",
        label="run log",
        pattern="match",
    )
    assert created["status"] == "ok"

    log_file.write_text("boot\nmatch one\nmatch two\n", encoding="utf-8")
    digest = monitor.monitor_digest_section("sess-1")

    assert digest is not None
    assert "run log" in digest
    assert "match one" in digest
    assert "match two" in digest


def test_read_before_write_guard_blocks_until_read(tmp_path):
    from core.services import read_before_write_guard as guard

    guard.clear_session("sess-2")
    path = tmp_path / "USER.md"
    path.write_text("original identity\n", encoding="utf-8")

    allowed, reason = guard.check_read_before_write(str(path), session_id="sess-2")
    assert allowed is False
    assert reason is not None
    assert "READ-BEFORE-WRITE GUARD" in reason

    guard.record_read(str(path), session_id="sess-2")
    allowed_after, reason_after = guard.check_read_before_write(str(path), session_id="sess-2")
    assert allowed_after is True
    assert reason_after is None


def test_agent_outcomes_log_roundtrips_recent_entries(tmp_path, monkeypatch):
    from core.services import agent_outcomes_log as log

    outcomes_file = tmp_path / "AGENT_OUTCOMES.md"
    monkeypatch.setattr(log, "_log_file", lambda: outcomes_file)

    log.append_agent_outcome(
        agent_id="agent-1",
        name="Jarvis",
        goal="close the loop",
        outcome="Finished the task cleanly.\nWith one short note.",
        execution_mode="solo-task",
    )

    recent = log.get_recent_agent_outcomes(limit=3)
    surface = log.build_agent_outcomes_surface(limit=3)
    lines = log.build_agent_outcomes_prompt_lines(limit=3)

    assert recent and recent[0]["name"] == "Jarvis"
    assert surface["authority"] == "agent-outcomes-log"
    assert surface["outcome_count"] == 1
    assert lines and "Jarvis" in lines[0]


def test_decision_review_prompter_reviews_due_decisions(monkeypatch):
    from core.services import decision_review_prompter as prompter

    review_calls: list[tuple[str, str | None]] = []

    behavioral = ModuleType("core.services.behavioral_decisions")

    def list_active_decisions(limit=20):
        return [
            {"decision_id": "fresh", "directive": "stay focused", "reason": "test"},
            {"decision_id": "due", "directive": "write tests", "reason": "prove contract"},
        ]

    def get_decision_with_reviews(decision_id):
        if decision_id == "fresh":
            return {
                "decision_id": "fresh",
                "directive": "stay focused",
                "reason": "test",
                "reviews": [
                    {
                        "created_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()
                    }
                ],
            }
        return {
            "decision_id": "due",
            "directive": "write tests",
            "reason": "prove contract",
            "reviews": [],
        }

    def review_decision(*, decision_id, verdict, note=None, evidence=None):
        review_calls.append((decision_id, verdict))

    behavioral.list_active_decisions = list_active_decisions
    behavioral.get_decision_with_reviews = get_decision_with_reviews
    behavioral.review_decision = review_decision

    daemon_llm = ModuleType("core.services.daemon_llm")

    def quality_daemon_llm_call(prompt, max_len=200, fallback="", daemon_name=""):
        assert "VERDICT:" in prompt
        assert "write tests" in prompt
        return "VERDICT: kept\nEVIDENCE: done via tests"

    daemon_llm.quality_daemon_llm_call = quality_daemon_llm_call

    monkeypatch.setitem(sys.modules, "core.services.behavioral_decisions", behavioral)
    monkeypatch.setitem(sys.modules, "core.services.daemon_llm", daemon_llm)

    result = prompter.review_pending_decisions()

    assert result["status"] == "ok"
    assert result["considered"] == 2
    assert result["reviewed"] == 1
    assert result["skipped_recent"] == 1
    assert review_calls == [("due", "kept")]
