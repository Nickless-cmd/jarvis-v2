"""Shadow-wiring af de to DØDE policies (0 call-sites) ind i Centralen.

HÅRDT INVARIANT: SHADOW = observe verdict, ALDRIG ændre adfærd.
  - delete_policy      → cluster="mutation", SECURITY-shadow (account-erase-stien)
  - memory_write_policy → cluster="memory", COGNITIVE-shadow (auto-remember-stien)

Disse tests beviser at:
  1. decide KALDES med det rette cluster på begge stier.
  2. erase_user / memory-store SKER STADIG uanset verdict (inkl. deny/blocked).
  3. Hvis decide KASTER, er erase/store upåvirket (self-safe try/except).
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


# ── POLICY 1 — delete_policy → mutation (account-erase-sti) ──────────────
def _run_erase(payload: dict):
    from apps.api.jarvis_api.routes import account
    return asyncio.get_event_loop().run_until_complete(account.account_erase(payload))


@pytest.fixture
def _erase_env():
    """Patch context/user-db/erase_user så account_erase kører uden HTTP/DB."""
    from apps.api.jarvis_api.routes import account

    erase_mock = MagicMock(return_value={"status": "ok"})
    with patch.object(account, "current_context_snapshot",
                      return_value={"user_id": "u-1"}), \
         patch.object(account.user_db, "get_user",
                      return_value={"email": "me@example.com", "role": "member"}), \
         patch("core.services.data_erasure.erase_user", erase_mock):
        yield account, erase_mock


def test_delete_shadow_calls_decide_with_mutation_cluster(_erase_env):
    account, erase_mock = _erase_env
    decide_mock = MagicMock()
    with patch("core.services.central_core.central") as central_mock:
        central_mock.return_value.decide = decide_mock
        _run_erase({"confirm": "me@example.com", "mode": "soft"})
    assert decide_mock.called, "decide skal kaldes på erase-stien"
    _, kwargs = decide_mock.call_args
    assert kwargs.get("cluster") == "mutation"
    # nerve = første positional arg
    assert decide_mock.call_args[0][0] == "delete_policy"
    # erase kørte STADIG
    assert erase_mock.called


@pytest.mark.parametrize("mode", ["soft", "hard"])
def test_delete_erase_runs_regardless_of_verdict(_erase_env, mode):
    account, erase_mock = _erase_env
    # decide returnerer et RED/deny-agtigt verdict → skal IKKE påvirke erase
    with patch("core.services.central_core.central") as central_mock:
        central_mock.return_value.decide = MagicMock(return_value="RED-block-verdict")
        _run_erase({"confirm": "me@example.com", "mode": mode})
    assert erase_mock.called, "erase_user skal køre uanset verdict"
    assert erase_mock.call_args.kwargs.get("mode") == mode


def test_delete_shadow_self_safe_when_decide_raises(_erase_env):
    account, erase_mock = _erase_env
    with patch("core.services.central_core.central") as central_mock:
        central_mock.return_value.decide = MagicMock(side_effect=RuntimeError("boom"))
        # må ikke kaste op igennem erase-stien
        _run_erase({"confirm": "me@example.com", "mode": "hard"})
    assert erase_mock.called, "decide-crash må ikke forhindre erase"


# ── POLICY 2 — memory_write_policy → memory (auto-remember-sti) ──────────
@pytest.fixture
def _remember_env():
    from core.services import auto_remember_subscriber as ars

    remember_mock = MagicMock(return_value={"status": "ok", "id": 1})
    result = {
        "kind": "fakta", "title": "Titel", "content": "Noget indhold her.",
        "visibility": "private", "domain": "code", "importance": 80,
    }
    with patch.object(ars, "_find_preceding_user_text",
                      return_value="a user question long enough to pass gate " * 2), \
         patch.object(ars, "evaluate_turn_for_memory", return_value=result), \
         patch("core.tools.jarvis_brain_tools.remember_this", remember_mock):
        yield ars, remember_mock


def _payload():
    return {"session_id": "s1", "message": {"id": "m1", "content": "x" * 400}}


def test_memory_shadow_calls_decide_with_memory_cluster(_remember_env):
    ars, remember_mock = _remember_env
    decide_mock = MagicMock()
    # 6. jul: the memory_write_policy shadow is skipped when there is NO user
    # context (evaluate_write reads a per-user workspace_dir → NoUserContextError
    # noise). So we must run inside a user context for the shadow decide to fire.
    from core.identity import workspace_context as _wc
    token = _wc.set_context(workspace_name="bjorn", user_id="test-owner")
    try:
        with patch("core.services.central_core.central") as central_mock:
            central_mock.return_value.decide = decide_mock
            ars._process_visible_assistant_turn(_payload())
    finally:
        _wc.reset_context(token)
    assert decide_mock.called, "decide skal kaldes på store-stien"
    _, kwargs = decide_mock.call_args
    assert kwargs.get("cluster") == "memory"
    assert decide_mock.call_args[0][0] == "memory_write_policy"
    assert remember_mock.called


def test_memory_store_runs_regardless_of_verdict(_remember_env):
    ars, remember_mock = _remember_env
    with patch("core.services.central_core.central") as central_mock:
        central_mock.return_value.decide = MagicMock(return_value="blocked-verdict")
        ars._process_visible_assistant_turn(_payload())
    assert remember_mock.called, "remember_this skal køre uanset verdict"


def test_memory_shadow_self_safe_when_decide_raises(_remember_env):
    ars, remember_mock = _remember_env
    with patch("core.services.central_core.central") as central_mock:
        central_mock.return_value.decide = MagicMock(side_effect=RuntimeError("boom"))
        ars._process_visible_assistant_turn(_payload())
    assert remember_mock.called, "decide-crash må ikke forhindre store"
