"""Én synlig grænse for første modelsvar.

Første pas har FIRE former for model-kontekst der aldrig må nå mennesket:
capability-markup, runtime-markører, DeepSeek's interne tool-call-DSL
(``<｜｜DSML｜｜ …>``) og den HALVE form af samme DSL — et bart værktøjsnavn
efterfulgt af rå ``<parameter name=…>``-tags uden nogen DSML-omslag.
Tidsstempler hører til den anden kategori: de bliver i transskriptet, men en
model-efterligning fjernes her.

DSML-leddet blev tilføjet 30/10-2026 efter Bjørns «nu leaker du osse». Stripperen
fandtes allerede (``cheap_provider_runtime_adapters._strip_dsml_leak``) og var
koblet på tre veje — men ikke på denne, som er den Bjørns EGEN tur kører.
Målt før fixet: 5 DSML-tokens gik uhindret igennem til den gemte besked.

Den halve form blev fundet i samme måling: besked 236732 bar `[remember_this">`
efterfulgt af 4.500 tegn rå `<parameter>`-tags. Kun 3 af 14.297
assistant-beskeder har formen — men de er ulæselige når de rammer.

Udskilt fra ``visible_runs.py`` efter Boy Scout-reglen. Kalderen behøver kun
``feed`` og ``flush`` og kan derfor ikke glemme at skylle state-maskinerne.
"""
from __future__ import annotations

import re

from core.services.cheap_provider_runtime_adapters import _strip_dsml_leak
from core.services.prompt_sections.capability_markup import _CapabilityMarkupBuffer
from core.services.visible_text_scrub import StroemSkrubber

# Den halve DSL-form: et værktøjsnavn i kantede parenteser (evt. med et halvt
# citationstegn) efterfulgt af rå parameter-tags. Ankret på at der FAKTISK
# følger en parameter — ellers ville almindelig omtale af `[bash]` blive ædt.
_HALV_DSL_RE = re.compile(
    r"\[[A-Za-z_][A-Za-z0-9_]*\"?>?\s*\n?\s*<parameter\s+name=",
)
# Selve tag'ene — åbning som lukning, både `parameter` og `invoke`. Værdien
# imellem dem er ægte indhold og skal blive stående; det er markup'en der er
# lækagen. `invoke` kom med 30/10-2026: besked 236732 endte med en bar
# `</invoke>` efter den halve form var ryddet — samme lækage i tredje form.
_PARAM_TAG_RE = re.compile(r"</?(?:parameter|invoke)[^>]*>")
# 30/10-2026: her stod en `_BARE_CLOSER_RE` der fjernede ALLE DSML-lukkere før
# stripperen så dem. Det var forkert: den spiste også den legitime `</calls>` der
# afslutter en blok, så blokken aldrig sluttede og alt teksten efter den forsvandt
# (målt: «Anden del af svaret.» blev ædt). Lukkere uden åbner håndteres nu INDE i
# `_strip_dsml_leak` som markup-rester — der kendes forskellen på en rest og en
# rigtig lukker.


class FirstPassOutputFilter:
    """Filtrér capability-markup, DSML og synlige runtime-markører — i den rækkefølge."""

    def __init__(self) -> None:
        self._markup = _CapabilityMarkupBuffer()
        self._synlig = StroemSkrubber()
        # DSML-stripperens tilstand: en åbner kan komme før sin closer, og en
        # hale kan være starten på en åbner vi ikke har set færdig endnu.
        self._dsml_hale = ""
        self._dsml_i_blok = False
        # Den halve form kan ikke afgøres før vi ved om der følger en parameter,
        # så vi holder en hale tilbage mens den er en mulig åbner.
        self._halv_hale = ""

    def _dsml(self, text: str) -> str:
        if not text:
            return ""
        # Ingen forfiltrering her: `_strip_dsml_leak` kender selv forskellen på
        # en markup-rest (lukker uden åbner) og en rigtig lukker. Lagde vi et
        # regex-lag foran, spiste det de legitime lukkere — og så løb blokken
        # til verdens ende.
        rent, self._dsml_hale, self._dsml_i_blok = _strip_dsml_leak(
            self._dsml_hale + text, self._dsml_i_blok
        )
        return rent

    def _halv(self, text: str) -> str:
        """Fjern den halve DSL-form: navnet og de rå tags — men BEHOLD indholdet.

        Målt 30/10-2026 på besked 236732: den halve form omsluttede et helt
        gyldigt argument (4.500 tegn hukommelsespost). At fjerne blokken ville
        kaste indholdet væk; det er tag'ene der er lækagen, ikke teksten.
        """
        if not text:
            return ""
        buffer = self._halv_hale + text
        self._halv_hale = ""
        m = _HALV_DSL_RE.search(buffer)
        if not m:
            # Hold en hale tilbage hvis slutningen KUNNE være starten på formen.
            hale = 0
            for k in range(1, min(64, len(buffer)) + 1):
                if _HALV_DSL_RE.match(buffer[-k:] + "<parameter name="):
                    hale = max(hale, k)
            if hale:
                self._halv_hale = buffer[-hale:]
                return buffer[:-hale]
            return buffer
        # Behold teksten FØR navnet, fjern navnet, og fjern derefter hver
        # parameter-tag (åbning som lukning) men behold værdien imellem dem.
        hoved = buffer[: m.start()]
        rest = buffer[m.end():]
        # `m.end()` står efter `name=` — spis resten af den første tag.
        while rest and rest[0] not in ">\n":
            rest = rest[1:]
        if rest.startswith(">"):
            rest = rest[1:]
        # Fjern alle efterfølgende parameter-tags, behold indholdet.
        rest = _PARAM_TAG_RE.sub("", rest)
        return hoved + rest

    def feed(self, text: str) -> str:
        # Rækkefølgen er bindende: `_halv` FØRST. Den halve form omslutter ægte
        # indhold, og kører DSML-leddet først, ser det `</invoke>` inde i den
        # halve blok som en åbner og æder alt til næste closer — målt 30/10-2026:
        # 1.671 tegn ægte svar forsvandt på besked 236732.
        return self._synlig.foed(self._markup.feed(self._dsml(self._halv(text))))

    def flush(self) -> str:
        dele: list[str] = []
        # En hale der stadig venter på sin closer er en uafsluttet DSML-blok:
        # den skal DØ her, ikke slippes ud. Er vi ikke i en blok, er halen en
        # mulig åbner der aldrig blev færdig — den er ufarlig prosa og slippes.
        if self._dsml_hale and not self._dsml_i_blok:
            dele.append(self._synlig.foed(self._markup.feed(self._dsml_hale)))
        self._dsml_hale = ""
        self._dsml_i_blok = False
        if self._halv_hale:
            dele.append(self._synlig.foed(self._markup.feed(self._halv_hale)))
        self._halv_hale = ""
        markup_rest = self._markup.flush()
        if markup_rest:
            dele.append(self._synlig.foed(markup_rest))
        dele.append(self._synlig.skyl())
        return "".join(dele)


__all__ = ["FirstPassOutputFilter"]
