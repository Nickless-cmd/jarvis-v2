"""Config-drift-nerve (§7) — fang når DEKLARERET config og RUNTIME-virkelighed er ude af sync.

Den konkrete bug der motiverede den (Bjørn): internal_api fejlede i DAGEVIS fordi settings
sagde port 8010 men API'en kørte på 8011/8080 — ingen cluster fangede mismatchet. Det var en
blind plet. Denne nerve prober den DEKLAREREDE port (load_settings().port) + kendte alternativer;
hvis API'en svarer på en ANDEN port end den deklarerede → DRIFT → observe + incident til review.

Read-only netværks-probe (localhost, kort timeout) — kører på kadence, ALDRIG på hot path.
Self-safe. Udvides senere til flere config↔runtime-akser (model-lanes, paths, feature-flags).
"""
from __future__ import annotations

from typing import Any

# Kendte porte API'en historisk har kørt på (declared sættes forrest dynamisk).
_ALT_PORTS = (8080, 8011, 80, 8000, 8010)


def _declared_port() -> int:
    try:
        from core.runtime.settings import load_settings
        return int(load_settings().port)
    except Exception:
        return 8010


def _api_responds(port: int) -> bool:
    """True hvis NOGET svarer HTTP på 127.0.0.1:port (selv 4xx/5xx = porten lytter)."""
    import urllib.error
    import urllib.request
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/", timeout=2.0)
        return True
    except urllib.error.HTTPError:
        return True  # svarede (4xx/5xx) → porten lytter
    except Exception:
        return False


def check_port_drift() -> dict[str, Any]:
    """Probe deklareret port + alternativer. drift=True hvis API'en svarer, men IKKE på den
    deklarerede port. Self-safe."""
    declared = _declared_port()
    candidates: list[int] = []
    for p in (declared, *_ALT_PORTS):
        if p not in candidates:
            candidates.append(p)
    reachable = [p for p in candidates if _api_responds(p)]
    drift = bool(reachable) and declared not in reachable
    return {
        "declared_port": declared,
        "reachable_ports": reachable,
        "actual_port": reachable[0] if reachable else None,
        "drift": drift,
    }


def observe_config_drift() -> dict[str, Any]:
    """Kør drift-check → observe til Centralen + flag incident hvis drift. Kadence-kaldt.
    ALDRIG destruktiv (retter ikke config selv — det er menneskets beslutning)."""
    rep = check_port_drift()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "config_drift",
            "declared_port": rep["declared_port"], "actual_port": rep["actual_port"],
            "reachable_ports": rep["reachable_ports"], "drift": rep["drift"],
        })
    except Exception:
        pass
    if rep["drift"]:
        msg = (f"config-drift: settings.port={rep['declared_port']} men API svarer på "
               f"{rep['actual_port']} (nåbare: {rep['reachable_ports']}) — internal_api "
               f"o.l. der bruger settings.port vil fejle")
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(cluster="system", nerve="config_drift", kind="drift",
                                    severity="severe", message=msg)
        except Exception:
            pass
        try:
            from core.services.ntfy_gateway import send_notification
            send_notification("⚠ " + msg, title="Config-drift", priority="high")
        except Exception:
            pass
    return rep


def build_config_drift_surface() -> dict[str, object]:
    """MC-surface — read-only config-drift-projektion."""
    rep = check_port_drift()
    return {
        "active": True, "mode": "config_drift",
        "declared_port": rep["declared_port"], "actual_port": rep["actual_port"],
        "reachable_ports": rep["reachable_ports"], "drift": rep["drift"],
        "authority": "derived-read-only — flagger, retter ALDRIG selv",
    }
