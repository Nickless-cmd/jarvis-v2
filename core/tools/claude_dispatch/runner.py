from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
import time
import uuid
from typing import Any

from core.tools.claude_dispatch.audit import (
    start_audit_row, finalize_audit_row,
)
from core.tools.claude_dispatch.budget import BudgetTracker
from core.services.dispatch_quota import quota_preflight
from core.tools.claude_dispatch.failure import (
    NONE, classify_dispatch_failure,
)
from core.tools.claude_dispatch.host_oauth import find_host_oauth_token
from core.tools.claude_dispatch.spec import TaskSpec
from core.tools.claude_dispatch.stream import parse_stream_line
from core.tools.claude_dispatch.worktree import create_worktree, worktree_diff

logger = logging.getLogger(__name__)


def _build_prompt(spec: TaskSpec, task_id: str) -> str:
    commit_subject = f"feat(worker): {spec.goal.strip()[:58]}"
    scoped_paths = " ".join(shlex.quote(path) for path in spec.scope_files)
    commit_command = shlex.join([
        "python",
        "scripts/commit_with_attribution.py",
        "--repo", ".",
        "--actor", "opus",
        "--run-id", task_id,
        "--session-id", "none",
        "--origin", "delegated",
        "--approved-by", "policy:claude-dispatch-v1",
        "--message", commit_subject,
        *[
            item
            for path in spec.scope_files
            for item in ("--path", path)
        ],
    ])
    parts = [
        f"GOAL: {spec.goal}",
        "",
        "SCOPE (touch only these paths):",
        *[f"  - {p}" for p in spec.scope_files],
    ]
    if spec.forbidden_paths:
        parts += ["", "FORBIDDEN:", *[f"  - {p}" for p in spec.forbidden_paths]]
    if spec.success_criteria:
        parts += ["", f"SUCCESS CRITERIA: {spec.success_criteria}"]
    parts += [
        "",
        "Operate strictly within SCOPE. Do not modify files outside it.",
        "",
        "When you have finished writing or editing files, stage only the "
        "scoped paths and commit through the attributed wrapper. Use:",
        f"git add -- {scoped_paths}",
        commit_command,
        "",
        "After committing, summarize what you changed in one paragraph.",
    ]
    return "\n".join(parts)


def _new_task_id() -> str:
    return uuid.uuid4().hex[:12]


def run_dispatch(spec: TaskSpec, eventbus: Any) -> dict[str, Any]:
    task_id = _new_task_id()
    branch = f"claude/{task_id}"

    budget = BudgetTracker()
    budget.check_and_reserve()  # raises BudgetExceeded if cap hit

    start_audit_row(task_id, spec)
    eventbus.publish("tool.dispatch.started", {"task_id": task_id, "goal": spec.goal})

    # 2026-11-04: kvoten måles FØR worktreet oprettes. Ved 100 % er dispatchen
    # dødsdømt — den ville oprette et worktree og dø efter sekunder med en
    # fejl der ligner en kodefejl. Blokeringen ligger efter audit-rækken, så
    # det kan ses at den blev afvist og hvorfor; ellers forsvinder den sporløst.
    # Ved målefejl går den igennem (fail-open): en netværksfejl er ikke et
    # bevis for at kvoten er brugt.
    if os.environ.get("JARVIS_DISPATCH_PREFLIGHT", "1").strip() not in ("0", "false", "no"):
        preflight = quota_preflight("claude")
        if not preflight["allow"]:
            error = f"quota_exhausted: {preflight['reason']}"
            finalize_audit_row(
                task_id, status="error", tokens_used=0, exit_code=None,
                diff_summary="", error=error, failure_kind="quota_exhausted",
            )
            eventbus.publish("tool.dispatch.finished", {
                "task_id": task_id, "status": "error",
                "tokens": 0, "branch": branch,
                "failure_kind": "quota_exhausted",
            })
            return {
                "task_id": task_id, "status": "error", "tokens": 0,
                "branch": branch, "diff_summary": "", "error": error,
                "failure_kind": "quota_exhausted",
                "action": (
                    "Kvoten er opbrugt — den går over af sig selv. "
                    "Der blev IKKE oprettet et worktree, og intet arbejde er tabt. "
                    f"Reset: {preflight['resets_at'] or 'ukendt'}"
                ),
                "needs_human": False,
            }

    worktree_path = create_worktree(task_id)

    cmd = [
        "claude", "-p", _build_prompt(spec, task_id),
        "--add-dir", str(worktree_path),
        "--allowed-tools", ",".join(spec.allowed_tools),
        "--permission-mode", spec.permission_mode,
        "--output-format", "stream-json",
        "--verbose",
    ]

    tokens_total = 0
    error: str | None = None
    status = "ok"
    exit_code: int | None = None
    deadline = time.monotonic() + spec.max_wall_seconds

    # 2026-04-29: `claude -p` headless calls authenticate via the host's
    # session-specific CLAUDE_CODE_OAUTH_TOKEN env var. The token in
    # ~/.claude/.credentials.json alone returns 401 for headless calls.
    # We look up a live host token from any running Claude Code process
    # owned by the same user and inject it into the spawn env.
    #
    # 2026-11-04: efter at systemd-enheden sætter EnvironmentFile peger
    # tokenet allerede i miljøet, så find_host_oauth_token() bliver aldrig
    # kaldt i drift. Grenen er derfor BEVARET som fallback — den er korrekt
    # og koster intet når den ikke rammes — men den er gjort MÅLBAR i stedet
    # for formodet: token_source følger med i audit-rækken, så «blev
    # fallbacken nogensinde brugt?» kan besvares med et tal i stedet for en
    # antagelse. Død kode der ser levende ud er netop fejlen; død kode der
    # rapporterer at den er død, er ikke.
    spawn_env = os.environ.copy()
    token_source = "env"  # noqa: literal-credential — kilde-etiket, ikke en hemmelighed
    if not spawn_env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        token_source = "host_proc"
        host_token = find_host_oauth_token()
        if host_token:
            spawn_env["CLAUDE_CODE_OAUTH_TOKEN"] = host_token
        else:
            token_source = "missing"  # noqa: literal-credential — kilde-etiket, ikke en hemmelighed
            error = (
                "no host Claude Code OAuth token available — "
                "open Claude Code (desktop or terminal) so its session "
                "exports CLAUDE_CODE_OAUTH_TOKEN, then retry"
            )
            status = "error"
            finalize_audit_row(
                task_id, status=status, tokens_used=0,
                exit_code=None, diff_summary="", error=error,
                token_source=token_source,
            )
            eventbus.publish("tool.dispatch.finished", {
                "task_id": task_id, "status": status,
                "tokens": 0, "branch": branch,
            })
            return {
                "task_id": task_id, "status": status, "tokens": 0,
                "branch": branch, "diff_summary": "", "error": error,
            }

    proc = subprocess.Popen(
        cmd, cwd=str(worktree_path),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, env=spawn_env,
    )

    def _watchdog() -> None:
        while proc.poll() is None:
            if time.monotonic() >= deadline:
                proc.kill()
                return
            time.sleep(1.0)

    wd = threading.Thread(target=_watchdog, daemon=True)
    wd.start()

    # 2026-11-04: stderr blev aldrig laest. Det betoed at aarsagen til en
    # fejl — som oftest staar paa stderr — forsvandt, og at en proces der
    # skrev meget til stderr kunne fylde pipe-bufferen og haenge. Begge er
    # rettet her: en traad toemmer stderr loebende, og raa stdout gemmes
    # forbi JSON-parseren, fordi fejlbeskeder som «You've hit your 5-hour
    # limit» ikke er JSON og derfor blev kastet vaek af parse_stream_line.
    _STDERR_LIMIT = 8000
    _RAW_LIMIT = 8000
    stderr_chunks: list[str] = []
    raw_out: list[str] = []

    def _drain_stderr() -> None:
        total = 0
        if proc.stderr is None:
            return
        try:
            for chunk in proc.stderr:
                if total >= _STDERR_LIMIT:
                    continue
                stderr_chunks.append(chunk)
                total += len(chunk)
        except Exception:
            pass

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                if sum(len(c) for c in raw_out) < _RAW_LIMIT:
                    raw_out.append(line)
                ev = parse_stream_line(line)
                if ev is None:
                    continue
                tokens_total += ev.tokens
                eventbus.publish(
                    f"tool.dispatch.{ev.kind}",
                    {"task_id": task_id, "text": ev.text[:500], "tokens": ev.tokens},
                )
        proc.wait()
        stderr_thread.join(timeout=2.0)
        exit_code = proc.returncode
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        status = "error"
        try:
            proc.kill()
        except Exception as kill_err:  # processen kan allerede vaere vaek
            logger.debug("proc.kill() efter fejl slog fejl: %s", kill_err)

    failure_kind = NONE
    action = ""
    needs_human = False
    if exit_code != 0 and status == "ok":
        status = "error"
        failure = classify_dispatch_failure(
            stdout="".join(raw_out),
            stderr="".join(stderr_chunks),
            exit_code=exit_code,
        )
        failure_kind = failure.kind
        action = failure.action
        needs_human = failure.needs_human
        if error is None:
            # Aarsagen staar i teksten, ikke i exit-koden: doedt token og
            # opbrugt kvote giver BEGGE exit 1 (maalt 4/11-2026).
            if failure.is_failure:
                error = f"{failure.kind}: {failure.detail}"
            else:
                error = f"claude exited with code {exit_code}"

    if time.monotonic() >= deadline:
        status = "timeout"
        if error is None:
            error = f"exceeded max_wall_seconds={spec.max_wall_seconds}"

    diff_summary = ""
    try:
        diff_summary = worktree_diff(task_id)[:8000]
    except Exception:
        pass

    budget.record_usage(tokens_total)
    finalize_audit_row(
        task_id, status=status, tokens_used=tokens_total,
        exit_code=exit_code, diff_summary=diff_summary, error=error,
        failure_kind=failure_kind, token_source=token_source,
    )
    eventbus.publish("tool.dispatch.finished", {
        "task_id": task_id, "status": status,
        "tokens": tokens_total, "branch": branch,
        "failure_kind": failure_kind,
    })

    return {
        "task_id": task_id,
        "status": status,
        "tokens": tokens_total,
        "branch": branch,
        "diff_summary": diff_summary,
        "error": error,
        "failure_kind": failure_kind,
        "action": action,
        "needs_human": needs_human,
        "token_source": token_source,
    }
