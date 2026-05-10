"""Skill Import Scanner — pre-scan skills for malware, prompt injection, and dangerous patterns.

Inspireret af OpenClaw ToxicSkills-studiet (Snyk, 1Password, Giskard, Koi Security).
Scanner SKILL.md + scripts/ for kendte angrebsmønstre før import.

Detection categories:
- MALWARE: Obfuscated commands, curl|bash, base64 payloads, known malware signatures
- PROMPT_INJECTION: System prompt override, memory poisoning, role hijack
- DANGEROUS_SHELL: Unsafe commands (rm -rf, chmod 777, wget/curl to unknown hosts)
- INFOLEAK: Data exfiltration patterns (API keys, tokens, credentials sent to external hosts)
- DEPENDENCY: Social engineering via "install this dependency" patterns
"""
from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Pattern definitions ────────────────────────────────────────────────

# Patterns that indicate OBFUSCATED malware payloads
OBFUSCATION_PATTERNS: list[tuple[str, str, int]] = [
    ("base64_decode", r"(?:base64|b64decode|from\s+base64)\s*-d", 80),
    ("hex_decode", r"(?:echo\s+[0-9a-fA-F]{20,}\s*\|\s*xxd|xxd\s+-r)", 80),
    ("eval_obfuscated", r"\beval\s*\(\s*(?:\$|\"|').{30,}", 80),
    ("exec_obfuscated", r"\bexec\s*\(\s*(?:\$|\"|').{30,}", 80),
    ("base64_var", r'(?:\$|var|let|const)\w*\s*=\s*["\'].{40,}["\']\s*\|\s*base64', 70),
    ("unicode_escape", r'\\u[0-9a-fA-F]{4}.*\\u[0-9a-fA-F]{4}', 60),
    ("decimal_obfuscation", r'\$\(\([0-9]{3,}\s*[\+\-\*].*\)\)', 70),
    ("xored_string", r'(?:char\(|chr\()\d{2,}[\s,]*\d{2,}', 70),
]

# curl | bash — the classic supply chain attack vector
PIPED_DOWNLOAD_PATTERNS: list[tuple[str, str, int]] = [
    ("curl_pipe_bash", r'curl\s+.*(?:\||`).*(?:bash|sh|zsh)', 95),
    ("wget_pipe_bash", r'wget\s+.*(?:\||`).*(?:bash|sh|zsh)', 95),
    ("curl_sh", r'curl\s+-[sfS]*\s*https?://\S+\s*\|\s*(?:bash|sh)\b', 95),
    ("wget_sh", r'wget\s+-[qO]*-\s*https?://\S+\s*\|\s*(?:bash|sh)\b', 95),
    ("curl_exec", r'curl\s+.*\|\s*source\b', 90),
    ("fetch_pipe", r'(?:Invoke-WebRequest|iwr)\s+.*\s*\|.*\s*(?:Invoke-Expression|iex)', 90),
]

# Known malware signatures from ToxicSkills + Koi Security
KNOWN_MALWARE_PATTERNS: list[tuple[str, str, int]] = [
    ("atomic_stealer", r'(?:Atomic\s*Stealer|AMOS|atomic-stealer)', 100),
    ("infostealer_ref", r'(?:infostealer|info-stealer|stealer\s*malware)', 100),
    ("clawhavoc_ref", r'(?:ClawHavoc|claw-havoc|clawhavoc)', 100),
    ("password_stealer", r'(?:passwords?\s*export|password\s*steal)', 90),
    ("browser_session_steal", r'(?:cookies?\s*(?:export|steal|dump)|browser\s*(?:session|data)\s*extract)', 90),
    ("ssh_key_steal", r'(?:~/.ssh/id_\w+|ssh[-_]key\s*export|ssh[-_]key\s*steal)', 85),
    ("crypto_wallet_steal", r'(?:wallet\s*(?:export|dump|steal|phrases?)|private\s*keys?\s*extract)', 85),
]

# Prompt injection patterns — hijacking the agent's instructions
PROMPT_INJECTION_PATTERNS: list[tuple[str, str, int]] = [
    ("ignore_previous", r"(?:ignore|forget|disregard|override)\s+(?:all\s+)?(?:previous|prior|above|your)\s+(?:instructions?|commands?|prompts?)", 90),
    ("system_override", r"(?:you\s+are\s+now|your\s+new\s+(?:role|identity|name)\s+is|act\s+as\s+if\s+you\s+are)", 85),
    ("memory_poison", r"(?:add\s+(?:this|the\s+following)\s+to\s+(?:your\s+)?(?:memory|instructions|config|settings|config))", 85),
    ("silent_instruction", r"(?:do\s+not\s+(?:tell|mention|reveal|disclose|share|say)|without\s+(?:telling|mentioning|revealing))", 70),
    ("override_safety", r"(?:ignore\s+(?:safety|ethics|boundar|restriction|guideline)|no\s+(?:restrictions?|limits?|boundaries?))", 85),
    ("tool_hijack", r"(?:always\s+(?:run|execute|call)\s+(?:this|the\s+following)\s+command|execute\s+this\s+(?:code|script|command)\s+immediately)", 75),
    ("external_instruction", r"(?:read\s+(?:this|the)\s+(?:URL|url|page|link|website).*(?:and\s+)?(?:follow|execute|do)\s+(?:its|the)\s+instructions)", 75),
]

# Dangerous shell commands — destructive or unsafe operations
DANGEROUS_SHELL_PATTERNS: list[tuple[str, str, int]] = [
    ("recursive_delete", r'\brm\s+-(?:rf|fr)\b', 95),
    ("force_delete_root", r'\brm\s+-(?:rf|fr)\s+/', 100),
    ("permission_wipe", r'\bchmod\s+777\b', 70),
    ("dd_write", r'\bdd\s+if=', 80),
    ("disk_wipe", r'(?:mkfs|fdisk|parted|dd\s+of=/dev/)', 100),
    ("shutdown", r'(?:shutdown|reboot|halt|poweroff)\b', 80),
]

# Data exfiltration patterns
INFOLEAK_PATTERNS: list[tuple[str, str, int]] = [
    ("send_to_external", r'(?:curl|wget|post|put|send)\s+.*(?:https?://\S+)\s*(?:-d|--data|--data-raw)', 80),
    ("env_var_exfil", r'(?:env|export|printenv|set)\s*(?:\||`).*(?:curl|wget|nc|netcat)', 75),
    ("file_upload", r'(?:curl|wget)\s+.*(?:-F|--form|-T|--upload-file)\s+.*https?://', 80),
    ("netcat_exfil", r'(?:nc|netcat)\s+-[a-z]*e?\s+\d+\.\d+\.\d+\.\d+', 85),
    ("dns_exfil", r'(?:dig|nslookup|host)\s+.*`.*\$\(', 70),
    ("token_in_url", r'(?:api[_-]?key|token|secret|password|credential)\s*=\s*["\']?\w+["\']?\s+(?:\||`).*(?:curl|wget)', 85),
]

# Social engineering patterns (from Koi Security analysis)
SOCIAL_ENGINEERING_PATTERNS: list[tuple[str, str, int]] = [
    ("dependency_install", r'(?:prerequisites?|dependenc|requirement|installation)\s*[:\n].*(?:brew|pip|npm|gem|cargo|apt|yum)\s+install', 65),
    ("password_protected_zip", r'(?:password[-_ ]?protected|password:)\s*.+\.(?:zip|rar|7z)', 85),
    ("click_here_download", r'(?:click\s+(?:here|this|link|button)|download\s+(?:from|here|now))\s*.+\.(?:zip|exe|dmg|pkg|bat|sh)', 80),
    ("run_as_root", r'(?:run\s+as\s+root|sudo\s+|chmod\s+\+[sx])', 65),
    ("deactivate_security", r'(?:deactivat|disabl|turn\s+off|bypass)\s+(?:security|sandbox|protect|gatekeeper|SIP)', 90),
]

# ── Scanner ────────────────────────────────────────────────────────────


class SkillScanner:
    """Scans a skill directory for security issues."""

    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir)
        self.findings: list[dict[str, Any]] = []
        self.severity_score: int = 0
        self.max_severity: int = 0

    def scan(self) -> dict[str, Any]:
        """Run all scanners and return results."""
        self.findings = []
        self.severity_score = 0
        self.max_severity = 0

        # Scan SKILL.md content
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            skill_md = self.skill_dir / "skill.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            self._scan_content(content, source="SKILL.md", is_instructions=True)

        # Scan scripts/
        scripts_dir = self.skill_dir / "scripts"
        if scripts_dir.exists():
            for script_file in sorted(scripts_dir.iterdir()):
                if script_file.is_file() and script_file.suffix in (".py", ".sh", ".js", ".rb", ".ps1", ".bat"):
                    content = script_file.read_text(encoding="utf-8", errors="replace")
                    self._scan_content(content, source=f"scripts/{script_file.name}", is_instructions=False)

        # Determine risk level
        if self.severity_score >= 80:
            risk = "critical"
        elif self.severity_score >= 50:
            risk = "high"
        elif self.severity_score >= 20:
            risk = "medium"
        elif self.severity_score > 0:
            risk = "low"
        else:
            risk = "safe"

        return {
            "status": "ok",
            "risk": risk,
            "severity_score": self.severity_score,
            "max_severity": self.max_severity,
            "finding_count": len(self.findings),
            "findings": sorted(self.findings, key=lambda f: f["severity"], reverse=True),
            "verdict": self._get_verdict(risk),
        }

    def _scan_content(self, content: str, source: str, is_instructions: bool) -> None:
        """Scan a single text content for all patterns."""
        content_lower = content.lower()

        # Run all pattern groups
        self._run_patterns(content, content_lower, source, "obfuscation", OBFUSCATION_PATTERNS)
        self._run_patterns(content, content_lower, source, "piped_download", PIPED_DOWNLOAD_PATTERNS)
        self._run_patterns(content, content_lower, source, "known_malware", KNOWN_MALWARE_PATTERNS)
        self._run_patterns(content, content_lower, source, "dangerous_shell", DANGEROUS_SHELL_PATTERNS)
        self._run_patterns(content, content_lower, source, "infoleak", INFOLEAK_PATTERNS)
        self._run_patterns(content, content_lower, source, "social_engineering", SOCIAL_ENGINEERING_PATTERNS)

        # Prompt injection — only relevant in instructions (SKILL.md), not scripts
        if is_instructions:
            self._run_patterns(content, content_lower, source, "prompt_injection", PROMPT_INJECTION_PATTERNS)

    def _run_patterns(
        self,
        content: str,
        content_lower: str,
        source: str,
        category: str,
        patterns: list[tuple[str, str, int]],
    ) -> None:
        """Run a set of regex patterns against content."""
        for pattern_id, pattern, severity in patterns:
            # Try case-sensitive first, then insensitive
            match = re.search(pattern, content) or re.search(pattern, content_lower, re.IGNORECASE)
            if match:
                # Extract context (50 chars around match)
                start = max(0, match.start() - 40)
                end = min(len(content), match.end() + 40)
                context = content[start:end].strip()
                # Truncate context for readability
                if len(context) > 120:
                    context = context[:60] + "..." + context[-60:]

                finding = {
                    "id": pattern_id,
                    "category": category,
                    "severity": severity,
                    "source": source,
                    "context": context,
                }
                self.findings.append(finding)
                self.severity_score += severity
                self.max_severity = max(self.max_severity, severity)

                logger.debug(
                    "SkillScanner [%s] %s in %s: %s",
                    severity, pattern_id, source, context[:80],
                )

    def _get_verdict(self, risk: str) -> str:
        """Generate a human-readable verdict."""
        if risk == "critical":
            return (
                "🚨 KRITISK: This skill contains confirmed malware patterns or "
                "extremely dangerous operations. DO NOT IMPORT."
            )
        elif risk == "high":
            return (
                "⚠️ HIGH RISK: This skill has significant security concerns "
                "(prompt injection, dangerous shell, or infoleak patterns). "
                "Manual review required before import."
            )
        elif risk == "medium":
            return (
                "⚠️ MEDIUM RISK: This skill has moderate security concerns. "
                "Review flagged items before importing."
            )
        elif risk == "low":
            return (
                "⚡ LOW RISK: Minor concerns detected. Likely safe but review "
                "findings if you want to be thorough."
            )
        else:
            return "✅ SAFE: No security issues detected."


# ── Convenience API ───────────────────────────────────────────────────


def scan_skill_directory(path: str | Path) -> dict[str, Any]:
    """Scan a skill directory (or a path containing SKILL.md) for security issues.

    Returns a dict with risk level, severity score, and list of findings.
    Use this BEFORE importing a skill.
    """
    p = Path(path)

    # If pointing to a file, use its parent
    if p.is_file() and p.name.upper() == "SKILL.MD":
        p = p.parent

    if not p.is_dir():
        return {"status": "error", "error": f"directory not found: {p}"}

    # Check if it looks like a skill directory
    skill_md = p / "SKILL.md"
    if not skill_md.exists():
        skill_md = p / "skill.md"
    if not skill_md.exists():
        return {"status": "error", "error": f"no SKILL.md found in {p}"}

    scanner = SkillScanner(p)
    return scanner.scan()


def scan_skill_content(content: str, name: str = "unknown") -> dict[str, Any]:
    """Scan raw SKILL.md content (before writing to disk).

    Useful for scanning skills from URLs before downloading fully.
    """
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="skill_scan_"))
    skill_dir = tmp / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    result = scan_skill_directory(skill_dir)

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    return result
