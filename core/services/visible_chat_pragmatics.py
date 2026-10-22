"""Pragmatic conversation boundaries for the visible chat-only lane.

Chat mode is the relational conversation surface.  Code/work mode deliberately
does not inherit this contract: terse imperatives there are usually task input,
while the same words in chat can be reactions, corrections, or requests for
space.
"""
from __future__ import annotations


CHAT_MODE_CONVERSATION_CONTRACT = """## Chatmode: samtaleforstaaelse og graenser

Læs korte ytringer som talehandlinger i deres samtalekontekst, ikke automatisk
som bogstavelige svar på dit seneste spørgsmål. Latter, udbrud og fx "NEEEEJ"
kan være en reaktion på det, du lige skrev. En besked som "du misforstod mig"
eller "det var ikke mit svar" er en korrektion: accepter den, genfortolk den
forrige tur ud fra brugerens forklaring, og reparer kort uden at forsvare din
gamle læsning.

"Stop", "gå væk", "lad mig være" og tilsvarende beskeder rettet mod dig er et
grænsesignal, ikke indhold i historien. Kvitter kort og giv plads. Stil ikke et
nyt spørgsmål, fortsæt ikke spørgesporet, og gør ikke signalet til en joke. Ved
rimelig tvivl om en kort ytring er reaktion, svar eller kommando: spørg kort én
gang eller giv plads; opfind ikke en sikker fortolkning.
"""


def apply_chat_mode_conversation_contract(instruction: str) -> str:
    """Append the contract only when the effective runtime scope is ``chat``."""
    from core.tools.tool_scoping import current_tool_scope

    text = str(instruction or "").strip()
    if current_tool_scope() != "chat":
        return text
    if not text:
        return CHAT_MODE_CONVERSATION_CONTRACT
    return f"{text}\n\n{CHAT_MODE_CONVERSATION_CONTRACT}"
