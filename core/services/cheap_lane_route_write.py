"""Best-effort persistence for cheap-lane route traces."""


def _spor_uden_at_vaelte(skriv, **felter) -> str:
    """Write a route trace without letting telemetry interrupt the call."""
    try:
        return str(skriv(**felter) or "")
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "cheap-lane: rute-sporet kunne ikke skrives", exc_info=True,
        )
        return ""
