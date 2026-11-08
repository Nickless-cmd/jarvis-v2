"""Lækage-tjek — password og email mod HaveIBeenPwned.

To værktøjer med vidt forskellige forudsætninger:

* ``check_password_breach`` kræver INGEN API-nøgle. Den bruger k-anonymitet:
  passwordet hashes til SHA-1, og kun de første fem hex-tegn sendes afsted.
  Serveren svarer med alle de suffixes der deler de fem tegn — typisk flere
  hundrede — og resten af sammenligningen sker lokalt. Passwordet forlader
  aldrig maskinen, og det kan ikke rekonstrueres fra det der blev sendt.

* ``check_email_breach`` kræver en betalt API-nøgle (``hibp_api_key`` i
  runtime.json). Uden nøglen findes svaret ikke — og her er fælden: en
  manglende nøgle må IKKE ligne «ingen brud fundet». De to tilstande er
  forskellige, og en bruger der tror sin mail er ren fordi et opslag stille
  fejlede, er værre stillet end en der ved at opslaget ikke blev gjort.

Netværksfejl giver derfor ``status: "error"`` — aldrig ``breaches: 0``.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_RANGE_URL = "https://api.pwnedpasswords.com/range/"
_ACCOUNT_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/"
# HIBP afviser kald uden User-Agent. Samme fælde som ntfy bag Cloudflare:
# et 403 uden denne header betyder «manglende header», ikke «nøgle roteret».
_USER_AGENT = "jarvis-v2-breach-check"
_TIMEOUT = 15.0


def _runtime_key(name: str) -> str:
    """Læs en nøgle fra runtime.json — tom streng hvis den ikke findes."""
    try:
        from core.runtime.runtime_config import read_runtime_key
    except ImportError as exc:
        logger.warning("runtime_config kunne ikke importeres: %s", exc)
        return ""
    try:
        return str(read_runtime_key(name) or "")
    except Exception as exc:
        logger.warning("kunne ikke laese '%s' fra runtime.json: %s", name, exc)
        return ""


def _exec_check_password_breach(args: dict[str, Any]) -> dict[str, Any]:
    """K-anonymitet: kun fem hex-tegn af SHA-1-hashen forlader maskinen."""
    raw = args.get("password")
    forudberegnet = args.get("sha1_hash")

    if forudberegnet:
        digest = str(forudberegnet).strip().upper()
        if len(digest) != 40 or any(c not in "0123456789ABCDEF" for c in digest):
            return {"status": "error",
                    "error": "sha1_hash skal være 40 hex-tegn (SHA-1, hex)"}
    elif raw:
        digest = hashlib.sha1(str(raw).encode("utf-8")).hexdigest().upper()
    else:
        return {"status": "error",
                "error": "angiv password (hashes straks lokalt) eller sha1_hash"}

    praefiks, suffiks = digest[:5], digest[5:]

    try:
        import httpx
        r = httpx.get(_RANGE_URL + praefiks,
                      headers={"User-Agent": _USER_AGENT},
                      timeout=_TIMEOUT)
    except Exception as exc:
        logger.warning("Pwned Passwords-opslag fejlede: %s", exc)
        # Bevidst ingen fallback: et netværksnedbrud er ikke «ikke lækket».
        return {"status": "error", "error": f"opslag fejlede: {exc}",
                "note": "Intet svar fra Pwned Passwords — det er IKKE det samme som at passwordet er rent."}

    if r.status_code != 200:
        return {"status": "error",
                "error": f"Pwned Passwords svarede HTTP {r.status_code}",
                "note": "Status ikke afgjort — prøv igen senere."}

    antal = 0
    for linje in r.text.splitlines():
        dele = linje.strip().split(":")
        if len(dele) == 2 and dele[0].upper() == suffiks:
            try:
                antal = int(dele[1])
            except ValueError:
                antal = 0
            break

    return {
        "status": "ok",
        "breached": antal > 0,
        "count": antal,
        "praefiks_sendt": praefiks,
        "kandidater_i_svar": len(r.text.splitlines()),
        "note": (f"Passwordet er set i {antal:,} lækager. Skift det nu."
                 if antal else
                 "Passwordet findes ikke i Pwned Passwords-databasen."),
    }


def _exec_check_email_breach(args: dict[str, Any]) -> dict[str, Any]:
    """Kræver API-nøgle. Uden nøgle meldes det eksplicit — ikke som «rent»."""
    email = str(args.get("email") or "").strip()
    if not email or "@" not in email:
        return {"status": "error", "error": "gyldig email er påkrævet"}

    noegle = _runtime_key("hibp_api_key")
    if not noegle:
        return {
            "status": "no_key",
            "email": email,
            "error": "ingen hibp_api_key i runtime.json",
            "gratis_vej": ("Slå adressen op på haveibeenpwned.com — hele svaret "
                           "kommer uden konto og uden nøgle. Nøglen er kun til "
                           "automatiske opslag herfra."),
            "note": ("Opslaget blev IKKE udført. Det betyder ikke at adressen er ren."),
        }

    try:
        import httpx
        r = httpx.get(_ACCOUNT_URL + email,
                      headers={"User-Agent": _USER_AGENT, "hibp-api-key": noegle},
                      params={"truncateResponse": "false"},
                      timeout=_TIMEOUT)
    except Exception as exc:
        logger.warning("HIBP-kontoopslag fejlede: %s", exc)
        return {"status": "error", "error": f"opslag fejlede: {exc}",
                "note": "Intet svar — status ikke afgjort."}

    if r.status_code == 404:
        # 404 er HIBPs svar på «ingen brud», ikke en fejl.
        return {"status": "ok", "breached": False, "count": 0, "email": email,
                "breaches": [], "note": "Adressen findes ikke i nogen kendt lækage."}
    if r.status_code == 401:
        return {"status": "error", "error": "nøglen blev afvist (401)",
                "note": "Nøglen kan være udløbet eller forkert."}
    if r.status_code == 429:
        return {"status": "error", "error": "rate-limit (429)",
                "note": "HIBP kræver ~1,5 sek mellem kald. Prøv igen."}
    if r.status_code != 200:
        return {"status": "error", "error": f"HIBP svarede HTTP {r.status_code}"}

    try:
        data = r.json()
    except ValueError as exc:
        logger.warning("HIBP-svaret var ikke JSON: %s", exc)
        return {"status": "error", "error": "svaret var ikke JSON"}

    if not isinstance(data, list):
        return {"status": "error", "error": "uventet svarform fra HIBP"}

    brud = [{
        "name": b.get("Name"),
        "title": b.get("Title"),
        "date": b.get("BreachDate"),
        "data_classes": b.get("DataClasses") or [],
        "pwn_count": b.get("PwnCount"),
        "sensitive": bool(b.get("IsSensitive")),
    } for b in data if isinstance(b, dict)]

    return {"status": "ok", "breached": True, "count": len(brud),
            "email": email, "breaches": brud}


BREACH_CHECK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "check_password_breach",
        "description": (
            "Tjek om et password er set i en kendt lækage — uden at passwordet "
            "forlader maskinen. Bruger k-anonymitet: kun de første fem tegn af "
            "SHA-1-hashen sendes, resten sammenlignes lokalt. Kræver ingen API-nøgle. "
            "Foretræk sha1_hash hvis passwordet ikke skal stå i klartekst i "
            "værktøjskaldet (argumenter gemmes i tool-results)."
        ),
        "parameters": {"type": "object", "properties": {
            "password": {"type": "string",
                         "description": "Password i klartekst — hashes straks lokalt og returneres aldrig"},
            "sha1_hash": {"type": "string",
                          "description": "Alternativ: 40-tegns SHA-1 hex, hvis du har hashet selv (sikrest)"},
        }, "required": []},
    }},
    {"type": "function", "function": {
        "name": "check_email_breach",
        "description": (
            "Slå en email op i HaveIBeenPwned: hvilke brud, hvornår, hvilke "
            "dataklasser. Kræver betalt API-nøgle (hibp_api_key). Uden nøgle "
            "returneres status=no_key — det betyder IKKE at adressen er ren, "
            "og svaret henviser til det gratis opslag på haveibeenpwned.com."
        ),
        "parameters": {"type": "object", "properties": {
            "email": {"type": "string", "description": "Emailadresse der skal slås op"},
        }, "required": ["email"]},
    }},
]

BREACH_CHECK_TOOL_HANDLERS: dict[str, Any] = {
    "check_password_breach": _exec_check_password_breach,
    "check_email_breach": _exec_check_email_breach,
}
