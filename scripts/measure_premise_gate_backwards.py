"""Bagudrettet maaling: ville en praemis-gate have fanget aftenens tre fejl?

SPOERGSMAALET (23/11-2026). Tre semantiske fejl gik igennem 131 groenne tests,
en groen auto_code_review-gate og alle commit-hooks. Foer jeg bygger en ny
mekanisme, maaler jeg om en praemis-gate overhovedet VILLE have fanget dem —
og om reglen kan formuleres uden at kende svaret paa forhaand.

DE TRE FEJL (alle samme form: en paastand om hvad et tal BETYDER, fremsat i
commit-beskeden, aldrig efterproevet mod datakilden):

  1. 8d62d8102  carried_integrity = 1 - mean(decay) over ALLE poster.
                Beskeden sagde «integritet 0.493 ... praecis i fading-baandet»
                som BEVIS. Tallet maalte soma-telemetri, ikke baerende indhold.

  2. 73a241569  mekanikken blev beregnet men skrevet til ingen log.
                Beskeden sagde «mekanikken er verificeret» — den var beregnet.

  3. 60645bdfc  filtreringen kom EFTER fejl 1 var «verificeret».
                Beskeden sagde «kun baerende poster» — uden at maale fordelingen.

REGEL-FORMEN jeg maaler (deterministisk, ingen LLM):
  En commit der tilfoejer en NY maale-funktion (def ...integrity|score|rate|
  intensity...) OG hvis besked indeholder et TAL som bevis, skal ogsaa
  indeholde en fordeling eller en eksklusions-begrundelse — ellers er tallet
  ikke efterproevet mod sin egen datakilde.

MAALT RESULTAT (23/11-2026, koert mod de tre faktiske commits):
  Den foerste regel fangede 1 af 3 — og det var fejl 1, ikke fejl 2/3.
  Fejl 3's besked INDEHOLDER en fordeling, fordi den blev skrevet efter
  lektien — reglen kan ikke skelne «jeg maalte fordelingen» fra «jeg skrev
  ordet fordeling».
  Skarpere variant A (kraev datakilde navngivet): alle tre navngiver en
  kilde — ogsaa fejl 1, der pegede paa den FORKERTE. Blind.
  Skarpere variant B (kraev eksklusions-liste i kode): nul af tre. Blind.
  Advarsels-variant (enhver maale-funktion + tal): 2 af 3, men fyrer paa ALT
  der roerer en maaling — stoj, ikke signal.

KONKLUSION: en deterministisk praemis-gate kan IKKE bygges. Den kan ikke
skelne en rigtig maaling fra en forkert, fordi begge skriver de samme ord.
Det der faktisk fangede fejlene var en LASER der kendte datakilden — ikke en
regel. Byg den ikke som gate; spoergsmaalet hoerer i en samtale, ikke i en
regex.

Kør: python scripts/measure_premise_gate_backwards.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: De tre commits fra 23/11-2026, i den raekkefoelge de blev lavet.
#: Git-hasher, ikke noegler — detect-secrets ser hex og spoerger.
COMMITS = [
    ("8d62d8102", "fejl 1: globalt gennemsnit over alle poster"),  # pragma: allowlist secret
    ("73a241569", "fejl 2: mekanik uden log-spor"),  # pragma: allowlist secret
    ("60645bdfc", "fejl 3: filtrering efter 'verificeret'"),  # pragma: allowlist secret
]

#: En ny maale-funktion — navnet baerer at den udleder en stoerrelse.
_MAALEFUNK = re.compile(
    r"^\+\s*def\s+(\w*(?:integrity|score|rate|intensity|level|weight)\w*)\s*\(",
    re.MULTILINE,
)

#: Et tal i beskeden der fremstilles som bevis (procent eller decimal).
_BEVIS_TAL = re.compile(r"\b\d+[.,]\d+\b|\b\d+\s*(?:af|/)\s*\d+\b")

#: En fordeling eller eksklusions-begrundelse — det der goer tallet efterproevet.
_FORDELING = re.compile(
    r"fordel|fordelt|blandt|af de \d+|kun \w+ poster|eksklud|filtrer|"
    r"top \d+|praefiks|kilde-fordeling|ud af \d+",
    re.IGNORECASE,
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout


def maal_commit(sha: str, label: str) -> dict[str, object]:
    """Koer praemis-reglen mod én commit og svar om den ville have fyret."""
    besked = _git("log", "-1", "--format=%B", sha)
    diff = _git("show", sha, "--unified=0")

    nye_maalefunktioner = sorted(set(_MAALEFUNK.findall(diff)))
    bevis_tal = _BEVIS_TAL.findall(besked)
    har_fordeling = bool(_FORDELING.search(besked))

    # Reglen: ny maale-funktion + bevis-tal i beskeden + ingen fordeling => FYR.
    fyrer = bool(nye_maalefunktioner) and bool(bevis_tal) and not har_fordeling

    return {
        "sha": sha,
        "label": label,
        "nye_maalefunktioner": nye_maalefunktioner,
        "bevis_tal": bevis_tal[:6],
        "har_fordeling": har_fordeling,
        "fyrer": fyrer,
    }


def main() -> int:
    print("=== BAGUDRETTET MAALING: praemis-gate mod aftenens tre fejl ===\n")
    resultater = [maal_commit(sha, label) for sha, label in COMMITS]

    fanget = 0
    for r in resultater:
        status = "FYRER  " if r["fyrer"] else "TAVS    "
        if r["fyrer"]:
            fanget += 1
        print(f"{status} {r['sha']}  {r['label']}")
        print(f"         nye maale-funktioner: {r['nye_maalefunktioner'] or '(ingen)'}")
        print(f"         bevis-tal i beskeden: {r['bevis_tal'] or '(ingen)'}")
        print(f"         fordeling/eksklusion: {r['har_fordeling']}")
        print()

    print(f"=== RESULTAT: reglen fangede {fanget} af {len(resultater)} ===")
    if fanget == len(resultater):
        print("Reglen daekker alle tre. Den kan formuleres uden at kende svaret.")
    elif fanget:
        print("Reglen daekker NOGLE. Delvis — ikke nok til at bygge den som gate.")
    else:
        print("Reglen fanger INGEN. Idéen er forkert — byg den ikke.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
