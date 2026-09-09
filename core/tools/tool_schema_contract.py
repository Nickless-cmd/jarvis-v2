"""Kanoniske argumenter mod versionerede skemaer — Fase 3, K2.

## Hvad maalingen viste, foer noget blev bygget

20.170 aegte vaerktoejskald fra transskriptet, holdt op mod de skemaer
vaerktoejerne selv erklaerer:

    gyldige                                 19.977
    brud                                       171
      heraf tomt input (afbrudt optagelse)      39
      heraf AEGTE brud                         132
        afvist hoejlydt af vaerktoejets vagt   104
        fik et 'vellykket' svar                 28

De 104 er dobbeltarbejde: vaerktoejet fanger det selv i sine foerste linjer.
De 28 er hullet. Og den stoerste gruppe i dem er ikke teoretisk:

`write_memory_topic` blev kaldt 17 gange uden `title` — og med `content` i
stedet for `body`. Vaerktoejet laeser `body`, faar tom streng, skriver filen,
laeser den tilbage, sammenligner tom med tom, og svarer `confirmed: true`.
**14 af 100 kuraterede hukommelsesfiler ligger som 0 bytes.** Hver eneste
blev meldt gemt.

## Hvorfor det ikke bare kan slaas til

Samme maaling viste det modsatte problem. `recall_memories` blev kaldt med
`modalities: ["somatic"]`, som skemaets enum ikke tillader — og vaerktoejet
returnerede 10 rigtige resultater, fordi koden accepterer enhver streng.
Dér er det SKEMAET der er forkert, ikke kaldet. At haandhaeve ville braekke
et kald der virker.

Derfor skelner kontrakten paa brud-ART:

    required   — vaerktoejet har selv sagt at det skal bruge feltet.
                 Et kald uden er ufuldstaendigt uanset hvem der har ret.
    enum/type  — skemaet kan vaere for snaevert. Rapportér, afvis ikke.

## Versioneret

`schema_version()` er en hash over selve skemaet. Den goer to ting muligt:
at se hvornaar et skema aendrer sig under foedderne paa en gemt invokation,
og at afvise en gammel dom som truffet paa et andet grundlag.

Modulet AFGOER intet af sig selv. `execute_tool` spoerger.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Brud-arter der er sikre at afvise paa: vaerktoejet har selv erklaeret behovet.
HAARDE_ARTER = frozenset({"required"})

_skemaer: dict[str, dict] | None = None
_validatorer: dict[str, Any] = {}
_versioner: dict[str, str] = {}


@dataclass(frozen=True)
class Brud:
    """Ét skema-brud. `haard` siger om det er sikkert at afvise paa."""
    art: str          # 'required', 'enum', 'type', ...
    sti: str          # hvor i argumenterne
    besked: str

    @property
    def haard(self) -> bool:
        return self.art in HAARDE_ARTER


def _indlaes() -> dict[str, dict]:
    global _skemaer
    if _skemaer is None:
        from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
        _skemaer = {}
        for d in TOOL_DEFINITIONS:
            f = d.get("function") or {}
            navn = str(f.get("name") or "")
            if navn:
                _skemaer[navn] = f.get("parameters") or {}
    return _skemaer


def _nulstil_for_tests() -> None:
    global _skemaer
    _skemaer = None
    _validatorer.clear()
    _versioner.clear()


def kendt(tool_name: str) -> bool:
    """Har vaerktoejet overhovedet et skema at maale imod?"""
    return str(tool_name or "") in _indlaes()


def schema_version(tool_name: str) -> str:
    """Indholds-hash over skemaet. Aendrer skemaet sig, aendrer versionen sig."""
    navn = str(tool_name or "")
    if navn not in _versioner:
        s = _indlaes().get(navn)
        if s is None:
            return ""
        krop = json.dumps(s, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, default=str)
        _versioner[navn] = "sha256:" + hashlib.sha256(
            krop.encode("utf-8")).hexdigest()[:16]
    return _versioner[navn]


def canonical_arguments(tool_name: str, arguments: dict[str, Any] | None
                        ) -> dict[str, Any]:
    """Argumenterne som SKEMAET ser dem.

    Runtime injicerer noegler med `_`-praefiks (`_runtime_session_id` og
    venner). De kommer ikke fra modellen og staar ikke i noget skema — at
    maale dem ville producere brud ingen har begaaet.
    """
    return {k: v for k, v in dict(arguments or {}).items()
            if not str(k).startswith("_")}


def _validator(tool_name: str):
    navn = str(tool_name or "")
    if navn not in _validatorer:
        s = _indlaes().get(navn)
        if s is None:
            return None
        try:
            from jsonschema import Draft202012Validator
            _validatorer[navn] = Draft202012Validator(s)
        except Exception:
            # Et ugyldigt skema er ikke et ugyldigt KALD. Maal ingenting frem
            # for at anklage kalderen for husets egen fejl.
            logger.warning("tool_schema_contract: ugyldigt skema for %s", navn,
                           exc_info=True)
            _validatorer[navn] = None
    return _validatorer[navn]


def violations(tool_name: str, arguments: dict[str, Any] | None) -> list[Brud]:
    """Hvilke skema-brud har dette kald? Tom liste = ingen."""
    v = _validator(tool_name)
    if v is None:
        return []
    args = canonical_arguments(tool_name, arguments)
    ud: list[Brud] = []
    try:
        for f in sorted(v.iter_errors(args), key=lambda e: str(list(e.path))):
            ud.append(Brud(art=str(f.validator),
                           sti="/".join(str(p) for p in f.path),
                           besked=str(f.message)[:300]))
    except Exception:
        logger.warning("tool_schema_contract: validering kastede for %s",
                       tool_name, exc_info=True)
        return []
    return ud


def haarde(brud: list[Brud]) -> list[Brud]:
    return [b for b in brud if b.haard]


def afvisning(tool_name: str, brud: list[Brud]) -> dict[str, Any]:
    """Svaret et afvist kald skal have.

    Beskeden er skrevet til den der kan rette den: modellen. Den siger HVAD
    der mangler og hvilket skema dommen blev truffet paa — ikke bare «error».
    """
    mangler = "; ".join(b.besked for b in brud[:4])
    return {
        "status": "error",
        "error": f"{tool_name}: {mangler}",
        "schema_version": schema_version(tool_name),
        "violations": [{"art": b.art, "sti": b.sti, "besked": b.besked}
                       for b in brud[:8]],
    }
