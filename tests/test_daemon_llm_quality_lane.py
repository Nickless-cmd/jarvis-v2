"""Tests for kvalitets-lanen i core/services/daemon_llm.py.

MÅLT 2026-09-01: ``inner_enrichment``-lanen har ét mål (betalt
deepseek-v4-flash) og ingen fallback i registret. Fire målinger med en
drøm-stor prompt gav 10,1 / 14,1 / 16,9 / 17,1 sekunder mod standardens 30 —
kun ~13 sekunders luft. Da drømme-gaten endelig åbnede 31-08 timede netop dette
kald ud, lanen faldt tilbage til cheap-lane, og drømmen blev tom.
"""

from __future__ import annotations

import logging

import pytest

import core.services.daemon_llm as dl


class TestQualityLaneTimeout:
    def test_timeout_is_generous_enough_for_the_measured_latency(self) -> None:
        """17,1 s var den langsomste måling; loftet skal have rigelig luft."""
        assert dl._QUALITY_LANE_TIMEOUT_SECONDS >= 60

    def test_timeout_is_larger_than_the_shared_default(self) -> None:
        from core.services.cheap_provider_runtime_adapters import (
            _DEFAULT_TIMEOUT_SECONDS,
        )
        assert dl._QUALITY_LANE_TIMEOUT_SECONDS > _DEFAULT_TIMEOUT_SECONDS

    def test_timeout_is_passed_to_the_executor(self, monkeypatch) -> None:
        """Selve fejlen: kaldet brugte den delte 30-sekunders standard."""
        seen: dict[str, object] = {}

        def fake_exec(**kwargs):
            seen.update(kwargs)
            return {"text": "svar", "input_tokens": 1, "output_tokens": 1}

        monkeypatch.setattr(
            "core.services.cheap_provider_runtime._execute_openai_compatible_chat",
            fake_exec, raising=False,
        )
        monkeypatch.setattr(
            "core.runtime.provider_router.resolve_provider_router_target",
            lambda **kw: {
                "active": True, "credentials_ready": True,
                "provider": "deepseek", "model": "deepseek-v4-flash",
                "auth_profile": "default", "base_url": "https://x/v1",
            }, raising=False,
        )
        out = dl.quality_daemon_llm_call("prompt-timeout-probe", daemon_name="test", max_len=0)
        assert out == "svar"
        assert seen.get("timeout") == dl._QUALITY_LANE_TIMEOUT_SECONDS


class TestDegradationIsVisible:
    def test_fallback_names_the_daemon(self, monkeypatch, caplog) -> None:
        """En kvalitets-daemon der stille får cheap-lane er en tavs svækkelse."""
        monkeypatch.setattr(
            "core.runtime.provider_router.resolve_provider_router_target",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("lane nede")),
            raising=False,
        )
        monkeypatch.setattr(dl, "daemon_llm_call",
                            lambda *a, **kw: "billigt svar", raising=False)
        with caplog.at_level(logging.WARNING):
            out = dl.quality_daemon_llm_call("prompt-degradering", daemon_name="dream_synthesis")
        assert out == "billigt svar"
        assert "NEDGRADERER" in caplog.text
        assert "dream_synthesis" in caplog.text

    def test_unknown_daemon_still_logs(self, monkeypatch, caplog) -> None:
        monkeypatch.setattr(
            "core.runtime.provider_router.resolve_provider_router_target",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("nede")), raising=False,
        )
        monkeypatch.setattr(dl, "daemon_llm_call", lambda *a, **kw: "x", raising=False)
        with caplog.at_level(logging.WARNING):
            dl.quality_daemon_llm_call("prompt-ukendt-daemon")
        assert "ukendt daemon" in caplog.text


class TestBreakerAdaptersStillReachable:
    """Boy Scout-udskillelsen må ikke bryde eksisterende imports."""

    @pytest.mark.parametrize("name", [
        "_ofa_circuit_open", "_ofa_circuit_record_failure",
        "_ofa_circuit_record_success", "_arko_circuit_open",
        "_arko_circuit_record_failure", "_arko_circuit_record_success",
        "_OFA_CB_THRESHOLD", "_ARKO_CB_THRESHOLD", "_ARKO_PROVIDER_ID",
    ])
    def test_symbol_is_reexported(self, name: str) -> None:
        import core.services.cheap_provider_runtime_adapters as adapters
        assert hasattr(adapters, name)

    def test_thresholds_are_unchanged(self) -> None:
        from core.services.cheap_provider_breaker_adapters import (
            _ARKO_CB_OPEN_DURATION_S, _ARKO_CB_THRESHOLD,
            _OFA_CB_OPEN_DURATION_S, _OFA_CB_THRESHOLD,
        )
        assert (_OFA_CB_THRESHOLD, _OFA_CB_OPEN_DURATION_S) == (3, 300.0)
        assert (_ARKO_CB_THRESHOLD, _ARKO_CB_OPEN_DURATION_S) == (3, 180)
