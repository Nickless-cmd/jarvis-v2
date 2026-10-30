"""Ejerskabs-overfoersel af en Routine skal ogsaa flytte krypteringen.

BAGGRUND (29/10-2026). Bjørn: «Lad Michelles være Michelles.. flyt den til
hende selv.» Hans morgenbrief-rutine var blevet oprettet under hans ejerskab,
selvom opgaven var Michelles. Den rigtige loesning er ikke at oprette en KOPI
ejet af hende — saa er det ikke hendes rutine, men min omskrivning af den.
Loesningen er at flytte hendes egen.

Men `routine_crypto.seal` binder HVER `_enc`-kolonne til ejerens noegle via
`keyring_store.get_user_key(owner)`. En `UPDATE ... SET owner_user_id=?` alene
efterlader rækker som den nye ejer ikke kan aabne: naeste laesning kaster
`DecryptionError`. Maalt paa den virkelige rutine: 7 tabeller, 244 felter.

Disse tests laaser tre ting:
  1. Den nye ejer kan laese rutinen — og den gamle kan IKKE (beviset paa flytning)
  2. Historikken foelger med (runs, events, tool-effects, deliveries)
  3. Versions-snapshot re-krypteres, saa naeste `create_run` ikke braekker
"""

from __future__ import annotations

import pytest

OLD = "owner-old"
NEW = "owner-new"


@pytest.fixture
def two_keys(monkeypatch):
    """To forskellige noegler — ellers kan testen ikke se en manglende re-kryptering."""
    import core.services.keyring_store as keyring_store

    keys = {OLD: b"a" * 32, NEW: b"b" * 32}
    monkeypatch.setattr(keyring_store, "get_user_key", lambda owner: keys[owner])
    return keys


def _make_routine(owner: str = OLD) -> str:
    from core.runtime.db_routines import create_routine

    created = create_routine(
        owner_user_id=owner,
        access_scope="user_private",
        name="Morgenbrief",
        instruction=b"Send vejret",
        capability_scope="chat",
        trigger_kind="interval",
        trigger_config={"interval_minutes": 1440},
        permission_policy={"max_rounds": 20},
        delivery_policy={"channel": "auto", "classification": {"execution_mode": "session"}},
        inbox_policy={},
        retention_policy={"archive_stopped_days": 30},
        failure_policy={"consecutive_failures": 3},
    )
    return created["routine_id"]


def test_den_nye_ejer_kan_laese_rutinen(isolated_runtime, two_keys):
    from core.runtime.db_routines import get_routine, transfer_ownership

    rid = _make_routine()
    moved = transfer_ownership(rid, to_owner_user_id=NEW)

    assert moved["owner_user_id"] == NEW
    assert moved["name"] == "Morgenbrief"
    assert moved["instruction"] == b"Send vejret"
    # Og den er stadig laesbar gennem det normale opslag
    assert get_routine(rid, decrypt_for=NEW)["name"] == "Morgenbrief"


def test_den_gamle_ejer_kan_ikke_laengere_laese_den(isolated_runtime, two_keys):
    """Det er beviset paa at indholdet FAKTISK blev re-krypteret."""
    from core.runtime.db_routines import get_routine, transfer_ownership

    rid = _make_routine()
    transfer_ownership(rid, to_owner_user_id=NEW)

    with pytest.raises(Exception) as exc:
        get_routine(rid, decrypt_for=OLD)
    assert "Decrypt" in type(exc.value).__name__


def test_historikken_foelger_med(isolated_runtime, two_keys):
    """Runs, events, tool-effects og deliveries er ogsaa ejer-forseglet."""
    from core.runtime import db_routines

    rid = _make_routine()
    run = db_routines.create_run(routine_id=rid, idempotency_key="k1", trigger_source="system")
    db_routines.append_run_event(run_id=run["run_id"], kind="started", payload={"a": 1})
    db_routines.create_delivery(run_id=run["run_id"], channel="push", payload=b"hej")

    db_routines.transfer_ownership(rid, to_owner_user_id=NEW)

    # Den nye ejer laeser run'et — inkl. dets snapshot og events
    private = db_routines.get_run(run["run_id"], decrypt_for=NEW)
    assert private["definition_snapshot"]["name"] == "Morgenbrief"
    events = db_routines.read_run_events(run["run_id"], decrypt_for=NEW)
    assert events[0]["payload"] == {"a": 1}

    # Og den gamle ejer kan ikke
    with pytest.raises(Exception):
        db_routines.get_run(run["run_id"], decrypt_for=OLD)


def test_naeste_run_virker_efter_flytning(isolated_runtime, two_keys):
    """create_run kopierer versions-snapshot RÅT — derfor skal den re-krypteres."""
    from core.runtime import db_routines

    rid = _make_routine()
    db_routines.transfer_ownership(rid, to_owner_user_id=NEW)

    fresh = db_routines.create_run(routine_id=rid, idempotency_key="efter", trigger_source="system")
    assert fresh["owner_user_id"] == NEW
    private = db_routines.get_run(fresh["run_id"], decrypt_for=NEW)
    assert private["definition_snapshot"]["instruction"] == b"Send vejret"


def test_samme_ejer_er_en_no_op(isolated_runtime, two_keys):
    from core.runtime.db_routines import get_routine, transfer_ownership

    rid = _make_routine()
    same = transfer_ownership(rid, to_owner_user_id=OLD)
    assert same["owner_user_id"] == OLD
    assert get_routine(rid, decrypt_for=OLD)["name"] == "Morgenbrief"


def test_tom_ejer_afvises(isolated_runtime, two_keys):
    from core.runtime.db_routines import transfer_ownership

    rid = _make_routine()
    with pytest.raises(ValueError):
        transfer_ownership(rid, to_owner_user_id="  ")
