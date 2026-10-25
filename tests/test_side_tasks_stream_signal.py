"""Ændringssignalet for sideopgaver (25/10-2026).

Desk havde tre uafhængige pollere af samme data — panelet hentede kun ved
mount, listen hvert 8. sekund, kortet hvert 6. Tre forbindelser for data der
ændrer sig få gange i timen, og et panel der slet ikke opdagede at Jarvis
oprettede en opgave i baggrunden.

Testen her værner det signal der gør pollerne overflødige. Det interessante er
ikke at der bliver publiceret noget — det er RÆKKEFØLGEN: et signal om en
ændring der ikke blev gemt ville få Desk til at hente det gamle svar igen, og
så ville panelet se ud som om det ignorerede handlingen.
"""
from __future__ import annotations

import pytest

from core.services import side_tasks


@pytest.fixture
def lager(monkeypatch):
    """In-memory lager — samme form som de øvrige side-task-tests."""
    state: list = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(
        side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items)
    )
    return state


@pytest.fixture
def bus(monkeypatch):
    """Fang publish-kald uden at røre den rigtige DB-bus."""
    kald: list[tuple[str, dict]] = []

    class _FakeBus:
        def publish(self, kind, payload=None, **_kw):
            kald.append((str(kind), dict(payload or {})))

    monkeypatch.setattr("core.eventbus.bus.event_bus", _FakeBus())
    return kald


class TestSignalet:
    def test_flag_publicerer_et_aendringssignal(self, lager, bus):
        side_tasks.flag(title="Undersøg", prompt="Find årsagen")

        kinds = [k for k, _ in bus]
        assert "runtime.side_tasks_changed" in kinds

    def test_signalet_kommer_efter_den_verificerede_skrivning(self, lager, bus, monkeypatch):
        """Rækkefølgen er pointen: intet signal før lageret faktisk holder posten.

        Mutationen der fælder denne: flyt `_publicer_aendring()` op FØR
        read-back-tjekket i `_save_all`.
        """
        set_under_publish: list[list] = []

        class _FakeBus:
            def publish(self, kind, payload=None, **_kw):
                # Hvad stod i lageret i det øjeblik signalet blev sendt?
                set_under_publish.append(list(lager))

        monkeypatch.setattr("core.eventbus.bus.event_bus", _FakeBus())

        side_tasks.flag(title="Undersøg", prompt="Find årsagen")

        assert set_under_publish, "der blev slet ikke publiceret"
        # Posten SKAL være i lageret når signalet går ud.
        assert any(r.get("title") == "Undersøg" for r in set_under_publish[0])

    def test_en_dod_bus_vaelter_ikke_en_gemt_opgave(self, lager, monkeypatch):
        """Signalet er sekundært. Opgaven er persisteret og verificeret når vi
        når hertil — en fejl i bussen må ikke gøre den til en fejl."""
        class _BraekketBus:
            def publish(self, *_a, **_kw):
                raise RuntimeError("bussen er nede")

        monkeypatch.setattr("core.eventbus.bus.event_bus", _BraekketBus())

        post = side_tasks.flag(title="Undersøg", prompt="Find årsagen")

        assert post.get("side_task_id")
        assert side_tasks.get(post["side_task_id"]) is not None

    def test_opdater_publicerer_ogsaa(self, lager, bus):
        post = side_tasks.flag(title="Undersøg", prompt="Find årsagen")
        bus.clear()

        side_tasks.opdater(post["side_task_id"], title="Undersøg grundigere")

        assert [k for k, _ in bus] == ["runtime.side_tasks_changed"]

    def test_resolve_publicerer_ogsaa(self, lager, bus):
        post = side_tasks.flag(title="Undersøg", prompt="Find årsagen")
        bus.clear()

        side_tasks.resolve(
            post["side_task_id"], decision="dismissed", reason="ikke relevant længere"
        )

        assert "runtime.side_tasks_changed" in [k for k, _ in bus]

    def test_ingen_signal_naar_skrivningen_fejler(self, lager, bus, monkeypatch):
        """Kan posten ikke læses tilbage, rejser `_save_all` — og så må der
        ikke være sendt et signal om en ændring der ikke skete."""
        def _skriv_men_tab(_key, _items):
            lager.clear()  # skrivningen "lykkedes" men indholdet forsvandt

        monkeypatch.setattr(side_tasks, "save_json", _skriv_men_tab)

        with pytest.raises(OSError):
            side_tasks.flag(title="Undersøg", prompt="Find årsagen")

        assert bus == [], "der blev sendt et signal om en ændring der ikke blev gemt"


class TestRuten:
    def test_stream_ruten_er_registreret(self):
        """Ruten skal findes i app'ens tabel — en fil på disk er ikke nok."""
        from apps.api.jarvis_api.app import app

        stier = {getattr(r, "path", "") for r in app.routes}
        assert "/cowork/side-tasks/stream" in stier

    def test_stream_ruten_kolliderer_ikke_med_id_ruterne(self):
        """`/side-tasks/stream` må ikke blive slugt af en `{side_task_id}`-rute."""
        from apps.api.jarvis_api.app import app

        stream_ruter = [
            r for r in app.routes
            if getattr(r, "path", "") == "/cowork/side-tasks/stream"
        ]
        assert len(stream_ruter) == 1
