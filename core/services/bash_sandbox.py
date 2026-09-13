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
import pathlib
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


def _conda_rod(sti: pathlib.Path) -> pathlib.Path | None:
    """Base-installationen bag et conda-env: `<rod>/envs/<navn>` → `<rod>`.

    Env'et laener sig paa delte biblioteker i basen, saa env'et alene raekker
    ikke altid.
    """
    dele = sti.parts
    if "envs" in dele:
        return pathlib.Path(*dele[:dele.index("envs")])
    return None


def _python_roedder() -> list[str]:
    """Tolkens EGEN rod — oploest gennem symlinks.

    `/opt` alene raakker ikke. Paa CT105 er `/opt/conda/envs/ai/bin/python` et
    symlink ind i `/home/bs/miniconda3`, og en read-only binding af `/opt`
    tager symlinket med men ikke dets maal — kommandoen doer med exit 127
    «not found». Lokalt er `/opt/conda` et rigtigt trae, saa det bestod hos mig
    og fejlede paa maskinen. Derfor bindes den OPLOESTE sti.
    """
    ud: list[str] = []
    try:
        import sys as _sys
        for raa in (_sys.prefix, _sys.base_prefix):
            if not raa:
                continue
            sti = pathlib.Path(raa).resolve()
            for kandidat in (sti, _conda_rod(sti)):
                if kandidat is None:
                    continue
                if kandidat.exists() and str(kandidat) not in ud:
                    ud.append(str(kandidat))
    except Exception:
        return []
    return ud


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
    """Findes bwrap på DENNE maskine?

    ATTEN: «findes» er ikke «virker». Se `kan_koere()` — en bwrap der ligger
    paa PATH kan naegte at starte, og denne funktion siger stadig True.
    """
    return shutil.which("bwrap") is not None


#: (tidspunkt, resultat, grund) for sidste aegte proeve. En exec pr. opslag
#: ville vaere for dyrt; en proeve der aldrig gentages ville aldrig opdage at
#: konfigurationen blev rettet.
_KAN_KOERE_CACHE: tuple[float, bool, str] | None = None
_KAN_KOERE_TTL_S = 300.0


def kan_koere(*, tving: bool = False) -> tuple[bool, str]:
    """Kan bwrap FAKTISK starte her? (svar, grund)

    ## Hvorfor det ikke er det samme som `is_available()`

    Maalt paa runtime 13/9-2026. `which("bwrap")` gav `/usr/bin/bwrap`, og
    baade `is_enabled()` og `is_available()` sagde True — men hvert eneste
    kald fejlede:

        bwrap: Unexpected capabilities but not setuid, old file caps config?

    Aarsagen er en kollision mellem to ting der hver for sig er rigtige:
    `jarvis-runtime.service` saetter `AmbientCapabilities=CAP_SETUID CAP_SETGID`,
    og ambient capabilities arves ind i ETHVERT barn — ogsaa bwrap. Bubblewrap
    naegter bevidst at koere med capabilities uden at vaere setuid; det er
    bwraps egen sikkerhedsvagt, ikke en fejl (containers/bubblewrap#380).

    Reproduceret med `systemd-run --uid=bs` og de samme ambient caps: exit 1 og
    ordret samme streng. Uden dem: exit 0. Servicen koerer som `bs`, ikke som
    root — en proeve som root ville vaere groen og bevise intet, og det var
    praecis fejlen i de to foerste forsoeg paa at reproducere.

    ## Hvorfor en aegte exec

    Der findes ingen maade at udlede svaret af konfigurationen. Det afhaenger
    af den arvede capability-maske, af binaerens file caps, og af brugeren. Et
    gaet ville vaere den slags «anmodet forklaedt som faktisk» der lod fejlen
    staa uopdaget i foerste omgang.

    Resultatet caches i 5 minutter: en exec pr. opslag er for dyrt, og en
    proeve der aldrig gentages ville aldrig opdage at nogen rettede unit-filen.
    """
    global _KAN_KOERE_CACHE
    import subprocess
    import time as _t

    # «Findes den overhovedet» spoerges FOER cachen, og gennem modulets egen
    # `is_available()` — ikke `shutil.which` direkte.
    #
    # To grunde, og begge kostede mig en roed test:
    #   * Gaar man uden om `is_available()`, kan den ikke laengere bruges til
    #     at simulere en maskine uden bwrap, og fire eksisterende tests der
    #     koder en RIGTIG kontrakt («taendt men umuligt = uopfyldt oenske»)
    #     holdt op med at maale noget.
    #   * Ligger tjekket EFTER cachen, kan en gemt `True` skjule at binaeren
    #     er forsvundet. Et which-opslag er billigt; det skal ikke caches.
    if not is_available():
        return False, "bwrap findes ikke paa PATH"

    if not tving and _KAN_KOERE_CACHE is not None:
        tid, svar, grund = _KAN_KOERE_CACHE
        if _t.monotonic() - tid < _KAN_KOERE_TTL_S:
            return svar, grund

    sti = shutil.which("bwrap")
    if not sti:
        resultat = (False, "bwrap findes ikke paa PATH")
    else:
        try:
            p = subprocess.run(
                [sti, "--ro-bind", "/", "/", "--dev", "/dev", "/bin/true"],
                capture_output=True, text=True, timeout=5.0,
            )
            if p.returncode == 0:
                resultat = (True, "proevet")
            else:
                fejl = (p.stderr or p.stdout or "").strip().splitlines()
                resultat = (False, fejl[0] if fejl else f"exit {p.returncode}")
        except Exception as e:
            resultat = (False, f"{type(e).__name__}: {e}")

    _KAN_KOERE_CACHE = (_t.monotonic(), resultat[0], resultat[1])
    return resultat


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
    """Tilstanden — og «findes» holdes adskilt fra «kører».

    Maalt 13/9-2026: denne funktion meldte `aktiv: True` paa en maskine hvor
    hvert eneste bwrap-kald fejlede. `bwrap_findes` var sandt, og «findes» blev
    laest som «virker».
    """
    findes = is_available()
    taendt = is_enabled()
    koerer, grund = kan_koere()
    return {
        "status": "ok",
        "tændt": taendt,
        "bwrap_findes": findes,
        # NY: den aegte proeve. `bwrap_findes` beholdes, fordi de to svar er
        # forskellige og begge er brugbare — en manglende binaer og en binaer
        # der naegter at starte kraever hver sin handling.
        "bwrap_kører": koerer,
        "bwrap_grund": grund,
        "aktiv": taendt and koerer,
        "note": ("aktiv" if (taendt and koerer) else
                 "slukket (standard)" if not taendt else
                 "tændt, men bwrap findes ikke på denne maskine — kører uindespærret"
                 if not findes else
                 f"tændt, men bwrap kan ikke starte ({grund}) — kører uindespærret"),
    }


def wrap_bwrap(command: str, cwd: str, *, writable_roots: list[str] | None = None,
               allow_egress: bool = True) -> list[str]:
    """Byg argv'en. Ren funktion — tjekker hverken flag eller tilgængelighed."""
    argv: list[str] = ["bwrap"]
    for ro in list(_RO_ROEDDER) + _python_roedder():
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
    # «Findes» daekker ikke «kan starte». Fandtes bwrap men naegtede at koere,
    # blev kommandoen alligevel pakket ind — og HVERT bash-kald doede.
    #
    # Maalt 13/9-2026: ambient capabilities fra unit-filen arves ind i bwrap,
    # og bwrap afviser bevidst at koere med capabilities uden at vaere setuid.
    # Resultatet var ikke en indespaerret bash, men INGEN bash.
    #
    # Fail-open er modulets egen dokumenterede adfaerd her (`require=True` er
    # den eneste vej til fail-closed), saa dette fjerner ingen beskyttelse der
    # fandtes — det bytter «intet virker og intet er indespaerret» ud med
    # «det virker, uindespaerret, og loggen siger det».
    _kan, _grund = kan_koere()
    if not _kan:
        logger.warning("bash_sandbox: tændt, men bwrap kan ikke starte (%s) — "
                       "kører uindespærret", _grund)
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
    # K9 siger «actual enforcement». `is_available()` er `which("bwrap")` og
    # svarer paa noget andet: at binaeren ligger der. Mekanismen til at
    # rapportere faktisk haandhaevelse har vaeret her siden Fase 3 — den maalte
    # bare et stedfortraeder-tal. Maalt 13/9-2026 rapporterede den haandhaevelse
    # paa en maskine hvor bwrap afviste hvert kald.
    brugbar, brugbar_grund = kan_koere()
    findes = is_available()          # `available` BETYDER «findes» — feltet
                                     # beholder sin mening, det er `actual` der
                                     # skal rette sig efter virkeligheden.
    taendt = is_enabled()
    oensket = bool(taendt) and bool(command) and bool(cwd)

    if not oensket:
        grund = "ikke tændt" if not taendt else "manglende kommando eller cwd"
        e = Enforcement(False, False, findes, taendt, None, grund)
    elif not brugbar:
        e = Enforcement(True, False, findes, taendt, None,
                        "bwrap findes ikke på denne maskine" if not findes
                        else f"bwrap kan ikke starte: {brugbar_grund}")
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
