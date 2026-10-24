"""Shared scanner for multi-profile provider auth slots.

Auth profiles live at ``~/.jarvis-v2/auth/profiles/<profile>/providers/<provider>/``
(each provider dir holds credentials.json + state.json). Historically only the
"default" profile was used; this module discovers every profile whose
credentials are ready for a given provider, so each becomes its own provider slot.

Keyless providers (auth_kind == "none" or public proxies) get exactly one slot
regardless of how many profile directories exist — there is nothing per-profile
to authenticate.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path

from core.services.cheap_provider_runtime_adapters import (
    CHEAP_PROVIDER_DEFAULTS,
    provider_auth_ready,
)

logger = logging.getLogger(__name__)

try:  # public proxies are keyless regardless of CHEAP_PROVIDER_DEFAULTS
    from core.services.cheap_lane_balancer import _PUBLIC_PROXIES
except Exception:  # pragma: no cover - defensive fallback if import shape changes
    # Local mirror of the public-proxy set; membership alone marks keyless.
    _PUBLIC_PROXIES = frozenset({"ollamafreeapi", "arko", "opencode"})

# Extra keyless providers not necessarily in _PUBLIC_PROXIES.
_KEYLESS_EXTRA = frozenset({"pollinations", "ovhcloud"})

# Only REAL account profiles become extra slots: "default" + "account2"/"account3"/…
# Excludes backups (default.bak-*), single-provider/legacy profiles (groq, mistral,
# gemini, …) and OAuth profiles (codex, copilot). Multi-profile means multiple
# ACCOUNTS of the same providers — not per-provider or backup directories.
_ACCOUNT_PROFILE_RE = re.compile(r"^(default|account\d+)$")


def _is_account_profile(profile: str) -> bool:
    """True only for real account profiles (default, account2, account3, …)."""
    return bool(_ACCOUNT_PROFILE_RE.match(profile))

# Batch-snapshot af ALLE auth-slots (24/10-2026).
#
# MÅLT før dette: ét enkelt `_configured_cheap_candidates()`-kald kaldte
# `root.iterdir()` 39 gange for den SAMME mappe og `provider_auth_ready()` 30
# gange — 264,89 ms koldt, 30,50 ms varmt, 233 kandidater. Bygerne på 8011
# (peak 189 %, 60-sekunders rytme) forsvandt IKKE af en per-provider-lås, fordi
# de samtidige tråde ramte HVER SIN provider og derfor aldrig mødtes om den
# samme lås. Låsen var korrekt bygget til det forkerte mønster.
#
# Derfor: ÉT scan bygger hele billedet {provider: [profiles]}, og single-flight
# ligger omkring DET — ikke omkring hver provider. Prisen er serialisering, men
# den betales én gang per TTL for hele processen, ikke én gang per provider.
#
# Bevidst IKKE cached her: round-robin-rotationen og den adaptive sortering.
# De kører per kald i `cheap_provider_runtime_selection`, så en cache ikke kan
# fryse profil-rækkefølgen (50/50-splittet) eller forsinke cooldowns.
_SNAPSHOT: tuple[float, dict[str, list[str]]] | None = None
_TTL_SECONDS = 60.0

# Låsen holdes ALDRIG under I/O (24/10-2026).
#
# MÅLT: den første version holdt en almindelig `threading.Lock` gennem hele
# scanningen. `provider_auth_ready()` kan for `openai-codex` kalde
# `get_openai_bearer_token()` → `refresh_openai_access_token()` →
# `save_provider_credentials()` → `clear_cache()` → forsøge SAMME lås. En
# vellykket token-refresh ville derfor hænge permanent inde i scanningen.
# Reproduceret: `deadlock_reproduceret = True`. `openai-codex` er i
# CHEAP_PROVIDER_DEFAULTS med `auth_kind=oauth`, så stien er aktiv produktion.
#
# Løsningen er ikke en reentrant lås — den ville stadig holde låsen gennem
# netværks-I/O og stadig lade et igangværende scan overskrive en frisk
# invalidering med sit forældede resultat. I stedet:
#
#   * `_LOCK` holdes kun til at vælge en leder og til at publicere resultatet.
#   * Selve scanningen kører UDEN lås (I/O må aldrig serialiseres af den).
#   * `_GENERATION` tælles op ved hver invalidering; et scan publicerer kun
#     hvis generationen er uændret, ellers kasseres resultatet.
#   * `clear_cache()` tager aldrig `_LOCK` under I/O og kan derfor kaldes fra
#     en readiness-sti inde i et igangværende scan.
_LOCK = threading.Lock()
_GENERATION = 0
_SCAN_ACTIVE = False
_SCAN_DONE = threading.Event()
_WAIT_SECONDS = 30.0


def _copy(snapshot: dict[str, list[str]]) -> dict[str, list[str]]:
    """Returnér en frisk kopi — kaldere må ikke dele mutérbare cache-objekter."""
    return {p: list(v) for p, v in snapshot.items()}


def clear_cache() -> None:
    """Drop the auth snapshot (test helper + explicit invalidation).

    Kaldes af ``save_provider_credentials()`` og ``revoke_provider()`` i
    ``core.auth.profiles``, så en credential-ændring slår igennem straks i
    stedet for at vente på TTL-udløb — ellers kunne en tilbagekaldt nøgle
    ligge i cheap-puljen i op til et minut.

    Tager ALDRIG ``_LOCK``: denne funktion kaldes fra ``provider_auth_ready()``,
    som selv kaldes inde i et igangværende scan. En lås her ville låse hele
    auth-laget permanent (målt 24/10-2026). ``_GENERATION`` er nok — det
    igangværende scan ser den og undlader at publicere sit forældede resultat.
    """
    global _SNAPSHOT, _GENERATION
    _SNAPSHOT = None
    _GENERATION += 1


def _do_scan() -> dict[str, list[str]]:
    """Byg ``{provider: [ready profiles]}`` med ÉT mappe-scan. Ingen lås her.

    En enkelt defekt slot (fx korrupt JSON) udelades og logges — den må ikke
    blinde hele auth-laget for alle andre providers.
    """
    by_provider: dict[str, list[str]] = {}
    root = _profiles_root()
    try:
        profile_dirs = [p for p in root.iterdir() if p.is_dir()]
    except (FileNotFoundError, NotADirectoryError):
        profile_dirs = []

    for prof_dir in profile_dirs:
        profile = prof_dir.name
        if not _is_account_profile(profile):
            continue  # backups, single-provider og OAuth-mapper er ikke konti
        try:
            provider_dirs = [
                p for p in (prof_dir / "providers").iterdir() if p.is_dir()
            ]
        except (FileNotFoundError, NotADirectoryError):  # profil uden providers/-mappe
            continue
        for prov_dir in provider_dirs:
            provider = prov_dir.name
            if _is_keyless(provider):
                continue  # keyless får ["default"] uden fil-I/O
            try:
                klar = provider_auth_ready(provider=provider, auth_profile=profile)
            except Exception:
                logger.warning(
                    "auth_snapshot: readiness fejlede for %s/%s — slotten udelades",
                    provider,
                    profile,
                    exc_info=True,
                )
                continue
            if klar:
                by_provider.setdefault(provider, []).append(profile)
    return by_provider


def auth_snapshot() -> dict[str, list[str]]:
    """Scan alle auth-profilmapper ÉN gang → ``{provider: [ready profiles]}``.

    Single-flight: kun én tråd scanner; de øvrige venter og læser dens
    resultat. Låsen dækker kun leder-valget og publiceringen — aldrig I/O, så
    en credential-refresh inde i scanningen kan ikke låse auth-laget.

    Returnerer KOPIER: kaldere må ikke dele mutérbare cache-objekter.
    """
    global _SNAPSHOT, _SCAN_ACTIVE

    snap = _SNAPSHOT
    if snap is not None and snap[0] > time.time():
        return _copy(snap[1])

    while True:
        with _LOCK:
            snap = _SNAPSHOT
            if snap is not None and snap[0] > time.time():
                return _copy(snap[1])
            if not _SCAN_ACTIVE:
                _SCAN_ACTIVE = True
                _SCAN_DONE.clear()
                generation = _GENERATION
                leader = True
            else:
                leader = False

        if leader:
            break
        # En anden tråd scanner. Vent på den — med timeout, så en død leder
        # ikke hænger os permanent. Løkken samler op: enten er der nu et hit,
        # eller også bliver vi selv leder.
        _SCAN_DONE.wait(timeout=_WAIT_SECONDS)

    try:
        result = _do_scan()
        with _LOCK:
            # Publicér KUN hvis ingen invalidering skete undervejs. Ellers ville
            # vi overskrive et friskere billede med et forældet.
            if _GENERATION == generation:
                _SNAPSHOT = (time.time() + _TTL_SECONDS, result)
        return _copy(result)
    finally:
        with _LOCK:
            _SCAN_ACTIVE = False
        _SCAN_DONE.set()


def _profiles_root() -> Path:
    """Return the auth/profiles directory (honoring JARVIS_CONFIG_DIR)."""
    root = os.environ.get("JARVIS_CONFIG_DIR")
    base = Path(root) if root else Path.home() / ".jarvis-v2"
    return base / "auth" / "profiles"


def _is_keyless(provider: str) -> bool:
    """True if the provider needs no per-profile credentials.

    Keyless if its CHEAP_PROVIDER_DEFAULTS auth_kind is "none", OR it is a known
    public proxy / keyless extra. Public-proxy membership is sufficient on its
    own, so keyless providers don't require CHEAP_PROVIDER_DEFAULTS entries.
    """
    ak = str((CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("auth_kind") or "")
    if ak == "none":
        return True
    if ak in ("bearer", "api_key"):
        # Per-account API key required → NEVER keyless, even if listed as a public
        # proxy. opencode is in _PUBLIC_PROXIES but authenticates with real per-account
        # bearer keys (default + account2 on disk) — treating it keyless hid its
        # account2 key from the profile rotation. arko (runtime-key, shared) and the
        # auth_kind="none" proxies stay keyless.
        return False
    return provider in _PUBLIC_PROXIES or provider in _KEYLESS_EXTRA


def _sort_default_first(profiles: list[str]) -> list[str]:
    rest = sorted(p for p in profiles if p != "default")
    return (["default"] if "default" in profiles else []) + rest


def ready_profiles_for(provider: str) -> list[str]:
    """Return profiles with ready credentials for ``provider``.

    Result is sorted with "default" first, then the rest alphabetical. Served
    from the batch snapshot (``auth_snapshot``): one directory scan answers every
    provider, refreshed every 60 s or immediately after a credential change.
    Keyless providers always return exactly ["default"].
    """
    if _is_keyless(provider):
        return ["default"]

    ready = list(auth_snapshot().get(provider) or [])

    # Delt ejer-nøgle i runtime.json (HuggingFace, xkiro): der findes ingen
    # profil-mappe at scanne, så uden det her returneres [] og udbyderen kommer
    # ALDRIG i cheap-puljen. Målt 7/9-2026: xkiro var klar
    # (provider_auth_ready=True) og svarede på et direkte kald, men
    # `_configured_cheap_candidates` gav nul kandidater, fordi profil-listen var
    # tom. HuggingFace skjulte hullet, fordi den OGSÅ har profil-nøgler.
    #
    # Tredje sted den samme nøgle skal kendes — readiness, dispatch og her.
    # TILFØJES, erstatter ikke: en kortslutning her ville have fjernet
    # HuggingFaces `account2`, som findes som rigtig profil.
    if "default" not in ready:
        from core.services.cheap_provider_runtime_keys import has_runtime_owner_key
        if has_runtime_owner_key(provider):
            ready.append("default")

    return _sort_default_first(ready)
