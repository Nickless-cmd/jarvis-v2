"""Device-presence pr. bruger. Lever i hukommelsen — og OVERLEVER en genstart.

Hybrid scoring: aktivitets-recency primær; foreground/desktop-sleep/mobil-netværk
er hints. Reachability: desktop kun online via frisk ping; mobil altid FCM-nåbar.

## Hvorfor den også ligger på disken (20/9-2026)

Tilstanden var rent efemær, og vi genstarter API'en mange gange om dagen. Hver
genstart nulstillede hvem der var til stede: desk er kun «online» med et ping
under 12 sekunder gammelt, så i vinduet mellem genstarten og desks næste ping
havde `rank()` kun de registrerede FCM-tokens tilbage — og alt gik til
telefonen. Det er den samme irritation Bjørn beskrev: han sidder i desk, og
kortet lander et sted han ikke kigger.

Pingene er sekundgamle, så snapshottet skrives med VÆGURSTID og oversættes
tilbage til monotont ur ved indlæsning; poster ældre end `_PRESENCE_TTL_S`
smides væk. Et gammelt snapshot kan altså aldrig holde en død enhed i live.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass, fields

logger = logging.getLogger(__name__)

_now = time.monotonic  # injicerbart i tests

# Justerbare konstanter
_DESKTOP_ONLINE_TTL_S = 12.0   # desktop pinger ~5s; >12s uden ping = offline
_PRESENCE_TTL_S = 120.0        # ryd state-records ældre end dette
_RECENCY_HORIZON_S = 600.0     # recency-vægt aftager lineært over 10 min
# Foreground = hvor brugeren FAKTISK er → skal dominere recency (max 100) + away
# (50), ellers klæber en netop-brugt-men-nu-baggrundet enhed (BUG1: skift mobil↔
# desktop fulgte ikke med). Stor nok til altid at slå recency+away.
_FOREGROUND_BONUS = 1000.0
# Foreground-bonus kræver et FRISK ping. En baggrundet enhed der holdt op med at
# pinge (mobil pinger hvert 30s; desktop hvert 5s) må ikke beholde sin foreground-
# bonus i det uendelige hvis transition-pinget (foreground=False) blev tabt.
_FOREGROUND_FRESH_S = 35.0
_AWAY_MOBILE_BONUS = 50.0
# Spec 2026-06-20 §3.2: en REGISTRERET men inaktiv enhed skal stadig være en nåbar
# fallback-kandidat (lavt score, under enhver aktiv enhed) — så rank() ALDRIG er tom
# når brugeren har en registreret enhed. Hullet der fik Mikkels invite-push til at
# fejle (tom rank → ingen levering).
_REGISTERED_FCM_SCORE = 50.0   # mobil-token uden aktivt ping
_DISCORD_ONLINE_SCORE = 100.0  # discord-gateway rapporterer online
_TELEGRAM_SCORE = 30.0         # altid-tilgængelig, lav prioritet (async)

_lock = threading.Lock()
_PRESENCE: dict[str, dict[str, "DeviceState"]] = {}

_STATE_NAVN = "device_presence"
# Desktop pinger hvert 5. sekund, mobilen hvert 30. Uden en spærre ville hver
# ping koste en fil-skrivning; 5 sekunder holder snapshottet friskt nok til at
# dække en genstart uden at skrive unødigt.
_GEM_INTERVAL_S = 5.0
_sidst_gemt = 0.0


@dataclass
class DeviceState:
    device_key: str
    platform: str           # "desktop" | "mobile"
    last_ping_at: float
    last_interaction_at: float
    foreground: bool = False
    awake: bool = True
    network: str = "unknown"  # "home" | "away" | "unknown"
    push_token: str | None = None
    device_name: str = ""
    active_session_id: str = ""
    battery_saver: bool = False
    # Geolocation (opt-in pr. enhed; None når brugeren ikke deler lokation).
    # {"lat": float, "lon": float, "label": str, "source": str, "precision": str}
    location: dict | None = None


def _gem(*, tving: bool = False) -> None:
    """Skriv et snapshot med vægurstid. Self-safe — må aldrig vælte et ping."""
    global _sidst_gemt
    now = _now()
    if not tving and (now - _sidst_gemt) < _GEM_INTERVAL_S:
        return
    _sidst_gemt = now
    try:
        vaeg = time.time()
        with _lock:
            data = {
                uid: {
                    key: {
                        **asdict(st),
                        # Monotone tal betyder intet efter en genstart. Vi gemmer
                        # ALDEREN oversat til vægursstempler i stedet.
                        "last_ping_wall": vaeg - (now - st.last_ping_at),
                        "last_interaction_wall": vaeg - (now - st.last_interaction_at),
                    }
                    for key, st in devices.items()
                }
                for uid, devices in _PRESENCE.items()
            }
        from core.runtime.state_store import save_json
        save_json(_STATE_NAVN, data)
    except Exception:
        logger.debug("device_presence: kunne ikke gemme snapshot", exc_info=True)


def _indlaes() -> None:
    """Genskab tilstanden fra disken ved import. Forældede poster droppes."""
    try:
        from core.runtime.state_store import load_json
        data = load_json(_STATE_NAVN, {}) or {}
        if not isinstance(data, dict):
            return
        now, vaeg = _now(), time.time()
        felter = {f.name for f in fields(DeviceState)}
        with _lock:
            for uid, devices in data.items():
                if not isinstance(devices, dict):
                    continue
                for key, raw in devices.items():
                    if not isinstance(raw, dict):
                        continue
                    alder = vaeg - float(raw.get("last_ping_wall") or 0.0)
                    if alder < 0 or alder > _PRESENCE_TTL_S:
                        continue  # for gammel (eller et ur der er gået baglæns)
                    i_alder = vaeg - float(raw.get("last_interaction_wall") or 0.0)
                    st = DeviceState(**{k: v for k, v in raw.items() if k in felter})
                    st.last_ping_at = now - alder
                    st.last_interaction_at = now - max(0.0, i_alder)
                    _PRESENCE.setdefault(str(uid), {})[str(key)] = st
    except Exception:
        logger.debug("device_presence: kunne ikke indlæse snapshot", exc_info=True)


def reset() -> None:
    """Kun til tests."""
    with _lock:
        _PRESENCE.clear()
    _gem(tving=True)


def record_ping(
    user_id: str,
    device_key: str,
    platform: str,
    *,
    foreground: bool,
    awake: bool,
    network: str,
    interaction: bool = False,
    location: dict | None = None,
    push_token: str | None = None,
    device_name: str | None = None,
    active_session_id: str | None = None,
    battery_saver: bool | None = None,
) -> None:
    uid, key = (user_id or "").strip(), (device_key or "").strip()
    if not uid or not key:
        return
    now = _now()
    loc = _sanitize_location(location)
    with _lock:
        devices = _PRESENCE.setdefault(uid, {})
        st = devices.get(key)
        ny_enhed = st is None
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
        if push_token is not None:
            st.push_token = (push_token or "").strip() or None
            try:
                if st.push_token:
                    from core.services.device_tokens import register as _register_token
                    _register_token(uid, st.push_token, "android" if platform == "mobile" else platform)
            except Exception:
                pass
        if device_name is not None:
            st.device_name = str(device_name or "").strip()[:80]
        if active_session_id is not None:
            st.active_session_id = str(active_session_id or "").strip()[:120]
        if battery_saver is not None:
            st.battery_saver = bool(battery_saver)
        # location=None i pinget = "ingen ændring" IKKE "ryd" — så en enhed der
        # midlertidigt ikke fik fix beholder sidste kendte. Klienten sender
        # eksplicit {} (tom) når brugeren slår lokation FRA → ryd.
        if location is not None:
            st.location = loc or None
        if interaction:
            st.last_interaction_at = now
    # Uden for låsen (_gem tager den selv). En NY enhed skrives med det samme:
    # det er præcis den besked et push ville mangle lige efter en genstart.
    _gem(tving=ny_enhed)


def _sanitize_location(location: dict | None) -> dict | None:
    """Validér og normalisér en indkommen lokation. Returnerer None ved ugyldigt."""
    if not isinstance(location, dict):
        return None
    try:
        lat = float(location.get("lat"))
        lon = float(location.get("lon"))
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    label = str(location.get("label") or "").strip()[:200]
    source = str(location.get("source") or "unknown").strip()[:20]
    precision = str(location.get("precision") or "city").strip()[:20]
    return {"lat": lat, "lon": lon, "label": label, "source": source, "precision": precision}


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
    # Ryd forældede poster FØR vi rangerer. `prune()` har eksisteret hele tiden
    # med nul kaldere (målt 8/9-2026), så en enhed der holdt op med at pinge blev
    # liggende til processen genstartede: Bjørns liste stod på fem poster for tre
    # enheder, fordi hver geninstallation laver et nyt device_id. Enhederne er
    # ikke tabt — de registrerede FCM-tokens nedenfor er stadig nåbare.
    # Uden for låsen: `prune` tager den selv, og _lock er ikke genindtrædende.
    prune(uid)
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
            # Foreground-bonus kun ved frisk ping → en baggrundet enhed der holdt
            # op med at pinge taber sin foreground-bonus (selv hvis dens sidste
            # ping sagde foreground=True).
            if st.foreground and (now - st.last_ping_at) <= _FOREGROUND_FRESH_S:
                score += _FOREGROUND_BONUS
            if st.platform == "mobile" and st.network == "away":
                score += _AWAY_MOBILE_BONUS
            out.append(RankedDevice(st.device_key, st.platform, score, reachable_via))

    # Augmentér med REGISTREREDE enheder uden aktivt ping (spec §3.2), så rank()
    # altid har ≥1 nåbar kandidat. Dedup mod allerede-rangerede device_keys (for
    # mobil ER device_key == FCM-token, så et aktivt ping vinder over sin egen token).
    seen = {r.device_key for r in out}
    with _lock:
        for st in (_PRESENCE.get(uid) or {}).values():
            if st.push_token:
                seen.add(st.push_token)
    # (a) registrerede FCM-tokens
    try:
        from core.services.device_tokens import list_for_user as _list_tokens
        for tok in _list_tokens(uid):
            if tok and tok not in seen:
                out.append(RankedDevice(tok, "mobile", _REGISTERED_FCM_SCORE, "fcm"))
                seen.add(tok)
    except Exception:
        pass
    # (b) Discord online — best-effort; aktiveres når gateway eksponerer en
    #     is_user_online()-kilde (findes ikke endnu → no-op).
    try:
        from core.services.discord_gateway import is_user_online as _disc_online  # type: ignore
        if _disc_online(uid) and f"discord:{uid}" not in seen:
            out.append(RankedDevice(f"discord:{uid}", "discord", _DISCORD_ONLINE_SCORE, "discord"))
            seen.add(f"discord:{uid}")
    except Exception:
        pass
    # (c) Telegram — best-effort lav-prioritets-fallback hvis brugeren har en binding.
    try:
        from core.services.telegram_gateway import chat_id_for_user as _tg_chat  # type: ignore
        if _tg_chat(uid) and f"telegram:{uid}" not in seen:
            out.append(RankedDevice(f"telegram:{uid}", "telegram", _TELEGRAM_SCORE, "telegram"))
            seen.add(f"telegram:{uid}")
    except Exception:
        pass

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
    loc = (st.location if st else None) or None
    if loc and loc.get("label"):
        # Lokation delt → vis hvor brugeren FAKTISK er. Kort label: sted + enhed +
        # kort netværk (fx "(mobil, mobildata)"); fokus-tilstand udelades — selve
        # lokationen er det vigtige, og device-awareness/routing bruger fokus andetsteds.
        net_short = ""
        if st and st.platform == "mobile":
            net_short = {"home": ", wifi", "away": ", mobildata"}.get(st.network, "")
        return f"Bjørn er ved {loc['label']} ({where}{net_short})."
    return f"Bjørn er ved {where} ({fg}{net})."


def location_for(user_id: str) -> dict | None:
    """Bedst-kendte lokation for en bruger på tværs af enheder (til geo-tools).

    Vælger den enhed med en lokation der har den friskeste ping. Returnerer None
    hvis ingen enhed deler lokation (toggle OFF overalt)."""
    uid = (user_id or "").strip()
    now = _now()
    best_loc: dict | None = None
    best_age = 1e18
    with _lock:
        for st in (_PRESENCE.get(uid) or {}).values():
            if not st.location:
                continue
            age = now - st.last_ping_at
            if age < best_age:
                best_age = age
                best_loc = {**st.location, "platform": st.platform, "age_s": round(age, 1)}
    return best_loc


def debug_snapshot(user_id: str) -> dict:
    """Diagnostik: live presence-tilstande + rank-resultat for én bruger."""
    uid = (user_id or "").strip()
    prune(uid)          # samme grund som i rank() — vis ikke enheder der er væk
    now = _now()
    with _lock:
        devices = [
            {
                "device_key": st.device_key[:12],
                "platform": st.platform,
                "foreground": st.foreground,
                "awake": st.awake,
                "network": st.network,
                "device_name": st.device_name,
                "active_session_id": st.active_session_id,
                "battery_saver": st.battery_saver,
                "ping_age_s": round(now - st.last_ping_at, 1),
                "interaction_age_s": round(now - st.last_interaction_at, 1),
                "location": st.location,
            }
            for st in (_PRESENCE.get(uid) or {}).values()
        ]
    ranked = [
        {"device_key": r.device_key[:12], "platform": r.platform,
         "score": round(r.score, 1), "via": r.reachable_via}
        for r in rank(uid)
    ]
    return {"devices": devices, "ranked": ranked, "summary": summary(uid)}


# Genskab tilstanden ved import — se modulets docstring. Sker én gang pr.
# proces, før nogen når at spørge `rank()` hvem der er til stede.
_indlaes()
