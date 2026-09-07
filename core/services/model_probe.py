"""Prøv én model: kan den kaldes, kan den bruge værktøjer, kan den kode.

Hvorfor den findes (7/9-2026): syv udbydere kørte på 0,0 % success i ugevis —
over 7.000 spildte kald på syv døgn — og ingen af dem sagde fra. Modeller
bliver pensioneret, gratis-niveauer forsvinder, værter flytter. Katalogerne
driver, og der var intet der opdagede det.

**Den vigtigste regel her: LISTET ER IKKE KALDBAR.** Samme dag, tre beviser:

  * LLM7 lister 46 modeller — **3** svarer, 31 giver 402
  * ollama-gatewayen lister 7 — **1** er gratis, resten kræver abonnement
  * NVIDIA lister 81 — af 12 testede virkede 3, og 2 af dem ramte 30-sekunders
    loftet. Kun én var reelt brugbar.

En opdatering der KOPIERER `/v1/models` ville derfor fylde puljen med døde
pladser. Derfor prøver vi hver model i stedet.

De fire prøver måler præcis det agent-arbejde kræver — i den rækkefølge en
opgave stiller krav:

  1. `callable`   svarer den overhovedet, inden for banens tålmodighed
  2. `tools`      kalder den et værktøj når opgaven kræver det
  3. `follows`    kan den BRUGE et værktøjsresultat til at svare
  4. `code`       producerer den kode der overhovedet kan parses

Nr. 3 er den vigtigste for explore. En model der kalder et værktøj og derefter
ignorerer svaret, ligner en der arbejder og leverer ingenting — præcis det
Bjørn så da explore returnerede «Hello! How can I assist you today?».

Ingen model-skrevet kode køres. Vi parser den med `ast`; at eksekvere output
fra en tilfældig gratis-model for at give den en karakter ville være en
mærkelig pris at betale for en score.
"""
from __future__ import annotations

import ast
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Banens egen tålmodighed. En model der svarer efter 30 s er lige så ubrugelig
# som en der giver 404 — den blev MÅLT: kimi-k3 og nemotron-ultra på NVIDIA
# svarer begge korrekt, men efter loftet, og faldt derfor altid over.
PROBE_TIMEOUT_S = 30.0

# Kort pause mellem delprøverne. Uden den rammer vi udbyderens rate limit med
# vores EGEN prøve og giver modellen en dårlig karakter for vores utålmodighed
# (målt: nvidia-nim gav 429 på tredje kald).
_PAUSE_S = 1.2

# Fejl der siger «ikke nu», ikke «kan ikke». En delprøve der falder på dem
# tæller HVERKEN for eller imod — ellers mister en fungerende model sin plads
# på en travl dag.
_FORBIGAAENDE = ("429", "rate", "timeout", "timed out", "too many",
                 "unavailable", "503", "502", "overloaded")


def _er_forbigaaende(fejl: str) -> bool:
    f = str(fejl or "").lower()
    return any(t in f for t in _FORBIGAAENDE)

_VÆRKTØJ = [{
    "type": "function",
    "function": {
        "name": "slaa_op",
        "description": "Slå en værdi op i projektets register",
        "parameters": {
            "type": "object",
            "properties": {"noegle": {"type": "string", "description": "Hvad der skal slås op"}},
            "required": ["noegle"],
        },
    },
}]

# Et ord modellen umuligt kan gætte — findes kun i værktøjssvaret. Dukker det
# op i det endelige svar, HAR den læst resultatet.
_HEMMELIGT_SVAR = "kobberfasan"

_KODE_FUNKTION = "tredje_bogstav"


_VÆGTE = {"callable": 25, "tools": 25, "follows": 35, "code": 15}


def _score(bestået: dict[str, bool], sprunget: set[str]) -> int:
    """Vægtene afspejler hvad agent-arbejde faktisk falder på.

    `follows` vejer tungest: en model der kalder værktøjer men ignorerer
    resultatet er den dyreste slags — den ser ud som om den arbejder.

    Delprøver der ikke KUNNE køre (rate limit, timeout hos udbyderen) tages ud
    af både tæller og nævner. Ellers straffer vi en fungerende model for vores
    egen utålmodighed: nvidia/minimax-m3 fik først 85 alene fordi kode-prøven
    ramte et 429.
    """
    talte = {k: v for k, v in _VÆGTE.items() if k not in sprunget}
    if not talte:
        return 0
    opnået = sum(p for k, p in talte.items() if bestået.get(k))
    return round(100 * opnået / sum(talte.values()))


def bedøm_kode(tekst: str) -> bool:
    """True hvis svaret indeholder en Python-funktion der kan parses.

    Vi kører den ikke. En syntaktisk gyldig funktion med det rigtige navn er
    et ærligt minimumssignal; at eksekvere fremmed kode for en karakter er det
    ikke værd.
    """
    t = str(tekst or "")
    if not t.strip():
        return False
    # Modeller pakker næsten altid kode i et fence. Tag den største blok.
    blokke = []
    if "```" in t:
        dele = t.split("```")
        for i in range(1, len(dele), 2):
            b = dele[i]
            if b.startswith(("python", "py")):
                b = b.split("\n", 1)[-1] if "\n" in b else ""
            blokke.append(b)
    blokke.append(t)
    for b in sorted(blokke, key=len, reverse=True):
        try:
            træ = ast.parse(b)
        except SyntaxError:
            continue
        for n in ast.walk(træ):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == _KODE_FUNKTION:
                return True
    return False


def probe_model(
    *,
    provider: str,
    model: str,
    auth_profile: str = "default",
    base_url: str = "",
    kald: Any = None,
) -> dict[str, object]:
    """Kør de fire prøver mod én model. Kaster aldrig.

    `kald` injiceres i tests; ellers bruges cheap-lane'ens egen dispatch, så
    prøven går ad præcis samme vej som rigtigt arbejde. Måler vi ad en anden
    vej, måler vi noget andet end det vi bruger.
    """
    if kald is None:
        from core.services.cheap_provider_runtime_adapters import _execute_provider_chat as kald

    ud: dict[str, object] = {
        "provider": provider, "model": model, "auth_profile": auth_profile,
        "callable": False, "tools": False, "follows": False, "code": False,
        "latency_ms": 0, "score": 0, "error": "", "sprunget": [],
    }
    sprunget: set[str] = set()

    def _kør(messages, tools=None):
        return kald(provider=provider, model=model, auth_profile=auth_profile,
                    base_url=base_url, messages=messages, tools=tools)

    # 1+2: svarer den, og kalder den værktøjet?
    t0 = time.monotonic()
    try:
        r = _kør([{"role": "user",
                   "content": "Slå værdien for nøglen 'projekt' op. Brug værktøjet."}], _VÆRKTØJ)
    except Exception as exc:
        ud["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
        ud["latency_ms"] = int((time.monotonic() - t0) * 1000)
        # Kan den ikke engang kaldes, er der intet at normalisere over — 0.
        return ud
    ud["latency_ms"] = int((time.monotonic() - t0) * 1000)
    if int(ud["latency_ms"]) > PROBE_TIMEOUT_S * 1000:
        ud["error"] = "over banens tidsloft"
        return ud
    kald_liste = list((r or {}).get("tool_calls") or [])
    ud["callable"] = bool(r is not None)
    ud["tools"] = bool(kald_liste)

    # 3: kan den BRUGE resultatet? Vi fodrer den et svar den ikke kan gætte.
    if kald_liste:
        time.sleep(_PAUSE_S)
        tc = kald_liste[0]
        try:
            r2 = _kør([
                {"role": "user", "content": "Slå værdien for nøglen 'projekt' op. Brug værktøjet."},
                {"role": "assistant", "content": "", "tool_calls": [tc]},
                {"role": "tool", "tool_call_id": str(tc.get("id") or ""),
                 "content": f"projekt = {_HEMMELIGT_SVAR}"},
                {"role": "user", "content": "Hvad var værdien? Svar med ét ord."},
            ], _VÆRKTØJ)
            ud["follows"] = _HEMMELIGT_SVAR in str((r2 or {}).get("text") or "").lower()
        except Exception as exc:
            besked = f"{type(exc).__name__}: {str(exc)[:100]}"
            ud["error"] = f"follows: {besked}"
            if _er_forbigaaende(besked):
                sprunget.add("follows")
    else:
        # Kaldte den ingen værktøjer, er `follows` ikke sprunget over — den er
        # dumpet. Man kan ikke bruge et resultat man aldrig bad om.
        pass

    # 4: kan den skrive kode der kan parses?
    time.sleep(_PAUSE_S)
    try:
        r3 = _kør([{"role": "user", "content":
                    f"Skriv en Python-funktion `{_KODE_FUNKTION}(s)` der returnerer "
                    f"det tredje bogstav i strengen s. Kun kode."}])
        ud["code"] = bedøm_kode(str((r3 or {}).get("text") or ""))
    except Exception as exc:
        besked = f"{type(exc).__name__}: {str(exc)[:100]}"
        if not ud["error"]:
            ud["error"] = f"code: {besked}"
        if _er_forbigaaende(besked):
            sprunget.add("code")

    ud["sprunget"] = sorted(sprunget)
    ud["score"] = _score({k: bool(ud[k]) for k in _VÆGTE}, sprunget)
    return ud
