"""Approval-ventetid må ikke være tavs.

Run 6f6235b0 (21. aug 2026) døde sådan her: 15 runder, 365s, et bash-kald
returnerede `approval_needed` kl. 07:59:33, og derefter sendte runnet nul frames
i 180 sekunder. `visible_runs_sse_v2._translation_loop` tolker 9 × 20s tavshed
som en død kilde og cancellerede den levende generator. Svaret gik tabt — nul
tegn persisteret, hverken svar eller afbrudt-besked.

Konflikten var mellem to konstanter: approval-vinduet 300s mod idle-loftet 180s.
Testen holder dem op mod hinanden, så en fremtidig justering af den ene ikke
tavst genåbner hullet.
"""
from __future__ import annotations

import asyncio

import pytest

from core.services.visible_runs_sections import approval_wait as aw


class _Clock:
    """Styret tid: ventelokken kalder loop.time(), så vi kan spole frem uden
    at bruge rigtige sekunder."""

    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t


def _drive(state_sequence, *, window_s=300.0, tick_s=1.0):
    """Kør ventelokken med et styret ur og en scriptet tilstandssekvens.

    Returnerer (frames, out). Hvert poll rykker uret `tick_s` frem og henter
    næste tilstand; sekvensens sidste element gentages.
    """
    clock = _Clock()
    seq = list(state_sequence)
    frames: list[str] = []
    out: dict = {}

    def _state(_approval_id):
        s = seq.pop(0) if len(seq) > 1 else seq[0]
        clock.t += tick_s
        return s

    async def _sleep(_):
        return None

    async def _go():
        loop = asyncio.get_running_loop()
        # Uret styres; sleep er gratis.
        orig_time = loop.time
        loop.time = clock.time  # type: ignore[method-assign]
        try:
            async for f in aw.wait_for_approval(
                approval_id="approval-test", tool_name="bash",
                run_id="visible-test", round_no=15, out=out, window_s=window_s,
            ):
                frames.append(f)
        finally:
            loop.time = orig_time  # type: ignore[method-assign]

    import unittest.mock as _m
    with _m.patch.object(
        aw, "wait_for_approval", aw.wait_for_approval
    ), _m.patch(
        "core.services.visible_runs_sections.run_control_state._get_visible_approval_state",
        side_effect=_state,
    ), _m.patch(
        "core.services.visible_runs_sections.run_control_state.touch_active_visible_run",
    ), _m.patch(
        "core.services.visible_runs._sse",
        side_effect=lambda ev, data: f"event: {ev}\ndata: {data}\n\n",
    ), _m.patch.object(asyncio, "sleep", _sleep):
        asyncio.run(_go())
    return frames, out


class TestKeepalive:
    def test_lang_ventetid_sender_heartbeats(self):
        """Den ægte regression: 200s venten skal producere frames undervejs."""
        pending = {"status": "pending"}
        frames, out = _drive([pending, pending, {"status": "approved",
                                                 "result_text": "kørt"}],
                             tick_s=100.0)
        assert frames, "ventelokken var TAVS — idle-loftet ville dræbe runnet"
        assert all("heartbeat" in f for f in frames)
        assert out["result_text"] == "kørt"

    def test_heartbeat_interval_er_under_idle_tick(self):
        """Hæves intervallet over _IDLE_TICK_S er bug'en tilbage, uanset at
        ventelokken 'sender heartbeats'."""
        from core.services.visible_runs_sse_v2 import _IDLE_TICK_S
        assert aw.HEARTBEAT_INTERVAL_S < _IDLE_TICK_S, (
            f"heartbeat hver {aw.HEARTBEAT_INTERVAL_S}s er ikke hurtigere end "
            f"idle-tick'ets {_IDLE_TICK_S}s")

    def test_heartbeat_holder_is_live_frisk(self):
        """is_live kræver en frame indenfor 45s (run_event_log)."""
        assert aw.HEARTBEAT_INTERVAL_S < 45.0

    def test_approval_vindue_er_faktisk_opnaaeligt(self):
        """Kernen i bug'en: vinduet var 300s, men streamen tålte kun 180s.
        Med keepalive er vinduet ægte — men kun så længe heartbeats faktisk
        holder idle-tælleren nede."""
        from core.services.visible_runs_sse_v2 import _IDLE_TICK_S, _MAX_IDLE_TICKS
        tavshedsloft = _MAX_IDLE_TICKS * _IDLE_TICK_S
        assert aw.DEFAULT_APPROVAL_WINDOW_S > tavshedsloft, (
            "hvis vinduet er mindre end loftet, er testen meningsløs — "
            "så var der aldrig en konflikt at fikse")
        assert aw.HEARTBEAT_INTERVAL_S < _IDLE_TICK_S


class TestResultat:
    def test_godkendt_giver_resultatteksten(self):
        _, out = _drive([{"status": "approved", "result_text": "output her"}])
        assert out["result_text"] == "output her"

    def test_afvist_giver_None(self):
        _, out = _drive([{"status": "denied"}])
        assert out["result_text"] is None

    def test_udloebet_giver_None(self):
        _, out = _drive([{"status": "expired"}])
        assert out["result_text"] is None

    def test_timeout_giver_None_og_stopper(self):
        """Vinduet skal stadig lukke — keepalive må ikke gøre ventetiden evig."""
        frames, out = _drive([{"status": "pending"}], window_s=30.0, tick_s=5.0)
        assert out["result_text"] is None

    def test_out_saettes_altid(self):
        """Kalderen læser out['result_text'] ubetinget — en manglende nøgle
        ville give KeyError midt i et run."""
        for state in ({"status": "approved", "result_text": ""},
                      {"status": "denied"}, {"status": "expired"}):
            _, out = _drive([state])
            assert "result_text" in out


class TestKaldesteder:
    def test_begge_stier_bruger_den_faelles_lokke(self):
        """Mønstret lå duplikeret to steder (simpel + agentisk). Fikser man kun
        den ene, dør lange runs stadig — og det var netop den agentiske der
        dræbte 6f6235b0."""
        import inspect
        from core.services import visible_runs
        src = inspect.getsource(visible_runs)
        assert src.count("async for _appr_frame in wait_for_approval(") == 1
        assert src.count("async for _a_appr_frame in wait_for_approval(") == 1

    def test_ingen_tavs_ventelokke_tilbage(self):
        """Regression: en genindført poll-lokke uden yield ville være usynlig
        for de øvrige tests."""
        import inspect
        from core.services import visible_runs
        src = inspect.getsource(visible_runs)
        assert "approval-wait-start" not in src, (
            "en ventelokke er tilbage i visible_runs — den yielder næppe frames")
