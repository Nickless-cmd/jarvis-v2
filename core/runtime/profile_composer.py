"""Profil-komponisten — Fase 9 i DeepSeek-harness-spec'en.

En **profil** er det sæt regler en kørsel arbejder under: hvilken model, hvilke
værktøjer, hvilken godkendelses-tilstand, hvor meget sandkasse. I dag ligger de
regler spredt som løse argumenter — `tool_scope` optræder 21 steder alene i
`visible_runs`, `approval_mode` to — og ingen kørsel kan bagefter gøre rede for
*hvilke* regler den faktisk kørte under.

## Den bærende invariant: sikkerhed kan kun indsnævres

Profiler komponeres i lag: en grundprofil, så en rolle, så en kørselsspecifik
overstyring. Et senere lag må **aldrig** kunne give mere end et tidligere.

Uden den regel er en profil ikke en sikkerhedsgrænse, men en anbefaling: enhver
der kan tilføje et lag, kan hæve sine egne rettigheder. Med den er rækkefølgen
ligegyldig for sikkerheden — man kan kun bevæge sig én vej.

Ikke-sikkerheds-felter (model, retry, compaction) følger almindelig præcedens:
sidste lag vinder. Skellet er bevidst — en profil skal kunne vælge en anden
model uden at det er en rettigheds-ændring.

## Hvorfor version og hash

Exit-kriteriet siger at hver kørsel skal registrere «effective profile schema
version and hash». Grunden er efterforskning: når noget gik galt i går, skal man
kunne afgøre om det kørte under de regler man tror. Et navn er ikke nok —
profiler ændrer sig. Hashen er over det EFFEKTIVE resultat, ikke over navnet.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

#: Skemaets version. Ændres kun når FORMEN ændrer sig — ikke når en profils
#: indhold gør. En kørsel gemmer den, så gamle kørsler kan læses korrekt.
SKEMA_VERSION = 1

#: Sikkerheds-akserne, ordnet fra mest til mindst tilladt. Et senere lag må
#: kun flytte VÆK fra indeks 0.
#:
#: Akserne er ikke opfundet her: `tool_scope` og `approval_mode` bruges allerede
#: i `visible_runs`. De får blot en retning, så «indsnævring» kan afgøres
#: maskinelt i stedet for at være en hensigt i en kommentar.
SIKKERHEDS_AKSER: dict[str, tuple[str, ...]] = {
    # Hvor mange værktøjer kørslen må se.
    "tool_scope": ("all", "standard", "limited", "none"),
    # Hvornår mennesket skal spørges.
    "approval_mode": ("never", "ask", "always"),
    # Hvor indelukket processen kører.
    "sandbox": ("none", "workspace", "readonly"),
    # Må kørslen læse kontekst fra ANDRE sessioner.
    "cross_session_context": ("full", "summary", "none"),
    # Må kørslens telemetri forlade maskinen.
    "telemetry_sharing": ("full", "redacted", "none"),
}

#: Felter en profil ALDRIG kan slå fra. Exit-kriteriet: «audit truth cannot be
#: disabled by profiles». Revision er ikke en indstilling — det er den eneste
#: grund til at man bagefter kan vide hvad der skete.
UKRAENKELIGE: frozenset[str] = frozenset({"audit", "audit_log", "event_ledger"})


@dataclass(frozen=True)
class EffektivProfil:
    """Resultatet af en komposition — og det en kørsel gemmer om sig selv."""

    navn: str
    felter: dict[str, Any]
    skema_version: int = SKEMA_VERSION
    lag: tuple[str, ...] = field(default_factory=tuple)

    @property
    def hash(self) -> str:
        """Hash over det EFFEKTIVE resultat, ikke over navnet.

        Et navn siger ikke hvad profilen indeholdt dengang; profiler ændrer sig.
        Hashen gør en kørsel efterprøvelig: kørte den under de regler vi tror?
        """
        kanonisk = json.dumps(
            {"v": self.skema_version, "felter": self.felter},
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        )
        return hashlib.sha256(kanonisk.encode("utf-8")).hexdigest()[:16]

    def forklar(self) -> dict[str, Any]:
        """Hvad Mission Control skal kunne vise. Exit-kriteriet kræver at
        model, værktøjer, godkendelse, retry, compaction, hukommelse, private
        lag og subagent-politik kan forklares — ikke gættes."""
        return {
            "navn": self.navn,
            "skema_version": self.skema_version,
            "hash": self.hash,
            "lag": list(self.lag),
            "felter": dict(self.felter),
            "sikkerhed": {a: self.felter.get(a) for a in SIKKERHEDS_AKSER
                          if a in self.felter},
        }


def _er_indsnaevring(akse: str, fra: Any, til: Any) -> bool:
    """Bevæger `til` sig væk fra «mest tilladt» i forhold til `fra`?

    Ukendte værdier regnes IKKE som indsnævring. En værdi vi ikke kender
    retningen på kan ikke bruges til at hæve rettigheder ved et uheld.
    """
    raekke = SIKKERHEDS_AKSER.get(akse)
    if not raekke:
        return True                      # ikke en sikkerheds-akse
    try:
        return raekke.index(til) >= raekke.index(fra)
    except ValueError:
        return False


def komponer(lag: list[tuple[str, dict[str, Any]]], *, navn: str = "") -> EffektivProfil:
    """Sæt lagene sammen i rækkefølge. Senere lag vinder — undtagen sikkerhed,
    hvor de kun må indsnævre, og revision, som slet ikke kan røres.

    `lag` er `(lagnavn, felter)` i den rækkefølge de skal anvendes.
    """
    ud: dict[str, Any] = {}
    navne: list[str] = []
    for lagnavn, felter in lag:
        navne.append(str(lagnavn))
        for nøgle, værdi in (felter or {}).items():
            if nøgle in UKRAENKELIGE:
                # Revision kan TILFØJES, men aldrig slås fra eller svækkes.
                if not værdi:
                    continue
                ud[nøgle] = værdi
                continue
            if nøgle in SIKKERHEDS_AKSER and nøgle in ud:
                if not _er_indsnaevring(nøgle, ud[nøgle], værdi):
                    continue             # forsøg på at udvide — ignoreres
            ud[nøgle] = værdi
    for nøgle in UKRAENKELIGE:
        ud.setdefault(nøgle, True)
    return EffektivProfil(navn=navn or (navne[-1] if navne else ""),
                          felter=ud, lag=tuple(navne))
