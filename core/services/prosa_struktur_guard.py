"""Mekanisk kontrol af fire former for formfejl i et synligt svar.

Baggrund (målt 25/10-2026, Bjørn): «på teksten under overskifterne.. du bruger
ikk - osv. istedet bliver en lang smøre til næste section».

Baggrund (målt 2/11-2026, Bjørn): «det sværeste er faktisk at få dig til at
formatere din tekst beder.. altså i chat mode.. prøv og læg mærke til under den
sidste kode boks». Han pegede på fire ting i samme svar: en pseudo-overskrift
(«**Så et hul på to timer.**»), en talmur (fem tal i to sætninger), og en
kodeblok der indeholdt commits som løbende prosa. Guarden fra 25/10 SÅ det
ikke — den målte kun opremsninger under en overskrift, og skrev intet.

De fire regler, i den rækkefølge de måles:

1. ``opremsning`` — parallelle led som løbende prosa under en overskrift.
2. ``pseudo-overskrift`` — fed tekst der optager overskriftens plads uden at
   være en overskrift.
3. ``talmur`` — fem eller flere tal i ét afsnit uden liste eller tabel.
4. ``kodeblok`` — en fence der ikke indeholder kode, men prosa.

**Én blok giver højst ét fund.** Den første regel der matcher vinder, og de
øvrige springes over for den blok. Uden den gate ville et fakta-tungt afsnit
blive flagget både som opremsning og som talmur, og korrektionen ville få to
modstridende opgaver for samme tekst.

To ting guarden bevidst IKKE gør:

* **Den omskriver ikke.** Et flag er en observation, ikke en redigering. En
  heuristik der gætter på struktur kan ødelægge prosa der flyder rigtigt, og
  den slags fejl er dyrere end den den retter.
* **Den dømmer ikke hele svaret.** Kun afsnit der står UNDER en overskrift
  måles for regel 1–3. Prosa uden overskrift er ikke en «smøre til næste
  section» — der er ingen section at smøre til. Regel 4 (kodeblok) gælder
  overalt, for en fence er en fence uanset hvad der står over den.

Grænsen for regel 1 er bevidst lav (``MIN_LED`` = 3) og måles på
opremsningskæder, ikke på sætningsantal: tre korte sætninger der hver bærer én
pointe er god prosa. Det er «A, B og C» skrevet som én løbende linje der er
problemet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "MIN_LED",
    "MIN_AFSNIT_TEGN",
    "MIN_TAL",
    "MIN_KODEBLOK_LINJER",
    "ProsaPunkt",
    "fejl_i_prosa",
    "find_prosa_punkter",
]

#: Hvor mange parallelle led et afsnit må bære i prosa før det flagges.
MIN_LED = 3

#: Kortere afsnit er ikke en smøre — de kan ikke rumme tre reelle led.
MIN_AFSNIT_TEGN = 120

#: Hvor mange tal ét afsnit må bære før det er en talmur og ikke en sætning.
#: Målt 2/11-2026: afsnittet Bjørn pegede på bar seks tal i to sætninger.
MIN_TAL = 5

#: Kortere fences er inline-eksempler, ikke prosa i forklædning.
MIN_KODEBLOK_LINJER = 2

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

#: Fed tekst der STARTER en blok og fortsætter med brødtekst på samme linje.
#: Det er formen der ser ud som en overskrift uden at være det: læseren får et
#: hvilested for øjet, og der er ingen struktur bag det.
_PSEUDO_OVERSKRIFT_RE = re.compile(r"^\*\*([^*\n]{2,90})\*\*(?=[ \t]+\S)")

#: Tidsstempler og git-hashes fjernes før tal tælles. «kl. 12:38:27» er ét
#: klokkeslæt, ikke tre tal, og «e4036a383» er en reference, ikke et regnestykke.
_TIDSSTEMPEL_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_TAL_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w.])")

#: Kode-markører. En fence uden en enkelt af dem bærer prosa, ikke kode.
#: Listen er bevidst bred: en falsk positiv koster en unødvendig korrektion,
#: men en falsk negativ betyder at ægte kodeblokke bliver «rettet» til prosa.
_KODE_ORD_RE = re.compile(
    r"^[ \t]*(?:sudo|git|curl|wget|ssh|scp|cd|ls|cat|tail|head|grep|rg|find|awk|sed|"
    r"python3?|pip|npm|npx|yarn|docker|podman|systemctl|journalctl|uvicorn|pytest|"
    r"make|export|source|chmod|chown|mkdir|rmdir|rm|cp|mv|ln|tar|zip|unzip|psql|"
    r"sqlite3|def|class|import|from|return|async|await|function|const|let|var|"
    r"if|for|while|try|catch|echo|printf|set|test|case|esac|fi|done)\b",
    re.MULTILINE,
)
_KODE_TEGN_RE = re.compile(r"\$|\{|\}|=>|->|//|#!|&&|\|\||;\s*$|\w[ \t]*=[ \t]*\S")
_STI_RE = re.compile(
    r"(?:^|[\s(])(?:\.{0,2}/|~/|/[A-Za-z])[A-Za-z0-9_./-]+"
    r"|\b[A-Za-z0-9_-]+\.(?:py|js|jsx|ts|tsx|md|json|sh|ya?ml|toml|sql|db|log|"
    r"txt|css|html|cfg|ini|env)\b"
)


@dataclass(frozen=True)
class ProsaPunkt:
    """Ét afsnit (eller én fence) der bærer en formfejl.

    ``slags`` er tilføjet 2/11-2026 og har en default, så ældre kald der
    konstruerer punktet positionelt stadig virker. Den ligger sidst med vilje.
    """

    overskrift: str
    antal_led: int
    uddrag: str
    grund: str
    slags: str = "opremsning"

    def som_fejl(self) -> str:
        """Læsbar fejlstreng — samme form som ``jarvis_ui_guard.fejl_i_flader``."""
        kort = self.uddrag if len(self.uddrag) <= 70 else self.uddrag[:67] + "…"
        if self.slags == "pseudo-overskrift":
            return (
                f"pseudo-overskrift under «{self.overskrift}» — fed tekst står "
                f"hvor en overskrift skulle stå, uden at være en: «{kort}»"
            )
        if self.slags == "talmur":
            return (
                f"talmur med {self.antal_led} tal under «{self.overskrift}» — "
                f"tallene skal i en liste eller tabel: «{kort}»"
            )
        if self.slags == "kodeblok":
            return (
                f"kodeblok uden kode under «{self.overskrift}» — den bærer prosa, "
                f"brug liste eller tabel: «{kort}»"
            )
        return (
            f"prosa-opremsning med {self.antal_led} led under "
            f"«{self.overskrift}» — brug punktopstilling: «{kort}»"
        )


def _blokke_med_overskrift(text: str) -> list[tuple[str, list[str]]]:
    """(nærmeste overskrift, blok) for hvert afsnit i hele teksten.

    Overskriften er ``""`` når afsnittet ikke står under nogen.

    Tilføjet 2/11-2026 efter en måling på mit eget svar fra samme aften: det
    indeholdt tre pseudo-overskrifter og en talmur, og guarden fandt kun
    kodeblokken. Årsagen var at regel 1–3 blev målt inde i `_sektioner`, og et
    svar hvor fed tekst ER overskrifterne har ingen sektioner at måle i — altså
    var reglerne døde præcis i det tilfælde de skulle fange.

    Adskillelsen er nu: opremsning (regel 1) kræver stadig en overskrift, for
    uden en section er der ingen «smøre til næste section». Pseudo-overskrift
    og talmur gælder overalt — de er fejl uanset hvad der står over dem.
    """
    resultat: list[tuple[str, list[str]]] = []
    overskrift = ""
    aktuel: list[str] = []
    i_fence = False
    for linje in text.splitlines():
        if _FENCE_RE.match(linje):
            i_fence = not i_fence
            if aktuel:
                resultat.append((overskrift, aktuel))
                aktuel = []
            continue
        if i_fence:
            continue
        if not linje.strip():
            if aktuel:
                resultat.append((overskrift, aktuel))
                aktuel = []
            continue
        m = _OVERSKRIFT_RE.match(linje) or _FED_OVERSKRIFT_RE.match(linje)
        if m:
            if aktuel:
                resultat.append((overskrift, aktuel))
                aktuel = []
            overskrift = (
                m.group(2) if m.re is _OVERSKRIFT_RE else m.group(1)
            ).strip()
            continue
        aktuel.append(linje)
    if aktuel:
        resultat.append((overskrift, aktuel))
    return resultat


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


def _antal_tal(afsnit: str) -> int:
    """Antal selvstændige tal i et afsnit, efter klokkeslæt og hashes er fjernet.

    Uden oprydningen ville «kl. 12:38:27» tælle som tre tal og «e4036a383» som
    to — altså gøre et enkelt tidsstempel til en talmur.
    """
    renset = _TIDSSTEMPEL_RE.sub(" ", afsnit)
    renset = _HASH_RE.sub(" ", renset)
    return len(_TAL_RE.findall(renset))


def _pseudo_overskrift(blok: list[str]) -> str | None:
    """Returnér den fede tekst hvis blokken indledes af en pseudo-overskrift."""
    første = blok[0].strip()
    m = _PSEUDO_OVERSKRIFT_RE.match(første)
    if not m:
        return None
    fed = m.group(1).strip()
    # Et enkelt fremhævet ord («**Nej.** Det holder ikke.») er godt håndværk,
    # ikke en overskrift. Kravet er at den fede tekst selv bærer et emne —
    # enten som en frase på tre ord, eller som en etiket med kolon. Uden
    # kolon-reglen slap «**Aften: chat-kontrakten** (19:16–19:58)» igennem,
    # fordi danske sammensætninger giver et helt emne på to ord (målt 2/11-2026).
    if len(fed.split()) < 3 and ":" not in fed:
        return None
    return fed


def _indeholder_kode(krop: str) -> bool:
    """Afgør om en fence-krop faktisk er kode."""
    return bool(
        _KODE_ORD_RE.search(krop)
        or _KODE_TEGN_RE.search(krop)
        or _STI_RE.search(krop)
    )


def _kodeblokke(text: str) -> list[tuple[str, str, list[str]]]:
    """Find fences uden kode. Returnerer (overskrift, krop, linjer)."""
    fund: list[tuple[str, str, list[str]]] = []
    overskrift = ""
    i_fence = False
    krop: list[str] = []
    for linje in text.splitlines():
        if _FENCE_RE.match(linje):
            if i_fence:
                indhold = [l for l in krop if l.strip()]
                if (
                    len(indhold) >= MIN_KODEBLOK_LINJER
                    and not _indeholder_kode("\n".join(krop))
                ):
                    fund.append((overskrift, "\n".join(indhold), indhold))
                krop = []
                i_fence = False
            else:
                i_fence = True
            continue
        if i_fence:
            krop.append(linje)
            continue
        m = _OVERSKRIFT_RE.match(linje) or _FED_OVERSKRIFT_RE.match(linje)
        if m:
            overskrift = (
                m.group(2) if m.re is _OVERSKRIFT_RE else m.group(1)
            ).strip()
    return fund


def find_prosa_punkter(text: str) -> list[ProsaPunkt]:
    """Find formfejl i et svar. Én blok giver højst ét fund."""
    if not text:
        return []

    fund: list[ProsaPunkt] = []

    blokke = _blokke_med_overskrift(text)
    har_liste_pr_overskrift: dict[str, bool] = {}
    for overskrift, blok in blokke:
        if _er_struktureret(blok) and any(_LISTE_RE.match(l) for l in blok):
            har_liste_pr_overskrift[overskrift] = True

    for overskrift, blok in blokke:
        if _er_struktureret(blok):
            continue
        afsnit = " ".join(l.strip() for l in blok).strip()
        if not afsnit:
            continue

        # 1. Pseudo-overskrift: fed tekst optager overskriftens plads.
        # Den måles FØR længde-gaten: en pseudo-overskrift er kort af natur
        # (målt 2/11-2026: «**Så et hul på to timer.** …» er 117 tegn), så et
        # 120-tegns-krav gjorde reglen død præcis for de tilfælde den findes for.
        fed = _pseudo_overskrift(blok)
        if fed:
            fund.append(
                ProsaPunkt(
                    overskrift=overskrift or "svaret",
                    antal_led=1,
                    uddrag=afsnit,
                    grund="fed tekst i overskriftens plads",
                    slags="pseudo-overskrift",
                )
            )
            continue

        if len(afsnit) < MIN_AFSNIT_TEGN:
            continue

        # 2. Opremsning skrevet som prosa — kræver en overskrift over sig.
        bedste = 0
        grund = ""
        if overskrift:
            for saetning in _SAETNING_SPLIT.split(afsnit):
                bedste = max(bedste, _antal_led(saetning))
            if bedste < MIN_LED:
                # Et talt antal («tre ting») varsler en liste der aldrig kom.
                if _TALORD_RE.search(afsnit):
                    bedste = MIN_LED
                    grund = "talt antal uden punktopstilling"
                else:
                    bedste = 0
                    grund = ""
            else:
                grund = "opremsning skrevet som prosa"

        if bedste >= MIN_LED:
            if har_liste_pr_overskrift.get(overskrift):
                grund += " (sektionen har en liste, men dette afsnit gentager den i prosa)"
            fund.append(
                ProsaPunkt(
                    overskrift=overskrift,
                    antal_led=bedste,
                    uddrag=afsnit,
                    grund=grund,
                    slags="opremsning",
                )
            )
            continue

        # 3. Talmur: mange tal, ingen liste eller tabel at aflæse dem i.
        antal_tal = _antal_tal(afsnit)
        if antal_tal >= MIN_TAL:
            fund.append(
                ProsaPunkt(
                    overskrift=overskrift or "svaret",
                    antal_led=antal_tal,
                    uddrag=afsnit,
                    grund="tal i prosa",
                    slags="talmur",
                )
            )

    # 4. Kodeblok uden kode — gælder overalt, ikke kun under en overskrift.
    for overskrift, krop, linjer in _kodeblokke(text):
        fund.append(
            ProsaPunkt(
                overskrift=overskrift or "svaret",
                antal_led=len(linjer),
                uddrag=krop,
                grund="fence uden kode",
                slags="kodeblok",
            )
        )

    return fund


def fejl_i_prosa(text: str) -> list[str]:
    """Returnér læsbare fejl for formfejl — tom liste = intet at rette.

    Samme kontrakt som ``jarvis_ui_guard.fejl_i_flader``: kalderen får viden,
    ikke en omskrevet tekst.
    """
    return [p.som_fejl() for p in find_prosa_punkter(text)]
