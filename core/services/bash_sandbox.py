"""bwrap-indespærring om én bash-kommando. SLUKKET som standard.

Porteret fra jarvis-code 2026-09-06 (`jc_sandbox.wrap_bwrap`). Bjørn: med,
men off by default.

## Hvad den gør

Bygger en `bwrap`-argv der kører kommandoen med basis-OS'et read-only
(`/usr /bin /lib /lib64 /etc`), `/tmp` som tmpfs, og KUN arbejdsmappen plus
eventuelle ekstra rødder skrivbare. Stier udenfor er ikke bare beskyttede —
de er usynlige. Uden `allow_egress` får processen sit eget tomme
net-namespace, hvilket er det ægte gulv under egress-værnets regex: dét er
rådgivende, det her er OS-niveau.

Argv, ikke en shell-streng, så der ikke opstår et nyt citerings-hul.

## Hvorfor den er slukket

To grunde, og den anden er den vigtige.

1. **Et fængsel om bash ændrer hvad der VIRKER, ikke bare hvad der er
   tilladt.** Kommandoer der har fungeret i månedsvis begynder at fejle på
   stier de ikke længere kan se, og fejlen ligner ikke en tilladelsesfejl —
   den ligner at filen ikke findes. Derfor er den et bevidst valg pr.
   installation, ikke noget der bare glider ind med en deploy.

2. **Den dækker ikke den normale bash-vej.** Runtime kører bash i en
   PERSISTENT session, og et fængsel pr. kommando kan ikke lægges om en
   shell der bliver stående mellem kald. Indespærringen sidder på
   engangs-vejen. Et halvt dækkende lag der er tændt er værre end et der er
   slukket, for det giver en tryghed der ikke svarer til virkeligheden.

**Tilgængelighed (opdateret 6/9 kl. 11):** bubblewrap 0.9.0 er nu installeret
BEGGE steder — workstationen og CT105 — og verificeret virksom i containeren
(user namespaces er åbne i den LXC, og `/media` er usynlig indefra). Den
tidligere note om at bwrap manglede på CT105 er dermed forældet. Laget fejler
stadig åbent hvis binæren forsvinder: en manglende mekanisme må ikke gøre
bash ubrugelig.

Flaget læses RÅT, ikke via `central_switches.is_enabled` — den defaulter til
ON når den er usat, og det er den forkerte vej rundt for det her.
"""
from __future__ import annotations

from dataclasses import dataclass

import logging
import shutil
from typing import Any

logger = logging.getLogger(__name__)

_SWITCH_SCOPE = "sandbox"
_SWITCH_NAME = "bash_bwrap"

# `/opt` kom til 10/9-2026. Uden den fandtes `/opt/conda` ikke inde i
# sandkassen, og HVERT script i huset koerer gennem
# `/opt/conda/envs/ai/bin/python`. Maalt ved at taende sandkassen paa CT105 og
# spoerge: `ls /opt/conda` → «No such file or directory». Indespaerringen
# rapporterede korrekt `honored=True` — den var bare ubrugelig.
_RO_ROEDDER = ("/usr", "/bin", "/lib", "/lib64", "/etc", "/opt")


def _runtime_hjem() -> str | None:
    """Jarvis' runtime-hjem, hvis det findes.

    Bindes SKRIVBART. Uden det kunne en indespaerret kommando ikke se
    `~/.jarvis-v2` overhovedet — hverken databasen, tilstanden eller
    hukommelsen — og engangs-stien kunne stort set intet nyttigt.

    Det svaekker sandkassen bevidst: den beskytter mod skade paa RESTEN af
    maskinen, ikke mod at Jarvis roerer sit eget hjem. Havde vi ladet det vaere
    ude, ville vaernet vaere blevet slaaet fra i stedet — og et vaern ingen
    taender, beskytter intet.
    """
    try:
        from core.runtime.config import JARVIS_HOME
        return str(JARVIS_HOME) if JARVIS_HOME.exists() else None
    except Exception:
        return None


def is_available() -> bool:
    """Findes bwrap på DENNE maskine?"""
    return shutil.which("bwrap") is not None


def is_enabled() -> bool:
    """Eksplicit tændt? Usat betyder SLUKKET — modsat central_switches' default."""
    try:
        from core.services import shared_cache
        val = shared_cache.get(f"flag:central.switch.{_SWITCH_SCOPE}.{_SWITCH_NAME}")
    except Exception:
        return False  # fail-closed mod at TÆNDE: et ukendt flag tænder intet
    return bool(isinstance(val, dict) and val.get("enabled") is True)


def set_enabled(on: bool) -> dict[str, Any]:
    from core.services import central_switches
    from core.services.gate_kernel import GateClass
    return central_switches.set_enabled(_SWITCH_SCOPE, _SWITCH_NAME, bool(on),
                                        klass=GateClass.COGNITIVE)


def status() -> dict[str, Any]:
    tilgaengelig = is_available()
    taendt = is_enabled()
    return {
        "status": "ok",
        "tændt": taendt,
        "bwrap_findes": tilgaengelig,
        "aktiv": taendt and tilgaengelig,
        "note": ("aktiv" if (taendt and tilgaengelig) else
                 "tændt, men bwrap findes ikke på denne maskine — kører uindespærret"
                 if taendt else "slukket (standard)"),
    }


def wrap_bwrap(command: str, cwd: str, *, writable_roots: list[str] | None = None,
               allow_egress: bool = True) -> list[str]:
    """Byg argv'en. Ren funktion — tjekker hverken flag eller tilgængelighed."""
    argv: list[str] = ["bwrap"]
    for ro in _RO_ROEDDER:
        argv += ["--ro-bind-try", ro, ro]
    argv += ["--tmpfs", "/tmp", "--dev", "/dev", "--proc", "/proc"]
    # cwd bindes EFTER --tmpfs /tmp, saa en cwd der selv ligger under /tmp
    # ikke skygges af tmpfs-mountet. bwrap anvender mounts i raekkefoelge.
    argv += ["--bind", cwd, cwd]
    _bundet = {cwd}
    _hjem = _runtime_hjem()
    if _hjem and _hjem not in _bundet:
        argv += ["--bind", _hjem, _hjem]
        _bundet.add(_hjem)
    for rod in (writable_roots or []):
        if rod not in _bundet:
            argv += ["--bind", rod, rod]
            _bundet.add(rod)
    argv += ["--unshare-all"]
    if allow_egress:
        argv += ["--share-net"]
    argv += ["--die-with-parent", "--chdir", cwd, "sh", "-c", command]
    return argv


def maybe_wrap(command: str, cwd: str, *, writable_roots: list[str] | None = None,
               allow_egress: bool = True) -> list[str] | None:
    """argv hvis sandboxen er tændt OG mulig her — ellers None (kør normalt).

    None betyder «ikke min sag». Fail-open er med vilje: en manglende
    mekanisme må ikke gøre bash ubrugelig, og den fejlklasse vi beskytter mod
    er en kommando der rører for meget — ikke en angriber med kodeadgang.
    """
    if not command or not cwd:
        return None
    if not is_enabled():
        return None
    if not is_available():
        logger.warning("bash_sandbox: tændt, men bwrap findes ikke — kører uindespærret")
        return None
    return wrap_bwrap(command, cwd, writable_roots=writable_roots,
                      allow_egress=allow_egress)


# ── ønsket vs. FAKTISK indespærring ──────────────────────────────────────
#
# Spec, Fase 3 K9: «every process-producing provider reports requested policy
# and actual enforcement; requested confinement fails before execution when
# unavailable».
#
# Kriteriet kolliderer med en beslutning der allerede er truffet ovenfor:
# `maybe_wrap` fejler ÅBENT med vilje, fordi «en manglende mekanisme må ikke
# gøre bash ubrugelig». Den beslutning omgøres ikke her.
#
# I stedet skilles de to spørgsmål ad, ligesom `permission_axes` skiller profil
# fra tilstand:
#
#   RAPPORTERING  — hvad blev bedt om, og hvad skete der? Altid, uanset udfald.
#   HÅNDHÆVELSE   — skal et manglende fængsel STOPPE kaldet? Kalderens valg.
#
# Uden det første kan man ikke vide om en kommando kørte indespærret. Uden det
# andet kan man ikke kræve det. De er ikke det samme spørgsmål.


class ConfinementUnavailable(RuntimeError):
    """Der blev KRÆVET indespærring, og den kunne ikke leveres."""


@dataclass(frozen=True)
class Enforcement:
    """Hvad der blev bedt om, og hvad der faktisk skete."""

    requested: bool          # skulle kommandoen indespærres?
    actual: bool             # BLEV den det?
    available: bool          # findes bwrap her?
    enabled: bool            # er kontakten tændt?
    argv: list[str] | None = None
    reason: str = ""

    @property
    def honored(self) -> bool:
        """Fik vi det vi bad om?"""
        return self.requested == self.actual

    def as_dict(self) -> dict[str, Any]:
        return {"requested": self.requested, "actual": self.actual,
                "available": self.available, "enabled": self.enabled,
                "honored": self.honored, "reason": self.reason}


def enforcement(command: str, cwd: str, *, writable_roots: list[str] | None = None,
                allow_egress: bool = True, require: bool = False) -> Enforcement:
    """Afgør indespærringen OG rapportér den. Kaster kun når `require` er sat.

    `require=True` er den eneste vej til fail-CLOSED. Standarden er uændret
    fail-open, så eksisterende kaldere opfører sig præcis som før.
    """
    tilgaengelig = is_available()
    taendt = is_enabled()
    oensket = bool(taendt) and bool(command) and bool(cwd)

    if not oensket:
        grund = "ikke tændt" if not taendt else "manglende kommando eller cwd"
        e = Enforcement(False, False, tilgaengelig, taendt, None, grund)
    elif not tilgaengelig:
        e = Enforcement(True, False, False, taendt, None,
                        "bwrap findes ikke på denne maskine")
    else:
        argv = wrap_bwrap(command, cwd, writable_roots=writable_roots,
                          allow_egress=allow_egress)
        e = Enforcement(True, True, True, taendt, argv, "")

    if not e.honored:
        # Aldrig tavst: en kommando der kører uindespærret mens nogen troede
        # den var spærret inde, er præcis den forskel der ikke må forsvinde.
        logger.warning("bash_sandbox: ØNSKET indespærring blev IKKE håndhævet "
                       "(%s) — kommandoen kører frit", e.reason)

    if require and not e.actual:
        # FØR eksekvering, ikke efter: en fejl bagefter er en kommando der
        # allerede er kørt.
        raise ConfinementUnavailable(
            f"indespærring blev krævet, men kunne ikke leveres: {e.reason}")
    return e
