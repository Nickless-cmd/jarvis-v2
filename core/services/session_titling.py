"""Session titling — giv sessionerne rigtige titler i sidebaren.

FEJLEN (målt 13/10-2026, 608 sessioner): titlen blev sat til den RÅ første
brugerbesked, klippet ved 48 tegn (`_navngiv_fra_foerste_besked` og
inline-omdøbningen i `save_chat_message`). Det giver en sidebar der hedder
«hey», «yo», «hey j..», «Godmorgen» — fordi en hilsen er det første man
skriver, og den bærer ingen information om hvad samtalen handlede om.

Titlen sættes ÉN gang, fra besked nummer ét. Informationen om emnet kommer
senere, og der er ingen der samler den op.

LØSNINGEN: en sweeper der finder sessioner hvis titel stadig er ubrugelig,
læser et BUNDET vindue af samtalen, og beder OLLAMA-LANEN om en rigtig titel
(billig-lanen kun som reserve, hvis ollama ikke svarer). Den rører ikke
besked-skrivevejen — et modelkald må aldrig kunne blokere en besked — og den
retter de eksisterende sessioner med, ikke kun fremtidige.

VÆRN:
  * Kun titler der er pladsholdere eller hilsen-stubbe røres. Har brugeren
    selv navngivet sessionen, eller bærer den en maskin-titel med betydning
    («Autonom · Drømme · …», «Discord DM — …»), står den.
  * Krypterede titler springes over. De tilhører et medlem, ikke ejeren, og
    en titel-generering på ciffertekst ville være volapyk.
  * Alt er tavst: en session uden navn er et skønhedsproblem, en brækket
    besked-gemning er det ikke.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request as urllib_request

from core.runtime.db import connect
from core.services.chat_crypto import er_krypteret
from core.services.chat_sessions import (
    _er_pladsholder,
    recent_chat_session_messages,
    rename_chat_session,
)

logger = logging.getLogger(__name__)

#: Hvor mange sessioner der højst navngives pr. sweep. Hvert navn koster ét
#: billig-lane-kald, og sweepet kører fra heartbeat-stien — en langsom lane må
#: ikke kunne bygge en pukkel. 3 pr. 15. minut = 12 i timen.
MAX_PR_SWEEP = 3

#: Hvor mange kandidater der undersøges pr. sweep. Vi tager kun `MAX_PR_SWEEP`
#: der LYKKES; resten er luft til at springe dem over vi ikke kan læse.
MAX_KANDIDATER = 40

#: Hvor mange af de nyeste sessioner der SKANNES for dårlige titler.
#:
#: 13/10-2026: vinduet skalede før med det ønskede antal (`limit * 4`). Det
#: virkede ved et stort limit og fejlede tavst ved et lille: de dårlige titler
#: ligger SPREDT mellem de gode, så `_kandidater(limit=5)` så på 20 rækker og
#: fandt nul — mens sweepet med sit default fandt ni. Ét fast, rundhåndet
#: vindue gør svaret det samme uanset hvem der spørger.
SKAN_VINDUE = 300

#: Beskeder pr. titel. Nok til at emnet står klart, ikke nok til at blæse
#: prompten op. Vinduet er de SENESTE — for en «hey»-session ligger emnet
#: længere fremme end hilsenen.
#:
#: 13/10-2026: 8 var for lidt. Et agentisk forløb består mest af
#: værktøjs-resultater, og efter filtreringen stod der ÉN assistant-linje
#: tilbage — modellen fik intet at navngive ud fra og skrev volapyk
#: («Betegne Redigeringsbereättigande Toolbox»). 30 koster det samme at
#: hente og efterlader nok rigtige runder til at emnet er der.
BESKEDER_PR_TITEL = 30

#: Samlet tegnbudget for samtale-teksten. Prompten klippes ikke tilfældigt.
MAKS_TEGN = 4000

#: Hilsener der ikke er en titel. Sammenligningen sker på en renset form.
_HILSENER = frozenset({
    "hey", "hej", "hejsa", "yo", "dav", "davs", "hallo", "halløj",
    "godmorgen", "godaften", "godnat", "god dag", "morgen", "aften",
    "er du der", "hvor er du", "hvad så", "hva så", "hey du", "hej du",
    "hello", "hi",
})

#: Hilsen med en kort hale: «hey j», «hej du». Halen er begrænset, så en
#: rigtig sætning der TILFÆLDIGVIS starter med en hilsen ikke rammes —
#: «hej, hvad er status på pve-værten?» er en titel, ikke en hilsen.
_HILSEN_MED_HALE = re.compile(
    r"^(?:hey|hej|hejsa|yo|dav|davs|hallo|halløj|godmorgen|godaften|godnat)"
    r"(?:[\s,]+[\wÆØÅæøå]{1,6})?$",
    re.IGNORECASE,
)

#: En hilsen er kort. Over denne længde er den ikke en hilsen længere.
_MAKS_HILSEN_TEGN = 20


def _rens(titel: str) -> str:
    """Renset sammenligningsform: små bogstaver, ingen haler, ét mellemrum."""
    t = str(titel or "").strip().lower()
    t = re.sub(r"[\s.!?,…:;]+$", "", t)
    return re.sub(r"\s+", " ", t).strip()


def er_ubrugelig_titel(titel: str) -> bool:
    """Er titlen værdiløs i sidebaren — en pladsholder eller en hilsen?

    Det er den ENESTE klasse sweepet må røre. Alt andet er enten brugerens
    eget valg eller en maskin-titel der betyder noget.
    """
    if _er_pladsholder(titel):
        return True
    renset = _rens(titel)
    if not renset or len(renset) > _MAKS_HILSEN_TEGN:
        return False
    return renset in _HILSENER or bool(_HILSEN_MED_HALE.match(renset))


def _kandidater(*, limit: int = MAX_KANDIDATER) -> list[dict[str, str]]:
    """Seneste sessioner hvis titel er ubrugelig OG som vi må læse.

    Krypterede titler springes over: de tilhører et medlem, og en titel
    udledt af ciffertekst ville være volapyk skrevet ind i deres sidebar.
    """
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, title, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (SKAN_VINDUE,),
            ).fetchall()
    except Exception as exc:
        logger.debug("session_titling: kunne ikke læse kandidater: %s", exc)
        return []

    ud: list[dict[str, str]] = []
    for row in rows:
        raa_titel = str(row["title"] or "")
        if er_krypteret(raa_titel):
            continue
        if not er_ubrugelig_titel(raa_titel):
            continue
        ud.append({
            "session_id": str(row["session_id"] or ""),
            "title": raa_titel,
            "updated_at": str(row["updated_at"] or ""),
        })
        if len(ud) >= limit:
            break
    return ud


def _samtale_tekst(session_id: str) -> str:
    """Et bundet vindue af samtalen, klar til at give modellen.

    Bruger `recent_chat_session_messages` — den dekrypterer som den eneste
    læser, og henter et FAST antal. En fuld historik-læsning er forbudt for
    nye kaldere (`scripts/verify_history_reads.py`), og her er den heller
    ikke nødvendig: emnet står i de seneste par runder.

    Kun user/assistant tælles med. Et agentisk forløb er mest
    værktøjs-resultater, og dem kan man ikke navngive en samtale efter —
    derfor hentes et bredt vindue og filtreres ned.
    """
    try:
        rows = recent_chat_session_messages(session_id, limit=BESKEDER_PR_TITEL)
    except Exception as exc:
        logger.debug("session_titling: kunne ikke læse %s: %s", session_id, exc)
        return ""

    linjer: list[str] = []
    brugt = 0
    for r in rows or []:
        rolle = str(r.get("role") or "")
        if rolle not in ("user", "assistant"):
            continue
        tekst = " ".join(str(r.get("content") or "").split())
        if not tekst or er_krypteret(tekst):
            continue
        linje = f"{'Bjørn' if rolle == 'user' else 'Jarvis'}: {tekst[:500]}"
        if brugt + len(linje) > MAKS_TEGN:
            break
        linjer.append(linje)
        brugt += len(linje)
    return "\n".join(linjer)


#: Ollama-lanens timeout. Titlen er fire ord; svarer lanen ikke inden for
#: dette, er den ikke værd at vente på i heartbeat-stien.
OLLAMA_TIMEOUT = 45.0

_PROMPT = (
    "Du får et uddrag af en samtale mellem Bjørn og Jarvis.\n\n"
    "{samtale}\n\n"
    "Skriv en kort titel på samtalen — på almindeligt dansk, højst 4 ord.\n"
    "Titlen skal sige hvad samtalen HANDLEDE om, ikke hvordan den begyndte.\n"
    "Brug de ord der faktisk står i samtalen. Digt ikke nye ord, og skriv "
    "ikke en sætning. Svar KUN med titlen — intet andet."
)


def _rens_titel(raa: str) -> str:
    """Gør modellens svar til noget der kan stå i en sidebar.

    En titel er ikke et sted at være kreativ: kommer der en sætning, et
    anførselstegn eller et «Titel:»-præfiks med, klippes det væk. Er svaret
    for langt, er det ikke en titel — så hellere ingen end en forkert.
    """
    t = " ".join(str(raa or "").split()).strip()
    for praefiks in ("titel:", "title:", "titel -", "title -"):
        if t.lower().startswith(praefiks):
            t = t[len(praefiks):].strip()
    t = t.strip('"\'`“”«»').strip()
    t = t.rstrip(".")
    if not t or len(t) > 60:
        return ""
    return t[:48]


def _ollama_lane_titel(samtale: str) -> str:
    """Spørg ollama-lanen (routerens local-lane) om en titel.

    Tom streng = lanen svarede ikke; kalderen falder videre til billig-lanen.
    Modellen og værten læses fra routeren, ikke hardkodet: local-lanen peger
    på GPU-ollama'en (127.0.0.1:11434) hvor chat-modellerne ligger — ikke på
    embed-hosten på 11435, som kun har `nomic-embed-text`.
    """
    try:
        from core.runtime.provider_router import resolve_provider_router_target
        target = resolve_provider_router_target(lane="local")
    except Exception as exc:
        logger.debug("session_titling: kunne ikke slå local-lanen op: %s", exc)
        return ""
    if str(target.get("provider") or "").lower() != "ollama":
        return ""
    model = str(target.get("model") or "").strip()
    base = str(target.get("base_url") or "").strip().rstrip("/")
    if not model or not base:
        return ""
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": _PROMPT.format(samtale=samtale[:MAKS_TEGN])}
        ],
        "stream": False,
        "options": {"temperature": 0},
    }
    req = urllib_request.Request(
        f"{base}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=OLLAMA_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.debug("session_titling: ollama-lane-kald fejlede: %s", exc)
        return ""
    return str((data.get("message") or {}).get("content") or "")


def generer_titel(samtale: str) -> str:
    """Spørg ollama-lanen om en titel, med billig-lanen som reserve.

    OLLAMA FØRST (Bjørn, 13/10-2026). Målt på de samme fem kandidater skrev
    ollama-lanen kortere og mere præcist dansk end billig-lanens
    «default»-tier:

        «Yo»        → «CI-fejl og broen nede»
                       (billig: «Chat-VI undersøgelse af CI-fejl i Jarvis' commit»)
        «Godmorgen» → «mergeServer bevarer ikke billedet»
                       (billig: «Fejl i mergeServer-funktion»)
        «hey..»     → «Krypteret chat-historik»

    Titlen sidder i Bjørns sidebar permanent, og lanen er fri — der er intet
    kvoteforbehold at tage, så rækkefølgen koster ingenting og vinder kvalitet.
    """
    if not samtale.strip():
        return ""
    titel = _rens_titel(_ollama_lane_titel(samtale))
    if titel:
        return titel
    # Reserve: billig-lanen. Kun når ollama-lanen intet gav.
    try:
        from core.services.non_visible_lane_execution import execute_cheap_lane
        svar = execute_cheap_lane(
            message=_PROMPT.format(samtale=samtale[:MAKS_TEGN]),
            task_kind="default",
        )
    except Exception as exc:
        logger.debug("session_titling: billig-lane-kald fejlede: %s", exc)
        return ""
    return _rens_titel(str((svar or {}).get("text") or ""))


def sweep(*, limit: int = MAX_PR_SWEEP) -> dict[str, object]:
    """Navngiv op til `limit` sessioner med en ubrugelig titel.

    Returnerer en tavs kvittering — hvem der blev rettet, hvem der ikke
    kunne. Kaldes fra heartbeat-stien, så den fejler aldrig højt.
    """
    kandidater = _kandidater()
    if not kandidater:
        return {"status": "ok", "kandidater": 0, "omdoebt": [], "sprunget_over": 0}

    omdoebt: list[dict[str, str]] = []
    sprunget_over = 0

    for kandidat in kandidater:
        if len(omdoebt) >= limit:
            break
        session_id = kandidat["session_id"]
        if not session_id:
            continue
        samtale = _samtale_tekst(session_id)
        if not samtale:
            sprunget_over += 1
            continue
        titel = generer_titel(samtale)
        if not titel:
            sprunget_over += 1
            continue
        if not er_ubrugelig_titel(kandidat["title"]):
            # En anden nåede at navngive den imens vi spurgte.
            sprunget_over += 1
            continue
        try:
            rename_chat_session(session_id, title=titel)
        except Exception as exc:
            logger.debug("session_titling: kunne ikke omdoebe %s: %s", session_id, exc)
            sprunget_over += 1
            continue
        omdoebt.append({"session_id": session_id, "fra": kandidat["title"], "til": titel})

    if omdoebt:
        logger.info("session_titling: navngav %d sessioner", len(omdoebt))

    return {
        "status": "ok",
        "kandidater": len(kandidater),
        "omdoebt": omdoebt,
        "sprunget_over": sprunget_over,
    }
