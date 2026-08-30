"""Provider-fejl-vagt — fang "providerens fejlbesked blev til Jarvis' svar".

Set live 30-08-2026 kl. 10:04:26 UTC. Denne tekst blev gemt som et ASSISTENT-svar
i Bjørns samtale, og kørslen talte som ``completed``::

    Sorry, to prevent abuse of free resources, accounts that have not been
    recharged can only try 10 times. You can increase the free quota after
    recharging; https://console.aihubmix.com/topup…

Det er en kvote-afvisning fra aihubmix. Den blev hverken opdaget som fejl,
logget som fejl eller vist som fejl — den passerede som indhold. Kørslen stod
som fuldført med et "svar" der i virkeligheden var en regning fra en tredjepart.

Samme princip som ``PresentationInvariantError`` i ``visible_runs``: tekst der
tydeligvis ikke er Jarvis må aldrig nå den synlige chat. Forskellen er kun at
dét værn fanger INTERNE artefakter (tool-markører), mens dette fanger FREMMED
tekst fra en udbyder.

Rent + side-effekt-frit → unit-testbart. Bevidst KONSERVATIVT: kræver både et
fejl-signal OG at teksten er kort nok til at være en ren fejlbesked, så et langt,
ægte svar der tilfældigvis nævner "quota" ikke kasseres.
"""

from __future__ import annotations

import re

# Fejl-signaler fra udbydere. Bevidst konkrete — ikke bare "error", som optræder
# i massevis af legitime svar om kode.
_ERROR_SIGNALS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bfree (quota|resources|tier)\b",
        r"\b(recharg|top ?up|topup)\w*\b",
        r"\bquota (exceeded|exhausted|reached|limit)\b",
        r"\b(rate|usage) limit (exceeded|reached)\b",
        r"\binsufficient (quota|credit|balance|funds)\b",
        r"\b(invalid|expired|missing|incorrect) api[_ ]?key\b",
        r"\b(unauthorized|forbidden|payment required)\b",
        r"\byour (account|balance|credits?) (has|have|is|are)\b.{0,40}\b(insufficient|exhausted|empty|run out)\b",
        r"https?://\S*(topup|billing|pricing|console)\S*",
        r"\bplease (try again later|contact support)\b",
        r"\bmodel (not found|does not exist|is not available)\b",
        r"\bservice (unavailable|overloaded)\b",
    )
)

# Udbydere svarer ALDRIG på dansk. Jarvis skriver dansk til Bjørn. Det er det
# stærkeste enkeltsignal vi har, og det fangede en falsk positiv i test: et langt
# dansk svar der HANDLEDE om rate limits blev ellers kasseret som en udbyder-fejl.
_DANISH = re.compile(
    r"[æøåÆØÅ]|\b(jeg|ikke|som|hvis|kunne|skal|derfor|altså|selv|men|også|"
    r"hvordan|hvorfor|indtil|hverken|netop)\b", re.IGNORECASE)

# En ægte fejlbesked fra en udbyder er kort. Bliver teksten lang, er det langt mere
# sandsynligt at Jarvis SKRIVER om kvoter (fx en rapport om cheap-lanen) end at
# udbyderen har svaret. Grænsen er rundhåndet nok til at rumme en typisk API-fejl.
_MAX_ERROR_CHARS = 320

# Stærke markører der alene er nok, uanset længde — de kan aldrig stå i et svar
# Jarvis selv har formuleret på dansk til Bjørn.
_DECISIVE: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^\s*sorry, to prevent abuse of free resources",
        r"^\s*\{\s*\"error\"\s*:",
        r"^\s*(error|fejl)\s*:\s*\d{3}\b",
    )
)


def looks_like_provider_error(text: str) -> bool:
    """True hvis `text` ligner en udbyders fejlbesked frem for Jarvis' svar.

    Konservativ: ved enhver tvivl False, så et ægte svar aldrig kasseres.
    Self-safe — kaster aldrig.
    """
    try:
        if not text:
            return False
        t = text.strip()
        if not t:
            return False
        if any(rx.search(t) for rx in _DECISIVE):
            return True
        if _DANISH.search(t):        # dansk ⇒ Jarvis skrev det, ikke en udbyder
            return False
        if len(t) > _MAX_ERROR_CHARS:
            return False
        # Kræv mindst ét konkret fejl-signal i en kort tekst.
        return any(rx.search(t) for rx in _ERROR_SIGNALS)
    except Exception:
        return False


def describe(text: str) -> str:
    """Kort, sikker beskrivelse til incident-beskeden. Lækker ikke hele teksten."""
    try:
        t = " ".join((text or "").split())
        return (t[:157] + "…") if len(t) > 158 else t
    except Exception:
        return "(kunne ikke beskrive)"
