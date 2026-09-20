"""Fladen («desk» | «mobil») skal overleve HELE vejen fra klient til push.

Bjørn 20/9-2026: «jeg sidder og laver noget med ham i desk og så står han bare
og hænger, indtil jeg kigger på min telefon og så ligger der et approval card
der». Kortet kendte aldrig sin oprindelse; ranglisten gættede.

Kæden har fem led, og hvert led er en ANDEN fil: klienten → ruten →
`start_or_attach_user_run` → `start_visible_run`/`run_event_log` →
`build_request`/pushet. Knækker ét led, sker der intet synligt: turen kører
videre, og notifikationen lander bare det forkerte sted. Testene her pinner
ledene hver for sig.
"""
import inspect

import core.services.run_event_log as rel
from core.services.visible_runs import VisibleRun, start_visible_run
from core.services.visible_runs_sections.detached_run import (
    start_user_run_detached,
)


# Nøglerne ruten sender videre (apps/api/jarvis_api/routes/chat_stream_v2.py).
_RUTENS_KWARGS = {
    "message": "hej",
    "session_id": "s1",
    "approval_mode": "ask",
    "thinking_mode": "think",
    "force_user_id": "bjorn",
    "tool_scope": "",
    "provider_override": "",
    "model_override": "",
    "local_tool_exec": False,
    "surface": "desk",
}


def test_start_visible_run_tager_rutens_kwargs():
    """En manglende parameter ses først når en ÆGTE tur startes.

    Præcis det hul: `surface` blev brugt inde i funktionen uden at være en
    parameter (NameError på hver eneste synlig tur), og ruten sendte den som
    et uventet kwarg. Begge dele fanges her uden at køre en tur.
    """
    inspect.signature(start_visible_run).bind(**_RUTENS_KWARGS)


def test_detached_run_tager_rutens_kwargs():
    sig = inspect.signature(start_user_run_detached)
    sig.bind(original_message="hej", eff_model="m", eff_provider="p", lane="l",
             research_mode=False, **_RUTENS_KWARGS)


def test_koerslen_baerer_fladen_ind_i_godkendelses_kortet():
    """Sidste led: kortet skal kunne sige hvor turen kom fra."""
    from core.services.approval_runtime import build_request
    run = VisibleRun(run_id="r1", lane="visible", provider="p", model="m",
                     user_message="hej", session_id="s1", surface="desk")
    kort = build_request(tool_name="bash", arguments={"command": "ls"},
                         result={}, run=run)
    assert kort["surface"] == "desk"
    # Ukendt flade er tom — aldrig et gæt.
    tom = VisibleRun(run_id="r2", lane="visible", provider="p", model="m",
                     user_message="hej", session_id="s1")
    assert build_request(tool_name="bash", arguments={}, result={}, run=tom)["surface"] == ""


def test_loggen_kan_svare_paa_fladen_med_kun_et_run_id():
    """Pushet har KUN run_id at gå efter — ikke kørsels-objektet."""
    rel._RUNS.clear()
    rel.create("r-push", "s1", surface="mobil")
    assert rel.surface_for_run("r-push") == "mobil"
