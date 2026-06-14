"""Kanal-plugin inbound-routing (spec §5.2/§5.3, Fase 5 Lag 1).

Når en lokal gateway (fx Discord på brugerens maskine) modtager en besked, ruter
den den hertil. route_inbound HÅNDHÆVER plugin_ruleset (hardblock for ALLE inkl.
owner, §5.3) FØR Jarvis overhovedet kaldes — så en kompromitteret/tweaked klient
ikke kan omgå brugerens egne regler (klienten pre-filtrerer også, men serveren er
sandheden).

Den ren gate (route_inbound) afgør allow/block. Selve run-startet sker i endpoint-
laget (best-effort), så gaten er testbar uden runtime.
"""
from __future__ import annotations

from core.plugins.base_plugin import PluginManifest, register_plugin

# Indbygget Discord-kanal-plugin (lokal gateway). Token bor KLIENT-side.
DISCORD_CHANNEL_MANIFEST = PluginManifest(
    plugin_id="discord-local",
    name="Discord (lokal server)",
    kind="channel",
    modes=["chat"],
    auth_fields=["bot_token", "server_id"],
    events=["message_received"],
    actions=["send_message"],
    description="Forbind Jarvis til din egen Discord-server via en lokal gateway.",
)

_BUILTINS_REGISTERED = False


def register_builtin_channel_plugins() -> None:
    """Idempotent registrering af indbyggede kanal-plugins (kaldes fra plugins-route)."""
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return
    try:
        register_plugin(DISCORD_CHANNEL_MANIFEST)
    except Exception:
        pass
    _BUILTINS_REGISTERED = True


def route_inbound(
    *,
    plugin_id: str,
    channel: str,
    author_role: str = "",
    text: str = "",
    hour: int = -1,
    now: float | None = None,
) -> dict:
    """Afgør om en indkommende kanal-besked må nå Jarvis (plugin_ruleset hardblock).

    Returnerer {allowed: bool, reason: str}. Endpoint-laget starter en Jarvis-run
    hvis allowed=True.
    """
    from core.services.plugin_ruleset_store import get_ruleset
    from core.services.plugin_ruleset import is_allowed

    rs = get_ruleset(plugin_id)
    ctx = {"channel": channel, "role": author_role, "hour": hour, "now": now}
    allowed, reason = is_allowed(ctx, rs)
    return {"allowed": bool(allowed), "reason": reason}
