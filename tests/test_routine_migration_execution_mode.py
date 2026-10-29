"""Migrationen skal arve opgavens ÆGTE execution_mode — ikke gætte fra session_id.

MÅLT 29/10-2026: morgenbriefen og medicin-påmindelsen blev migreret som
`background`, fordi migrationen gættede ud fra `recurring_tasks.session_id`,
som er TOM for en opgave sat til `session` (tom betyder «slå den aktive op
nu», ikke «ingen adresse»).

Konsekvensen var ikke kosmetisk: rutine-vejen læser sin EGEN kopi af
klassifikationen (`delivery_policy.classification.execution_mode`), og med
`background` kørte opgaven i en isoleret silo. `routine_runs.status` blev
`succeeded` og `routine_deliveries.status` blev `delivered` — men
`deliver_next` kopierer aldrig resultatteksten til en samtale. Så basen
sagde «leveret» om noget ingen nogensinde så.
"""

from __future__ import annotations

from core.services.routine_migration import _definition


def _recurring_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "source_kind": "recurring",
        "task_id": "rec-test",
        "focus": "Send morgenbrief",
        "interval_minutes": 1440,
        "channel": "auto",
        "session_id": "",
        "execution_mode": "session",
        "user_id": "u1",
        "verified_owner_user_id": "u1",
    }
    row.update(overrides)
    return row


def _mode(definition: dict[str, object]) -> str:
    delivery = dict(definition.get("delivery_policy") or {})
    classification = dict(delivery.get("classification") or {})
    return str(classification.get("execution_mode") or "")


def test_opgavens_egen_mode_vinder_over_tom_session_id() -> None:
    """Kernen i fejlen: `session` + tom `session_id` må ikke blive `background`."""
    definition = _definition(_recurring_row(execution_mode="session", session_id=""))
    assert _mode(definition) == "session"


def test_background_forbliver_background() -> None:
    """Den modsatte retning: en ægte background-opgave må ikke flyttes."""
    definition = _definition(_recurring_row(execution_mode="background", session_id=""))
    assert _mode(definition) == "background"


def test_fallback_til_session_id_naar_kolonnen_mangler() -> None:
    """Rækker fra før kolonnen fandtes: gættet er stadig det bedste vi har."""
    definition = _definition(_recurring_row(execution_mode="", session_id="chat-abc"))
    assert _mode(definition) == "session"


def test_fallback_uden_session_id_giver_background() -> None:
    definition = _definition(_recurring_row(execution_mode="", session_id=""))
    assert _mode(definition) == "background"


def test_ukendt_mode_falder_tilbage_paa_gaettet() -> None:
    """En værdi vi ikke kender må ikke sendes videre som om den var gyldig."""
    definition = _definition(_recurring_row(execution_mode="banana", session_id="chat-abc"))
    assert _mode(definition) == "session"
