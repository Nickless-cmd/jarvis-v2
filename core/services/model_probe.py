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
import re
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

# `follows` skal ligne ægte arbejde, ikke en quiz. Første udgave fodrede
# modellen ÉN linje — og nemotron-3-ultra bestod med 100, mens den i praksis
# kaldte `search`, fik korrekte filstier tilbage og derefter opdigtede
# «/workspace/jarvis-v2/jarvis/core/keys.py». Et værktøjssvar i virkeligheden
# er langt, larmende og har svaret begravet et sted inde i sig. Derfor det her:
# 14 linjer der ligner et søgeresultat, med svaret på linje 9.
_STØJ = [
    "./core/services/cheap_provider_runtime.py:12: import logging",
    "./core/services/cheap_lane_balancer.py:88: def _score(provider: str) -> float:",
    "./core/tools/simple_tools.py:1560: \"explore\": _exec_explore,",
    "./apps/api/jarvis_api/routes/mobile.py:44: return {\"ok\": True}",
    "./core/runtime/db.py:9021: CREATE TABLE IF NOT EXISTS costs (",
    "./core/services/visible_runs.py:2499: _hollow_promise_nudges = 0",
    "./core/identity/users.py:248: def get_owner() -> User | None:",
    "./scripts/api_docs_gen.py:31: REPO = Path(__file__).resolve().parents[1]",
    f"./core/runtime/secrets.py:77: PROJEKT_KODENAVN = \"{_HEMMELIGT_SVAR}\"",
    "./core/eventbus/bus.py:14: class EventBus:",
    "./core/services/prompt_contract.py:3097: parts.append(_SENTINEL)",
    "./core/memory/brain.py:512: def prune_edges(confidence: float) -> int:",
    "./core/services/agent_runtime_spawn.py:92: def spawn_agent_task(",
    "./core/tools/workspace_capabilities.py:210: def resolve_tool_call_to_capability(",
]

_KODE_FUNKTION = "tredje_bogstav"

# `follows` køres FLERE gange og skal bestå HVER gang.
#
# Målt 7/9-2026: to explore-kørsler, samme model (copilot-free/gpt-4.1), samme
# værktøjskæde, korrekte søgeresultater begge gange. Den ene gengav dem
# trofast; den anden skrev tre funktioner der ikke findes og tilføjede
# «Confidence: høj (begrundet i direkte søgeresultater)». Forskellen var ren
# tilfældighed i modellen.
#
# En engangsprøve kan pr. definition ikke fange det. Og en model der lyver hver
# tredje gang er FARLIGERE end en der altid fejler: den fejler ikke synligt, den
# fejler troværdigt. Derfor 3 af 3, ikke bedst-ud-af-3.
_FOLLOWS_FORSØG = 3


_VÆGTE = {"callable": 25, "tools": 25, "follows": 35, "code": 15}


# Filnavne der KUN findes i støjen. Nævner svaret en fil der ikke stod der,
# har modellen opfundet den.
_KENDTE_FILER = frozenset(
    l.split(":", 1)[0].lstrip("./") for l in _STØJ
)
_FILNAVN = re.compile(r"(?:\./)?([A-Za-z0-9_./-]+\.py)")


def _fulgte_resultatet(svar: str) -> bool:
    """Bestået kræver TO ting: at svaret bærer det plantede faktum, og at det
    ikke nævner filer der ikke stod i resultatet.

    Første udgave tjekkede kun det første. `copilot-free/gpt-4.1` bestod med
    100 — og opdigtede derefter i produktion tre funktionsnavne der ikke
    findes, mens den påstod tallene kom fra `search`. At gengive ét faktum er
    let; at lade være med at digte videre er dét arbejdet kræver.
    """
    t = str(svar or "")
    if _HEMMELIGT_SVAR not in t.lower():
        return False
    for fil in set(_FILNAVN.findall(t)):
        if fil.lstrip("./") not in _KENDTE_FILER:
            return False          # nævnte en kilde der aldrig blev vist
    return True


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

    # 3: kan den BRUGE resultatet — HVER gang? Se _FOLLOWS_FORSØG.
    if kald_liste:
        tc = kald_liste[0]
        bestået_alle = True
        for forsøg in range(_FOLLOWS_FORSØG):
            time.sleep(_PAUSE_S)
            if not bestået_alle:
                break
            try:
                r2 = _kør([
                    {"role": "user", "content": "Slå værdien for nøglen 'projekt' op. Brug værktøjet."},
                    {"role": "assistant", "content": "", "tool_calls": [tc]},
                    {"role": "tool", "tool_call_id": str(tc.get("id") or ""),
                     "content": "\n".join(_STØJ)},
                    {"role": "user", "content":
                     "Hvad er PROJEKT_KODENAVN sat til, og hvilken fil står det i? "
                     "Svar kort, og nævn KUN filer der står i søgeresultatet."},
                ], _VÆRKTØJ)
                if not _fulgte_resultatet(str((r2 or {}).get("text") or "")):
                    bestået_alle = False
                    ud["error"] = f"follows: dumpede i forsøg {forsøg + 1} af {_FOLLOWS_FORSØG}"
            except Exception as exc:
                besked = f"{type(exc).__name__}: {str(exc)[:100]}"
                ud["error"] = f"follows: {besked}"
                if _er_forbigaaende(besked):
                    sprunget.add("follows")
                bestået_alle = False
                break
        ud["follows"] = bestået_alle and "follows" not in sprunget
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
