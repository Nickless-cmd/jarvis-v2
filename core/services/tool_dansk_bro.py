"""Danske udtryk for værktøjer der kun beskriver sig selv på engelsk.

## Hvorfor (2/10-2026)

Bjørn spurgte hvorfor skill-gaten aldrig blev brugt, og vejen førte videre til
``tool_discovery_nudge``: den peger på et værktøj uden for hans kasse når hans
besked rører det. Den blev tændt samme dag — og svarede næsten intet på dansk.

Målt 2/10-2026 på 600 af Bjørns egne beskeder: **104 gav et træf (17 %)**. De
der VIRKEDE havde det danske ord i selve værktøjsnavnet — «skill gate» →
``skill_gate``, «restart_self» → ``restart_self``. Resten stod uden modstykke:
``billede`` (37), ``desk`` (28), ``besked`` (14), ``genstart`` (8), ``kode`` (8).

Matcheren (``tool_lexical_match``) rangerer på ord-overlap mellem beskeden og
værktøjets navn+beskrivelse. Værktøjerne beskriver sig på engelsk; Bjørn skriver
dansk. Intet overlap — intet træf. Det er ikke en dårlig matcher; det er to
sprog i hver sin ende af et opslag der kræver samme ord.

## Hvorfor ikke bare oversætte beskrivelserne

Fordi de fleste værktøjer er genererede og overskrives ved næste opdatering. Og
fordi en maskinoversættelse ville gentage hvad beskrivelsen allerede siger —
bare på et andet sprog — uden at kende de ord Bjørn faktisk bruger.

## Samme mønster som ``skill_dansk_tillaeg`` (15/9-2026)

Skills havde præcis denne sygdom: «lav et regneark» gav INTET fordi
``excel-automation`` hedder noget andet. Løsningen dér var en kurateret
udtryks-liste ved siden af filerne. Denne fil er den samme løsning for tools.

## Hvordan den holdes ærlig — to værn

1. **Kun værktøjer der FINDES.** Et navn her uden et registreret værktøj er en
   fejl; testen kræver det, så listen ikke stille peger på noget der er fjernet.
2. **Kun udtryk, aldrig nye betydninger.** Linjerne er hvad Bjørn faktisk ville
   skrive — ikke en oversættelse af den engelske beskrivelse. Ellers gentog vi
   bare det matcheren allerede har.

## Hvordan den virker

Udtrykkene flettes ind i værktøjets korpus-tekst og vejer som NAVNET (dobbelt),
fordi et dansk ord der kun står i ét værktøjs udtryk er et lige så stærkt signal
som et ord i selve navnet. Målt: «hvordan er vejret» giver ``vejret`` i
``get_weather`` og rammer gulvet på ét ord (2 × 0,89 = 1,78 mod gulvet 1,35).

Et udtryk der optræder i mange værktøjer («send», «vis») får automatisk lav IDF
og vejer derfor næsten intet — listen selvregulerer mod støj, og en tvetydig
besked («send en besked») ender med at give intet træf, hvilket er det rigtige
svar.
"""
from __future__ import annotations

#: værktøjsnavn → danske udtryk. Skrevet som Bjørn ville sige det, ikke som en
#: oversættelse af den engelske beskrivelse. Kommasepareret, små bogstaver.
DANSKE_UDTRYK: dict[str, str] = {
    # ── Vejr, nyheder, eksternt ──────────────────────────────────────────
    "get_weather": "vejr, vejret, temperatur, hvordan er vejret, vejrudsigt, hvor koldt er det, prognose, bliver det regn, kommer der regn, hvordan bliver vejret, weekendens vejr, luftkvalitet, resten af dagen, dagens vejr, vejret i dag, hvordan bliver i dag, i morgen, på lørdag, på søndag, næste uge, bliver det godt vejr",
    "get_news": "nyheder, find nyheder, hvad sker der i verden, seneste nyt, dagens nyheder, nyheder i dag, hvad er der sket, seneste nyheder, nyheder om, hvad skriver aviserne",
    "get_exchange_rate": "valutakurs, vekselkurs, hvad koster en dollar, kursen, omregn, konverter, hvor mange dollar, hvor mange euro, hvor meget er, pund, dollar, euro, valuta",
    "wolfram_query": "beregn, regn ud, matematik, hvad er resultatet, omregn enheder, hvor mange meter, hvor mange kilo, videnskabeligt, statistik, præcist tal, befolkningstal, hvor mange indbyggere",
    "madopskrift": "opskrift, opskrifter, madopskrift, madopskrifter, opskrift på, find opskrift, hvad skal vi spise, hvad skal vi have at spise, aftensmad, madlavning, hvad kan jeg lave af, hvad kan jeg lave med, hvad kan jeg lave, ingredienser, madidé, madidéer, vegetarisk opskrift, hvad er i køleskabet, brug mine rester, ret med kylling, ret med kartofler, ret med fisk, suppe opskrift, bag opskrift",
    # ── Kommunikation ────────────────────────────────────────────────────
    "send_discord_dm": "send en besked, skriv til, discord besked, skriv til mig på discord, dm",
    "send_telegram_message": "telegram besked, skriv på telegram, send på telegram",
    "send_webchat_message": "besked i chatten, skriv i chatten, send til chatvinduet",
    "send_mail": "send en mail, skriv en mail, send en email",
    "send_ntfy": "push besked, notifikation til telefonen, giv mig et prik",
    "gmail_send": "svar på mailen, send mailen, besvar mail",
    "gmail_search": "søg i mine mails, find mailen, led efter mail",
    "gmail_list": "vis mine mails, indbakken, nyeste mails, hvad har jeg fået",
    # ── Billeder og vision ───────────────────────────────────────────────
    "hf_vision_analyze": "analyser billedet, hvad er på billedet, se på billedet, beskriv billedet",
    "openrouter_image": "lav et billede, generer et billede, tegn et billede, lav en illustration",
    "pollinations_image": "lav et billede, generer et billede, tegn noget",
    "browser_screenshot": "skærmbillede af siden, tag et billede af siden",
    "operator_screenshot": "skærmbillede, se min skærm, tag et billede af skærmen, hvad står på skærmen",
    "operator_screenshot_window": "billede af vinduet, skærmbillede af vinduet",
    # ── Hukommelse ───────────────────────────────────────────────────────
    "note_add": "huskeseddel, gem en note, skriv en huskeseddel, husk at",
    "note_list": "vis mine noter, mine huskesedler, hvad har jeg noteret",
    "note_search": "søg i mine noter, find noten",
    "note_delete": "slet noten, fjern huskesedlen",
    "memory_graph_query": "hvad ved du om, fortæl mig om, hvad har du på",
    "recall_sensory_memories": "hvad har jeg set, mine sanser, sanseindtryk",
    # Maalt 2/10-2026: uden denne linje ramte «optag en sans fra rummet» intet —
    # «optag» faldt til mic_listen/phone_record_audio (1,55) og «sans» stod uden
    # modstykke. Vaerktoejet var i korpus hele tiden; det manglede kun i broen.
    "record_sensory_memory": "optag en sans, gem et sanseindtryk, skriv i sansernes arkiv",
    "search_chat_history": "søg i vores samtaler, hvad sagde vi om, tidligere snak",
    "search_jarvis_brain": "søg i din hjerne, hvad har du gemt",
    # ── Beslutninger, mål, planer ────────────────────────────────────────
    "decision_create": "lov mig, beslutning, beslut at, forpligt mig",
    "decision_list": "vis mine beslutninger, mine løfter, hvad har jeg lovet",
    "decision_review": "holdt jeg det, gennemgå beslutningen",
    "goal_create": "sæt et mål, nyt mål, jeg vil opnå",
    "goal_list": "vis målene, hvad arbejder jeg mod",
    "goal_update": "opdater målet, fremgang på målet",
    "propose_plan": "lav en plan, foreslå en plan, hvordan griber vi det an",
    "list_plans": "vis planerne, hvilke planer har vi",
    "approve_plan": "godkend planen",
    "revise_plan": "ret planen, opdater planen",
    # Maalt 2/10-2026: uden denne linje tog ``approve_plan`` ALLE «godkend
    # prop-…»-beskeder (10 af 20 nye nudges), fordi «godkend» stod alene i dens
    # udtryk. Bjørn godkender kandidater/props, ikke planer.
    "approve_proposal": "godkend forslaget, godkend kandidaten, godkend prop, godkend forslaget her",
    "list_proposals": "hvilke forslag venter, vis forslagene, hvad venter på godkendelse",
    # ── Kalender ─────────────────────────────────────────────────────────
    "calendar_create_event": "lav en aftale, opret en begivenhed, læg i kalenderen, sæt et møde ind",
    "calendar_list_events": "hvad har jeg i kalenderen, mine aftaler, hvad sker der i morgen",
    "create_event": "lav en aftale, opret begivenhed, sæt i kalenderen",
    "list_events": "mine aftaler, vis kalenderen, kommende begivenheder",
    # ── Skærm og desk ────────────────────────────────────────────────────
    "open_ui_panel": "åbn panelet, vis et panel, vis mig noget i appen",
    "desk_show_pane": "vis sidepanelet, åbn sidepanelet",
    "desk_get_layout": "hvor er vi på skærmen, hvordan ser layoutet ud",
    "screen_control": "sluk skærmen, tænd skærmen, skærmen i standby",
    "jarvis_browser_open": "åbn en hjemmeside, åbn linket, vis mig siden",
    "jarvis_browser_navigate": "gå til siden, naviger til",
    "jarvis_browser_read": "læs siden, hvad står der på siden",
    # ── Filer og kode ────────────────────────────────────────────────────
    "semantic_search_code": "søg i koden, find i kodebasen, hvor i koden",
    "smart_outline": "struktur af filen, oversigt over filen, hvad indeholder filen",
    "find_symbol": "find funktionen, hvor er den defineret, find klassen",
    "dispatch_to_claude_code": "send til claude, lad claude lave det, claude kode",
    "worktree_create": "lav en worktree, opret et arbejdstræ",
    "worktree_list": "vis worktrees, hvilke arbejdstræer",
    "git_blame": "hvem ændrede linjen, hvem skrev det",
    "git_branch": "hvilke branches, vis grene",
    # ── System og drift ──────────────────────────────────────────────────
    "health_check": "tjek om det virker, er systemet sundt, sundhedstjek",
    "verify_service_active": "kører servicen, tjek om servicen er oppe",
    "verify_endpoint_responds": "svarer endpointet, tjek om siden svarer",
    "tail_log": "se loggen, hvad står i loggen, loggen for",
    "daemon_status": "status på daemons, kører daemonerne",
    "control_daemon": "sluk daemonen, tænd daemonen, genstart daemonen",
    "update_setting": "ret en indstilling, skift en setting",
    "operator_list_processes": "hvilke processer kører, vis processerne, hvad kører på maskinen",
    "process_list": "vis processerne, hvad kører",
    "process_stop": "stop processen, dræb processen",
    # ── Lyd og tale ──────────────────────────────────────────────────────
    "mic_listen": "lyt, optag lyd, hvad hører du, lyt efter",
    "hf_transcribe_audio": "skriv lyden ned, transskriber, hvad blev sagt",
    "voice_journal": "tal en besked ind, journal på lyd, optag en stemmenote",
    # ── Skills ───────────────────────────────────────────────────────────
    "skill_list": "vis skills, hvilke skills har du, hvad kan du",
    "skill_search": "find et skill, søg efter et skill",
    "skill_invoke": "brug et skill, tag et skill i brug",
    "skill_suggest": "hvilket skill passer, foreslå et skill",
    # ── Web ──────────────────────────────────────────────────────────────
    "web_scrape": "læs hjemmesiden, hent siden, hvad står der på siden",
    "web_fetch": "hent siden, læs siden",
    # ── Telefon ──────────────────────────────────────────────────────────
    "phone_photo": "tag et billede med telefonen, foto fra mobilen",
    "phone_location": "hvor er jeg, min position, find min telefon",
    "phone_speak": "sig det højt på telefonen, læs op",
    "phone_record_audio": "optag lyd på telefonen",
    "phone_bubble": "vis en boble på telefonen",
    # ── Google Workspace ─────────────────────────────────────────────────
    "docs_read": "læs dokumentet, hvad står der i dokumentet",
    "docs_append": "skriv i dokumentet, tilføj til dokumentet",
    "sheets_write": "skriv i regnearket, indsæt i arket, opdater regnearket",
    "drive_search": "søg i drevet, find filen på drevet",
    # ── Sub-agenter ──────────────────────────────────────────────────────
    "scout_agent": "undersøg, find ud af, research, kig efter",
    "list_agents": "hvilke agenter kører, status på agenterne",
    "dispatch_code_mode_task": "sæt agenter på, kør en kodeopgave",
    # ── Discords og webhooks ─────────────────────────────────────────────
    "discord_status": "virker discord, discord status, er discord oppe",
    "webhook_register": "opret en webhook, registrer et kald",
    "webhook_send": "send til webhooken, kald webhooken",
    # ── Diverse ──────────────────────────────────────────────────────────
    "unified_recall": "hvad husker du om, søg i alt, find alt om",
    "read_mood": "hvordan har du det, dit humør",
    "read_self_state": "din tilstand, hvordan går det dig",
    "curiosity_read_dreams": "hvad drømte du, dine drømme",
    "list_pending_nudges": "hvad venter der, nye beskeder i brønden",
    "analyze_image": "analyser billedet, hvad er på billedet, se på billedet",
    "comfyui_workflow": "kør workflowet, generer med comfyui",
    "set_notification_preferences": "hvor skal beskeder lande, skift notifikationer",
    "schedule_self_wakeup": "væk mig om, husk mig om, mind mig om",
    "list_scheduled_tasks": "hvilke opgaver er planlagt, vis planlagte opgaver",
    # ── Chat-kassen: de 47 huller (18/10-2026) ───────────────────────────
    #
    # Maalt samme dag mod `CHAT_MODE_TOOLS_BASE`: 47 af de 67 vaerktoejer Bjoern
    # faktisk kan ramme naar han skriver i chat havde intet dansk modstykke.
    # Det er praecis den scope han skriver i — saa hullet var ikke teoretisk:
    # «soeg paa nettet» og «kan du huske» gik begge forbi `web_search` og
    # `recall` og landede ingen steder.
    #
    # Raekkefoelgen er ikke tilfaeldig: de to foerste er de mest brugte.
    "web_search": "søg på nettet, søg efter, google det, find ud af på nettet, slå op, hvad siger nettet, søg information om",
    "recall": "kan du huske, hvad ved du om, søg i hukommelsen, husk tilbage, hvad har du gemt om, find i din hukommelse",
    # Hukommelse — skriv og grav
    "remember_this": "husk det her, gem det, skriv det ned, noter det, det skal du huske",
    "search_memory": "søg i hukommelsen, find i mine noter, hvad har du skrevet om",
    "memory_upsert_section": "skriv i hukommelsen, gem et afsnit, opdater memory, tilføj til hukommelsen",
    "read_brain_entry": "læs den post, åbn hjerneposten, vis den gemte post",
    "resurface_old_memory": "hent det gamle frem, mind mig om, hvad skrev jeg om, gå tilbage til",
    "read_chronicles": "læs dine krøniker, din historie, hvad har du skrevet om dig selv",
    "read_dreams": "hvad har du drømt, dine drømme, hvad drømte du om",
    # Indbakken — hvad venter
    "inbox": "hvad venter på mig, min indbakke, hvad blokerer, hvad er der i indbakken",
    "inbox_done": "den er klaret, kvittér, marker som færdig, den er ordnet",
    "inbox_drop": "drop den, afvis posten, den skal ikke, den er ikke relevant",
    # Opgaver (todo)
    "todo_list": "vis mine opgaver, hvad har jeg på listen, mine todos, hvad mangler jeg",
    "todo_add": "tilføj en opgave, ny todo, skriv på listen, sæt på listen",
    "todo_set": "sæt opgavelisten, erstat listen, skriv listen om",
    "todo_update_status": "opgaven er færdig, marker som løst, den er klaret, den er i gang",
    "todo_remove": "fjern opgaven, slet fra listen, den skal ud",
    # Sideopgaver
    "list_side_tasks": "vis sideopgaverne, hvad har jeg af sideopgaver, hvilke sideopgaver",
    "flag_side_task": "noter til senere, gem som sideopgave, skriv det på listen, tag den senere",
    "dismiss_side_task": "drop sideopgaven, afvis sideopgaven, glem sideopgaven",
    "activate_side_task": "sæt sideopgaven i gang, aktivér sideopgaven, tag sideopgaven nu",
    "snooze_side_task": "udskyd sideopgaven, vent med den, tag den senere",
    "wake_side_task": "væk sideopgaven, tag den op nu, den skal køre nu",
    # Kontinuitet og selvstart
    "start_session": "start en session, sæt dig selv i gang, kør det selv, tag den selv",
    "write_handover": "skriv en overdragelse, giv den videre, hvad skal den næste vide",
    "checkpoint": "fortryd det, rul tilbage, gendan filerne, annullér ændringerne, tilbage til før",
    # Placering og ruter
    "geolocation_lookup": "hvor er jeg, hvor er vi henne, min placering, hvor står jeg",
    "geocode": "hvor ligger, find adressen, koordinater for, hvor er henne",
    "reverse_geocode": "hvilken adresse er det, hvor er den her, hvad ligger her",
    "route_directions": "hvordan kommer jeg til, rute til, vej til, hvor langt er der til",
    "nearby_search": "hvad er der i nærheden, find butikker tæt på, i nærheden af, hvad ligger tæt på",
    # Browsere
    "jarvis_browser_click": "klik på, tryk på knappen, klik linket, klik der",
    "jarvis_browser_type": "skriv i feltet, tast ind, udfyld feltet, skriv i søgefeltet",
    "jarvis_browser_tabs": "hvilke faner, vis fanerne, åbne faner, skift fane",
    "jarvis_browser_screenshot": "skærmbillede af siden, tag et billede af siden, se siden",
    "jarvis_browser_close": "luk browseren, luk fanen, luk siden",
    "desk_close_pane": "luk panelet, luk sidepanelet, luk det panel",
    # Filer og vedhæftninger
    "read_attachment": "læs filen jeg sendte, se vedhæftningen, hvad er i filen, åbn det jeg sendte",
    # Agenter og MCP
    "mcp": "mcp server, hvilke mcp, eksterne værktøjer, forbind til serveren",
    "operator_channel": "åbn kanalen, forbind til min maskine, åbn operator-kanalen",
    # App og stemning
    "request_app_action": "skift til kode, åbn kode-tilstand, foreslå et skift, skift mode",
    "set_chat_flow_preference": "foretræk flydende svar, sæt svarmåden, hvordan skal du svare",
    "adjust_mood": "justér humøret, skru op for humøret, ændr din stemning, bliv gladere",
    "read_model_config": "hvilken model, hvilken model kører du på, modelkonfiguration, hvilken model bruger du",
    "send_push_notification": "send en push, giv mig et prik på telefonen, notifikation til mobilen",
}


def dansk_tillaeg(navn: str) -> str:
    """Danske udtryk for et værktøj, eller tom streng.

    Slår op på det RÅ navn — aliaser (``runtime_read_file``) og
    ``operator_``-præfikser dækkes ved at kalde med begge former fra kalderen.
    """
    return DANSKE_UDTRYK.get(str(navn or "").strip(), "")
