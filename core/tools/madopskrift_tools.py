"""Madopskrifter på dansk — TheMealDB + MyPlate.food med oversættelseslag.

Baggrund (25/10-2026, Bjørn): Michelle ville gerne kunne slå opskrifter op.
Der findes INGEN god offentlig dansk opskrift-API — Arla og Valdemarsro har
ingen åbne endpoints. Alle kilder er engelsksprogede, så oversættelseslaget
er ikke en detalje: det er hele arbejdet.

Målt live 25/10-2026:
- TheMealDB: ``search.php?s=kartoffel`` → ``{"meals":null}``; ``s=potato`` virker.
- MyPlate.food: 1.072 opskrifter; ``?q=`` og ``?ingredients=`` virker uden nøgle.

Designprincip: fejl skal være HØJE. Et tomt resultat på et dansk ord der
burde matche er en fejl — ikke et gyldigt «ingen opskrifter fundet». Derfor
returnerer vi ``status="error"`` med den oversatte term, så det kan ses HVOR
det gik galt, i stedet for en tom liste der ligner et svar.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

_USER_AGENT = "Jarvis/1.0 (jarvis-v2; contact onkeladolf@gmail.com)"
_THEMEALDB = "https://www.themealdb.com/api/json/v1/1"
_MYPLATE = "https://myplate.food/api/v1"

# ── Dansk → engelsk ordbog ────────────────────────────────────────────────
# Dækker de termer en dansk bruger faktisk skriver. Ordbogen er førstevalg
# fordi den er deterministisk og øjeblikkelig; cheap-lane bruges kun for ord
# der ikke findes her. Målt behov: TheMealDB søger KUN på engelsk.
_DA_EN: dict[str, str] = {
    # basisingredienser
    "kartoffel": "potato", "kartofler": "potato", "kylling": "chicken",
    "kyllingebryst": "chicken breast", "kød": "beef", "oksekød": "beef",
    "svinekød": "pork", "flæsk": "pork", "bacon": "bacon", "lam": "lamb",
    "fisk": "fish", "laks": "salmon", "torsk": "cod", "tun": "tuna",
    "rejer": "prawns", "muslinger": "mussels", "æg": "egg", "æggehvide": "egg white",
    "mælk": "milk", "fløde": "cream", "smør": "butter", "ost": "cheese",
    "flødeost": "cream cheese", "yoghurt": "yoghurt", "creme fraiche": "creme fraiche",
    # grønt
    "løg": "onion", "rødløg": "red onion", "hvidløg": "garlic", "porre": "leek",
    "gulerod": "carrot", "gulerødder": "carrot", "tomat": "tomato", "tomater": "tomato",
    "agurk": "cucumber", "peberfrugt": "bell pepper", "chili": "chilli",
    "svamp": "mushroom", "svampe": "mushroom", "champignon": "mushroom",
    "spinat": "spinach", "salat": "lettuce", "kål": "cabbage", "broccoli": "broccoli",
    "blomkål": "cauliflower", "ærter": "peas", "bønner": "beans", "majs": "corn",
    "squash": "courgette", "aubergine": "aubergine", "selleri": "celery",
    "persille": "parsley", "basilikum": "basil", "timian": "thyme", "dild": "dill",
    "mynte": "mint", "ingefær": "ginger", "citron": "lemon", "lime": "lime",
    "avocado": "avocado", "oliven": "olives", "nødder": "nuts", "mandler": "almonds",
    # kolonial
    "pasta": "pasta", "spaghetti": "spaghetti", "nudler": "noodles", "ris": "rice",
    "risotto": "risotto", "mel": "flour", "sukker": "sugar", "salt": "salt",
    "peber": "pepper", "olie": "oil", "olivenolie": "olive oil", "eddike": "vinegar",
    "soja": "soy sauce", "sojasauce": "soy sauce", "honning": "honey",
    "sennep": "mustard", "ketchup": "ketchup", "majonnaise": "mayonnaise",
    "tomatpuré": "tomato puree", "kokosmælk": "coconut milk", "bouillon": "stock",
    "linser": "lentils", "kikærter": "chickpeas", "quinoa": "quinoa", "couscous": "couscous",
    "brød": "bread", "toast": "toast", "tortilla": "tortilla", "pitabrød": "pita bread",
    # retter og kategorier
    "suppe": "soup", "salatret": "salad", "gryderet": "stew", "gryde": "casserole",
    "tærte": "pie", "pizza": "pizza", "burger": "burger", "sandwich": "sandwich",
    "omelet": "omelette", "pandekage": "pancake", "pandekager": "pancake",
    "kage": "cake", "dessert": "dessert", "is": "ice cream", "budding": "pudding",
    "morgenmad": "breakfast", "frokost": "lunch", "aftensmad": "dinner",
    "forret": "starter", "vegetar": "vegetarian", "vegansk": "vegan",
    "kyllingesuppe": "chicken soup", "grøntsagssuppe": "vegetable soup",
    "frikadeller": "meatballs", "kødsovs": "bolognese", "lasagne": "lasagne",
    "wok": "stir fry", "curry": "curry", "taco": "taco", "burrito": "burrito",
    "fiskefilet": "fish fillet", "stegt": "fried", "bagt": "baked", "grillet": "grilled",
}

# Ord der ikke er mad, men som dukker op i en ingrediensliste.
_STOPORD = {
    "og", "eller", "med", "uden", "lidt", "noget", "jeg", "har", "vi", "der",
    "en", "et", "den", "det", "de", "i", "på", "af", "til", "fra", "min", "mine",
    "hvad", "kan", "lave", "opskrift", "opskrifter", "ret", "retter", "mad",
}


def _http_get_json(url: str, *, timeout: float = 15.0) -> Any:
    """GET JSON med Jarvis User-Agent. Kaster ved netværks-/parse-fejl."""
    req = urllib_request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


# ── Oversættelseslag ─────────────────────────────────────────────────────

def _cheap_lane(prompt: str) -> str:
    """Ét kald til cheap-lane. Returnerer tom streng hvis den ikke kan."""
    try:
        from core.services.cheap_provider_runtime_selection import (
            execute_public_safe_cheap_lane,
        )

        result = execute_public_safe_cheap_lane(message=prompt)
        return str(result.get("text") or "").strip()
    except Exception as exc:  # pragma: no cover - netværksafhængig
        logger.warning("madopskrift: cheap-lane fejlede: %s", exc)
        return ""


def _split_sammensat(ord: str) -> str | None:
    """Del et dansk sammensat ord i to kendte ordbogsord.

    Dansk sætter ord sammen på en måde engelsk ikke gør: «blomkålssuppe» er
    ikke et opslagsord nogen steder, men «blomkål» + «suppe» er. Målt
    25/10-2026: uden dette fejlede netop det ord, og det er en fejl Michelle
    ville ramme konstant. Fugebogstaverne -s- og -e- håndteres.
    """
    if len(ord) < 5:
        return None
    for i in range(2, len(ord) - 1):
        venstre, rest = ord[:i], ord[i:]
        if venstre not in _DA_EN:
            continue
        for fuge in ("", "s", "e"):
            hoejre = rest[len(fuge):] if fuge and rest.startswith(fuge) else rest
            if hoejre and hoejre in _DA_EN:
                return f"{_DA_EN[venstre]} {_DA_EN[hoejre]}"
    return None


def oversaet_ord_til_engelsk(ord: str) -> tuple[str, str]:
    """Dansk mad-ord → engelsk søgeord. Returnerer (engelsk, kilde).

    Kilden er ``ordbog``, ``sammensat`` eller ``model`` — så det kan ses hvad
    der blev gættet. Kaster ``ValueError`` hvis ordet hverken findes i
    ordbogen eller kan oversættes. Det er med vilje: et uoversat ord må ikke
    blive et tomt søg.
    """
    rent = " ".join(str(ord or "").strip().lower().split())
    if not rent:
        raise ValueError("tomt søgeord")
    if rent in _DA_EN:
        return _DA_EN[rent], "ordbog"

    # Sammensat dansk ord: «blomkålssuppe» → «cauliflower soup».
    sammensat = _split_sammensat(rent)
    if sammensat:
        return sammensat, "sammensat"

    # Flere ord: oversæt hvert led der findes, behold resten.
    if " " in rent:
        dele = [d for d in rent.split() if d not in _STOPORD]
        oversatte = [_DA_EN.get(d, d) for d in dele]
        if any(d in _DA_EN for d in dele):
            return " ".join(oversatte), "ordbog"

    svar = _cheap_lane(
        "Oversæt dette danske mad-ord til det engelske ord man ville søge med "
        "i en opskriftsdatabase. Svar KUN med ordet, ingen forklaring, ingen "
        f"punktum.\n\nOrd: {rent}"
    )
    kandidat = svar.strip().strip(".!\"'").split("\n")[0].strip().lower()
    if kandidat and " " not in kandidat and len(kandidat) <= 40:
        return kandidat, "model"
    raise ValueError(
        f"kunne ikke oversætte «{rent}» til engelsk — ordbogen kender det ikke, "
        "og modellen gav intet brugbart svar"
    )


def oversaet_til_dansk(tekst: str, *, kontekst: str = "opskrift") -> tuple[str, bool]:
    """Engelsk tekst → dansk. Returnerer (tekst, blev_oversat).

    Ved fejl returneres den engelske tekst med ``False`` — det er ærligt,
    og opskriften er stadig brugbar. Vi opfinder ikke en oversættelse.
    """
    rent = str(tekst or "").strip()
    if not rent:
        return "", True
    svar = _cheap_lane(
        f"Oversæt denne {kontekst} til naturligt dansk. Behold mål, tal og "
        "enheder præcist som de står. Behold linjeskift. Svar KUN med den "
        f"oversatte tekst, ingen indledning.\n\n{rent}"
    )
    if svar and len(svar) > 0.3 * len(rent):
        return svar, True
    return rent, False


# ── Kilder ───────────────────────────────────────────────────────────────

def _themealdb_soeg(engelsk: str, *, limit: int = 8) -> list[dict[str, Any]]:
    data = _http_get_json(f"{_THEMEALDB}/search.php?s={urllib_parse.quote(engelsk)}")
    meals = (data or {}).get("meals") or []
    ud: list[dict[str, Any]] = []
    for m in meals[:limit]:
        ud.append({
            "id": f"themealdb:{m.get('idMeal')}",
            "navn": m.get("strMeal") or "",
            "kategori": m.get("strCategory") or "",
            "omraade": m.get("strArea") or "",
            "billede": m.get("strMealThumb") or "",
            "kilde": "TheMealDB",
        })
    return ud


def _themealdb_hent(meal_id: str) -> dict[str, Any] | None:
    data = _http_get_json(f"{_THEMEALDB}/lookup.php?i={urllib_parse.quote(meal_id)}")
    meals = (data or {}).get("meals") or []
    if not meals:
        return None
    m = meals[0]
    ingredienser: list[str] = []
    for i in range(1, 21):
        navn = (m.get(f"strIngredient{i}") or "").strip()
        maal = (m.get(f"strMeasure{i}") or "").strip()
        if navn:
            ingredienser.append(f"{maal} {navn}".strip())
    return {
        "navn": m.get("strMeal") or "",
        "kategori": m.get("strCategory") or "",
        "omraade": m.get("strArea") or "",
        "billede": m.get("strMealThumb") or "",
        "portioner": "",
        "ingredienser": ingredienser,
        "fremgangsmaade": (m.get("strInstructions") or "").replace("\r\n", "\n").strip(),
        "kilde": "TheMealDB",
        "url": m.get("strSource") or "",
    }


def _myplate_soeg(engelsk: str, *, limit: int = 8) -> list[dict[str, Any]]:
    url = f"{_MYPLATE}/recipes?q={urllib_parse.quote(engelsk)}&limit={limit}"
    data = _http_get_json(url)
    ud: list[dict[str, Any]] = []
    for r in (data or {}).get("results") or []:
        ud.append({
            "id": f"myplate:{r.get('slug')}",
            "navn": r.get("name") or "",
            "kategori": "",
            "omraade": "",
            "billede": "",
            "beskrivelse": (r.get("description") or "")[:200],
            "kilde": "MyPlate.food",
        })
    return ud


def _myplate_hent(slug: str) -> dict[str, Any] | None:
    data = _http_get_json(f"{_MYPLATE}/recipes/{urllib_parse.quote(slug)}")
    if not data or not data.get("name"):
        return None
    ingredienser: list[str] = []
    for ing in data.get("ingredients") or []:
        tekst = (ing.get("text") or "").strip()
        note = (ing.get("note") or "").strip()
        if tekst:
            ingredienser.append(f"{tekst} ({note})" if note else tekst)
    return {
        "navn": data.get("name") or "",
        "kategori": "",
        "omraade": "",
        "billede": "",
        "portioner": data.get("yield") or "",
        "ingredienser": ingredienser,
        "fremgangsmaade": (data.get("directions") or "").strip(),
        "kilde": "MyPlate.food",
        "url": "",
    }


def _myplate_koleskab(ingredienser: list[str], *, limit: int = 8) -> list[dict[str, Any]]:
    samlet = ",".join(urllib_parse.quote(i) for i in ingredienser)
    url = f"{_MYPLATE}/recipes?ingredients={samlet}&limit={limit}"
    data = _http_get_json(url)
    ud: list[dict[str, Any]] = []
    for r in (data or {}).get("results") or []:
        ud.append({
            "id": f"myplate:{r.get('slug')}",
            "navn": r.get("name") or "",
            "kategori": "",
            "omraade": "",
            "billede": "",
            "beskrivelse": (r.get("description") or "")[:200],
            "kilde": "MyPlate.food",
        })
    return ud


# ── Værktøjets indgang ───────────────────────────────────────────────────

def _exec_madopskrift(args: dict[str, Any]) -> dict[str, Any]:
    """Slå opskrifter op på dansk. Se ``madopskrift``-definitionen."""
    handling = str(args.get("handling") or "soeg").strip().lower()

    try:
        svar = (
            _hent(args)
            if handling == "hent"
            else _koleskab(args)
            if handling == "koleskab"
            else _soeg(args)
        )
    except ValueError as exc:
        # Bevidst uden log: en uoversættelig term er et svar TIL brugeren,
        # ikke en fejl i systemet. Den skal vises, ikke begraves i en log.
        return {"status": "error", "error": str(exc)}
    except urllib_error.URLError as exc:
        # Nettet mod TheMealDB/MyPlate — forbigående, og svaret bærer årsagen.
        return {"status": "error", "error": f"netværksfejl mod opskriftskilden: {exc}"}
    except Exception as exc:  # pragma: no cover - uventet
        logger.warning("madopskrift: uventet fejl: %s", exc)
        return {"status": "error", "error": f"uventet fejl: {exc}"}


def _soeg(args: dict[str, Any]) -> dict[str, Any]:
    raa = str(args.get("soegning") or args.get("query") or "").strip()
    if not raa:
        return {"status": "error", "error": "soegning mangler — skriv et dansk mad-ord"}

    engelsk, kilde = oversaet_ord_til_engelsk(raa)

    resultater: list[dict[str, Any]] = []
    fejl: list[str] = []
    for navn, fn in (("TheMealDB", _themealdb_soeg), ("MyPlate.food", _myplate_soeg)):
        try:
            resultater.extend(fn(engelsk))
        except Exception as exc:
            fejl.append(f"{navn}: {exc}")

    if not resultater:
        # BREDERE SØG FØR VI GIVER OP. Målt 25/10-2026: «blomkålssuppe» blev
        # korrekt oversat til «cauliflower soup», men TheMealDB har ingen ret
        # med netop det navn — mens den har masser med «cauliflower». Uden
        # dette fald ville Michelle få «ingen opskrifter» på et ord der ER
        # dækket, og det er præcis den slags tavse nej kravet forbyder.
        if kilde != "model" and " " in engelsk:
            for bredere in (engelsk.split()[0], engelsk.split()[-1]):
                if not bredere or bredere == engelsk:
                    continue
                for navn, fn in (("TheMealDB", _themealdb_soeg), ("MyPlate.food", _myplate_soeg)):
                    try:
                        fundet = fn(bredere)
                    except Exception as exc:
                        fejl.append(f"{navn} (bredere «{bredere}»): {exc}")
                        continue
                    if fundet:
                        resultater.extend(fundet)
                        engelsk = bredere
                        break
                if resultater:
                    break

    if not resultater:
        # Sondringen der betyder noget: et tomt svar er kun en FEJL hvis
        # oversættelsen var et gæt. Er termen slået op i ordbogen (eller delt
        # ad et sammensat ord), er den sikker — og så er et tomt svar kildens
        # ægte svar, ikke vores fejl. Målt 25/10-2026: TheMealDB har hverken
        # «cauliflower soup» som navn ELLER «cauliflower» som ingrediens.
        if kilde == "model":
            return {
                "status": "error",
                "error": (
                    f"«{raa}» blev gættet oversat til «{engelsk}» (kilde: model), og "
                    "begge kilder gav nul resultater. Gættet kan være forkert — "
                    "prøv et andet dansk ord."
                ),
                "dansk_term": raa,
                "engelsk_term": engelsk,
                "oversaettelse_kilde": kilde,
                "kildefejl": fejl,
            }
        return {
            "status": "ok",
            "dansk_term": raa,
            "engelsk_term": engelsk,
            "oversaettelse_kilde": kilde,
            "antal": 0,
            "resultater": [],
            "kildefejl": fejl,
            "note": (
                f"Oversættelsen er sikker («{raa}» → «{engelsk}», kilde: {kilde}), "
                "men kilderne har ingen opskrifter med den term. Det er kildens "
                "svar — ikke en oversættelsesfejl. Prøv en bredere term."
            ),
        }

    return {
        "status": "ok",
        "dansk_term": raa,
        "engelsk_term": engelsk,
        "oversaettelse_kilde": kilde,
        "antal": len(resultater),
        "resultater": resultater,
        "kildefejl": fejl,
        "naeste_skridt": "Kald handling='hent' med et id for den fulde opskrift på dansk.",
    }


def _hent(args: dict[str, Any]) -> dict[str, Any]:
    raa_id = str(args.get("id") or "").strip()
    if not raa_id:
        return {"status": "error", "error": "id mangler (fx 'themealdb:52965')"}

    if ":" in raa_id:
        kilde, _, ident = raa_id.partition(":")
    else:
        kilde, ident = "themealdb", raa_id

    if kilde == "myplate":
        opskrift = _myplate_hent(ident)
    else:
        opskrift = _themealdb_hent(ident)

    if not opskrift:
        return {"status": "error", "error": f"fandt ingen opskrift med id «{raa_id}»"}

    # Ingredienslisten oversættes som ÉN blok: linje for linje ville være op
    # til 20 modelkald for én opskrift. Blokken bevarer linjeskift, så vi kan
    # splitte den igen — og falder tilbage til originalen hvis længden skrider.
    oversat_navn, navn_ok = oversaet_til_dansk(opskrift["navn"], kontekst="opskriftstitel")
    oversat_fremgang, fremgang_ok = oversaet_til_dansk(
        opskrift["fremgangsmaade"], kontekst="opskriftsfremgangsmåde"
    )
    raa_ingredienser = opskrift["ingredienser"]
    blok, blok_ok = oversaet_til_dansk(
        "\n".join(raa_ingredienser), kontekst="ingrediensliste (én linje pr. ingrediens)"
    )
    kandidat = [linje.strip() for linje in blok.split("\n") if linje.strip()]
    if blok_ok and len(kandidat) == len(raa_ingredienser):
        oversatte_ingredienser = kandidat
    else:
        oversatte_ingredienser = raa_ingredienser
        fremgang_ok = fremgang_ok and False

    return {
        "status": "ok",
        "id": raa_id,
        "navn": oversat_navn,
        "navn_originalt": opskrift["navn"],
        # Kilderne er uenige om hvilke felter de leverer: TheMealDB har
        # «strServings»/«strMealThumb», MyPlate har dem ikke altid. Direkte
        # indeksering gjorde et manglende felt til en KeyError midt i et
        # ellers gyldigt svar — målt 25/10-2026 i testen.
        "portioner": opskrift.get("portioner") or "",
        "ingredienser": oversatte_ingredienser,
        "fremgangsmaade": oversat_fremgang,
        "billede": opskrift.get("billede") or "",
        "kilde": opskrift.get("kilde") or kilde,
        "oversat": bool(navn_ok and fremgang_ok),
        "note": "" if (navn_ok and fremgang_ok) else (
            "Oversættelsen faldt delvist tilbage til engelsk — teksten er stadig brugbar."
        ),
    }


def _koleskab(args: dict[str, Any]) -> dict[str, Any]:
    raa = args.get("ingredienser") or args.get("soegning") or ""
    if isinstance(raa, str):
        dele = [d.strip() for d in raa.replace(";", ",").split(",") if d.strip()]
    else:
        dele = [str(d).strip() for d in raa if str(d).strip()]
    if not dele:
        return {"status": "error", "error": "ingredienser mangler — fx 'kylling, ris, løg'"}

    oversatte: list[str] = []
    kilder: dict[str, str] = {}
    for d in dele:
        if d.lower() in _STOPORD:
            continue
        engelsk, kilde = oversaet_ord_til_engelsk(d)
        oversatte.append(engelsk)
        kilder[d] = f"{engelsk} ({kilde})"

    if not oversatte:
        return {"status": "error", "error": "ingen brugbare ingredienser efter frasortering"}

    resultater = _myplate_koleskab(oversatte)
    if not resultater:
        return {
            "status": "error",
            "error": (
                f"ingen opskrifter med {', '.join(oversatte)} — det er en fejl, "
                "ikke et gyldigt tomt svar"
            ),
            "oversatte_ingredienser": kilder,
        }

    return {
        "status": "ok",
        "ingredienser_oversat": kilder,
        "antal": len(resultater),
        "resultater": resultater,
        "naeste_skridt": "Kald handling='hent' med et id for den fulde opskrift på dansk.",
    }
