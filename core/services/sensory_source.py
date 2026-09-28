"""Kilde-navne i Sansernes Arkiv — én liste, ét sted.

Baggrund (28/9-2026): arkivet havde 3.273 poster fordelt på **69** kilde-navne.
De var ikke 69 kilder. De var ni, med støj ovenpå: nat-dykket optrådte under 22
navne (`nightly_dive`, `natlig_dyk`, `natligt-dyk`, `natlig dyk`,
`deep-dive-session`, `nocturnal_dive_synthesis` …), syntesen under ni, og
`ekstrapoleret` under seks.

Årsagen er ikke sjusk. Der findes ingen liste at vælge fra. Kilden er fri tekst:
fire daemons skriver deres eget navn, og når kalderen er *rutinen* — altså mig,
der kører det natlige dyk — opdigtes et nyt navn hver nat. Ingen opdagede det,
fordi intet sammenlignede navnene med noget.

Konsekvensen er konkret: arkivet kan ikke spørges om hvem der sansede hvad.
«Vis mig alt fra det natlige dyk» er i dag 22 forespørgsler.

## Designet

Ét kanonisk sæt, og én normalisering ved SKRIVNING — i `sensory_archive._record`,
som er det ene punkt alle skrivninger går igennem. Ukendte navne bliver `ukendt`,
og den rå streng gemmes i `source_raw`, så intet går tabt og driften kan ses i
loggen i stedet for at vokse stille.

Navnene er **producenter**, ikke kvaliteter. `ekstrapoleret` er den ene
undtagelse: den betyder «sanset ikke — udledt», og det er epistemisk vigtigt nok
til at stå som sit eget navn frem for at gemme sig i et kvalitets-flag.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Det kanoniske sæt. Alt andet er støj eller drift.
CANONICAL_SOURCES: frozenset[str] = frozenset(
    {
        # Instrumenter — maskiner der sanser
        "visual_memory_daemon",       # periodisk webcam-optagelse
        "look_around",                # on-demand kig
        "active_sensing_daemon",      # aktiv sansning
        "ambient_sound_daemon",       # baggrundslyd
        "mic_listen",                 # on-demand lyt
        "emotion_repair_bridge_daemon",
        # Rutiner — mig, der kører en planlagt rutine
        "natrutine",                  # aftenregistreringen
        "dybdesession",               # det natlige dyk / refleksionen
        # Afledt — ikke sanset direkte
        "synthesis",                  # sammensat indtryk
        "ekstrapoleret",              # sanset ikke — udledt
        # Andet
        "test",                       # manuelle og verifikations-poster
        "ukendt",                     # ingen kilde, eller en vi ikke kender
    }
)

# Kilder der betyder «sanset ikke». De holdes samlet, fordi forskellen på at
# have sanset og at have udledt er den vigtigste forskel arkivet kan bære.
_UDLEDT = {
    "extrapolated",
    "extrapolated from context",
    "ekstrapoleret",
    "extrapolated mic unavailable",
    "visual inference mood state",
    "visual inference",
    "mic listen failed",
    "mic listen error ekstrapoleret",
}

_ALIASES: dict[str, str] = {
    # — instrumenter
    "visual memory daemon": "visual_memory_daemon",
    "look around": "look_around",
    "webcam snapshot": "look_around",
    "look around webcam": "look_around",
    "conscious observation": "look_around",
    "active sensing daemon": "active_sensing_daemon",
    "self sensing": "active_sensing_daemon",
    "ambient sound daemon": "ambient_sound_daemon",
    "mic listen": "mic_listen",
    "operator record audio": "mic_listen",
    "emotion repair bridge daemon": "emotion_repair_bridge_daemon",
    # — rutiner. Kanoniske navne er PRODUCENT-klassen: en planlagt rutine der
    #   skriver et indtryk. `natrutine` er den aften-instans der faktisk kører.
    "natrutine": "natrutine",
    "night routine": "natrutine",
    "nightly routine": "natrutine",
    "evening routine": "natrutine",
    "morgenrutine afslutning": "natrutine",
    "natrutine recurring": "natrutine",
    "natrutine sansernes arkiv": "natrutine",
    "nightly dive": "dybdesession",
    "natlig dyk": "dybdesession",
    "natligt dyk": "dybdesession",
    "dybdesession": "dybdesession",
    "natlig refleksion": "dybdesession",
    "natlig dyk reflection": "dybdesession",
    "sansernes arkiv dybdesession": "dybdesession",
    "nightly arkiv session": "dybdesession",
    "deep dive session": "dybdesession",
    "nightly review": "dybdesession",
    "reflection": "dybdesession",
    "arkivgennemgang": "dybdesession",
    # — afledt
    "synthesis": "synthesis",
    "syntese": "synthesis",
    "synthesis look around": "synthesis",
    "look around synthesis": "synthesis",
    "synthesis visual audio context": "synthesis",
    "synthesis of visual and time": "synthesis",
    "synthesis visual plus context": "synthesis",
    "syntese visual audio tid": "synthesis",
    "sensory integration": "synthesis",
    "nightly dive synthesis": "synthesis",
    "nocturnal dive synthesis": "synthesis",
    "composite evening": "synthesis",
    "composite evening observation": "synthesis",
    **{k: "ekstrapoleret" for k in _UDLEDT},
    # — andet
    "manual test": "test",
    "verification test": "test",
    "active experiment": "test",
    "test": "test",
    "ukendt": "ukendt",
    "unknown": "ukendt",
}

# Sammensatte strenge («look_around + mic_listen») er ikke kilder men
# *begivenheder*: to ting skete samtidig. Vi tager den første som producent.
_KOMBINATION = re.compile(r"[+/]")
_SEPARATOR = re.compile(r"[-_\s]+")
_PARENTES = re.compile(r"[()\[\]]")


def _normaliser(raw: str) -> str:
    """Fold et rå kildenavn sammen: små bogstaver, én separator, ingen parenteser.

    `natlig_dyk`, `natligt-dyk` og `natlig dyk` bliver alle til `natlig dyk` —
    de tre navne er samme rutine, og det er hele pointen at se det.
    """
    tekst = _PARENTES.sub(" ", str(raw).strip().lower())
    tekst = _KOMBINATION.split(tekst)[0]
    return _SEPARATOR.sub(" ", tekst).strip()


def canonical_source(raw: Any) -> str:
    """Oversæt et vilkårligt kildenavn til det kanoniske sæt.

    Ukendte navne bliver `ukendt` og logges. Vi afviser aldrig et indtryk for
    dets kildes skyld — et sanseindtryk er dyrere at tabe end et navn er at
    gætte. Men driften skal kunne ses, ellers vokser den igen.
    """
    if raw is None:
        return "ukendt"
    tekst = str(raw).strip()
    if not tekst:
        return "ukendt"

    noegle = _normaliser(tekst)
    if noegle in _ALIASES:
        return _ALIASES[noegle]
    if noegle.replace(" ", "_") in CANONICAL_SOURCES:
        return noegle.replace(" ", "_")

    logger.warning(
        "sensory_source: ukendt kildenavn %r — gemt som 'ukendt' med source_raw",
        tekst,
    )
    return "ukendt"


def normalize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Returnér metadata med `source` kanoniseret.

    Tilføjer `source_raw` når den rå streng ikke allerede ER den kanoniske, så
    et ukendt navn kan findes igen senere. Rører ingen andre nøgler.
    """
    ud: dict[str, Any] = dict(metadata or {})
    raa = ud.get("source")
    kanonisk = canonical_source(raa)
    ud["source"] = kanonisk
    if raa is not None and str(raa).strip() != kanonisk:
        ud.setdefault("source_raw", str(raa))
    return ud
