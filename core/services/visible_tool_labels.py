"""Human-readable labels and short hints for visible tool activity.

Extracted from visible_runs so progress labels have one responsibility.
"""
from __future__ import annotations

import re


_TOOL_LABELS: dict[str, str] = {
    # Filer
    "read_file": "Læser fil",
    "write_file": "Skriver fil",
    "edit_file": "Redigerer fil",
    "find_files": "Søger filer",
    "search": "Søger i filer",
    "read_archive": "Læser arkiv",
    "publish_file": "Publicerer fil",
    # System
    "bash": "Bash",
    "internal_api": "Kalder intern API",
    "db_query": "Forespørger database",
    "update_setting": "Opdaterer indstilling",
    "compact_context": "Komprimerer kontekst",
    # Web
    "web_fetch": "Henter webside",
    "web_scrape": "Skraber webside",
    "web_search": "Søger på nettet",
    "get_weather": "Henter vejr",
    "geolocation_lookup": "Finder lokation",
    "geocode": "Slår adresse op",
    "reverse_geocode": "Slår koordinater op",
    "route_directions": "Beregner rute",
    "nearby_search": "Søger i nærheden",
    "get_news": "Henter nyheder",
    "get_exchange_rate": "Henter valutakurs",
    "wolfram_query": "Beregner (Wolfram)",
    # Hukommelse og identitet
    "search_memory": "Søger i hukommelse",
    "read_chronicles": "Læser krøniker",
    "read_dreams": "Læser drømme",
    "read_self_state": "Læser selvtilstand",
    "read_model_config": "Læser modelkonfig",
    "read_mood": "Læser stemning",
    "adjust_mood": "Justerer stemning",
    "read_self_docs": "Læser selvdokumentation",
    "read_tool_result": "Læser tool-resultat",
    # Sanser
    "analyze_image": "Analyserer billede",
    "look_around": "Kigger rundt",
    "deep_analyze": "Dybdeanalyserer",
    # Initiativer og opgaver
    "push_initiative": "Registrerer initiativ",
    "list_initiatives": "Lister initiativer",
    "schedule_task": "Planlægger opgave",
    "list_scheduled_tasks": "Lister planlagte opgaver",
    "cancel_task": "Annullerer opgave",
    "edit_task": "Redigerer opgave",
    "queue_followup": "Kø-stiller opfølgning",
    # Kode og forslag
    "propose_source_edit": "Foreslår kodeændring",
    "propose_git_commit": "Foreslår commit",
    "approve_proposal": "Godkender forslag",
    "list_proposals": "Lister forslag",
    # Projekt
    "my_project_status": "Læser projektstatus",
    "my_project_journal_write": "Skriver projektlog",
    "my_project_accept_proposal": "Godkender projektforslag",
    "my_project_declare": "Deklarerer projekt",
    # System/runtime
    "heartbeat_status": "Tjekker heartbeat",
    "trigger_heartbeat_tick": "Trigger heartbeat",
    "daemon_status": "Tjekker daemons",
    "control_daemon": "Styrer daemon",
    "list_signal_surfaces": "Lister signalflader",
    "read_signal_surface": "Læser signalflade",
    "eventbus_recent": "Læser eventbus",
    # Kommunikation
    "search_chat_history": "Søger i chathistorik",
    "discord_status": "Tjekker Discord",
    "send_telegram_message": "Sender Telegram-besked",
    "send_ntfy": "Sender notifikation",
    "notify_user": "Notificerer bruger",
    "send_webchat_message": "Sender webchat-besked",
    "send_discord_dm": "Sender Discord DM",
    "discord_channel": "Tilgår Discord-kanal",
    # Råd og agenter
    "spawn_agent_task": "Spawner agent",
    "send_message_to_agent": "Sender besked til agent",
    "list_agents": "Lister agenter",
    "relay_to_agent": "Videresender til agent",
    "cancel_agent": "Annullerer agent",
    # Smart home
    "home_assistant": "Home Assistant",
    # De hyppigste der MANGLEDE (målt 17/9-2026 på to ugers tool.invoked:
    # operator_bash 16.045, remember_this 336, bash_session_run 237, …).
    # Bjørn: «mange kommandoer har navne remember_this eller operator_bash og
    # det ser sku ikke særlig godt ud». De stod med deres rå funktionsnavn,
    # fordi tabellen kun kendte halvdelen af huset.
    "remember_this": "Husker",
    "archive_brain_entry": "Arkiverer note",
    "bash_session_run": "Bash",
    "grep": "Søger efter",
    "glob": "Finder filer",
    "list_dir": "Ser i mappe",
    "multi_edit": "Redigerer fil",
    "verify_file_contains": "Verificerer fil",
    "explore": "Undersøger",
    "recall": "Genkalder",
    "memory_search": "Søger i hukommelse",
    "memory_upsert_section": "Opdaterer hukommelse",
    "central_query": "Spørger centralen",
    "channel": "Skriver i kanal",
    "load_more_tools": "Henter flere værktøjer",
    "schedule_self_wakeup": "Sætter en påmindelse",
    "mark_wakeup_consumed": "Kvitterer påmindelse",
    "skill_invoke": "Bruger en skill",
    "scout_agent": "Sender en spejder",
    "phone_adb_shell": "Styrer telefonen",
    "list_proposals_diff": "Viser forslags-diff",
}


#: Led der KUN sætter scenen. Hele leddet springes over — resten af det er
#: argumentet til skiftet, ikke en kommando («cd /media/projects/jarvis-v2»).
_SCENE_LED = {"cd", "export", "source", ".", "set", "conda"}
#: Shell-NØGLEORD er syntaks, ikke en kommando. `for … do … done` og
#: `if … then … fi` beskriver en løkke; `echo` er en overskrift. Uden dem stod
#: liveness-linjen «Kører kommando: do if» og «Kører kommando: echo ===»
#: (Bjørn 23/9-2026: «det samme i progress»). Desk's `kommandoEmne` fik
#: listen 23/9 — denne kopi gjorde ikke, så de to sagde hver sit om samme kald.
_NOEGLEORD = {
    "for", "while", "until", "if", "then", "else", "elif", "fi", "do", "done",
    "case", "esac", "in", "echo", "exit", "unset",
}
#: Ord der står FORAN den rigtige kommando i samme led og skal skrælles af.
_PRAEFIKS = {"sudo", "nohup", "env", "time", "timeout", "exec", "command", "xargs"}
#: Omdirigering: `>`, `>>`, `2>`, `<<'PY'`, `&1`.
_OMDIRIGERING = re.compile(r"^(?:\d?[<>]{1,2}|&\d?|<<[-']?\w*)$")


def _bash_hint(cmd: str) -> str:
    """Hvad kommandoen egentlig GØR — ikke dens første ord.

    Målt 17/9-2026: hintet var `cmd.split()[0]`, så liveness-linjen stod på
    «Kører kommando: cd» det meste af en tung kørsel, fordi næsten hver
    kommando begynder med `cd /media/projects/jarvis-v2 && …`. Bjørn: «næsten
    altid på køre kommando: cd indtil kommandoen er kørt».

    Her springes scene-sætningen over — mappeskift, `sudo`, `timeout`,
    miljøvariable — og der vises kommandoen plus dens første rigtige argument.
    """
    s = " ".join((cmd or "").split())
    if not s:
        return ""
    led = [d.strip() for d in re.split(r"&&|\|\||;", s) if d.strip()]
    for d in led:
        ord_ = d.split()
        # Miljøvariable foran (FOO=bar kommando) hører til scenen.
        while ord_ and "=" in ord_[0] and not ord_[0].startswith("-"):
            ord_ = ord_[1:]
        # Resten af et VARIABEL-led er variablens egne argumenter, ikke en
        # kommando: `RUN_ID=manual-$(date -u +%Y%m%dT%H%M%SZ)-$(openssl ...)`
        # gav ellers «Koerer kommando: -u +%Y%m%dT%H%M%SZ)-$(openssl» (Bjoern
        # 23/9-2026). Et led der begynder med `-` er aldrig en kommando.
        if not ord_ or ord_[0].startswith("-"):
            continue
        if ord_[0] in _SCENE_LED or ord_[0] in _NOEGLEORD:
            continue                      # leddet var scene-sætning eller nøgleord
        while ord_ and ord_[0] in _PRAEFIKS:
            ord_ = ord_[1:]
            # `sudo -n x`, `timeout 300 x`: flaget/tallet hører til præfikset.
            while ord_ and (ord_[0].startswith("-") or ord_[0].isdigit()):
                ord_ = ord_[1:]
        if ord_:
            return _hoved_og_genstand(ord_)
    # Kun scene-sætning — så er DET hvad der skete («cd /tmp»).
    if not led:
        return s[:40]
    foerste = led[0].split()
    if foerste and "=" in foerste[0] and not foerste[0].startswith("-"):
        # Ren variabel-tildeling: der findes ingen ydre kommando. Navnet siger
        # mere end «RUN_ID=manual-$(date -u» (Bjoern 23/9-2026).
        return foerste[0].split("=", 1)[0][:40]
    # Ren `echo`: det meningsfulde er det den UDSKRIVER, ikke ordet «echo» og
    # dets dekorations-`===`. Bjoern 23/9-2026: «dette echo === burde vise den
    # faktisk kommando». `echo "=== koerer electron-builder? ==="` giver
    # «koerer electron-builder?»; et banner-løst `echo === status ===` giver
    # «status». Grebet rammer KUN faldbacken — staar der en rigtig kommando
    # efter echo-leddet, fandt løkken den allerede.
    if foerste and foerste[0].split("/")[-1] == "echo":
        budskab = " ".join(foerste[1:]).strip("\"' ")
        renset = budskab.strip("= -_").strip()
        if renset:
            return renset[:40]
    return " ".join(foerste[:2])[:40]


def _hoved_og_genstand(ord_: list[str]) -> str:
    """«grep tool_calls» — kommandoen og det den blev kørt på."""
    hoved = ord_[0].split("/")[-1]        # /opt/conda/…/python → python
    genstand = ""
    for o in ord_[1:]:
        # Flag og omdirigering er ikke kommandoens genstand: `cat > fil.py`
        # handler om filen, ikke om pilen.
        if o.startswith("-") or _OMDIRIGERING.match(o):
            continue
        genstand = o.strip("\"'`")
        if "/" in genstand:
            genstand = genstand.rstrip("/").split("/")[-1] or genstand
        break
    return (f"{hoved} {genstand}".strip() if genstand else hoved)[:40]


#: Felter et emne ledes efter når værktøjet ikke har sin egen gren — første
#: ikke-tomme streng vinder. Det dækker de ~350 værktøjer uden håndskrevet
#: gren, så linjen sjældent står uden et «hvad». Uden den stod «Opdaterer
#: hukommelse» og «Verificerer fil» uden emne (Bjørn 23/9-2026).
_HINT_FELTER = (
    "path", "file_path", "title", "heading", "query", "q", "pattern",
    "url", "command", "name", "action", "text", "agent_id",
)


def _tool_hint(tool_name: str, arguments: dict | None = None) -> str:
    """Emnet for ét kald — HVAD det handler om, uden label foran.

    «git status», «raekkeModel.ts», «Rækkevisningen — tre rettelser». Klienten
    sætter selv værktøjets ikon foran, så labelen («Kører kommando») hører
    ikke her; `_tool_label` limer de to sammen for de flade tekst-kanaler
    (Discord, liveness-linjen).
    """
    if not arguments:
        return ""
    navn = str(tool_name or "")
    name = navn[len("operator_"):] if navn.startswith("operator_") else navn
    a = arguments
    hint = ""
    if name in {"read_file", "write_file", "edit_file", "publish_file",
                "verify_file_contains"}:
        path = str(a.get("path") or a.get("file_path") or "")
        if path:
            hint = path.split("/")[-1]  # basename only
    elif name == "find_files":
        hint = str(a.get("pattern") or a.get("path") or "")[:40]
    elif name in {"search", "web_search", "search_memory", "search_chat_history"}:
        hint = str(a.get("query") or a.get("q") or "")[:40]
    elif name == "web_fetch":
        url = str(a.get("url") or "")
        hint = url.replace("https://", "").replace("http://", "").split("/")[0][:40]
    elif name in {"bash", "bash_session_run"}:
        hint = _bash_hint(str(a.get("command") or ""))
    elif name in {"discord_channel", "send_discord_dm"}:
        hint = str(a.get("channel") or a.get("user") or "")[:30]
    elif name == "home_assistant":
        hint = str(a.get("action") or a.get("entity_id") or "")[:30]
    elif name in {"spawn_agent_task", "send_message_to_agent", "relay_to_agent", "cancel_agent"}:
        hint = str(a.get("agent_id") or a.get("task_id") or "")[:20]
    elif name in {"todo_set", "todo_add"}:
        todos = a.get("todos")
        hint = f"{len(todos)} opgaver" if isinstance(todos, list) else ""
    if not hint:
        for felt in _HINT_FELTER:
            vaerdi = a.get(felt)
            if isinstance(vaerdi, str) and vaerdi.strip():
                renset = vaerdi.strip()
                hint = renset.split("/")[-1] if felt in {"path", "file_path"} else renset
                break
    return hint.strip()[:60]


def _tool_label(tool_name: str, arguments: dict | None = None) -> str:
    navn = str(tool_name or "")
    base = _TOOL_LABELS.get(navn)
    if base is None:
        # `operator_read_file` og `read_file` er samme handling for læseren —
        # og operator-sættet er det MEST brugte (16.045 kald på to uger).
        # Uden dette stod der «operator_bash» i klartekst.
        grund = navn[len("operator_"):] if navn.startswith("operator_") else navn
        base = _TOOL_LABELS.get(grund) or _reserveetiket(grund)
        tool_name = grund or tool_name
    hint = _tool_hint(tool_name, arguments)
    return f"{base}: {hint}" if hint else base


_HANDLINGSORD = {
    "read": "Læser", "write": "Skriver", "edit": "Redigerer",
    "search": "Søger efter", "find": "Finder", "list": "Viser",
    "get": "Henter", "fetch": "Henter", "create": "Opretter",
    "update": "Opdaterer", "delete": "Sletter", "send": "Sender",
    "run": "Kører", "check": "Tjekker", "verify": "Kontrollerer",
    "analyze": "Analyserer", "open": "Åbner", "close": "Lukker",
    "upload": "Uploader", "download": "Henter", "generate": "Genererer",
}
_EMNEORD = {
    "file": "fil", "files": "filer", "memory": "hukommelse",
    "chat": "chat", "history": "historik", "session": "session",
    "jobs": "job", "settings": "indstillinger", "agent": "agent",
    "agents": "agenter", "tool": "værktøj", "tools": "værktøjer",
    "document": "dokument", "documents": "dokumenter",
    "issues": "sager", "issue": "sag", "prs": "pull requests",
    "events": "begivenheder", "event": "begivenhed",
    "in": "i", "background": "baggrunden",
}
_OMRAADER = {
    "github": "GitHub", "gmail": "Gmail", "calendar": "kalender",
    "drive": "Drev", "docs": "dokumenter", "sheets": "regneark",
    "slides": "præsentationer", "pdf": "PDF", "note": "noter",
    "hf": "Hugging Face",
}


def _reserveetiket(name: str) -> str:
    """Læsbar reserve for nye værktøjer; aldrig rå snake_case i UI'et."""
    words = [word for word in re.split(r"[_\s]+", name) if word]
    if not words:
        return "Værktøj"
    action = _HANDLINGSORD.get(words[0].lower())
    if action and len(words) > 1:
        subject = " ".join(_EMNEORD.get(word.lower(), word) for word in words[1:])
        return f"{action} {subject}"
    if len(words) > 1 and words[0].lower() in _OMRAADER:
        action = _HANDLINGSORD.get(words[1].lower())
        if action:
            domain = _OMRAADER[words[0].lower()]
            subject = " ".join(_EMNEORD.get(word.lower(), word) for word in words[2:])
            if subject:
                return f"{action} {subject} i {domain}"
            return f"Søger i {domain}" if words[1].lower() == "search" else f"{action} {domain}"
    return " ".join(words).capitalize()
