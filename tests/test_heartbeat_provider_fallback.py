"""Tests for heartbeat provider fallback load-spreading (2026-06-22)."""
from unittest.mock import patch

import core.services.cheap_provider_runtime as cpr
from core.services import heartbeat_provider_fallback as hpf


def _cand(provider, model="m"):
    return {
        "provider": provider,
        "model": model,
        "credentials_ready": True,
        "auth_profile": "",
        "base_url": "http://x/v1",
    }


def test_skips_blocked_and_rotates_among_usable():
    cands = [_cand("deepseek"), _cand("mistral"), _cand("opencode")]
    used: list[str] = []

    def _quota(c):
        return {"blocked": c["provider"] == "deepseek"}

    def _exec(*, prompt, target):
        used.append(target["provider"])
        return {"text": "ok"}

    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", side_effect=_quota), \
         patch.object(hpf, "execute_openai_compat_heartbeat_prompt", side_effect=_exec):
        for _ in range(4):
            hpf.try_heartbeat_cheap_fallback("hi")

    # blocked (dry) provider never used; load spread across both usable lanes
    assert "deepseek" not in used
    assert set(used) == {"mistral", "opencode"}


def test_returns_none_when_no_usable():
    cands = [_cand("deepseek")]
    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", return_value={"blocked": True}):
        assert hpf.try_heartbeat_cheap_fallback("hi") is None


def test_falls_through_on_provider_error():
    cands = [_cand("mistral"), _cand("opencode")]

    def _exec(*, prompt, target):
        if target["provider"] == "mistral":
            raise RuntimeError("mistral down")
        return {"text": "ok"}

    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", return_value={"blocked": False}), \
         patch.object(hpf, "execute_openai_compat_heartbeat_prompt", side_effect=_exec):
        # may start on mistral (fails) but must fall through to opencode
        results = [hpf.try_heartbeat_cheap_fallback("hi") for _ in range(2)]
    assert any(r == {"text": "ok"} for r in results)
