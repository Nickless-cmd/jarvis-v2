"""Vækningen skal lande i den indbakke personen faktisk læses i.

Målt 12/11-2026: tre rutine-vækninger lå `aaben` med tom `sidste_vaekning_tur`.
Årsagen var ikke vækkeren — den var at posten var skrevet på rutinens
`owner_user_id`, som for en system-ejet rutine er ejerens LEGACY-identitet,
mens hans indbakke læses under hans discord-id. Polleren spurgte efter den ene
identitet og posten stod på den anden, så vækningen stod stille mens den så ud
som om den var kørt.

Huset har ramt navnerumsblandingen før (se `bruger_for_workspace`): 36 poster
under workspace-navnet blev aldrig arbejdet i. Denne test pinner at gatewayen
ikke kan gentage den med et legacy-id.
"""

from __future__ import annotations

import pytest

from core.runtime import db_inbox
from core.services import wake_gateway
from core.services.inbox_state import normaliser_indbakke_bruger

LEGACY = "legacy-bjoern-identitet"
ÆGTE = "1246415163603816499"


@pytest.fixture
def isoleret(tmp_path, monkeypatch):
    """Egen DB med én bruger der har en legacy-identitet og en ægte indbakke."""
    from core.runtime import db_core

    sti = tmp_path / "jarvis.db"
    monkeypatch.setattr(db_core, "DB_PATH", sti, raising=False)
    monkeypatch.setattr(db_core, "_DB_PATH", sti, raising=False)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    with db_core.connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            " id INTEGER PRIMARY KEY, user_id TEXT, workspace TEXT,"
            " deleted_at TEXT)"
        )
        conn.execute(
            "INSERT INTO users (user_id, workspace, deleted_at) VALUES (?,?,NULL)",
            (LEGACY, "bjorn"),
        )
        conn.commit()

    monkeypatch.setattr(
        "core.services.inbox_state.bruger_for_workspace",
        lambda navn: ÆGTE if str(navn) == "bjorn" else "",
    )
    return sti


def test_legacy_identitet_oploses_til_indbakke_identiteten(isoleret):
    assert normaliser_indbakke_bruger(LEGACY) == ÆGTE


def test_ukendt_identitet_gaettes_ikke(isoleret):
    """At gætte en indbakke er værre end at lade kilden bestemme."""
    assert normaliser_indbakke_bruger("helt-ukendt") == "helt-ukendt"
    assert normaliser_indbakke_bruger("") == ""


def test_gatewayen_skriver_paa_den_loesbare_identitet(isoleret):
    """Hele pointen: posten skal kunne findes af den poller der læser indbakken."""
    kvit = wake_gateway.anmod_om_vaekning(
        kilde="routine",
        sag="run-abc",
        tekst="kør rutinen",
        bruger_id=LEGACY,
        session_id="chat-1",
        task_id="run-abc",
    )
    assert kvit["status"] == "queued", kvit

    post = db_inbox.hent(bruger_id=ÆGTE, kilde_id=wake_gateway.vaekning_kilde_id("run-abc"))
    assert post is not None, "posten landede ikke i den indbakke polleren læser"

    # Og den må IKKE også ligge på legacy-identiteten: to indbakker til én
    # person er præcis den fejl der blev målt i 2026.
    assert db_inbox.hent(
        bruger_id=LEGACY, kilde_id=wake_gateway.vaekning_kilde_id("run-abc")
    ) is None
