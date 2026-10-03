"""Tests for core/services/visible_runs_outcomes.py.

Fokus: udbyder-fejl-vagten ved persisteringen (2026-09-02).

_persist_session_assistant_message er choke-punktet hvor ALT der bliver til en
assistent-besked passerer. Aihubmix' kvote-afvisning stod ordret i Jarvis' mund
35 gange på 14 dage — og dermed i hans hukommelse — fordi den eksisterende vagt
kun sad på ANDEN pas, som næsten aldrig kører.
"""

from __future__ import annotations

import pytest

import core.services.visible_runs_outcomes as vro

AIHUBMIX = ("Sorry, to prevent abuse of free resources, accounts that have not "
            "been recharged can only try 10 times. You can increase the free "
            "quota after recharging; https://console.aihubmix.com/topup")


class _Run:
    def __init__(self, session_id="auto-dream-20260902"):
        self.run_id = "visible-test"
        self.session_id = session_id
        self.provider = "aihubmix"
        self.model = "gratis-model"


@pytest.fixture
def gemte(monkeypatch):
    ude: list[tuple] = []
    monkeypatch.setattr(vro, "_append_chat_message_with_retry",
                        lambda *a, **k: ude.append((a, k)), raising=False)
    return ude


class TestUdbyderFejlNaarAldrigHansMund:
    def test_den_ægte_haendelse_gemmes_ikke(self, gemte, monkeypatch) -> None:
        journal: list[dict] = []
        monkeypatch.setattr("core.services.autonomous_run_failures.record_failure",
                            lambda **kw: journal.append(kw) or kw, raising=False)
        vro._persist_session_assistant_message(_Run(), AIHUBMIX)
        assert gemte == [], "udbyder-fejlen blev gemt som hans svar"
        assert journal, "fejlen blev tavst kasseret uden at blive journaliseret"
        assert journal[0]["origin"] == "dream"

    def test_et_aegte_svar_gemmes_stadig(self, gemte) -> None:
        vro._persist_session_assistant_message(_Run(), "Jeg har tjekket disken, alt er fint.")
        assert len(gemte) == 1

    def test_dansk_tekst_om_kvoter_censureres_ikke(self, gemte) -> None:
        """Han skal kunne FORTÆLLE om en kvote uden at blive tavs."""
        vro._persist_session_assistant_message(
            _Run(), "Jeg mærkede at kvoten løb tør hos en udbyder, så jeg flyttede mig.")
        assert len(gemte) == 1

    def test_vagtens_fald_maa_ikke_aede_svaret(self, gemte, monkeypatch) -> None:
        monkeypatch.setattr(
            "core.services.provider_error_guard.looks_like_provider_error",
            lambda t: (_ for _ in ()).throw(RuntimeError("vagt nede")), raising=False)
        vro._persist_session_assistant_message(_Run(), "et helt normalt svar")
        assert len(gemte) == 1

    def test_journalens_fald_maa_ikke_gemme_fejlen_alligevel(self, gemte, monkeypatch) -> None:
        """Kan journalen ikke skrive, er teksten stadig ikke hans ord."""
        monkeypatch.setattr("core.services.autonomous_run_failures.record_failure",
                            lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")),
                            raising=False)
        vro._persist_session_assistant_message(_Run(), AIHUBMIX)
        assert gemte == []


class TestOprindelse:
    @pytest.mark.parametrize("sid,ventet", [
        ("auto-dream-20260902", "dream"),
        ("auto-recurring-20260902", "recurring"),
        ("auto-heartbeat-20260902", "heartbeat"),
        ("chat-439a65c933164392871cabeffc7bdc8c", ""),
        ("", ""),
    ])
    def test_oprindelse_udledes(self, sid: str, ventet: str) -> None:
        assert vro._origin_of_session(sid) == ventet


def test_persisted_answer_records_action_outcome(gemte, monkeypatch):
    recorded = []
    monkeypatch.setattr(
        "core.services.decision_action_gate.record_outcomes",
        lambda *args, **kwargs: recorded.append((args, kwargs)),
    )
    run = _Run()
    run.user_message = "Hvad aftalte vi sidst?"
    vro._persist_session_assistant_message(
        run, "Vi aftalte A.", blocks=[{"type": "tool_use", "name": "recall"}],
    )
    assert len(gemte) == 1
    assert recorded == [
        (("visible-test", "Hvad aftalte vi sidst?", "Vi aftalte A."), {"tool_names": ["recall"]})
    ]


def test_autonomous_answer_does_not_create_owner_action_metric(gemte, monkeypatch):
    recorded = []
    monkeypatch.setattr(
        "core.services.decision_action_gate.record_outcomes",
        lambda *args, **kwargs: recorded.append((args, kwargs)),
    )
    run = _Run()
    run.autonomous = True
    run.user_message = "Hvad aftalte vi sidst?"
    vro._persist_session_assistant_message(run, "Et internt svar")
    assert len(gemte) == 1
    assert recorded == []


def test_persisted_outcome_passes_real_session_to_cognitive_updates(monkeypatch):
    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, *_args, **_kwargs):
            return self

        def commit(self):
            return None

    captured: dict[str, object] = {}
    run = _Run(session_id="chat-session-real")
    run.lane = "visible"
    monkeypatch.setattr(vro, "connect", lambda: _Connection())
    monkeypatch.setattr(vro, "write_private_terminal_layers", lambda **_kwargs: None)
    monkeypatch.setattr(vro._vr, "get_visible_run_controller", lambda _run_id: None)
    monkeypatch.setattr(vro._vr, "_get_visible_run_control", lambda _run_id: {})
    monkeypatch.setattr(vro._vr, "_update_cognitive_systems_async", lambda **values: captured.update(values))

    vro._persist_visible_run_outcome(
        run,
        status="completed",
        finished_at="2026-09-10T10:00:00+00:00",
        text_preview="Completed response",
    )

    assert captured["session_id"] == "chat-session-real"


def test_autonomous_outcome_does_not_pass_task_as_user_message(monkeypatch):
    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, *_args, **_kwargs):
            return self

        def commit(self):
            return None

    captured: dict[str, object] = {}
    run = _Run(session_id="auto-recurring-test")
    run.autonomous = True
    run.lane = "visible"
    monkeypatch.setattr(vro, "connect", lambda: _Connection())
    monkeypatch.setattr(vro, "write_private_terminal_layers", lambda **_kwargs: None)
    monkeypatch.setattr(vro._vr, "get_visible_run_controller", lambda _run_id: None)
    monkeypatch.setattr(
        vro._vr, "_get_visible_run_control",
        lambda _run_id: {"current_user_message_preview": "Send morgenbriefing"},
    )
    monkeypatch.setattr(vro._vr, "_update_cognitive_systems_async", lambda **values: captured.update(values))

    vro._persist_visible_run_outcome(
        run,
        status="completed",
        finished_at="2026-09-10T10:00:00+00:00",
        text_preview="Briefing sendt.",
    )

    assert captured["user_message"] == ""


def test_tekstbloggene_normaliseres_ogsaa():
    """Klienterne tegner en gemt tur ud fra content_json — ikke content."""
    from core.services.visible_runs_outcomes import _normaliser_tekstblokke
    ud = _normaliser_tekstblokke([
        {"type": "text", "text": "Kørt. ## Runderne | A | B | |---|---| | a | b | | c | d |"},
        {"type": "tool_use", "id": "t1", "name": "bash", "input": {}},
    ])
    assert "\n| a | b |\n| c | d |" in ud[0]["text"]
    assert ud[1] == {"type": "tool_use", "id": "t1", "name": "bash", "input": {}}


# ── Race-vinduet ved afslutning (3/10-2026) ─────────────────────────────────
# `set_last_visible_run_outcome` laegger DB-projektionen i en daemon-traad.
# Men `run_er_terminal` — som nedluknings-sweepen spoerger — laeser netop
# `visible_runs`-raekken. Stod den stadig `running` med tom `finished_at` da
# sweepen spoergte, blev et run der HAVDE svaret stemplet `interrupted`.
# Maalt 3/10-2026: fire af dagens syv interrupted-stempler sad paa ture der
# havde svaret, og svaret kom paa SAMME sekund som stemplet.
#
# Fixet er ét synkront UPDATE foer traaden starter. Testene her laaser begge
# sider: raekken SKAL staa afsluttet naar funktionen vender tilbage — ogsaa
# naar traaden aldrig naar at koere — og et rigtigt udfald maa aldrig
# overskrives.


def _indsæt_koerende(run_id: str, *, status: str = "running",
                     finished_at: str = "") -> None:
    from core.runtime.db import connect
    with connect() as conn:
        conn.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status,"
            " finished_at) VALUES (?,?,?,?,?,?)",
            (run_id, "visible", "deepseek", "deepseek-v4-flash", status, finished_at))
        conn.commit()


def _laes_raekke(run_id: str):
    from core.runtime.db import connect
    with connect() as conn:
        return conn.execute(
            "SELECT status, finished_at FROM visible_runs WHERE run_id = ?",
            (run_id,)).fetchone()


def _vis_run(run_id: str):
    import core.services.visible_runs as vr
    return vr.VisibleRun(run_id=run_id, lane="visible", provider="deepseek",
                         model="deepseek-v4-flash", user_message="hej",
                         session_id="chat-race")


@pytest.fixture
def uden_traad(monkeypatch):
    """Traaden naar ALDRIG at koere — den vaerste udgave af raceren."""
    monkeypatch.setattr(
        vro, "_persist_visible_run_outcome", lambda *a, **kw: None)
    return None


class TestAfslutningSkrivesSynkront:
    def test_raekken_staar_afsluttet_selv_om_traaden_aldrig_koerer(
            self, isolated_runtime, uden_traad) -> None:
        from core.services.visible_runs_outcomes import set_last_visible_run_outcome
        _indsæt_koerende("visible-race")
        set_last_visible_run_outcome(
            _vis_run("visible-race"), status="completed",
            text_preview="Svar sendt.")
        status, finished = _laes_raekke("visible-race")
        assert status == "completed"
        assert finished, "finished_at staar stadig tom — race-vinduet er aabent"

    def test_sweepen_ser_den_som_terminal(self, isolated_runtime, uden_traad) -> None:
        """Det er DENNE egenskab sweepen spoerger om. Er den True, kalder
        sweepen `mark_completed` og stempler aldrig turen som afbrudt."""
        from core.services.visible_runs_outcomes import (
            run_er_terminal, set_last_visible_run_outcome,
        )
        _indsæt_koerende("visible-race")
        set_last_visible_run_outcome(
            _vis_run("visible-race"), status="completed", text_preview="Svar.")
        assert run_er_terminal("visible-race") is True

    def test_interrupted_stemplet_kan_ikke_laengere_ramme_den(
            self, isolated_runtime, uden_traad) -> None:
        from core.services.visible_runs_outcomes import (
            set_last_visible_run_outcome, stamp_visible_run_interrupted,
        )
        _indsæt_koerende("visible-race")
        set_last_visible_run_outcome(
            _vis_run("visible-race"), status="completed", text_preview="Svar.")
        assert stamp_visible_run_interrupted(
            "visible-race", reason="api-nedlukning") is False
        assert _laes_raekke("visible-race")[0] == "completed"

    def test_et_afsluttet_run_overskrives_ikke(
            self, isolated_runtime, uden_traad) -> None:
        """En raekke der ALLEREDE har et udfald maa ikke roeres — heller ikke
        af et senere, fejlagtigt kald."""
        from core.services.visible_runs_outcomes import set_last_visible_run_outcome
        _indsæt_koerende("visible-race", status="failed",
                         finished_at="2026-10-03T12:00:00+00:00")
        set_last_visible_run_outcome(
            _vis_run("visible-race"), status="completed", text_preview="Svar.")
        status, finished = _laes_raekke("visible-race")
        assert status == "failed"
        assert finished == "2026-10-03T12:00:00+00:00"

    def test_uden_raekke_kaster_det_ikke(self, isolated_runtime, uden_traad) -> None:
        """Start-raekken skrives af `persist_visible_run_start`, men en tur kan
        naa hertil uden den. Et UPDATE der rammer nul raekker er ikke en fejl."""
        from core.services.visible_runs_outcomes import set_last_visible_run_outcome
        set_last_visible_run_outcome(
            _vis_run("visible-findes-ikke"), status="completed",
            text_preview="Svar.")
        assert _laes_raekke("visible-findes-ikke") is None

    def test_db_fejl_draeber_ikke_svaret(
            self, isolated_runtime, uden_traad, monkeypatch) -> None:
        from core.services.visible_runs_outcomes import set_last_visible_run_outcome

        def _braek():
            raise RuntimeError("databasen svarer ikke")

        monkeypatch.setattr(vro, "connect", _braek)
        set_last_visible_run_outcome(
            _vis_run("visible-race"), status="completed", text_preview="Svar.")
