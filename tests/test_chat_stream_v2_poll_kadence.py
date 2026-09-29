"""Poll-kadencen på SSE-subscriberen i chat_stream_v2.

Baggrund (målt 29/9-2026, direkte på udgangen med `curl -N` og ms-tidsstempler):
subscriberen havde to poll-stier — 15 ms mens der flød frames, 80 ms når der var
tavst. Målingen viste huller på 95/96/95 ms mellem delta-bølger. Det er
80 + 15: idle-stien sov 80 ms, og en bølge der ankom 5 ms senere ventede 75 ms
i utide. Polleren KVANTISEREDE altså kildens huller op i stedet for at følge dem.

Begge stier poller derfor 15 ms. Prisen er at give-up-tærsklen — som er en
TÆLLING af tomme polls — skulle hæves fra 300 til 1600, ellers var tavsheds-
timeouten faldet fra ~24 s til ~4,5 s. Den kobling er det nemt at glemme, og
denne fil holder den fast.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_MODUL = Path(__file__).resolve().parents[1] / "apps/api/jarvis_api/routes/chat_stream_v2.py"

#: Poll-intervallet begge stier skal bruge (sekunder).
_POLL_S = 0.015
#: Tavshed før subscriberen giver op (sekunder) — den tidligere adfærd.
_GIVEUP_S = 24.0


def _kilde() -> str:
    return _MODUL.read_text(encoding="utf-8")


def test_modulet_kan_parses() -> None:
    """Sanity: stien findes og filen er gyldig Python."""
    assert _MODUL.exists(), f"modulet findes ikke: {_MODUL}"
    ast.parse(_kilde())


def test_giveup_taersklen_foelger_poll_intervallet() -> None:
    """Tærsklen × poll-intervallet skal give ~24 s tavsheds-timeout.

    Fejler denne, er enten tærsklen eller intervallet ændret uden at den anden
    fulgte med — og give-up'en fyrer enten for tidligt (dræber en levende run,
    se glm-5.2-hændelsen 29. jun) eller alt for sent.
    """
    tre = ast.parse(_kilde())
    vaerdi = None
    for node in tre.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_IDLE_GIVEUP_POLLS":
                    vaerdi = ast.literal_eval(node.value)
    assert vaerdi is not None, "_IDLE_GIVEUP_POLLS er ikke defineret på modulniveau"

    timeout_s = vaerdi * _POLL_S
    assert abs(timeout_s - _GIVEUP_S) <= 1.0, (
        f"_IDLE_GIVEUP_POLLS={vaerdi} × {_POLL_S}s = {timeout_s:.1f}s, "
        f"forventet ~{_GIVEUP_S}s. Justér tærsklen når poll-intervallet ændres."
    )


def test_begge_poll_stier_sover_kort() -> None:
    """Ingen poll-sti i subscriberen må sove længere end 15 ms.

    Den lange (80 ms) idle-søvn er selve årsagen til de målte 95 ms-huller:
    den kvantiserer kildens kadence op. Denne test er en vagt mod at den
    sniger sig ind igen "for at spare CPU".
    """
    soevne = re.findall(r"_a\.sleep\(\s*([0-9.]+)\s*\)", _kilde())
    assert soevne, "fandt ingen _a.sleep(...) i modulet — er poll-løkken flyttet?"

    for raa in soevne:
        sek = float(raa)
        assert sek <= _POLL_S + 1e-9, (
            f"en poll-sti sover {sek}s (> {_POLL_S}s). Idle-søvn på 80 ms "
            f"kvantiserede kildens huller op til 95 ms — målt 29/9-2026."
        )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
