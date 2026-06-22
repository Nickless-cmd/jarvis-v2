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
    modes=["chat", "code"],  # code kun for owner/override (§18.9), gates pr. besked
    auth_fields=["bot_token", "server_id"],
    events=["message_received"],
    actions=["send_message"],
    description="Forbind Jarvis til din egen Discord-server via en lokal gateway.",
)

_VALID_MODES = ("chat", "code", "cowork")

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


def resolve_inbound_mode(requested_mode: str = "chat", *, author_role: str = "",
                         override_active: bool = False) -> dict:
    """Afgør den effektive mode for en indkommende kanal-besked (§18.9).

    Default chat. code/cowork kræver owner-rolle ELLER aktiv TOTP-override —
    ellers nedgraderes stille til chat (beskeden blokeres ikke, den behandles
    bare i chat mode). Returnerer {mode, downgraded, reason}.
    """
    req = str(requested_mode or "chat").strip().lower()
    if req not in _VALID_MODES:
        req = "chat"
    if req == "chat":
        return {"mode": "chat", "downgraded": False, "reason": ""}
    if str(author_role or "").strip().lower() == "owner" or override_active:
        return {"mode": req, "downgraded": False, "reason": ""}
    return {"mode": "chat", "downgraded": True, "reason": "mode_requires_owner"}


def route_inbound(**kwargs) -> dict:
    """Auth-cluster GENNEM Den Intelligente Central (observe). A2+A4: plugin-hardblock +
    kvote-udfald + mode-downgrade synligt pr. plugin/kanal i Centralen — UDEN at røre
    logikken (orchestrator returnerer rigt dict → observe, ikke decide). Self-safe."""
    result = _route_inbound_impl(**kwargs)
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "auth", "nerve": "plugin_inbound",
            "plugin": str(kwargs.get("plugin_id") or ""),
            "channel": str(kwargs.get("channel") or ""),
            "allowed": bool(result.get("allowed")),
            "reason": str(result.get("reason") or ""),
            "mode_downgraded": bool(result.get("mode_downgraded")),
            "quota_blocked": result.get("reason") == "quota_exceeded",
        })
    except Exception:
        pass
    return result


def _route_inbound_impl(
    *,
    plugin_id: str,
    channel: str,
    author_role: str = "",
    author_user_id: str = "",
    text: str = "",
    hour: int = -1,
    now: float | None = None,
    mode: str = "chat",
    override_active: bool = False,
) -> dict:
    """Afgør om en indkommende kanal-besked må nå Jarvis (plugin_ruleset hardblock),
    i hvilken mode (§18.9), OG om brugeren har chat-kvote tilbage (§21.7).

    Returnerer {allowed, reason, mode, mode_downgraded, quota?}. Endpoint-laget starter
    en Jarvis-run i `mode` hvis allowed=True; ellers sendes `reason` (fx upgrade-besked).
    """
    from core.services.plugin_ruleset_store import get_ruleset
    from core.services.plugin_ruleset import is_allowed

    rs = get_ruleset(plugin_id)
    ctx = {"channel": channel, "role": author_role, "hour": hour, "now": now}
    allowed, reason = is_allowed(ctx, rs)
    resolved = resolve_inbound_mode(mode, author_role=author_role, override_active=override_active)
    result = {
        "allowed": bool(allowed),
        "reason": reason,
        "mode": resolved["mode"],
        "mode_downgraded": resolved["downgraded"],
    }
    if not allowed:
        return result

    # §21.7: chat-kvote pr. bruger (owner/betalt = ubegrænset). Fail-open ved fejl.
    try:
        from core.services.quota_store import consume_quota
        q = consume_quota(author_user_id, "chat")
        if not q.get("consumed", True):
            result["allowed"] = False
            result["reason"] = "quota_exceeded"
            result["quota"] = {
                "used": q.get("used"), "limit": q.get("limit"), "tier": q.get("tier"),
                "message": "Du har nået din daglige gratis-kvote. Opgradér for ubegrænset samtale.",
            }
        elif q.get("warn"):
            result["quota"] = {"warn": True, "used": q.get("used"), "limit": q.get("limit")}
    except Exception:
        pass  # kvote-fejl må aldrig blokere en legitim besked
    return result
