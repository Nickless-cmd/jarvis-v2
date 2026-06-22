"""Skill-Safety-cluster gate 🔒 — graderet SECURITY-gate for skill-indholds-scanning
(prompt-injection / malware / boundary) FØR en skill oprettes, vises eller dispatch'es.

KONSOLIDERING: scan_skill-DETEKTOREN (ren regex/unicode-scanner) lå wired på tre spredte
call-sites (skill_engine create=hard-block · skill_engine read=advisory · agent_dispatch
=dispatch-blok), hver med eget ``except: pass`` og INGEN central trace. Nu routes ALLE
skill-scan-beslutninger gennem ÉT gate-kald i Den Intelligente Central → trace pr. run_id
+ circuit-breaker + drift + incident. En blokeret (ondsindet) skill er nu synlig i loggen.

Grader:
  RED    = blokeret (fund ≥ high — ondsindet skill når aldrig disk/dispatch)
  YELLOW = fund under blok-tærskel (advisory — caller/UI kan flagge, men blokerer ikke)
  GREEN  = ren

check_skill_scan returnerer et ScanResult-lignende objekt (.allowed/.blocked_reasons/
.as_dict()) så call-sites er near-drop-in. SECURITY fail-CLOSED: scanner-fejl → RED (en
skill der ikke kan scannes oprettes ikke — den sikre retning for ondsindet-indhold).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict

_SEC = GateClass.SECURITY


def skill_gate(ctx: dict[str, Any]) -> Verdict:
    """Scan skill-indhold via skill_scanner; returnér graderet Verdict.
    Verdict.evidence bærer hele ScanResult.as_dict() + blocked_reasons."""
    content = str(ctx.get("content") or "")
    from core.services.skill_scanner import scan_skill
    res = scan_skill(content)
    ev = {"scan": res.as_dict(), "allowed": bool(res.allowed),
          "blocked_reasons": list(res.blocked_reasons)}
    if not res.allowed:
        return Verdict("skill_scan", Decision.RED,
                       "; ".join(res.blocked_reasons[:3]) or "blokeret",
                       action="block", klass=_SEC, evidence=ev)
    if res.findings:
        return Verdict("skill_scan", Decision.YELLOW, "advisory findings",
                       action="warn", klass=_SEC, evidence=ev)
    return Verdict("skill_scan", Decision.GREEN, "clean", klass=_SEC, evidence=ev)


@dataclass
class SkillScanVerdict:
    """ScanResult-lignende facade så call-sites er near-drop-in."""
    allowed: bool
    decision: Decision
    blocked_reasons: list[str] = field(default_factory=list)
    _scan: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return self._scan


def _decide(ctx: dict[str, Any]) -> Verdict:
    """Route gennem Centralen (SECURITY, fail-CLOSED). Central-katastrofe → kør gaten
    direkte; sidste udvej RED (en skill der ikke kan scannes blokeres = sikker retning)."""
    try:
        from core.services.central_core import central
        return central().decide("skill_scan", ctx, skill_gate, cluster="skill", klass=_SEC)
    except Exception:
        try:
            return skill_gate(ctx)
        except Exception:
            return Verdict("skill_scan", Decision.RED, "skill-gate-error",
                           action="block", klass=_SEC,
                           evidence={"allowed": False, "blocked_reasons": ["scan-error"]})


def check_skill_scan(content: str) -> SkillScanVerdict:
    """Scan skill-indhold gennem Centralen. Returnér ScanResult-lignende facade.
    .allowed=False ⇔ RED (blokér); YELLOW/GREEN ⇒ .allowed=True (advisory-fund i .as_dict)."""
    v = _decide({"kind": "scan", "content": content})
    ev = v.evidence or {}
    return SkillScanVerdict(
        allowed=bool(ev.get("allowed", v.decision is not Decision.RED)),
        decision=v.decision,
        blocked_reasons=list(ev.get("blocked_reasons") or []),
        _scan=dict(ev.get("scan") or {}),
    )
