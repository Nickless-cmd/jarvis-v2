"""Web/search/system-info tool executors for Jarvis' native lane.

Udskilt fra ``simple_tools.py`` (Boy Scout, 2026-07): search/find_files/bash/
web_fetch/web_scrape/web_search/weather/exchange_rate/news/wolfram/analyze_image/
read_archive + deres hjælpere og default-bash-session-state. INGEN logik-ændring
— kun flyt. ``simple_tools`` re-importerer alle navne (dispatch-dict + tests).

§4 monkeypatch-søm: ``_cached_web_search_fn`` er en designeret test-søm
(``test_web_cache`` patcher den PÅ ``core.tools.simple_tools`` og kalder
``_exec_web_search``). Det patch-bare navn bor derfor i ``simple_tools`` (import
af *_impl); ``_exec_web_search`` slår det op via ``_st()``-facaden, så patchen
rammer.
"""

from __future__ import annotations

import html
import json
import os
import subprocess
import threading as _threading_for_bash
import time
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

import re
from datetime import datetime, timedelta, timezone
from time import monotonic as _monotonic

from core.runtime.config import PROJECT_ROOT
from core.runtime.workspace_paths import shared_dir as _shared_dir
# _exec_bash klipper stor output med clip_head_tail (halen betyder mest for bash).
# Den blev BRUGT (linje ~346/373) men aldrig importeret her → NameError
# "'_clip_head_tail' is not defined" ramte ETHVERT bash-kald med output >16k
# (fx `ls -la /tmp` på ChiefOne) → tool-fejl i kode-lanen. (2026-07-23)
from core.services.text_clip import clip_head_tail as _clip_head_tail, clip_text as _clip_text

logger = __import__("logging").getLogger(__name__)

# Konstanter — spejlet fra simple_tools (samme værdier; caps er rene tal, ingen
# dobbelt-sandhed da de ikke muteres). Holdes lokalt så modulet er selvstændigt.
WORKSPACE_DIR = _shared_dir()
MAX_SEARCH_RESULTS = 60
MAX_SEARCH_LINE_CHARS = 200
MAX_FIND_RESULTS = 100
MAX_BASH_OUTPUT_CHARS = 16000
from core.tools.tool_limits import bash_timeout_s as _bash_timeout_s  # noqa: E402
# Ét sted, konfigurerbart. To kopier af samme tal driver fra hinanden.
MAX_BASH_SECONDS = _bash_timeout_s()
MAX_WEB_FETCH_CHARS = 24000

# Mapper der ALDRIG traverseres af find_files' **-glob (matcher find-subprocess-grenens
# udelukkelser + almindelige tunge build/VCS-mapper). Uden pruning gik glob'en i node_modules
# i minutter (Rådet/streaming-undersøgelse 9. jul).
_FIND_PRUNE_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".claude", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".idea", ".vscode",
    "dist", "build", ".next", ".cache", ".gradle", "target", ".terraform",
})


def _glob_to_regex(pattern: str) -> "re.Pattern[str]":
    """Oversæt et glob-mønster (POSIX-relativt) til en regex med KORREKT sti-semantik:
    ``**`` krydser mappe-grænser, ``*``/``?`` gør ikke. Bruges af find_files' bundne os.walk
    så vi bevarer glob-adfærd uden pathlib.glob's ubundne traversal."""
    i, n = 0, len(pattern)
    out = ["(?s)^"]
    while i < n:
        if pattern[i:i + 3] == "**/":
            out.append("(?:[^/]*/)*"); i += 3
        elif pattern[i:i + 2] == "**":
            out.append(".*"); i += 2
        elif pattern[i] == "*":
            out.append("[^/]*"); i += 1
        elif pattern[i] == "?":
            out.append("[^/]"); i += 1
        else:
            out.append(re.escape(pattern[i])); i += 1
    out.append("$")
    return re.compile("".join(out))


def _st():
    """Lazy accessor til simple_tools (facade-søm for _cached_web_search_fn)."""
    import core.tools.simple_tools as _m
    return _m


def _cached_web_search_fn(*, query: str, max_results: int, fetch_fn: Any) -> dict[str, Any]:
    """Facade → simple_tools._cached_web_search_fn (honorér test-patch-søm)."""
    return _st()._cached_web_search_fn(query=query, max_results=max_results, fetch_fn=fetch_fn)


def _observe_research_result(tool_name: str, result: object) -> None:
    """Best-effort observer; ordinary web calls never depend on research state."""
    try:
        from core.services.research_evidence_collector import observe_web_result
        observe_web_result(tool_name, result)
    except Exception:
        logger.debug("research evidence observer failed", exc_info=True)


def _exec_search(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    search_path = str(args.get("path") or "").strip() or str(PROJECT_ROOT)
    file_glob = str(args.get("glob") or "").strip()
    multiline = bool(args.get("multiline", False))
    case_insensitive = bool(args.get("ignore_case", False))
    if not pattern:
        return {"error": "pattern is required", "status": "error"}

    # `path` maa gerne pege paa en FIL. Foer 6/9-2026 blev den brugt raat som
    # `cwd`, saa et filnavn gav «[Errno 20] Not a directory» — set i en explore-
    # agents transkript, hvor den proevede tre gange i traek og gav op. At soege
    # i én fil er en helt naturlig ting at ville, saa nu bliver mappen til cwd
    # og filnavnet til glob.
    _sti = Path(search_path).expanduser()
    if _sti.is_file():
        if not file_glob:
            file_glob = _sti.name
        search_path = str(_sti.parent)

    # ── EN STI I `glob` GAV STILLE NUL (7/9-2026) ───────────────────────────
    # `--include=` (og rg's `-g`) matcher på FILNAVN-mønster, ikke på sti. En
    # agent skrev det oplagte — glob='core/runtime/provider_router.py' — og fik
    # «[no matches]» på et mønster der findes 20 gange i filen. Ikke en fejl,
    # ikke et tomt resultat man kan lære af: bare tavshed.
    #
    # Indeholder globben en skråstreg og peger på noget der findes, behandler
    # vi den som dét den er: en sti. Så bliver mappen til rod og filnavnet til
    # globben, præcis som når `path` peger på en fil.
    # Målet er "." (hele træet) med mindre globben peger på noget konkret. Vi
    # skifter IKKE rod til filens mappe: så ville træffene komme tilbage som
    # `./provider_router.py:18` uden sti, og stien er netop dét agenten skal
    # citere. I stedet søger vi i filen med rod stadig i projektet, så
    # resultatet lyder `core/runtime/provider_router.py:18`.
    _maal = "."
    if file_glob and "/" in file_glob and "*" not in file_glob:
        _g = Path(file_glob)
        _abs = _g if _g.is_absolute() else Path(search_path) / _g
        if _abs.exists():
            _maal = str(_g) if not _g.is_absolute() else str(_abs)
            file_glob = ""

    # Prefer ripgrep when present — much faster, smarter defaults
    # (.gitignore aware, binary-skip, type-detection). Fall back to grep
    # so the tool still works on machines without rg installed.
    have_rg = subprocess.run(
        ["which", "rg"], capture_output=True, text=True
    ).returncode == 0

    if have_rg:
        # `--with-filename`: uden den udelader både rg og grep filnavnet når
        # målet er ÉN fil — og så står agenten med «18:def …» uden at vide
        # hvilken fil. Stien er halvdelen af et brugbart fund.
        argv = ["rg", "-n", "--with-filename", "--color=never",
                "-m", str(MAX_SEARCH_RESULTS)]
        if file_glob:
            argv += ["-g", file_glob]
        if multiline:
            argv += ["-U", "--multiline-dotall"]
        if case_insensitive:
            argv += ["-i"]
        argv += [pattern, _maal]
    else:
        # `-E` (6/9-2026): grep uden det er BASIC regex, hvor |, (, ), ? og +
        # er LITERALER. rg bruger moderne regex. Uden ripgrep installeret — og
        # containeren har den IKKE — fejlede derfor hvert eneste moenster med
        # alternation stille: «[no matches]», aldrig en fejl. Maalt: agenten
        # soegte efter 'def |class' i attachment_service.py og fik nul.
        # Det er formentlig stoerste enkeltaarsag til at agenternes
        # undersoegelser blev ringe netop dér hvor Jarvis bor.
        argv = [
            "grep", "-rEnH", "--color=never",
            "--exclude-dir=.git", "--exclude-dir=node_modules",
            "--exclude-dir=__pycache__", "--exclude-dir=.claude",
            "--exclude-dir=dist", "--exclude-dir=build",
            "-m", str(MAX_SEARCH_RESULTS),
        ]
        if file_glob:
            argv += [f"--include={file_glob}"]
        if case_insensitive:
            argv += ["-i"]
        argv += [pattern, _maal]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
            cwd=search_path,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out", "status": "error"}

    lines = result.stdout.strip().splitlines()[:MAX_SEARCH_RESULTS]
    bounded = [
        line if len(line) <= MAX_SEARCH_LINE_CHARS else _clip_text(line, limit=MAX_SEARCH_LINE_CHARS)
        for line in lines
    ]
    if bounded:
        return {"text": "\n".join(bounded), "match_count": len(bounded), "status": "ok"}
    # NUL TRÆFFERE SKAL SIGE HVOR DER BLEV LEDT.
    #
    # 4. sep 2026 (Jarvis): «search returnerer [no matches] for strenge der ER i
    # repoet» — det kostede en halv times fejlslutning, fordi han konkluderede
    # at koden ikke fandtes. Jeg kunne ikke genskabe fejlen bagefter: samme
    # mønstre gav træffere på både workstation og container.
    #
    # Så det er sandsynligvis IKKE motoren der fejler — det er at «[no matches]»
    # ikke skelner mellem «findes ikke» og «du ledte et andet sted end du tror».
    # En nul-træffer uden kontekst er en påstand man ikke kan efterprøve. Nu
    # står roden, glob'en og motoren i svaret, så man ser forskellen med det
    # samme i stedet for at drage en konklusion om koden.
    hvor = [f"rod={search_path}"]
    if file_glob:
        hvor.append(f"glob={file_glob}")
    hvor.append("motor=rg" if have_rg else "motor=grep")
    if case_insensitive:
        hvor.append("ignore_case")
    if multiline:
        hvor.append("multiline")
    return {
        "text": f"[no matches] — søgt i {', '.join(hvor)} efter {pattern!r}",
        "match_count": 0,
        "searched_root": search_path,
        "engine": "rg" if have_rg else "grep",
        "status": "ok",
    }


def _exec_find_files(args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "").strip()
    search_path = str(args.get("path") or "").strip() or str(PROJECT_ROOT)
    if not pattern:
        return {"error": "pattern is required", "status": "error"}

    # Recursive **-glob: bounded os.walk (NOT naive pathlib.glob).
    # ROD (Rådet/streaming-undersøgelse 9. jul): den gamle `base.glob(pattern)` havde HVERKEN
    # timeout HELLER dir-pruning — et `**/*x`-mønster på repo-roden gik i node_modules/.git i
    # MINUTTER (målt: 884s live) → run'et så "hængt/cutoff" ud og blev afbrudt. Find-subprocess-
    # grenen nedenfor prunede allerede; denne gren gjorde ikke. Nu: os.walk med in-place pruning
    # af tunge mapper + wall-clock deadline + korrekt **-semantik, så traversal ALTID er bundet.
    if "**" in pattern or "/" in pattern:
        try:
            base = Path(search_path).expanduser().resolve()
            rx = _glob_to_regex(pattern)
            deadline = _monotonic() + MAX_BASH_SECONDS
            found: list[Path] = []
            timed_out = False
            for root, dirs, files in os.walk(base):
                if _monotonic() > deadline:
                    timed_out = True
                    break
                # Prune tunge/irrelevante mapper i traversal (mutér dirs in-place).
                dirs[:] = [d for d in dirs if d not in _FIND_PRUNE_DIRS]
                for fn in files:
                    full = Path(root) / fn
                    rel = os.path.relpath(str(full), str(base)).replace(os.sep, "/")
                    if rx.match(rel):
                        found.append(full)
                if len(found) >= MAX_FIND_RESULTS * 10:
                    break   # rigeligt at sortere fra; undgå at samle ubundet
            matches = sorted(
                found,
                key=lambda p: (p.stat().st_mtime if p.exists() else 0.0),
                reverse=True,
            )
            entries: list[str] = []
            for p in matches[:MAX_FIND_RESULTS]:
                try:
                    entries.append(f"{p} ({os.path.getsize(p)}B)")
                except OSError:
                    entries.append(str(p))
            text = "\n".join(entries) if entries else "[no matches]"
            if timed_out:
                text += f"\n[søgning stoppet efter {MAX_BASH_SECONDS}s — indsnævr pattern/path]"
            return {"text": text, "match_count": len(entries),
                    "timed_out": timed_out, "status": "ok"}
        except Exception as exc:
            return {"error": f"glob failed: {exc}", "status": "error"}

    argv = [
        "find", search_path,
        "-type", "f",
        "-name", pattern,
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
        "-not", "-path", "*/__pycache__/*",
        "-not", "-path", "*/.claude/*",
    ]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Find timed out", "status": "error"}

    paths = result.stdout.strip().splitlines()[:MAX_FIND_RESULTS]
    entries: list[str] = []
    for fp in paths:
        try:
            size = Path(fp).stat().st_size
            entries.append(f"{fp}  ({size} bytes)")
        except OSError:
            entries.append(fp)

    text = "\n".join(entries) if entries else "[no files found]"
    return {"text": text, "file_count": len(entries), "status": "ok"}


# ── Default bash session (for the one-shot `bash` tool) ──────────────
# We keep a single per-process default session id. The bash_session
# daemon is shared across workers (Unix socket singleton), so even if
# one worker's reference goes stale, the daemon keeps the session alive
# while another worker is using it. Stale-session retries are handled
# in _exec_bash via _reset_default_bash_session.
import threading as _threading_for_bash
import time
_DEFAULT_BASH_SESSION_ID: str | None = None
_DEFAULT_BASH_SESSION_LOCK = _threading_for_bash.Lock()


def _get_or_open_default_bash_session() -> str | None:
    global _DEFAULT_BASH_SESSION_ID
    # Importeres HER (6/9-2026). De to `_exec_bash_session_*` blev BRUGT uden
    # nogensinde at vaere importeret — en NameError som kalderen fangede med
    # `except Exception` og loggede paa DEBUG. Resultatet: sid blev None, alt
    # faldt til engangs-subprocessen, og den PERSISTENTE shell har aldrig
    # vaeret i brug herfra. Maalt: `cd /tmp` efterfulgt af `pwd` gav
    # repo-roden, selv om kommentaren i _exec_bash lover det modsatte.
    from core.tools.bash_session import (
        _exec_bash_session_list,
        _open_arbejdssession,
    )
    with _DEFAULT_BASH_SESSION_LOCK:
        sid = _DEFAULT_BASH_SESSION_ID
        if sid:
            # Verify the daemon still knows this session.
            listed = _exec_bash_session_list({})
            if listed.get("status") == "ok":
                alive_ids = {
                    str(s.get("session_id"))
                    for s in (listed.get("sessions") or [])
                    if s.get("alive")
                }
                if sid in alive_ids:
                    return sid
            # Otherwise: fall through and re-open below.
            _DEFAULT_BASH_SESSION_ID = None
        # `_open_arbejdssession`, ikke `_exec_bash_session_open`: den delte
        # shell er ikke en opgave, og daemonen skal maerke den som arbejde.
        result = _open_arbejdssession()
        if result.get("status") == "ok" and result.get("session_id"):
            _DEFAULT_BASH_SESSION_ID = str(result["session_id"])
            return _DEFAULT_BASH_SESSION_ID
        return None


def _reset_default_bash_session() -> None:
    global _DEFAULT_BASH_SESSION_ID
    with _DEFAULT_BASH_SESSION_LOCK:
        _DEFAULT_BASH_SESSION_ID = None


def _exec_bash(args: dict[str, Any]) -> dict[str, Any]:
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}

    # ── Operator-kanal (6/9-2026) ────────────────────────────────────────────
    # Er kanalen aaben, hoerer denne kommando til paa Bjoerns maskine og ikke
    # paa containeren. Owner-only, hardt gatet inde i modulet. Er den lukket,
    # returnerer den None og alt fortsaetter praecis som foer.
    _kanal_note = ""
    try:
        from core.services import operator_channel as _oc
        # Session-noeglen kommer fra `_runtime_session_id` naar den findes: det
        # er PRAECIS det id executoren gav dette kald, saa kanalen og bash'en
        # ikke kan pege paa hvert sit. Maalt 5/10-2026 pegede de paa hvert sit
        # (begge opslags-kilder var doede imports), noeglen blev `_default` for
        # ALLE sessioner, og bash faldt stille tilbage til containeren midt i
        # en tur — uden at sige det.
        _sid = (str(args.get("_runtime_session_id") or "").strip()
                or _oc.current_session_id())
        _owner = _oc.current_is_owner()
        _via = _oc.maybe_reroute_bash(command, args.get("cwd"),
                                      is_owner=_owner, session_id=_sid)
    except Exception:
        # Ukendt kanaltilstand må aldrig betyde "kør samme kommando lokalt".
        # Kommandoen kan være skrevet til workstation og have sideeffekter.
        logger.warning("operator_channel: routing kunne ikke afgøres", exc_info=True)
        return {"status": "error", "error":
                "operator-kanalens tilstand kunne ikke afgøres; bash blev ikke kørt"}

    if _via is not None:
        # K10: DENNE gren er den Bjoerns egne kommandoer faktisk tager
        # (`via: operator-kanal`), og den returnerede foer rapporten
        # laengere nede. Den mest brugte shell-vej var altsaa den mest
        # tavse. Fundet ved at koere en kommando paa produktionen og laese
        # svaret — ikke ved at laese koden.
        from core.services.shell_confinement_report import OPERATOR, vedhaeft
        return vedhaeft(_via, OPERATOR)

    # Kanalen er BEVISELIGT lukket eller for gammel til at genopstaa, så
    # kommandoen hører til her. Noten nedenfor er kosmetisk: den forklarer
    # hvorfor svaret kom fra serveren. Fejler den, kører kommandoen alligevel.
    # (Den lå før inde i fail-closed-blokken, så et DB-hikke blokerede al bash
    # — også når kanalen med sikkerhed var lukket. Bjørn 7/10-2026.)
    try:
        # Kanalen faldt af sig selv og var for gammel til at genopstaa. Saa
        # skal svaret SIGE at denne kommando koerte paa serveren — ellers ser
        # et tomt eller fejlende svar ud som om filen ikke findes, naar den i
        # virkeligheden ligger et andet sted. (Bjørn 5/10-2026.)
        _kanal_note = _oc.kanal_note(_sid)
    except Exception:
        logger.debug("operator_channel: note sprunget over", exc_info=True)
        _kanal_note = ""

    # ── Egress-observation (6/9-2026) ────────────────────────────────────────
    # De eksisterende vaern fanger `curl | bash`. Det her fanger ENHVER udgaaende
    # netvaerks-raekken, uanset om den piper videre. Vi BLOKERER ikke — bash er
    # hans arbejdsredskab og en blokering her ville koste mere end den beskytter.
    # Vi goer det TAELLELIGT, saa et moenster kan ses i Centralen bagefter.
    #
    # Undtagelsen er interne maal: `curl https://api.eksempel.dk` er almindeligt
    # arbejde, `curl http://169.254.169.254/` er noget andet, og dét fortjener en
    # linje i loggen mens det sker.
    try:
        from core.services.egress_guard import (
            classify_egress, internal_targets_in_command,
        )
        _eg = classify_egress(command)
        if _eg.get("egress"):
            _interne = internal_targets_in_command(command)
            try:
                from core.services.central_core import central
                central().observe({
                    "cluster": "security", "nerve": "bash_egress", "kind": "observe",
                    "tool": _eg.get("tool", ""), "internal_targets": len(_interne),
                })
            except Exception:
                pass
            if _interne:
                logger.warning(
                    "bash-egress mod INTERNT maal: %s (%s)",
                    ", ".join(_interne[:3]), _eg.get("reason", ""))
    except Exception:
        pass

    # Execution-cluster 🔒 GENNEM Den Intelligente Central (SECURITY): read-before-write
    # (cp/mv/redirect/tee/sed mod protected-filer) + kommando-klassifikation konsolideret
    # til ÉT traced gate-kald. Rå-signalet bæres tilbage så svar-formerne er uændrede.
    _session_id = (
        args.get("_runtime_session_id")
        or args.get("_session_id")
        or "default"
    )
    from core.services.gate_execution import check_command
    _ec = check_command(command, session_id=str(_session_id))

    # Gate-domme leveres som IN-LOOP observationer med begrundelse + næste skridt
    # (Bjørns gate-princip, 18. aug 2026). Før returnerede "blocked" kun
    # "Command blocked for safety: <cmd>" og SMED _ec.reason væk — så Jarvis vidste
    # AT han blev stoppet, men ikke HVORFOR eller HVAD han skulle gøre i stedet, og
    # kunne derfor ikke rette sig selv. Gaten dræber stadig ikke runden; den giver nu
    # bare brugbar feedback, er synlig for klienten, og skærper tonen ved gentagelse.
    from core.services.gate_execution import gate_observation

    if _ec.classification == "guard_blocked":
        return gate_observation(
            _ec, gate="exec_command_guard", subject=command,
            status="gate_blocked",   # klient-synlig sti (capability-event m. gate_type)
            remedy="Omformulér kommandoen uden det blokerede mønster, eller brug et "
                   "dedikeret værktøj (read_file/edit_file) i stedet for shell.",
        )

    if _ec.classification == "blocked":
        return gate_observation(
            _ec, gate="exec_command", subject=command, status="gate_blocked",
            remedy="Vælg en ikke-destruktiv variant, indsnævr stien, eller spørg Bjørn "
                   "om lov før du prøver igen — gentag ikke den samme kommando.",
        )

    # `_runtime_trust_all` springer GODKENDELSEN over — og kun den (6/9-2026).
    # Blokerede og guard-blokerede kommandoer stoppes stadig ovenfor, foer vi
    # naar hertil. Flaget er samme konvention som operator-force-handlerne i
    # simple_tools.py bruger, og det findes for at autonome runs kan koere den
    # SAMME bash som synlige ture i stedet for en parallel kopi.
    _spring_godkendelse = bool(args.get("_runtime_trust_all"))

    # DESTRUKTIVT springes ALDRIG over af TRUST. Den gamle `_force_bash`
    # tjekkede kun for klassen "blocked" — men `rm -rf /` klassificeres som
    # "destructive", saa den slap igennem og KOERTE i autonome runs.
    #
    # Den sidste saetning i den gamle kommentar her var forkert, og det kostede
    # Bjoern en dag: der stod at en menneskelig godkendelse «kommer gennem
    # resolve_pending_approval med sin egen godkendelse i ryggen — ikke gennem
    # det her flag». Men resolve_pending_approval kalder execute_tool_force →
    # _force_bash → _exec_bash(_runtime_trust_all=True), altsaa PRAECIS dette
    # flag. En godkendt destruktiv kommando ramte derfor gaten igen og fik
    # approval_needed tilbage — i ring. Maalt 7/9: kortet kom, han godkendte,
    # og runnet ventede videre til det timede ud.
    #
    # Ejer-godkendelsen baeres nu i en ContextVar, ikke i argumenterne — for
    # modellen skriver selv argumenterne og kunne ellers sende sin egen
    # godkendelse med. Se core.tools.owner_approval.
    if _ec.classification == "destructive":
        from core.tools.owner_approval import er_ejer_godkendt
        if not er_ejer_godkendt():
            return {
                "status": "approval_needed",
                "message": f"Destructive command requires explicit approval: {command}",
                "command": command,
                "classification": "destructive",
            }
        logger.warning(
            "bash: destruktiv kommando koert paa EJER-godkendelse: %s", command[:160],
        )

    if _ec.classification == "approval" and not _spring_godkendelse:
        return {
            "status": "approval_needed",
            "message": f"This command may modify the system. Please confirm: {command}",
            "command": command,
            "classification": "mutation",
        }

    # Auto-approved (read-only). Route through the bash_session daemon so
    # we get:
    #   • A persistent shared shell (cd, env-vars, virtualenvs persist
    #     across calls) — no more "lost cwd" between bash invocations.
    #   • A 300s default timeout instead of MAX_BASH_SECONDS=15s.
    #   • Auto-recovery if the daemon died (session re-opened on next call).
    # The legacy subprocess path is kept as a fallback if the daemon
    # really cannot be reached.
    try:
        from core.tools.bash_session import _exec_bash_session_run
        sid = _get_or_open_default_bash_session()
    except Exception as exc:
        sid = None
        # WARNING, ikke DEBUG (6/9-2026): en NameError her gjorde HELE den
        # persistente sti doed i det stille — bash virkede jo, bare uden
        # shell-tilstand. En fejl der koster en funktion maa ikke logges paa
        # et niveau ingen laeser.
        logger.warning("bash: kunne ikke aabne persistent session (%s) — "
                       "falder tilbage til engangs-subprocess", exc)

    if sid:
        run_result = _exec_bash_session_run({
            "session_id": sid,
            "command": command,
            "timeout": 120.0,  # bump from 15s — most ops need more
            "_runtime_tool_use_id": args.get("_runtime_tool_use_id"),
        })
        # If the session died between resolve and run (rare but possible),
        # transparently retry with a fresh session once.
        err = str(run_result.get("error") or "")
        if "unknown session_id" in err or "session terminated" in err:
            _reset_default_bash_session()
            try:
                sid2 = _get_or_open_default_bash_session()
            except Exception:
                sid2 = None
            if sid2:
                run_result = _exec_bash_session_run({
                    "session_id": sid2,
                    "command": command,
                    "timeout": 120.0,
                    "_runtime_tool_use_id": args.get("_runtime_tool_use_id"),
                })
        # Normalize bash_session_run shape -> bash shape
        if run_result.get("status") in ("ok", None) and "exit_code" in run_result:
            output = str(run_result.get("output") or "").strip()
            # `text_full` beholder HELE outputtet til tool-result-storen.
            # Foer 6/9-2026 klippede bash sig selv HER, saa den "fulde" gemte
            # udgave ogsaa havde hullet — og `read_tool_result` kunne ikke
            # hente en midte der aldrig blev bevaret. Maalt: 60.932 tegn vaek
            # uden nogen vej tilbage.
            fuld = output
            if len(output) > MAX_BASH_OUTPUT_CHARS:
                output = _clip_head_tail(output, limit=MAX_BASH_OUTPUT_CHARS)
            svar = {
                "text": output or "[no output]",
                "exit_code": run_result.get("exit_code"),
                "status": "ok",
            }
            if _kanal_note:
                svar["kanal"] = {"note": _kanal_note}
            # ØNSKET vs. FAKTISK indespærring, også her (Fase 3, K9).
            #
            # Den VEDVARENDE shell kan ikke indespærres pr. kommando — et
            # fængsel kan ikke lægges om en shell der bliver stående mellem
            # kald. Det er en egenskab ved stien, ikke en fejl.
            #
            # Men det skal SIGES. Uden denne linje ville en tændt sandbox se
            # ud som om den dækkede bash, mens den normale vej gik udenom og
            # kun reserve-stien blev indespærret. Rapporten er hele forskellen
            # mellem «ikke indespærret» og «troede den var det».
            try:
                from core.services.bash_sandbox import is_enabled, kan_koere
                if is_enabled():
                    svar["confinement"] = {
                        "requested": True, "actual": False, "honored": False,
                        # BRUGBAR, ikke «findes» — modellen faar ellers at
                        # vide at bash er indespaerret naar den ikke er.
                        "available": kan_koere()[0], "enabled": True,
                        "reason": ("vedvarende delt shell — kan ikke indespærres "
                                   "pr. kommando; kun engangs-stien kan"),
                    }
            except Exception:
                logger.warning("bash: kunne ikke afgoere indespaerring paa den "
                               "vedvarende sti", exc_info=True)
            if fuld != output:
                svar["text_full"] = fuld
            return svar
        # Daemon-side error — fall through to subprocess fallback so a
        # transient daemon problem doesn't break bash entirely.
        logger.warning("bash: session path errored, falling back to subprocess: %s", err)

    # Fallback: legacy one-shot subprocess.
    #
    # bwrap-indespaerringen (6/9-2026) sidder KUN her, og det er en aegte
    # graense vaerd at kende: den normale vej er en PERSISTENT bash-session,
    # og et fangsel pr. kommando kan ikke laegges om en shell der bliver
    # staaende mellem kald. jarvis-code kan wrappe hver kommando fordi den
    # koerer engangs-kommandoer. Her daekker den engangs-vejen.
    # Slukket som standard; `maybe_wrap` returnerer None og intet aendrer sig.
    # ØNSKET vs. FAKTISK indespærring (Fase 3, K9). Rapporteres ALTID — også
    # når intet blev bedt om — så man bagefter kan vide om kommandoen kørte
    # indespærret. Før stod wrappen i `except Exception: logger.debug(...)`:
    # kunne fængslet ikke lægges på, kørte kommandoen frit, og det eneste spor
    # var en debug-linje ingen læser.
    #
    # Retningen er UÆNDRET fail-open. `bash_sandbox` traf den beslutning med
    # vilje — «en manglende mekanisme må ikke gøre bash ubrugelig» — og den
    # omgøres ikke under en rapporterings-rettelse. `require=True` findes for
    # de kaldere der vil have fail-closed.
    _argv = ["bash", "-c", command]
    _indespaerring: dict[str, object] = {}
    # K9, anden halvdel (Bjoern 10/9-2026): en UOVERVAAGET koersel skal fejle
    # lukket naar indespaerringen er oensket men ikke mulig. Der er ingen til at
    # redde den, saa den skal hellere lade vaere. Bjoerns egen sti er
    # fail-open med vilje — han er der selv til at se hvad der sker.
    #
    # OG kun naar sandkassen faktisk er TAENDT. `enforcement(require=True)`
    # kaster ogsaa paa «ikke taendt» — saa uden dette led ville ALT autonomt
    # bash-arbejde doe hver gang sandkassen var slukket, hvilket er dens
    # normale tilstand. Fanget af en test foer det naaede maskinen.
    # Er der ingen indespaerring oensket, er der intet at fejle lukket paa.
    try:
        from core.services.bash_sandbox import is_enabled as _sbx_taendt
        from core.services.run_autonomy_context import is_autonomous
        _kraev = is_autonomous() and _sbx_taendt()
    except Exception:
        _kraev = False
    try:
        from core.services.bash_sandbox import ConfinementUnavailable, enforcement
        # BRUGERISOLERING (målt 22/10-2026): uden `egen_workspace` blev HELE
        # runtime-hjemmet bundet skrivbart, så en medlems kommando kunne læse og
        # skrive i enhver anden brugers workspace — inklusive ejerens
        # MEMORY.md. Sandkassen beskyttede resten af maskinen og lukkede
        # samtidig den grænse ind som multi-bruger-driften hviler på.
        #
        # EJERENS STI ER UÆNDRET: er brugeren ejeren (eller kan ejeren ikke
        # afgøres), sendes None, og `wrap_bwrap` binder hjemmet som før. En
        # medlem får sin EGEN mappe — og de andres findes ikke i fængslet.
        _egen_ws = None
        try:
            from core.identity.workspace_bootstrap import (
                ensure_default_workspace as _ws_dir,
            )
            from core.identity.workspace_context import (
                current_user_id as _cuid,
                current_workspace_name as _cwn,
            )
            from core.services.security_guard import is_owner as _er_ejer

            _uid = str(_cuid() or "").strip()
            if _uid and not _er_ejer(_uid):
                _egen_ws = str(_ws_dir(name=_cwn() or "default"))
        except Exception:
            # Kan brugeren ikke afgøres, bindes som før. Det er den FORKERTE
            # retning for en sikkerhedsgrænse, men alternativet — at gætte en
            # mappe — giver en tryghed der ikke svarer til virkeligheden.
            _egen_ws = None
        _e = enforcement(command, str(PROJECT_ROOT), require=_kraev,
                         egen_workspace=_egen_ws)
        _indespaerring = _e.as_dict()
        if _e.argv:
            _argv = _e.argv
    except ConfinementUnavailable as _ci:
        logger.warning("bash: AUTONOM koersel naegtet — indespaerring oensket "
                       "men ikke mulig: %s", _ci)
        return {
            "status": "error",
            "error": ("Indespaerring er paakraevet for autonome koersler, men "
                      f"ikke mulig her: {_ci}"),
            "confinement": {"requested": True, "actual": False, "honored": False,
                            "reason": str(_ci)},
        }
    except Exception as _sb_exc:
        # Selve afgørelsen fejlede. Kommandoen kører stadig (fail-open), men
        # det siges højt — en debug-linje er ikke en rapport.
        _indespaerring = {"requested": None, "actual": False, "honored": False,
                          "reason": f"{type(_sb_exc).__name__}: {_sb_exc}"}
        logger.warning("bash_sandbox: kunne ikke afgøre indespærring — "
                       "kommandoen kører frit: %s", _sb_exc)
    from core.runtime.settings import load_settings
    from core.services.tool_execution_trace import emit_current_output, note_executor_timing
    from core.tools.streaming_subprocess import run_streaming

    live_output = bool(load_settings().live_tool_output_enabled)
    result = run_streaming(
        _argv,
        cwd=str(PROJECT_ROOT),
        timeout_s=MAX_BASH_SECONDS,
        on_output=emit_current_output if live_output else None,
    )
    note_executor_timing(str(args.get("_runtime_tool_use_id") or ""), {
        "route": "server_fallback",
        "first_output_ms": result.first_output_ms,
        "process_ms": result.process_ms,
        "had_output": bool(result.stdout or result.stderr),
    })
    if result.timed_out:
        return {"error": f"Command timed out after {MAX_BASH_SECONDS}s", "status": "error"}

    output = result.stdout.strip()
    if result.stderr.strip():
        output += "\n[stderr] " + result.stderr.strip()

    fuld = output
    if len(output) > MAX_BASH_OUTPUT_CHARS:
        output = _clip_head_tail(output, limit=MAX_BASH_OUTPUT_CHARS)

    svar = {
        "text": output or "[no output]",
        "exit_code": result.exit_code,
        "status": "ok",
    }
    if _kanal_note:
        svar["kanal"] = {"note": _kanal_note}
    # Rapporten følger med SVARET og ikke kun loggen: den der læser resultatet
    # skal kunne se om kommandoen kørte indespærret. Kun når der var noget at
    # sige — et uændret «intet ønsket, intet sket» er støj.
    if _indespaerring and (_indespaerring.get("requested")
                           or not _indespaerring.get("honored", True)):
        svar["confinement"] = _indespaerring
    if fuld != output:
        svar["text_full"] = fuld   # se noten paa session-stien ovenfor
    return svar


def _html_to_text(raw: str) -> str:
    """Grov HTML→tekst der BEVARER afsnits-struktur (blok-tags → linjeskift).

    Den gamle version kollapsede AL whitespace til ét mellemrum → én lang mur uden
    linjeskift, ulæselig og umulig at linje-snappe. Her bliver blok-grænser (p/div/
    li/h1-6/br/tr/section/article) til linjeskift, så afsnit overlever og et vindue
    er læsbart. Self-safe.
    """

    try:
        t = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.DOTALL | re.IGNORECASE)
        t = re.sub(r"<!--.*?-->", " ", t, flags=re.DOTALL)
        # blok-grænser → linjeskift (bevar afsnit)
        t = re.sub(r"(?i)<(?:br|/p|/div|/li|/h[1-6]|/tr|/section|/article|/header|/footer|/blockquote)\s*/?>", "\n", t)
        t = re.sub(r"(?i)<(?:p|div|li|h[1-6]|tr|section|article|blockquote)\b[^>]*>", "\n", t)
        t = re.sub(r"<[^>]+>", " ", t)              # resterende tags væk
        t = html.unescape(t)
        # normalisér: kollaps kun INTRA-linje-whitespace; bevar linjeskift; max ét blankt linje
        out: list[str] = []
        blank = False
        for ln in t.split("\n"):
            ln = re.sub(r"[ \t\f\v\r]+", " ", ln).strip()
            if ln:
                out.append(ln)
                blank = False
            elif not blank:
                out.append("")
                blank = True
        return "\n".join(out).strip()
    except Exception:
        # fald tilbage til den gamle grove strip så vi aldrig kaster
        try:
            t = re.sub(r"<[^>]+>", " ", str(raw or ""))
            return re.sub(r"\s+", " ", html.unescape(t)).strip()
        except Exception:
            return ""


def _egress_blokeret(url: str) -> dict[str, Any] | None:
    """Fejl-svaret hvis destinationen er intern, ellers None.

    Fail-OPEN ved en fejl i selve vaernet: et vaern der er i stykker maa ikke
    goere web-hentning umulig. Det er et bevidst valg — den fejlklasse vi
    beskytter mod er en model der peger paa 169.254.169.254, ikke en angriber
    med kodeadgang.
    """
    try:
        from core.services.egress_guard import classify
        v = classify(url)
        if v.get("blocked"):
            return {"status": "error", "error": f"blokeret destination: {v['reason']}",
                    "blocked_by": "egress_guard", "url": url}
    except Exception:
        pass
    return None


# ── Redirect-revalidering + hentnings-cache (6/9-2026) ───────────────────
# To huller i web_fetch. Det foerste er sikkerhed: `urlopen` foelger 302
# SELV, saa en offentlig URL der bestod egress-tjekket kunne stille om til
# 169.254.169.254, og saa var det foerste tjek uden vaerdi. `check_redirect_hop`
# blev bygget 6/9 og aldrig tilsluttet — her er kaldsstedet.
# Det andet er spild: den samme side blev hentet forfra hver gang. En kort
# TTL raekker, for gentagelserne ligger inden for samme tur.
# Cachen ligger i DB'en som `web_scrape`s og `web_search`s — ikke i en
# modul-global (6/9-2026, anden omgang). Grunden er den samme som for
# operator-kanalen: runtime er TO processer, saa en global betyder to
# separate caches der ikke ved af hinanden, og alt gaar tabt ved genstart.
# De to andre web-vaerktoejer laa allerede i `web_cache`-tabellen; det her
# var det eneste sted der stak ud.
#
# NB: den deles bevidst IKKE med `web_scrape`. Scrape har en
# Playwright-fallback naar indholdet er tyndt, og genbrugte den denne rene
# urllib-HTML, ville den springe render-vejen over og blive DAARLIGERE paa
# JS-tunge sider. To vaerktoejer, to behov.
_FETCH_CACHE_TTL_S = 900.0
_MAX_REDIRECTS = 5


def _fetch_cache_get(url: str) -> str | None:
    try:
        from core.runtime.db import _ensure_web_cache_table, connect, web_cache_lookup
        with connect() as conn:
            _ensure_web_cache_table(conn)
            hit = web_cache_lookup(conn=conn, cache_key=f"fetch:{url}")
        return str(hit.get("body")) if hit and hit.get("body") else None
    except Exception:
        return None


def _fetch_cache_put(url: str, raw: str) -> None:
    try:
        from datetime import UTC, datetime, timedelta

        from core.runtime.db import _ensure_web_cache_table, connect, web_cache_store
        with connect() as conn:
            _ensure_web_cache_table(conn)
            web_cache_store(
                conn=conn, cache_key=f"fetch:{url}", query_raw=url,
                query_normalized=url, source_url=url, title="", body=raw,
                ttl_policy="fetch",
                expires_at=(datetime.now(UTC)
                            + timedelta(seconds=_FETCH_CACHE_TTL_S)).isoformat(),
            )
    except Exception:
        logger.debug("web_fetch: kunne ikke gemme i cachen", exc_info=True)


class _RevaliderendeRedirect(urllib_request.HTTPRedirectHandler):
    """Stopper en omdirigering mod et internt maal, hop for hop."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            from core.services.egress_guard import check_redirect_hop
            dom = check_redirect_hop(newurl)
            if not dom.get("safe", True):
                raise urllib_error.URLError(
                    f"omdirigering blokeret: {newurl} ({dom.get('reason')})"
                )
        except urllib_error.URLError:
            raise
        except Exception:
            pass  # fail-open, samme valg som _egress_blokeret
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _hent_side(url: str) -> str:
    """Hent en side med redirect-revalidering og kort cache."""
    truffet = _fetch_cache_get(url)
    if truffet is not None:
        return truffet
    aabner = urllib_request.build_opener(_RevaliderendeRedirect)
    req = urllib_request.Request(
        url, headers={"User-Agent": "Jarvis/2.0 (personal assistant)"},
    )
    try:
        with aabner.open(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        # EXA-FALLBACK (målt 18/10-2026). Vores egen hentning er brugbar i 65 %
        # af tilfældene på de samme 17 sider hvor Exa klarer 94 % — den knækker
        # på nyhedssites med JS/paywall og på Q&A-sites. Når den fejler, spørger
        # vi Exa i stedet for at give op. Fejler begge, kastes den oprindelige
        # fejl videre, så svaret stadig siger hvad der gik galt.
        exa = _hent_side_via_exa(url)
        if exa is not None:
            _fetch_cache_put(url, exa)
            return exa
        raise exc
    _fetch_cache_put(url, raw)
    return raw


def _hent_side_via_exa(url: str) -> str | None:
    """Hent en side gennem Exas MCP-server. ``None`` hvis den ikke kan."""
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "web_fetch_exa", "arguments": {"urls": [url]}},
    }
    req = urllib_request.Request(
        "https://mcp.exa.ai/mcp",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
    )
    try:
        with urllib_request.urlopen(req, timeout=25) as response:
            raw = response.read().decode("utf-8", "replace")
    except (urllib_error.URLError, urllib_error.HTTPError, OSError):
        return None  # fallback fejlede — den oprindelige fejl er den ærlige
    tekst = ""
    for linje in raw.splitlines():
        if linje.startswith("data:"):
            try:
                data = json.loads(linje[5:].strip())
            except json.JSONDecodeError:  # ikke-JSON i streamen — spring over
                continue
            for blok in (data.get("result") or {}).get("content") or []:
                if isinstance(blok, dict) and blok.get("type") == "text":
                    tekst += str(blok.get("text") or "")
    return tekst or None


def _exec_web_fetch(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}

    # Paginering: head-først vindue fra `offset`. Web-prosa har indholdet i MIDTEN —
    # den gamle clip_head_tail (bygget til bash-output hvor HALEN betyder mest) smed
    # brødteksten væk og gav intro+footer. Nu returneres et sammenhængende vindue og
    # metadata (has_more/next_offset) så modellen kan side-blade til resten.
    try:
        offset = max(int(args.get("offset") or 0), 0)
    except (TypeError, ValueError):
        offset = 0

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # SSRF-vaern. Runtimen havde INGEN destinations-validering foer 5/9-2026:
    # en hentning kunne pege paa cloud-metadata, pfSense eller Jarvis' eget API.
    # Vaernet er porteret fra jarvis-code, som havde det.
    _eg = _egress_blokeret(url)
    if _eg:
        return _eg

    try:
        raw = _hent_side(url)
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Fetch failed: {exc}", "status": "error"}

    text = _html_to_text(raw)
    total = len(text)

    if offset >= total and total > 0:
        result = {"text": f"[offset {offset} er forbi sidens slut (total {total} tegn)]",
                "url": url, "offset": offset, "returned": 0, "total_chars": total,
                "has_more": False, "next_offset": None, "chars": 0, "status": "ok"}
        _observe_research_result("web_fetch", result)
        return result

    window = text[offset: offset + MAX_WEB_FETCH_CHARS]
    returned = len(window)
    end = offset + returned
    has_more = end < total
    next_offset = end if has_more else None

    body = window
    if offset > 0:
        body = f"[fortsat fra tegn {offset} af {total}]\n\n{body}"
    if has_more:
        body = (f"{body}\n\n… [{total - end} tegn tilbage — kald web_fetch igen med "
                f"offset={next_offset} for næste vindue ({offset}-{end} af {total})] …")

    result = {
        "text": body or "[tom side]",
        "url": url,
        "offset": offset,
        "returned": returned,
        "total_chars": total,
        "has_more": has_more,
        "next_offset": next_offset,
        "chars": returned,  # bagudkompat med tidligere felt
        "status": "ok",
    }
    _observe_research_result("web_fetch", result)
    return result


def _exec_web_scrape(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.web_scrape_tool import web_scrape
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    _eg = _egress_blokeret(url if url.startswith(("http://", "https://"))
                           else "https://" + url)
    if _eg:
        return _eg
    mode = str(args.get("mode") or "auto").strip()
    extract = str(args.get("extract") or "").strip()
    include_links = bool(args.get("include_links", False))
    result = web_scrape(url, mode=mode, extract=extract, include_links=include_links)
    if isinstance(result, dict) and result.get("status") == "ok":
        result.setdefault("url", url)
    _observe_research_result("web_scrape", result)
    return result


def _read_api_key(key: str) -> str:
    """Read an API key directly from runtime.json."""
    from core.runtime.config import SETTINGS_FILE
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return str(data.get(key) or "")
    except Exception:
        return ""


def _fetch_tavily(query: str, max_results: int) -> dict[str, Any]:
    """Raw Tavily API call — no caching."""
    api_key = _read_api_key("tavily_api_key")
    if not api_key:
        return {"error": "tavily_api_key not configured in runtime.json", "status": "error"}

    payload = json.dumps({
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
    }).encode()
    req = urllib_request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Search failed: {exc}", "status": "error"}

    lines: list[str] = []
    if data.get("answer"):
        lines.append(f"**Summary:** {data['answer']}\n")
    for i, r in enumerate(data.get("results", []), 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")[:300]
        lines.append(f"{i}. **{title}**\n   {content}\n   {url}")
    text = "\n\n".join(lines) if lines else "[no results]"
    return {
        "text": text,
        "results": [dict(item) for item in data.get("results", []) if isinstance(item, dict)],
        "result_count": len(data.get("results", [])),
        "query": query,
        "status": "ok",
    }


def _fetch_serpapi(query: str, max_results: int) -> dict[str, Any]:
    """Raw SerpAPI (Google SERP) call — no caching.

    Målt 18/10-2026: 0,07-0,22 s på danske queries, og den vandt dansk-specifik
    hvor Tavily gav ukrainske og amerikanske grantsider. Til gengæld tabte den
    dansk-lokal (matchede "åbent" som "åbent hus"). Derfor er den ikke en
    erstatning men en kandidat — se core.services.search_quality.
    """
    api_key = _read_api_key("serpapi_api_key")
    if not api_key:
        return {"error": "serpapi_api_key not configured in runtime.json", "status": "error"}

    params = urllib_parse.urlencode({
        "q": query, "api_key": api_key, "engine": "google",
        "gl": "dk", "hl": "da", "num": str(max_results),
    })
    try:
        with urllib_request.urlopen(
            f"https://serpapi.com/search.json?{params}", timeout=25
        ) as response:
            data = json.loads(response.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:  # netvaerksfejl -> aerlig fejl, ikke tomt svar
        return {"error": f"SerpAPI failed: {exc}", "status": "error"}

    if data.get("error"):
        return {"error": f"SerpAPI: {data['error']}", "status": "error"}

    results = [
        {"title": r.get("title", ""), "url": r.get("link", ""),
         "content": (r.get("snippet") or "")[:300]}
        for r in data.get("organic_results", [])
    ]
    lines: list[str] = []
    svar = data.get("answer_box") or {}
    if svar.get("answer") or svar.get("snippet"):
        lines.append(f"**Summary:** {svar.get('answer') or svar.get('snippet')}\n")
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**\n   {r['content']}\n   {r['url']}")
    return {
        "text": "\n\n".join(lines) if lines else "[no results]",
        "results": results,
        "result_count": len(results),
        "query": query,
        "status": "ok",
    }


def _fetch_exa(query: str, max_results: int) -> dict[str, Any]:
    """Raw Exa MCP search — no caching. Bruges som tredje kandidat.

    Målt 18/10-2026: semantisk søgning, ramte et konkret dansk Innofounder-opslag
    hvor Tavily svarede at oplysningen ikke fandtes. Kræver ingen nøgle på
    gratis-niveauet, men giver kortere indhold end de to andre.
    """
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "web_search_exa",
                   "arguments": {"query": query, "numResults": max_results}},
    }
    # MCP over HTTP kraever et haandtryk FOER tools/call (maalt 18/10-2026:
    # uden initialize svarer serveren fejl, og jeg konkluderede fejlagtigt at
    # Exa var nede). Session-id'et kommer tilbage i en header og skal med paa
    # alle efterfoelgende kald.
    #
    # ⚠️ User-Agent er IKKE valgfri her. Cloudflare foran mcp.exa.ai afviser
    # `Python-urllib/3.x` med error 1010, saa et kald uden UA ligner en doed
    # tjeneste. Maalt 18/10-2026: UA=None -> 403 error 1010, UA='Jarvis/1.0
    # (agent)' -> 200 + session. Samme faelde som ntfy-gatewayen.
    _UA = "Jarvis/1.0 (agent)"
    session_id = ""
    try:
        init_req = urllib_request.Request(
            "https://mcp.exa.ai/mcp",
            data=json.dumps({
                "jsonrpc": "2.0", "id": 0, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "jarvis", "version": "1.0"}},
            }).encode(),
            headers={"Content-Type": "application/json",
                     "User-Agent": _UA,
                     "Accept": "application/json, text/event-stream"},
        )
        with urllib_request.urlopen(init_req, timeout=15) as response:
            session_id = response.headers.get("Mcp-Session-Id") or ""
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:  # netvaerksfejl -> aerlig fejl, ikke tomt svar
        return {"error": f"Exa init failed: {exc}", "status": "error"}

    headers = {"Content-Type": "application/json",
               "User-Agent": _UA,
               "Accept": "application/json, text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib_request.Request(
        "https://mcp.exa.ai/mcp",
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    try:
        with urllib_request.urlopen(req, timeout=25) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib_error.HTTPError as exc:
        # 429 bærer `Retry-After`, og det er den ENESTE kilde til at skelne
        # QPS-loftet (sekunder, nulstilles straks) fra den daglige kvote
        # (timer). Målt 19/10-2026: 3 af 6 parallelle kald → 429, Retry-After 1.
        svar_429: dict[str, Any] = {"error": f"Exa failed: {exc}", "status": "error",
                                    "http_status": exc.code}
        ra = exc.headers.get("Retry-After") if exc.headers else None
        if ra:
            try:
                svar_429["retry_after"] = float(ra)
            except (TypeError, ValueError):
                pass
        return svar_429
    except (urllib_error.URLError, OSError) as exc:  # netvaerksfejl -> aerlig fejl, ikke tomt svar
        return {"error": f"Exa failed: {exc}", "status": "error"}

    # Serveren svarer SSE: "event: message\ndata: {...}"
    data: dict[str, Any] = {}
    for linje in raw.splitlines():
        if linje.startswith("data:"):
            try:
                data = json.loads(linje[5:].strip())
            except json.JSONDecodeError:  # SSE-keepalive/ping-linje, ikke JSON — spring over
                continue
    indhold = (data.get("result") or {}).get("content") or []
    tekst = ""
    for blok in indhold:
        if isinstance(blok, dict) and blok.get("type") == "text":
            tekst += str(blok.get("text") or "")
    if not tekst:
        return {"error": "Exa: tomt svar", "status": "error"}

    # Exa leverer ren markdown med "Title:"/"URL:"-linjer — parse dem til results.
    results: list[dict[str, str]] = []
    for blok in re.split(r"\n(?=Title: )", tekst):
        t = re.search(r"^Title: (.+)$", blok, re.M)
        u = re.search(r"^URL: (.+)$", blok, re.M)
        if t and u:
            results.append({"title": t.group(1).strip(), "url": u.group(1).strip(),
                            "content": blok[:300]})
    return {
        "text": tekst,
        "results": results,
        "result_count": len(results),
        "query": query,
        "status": "ok",
    }


def _fetch_alle_providers(query: str, max_results: int) -> dict[str, Any]:
    """Exa først — de to andre som fallback. IKKE en dommer (målt 18/10-2026).

    HVORFOR IKKE DOMMEREN LÆNGERE
    Den blev bygget og målt mod 10 queries med objektivt facit (top-1
    præcision). Resultatet var negativt:

        Tavily    2/10 = 20 %
        SerpAPI   5/10 = 50 %
        Exa       7/10 = 70 %
        Dommeren  4/10 = 40 %

    Dommeren var altså dårligere end at vælge Exa blindt, og 28.561
    vægtkombinationer kunne ikke løfte den over 4/10. Årsagen er strukturel:
    dens fire led (dansk-andel, støj, dækning, ord-overlap) kan alle beregnes
    uden at læse hvad resultatet siger, mens Exa vinder på semantisk match —
    noget dommeren pr. konstruktion ikke kan se. At tune vægtene videre ville
    være at flytte gætteriet fra en fast rækkefølge til en formel.

    KÆDEN NU
    1. Exa — bedst på top-1 (70 %) og har det rigtige svar i top-6 i 9/10
       tilfælde. Gratis-tier, ingen nøgle.
    2. Fejler Exa (eller giver nul resultater), prøves SerpAPI og Tavily
       parallelt, og den af dem med flest brugbare resultater bruges.
    3. Fejler alle tre, returneres en ærlig fejl — ikke en tom "ok".

    `quality_score` og `kandidater` bæres stadig med i svaret som telemetri,
    så jeg kan se hvad de andre kilder ville have givet. Det er den eneste
    grund til at score_resultater stadig findes.
    """
    from concurrent.futures import ThreadPoolExecutor
    from core.services.search_quality import score_resultater

    def _kør(navn: str, fn: Any) -> dict[str, Any]:
        try:
            svar = fn(query, max_results)
        except Exception as exc:  # én død provider må ikke vælte søgningen
            logger.warning("web_search: provider %s fejlede: %s", navn, exc)
            svar = {"status": "error", "error": str(exc)}
        # Kaldet tælles UANSET udfald: en fejl kan stadig have ramt kvoten.
        # Tavily og SerpAPI læses live fra provideren; dette er kun supplement.
        try:
            from core.services.search_quota import noter_kald

            noter_kald(navn)
        except Exception:  # regnskab må aldrig vælte en søgning
            pass
        # Et 429 kan KALIBRERE grænsen: et langt Retry-After betyder at det
        # daglige forbrugsloft blev ramt, og forbruget er så pr. definition
        # grænsen. Et kort (≤ 60 s) er kun QPS-vinduet og siger intet om kvoten.
        try:
            from core.services.search_quota import noter_429

            if isinstance(svar, dict) and svar.get("http_status") == 429:
                noter_429(navn, svar.get("retry_after"))
        except Exception:  # regnskab må aldrig vælte en søgning
            pass
        return {"provider": navn, "resultat": svar}

    def _brugbar(k: dict[str, Any]) -> bool:
        res = k.get("resultat") or {}
        return res.get("status") != "error" and bool(res.get("results"))

    # 1. Den foretrukne kilde — men kun så længe den har kvote tilbage.
    #
    # KVALITET FØR SPREDNING (målt 18/10-2026). Exa er bedst på top-1 (70 %
    # mod SerpAPIs 50 % og Tavilys 20 %), så den er default. At sprede
    # forbruget jævnt «for at spare kvote» ville bytte et reelt kvalitetstab
    # for en kvote vi ikke er ved at løbe tør for. Skiftet sker derfor først
    # når en kilde NÆRMER sig loftet (80 %) — så udtømmes vi gradvist i
    # stedet for at ramme en væg uden varsel.
    #
    # Alle over loft → prøv den foretrukne alligevel. «Over loft» er ikke
    # «nede», og et blokeret søgekald er værre end et kald der måske afvises.
    from core.services import search_quota as _kvote

    foretrukken, _kvote_status = _kvote.bedste_provider("exa")
    for _navn, _status in _kvote_status.items():
        _kvote.varsle_hvis_over_loft(_status)

    foerste_navn = foretrukken or "exa"
    _kilde_fn = {"exa": _fetch_exa, "serpapi": _fetch_serpapi, "tavily": _fetch_tavily}
    foerste = _kør(foerste_navn, _kilde_fn[foerste_navn])
    kandidater: list[dict[str, Any]] = [foerste]
    valgt = foerste if _brugbar(foerste) else None

    # 2. Fallback: de ØVRIGE kilder, parallelt, kun hvis den første ikke gav noget.
    if valgt is None:
        resten = [(n, f) for n, f in (("serpapi", _fetch_serpapi), ("tavily", _fetch_tavily))
                  if n != foerste_navn]
        with ThreadPoolExecutor(max_workers=max(1, len(resten))) as pool:
            fremtider = {
                pool.submit(_kør, navn, fn): navn
                for navn, fn in resten
            }
            for fremtid in fremtider:
                kandidater.append(fremtid.result(timeout=30))
        brugbare = [k for k in kandidater if _brugbar(k)]
        if brugbare:
            # Flest brugbare resultater vinder — uden dommerens fire led.
            valgt = max(brugbare, key=lambda k: len((k["resultat"] or {}).get("results") or []))

    if valgt is None:
        fejl = [f"{k['provider']}: {(k['resultat'] or {}).get('error', 'ukendt')}"
                for k in kandidater]
        return {"error": "alle søgekilder fejlede — " + "; ".join(fejl),
                "status": "error"}

    svar = dict(valgt["resultat"])
    svar["provider"] = valgt["provider"]
    svar["kandidater"] = {k["provider"]: (k["resultat"] or {}).get("status", "?")
                          for k in kandidater}
    # Telemetri: hvad dommeren ville have scoret den valgte liste. Ikke en vælger.
    try:
        svar["quality_score"] = score_resultater(
            svar.get("results") or [], query=query
        )
    except Exception:  # telemetri må aldrig vælte et gyldigt svar
        svar["quality_score"] = None
    return svar


def _cached_web_search_fn_impl(*, query: str, max_results: int, fetch_fn: Any) -> dict[str, Any]:
    """Wrapper so tests can monkeypatch the cache layer (real impl)."""
    from core.tools.web_cache import cached_web_search

    return cached_web_search(query=query, max_results=max_results, fetch_fn=fetch_fn)


def _exec_web_search(args: dict[str, Any]) -> dict[str, Any]:
    """Web search via Tavily API with result caching."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}
    max_results = min(int(args.get("max_results") or 5), 10)

    result = _cached_web_search_fn(
        query=query, max_results=max_results, fetch_fn=_fetch_alle_providers,
    )
    _observe_research_result("web_search", result)
    return result


def _read_user_location() -> str:
    """Read Location from the live workspace USER.md."""
    try:
        user_md = WORKSPACE_DIR / "USER.md"
        for line in user_md.read_text(encoding="utf-8").splitlines():
            if line.startswith("Location:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "Svendborg, Denmark"


# ── Vejr ─────────────────────────────────────────────────────────────────────
# Udvidet 18/10-2026 (Bjørn: «det tool burde kunne mange flere ting»). Før
# hentede det udelukkende /data/2.5/weather — altså NÆRVÆRET — selv om skemaet
# lovede en «short forecast». Nu dækker det tre gratis-endpoints på samme nøgle:
#
#   /data/2.5/weather       → nu: temp, vind, vindstød, sigtbarhed, solopgang/ned
#   /data/2.5/forecast      → 5 døgn i 3-timers trin med pop og regn/sne-mængde
#   /data/2.5/air_pollution → AQI + partikler (kræver koordinater fra «weather»)
#
# Målt 18/10-2026: /data/3.0/onecall svarer HTTP 401 på denne nøgle (kræver
# separat abonnement). Derfor er prognosen 3-timers — den kaldes ikke
# time-for-time, for det ville være en løgn om opløsningen.

_AQI_LABEL = {1: "god", 2: "rimelig", 3: "moderat", 4: "dårlig", 5: "meget dårlig"}


def _er_dato(tekst: str) -> bool:
    """Sandt hvis ``tekst`` er en gyldig YYYY-MM-DD-dato.

    Bruges til ``date``-parameteren: et vrøvle-input skal ignoreres, ikke kaste.
    """
    try:
        datetime.strptime(str(tekst), "%Y-%m-%d")
        return True
    except (TypeError, ValueError):  # ikke en dato → parameteren ignoreres
        return False


def _owm_get(path: str, params: dict[str, Any], api_key: str, timeout: float = 12.0) -> dict[str, Any]:
    """Ét OpenWeatherMap-kald. Kaster aldrig — fejl returneres som ``_error``."""
    query = "&".join(f"{k}={urllib_request.quote(str(v))}" for k, v in params.items())
    url = f"https://api.openweathermap.org{path}?{query}&appid={api_key}"
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=timeout) as resp:
            return json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"_error": f"{path}: {exc}"}


def _owm_local(epoch: Any, offset_s: int) -> str:
    """Epoch → ISO-lokal tid for STEDET.

    OWM leverer kun et offset i sekunder, ingen zone-ident. Vi bygger derfor en
    fast-offset-zone, så tiderne er stedets og ikke serverens.
    """
    try:
        if not epoch:
            return ""
        return datetime.fromtimestamp(
            float(epoch), timezone(timedelta(seconds=int(offset_s)))
        ).strftime("%Y-%m-%dT%H:%M")
    except (TypeError, ValueError, OSError, OverflowError):  # ugyldigt epoch-tal → tom tid, ikke et kast
        return ""


def _owm_precip_mm(punkt: dict[str, Any]) -> float:
    """Regn + sne i mm. Current bruger ``1h``, forecast bruger ``3h`` — vi summer alt."""
    total = 0.0
    for noegle in ("rain", "snow"):
        blok = punkt.get(noegle)
        if isinstance(blok, dict):
            for vaerdi in blok.values():
                try:
                    total += float(vaerdi or 0.0)
                except (TypeError, ValueError):  # OWM kan sende null/tekst i en nedboersblok
                    continue
    return round(total, 2)


def _owm_daily(punkter: list[dict[str, Any]], offset_s: int, antal: int) -> list[dict[str, Any]]:
    """Gruppér 3-timers-punkter i lokale døgn og opsummer hvert døgn.

    Beskrivelsen vælges fra punktet nærmest kl. 13 — dagens ansigt, ikke et
    tilfældigt nattetime-punkt. Døgnet kan være delvist dækket (prognosen
    starter ved næste 3-timers-grænse), og det er ærligt nok: tallene er
    summen af de punkter der FINDES for dagen.
    """
    dage: dict[str, dict[str, Any]] = {}
    for p in punkter:
        dt_vaerdi = p.get("dt")
        if not dt_vaerdi:
            continue
        try:
            lokal = datetime.fromtimestamp(
                float(dt_vaerdi), timezone(timedelta(seconds=int(offset_s)))
            )
        except (TypeError, ValueError, OSError, OverflowError):  # ét raat punkt maa ikke vaelte hele doegnet
            continue
        noegle = lokal.strftime("%Y-%m-%d")
        main = p.get("main") or {}
        beskrivelse = ((p.get("weather") or [{}])[0] or {}).get("description", "")
        d = dage.setdefault(
            noegle,
            {
                "date": noegle,
                "min_c": None,
                "max_c": None,
                "precip_mm": 0.0,
                "chance_pct": 0,
                "description": "",
                "_naermest_middag": 99,
            },
        )
        for felt, raa, vaelger in (
            ("min_c", main.get("temp_min", main.get("temp")), min),
            ("max_c", main.get("temp_max", main.get("temp")), max),
        ):
            if raa is None:
                continue
            d[felt] = float(raa) if d[felt] is None else vaelger(d[felt], float(raa))
        d["precip_mm"] = round(d["precip_mm"] + _owm_precip_mm(p), 2)
        d["chance_pct"] = max(d["chance_pct"], int(round(float(p.get("pop") or 0) * 100)))
        afstand = abs(lokal.hour - 13)
        if beskrivelse and afstand < d["_naermest_middag"]:
            d["_naermest_middag"] = afstand
            d["description"] = beskrivelse

    resultat: list[dict[str, Any]] = []
    for d in list(dage.values())[:antal]:
        d.pop("_naermest_middag", None)
        for felt in ("min_c", "max_c"):
            if d[felt] is not None:
                d[felt] = round(d[felt], 1)
        resultat.append(d)
    return resultat


def _exec_get_weather(args: dict[str, Any]) -> dict[str, Any]:
    """Vejr via OpenWeatherMap — nu, prognose, døgn og luftkvalitet.

    ``mode``: ``all`` (standard — nu + resten af dagen + døgn + luft),
    ``current`` (kun nu), ``today`` (resten af dagen, fra nu til midnat),
    ``hourly`` (3-timers prognose fremad) eller ``daily`` (kun døgn).

    ``date`` (YYYY-MM-DD) filtrerer til ÉN bestemt dag inden for prognosens
    rækkevidde — fx «hvordan bliver lørdag?». Uden ``date`` er ``all`` dagens
    forløb fra nu til midnat, hvilket er det morgenbriefet læser.
    """
    city = str(args.get("city") or "").strip() or _read_user_location()
    mode = str(args.get("mode") or "all").strip().lower()
    if mode not in ("current", "hourly", "daily", "all", "today"):
        mode = "all"
    # Specifik dag (18/10-2026, Bjørn: «kan toolet hente specifikke dage osse?»).
    # Kun en gyldig YYYY-MM-DD accepteres; alt andet ignoreres frem for at kaste.
    oensket_dag = str(args.get("date") or "").strip()
    if oensket_dag and not _er_dato(oensket_dag):
        oensket_dag = ""
    if oensket_dag:
        mode = "daily" if mode == "all" else mode
    try:
        timer = max(1, min(int(args.get("hours") or 24), 48))
    except (TypeError, ValueError):
        timer = 24
    try:
        dage = max(1, min(int(args.get("days") or 3), 5))
    except (TypeError, ValueError):
        dage = 3
    units = "imperial" if str(args.get("units") or "").lower() == "imperial" else "metric"
    lang = str(args.get("lang") or "da").strip() or "da"

    api_key = _read_api_key("openweathermap_api_key")
    if not api_key:
        return {"error": "openweathermap_api_key not configured in runtime.json", "status": "error"}

    faelles = {"q": city, "units": units, "lang": lang}
    nu_raa = _owm_get("/data/2.5/weather", faelles, api_key)
    if nu_raa.get("_error"):
        return {"error": f"Weather fetch failed: {nu_raa['_error']}", "status": "error"}

    offset = int(nu_raa.get("timezone") or 0)
    main = nu_raa.get("main") or {}
    vind = nu_raa.get("wind") or {}
    sys_blok = nu_raa.get("sys") or {}
    coord = nu_raa.get("coord") or {}
    sol_op = sys_blok.get("sunrise")
    sol_ned = sys_blok.get("sunset")
    sigt = nu_raa.get("visibility")

    nu = {
        "time": _owm_local(nu_raa.get("dt"), offset),
        "description": ((nu_raa.get("weather") or [{}])[0] or {}).get("description", ""),
        "temp_c": main.get("temp"),
        "feels_like_c": main.get("feels_like"),
        "humidity_pct": main.get("humidity"),
        "pressure_hpa": main.get("pressure"),
        "wind_ms": vind.get("speed"),
        "wind_gust_ms": vind.get("gust"),
        "wind_dir_deg": vind.get("deg"),
        "clouds_pct": (nu_raa.get("clouds") or {}).get("all"),
        "visibility_km": round(float(sigt) / 1000.0, 1) if sigt is not None else None,
        "precip_mm": _owm_precip_mm(nu_raa),
        "sunrise": _owm_local(sol_op, offset),
        "sunset": _owm_local(sol_ned, offset),
        "daylight_h": round((float(sol_ned) - float(sol_op)) / 3600.0, 1) if sol_op and sol_ned else None,
    }

    by = str(nu_raa.get("name") or city).strip()
    land = str(sys_blok.get("country") or "").strip()
    svar: dict[str, Any] = {
        "city": f"{by}, {land}" if land else by,
        "mode": mode,
        "units": units,
        "now": nu,
        # Bagudkompatible top-niveau-felter: morgenbriefet og ældre læsere
        # henter stadig «description» og «temp_c» herfra.
        "description": nu["description"],
        "temp_c": nu["temp_c"],
        "feels_like_c": nu["feels_like_c"],
        "humidity_pct": nu["humidity_pct"],
        "wind_ms": nu["wind_ms"],
        "status": "ok",
    }

    if mode in ("hourly", "daily", "all", "today") or oensket_dag:
        prognose = _owm_get("/data/2.5/forecast", faelles, api_key)
        if prognose.get("_error"):
            svar["forecast_error"] = prognose["_error"]
            punkter: list[dict[str, Any]] = []
        else:
            punkter = prognose.get("list") or []
        if punkter:
            nu_dt = float(nu_raa.get("dt") or 0)
            i_dag = _owm_local(nu_dt, offset)[:10]

            def _punkt(p: dict[str, Any]) -> dict[str, Any]:
                return {
                    "time": _owm_local(p.get("dt"), offset),
                    "temp_c": (p.get("main") or {}).get("temp"),
                    "description": ((p.get("weather") or [{}])[0] or {}).get("description", ""),
                    "precip_mm": _owm_precip_mm(p),
                    "chance_pct": int(round(float(p.get("pop") or 0) * 100)),
                    "wind_ms": (p.get("wind") or {}).get("speed"),
                    "wind_gust_ms": (p.get("wind") or {}).get("gust"),
                }

            if oensket_dag:
                # Én bestemt dag: alle punkter på den lokale dato — hele dagen,
                # ikke kun fremad, så man kan se morgenens forløb fra 00:00.
                svar["date"] = oensket_dag
                svar["hourly"] = [
                    _punkt(p) for p in punkter if _owm_local(p.get("dt"), offset)[:10] == oensket_dag
                ]
                svar["daily"] = [
                    d for d in _owm_daily(punkter, offset, 5) if d.get("date") == oensket_dag
                ]
            else:
                if mode == "hourly":
                    graense = nu_dt + timer * 3600.0
                    svar["hourly"] = [
                        _punkt(p) for p in punkter if float(p.get("dt") or 0) <= graense
                    ][: max(1, timer // 3)]
                if mode in ("today", "all"):
                    # Resten af dagen: fra NU til midnat, i stedet for et fast
                    # timetal. Det er det morgenbriefet læser — hele dagen.
                    svar["today"] = [
                        _punkt(p)
                        for p in punkter
                        if _owm_local(p.get("dt"), offset)[:10] == i_dag
                        and float(p.get("dt") or 0) >= nu_dt
                    ]
                    svar["today_date"] = i_dag
                if mode in ("daily", "all"):
                    svar["daily"] = _owm_daily(punkter, offset, dage)

    if mode == "all" and coord.get("lat") is not None and coord.get("lon") is not None:
        luft = _owm_get(
            "/data/2.5/air_pollution",
            {"lat": coord["lat"], "lon": coord["lon"]},
            api_key,
        )
        poster = luft.get("list") or []
        if poster:
            foerste = poster[0]
            aqi = (foerste.get("main") or {}).get("aqi")
            komp = foerste.get("components") or {}
            try:
                aqi_nr = int(aqi) if aqi is not None else None
            except (TypeError, ValueError):
                aqi_nr = None
            svar["air"] = {
                "aqi": aqi_nr,
                "aqi_label": _AQI_LABEL.get(aqi_nr) if aqi_nr else None,
                "pm2_5": komp.get("pm2_5"),
                "pm10": komp.get("pm10"),
                "o3": komp.get("o3"),
            }
        elif luft.get("_error"):
            svar["air_error"] = luft["_error"]

    return svar


def _exec_get_exchange_rate(args: dict[str, Any]) -> dict[str, Any]:
    """Valutakurser via exchangerate.host — med lokal konvertering.

    Udvidet 18/10-2026. Målt på nøglen: ``/live`` virker (173 quotes), men
    ``/historical`` og ``/convert`` svarer **HTTP 429 rate_limit_reached** på
    denne plan. Konverteringen regnes derfor LOKALT ud fra live-raten i stedet
    for at kalde et endpoint der ikke er åbent — og det er præcist nok, fordi
    begge tal kommer fra samme øjebliksbillede.
    """
    base = str(args.get("base") or "DKK").strip().upper() or "DKK"
    targets = str(args.get("targets") or "").strip().upper()
    try:
        beloeb = float(args.get("amount") or 1.0)
    except (TypeError, ValueError):  # "mange" er ikke et beloeb → 1 som neutral
        beloeb = 1.0

    api_key = _read_api_key("exchangerate_api_key")
    if not api_key:
        return {"error": "exchangerate_api_key not configured in runtime.json", "status": "error"}

    url = f"https://api.exchangerate.host/live?access_key={api_key}&source={base}"
    if targets:
        url += f"&currencies={targets}"
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Exchange rate fetch failed: {exc}", "status": "error"}

    if not data.get("success"):
        return {"error": (data.get("error") or {}).get("info", "API error"), "status": "error"}

    quotes = data.get("quotes") or {}
    # Strip source prefix from keys (e.g. "DKKUSD" → "USD")
    rates = {k[len(base):]: v for k, v in quotes.items() if k.startswith(base)}
    return {
        "base": base,
        "rates": rates,
        "amount": beloeb,
        # Konvertering fra den SAMME øjebliksbillede-rat: beløb × kurs.
        "converted": {k: round(beloeb * float(v), 4) for k, v in rates.items()},
        # Omvendt kurs — hvor mange base koster én enhed af valutaen.
        "inverse": {
            k: round(1.0 / float(v), 6) for k, v in rates.items() if v
        },
        "rate_count": len(rates),
        "timestamp": data.get("timestamp"),
        "status": "ok",
    }


def _exec_get_news(args: dict[str, Any]) -> dict[str, Any]:
    """Nyheder via NewsAPI — bred dansk søgning som standard.

    Udvidet 18/10-2026 (Bjørn: «det var nogen af dine aller første tools»). Før
    krævede den en ``query`` og fejlede derfor på «hvad sker der i verden», og
    den kunne hverken datoafgrænse eller sortere. Målt på nøglen 18/10-2026:

      ``/v2/top-headlines?country=dk`` → HTTP 200 med **0 artikler**
      (free-plan-hul; ``country=us`` giver 2 af 35). Vi bruger den derfor ikke.
      ``/v2/everything?q=Danmark&language=da`` → 1.931 træf. Det er vejen.
      ``/v2/everything`` uden ``q`` → HTTP 400 «scope too broad». Derfor en bred
      dansk standard-søgning i stedet for at fejle.
    """
    query = str(args.get("query") or "").strip() or "Danmark"
    language = str(args.get("language") or "da").strip().lower() or "da"
    sort_by = str(args.get("sort_by") or "publishedAt").strip().lower()
    if sort_by not in ("publishedat", "relevancy", "popularity"):
        sort_by = "publishedat"
    sort_by = {"publishedat": "publishedAt"}.get(sort_by, sort_by)
    try:
        max_results = max(1, min(int(args.get("max_results") or 10), 100))
    except (TypeError, ValueError):  # ikke-tal → standard frem for et kast
        max_results = 10

    api_key = _read_api_key("newsapi_api_key")
    if not api_key:
        return {"error": "newsapi_api_key not configured in runtime.json", "status": "error"}

    dele = [
        f"q={urllib_request.quote(query)}",
        f"language={urllib_request.quote(language)}",
        f"pageSize={max_results}",
        f"sortBy={sort_by}",
    ]
    # Datoafgrænsning (18/10-2026): «hvad skete der i går» var umuligt før.
    for felt, noegle in (("from_date", "from"), ("to_date", "to")):
        vaerdi = str(args.get(felt) or "").strip()
        if vaerdi and _er_dato(vaerdi):
            dele.append(f"{noegle}={vaerdi}")
    domaener = str(args.get("domains") or "").strip()
    if domaener:
        dele.append(f"domains={urllib_request.quote(domaener)}")

    url = f"https://newsapi.org/v2/everything?{'&'.join(dele)}&apiKey={api_key}"
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"News fetch failed: {exc}", "status": "error"}

    if data.get("status") == "error":
        return {"error": data.get("message", "NewsAPI error"), "status": "error"}

    artikler = data.get("articles") or []
    linjer: list[str] = []
    for i, a in enumerate(artikler, 1):
        titel = a.get("title") or ""
        kilde = (a.get("source") or {}).get("name") or ""
        udgivet = (a.get("publishedAt") or "")[:16].replace("T", " ")
        beskrivelse = (a.get("description") or "")[:200]
        link = a.get("url") or ""
        linjer.append(f"{i}. **{titel}** ({kilde}, {udgivet})\n   {beskrivelse}\n   {link}")
    tekst = "\n\n".join(linjer) if linjer else "[no articles found]"
    return {
        "text": tekst,
        "articles": [
            {
                "title": a.get("title"),
                "source": (a.get("source") or {}).get("name"),
                "published_at": a.get("publishedAt"),
                "url": a.get("url"),
            }
            for a in artikler
        ],
        "article_count": len(artikler),
        "total_results": data.get("totalResults"),
        "query": query,
        "language": language,
        "sort_by": sort_by,
        "status": "ok",
    }


def _stage_image_preview(image_bytes: bytes | None, source_path: str) -> str:
    """Den sti desk kan hente billedet paa — uden at aabne hvidlisten.

    Var en kopi ved HVERT kald, med `NamedTemporaryFile`. To ting var galt med
    det: den kopierede ogsaa naar originalen allerede maatte vises (alt
    uploadet ligger under `JARVIS_HOME`), og ventefladen — som nu skal bruge
    den samme sti under koerslen — ville have lavet endnu en ved siden af.
    Maalt 28/9-2026 paa CT105: 163 kopier, 120 MB.

    `visnings_sti` svarer paa begge dele: originalen naar den maa vises, ellers
    én kopi med et navn udledt af filen selv, saa to kald om samme billede
    lander paa samme fil.

    `image_bytes` er ikke laengere noedvendig — kilden laeses fra disken — men
    beholdes som skranke: er der intet indhold, er der intet at vise.
    """
    if not image_bytes:
        return ""
    from core.services.vision_preview import visnings_sti
    return visnings_sti(source_path)


def _exec_analyze_image(args: dict[str, Any]) -> dict[str, Any]:
    """Analyze an image using a vision-capable model via Ollama.

    Requires a vision model to be running (e.g. llava, moondream, gemma4).
    Accepts a local file path or a URL.
    """
    import base64

    image_path = str(args.get("image_path") or "").strip()
    image_url = str(args.get("image_url") or "").strip()
    prompt = str(args.get("prompt") or "Describe this image in detail.").strip()
    model = str(args.get("model") or "").strip()

    # Uden en udtrykkelig model kigger vi gennem de øjne der er valgt lige nu —
    # samme regel som resten af syns-værktøjerne. Er der ikke valgt nogen,
    # falder resolve_vision_target tilbage til runtime-config.
    provider = ""
    if not model:
        try:
            from core.services.vision_backend import resolve_vision_target
            provider, model, _source = resolve_vision_target()
        except Exception:
            provider, model = "", ""
    if not model:
        # Sidste udvej: find en synskyndig model blandt dem Ollama har kørende.
        try:
            with urllib_request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as resp:
                tags = json.loads(resp.read())
            names = [m["name"] for m in tags.get("models", [])]
            vision_keywords = ("llava", "moondream", "bakllava", "gemma4", "minicpm", "vision")
            model = next((n for n in names if any(k in n.lower() for k in vision_keywords)), "")
        except Exception:
            pass
        if not model:
            return {
                "error": (
                    "No vision-capable model found. Pull one with: "
                    "ollama pull llava  or  ollama pull moondream"
                ),
                "status": "error",
            }

    # Load image as base64
    image_b64: str | None = None
    image_bytes: bytes | None = None
    if image_path:
        try:
            image_bytes = Path(image_path).read_bytes()
            image_b64 = base64.b64encode(image_bytes).decode()
        except OSError as exc:
            return {"error": f"Could not read image file: {exc}", "status": "error"}
    elif image_url:
        try:
            req = urllib_request.Request(
                image_url, headers={"User-Agent": "Jarvis/2.0"}
            )
            with urllib_request.urlopen(req, timeout=15) as resp:
                image_b64 = base64.b64encode(resp.read()).decode()
        except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
            return {"error": f"Could not fetch image URL: {exc}", "status": "error"}
    else:
        return {"error": "image_path or image_url is required", "status": "error"}

    # Sidder øjnene i DeepSeek, må billedet ikke sendes til Ollama — den har
    # ikke modellen og svarer 404. Samme fælde som vision_backend faldt i.
    if provider == "deepseek":
        try:
            from core.services.vision_backend import describe
            out = describe(image_b64=image_b64, model=model, prompt=prompt,
                           provider="deepseek")
            preview_path = _stage_image_preview(image_bytes, image_path)
            return {"analysis": out.get("text", ""), "model": model, "status": "ok",
                    **({"preview_path": preview_path} if preview_path else {})}
        except Exception as exc:
            return {"error": f"Vision model call failed: {exc}", "status": "error"}

    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
        "stream": False,
    }).encode()

    req = urllib_request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    # 2026-06-10 (Claude): bumpet 60s → 180s + 1 retry. gemma4:31b-cloud
    # har cold-start latens når den ikke er blevet brugt i et stykke tid
    # — første kald kan tage 30-60s, store billeder forlænger yderligere.
    # Bjørn så live: vision model call failed: timed out, men direkte test
    # 5 min senere virkede på ~5s (modellen blev varm). Retry med længere
    # timeout giver Ollama Cloud chance for at varme op uden at faile hele
    # vision-skill.
    _last_exc: Exception | None = None
    result = None
    for _vision_attempt in range(2):
        try:
            with urllib_request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read())
            break
        except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
            _last_exc = exc
            # Retry once for transient timeout/network issues; cold-start
            # tager typisk 30-60s og næste call kommer på varm cache.
            continue
    if result is None:
        return {
            "error": f"Vision model call failed after 2 attempts: {_last_exc}",
            "status": "error",
        }

    answer = result.get("message", {}).get("content", "").strip()
    if not answer:
        return {"error": "Vision model returned empty response", "status": "error"}
    preview_path = _stage_image_preview(image_bytes, image_path)
    return {"analysis": answer, "model": model, "status": "ok",
            **({"preview_path": preview_path} if preview_path else {})}


def _exec_read_archive(args: dict[str, Any]) -> dict[str, Any]:
    """List or extract a zip / tar / rar archive.

    Security: only allows paths inside ~/.jarvis-v2/ to prevent path traversal.
    """
    archive_path = str(args.get("archive_path") or "").strip()
    if not archive_path:
        return {"error": "archive_path is required", "status": "error"}

    allowed_prefix = str((Path.home() / ".jarvis-v2").resolve())
    resolved = str(Path(archive_path).resolve())
    if not resolved.startswith(allowed_prefix):
        return {
            "error": f"archive_path must be inside ~/.jarvis-v2/ (got: {archive_path})",
            "status": "error",
        }

    path = Path(archive_path)
    if not path.exists():
        return {"error": f"File not found: {archive_path}", "status": "error"}

    extract = bool(args.get("extract", False))
    extract_path_arg = str(args.get("extract_path") or "").strip()
    name_lower = path.name.lower()

    try:
        if name_lower.endswith(".zip"):
            import zipfile as _zipfile
            with _zipfile.ZipFile(path) as zf:
                file_list = zf.namelist()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    zf.extractall(dest)
        elif any(name_lower.endswith(ext) for ext in (".tar.gz", ".tgz", ".tar.bz2", ".tar")):
            import tarfile as _tarfile
            with _tarfile.open(path) as tf:
                file_list = tf.getnames()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    tf.extractall(dest)
        elif name_lower.endswith(".rar"):
            try:
                import rarfile as _rarfile
            except ImportError:
                return {
                    "error": "rarfile package not installed. Run: pip install rarfile",
                    "status": "error",
                }
            with _rarfile.RarFile(path) as rf:
                file_list = rf.namelist()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    rf.extractall(dest)
        else:
            return {
                "error": f"Unsupported archive format: {path.suffix}. Supported: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .rar",
                "status": "error",
            }
    except Exception as exc:
        return {"error": f"Archive operation failed: {exc}", "status": "error"}

    result: dict[str, Any] = {"file_list": file_list, "count": len(file_list), "status": "ok"}
    if extract:
        result["extracted_to"] = str(dest)
    return result


def _exec_wolfram_query(args: dict[str, Any]) -> dict[str, Any]:
    """Wolfram Alpha — kort svar eller de fulde pods.

    Udvidet 18/10-2026. Før brugte den kun Short Answers (``/v1/result``), som
    giver ÉT ord og intet mere — «Danmarks befolkning» blev til et tal uden
    kilde eller enhed. ``/v2/query`` med ``output=json&format=plaintext`` virker
    på samme app_id (målt 18/10) og giver de rigtige sektioner, derfor
    ``mode='pods'``. Short answers er stadig standard: hurtigere og billigere.
    """
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}
    mode = str(args.get("mode") or "short").strip().lower()
    if mode not in ("short", "pods"):
        mode = "short"

    app_id = _read_api_key("wolframalpha_app_id")
    if not app_id:
        return {"error": "wolframalpha_app_id not configured in runtime.json", "status": "error"}

    if mode == "pods":
        url = (
            "https://api.wolframalpha.com/v2/query"
            f"?appid={app_id}&input={urllib_request.quote(query)}"
            "&format=plaintext&output=json"
        )
        try:
            with urllib_request.urlopen(urllib_request.Request(url), timeout=25) as resp:
                data = json.loads(resp.read())
        except urllib_error.HTTPError as exc:  # 4xx/5xx fra Wolfram → fejl til kalderen
            return {"error": f"Wolfram Alpha error: {exc}", "status": "error"}
        except (urllib_error.URLError, OSError, json.JSONDecodeError) as exc:  # netvaerk/uformeligt JSON → fejl til kalderen
            return {"error": f"Wolfram Alpha fetch failed: {exc}", "status": "error"}

        svar_blok = data.get("queryresult") or {}
        if not svar_blok.get("success"):
            # Wolfram svarer 200 med success=false når den ikke forstår input.
            fejl = ((svar_blok.get("error") or {}).get("msg")) or "could not interpret this query"
            return {"error": str(fejl), "query": query, "status": "error"}

        pods: list[dict[str, Any]] = []
        for pod in svar_blok.get("pods") or []:
            underdele = [
                sub.get("plaintext")
                for sub in (pod.get("subpods") or [])
                if sub.get("plaintext")
            ]
            if underdele:
                pods.append({"title": pod.get("title") or "", "lines": underdele})
        tekst = "\n\n".join(
            f"**{p['title']}**\n" + "\n".join(p["lines"]) for p in pods
        )
        return {
            "mode": "pods",
            "query": query,
            "pods": pods,
            "text": tekst or "[no plaintext pods]",
            "pod_count": len(pods),
            "status": "ok",
        }

    url = (
        f"https://api.wolframalpha.com/v1/result"
        f"?appid={app_id}&i={urllib_request.quote(query)}"
    )
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=15) as resp:
            answer = resp.read().decode("utf-8", errors="replace").strip()
    except urllib_error.HTTPError as exc:
        if exc.code == 501:
            return {"error": "Wolfram Alpha could not interpret this query", "status": "error"}
        return {"error": f"Wolfram Alpha error: {exc}", "status": "error"}
    except (urllib_error.URLError, OSError) as exc:
        return {"error": f"Wolfram Alpha fetch failed: {exc}", "status": "error"}

    return {"mode": "short", "answer": answer, "query": query, "status": "ok"}


__all__ = [
    "_cached_web_search_fn",
    "_exec_search",
    "_exec_find_files",
    "_get_or_open_default_bash_session",
    "_reset_default_bash_session",
    "_exec_bash",
    "_exec_web_fetch",
    "_exec_web_scrape",
    "_read_api_key",
    "_fetch_tavily",
    "_cached_web_search_fn_impl",
    "_exec_web_search",
    "_read_user_location",
    "_exec_get_weather",
    "_exec_get_exchange_rate",
    "_exec_get_news",
    "_exec_analyze_image",
    "_exec_read_archive",
    "_exec_wolfram_query",
]
