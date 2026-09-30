"""Support-signalernes indhold — forbeholdet hoistet, kroppen samlet.

Udskilt fra `prompt_contract.py` 30/9-2026 (Boy Scout: filen var 4.911 linjer)
i samme ombæring som sektionen blev flyttet fra prompt-PRÆFIKSET til halen.

Hvorfor den skulle flyttes, målt på CT105 samme dag: sektionen var den SIDSTE
i det cachede præfiks, og dens indhold er et **tids-snapshot**. Bygningen er
cappet (`_HOT_RESOLVE_CAP_S`), og rammes deadline'en beholdes kun de
under-sektioner der nåede at blive færdige — resten løber videre i baggrunden.
Hvilke der nåede det afhænger af et kapløb.

Prisen blev målt direkte: to præfiks-varianter, 30.204 og 30.206 tegn, hvor
første forskel lå i chunk 29 af 30 — altså 98 % inde i systemblokken. Alligevel
overlevede kun 33 % af præfikset, og hit faldt fra 89,5 % til 79,2 %. DeepSeeks
rækkefølge er [system][tools][beskeder], så to tegn i systemblokkens hale
kostede hele værktøjsarrayet OG hele samtalen.

En sektion hvis indhold afgøres af et kapløb hører derfor efter cache-grænsen.
Det er samme flytning som tool-kataloget fik (`eacce27e9`), men med en stærkere
grund: kataloget var i det mindste forudsigeligt pr. scope.
"""
from __future__ import annotations

#: Forbeholdet. Hoistet til toppen af den samlede blok 8/9-2026: hver enkelt
#: support-bygger sluttede med den, og attention-budgettet klipper blokken ved
#: sidste linjeskift — så værnet blev klippet af mens dataen blev tilbage.
#: Målt: forbeholdet stod NUL steder i den samlede prompt. Én gang øverst
#: overlever beskæringen og fylder ikke fem gange i en blok der i forvejen er
#: for stor til sit budget.
SUBORDINAT = "Use only as subordinate support. Runtime and visible truth outrank it."


def byg_support_indhold(support_raw: list[str] | None) -> str | None:
    """Saml support-blokkene til ÉN sektion med forbeholdet øverst.

    Returnerer ``None`` når der ikke er nogen blokke — så budgettet udelader
    sektionen helt i stedet for at bære et tomt forbehold.
    """
    if not support_raw:
        return None
    krop = "\n\n".join(
        "\n".join(linje for linje in blok.split("\n") if linje.strip() != SUBORDINAT)
        for blok in support_raw
    )
    return SUBORDINAT + "\n\n" + krop
