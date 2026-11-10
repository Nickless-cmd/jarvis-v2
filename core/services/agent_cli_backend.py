"""Claude Code og Codex CLI som eksekveringsbackends for ``Task``.

CLI'erne er ikke endnu et model-API. De er komplette kodeagenter, saa en
``Task`` der vaelger dem koerer én afgraenset CLI-session i assignmentets
egen arbejdsrod. En skrivende Task bruger altid det allerede reserverede
agent-worktree; en laesende Task bruger repository-roden i read-only mode.

Ruten er kun en eksplicit ejer-rute. Admission bruger den faelles
``dispatch_quota``-preflight, og execution gentager kontrollen umiddelbart
foer processen startes. Intet worktree oprettes her, og intet integreres i
main: den eksisterende Task-livscyklus ejer begge dele.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from core.runtime.config import PROJECT_ROOT


CLI_PROVIDERS = frozenset({"claude-cli", "codex-cli"})
DEFAULT_MODELS = {"claude-cli": "default", "codex-cli": "default"}
ALIASES = {
    "claude": ("claude-cli", "default"),
    "claude-code": ("claude-cli", "default"),
    "claude-cli": ("claude-cli", "default"),
    "codex": ("codex-cli", "default"),
    "codex-cli": ("codex-cli", "default"),
}


class CliBackendError(RuntimeError):
    def __init__(self, message: str, *, error_code: str = "CLI_BACKEND_FAILED",
                 error_phase: str = "execution", provider_status: str = "failed") -> None:
        super().__init__(message)
        self.error_code = error_code
        self.error_phase = error_phase
        self.provider_status = provider_status


_QUOTA_FAILURE_MARKERS = (
    "429", "credit balance", "credits exhausted", "limit reached", "quota",
    "rate limit", "rate_limit", "too many requests", "usage limit",
    "you've hit your limit", "you have hit your limit",
)


def _cli_failure(provider: str, returncode: int, stdout: str, stderr: str) -> CliBackendError:
    detail = (stderr or stdout or "ukendt CLI-fejl").strip()[-2000:]
    normalized = " ".join(detail.lower().split())
    if any(marker in normalized for marker in _QUOTA_FAILURE_MARKERS):
        return CliBackendError(
            f"{provider} har opbrugt eller ramt sin kvote: {detail}",
            error_code="CLI_QUOTA_EXHAUSTED",
            error_phase="provider",
            provider_status="quota_exhausted",
        )
    return CliBackendError(f"{provider} sluttede med {returncode}: {detail}")


def parse_preference(value: str) -> tuple[str, str] | None:
    """Returner en CLI-rute for de dokumenterede aliases, ellers ``None``."""
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw in ALIASES:
        return ALIASES[raw]
    provider, sep, model = raw.partition("/")
    if sep and provider in CLI_PROVIDERS and model.strip():
        return provider, model.strip()
    return None


def is_cli_provider(provider: str) -> bool:
    return str(provider or "").strip() in CLI_PROVIDERS


def resolve_executable(provider: str) -> str | None:
    name = "claude" if provider == "claude-cli" else "codex" if provider == "codex-cli" else ""
    if not name:
        return None
    found = shutil.which(name)
    if found:
        return found
    candidate = Path.home() / ".local" / "bin" / name
    return str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None


def _claude_spawn_env(provider: str) -> dict[str, str]:
    """Miljoeet CLI-processen startes med. Claude skal have SIT EGET token med.

    MAALT 9/11-2026, to fejl der tilsammen gjorde en levende lane ubrugelig:

    1. Spawn'en arvede ``os.environ`` uden ``CLAUDE_CODE_OAUTH_TOKEN``. Headless
       ``claude -p`` autentificerer via den env-var; uden den falder den tilbage
       paa ``~/.claude/.credentials.json``, hvis token udloeb 20/5-2026 — og
       svarede ``401 OAuth access token is invalid``.
    2. En tidligere kontrol her laeste netop den udloebne fil og erklaerede
       lanen doed. Det levende token ligger i ``claude_dispatch.env`` og virker
       (bevist samme dag: samme kommando svarede ``hej``, exit 0), saa kontrollen
       blokerede en lane der kørte fint.

    ``dispatch_quota._claude_token()`` ejer allerede den korrekte kaede
    (miljoe -> env-fil -> credentials) og genbruges her. To kopier af samme
    opslag drev fra hinanden, og den ene pegede paa en udloebet fil.
    """
    env = os.environ.copy()
    if provider != "claude-cli" or env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return env
    from core.services.dispatch_quota import _claude_token

    token, _source = _claude_token()
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    return env


def admission_reason(provider: str) -> str:
    """Tom streng betyder at CLI-ruten kan optages i Task-rutekæden.

    Doed-token-kontrollen ligger bevidst i ``quota_preflight`` og ikke her:
    den bruger ``_claude_token()``s fulde kaede, mens en lokal kopi laeste
    ``.credentials.json`` og erklaerede en virkende lane doed (maalt 9/11-2026).
    """
    if not resolve_executable(provider):
        return "cli_ikke_installeret"
    from core.services.dispatch_quota import quota_preflight

    backend = "claude" if provider == "claude-cli" else "codex"
    preflight = quota_preflight(backend)
    if not preflight["allow"]:
        return f"quota:{preflight['reason']}"
    return ""


def _assignment(agent_id: str) -> dict[str, Any]:
    from core.runtime.db_agent_contract import open_assignment_for_agent

    row = open_assignment_for_agent(agent_id)
    if row is None:
        raise CliBackendError("CLI-backenden kraever et aktivt Task-assignment")
    return dict(row)


def _working_root(agent: dict[str, Any], assignment: dict[str, Any]) -> tuple[str, bool]:
    writes = str(agent.get("tool_policy") or "") == "worktree-write"
    if not writes:
        return str(PROJECT_ROOT), False
    from core.services.agent_worktrees import get_for_assignment

    wt = get_for_assignment(
        owner_user_id=str(assignment["owner_user_id"]),
        assignment_id=str(assignment["assignment_id"]),
    )
    if not wt or str(wt.get("status") or "") != "active":
        raise CliBackendError("Task-worktree mangler eller er ikke aktivt")
    path = os.path.realpath(str(wt.get("path") or ""))
    if not path or not os.path.isdir(path):
        raise CliBackendError("Task-worktree findes ikke paa disken")
    return path, True


def _prompt(prompt: str, *, writes: bool) -> str:
    # Taskens normale worker ser worktree'et som /work. CLI-backenden koerer
    # med samme worktree som cwd og maa ikke sendes paa jagt efter en sti der
    # kun findes inde i workerens bubblewrap-namespace.
    prompt = prompt.replace(
        "your workspace root is /work. Use absolute paths inside that root",
        "your workspace root is the current working directory. Use paths inside that root",
    )
    boundary = (
        "Du arbejder i Task-assignmentets isolerede git-worktree. Udfør ændringer og relevante "
        "verifikationer her; integrer eller push aldrig til main."
        if writes else
        "Opgaven er read-only. Undersøg repository'et, men ændr ingen filer."
    )
    return f"{prompt}\n\nCLI backend boundary: {boundary}\nAfslut med en kompakt, konkret leverance."


def _cli_tools_for_policy(policy: str) -> str:
    """Oversæt en ``tool_policy`` til claude-CLI'ens ``--tools``-liste.

    ## Hvorfor denne findes (maalt 10/11-2026)

    ``_command`` satte værktøjerne ud fra ÉN ting: om policyen var
    ``worktree-write``. Alt andet fik ``Read,Glob,Grep``. Det gjorde
    ``default_tool_policy`` i ``AGENT_ROLE_TEMPLATES`` til **død kode** på
    denne vej — to sandheder om samme agent:

      * ``critic`` og ``planner`` er deklareret med ``"none"`` = nul
        værktøjer, men fik tre. Tabellen loej.
      * ``researcher`` er deklareret med ``read-only-runtime`` = ti værktøjer
        inkl. ``bash``, men fik tre. Tabellen loej den anden vej.

    Det var ikke kosmetik: jeg valgte ``critic`` til en maaleopgave ud fra
    tabellen og fik en agent der ikke kunne maale noget. Den svarede aerligt
    «jeg har ikke maalt noget» — men valget var mit, og det byggede paa en
    tabel der ikke passede med virkeligheden.

    ## Shell er BEVIDST udeladt

    ``_READ_ONLY_TOOLS`` indeholder ``bash``, saa ``read-only-runtime`` lover
    shell i tabellen. CLI-agenter faar den ikke her — og det er nu en
    STRUKTUREL egenskab ved denne funktion, ikke en regel der håndhæver den:
    ingen policy giver shell, heller ikke ``worktree-write``.

    Historik: indtil 10/11-2026 stod der at ``dec_6a234cd30460`` (Bjoern,
    5/11-2026) indskraenkede det. Den beslutning er tilbagekaldt — maalt var
    den overfloedig, fordi koden aldrig gav shell, og den ramte samtidig
    fil-redigeringer der blot naevnte rollenavnet. Det der stod tilbage var
    forskellen mellem tabellen og denne funktion, og den fæstnes stadig af
    ``tests/test_agent_cli_policy.py``.

    Ukendt eller tom policy giver laeseadgang, ikke nul: en CLI der starter
    uden værktøjer kan ikke engang laese den fil den blev bedt om at vurdere,
    og fejlen ville se ud som en tom leverance.
    """
    pol = str(policy or "").strip()
    if pol == "worktree-write":
        return "Read,Glob,Grep,Edit,Write"
    # none, read-only-runtime, read-only-workstation, can-spawn og ukendt:
    # alle er laesende set fra CLI'ens side. `none` er ikke nul her — se
    # docstringen: nul værktøjer gør agenten blind, ikke sikker.
    return "Read,Glob,Grep"


def _command(provider: str, executable: str, model: str, root: str, prompt: str,
             *, policy: str, output_path: str) -> list[str]:
    writes = str(policy or "") == "worktree-write"
    selected = str(model or "").strip()
    if provider == "codex-cli":
        cmd = [executable, "exec", "--ephemeral", "--color", "never", "-C", root,
               "--sandbox", "workspace-write" if writes else "read-only",
               "--output-last-message", output_path]
        if selected and selected != "default":
            cmd += ["--model", selected]
        return [*cmd, prompt]

    tools = _cli_tools_for_policy(policy)
    cmd = [executable, "--print", prompt, "--restricted", "--no-session-persistence",
           "--permission-prompts", "none", "--output-format", "json", "--tools", tools]
    if writes:
        cmd += ["--permission-mode", "acceptEdits"]
    if selected and selected != "default":
        cmd += ["--model", selected]
    return cmd


def _cancelled(agent_id: str) -> bool:
    from core.runtime.db_agent_runtime import get_agent_registry_entry

    status = str((get_agent_registry_entry(agent_id) or {}).get("status") or "")
    return status in {"cancelled", "expired"}


def _stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:  # processen var allerede vaek — intet at draebe
        return
    except Exception:  # processen kan allerede vaere vaek — kill er sidste forsog
        proc.kill()


def _claude_text(stdout: str) -> tuple[str, int, int]:
    try:
        data = json.loads(stdout)
    except ValueError as exc:
        raise CliBackendError(f"Claude CLI gav ikke JSON: {exc}") from exc
    text = str(data.get("result") or "").strip() if isinstance(data, dict) else ""
    usage = data.get("usage") or {} if isinstance(data, dict) else {}
    return text, int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)


def run_task_cli(*, agent: dict[str, Any], prompt: str, run_id: str,
                 timeout_s: float = 45 * 60.0) -> dict[str, Any]:
    """Koer den valgte CLI én gang og returner agent-runtimens resultatform."""
    provider = str(agent.get("provider") or "")
    model = str(agent.get("model") or "default")
    executable = resolve_executable(provider)
    if not executable:
        raise CliBackendError(f"{provider} executable mangler")
    reason = admission_reason(provider)
    if reason:
        is_quota = reason.startswith("quota:")
        raise CliBackendError(
            f"{provider} preflight afviste dispatch: {reason}",
            error_code="CLI_QUOTA_BLOCKED" if is_quota else "CLI_PREFLIGHT_REJECTED",
            error_phase="preflight",
            provider_status="quota_blocked" if is_quota else "rejected",
        )

    assignment = _assignment(str(agent.get("agent_id") or ""))
    root, writes = _working_root(agent, assignment)
    # Policyen sendes videre, ikke kun `writes`: `_cli_tools_for_policy` skal
    # kunne skelne de laesende policies fra hinanden. Foer 10/11-2026 var
    # `default_tool_policy` død kode her, og tabellen loej begge veje.
    policy = str(agent.get("tool_policy") or "")
    fd, output_path = tempfile.mkstemp(prefix="jarvis-task-cli-", suffix=".txt")
    os.close(fd)
    cmd = _command(provider, executable, model, root, _prompt(prompt, writes=writes),
                   policy=policy, output_path=output_path)
    started = time.monotonic()
    proc = subprocess.Popen(
        cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True, env=_claude_spawn_env(provider),
    )
    stdout = stderr = ""
    try:
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=1.0)
                break
            except subprocess.TimeoutExpired:
                if _cancelled(str(agent.get("agent_id") or "")):
                    _stop(proc)
                    proc.wait(timeout=10)
                    raise CliBackendError("Task blev afbrudt")
                if time.monotonic() - started >= timeout_s:
                    _stop(proc)
                    proc.wait(timeout=10)
                    raise CliBackendError(f"{provider} overskred tidsloftet")
        if proc.returncode != 0:
            raise _cli_failure(provider, proc.returncode, stdout, stderr)
        if provider == "claude-cli":
            text, input_tokens, output_tokens = _claude_text(stdout)
        else:
            text = Path(output_path).read_text(encoding="utf-8").strip()
            input_tokens = max(1, len(prompt) // 4)
            output_tokens = max(1, len(text) // 4)
        if not text:
            raise CliBackendError(f"{provider} returnerede ingen leverance")
        return {
            "status": "completed", "text": text, "provider": provider, "model": model,
            "execution_mode": "task-cli-backend", "source": "Task.model",
            "input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": 0.0,
            "run_id": run_id,
        }
    finally:
        try:
            os.unlink(output_path)
        except OSError:  # temp-filen kan vaere ryddet — ikke en fejl der skal kaste
            pass
