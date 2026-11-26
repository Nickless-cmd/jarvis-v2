"""core/services/raw_provider_capture.py

Rå provider-bytes, fanget FØR adapteren ser dem (26/11-2026).

## Spørgsmålet

`_promote_last_text_block_to_answer` udpeger turens SIDSTE tekstblok som
svaret. Det er en antagelse, ikke en måling — og den holder ikke for
progressiv levering (lever A, kald, lever B: så bliver A og B stemplet som
«arbejde» og foldet væk, mens B bliver svaret).

Runtime har ingen eksplicit repræsentation af om en tekstblok er kommentar
eller levering. Fasen gættes BAGEFTER ud fra hvad modellen gjorde derefter.

Det principielle krav (GPT, 26/11-2026): *en tekstbloks semantiske rolle må
aldrig afhænge af hvilke hændelser der kommer efter den.*

## Hvorfor dette modul findes

Før nogen bygger et leveringssignal skal vi vide om udbyderen ALLEREDE
sender ét. Vi har 26.558 gemte payloads — men de er NORMALISEREDE
(`text`, `reasoning_content`, `tool_calls`). Capture ligger EFTER adapteren,
så de er ikke observationer af udbyderens protokol. De kan ikke falsificere
«provideren sender et felt vi kaster».

Adapterens FØRSTE filter er::

    if not line.startswith("data: "):
        continue

Alt andet — `event:`-linjer, keepalives, udbyder-specifikke extensions —
bliver kastet uden at nogen har spurgt hvad det betød. Dette modul fanger
linjen FØR det filter.

## To udgange, fordi de svarer på to forskellige spørgsmål

* ``capture.jsonl`` — de rå linjer, afgrænset og redigeret. **Beviset.**
* ``skema.json``    — hvilke nøglestier er set, på tværs af alle kald.
  **Svaret** på «findes der et `channel`-felt?» uden at læse tusind payloads.

Skemaet er akkumulerende og provider-agnostisk: nøglen er
``provider → sti``, så et felt der kun findes hos én udbyder ikke drukner i
mængden fra en anden.

## Afgrænsning

* Max ``_MAX_LINJER_PR_KALD`` (80) linjer pr. kald — nok til at se hele
  skemaet i én tur. Derudover fanges altid: ikke-``data:``-linjer,
  usage-chunks, finish_reason og ``[DONE]``, fordi det er der
  protokol-oplysningerne ligger.
* Max ``_MAX_BYTES_PR_LINJE`` (4.000) bytes pr. linje.
* Rotation ved ``_MAX_FIL_BYTES`` (5 MB) → ``capture.jsonl.1``.
* API-nøgler og Bearer-tokens redigeres før skrivning. Selve
  tekst-indholdet kan ikke redigeres væk — det er dét vi undersøger.

## Arméres med

::

    touch /tmp/jarvis-raw-provider

Self-safe: kaster aldrig, og koster ét ``os.path.exists`` pr. STREAM —
ikke pr. linje — fordi ``armeret()`` kaldes én gang før løkken i
``_iter_openai_compatible_chat_events``.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import UTC, datetime

_SENTINEL = "/tmp/jarvis-raw-provider"
# ⚠️ Må ALDRIG være samme sti som `_SENTINEL`: sentinel er en FIL (touch),
# og `os.makedirs` på en fil-sti fejler. Målt 26/11-2026 — de to hed det
# samme i første udgave, så `armeret()` svarede True, kaldet kørte, og der
# blev skrevet NUL. Fejlen var tavs fordi self-safe'en slugte den.
# `prompt_dump` bruger `jarvis-prompt-dump` + `jarvis-prompt-dumps`; samme
# skelnen. Vagt: `test_sentinel_og_mappe_er_forskellige_stier`.
_DIR = "/tmp/jarvis-raw-provider-data"
_CAPTURE = os.path.join(_DIR, "capture.jsonl")
_SKEMA = os.path.join(_DIR, "skema.json")

_MAX_LINJER_PR_KALD = 80
_MAX_BYTES_PR_LINJE = 4000
_MAX_FIL_BYTES = 5 * 1024 * 1024
_SKEMA_FLUSH_HVERT = 25

# Nøgler og tokens må aldrig lande i filen. Rækkefølgen betyder noget:
# de brede mønstre kører først, ellers kan et smalt mønster efterlade resten.
_REDAKTION: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), "[REDAKTERET_API_KEY]"),  # pragma: allowlist secret
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}"), "Bearer [REDAKTERET]"),
    (
        re.compile(
            r'"(api_key|authorization|access_token|refresh_token|secret)"'
            r'\s*:\s*"[^"]{6,}"'
        ),
        r'"\1": "[REDAKTERET]"',
    ),
)

_lock = threading.Lock()
_skema: dict[str, dict[str, int]] = {}
_siden_flush = 0
_advarsel_givet = False


def _advarsel_én_gang(exc: BaseException) -> None:
    """Sig det ÉN gang hvis capture ikke kan skrive.

    Self-safe betyder «må ikke vælte turen» — ikke «må fejle i stilhed».
    Målt 26/11-2026: en sti-kollision gjorde hver skrivning umulig, og den
    tavse `pass` gjorde at værktøjet så ud som om det virkede mens det skrev
    nul. Tavshed er den rigtige vej inde i stream-stien, men den skal siges
    én gang, ellers er målingen blind.
    """
    global _advarsel_givet
    if _advarsel_givet:
        return
    _advarsel_givet = True
    try:
        import sys

        print(
            f"[raw_provider_capture] SKRIVER IKKE: {type(exc).__name__}: {exc} "
            f"(mappe={_DIR})",
            file=sys.stderr,
        )
    except Exception:  # self-safe
        pass


def armeret() -> bool:
    """Er capture tændt? Kaldes ÉN gang pr. stream, ikke pr. linje."""
    try:
        return os.path.exists(_SENTINEL)
    except Exception:  # self-safe: et sentinel-tjek må ikke ramme streamen
        return False


def _rediger(tekst: str) -> str:
    for moenster, erstatning in _REDAKTION:
        tekst = moenster.sub(erstatning, tekst)
    return tekst


def _walk(obj: object, sti: str = "", dybde: int = 0):
    """Yield (nøglesti, typenavn) for hver nøgle i et parset event.

    Lister repræsenteres som ``[]`` og der kigges kun på de to første
    elementer — formen er den samme resten af listen, og et tool_calls-array
    kan være langt.
    """
    if dybde > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            s = f"{sti}.{k}" if sti else str(k)
            yield s, type(v).__name__
            yield from _walk(v, s, dybde + 1)
    elif isinstance(obj, list):
        for item in obj[:2]:
            yield from _walk(item, sti + "[]", dybde + 1)


def _roter_hvis_stor() -> None:
    try:
        if os.path.getsize(_CAPTURE) < _MAX_FIL_BYTES:
            return
        os.replace(_CAPTURE, _CAPTURE + ".1")
    except Exception:  # self-safe: rotation er bekvemmelighed, ikke kritisk
        pass


def noter_linje(*, provider: str, model: str, linje: str, linje_nr: int) -> None:
    """Skriv én rå SSE-linje, som udbyderen sendte den.

    Kaldes FØR adapterens ``startswith("data: ")``-filter, så ikke-data-events
    også fanges. Afgrænset: efter de første ``_MAX_LINJER_PR_KALD`` linjer
    gemmes kun linjer der bærer protokol-oplysning.
    """
    try:
        interessant = (
            linje_nr <= _MAX_LINJER_PR_KALD
            or not linje.startswith("data: ")
            or '"usage"' in linje
            or '"finish_reason"' in linje
            or linje.endswith("[DONE]")
        )
        if not interessant:
            return
        linje = _rediger(linje)
        if len(linje) > _MAX_BYTES_PR_LINJE:
            linje = linje[:_MAX_BYTES_PR_LINJE] + "…[KLIPPET]"
        post = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "provider": provider,
            "model": model,
            "nr": linje_nr,
            "linje": linje,
        }
        with _lock:
            os.makedirs(_DIR, exist_ok=True)
            _roter_hvis_stor()
            with open(_CAPTURE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(post, ensure_ascii=False) + "\n")
    except Exception as exc:  # self-safe: en capture må aldrig vælte en tur
        _advarsel_én_gang(exc)


def noter_event(*, provider: str, model: str, event: object) -> None:
    """Registrér nøglestierne i et parset event i skema-indekset.

    Kun FORMEN gemmes — ikke værdierne. Det er dét der gør det muligt at
    svare på «findes der et felt vi ikke læser?» uden at læse payloads.
    """
    global _siden_flush
    try:
        nye: list[tuple[str, str]] = list(_walk(event))
        if not nye:
            return
        with _lock:
            gren = _skema.setdefault(str(provider or "?"), {})
            for sti, typenavn in nye:
                noegle = f"{sti}:{typenavn}"
                gren[noegle] = gren.get(noegle, 0) + 1
            _siden_flush += 1
            if _siden_flush >= _SKEMA_FLUSH_HVERT:
                _siden_flush = 0
                _skriv_skema()
    except Exception as exc:  # self-safe
        _advarsel_én_gang(exc)


def _skriv_skema() -> None:
    """Skriv det akkumulerede skema. Kaldes under _lock."""
    try:
        os.makedirs(_DIR, exist_ok=True)
        with open(_SKEMA, "w", encoding="utf-8") as fh:
            json.dump(_skema, fh, indent=2, ensure_ascii=False, sort_keys=True)
    except Exception:  # self-safe
        pass


def afslut_kald() -> None:
    """Flush skemaet ved kald-slut, så en kort stream ikke efterlader det tomt."""
    try:
        with _lock:
            _skriv_skema()
    except Exception:  # self-safe
        pass


def skema_rapport() -> dict[str, dict[str, int]]:
    """Læs det akkumulerede skema fra disk (til diagnose uden for streamen)."""
    try:
        with open(_SKEMA, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:  # en manglende/utæt skema-fil betyder «intet målt endnu»,
        # ikke en fejl — tom rapport er det ærlige svar, og kalderen skal kunne
        # spørge uden at skulle skelne de to tilfælde.
        return {}


def nulstil() -> None:
    """Ryd skema og capture. Til brug i tests og ved en ny målerunde."""
    global _siden_flush
    with _lock:
        _skema.clear()
        _siden_flush = 0
        for sti in (_CAPTURE, _CAPTURE + ".1", _SKEMA):
            try:
                os.remove(sti)
            except Exception:  # filen findes måske ikke — det er netop det
                # nulstilling skal tillade. Kun FileNotFoundError forventes;
                # en anden fejl ville vise sig ved næste skrivning, hvor
                # `_advarsel_én_gang` siger den højt.
                pass
