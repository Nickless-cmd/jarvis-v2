"""Hvilket billede må en klient hente — og hvad gør vi når svaret er «ingen»?

## Reglen boede i en rute

`/visning/billede` afgør om en sti må vises: kun under `JARVIS_HOME` eller
Jarvis' egne skærmbilleder i temp-mappen. Den regel lå inde i selve ruten, og
`core/` kan ikke importere en API-rute. Derfor kunne værktøjslaget ikke spørge
«må klienten hente det her?» før det svarede — og gjorde i stedet det eneste
det kunne: tog altid en kopi.

Reglen bor her nu. Ruten importerer den; det er den samme regel, ét sted.

## Kopien

Beskærer Jarvis et skærmbillede til `/tmp/ss_mid.png`, må ruten ikke vise det
— `/tmp` er fælles, og en hvidliste på hele mappen ville gøre ruten til en
fil-browser. Men billedet er hans eget, og det er dét brugeren gerne vil se
under scanneren.

Så laver vi en kopi med `jarvisx-vision-`-præfikset, som ruten ALLEREDE stoler
på. Hvidlisten røres ikke.

To ting gør kopien billig:

  - **Den laves kun når den skal.** Ligger originalen under `JARVIS_HOME` —
    hvilket alt uploadet gør — bæres originalens sti videre uændret. Ingen
    kopi overhovedet.
  - **Navnet er udledt af filen selv** (sti + mtime + størrelse). Samme billede
    to gange giver samme kopi. Før lavede `_stage_image_preview` en ny fil ved
    hvert kald med `NamedTemporaryFile`, og ventefladen ville have lavet endnu
    en ved siden af.

Målt på CT105 28/9-2026: 163 `jarvisx-vision-`-kopier, 120 MB — og ingen ældre
end 7 dage, fordi temp-mappen selv ryddes. Derfor er der ikke bygget en
oprydning her: den findes allerede, og en til ville være to sandheder om samme
fil.
"""
from __future__ import annotations

import hashlib
import logging
import tempfile
from pathlib import Path

from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

# Samme liste som desk'ens `electron/billede.ts`. To steder med samme regel er
# ét sted for meget — men den ene kan ikke importere den anden (TS mod Python),
# og reglen er lille nok til at kunne holdes i hånden.
MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
}

# 12 MB. Et fuldt skærmbillede er ~2 MB — resten er ikke noget vi viser.
LOFT = 12 * 1024 * 1024

TEMP_PREFIKSER = (
    "jarvisx-screenshot-",
    "jarvisx-window-",
    "jarvisx-browser-",
    "jarvis-browser-",
    "jarvisx-vision-",
)

_KOPI_PRAEFIKS = "jarvisx-vision-"


def _ligger_under(sti: Path, rod: Path) -> bool:
    try:
        sti.relative_to(rod)
    except ValueError:  # uden for roden — det ER svaret, ikke en fejl
        return False
    return True


def maa_vises(sti: str) -> Path | None:
    """Den opløste sti hvis den må vises — ellers None.

    Ren funktion uden I/O ud over `resolve()`, så reglen kan testes for sig.
    """
    if not sti or not sti.startswith("/"):
        return None
    raa = Path(sti)
    if raa.suffix.lower() not in MIME:
        return None
    try:
        fuld = raa.resolve()
    except OSError:  # kan stien ikke opløses (fx for lang), må den ikke vises
        return None

    if _ligger_under(fuld, JARVIS_HOME.resolve()):
        return fuld

    # Jarvis' egne skærmbilleder: direkte i temp-roden, med et kendt prefix.
    tmp = Path(tempfile.gettempdir()).resolve()
    if fuld.parent == tmp and fuld.name.startswith(TEMP_PREFIKSER):
        return fuld

    return None


def _kopinavn(fuld: Path) -> str:
    """Et navn udledt af filen selv, så samme billede giver samme kopi.

    mtime og størrelse er med, fordi en sti kan genbruges til et nyt billede —
    så ville et navn på stien alene vise det forrige.
    """
    st = fuld.stat()
    noegle = f"{fuld}|{int(st.st_mtime)}|{st.st_size}".encode("utf-8")
    return _KOPI_PRAEFIKS + hashlib.sha256(noegle).hexdigest()[:20] + fuld.suffix.lower()


def visnings_sti(sti: str) -> str:
    """Den sti en klient kan HENTE billedet på. Tom streng hvis ingen findes.

    Rækkefølgen er hele pointen:

      1. Må originalen vises, bæres den videre uændret — ingen kopi.
      2. Ellers kopieres den til en hvidlistet temp-sti.
      3. Kan ingen af delene lade sig gøre, tom streng: klienten viser rammen
         uden billede, som den gjorde før. Aldrig en sti der ikke virker.

    Kaster aldrig. Den kaldes fra annonceringen af et værktøjskald, midt i
    streamen — en fejl her må ikke koste turen.
    """
    raa = str(sti or "").strip()
    if not raa:
        return ""
    if maa_vises(raa):
        return raa
    try:
        fuld = Path(raa).resolve()
        if fuld.suffix.lower() not in MIME or not fuld.is_file():
            return ""
        if fuld.stat().st_size > LOFT:
            return ""
        maal = Path(tempfile.gettempdir()).resolve() / _kopinavn(fuld)
        if not maal.exists():
            # Skriv ved siden af og flyt på plads: to samtidige kald må ikke
            # kunne lade en klient hente en halvskreven fil. Endelsen `.delvis`
            # gør desuden at `maa_vises` afviser den undervejs — den ligner
            # ikke et billede før den ER et.
            midlertidig = maal.with_name(maal.name + f".{id(fuld):x}.delvis")
            try:
                midlertidig.write_bytes(fuld.read_bytes())
                midlertidig.replace(maal)
            finally:
                midlertidig.unlink(missing_ok=True)
        return str(maal)
    except OSError as exc:
        logger.warning("kunne ikke lave visnings-kopi af %s: %s", raa, exc)
        return ""
