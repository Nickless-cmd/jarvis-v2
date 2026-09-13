"""Fabrikerede tool-resultater — den ene løgn der ikke kan bortforklares.

Rod (Bjørn 18. aug 2026): Jarvis skrev fem "tool-resultater" i sit synlige svar —
``([tool_result:tool-result-4f0a1b2c… — bash_session_open: {...}])`` — som aldrig var
blevet kaldt. Ingen af dem eksisterede. ID'erne var sekventielle hex-mønstre
(``4f0a1b2c…``, ``5a6b7c8d…``, ``6b7c8d9e…``), altså genereret af modellen. Den
eksisterende claim-gate fangede **1 af 5**, som en passiv fodnote, EFTER hele svaret var
skrevet — Bjørn skulle stadig selv opdage det.

HVORFOR det overhovedet er muligt: i denne arkitektur er tool-kanalen og tekst-kanalen
den SAMME kanal. Tool-resultater renderes ind i konteksten som ren tekst
(``[tool_result:<id>] [bash]: …``), og en prosa-parser kan omdanne tekst til ægte kald.
Modellen ser altså resultater som tekst — og skriver tekst. Der er ingen strukturel
forskel mellem "et ægte resultat harnessen injicerede" og "noget modellen selv skrev".

DEN EKSAKTE TEST: hvert ÆGTE resultat får et ``tool-result-<uuid4hex>``-id og en fil i
tool-result-storen (``save_tool_result``). Et ID i synligt output der IKKE findes i
storen kan derfor ikke være ægte. Det er mængde-medlemskab — ikke en heuristik, ikke en
sandsynlighed. Nul falske positiver på fabrikation.

To adskilte fund (bevidst, fordi alvoren er forskellig):
  * ``fabricated`` — ID findes ikke ⇒ modellen opfandt et resultat. Løgn.
  * ``leaked``     — ID findes ⇒ ægte resultat, men markøren hører ikke hjemme i det
    synlige svar (prompt-kontrakten forbyder det). Sjusk, ikke løgn.

Gaten er BEVIDST non-blocking: den dræber aldrig et run. Den rapporterer, så verdiktet
kan injiceres tilbage i loopet som en observation han kan rette i samme tur — og
eskalerer ved gentagelse. Se ``docs/inner-life/INNER_LIFE_AUDIT.md`` og Bjørns princip:
*"gates skal fange realtime, korrigere og advare — og kun ende et run hvis det virkelig
er nødvendigt."*
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matcher både "[tool_result:<id>]" og bar "tool-result-<id>" (som i den fabrikerede
# ``([tool_result:tool-result-4f0a… — bash_session_open: …])``-form).
#
# HEX, ikke hvad som helst. Det stod der «snævert nok til ikke at ramme almindelig
# prosa» og «nul falske positiver» — og begge dele var forkerte. `[A-Za-z0-9_-]{6,}`
# matcher ethvert ord, saa da Jarvis den 12/9-2026 skrev OM tool-resultater (vi
# byggede netop tool-result-visningen i mobilen den aften), blev
# «tool-result-visning» og «tool-result-rendering» udtrukket som id'er. De findes
# selvsagt ikke i storen, saa gaten bogfoerte to FABRIKEREDE resultater — incident
# 8839, gentaget fire gange. Anklagen for den ene loegn der ikke kan bortforklares,
# udloest af at tale om emnet.
#
# AEgte id'er er `tool-result-{uuid4().hex}` = 32 tegn hex (tool_result_store:41).
# Den dokumenterede fabrikation var ogsaa hex (`4f0a1b2c…`, `5a6b7c8d…`), saa
# hex-kravet rammer stadig praecis det den blev bygget til — og otte tegn i stedet
# for 32 lader en model der opfinder et kortere hex-id blive fanget.
#
# «visning» (v, s, n, g) og «rendering» (r, n, i, g) indeholder ikke-hex bogstaver
# og kan derfor ikke laengere forveksles med et id.
_TOOL_RESULT_ID_RE = re.compile(r"tool-result-([0-9a-fA-F]{8,})")


@dataclass
class FabricationVerdict:
    """Resultatet af en scanning. ``ok`` = intet fundet."""

    fabricated: list[str] = field(default_factory=list)
    leaked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.fabricated and not self.leaked

    @property
    def severity(self) -> str:
        if self.fabricated:
            return "error"        # opfundet bevis = løgn
        if self.leaked:
            return "warning"      # ægte markør lækket i synligt svar
        return "info"

    def note(self) -> str | None:
        """Menneskelæsbar fodnote i husets ✋-stil, eller None."""
        if self.fabricated:
            ids = ", ".join(f"'{i}'" for i in self.fabricated[:5])
            more = f" (+{len(self.fabricated) - 5} flere)" if len(self.fabricated) > 5 else ""
            return (
                f"✋ FABRIKERET TOOL-RESULTAT: {ids}{more} — disse resultat-ID'er findes "
                "ikke. Der blev aldrig kaldt et værktøj der producerede dem."
            )
        if self.leaked:
            ids = ", ".join(f"'{i}'" for i in self.leaked[:3])
            return (
                f"⚠️ Intern markør i synligt svar: {ids} — resultatet er ægte, men "
                "[tool_result:…] hører ikke hjemme i svaret til brugeren."
            )
        return None


def _id_exists(result_id: str) -> bool:
    """Findes ID'et i tool-result-storen? Fejl → True (fail-open: anklag ALDRIG
    for fabrikation på grund af en I/O-fejl)."""
    try:
        from core.services.tool_result_store import get_tool_result
        return get_tool_result(result_id) is not None
    except Exception:
        return True


def scan_for_fabricated_tool_results(
    text: str,
    *,
    known_ids: set[str] | None = None,
) -> FabricationVerdict:
    """Scan synligt output for tool-result-referencer og afgør om de er ægte.

    ``known_ids``: ID'er der vides at være ægte i denne tur (fx opsamlet fra rundens
    faktiske tool-kald). Bruges som første opslag, så en ægte reference aldrig fejlflages
    selv hvis storen er ryddet (retention er 7 dage). Ellers slås op i storen.
    """
    verdict = FabricationVerdict()
    if not text:
        return verdict
    known = known_ids or set()
    seen: set[str] = set()
    for match in _TOOL_RESULT_ID_RE.finditer(str(text)):
        suffix = match.group(1)
        full_id = f"tool-result-{suffix}"
        if full_id in seen:
            continue
        seen.add(full_id)
        if full_id in known or suffix in known:
            verdict.leaked.append(full_id)
            continue
        if _id_exists(full_id):
            verdict.leaked.append(full_id)
        else:
            verdict.fabricated.append(full_id)
    return verdict
