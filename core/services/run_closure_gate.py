"""Run-closure gate — fang tomme replies og unstaged changes efter agentic runs.

2026-05-22 (Claude): Bjørn rapporterede et systemisk problem: når Jarvis
laver agentic runs, returnerer han ofte ALDRIG et svar — brugeren ser
"han skriver..." status der aldrig færdiggør. Plus, hvis Jarvis har
redigeret kode under runet, ender ændringerne ofte som unstaged i git
working tree — Bjørn skal selv følge op og bede ham committe.

Diagnose:
1. visible_runs._post_process() kører KUN hvis ``visible_output_text``
   er truthy. Hvis modellen lander efter tool-calls uden text-output,
   sker der ingen post-processing.
2. discord_gateway subscriber buffer-er kun reply hvis ``content``
   ikke er tom; tom assistent-output → ingen buffer → flush ved
   run_completed finder intet → bruger får tavshed.
3. Ingen post-run gate tjekker git working tree for changes der blev
   introduceret under runet men aldrig committet.

Denne service subscriber til ``runtime.autonomous_run_completed`` og:

- Tager et snapshot af ``git status --porcelain`` PRE-run (via
  in-flight registry) og POST-run; hvis der er nye unstaged/untracked
  filer → publish ``runtime.run_left_unstaged_changes`` med fil-liste.
- Hvis runet endte med tom visible-text MEN værktøjer blev kaldt under
  forløbet → publish ``runtime.run_ended_silent`` med summary af
  tool-aktivitet, så Discord/Telegram-subscriber kan sende en
  auto-status til brugeren i stedet for ren tavshed.
- Siden 2026-08-30 (Jarvis): for AUTONOME runs (ingen bruger til stede)
  er gaten hård, ikke kun informativ — den committer selv de rørte paths
  gennem ``git commit`` så pre-commit-hooks (docs-drift, secrets,
  coverage) kører i sessionen. FAIL-CLOSED: auto-commit sker KUN når
  et pre-run snapshot findes OG working tree var rent ved run-start —
  ellers afstår gaten (kan ikke attribuere ændringerne sikkert).
  Lykkes det, publiseres
  ``runtime.run_auto_committed`` med commit-hash. Blokeres den (hook
  fejlede, git-konflikt), rulles staging tilbage, ``run_left_unstaged_changes``
  får ``auto_commit_error``, og Bjørn nudges via nudge-brønden — nat-runs
  har ofte ingen Discord-session, så den gamle Discord-only-sti lod
  ændringer forsvinde i stilhed i dagevis.
  Synlige chats (``autonomous=False``) er uændrede: brugeren er til stede
  og kan selv se/spørge; der committer gaten ikke uden videre.
"""

from __future__ import annotations

import logging
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_listener_thread: threading.Thread | None = None
_listener_running: bool = False


# ── git state snapshot ────────────────────────────────────────────────


def _git_porcelain_status(*, cwd: Path = _REPO_ROOT) -> set[str]:
    """Return the set of path-strings reported by ``git status --porcelain``.

    Each path is prefixed by its status code (e.g. ``" M file.py"``,
    ``"?? newfile.py"``). Returns empty set on any git failure — we
    fail-open so the gate never blocks a run on transient git errors.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode != 0:
            return set()
        return set(line for line in result.stdout.splitlines() if line.strip())
    except Exception:
        return set()


def _git_dirty_content_hashes(*, cwd: Path = _REPO_ROOT) -> dict[str, str]:
    """Return {path: content_hash} for every file currently dirty in working tree.

    2026-05-22 (Claude): originally used `git diff HEAD --raw` to get blob
    hashes, but git reports "00000000" as the destination hash for any
    unstaged modification (because the working tree isn't a committed
    object). That meant the hash never changed between pre and post,
    defeating the modify-modify detection entirely.

    Fixed by collecting the list of dirty paths via porcelain, then
    running `git hash-object <path>` for each to get the would-be-staged
    SHA. That hash actually reflects current content and changes when
    the file is edited. Untracked files are also hashed this way.
    """
    dirty_paths: list[str] = []
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode != 0:
            return {}
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            # porcelain line format: XY<space>path  (X/Y are status codes)
            if len(line) > 3:
                path = line[3:].strip()
                # Renames look like "old -> new" — take new
                if " -> " in path:
                    path = path.split(" -> ", 1)[1].strip()
                if path:
                    dirty_paths.append(path)
    except Exception:
        return {}

    # Filter out directory-only porcelain entries (e.g. untracked
    # directory `?? .codex/`) — git hash-object fails on those with
    # "fatal: Unable to hash <dir>" and aborts the whole batch.
    file_paths: list[str] = []
    for path in dirty_paths:
        full = cwd / path
        try:
            if full.is_file():
                file_paths.append(path)
        except Exception:
            continue

    if not file_paths:
        return {}

    # Hash each file individually so one bad path doesn't abort the batch.
    # (stdin-paths is faster but it returns nothing for the whole batch
    # on the first error.)
    out: dict[str, str] = {}
    for path in file_paths:
        try:
            result = subprocess.run(
                ["git", "hash-object", path],
                capture_output=True, text=True, timeout=3, cwd=cwd,
            )
            if result.returncode == 0:
                h = result.stdout.strip()
                if h:
                    out[path] = h
        except Exception:
            continue
    return out


# ── per-run state cache ────────────────────────────────────────────────
# Pre-run git snapshot, keyed by run_id. We store both porcelain status
# AND a content-hash map so we can detect modify-modify changes within
# a single run window (where porcelain status alone would look identical
# before and after).
_pre_run_git_state: dict[str, tuple[set[str], dict[str, str]]] = {}
_pre_run_git_lock = threading.Lock()


def _record_pre_run_state(run_id: str) -> None:
    if not run_id:
        return
    snapshot = _git_porcelain_status()
    hashes = _git_dirty_content_hashes()
    with _pre_run_git_lock:
        _pre_run_git_state[run_id] = (snapshot, hashes)


def _pop_pre_run_state(run_id: str) -> tuple[set[str], dict[str, str]] | None:
    """Return pre-run snapshot, or ``None`` if no snapshot was recorded.

    Returning ``None`` (not empty set) on missing snapshot is fail-closed:
    an empty set is indistinguishable from "clean baseline", which would
    attribute ALL dirty files to the run. ``None`` forces the caller to
    abstain — no auto-commit without a verified starting point.
    """
    with _pre_run_git_lock:
        return _pre_run_git_state.pop(run_id, None)


# ── tool-call tracking ────────────────────────────────────────────────
# Track which runs have called any tool. We listen for tool events on
# the bus rather than parsing run-internal state.
_run_tool_calls: dict[str, list[str]] = {}
_run_tool_lock = threading.Lock()
# Cap memory: never track more than this many runs' tool histories.
_RUN_TOOL_CACHE_MAX = 256


# Latest in-flight run_id. Tool events from simple_tools.py don't carry
# run_id in their payload — we fall back to this when correlating.
# Concurrent runs would collide here, but in practice we have one active
# visible run at a time per process.
_current_run_id: str = ""
_current_run_lock = threading.Lock()


def _set_current_run(run_id: str) -> None:
    with _current_run_lock:
        global _current_run_id
        _current_run_id = run_id


def _get_current_run() -> str:
    with _current_run_lock:
        return _current_run_id


def _record_tool_call(run_id: str, tool_name: str) -> None:
    # Fall back to the in-flight run if payload didn't include run_id.
    if not run_id:
        run_id = _get_current_run()
    if not run_id or not tool_name:
        return
    with _run_tool_lock:
        if len(_run_tool_calls) >= _RUN_TOOL_CACHE_MAX:
            # Drop the oldest tracked run to bound memory
            oldest = next(iter(_run_tool_calls))
            _run_tool_calls.pop(oldest, None)
        _run_tool_calls.setdefault(run_id, []).append(tool_name)


def _pop_tool_calls(run_id: str) -> list[str]:
    with _run_tool_lock:
        return _run_tool_calls.pop(run_id, [])


# ── post-run handler ──────────────────────────────────────────────────


def _summarize_unstaged(diff: set[str], limit: int = 8) -> dict[str, Any]:
    """Build a structured summary of new unstaged/untracked paths."""
    paths: list[str] = []
    for line in sorted(diff):
        if not line.strip():
            continue
        # status codes are first 2 chars, then space, then path
        path = line[3:].strip() if len(line) > 3 else line.strip()
        paths.append(path)
    return {
        "count": len(paths),
        "paths": paths[:limit],
        "truncated": len(paths) > limit,
    }


# ── auto-commit gate (2026-08-30, Jarvis) ─────────────────────────────
# Efter et AUTONOMT run (ingen bruger til stede) skal efterladte filændringer
# forsegles MENS konteksten er frisk — ikke ligge unstaged i 6 dage. Gaten
# committer de rørte paths gennem git commit, så pre-commit-hooks (docs-drift,
# detect-secrets, test-coverage) kører I sessionen. Hvis en hook blokerer eller
# git fejler, rulles staging tilbage og Bjørn nudges med årsagen.
#
# Hårde sikkerhedsregler:
#   1. KUN paths rørt under runet committes — aldrig `git add -A`.
#   2. ALDRIG hvis der allerede ligger staged ændringer (kan være Bjørns arbejde).
#   3. Artefakt-filer (*.bak, __pycache__, *.pyc, *.lock, ...) committes aldrig
#      — de hører ikke i git, og de efterlades synlige i working tree.
#   4. Fejl → fail-open: unstage + nudge. Gaten må aldrig spise en ændring.

_AUTO_COMMIT_EXCLUDE_SUFFIXES = (".bak", ".orig", ".rej", "~", ".tmp", ".pyc")
_AUTO_COMMIT_EXCLUDE_PARTS = ("__pycache__", ".lock")
# Sidste fejlårsag fra et auto-commit-forsøg — med i unstaged-eventen så
# modtageren ser hvorfor gaten ikke kunne forsegle arbejdet.
_last_auto_commit_error: str = ""


def _is_auto_commit_excluded(path: str) -> bool:
    """True hvis en path er et arbejdsartefakt der aldrig skal committes."""
    lower = path.lower()
    if any(part in lower for part in _AUTO_COMMIT_EXCLUDE_PARTS):
        return True
    return any(lower.endswith(s) for s in _AUTO_COMMIT_EXCLUDE_SUFFIXES)


def _git_staged_paths(*, cwd: Path = _REPO_ROOT) -> set[str] | None:
    """Return paths currently staged in the index.

    Returns ``None`` on git failure — fail-closed so the caller abstains
    rather than proceeding with an unknown staging state (which could
    sweep another process's staged work into an auto-commit).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if result.returncode != 0:
            return None  # fail-closed — unknown state, must not proceed
        return {p for p in result.stdout.splitlines() if p.strip()}
    except Exception:
        return None  # fail-closed


def _try_auto_commit(
    touched_paths: set[str],
    *,
    run_id: str,
    session_id: str,
    focus: str,
) -> str | None:
    """Commit filer rørt under et autonomt run. Return short-hash eller None.

    Kører pre-commit-hooks via git commit. Ved fejl: unstager de tilføjede
    paths (så working tree forbliver ærligt vist) og gemmer årsagen i
    ``_last_auto_commit_error``. Returnerer None ved enhver fejl/afståelse —
    aldrig raise.
    """
    global _last_auto_commit_error
    _last_auto_commit_error = ""

    # Sikkerhedsregel 1: kun paths der ikke er artefakter.
    # NB: vi filtrerer IKKE på is_file() — slettede filer eksisterer ikke
    # på disk, men `git add -- <path>` håndterer dem korrekt (stages sletningen).
    # Renames normaliseres allerede i _git_dirty_content_hashes og porcelain-
    # parsing (tager "new"-siden af "old -> new").
    candidates: list[str] = []
    for path in sorted(touched_paths):
        if not path or _is_auto_commit_excluded(path):
            continue
        candidates.append(path)
    if not candidates:
        _last_auto_commit_error = "kun artefakter — intet at forsegle"
        return None

    # Sikkerhedsregel 2: aldrig oven i eksisterende staged ændringer.
    # Fail-closed: None = ukendt state → afstå (committer intet).
    pre_staged = _git_staged_paths()
    if pre_staged is None:
        _last_auto_commit_error = "afstår — kan ikke verificere staging-state (git-fejl)"
        return None
    if pre_staged:
        _last_auto_commit_error = (
            f"afstår — {len(pre_staged)} allerede staged path(s): "
            + ", ".join(sorted(pre_staged)[:3])
        )
        return None

    subject = f"auto(run): {focus or 'autonom session'} — {len(candidates)} fil(er)"
    body = f"\n\nrun_id: {run_id}\nsession_id: {session_id}\npaths: {len(candidates)}"
    try:
        add = subprocess.run(
            ["git", "add", "--", *candidates],
            capture_output=True, text=True, timeout=15, cwd=_REPO_ROOT,
        )
        if add.returncode != 0:
            _last_auto_commit_error = (add.stderr or add.stdout or "git add fejlede").strip()[:300]
            return None

        commit = subprocess.run(
            ["git", "commit", "-m", subject + body, "--", *candidates],
            capture_output=True, text=True, timeout=120, cwd=_REPO_ROOT,
        )
        if commit.returncode != 0:
            # Hook blokerede eller git fejlede → rul staging tilbage, behold
            # ændringerne synlige, gem årsagen (sidste 400 tegn af stderr).
            _last_auto_commit_error = (
                commit.stderr or commit.stdout or "git commit fejlede"
            ).strip()[-400:]
            try:
                subprocess.run(
                    ["git", "restore", "--staged", "--", *candidates],
                    capture_output=True, text=True, timeout=15, cwd=_REPO_ROOT,
                )
            except Exception:
                pass
            return None

        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=_REPO_ROOT,
        )
        short = (rev.stdout or "?").strip()
        logger.info(
            "run_closure_gate: auto-commit %s → %s (%d paths, run %s)",
            short[:12], subject[:60], len(candidates), run_id[:12],
        )
        return short or "?"
    except Exception as exc:
        _last_auto_commit_error = f"auto-commit exception: {exc}"[:300]
        return None


def _notify_auto_commit_blocked(
    summary: dict[str, Any],
    *,
    run_id: str,
    session_id: str,
) -> None:
    """Nudge Bjørn når gaten ikke kunne forsegle et autonomt runs ændringer.

    Nudge-brønden leverer uanset kanal og venter til han er til stede —
    den gamle Discord-only-sti ramte aldrig nat-runs uden session-binding.
    """
    paths = ", ".join(summary.get("paths") or [])
    error = _last_auto_commit_error or ""
    message = (
        f"🛡️ **run-closure-gate:** autonomt run `{run_id[:12]}` efterlod "
        f"**{summary.get('count', 0)} ucommitted fil(er)** i repoet — "
        f"auto-commit kunne ikke forsegle dem."
    )
    if error:
        message += f"\nÅrsag: `{error[:200]}`"
    if paths:
        message += f"\nFiler: {paths}"
    message += "\nKig på repoet når du har tid — eller sig til, så ordner jeg det."

    nudged = False
    try:
        from core.services.outbound_nudges import push_nudge
        result = push_nudge(
            source="run_closure_gate",
            kind="unstaged_changes",
            message=message,
            importance="high",
        )
        nudged = result.get("status") in ("ok", "queued")
    except Exception:
        nudged = False
    if not nudged:
        # Fallback: notification bridge (urgent — det er en efterladt ændring).
        try:
            from core.services.notification_bridge import send_session_notification
            send_session_notification(message, source="run-closure-gate", urgent=True)
        except Exception:
            logger.warning("run_closure_gate: auto-commit-blocked notice delivery failed", exc_info=True)


def _on_run_completed(payload: dict[str, Any]) -> None:
    """Handle a runtime.autonomous_run_completed event."""
    run_id = str(payload.get("run_id") or "")
    session_id = str(payload.get("session_id") or "")
    if not run_id:
        return
    # Clear in-flight pointer if this is the current run.
    if _get_current_run() == run_id:
        _set_current_run("")

    # Compute changed/new paths introduced during this run.
    # We diff TWO things:
    #   1. New porcelain status lines (catches genuinely new file
    #      appearances and status-transitions like staged→unstaged)
    #   2. Content-hash deltas (catches modify-modify within run window
    #      where porcelain alone would look identical before and after)
    pre_state = _pop_pre_run_state(run_id)
    if pre_state is None:
        # No pre-run snapshot → cannot safely attribute changes to this run.
        # Fail-closed: skip auto-commit, but still publish unstaged-event.
        pre_lines: set[str] = set()
        pre_hashes: dict[str, str] = {}
        _no_baseline = True
    else:
        pre_lines, pre_hashes = pre_state
        _no_baseline = False
    post_lines = _git_porcelain_status()
    post_hashes = _git_dirty_content_hashes()

    new_lines = post_lines - pre_lines
    # Content-changed paths: present in both pre+post but with different hash
    content_changed: set[str] = set()
    for path, new_hash in post_hashes.items():
        old_hash = pre_hashes.get(path)
        if old_hash is None or old_hash != new_hash:
            content_changed.add(path)
    # Combine into a single "touched during run" set (path-strings).
    # For porcelain new_lines, strip the status prefix so we get just paths.
    touched_paths: set[str] = set(content_changed)
    for line in new_lines:
        if len(line) > 3:
            touched_paths.add(line[3:].strip())
        else:
            touched_paths.add(line.strip())
    touched_paths.discard("")

    tool_calls = _pop_tool_calls(run_id)

    # LivingNeuron Fase B (surface-only): udled kandidat-procedure fra kørslens tool-sekvens.
    # Defensiv — må ALDRIG påvirke closure-logikken (som gut_calibration nedenfor).
    try:
        from core.services.procedure_bank_pipeline import maybe_record_procedure_from_run
        rec = maybe_record_procedure_from_run(session_id=session_id, tool_calls=tool_calls)
        if rec:
            from core.services.central_core import central as _central
            _central().observe({"cluster": "cognition", "nerve": "procedure_bank",
                                "recorded": rec.get("name", "")[:60]})
    except Exception:
        logger.debug("run_closure_gate: procedure_bank feed failed", exc_info=True)

    if touched_paths:
        # 2026-08-30 (Jarvis): HÅRD gate for autonome nat-runs.
        # Før: KUN informational event → Discord-subscriber sendte besked kun
        # til Discord-sessioner → et heartbeat nat-run uden Discord-binding
        # efterlod ændringer i stilhed i 6 dage (dreamfix 2026-08-24).
        # Nu: hvis runet var autonomt (ingen bruger til stede), commitér de
        # rørte paths MED pre-commit-hooks — docs-drift, detect-secrets og
        # coverage kører dermed I sessionen, ikke 6 dage senere. Hvis en hook
        # blokerer eller git fejler → nudge til Bjørn med årsagen. Synlige
        # chats (autonomous=False) beholder gammel adfærd — brugeren sidder
        # der og kan selv se/spørge.
        autonomous = bool(payload.get("autonomous"))
        synthetic = {f"   {p}" for p in touched_paths}
        summary = _summarize_unstaged(synthetic)

        auto_commit = None
        if autonomous and not _no_baseline and not pre_lines:
            # Fail-closed: only auto-commit when we have a verified clean
            # baseline. Missing snapshot (_no_baseline) or dirty pre-run
            # state (pre_lines) means we cannot safely attribute changes
            # to this run — another process may have been working too.
            auto_commit = _try_auto_commit(
                touched_paths,
                run_id=run_id,
                session_id=session_id,
                focus=str(payload.get("focus") or "")[:120],
            )
            if auto_commit:
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish("runtime.run_auto_committed", {
                        "run_id": run_id,
                        "session_id": session_id,
                        "commit": auto_commit,
                        "summary": summary,
                        "tool_calls": tool_calls,
                    })
                    logger.info(
                        "run_closure_gate: auto-committed %d paths efter autonomt run %s → %s",
                        summary["count"], run_id[:12], auto_commit[:12],
                    )
                except Exception:
                    logger.debug("run_closure_gate: failed to publish auto-committed event", exc_info=True)

        if not auto_commit:
            # Publiser unstaged-eventen (uanset autonom eller ej) — og for
            # autonome runs tillæg auto_commit_error, så modtageren ser hvorfor
            # gaten ikke kunne forsegle arbejdet selv.
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish("runtime.run_left_unstaged_changes", {
                    "run_id": run_id,
                    "session_id": session_id,
                    "summary": summary,
                    "tool_calls": tool_calls,
                    "autonomous": autonomous,
                    "auto_commit_error": _last_auto_commit_error,
                })
                logger.info(
                    "run_closure_gate: %d unstaged paths after run %s (%s)",
                    summary["count"],
                    run_id[:12],
                    ", ".join(summary["paths"][:3]),
                )
            except Exception:
                logger.debug("run_closure_gate: failed to publish unstaged event", exc_info=True)

            # Autonome nat-runs har ofte INGEN Discord-session — den gamle
            # event ville forsvinde i stilhed. Nudge-brønden leverer til Bjørn
            # uanset kanal og venter til han er der. (Synlige chats: brugeren
            # er til stede, eksisterende kanaler dækker det.)
            if autonomous:
                _notify_auto_commit_blocked(summary, run_id=run_id, session_id=session_id)

    # Silent-run detection: tool calls happened but no visible text was
    # delivered. We check the run-record DB for the final preview text.
    #
    # 2026-05-22 (Claude, second pass): originally queried `output_text`
    # column which doesn't exist — the column is `text_preview`. The
    # try/except silently swallowed the OperationalError so silent-run
    # detection never fired. Corroborated by run autonomous-141add33d9
    # (30 tool.force_invoked, 20 agentic rounds, text_preview empty,
    # zero notification to Bjørn — his actual complaint pattern).
    if tool_calls:
        try:
            from core.runtime.db import connect
            with connect() as conn:
                row = conn.execute(
                    "SELECT text_preview FROM visible_runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
            output = (row[0] if row else "") or ""
            if not output.strip():
                from core.eventbus.bus import event_bus
                event_bus.publish("runtime.run_ended_silent", {
                    "run_id": run_id,
                    "session_id": session_id,
                    "tool_calls": tool_calls,
                    "tool_call_count": len(tool_calls),
                    "unique_tools": sorted(set(tool_calls)),
                })
                logger.info(
                    "run_closure_gate: silent run %s — %d tool calls, no visible output",
                    run_id[:12], len(tool_calls),
                )
        except Exception:
            logger.warning("run_closure_gate: failed silent-run check", exc_info=True)


def _on_run_started(payload: dict[str, Any]) -> None:
    """Handle runtime.autonomous_run_started — snapshot git state."""
    run_id = str(payload.get("run_id") or "")
    if run_id:
        _record_pre_run_state(run_id)
        _set_current_run(run_id)


def _on_tool_used(payload: dict[str, Any]) -> None:
    """Track tool calls so we can detect silent runs.

    Tool events from simple_tools.py don't include run_id in their
    payload — _record_tool_call falls back to the current in-flight
    run via _get_current_run().
    """
    run_id = str(payload.get("run_id") or "")
    tool_name = str(payload.get("tool") or payload.get("tool_name") or "")
    if tool_name:
        _record_tool_call(run_id, tool_name)


# ── eventbus subscriber thread ────────────────────────────────────────


def _listener_loop(q: "queue.Queue[dict[str, Any] | None]") -> None:
    global _listener_running
    while _listener_running:
        try:
            item = q.get(timeout=2.0)
            if item is None:
                break
            kind = str(item.get("kind") or "")
            payload = dict(item.get("payload") or {})
            if kind == "runtime.autonomous_run_started":
                _on_run_started(payload)
            elif kind == "runtime.autonomous_run_completed":
                _on_run_completed(payload)
            elif kind == "tool.invoked" or kind == "tool.used":
                _on_tool_used(payload)
            # Gut-calibration (fodrer cognitive_gut_state — tidligere forældreløs
            # skrive-sti). Defensiv: må ALDRIG påvirke closure-logikken.
            try:
                from core.services import gut_calibration
                gut_calibration.observe_run_event(kind, payload)
            except Exception:
                logger.debug("run_closure_gate: gut observe failed", exc_info=True)
        except queue.Empty:
            continue
        except Exception:
            logger.warning("run_closure_gate: listener iteration error", exc_info=True)


def start_run_closure_gate() -> None:
    """Start the eventbus subscriber thread. Safe to call multiple times."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        from core.eventbus.bus import event_bus
        q = event_bus.subscribe()
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop,
            args=(q,),
            daemon=True,
            name="run-closure-gate",
        )
        _listener_thread.start()
        logger.warning(
            "run_closure_gate: subscriber started — event_bus=%s subscribers=%d",
            id(event_bus),
            len(event_bus._subscribers),
        )
    except Exception:
        logger.exception("run_closure_gate: failed to start subscriber")


def stop_run_closure_gate() -> None:
    global _listener_running
    _listener_running = False
