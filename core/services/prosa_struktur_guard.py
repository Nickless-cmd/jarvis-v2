"""Mekanisk kontrol: et afsnit under en overskrift der opremser tre eller flere
parallelle led i prosa i stedet for som punktopstilling.

Baggrund (målt 25/10-2026, Bjørn): «på teksten under overskifterne.. du bruger
ikk - osv. istedet bliver en lang smøre til næste section».

Reglen findes allerede i ``CHAT_FORMAT_CORE`` (``chat_response_policy.py``):
«punktopstilling når mindst tre parallelle ting, trin eller valg skal kunne
skimmes». Den blev brudt i samme svar hvor den blev citeret — og en
model-baseret korrektur returnerede den SAMME tekst (commit ``4b473aecd``),
altså nul effekt. Derfor er denne kontrol mekanisk: den måler teksten, den
spørger ikke en model.

To ting den bevidst IKKE gør:

* **Den omskriver ikke.** Et flag er en observation, ikke en redigering. En
  heuristik der gætter på struktur kan ødelægge prosa der flyder rigtigt, og
  den slags fejl er dyrere end den den retter.
* **Den dømmer ikke hele svaret.** Kun afsnit der står UNDER en overskrift
  måles. Prosa uden overskrift er ikke en «smøre til næste section» — der er
  ingen section at smøre til.

Grænsen er bevidst lav (``MIN_LED`` = 3) og måles på opremsningskæder, ikke på
sætningsantal: tre korte sætninger der hver bærer én pointe er god prosa. Det
er «A, B og C» skrevet som én løbende linje der er problemet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "MIN_LED",
    "MIN_AFSNIT_TEGN",
    "ProsaPunkt",
    "fejl_i_prosa",
    "find_prosa_punkter",
]

#: Hvor mange parallelle led et afsnit må bære i prosa før det flagges.
MIN_LED = 3

#: Kortere afsnit er ikke en smøre — de kan ikke rumme tre reelle led.
MIN_AFSNIT_TEGN = 120

_OVERSKRIFT_RE = re.compile(r"^(#{1,6})[ \t]+(\S.*?)[ \t]*$")
_FED_OVERSKRIFT_RE = re.compile(r"^\*\*([^*\n]{2,60})\*\*[ \t]*$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_LISTE_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]|\d{1,9}[.)][ \t])")
_TABEL_RE = re.compile(r"^[ \t]*\|")
_CITAT_RE = re.compile(r"^[ \t]*>")
_SAETNING_SPLIT = re.compile(r"(?<=[.!?])\s+")
_OPREMSNING_SPLIT = re.compile(r"[,;]")
_OG_RE = re.compile(r"\bog\b", re.IGNORECASE)
_TALORD_RE = re.compile(
    r"\b(?:tre|fire|fem|seks)\s+(?:ting|grunde|dele|trin|valg|punkter|lag|tingene)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProsaPunkt:
    """Ét afsnit der bærer en opremsning som prosa i stedet for en liste."""

    overskrift: str
    antal_led: int
    uddrag: str
    grund: str

    def som_fejl(self) -> str:
        """Læsbar fejlstreng — samme form som ``jarvis_ui_guard.fejl_i_flader``."""
        kort = self.uddrag if len(self.uddrag) <= 70 else self.uddrag[:67] + "…"
        return (
            f"prosa-opremsning med {self.antal_led} led under "
            f"«{self.overskrift}» — brug punktopstilling: «{kort}»"
        )


def _sektioner(text: str) -> list[tuple[str, list[str]]]:
    """Del teksten i (overskrift, linjer) — kun sektioner der HAR en overskrift.

    Overskrifter inde i kodeblokke tælles ikke: en `# kommentar` i et bash- eller
    Python-eksempel er ikke en sektion i svaret. Det er den samme fælde som
    ``markdown_structure`` værner mod med sin fence-split.
    """
    sektioner: list[tuple[str, list[str]]] = []
    aktuel: str | None = None
    linjer: list[str] = []
    i_fence = False
    for linje in text.splitlines():
        if _FENCE_RE.match(linje):
            i_fence = not i_fence
            if aktuel is not None:
                linjer.append(linje)
            continue
        if not i_fence:
            m = _OVERSKRIFT_RE.match(linje) or _FED_OVERSKRIFT_RE.match(linje)
            if m:
                if aktuel is not None:
                    sektioner.append((aktuel, linjer))
                aktuel = (m.group(2) if m.re is _OVERSKRIFT_RE else m.group(1)).strip()
                linjer = []
                continue
        if aktuel is not None:
            linjer.append(linje)
    if aktuel is not None:
        sektioner.append((aktuel, linjer))
    return sektioner


def _blokke(linjer: list[str]) -> list[list[str]]:
    """Del en sektion i afsnit (blank-linje-adskilte) og fjern strukturerede blokke.

    En blok der er en liste, tabel, citat eller kodeblok er allerede struktureret
    — den er svaret på problemet, ikke problemet.
    """
    blokke: list[list[str]] = []
    aktuel: list[str] = []
    i_fence = False
    for linje in linjer:
        if _FENCE_RE.match(linje):
            i_fence = not i_fence
            if aktuel:
                blokke.append(aktuel)
                aktuel = []
            continue
        if i_fence:
            continue
        if not linje.strip():
            if aktuel:
                blokke.append(aktuel)
                aktuel = []
            continue
        aktuel.append(linje)
    if aktuel:
        blokke.append(aktuel)
    return blokke


def _er_struktureret(blok: list[str]) -> bool:
    return any(
        _LISTE_RE.match(l) or _TABEL_RE.match(l) or _CITAT_RE.match(l) for l in blok
    )


def _antal_led(saetning: str) -> int:
    """Antal parallelle led i én sætning, målt på opremsningskæden.

    «A, B og C» giver 3: to dele efter kommast opdeling, plus ét for den
    afsluttende «og»-forbindelse. Grænsen er at der skal være mindst ét
    komma/semikolon — ellers er der ingen kæde at måle.
    """
    dele = [d.strip() for d in _OPREMSNING_SPLIT.split(saetning) if d.strip()]
    if len(dele) < 2:
        return 0
    antal = len(dele)
    if _OG_RE.search(saetning):
        antal += 1
    return antal


def find_prosa_punkter(text: str) -> list[ProsaPunkt]:
    """Find afsnit under en overskrift der opremser parallelle led som prosa."""
    if not text or "#" not in text and "**" not in text:
        return []
    fund: list[ProsaPunkt] = []
    for overskrift, linjer in _sektioner(text):
        har_liste = any(_LISTE_RE.match(l) for l in linjer)
        for blok in _blokke(linjer):
            if _er_struktureret(blok):
                continue
            afsnit = " ".join(l.strip() for l in blok).strip()
            if len(afsnit) < MIN_AFSNIT_TEGN:
                continue
            bedste = 0
            for saetning in _SAETNING_SPLIT.split(afsnit):
                bedste = max(bedste, _antal_led(saetning))
            if bedste < MIN_LED:
                # Et talt antal («tre ting») varsler en liste der aldrig kom.
                if not _TALORD_RE.search(afsnit):
                    continue
                bedste = max(bedste, MIN_LED)
            grund = (
                "opremsning skrevet som prosa"
                if bedste >= MIN_LED
                else "talt antal uden punktopstilling"
            )
            if har_liste:
                grund += " (sektionen har en liste, men dette afsnit gentager den i prosa)"
            fund.append(
                ProsaPunkt(
                    overskrift=overskrift,
                    antal_led=bedste,
                    uddrag=afsnit,
                    grund=grund,
                )
            )
    return fund


def fejl_i_prosa(text: str) -> list[str]:
    """Returnér læsbare fejl for prosa-opremsninger — tom liste = intet at rette.

    Samme kontrakt som ``jarvis_ui_guard.fejl_i_flader``: kalderen får viden,
    ikke en omskrevet tekst.
    """
    return [p.som_fejl() for p in find_prosa_punkter(text)]
