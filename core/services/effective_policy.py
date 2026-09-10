"""Hvad GJALDT der faktisk for denne koersel — Fase 9.

MAALT 10/9-2026: hverken `visible_runs` (13 kolonner) eller `agent_runs` (19)
havde ét eneste politik-felt. Ingen koersel kunne bagefter sige hvilke
vaerktoejer den saa, om den var autonom, eller om bash var i sandkasse.

Det er ikke bogholderi. Det er den observabilitet der goer dagens
hyppigste fejlklasse SYNLIG i stedet for noget der skal bevises med en
subproces-test: et barn i en bar traad mister tavst sit vaerktoejs-scope og
sin autonomi, og de to tab peger i den FARLIGE retning — tomt scope betyder
«unbound legacy» (ser alt), og tabt autonomi fjerner sandkasse-kravet for
bash. Med et oejebliksbillede pr. koersel staar det i data i stedet for at
skulle udledes.

ANMODET vs FAKTISK (kriterium 7). Sandkassen har to sandheder: om den er
slaaet til, og om den faktisk blev KRAEVET for dette kald. De to kan afvige —
autonomi-kravet er `is_autonomous() and _sbx_taendt()` — og en profil der kun
viser den ene ville lyve. Begge felter er derfor med.

Hashen er over de POLITIK-baerende felter, ikke over tidsstempler, saa to
koersler under samme politik giver samme hash og en aendring er til at se.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("uvicorn.error")

# Hoejnes naar FELTERNE aendrer sig, saa gamle hashes ikke sammenlignes med nye.
SKEMA_VERSION = 1


def _tool_scope() -> str:
    try:
        from core.tools.tool_scoping import current_tool_scope
        return str(current_tool_scope() or "")
    except Exception:
        return ""


def _autonom() -> bool | None:
    try:
        from core.services.run_autonomy_context import is_autonomous
        return bool(is_autonomous())
    except Exception:
        return None


def _sandkasse() -> tuple[bool | None, bool | None]:
    """(slaaet_til, kraevet_for_denne_koersel) — anmodet vs faktisk."""
    taendt: bool | None = None
    try:
        # SAMME kilde som exec-stien bruger (`simple_tools_web._exec_bash`),
        # ikke `central_switches.is_enabled` — den defaulter til AABEN, og en
        # profil der viser «sandkasse til» paa en fail-open-default ville
        # lyve. Foerste udgave gaettede funktionsnavnet og fik tavst `None`:
        # maalt, men forkert maalt.
        from core.services.bash_sandbox import is_available, is_enabled
        taendt = bool(is_enabled()) and bool(is_available())
    except Exception:
        taendt = None
    aut = _autonom()
    kraevet = None if (taendt is None or aut is None) else bool(taendt and aut)
    return taendt, kraevet


def _tillid() -> bool | None:
    try:
        from core.services.workspace_trust import _trust_ctx
        return _trust_ctx.get(None) is not None
    except Exception:
        return None


def _ejer_godkendt() -> bool | None:
    try:
        from core.tools.owner_approval import _ejer_godkendt as v
        return bool(v.get(False))
    except Exception:
        return None


def snapshot(**ekstra: Any) -> dict[str, Any]:
    """Tag et oejebliksbillede af den politik der gaelder LIGE NU.

    Kaster aldrig: en manglende maaling bliver `None`, ikke en fejl. Et
    ukendt felt maa ikke kunne vaelte en koersel, men det maa heller ikke
    forveksles med et maalt «nej» — derfor `None` og ikke `False`.
    """
    try:
        felter = _maal()
    except Exception:
        # Loeftet «kaster aldrig» skal holde STRUKTURELT, ikke fordi hver
        # hjaelper husker sin egen vagt. `snapshot()` kaldes inde i
        # `create_agent_run`, saa en fejl her ville braekke oprettelsen af
        # koersler — en observabilitets-funktion der vaelter det den
        # observerer. (Min egen test fandt det.)
        logger.warning("kunne ikke maale politikken — koerslen bogfoeres uden",
                       exc_info=True)
        felter = {"skema_version": SKEMA_VERSION, "maaling_fejlede": True}
    for k, v in ekstra.items():
        felter[str(k)] = v
    felter["policy_hash"] = _hash(felter)
    return felter


def _maal() -> dict[str, Any]:
    taendt, kraevet = _sandkasse()
    felter: dict[str, Any] = {
        "skema_version": SKEMA_VERSION,
        "tool_scope": _tool_scope(),
        # Tomt scope er IKKE «ingen adgang». Det betyder «unbound legacy» og
        # ser ALT — derfor staar det eksplicit, saa en flade ikke laeser
        # tomheden som en begraensning.
        "tool_scope_betydning": ("unbound-legacy (ser alt)" if not _tool_scope()
                                 else "afgraenset"),
        "autonom": _autonom(),
        "sandkasse_taendt": taendt,
        "sandkasse_kraevet": kraevet,
        "workspace_tillid": _tillid(),
        "ejer_godkendt": _ejer_godkendt(),
    }
    return felter


def _hash(felter: dict[str, Any]) -> str:
    """sha256 over de politik-baerende felter — uden tidsstempler og id'er,
    saa to koersler under samme politik giver SAMME hash."""
    rene = {k: v for k, v in felter.items()
            if k not in ("policy_hash",) and not k.endswith("_at")
            and not k.endswith("_id")}
    try:
        raa = json.dumps(rene, sort_keys=True, ensure_ascii=True, default=str)
    except Exception:
        raa = repr(sorted(rene.items(), key=lambda kv: kv[0]))
    return hashlib.sha256(raa.encode("utf-8")).hexdigest()[:16]


def afviger(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Hvilke politik-felter er forskellige? Til at forklare et hash-skift."""
    ud = []
    for k in sorted(set(a) | set(b)):
        if k == "policy_hash":
            continue
        if a.get(k) != b.get(k):
            ud.append(f"{k}: {a.get(k)!r} -> {b.get(k)!r}")
    return ud
