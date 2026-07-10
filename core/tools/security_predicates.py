"""Nummererede security-predikater (spec E, 2026-07-10).

Struktureret, navngivet registry af tool-sikkerheds-checks — så et deny logges som
"check #14: dd-disk-write" i stedet for bare "blocked". Ingen NY sikkerhedspolitik:
predikaterne er seedet 1:1 fra de eksisterende block/destructive-patterns i
simple_tools.py. Additivt observability-lag; beslutningerne er uændrede.
"""
from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SecurityPredicate:
    id: int
    name: str
    kind: str        # "bash" | "write"
    decision: str    # "blocked" | "destructive"
    pattern: str     # regex (bash) eller substring (write)
    why: str


# Bash-predikater. blocked = hård afvisning; destructive = kræver approval.
# Rækkefølge = evalueringsrækkefølge (blocked før destructive, jf. classify_command).
BASH_PREDICATES: tuple[SecurityPredicate, ...] = (
    SecurityPredicate(1, "curl-pipe-bash", "bash", "blocked", r"\bcurl\b.*\|\s*bash", "Fjern-kode hentet og eksekveret direkte"),
    SecurityPredicate(2, "wget-pipe-bash", "bash", "blocked", r"\bwget\b.*\|\s*bash", "Fjern-kode hentet og eksekveret direkte"),
    SecurityPredicate(3, "sudo-rm", "bash", "blocked", r"\bsudo\s+rm\b", "Privilegeret sletning"),
    SecurityPredicate(4, "rm", "bash", "destructive", r"\brm\b", "Filsletning"),
    SecurityPredicate(5, "rm-rf", "bash", "destructive", r"\brm\s+-rf\b", "Rekursiv tvungen sletning"),
    SecurityPredicate(6, "git-reset-hard", "bash", "destructive", r"git\s+reset\s+--hard", "Kasserer ucommittede ændringer"),
    SecurityPredicate(7, "git-clean", "bash", "destructive", r"git\s+clean", "Sletter untracked filer"),
    SecurityPredicate(8, "git-push-force", "bash", "destructive", r"git\s+push\s+--force", "Overskriver remote-historik"),
    SecurityPredicate(9, "git-push-f", "bash", "destructive", r"git\s+push\s+-f\b", "Overskriver remote-historik"),
    SecurityPredicate(10, "drop-table", "bash", "destructive", r"\bdrop\s+table\b", "Sletter database-tabel"),
    SecurityPredicate(11, "drop-database", "bash", "destructive", r"\bdrop\s+database\b", "Sletter hel database"),
    SecurityPredicate(12, "truncate", "bash", "destructive", r"\btruncate\b", "Tømmer tabel/fil"),
    SecurityPredicate(13, "mkfs", "bash", "destructive", r"mkfs\b", "Formaterer filsystem"),
    SecurityPredicate(14, "dd-disk-write", "bash", "destructive", r"dd\s+if=", "Rå disk-skrivning"),
    SecurityPredicate(15, "fork-bomb", "bash", "destructive", r":\(\)\{ :\|:& \};:", "Fork-bomb (resurs-udmattelse)"),
    SecurityPredicate(16, "shutdown", "bash", "destructive", r"\bshutdown\b", "Lukker maskinen ned"),
    SecurityPredicate(17, "reboot", "bash", "destructive", r"\breboot\b", "Genstarter maskinen"),
    SecurityPredicate(18, "poweroff", "bash", "destructive", r"\bpoweroff\b", "Slukker maskinen"),
)

# Write-predikater (substring på resolved path). Alle blocked.
WRITE_PREDICATES: tuple[SecurityPredicate, ...] = (
    SecurityPredicate(19, "git-internal", "write", "blocked", "/.git/", "Skriv i git-interne data"),
    SecurityPredicate(20, "env-file", "write", "blocked", "/.env", "Skriv i miljø-/secret-fil"),
    SecurityPredicate(21, "credentials", "write", "blocked", "/credentials", "Skriv i credential-fil"),
    SecurityPredicate(22, "ssh-keys", "write", "blocked", "/.ssh/", "Skriv i SSH-nøgler"),
    SecurityPredicate(23, "node-modules", "write", "blocked", "/node_modules/", "Skriv i dependency-mappe"),
    SecurityPredicate(24, "pycache", "write", "blocked", "/__pycache__/", "Skriv i bytecode-cache"),
)


def evaluate_command(command: str) -> dict | None:
    """Første matchende bash-predikat (blocked før destructive) på den normaliserede
    kommando, ellers None. Returnerer {id, name, decision, why}."""
    normalized = str(command or "").strip().lower()
    if not normalized:
        return None
    for want in ("blocked", "destructive"):
        for p in BASH_PREDICATES:
            if p.decision != want:
                continue
            try:
                if re.search(p.pattern, normalized):
                    return {"id": p.id, "name": p.name, "decision": p.decision, "why": p.why}
            except re.error:
                continue
    return None


def evaluate_write(resolved_path: str) -> dict | None:
    """Første matchende write-predikat (substring) på stien, ellers None."""
    path = str(resolved_path or "")
    if not path:
        return None
    for p in WRITE_PREDICATES:
        if p.pattern in path:
            return {"id": p.id, "name": p.name, "decision": p.decision, "why": p.why}
    return None


def all_predicates() -> tuple[SecurityPredicate, ...]:
    return BASH_PREDICATES + WRITE_PREDICATES


def build_security_predicates_surface() -> dict:
    """Central-CLI read-surface: jc raw /central/security-predicates."""
    preds = all_predicates()
    return {
        "active": True,
        "mode": "security-predicates",
        "summary": {"count": len(preds)},
        "items": [
            {"id": p.id, "name": p.name, "kind": p.kind, "decision": p.decision, "why": p.why}
            for p in preds
        ],
    }


def render_predicates_md() -> str:
    """Genererer docs/security_predicates.md fra registry'en (kilde = koden)."""
    lines = [
        "# Security Predicates",
        "",
        "> Auto-genereret fra `core/tools/security_predicates.py`. Rediger IKKE i hånden — ret registry'en.",
        "",
        "Nummererede tool-sikkerheds-checks. Et deny logges med sit check-id (fx \"check #14: dd-disk-write\").",
        "",
        "| # | Navn | Type | Beslutning | Hvorfor |",
        "|---|------|------|-----------|---------|",
    ]
    for p in all_predicates():
        lines.append(f"| {p.id} | `{p.name}` | {p.kind} | {p.decision} | {p.why} |")
    lines.append("")
    return "\n".join(lines)
