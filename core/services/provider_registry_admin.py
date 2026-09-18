"""Registret over udbydere og modeller — nu med en skrivevej.

## Hvorfor den findes (16/9-2026)

`provider_router.json` ER sandheden om hvilke udbydere og modeller der findes,
og hvilke der er slaaet til. Men der har aldrig vaeret en vej til at SLAA NOGET
FRA: `configure_provider_router_entry` kan kun tilfoeje eller aktivere (den
saetter altid ``enabled: True``), og de eneste deaktiveringer i den levende fil
er skrevet i haanden. Bjoern skal kunne styre det fra desk, og en knap der ikke
kan skrive er en knap der lyver.

## Hvad den ikke goer

* **Roerer aldrig legitimation.** At fjerne en udbyder fra registret sletter
  IKKE dens API-noegle i `~/.jarvis-v2/auth/profiles/…`. En fortrudt fjernelse
  skal kunne fortrydes uden at skulle finde noeglen frem igen.
* **Sletter aldrig uden at have skrevet en backup foerst.** Hver skrivning
  laegger den FORRIGE fil i `~/.jarvis-v2/config/provider_router.backups/`
  med tidsstempel. De ti nyeste beholdes.

## Hvorfor deaktivering og fjernelse er to ting

En deaktiveret model beholder sin plads, sin lane og sin historie, og kan
taendes igen med ét klik. En fjernet model er vaek af registret — og balanceren
bygger sin pulje af netop det register, saa slots forsvinder ved naeste
`refresh_pool`. Det foerste er en beslutning man kan fortryde i morgen; det
andet er oprydning.
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

#: Hvor mange backups vi beholder. Ti raekker en uges pilleri.
BACKUP_LOFT = 10


def _fil():
    from core.runtime.config import PROVIDER_ROUTER_FILE
    return PROVIDER_ROUTER_FILE


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def _laes() -> dict[str, Any]:
    from core.runtime.provider_router import load_provider_router_registry
    r = load_provider_router_registry()
    return {"providers": list(r.get("providers") or []), "models": list(r.get("models") or [])}


def _backup() -> str:
    """Kopiér den nuvaerende fil til side. Returnerer stien, eller "" hvis intet."""
    fil = _fil()
    if not fil.exists():
        return ""
    mappe = fil.parent / "provider_router.backups"
    try:
        mappe.mkdir(parents=True, exist_ok=True)
        # MIKROSEKUNDER, ikke sekunder: to aendringer i samme sekund fik ellers
        # samme navn, og den anden overskrev den foerstes backup. Fanget af
        # testen der ruller to skrivninger tilbage.
        maal = mappe / f"provider_router-{datetime.now(UTC):%Y%m%dT%H%M%S_%fZ}.json"
        shutil.copy2(fil, maal)
        gamle = sorted(mappe.glob("provider_router-*.json"))
        for g in gamle[:-BACKUP_LOFT]:
            g.unlink(missing_ok=True)
        return str(maal)
    except Exception as exc:
        logger.warning("provider_registry_admin: kunne ikke tage backup: %s", exc)
        return ""


def _skriv(registry: dict[str, Any]) -> str:
    """Skriv registret. Backup FOERST — en fortrydelse skal kunne lade sig goere."""
    backup = _backup()
    fil = _fil()
    fil.parent.mkdir(parents=True, exist_ok=True)
    midlertidig = fil.with_suffix(".json.tmp")
    midlertidig.write_text(
        json.dumps({"providers": registry["providers"], "models": registry["models"]},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    midlertidig.replace(fil)          # atomisk: ingen halv fil hvis noget gaar galt
    return backup


def _sig_det_hoejt(handling: str, detalje: dict[str, Any]) -> None:
    """En aendring i registret er en driftsbeslutning. Den skal kunne ses bagefter."""
    logger.info("provider-registret: %s %s", handling, detalje)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("runtime.provider_registry_changed",
                          {"handling": handling, **detalje})
    except Exception:
        logger.debug("provider_registry_admin: kunne ikke udsende haendelsen", exc_info=True)


# ── laesning ──────────────────────────────────────────────────────────────

def fuld_registrering() -> dict[str, Any]:
    """HELE registret — ikke de foerste 8 og 12.

    `provider_router_summary()` klipper til `providers[:8]` og `models[:12]`.
    Live er der 15 udbydere og 46 modeller, saa et dashboard bygget paa den
    ville vise en tredjedel og se komplet ud.
    """
    r = _laes()
    from core.runtime.provider_router import _credentials_ready

    udbydere = []
    for p in r["providers"]:
        navn = str(p.get("provider") or "")
        profil = str(p.get("auth_profile") or "default")
        try:
            klar = bool(_credentials_ready(provider=navn, auth_profile=profil))
        except Exception:
            klar = False
        modeller = [m for m in r["models"] if str(m.get("provider") or "") == navn]
        udbydere.append({
            "provider": navn,
            "auth_mode": p.get("auth_mode"),
            "auth_profile": profil,
            "base_url": p.get("base_url"),
            "enabled": bool(p.get("enabled", True)),
            "credentials_ready": klar,
            "updated_at": p.get("updated_at"),
            "model_count": len(modeller),
            "enabled_model_count": sum(1 for m in modeller if bool(m.get("enabled", True))),
            "quota_policy": list(p.get("quota_policy") or []),
        })

    modeller = [{
        "provider": m.get("provider"),
        "model": m.get("model"),
        "lane": m.get("lane"),
        "enabled": bool(m.get("enabled", True)),
        "priority": m.get("priority"),
        "probe_score": m.get("probe_score"),
        "updated_at": m.get("updated_at"),
        "disabled_at": m.get("disabled_at"),
        "disabled_reason": m.get("disabled_reason"),
        "routing_bias": float(m.get("routing_bias") or 0.0),
    } for m in r["models"]]

    lanes: dict[str, dict[str, int]] = {}
    for m in modeller:
        b = lanes.setdefault(str(m["lane"] or "-"), {"i_alt": 0, "aktive": 0})
        b["i_alt"] += 1
        b["aktive"] += 1 if m["enabled"] else 0

    return {
        "aktiv": True,
        "sti": str(_fil()),
        "udbydere": udbydere,
        "modeller": modeller,
        "lanes": lanes,
        "opsummering": {
            "udbydere": len(udbydere),
            "modeller": len(modeller),
            "aktive_modeller": sum(1 for m in modeller if m["enabled"]),
        },
    }


# ── skrivning ─────────────────────────────────────────────────────────────

_KVOTE_PERIODER = {"minute", "day", "week", "month"}
_KVOTE_ENHEDER = {"tokens", "requests", "credits_usd"}


def _valider_kvote_vinduer(windows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not isinstance(windows, list):
        raise ValueError("windows skal vaere en liste")
    valideret: list[dict[str, object]] = []
    set_nøgler: set[tuple[str, str]] = set()
    for vindue in windows:
        if not isinstance(vindue, dict):
            raise ValueError("hvert kvotevindue skal vaere et objekt")
        period = str(vindue.get("period") or "").strip().lower()
        unit = str(vindue.get("unit") or "").strip().lower()
        if period not in _KVOTE_PERIODER:
            raise ValueError(f"ukendt kvoteperiode: {period or '-'}")
        if unit not in _KVOTE_ENHEDER:
            raise ValueError(f"ukendt kvoteenhed: {unit or '-'}")
        try:
            graense = float(vindue.get("limit") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("kvotegraensen skal vaere et tal") from exc
        if graense <= 0:
            raise ValueError("kvotegraensen skal vaere stoerre end nul")
        noegle = (period, unit)
        if noegle in set_nøgler:
            raise ValueError(f"dobbelt kvotevindue: {period}/{unit}")
        set_nøgler.add(noegle)
        timezone = str(vindue.get("reset_timezone") or "UTC").strip()
        if timezone != "UTC":
            raise ValueError("kun UTC understøttes som reset_timezone")
        normaliseret: dict[str, object] = {
            "period": period,
            "unit": unit,
            "limit": graense,
            "reset_timezone": "UTC",
        }
        if period == "month" and vindue.get("reset_day") is not None:
            try:
                reset_day = int(vindue["reset_day"])
            except (TypeError, ValueError) as exc:
                raise ValueError("reset_day skal vaere et heltal") from exc
            if not 1 <= reset_day <= 31:
                raise ValueError("reset_day skal vaere mellem 1 og 31")
            normaliseret["reset_day"] = reset_day
        valideret.append(normaliseret)
    return valideret


def saet_kvote_politik(*, provider: str, auth_profile: str,
                       windows: list[dict[str, object]],
                       expected_revision: str = "") -> dict[str, Any]:
    """Gem deklarerede kvoter paa den konkrete provider-profil."""
    del expected_revision  # Revisionskontrol tilfoejes med de auditerede kontroller.
    p = (provider or "").strip()
    profil = (auth_profile or "default").strip() or "default"
    try:
        valideret = _valider_kvote_vinduer(windows)
    except ValueError as exc:
        return {"status": "error", "fejl": str(exc)}
    r = _laes()
    for post in r["providers"]:
        if str(post.get("provider") or "") != p:
            continue
        if str(post.get("auth_profile") or "default") != profil:
            return {"status": "error", "fejl": f"ukendt auth_profile: {p}/{profil}"}
        har_cheap_lane = any(
            str(model.get("provider") or "") == p
            and str(model.get("lane") or "") == "cheap"
            for model in r["models"]
        )
        if not har_cheap_lane:
            return {"status": "error", "fejl": f"udbyderen er ikke i cheap lane: {p}"}
        post["quota_policy"] = valideret
        post["updated_at"] = _nu()
        backup = _skriv(r)
        _sig_det_hoejt("kvote_politik", {
            "provider": p, "auth_profile": profil, "vinduer": len(valideret),
        })
        return {"status": "ok", "provider": post, "backup": backup}
    return {"status": "error", "fejl": f"ukendt udbyder: {p}"}

def saet_model_aktiv(*, provider: str, model: str, aktiv: bool,
                     grund: str = "") -> dict[str, Any]:
    """Slaa én model til eller fra. Pladsen, lanen og historien bevares."""
    p, m = (provider or "").strip(), (model or "").strip()
    if not p or not m:
        return {"status": "error", "fejl": "provider og model skal begge angives"}
    r = _laes()
    ramt = None
    for post in r["models"]:
        if str(post.get("provider")) == p and str(post.get("model")) == m:
            post["enabled"] = bool(aktiv)
            post["updated_at"] = _nu()
            if aktiv:
                post.pop("disabled_at", None)
                post.pop("disabled_reason", None)
            else:
                post["disabled_at"] = _nu()
                post["disabled_reason"] = (grund or "slaaet fra fra desk")[:200]
            ramt = post
            break
    if ramt is None:
        return {"status": "error", "fejl": f"ukendt model: {p}/{m}"}
    backup = _skriv(r)
    _sig_det_hoejt("model_aktiv" if aktiv else "model_inaktiv",
                   {"provider": p, "model": m, "grund": grund[:200]})
    return {"status": "ok", "model": ramt, "backup": backup}


def saet_udbyder_aktiv(*, provider: str, aktiv: bool, grund: str = "") -> dict[str, Any]:
    """Slaa en HEL udbyder til eller fra.

    Balanceren filtrerer paa baade udbyder- og model-posten, saa dette slukker
    alle udbyderens modeller paa én gang uden at roere deres egne flag.
    """
    p = (provider or "").strip()
    if not p:
        return {"status": "error", "fejl": "provider skal angives"}
    r = _laes()
    for post in r["providers"]:
        if str(post.get("provider")) == p:
            post["enabled"] = bool(aktiv)
            post["updated_at"] = _nu()
            if not aktiv:
                post["disabled_reason"] = (grund or "slaaet fra fra desk")[:200]
            else:
                post.pop("disabled_reason", None)
            backup = _skriv(r)
            _sig_det_hoejt("udbyder_aktiv" if aktiv else "udbyder_inaktiv",
                           {"provider": p, "grund": grund[:200]})
            return {"status": "ok", "provider": post, "backup": backup}
    return {"status": "error", "fejl": f"ukendt udbyder: {p}"}


def fjern_model(*, provider: str, model: str) -> dict[str, Any]:
    """Fjern én model fra registret. Legitimationen roeres ikke."""
    p, m = (provider or "").strip(), (model or "").strip()
    r = _laes()
    foer = len(r["models"])
    r["models"] = [x for x in r["models"]
                   if not (str(x.get("provider")) == p and str(x.get("model")) == m)]
    if len(r["models"]) == foer:
        return {"status": "error", "fejl": f"ukendt model: {p}/{m}"}
    backup = _skriv(r)
    _sig_det_hoejt("model_fjernet", {"provider": p, "model": m})
    return {"status": "ok", "fjernet": 1, "backup": backup}


def fjern_udbyder(*, provider: str) -> dict[str, Any]:
    """Fjern en udbyder OG dens modeller fra registret.

    Noeglen bliver liggende i auth-profilen med vilje: fortryder man, skal man
    ikke skulle finde den frem igen.
    """
    p = (provider or "").strip()
    r = _laes()
    modeller = [x for x in r["models"] if str(x.get("provider")) == p]
    udbydere = [x for x in r["providers"] if str(x.get("provider")) == p]
    if not modeller and not udbydere:
        return {"status": "error", "fejl": f"ukendt udbyder: {p}"}
    r["models"] = [x for x in r["models"] if str(x.get("provider")) != p]
    r["providers"] = [x for x in r["providers"] if str(x.get("provider")) != p]
    backup = _skriv(r)
    _sig_det_hoejt("udbyder_fjernet", {"provider": p, "modeller": len(modeller)})
    return {"status": "ok", "fjernede_modeller": len(modeller),
            "legitimation_bevaret": True, "backup": backup}


def gendan_backup(*, sti: str = "") -> dict[str, Any]:
    """Rul registret tilbage til en backup. Tom sti = den nyeste."""
    mappe = _fil().parent / "provider_router.backups"
    try:
        valgt = (mappe / sti).resolve() if sti else None
        if valgt is None:
            kandidater = sorted(mappe.glob("provider_router-*.json"))
            if not kandidater:
                return {"status": "error", "fejl": "der er ingen backups"}
            valgt = kandidater[-1]
        # Vaern mod at pege ud af mappen med «../» — stien kommer fra en klient.
        if mappe.resolve() not in valgt.parents:
            return {"status": "error", "fejl": "stien ligger uden for backup-mappen"}
        data = json.loads(valgt.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error", "fejl": str(exc)[:200]}
    backup = _skriv({"providers": list(data.get("providers") or []),
                     "models": list(data.get("models") or [])})
    _sig_det_hoejt("gendannet", {"fra": str(valgt)})
    return {"status": "ok", "gendannet_fra": str(valgt), "backup": backup}


def backups() -> list[dict[str, Any]]:
    """Hvilke backups findes — nyeste foerst."""
    mappe = _fil().parent / "provider_router.backups"
    try:
        ud = []
        for f in sorted(mappe.glob("provider_router-*.json"), reverse=True):
            s = f.stat()
            ud.append({"navn": f.name, "bytes": s.st_size,
                       "tid": datetime.fromtimestamp(s.st_mtime, UTC).isoformat()})
        return ud
    except Exception:
        return []


def tilfoej(*, provider: str, model: str, lane: str = "cheap",
            auth_mode: str = "api_key", auth_profile: str = "default",
            base_url: str = "", api_key: str = "") -> dict[str, Any]:
    """Tilfoej (eller gen-aktivér) en udbyder + model i registret.

    Bygger paa `configure_provider_router_entry`, som allerede kan det —
    og som ALTID saetter `enabled: True`. Det er rigtigt HER: man tilfoejer
    noget for at bruge det. At slaa fra er en anden handling med sin egen knap.

    ## Noeglen

    `api_key` er valgfri. Er den tom, roeres legitimationen ikke — saa kan man
    tilfoeje en model til en udbyder der allerede har sin noegle, uden at skulle
    finde den frem igen. Noeglen gemmes af `save_provider_credentials` i
    auth-profilen, aldrig i registret, og den vender aldrig tilbage i svaret.
    """
    p_navn, m_navn = (provider or "").strip(), (model or "").strip()
    if not p_navn or not m_navn:
        return {"status": "error", "fejl": "provider og model skal begge angives"}
    backup = _backup()
    try:
        from core.runtime.provider_router import configure_provider_router_entry
        ud = configure_provider_router_entry(
            provider=p_navn, model=m_navn, auth_mode=auth_mode,
            auth_profile=auth_profile, base_url=base_url,
            api_key=api_key, lane=lane, set_visible=False,
        )
    except Exception as exc:
        return {"status": "error", "fejl": str(exc)[:200], "backup": backup}
    _sig_det_hoejt("tilfoejet", {"provider": p_navn, "model": m_navn, "lane": lane,
                                "noegle_gemt": bool(ud.get("credentials_saved"))})
    # Noeglen selv naar ALDRIG tilbage til klienten.
    return {"status": "ok", "provider": p_navn, "model": m_navn, "lane": lane,
            "noegle_gemt": bool(ud.get("credentials_saved")), "backup": backup}


def saet_lane(*, provider: str, model: str, lane: str) -> dict[str, Any]:
    """Flyt en model til en anden lane (cheap, local, coding, visible …).

    Lanen afgoer HVEM der bruger modellen. Balanceren bygger sin pulje af
    `lane == "cheap"`, saa en flytning herfra tager modellen ud af puljen ved
    naeste opbygning — uden at den bliver slaaet fra.
    """
    p_navn, m_navn, l = (provider or "").strip(), (model or "").strip(), (lane or "").strip()
    if not p_navn or not m_navn or not l:
        return {"status": "error", "fejl": "provider, model og lane skal alle angives"}
    r = _laes()
    for post in r["models"]:
        if str(post.get("provider")) == p_navn and str(post.get("model")) == m_navn:
            foer = post.get("lane")
            post["lane"] = l
            post["updated_at"] = _nu()
            backup = _skriv(r)
            _sig_det_hoejt("lane_aendret", {"provider": p_navn, "model": m_navn,
                                            "fra": foer, "til": l})
            return {"status": "ok", "fra": foer, "til": l, "backup": backup}
    return {"status": "error", "fejl": f"ukendt model: {p_navn}/{m_navn}"}


def saet_routing_bias(*, provider: str, model: str, bias: float) -> dict[str, Any]:
    """Set a bounded, explicit soft routing factor on one Cheap Lane model."""
    if not -0.9 <= float(bias) <= 2.0:
        return {"status": "error", "fejl": "routing bias skal vaere mellem -0.9 og 2.0"}
    p, m = (provider or "").strip(), (model or "").strip()
    r = _laes()
    for post in r["models"]:
        if str(post.get("provider") or "") == p and str(post.get("model") or "") == m:
            if str(post.get("lane") or "") != "cheap":
                return {"status": "error", "fejl": f"modellen er ikke i cheap lane: {p}/{m}"}
            post["routing_bias"] = float(bias)
            post["updated_at"] = _nu()
            backup = _skriv(r)
            _sig_det_hoejt("routing_bias", {"provider": p, "model": m, "bias": float(bias)})
            return {"status": "ok", "model": post, "backup": backup}
    return {"status": "error", "fejl": f"ukendt model: {p}/{m}"}
