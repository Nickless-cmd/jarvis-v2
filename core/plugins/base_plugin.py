"""Plugin-kontrakt + registry (spec §5, Fase 5 Task 5.1).

To plugin-typer:
- **connector** (Gmail, Calendar, Slack, Notion, GitHub): brugerens egne tjenester.
- **channel** (Discord/Slack/Telegram lokal-gateway): forbinder Jarvis til brugerens
  EGEN server via en lokal gateway på klienten.

**Sikkerhedsmodel (Claude-Desktop):** brugerens tokens/auth ligger på BRUGERENS
maskine (i jarvis-desktop), ALDRIG på Jarvis' server. Denne server-side kontrakt
holder kun *metadata, status og regelsæt* — aldrig hemmeligheder. `auth_fields`
beskriver hvad klienten skal indsamle lokalt, ikke værdierne.

Status er DB-backed (cross-proces) som de øvrige stores. Plugin-regelsæt bor i
plugin_ruleset_store (§5.3) og er hardblock for ALLE inkl. owner.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATUS_KEY = "plugin_status"
_VALID_KINDS = ("connector", "channel")
_VALID_MODES = ("chat", "code", "cowork")


@dataclass(frozen=True)
class PluginManifest:
    """Beskriver et plugin uden at indeholde hemmeligheder."""
    plugin_id: str
    name: str
    kind: str               # "connector" | "channel"
    modes: list[str]        # hvilke modes plugin'et er tilgængeligt i
    auth_fields: list[str] = field(default_factory=list)  # hvad KLIENTEN indsamler lokalt
    events: list[str] = field(default_factory=list)       # events plugin'et kan emittere
    actions: list[str] = field(default_factory=list)      # actions plugin'et tilbyder
    description: str = ""

    def as_dict(self) -> dict:
        return {
            "plugin_id": self.plugin_id, "name": self.name, "kind": self.kind,
            "modes": list(self.modes), "auth_fields": list(self.auth_fields),
            "events": list(self.events), "actions": list(self.actions),
            "description": self.description,
        }


class BasePlugin(ABC):
    """Basis-kontrakt et plugin implementerer.

    `requires_owner` markerer actions der kræver owner-autoritet — de respekterer
    TOTP-override (effective_role) som alt andet (override-flow). Selve token/auth
    håndteres klient-side; server-siden kender kun manifestet + status.
    """
    manifest: PluginManifest

    @abstractmethod
    def is_connected(self) -> bool:
        """True hvis plugin'et har en aktiv (klient-rapporteret) forbindelse."""
        ...

    def requires_owner(self, action: str) -> bool:  # noqa: D401
        """Om en action kræver owner-autoritet (default: nej). Override pr. plugin."""
        return False


# ── Registry: tilgængelige plugins (manifest) + status (DB-backed) ───────────

_REGISTRY: dict[str, PluginManifest] = {}


def register_plugin(manifest: PluginManifest) -> None:
    """Registrér et plugin-manifest. Validerer kind/modes (fail-closed)."""
    if manifest.kind not in _VALID_KINDS:
        raise ValueError(f"ugyldig plugin-kind: {manifest.kind!r}")
    bad = [m for m in manifest.modes if m not in _VALID_MODES]
    if bad:
        raise ValueError(f"ugyldige modes: {bad}")
    _REGISTRY[manifest.plugin_id] = manifest


def available_plugins() -> list[PluginManifest]:
    """Alle registrerede plugin-manifester."""
    return list(_REGISTRY.values())


def get_manifest(plugin_id: str) -> PluginManifest | None:
    return _REGISTRY.get(str(plugin_id or ""))


def clear_registry() -> None:
    """Test-helper."""
    _REGISTRY.clear()


# Status rapporteres af klienten (forbundet/fejlet/offline) — DB-backed cross-proces.
def set_status(plugin_id: str, status: str, *, detail: str = "") -> None:
    """Sæt klient-rapporteret status for et plugin (connected|failed|offline)."""
    pid = str(plugin_id or "").strip()
    if not pid:
        return
    allp = get_runtime_state_value(_STATUS_KEY, {})
    if not isinstance(allp, dict):
        allp = {}
    allp[pid] = {"status": str(status or "offline"), "detail": str(detail or "")[:200]}
    set_runtime_state_value(_STATUS_KEY, allp)


def get_status(plugin_id: str) -> dict:
    allp = get_runtime_state_value(_STATUS_KEY, {})
    if not isinstance(allp, dict):
        return {"status": "offline", "detail": ""}
    rec = allp.get(str(plugin_id or ""))
    return rec if isinstance(rec, dict) else {"status": "offline", "detail": ""}
