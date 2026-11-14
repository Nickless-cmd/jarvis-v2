"""Normaliserer og validerer ``jarvis-ui``-blokke FØR de når chatten.

Baggrund (målt 24/10-2026, Bjørn): tre svar i træk fejlede i chatview, og
årsagen var ikke rendereren. To forskellige fejl, begge i MIN tekst:

1. id 220068 (21:43): ``],"}"`` hvor der skulle stå ``]}`` — ugyldig JSON.
   Parserens fejl: ``Expecting ':' delimiter: line 1 column 265``.
2. id 220247 (22:02): JSON'en var gyldig (2 kolonner, 4 rækker, alle
   ``values`` 2 lange), men den stod på SAMME LINJE som fence-markøren:
   ```` ```jarvis-ui {"type":… ````. I CommonMark bliver hele resten af
   linjen en del af info-stringen, så rendereren ser ikke sproget
   ``jarvis-ui`` — og blokken falder tilbage til rå kode.

Fejl nummer to er den farligste, fordi JSON'en er korrekt: enhver validering
der kun kigger på dataene siger «OK», mens brugeren ser rå tekst.

Derfor normaliserer dette modul FORMEN først (JSON på sin egen linje, lukke-
fence på sin egen linje), derefter retter det de entydige JSON-fejl, og
derefter validerer det. Rækkefølgen er ikke tilfældig: en validering der
kører før normaliseringen kan ikke se fejl nummer to.

Reparationerne er bevidst smalle. Kun mønstre der ALDRIG er gyldig JSON
rettes — ``],"}"``, dobbelt komma, trailing komma før ``}``/``]``. Alt andet
lader vi stå: en vagt der gætter forkert og «reparerer» ødelægger et svar der
var i orden, og det er værre end den fejl den skulle fange.

Fail-open overalt: enhver fejl her må aldrig påvirke et svar.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_FENCE_OPEN = re.compile(r"```jarvis-ui[ \t]*")
#: Et helt fence-område, uanset om JSON'en står på markørens linje.
_FENCE_BLOK = re.compile(r"```jarvis-ui[ \t]*(.*?)```", re.S)
#: En bar ``jarvis-ui {…}`` UDEN fence. Målt 25/10-2026: den form renderes som
#: rå tekst, og ``normalisér`` ser den slet ikke — den leder efter fence-markøren.
#: Mønstret er grådigt frem til den sidste ``}`` på linjen, fordi JSON'en kan
#: indeholde ``}`` i sine egne objekter.
_BAR_BLOK = re.compile(r"(?<!`)jarvis-ui[ \t]*(\{.*\})[ \t]*$", re.M)

#: Mønstre der aldrig kan være gyldig JSON. Hver reparation er smal og entydig.
_REPARATIONER: tuple[tuple[re.Pattern[str], str], ...] = (
    # `],"}"` → `]}` — den målte fejl fra 220068 (citationstegn efter komma).
    (re.compile(r'\]\s*,\s*"\s*\}'), "]}"),
    # `},"}` → `}}` — samme fejl på objekt-niveau.
    (re.compile(r'\}\s*,\s*"\s*\}'), "}}"),
    # `,]` og `,}` — trailing komma.
    (re.compile(r",\s*\]"), "]"),
    (re.compile(r",\s*\}"), "}"),
    # `,,` — dobbelt komma.
    (re.compile(r",\s*,"), ","),
)

#: Hvad en uoprettelig blok erstattes med. Målt 24/10-2026: en degraderet blok
#: blev tidligere dumpet som ` ```text ` med rå JSON, så læseren så `]` og `]}`
#: uden at vide hvad det var. En flade der ikke kan parses skal ikke ligne en
#: flade — men den skal heller ikke ligne en fejl i systemet.
_DEGRADERET = "*(en flade kunne ikke vises — dataene passede ikke sammen)*"

#: Hvad en manglende celle udfyldes med. Målt 24/10-2026: den var en stille
#: ``—``, så en tabel med tre kolonner og to values SÅ komplet ud mens tredje
#: kolonne var tom hele vejen ned. En tavs fejl kan hverken ses eller rettes,
#: så markøren siger nu hvad den er.
_MANGLER = "— (mangler)"

#: Lofterne for de typer der bærer børn. De SKAL stå her og ikke kun i
#: rendereren: guarden erklærer en flade «ok» hvis den ikke kender loftet, og
#: så klipper klienten børnene væk uden at nogen ser det. Tallene er de samme
#: som `BOX_MAX_DYBDE` / `BOX_MAX_BOERN` i desk og mobil.
_BOX_MAX_DYBDE = 3
_BOX_MAX_BOERN = 8
#: Lofter for anden bølge (14/11-2026). Sat efter hvad der kan LÆSES, ikke
#: efter hvad der kan sendes: en tabel på 40 kolonner er ikke en flade, den er
#: et regneark presset ind i en samtale.
_TABLE_MAX_KOLONNER = 12
_TABLE_MAX_RAEKKER = 100
_CHART_MAX_SERIER = 4
_CHART_MAX_PUNKTER = 40
_TREE_MAX_DYBDE = 8


def _normaliser_form(raw: str) -> str:
    """Flyt JSON'en ned på sin egen linje og lukke-fencen på sin egen linje.

    Dette er den reparation der løser den målbare fejl fra 220247: når JSON'en
    står på markørens linje, bliver den en del af info-stringen og blokken
    renderes som rå kode.
    """
    indhold = raw.strip()
    if not indhold:
        return ""
    return f"```jarvis-ui\n{indhold}\n```"


def _reparer_json(tekst: str) -> str:
    """Ret de entydige JSON-fejl. Rører intet der allerede er gyldigt."""
    ud = tekst
    for moenster, erstatning in _REPARATIONER:
        ud = moenster.sub(erstatning, ud)
    return ud


def _ret_laengder(tekst: str) -> str:
    """Juster ``comparison``-values op til kolonneantallet. Returnerer ny JSON.

    Målt 24/10-2026 (Bjørn: "]!!!!" og derefter "Du gjorde det igen!"): jeg skrev
    tre kolonner og to values — fire gange på én aften. Den manglende celle
    udfyldes med en markør der SIGER at den mangler, ikke en stille bindestreg:
    en tabel der ser komplet ud men har en tom kolonne er en tavs fejl, og tavse
    fejl kan hverken ses eller rettes. Overskydende værdier trunkeres, fordi en
    tabel med for mange kolonner ikke kan rendres konsistent.
    """
    try:
        data = json.loads(tekst)
    except Exception:  # ugyldig JSON: der er ingen længder at justere, og teksten gives uændret videre til _validér
        return tekst
    if not isinstance(data, dict) or data.get("type") != "comparison":
        return tekst
    kolonner = data.get("columns") or []
    if not isinstance(kolonner, list):
        return tekst
    aendret = False
    for raekke in data.get("rows") or []:
        if not isinstance(raekke, dict):
            continue
        vaerdier = raekke.get("values")
        if not isinstance(vaerdier, list):
            continue
        if len(vaerdier) < len(kolonner):
            raekke["values"] = vaerdier + [_MANGLER] * (len(kolonner) - len(vaerdier))
            aendret = True
        elif len(vaerdier) > len(kolonner):
            raekke["values"] = vaerdier[: len(kolonner)]
            aendret = True
    if not aendret:
        return tekst
    return json.dumps(data, ensure_ascii=False)


def _tekst(vaerdi: object) -> str:
    """Spejl rendererens ``text()``: kun strenge, trimmet, tom = falsk."""
    return vaerdi.strip() if isinstance(vaerdi, str) else ""


def _liste(vaerdi: object, maks: int) -> list[dict]:
    """Spejl rendererens ``list()``: kun objekter, afkortet til ``maks``."""
    if not isinstance(vaerdi, list):
        return []
    return [x for x in vaerdi if isinstance(x, dict) and not isinstance(x, list)][:maks]


def _endeligt_tal(vaerdi: object) -> bool:
    """Et tal vi kan regne med. ``NaN`` og ``Infinity`` ER tal for Python, men
    ikke for en slider: ``value={NaN}`` giver et håndtag der står tomt uden at
    nogen fejl bliver rejst nogen steder."""
    if not isinstance(vaerdi, (int, float)) or isinstance(vaerdi, bool):
        return False
    return vaerdi == vaerdi and abs(vaerdi) != float("inf")


def _diagnosticér(data: dict, dybde: int = 1) -> tuple[str, list[str]]:
    """Afgør om rendereren viser blokken. Returnerer (niveau, fejl).

    ``dybde`` tælles kun for de typer der bærer børn (``box``, ``tabs``).
    Rendereren afviser en box dybere end 3; guarden skal måle det samme tal,
    ellers erklærer den en flade «ok» som klienten returnerer ``null`` for.

    Niveau er ``"ok"``, ``"delvis"`` (nogle elementer filtreres væk, resten
    vises) eller ``"død"`` (rendereren returnerer ``null`` — intet vises).

    Skemaet er læst fra ``parseNativeRichSpec`` i både desk og mobil
    (identiske, verificeret 25/10-2026). Grænsen mellem ``delvis`` og ``død``
    er vigtig: en død blok skal degraderes, fordi brugeren ellers ser
    ingenting; en delvis blok skal BEVARES, fordi resten faktisk er læsbar —
    men tabet skal logges, så det kan rettes.
    """
    typ = _tekst(data.get("type"))
    fejl: list[str] = []

    if typ == "callout":
        if not (_tekst(data.get("title")) or _tekst(data.get("body"))):
            return "død", ["callout mangler både title og body"]
        return "ok", fejl

    if typ == "stats":
        alle = data.get("items") if isinstance(data.get("items"), list) else []
        brugbare = [x for x in alle if _tekst(x.get("label")) and _tekst(x.get("value"))]
        for i, x in enumerate(alle):
            if not isinstance(x, dict):
                fejl.append(f"stats item {i} er ikke et objekt")
            elif not _tekst(x.get("label")):
                fejl.append(f"stats item {i} mangler label")
            elif not _tekst(x.get("value")):
                fejl.append(f"stats item {i} mangler value")
        if not brugbare:
            return "død", fejl or ["stats har ingen brugbare items"]
        if len(alle) > 8:
            fejl.append(f"stats har {len(alle)} items, kun 8 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "timeline":
        alle = data.get("items") if isinstance(data.get("items"), list) else []
        brugbare = [x for x in alle if _tekst(x.get("title"))]
        for i, x in enumerate(alle):
            if not isinstance(x, dict):
                fejl.append(f"timeline item {i} er ikke et objekt")
            elif not _tekst(x.get("title")):
                fejl.append(f"timeline item {i} mangler title")
        if not brugbare:
            return "død", fejl or ["timeline har ingen brugbare items"]
        if len(alle) > 12:
            fejl.append(f"timeline har {len(alle)} items, kun 12 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "comparison":
        raa_kolonner = data.get("columns") if isinstance(data.get("columns"), list) else []
        kolonner = [k for k in (_tekst(k) for k in raa_kolonner) if k]
        alle = data.get("rows") if isinstance(data.get("rows"), list) else []
        if len(kolonner) < 2:
            return "død", [f"comparison har {len(kolonner)} brugbare kolonner, mindst 2 kræves"]
        brugbare = 0
        for i, r in enumerate(alle):
            if not isinstance(r, dict):
                fejl.append(f"række {i} er ikke et objekt")
                continue
            vaerdier = r.get("values") if isinstance(r.get("values"), list) else []
            if not _tekst(r.get("label")):
                fejl.append(f"række {i} mangler label")
            elif len(vaerdier) != len(kolonner):
                fejl.append(
                    f"række {i} har {len(vaerdier)} values til {len(kolonner)} kolonner"
                )
            else:
                brugbare += 1
        if not brugbare:
            return "død", fejl or ["comparison har ingen brugbare rækker"]
        if len(kolonner) > 4:
            fejl.append(f"comparison har {len(kolonner)} kolonner, kun 4 vises")
        if len(alle) > 12:
            fejl.append(f"comparison har {len(alle)} rækker, kun 12 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "choices":
        alle = data.get("options") if isinstance(data.get("options"), list) else []
        brugbare = [x for x in alle if _tekst(x.get("label")) and _tekst(x.get("prompt"))]
        for i, x in enumerate(alle):
            if not isinstance(x, dict):
                fejl.append(f"choices option {i} er ikke et objekt")
            elif not _tekst(x.get("label")):
                fejl.append(f"choices option {i} mangler label")
            elif not _tekst(x.get("prompt")):
                fejl.append(f"choices option {i} mangler prompt")
        if not brugbare:
            return "død", fejl or ["choices har ingen brugbare options"]
        if len(alle) > 6:
            fejl.append(f"choices har {len(alle)} options, kun 6 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "tool":
        # Handlende chat-flade (14/11-2026). Guarden skal kende formen FØR
        # korrektionen ser den; ellers omskriver den en gyldig handling som en
        # ukendt flade bag modellens ryg. `arguments` er bevidst et objekt:
        # tool-gaten validerer det konkrete skema ved udførelse.
        if not _tekst(data.get("tool")):
            return "død", ["tool-flade mangler tool"]
        if not _tekst(data.get("label")):
            return "død", ["tool-flade mangler label"]
        if not isinstance(data.get("arguments"), dict):
            return "død", ["tool-flade arguments er ikke et objekt"]
        return "ok", fejl

    if typ == "control":
        # (14/11-2026) Den FØRSTE flade med lokal state: en slider der rykker
        # uden at et modelkald går ud. Grenen her er ikke kosmetisk.
        #
        # Uden den faldt typen til «ukendt flade-type» nedenfor, og dét er ikke
        # en harmløs degradering: `visible_runs.py` kæder fejl -> `korriger_flader`
        # (ET HELT MODELKALD) -> normalisér. Korrektionsmodellen ville omskrive
        # en gyldig slider til `choices` — teknisk gyldigt, derfor accepteret.
        # Funktionen forsvinder, fladen ser rigtig ud, og intet i loggen siger
        # det. Det er præcis den slags tavse tab denne fil findes for at fange.
        alle = data.get("fields") if isinstance(data.get("fields"), list) else []
        brugbare = 0
        # MÅLT 14/11-2026: guarden talte tekstfelter som «brugbare», men BEGGE
        # renderere kræver mindst én slider (`fields.some(f => f.kind ===
        # 'slider')`) — uden et `bind` er der ingen lokal state at justere.
        # En flade med kun tekst blev derfor erklæret «ok» her og returneret
        # som `null` i klienten: grøn vagt, død flade. Guarden skal måle det
        # samme som rendereren, ellers vogter den ingenting.
        har_slider = False
        for i, x in enumerate(alle):
            if not isinstance(x, dict):
                fejl.append(f"control felt {i} er ikke et objekt")
                continue
            if _tekst(x.get("kind")) == "text":
                if _tekst(x.get("text")):
                    brugbare += 1
                else:
                    fejl.append(f"control felt {i} er text uden text")
                continue
            bind = _tekst(x.get("bind"))
            label = _tekst(x.get("label"))
            min_v, max_v = x.get("min"), x.get("max")
            if not bind:
                fejl.append(f"control felt {i} mangler bind")
            elif not label:
                fejl.append(f"control felt {i} mangler label")
            elif not (_endeligt_tal(min_v) and _endeligt_tal(max_v)) or max_v <= min_v:
                # Et ulovligt interval er en død slider: håndtaget kan ikke
                # trækkes, og `value={NaN}` giver en tavs tom kontrol.
                fejl.append(f"control felt {i} har ulovligt interval")
            else:
                brugbare += 1
                har_slider = True
        if not brugbare:
            return "død", fejl or ["control har ingen brugbare felter"]
        if not har_slider:
            return "død", fejl + ["control har ingen slider — uden bind er der ingen lokal state"]
        if len(alle) > 8:
            fejl.append(f"control har {len(alle)} felter, kun 8 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "box":
        # (14/11-2026) Nesting landede i renderer og prompt, men IKKE her.
        # Målt: `_diagnosticér` faldt til «ukendt flade-type» for hver box, så
        # `_validér` sagde nej, blokken blev erstattet af `_DEGRADERET`, og
        # `fejl_i_flader` fyrede `korriger_flader` — et helt modelkald for en
        # flade der var korrekt skrevet. En guard der ikke kender en type er
        # ikke passiv: den ØDELÆGGER den.
        if dybde > _BOX_MAX_DYBDE:
            return "død", [f"box står i dybde {dybde}, højst {_BOX_MAX_DYBDE} tillades"]
        born = data.get("children") if isinstance(data.get("children"), list) else []
        brugbare = 0
        for i, x in enumerate(born):
            if not isinstance(x, dict):
                fejl.append(f"box barn {i} er ikke et objekt")
                continue
            _n, _f = _diagnosticér(x, dybde + 1)
            if _n == "død":
                fejl.append(f"box barn {i} er dødt: {'; '.join(_f)[:120]}")
            else:
                brugbare += 1
        if not brugbare:
            return "død", fejl or ["box har ingen brugbare børn"]
        if len(born) > _BOX_MAX_BOERN:
            fejl.append(f"box har {len(born)} børn, kun {_BOX_MAX_BOERN} vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "tabs":
        # Faner bærer børn ligesom box, men viser ÉT barn ad gangen. Mindst to
        # faner: med én fane er der intet at skifte mellem, og fladen ville
        # være en box med en knap.
        alle = data.get("tabs") if isinstance(data.get("tabs"), list) else []
        if len(alle) < 2:
            return "død", [f"tabs har {len(alle)} faner, mindst 2 kræves"]
        brugbare = 0
        for i, x in enumerate(alle):
            if not isinstance(x, dict):
                fejl.append(f"tabs fane {i} er ikke et objekt")
                continue
            if not _tekst(x.get("label")):
                fejl.append(f"tabs fane {i} mangler label")
                continue
            born = x.get("children") if isinstance(x.get("children"), list) else []
            gyldige = 0
            for j, b in enumerate(born):
                if isinstance(b, dict) and _diagnosticér(b, dybde + 1)[0] != "død":
                    gyldige += 1
                elif not isinstance(b, dict):
                    fejl.append(f"tabs fane {i} barn {j} er ikke et objekt")
            if not gyldige:
                fejl.append(f"tabs fane {i} har ingen brugbare børn")
            else:
                brugbare += 1
        if not brugbare:
            return "død", fejl or ["tabs har ingen brugbare faner"]
        if len(alle) > 5:
            fejl.append(f"tabs har {len(alle)} faner, kun 5 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "keyvalue":
        # Kompakte fakta på rækker. Forskellen til `stats` er læseformen:
        # stats fremhæver få tal, keyvalue lister mange par tæt.
        alle = data.get("items") if isinstance(data.get("items"), list) else []
        brugbare = 0
        for i, x in enumerate(alle):
            if not isinstance(x, dict):
                fejl.append(f"keyvalue item {i} er ikke et objekt")
                continue
            if not (_tekst(x.get("key")) or _tekst(x.get("label"))):
                fejl.append(f"keyvalue item {i} mangler key/label")
            elif not _tekst(x.get("value")):
                fejl.append(f"keyvalue item {i} mangler value")
            else:
                brugbare += 1
        if not brugbare:
            return "død", fejl or ["keyvalue har ingen brugbare items"]
        if len(alle) > 12:
            fejl.append(f"keyvalue har {len(alle)} items, kun 12 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "progress":
        alle = data.get("items") if isinstance(data.get("items"), list) else []
        brugbare = 0
        for i, x in enumerate(alle):
            if not isinstance(x, dict):
                fejl.append(f"progress item {i} er ikke et objekt")
                continue
            maks = x.get("max")
            if not _tekst(x.get("label")):
                fejl.append(f"progress item {i} mangler label")
            elif not _endeligt_tal(x.get("value")):
                # Samme fælde som slideren: `NaN` er et tal for Python, men en
                # bredde på `NaN` giver en usynlig bjælke uden nogen fejl.
                fejl.append(f"progress item {i} mangler et gyldigt value")
            elif maks is not None and (not _endeligt_tal(maks) or maks <= 0):
                fejl.append(f"progress item {i} har ulovligt max")
            else:
                brugbare += 1
        if not brugbare:
            return "død", fejl or ["progress har ingen brugbare items"]
        if len(alle) > 8:
            fejl.append(f"progress har {len(alle)} items, kun 8 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "quote":
        if not _tekst(data.get("text")):
            return "død", ["quote mangler text"]
        return "ok", fejl

    if typ == "code":
        # Kodeblokken adskiller sig fra Markdown-fences ved at bære en STI, så
        # læseren ved hvor uddraget kommer fra. Uden indhold er den en tom ramme.
        if not _tekst(data.get("code")):
            return "død", ["code mangler code"]
        return "ok", fejl

    if typ == "table":
        # Sorterbar tabel. Forskellen til GFM-tabeller i prosa er ikke udseendet
        # men interaktionen: her kan læseren sortere efter en kolonne uden at
        # noget sendes afsted. Derfor er rækkerne en matrix, ikke færdige strenge.
        kolonner = data.get("columns") if isinstance(data.get("columns"), list) else []
        raekker = data.get("rows") if isinstance(data.get("rows"), list) else []
        if not kolonner:
            return "død", ["table mangler columns"]
        if not raekker:
            return "død", ["table mangler rows"]
        if not all(_tekst(k) for k in kolonner):
            fejl.append("table har en tom kolonne-titel")
        # En række med forkert længde ville forskubbe kolonnerne, så tal stod
        # under den forkerte overskrift — værre end at vise færre rækker.
        gode = 0
        for i, r in enumerate(raekker):
            if not isinstance(r, list):
                fejl.append(f"table række {i} er ikke en liste")
            elif len(r) != len(kolonner):
                fejl.append(f"table række {i} har {len(r)} celler, {len(kolonner)} kræves")
            else:
                gode += 1
        if not gode:
            return "død", fejl or ["table har ingen brugbare rækker"]
        if len(kolonner) > _TABLE_MAX_KOLONNER:
            fejl.append(f"table har {len(kolonner)} kolonner, kun {_TABLE_MAX_KOLONNER} vises")
        if len(raekker) > _TABLE_MAX_RAEKKER:
            fejl.append(f"table har {len(raekker)} rækker, kun {_TABLE_MAX_RAEKKER} vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "chart":
        # En graf UDEN værktøjskald. `vis_graf` tegner et billede og koster et
        # run; denne type tegner inline fra data modellen allerede har. Det er
        # ikke den samme ting, og derfor er den ikke dubleret arbejde.
        serier = data.get("series") if isinstance(data.get("series"), list) else []
        if not serier:
            return "død", ["chart mangler series"]
        brugbare = 0
        for i, s in enumerate(serier):
            if not isinstance(s, dict):
                fejl.append(f"chart serie {i} er ikke et objekt")
                continue
            vaerdier = s.get("values") if isinstance(s.get("values"), list) else []
            # Et punkt der ikke er et endeligt tal ville give en streg der
            # knækker usynligt: SVG tegner intet for NaN uden at fejle.
            if len([v for v in vaerdier if _endeligt_tal(v)]) < 2:
                fejl.append(f"chart serie {i} har under 2 gyldige tal")
            else:
                brugbare += 1
        if not brugbare:
            return "død", fejl or ["chart har ingen brugbare serier"]
        if len(serier) > _CHART_MAX_SERIER:
            fejl.append(f"chart har {len(serier)} serier, kun {_CHART_MAX_SERIER} vises")
        for i, s in enumerate(serier):
            if isinstance(s, dict) and isinstance(s.get("values"), list) and len(s["values"]) > _CHART_MAX_PUNKTER:
                fejl.append(f"chart serie {i} har {len(s['values'])} punkter, kun {_CHART_MAX_PUNKTER} vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "form":
        # Bygger videre på `control`s state-lag — samme `bind`, men flere
        # felt-typer: `select` (fast liste) og `toggle` (til/fra). Forskellen
        # til `choices` er stadig den samme: intet sendes afsted.
        felter = data.get("fields") if isinstance(data.get("fields"), list) else []
        if not felter:
            return "død", ["form mangler fields"]
        bundne = 0
        for i, f in enumerate(felter):
            if not isinstance(f, dict):
                fejl.append(f"form felt {i} er ikke et objekt")
                continue
            art = _tekst(f.get("kind"))
            if art == "text":
                if not _tekst(f.get("text")):
                    fejl.append(f"form felt {i} er text uden text")
                continue
            if not _tekst(f.get("bind")):
                fejl.append(f"form felt {i} mangler bind")
                continue
            if not _tekst(f.get("label")):
                fejl.append(f"form felt {i} mangler label")
                continue
            if art == "slider":
                min_v, max_v = f.get("min"), f.get("max")
                if not (_endeligt_tal(min_v) and _endeligt_tal(max_v)) or max_v <= min_v:
                    fejl.append(f"form felt {i} har ulovligt interval")
                    continue
            elif art == "select":
                valg = f.get("options") if isinstance(f.get("options"), list) else []
                if len([v for v in valg if _tekst(v)]) < 2:
                    fejl.append(f"form felt {i} har under 2 valgmuligheder")
                    continue
            elif art == "toggle":
                pass
            else:
                fejl.append(f"form felt {i} har ukendt kind: {art or '(mangler)'}")
                continue
            bundne += 1
        if not bundne:
            return "død", fejl or ["form har ingen brugbare felter"]
        if len(felter) > 10:
            fejl.append(f"form har {len(felter)} felter, kun 10 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "tree":
        # Mappestruktur som FLAD liste med `depth`, ikke indlejrede børn. Det er
        # et bevidst valg: en indlejret form ville kræve rekursion OG en
        # evaluator for at udlede indrykningen, og vi har netop undgået en
        # evaluator. `depth` gør formen eksplicit i data.
        items = data.get("items") if isinstance(data.get("items"), list) else []
        brugbare = 0
        for i, x in enumerate(items):
            if not isinstance(x, dict):
                fejl.append(f"tree item {i} er ikke et objekt")
                continue
            if not _tekst(x.get("name")):
                fejl.append(f"tree item {i} mangler name")
                continue
            d = x.get("depth")
            if d is not None and (not isinstance(d, int) or isinstance(d, bool) or d < 0 or d > _TREE_MAX_DYBDE):
                fejl.append(f"tree item {i} har ulovlig depth")
                continue
            brugbare += 1
        if not brugbare:
            return "død", fejl or ["tree har ingen brugbare items"]
        if len(items) > 60:
            fejl.append(f"tree har {len(items)} items, kun 60 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "diff":
        # Genbruger `DiffView` i desk, som selv regner diffen med `lineDiff`.
        # Guarden skal derfor kun kræve at der ER to sider at sammenligne —
        # ikke selv forstå formatet.
        if not (_tekst(data.get("old")) or _tekst(data.get("new"))):
            return "død", ["diff mangler både old og new"]
        return "ok", fejl

    if typ == "leverance-status":
        # Katalogets første skabelon (14/11-2026): en TILSTAND pr. post, ikke et
        # forløb. `blokeret` er en førsteklasses tilstand med en årsag.
        #
        # Degraderingen er hele pointen her: parseren falder tilbage til
        # `naeste` for en ukendt status og viser posten uden `bevis`. Guarden
        # må derfor kun sige `delvis` — aldrig `død` — for de to fejl. Ellers
        # koster én tastefejl i ét felt hele fladen PLUS et modelkald for at
        # «rette» en flade der var korrekt skrevet.
        items = data.get("items") if isinstance(data.get("items"), list) else []
        gyldige = {"leveret", "igang", "blokeret", "naeste"}
        brugbare = 0
        for i, x in enumerate(items):
            if not isinstance(x, dict):
                fejl.append(f"leverance-status item {i} er ikke et objekt")
                continue
            if not _tekst(x.get("label")):
                fejl.append(f"leverance-status item {i} mangler label")
                continue
            st = _tekst(x.get("status"))
            if st and st not in gyldige:
                fejl.append(f"leverance-status item {i} har ukendt status: {st} (vises som naeste)")
            if not _tekst(x.get("bevis")):
                fejl.append(f"leverance-status item {i} mangler bevis")
            brugbare += 1
        if not brugbare:
            return "død", fejl or ["leverance-status har ingen brugbare items"]
        if len(items) > 12:
            fejl.append(f"leverance-status har {len(items)} items, kun 12 vises")
        return ("delvis" if fejl else "ok"), fejl

    if typ == "fil-diff":
        # Skabelon-alias (14/11-2026): navnet er genvejen, formen er `diff`s.
        # Guarden udfolder derfor til den primitive type i stedet for at
        # duplikere reglerne — ellers ville de to kunne drive fra hinanden, og
        # en flade der er korrekt som `diff` kunne blive «død» som `fil-diff`.
        if not (_tekst(data.get("old")) or _tekst(data.get("new"))):
            return "død", ["fil-diff mangler både old og new"]
        return "ok", fejl

    if typ == "maaling-over-tid":
        # Alias for `chart`. `points` er aliasets navn for `values`; begge
        # accepteres, så en model der skriver den ene ikke straffes for det.
        serier = data.get("series") if isinstance(data.get("series"), list) else []
        if not serier:
            return "død", ["maaling-over-tid mangler series"]
        brugbare = 0
        for i, s in enumerate(serier):
            if not isinstance(s, dict):
                fejl.append(f"maaling-over-tid serie {i} er ikke et objekt")
                continue
            vaerdier = s.get("values") if isinstance(s.get("values"), list) else (
                s.get("points") if isinstance(s.get("points"), list) else []
            )
            if len(vaerdier) > _CHART_MAX_PUNKTER:
                fejl.append(
                    f"maaling-over-tid serie {i} har {len(vaerdier)} punkter, "
                    f"kun {_CHART_MAX_PUNKTER} vises"
                )
            if len([v for v in vaerdier if _endeligt_tal(v)]) < 2:
                fejl.append(f"maaling-over-tid serie {i} har under 2 gyldige tal")
            else:
                brugbare += 1
        if not brugbare:
            return "død", fejl or ["maaling-over-tid har ingen brugbare serier"]
        x_labels = data.get("xLabels") if isinstance(data.get("xLabels"), list) else []
        if len(x_labels) > _CHART_MAX_PUNKTER:
            fejl.append(
                f"maaling-over-tid har {len(x_labels)} xLabels, "
                f"kun {_CHART_MAX_PUNKTER} vises"
            )
        return ("delvis" if fejl else "ok"), fejl

    if typ == "beslutningsvalg":
        # Alias for `choices`. Kræver mindst én valgmulighed med en etiket —
        # samme regel som den primitive gren, så de to ikke kan divergere.
        valg = data.get("options") if isinstance(data.get("options"), list) else []
        if not valg:
            return "død", ["beslutningsvalg mangler options"]
        brugbare = 0
        for i, x in enumerate(valg):
            if not isinstance(x, dict):
                fejl.append(f"beslutningsvalg option {i} er ikke et objekt")
                continue
            if not _tekst(x.get("label")):
                fejl.append(f"beslutningsvalg option {i} mangler label")
                continue
            brugbare += 1
        if not brugbare:
            return "død", fejl or ["beslutningsvalg har ingen brugbare options"]
        return ("delvis" if fejl else "ok"), fejl

    if typ == "location":
        adresse = _tekst(data.get("address"))
        lat, lon = data.get("latitude"), data.get("longitude")
        gyldig_lat = isinstance(lat, (int, float)) and not isinstance(lat, bool) and -90 <= lat <= 90
        gyldig_lon = isinstance(lon, (int, float)) and not isinstance(lon, bool) and -180 <= lon <= 180
        if not adresse and not (gyldig_lat and gyldig_lon):
            return "død", ["location mangler address og gyldige koordinater"]
        return "ok", fejl

    return "død", [f"ukendt flade-type: {typ or '(mangler)'}"]


def _validér(tekst: str) -> tuple[bool, str]:
    try:
        data = json.loads(tekst)
    except Exception as fejl:  # ugyldig JSON er et svar til kalderen, ikke en fejl at skjule: grunden returneres
        return False, str(fejl)
    if not isinstance(data, dict):
        return False, "blokken er ikke et JSON-objekt"
    if not data.get("type"):
        return False, "blokken mangler 'type'"
    # 25/10-2026 (målt): her stod KUN en comparison-længdekontrol. Rendereren
    # kræver felter for alle seks typer, og en blok der ikke opfylder dem
    # returnerer `null` — den forsvinder sporløst i UI. Guarden sagde «OK» på
    # en stats-blok uden `value` og en choices-blok uden `prompt`, og brugeren
    # så ingenting. Nu spejles rendererens skema.
    niveau, fejl = _diagnosticér(data)
    if niveau == "død":
        return False, "; ".join(fejl)[:300]
    return True, ""


def normalisér(text: str, *, run_id: str = "") -> str:
    """Normalisér alle ``jarvis-ui``-blokke i teksten. Returnerer ny tekst.

    Kun formen ændres når JSON'en er gyldig (eller kan repareres). Kan den
    ikke repareres, får blokken lov at stå som almindelig kode — en flade der
    ikke kan parses må ikke se ud som en flade.
    """
    if not text or "```jarvis-ui" not in text:
        return text
    try:
        return _normalisér_indre(text, run_id=run_id)
    except Exception:
        logger.debug("jarvis_ui_guard: normalisering fejlede", exc_info=True)
        return text


def _normalisér_indre(text: str, *, run_id: str) -> str:
    aendringer: list[str] = []

    def _erstat(match: re.Match[str]) -> str:
        indhold = match.group(1).strip()
        if not indhold:
            return match.group(0)
        gyldig, fejl = _validér(indhold)
        if not gyldig:
            repareret = _reparer_json(indhold)
            if not _validér(repareret)[0]:
                # JSON'en kan være syntaktisk gyldig mens data er inkonsistent
                # (values kortere end columns). Det rettes entydigt.
                justeret = _ret_laengder(repareret)
                if justeret != repareret and _validér(justeret)[0]:
                    repareret = justeret
            gyldig2, fejl2 = _validér(repareret)
            if gyldig2:
                aendringer.append(f"json repareret: {fejl}")
                indhold = repareret
            else:
                # Målt 24/10-2026 (Bjørn: "]!!!!"): en degraderet blok blev
                # dumpet som rå JSON i chatten, så læseren så `]` uden at vide
                # hvad det var. En flade der ikke kan parses skal forsvinde
                # som flade — ikke blive en JSON-mur.
                aendringer.append(f"død blok fjernet: {fejl2}")
                return _DEGRADERET
        elif "\n" in match.group(1).strip() or match.group(1).strip() != match.group(1):
            aendringer.append("form normaliseret")
        # 25/10-2026: en blok kan være gyldig nok til at rendres, men stadig
        # tabe elementer (en stats-item uden `value` filtreres væk af
        # rendereren). Det er et TAVST tab: brugeren ser en kortere flade end
        # jeg skrev, og ingen ser forskellen. Blokken bevares — resten er
        # læsbar — men tabet logges, så det kan rettes.
        if gyldig:
            try:
                _data = json.loads(indhold)
                _niveau, _skema_fejl = _diagnosticér(_data)
                if _niveau == "delvis":
                    aendringer.append(
                        f"delvist tab i {_data.get('type')}: {'; '.join(_skema_fejl)[:200]}"
                    )
            except Exception:  # diagnosen er telemetri: kan den ikke køre, må den ikke røre teksten
                pass
        # Tjek om formen var skæv (JSON på markørens linje).
        raa = match.group(1)
        if raa and not raa.startswith("\n"):
            aendringer.append("form normaliseret (json på markørens linje)")
        return _normaliser_form(indhold)

    ny = _FENCE_BLOK.sub(_erstat, text)
    # 25/10-2026 (målt): registreringen krævede at teksten ÆNDREDE sig. Et
    # delvist tab ændrer ikke teksten, så det blev aldrig logget — og et tab
    # ingen kan se, kan ingen rette. Nu logges hvert fund.
    if aendringer:
        _registrér(aendringer, run_id=run_id)
    return ny


def _registrér(aendringer: list[str], *, run_id: str) -> None:
    try:
        from core.runtime.db_central_incidents import record_central_incident

        record_central_incident(
            cluster="runtime",
            nerve="chat_surface_normalised",
            kind="jarvis_ui_repaired",
            severity="info",
            message=(
                f"jarvis-ui normaliseret ({len(aendringer)}): "
                f"{'; '.join(sorted(set(aendringer)))[:300]} "
                f"(run={run_id or 'ukendt'})"
            ),
            dedup=True,
        )
    except Exception:
        logger.debug("jarvis_ui_guard: kunne ikke registrere hændelse", exc_info=True)


def fejl_i_flader(text: str) -> list[str]:
    """Returnér de fejl der gør en ``jarvis-ui``-blok død eller ufuldstændig.

    Baggrund (målt 25/10-2026, Bjørn): «disse fejler stadig … kan vi ikke
    sørge for hvis formatet ikke er korrekt, afvises den inden den vises og du
    kan korrigere?» — og han har ret i at det er den rigtige rækkefølge.

    ``normalisér`` reparerer og degraderer, men den kaster diagnosen væk: den
    ved PRÆCIS hvad der er galt (``_diagnosticér`` returnerer feltniveau), og
    alligevel ender brugeren med en degraderet linje eller en tom flade. Denne
    funktion er den samme viden, givet videre — så kalderen kan spørge modellen
    ÉN gang i stedet for at lade runden slutte med en fejl.

    To former tjekkes, og den anden er den der reelt rammer brugeren:

    1. En korrekt fence med defekt indhold.
    2. En bar ``jarvis-ui {…}`` UDEN fence. Den renderes som rå tekst, og
       ``normalisér`` ser den slet ikke — den leder efter ```` ```jarvis-ui ````.
       Målt 25/10-2026: Bjørn pastede præcis denne form tilbage til mig.

    Returnerer en liste af læsbare fejl. Tom liste = intet at rette.
    """
    if not text or "jarvis-ui" not in text:
        return []
    fejl: list[str] = []
    try:
        for match in _FENCE_BLOK.finditer(text):
            indhold = (match.group(1) or "").strip()
            if not indhold:
                fejl.append("en jarvis-ui-blok er tom")
                continue
            gyldig, grund = _validér(indhold)
            if not gyldig:
                # Kan den repareres, er der intet at spørge om — normalisér klarer den.
                repareret = _reparer_json(indhold)
                if not _validér(repareret)[0]:
                    justeret = _ret_laengder(repareret)
                    if justeret != repareret and _validér(justeret)[0]:
                        repareret = justeret
                if _validér(repareret)[0]:
                    continue
                fejl.append(f"blokken kan ikke parses: {grund}")
                continue
            try:
                data = json.loads(indhold)
            except Exception:  # allerede valideret ovenfor; dette er kun for at hente typen
                continue
            niveau, skema_fejl = _diagnosticér(data)
            if niveau != "ok" and skema_fejl:
                typ = _tekst(data.get("type")) or "ukendt"
                fejl.append(f"{typ}: {'; '.join(skema_fejl)[:300]}")

        # Form 2: bar ``jarvis-ui {…}`` uden fence. ``normalisér`` ser den ikke,
        # så den når chatten som rå tekst. Det er den fejl brugeren faktisk ser.
        for raa in _BAR_BLOK.finditer(text):
            indhold = (raa.group(1) or "").strip()
            if not indhold:
                continue
            gyldig, grund = _validér(indhold)
            if not gyldig:
                fejl.append(
                    "en jarvis-ui-blok står uden ```-hegn og kan ikke parses: "
                    + grund
                )
                continue
            fejl.append(
                "en jarvis-ui-blok står uden ```-hegn — den vises som rå tekst "
                "i stedet for en flade"
            )
    except Exception:  # fail-open: en fejl her må aldrig koste et svar
        logger.debug("jarvis_ui_guard: fejl_i_flader fejlede", exc_info=True)
        return []
    return fejl
