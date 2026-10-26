"""Value objects shared by the Routine domain.

Definitions intentionally contain no session identifier.  A session execution is
authorized by the routine owner and resolves a freshly owner-verified session at
dispatch time; a stale chat id is never an authority token.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class RoutineStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ARCHIVED = "archived"
    DELETED = "deleted"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class AccessScope(StrEnum):
    USER_PRIVATE = "user_private"
    SYSTEM_OWNER = "system_owner"


class RoutineExecutionMode(StrEnum):
    """Hvor en rutine UDFØRES — valgt ved oprettelsen, ikke gættet bagefter.

    Bjørn 19/10-2026: «når en rutine oprettes skal man vælge om den skal udføre
    i baggrunden og rapportere til inbox eller om rutines udføres af dig hvor
    brugeren sidst var aktiv». Det er to forskellige livscyklusser, ikke en
    indstilling: den ene kører uden vidner, den anden deler kontekst med
    brugeren. Derfor et eksplicit valg frem for en heuristik i indbakken —
    en dommer der læser teksten ved hver poll er både dyr og
    nondeterministisk, og det er netop sådan en gammel opgave starter midt i
    en kørende samtale.
    """

    BACKGROUND = "background"
    """Isoleret run. Resultatet projiceres til indbakken; ingen deler kontekst."""

    SESSION = "session"
    """Udføres i den samtale brugeren sidst var aktiv — med cool-down."""

    ADAPTIVE = "adaptive"
    """Wakeup når ejeren har en ledig session, ellers isoleret baggrundsrun."""


class RoutineImportance(StrEnum):
    """Hvor vigtigt et rutine-resultat er — styrer om indbakken fremhæver det.

    Klassifikationen sættes ved oprettelsen. `inbox_gate` læser den; den
    digter den ikke. `kraever_handling` er en *konsekvens* af klassen, ikke et
    løsrevet flag nogen skriver i hånden.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RoutinePrincipal:
    canonical_user_id: str
    role: str = "member"
    actor_kind: str = "user"

    @property
    def user_id(self) -> str:
        return self.canonical_user_id


@dataclass(frozen=True)
class RoutineExecutionContext:
    run_id: str
    routine_id: str
    routine_version: int
    owner_user_id: str
    access_scope: AccessScope
    instruction_ref: str
    instruction_hash: str
    trigger_inputs: dict[str, object]
    workspace_name: str
    workspace_kind: str
    workspace_root: str
    capability_scope: str
    permission_policy: dict[str, object]
    approval_policy: dict[str, object]
    provider: str
    model: str
    lease_generation: int


@dataclass(frozen=True)
class RoutineClassification:
    """Den udledte klassifikation — gemt i ``delivery_policy['classification']``.

    ``as_dict()`` er det der persisteres, så læseren (runner, indbakke, API)
    ikke skal genskabe reglerne. Tom streng i ``execution_mode``/``importance``
    ved oprettelsen betyder «brug den bagudkompatible standard», så alle
    eksisterende kaldesteder er uændrede.
    """

    execution_mode: RoutineExecutionMode
    importance: RoutineImportance
    requires_handling: bool
    blocks_mutations: bool
    highlights: bool
    cool_down_minutes: int

    def as_dict(self) -> dict[str, object]:
        return {
            "execution_mode": self.execution_mode.value,
            "importance": self.importance.value,
            "requires_handling": self.requires_handling,
            "blocks_mutations": self.blocks_mutations,
            "highlights": self.highlights,
            "cool_down_minutes": self.cool_down_minutes,
        }


@dataclass(frozen=True)
class RoutineCreate:
    name: str
    instruction: bytes
    capability_scope: str
    trigger_kind: str
    #: Hvor opgaven udføres. Tom = ``background`` (den adfærd alle
    #: eksisterende rutiner har haft), så tilføjelsen er bagudkompatibel.
    execution_mode: str = ""
    #: Hvor vigtigt resultatet er. Tom = ``normal``.
    importance: str = ""
    trigger_config: Mapping[str, object] = field(default_factory=dict)
    permission_policy: Mapping[str, object] = field(default_factory=dict)
    delivery_policy: Mapping[str, object] = field(default_factory=dict)
    inbox_policy: Mapping[str, object] = field(default_factory=dict)
    retention_policy: Mapping[str, object] = field(default_factory=dict)
    failure_policy: Mapping[str, object] = field(default_factory=dict)
    access_scope: AccessScope = AccessScope.USER_PRIVATE
    created_by: str = "user"
    workspace_name: str = ""
    workspace_kind: str = ""
    workspace_root: str = ""
    jarvis_restart_allowed: bool = False


@dataclass(frozen=True)
class RoutinePatch:
    name: str | None = None
    instruction: bytes | None = None
    capability_scope: str | None = None
    trigger_kind: str | None = None
    trigger_config: Mapping[str, object] | None = None
    permission_policy: Mapping[str, object] | None = None
    delivery_policy: Mapping[str, object] | None = None
    inbox_policy: Mapping[str, object] | None = None
    retention_policy: Mapping[str, object] | None = None
    failure_policy: Mapping[str, object] | None = None
    workspace_name: str | None = None
    workspace_kind: str | None = None
    workspace_root: str | None = None
    jarvis_restart_allowed: bool | None = None

    def changes(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}
