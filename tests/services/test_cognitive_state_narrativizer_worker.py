"""Vagter for den delte sekventielle narrativizer-worker (24/10-2026).

Baggrund: narrativizeren startede tidligere én ny daemon-tråd per kald. Fem
linjer der skiftede state i samme tick gav derfor fem samtidige
`call_compact_llm`-kæder, som hver byggede hele kandidatlisten og
konkurrerede om GIL'en. Målt med py-spy midt i en byge: fem
`Thread-N (_worker)` i samme kæde, 6-9 µs CPU-slices, peak 249 %.

Kontrakten der bevogtes her:
- højst ét LLM-kald ad gangen,
- alle fem linjer bliver stadig genereret,
- det nyeste fingerprint erstatter et ældre ventende job (coalescing),
- shutdown med et langsomt kald blokerer ikke processtop,
- en fejlet enqueue efterlader ikke linjen hængende som "i gang".
"""

from __future__ import annotations

import threading
import time

from core.services import cognitive_state_narrativizer as narr

LINJER = ["body", "affect", "attention", "self_anchor", "boundary"]


def _vent_til(predikat, timeout: float = 5.0, interval: float = 0.01) -> bool:
    frist = time.monotonic() + timeout
    while time.monotonic() < frist:
        if predikat():
            return True
        time.sleep(interval)
    return False


def test_hoejst_et_llm_kald_ad_gangen(monkeypatch) -> None:
    """Fem linjer i samme tick må ikke give fem samtidige LLM-kald."""
    narr._reset_for_tests()
    aktive = {"n": 0, "maks": 0}
    laas = threading.Lock()

    def fake_llm(system_prompt: str, user_message: str) -> str:
        with laas:
            aktive["n"] += 1
            aktive["maks"] = max(aktive["maks"], aktive["n"])
        try:
            time.sleep(0.05)
            return f"svar paa {user_message}"
        finally:
            with laas:
                aktive["n"] -= 1

    monkeypatch.setattr(narr, "_call_narrativizer_llm", fake_llm)

    for i, linje in enumerate(LINJER):
        narr.narrativize_line(
            line_key=linje,
            state={"i": i},
            system_prompt="Kort dansk saetning.",
            user_message_builder=lambda navn=linje: f"linje {navn}",
            fallback="venter",
        )

    assert _vent_til(lambda: all(l in narr._CACHE for l in LINJER)), (
        "ikke alle fem linjer blev genereret — køen taber jobs"
    )
    assert aktive["maks"] == 1, (
        f"maks samtidige LLM-kald = {aktive['maks']}, skal være 1"
    )
    narr._reset_for_tests()


def test_alle_fem_linjer_bliver_genereret(monkeypatch) -> None:
    """Sekventiel afvikling må ikke betyde at nogle linjer aldrig kører."""
    narr._reset_for_tests()
    set_linjer: list[str] = []
    laas = threading.Lock()

    def fake_llm(system_prompt: str, user_message: str) -> str:
        with laas:
            set_linjer.append(user_message)
        return f"svar paa {user_message}"

    monkeypatch.setattr(narr, "_call_narrativizer_llm", fake_llm)

    for i, linje in enumerate(LINJER):
        narr.narrativize_line(
            line_key=linje,
            state={"i": i},
            system_prompt="s",
            user_message_builder=lambda navn=linje: f"linje {navn}",
            fallback="venter",
        )

    assert _vent_til(lambda: len(set_linjer) == len(LINJER)), (
        f"kun {len(set_linjer)} af {len(LINJER)} linjer blev genereret"
    )
    assert sorted(set_linjer) == sorted(f"linje {l}" for l in LINJER)
    narr._reset_for_tests()


def test_nyt_fingerprint_erstatter_ventende_job(monkeypatch) -> None:
    """Står en linje i kø, skal et nyt fingerprint erstatte det gamle job."""
    narr._reset_for_tests()
    gate = threading.Event()
    arbejder_optaget = threading.Event()

    def fake_llm(system_prompt: str, user_message: str) -> str:
        if "BLOKER" in user_message:
            arbejder_optaget.set()
            gate.wait(timeout=5)
            return "blocker svar"
        return f"svar: {user_message}"

    monkeypatch.setattr(narr, "_call_narrativizer_llm", fake_llm)

    # Optag workeren med en anden linje, saa "body" bliver liggende i koeen.
    narr.narrativize_line(
        line_key="blocker",
        state={"x": 1},
        system_prompt="s",
        user_message_builder=lambda: "BLOKER",
    )
    assert arbejder_optaget.wait(timeout=5), "workeren startede ikke"

    state_a = {"v": "a"}
    state_b = {"v": "b"}
    fp_a = narr._fingerprint(state_a)
    fp_b = narr._fingerprint(state_b)
    assert fp_a != fp_b

    narr.narrativize_line(
        line_key="body",
        state=state_a,
        system_prompt="s",
        user_message_builder=lambda: "besked A",
    )
    with narr._CACHE_LOCK:
        assert narr._PENDING["body"].fingerprint == fp_a

    narr.narrativize_line(
        line_key="body",
        state=state_b,
        system_prompt="s",
        user_message_builder=lambda: "besked B",
    )
    with narr._CACHE_LOCK:
        assert narr._PENDING["body"].fingerprint == fp_b, (
            "det nyeste fingerprint erstattede ikke det ventende job"
        )

    gate.set()
    assert _vent_til(lambda: "body" in narr._CACHE), "body blev aldrig genereret"
    assert narr._CACHE["body"].fingerprint == fp_b, (
        "det foraeldede fingerprint vandt over det nyeste"
    )
    narr._reset_for_tests()


def test_shutdown_med_langsomt_kald(monkeypatch) -> None:
    """En langsom LLM-koersel maa ikke holde processtop tilbage."""
    narr._reset_for_tests()
    startet = threading.Event()

    def fake_llm(system_prompt: str, user_message: str) -> str:
        startet.set()
        time.sleep(0.8)
        return "sent svar"

    monkeypatch.setattr(narr, "_call_narrativizer_llm", fake_llm)

    narr.narrativize_line(
        line_key="body",
        state={"a": 1},
        system_prompt="s",
        user_message_builder=lambda: "langsom",
    )
    assert startet.wait(timeout=5), "LLM-kaldet startede ikke"
    with narr._CACHE_LOCK:
        worker = narr._WORKER
    assert worker is not None, "workeren blev ikke oprettet"
    assert worker.daemon is True, "workeren er ikke daemon — kan blokere processtop"

    t0 = time.monotonic()
    narr.shutdown(timeout=0.2)
    brugt = time.monotonic() - t0
    assert brugt < 0.6, f"shutdown tog {brugt:.2f}s — blokerer processtop"
    assert narr._STOP.is_set()
    with narr._CACHE_LOCK:
        assert narr._PENDING == {}, "koeen blev ikke toemt ved shutdown"

    # Ryd op: lade det langsomme kald faerdiggoere, saa traaden doer.
    worker.join(timeout=3.0)
    assert not worker.is_alive(), "worker-traaden lever videre efter shutdown"
    narr._reset_for_tests()


def test_enqueue_fejl_rydder_inflight(monkeypatch) -> None:
    """Fejler enqueue, maa linjen ikke henge som 'i gang' for evigt."""
    narr._reset_for_tests()

    def boom() -> None:
        raise RuntimeError("worker kunne ikke startes")

    monkeypatch.setattr(narr, "_ensure_worker_locked", boom)

    resultat = narr.narrativize_line(
        line_key="body",
        state={"a": 1},
        system_prompt="s",
        user_message_builder=lambda: "besked",
        fallback="venter",
    )
    assert resultat == "venter"
    with narr._CACHE_LOCK:
        assert "body" not in narr._REFRESH_INFLIGHT, (
            "inflight hang efter fejlet enqueue"
        )
        assert "body" not in narr._PENDING
    narr._reset_for_tests()


def test_enqueue_efter_shutdown_efterlader_ikke_et_spoegelsesjob() -> None:
    """Efter ``shutdown()`` må ``_enqueue`` ikke gemme et job som ingen tager.

    24/10-2026 (Codex): ``_ensure_worker_locked`` returnerer stille når
    ``_STOP`` er sat, men ``_enqueue`` tjekkede ikke flaget. Et job lagt i
    køen efter stop blev derfor stående for evigt, og ``_REFRESH_INFLIGHT``
    holdt linjen som "i gang" — så den aldrig kunne genereres igen.
    """
    from core.services import cognitive_state_narrativizer as n

    n._reset_for_tests()
    try:
        n.shutdown(timeout=2.0)

        accepteret = n._enqueue(
            line_key="body",
            fingerprint="efter-stop",
            system_prompt="sys",
            user_message="msg",
        )

        assert accepteret is False, "enqueue accepterede et job efter shutdown"
        assert n._PENDING == {}, f"spøgelsesjob efterladt: {n._PENDING}"
        assert "body" not in n._REFRESH_INFLIGHT, (
            "_REFRESH_INFLIGHT blev ikke ryddet — linjen kan aldrig genereres igen"
        )
    finally:
        n._reset_for_tests()


def test_shutdown_og_enqueue_er_atomiske(monkeypatch) -> None:
    """Stop-flaget SKAL være sat når shutdown() tømmer køen.

    24/10-2026 (Codex): testen ovenfor kalder ``shutdown()`` HELT færdig og
    derefter ``_enqueue()``. Den beviser derfor kun den sekventielle orden —
    ikke atomiciteten. ``_STOP.set()`` stod uden for ``_CACHE_LOCK``, så en
    samtidig enqueue kunne få låsen i vinduet mellem kø-tømningen og
    stop-flaget, se ``_STOP=False`` og lægge et job som ingen worker tager.

    Vagtens kerne er deterministisk: vi fanger øjeblikket hvor shutdown tømmer
    køen — det sker INDE i låsen — og kræver at ``_STOP`` allerede er sat der.
    Er den ikke det, kan enhver enqueue der venter på samme lås komme ind
    bagefter og acceptere et spøgelsesjob. En samtidig enqueue-tråd køres
    oveni som supplerende bevis.
    """
    import threading

    from core.services import cognitive_state_narrativizer as n

    n._reset_for_tests()

    inde_i_laasen = threading.Event()
    forlad_laasen = threading.Event()
    stop_sat_ved_clear: list[bool] = []

    class _SignalPending(dict):
        """Fanger tilstanden i det øjeblik shutdown tømmer køen."""

        def clear(self) -> None:
            # Her holder shutdown _CACHE_LOCK. Er _STOP ikke sat endnu, kan
            # en ventende enqueue slippe ind bagefter og se False.
            stop_sat_ved_clear.append(n._STOP.is_set())
            super().clear()
            inde_i_laasen.set()
            forlad_laasen.wait(timeout=5)

    monkeypatch.setattr(n, "_PENDING", _SignalPending())

    accepteret: list[bool] = []
    fejl: list[BaseException] = []

    def kalder_shutdown() -> None:
        try:
            n.shutdown(timeout=0.1)
        except BaseException as exc:  # pragma: no cover
            fejl.append(exc)

    def kalder_enqueue() -> None:
        try:
            accepteret.append(
                n._enqueue(
                    line_key="body",
                    fingerprint="fp-race",
                    system_prompt="sys",
                    user_message="msg",
                )
            )
        except BaseException as exc:  # pragma: no cover
            fejl.append(exc)

    t_shutdown = threading.Thread(target=kalder_shutdown, name="t-shutdown")
    t_shutdown.start()
    try:
        assert inde_i_laasen.wait(timeout=5), "shutdown nåede aldrig låseblokken"

        t_enqueue = threading.Thread(target=kalder_enqueue, name="t-enqueue")
        t_enqueue.start()
        # Lad enqueue-tråden nå frem til låsen, slip så shutdown.
        t_enqueue.join(timeout=0.15)
        forlad_laasen.set()

        t_shutdown.join(timeout=5)
        t_enqueue.join(timeout=5)

        assert stop_sat_ved_clear == [True], (
            "_STOP var ikke sat da shutdown tømte køen — en samtidig enqueue "
            "kan derfor slippe ind og acceptere et spøgelsesjob"
        )
        assert not t_shutdown.is_alive(), "shutdown hang"
        assert not t_enqueue.is_alive(), "enqueue hang"
        assert not fejl, f"uventet fejl i trådene: {fejl!r}"
        assert accepteret == [False], (
            "enqueue blev accepteret samtidig med shutdown"
        )
        assert dict(n._PENDING) == {}, (
            f"spøgelsesjob efterladt i køen: {dict(n._PENDING)}"
        )
    finally:
        forlad_laasen.set()
        monkeypatch.undo()
        n._STOP.clear()
        n._reset_for_tests()
