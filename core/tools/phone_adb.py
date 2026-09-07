"""ADB over Wi-Fi — ægte skal på telefonen, uden om broen.

Broen ([[phone_tools]]) lader appen udføre ting i sin EGEN sandkasse. Det er
rigtigt for kamera, position og mikrofon, men det er også grænsen: en
Android-app kan køre ``sh``, men ser kun sine egne filer, et skrabet toybox
og ``/system`` skrivebeskyttet. Et ``phone_bash`` bygget på broen ville ligne
noget det ikke er, og det er værre end ikke at have det.

Den her vej går uden om appen: ``adb`` kører på CT105 og taler direkte med
telefonen over LAN'et. Det giver den rigtige skal — ``getprop``, ``dumpsys``,
filsystemet, input-events, skærmbilleder.

**Det er et stående hul, og det skal det se ud som.** Trådløs fejlfinding er
tændt på telefonen, og enhver på LAN'et der kan nå porten kan prøve at parre.
Derfor:

* Adressen står i ``runtime.json`` (``phone_adb_address``), ikke i koden. Ingen
  hardkodet enhed, jf. repoets secrets-regel.
* ``phone_adb_shell`` går gennem samme godkendelses-kort som
  ``operator_open_url`` — Bjørn ser kommandoen før den kører. Vilkårlig
  eksekvering på hans telefon må ikke have en lettere vej end på hans
  computer.
* Parringskoden kan ikke automatiseres, og det er med vilje: den er selve
  sikkerhedskontrollen. ``phone_adb_pair`` beder om den, den gemmes ikke, og
  den logges ikke.

Læs- og status-kald kræver ingen godkendelse — de ændrer intet.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

_ADB_TIMEOUT_S = 30.0
_ADRESSE_NOEGLE = "phone_adb_address"


def _adb_sti() -> str | None:
    return shutil.which("adb")


def _adresse(args: dict[str, Any] | None = None) -> str:
    """Telefonens ``host:port``. Argument slår config, config slår ingenting."""
    fra_arg = str((args or {}).get("adresse") or "").strip()
    if fra_arg:
        return fra_arg
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key(_ADRESSE_NOEGLE) or "").strip()
    except Exception:
        return ""


def _koer_adb(argv: list[str], *, timeout_s: float = _ADB_TIMEOUT_S) -> dict[str, Any]:
    """Kør adb og returnér resultatet. Kaster aldrig — fejl er data.

    Kommandolinjen returneres med, så et fejlende kald kan efterprøves i
    hånden i stedet for at skulle gættes.
    """
    adb = _adb_sti()
    if not adb:
        return {"status": "error", "error": "adb_ikke_installeret",
                "hint": "sudo apt-get install -y adb på den maskine runtime kører på"}
    try:
        p = subprocess.run(
            [adb, *argv], capture_output=True, text=True, timeout=timeout_s,
        )
        return {
            "status": "ok" if p.returncode == 0 else "error",
            "exit_code": p.returncode,
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip(),
            "kommando": "adb " + " ".join(argv),
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "adb_timeout",
                "kommando": "adb " + " ".join(argv), "timeout_s": timeout_s}
    except Exception as exc:  # pragma: no cover — subprocess-fejl er sjældne
        return {"status": "error", "error": f"adb_fejl: {exc!s}"[:200]}


def _forbundet(adresse: str) -> bool:
    """Står telefonen som ``device`` (ikke ``offline``/``unauthorized``) i adb?"""
    r = _koer_adb(["devices"])
    if r.get("status") != "ok":
        return False
    for linje in str(r.get("stdout") or "").splitlines()[1:]:
        dele = linje.split()
        if len(dele) >= 2 and dele[0] == adresse and dele[1] == "device":
            return True
    return False


# ── exec-handlere ───────────────────────────────────────────────────────


def _exec_phone_adb_status(args: dict[str, Any]) -> dict[str, Any]:
    """Hvad adb ser lige nu. Ændrer intet, kræver derfor ingen godkendelse."""
    adresse = _adresse(args)
    r = _koer_adb(["devices", "-l"])
    r["adresse"] = adresse or "(ikke sat i runtime.json: %s)" % _ADRESSE_NOEGLE
    r["forbundet"] = bool(adresse) and _forbundet(adresse)
    if not adresse:
        r["hint"] = (
            "Sæt %s i ~/.jarvis-v2/config/runtime.json til telefonens "
            "host:port fra Trådløs fejlfinding." % _ADRESSE_NOEGLE
        )
    return r


def _exec_phone_adb_connect(args: dict[str, Any]) -> dict[str, Any]:
    """Forbind til telefonen. Kræver at der er parret én gang først."""
    adresse = _adresse(args)
    if not adresse:
        return {"status": "error", "error": "ingen_adresse",
                "hint": "Sæt %s i runtime.json eller send adresse=host:port." % _ADRESSE_NOEGLE}
    r = _koer_adb(["connect", adresse])
    # adb connect giver exit 0 selv når den fejler ('failed to connect'), så
    # returkoden alene er ikke et svar — vi spørger devices bagefter.
    r["forbundet"] = _forbundet(adresse)
    if not r["forbundet"]:
        r["status"] = "error"
        r.setdefault("hint",
                     "Er Trådløs fejlfinding tændt, og er der parret? Kør phone_adb_pair.")
    return r


def _exec_phone_adb_pair(args: dict[str, Any]) -> dict[str, Any]:
    """Par med telefonen. Koden kommer fra Bjørn og gemmes ikke.

    Parringen er en ENGANGS-handling pr. telefon, og koden er selve
    sikkerhedskontrollen — den vises kun på telefonens skærm og skiftes hver
    gang. Derfor kan den hverken automatiseres eller huskes her, og det er
    ikke en mangel.
    """
    par_adresse = str(args.get("par_adresse") or "").strip()
    kode = str(args.get("kode") or "").strip()
    if not par_adresse or not kode:
        return {
            "status": "mangler_input",
            "hint": (
                "Telefonen: Indstillinger → Udvikler → Trådløs fejlfinding → "
                "Par enhed med parringskode. Giv mig BÅDE adressen (den med "
                "parrings-porten, ikke forbindelses-porten) og den 6-cifrede kode."
            ),
        }
    r = _koer_adb(["pair", par_adresse, kode])
    # Koden må ikke ende i et event, en log eller et tool-resultat.
    r.pop("kommando", None)
    r["kommando"] = "adb pair %s <kode udeladt>" % par_adresse
    return r


def _exec_phone_adb_shell(args: dict[str, Any]) -> dict[str, Any]:
    """Kør en kommando på telefonen. **Kræver godkendelse.**

    Samme port som ``operator_open_url``: vilkårlig eksekvering på Bjørns
    telefon må ikke have en lettere vej end på hans computer.
    """
    kommando = str(args.get("kommando") or args.get("command") or "").strip()
    if not kommando:
        return {"status": "error", "error": "kommando er påkrævet"}
    adresse = _adresse(args)
    if not adresse:
        return {"status": "error", "error": "ingen_adresse",
                "hint": "Sæt %s i runtime.json." % _ADRESSE_NOEGLE}

    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "phone_adb_shell",
            "message": "Jarvis vil køre en kommando på din telefon (%s): %s" % (adresse, kommando),
            "command": kommando,
        }

    timeout_s = float(args.get("timeout") or _ADB_TIMEOUT_S)
    return _koer_adb(["-s", adresse, "shell", kommando],
                     timeout_s=max(5.0, min(timeout_s, 300.0)))


def _exec_phone_adb_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    """Tag et skærmbillede af telefonen og gem det på runtime-maskinen.

    Kræver godkendelse — modsat computerens ``operator_screenshot``. En
    telefonskærm har bank, beskeder og totrins-koder på sig, og den ligger
    ikke ved siden af Bjørn når han arbejder. Han skal se at det sker.
    """
    adresse = _adresse(args)
    if not adresse:
        return {"status": "error", "error": "ingen_adresse"}
    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "phone_adb_screenshot",
            "message": "Jarvis vil tage et skærmbillede af din telefon (%s)." % adresse,
            "command": "adb -s %s exec-out screencap -p" % adresse,
        }

    import base64
    adb = _adb_sti()
    if not adb:
        return {"status": "error", "error": "adb_ikke_installeret"}
    try:
        p = subprocess.run(
            [adb, "-s", adresse, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=_ADB_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "adb_timeout"}
    if p.returncode != 0 or not p.stdout:
        return {"status": "error", "error": (p.stderr or b"").decode("utf-8", "replace")[:200]}
    gem_sti = str(args.get("gem_sti") or "").strip()
    ud: dict[str, Any] = {"status": "ok", "bytes": len(p.stdout), "format": "png"}
    if gem_sti:
        with open(gem_sti, "wb") as f:
            f.write(p.stdout)
        ud["gem_sti"] = gem_sti
    else:
        ud["png_base64"] = base64.b64encode(p.stdout).decode("ascii")
    return ud


PHONE_ADB_TOOL_NAMES: tuple[str, ...] = (
    "phone_adb_status", "phone_adb_connect", "phone_adb_pair",
    "phone_adb_shell", "phone_adb_screenshot",
)

PHONE_ADB_TOOL_EXECUTORS: dict[str, Any] = {
    "phone_adb_status": _exec_phone_adb_status,
    "phone_adb_connect": _exec_phone_adb_connect,
    "phone_adb_pair": _exec_phone_adb_pair,
    "phone_adb_shell": _exec_phone_adb_shell,
    "phone_adb_screenshot": _exec_phone_adb_screenshot,
}


def _f(navn: str, beskrivelse: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": navn, "description": beskrivelse,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


PHONE_ADB_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _f("phone_adb_status",
       "Owner-only. Hvad adb ser: er Bjørns telefon forbundet over Wi-Fi. "
       "Ændrer intet. Start her når et phone_adb_*-kald fejler.",
       {"adresse": {"type": "string", "description": "host:port (default fra runtime.json)."}},
       []),
    _f("phone_adb_connect",
       "Owner-only. Forbind til telefonen over Wi-Fi. Kræver at der er parret "
       "én gang først (phone_adb_pair).",
       {"adresse": {"type": "string"}}, []),
    _f("phone_adb_pair",
       "Owner-only. Par med telefonen. Koden vises KUN på telefonens skærm og "
       "skifter hver gang — spørg Bjørn om den, den kan ikke slås op.",
       {"par_adresse": {"type": "string", "description": "host:port fra parrings-dialogen (anden port end forbindelsen)."},
        "kode": {"type": "string", "description": "Den 6-cifrede kode fra telefonens skærm."}},
       []),
    _f("phone_adb_shell",
       "Owner-only. Kør en kommando på Bjørns telefon over adb. ÆGTE skal — "
       "getprop, dumpsys, filsystem, input. KRÆVER godkendelse, som på hans "
       "computer.",
       {"kommando": {"type": "string"},
        "adresse": {"type": "string"},
        "timeout": {"type": "number", "description": "Sekunder, 5-300 (default 30)."}},
       ["kommando"]),
    _f("phone_adb_screenshot",
       "Owner-only. Skærmbillede af telefonen. KRÆVER godkendelse — en "
       "telefonskærm har bank, beskeder og koder på sig.",
       {"adresse": {"type": "string"},
        "gem_sti": {"type": "string", "description": "Gem PNG her i stedet for at returnere base64."}},
       []),
]
