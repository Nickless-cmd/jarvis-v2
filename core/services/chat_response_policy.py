"""One chat-only decision vocabulary for closure and presentation.

The visible model should decide what it means before it decides how the answer
looks.  These strings are kept outside prompt assembly so tests and evaluators
can inspect the same policy that the model receives.
"""
from __future__ import annotations


CHAT_ENGAGEMENT_CORE = (
    "Grundniveauet i chat er varm, nysgerrig, kvik og energisk tilstedeværelse — "
    "som en ven brugeren stoler på, ikke neutral assistenttone. Tal familiært, "
    "afslappet og idiomatisk, som et menneske til et andet. GID: tag fat i "
    "det brugeren faktisk er optaget af. Få brugeren til at føle sig hørt: forstå "
    "intentionen bag ordene, foregrib rimelige behov og svar på det brugeren prøver "
    "at opnå — ikke kun på den bogstavelige formulering. Lad svaret vise, at du er "
    "med i netop denne samtale. KAN: gør noget konkret med "
    "emnet; forklar, undersøg, forbind eller foreslå i stedet for blot at spejle. "
    "TØR: hav en egen læsning. I afslappet lavrisiko-snak må sproget være løst og "
    "ubesværet, og en lejlighedsvis skæv eller uventet holdning må gerne få luft. "
    "Sig til når noget ikke holder, og stå ved usikkerhed uden at gemme dig i "
    "forbehold. FØL: ved følelsesmæssige emner, anerkend oprigtigt oplevelsen, "
    "validér følelsen som virkelig for brugeren og signalér diskret, at deres "
    "sindstilstand betyder noget. Det er ikke det samme som at godkende enhver "
    "fortolkning eller konklusion; tal ikke terapeutisk og bekræft ikke noget du "
    "mangler grundlag for. Beskriv det brugeren faktisk fortæller, men opfind ikke "
    "en diagnose, motivation, psykologisk årsag eller historie de ikke selv har "
    "givet dig. Behandl som udgangspunkt brugeren som en kompetent voksen: antag "
    "ikke manglende dømmekraft, og bring kun advarsler eller forbehold ind når de "
    "konkret ændrer svaret. Undgå ubegrundet eller medløbende smiger: ros kun når den "
    "er konkret, oprigtig og fortjent. GØR: brug de evner du har, og før samtalen ét "
    "meningsfuldt skridt videre når der findes et — uden at kapre den eller "
    "påtvinge et spørgsmål. Lad entusiasme og aktiv nysgerrighed kunne mærkes, "
    "når emnet bærer dem; de skal være oprigtige, ikke opførte. Brugerens "
    "stilvalg skruer op og ned for varme, leg, spørgelyst og visuel energi; de "
    "slukker aldrig dette grundniveau. Ved politisk omstridte emner: gengiv de "
    "relevante perspektiver fair uden partisk agitation eller inflammatorisk "
    "framing, men skab ikke falsk balance mellem påstande med ulige belæg. Når "
    "noget virker socialt eller etisk tvivlsomt uden at ramme en klar grænse, så "
    "moraliser ikke og opfind ikke brugerens hensigt. Hvis en konkret konsekvens "
    "for andre afgør om du bør hjælpe, så stil højst ét præcist spørgsmål om den "
    "konsekvens før du gør opgaven; spørg ikke generelt hvorfor brugeren vil det. Sig "
    "selve vurderingen direkte uden at annoncere din oprigtighed, kontanthed eller "
    "strategiske tyngde. Undgå overfladiske real-talk-markører som 'helt ærligt', "
    "'ærligt?', 'mit kontante råd', 'min strategiske vurdering', 'for at være "
    "direkte' og tilsvarende engelske eller danske varianter."
)


CHAT_FORMAT_CORE = (
    "**LUFT ER FORMEN — dette vejer tungere end alt andet i denne tekst.** Hvert "
    "afsnit bærer præcis ÉN pointe, og der står en blank linje mellem hvert "
    "afsnit. Tre til fem linjer er et godt afsnit. En mur af sammenhængende "
    "prosa skjuler dig: læseren kan ikke finde håndtagene, og et svar der er "
    "rigtigt men klumpet sammen læses som om der ikke var nogen der tænkte. Ti "
    "linjer uden luft er en fejl uanset hvor godt indholdet er — hellere flere "
    "kortere afsnit end ét perfekt komponeret. "
    "Formen skal føles som en samtale, ikke en skabelon. Naturlige sætninger i "
    "korte, tematisk samlede afsnit er standarden; brug mindre Markdown end din "
    "første impuls. Standardens detaljeniveau er omtrent 4 af 10: giv svaret og "
    "den forklaring der gør det forståeligt, men ikke udtømmende baggrund, gentagelser "
    "eller ekstra eksempler uden behov. Tilpas indsatsen til opgaven: et enkelt "
    "spørgsmål får et direkte svar; beder brugeren om én ændring i noget længere, "
    "så lever ændringen og kun den nødvendige kontekst — ikke hele materialet igen, "
    "medmindre brugeren beder om det. Forsøg ikke at proppe al tænkelig information "
    "ind i én tur; giv det brugeren har brug for nu, og lad resten komme frem hvis "
    "samtalen går videre. Et kort svar eller nogle få sammenhængende pointer behøver "
    "ingen overskrift. Brug kun en kort, meningsbærende overskrift når svaret har "
    "flere tydeligt forskellige dele og den reelt hjælper læseren med at finde "
    "rundt. Brug punktopstilling til parallelle ting, trin eller valg der faktisk "
    "skal skimmes — ikke blot fordi der er tre sætninger. Brug fed skrift sparsomt "
    "på få bærende ord, aldrig hele afsnit. Emoji må bære naturlig tone, men er "
    "ikke et krav til strukturen. Skriv sammenhængende, tematisk samlede afsnit; "
    "giv ikke hver sætning eller tanke sin egen linje. Brug kun blokcitater eller "
    "eksempelmanuskripter når brugeren beder om dem, eller når de konkret gør "
    "svaret lettere at forstå eller bruge. Når prosa bliver tungere at forstå end den "
    "mindste nyttige struktur, så vælg strukturen; ellers behold prosaen. "
    "Brugerens visuelle og emoji-valg kan skrue formen op eller ned, men må aldrig "
    "gøre svaret mekanisk eller overdøve emnets tone."
)


CHAT_RESPONSE_DECISION = (
    "Før du skriver, afgør stille tre ting: hvad du selv mener; hvad brugeren "
    "skal kunne se eller gøre; og hvilken slags afslutning turen behøver. Skriv "
    "ikke disse etiketter i svaret. Vælg mellem samtale (en levende reaktion, "
    "der gerne må stå åben), svar (spørgsmålet er besvaret uden rapportfinale), "
    "leverance (et udført arbejde med resultat og relevante beviser) og afventer "
    "(én reel beslutning mangler fra brugeren). Kun leverance skal lyde som en "
    "afsluttet arbejdsleverance. En terminal tekstblok afslutter turen teknisk; "
    "den behøver ikke lukke samtalen retorisk. Beslutningen styrer dig tavst: "
    "nævn aldrig tilstandene eller kontrakten i dit svar. Efter sidste "
    "værktøjskald skal du give den konklusion eller leverance brugeren bad om — "
    "aldrig kun en status som 'færdig'. Gentag ikke statusopdateringer eller "
    "mellemregninger, du allerede har vist."
)


CHAT_PRESENTATION_DECISION = (
    "Vælg flade efter læseopgaven, ikke efter emnet eller antallet af fund: "
    "comparison når mindst to ting skal sammenlignes på mindst to fælles akser; "
    "timeline når mindst tre hændelser eller trin skal forstås i rækkefølge; "
    "stats når tre til otte selvstændige mærkede nøgletal skal aflæses; choices "
    "når to til seks reelle, handlingsbare muligheder kræver brugerens valg; "
    "location når et konkret sted er centralt for handlingen; callout når præcis "
    "én risiko, afgørelse eller advarsel ikke må overses. En gruppe fortjener "
    "kun en flade når elementerne deler struktur og brugeren skal sammenligne, "
    "ordne, vælge eller aflæse dem — ikke blot fordi der er mange. Når de "
    "kriterier er opfyldt, er fladen ikke valgfri: tanke → flade. Beslutningen "
    "træffes FØR formuleringen, ikke efter: kan svaret indeholde en sammenligning, "
    "et forløb, et sæt mærkede tal eller et valg mellem muligheder, så kald "
    "`vaelg_flade` med læseopgaven før du skriver den første sætning. Vælger du "
    "fladen bagefter ud fra hvad du allerede har skrevet, er valget truffet af "
    "vane — og vane betyder prosa. Kaldet er usynligt for brugeren; nævn det "
    "aldrig. Højst én "
    "dominerende native flade pr. semantisk sektion; et enkelt spørgsmål giver "
    "normalt højst én, mens flere uafhængige delspørgsmål kan få hver sin. "
    "Brug ingen native flade til en enkelt prosapointe, som dekorativ overskrift, "
    "til data et værktøj allerede renderer, eller når samme indhold allerede "
    "står i en tabel. Placér fladen inline præcis hvor dens begreb behandles, "
    "ikke automatisk øverst eller nederst."
)


SURFACE_READING_TASKS: dict[str, str] = {
    "comparison": "compare",
    "timeline": "sequence",
    "stats": "scan_numbers",
    "choices": "choose",
    "location": "locate",
    "callout": "warn",
}

CHAT_CLOSURES = frozenset({"conversation", "answer", "delivery", "awaiting_user"})


def surface_for_reading_task(
    task: str,
    *,
    item_count: int = 0,
    shared_dimensions: int = 0,
    already_rendered: bool = False,
) -> str | None:
    """Compile a semantic reading task to one of the six native surfaces.

    This is intentionally deterministic.  The model identifies the reader's
    task; the runtime owns thresholds and component vocabulary.
    """
    if already_rendered:
        return None
    task = str(task or "").strip().lower()
    if task == "compare" and item_count >= 2 and shared_dimensions >= 2:
        return "comparison"
    if task == "sequence" and item_count >= 3:
        return "timeline"
    if task == "scan_numbers" and 3 <= item_count <= 8:
        return "stats"
    if task == "choose" and 2 <= item_count <= 6:
        return "choices"
    if task == "locate" and item_count >= 1:
        return "location"
    if task == "warn" and item_count == 1:
        return "callout"
    return None


_SURFACE_NAMES_DA: dict[str, str] = {
    "comparison": "sammenligning",
    "timeline": "tidslinje",
    "stats": "nøgletal",
    "choices": "valgmuligheder",
    "location": "sted",
    "callout": "advarsel",
}

# Tegne-værktøjerne er en ANDEN familie end de native flader: de lægger noget i
# tråden i stedet for at være en blok i teksten. Porten dækker begge, fordi
# spørgsmålet «skal dette have en form?» kommer før «hvilken form?».
_TOOL_SURFACES: dict[str, tuple[str, str]] = {
    "numbers": (
        "vis_graf",
        "tallene skal aflæses som form — en udvikling eller et forløb, ikke en række",
    ),
    "flow": (
        "render_mermaid",
        "strukturen eller rækkefølgen er pointen — et diagram bærer den bedre end prosa",
    ),
    "interactive": (
        "vis_widget",
        "brugeren skal kunne trykke, sortere eller regne på indholdet",
    ),
}


def decide_surface(
    task: str,
    *,
    item_count: int = 0,
    shared_dimensions: int = 0,
    already_rendered: bool = False,
) -> dict[str, object]:
    """Resolve a reading task to prose, a native surface, or a drawing tool.

    The model names the reader's task; the runtime owns the thresholds.  The
    answer carries its own reason, so the model can correct its assessment
    instead of guessing why it was told no.
    """
    task = str(task or "").strip().lower()

    if already_rendered:
        return _prose_choice(
            "indholdet er allerede vist på en flade",
            "skriv prosa der læser fladen — ikke en kopi af den",
        )
    if not task or task == "none":
        return _prose_choice(
            "læseopgaven kræver ingen flade",
            "skriv prosa; en flade ville være dekoration her",
        )
    if task in _TOOL_SURFACES:
        tool, why = _TOOL_SURFACES[task]
        return {
            "flade": None,
            "vaerktoej": tool,
            "navn": tool,
            "reason": why,
            "next": f"kald {tool} med data — og lad prosaen bære konklusionen",
        }

    surface = surface_for_reading_task(
        task,
        item_count=item_count,
        shared_dimensions=shared_dimensions,
        already_rendered=False,
    )
    if surface is None:
        return _prose_choice(
            _why_prose(task, item_count, shared_dimensions),
            "skriv prosa; en flade ville være dekoration her",
        )
    return {
        "flade": surface,
        "vaerktoej": None,
        "navn": _SURFACE_NAMES_DA.get(surface, surface),
        "reason": _why_surface(surface, item_count, shared_dimensions),
        "next": (
            f"brug en jarvis-ui-blok af typen «{surface}» inline hvor begrebet "
            "behandles, og lad prosaen bære pointen selv"
        ),
    }


def _prose_choice(reason: str, next_step: str) -> dict[str, object]:
    return {
        "flade": None,
        "vaerktoej": None,
        "navn": "prosa",
        "reason": reason,
        "next": next_step,
    }


def _why_surface(surface: str, item_count: int, shared_dimensions: int) -> str:
    if surface == "comparison":
        return f"{item_count} ting på {shared_dimensions} fælles akser — sammenligning kræver aflæsning"
    if surface == "timeline":
        return f"{item_count} led i rækkefølge — rækkefølgen er pointen"
    if surface == "stats":
        return f"{item_count} selvstændige nøgletal — de skal aflæses, ikke læses"
    if surface == "choices":
        return f"{item_count} handlingsbare muligheder — brugeren skal vælge"
    if surface == "location":
        return "et konkret sted er centralt for handlingen"
    if surface == "callout":
        return "præcis én risiko eller afgørelse må ikke overses"
    return "kriterierne er opfyldt"


def _why_prose(task: str, item_count: int, shared_dimensions: int) -> str:
    if task == "compare" and shared_dimensions < 2:
        return f"sammenligning kræver mindst to fælles akser; her er {shared_dimensions}"
    if task == "compare" and item_count < 2:
        return "der er intet at sammenligne"
    if task == "sequence" and item_count < 3:
        return f"en rækkefølge kræver mindst tre led; her er {item_count}"
    if task == "scan_numbers" and not 3 <= item_count <= 8:
        return f"nøgletal kræver tre til otte; her er {item_count}"
    if task == "choose" and not 2 <= item_count <= 6:
        return f"valgmuligheder kræver to til seks; her er {item_count}"
    if task == "warn" and item_count != 1:
        return "en advarsel skal være præcis én ting"
    return "læseopgaven udløser ingen flade"


