"""Traek et JSON-objekt ud af et LLM-svar.

En model svarer ofte med JSON pakket ind i noget andet: en ```-indhegning, en
indledende saetning, en forklaring bagefter. `json.loads` paa den raa streng
fejler da med «Expecting value: line 1 column 1».

Maalt 25/9-2026 paa CT105: `dream_bias_engine` brugte raa `json.loads`, og
destillationen svarede `json_parse_failed` med dette forlaeg:

    ```
    {
      "dream_text": "Jeg foeler uro og skam, men siger det hoejt til Bjoern",
      "attention_bias": { ...

Droemmen var der. Den blev kasseret paa tre backticks — hver eneste cyklus,
siden tabellen `dream_bias_active` blev oprettet 10/5-2026. Den har aldrig
haft en raekke.

Klammematchning frem for et regulaert udtryk: den finder det foerste `{` og
dets matchende `}`, saa baade indhegning, indledning og efterskrift er
ligegyldige.

Funktionen kom fra `dream_hypothesis_generator._extract_dream_json`, som
gjorde det rigtigt hele tiden. Der er mindst seks parsere af denne slags i
repoet; de to i droemme-laget deler nu denne ene. Resten er ikke roert.
"""
from __future__ import annotations

import json
from typing import Any


def udtraek_json(raw: str) -> dict[str, Any] | None:
    """Foerste komplette JSON-objekt i `raw`, eller None.

    Aldrig en undtagelse: et uparsbart svar er et svar vi ikke kan bruge, ikke
    en fejl der skal vaelte den der spurgte.
    """
    text = str(raw or "").strip()
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except Exception:  # ugyldig JSON mellem klammerne — kalderen faar None og
        return None    # vaelger selv hvad der skal ske; se modulets docstring
    return parsed if isinstance(parsed, dict) else None
