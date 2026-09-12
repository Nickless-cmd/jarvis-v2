"""Et detached run maa ALDRIG kunne fejle tavst.

Bjoern 13/9-2026: beskeder fra telefonen fik `200 OK`, en valgt udbyder og et
run-id — og derefter absolut stilhed. Ingen fejl, intet svar, ingen raekke i
`visible_runs`. Eneste udvej var at skrive «Forsæt»; maalt 24 gange paa ét doegn.

Aarsagen var seks linjer i traaden der driver HELE svaret:

    try:
        loop.run_until_complete(_consume())
    except Exception:
        rel.mark_done(run_id)      # og ikke ét ord om hvad der gik galt
"""
import inspect

import core.services.visible_runs_sections.detached_run as dr


def _traad_kilde() -> str:
    k = inspect.getsource(dr.start_user_run_detached)
    return k[k.index("loop.run_until_complete"):]


def test_fejlen_logges_med_run_id():
    k = _traad_kilde()
    assert "logger.exception" in k, "krakket logges stadig ikke"
    assert "run_id" in k.split("logger.exception")[1][:200]


def test_ogsaa_BaseException_fanges():
    """En CancelledError herinde er praecis den slags der forsvandt sporloest —
    og den er IKKE en Exception."""
    k = _traad_kilde()
    gren = k[:k.index("logger.exception")]
    assert "except BaseException" in gren, "kun Exception fanges — Cancelled slipper igennem"


def test_klienten_faar_en_terminal_frame():
    """Uden den bliver telefonen staaende i «arbejder» til den giver op selv."""
    k = _traad_kilde()
    assert "synthetic_terminal_frame" in k
    assert "detached_run_crashed" in k


def test_terminal_frame_kaldes_med_den_rigtige_signatur():
    """`append(run_id, frame)` tager TO argumenter. Foerste udgave gaettede paa
    ét og skrev en TypeError-fallback i stedet for at slaa det op."""
    sig = inspect.signature(
        __import__("core.services.run_event_log", fromlist=["append"]).append)
    assert list(sig.parameters) == ["run_id", "frame"]
    k = _traad_kilde()
    assert "rel.append(run_id, rel.synthetic_terminal_frame(" in k
    assert "except TypeError" not in k, "gaetteriet staar der stadig"
