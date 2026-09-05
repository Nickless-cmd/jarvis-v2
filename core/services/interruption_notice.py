"""Afbrydelses-noten — en besked til MENNESKET, ikke til modellen.

Naar et run afbrydes midt-flugt persisteres en rolig linje i sessionen, saa
Bjoern ved genindlaesning ser HVORFOR der blev stille i stedet for ingenting.
Det er en god ting og skal blive.

**Men den maa ikke ind i historikken modellen faar.** Maalt 5/9-2026:

    45 stubs paa tvaers af systemet, klumpet: 16 i én session, saa 8, 7, 4, 2

Klumpningen ER symptomet. Da tre af dem laa i traek i én session, svarede
DeepSeek paa en helt almindelig prompt ved at skrive den SAMME saetning igen —
ord for ord, som en delta-stroem, `first_pass_status: completed`,
`native_tool_call_count: 0`. Modellen efterlignede sin egen historik.

Konsekvensen er grim: ét aegte cut skaber en stub, stubben faar modellen til at
producere endnu en, og fra da af «cuttes» han i hver tur i den session — uden at
noget som helst er galt. Brugeren oplever konstante afbrydelser; i
virkeligheden blev han afbrudt én gang og papegoejer siden.

Derfor: behold noten for mennesket, filtrér den ud af det modellen ser.
"""
from __future__ import annotations

# Ordret den tekst der persisteres ved afbrydelse. ÉN sandhed, saa skriveren og
# filteret ikke kan drive fra hinanden — dét er praecis hvordan et filter bliver
# stille virkningsloest.
INTERRUPTION_NOTICE = (
    "Jeg blev afbrudt midt i det — svaret nåede ikke helt ud. "
    "Skriv bare igen, så samler jeg tråden op."
)

# Kortere kendetegn, saa smaa variationer (tegnsaetning, en tilfoejet linje)
# stadig genkendes. Snaevert nok til aldrig at ramme et aegte svar.
_KENDETEGN = "blev afbrudt midt i det"


def is_interruption_notice(text: str) -> bool:
    """Er dette runtimens afbrydelses-note frem for et aegte svar? Self-safe."""
    try:
        t = (text or "").strip()
        if not t or len(t) > 400:
            return False
        return _KENDETEGN in t.lower()
    except Exception:
        return False


def strip_interruption_notices(history: list) -> list:
    """Fjern afbrydelses-noter fra den historik modellen faar. Self-safe.

    Kun ASSISTENT-beskeder: skriver brugeren selv noget om at blive afbrudt, er
    det en aegte ytring og skal blive staaende.
    """
    try:
        ud = []
        for m in history or []:
            rolle = (m.get("role") if isinstance(m, dict) else None) or ""
            indhold = (m.get("content") if isinstance(m, dict) else "") or ""
            if rolle == "assistant" and is_interruption_notice(str(indhold)):
                continue
            ud.append(m)
        return ud
    except Exception:
        return history or []
