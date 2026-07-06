from __future__ import annotations

import importlib
from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace


def test_end_of_run_memory_consolidation_can_auto_apply_explicit_user_preference(
    isolated_runtime,
    monkeypatch,
) -> None:
    module = importlib.import_module(
        "core.services.end_of_run_memory_consolidation"
    )
    module = importlib.reload(module)

    monkeypatch.setattr(
        module,
        "_run_local_consolidation_model",
        lambda prompt: """
        {
          "needs_full_context": false,
          "items": [
            {
              "target": "USER.md",
              "kind": "preference",
              "confidence": "high",
              "source": "explicit-user-statement",
              "summary": "User prefers replies in Danish.",
              "reason": "Explicit durable preference.",
              "line": "- Language preference: replies in Danish by default."
            }
          ]
        }
        """,
    )

    result = module.consolidate_run_memory(
        session_id="test-session",
        run_id="test-run",
        user_message="Husk det her fremover: svar på dansk.",
        assistant_response="Jeg svarer på dansk fremover.",
    )

    workspace = ensure_default_workspace()
    user_md = (workspace / "USER.md").read_text(encoding="utf-8")
    daily_memory = next((workspace / "memory" / "daily").glob("*.md"))
    daily_text = daily_memory.read_text(encoding="utf-8")

    assert result["consolidated"] is True
    assert result["candidate_count"] == 1
    assert result["user_updated"] is True
    assert result["daily_memory_logged"] is True
    assert "- Language preference: replies in Danish by default." in user_md
    # 2026-05-22 provenance fix: carried lines are prefixed [CANDIDATE→<target>]
    # (a proposal), never [<target>] (a fabricated citation).
    assert "[CANDIDATE→USER.md] Language preference: replies in Danish by default." in daily_text


def test_end_of_run_memory_consolidation_reruns_with_full_context_when_model_requests_it(
    isolated_runtime,
    monkeypatch,
) -> None:
    module = importlib.import_module(
        "core.services.end_of_run_memory_consolidation"
    )
    module = importlib.reload(module)

    prompts: list[str] = []
    responses = iter(
        [
            '{"needs_full_context": true, "items": []}',
            """
            {
              "needs_full_context": false,
              "items": [
                {
                  "target": "MEMORY.md",
                  "kind": "context",
                  "confidence": "high",
                  "source": "explicit-user-statement",
                  "summary": "Current collaboration is anchored in the repo path.",
                  "reason": "Stable working context the user explicitly asked to carry forward.",
                  "line": "- Repo context: current collaboration happens in /media/projects/jarvis-v2."
                }
              ]
            }
            """,
        ]
    )

    def _fake_run(prompt: str) -> str:
        prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr(module, "_run_local_consolidation_model", _fake_run)

    result = module.consolidate_run_memory(
        session_id="test-session",
        run_id="test-run",
        user_message="Husk at vi arbejder i /media/projects/jarvis-v2.",
        assistant_response="Jeg vil bære repo-konteksten videre.",
    )

    workspace = ensure_default_workspace()
    memory_md = (workspace / "MEMORY.md").read_text(encoding="utf-8")
    daily_memory = next((workspace / "memory" / "daily").glob("*.md"))
    daily_text = daily_memory.read_text(encoding="utf-8")

    assert result["consolidated"] is True
    assert result["used_full_context"] is True
    assert result["memory_updated"] is True
    assert result["daily_memory_logged"] is True
    assert len(prompts) == 2
    assert "FULL FILE CONTEXT" in prompts[1]
    assert "- Repo context: current collaboration happens in /media/projects/jarvis-v2." in memory_md
    # 2026-05-22 provenance fix: carried lines are prefixed [CANDIDATE→<target>].
    assert "[CANDIDATE→MEMORY.md] Repo context: current collaboration happens in /media/projects/jarvis-v2." in daily_text


def test_end_of_run_memory_consolidation_audits_skipped_runs(
    isolated_runtime,
    monkeypatch,
) -> None:
    module = importlib.import_module(
        "core.services.end_of_run_memory_consolidation"
    )
    module = importlib.reload(module)

    monkeypatch.setattr(module, "_run_local_consolidation_model", lambda prompt: "")

    result = module.consolidate_run_memory(
        session_id="audit-session",
        run_id="audit-run",
        user_message="Husk at dette er en længere besked.",
        assistant_response="Dette er et længere svar som udløser consolidation.",
    )

    # publish() is async — flush so the audit event is committed before we read.
    event_bus.flush()
    latest = event_bus.recent(limit=4)[0]
    assert result["skipped_reason"] == "model-unavailable"
    assert latest["kind"] == "memory.end_of_run_consolidation"
    assert latest["payload"]["run_id"] == "audit-run"
    assert latest["payload"]["skipped_reason"] == "model-unavailable"


def test_end_of_run_memory_consolidation_prompt_includes_internal_context(
    isolated_runtime,
    monkeypatch,
) -> None:
    module = importlib.import_module(
        "core.services.end_of_run_memory_consolidation"
    )
    module = importlib.reload(module)

    prompts: list[str] = []

    def _fake_run(prompt: str) -> str:
        prompts.append(prompt)
        return '{"needs_full_context": false, "items": []}'

    monkeypatch.setattr(module, "_run_local_consolidation_model", _fake_run)

    module.consolidate_run_memory(
        session_id="tool-session",
        run_id="tool-run",
        user_message="Undersøg runtime events og husk resultatet.",
        assistant_response="Jeg har undersøgt runtime events.",
        internal_context="[bash]: found one failed runtime event",
    )

    assert "INTERNAL JARVIS-ONLY TOOL/RUNTIME CONTEXT" in prompts[0]
    assert "[bash]: found one failed runtime event" in prompts[0]


# ─── 2026-05-22: fabricated provenance fix ───

class TestDailyMemoryProvenance:
    """Daily-memory writer must mark carried items as CANDIDATES,
    not as MEMORY.md citations."""

    def test_carried_items_use_candidate_prefix(self, tmp_path):
        from core.services.end_of_run_memory_consolidation import _append_daily_memory_log
        daily = tmp_path / "2026-05-22.md"
        items = [
            {
                "target": "MEMORY.md",
                "line": "- Subdomains: foo.bar.dk",
                "kind": "fact",
                "confidence": "medium",
                "source": "runtime-inference",
                "summary": "",
                "reason": "",
            }
        ]
        ok = _append_daily_memory_log(
            daily_memory_path=daily,
            session_id="s",
            run_id="r",
            user_message="u",
            assistant_response="a",
            items=items,
        )
        assert ok
        content = daily.read_text(encoding="utf-8")
        # Old (bad) prefix must NOT appear
        assert "  - [MEMORY.md] Subdomains" not in content
        # New (correct) candidate prefix must be present
        assert "[CANDIDATE→MEMORY.md] Subdomains: foo.bar.dk" in content

    def test_user_md_target_also_prefixed(self, tmp_path):
        from core.services.end_of_run_memory_consolidation import _append_daily_memory_log
        daily = tmp_path / "test.md"
        items = [
            {
                "target": "USER.md",
                "line": "- prefers concise answers",
                "kind": "preference",
                "confidence": "high",
                "source": "explicit-user-statement",
                "summary": "",
                "reason": "",
            }
        ]
        _append_daily_memory_log(
            daily_memory_path=daily,
            session_id="s",
            run_id="r",
            user_message="u",
            assistant_response="a",
            items=items,
        )
        content = daily.read_text(encoding="utf-8")
        assert "[CANDIDATE→USER.md] prefers concise answers" in content
        assert "[USER.md] prefers" not in content
