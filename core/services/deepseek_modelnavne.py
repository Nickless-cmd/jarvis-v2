"""Hvad DeepSeeks modeller HEDDER — ét sted.

## Hvorfor filen findes

`deepseek-v4-flash` er et LEGACY-navn. Verificeret mod API'en 1/10-2026 ved at
sende et kald med hvert navn og læse `model` i svaret:

    anmodet: deepseek-v4-flash   -> svarede som: 'deepseek-flash'
    anmodet: deepseek-chat       -> svarede som: 'deepseek-flash'
    anmodet: deepseek-v4-pro     -> svarede som: 'deepseek-v4-pro'

og `GET /models` udstiller præcis to id'er: `deepseek-flash` og
`deepseek-v4-pro`. Deres dokumentation siger det samme: de gamle navne
accepteres stadig, men modellerne bag er taget ud af drift, og kaldene serveres
af DeepSeek-V4.1-Flash til Flash-pris.

## Hvorfor det er samlet her

Navnet lå spredt i SEKS medlemskabstests og TO pristabeller. Hver af dem var en
selvstændig kopi af den samme viden, og de var allerede drevet fra hinanden:
`vision_backend` kendte det kanoniske navn og brugte det, mens thinking-testen
og begge pristabeller kun kendte det gamle. Et skift af konfigurationen ville
derfor have slået thinking fra og sendt prisen til nul — i stilhed, hver for sig.

Sættene her indeholder BEGGE navne med vilje. Så virker de både før og efter et
konfigurations-skift, og en gammel `runtime.json` et andet sted i huset bliver
ikke pludselig forkert.
"""
from __future__ import annotations

from typing import Final

#: Det navn DeepSeek selv bruger i dag. Nye konfigurationer skal pege her.
KANONISK_FLASH: Final[str] = "deepseek-flash"
KANONISK_PRO: Final[str] = "deepseek-v4-pro"

#: Alle navne der i praksis serveres af `deepseek-flash`.
FLASH_NAVNE: Final[frozenset[str]] = frozenset({
    "deepseek-flash",
    "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp",
})

#: Modeller hvis API KRÆVER at tidligere assistant-ture bærer
#: `reasoning_content`. Uden strip af de øvrige afvises requesten.
#:
#: `deepseek-chat` og `deepseek-reasoner` er også aliaser for flash, men de stod
#: forskelligt i de seks kopier: nogle havde `deepseek-reasoner` med, ingen
#: havde `deepseek-chat`. Sættet her bevarer den adfærd præcist og tilføjer kun
#: det kanoniske navn — en udvidelse til `deepseek-chat` ville være en
#: adfærdsændring ingen har bedt om.
THINKING_MODELLER: Final[frozenset[str]] = frozenset({
    "deepseek-flash",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "deepseek-reasoner",
})


def er_flash(model: str) -> bool:
    """Serveres denne model af `deepseek-flash`?"""
    return (model or "").strip() in FLASH_NAVNE


def er_thinking_model(model: str, *, provider: str = "deepseek") -> bool:
    """Kræver modellen `reasoning_content` på tidligere assistant-ture?

    `provider` er med, fordi alle kaldssteder i forvejen tjekker den: et
    model-navn alene siger ikke hvem der svarer, og et andet hus kan have en
    model med samme navn.
    """
    return (provider or "").strip() == "deepseek" and (model or "").strip() in THINKING_MODELLER
