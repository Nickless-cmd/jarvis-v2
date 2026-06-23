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
    """Læs den DEKLAREREDE port DIREKTE fra runtime.json på disk — IKKE in-memory settings.

    Bug'en (Bjørn): den kørende proces har stadig den GAMLE port i hukommelsen (load_settings()
    er læst ved opstart). Når runtime.json rettes på disk, ser in-memory den ikke → nerven
    ville flagge drift for evigt. Ved at læse filen pr. check ser nerven rettelsen med det samme
    og kan auto-resolve. Én disk-læsning pr. check — ingen watcher, ingen tråde. Self-safe.
    """
    try:
        import json

        from core.runtime.config import SETTINGS_FILE
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return int(data.get("port", 8010))
    except Exception:
        # Fald tilbage til in-memory hvis filen ikke kan læses (hellere det end at fejle).
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
        # Rate-limit (Bjørn): opret KUN hvis samme besked ikke allerede findes uløst inden
        # for sidste time — ellers akkumulerer hver kadence-tik en dublet (vi så 11 stk).
        try:
            from core.runtime.db_central_incidents import (
                has_unresolved_message,
                record_central_incident,
            )
            if not has_unresolved_message(cluster="system", nerve="config_drift",
                                          message=msg, within_seconds=3600):
                record_central_incident(cluster="system", nerve="config_drift", kind="drift",
                                        severity="severe", message=msg)
                try:
                    from core.services.ntfy_gateway import send_notification
                    send_notification("⚠ " + msg, title="Config-drift", priority="high")
                except Exception:
                    pass
        except Exception:
            pass
    else:
        # Ingen drift → filen er korrekt: auto-resolve alle hængende config_drift-flag.
        # (Disk-læsningen i _declared_port ser rettelsen uden proces-genstart.)
        try:
            from core.runtime.db_central_incidents import resolve_central_incidents
            resolve_central_incidents(cluster="system", nerve="config_drift")
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
