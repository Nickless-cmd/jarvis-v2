"""Hemmeligheder ud af det der havner i PROMPTEN — ikke ud af det han redigerer.

Målt 6/9-2026: en API-nøgle i et tool-resultat gik ordret i modellens kontekst,
i den persisterede historik, og videre til DeepSeek. Runtime havde ingen
redigering overhovedet.

## Den vigtige afgrænsning

Det oplagte — at rense hvert tool-resultat — ville gøre skade. Læser Jarvis en
konfigfil for at rette én linje, og får `[REDIGERET]` tilbage, så skriver han
det tilbage ved næste redigering. Værnet ville ødelægge Bjørns nøgler i stedet
for at beskytte dem. jarvis-code rører derfor heller ikke det levende
resultat; den renser kun spill-filen og projekt-filer på vej ind i prompten.

Her gælder samme regel, og den er indbygget i navnene: `read_for_prompt` er
den eneste vej der renser. `read_text_for_path` — som redigerings-værktøjerne
bruger — er urørt. Et værn der sidder på den delte læser ville ramme begge
veje, og det er præcis fejlen.

## Hvorfor prompten er det rigtige sted

En nøgle indsat i en dagbogsnote eller MEMORY.md læses ind i HVER eneste
prompt, tur efter tur, og sendes til en ekstern udbyder hver gang. Det er den
læk der har størst volumen og ingen risiko ved at lukke: prompten er kontekst
han læser, ikke en kilde han skriver tilbage fra.

## Mønstre

Kun høj-tillids-former. `token: 42` i en parser-log er ikke en hemmelighed,
så tildelings-mønsteret kræver en værdi der faktisk ligner en nøgle. Et værn
der råber ved hvert tal lærer én at overse det.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_MASKE = "[hemmelighed fjernet]"

# Udbyder-præfikser med kendt form — praktisk talt nul falske positiver.
_MOENSTRE: tuple[re.Pattern[str], ...] = (
    # `sk-` kraever mindst ét CIFFER i halen. Uden det ramte moensteret
    # `sk-g-ld-prioritetsplan` — et dansk filnavn i Bjoerns hukommelses-indeks
    # — og ville have maskeret det i prompten. Fundet ved at proeve mod de
    # AEGTE workspace-filer, ikke mod opdigtede eksempler.
    re.compile(r"\bsk-(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{16,}"),   # OpenAI / Anthropic
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),            # GitHub
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                    # AWS access key id
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),          # Slack
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),                # Google
    re.compile(r"\bglpat-[A-Za-z0-9_-]{16,}"),              # GitLab
    # Tildeling: navnet SKAL antyde en hemmelighed, og vaerdien skal vaere
    # laang nok og ikke-triviel. Uden det ville «port: 8080» blive maskeret.
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret[_-]?key|secret|access[_-]?token|auth[_-]?token"
        r"|bearer[_-]?token|password|passwd|client[_-]?secret)\b\s*[:=]\s*"
        r"[\"']?([A-Za-z0-9_\-./+]{12,})[\"']?"
    ),
)


def contains_secret(text: str) -> bool:
    """Ser det ud til at indeholde en hemmelighed? Ren, ingen mutation."""
    if not text:
        return False
    return any(m.search(text) for m in _MOENSTRE)


def redact(text: str) -> str:
    """Maskér hemmeligheder. Bevarer alt andet tegn for tegn."""
    if not text:
        return text
    ud = text
    for m in _MOENSTRE:
        if m.groups:
            # Tildelings-formen: behold navnet, maskér KUN vaerdien, saa det
            # stadig kan ses AT der stod en noegle — og hvilken slags.
            ud = m.sub(lambda mm: mm.group(0).replace(mm.group(1), _MASKE), ud)
        else:
            ud = m.sub(_MASKE, ud)
    return ud


def read_for_prompt(path) -> str | None:
    """Læs en workspace-fil TIL PROMPTEN, med hemmeligheder maskeret.

    Brug KUN denne når teksten skal i prompten. Skal filen redigeres, så læs
    med `read_text_for_path` — ellers skriver han masken tilbage i stedet for
    nøglen.

    **None betyder «filen findes ikke»** — præcis som `read_text_for_path`.
    Kaldere skelner på `is None` mellem en manglende fil og en tom, og at
    returnere `""` for begge ville få en manglende fil til at se tom ud. Jeg
    lavede netop den fejl da modulet blev skrevet.
    """
    # Kaldet holdes ETT-ARGUMENTS, praecis som alle andre kaldere: en ekstra
    # `encoding=` braekkede test-dubler der kun tager `path`, og den brede
    # except herunder slugte TypeError'en TAVST og returnerede None — filen
    # saa ud til ikke at findes. Derfor logges fejlen nu.
    try:
        from core.services.workspace_crypto import read_text_for_path
        raa = read_text_for_path(path)
    except Exception:
        logger.warning("secret_redaction: kunne ikke læse %s", path, exc_info=True)
        return None
    if not raa:
        return raa
    renset = redact(raa)
    if renset != raa:
        logger.warning(
            "secret_redaction: maskerede hemmelighed(er) i %s på vej i prompten", path,
        )
    return renset
