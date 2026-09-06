"""To akser: hvad et kald MÅ røre, og hvornår et menneske skal spørges.

Porteret fra jarvis-code 2026-09-06 (`permissions.py`).

Runtime har `runtime_action_registry` og godkendelser, men de to spørgsmål
har været sammenfiltrede: godkendelses-tilstanden afgjorde både «må det her
skrive» og «skal jeg spørge først». Det gør en kombination umulig at udtrykke
— for eksempel «læs-kun, men med netværk», eller «må skrive, spørg ikke».

Her er de skilt ad:

  **Profil** (evne/indespærring) — hvad kaldet overhovedet må røre.
  **Tilstand** (timing) — hvornår Bjørn skal bekræfte det.

`resolve_effective` er det ENESTE sted de to forenes. Andre steder må ikke
udlede det samme igen; to steder der regner sig frem til en tilladelse er
per definition to sandheder.

VIGTIGT: modulet slækker ikke på de ubetingede værn — farlige kommandoer,
secret-stier, egress-klassifikation. De fyrer i ALLE tilstande, også
`bypass`, og lever et andet sted. Det her er aksen der ligger VED SIDEN AF
dem, aldrig i stedet for.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class SandboxProfile(str, Enum):
    """Evne-aksen. Uafhængig af hvornår der spørges."""

    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    RESTRICTED = "restricted"


# Timing-aksen. `plan` er et hårdt læse-kun-gulv, ikke et forslag.
APPROVAL_MODES = ("plan", "ask", "auto-edit", "full-auto", "bypass")

_DEFAULT_PROFIL = SandboxProfile.WORKSPACE_WRITE
_DEFAULT_MODE = "ask"


def _som_profil(profile: SandboxProfile | str) -> SandboxProfile:
    if isinstance(profile, SandboxProfile):
        return profile
    try:
        return SandboxProfile(str(profile).strip().lower())
    except ValueError:
        return _DEFAULT_PROFIL


def resolve_effective(profile: SandboxProfile | str, mode: str) -> dict[str, Any]:
    """Foren de to akser til én beslutning.

    - `allow_write`   — må kaldet skrive overhovedet
    - `allow_egress`  — må det nå nettet
    - `confine_paths` — skal stier holde sig inden for arbejdsmappen
    - `must_prompt`   — skal et menneske bekræfte før det kører

    `plan` tvinger læse-kun uanset profil. Det er et gulv: en tilstand der
    hedder «plan» og alligevel kan skrive er værre end ingen tilstand.
    """
    p = _som_profil(profile)
    m = mode if mode in APPROVAL_MODES else _DEFAULT_MODE

    profil_maa_skrive = p is not SandboxProfile.READ_ONLY
    profil_maa_ud = p is SandboxProfile.WORKSPACE_WRITE
    profil_indespaerrer = p is SandboxProfile.RESTRICTED

    allow_write = profil_maa_skrive and m != "plan"
    allow_egress = profil_maa_ud and m != "plan"
    # Der spoerges kun naar der er noget at spoerge OM. En prompt for et kald
    # der alligevel ikke maa skrive er stoej der laerer ham at klikke ja.
    must_prompt = m in ("ask", "auto-edit") and allow_write

    return {
        "allow_write": allow_write,
        "allow_egress": allow_egress,
        "confine_paths": profil_indespaerrer,
        "must_prompt": must_prompt,
        "profil": p.value,
        "tilstand": m,
    }


def format_axes(profile: SandboxProfile | str, mode: str) -> str:
    """«profil · tilstand» — begge akser synlige, aldrig kun den ene."""
    return f"{_som_profil(profile).value} · {mode if mode in APPROVAL_MODES else _DEFAULT_MODE}"


def sandbox_kwargs(profile: SandboxProfile | str, mode: str) -> dict[str, Any]:
    """Oversæt akserne til `bash_sandbox.maybe_wrap`-argumenter.

    Det er her de to lag møder hinanden: profilen siger om kaldet må nå
    nettet, og sandboxen kan håndhæve det på OS-niveau i stedet for kun at
    klassificere det med et regex.
    """
    besl = resolve_effective(profile, mode)
    return {"allow_egress": bool(besl["allow_egress"])}
