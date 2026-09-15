"""Danske udtryksmaader for skills der kun beskriver sig selv paa engelsk.

## Hvorfor (15/9-2026)

Maalt paa otte rimelige danske formuleringer: seks fandt ingenting.

    «lav et regneark»        → INTET   (excel-automation findes)
    «lav en powerpoint»      → INTET   (pptx findes)
    «lav en praesentation»   → INTET
    «skriv et word-dokument» → fact-checker, tdd
    «undersoeg det grundigt» → INTET   (deep-research findes)
    «lav en pdf»             → pdf     ✓

Moensteret er tydeligt: de to der VIRKEDE har det danske ord i selve navnet
(«pdf», «youtube»). De oevrige kraever oversaettelse — regneark er ikke excel,
praesentation er ikke pptx, word-dokument er ikke docx.

Embedderen er ``all-MiniLM-L6-v2``, som er engelsk-centreret. En dansk
forespoergsel ligger daarligt op ad en engelsk beskrivelse, uanset hvor godt
de betyder det samme.

## Hvorfor ikke i skill-filerne

Matcheren UNDERSTOETTER tosprogede ``use_when`` — den splitter dem i
per-sprog-fragmenter. Mekanismen har vaeret der hele tiden; ingen skrev
indholdet. Fjerde gang paa én dag at noget findes uden en kalder.

Den naerliggende rettelse var at skrive ``DA:``-linjer ind i hver SKILL.md.
Men de fleste er leverandoer-filer (``composio-*`` og dokument-bundtet), og de
bliver overskrevet ved naeste opdatering. Tillaegget bor derfor HER, ved siden
af, og flettes ind som et ekstra kandidat-fragment.

## Hvordan den holdes aerlig

En haandholdt ordliste roadner. To vaern:

1. Den daekker kun skills der FINDES. Et navn her uden et skill er en fejl —
   testen kraever det, saa listen ikke stille peger paa noget der er fjernet.
2. Den tilfoejer kun UDTRYK, aldrig nye betydninger. Linjerne er hvad Bjoern
   faktisk ville skrive paa dansk — ikke en oversaettelse af den engelske
   beskrivelse, for saa ville den bare gentage det embedderen allerede har.

Se ogsaa reference_nudge_shadow_verdict: en ordliste udledt af vaerktoejernes
eget korpus var forkert her foer, netop fordi den ikke kendte hans sprog.
"""
from __future__ import annotations

#: skill-navn → dansk udtryks-linje. Skrevet som en bruger ville sige det.
DANSKE_UDTRYK: dict[str, str] = {
    "excel-automation": (
        "regneark, lav et regneark, analyser et regneark, aabn en xlsx-fil, "
        "opstil et budget i et ark, laes tal fra et ark, formler og faneblade"
    ),
    "xlsx": (
        "regneark, xlsx-fil, celler og faneblade, lav et ark med tal, "
        "opstil en tabel i et regneark"
    ),
    "pptx": (
        "praesentation, powerpoint, lav en praesentation, lav nogle slides, "
        "et slideshow, dias, tilfoej talernoter"
    ),
    "docx": (
        "word-dokument, skriv et dokument, lav et brev, en rapport i word, "
        "docx-fil, formatteret tekstdokument"
    ),
    "pdf": (
        "pdf, lav en pdf, udfyld en pdf-formular, slaa pdf-filer sammen, "
        "traek tekst ud af en pdf, del en pdf op"
    ),
    "deep-research": (
        "undersoeg det grundigt, grav dybt i emnet, lav en grundig research, "
        "find kilder og saml et overblik, dyk ned i det"
    ),
    "slides": (
        "slides, lav nogle slides, en praesentation, dias til et oplaeg"
    ),
    "markdown-helper": (
        "markdown, formatér teksten pænt, opstil det i markdown, tabeller i markdown"
    ),
    "docker": (
        "docker, container, byg et image, containeren starter ikke, "
        "docker-compose, hvorfor doer min container"
    ),
    "code-review": (
        "gennemgaa koden, kig min kode igennem, review af aendringerne, "
        "hvad er galt i den her kode"
    ),
    "prompt-optimizer": (
        "forbedr prompten, skriv prompten om, gør prompten skarpere"
    ),
    "youtube-downloader": (
        "hent en youtube-video, download en video, traek lyden ud af en video"
    ),
    "terminal-cli": (
        "kommandolinje, terminal, hvilken kommando skal jeg bruge, shell-kommando"
    ),
    "banner-design": (
        "lav et banner, en grafik til toppen, header-billede"
    ),
    "design-system": (
        "designsystem, farver og typografi, ensartet udtryk paa tvaers"
    ),
    "ui-ux-pro-max": (
        "brugerflade, hvordan skal det se ud, design af skaermbilledet, "
        "gør fladen pænere"
    ),
    "pfsense-api": (
        "pfsense, firewall-regler, min router, nat-regel, aabn en port"
    ),
}


def dansk_udtryk(skill_navn: str) -> str:
    """Den danske udtryks-linje for et skill, eller "" hvis der ingen er."""
    return DANSKE_UDTRYK.get(str(skill_navn or "").strip(), "")
