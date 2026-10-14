"""Et run der ANONNCERES men aldrig fødes skal lukkes — ikke hænge klienten.

Målt 14/10-2026: `visible-b52c63a8` blev annonceret kl. 18:01:24, fik ingen
frame, ingen fejl og ingen række i `visible_runs`. Klienten pollede det 64
gange på fire minutter (503/404) og slap først da søskende-sweepet lukkede
posten seks minutter senere.

Vagten måler det ene der ER et faktum — et åbent run uden sin første frame —
og lukker det. Den spørger ikke hvorfor, og det er med vilje: en vagt der
hviler på en ubevist årsag ville tie netop når årsagen er en anden.
"""

from __future__ import annotations

import threading

import core.services.run_event_log as rel
import core.services.visible_runs_sections.detached_run as dr


class _Fang:
    def __init__(self) -> None:
        self.frames: list[tuple[str, str]] = []
        self.done: list[str] = []
        self.settle: list[dict] = []


def _arm(monkeypatch, fang: _Fang, *, aaben: bool = True) -> None:
    monkeypatch.setattr(dr, "_FOEDSELSFRIST_S", 0.05)
    monkeypatch.setattr(rel, "is_open", lambda rid: aaben)
    monkeypatch.setattr(rel, "append",
                        lambda rid, frame: fang.frames.append((rid, frame)))
    monkeypatch.setattr(rel, "mark_done", lambda rid: fang.done.append(rid))
    monkeypatch.setattr(rel, "synthetic_terminal_frame",
                        lambda rid, sid, reason="": f'{{"reason": "{reason}"}}')

    import core.services.in_flight_runs as ifr
    monkeypatch.setattr(ifr, "settle_terminal",
                        lambda *a, **k: fang.settle.append(k))


def _koer(fang: _Fang, *, birth_sat: bool = False, stop_sat: bool = False,
          task_id: str = "visible-ea72d19e064c43328763790e48512a30") -> None:
    birth = threading.Event()
    stop = threading.Event()
    if birth_sat:
        birth.set()
    if stop_sat:
        stop.set()
    dr._foedselsvagt(
        run_id="visible-b52c63a897ae48259144588bdeb0b5f3",
        sid="chat-6f46260f781d456cb93383cfcd15cd58",
        task_id=task_id, generation=1, owner="api",
        birth=birth, stop=stop,
    )


def test_udeblivende_foedsel_lukker_runnet(monkeypatch):
    fang = _Fang()
    _arm(monkeypatch, fang)
    _koer(fang)
    assert fang.done == ["visible-b52c63a897ae48259144588bdeb0b5f3"]
    assert fang.frames, "runnet skal have en terminal-frame"
    assert "run_never_born" in fang.frames[0][1]
    assert fang.settle, "opgaven skal lukkes, ikke blive staaende 'running'"
    assert fang.settle[0]["status"] == "failed_terminal"
    assert fang.settle[0]["reason"] == "run-never-born"


def test_foedt_run_roeres_ikke(monkeypatch):
    fang = _Fang()
    _arm(monkeypatch, fang)
    _koer(fang, birth_sat=True)
    assert fang.done == []
    assert fang.frames == []
    assert fang.settle == []


def test_allerede_afsluttet_run_roeres_ikke(monkeypatch):
    fang = _Fang()
    _arm(monkeypatch, fang, aaben=False)
    _koer(fang)
    assert fang.done == []
    assert fang.frames == []
    assert fang.settle == []


def test_stoppet_tur_roeres_ikke(monkeypatch):
    fang = _Fang()
    _arm(monkeypatch, fang)
    _koer(fang, stop_sat=True)
    assert fang.done == []
    assert fang.settle == []


def test_uden_opgave_lukkes_runnet_stadig(monkeypatch):
    """En bruger-tur har ingen opgave — men klienten skal stadig frigives."""
    fang = _Fang()
    _arm(monkeypatch, fang)
    _koer(fang, task_id="")
    assert fang.done == ["visible-b52c63a897ae48259144588bdeb0b5f3"]
    assert fang.settle == []
