from __future__ import annotations

import ast
import pathlib


def _kilde() -> str:
    return pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")


def test_brugerstop_markeres_cancelled_ikke_interrupted() -> None:
    """Brugerens eget stop må ikke se ud som en afbrudt tur.

    Stop-endepunktet skriver stoppet durabelt ned via `settle_user_stop`
    (`explicit_user_cancel=True`) FØR kørslen afbrydes. Markerede den agentiske
    løkke derefter «interrupted», overskrev den den beslutning — og en afbrudt
    tur er en genoptagelses-kandidat, mens en annulleret ikke er.

    Målt 18/9-2026: tre ture stod som `interrupted` med grunden
    `user-cancelled-during-agentic-loop`, mens de to stop der ramte uden for
    løkken korrekt stod som `cancelled`. Bjørn så sine egne stop starte igen.
    """
    kilde = _kilde()
    linjer = kilde.splitlines()

    afbrydelser = [
        nr for nr, linje in enumerate(linjer)
        if "controller.is_cancelled():" in linje
    ]
    assert afbrydelser, "fandt ingen afbrydelses-kontrol at pinne"

    for nr in afbrydelser:
        blok = "\n".join(linjer[nr:nr + 14])
        if "_outcome_state.mark(" not in blok:
            continue
        assert '_outcome_state.mark("interrupted"' not in blok, (
            f"linje {nr + 1}: et brugerstop markeres «interrupted» og bliver "
            "dermed genoptaget"
        )
        assert "_outcome_state.mark(_CANCELLED_STATUS" in blok, (
            f"linje {nr + 1}: brugerstop skal markeres med CANCELLED"
        )


def test_cancelled_konstanten_er_importeret_i_samme_funktion() -> None:
    """`_CANCELLED_STATUS` bruges dybt inde i `_stream_visible_run`.

    Ligger importen i en anden funktion, giver det NameError i præcis den sti
    der skal stoppe kørslen — altså ville stop-knappen brække i stedet for at
    virke. Testen pinner at brug og import deler funktion.
    """
    kilde = _kilde()
    traeet = ast.parse(kilde)
    linjer = kilde.splitlines()

    brug = [nr + 1 for nr, l in enumerate(linjer) if "_CANCELLED_STATUS" in l]
    assert len(brug) >= 3, "forventede importen plus mindst to brugssteder"

    def indre_funktion(linjenr: int) -> str:
        bedst = ""
        start = -1
        for node in ast.walk(traeet):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.lineno <= linjenr <= (node.end_lineno or node.lineno):
                    if node.lineno > start:
                        start, bedst = node.lineno, node.name
        return bedst

    funktioner = {indre_funktion(nr) for nr in brug}
    assert len(funktioner) == 1, (
        f"import og brug ligger i forskellige funktioner: {funktioner}"
    )
    assert funktioner != {""}, "kunne ikke bestemme funktionen"


def test_cancelled_er_ikke_en_genoptagelses_tilstand() -> None:
    """Politikken må ikke behandle et brugerstop som noget der kan genoptages."""
    from core.services.visible_terminal_policy import (
        TerminalEvidence,
        TerminalState,
        classify_terminal,
    )

    dom = classify_terminal(TerminalEvidence(
        exit_reason="user-cancelled-during-agentic-loop",
        explicit_user_cancel=True,
    ))

    assert dom.state is TerminalState.CANCELLED
    # should_continue er feltet der afgoer om turen tages op igen.
    assert dom.should_continue is False
    assert dom.stop_reason == "cancelled"
