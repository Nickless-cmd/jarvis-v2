"""En klient der kommer tilbage efter en genstart skal kunne se sandheden.

Opgave 7. Den proces-lokale hændelseslog er tom efter en genstart, og «tom»
blev læst som «turen er færdig». Journalen på disken ved bedre: opgaven står
som genoptagelig, og dét er hvad klienten skal få at vide.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    return poster


def test_en_genoptagelig_opgave_ses_selv_naar_haendelsesloggen_er_tom():
    ifr.mark_started(run_id="r1", session_id="s1", user_message="ret cheap lane")
    ifr.settle_recovering("r1", reason="shutdown", summary="ret cheap lane")
    snap = ifr.recovery_snapshot("s1")
    assert snap is not None
    assert snap["state"] == "recovering"
    assert snap["reason"] == "shutdown"
    assert snap["task_id"] == "r1"
    assert snap["notice"]["continuing"] is True
    assert "ret cheap lane" in snap["checkpoint_summary"]


def test_en_helt_almindelig_koerende_tur_er_ikke_en_genoptagelse():
    """Ellers ville enhver aktiv tur se ud som noget der var gået galt."""
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    assert ifr.recovery_snapshot("s1") is None


def test_en_afsluttet_tur_giver_ingenting():
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    ifr.settle_terminal("r1", status="completed", reason="completed")
    assert ifr.recovery_snapshot("s1") is None


def test_en_anden_samtale_smitter_ikke():
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    ifr.settle_recovering("r1", reason="shutdown")
    assert ifr.recovery_snapshot("s2") is None


def test_ruten_svarer_204_naar_der_ikke_er_noget(monkeypatch):
    from fastapi import Response
    from apps.api.jarvis_api.routes.chat import chat_session_recovery

    svar = Response()
    assert chat_session_recovery("s-tom", svar) == {}
    assert svar.status_code == 204


def test_ruten_giver_kun_det_brugeren_maa_se(monkeypatch):
    from fastapi import Response
    from apps.api.jarvis_api.routes.chat import chat_session_recovery

    ifr.mark_started(run_id="r1", session_id="s1", user_message="ret cheap lane")
    ifr.settle_recovering("r1", reason="provider-round-timeout", summary="ret cheap lane")
    ud = chat_session_recovery("s1", Response())
    assert set(ud) == {"task_id", "run_id", "state", "reason", "recovery_attempt",
                       "recovery_limit", "checkpoint_summary", "notice"}
    assert "owner_proc" not in ud and "recovery_owner" not in ud


def test_en_syntetisk_afslutning_paastaar_aldrig_at_turen_er_faerdig():
    """«end_turn» ville betyde at svaret står færdigt. Det gør det ikke."""
    import core.services.run_event_log as rel
    frame = rel.synthetic_terminal_frame("r1", "s1", reason="provider-round-timeout")
    assert '"stop_reason": "recovering"' in frame
    assert '"stop_reason": "end_turn"' not in frame
