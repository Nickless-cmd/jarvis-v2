"""Vækningen skal BINDE rutine-runnet til det visible run der udfører det.

11/11-2026. En rutine der dispatches til en samtale udføres ikke af
``routine_runner`` men af et visible run i en anden tråd. Afregningen skete
hidtil i en proces-lokal closure, som ikke kan bæres gennem indbakken.

Uden bindingen kan reconcileren kun se «leasen er udløbet» — og requeuer et
run der måske netop lykkedes, så rutinen kører en gang til. Derfor skrives
det visible run-id på rutine-rækken i det øjeblik runnet fødes.
"""
from __future__ import annotations


def _fang_binding(monkeypatch) -> list[dict]:
    bundet: list[dict] = []

    def _bind(run_id, *, visible_run_id, session_id=""):
        bundet.append({
            "run_id": run_id,
            "visible_run_id": visible_run_id,
            "session_id": session_id,
        })
        return True

    monkeypatch.setattr("core.runtime.db_routines.bind_visible_run", _bind)
    return bundet


def _fake_starter(monkeypatch) -> None:
    def _start(tekst, **kw):
        # Vækkeren skal give starteren en callback der får run-id'et.
        kw["started_callback"](visible_run_id="vis-9", session_id="chat-1")
        return True

    monkeypatch.setattr(
        "core.services.visible_autonomous_run.start_autonomous_run", _start,
    )


def test_vaekningen_binder_rutine_runnet_til_det_visible_run(monkeypatch):
    from core.services import inbox_idle_waker as w

    bundet = _fang_binding(monkeypatch)
    _fake_starter(monkeypatch)

    assert w._start_run(
        "gør noget", session_id="chat-1", user_id="42", task_id="rrun-7",
    ) is True

    assert bundet == [{
        "run_id": "rrun-7",
        "visible_run_id": "vis-9",
        "session_id": "chat-1",
    }], bundet


def test_bindingen_faar_postens_opgave_id_ogsa_nar_det_er_tomt(monkeypatch):
    """Vækkeren må ikke gætte et id — den sender postens, også når det er tomt.

    ``bind_visible_run`` er selv en no-op for et tomt id; testen beviser at
    vækkeren kalder den med netop det id posten bar.
    """
    from core.services import inbox_idle_waker as w

    bundet = _fang_binding(monkeypatch)
    _fake_starter(monkeypatch)

    w._start_run("gør noget", session_id="chat-1", user_id="42", task_id="")

    assert bundet == [{
        "run_id": "", "visible_run_id": "vis-9", "session_id": "chat-1",
    }], bundet


def test_vaekningen_binder_POSTEN_til_runnet(monkeypatch):
    """Posten skal bære run-id'et — det er den eneste kobling udgiften kan måles over.

    `costs` har `run_id` men ingen session, og et tidsvindue rammer også runs
    posten ikke startede. Uden denne binding kan kroneloftet i `self_wakeup`
    ikke se hvad en vækning kostede (målt 12/11-2026: 0 af 1.102 poster bandt).
    """
    from core.services import inbox_idle_waker as w

    bundet: list[dict] = []

    def _noter(**kw):
        bundet.append(kw)
        return {"status": "ok"}

    monkeypatch.setattr("core.runtime.db_inbox.noter_leveret_til_run", _noter)
    _fang_binding(monkeypatch)
    _fake_starter(monkeypatch)

    assert w._start_run(
        "gør noget", session_id="chat-1", user_id="42",
        kilde_id="wake-abc", kildetype="wakeup",
    ) is True

    assert bundet == [{
        "bruger_id": "42",
        "kilde_id": "wake-abc",
        "run_id": "vis-9",
        "session_id": "chat-1",
    }], bundet


def test_en_post_uden_adresse_binder_intet(monkeypatch):
    """Et run uden en post må ikke kunne knytte sig til en tilfældig række."""
    from core.services import inbox_idle_waker as w

    bundet: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_inbox.noter_leveret_til_run",
        lambda **kw: bundet.append(kw) or {"status": "ok"},
    )
    _fang_binding(monkeypatch)
    _fake_starter(monkeypatch)

    w._start_run("gør noget", session_id="chat-1", user_id="42")

    assert bundet == [], bundet
