"""Fail-closed policy and independent kill switches for private recall."""
from __future__ import annotations

from core.identity.workspace_context import current_session_id, current_user_id
from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value
from core.services.chat_sessions import get_session_owner


RECALL_FLAG = "scoped_recall_enabled"
MIGRATION_FLAG = "scoped_recall_migration_enabled"


class MissingRecallScope(RuntimeError):
    """A private recall path has no authoritative user principal."""


def recall_enabled() -> bool:
    return get_runtime_state_value(RECALL_FLAG, False) is True


def recall_migration_enabled() -> bool:
    return get_runtime_state_value(MIGRATION_FLAG, False) is True


def set_recall_enabled(enabled: bool) -> None:
    set_runtime_state_value(RECALL_FLAG, enabled is True)


def set_recall_migration_enabled(enabled: bool) -> None:
    set_runtime_state_value(MIGRATION_FLAG, enabled is True)


def require_private_scope(session_id: str = "") -> str:
    user_id = str(current_user_id() or "").strip()
    resolved_session = str(session_id or current_session_id() or "").strip()
    if not user_id and resolved_session:
        user_id = str(get_session_owner(resolved_session) or "").strip()
    if not user_id:
        raise MissingRecallScope("private recall requires explicit user scope")
    # During the explicit identity cutover Desk/JWT contexts may still carry an
    # external Discord subject while private stores use canonical account IDs.
    # Converge when an authoritative encrypted link exists; unresolved test or
    # pre-cutover principals remain stable while the master recall gate is off.
    try:
        from core.services.routine_migration import resolve_canonical_identity
        return str(resolve_canonical_identity(user_id) or user_id)
    except Exception:  # Pre-cutover principals remain stable while recall is disabled.
        return user_id


def disabled_result(path: str) -> dict[str, object]:
    """Svar fra et recall-vaerktoej naar den private soegning er slaaet fra.

    Formen skal kunne SES. Foer 15/10-2026 returnerede den `results` mens
    normal-vejen returnerer `items`, og den sagde ikke ét ord om hvorfor.
    Maalt 14/10-2026: `recall_sensory_memories` svarede `count: 0` for
    query="stue" mens arkivet havde 188 traef — modellen laeste «slukket»
    som «tomt» og konkluderede at der ikke var noget. `note` goer tilstanden
    umulig at forveksle med et tomt resultat, og `items` goer noeglen den
    samme som normal-vejen bruger.
    """
    navn = str(path or "recall")
    return {
        "status": "disabled",
        "path": navn,
        "note": (
            f"{navn}: privat recall er slaaet fra (scoped_recall_enabled=false). "
            "Dette er IKKE et tomt resultat — der blev ikke soegt."
        ),
        "items": [],
        "results": [],
        "count": 0,
    }


__all__ = [
    "MIGRATION_FLAG",
    "RECALL_FLAG",
    "MissingRecallScope",
    "disabled_result",
    "recall_enabled",
    "recall_migration_enabled",
    "require_private_scope",
    "set_recall_enabled",
    "set_recall_migration_enabled",
]
