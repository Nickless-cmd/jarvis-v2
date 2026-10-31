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
    # Se `evaluate_command`: quoted indhold er en OMTALE af kommandoen, ikke
    # kommandoen — medmindre kommandoen selv fortolker det som kode.
    quote_aware: bool = False


# Bash-predikater. blocked = hård afvisning; destructive = kræver approval.
# Rækkefølge = evalueringsrækkefølge (blocked før destructive, jf. classify_command).
BASH_PREDICATES: tuple[SecurityPredicate, ...] = (
    SecurityPredicate(1, "curl-pipe-bash", "bash", "blocked", r"\bcurl\b.*\|\s*bash", "Fjern-kode hentet og eksekveret direkte"),
    SecurityPredicate(2, "wget-pipe-bash", "bash", "blocked", r"\bwget\b.*\|\s*bash", "Fjern-kode hentet og eksekveret direkte"),
    # 31/10-2026: de tre rm-predikater er `quote_aware`. Målt samme dag:
    # `classify_command('grep -c "rm" /tmp/x')` var `destructive` — en ren
    # læsning der blot NÆVNER rm blev gated som filsletning. Mønstret matchede
    # et STED i strengen, ikke kommandoen (samme fejlform som `;`-kæden 26/10).
    SecurityPredicate(3, "sudo-rm", "bash", "blocked", r"\bsudo\s+rm\b", "Privilegeret sletning", quote_aware=True),
    SecurityPredicate(4, "rm", "bash", "destructive", r"\brm\b", "Filsletning", quote_aware=True),
    SecurityPredicate(5, "rm-rf", "bash", "destructive", r"\brm\s+-rf\b", "Rekursiv tvungen sletning", quote_aware=True),
    SecurityPredicate(6, "git-reset-hard", "bash", "destructive", r"git\s+reset\s+--hard", "Kasserer ucommittede ændringer"),
    SecurityPredicate(7, "git-clean", "bash", "destructive", r"git\s+clean", "Sletter untracked filer"),
    SecurityPredicate(8, "git-push-force", "bash", "destructive", r"git\s+push\s+--force", "Overskriver remote-historik"),
    SecurityPredicate(9, "git-push-f", "bash", "destructive", r"git\s+push\s+-f\b", "Overskriver remote-historik"),
    SecurityPredicate(10, "drop-table", "bash", "destructive", r"\bdrop\s+table\b", "Sletter database-tabel", quote_aware=True),
    SecurityPredicate(11, "drop-database", "bash", "destructive", r"\bdrop\s+database\b", "Sletter hel database", quote_aware=True),
    SecurityPredicate(12, "truncate", "bash", "destructive", r"\btruncate\b", "Tømmer tabel/fil", quote_aware=True),
    SecurityPredicate(13, "mkfs", "bash", "destructive", r"mkfs\b", "Formaterer filsystem", quote_aware=True),
    SecurityPredicate(14, "dd-disk-write", "bash", "destructive", r"dd\s+if=", "Rå disk-skrivning"),
    SecurityPredicate(15, "fork-bomb", "bash", "destructive", r":\(\)\{ :\|:& \};:", "Fork-bomb (resurs-udmattelse)"),
    SecurityPredicate(16, "shutdown", "bash", "destructive", r"\bshutdown\b", "Lukker maskinen ned", quote_aware=True),
    SecurityPredicate(17, "reboot", "bash", "destructive", r"\breboot\b", "Genstarter maskinen", quote_aware=True),
    SecurityPredicate(18, "poweroff", "bash", "destructive", r"\bpoweroff\b", "Slukker maskinen", quote_aware=True),
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


#: Fortolker kommandoen quoted indhold som KODE? (31/10-2026)
#:
#: `grep -c "rm" fil` gør ikke — quoted er et mønster, og rm-predikaterne må
#: ikke se det. Men `bash -c "rm -rf /"` gør — der ER quoted indhold et
#: program. Uden denne gren ville quote-fixet åbne en dør: den mest direkte
#: måde at skrive en sletning på ville slippe gennem som en ren læsning.
#:
#: `| bash` tælles med: `echo "rm -rf /" | bash` eksekverer teksten.
_SHELL_FORTOLKER_KODE = re.compile(
    r"\b(?:bash|sh|zsh|dash|ksh|fish)\b[^|;&]*\s(?:-c|--command)\b"
    r"|\beval\b"
    r"|\|\s*(?:bash|sh|zsh|dash|ksh|fish)\b"
    # 31/10-2026: database- og fjern-klienter eksekverer quoted indhold som
    # KODE. `psql -c "drop table users"` ER en sletning. Uden denne gren ville
    # `quote_aware` på drop-table-predikatet gøre den til en ren læsning — et
    # hul åbnet af præcis det fix der skulle lukke et andet.
    r"|\b(?:psql|mysql|mariadb|sqlite3)\b[^|;&]*\s(?:-c|-e)\b"
    r"|\bssh\b[^|;&]*\s"
    r"|\b(?:docker|podman|kubectl)\s+exec\b"
)

#: Separatorer der gør kommandoen til MERE end ét segment — eller indlejret
#: kode. Er en af dem til stede, er kommandoen ikke «én ren læsning», og så
#: matcher predikaterne bredt igen. `&` tælles med som baggrunds-separator.
_FLERE_SEGMENTER = re.compile(r"\|\||&&|[;|&\n`]|\$\(|\(")


def _er_ren_laesning(command: str) -> bool:
    """Er HELE kommandoen ét rent læse-segment?

    Målt 31/10-2026: 9 af 26 kommandoer blev gated som det de NÆVNTE, ikke det
    de GJORDE — `grep -i shutdown /var/log/syslog` blev `destructive`.

    Indsnævringen kan ikke være en positions-regel (opgavens første forslag):
    `systemctl reboot`, `ssh host reboot` og `xargs rm` har alle ordet som
    ARGUMENT, så en positions-regel ville gøre dem til rene læsninger — fire
    huller i en SECURITY-gate. Det der skiller dem fra `grep -i shutdown` er
    PROGRAMMET: `grep` fortolker ikke sine argumenter, `systemctl` gør.

    Derfor genbruges husets egen læser-regel (`_segment_er_laesende`), som
    allerede er fail-closed: ukendt program, skrivende redirect, `-exec` og
    programmer som `sed`/`awk`/`xargs`/`sudo` giver False.
    """
    try:
        from core.tools.simple_tools import _segment_er_laesende
    except Exception:
        return False  # kan reglen ikke læses, matcher vi bredt: fail-closed
    if _FLERE_SEGMENTER.search(command):
        return False
    return _segment_er_laesende(command)


def evaluate_command(command: str) -> dict | None:
    """Første matchende bash-predikat (blocked før destructive) på den normaliserede
    kommando, ellers None. Returnerer {id, name, decision, why}.

    ``quote_aware``-predikater matcher på kommandoen UDEN for quoted strenge.
    Se `_SHELL_FORTOLKER_KODE` for hvornår quoted indhold alligevel tælles med.
    """
    normalized = str(command or "").strip().lower()
    if not normalized:
        return None

    # Quoted indhold er en OMTALE — medmindre kommandoen fortolker det som kode.
    # Kan hjælperen ikke importeres, falder vi tilbage til den RAA streng: flere
    # godkendelses-kort er billigere end et hul i en SECURITY-gate.
    try:
        from core.tools.simple_tools import _uden_for_quotes
        uden_quotes = _uden_for_quotes(normalized)
    except Exception:
        uden_quotes = normalized
    kode_i_quotes = bool(_SHELL_FORTOLKER_KODE.search(normalized))

    # 31/10-2026: er HELE kommandoen ét rent læse-segment, er hvert ord i den
    # en OMTALE — `grep -i shutdown /var/log/syslog` lukker ikke maskinen.
    # Se `_er_ren_laesning` for hvorfor indsnævringen ikke kan være en
    # positions-regel. Er svaret «ikke en ren læsning», matcher vi bredt som
    # før: fail-closed, og det er den gren de 17 kontrakt-tilfælde ligger i.
    if not kode_i_quotes and _er_ren_laesning(uden_quotes):
        return None

    for want in ("blocked", "destructive"):
        for p in BASH_PREDICATES:
            if p.decision != want:
                continue
            tekst = normalized if (not p.quote_aware or kode_i_quotes) else uden_quotes
            try:
                if re.search(p.pattern, tekst):
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
