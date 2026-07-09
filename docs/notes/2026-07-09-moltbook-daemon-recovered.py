"""RECOVERED skeleton — genskabt fra moltbook_daemon.cpython-311.pyc (kilden var tabt).

Rekonstrueret 2026-07-09 fra fuld bytecode-disassembly (dis + co_consts/co_names). Dette er
IKKE den nye nerve — det er arkæologi: den gamle daemons FAKTISKE adfærd, så designet af
central_moltbook-nerven kan bygge på verificeret grund (ikke gættede endpoints).

VERIFICERET fra bytecoden:
  - Base:  https://www.moltbook.com/api/v1/
  - Auth:  Authorization: Bearer <api_key> (fra ~/.config/moltbook/credentials.json, nøgle "api_key")
  - Headers: Accept: application/json · User-Agent: Jarvis-Moltbook-Daemon/1.0
  - READ-ONLY endpoints der faktisk blev kaldt:  home · activity_on_your_posts · notifications
  - Status-håndtering: 429 rate-limit · 401 → auto-disable daemon · 200 parse
  - Emitterede: event_bus.publish("moltbook.new_activity", ...) (priority high/normal)
               + core.services.outbound_nudges.push_nudge(...)
  - Dedup: _seen_ids (cap 500) · State: _last_check_at / _last_new_activity_count / _last_activity_summary
  - INGEN skrive-endpoints, INGEN webhooks (bekræfter: post/reply/reactions/webhooks var GÆTTET).
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_CREDS_PATH = Path.home() / ".config" / "moltbook" / "credentials.json"
_MAX_SEEN_IDS = 500
_API_BASE = "https://www.moltbook.com/api/v1/"

# Modul-state (den gamle daemons hukommelse mellem tick)
_last_check_at: datetime | None = None
_last_new_activity_count: int = 0
_last_activity_summary: list[dict] = []
_seen_ids: set[str] = set()


def _load_api_key() -> str | None:
    """Load Moltbook API key from credentials file."""
    try:
        return json.loads(_CREDS_PATH.read_text(encoding="utf-8"))["api_key"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("moltbook: cannot load credentials: %s", exc)
        return None


def _call_moltbook_api(endpoint: str, api_key: str, timeout: int = 15) -> dict | None:
    """Call Moltbook API with auth header. Returns parsed JSON or None on error.
    Returnerer strengen 'unauthorized' ved 401 (så tick kan auto-disable)."""
    req = urllib_request.Request(_API_BASE + endpoint)
    req.add_header("Authorization", "Bearer " + api_key)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Jarvis-Moltbook-Daemon/1.0")
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 429:
                logger.warning("moltbook: rate limited (429) on %s", endpoint)
                return None
            if resp.status != 200:
                logger.warning("moltbook: unexpected status %s on %s", resp.status, endpoint)
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        if exc.code == 401:
            logger.warning("moltbook: unauthorized (401) — API key expired/revoked")
            return "unauthorized"          # noqa: type — sentinel (gammel adfærd)
        logger.warning("moltbook: HTTP %s on %s", exc.code, endpoint)
        return None
    except urllib_error.URLError as exc:
        logger.warning("moltbook: network error on %s: %s", endpoint, exc)
        return None
    except json.JSONDecodeError:
        logger.warning("moltbook: invalid JSON from %s", endpoint)
        return None
    except Exception as exc:  # noqa: BLE001 — daemon må aldrig dø
        logger.warning("moltbook: unexpected error on %s: %s", endpoint, exc)
        return None


def tick_moltbook_daemon() -> str:
    """Observe-tick (den gamle heartbeat-model, 15-min polling). Rekonstruktion af flowet:
      1. _load_api_key() → 'no_api_key' hvis mangler
      2. GET home → hvis 'unauthorized' → daemon_manager.set_daemon_enabled('moltbook', False)
         (auto-disable ved 401), returnér 'home_endpoint_failed'
      3. GET activity_on_your_posts → items: id/post_id/activity/title/content/author(_name)/karma/created_at
      4. GET notifications → notification_id/notification/message
      5. dedup mod _seen_ids (cap 500); ny aktivitet → event_bus.publish('moltbook.new_activity',
         {..., priority: 'high'|'normal'}) + outbound_nudges.push_nudge(...)
      6. opdater _last_check_at / _last_new_activity_count / _last_activity_summary
    (Fuld payload-parsing udeladt her — se dis; den nye nerve genimplementerer dette rent.)"""
    raise NotImplementedError("skeleton — se docstring for det rekonstruerede flow")


def build_moltbook_surface() -> dict:
    """Mission Control surface — read-only status for the cartographer.
    Returnerede: last_check_at.isoformat(), _last_new_activity_count, _last_activity_summary[:5],
    + om api_key kunne loades."""
    return {
        "last_check_at": _last_check_at.isoformat() if _last_check_at else None,
        "new_activity_count": _last_new_activity_count,
        "recent": _last_activity_summary[:5],
        "has_credentials": _load_api_key() is not None,
    }
