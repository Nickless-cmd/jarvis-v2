from __future__ import annotations

import importlib
from core.identity.workspace_bootstrap import ensure_default_workspace


def test_end_of_run_memory_consolidation_can_auto_apply_explicit_user_preference(
    isolated_runtime,
    monkeypatch,
) -> None:
    module = importlib.import_module(
        "apps.api.jarvis_api.services.end_of_run_memory_consolidation"
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
    assert "[USER.md] Language preference: replies in Danish by default." in daily_text


def test_end_of_run_memory_consolidation_reruns_with_full_context_when_model_requests_it(
    isolated_runtime,
    monkeypatch,
) -> None:
    module = importlib.import_module(
        "apps.api.jarvis_api.services.end_of_run_memory_consolidation"
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
    assert "[MEMORY.md] Repo context: current collaboration happens in /media/projects/jarvis-v2." in daily_text
