#!/usr/bin/env python3
"""Prøv HVER nøgle og HVER model i cheap lane — ad præcis den vej lanen selv bruger.

Bjørn 17/9-2026: «den enste måde at komme igennem og få et klart svar er at
teste hver enste nøgle og provider i systemet manuelt... så vi kan se hvilke
bare er opdatering af model katalog og hvilke skal ud og hvilke der kan gøres
noget ved».

Tællerne i databasen siger HVOR MEGET der fejler; de siger ikke altid HVORFOR
(«not supported» blev bogført som auth-rejected). Denne prøve spørger direkte:

  for hver udbyder × konto (a1 = default, a2 = account2 …):
    * vejen trafikken tager: hjemme-IPv4, native IPv6 (v6bind), NAT64 eller
      VPN-proxy — og hvilken IP det kommer ud som
    * hvad udbyderens /models siger (findes modellen overhovedet?)
    * ét rigtigt kald pr. katalog-model gennem cheap-lanens egen adapter
      (`_execute_provider_chat`) — samme nøgle-opslag, samme egress, samme
      fejlklassificering

Skriver /tmp/cheap_fuld_proeve.json og printer én linje pr. kald. Rører
hverken katalog, registry eller karantæne.

    python scripts/cheap_lane_fuld_proeve.py [--udbyder xkiro] [--timeout 40]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_ROD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROD))

AUTH = Path.home() / ".jarvis-v2" / "auth" / "profiles"


def konti_med_noegle(udbyder: str) -> list[str]:
    """Konti der HAR en nøgle — også dem balanceren ikke regner for klar."""
    konti = set()
    try:
        from core.services.auth_profile_scan import _is_account_profile
    except Exception:
        _is_account_profile = lambda navn: True  # noqa: E731
    if AUTH.is_dir():
        for p in AUTH.iterdir():
            # Enkelt-udbyder-mapper (fx `groq/`, `opencode/`) og backups er ikke
            # konti — balanceren springer dem over, og det skal prøven også.
            if (p / "providers" / udbyder).is_dir() and _is_account_profile(p.name):
                konti.add(p.name)
    try:
        from core.services.auth_profile_scan import ready_profiles_for
        konti.update(ready_profiles_for(udbyder))
    except Exception:
        pass
    try:
        from core.services.cheap_provider_runtime_keys import has_runtime_owner_key
        if has_runtime_owner_key(udbyder):
            konti.add("default")
    except Exception:
        pass
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    if str((CHEAP_PROVIDER_DEFAULTS.get(udbyder) or {}).get("auth_kind")) == "none":
        konti.add("default")
    return sorted(konti, key=lambda k: (k != "default", k))


def vej(udbyder: str, konto: str) -> tuple[str, str | None]:
    from core.services import egress_routing as er
    src = er.resolve_v6bind_source(udbyder, konto)
    if src:
        return "v6bind", src
    if er.resolve_nat64(udbyder, konto):
        return "nat64", None
    from core.services.cheap_provider_runtime_adapters import _resolve_egress_proxy
    try:
        proxy = _resolve_egress_proxy(provider=udbyder, auth_profile=konto)
    except Exception as exc:  # lækage-guarden hæver hellere end at bruge hjemme-IP
        return "BLOKERET", str(exc)[:80]
    return ("proxy", proxy) if proxy else ("hjemme", None)


_IP_CACHE: dict[tuple[str, str | None], str] = {}


def udgangs_ip(rute: str, detalje: str | None) -> str:
    nøgle = (rute, detalje)
    if nøgle in _IP_CACHE:
        return _IP_CACHE[nøgle]
    import httpx
    try:
        if rute == "v6bind":
            with httpx.Client(transport=httpx.HTTPTransport(local_address=detalje), timeout=10) as c:
                ip = c.get("https://api64.ipify.org").text.strip()
        elif rute == "proxy":
            with httpx.Client(proxy=detalje, timeout=10) as c:
                d = c.get("https://ipinfo.io/json").json()
                ip = f"{d.get('ip')} ({d.get('city')}, {d.get('country')})"
        elif rute == "hjemme":
            with httpx.Client(timeout=10) as c:
                d = c.get("https://ipinfo.io/json").json()
                ip = f"{d.get('ip')} ({d.get('city')}, {d.get('country')})"
        elif rute == "nat64":
            ip = "nat64.net (London/Hetzner)"
        else:
            ip = "—"
    except Exception as exc:
        ip = f"ukendt ({type(exc).__name__})"
    _IP_CACHE[nøgle] = ip
    return ip


def modeller_for(udbyder: str, konto: str) -> list[str]:
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    ms = list((CHEAP_PROVIDER_DEFAULTS.get(udbyder) or {}).get("static_models") or [])
    try:
        from core.services.cheap_provider_runtime_selection import _configured_cheap_candidates
        for c in _configured_cheap_candidates(include_public_proxy=True):
            if c.get("provider") == udbyder and c.get("model") not in ms:
                ms.append(str(c.get("model")))
    except Exception:
        pass
    return ms


def liste_modeller(udbyder: str, konto: str) -> tuple[int | None, set[str] | None, str]:
    """Udbyderens egen /models, ad samme vej. (None, None, fejl) hvis den ikke svarer."""
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    k = CHEAP_PROVIDER_DEFAULTS.get(udbyder) or {}
    if k.get("protocol") != "openai-chat" or not k.get("models_endpoint"):
        return None, None, "ingen /models"
    import httpx
    try:
        from core.auth.profiles import get_provider_credentials
    except Exception:
        get_provider_credentials = None
    nøgle = ""
    try:
        from core.services.cheap_provider_runtime_keys import runtime_owner_key
        nøgle = runtime_owner_key(udbyder) if konto == "default" else ""
    except Exception:
        pass
    if not nøgle and get_provider_credentials:
        try:
            cred = get_provider_credentials(profile=konto, provider=udbyder) or {}
            nøgle = str(cred.get("api_key") or cred.get("token") or cred.get("key") or "")
        except Exception:
            pass
    rute, detalje = vej(udbyder, konto)
    kw: dict = {"timeout": 20}
    if rute == "proxy":
        kw["proxy"] = detalje
    elif rute == "v6bind":
        kw["transport"] = httpx.HTTPTransport(local_address=detalje)
    elif rute in ("nat64", "BLOKERET"):
        return None, None, f"springes over ({rute})"
    hoveder = {"User-Agent": "jarvis-v2/cheap-lane"}
    if nøgle:
        hoveder["Authorization"] = f"Bearer {nøgle}"
    try:
        with httpx.Client(**kw) as c:
            r = c.get(str(k["base_url"]).rstrip("/") + str(k["models_endpoint"]), headers=hoveder)
        if r.status_code >= 300:
            return r.status_code, None, r.text[:120].replace("\n", " ")
        data = r.json()
        ids = {str(m.get("id")) for m in (data.get("data") if isinstance(data, dict) else data) or [] if isinstance(m, dict)}
        return r.status_code, ids, ""
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {str(exc)[:80]}"


def proev_kald(udbyder: str, konto: str, model: str, timeout: float) -> dict:
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    from core.services.cheap_provider_runtime_adapters import CheapProviderError, _execute_provider_chat
    import core.services.cheap_provider_runtime_adapters as ad
    t = time.monotonic()
    try:
        # Kortere tidsloft end i drift, så én hængende udbyder ikke tager timer.
        if hasattr(ad, "_TIMEOUT_SECONDS"):
            ad._TIMEOUT_SECONDS = timeout
        r = _execute_provider_chat(
            provider=udbyder, model=model, auth_profile=konto,
            base_url=str((CHEAP_PROVIDER_DEFAULTS.get(udbyder) or {}).get("base_url") or ""),
            message="Svar kun med ordet: pong",
        )
        tekst = str(r.get("text") or r.get("content") or r.get("output_text") or "")
        return {"ok": bool(tekst.strip()), "kode": "ok" if tekst.strip() else "tomt-svar",
                "besked": tekst[:60], "sek": round(time.monotonic() - t, 1)}
    except CheapProviderError as exc:
        return {"ok": False, "kode": exc.code, "status": exc.status_code,
                "besked": " ".join(str(exc.message).split())[:220], "sek": round(time.monotonic() - t, 1)}
    except Exception as exc:
        return {"ok": False, "kode": type(exc).__name__, "besked": str(exc)[:220], "sek": round(time.monotonic() - t, 1)}


def proev_udbyder(udbyder: str, timeout: float) -> list[dict]:
    ud = []
    for konto in konti_med_noegle(udbyder):
        rute, detalje = vej(udbyder, konto)
        ip = udgangs_ip(rute, detalje)
        status, ids, fejl = liste_modeller(udbyder, konto)
        for model in modeller_for(udbyder, konto):
            res = proev_kald(udbyder, konto, model, timeout)
            række = {"udbyder": udbyder, "konto": konto, "model": model, "rute": rute, "udgang": ip,
                     "models_status": status, "models_fejl": fejl,
                     "listet": (model in ids) if ids is not None else None, **res}
            ud.append(række)
            listet = {True: "listet", False: "IKKE-listet", None: "?"}[række["listet"]]
            print(f"{'✅' if res['ok'] else '❌'} {udbyder:15} {konto:9} {model[:40]:40} {rute:7} {listet:11} "
                  f"{res['kode']:18} {res['sek']:5}s {res.get('besked','')[:200]}", flush=True)
    return ud


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--udbyder", action="append")
    a.add_argument("--timeout", type=float, default=40)
    a.add_argument("--ud", default="/tmp/cheap_fuld_proeve.json")
    args = a.parse_args()
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    udbydere = args.udbyder or sorted(CHEAP_PROVIDER_DEFAULTS)
    alle: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rækker in pool.map(lambda u: proev_udbyder(u, args.timeout), udbydere):
            alle.extend(rækker)
    Path(args.ud).write_text(json.dumps(alle, ensure_ascii=False, indent=1))
    ok = sum(1 for r in alle if r["ok"])
    print(f"\n{ok}/{len(alle)} kald svarede. Skrevet til {args.ud}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
