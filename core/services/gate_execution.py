"""Execution-cluster gate 🔒 — én graderet SECURITY-gate for ALLE tool-eksekverings-
sikkerhedsbeslutninger (shell/filsystem/operator-skrivning + workspace-trust).

KONSOLIDERING (som TruthGate 8→1): seks spredte, rå inline-checks der hver lå med
sin egen ``except: pass`` fail-retning og INGEN trace, samles her bag ÉT gate-kald
routet gennem Den Intelligente Central. Før var de usynlige i loggen — en exception i
en guard slap en destruktiv handling igennem ubemærket. Nu er HVER eksekverings-
beslutning traced (run_id), circuit-breaker-dækket, drift-overvåget og incident-logget.

Smeltede detektorer (kaldes internt, ejer stadig deres regex/tabeller hvor de bor):
  - classify_command            (simple_tools)            → auto/approval/destructive/blocked
  - classify_file_write         (simple_tools)            → auto/approval/blocked
  - check_bash_command_safe     (read_before_write_guard) → protected-fil-clobber via bash
  - check_read_before_write     (read_before_write_guard) → protected-fil-clobber via write_file
  - check_operator_read_before_write (read_before_write_guard) → operator-side clobber
  - guard_code_write            (workspace_trust)         → skriv/exec i ikke-betroet workspace

Grader (matcher TruthGate-modellen):
  RED    = blocked-klassifikation · read-before-write-blok · ikke-betroet workspace → DENY
  YELLOW = destructive/approval-klassifikation → kræver bruger-godkendelse (approval-kort)
  GREEN  = auto / tilladt → fortsæt

FAIL-RETNING (ærligt): gaten er SECURITY (kan ikke slås fra, circuit-breaker + incident).
De EKSPLICITTE blok-signaler (classify=blocked, rbw fandt ulæst protected-fil, untrusted)
er ren/robust detektion → RED med fuld tillid. De infra-afhængige sub-checks (rbw's
shared_cache-opslag) fejler allerede SIKKERT internt (_was_read-fejl → "ikke læst" → blok).
Et uventet infra-blip i selve guard-orkestreringen bevarer den tidligere fail-open adfærd
(blokerer ikke harmløse owner-kommandoer = ingen brick) MEN er nu traced via Centralen i
stedet for et tavst ``except: pass``. Det lukker observabilitets-hullet ("bugs i blinde").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict

_SEC = GateClass.SECURITY


# ── interne verdict-byggere ──────────────────────────────────────────────
def _red(nerve: str, reason: Any, classification: str) -> Verdict:
    return Verdict(nerve, Decision.RED, str(reason or ""), action="block", klass=_SEC,
                   evidence={"classification": classification, "reason": str(reason or "")})


def _yellow(nerve: str, classification: str) -> Verdict:
    return Verdict(nerve, Decision.YELLOW, f"approval:{classification}", action="warn",
                   klass=_SEC, evidence={"classification": classification})


def _green(nerve: str, classification: str) -> Verdict:
    return Verdict(nerve, Decision.GREEN, str(classification), action="none", klass=_SEC,
                   evidence={"classification": classification})


# ── den konsoliderede gate ───────────────────────────────────────────────
def execution_gate(ctx: dict[str, Any]) -> Verdict:
    """Én SECURITY-gate, dispatch på ctx['action']. Returnér ét graderet Verdict.
    Verdict.evidence['classification'] bærer rå-signalet så kald-stedet kan bygge sit
    eksakte svar (approval-kort, guard_blocked-besked, blocked-fejl) uden adfærdstab."""
    action = str(ctx.get("action") or "")

    # ── shell-kommando: rbw FØR classify (paritet med _exec_bash) ──
    if action == "command":
        command = str(ctx.get("command") or "")
        session_id = str(ctx.get("session_id") or "default")
        blocked_only = bool(ctx.get("blocked_only"))
        if not blocked_only:
            try:
                from core.services.read_before_write_guard import check_bash_command_safe
                ok, reason = check_bash_command_safe(command, session_id=session_id)
                if not ok:
                    return _red("exec_command", reason, "guard_blocked")
            except Exception:
                pass  # infra-blip → fortsæt til classify (blocked blokerer stadig)
        from core.tools.simple_tools import classify_command
        cls = classify_command(command)
        if cls == "blocked":
            return _red("exec_command", "command blocked for safety", "blocked")
        if blocked_only:
            return _green("exec_command", cls)
        if cls in ("destructive", "approval"):
            return _yellow("exec_command", cls)
        return _green("exec_command", "auto")

    # ── fil-skrivning: classify FØR rbw (paritet med _exec_write_file) ──
    if action == "file":
        path = str(ctx.get("path") or "")
        session_id = str(ctx.get("session_id") or "default")
        kind = str(ctx.get("kind") or "write")  # write | edit
        blocked_only = bool(ctx.get("blocked_only"))
        from core.tools.simple_tools import classify_file_write
        cls = classify_file_write(path)
        if cls == "blocked":
            return _red("exec_file", f"{kind} blocked for safety", "blocked")
        if blocked_only:
            return _green("exec_file", cls)
        if cls == "approval":
            return _yellow("exec_file", "approval")
        # auto-stien → read-before-write (KUN write; edit har historisk ingen rbw)
        if kind == "write":
            try:
                from core.services.read_before_write_guard import check_read_before_write
                ok, reason = check_read_before_write(path, session_id=session_id)
                if not ok:
                    return _red("exec_file", reason, "guard_blocked")
            except Exception:
                pass  # infra-blip → tillad (paritet med tidligere except:pass), men traced
        return _green("exec_file", "auto")

    # ── workspace-trust (skrive/exec i ikke-betroet code-workspace) ──
    if action == "workspace_trust":
        tool_name = str(ctx.get("tool_name") or "")
        try:
            from core.services.workspace_trust import guard_code_write
            block = guard_code_write(tool_name)
        except Exception:
            block = None  # paritet med tidligere _trust_block=None (fail-open)
        if block:
            return _red("exec_workspace_trust", block, "untrusted")
        return _green("exec_workspace_trust", "trusted")

    # ── operator-side read-before-write (write/edit på brugerens maskine) ──
    if action == "operator":
        path = str(ctx.get("path") or "")
        session_id = str(ctx.get("session_id") or "default")
        file_exists = ctx.get("file_exists")
        try:
            from core.services.read_before_write_guard import check_operator_read_before_write
            ok, reason = check_operator_read_before_write(
                path, session_id=session_id, file_exists=file_exists)
            if not ok:
                return _red("exec_operator", reason, "guard_blocked")
        except Exception:
            pass
        return _green("exec_operator", "auto")

    # ukendt action → ingen indvending (gaten kaldes kun fra kendte kald-steder)
    return _green("execution", "unknown_action")


# ── resultat-objekt + central-routing ────────────────────────────────────
@dataclass
class ExecCheck:
    allowed: bool          # True ⇔ GREEN (fortsæt uden videre)
    decision: Decision
    classification: str    # auto|approval|destructive|blocked|guard_blocked|untrusted|trusted
    reason: str


def _to_check(v: Verdict) -> ExecCheck:
    ev = v.evidence or {}
    cls = str(ev.get("classification") or "")
    # Isoleret/breaker-RED (central isolerer en fejlende SECURITY-nerve) har ingen
    # klassifikation → map til generisk hård blok, så kald-stedet nægter i stedet for
    # tavst at slippe igennem.
    if not cls and v.decision is Decision.RED:
        cls = "blocked"
    return ExecCheck(
        allowed=v.decision is Decision.GREEN,
        decision=v.decision,
        classification=cls,
        reason=str(ev.get("reason") or v.reason or ""),
    )


def _decide(nerve: str, ctx: dict[str, Any]) -> Verdict:
    """Route gennem Den Intelligente Central (SECURITY). Defense-in-depth: hvis central-
    stien kollapser, kør gaten direkte så vi ALDRIG taber håndhævelse; sidste udvej GREEN
    (for ikke at brikke harmløse handlinger — enforcement-tabet er da allerede traced)."""
    try:
        from core.services.central_core import central
        return central().decide(nerve, ctx, execution_gate, cluster="execution", klass=_SEC)
    except Exception:
        try:
            return execution_gate(ctx)
        except Exception:
            return Verdict(nerve, Decision.GREEN, "exec-gate-error", klass=_SEC,
                           evidence={"classification": ""})


# ── offentlige kald-helpers (ét pr. eksekverings-koncern) ────────────────
def check_command(command: str, session_id: str = "default", *,
                  blocked_only: bool = False) -> ExecCheck:
    return _to_check(_decide("exec_command", {
        "action": "command", "command": command,
        "session_id": session_id, "blocked_only": blocked_only}))


def check_file(path: str, session_id: str = "default", *,
               kind: str = "write", blocked_only: bool = False) -> ExecCheck:
    return _to_check(_decide("exec_file", {
        "action": "file", "path": path, "session_id": session_id,
        "kind": kind, "blocked_only": blocked_only}))


def check_workspace_trust(tool_name: str) -> ExecCheck:
    return _to_check(_decide("exec_workspace_trust", {
        "action": "workspace_trust", "tool_name": tool_name}))


def check_operator(path: str, session_id: str = "default", *,
                   file_exists: bool | None = None) -> ExecCheck:
    return _to_check(_decide("exec_operator", {
        "action": "operator", "path": path,
        "session_id": session_id, "file_exists": file_exists}))
