"""Dommer over drømme-hypoteser: hvad skal videre fra drømme-stadiet?

Bjørn 8/9-2026: «drømme hypoteser bør der være en slags dommer på som kan
vurdere hvilke skal videre fra drømme stadiet» — og «sørg for det er faktisk
hypoteser».

## Hvorfor den dømmer markdown og ikke en tabel

Der er TRE hypotese-strømme, og kun én indeholder tænkning:

* ``runtime_dream_hypothesis_signals`` (37 aktive) er Bjørns EGNE beskeder i én
  fast sætning — «Dream hypothesis: jarvis ssh?». En skabelon, ikke en
  generator.
* ``central_hypotheses`` med ``source='oneiric_loop'`` (47) er den samme
  bias-skabelon med skiftende tal, «Nattens drøm satte loop_persistence +0.60».
  22 af 23 aktive har NUL samples.
* ``~/dreams/hypothesis-candidate-*.md`` er den ægte tænkning: konfidens,
  carry-tæller, testbar forudsigelse, forbindelser og en risiko-sektion der
  overvejer sin egen selv-bekræftelse.

En dommer over de to første ville dømme støj. Denne dømmer den tredje.

## To spørgsmål, i den rækkefølge

**1. Er det overhovedet en hypotese?** Bjørns eksplicitte krav. En hypotese
gør en påstand der KAN vise sig falsk. En observation, en idé eller en
stemningsbeskrivelse kan ikke, uanset hvor godt den er skrevet. Kun ~5 af
sektionerne i korpuset bærer et eksplicit test-felt, så spørgsmålet kan ikke
afgøres på feltnavne — teksten skal læses.

**2. Skal den videre?** Først dér spørger vi om modenhed: er den båret over
flere sessioner, er den blevet angrebet, står der en konklusion.

Rækkefølgen er ikke tilfældig. Uden det første spørgsmål ville dommeren
forfremme velformulerede stemningsbilleder.

## Hvad «videre» betyder

En forfremmet hypotese skrives i ``central_hypotheses`` — tabellen med
samples, falsifikations-kriterium og livscyklus. Dér kan den blive testet og
dø. Det er forskellen på at være skrevet ned og at være i spil.

Dommeren er den samme lokale model som nudge-gaten og Smiths veto: den fejler
LUKKET. Ingen dom → ingen forfremmelse. En hypotese der bliver i drømmen én
runde mere koster ingenting; én der forfremmes uden at være en hypotese
forurener tabellen med 74.000 rækker.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DRØMME_MAPPE = Path.home() / "dreams"
_FILMØNSTER = "hypothesis-candidate-*.md"

# Feltnavne varierer over korpuset (43 filer, dansk og engelsk imellem
# hinanden). Målt: Confidence 11 · Konfidens 9 · Hypotese 10 · Titel 8 ·
# Udsagn 1 · Testbar implikation 3 · Testbar forudsigelse 1 · Test 1.
_KONFIDENS = re.compile(
    r"\*\*(?:confidence|konfidens)\s*:?\*\*\s*:?\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
_CARRY = re.compile(r"\*\*carry\s*:?\*\*\s*:?\s*(\d+)", re.IGNORECASE)
_KONKLUSION = re.compile(r"\*\*konklusion\s*:?\*\*\s*:?\s*(.+)", re.IGNORECASE)
_AFVIST = re.compile(r"\bafvis\b|\bafvist\b|\bforkast", re.IGNORECASE)


@dataclass
class Kandidat:
    """Én ``## sektion`` fra en kandidat-fil."""

    navn: str
    tekst: str
    fil: str
    konfidens: float | None = None
    carry: int | None = None
    konklusion: str = ""
    fingeraftryk: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        # Felterne udtraekkes HER, ikke i parseren. Foer laa udtraekket i
        # ``_parse_fil``, saa en Kandidat bygget paa anden vis — i en test, i
        # en fremtidig kalder — var halvtom og saa ud til ikke at have en
        # konklusion. En test fangede det.
        if self.konfidens is None:
            m = _KONFIDENS.search(self.tekst)
            self.konfidens = float(m.group(1)) if m else None
        if self.carry is None:
            m = _CARRY.search(self.tekst)
            self.carry = int(m.group(1)) if m else None
        if not self.konklusion:
            m = _KONKLUSION.search(self.tekst)
            self.konklusion = m.group(1).strip() if m else ""
        if not self.fingeraftryk:
            self.fingeraftryk = hashlib.sha1(  # noqa: S324 - dedup, ikke sikkerhed
                self.navn.strip().lower().encode()
            ).hexdigest()[:16]

    @property
    def selv_afvist(self) -> bool:
        """Han har allerede dømt den i selve artefaktet.

        «**Konklusion:** Afvis adoption. Behold som eksempel på hvordan
        drømmesystemet producerer smukke hypoteser der føles sande uden at
        være det.» — den dom skal ikke overprøves af en model.
        """
        return bool(self.konklusion and _AFVIST.search(self.konklusion))


def _parse_fil(sti: Path) -> list[Kandidat]:
    try:
        raa = sti.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.debug("dream_hypothesis_judge: kunne ikke læse %s: %s", sti, exc)
        return []

    ud: list[Kandidat] = []
    # Sektioner er «## navn» indtil næste «## » eller «---».
    for blok in re.split(r"\n---+\n", raa):
        m = re.search(r"^##\s+(.+?)\s*$", blok, re.MULTILINE)
        if not m:
            continue
        krop = blok[m.end():].strip()
        if len(krop) < 40:
            continue        # en overskrift uden indhold er ikke en kandidat
        ud.append(Kandidat(navn=m.group(1).strip(), tekst=krop, fil=sti.name))
    return ud


def laes_kandidater(mappe: Path | None = None) -> list[Kandidat]:
    """Alle hypotese-kandidater fra drømme-mappen, nyeste fil først."""
    rod = mappe or DRØMME_MAPPE
    try:
        filer = sorted(rod.glob(_FILMØNSTER), reverse=True)
    except Exception as exc:
        logger.debug("dream_hypothesis_judge: kunne ikke liste %s: %s", rod, exc)
        return []
    ud: list[Kandidat] = []
    for f in filer:
        ud.extend(_parse_fil(f))
    return ud


# ── porten før modellen: siger den hvad der ville vise den forkert? ─────────
#
# Målt på korpuset: 10 af 26 kandidater bærer en falsificerbar formulering.
# Uden dette krav sagde modellen FREMFOER til 24 af 26 — den er medgørlig, og
# et velformuleret stemningsbillede lyder som en hypotese hvis man kun spørger
# «er det en hypotese?».
#
# Kravet ER standarden Bjørn bad om: kan noten ikke sige hvad der ville vise
# den forkert, er den ikke færdig som hypotese. Den bliver i drømmen — hvor
# den kan skærpes — i stedet for at blive skrevet ind i en tabel med 74.000
# rækker som noget der kan testes.
_FALSIFICERBAR = re.compile(
    r"\*\*(?:test|testbar[^*:]*|forudsig[^*:]*|prediction|falsifik[^*:]*)\s*:?\*\*"
    r"|\bhvis\b[^.]{0,120}\b(vil|ville|forudsiger|burde|skulle)\b"
    r"|\bforudsiger jeg\b|\bfalsifik",
    re.IGNORECASE,
)


def siger_hvad_der_ville_modbevise_den(k: "Kandidat") -> bool:
    return bool(_FALSIFICERBAR.search(k.tekst))


# ── spørgsmål 1: er det en hypotese? ────────────────────────────────────────

_ER_HYPOTESE = (
    "Nedenfor står en note fra en AI-assistents droemmejournal.\n\n"
    "Afgoer ÉN ting: er det en HYPOTESE — en paastand om hvordan noget "
    "haenger sammen, som kunne vise sig at vaere FORKERT?\n\n"
    "Svar HYPOTESE hvis noten paastaar en aarsag, en mekanisme eller en "
    "sammenhaeng man kunne modbevise.\n"
    "Svar NOTE hvis den kun beskriver, observerer, stemningssaetter eller "
    "stiller et spoergsmaal — uanset hvor velformuleret den er.\n\n"
    "Svar med ét ord: HYPOTESE eller NOTE."
)

# ── spørgsmål 2: skal den videre? ───────────────────────────────────────────

_SKAL_VIDERE = (
    "Nedenfor staar en hypotese fra en AI-assistents droemmejournal. Den skal "
    "kun forlade droemmelaget hvis nogen KONKRET kunne afgoere den.\n\n"
    "Svar BEHOLD hvis noget af dette gaelder:\n"
    "- proeven kraever at maale en indre tilstand der ikke kan observeres udefra\n"
    "- hypotesen forklarer sin egen manglende testbarhed\n"
    "- den kan hverken bekraeftes eller afkraeftes af noget der kan taelles\n"
    "- den er en omformulering af en anden hypotese frem for en ny paastand\n\n"
    "Svar FREMFOER kun hvis man kunne skrive proeven ned i én saetning og vide "
    "hvad et nej ville se ud som.\n\n"
    "Svar med ét ord: FREMFOER eller BEHOLD."
)


def er_en_hypotese(k: Kandidat) -> bool:
    """Bjørns krav: «sørg for det er faktisk hypoteser».

    Fejler lukket — uden en dom er svaret nej.
    """
    try:
        from core.services.local_small_model import spoerg_et_ord
        return spoerg_et_ord(_ER_HYPOTESE, k.tekst[:1200]) == "HYPOTESE"
    except Exception as exc:
        logger.debug("dream_hypothesis_judge: hypotese-proeve fejlede: %s", exc)
        return False


def skal_videre(k: Kandidat) -> bool:
    try:
        from core.services.local_small_model import spoerg_et_ord
        return spoerg_et_ord(_SKAL_VIDERE, k.tekst[:1200]) == "FREMFOER"
    except Exception as exc:
        logger.debug("dream_hypothesis_judge: modenheds-proeve fejlede: %s", exc)
        return False


def doem(k: Kandidat) -> tuple[bool, str]:
    """``(forfrem, grund)``. Grunden logges, saa dommen kan efterproeves."""
    if k.selv_afvist:
        return False, "selv-afvist"
    if not siger_hvad_der_ville_modbevise_den(k):
        return False, "ingen falsifikation"
    if not er_en_hypotese(k):
        return False, "ikke en hypotese"
    if not skal_videre(k):
        return False, "ikke moden"
    return True, "fremfoert"


# ── forfremmelsen: fra markdown til noget der kan dø ────────────────────────

_AFSNIT = re.compile(
    r"\*\*(?P<navn>[^*:]{1,40})\s*:?\*\*\s*:?\s*(?P<krop>.+?)(?=\n\*\*|\n###|\n##|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_H3 = re.compile(r"^###\s+(?P<navn>.+?)\s*$\n(?P<krop>.*?)(?=\n###|\n##|\Z)",
                 re.MULTILINE | re.DOTALL)

_STANDARD_SAMPLES = 5
_STANDARD_TTL_S = 30 * 24 * 3600


def _afsnit(k: Kandidat) -> dict[str, str]:
    """Felter fra begge notations-former i korpuset: ``**Navn:**`` og ``### Navn``."""
    ud: dict[str, str] = {}
    for m in _AFSNIT.finditer(k.tekst):
        ud[m.group("navn").strip().lower()] = " ".join(m.group("krop").split())
    for m in _H3.finditer(k.tekst):
        ud.setdefault(m.group("navn").strip().lower(), " ".join(m.group("krop").split()))
    return ud


def _foerste(felter: dict[str, str], *navne: str) -> str:
    for n in navne:
        for nøgle, værdi in felter.items():
            if nøgle.startswith(n) and værdi:
                return værdi
    return ""


def byg_preregistrering(k: Kandidat) -> dict[str, object]:
    """Markdown → den form ``register_governed_hypothesis`` kræver.

    Nulhypotesen og succes-kriteriet UDLEDES mekanisk af forudsigelsen og
    mærkes som udledte. Alternativet var at lade modellen skrive dem, og en
    model der digter et falsifikations-kriterium ville gøre hypotesen
    *sværere* at modbevise — stik imod formålet.
    """
    f = _afsnit(k)
    paastand = _foerste(f, "hypotese", "udsagn", "mekanisme", "statement") or k.tekst[:400]
    forudsigelse = _foerste(f, "testbar", "test", "forudsig", "prediction", "implikation")
    if not forudsigelse:
        m = re.search(r"(hvis\b[^.]{0,240}\.)", k.tekst, re.IGNORECASE)
        forudsigelse = " ".join(m.group(1).split()) if m else ""
    return {
        "source": "dream_judge",
        "statement": paastand[:900],
        "prediction": forudsigelse[:900],
        "null_hypothesis": ("UDLEDT: forudsigelsen indtræffer ikke — "
                            "observationerne er uændrede når betingelsen er til stede."),
        "success_criterion": ("UDLEDT: mindst %d observationer der understøtter "
                              "forudsigelsen, uden lige så mange der modsiger den."
                              % _STANDARD_SAMPLES),
        "sample_size": _STANDARD_SAMPLES,
        "ttl_seconds": _STANDARD_TTL_S,
        "confidence": float(k.konfidens if k.konfidens is not None else 0.3),
        "provenance": {"mechanism": "dream_hypothesis_judge",
                       "family": "oneiric", "cursor_id": k.fingeraftryk},
    }


def _allerede_forfremmet(k: Kandidat) -> bool:
    """Er denne kandidat skrevet ind foer?

    ``register_governed_hypothesis`` deduplikerer paa ``_stable_id``, som
    inkluderer OPRETTELSES-TIDSPUNKTET — saa den kan aldrig genkende den samme
    kandidat i en senere koersel. Maalt: to koerslinger gav fire raekker.
    Vi deduplikerer derfor selv paa kandidatens eget fingeraftryk, som ligger
    stabilt i provenance som ``cursor_id``.
    """
    try:
        from core.runtime.db import connect
        with connect() as c:
            row = c.execute(
                "SELECT 1 FROM central_hypotheses WHERE source='dream_judge' "
                "AND provenance_json LIKE ? LIMIT 1",
                ("%%\"cursor_id\": \"%s\"%%" % k.fingeraftryk,)).fetchone()
        return row is not None
    except Exception as exc:
        logger.debug("dream_hypothesis_judge: dedup-opslag fejlede: %s", exc)
        return True     # kan vi ikke tjekke, forfremmer vi ikke igen


def forfrem(k: Kandidat) -> dict[str, object]:
    """Skriv hypotesen ind hvor den kan testes og dø. Self-safe."""
    if _allerede_forfremmet(k):
        return {"status": "duplicate"}
    try:
        from core.services.central_hypothesis_generator import register_governed_hypothesis
        return dict(register_governed_hypothesis(byg_preregistrering(k)))
    except Exception as exc:
        logger.debug("dream_hypothesis_judge: forfremmelse fejlede: %s", exc)
        return {"status": "error"}


def koer_dommer(*, mappe: Path | None = None) -> dict[str, object]:
    """Dømm alle kandidater og forfrem dem der har fortjent det.

    Returnerer tællinger pr. udfald, saa dommen kan efterproeves i Centralen
    frem for kun at kunne ses paa hvad der DUKKEDE OP i tabellen.
    """
    tal: dict[str, int] = {}
    forfremmede: list[str] = []
    for k in laes_kandidater(mappe):
        ok, grund = doem(k)
        if ok:
            res = forfrem(k)
            grund = "forfremmet" if res.get("status") == "registered" else \
                    "allerede-kendt" if res.get("status") == "duplicate" else \
                    "afvist-praeregistrering"
            if res.get("status") == "registered":
                forfremmede.append(k.navn)
        tal[grund] = tal.get(grund, 0) + 1
    try:
        from core.services.central_core import central
        central().observe({"cluster": "cognition", "nerve": "dream_hypothesis_judge",
                           "kind": "dom", **tal})
    except Exception:
        pass
    return {"tal": tal, "forfremmede": forfremmede}
