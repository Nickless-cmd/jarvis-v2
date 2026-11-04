"""Hvorfor fejlede dispatchen? Exit-koden kan ikke svare.

Målt 4/11-2026 på to ægte kald:

    dødt token      → stderr «401 OAuth access token is invalid»      exit 1
    opbrugt kvote   → stdout «You've hit your 5-hour limit · resets 11:30pm»  exit 1

Samme exit-kode, vidt forskellige konsekvenser. Det ene kræver et nyt token
fra et menneske; det andet går over af sig selv om få timer, og arbejdet er
ikke tabt. Behandles de ens, bliver en ventetid til en fejlretning — og
næste gang nogen ser «exit 1» ved de ikke om de skal åbne Claude Code eller
bare vente.

Derfor bærer klassifikationen sin egen handlingsanvisning. En kode der kun
siger «error» tvinger læseren til at gætte, og et gæt på årsagen er dyrere
end ingen klassifikation.

`claude auth status` er IKKE en probe: den svarede `loggedIn: true` på et
token der havde været dødt siden 20. maj. Kun den faktiske fejltekst kan
skelne.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TOKEN_DEAD = "token_dead"
QUOTA_EXHAUSTED = "quota_exhausted"
OTHER = "other"
NONE = "none"

# De målte strenge står først; de øvrige er variationer set i praksis.
_TOKEN_PATTERNS = (
    r"401\s+oauth access token is invalid",
    r"oauth access token is invalid",
    r"oauth token (?:has )?expired",
    r"invalid_grant",
    r"401\s+unauthorized",
    r"authentication_error",
    r"please run /login",
    r"api key is invalid",
)

# «limit» alene er for bredt — en hvilken som helst besked om en grænse ville
# matche. Vi kræver en af de former der faktisk betyder «kvoten er brugt op».
_QUOTA_PATTERNS = (
    r"you'?ve hit your (?:[a-z0-9-]+ )*limit",
    r"usage limit (?:reached|exceeded)",
    r"rate limit (?:reached|exceeded)",
    r"hit your (?:5-hour|weekly|daily) limit",
    r"quota (?:exceeded|exhausted)",
    r"credit balance is too low",
)

_RESET_HINT = re.compile(
    r"resets?\s+(?:at\s+)?([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?)",
    re.IGNORECASE,
)

_TOKEN_ACTION = (
    "Tokenet er dødt — det er ikke kvoten. Forny CLAUDE_CODE_OAUTH_TOKEN i "
    "~/.jarvis-v2/config/claude_dispatch.env (åbn Claude Code på CheifOne og "
    "kopiér det friske token), og genstart jarvis-api. Brug IKKE "
    "`claude auth status` som kontrol: den svarer loggedIn:true på et dødt token."
)

_QUOTA_ACTION = (
    "Kvoten er opbrugt. Den går over af sig selv — kør ikke igen før reset. "
    "Arbejdet er ikke tabt; worktreet og auditen står stadig."
)

_OTHER_ACTION = (
    "Ukendt fejl. Læs stdout/stderr i claude_dispatch_audit for denne task_id "
    "før du prøver igen — et nyt forsøg uden årsagen gentager den."
)


@dataclass(frozen=True)
class DispatchFailure:
    kind: str
    detail: str = ""
    action: str = ""
    reset_hint: str = ""

    @property
    def is_failure(self) -> bool:
        return self.kind not in (NONE,)

    @property
    def needs_human(self) -> bool:
        """Kvote gør ikke. Et dødt token gør — der skal et nyt token til."""
        return self.kind in (TOKEN_DEAD, OTHER)


def _first_match(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def classify_dispatch_failure(
    stdout: str = "", stderr: str = "", exit_code: int | None = 0,
) -> DispatchFailure:
    """Klassificér en afsluttet dispatch.

    En grøn kørsel er aldrig en fejl, uanset hvad der står i teksten: en
    vellykket opgave kan sagtens *omtale* en kvote-grænse i sit svar, og en
    klassifikation der læser svaret som en fejl ville være værre end ingen.
    """
    if exit_code == 0:
        return DispatchFailure(kind=NONE)

    haystack = f"{stdout}\n{stderr}"

    # Token først: et dødt token kan slet ikke rapportere om kvote, så når
    # teksten nævner 401/invalid er det årsagen — også selv om ordet «limit»
    # skulle optræde i samme besked.
    token_hit = _first_match(haystack, _TOKEN_PATTERNS)
    if token_hit:
        return DispatchFailure(
            kind=TOKEN_DEAD, detail=token_hit, action=_TOKEN_ACTION,
        )

    quota_hit = _first_match(haystack, _QUOTA_PATTERNS)
    if quota_hit:
        hint = ""
        match = _RESET_HINT.search(haystack)
        if match:
            hint = match.group(1).strip()
        action = _QUOTA_ACTION
        if hint:
            action = f"Kvoten er opbrugt — reset {hint}. " + _QUOTA_ACTION
        return DispatchFailure(
            kind=QUOTA_EXHAUSTED, detail=quota_hit, action=action,
            reset_hint=hint,
        )

    detail = ""
    for text in (stderr, stdout):
        stripped = text.strip()
        if stripped:
            detail = stripped.splitlines()[-1][:300]
            break
    return DispatchFailure(kind=OTHER, detail=detail, action=_OTHER_ACTION)
