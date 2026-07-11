from __future__ import annotations

import asyncio

from central_cli.client import CentralClient, CentralError
from central_cli.engine.state import HudState

# Surface-navn → (path, params). Kun Fase 1-surfaces her; udvides pr. fase.
SURFACE_PATHS: dict[str, tuple[str, dict | None]] = {
    "realtime": ("/central/realtime", None),
    "costs_daily": ("/central/costs-daily", None),
    "diagnostics": ("/central/diagnostics", None),
    "timeseries": ("/central/timeseries", None),
}

# Surface-navn → kadence i sekunder (hvor ofte worker gen-henter).
SURFACE_CADENCE: dict[str, float] = {
    "realtime": 2.0,
    "costs_daily": 30.0,
    "diagnostics": 5.0,
    "timeseries": 4.0,
}


async def fetch_surface(client: CentralClient, state: HudState, surface: str) -> None:
    """Hent én surface og skriv til state. Blokerende httpx-kald køres i en tråd
    så UI-loopet aldrig blokeres. Fejl bevarer sidste gode data."""
    path, params = SURFACE_PATHS[surface]
    state.set_loading(surface, True)
    try:
        data = await asyncio.to_thread(client.get_json, path, params)
        state.set_ok(surface, data)
    except CentralError as exc:
        state.set_error(surface, f"{exc.category}: {exc}")
    except Exception as exc:  # defensiv — en worker må aldrig vælte appen
        state.set_error(surface, str(exc))


async def fetch_detail(
    client: CentralClient, state: HudState, surface_key: str, path: str
) -> None:
    """On-demand detalje-fetch (fx 'nerve_detail:<navn>')."""
    state.set_loading(surface_key, True)
    try:
        data = await asyncio.to_thread(client.get_json, path, None)
        state.set_ok(surface_key, data)
    except CentralError as exc:
        state.set_error(surface_key, f"{exc.category}: {exc}")
    except Exception as exc:
        state.set_error(surface_key, str(exc))
