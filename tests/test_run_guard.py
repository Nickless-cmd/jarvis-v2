"""Den fælles cross-proces run-vagt (13/10-2026).

Bjørn: «Byg den fælles cross-proces run-vagt og wire den ind». Baggrunden er
målt, ikke gættet: `run_event_log` er in-memory PR. PROCES. jarvis-runtime
(8011) kører daemonerne; jarvis-api (8080) serverer desk'en. En vagt i den ene
proces kan derfor ikke se den andens runs.

Konsekvensen stod i `visible_runs` 13/10: `autonomous-af9f…` og `visible-4f70…`
begge `running` i SAMME session `chat-6f46…` med 31 sekunders mellemrum. Den
ene født mens den anden kørte — den dublet Bjørn så som «flere instanser af dig
i samme session».

Kernen i testene er regressionen: den lokale log er TOM, journalen har runnet.
Det er præcis situationen i drift, og det er den eneste test der fanger den.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import in_flight_runs as ifr
from core.services import run_guard


@pytest.fixture(autouse=True)
def _isoleret_lager(tmp_path, monkeypatch):
    """Registret i hukommelsen — samme mønster som test_in_flight_runs.py."""
    lager: dict = {}
    monkeypatch.setattr(ifr, "_load", lambda: lager)
    monkeypatch.setattr(ifr, "_save", lambda d: lager.update(d))
    return lager


def _post(lager, rid, sid, *, status="running", owner="", alder_s=0.0):
    t = (datetime.now(UTC) - timedelta(seconds=alder_s)).isoformat()
    lager[rid] = {
        "run_id": rid, "session_id": sid, "status": status,
        "started_at": t, "last_progress_at": t, "owner_proc": owner,
    }


# ── levende_koersler: den DELTE læser ────────────────────────────────────────

class TestLevendeKoersler:
    def test_frisk_run_uden_doed_ejer_er_levende(self, _isoleret_lager):
        _post(_isoleret_lager, "r1", "s1")
        assert [r["run_id"] for r in ifr.levende_koersler(session_id="s1")] == ["r1"]

    def test_afsuttet_post_er_ikke_levende(self, _isoleret_lager):
        _post(_isoleret_lager, "r1", "s1", status="completed")
        assert ifr.levende_koersler(session_id="s1") == []

    def test_doed_ejer_er_en_zombie_ikke_et_levende_run(self, _isoleret_lager):
        """Ejeren findes ikke i /proc → posten er en zombie. Det er
        `list_running_orphans` der må stemple den, ikke vagten der må tro på
        den. En pid der er genbrugt narrer os ikke: `owner_still_alive`
        sammenligner OGSÅ starttiden."""
        _post(_isoleret_lager, "r1", "s1", owner="999999999:12345")
        assert ifr.levende_koersler(session_id="s1") == []

    def test_stilstand_over_loftet_er_ikke_levende(self, _isoleret_lager):
        """Uden et loft ville en post der aldrig blev afmeldt blokere hvert
        efterfølgende wakeup for evigt."""
        _post(_isoleret_lager, "r1", "s1", alder_s=4000.0)
        assert ifr.levende_koersler(session_id="s1", max_alder_s=1800.0) == []
        assert len(ifr.levende_koersler(session_id="s1", max_alder_s=0)) == 1

    def test_session_filter_er_praecis(self, _isoleret_lager):
        _post(_isoleret_lager, "r1", "s1")
        _post(_isoleret_lager, "r2", "s2")
        assert [r["run_id"] for r in ifr.levende_koersler(session_id="s2")] == ["r2"]
        assert len(ifr.levende_koersler()) == 2


# ── run_guard: selve vagten ──────────────────────────────────────────────────

class TestRunGuard:
    def test_KERNEN_blokerer_naar_runnet_kun_findes_i_den_DELTE_journal(
        self, monkeypatch,
    ):
        """Den eneste test der fanger defekten. Den lokale log svarer «ingen»
        — præcis som daemonerne oplever det i runtime-processen — mens den
        delte journal har runnet. Vagten SKAL blokere alligevel."""
        import core.services.run_event_log as rel

        monkeypatch.setattr(rel, "active_run_for_session", lambda sid: None)
        monkeypatch.setattr(
            ifr, "levende_koersler",
            lambda **kw: [{"run_id": "visible-af9f", "session_id": "s1"}],
        )
        assert run_guard.blokeringsgrund("wakeup", "s1") == (
            "levende_run_i_session:visible-af9f"
        )

    def test_samme_proces_er_stadig_den_hurtige_vej(self, monkeypatch):
        import core.services.run_event_log as rel

        monkeypatch.setattr(rel, "active_run_for_session", lambda sid: "visible-lokal")
        kaldt: list = []
        monkeypatch.setattr(ifr, "levende_koersler", lambda **kw: kaldt.append(kw) or [])
        assert run_guard.levende_run_i_session("s1") == "visible-lokal"
        assert kaldt == [], "journalen skal ikke spørges når loggen allerede svarer"

    def test_ikke_beskyttet_origin_blokeres_ALDRIG(self, monkeypatch):
        """Et Discord-svar Bjørn selv venter på, eller et barn-agent-svar, må
        ikke spærres af et levende run i sessionen. Vagten er en positivliste."""
        monkeypatch.setattr(
            ifr, "levende_koersler",
            lambda **kw: [{"run_id": "visible-x", "session_id": "s1"}],
        )
        import core.services.run_event_log as rel

        monkeypatch.setattr(rel, "active_run_for_session", lambda sid: "visible-x")
        for origin in ("discord", "telegram", "continuation", "", None):
            assert run_guard.blokeringsgrund(origin, "s1") == ""

    def test_fri_bane_naar_intet_koerer(self, monkeypatch):
        import core.services.run_event_log as rel

        monkeypatch.setattr(rel, "active_run_for_session", lambda sid: None)
        monkeypatch.setattr(ifr, "levende_koersler", lambda **kw: [])
        assert run_guard.blokeringsgrund("wakeup", "s1") == ""

    def test_tom_session_blokerer_ikke(self):
        assert run_guard.levende_run_i_session("") == ""
        assert run_guard.blokeringsgrund("wakeup", "") == ""

    def test_vagten_kaster_aldrig_naar_kilden_braekker(self, monkeypatch):
        """Self-safe: et wakeup må ikke forsvinde fordi registret fejlede."""
        import core.services.run_event_log as rel

        def _boom(*a, **k):
            raise RuntimeError("registeret er væk")

        monkeypatch.setattr(rel, "active_run_for_session", _boom)
        monkeypatch.setattr(ifr, "levende_koersler", _boom)
        assert run_guard.blokeringsgrund("wakeup", "s1") == ""


# ── wiring: at vagten faktisk bliver spurgt ──────────────────────────────────

class TestWiring:
    def test_start_autonomous_run_spoerger_vagten_med_RAA_origin(self, monkeypatch):
        """Origin SKAL være rå. `normalize_origin` kollapser ukendte navne til
        "autonomous" — og så ville «inbox» blive uskelneligt fra et vilkårligt
        autonomt run, og vagten ville gælde noget andet end den så ud til."""
        kaldt: list = []
        monkeypatch.setattr(
            "core.services.run_guard.blokeringsgrund",
            lambda o, s: kaldt.append((o, s)) or "stop",
        )
        from core.services.visible_autonomous_run import start_autonomous_run

        start_autonomous_run("test", session_id="s1", origin="inbox")
        assert kaldt == [("inbox", "s1")]

    def test_wakeup_vagten_bruger_den_faelles_kilde(self, monkeypatch):
        """`_active_turn_blocks` spurgte `run_event_log` direkte. Nu skal den
        gå gennem `run_guard`, som også læser den delte journal."""
        import core.services.wakeup_dispatcher as wd

        monkeypatch.setattr(
            "core.services.run_guard.levende_run_i_session",
            lambda sid: "visible-fra-journalen",
        )
        assert wd._active_turn_blocks("s1") == "session_har_levende_run"

    def test_active_runs_endpointet_laeser_den_delte_journal(self, monkeypatch):
        """Indikatoren i desk'en. Uden dette er et run født i runtime-processen
        usynligt — og Bjørn ser det først ved næste run eller manuel
        opdatering, præcis som han beskrev."""
        monkeypatch.setattr(
            ifr, "levende_koersler",
            lambda **kw: [
                {"run_id": "autonomous-1", "session_id": "chat-abc"},
                {"run_id": "autonomous-2", "session_id": ""},   # uden session: ude
            ],
        )
        import apps.api.jarvis_api.routes.chat as chat

        assert chat._journal_sessions() == [
            {"session_id": "chat-abc", "run_id": "autonomous-1", "status": "working"},
        ]
