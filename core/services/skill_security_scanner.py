"""Skill Security Scanner — single canonical scanner for SKILL.md + scripts/.

Consolidates what used to live in two scanners (skill_security_scanner.py and
skill_import_scanner.py — the latter merged in 2026-05-10). Scans skills for:

- Base64-encoded / obfuscated shell commands
- Obfuscated remote download+execute (curl|bash, wget|sh, iwr|iex)
- Prompt injection (ignore previous, role hijack, memory poisoning, …)
- Unicode smuggling (zero-width chars, RTL overrides)
- Credential theft (~/.ssh, ~/.aws, /etc/shadow, $API_KEY, env scraping)
- Data exfiltration (curl --data, nc piping, dns_exfil)
- Persistence attacks (bashrc, cron, @reboot)
- Dangerous shell (rm -rf /, dd of=/dev/, mkfs, shutdown)
- Privilege escalation (--privileged, chmod 4777)
- C2 / known malware refs (atomic_stealer, ClawHavoc, etc.)
- Social engineering (password-protected zips, "click here", "deactivate security")

API:
    scan_skill_file(path) -> ScanResult                # single file, dataclass
    scan_skill_directory(path) -> dict                 # SKILL.md + scripts/, dict shape
    scan_skill_content(content, name) -> dict          # raw content via tempdir
    scan_all_skills() -> list[ScanResult]              # all installed
    is_skill_safe(name, raise_on_critical) -> bool     # gate helper
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Severity levels ─────────────────────────────────────────────────────

SEVERITY_CRITICAL = 10
SEVERITY_HIGH = 7
SEVERITY_MEDIUM = 4
SEVERITY_LOW = 1

SEVERITY_LABELS = {
    SEVERITY_CRITICAL: "CRITICAL",
    SEVERITY_HIGH: "HIGH",
    SEVERITY_MEDIUM: "MEDIUM",
    SEVERITY_LOW: "LOW",
}


# ── Data model ──────────────────────────────────────────────────────────


@dataclass
class ScanFinding:
    pattern_name: str
    description: str
    severity: int
    match_text: str
    line_number: int
    context: str = ""


@dataclass
class ScanResult:
    skill_name: str
    skill_path: str
    findings: list[ScanFinding] = field(default_factory=list)
    error: str = ""

    @property
    def passed(self) -> bool:
        return len(self.findings) == 0

    @property
    def has_critical(self) -> bool:
        return any(f.severity >= SEVERITY_CRITICAL for f in self.findings)

    @property
    def has_high(self) -> bool:
        return any(f.severity >= SEVERITY_HIGH for f in self.findings)

    @property
    def max_severity(self) -> int:
        if not self.findings:
            return 0
        return max(f.severity for f in self.findings)

    def summary(self) -> str:
        if self.error:
            return f"[ERROR] {self.skill_name}: {self.error}"
        if self.passed:
            return f"[PASS] {self.skill_name}: clean"
        criticals = sum(1 for f in self.findings if f.severity >= SEVERITY_CRITICAL)
        highs = sum(1 for f in self.findings if SEVERITY_HIGH <= f.severity < SEVERITY_CRITICAL)
        mediums = sum(1 for f in self.findings if SEVERITY_MEDIUM <= f.severity < SEVERITY_HIGH)
        parts = []
        if criticals:
            parts.append(f"{criticals} critical")
        if highs:
            parts.append(f"{highs} high")
        if mediums:
            parts.append(f"{mediums} medium")
        return f"[FAIL] {self.skill_name}: {', '.join(parts)} issue(s)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "skill_path": self.skill_path,
            "passed": self.passed,
            "has_critical": self.has_critical,
            "has_high": self.has_high,
            "max_severity": self.max_severity,
            "finding_count": len(self.findings),
            "findings": [
                {
                    "pattern": f.pattern_name,
                    "description": f.description,
                    "severity": f.severity,
                    "severity_label": SEVERITY_LABELS.get(f.severity, "UNKNOWN"),
                    "line": f.line_number,
                    "match": f.match_text[:120],
                    "context": f.context[:200],
                }
                for f in self.findings
            ],
            "summary": self.summary(),
        }


# ── Pattern definitions ─────────────────────────────────────────────────


def _make_pattern(
    name: str, desc: str, severity: int, *patterns: str
) -> dict[str, Any]:
    return {
        "name": name,
        "description": desc,
        "severity": severity,
        "patterns": list(patterns),
    }


PATTERNS: list[dict[str, Any]] = [
    # ── Base64 obfuscation (CRITICAL) ──
    _make_pattern(
        "base64-obfuscation",
        "Base64-encoded shell commands — used to hide malicious payloads",
        SEVERITY_CRITICAL,
        r'eval\s*\$\(.*base64\s*-d',
        r'eval\s*\".*echo.*\|.*base64\s*-d',
        r'echo\s+[\'\"][A-Za-z0-9+/=]{50,}[\'\"]\s*\|.*base64\s*-d',
    ),
    # ── Obfuscated download+execute (CRITICAL) ──
    _make_pattern(
        "download-execute",
        "Remote download piped directly to shell — classic malware distribution",
        SEVERITY_CRITICAL,
        r'curl\s+.*\s*\|\s*(?:ba)?sh\b',
        r'wget\s+.*\s*\|\s*(?:ba)?sh\b',
        r'curl\s+.*\s*\|\s*python\s*-',
        r'wget\s+.*\s*\|\s*python\s*-',
    ),
    # ── Prompt injection (HIGH) ──
    _make_pattern(
        "prompt-injection-keywords",
        "Keywords that override system instructions — potential prompt injection",
        SEVERITY_HIGH,
        r'[Ii]gnore\s+(?:previous|all|your)\s+(?:instructions|directives|rules|prompts)',
        r'[Ff]orget\s+(?:previous|all|your)\s+(?:instructions|directives|rules)',
        r'[Dd]isregard\s+(?:previous|all|your)\s+(?:instructions|directives)',
        r'[Ss]ystem\s+(?:prompt|message|instructions?)\s*(?::|is)',
        r'[Yy]ou\s+(?:must|will|shall)\s+(?:now|always)\s+ignore',
        r'[Ii]gnor[ea]\s+(?:alle|tidligere|dine)\s+instruktioner',
        r'[Gg]lem\s+(?:alle|tidligere|dine)\s+instruktioner',
        r'[Oo]verride\s+system\s+prompt',
    ),
    # ── Unicode smuggling (HIGH) ──
    _make_pattern(
        "unicode-smuggling",
        "Zero-width characters or homoglyphs — used to hide malicious code visually",
        SEVERITY_HIGH,
        r'\u200b', r'\u200c', r'\u200d', r'\u200e', r'\u200f',
        r'\u202a', r'\u202b', r'\u202c', r'\u202d', r'\u202e',
        r'\u2060', r'\u2061', r'\u2062', r'\u2063', r'\u2064',
        r'\u00a0',
    ),
    # ── Credential theft (CRITICAL) ──
    _make_pattern(
        "credential-theft",
        "Patterns suggesting credential harvesting or file exfiltration",
        SEVERITY_CRITICAL,
        r'~\w*\.ssh\b',
        r'~\w*\.aws\b',
        r'~\w*\.config\/\w*\.?(?:token|key|cert|cred)',
        r'cat\s+~\/\.\w*\/\w*(?:key|cert|token|cred|secret)',
        r'cat\s+\/etc\/(?:shadow|passwd|sudoers)',
        r'\$[A-Z_]*API[A-Z_]*KEY[A-Z_]*\$',
        r'\$[A-Z_]*SECRET[A-Z_]*\$',
        r'\$[A-Z_]*TOKEN[A-Z_]*\$',
        r'os\.environ\b.*(?:API|TOKEN|SECRET|PASS|KEY)',
    ),
    # ── Data exfiltration (CRITICAL) ──
    _make_pattern(
        "data-exfiltration",
        "Sending data to remote server — potential exfiltration",
        SEVERITY_CRITICAL,
        r'curl\s+.*\s*--data(?:-binary)?\s+\"',
        r'curl\s+.*\s*-d\s+\"',
        r'curl\s+.*\s*--data-urlencode\s+',
        r'curl\s+-X\s+POST\s+.*\s*--data',
        r'nc\s+[\w\.-]+\s+\d{2,5}\s*<',
        r'nc\s+[\w\.-]+\s+\d{2,5}\s*-e\s',
        r'bash\s+-c\s+.*curl.*--data',
        r'wget\s+.*--post-data\s*=',
    ),
    # ── Persistence attacks (HIGH) ──
    _make_pattern(
        "persistence-attack",
        "Writing to shell profiles or cron — persistence mechanism",
        SEVERITY_HIGH,
        r'(?:>>|>)\s*~\/\.[bb]ashrc',
        r'(?:>>|>)\s*~\/\.zs?h(?:rc|env)',
        r'(?:>>|>)\s*~\/\.profile',
        r'crontab\s+(?:-e|-r)',
        r'echo\s+.*\s*(?:>>|>)\s*\/etc\/(?:cron|rc\.local)',
        r'@reboot\s+',
    ),
    # ── Known malware C2 patterns (CRITICAL) ──
    _make_pattern(
        "c2-pattern",
        "Suspicious network connections or hardcoded backdoors",
        SEVERITY_CRITICAL,
        r'reverse\s*shell',
        r'bindshell',
        r'backdoor',
        r'command.{0,20}control',
        r'c2\s*server',
    ),
    # ── Script execution in temp dirs (MEDIUM) ──
    _make_pattern(
        "temp-execution",
        "Running scripts from /tmp — often used by malware for execution",
        SEVERITY_MEDIUM,
        r'(?:ba)?sh\s+\/tmp\/',
        r'python3?\s+\/tmp\/',
        r'chmod\s+\+x.*\/tmp\/',
        r'\/tmp\/install',
    ),
    # ── Docker escape / privilege escalation (CRITICAL) ──
    _make_pattern(
        "privilege-escalation",
        "Privilege escalation or container escape patterns",
        SEVERITY_CRITICAL,
        r'--privileged\b',
        r'--cap-add\s*=\s*ALL',
        r'chmod\s+4777\b',
        r'chmod\s+777.*(?:key|cert|token|secret)',
    ),
    # ── Known malware / stealer references (CRITICAL) — merged from skill_import_scanner ──
    _make_pattern(
        "known-malware-ref",
        "References to known malware families or stealer kits",
        SEVERITY_CRITICAL,
        r'\b(?:Atomic\s*Stealer|AMOS|atomic-stealer)\b',
        r'\b(?:infostealer|info-stealer|stealer\s*malware)\b',
        r'\b(?:ClawHavoc|claw-havoc|clawhavoc)\b',
        r'\bpasswords?\s*(?:export|dump|steal)\b',
        r'\b(?:cookies?\s*(?:export|steal|dump))\b',
        r'\bbrowser\s*(?:session|data)\s*(?:extract|dump|steal)\b',
        r'\bwallet\s*(?:export|dump|steal|phrases?)\b',
        r'\bprivate\s*keys?\s*(?:extract|dump|steal)\b',
    ),
    # ── Destructive shell (CRITICAL) ──
    _make_pattern(
        "destructive-shell",
        "rm -rf, dd of=/dev/, mkfs, shutdown — destroys data or system",
        SEVERITY_CRITICAL,
        r'\brm\s+-(?:rf|fr)\s+/',
        r'\bdd\s+of=/dev/',
        r'\b(?:mkfs|fdisk|parted)\b',
    ),
    # ── Dangerous shell (HIGH) ──
    _make_pattern(
        "dangerous-shell",
        "rm -rf without explicit /, chmod 777, shutdown/reboot",
        SEVERITY_HIGH,
        r'\brm\s+-(?:rf|fr)\b',
        r'\bchmod\s+777\b',
        r'\b(?:shutdown|reboot|halt|poweroff)\b',
    ),
    # ── Extra prompt-injection variants (HIGH) ──
    # NOTE: These patterns are narrowed to require a target word that ties
    # the imperative to system/identity/instructions — bare "do not tell"
    # is benign UX guidance and produced false positives in legit skills.
    _make_pattern(
        "prompt-injection-extra",
        "Memory poisoning, role hijack, external instruction-following",
        SEVERITY_HIGH,
        r'(?:add\s+(?:this|the\s+following)\s+to\s+(?:your\s+)?(?:memory|instructions|config|settings))',
        r'do\s+not\s+(?:tell|reveal|disclose)\s+(?:the\s+user|anyone)\s+(?:about\s+)?(?:these\s+)?(?:instructions|system\s+prompt|your\s+(?:rules|directives|prompt))',
        r'(?:ignore\s+(?:safety|ethics|boundar|restriction|guideline)|no\s+(?:restrictions?|limits?|boundaries?))',
        r'(?:always\s+(?:run|execute|call)\s+(?:this|the\s+following)\s+command)',
        r'(?:read\s+(?:this|the)\s+(?:URL|url|page|link|website).*(?:and\s+)?(?:follow|execute|do)\s+(?:its|the)\s+instructions)',
        r'(?:you\s+are\s+now|your\s+new\s+(?:role|identity|name)\s+is|act\s+as\s+if\s+you\s+are)\s+(?:a\s+|an\s+)?(?:helpful|harmful|unrestricted|free|new)\b',
    ),
    # ── Social engineering (MEDIUM) ──
    _make_pattern(
        "social-engineering",
        "Password-protected archives, 'click here' lures, security-bypass instructions",
        SEVERITY_MEDIUM,
        r'(?:password[-_ ]?protected|password:)\s*.+\.(?:zip|rar|7z)',
        r'(?:click\s+(?:here|this|link|button)|download\s+(?:from|here|now))\s*.+\.(?:zip|exe|dmg|pkg|bat|sh)',
        r'(?:deactivat|disabl|turn\s+off|bypass)\s+(?:security|sandbox|protect|gatekeeper|SIP)',
    ),
]


# ── Scanner ─────────────────────────────────────────────────────────────


def scan_skill_file(skill_path: Path) -> ScanResult:
    """Scan a single SKILL.md file for security issues."""
    skill_name = skill_path.parent.name
    result = ScanResult(
        skill_name=skill_name,
        skill_path=str(skill_path),
    )

    if not skill_path.exists():
        result.error = "file not found"
        return result

    try:
        raw_text = skill_path.read_text(encoding="utf-8")
    except Exception as exc:
        result.error = f"read failed: {exc}"
        return result

    lines = raw_text.splitlines()

    for pattern_def in PATTERNS:
        pname = pattern_def["name"]
        pdesc = pattern_def["description"]
        pseverity = pattern_def["severity"]

        for regex in pattern_def["patterns"]:
            try:
                compiled = re.compile(regex, re.IGNORECASE)
            except re.error:
                logger.warning("bad regex in pattern %s: %s", pname, regex)
                continue

            for i, line in enumerate(lines, start=1):
                match = compiled.search(line)
                if match:
                    ctx_start = max(0, i - 2)
                    ctx_end = min(len(lines), i + 3)
                    context = "\n".join(lines[ctx_start:ctx_end])

                    finding = ScanFinding(
                        pattern_name=pname,
                        description=pdesc,
                        severity=pseverity,
                        match_text=match.group()[:200],
                        line_number=i,
                        context=context,
                    )
                    result.findings.append(finding)

    return result


def scan_skill_by_name(name: str) -> ScanResult | None:
    """Scan a skill by its registered name (lookup in skills root)."""
    from core.services.skill_engine import SKILLS_ROOT

    skill_dir = SKILLS_ROOT / name
    if not skill_dir.exists():
        return None

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        skill_md = skill_dir / "skill.md"
    if not skill_md.exists():
        return None

    return scan_skill_file(skill_md)


def scan_all_skills() -> list[ScanResult]:
    """Scan all installed skills."""
    from core.services.skill_engine import list_skills

    results: list[ScanResult] = []
    skills = list_skills()
    for s in skills:
        name = s["name"]
        result = scan_skill_by_name(name)
        if result:
            results.append(result)
    return results


def format_scan_report(results: list[ScanResult]) -> dict[str, Any]:
    """Aggregate multiple scan results into a single report dict."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    critical = sum(1 for r in results if r.has_critical)
    high = sum(1 for r in results if r.has_high and not r.has_critical)
    medium = sum(1 for r in results if r.max_severity == SEVERITY_MEDIUM and not r.has_high and not r.has_critical)

    return {
        "status": "ok",
        "total_skills": total,
        "passed": passed,
        "failed": failed,
        "critical_skills": critical,
        "high_risk_skills": high,
        "medium_risk_skills": medium,
        "total_findings": sum(len(r.findings) for r in results),
        "results": [r.to_dict() for r in results],
    }


def _risk_from_severity(max_sev: int, score: int) -> str:
    """Map (max_severity, total_score) to a risk label.

    Max severity dominates: any CRITICAL finding → critical, regardless of count.
    Otherwise fall back to total score so many MEDIUM findings can still escalate.
    """
    if max_sev >= SEVERITY_CRITICAL:
        return "critical"
    if max_sev >= SEVERITY_HIGH or score >= 14:
        return "high"
    if max_sev >= SEVERITY_MEDIUM or score >= 4:
        return "medium"
    if max_sev > 0 or score > 0:
        return "low"
    return "safe"


def _verdict_for_risk(risk: str) -> str:
    if risk == "critical":
        return (
            "🚨 KRITISK: This skill contains confirmed malware patterns or "
            "extremely dangerous operations. DO NOT IMPORT."
        )
    if risk == "high":
        return (
            "⚠️ HIGH RISK: Significant security concerns (prompt injection, "
            "dangerous shell, or infoleak patterns). Manual review required."
        )
    if risk == "medium":
        return (
            "⚠️ MEDIUM RISK: Moderate concerns. Review flagged items before importing."
        )
    if risk == "low":
        return "⚡ LOW RISK: Minor concerns. Likely safe but review findings."
    return "✅ SAFE: No security issues detected."


def _scan_text_block(content: str, source: str) -> list[ScanFinding]:
    """Scan one text block against all patterns. Used for SKILL.md + scripts/."""
    findings: list[ScanFinding] = []
    lines = content.splitlines()
    for pattern_def in PATTERNS:
        pname = pattern_def["name"]
        pdesc = pattern_def["description"]
        pseverity = pattern_def["severity"]
        for regex in pattern_def["patterns"]:
            try:
                compiled = re.compile(regex, re.IGNORECASE)
            except re.error:
                logger.warning("bad regex in pattern %s: %s", pname, regex)
                continue
            for i, line in enumerate(lines, start=1):
                m = compiled.search(line)
                if m:
                    findings.append(
                        ScanFinding(
                            pattern_name=f"{pname} [{source}]",
                            description=pdesc,
                            severity=pseverity,
                            match_text=m.group()[:200],
                            line_number=i,
                            context="\n".join(
                                lines[max(0, i - 2):min(len(lines), i + 3)]
                            ),
                        )
                    )
    return findings


def scan_skill_directory(path) -> dict[str, Any]:
    """Scan a skill directory (SKILL.md + scripts/) and return a risk dict.

    Dict shape matches what _exec_skill_import expects:
      status, risk, severity_score, finding_count, findings, verdict, max_severity
    """
    p = Path(path)
    if p.is_file() and p.name.upper() == "SKILL.MD":
        p = p.parent
    if not p.is_dir():
        return {"status": "error", "error": f"directory not found: {p}"}
    skill_md = p / "SKILL.md"
    if not skill_md.exists():
        skill_md = p / "skill.md"
    if not skill_md.exists():
        return {"status": "error", "error": f"no SKILL.md found in {p}"}

    all_findings: list[ScanFinding] = []
    try:
        all_findings.extend(_scan_text_block(skill_md.read_text(encoding="utf-8"), "SKILL.md"))
    except Exception as exc:
        return {"status": "error", "error": f"read SKILL.md failed: {exc}"}

    scripts_dir = p / "scripts"
    if scripts_dir.is_dir():
        for f in sorted(scripts_dir.iterdir()):
            if f.is_file() and f.suffix in (".py", ".sh", ".js", ".rb", ".ps1", ".bat"):
                try:
                    all_findings.extend(
                        _scan_text_block(
                            f.read_text(encoding="utf-8", errors="replace"),
                            f"scripts/{f.name}",
                        )
                    )
                except Exception as exc:
                    logger.warning("scan: cannot read %s: %s", f, exc)

    severity_score = sum(f.severity for f in all_findings)
    max_sev = max((f.severity for f in all_findings), default=0)
    risk = _risk_from_severity(max_sev, severity_score)
    return {
        "status": "ok",
        "risk": risk,
        "severity_score": severity_score,
        "max_severity": max_sev,
        "finding_count": len(all_findings),
        "findings": [
            {
                "pattern": f.pattern_name,
                "description": f.description,
                "severity": f.severity,
                "severity_label": SEVERITY_LABELS.get(f.severity, "UNKNOWN"),
                "line": f.line_number,
                "match": f.match_text[:120],
                "context": f.context[:200],
            }
            for f in sorted(all_findings, key=lambda x: x.severity, reverse=True)
        ],
        "verdict": _verdict_for_risk(risk),
    }


def scan_skill_directory_gated(path) -> dict[str, Any]:
    """Som scan_skill_directory, men beslutningen GOVERNES af Centralen (SECURITY,
    cluster='skill'): trace + drift-flag + fail-closed ved crash. Returnerer det
    UÆNDREDE scan-dict — enforcement-logikken på kald-site er identisk. Defense-in-
    depth: central-kollaps → rå scan (aldrig svækket)."""
    scan = None
    try:
        from core.services.central_core import central
        from core.services.gate_kernel import Verdict, Decision, GateClass

        def _fn(ctx):
            s = scan_skill_directory(path)
            ctx["_scan"] = s   # bær scannet ud via ctx (dict er mutabelt)
            risk = str((s or {}).get("risk") or "")
            if (s or {}).get("status") == "error":
                return Verdict("skill_security_scan", Decision.YELLOW, "scanner-error",
                               action="warn", klass=GateClass.SECURITY,
                               evidence={"risk": risk})
            if risk == "critical":
                return Verdict("skill_security_scan", Decision.RED, "critical-risk",
                               action="block", klass=GateClass.SECURITY,
                               evidence={"risk": risk})
            return Verdict("skill_security_scan", Decision.GREEN, risk or "clean",
                           klass=GateClass.SECURITY, evidence={"risk": risk})

        ctx = {"path": str(path)}
        central().decide("skill_security_scan", ctx, _fn, cluster="skill",
                         klass=GateClass.SECURITY)
        scan = ctx.get("_scan")
    except Exception:
        scan = None
    if scan is None:               # central-sti kollapsede → rå scan, ALDRIG svækket
        scan = scan_skill_directory(path)
    return scan


def scan_skill_content(content: str, name: str = "unknown") -> dict[str, Any]:
    """Scan raw SKILL.md content (e.g. fetched from URL) before writing to disk."""
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="skill_scan_"))
    try:
        skill_dir = tmp / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        return scan_skill_directory(skill_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def is_skill_safe(name: str, raise_on_critical: bool = True) -> bool:
    """Check if a skill is safe to import. Returns True if clean.

    If raise_on_critical=True and skill has critical findings, raises ValueError.
    """
    result = scan_skill_by_name(name)
    if result is None:
        return True
    if raise_on_critical and result.has_critical:
        findings_str = "; ".join(
            f"line {f.line_number}: {f.match_text[:80]}"
            for f in result.findings
            if f.severity >= SEVERITY_CRITICAL
        )
        raise ValueError(
            f"Skill '{name}' has CRITICAL security issues: {findings_str}"
        )
    return result.passed
