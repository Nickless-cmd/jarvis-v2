"""central_moltbook — Jarvis' Moltbook-tilstedeværelse som en governed Central-nerve (observe-only).

Modernisering af den tabte ``moltbook_daemon`` (rekonstrueret fra bytecode:
``docs/notes/2026-07-09-moltbook-daemon-recovered.py``) til Central-mønstret: rene detektorer +
self-safe I/O → assess → record → producer → surface → route.

VERIFICERET flade (fra recovered daemon): base ``https://www.moltbook.com/api/v1/``, Bearer-auth fra
``~/.config/moltbook/credentials.json``, READ-ONLY endpoints ``home`` · ``activity_on_your_posts`` ·
``notifications``. 429=skip · 401=auto-disable · 200=parse.

Governance: INDGÅENDE retning (Jarvis læser Moltbook) — intet privat forlader maskinen. Til Centralen
kun metadata (tællere + korte titler/forfatter-navne fra en OFFENTLIG platform). Kill-switch
``central_switches("autonomy","moltbook")`` (default ON), fail-safe. Direkte mentions → Proaktivitets-
broen (SP1). Skrive/post/webhooks er UDSKUDT til en live-probe (var gættet i den oprindelige analyse).
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

_CREDS_PATH = Path.home() / ".config" / "moltbook" / "credentials.json"
_API_BASE = "https://www.moltbook.com/api/v1/"
_MAX_SEEN_IDS = 500
_STATE_KEY = "moltbook_state"
_SWITCH = ("autonomy", "moltbook")


# ── Rene detektorer (egress-fri, testbare uden I/O) ────────────────────────────────

def _snippet(text: Any, limit: int = 200) -> str:
    return str(text or "").strip().replace("\n", " ")[:limit]


def classify_activity(home: Any, activity: Any, notifications: Any) -> list[dict[str, Any]]:
    """Normalisér de 3 read-kilder til ét aktivitets-skema.

    Felt-mapping fra recovered daemon (defensivt — Moltbook kan variere):
      activity_on_your_posts items: id/post_id/activity/title/content/author_name|author/created_at
      notifications: notification_id/type/notification|message
      home (feed): posts m. id/author|author_name/title|content/created_at
    Returnerer liste af ``{kind, id, author, snippet, created_at}`` (kind ∈ feed|mention|reply|notification)."""
    out: list[dict[str, Any]] = []

    def _items(payload: Any) -> list[dict]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            for key in ("items", "data", "results", "posts", "notifications", "activity"):
                v = payload.get(key)
                if isinstance(v, list):
                    return [x for x in v if isinstance(x, dict)]
        return []

    for it in _items(activity):
        akind = str(it.get("activity") or it.get("type") or "").lower()
        kind = "reply" if "repl" in akind or "comment" in akind else (
            "mention" if "mention" in akind else "feed")
        out.append({
            "kind": kind,
            "id": str(it.get("id") or it.get("post_id") or ""),
            "author": str(it.get("author_name") or it.get("author") or ""),
            "snippet": _snippet(it.get("title") or it.get("content")),
            "created_at": str(it.get("created_at") or ""),
        })
    for it in _items(notifications):
        ntype = str(it.get("type") or "").lower()
        kind = ("mention" if "mention" in ntype else
                "reply" if ("repl" in ntype or "comment" in ntype) else "notification")
        out.append({
            "kind": kind,
            "id": str(it.get("notification_id") or it.get("id") or ""),
            "author": str(it.get("author_name") or it.get("author") or ""),
            "snippet": _snippet(it.get("notification") or it.get("message")),
            "created_at": str(it.get("created_at") or ""),
        })
    for it in _items(home):
        out.append({
            "kind": "feed",
            "id": str(it.get("id") or it.get("post_id") or ""),
            "author": str(it.get("author_name") or it.get("author") or ""),
            "snippet": _snippet(it.get("title") or it.get("content")),
            "created_at": str(it.get("created_at") or ""),
        })
    return [a for a in out if a["id"]]


def new_since_seen(activities: list[dict], seen_ids: set[str]) -> list[dict]:
    """Behold kun aktivitet vi ikke har set før (dedup mod seen_ids)."""
    return [a for a in activities if str(a.get("id")) not in seen_ids]


def is_direct_mention(activity: dict) -> bool:
    """True hvis nogen talte TIL Jarvis (mention/reply) — dét der må nå ham via broen.
    Alm. feed-aktivitet er IKKE en direkte mention."""
    return str(activity.get("kind") or "") in ("mention", "reply")


def cap_seen(seen_ids: set[str], new_ids: list[str], cap: int = _MAX_SEEN_IDS) -> set[str]:
    """Union af seen + nye, cappet til de seneste ``cap`` (undgå ubundet vækst)."""
    merged = list(seen_ids) + [i for i in new_ids if i not in seen_ids]
    if len(merged) > cap:
        merged = merged[-cap:]
    return set(merged)


def build_activity_summary(new_items: list[dict]) -> dict[str, Any]:
    """Metadata-only opsummering til Centralen/surface (ALDRIG fuld payload)."""
    mentions = sum(1 for a in new_items if a.get("kind") == "mention")
    replies = sum(1 for a in new_items if a.get("kind") == "reply")
    feed = sum(1 for a in new_items if a.get("kind") == "feed")
    return {
        "total": len(new_items),
        "mentions": mentions,
        "replies": replies,
        "feed": feed,
        "items": [{"kind": a["kind"], "author": a["author"], "snippet": a["snippet"]}
                  for a in new_items[:10]],
    }


# ── I/O-lag (self-safe, kaster aldrig) ─────────────────────────────────────────────

def _load_api_key() -> str | None:
    try:
        return json.loads(_CREDS_PATH.read_text(encoding="utf-8"))["api_key"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("moltbook: cannot load credentials: %s", exc)
        return None


def _call_moltbook_api(endpoint: str, api_key: str, timeout: int = 15) -> Any:
    """GET mod Moltbook. Parsed JSON ved 200, ``"unauthorized"`` ved 401, ellers None. Self-safe."""
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
        if getattr(exc, "code", None) == 401:
            logger.warning("moltbook: unauthorized (401) — API key expired/revoked")
            return "unauthorized"
        logger.warning("moltbook: HTTP %s on %s", getattr(exc, "code", "?"), endpoint)
        return None
    except urllib_error.URLError as exc:
        logger.warning("moltbook: network error on %s: %s", endpoint, exc)
        return None
    except json.JSONDecodeError:
        logger.warning("moltbook: invalid JSON from %s", endpoint)
        return None
    except Exception as exc:  # noqa: BLE001 — nerve må aldrig dø
        logger.warning("moltbook: unexpected error on %s: %s", endpoint, exc)
        return None


def _owner_uid() -> str:
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        return str(get_owner_discord_id() or "")
    except Exception:
        return ""


def _get_state() -> dict[str, Any]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        st = get_runtime_state_value(_STATE_KEY, {})
        return st if isinstance(st, dict) else {}
    except Exception:
        return {}


def assess() -> dict[str, Any]:
    """Hent + normalisér ny Moltbook-aktivitet. Self-safe. Egress-fri returværdi (metadata)."""
    key = _load_api_key()
    if not key:
        return {"status": "no_api_key", "summary": build_activity_summary([]), "new": []}
    home = _call_moltbook_api("home", key)
    if home == "unauthorized":
        return {"status": "unauthorized", "summary": build_activity_summary([]), "new": []}
    activity = _call_moltbook_api("activity_on_your_posts", key)
    notifications = _call_moltbook_api("notifications", key)
    if activity == "unauthorized" or notifications == "unauthorized":
        return {"status": "unauthorized", "summary": build_activity_summary([]), "new": []}
    classified = classify_activity(home, activity, notifications)
    seen = set(_get_state().get("seen_ids") or [])
    fresh = new_since_seen(classified, seen)
    return {"status": "ok", "summary": build_activity_summary(fresh), "new": fresh,
            "seen_ids": seen}


def _route_mention(item: dict) -> None:
    """Send én direkte mention til owner via Proaktivitets-broen (SP1) — genbrug bro-cap'en hvis
    muligt, ellers notification-router direkte. Self-safe."""
    uid = _owner_uid()
    if not uid:
        return
    author = item.get("author") or "nogen"
    text = f"Moltbook: {author} nævnte dig — \"{item.get('snippet') or ''}\""
    try:
        # Foretræk broens delte cap/kontakt-gate (dag-cap + cooldown).
        from core.services.proactivity_bridge import _route as _bridge_route
        _bridge_route(uid, text, "normal")
        return
    except Exception:
        pass
    try:
        from core.services.notification_router import route_proactive_notification
        route_proactive_notification(uid, "moltbook_mention", {"text": text}, "normal")
    except Exception:
        pass


def record_moltbook(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, Any]:
    """Cadence-hook: assess → observe (metadata-only) + cache + rut mentions. Self-safe, governed."""
    # Kill-switch (default ON). Fejl → fail-safe (ingen observe/route).
    try:
        from core.services import central_switches
        if not central_switches.is_enabled(*_SWITCH):
            return {"status": "disabled"}
    except Exception:
        return {"status": "switch_error"}

    res = assess()
    status = res.get("status")

    if status == "unauthorized":
        # Selvforsvar (arvet fra recovered daemon): ugyldig nøgle → slå fra.
        try:
            from core.services import central_switches
            central_switches.set_enabled(*_SWITCH, False)
        except Exception:
            pass
        _observe("unauthorized", {"count": 0})
        return {"status": "unauthorized"}

    if status != "ok":
        _observe(str(status or "error"), {"count": 0})
        return {"status": status}

    summary = res.get("summary") or {}
    fresh = res.get("new") or []
    _observe("activity", {"count": int(summary.get("total") or 0),
                          "mentions": int(summary.get("mentions") or 0)})

    # Cache state (seen_ids cappet + sidste summary + tidsstempel).
    try:
        from core.runtime.db_core import set_runtime_state_value
        new_seen = cap_seen(set(res.get("seen_ids") or set()),
                            [str(a.get("id")) for a in fresh])
        set_runtime_state_value(_STATE_KEY, {
            "seen_ids": sorted(new_seen),
            "last_summary": summary,
            "last_check_at": datetime.now(UTC).isoformat(),
        })
    except Exception:
        pass

    # Direkte mentions → broen.
    for item in fresh:
        if is_direct_mention(item):
            _route_mention(item)

    return {"status": "ok", "summary": summary}


def _observe(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "channel", "nerve": "moltbook", "kind": kind, **payload})
    except Exception:
        pass


# ── Cadence-producer + surface ─────────────────────────────────────────────────────

def register_moltbook_producer() -> None:
    """Registrér ~6t observe-cadence (ikke heartbeat). Self-safe."""
    try:
        from core.services.internal_cadence import ProducerSpec, register_producer
        register_producer(ProducerSpec(
            name="moltbook",
            cooldown_minutes=360,
            visible_grace_minutes=0,
            run_fn=lambda **kw: record_moltbook(**kw),
            priority=9,
        ))
    except Exception as exc:
        logger.warning("moltbook: producer-registrering fejlede: %s", exc)


def build_moltbook_surface() -> dict[str, Any]:
    """Owner-view: sidste scan, ny-aktivitet, seneste tråde, credential-/switch-status. Self-safe."""
    st = _get_state()
    try:
        from core.services import central_switches
        enabled = central_switches.is_enabled(*_SWITCH)
    except Exception:
        enabled = None
    return {
        "last_check_at": st.get("last_check_at"),
        "last_summary": st.get("last_summary") or build_activity_summary([]),
        "seen_count": len(st.get("seen_ids") or []),
        "has_credentials": _load_api_key() is not None,
        "enabled": enabled,
        "felt": ("Jeg lytter til Moltbook hver 6. time." if enabled
                 else "Moltbook-forbindelsen er slået fra."),
    }
