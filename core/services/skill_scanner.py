"""Skill-scanning før lokal eksekvering (spec §19.8 / §15.3.2).

Skills der kører lokalt på brugerens maskine er en angrebsflade. Hver skill
verificeres FØR eksekvering for tre kategorier:

- **prompt_injection** — skjulte instruktioner der forsøger at kapre Jarvis
  (ignorér tidligere, du er nu, afslør system-prompt, skjult unicode, …)
- **malware** — farlige operationer (rm -rf /, curl|sh, reverse shells, eval på
  netværks-input, fork-bombs, crypto-miners, …)
- **boundary** — forsøg på at tilgå filer uden for workspace (~/.ssh, /etc/passwd,
  sti-traversal, absolutte system-stier)

Ren, stdlib-only mønster-scanner (ClamAV/sandboxing er separate lag, §15.3.1).
Returnerer et struktureret `ScanResult`; blokerer som standard ved `high`-fund.
Ingen eksekvering, ingen side-effekter — sikker at køre på upålideligt indhold.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class Finding:
    category: str   # prompt_injection | malware | boundary
    severity: str   # low | medium | high
    pattern: str    # kort navn på det matchede mønster
    detail: str     # uddrag/forklaring


@dataclass
class ScanResult:
    allowed: bool
    findings: list[Finding] = field(default_factory=list)

    @property
    def max_severity(self) -> str | None:
        if not self.findings:
            return None
        return max(self.findings, key=lambda f: _SEVERITY_ORDER[f.severity]).severity

    @property
    def blocked_reasons(self) -> list[str]:
        return [f"{f.category}/{f.pattern}: {f.detail}" for f in self.findings]

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "max_severity": self.max_severity,
            "findings": [
                {"category": f.category, "severity": f.severity,
                 "pattern": f.pattern, "detail": f.detail}
                for f in self.findings
            ],
        }


# (navn, regex, severity, kategori) — regex matches case-insensitivt mod indhold
_PROMPT_INJECTION: tuple[tuple[str, str, str], ...] = (
    ("ignore_previous", r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", "high"),
    ("disregard", r"disregard\s+(all\s+)?(previous|prior|above|your)\b", "high"),
    ("you_are_now", r"you\s+are\s+now\b|from\s+now\s+on\s+you\b|pretend\s+to\s+be\b", "medium"),
    ("reveal_system", r"(reveal|show|print|repeat|output)\s+(your\s+)?(system\s+prompt|initial\s+instructions|hidden\s+rules)", "high"),
    ("override_rules", r"(override|bypass|disable)\s+(your\s+)?(safety|guard|rules|restrictions|filter)", "high"),
    ("do_not_tell", r"do\s+not\s+(tell|inform|mention\s+to)\s+(the\s+)?(user|owner|bjørn)", "high"),
    ("new_persona", r"act\s+as\s+(an?\s+)?(unrestricted|jailbroken|dan|evil)\b", "high"),
    ("exfiltrate", r"(send|post|upload|exfiltrate)\s+(the\s+)?(secret|token|password|api[_\s-]?key|credentials)", "high"),
)

_MALWARE: tuple[tuple[str, str, str], ...] = (
    ("rm_rf_root", r"rm\s+-rf?\s+(--no-preserve-root\s+)?/(['\"\s)]|\*|etc|root|home|var|usr|bin|boot|$)", "high"),
    ("curl_pipe_sh", r"(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba)?sh\b", "high"),
    ("reverse_shell", r"(bash\s+-i\s+>&\s*/dev/tcp|nc\s+-e\b|/dev/tcp/\d|socket\.socket\([^\n]*SOCK_STREAM[^\n]*connect)", "high"),
    ("eval_exec", r"\b(eval|exec)\s*\(\s*(request|input|response|payload|data|os\.environ|urlopen)", "high"),
    ("dangerous_import", r"__import__\s*\(\s*['\"](os|subprocess|socket|ctypes)['\"]", "medium"),
    ("shell_true_rm", r"subprocess\.\w+\([^\n]*shell\s*=\s*True[^\n]*\brm\b", "high"),
    ("fork_bomb", r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "high"),
    ("crypto_miner", r"\b(xmrig|minerd|stratum\+tcp|coinhive)\b", "high"),
    ("chmod_x_tmp", r"chmod\s+\+x\s+/tmp/", "medium"),
    ("base64_decode_exec", r"base64\s+(-d|--decode)[^\n|]*\|\s*(ba)?sh", "high"),
)

_BOUNDARY: tuple[tuple[str, str, str], ...] = (
    ("ssh_keys", r"~?/\.ssh/|id_rsa\b|authorized_keys\b", "high"),
    ("etc_passwd_shadow", r"/etc/(passwd|shadow|sudoers)\b", "high"),
    ("path_traversal", r"(\.\./){2,}", "medium"),
    ("absolute_system_path", r"\b(/root/|/etc/|/var/lib/|/boot/|/sys/)", "medium"),
    ("aws_credentials", r"~?/\.aws/credentials|AWS_SECRET_ACCESS_KEY", "high"),
    ("runtime_secrets", r"\.jarvis-v2/config/runtime\.json|encryption_kek\b", "high"),
)

_CATEGORY_PATTERNS = (
    ("prompt_injection", _PROMPT_INJECTION),
    ("malware", _MALWARE),
    ("boundary", _BOUNDARY),
)


def _normalize(content: str) -> str:
    """Fold skjult/forvirrende unicode til NFKC så injection ikke gemmer sig i
    homoglyffer/zero-width-tegn."""
    text = unicodedata.normalize("NFKC", content or "")
    # Fjern zero-width + andre formaterings-tegn der bruges til at skjule tekst.
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def _has_hidden_format_chars(content: str) -> bool:
    return any(unicodedata.category(ch) == "Cf" for ch in (content or ""))


def scan_skill(content: str, *, path: str | None = None,
               block_severity: str = "high") -> ScanResult:
    """Scan en skill-definition (tekst/kode) for injection/malware/boundary.

    Blokerer hvis et fund har severity >= block_severity (default "high").
    Ren funktion — eksekverer aldrig indholdet.
    """
    raw = content or ""
    normalized = _normalize(raw)
    findings: list[Finding] = []

    # Skjulte format-tegn er i sig selv mistænkeligt (typisk injection-skjul).
    if _has_hidden_format_chars(raw):
        findings.append(Finding(
            "prompt_injection", "medium", "hidden_unicode",
            "indeholder skjulte format-tegn (zero-width/bidi)",
        ))

    for category, patterns in _CATEGORY_PATTERNS:
        for name, regex, severity in patterns:
            m = re.search(regex, normalized, re.IGNORECASE)
            if m:
                excerpt = m.group(0)[:80]
                findings.append(Finding(category, severity, name, excerpt))

    threshold = _SEVERITY_ORDER.get(block_severity, 2)
    blocked = any(_SEVERITY_ORDER[f.severity] >= threshold for f in findings)
    return ScanResult(allowed=not blocked, findings=findings)
