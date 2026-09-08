"""Er dette en tanke — eller er det maskineriet der taler?

Bjoern 8/9-2026: «noget leaker ind i» de proaktive spoergsmaal. Det gjorde der.
Det her stod som hans tanker i `proactivity-bridge`:

    • I'll test it going forward) - Conductor mode: clarify - Most salient item:
      Visible run completed after tools: readdreams, readchronicles, bash, ...
    • Should include a "thought" and optionally an "initiative" (real next step
      if genuine, el
    • Initiative: a genuine next step — perhaps re-reading the witness trace

Tre ting laekkede: den indre daemons egen telemetri (conductor mode, salient
item, tool-listen), generatorens OUTPUT-KONTRAKT gengivet i stedet for opfyldt,
og fragmenter revet midt over.

Der fandtes allerede et vaern — ``visible_inner_life._is_instruction_echo`` —
men det er en haandholdt fraseliste, og den daekkede ingen af disse tre. Det er
samme moenster som resten af huset: en ordliste udskyder bare den naeste
formulering. Derfor er der her OGSAA strukturelle proever, som ikke skal
vedligeholdes:

* **Telemetri-formen.** To eller flere ``Etiket: vaerdi``-led bundet sammen med
  » - «. Ingen skriver en tanke i den form; det er en datastruktur der er blevet
  til en streng.
* **Kontrakt-ekko.** Teksten naevner sine egne outputfelter i anfoerselstegn
  (»thought«, »initiative«, »mode«) — eller BEGYNDER med et af dem som etiket
  («Initiative: a genuine next step ...»). Modellen har udfyldt skemaet og
  sendt skemaet med i stedet for indholdet.
* **Afrevet fragment.** Uafbalancerede parenteser eller anfoerselstegn, eller en
  tekst der ender midt i et ord. Et stykke raesonnement uden sin sammenhaeng.

Fraselisten er beholdt som supplement, ikke som hovedvaern.

Self-safe: enhver fejl → tom streng (behold teksten). Et vaern maa ikke kunne
tie hele den proaktive kanal ihjel.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# To eller flere «Etiket: vaerdi»-led bundet med » - «.
#
# STRAMMET 8/9-2026, samme dag som vaernet kom til. Foerste udgave kasserede
# 3 af hans 12 aegte droemme-beskeder: naar whitespace kollapses, bliver en
# markdown-liste
#
#     Tre artefakter skrevet:
#     - **Dream note** (`...md`) — observationer, forbindelser
#     - **Hypothesis candidates** (`...`) — to nye: MSATI (0.45)
#
# til «skrevet: - **Dream note** … — … candidates …: to nye», og det ligner
# telemetri paa en prik. To stramninger, begge strukturelle:
#
#   * etiketten maa ikke baere markdown (`*`, backtick) — en telemetri-etiket
#     er et rent noeglenavn, en listepost er formateret prosa.
#   * vaerdien maa ikke begynde med en listemarkoer (`-`, `*`) eller backtick.
#     «Tre artefakter skrevet: - **Dream note** …» blev ellers laest som
#     etiket «Tre artefakter skrevet» med vaerdien «- **Dream note**».
#   * moensteret skal begynde inden for de foerste 60 tegn. En serialiseret
#     datastruktur har ingen prosa-optakt; en saetning med en liste i har.
#
# Den aegte laekage der ellers ville slippe («I'll test it going forward) -
# Conductor mode: clarify - …», hvor telemetrien starter sent) fanges stadig —
# af den uafbalancerede parentes.
_ETIKET = r"[A-Za-zÆØÅæøå][A-Za-zÆØÅæøå0-9 _]{0,28}"
_VAERDI_START = r"[^\s*`\-—]"
_TELEMETRI = re.compile(
    r"^.{0,60}?" + _ETIKET + r":\s*" + _VAERDI_START
    + r".*?\s+[-—]\s+" + _ETIKET + r":\s*" + _VAERDI_START
)

# Outputfelterne naevnt i anfoerselstegn = kontrakten gengivet, ikke opfyldt.
_KONTRAKT = re.compile(
    r"[\"'«»](thought|initiative|mode|voice|tanke|initiativ)[\"'«»]", re.IGNORECASE
)

# Teksten BEGYNDER med et af outputfelterne som etiket — «Initiative: a genuine
# next step ...». Modellen har udfyldt skemaet og sendt skemaet med.
_FELT_SOM_ETIKET = re.compile(
    r"^\s*(thought|initiative|mode|voice|tanke|initiativ|reflection)\s*:",
    re.IGNORECASE,
)

_PAR = {"(": ")", "[": "]", "{": "}"}


def _uafbalanceret(tekst: str) -> bool:
    """Flere lukke- end aabne-tegn = teksten begyndte foer den blev revet ud."""
    for aab, luk in _PAR.items():
        if tekst.count(luk) > tekst.count(aab):
            return True
    return tekst.count('"') % 2 == 1


def _ender_midt_i_et_ord(tekst: str) -> bool:
    """«... if genuine, el» — afkortet mellem to bogstaver uden tegnsaetning.

    Kraever et kort halehale-ord OG at teksten er lang nok til at afkortning er
    den sandsynlige forklaring; ellers ville «Ja» og «Kom nu» blive afvist.
    """
    t = (tekst or "").rstrip()
    if len(t) < 60 or not t or not t[-1].isalpha():
        return False
    sidste = t.split()[-1] if t.split() else ""
    return 1 <= len(sidste) <= 2


def ligner_ikke_en_tanke(tekst: str) -> str:
    """Grund til at kassere teksten. Tom streng = behold den.

    Raekkefoelgen er billigst foerst: strukturen afgoeres uden opslag, mens
    fraselisten og udbyder-vaernet importerer andre moduler.
    """
    t = " ".join(str(tekst or "").split()).strip()
    if not t:
        return "tom"

    if _TELEMETRI.search(t):
        return "telemetri"
    if _KONTRAKT.search(t) or _FELT_SOM_ETIKET.match(t):
        return "kontrakt-ekko"
    if _uafbalanceret(t):
        return "afrevet fragment"
    if _ender_midt_i_et_ord(t):
        return "afkortet"

    try:
        from core.services.visible_inner_life import _is_instruction_echo
        if _is_instruction_echo(t):
            return "instruks-ekko"
    except Exception as exc:
        logger.debug("thought_leak_guard: fraseliste utilgaengelig: %s", exc)

    try:
        from core.services.provider_error_guard import looks_like_provider_error
        if looks_like_provider_error(t):
            return "udbyder-fejl"
    except Exception as exc:
        logger.debug("thought_leak_guard: udbyder-vaern utilgaengeligt: %s", exc)

    return ""
