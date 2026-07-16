from __future__ import annotations


def test_count_filters_by_auth_profile(isolated_runtime):
    from core.runtime.db_cheap_provider import (
        record_cheap_provider_invocation,
        count_cheap_provider_invocations,
    )

    record_cheap_provider_invocation(
        provider="groq", status="ok", auth_profile="default"
    )
    record_cheap_provider_invocation(
        provider="groq", status="ok", auth_profile="account2"
    )
    since = "1970-01-01"
    assert (
        count_cheap_provider_invocations(
            provider="groq", since=since, auth_profile="default"
        )
        == 1
    )
    assert (
        count_cheap_provider_invocations(
            provider="groq", since=since, auth_profile="account2"
        )
        == 1
    )
    # no filter => counts both (backward compat)
    assert count_cheap_provider_invocations(provider="groq", since=since) == 2
