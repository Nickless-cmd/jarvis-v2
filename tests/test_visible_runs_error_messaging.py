from __future__ import annotations


def test_friendly_message_for_connection_refused(isolated_runtime) -> None:
    from urllib.error import URLError
    from core.services.visible_runs_error_messaging import (
        friendly_provider_error_message,
    )

    exc = URLError("[Errno 111] Connection refused")
    msg = friendly_provider_error_message(exc)
    assert "Ollama" in msg or "backend" in msg.lower()
    assert "Errno" not in msg
    assert "<" not in msg  # no Python repr-text leakage


def test_friendly_message_for_urlopen_repr(isolated_runtime) -> None:
    """Exact production fingerprint from 2026-05-05 incident."""
    from urllib.error import URLError
    from core.services.visible_runs_error_messaging import (
        friendly_provider_error_message,
    )

    # str(URLError) produces "<urlopen error ...>" — verify we don't pass through
    exc = URLError("Connection refused")
    msg = friendly_provider_error_message(exc)
    assert "<urlopen" not in msg
    assert "Connection refused" not in msg


def test_friendly_message_for_timeout_error(isolated_runtime) -> None:
    from core.services.visible_runs_error_messaging import (
        friendly_provider_error_message,
    )

    msg = friendly_provider_error_message(TimeoutError("read timeout"))
    assert "tid" in msg.lower() or "hang" in msg.lower()


def test_friendly_message_for_ssl_handshake(isolated_runtime) -> None:
    from core.services.visible_runs_error_messaging import (
        friendly_provider_error_message,
    )

    exc = Exception("SSL: handshake operation timed out")
    msg = friendly_provider_error_message(exc)
    # "ssl" + "handshake" matches the SSL branch
    assert "SSL" in msg or "handshake" in msg.lower()


def test_friendly_message_for_dns_failure(isolated_runtime) -> None:
    from core.services.visible_runs_error_messaging import (
        friendly_provider_error_message,
    )

    exc = Exception("Name or service not known")
    msg = friendly_provider_error_message(exc)
    assert "DNS" in msg or "host" in msg.lower()


def test_friendly_message_falls_back_to_generic(isolated_runtime) -> None:
    from core.services.visible_runs_error_messaging import (
        friendly_provider_error_message,
    )

    msg = friendly_provider_error_message(ValueError("totally unexpected thing"))
    assert "visible-lane" in msg or "stadig her" in msg
    # Generic fallback should still be in Jarvis' voice (Danish)
    assert "ValueError" not in msg
    assert "totally unexpected" not in msg


def test_friendly_message_handles_unstringable_exception(isolated_runtime) -> None:
    from core.services.visible_runs_error_messaging import (
        friendly_provider_error_message,
    )

    class NoStr(Exception):
        def __str__(self) -> str:
            raise RuntimeError("cannot stringify")

    # Must not raise
    msg = friendly_provider_error_message(NoStr())
    assert msg  # returns the generic fallback
