"""In-memory device-presence pr. bruger. Efemær — genopbygges af klient-pings.

Hybrid scoring: aktivitets-recency primær; foreground/desktop-sleep/mobil-netværk
er hints. Reachability: desktop kun online via frisk ping; mobil altid FCM-nåbar.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

_now = time.monotonic  # injicerbart i tests

# Justerbare konstanter
_DESKTOP_ONLINE_TTL_S = 12.0   # desktop pinger ~5s; >12s uden ping = offline
_PRESENCE_TTL_S = 120.0        # ryd state-records ældre end dette
_RECENCY_HORIZON_S = 600.0     # recency-vægt aftager lineært over 10 min
_FOREGROUND_BONUS = 100.0
_AWAY_MOBILE_BONUS = 50.0

_lock = threading.Lock()
_PRESENCE: dict[str, dict[str, "DeviceState"]] = {}


@dataclass
class DeviceState:
    device_key: str
    platform: str           # "desktop" | "mobile"
    last_ping_at: float
    last_interaction_at: float
    foreground: bool = False
    awake: bool = True
    network: str = "unknown"  # "home" | "away" | "unknown"


def reset() -> None:
    """Kun til tests."""
    with _lock:
        _PRESENCE.clear()


def record_ping(
    user_id: str,
    device_key: str,
    platform: str,
    *,
    foreground: bool,
    awake: bool,
    network: str,
    interaction: bool = False,
) -> None:
    uid, key = (user_id or "").strip(), (device_key or "").strip()
    if not uid or not key:
        return
    now = _now()
    with _lock:
        devices = _PRESENCE.setdefault(uid, {})
        st = devices.get(key)
        if st is None:
            st = DeviceState(
                device_key=key, platform=platform,
                last_ping_at=now, last_interaction_at=now,
            )
            devices[key] = st
        st.platform = platform
        st.last_ping_at = now
        st.foreground = bool(foreground)
        st.awake = bool(awake)
        st.network = network or "unknown"
        if interaction:
            st.last_interaction_at = now


@dataclass
class RankedDevice:
    device_key: str
    platform: str
    score: float
    reachable_via: str   # "desktop_queue" | "fcm"


def _recency_weight(now: float, last_interaction_at: float) -> float:
    age = max(0.0, now - last_interaction_at)
    if age >= _RECENCY_HORIZON_S:
        return 0.0
    return (_RECENCY_HORIZON_S - age) / _RECENCY_HORIZON_S * 100.0


def rank(user_id: str) -> list[RankedDevice]:
    uid = (user_id or "").strip()
    now = _now()
    out: list[RankedDevice] = []
    with _lock:
        for st in (_PRESENCE.get(uid) or {}).values():
            if st.platform == "desktop":
                if not st.awake:
                    continue  # sovende desktop = ikke kandidat
                if (now - st.last_ping_at) > _DESKTOP_ONLINE_TTL_S:
                    continue  # offline desktop = ikke nåbar
                reachable_via = "desktop_queue"
            else:  # mobile — altid FCM-nåbar
                reachable_via = "fcm"
            score = _recency_weight(now, st.last_interaction_at)
            if st.foreground:
                score += _FOREGROUND_BONUS
            if st.platform == "mobile" and st.network == "away":
                score += _AWAY_MOBILE_BONUS
            out.append(RankedDevice(st.device_key, st.platform, score, reachable_via))
    out.sort(key=lambda r: r.score, reverse=True)
    return out


def prune(user_id: str | None = None) -> None:
    now = _now()
    with _lock:
        uids = [user_id] if user_id else list(_PRESENCE.keys())
        for uid in uids:
            devices = _PRESENCE.get(uid) or {}
            stale = [k for k, st in devices.items() if (now - st.last_ping_at) > _PRESENCE_TTL_S]
            for k in stale:
                devices.pop(k, None)
            if not devices:
                _PRESENCE.pop(uid, None)


def summary(user_id: str) -> str:
    ranked = rank(user_id)
    if not ranked:
        return "Ingen aktiv enhed lige nu."
    best = ranked[0]
    with _lock:
        st = (_PRESENCE.get((user_id or "").strip()) or {}).get(best.device_key)
    where = "desktop" if best.platform == "desktop" else "mobil"
    fg = "i fokus" if (st and st.foreground) else "i baggrund"
    net = ""
    if st and st.platform == "mobile":
        net = {"home": ", hjemme-wifi", "away": ", på mobildata (ude)"}.get(st.network, "")
    return f"Bjørn er ved {where} ({fg}{net})."
