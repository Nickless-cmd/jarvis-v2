"""Klassifikationen PERSISTERET — at valget faktisk når frem.

Reglerne selv testes i `tests/test_routine_classification.py`. Her måles kun
kæden: `RoutineCreate` → `delivery_policy['classification']` → læst tilbage.

To ting er lige vigtige:
1. **Valget bæres igennem** — ellers er feltet endnu en død kontakt.
2. **Intet eksisterende skifter** — en rutine oprettet uden valget skal have
   præcis den adfærd den havde før, og `channel` må ikke blive spist.
"""
from __future__ import annotations

import pytest

from core.services.routine_types import RoutineCreate, RoutinePrincipal


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


def _create(**changes):
    values = {
        "name": "Medicinpåmindelse",
        "instruction": b"Mind brugeren om morgenmedicin",
        "capability_scope": "chat",
        "trigger_kind": "interval",
        "trigger_config": {"interval_minutes": 1440},
        "permission_policy": {},
        "delivery_policy": {"channel": "mobile"},
        "inbox_policy": {"failed": True},
        "retention_policy": {"archive_stopped_days": 30},
        "failure_policy": {"consecutive_failures": 3},
    }
    values.update(changes)
    return RoutineCreate(**values)


@pytest.fixture
def service(isolated_runtime):
    from core.services.routine_service import RoutineService

    return RoutineService(principal=RoutinePrincipal("member-a", role="member"))


def test_klassifikation_persisteres_i_delivery_policy(service):
    view = service.create_and_activate(
        _create(execution_mode="session", importance="critical")
    )
    klassifikation = view.delivery_policy["classification"]
    assert klassifikation["execution_mode"] == "session"
    assert klassifikation["importance"] == "critical"
    assert klassifikation["blocks_mutations"] is True
    assert klassifikation["cool_down_minutes"] == 5


def test_eksisterende_channel_bevares(service):
    # Klassifikationen må ikke spise `channel` — runneren læser den.
    view = service.create_and_activate(_create(importance="high"))
    assert view.delivery_policy["channel"] == "mobile"
    assert view.delivery_policy["classification"]["importance"] == "high"


def test_uden_valg_er_adfaerden_uaendret(service):
    # Bagudkompatibilitet: intet eksisterende kaldestykke må skifte adfærd.
    view = service.create_and_activate(_create())
    klassifikation = view.delivery_policy["classification"]
    assert klassifikation["execution_mode"] == "background"
    assert klassifikation["importance"] == "normal"
    assert klassifikation["requires_handling"] is False


def test_ukendt_valg_stopper_oprettelsen(service):
    with pytest.raises(ValueError, match="importance"):
        service.create_and_activate(_create(importance="akut"))
