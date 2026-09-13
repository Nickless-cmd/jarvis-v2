"""Opløs et bart ollama-modelnavn til det tag ollama faktisk serverer.

## Hvorfor det findes — og hvorfor det ligger HER

Ollama registrerer cloud-modeller med et tag: `glm-5.2:cloud`. Sender man det
bare navn, svarer den

    HTTP 404: {"error":"model 'glm-5.2' not found"}

Rettelsen blev lavet 23/7-2026 — men i `chat_stream_v2.py`, altså i én rute.
Autonome kørsler gaar ikke derigennem, og de sender derfor stadig det bare navn.

MAALT 13/9-2026 kl. 10:25: et autonomt wakeup-run doede paa netop den 404.
Resultatet var ikke en fejlmeddelelse til Bjoern, men et svar hvor Jarvis
skrev at han «ikke har adgang til at udfoere operativsystem- eller
runtime-kommandoer» og tilboed at **simulere** rapporten. Modellen faldt altsaa
tilbage til noget der lyder som en begraensning i hans rettigheder, mens
aarsagen var et manglende `:cloud`-suffiks.

Derfor ligger opslaget nu i et servicemodul og kaldes dér hvor navnet BRUGES —
i selve ollama-kaldet — i stedet for hos hver kalder der maatte huske det.
Samme princip som notifikations-vagterne: den hoerer til hos porten.

Fail-open hele vejen: kan ollama ikke naas, eller findes der ikke et bedre tag,
returneres navnet uaendret. Et opslag der fejler maa aldrig kunne stoppe et kald
der ellers ville virke.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

_TAGS_TTL_S = 120.0
_cache: dict[str, object] = {"tags": set(), "ts": 0.0}


def _base_url() -> str:
    base = "http://127.0.0.1:11434"
    try:
        from core.runtime.settings import load_settings
        b = str(getattr(load_settings(), "embed_ollama_base_url", "") or "").strip()
        if b:
            return b.rstrip("/")
    except Exception:
        pass
    return base


def served_tags() -> set[str]:
    """De modelnavne ollama serverer lige nu. Cachet 120 s; tom maengde ved fejl."""
    nu = time.monotonic()
    cached = _cache.get("tags") or set()
    if cached and (nu - float(_cache.get("ts") or 0)) < _TAGS_TTL_S:
        return set(cached)
    tags: set[str] = set()
    try:
        with urllib.request.urlopen(_base_url() + "/api/tags", timeout=3) as r:
            data = json.loads(r.read())
        for m in (data.get("models") or []):
            navn = str(m.get("name") or "").strip()
            if navn:
                tags.add(navn)
    except Exception:
        logger.debug("ollama_model_names: kunne ikke hente tags", exc_info=True)
        return set(cached)
    _cache["tags"] = tags
    _cache["ts"] = nu
    return set(tags)


def resolve_model_name(model: str) -> str:
    """`glm-5.2` → `glm-5.2:cloud` naar den variant findes. Ellers uaendret."""
    m = (model or "").strip()
    if not m:
        return m
    tags = served_tags()
    if not tags or m in tags:
        return m
    for kandidat in (f"{m}:cloud", f"{m}:latest"):
        if kandidat in tags:
            logger.info("ollama: opløste bart modelnavn %s → %s", m, kandidat)
            return kandidat
    return m
