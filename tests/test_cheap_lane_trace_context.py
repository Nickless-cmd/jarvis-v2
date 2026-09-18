from __future__ import annotations


def test_trace_context_normalizes_identity_and_advances_fallback():
    from core.services.cheap_lane_trace_context import CheapLaneTraceContext

    context = CheapLaneTraceContext.create(
        correlation_id=" corr-1 ", daemon=" dream ", task_kind=" Background ",
        attempt=0, retry_parent_id="retry-1",
    )
    fallback = context.next_fallback("inv-1")

    assert context.correlation_id == "corr-1"
    assert context.daemon == "dream"
    assert context.task_kind == "background"
    assert context.attempt == 1
    assert fallback.attempt == 2
    assert fallback.fallback_parent_id == "inv-1"
    assert fallback.retry_parent_id == ""


def test_candidate_slot_id_uses_profile_and_honors_explicit_id():
    from core.services.cheap_lane_trace_context import candidate_slot_id

    assert candidate_slot_id({
        "provider": "groq", "model": "llama", "auth_profile": "account2",
    }) == "groq::llama::account2"
    assert candidate_slot_id({
        "slot_id": "custom", "provider": "groq", "model": "llama",
    }) == "custom"
