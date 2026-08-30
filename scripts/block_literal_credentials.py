#!/usr/bin/env python3
"""Blokér credential-lignende NAVNE der får en literal streng-VÆRDI.

Hvorfor denne findes ud over detect-secrets
-------------------------------------------
Et kort mail-kodeord (8 tegn, kun små bogstaver og tal) blev engang skrevet
direkte i en modulkonstant her i repoet. detect-secrets fangede det ALDRIG:
så kort en værdi har for lav entropi til entropi-detektorerne, og den har
intet `sk-`/`ghp_`-præfiks at matche på. Kontoen blev senere misbrugt af
tredjepart. Det er samme fejlklasse som `block_jvs_keys.sh` blev lavet til:
**korte hemmeligheder er usynlige for entropi-heuristikker.**

Derfor kigger denne hook ikke på værdiens form, men på **navnet**: hedder
variablen noget med pass/token/secret/api_key, må den ikke tildeles en literal
streng. Den skal læses fra runtime.json via
`core.runtime.secrets.read_runtime_key()` — se CLAUDE.md.

Undtagelser: `# noqa: literal-credential` på linjen, eller repoets eksisterende
`# pragma: allowlist secret`.
"""

from __future__ import annotations

import re
import sys

# --- navne-analyse ---------------------------------------------------------
# Ordet i identifikatoren afgør — ikke værdiens entropi. `MAIL_PASS` skal
# fanges, `bypass_cache` skal ikke. Derfor splittes navnet i led.
_UNAMBIGUOUS = {
    "passwd", "password", "passphrase", "secret", "token",
    "apikey", "credential", "credentials",
}
# Kan ogsaa betyde noget uskyldigt (en "pass" = en runde) — kraever sidsteplads.
_AMBIGUOUS = {"pass", "pwd"}
# `key` alene er for bredt (sort_key, cache_key). Kræver et af disse led med.
_KEY_QUALIFIERS = {"api", "access", "private", "secret", "signing", "encryption", "kek", "master"}

# Et af disse led ANYWHERE i navnet betyder "det her er en adresse/et navn
# paa noget" — ikke hemmeligheden selv. `_TOKEN_ENV_KEY` er navnet paa en
# miljoevariabel, ikke en token.
_DESCRIPTOR_TOKENS = {"env", "url", "uri", "header", "endpoint"}

# Navne der beskriver hvor/hvad — ikke selve hemmeligheden.
_NAME_SUFFIX_OK = (
    "url", "uri", "header", "name", "field", "path", "file", "env", "issuer",
    "algo", "prefix", "suffix", "pattern", "regex", "template", "scheme", "type",
)

_IDENT = r"[A-Za-z_][A-Za-z0-9_.-]*"
# MAIL_PASS = "..."   password: '...'   "api_key": "..."
# Bart navn:      MAIL_PASS = "..."      password: '...'
_ASSIGN_BARE = re.compile(rf"(?<![\w'\"])({_IDENT})\s*[:=]\s*(['\"])(?P<val>[^'\"\n]*)\2")
# Citeret nøgle:  "api_key": "..."   (JSON/dict — kræver ENS citationstegn om navnet)
_ASSIGN_QUOTED = re.compile(rf"(['\"])({_IDENT})\1\s*:\s*(['\"])(?P<val>[^'\"\n]*)\3")

_PLACEHOLDER = re.compile(
    r"^(?:|x+|\.\.\.|none|null|true|false|changeme|change_me|placeholder|redacted|"
    r"your[-_ ]?\w*|example\w*|dummy\w*|fake\w*|sample\w*|test\w*|foo|bar|baz|"
    r"secret|password|token|hunter2|\*+|<[^>]*>|\[[^\]]*\]|\{\{?[^}]*\}?\}|"
    r"\$\{?[A-Z_]+\}?|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$",
    re.IGNORECASE,
)
_URLISH = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|/|\./|~/|[A-Z][a-z]+-[A-Z])", re.IGNORECASE)
_NOT_LITERAL = re.compile(
    r"(os\.environ|getenv|read_runtime_key|process\.env|\$\{|%s|\{\}|\{[a-z_]+\})", re.IGNORECASE
)

_SKIP_PATH = re.compile(
    r"(^|/)(\.git|node_modules|dist|build|\.venv|__pycache__)(/|$)"
    r"|(^|/)(\.secrets\.baseline|package-lock\.json|yarn\.lock|pnpm-lock\.yaml"
    r"|poetry\.lock|Cargo\.lock)$"
    # Testfixtures og design-dokumenter er fyldt med illustrative attrap-
    # credentials ("tok123", "rigtig"). De er ikke driftskonfiguration.
    # detect-secrets dækker stadig høj-entropi-værdier begge steder.
    r"|(^|/)tests?/"
    r"|^docs/superpowers/"
    r"|\.(lock|min\.js|map|png|jpg|jpeg|gif|ico|woff2?|ttf|pdf|mp4)$",
    re.IGNORECASE,
)

_EXEMPT_MARKS = ("noqa: literal-credential", "pragma: allowlist secret")
_SELF = "scripts/block_literal_credentials.py"
_MIN_LEN = 4


def _tokens(name: str) -> list[str]:
    """Split MAIL_PASS / mailPass / mail-pass / mail.pass -> ['mail', 'pass']."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return [t for t in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if t]


def _is_credential_name(name: str) -> bool:
    toks = _tokens(name)
    if not toks:
        return False
    if toks[-1] in _NAME_SUFFIX_OK:
        return False
    if any(t in _DESCRIPTOR_TOKENS for t in toks):
        return False
    if any(t in _UNAMBIGUOUS for t in toks):
        return True
    # Tvetydige led skal staa sidst: MAIL_PASS ja, provider_first_pass_status nej.
    if toks[-1] in _AMBIGUOUS:
        return True
    return toks[-1] == "key" and any(t in _KEY_QUALIFIERS for t in toks)


def _suspicious(line: str) -> tuple[str, str] | None:
    if any(mark in line for mark in _EXEMPT_MARKS):
        return None
    for pattern, grp in ((_ASSIGN_BARE, 1), (_ASSIGN_QUOTED, 2)):
        for m in pattern.finditer(line):
            name, val = m.group(grp), m.group("val")
            if not _is_credential_name(name):
                continue
            if len(val) < _MIN_LEN:
                continue
            if _PLACEHOLDER.match(val) or _URLISH.match(val) or _NOT_LITERAL.search(val):
                continue
            return name, val
    return None


def check(paths: list[str]) -> int:
    findings: list[tuple[str, int, str, int]] = []
    for path in paths:
        if _SKIP_PATH.search(path) or path.endswith(_SELF):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except (OSError, IsADirectoryError):
            continue
        for n, line in enumerate(lines, 1):
            hit = _suspicious(line)
            if hit:
                name, val = hit
                # vis ALDRIG værdien — kun navnet og hvor lang literalen er
                findings.append((path, n, name, len(val)))

    if not findings:
        return 0

    print("BLOKERET: credential-navn tildelt en literal streng\n", file=sys.stderr)
    for path, n, name, ln in findings:
        print(f"  {path}:{n}  {name} = <literal på {ln} tegn>", file=sys.stderr)
    print(
        "\nHemmeligheder må ikke stå i koden — heller ikke korte, og heller ikke"
        "\n'midlertidigt'. Præcis sådan en linje har før kostet os en kapret"
        "\nmailkonto. Kort betyder ikke ufarligt."
        "\n\nLæs den i stedet fra runtime.json:"
        "\n    from core.runtime.secrets import read_runtime_key"
        '\n    pw = read_runtime_key("mail_password")'
        "\n\nEr det en falsk positiv, så skriv  # noqa: literal-credential  på linjen.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(check(sys.argv[1:]))
