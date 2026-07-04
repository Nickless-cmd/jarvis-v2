"""Tests for canonical error-taxonomi (Fase 0 — Canonical Error System).

Håndhæver: taxonomi-komplethed, envelope_from_kind-udfyldning + ukendt→ui.unknown,
nerve→kind-mapping af dagens LIVE nerver, og at eksisterende ErrorEnvelope-konstruktion
+ legacy build_envelope STADIG virker (back-compat er ufravigeligt).
"""
from __future__ import annotations

import pytest

from core.services import central_error_envelope as cee


# ── (1) Taxonomi-komplethed ─────────────────────────────────────────────────

def test_taxonomy_has_expected_total():
    # spec §3.1 (28) + audit-extras (server.error, protocol.malformed,
    # infra.git_unavailable = 3) + self.hollow_promise (1) = 32.
    assert len(cee.ERROR_KINDS) == 32
    assert cee.ERROR_KINDS == frozenset(cee.KIND_MAP)


def test_every_kind_has_valid_kind_map_entry():
    for kind in cee.ERROR_KINDS:
        spec = cee.KIND_MAP[kind]
        assert spec["severity"] in cee.SEVERITIES, kind
        assert spec["recoverable"] in cee.RECOVERABILITIES, kind
        assert isinstance(spec["user_message_da"], str) and spec["user_message_da"], kind


def test_pfsense_dropped_in_favor_of_infra():
    assert "infra.syslogd_dead" in cee.ERROR_KINDS
    assert "pfsense.syslogd_dead" not in cee.ERROR_KINDS


def test_new_and_audit_kinds_present():
    for k in ("self.hollow_promise", "server.error", "protocol.malformed",
              "infra.git_unavailable"):
        assert k in cee.ERROR_KINDS


# ── (2) envelope_from_kind ──────────────────────────────────────────────────

def test_envelope_from_kind_fills_from_map():
    env = cee.envelope_from_kind("network.timeout", origin_cluster="stream",
                                 run_id="run-1", scope="run")
    assert env.kind == "network.timeout"
    assert env.code == "network.timeout"
    assert env.severity == "warning"
    assert env.recoverable == "retry"
    assert env.retryable is True
    assert env.scope == "run"
    assert env.correlation_id == "run-1"
    assert env.origin_cluster == "stream"
    assert env.user_message


def test_envelope_from_kind_degraded_is_not_retryable_bool():
    env = cee.envelope_from_kind("model.context_exceeded")
    assert env.recoverable == "degraded"
    assert env.retryable is False


def test_envelope_from_kind_auto_is_retryable_bool():
    env = cee.envelope_from_kind("central.daemon_dead")
    assert env.recoverable == "auto" and env.retryable is True


def test_unknown_kind_falls_back_to_ui_unknown():
    env = cee.envelope_from_kind("totally.made_up", run_id="r")
    assert env.kind == "ui.unknown"
    assert env.code == "ui.unknown"
    assert env.severity == cee.KIND_MAP["ui.unknown"]["severity"]


def test_envelope_from_kind_client_event_carries_canonical_fields():
    env = cee.envelope_from_kind("provider.unavailable", scope="run")
    ev = env.to_client_event()
    assert ev["kind"] == "provider.unavailable"
    assert ev["recoverable"] == "degraded"
    assert ev["scope"] == "run"
    assert ev["type"] == "error"


# ── (3) kind_for_nerve — dagens LIVE nerver ─────────────────────────────────

@pytest.mark.parametrize("cluster,nerve,expected", [
    ("stream", "cutoff_at_loop_lag", "self.cutoff"),
    ("runtime", "loop_lag_spike", "self.loop_lag"),
    ("loop", "no_progress_finalize", "self.loop_lag"),
    ("stream", "dsml_tail_dropped", "self.cutoff"),
    ("stream", "provider_length_truncation", "model.context_exceeded"),
    ("security", "membrane_watch", "trust.workspace_untrusted"),
    ("stream", "provider_fallback", "provider.unavailable"),
    ("stream", "hollow_promise", "self.hollow_promise"),
])
def test_kind_for_nerve_maps_live_nerves(cluster, nerve, expected):
    assert cee.kind_for_nerve(cluster, nerve) == expected


def test_kind_for_nerve_hollow_promise_cluster_tolerant():
    assert cee.kind_for_nerve("whatever", "hollow_promise") == "self.hollow_promise"


def test_kind_for_nerve_unknown_returns_none():
    assert cee.kind_for_nerve("stream", "some_healthy_nerve") is None


def test_every_mapped_kind_exists_in_taxonomy():
    for kind in cee.NERVE_TO_KIND.values():
        assert kind in cee.ERROR_KINDS


# ── (4) Back-compat — eksisterende konstruktion / API uændret ───────────────

def test_legacy_envelope_construction_positional_still_works():
    env = cee.ErrorEnvelope(
        "provider_error", "error", "besked", True, "hint", "run-x", "stream")
    assert env.code == "provider_error"
    assert env.detail == ""
    assert env.kind == "" and env.recoverable == "" and env.scope == ""


def test_legacy_build_envelope_unaffected():
    env = cee.build_envelope(code="provider_rate_limited", origin_cluster="stream",
                             run_id="v1")
    assert env.severity == "warning" and env.retryable is True
    assert env.kind == "" and env.recoverable == ""


def test_legacy_client_event_shape_unchanged():
    env = cee.build_envelope(code="agent_error", run_id="r2")
    ev = env.to_client_event()
    assert set(ev) == {"type", "code", "severity", "message", "retryable",
                       "fix_hint", "correlation_id"}
