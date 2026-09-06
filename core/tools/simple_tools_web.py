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
from urllib import request as urllib_request

import re
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

    # Prefer ripgrep when present — much faster, smarter defaults
    # (.gitignore aware, binary-skip, type-detection). Fall back to grep
    # so the tool still works on machines without rg installed.
    have_rg = subprocess.run(
        ["which", "rg"], capture_output=True, text=True
    ).returncode == 0

    if have_rg:
        argv = ["rg", "-n", "--color=never", "-m", str(MAX_SEARCH_RESULTS)]
        if file_glob:
            argv += ["-g", file_glob]
        if multiline:
            argv += ["-U", "--multiline-dotall"]
        if case_insensitive:
            argv += ["-i"]
        argv += [pattern, "."]
    else:
        # `-E` (6/9-2026): grep uden det er BASIC regex, hvor |, (, ), ? og +
        # er LITERALER. rg bruger moderne regex. Uden ripgrep installeret — og
        # containeren har den IKKE — fejlede derfor hvert eneste moenster med
        # alternation stille: «[no matches]», aldrig en fejl. Maalt: agenten
        # soegte efter 'def |class' i attachment_service.py og fik nul.
        # Det er formentlig stoerste enkeltaarsag til at agenternes
        # undersoegelser blev ringe netop dér hvor Jarvis bor.
        argv = [
            "grep", "-rEn", "--color=never",
            "--exclude-dir=.git", "--exclude-dir=node_modules",
            "--exclude-dir=__pycache__", "--exclude-dir=.claude",
            "--exclude-dir=dist", "--exclude-dir=build",
            "-m", str(MAX_SEARCH_RESULTS),
        ]
        if file_glob:
            argv += [f"--include={file_glob}"]
        if case_insensitive:
            argv += ["-i"]
        argv += [pattern, "."]
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
        _exec_bash_session_open,
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
        result = _exec_bash_session_open({})
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
    try:
        from core.services import operator_channel as _oc
        _sid, _owner = _oc.current_session_id(), _oc.current_is_owner()
        _via = _oc.maybe_reroute_bash(command, args.get("cwd"),
                                      is_owner=_owner, session_id=_sid)
        if _via is not None:
            return _via
    except Exception:
        logger.debug("operator_channel: sprunget over", exc_info=True)

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

    # DESTRUKTIVT springes ALDRIG over. Den gamle `_force_bash` tjekkede kun
    # for klassen "blocked" — men `rm -rf /` klassificeres som "destructive",
    # saa den slap igennem og KOERTE i autonome runs. Hullet er aeldre end
    # sammenlaegningen; det lukkes her.
    #
    # Naar Bjoern selv har klikket Godkend paa praecis den kommando, kommer
    # kaldet gennem resolve_pending_approval med sin egen godkendelse i
    # ryggen — ikke gennem det her flag.
    if _ec.classification == "destructive":
        return {
            "status": "approval_needed",
            "message": f"Destructive command requires explicit approval: {command}",
            "command": command,
            "classification": "destructive",
        }

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
    _argv = ["bash", "-c", command]
    try:
        from core.services.bash_sandbox import maybe_wrap
        _spaerret = maybe_wrap(command, str(PROJECT_ROOT))
        if _spaerret:
            _argv = _spaerret
    except Exception:
        logger.debug("bash_sandbox sprunget over", exc_info=True)
    try:
        result = subprocess.run(
            _argv,
            capture_output=True,
            text=True,
            timeout=MAX_BASH_SECONDS,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {MAX_BASH_SECONDS}s", "status": "error"}

    output = result.stdout.strip()
    if result.stderr.strip():
        output += "\n[stderr] " + result.stderr.strip()

    fuld = output
    if len(output) > MAX_BASH_OUTPUT_CHARS:
        output = _clip_head_tail(output, limit=MAX_BASH_OUTPUT_CHARS)

    svar = {
        "text": output or "[no output]",
        "exit_code": result.returncode,
        "status": "ok",
    }
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
    with aabner.open(req, timeout=15) as response:
        raw = response.read().decode("utf-8", errors="replace")
    _fetch_cache_put(url, raw)
    return raw


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
        return {"text": f"[offset {offset} er forbi sidens slut (total {total} tegn)]",
                "url": url, "offset": offset, "returned": 0, "total_chars": total,
                "has_more": False, "next_offset": None, "chars": 0, "status": "ok"}

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

    return {
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
    return web_scrape(url, mode=mode, extract=extract, include_links=include_links)


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
    return {"text": text, "result_count": len(data.get("results", [])), "query": query, "status": "ok"}


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

    return _cached_web_search_fn(query=query, max_results=max_results, fetch_fn=_fetch_tavily)


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


def _exec_get_weather(args: dict[str, Any]) -> dict[str, Any]:
    """Current weather via OpenWeatherMap."""
    city = str(args.get("city") or "").strip() or _read_user_location()

    api_key = _read_api_key("openweathermap_api_key")
    if not api_key:
        return {"error": "openweathermap_api_key not configured in runtime.json", "status": "error"}

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={urllib_request.quote(city)}&appid={api_key}&units=metric&lang=en"
    )
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"Weather fetch failed: {exc}", "status": "error"}

    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})
    name = data.get("name", city)
    country = data.get("sys", {}).get("country", "")
    return {
        "city": f"{name}, {country}",
        "description": weather.get("description", ""),
        "temp_c": main.get("temp"),
        "feels_like_c": main.get("feels_like"),
        "humidity_pct": main.get("humidity"),
        "wind_ms": wind.get("speed"),
        "status": "ok",
    }


def _exec_get_exchange_rate(args: dict[str, Any]) -> dict[str, Any]:
    """Currency exchange rates via exchangerate.host."""
    base = str(args.get("base") or "DKK").strip().upper()
    targets = str(args.get("targets") or "").strip().upper()

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
        return {"error": data.get("error", {}).get("info", "API error"), "status": "error"}

    quotes = data.get("quotes", {})
    # Strip source prefix from keys (e.g. "DKKUSD" → "USD")
    rates = {k[len(base):]: v for k, v in quotes.items()}
    return {"base": base, "rates": rates, "status": "ok"}


def _exec_get_news(args: dict[str, Any]) -> dict[str, Any]:
    """Recent news via NewsAPI."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}
    language = str(args.get("language") or "en").strip()
    max_results = min(int(args.get("max_results") or 5), 10)

    api_key = _read_api_key("newsapi_api_key")
    if not api_key:
        return {"error": "newsapi_api_key not configured in runtime.json", "status": "error"}

    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={urllib_request.quote(query)}&language={language}"
        f"&pageSize={max_results}&sortBy=publishedAt&apiKey={api_key}"
    )
    try:
        with urllib_request.urlopen(urllib_request.Request(url), timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError) as exc:
        return {"error": f"News fetch failed: {exc}", "status": "error"}

    articles = data.get("articles", [])
    lines: list[str] = []
    for i, a in enumerate(articles, 1):
        title = a.get("title", "")
        source = a.get("source", {}).get("name", "")
        published = a.get("publishedAt", "")[:10]
        description = (a.get("description") or "")[:200]
        url_a = a.get("url", "")
        lines.append(f"{i}. **{title}** ({source}, {published})\n   {description}\n   {url_a}")
    text = "\n\n".join(lines) if lines else "[no articles found]"
    return {"text": text, "article_count": len(articles), "query": query, "status": "ok"}


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
    if image_path:
        try:
            image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
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
            return {"analysis": out.get("text", ""), "model": model, "status": "ok"}
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
    return {"analysis": answer, "model": model, "status": "ok"}


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
    """Precise answers via Wolfram Alpha Short Answers API."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}

    app_id = _read_api_key("wolframalpha_app_id")
    if not app_id:
        return {"error": "wolframalpha_app_id not configured in runtime.json", "status": "error"}

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

    return {"answer": answer, "query": query, "status": "ok"}


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
