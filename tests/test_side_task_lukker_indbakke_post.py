"""Lukning af en sideopgave lukker dens `background_attention`-post.

Målt 8/11-2026: post 10342 og 10348 («stadig åben efter 3 autonome forsøg»)
stod `aaben` efter at deres sideopgaver var lukket med bevis. Testen bruger den
ægte indbakke-tabel (isolated_runtime) — en mock af `afgoer` ville kunne bestå
mens den rigtige post stadig løj.
"""
from contextlib import nullcontext

import pytest

from core.runtime import db_inbox
from core.services import background_attention, side_tasks

OWNER = "bjorn"
BEVIS = "Verificeret: testen er grøn og ændringen er læst igennem"


@pytest.fixture
def opsaetning(isolated_runtime, monkeypatch):
    # `_skema_klar` er en MODUL-konstant. Uden nulstillingen tror test nr. 2 at
    # skemaet findes i sin egen, nye fil — og fejler saa paa en manglende tabel
    # af en grund der intet har med dens emne at goere. Maalt 8/11-2026.
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    state: list = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _k, _d: list(state))
    monkeypatch.setattr(side_tasks, "save_json",
                        lambda _k, items: state.__setitem__(slice(None), items))
    monkeypatch.setattr(side_tasks, "med_laas", lambda _k: nullcontext())
    monkeypatch.setattr(background_attention, "_owner_user_id", lambda: OWNER)


def _post(kilde_id: str, kildetype: str = "background_attention") -> None:
    r = db_inbox.opret_eller_hent(
        bruger_id=OWNER, kildetype=kildetype, kilde_id=kilde_id,
        kraever_handling=True, beskrivelse="stadig åben efter 3 autonome forsøg",
    )
    assert r.get("status") != "fejl", r


def _hent(kilde_id: str) -> dict:
    return db_inbox.hent(bruger_id=OWNER, kilde_id=kilde_id)


def test_completed_lukker_alle_aabne_poster_for_samme_sideopgave(opsaetning):
    tid = side_tasks.flag(title="A", prompt="Gør A")["side_task_id"]
    andet = side_tasks.flag(title="B", prompt="Gør B")["side_task_id"]
    _post(f"background-side-task-{tid}")
    _post(f"background-side-task-{tid}-20261108175555")  # ny generation
    _post(f"background-side-task-{andet}")                # en ANDEN sideopgave
    _post(f"background-side-task-{tid}-x", kildetype="scheduled")  # anden type

    r = side_tasks.resolve(tid, decision="completed", bevis=BEVIS)

    assert r["status"] == "ok" and r["inbox"]["fejl"] == []
    for kid in (f"background-side-task-{tid}",
                f"background-side-task-{tid}-20261108175555"):
        post = _hent(kid)
        assert post["status"] == "done", kid
        assert post["afgjort_at"], kid
        assert BEVIS in post["afgjort_grund"] and tid in post["afgjort_grund"]
    assert _hent(f"background-side-task-{andet}")["status"] == "aaben"
    assert _hent(f"background-side-task-{tid}-x")["status"] == "aaben"


def test_dismissed_dropper_posten_med_grunden(opsaetning):
    tid = side_tasks.flag(title="A", prompt="Gør A")["side_task_id"]
    _post(f"background-side-task-{tid}")
    side_tasks.resolve(tid, decision="dismissed", reason="Ikke relevant længere")
    post = _hent(f"background-side-task-{tid}")
    assert post["status"] == "drop"
    assert "Ikke relevant længere" in post["afgjort_grund"]


def test_lukning_der_fejler_sluges_ikke(opsaetning, monkeypatch):
    tid = side_tasks.flag(title="A", prompt="Gør A")["side_task_id"]
    _post(f"background-side-task-{tid}")

    def _ryger(**_kw):
        raise RuntimeError("db låst")

    monkeypatch.setattr(db_inbox, "afgoer", _ryger)
    r = side_tasks.resolve(tid, decision="completed", bevis=BEVIS)

    assert r["new_status"] == "completed"  # sideopgaven står lukket
    assert r["inbox"]["lukket"] == []
    assert any("db låst" in f for f in r["inbox"]["fejl"])
    assert _hent(f"background-side-task-{tid}")["status"] == "aaben"
