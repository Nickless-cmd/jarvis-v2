from __future__ import annotations


def test_familien_er_registreret(isolated_runtime) -> None:
    """Femte gang samme moenster: en uregistreret familie faar publish til at
    kaste, kaldestedet sluger det, og hverken feed eller klient ser noget."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES
    assert "notifikation" in ALLOWED_EVENT_FAMILIES


def test_opret_lander_paa_bussen(isolated_runtime) -> None:
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    event_bus.flush()
    with connect() as conn:
        raekker = conn.execute(
            "SELECT payload_json FROM events WHERE kind=?",
            ("notifikation.ny",)).fetchall()
    assert any(nid in r[0] for r in raekker)


def test_luk_lander_paa_bussen(isolated_runtime) -> None:
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    n.luk(nid, "seen")
    event_bus.flush()
    with connect() as conn:
        raekker = conn.execute(
            "SELECT payload_json FROM events WHERE kind=?",
            ("notifikation.klaret",)).fetchall()
    assert any(nid in r[0] for r in raekker)


def test_luk_dublet_udsender_ikke_igen(isolated_runtime) -> None:
    """Samme faelde som opret(): kald luk() to gange paa samme raekke maa
    ikke faa klokken til at blinke to gange for det samme."""
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    n.luk(nid, "seen")
    n.luk(nid, "seen")
    event_bus.flush()
    with connect() as conn:
        antal = conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", ("notifikation.klaret",)).fetchone()[0]
    assert antal == 1


def test_dublet_udsender_ikke_igen(isolated_runtime) -> None:
    """Ellers ville en gen-udsendt haendelse faa klokken til at blinke igen."""
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    from core.services import notifikationer as n

    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    event_bus.flush()
    with connect() as conn:
        antal = conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", ("notifikation.ny",)).fetchone()[0]
    assert antal == 1
