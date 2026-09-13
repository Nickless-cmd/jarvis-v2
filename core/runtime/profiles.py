"""De navngivne profiler — Fase 9 i DeepSeek-harness-spec'en.

Spec'en navngiver syv: `visible-owner`, `visible-member`, `jarvis-code`,
`autonomous`, `maintenance`, `research`, `safe-offline`.

De er DATA, ikke kode. Hver profil er et lag oven på `GRUND`, og komposition
sker i `profile_composer` — som håndhæver at et senere lag kun kan indsnævre
sikkerhed. Derfor kan en profil her ikke komme til at give mere end grunden
tillader; den kan kun tage.

## Hvorfor grunden er den mest tilladte

Fordi indsnævring er den eneste retning der findes. Var grunden stram, kunne
ingen profil åbne noget, og hver ny profil måtte redigere grunden — hvorved
grunden holdt op med at være en grænse. Grunden sætter loftet; profilerne
sætter deres eget lavere.

## Hvorfor `safe-offline` ikke bare er «nul til alt»

Den skal stadig kunne svare. Den har værktøjer slået fra og hverken
tvær-sessions-kontekst eller telemetri ud af huset — men revision kører, for
den kan ingen profil slå fra.
"""
from __future__ import annotations

from typing import Any

from core.runtime.profile_composer import EffektivProfil, komponer

#: Loftet. Alle profiler er lag OVEN PÅ denne, og kan kun indsnævre.
GRUND: dict[str, Any] = {
    "tool_scope": "all",
    "approval_mode": "never",
    "sandbox": "none",
    "cross_session_context": "full",
    "telemetry_sharing": "full",
    "retry": 3,
    "compaction": True,
    "memory": True,
    "private_layers": True,
    "subagents": True,
}

PROFILER: dict[str, dict[str, Any]] = {
    # Bjørn selv. Fuld rækkevidde; godkendelse kun hvor gaten kræver det.
    "visible-owner": {
        "approval_mode": "ask",
        "sandbox": "workspace",
    },
    # Et husstandsmedlem. Ser færre værktøjer og aldrig andres sessioner.
    "visible-member": {
        "tool_scope": "standard",
        "approval_mode": "ask",
        "sandbox": "workspace",
        "cross_session_context": "none",
        "private_layers": False,
    },
    # Kodefladen. Bredde i værktøjer, men ingen private lag — den arbejder i
    # repoet, ikke i hans indre liv.
    "jarvis-code": {
        "approval_mode": "ask",
        "sandbox": "workspace",
        "private_layers": False,
    },
    # Baggrundskørsler uden et menneske til stede. Derfor: ingen godkendelse
    # at vente på, og et strammere værktøjssæt.
    "autonomous": {
        "tool_scope": "standard",
        "approval_mode": "never",
        "sandbox": "workspace",
        "cross_session_context": "summary",
        "subagents": False,
    },
    # Vedligehold. Må røre systemet, men aldrig uden at blive spurgt.
    "maintenance": {
        "tool_scope": "limited",
        "approval_mode": "always",
        "sandbox": "workspace",
        "cross_session_context": "none",
        "private_layers": False,
        "subagents": False,
    },
    # Research-lanen. Mange kald, men læsende — og resultatet skal kunne
    # deles, så telemetrien renses.
    "research": {
        "tool_scope": "standard",
        "approval_mode": "ask",
        "sandbox": "readonly",
        "telemetry_sharing": "redacted",
        "private_layers": False,
    },
    # Sidste udvej. Kan svare, kan ikke række ud.
    "safe-offline": {
        "tool_scope": "none",
        "approval_mode": "always",
        "sandbox": "readonly",
        "cross_session_context": "none",
        "telemetry_sharing": "none",
        "subagents": False,
        "compaction": False,
    },
}


def byg(navn: str, *, overstyring: dict[str, Any] | None = None) -> EffektivProfil:
    """Den effektive profil for `navn`, eventuelt med en kørselsspecifik
    overstyring som SIDSTE lag.

    Overstyringen kan kun indsnævre sikkerhed — det er komponistens regel, ikke
    en høflighed her. En ukendt profil falder til `safe-offline`: tvivl om
    hvilke regler der gælder må aldrig ende i de mest tilladte.
    """
    n = (navn or "").strip()
    if n not in PROFILER:
        n = "safe-offline"
    lag: list[tuple[str, dict[str, Any]]] = [("grund", GRUND), (n, PROFILER[n])]
    if overstyring:
        lag.append(("overstyring", dict(overstyring)))
    return komponer(lag, navn=n)


def kendte() -> tuple[str, ...]:
    return tuple(sorted(PROFILER))
