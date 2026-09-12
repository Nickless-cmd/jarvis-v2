"""Stop-knappen skal svare mens vaerktoejerne koerer."""
from __future__ import annotations

import asyncio
import time
import types

import pytest

import core.services.simple_tool_executor as ste
import core.services.visible_tool_exec as vte


class _Run:
    run_id = "visible-test"
    session_id = "chat-test"
    user_message = "hej"
    autonomous = False
    local_tool_exec = False
    provider = "p"
    model = "m"


async def _koer(afbrudt_efter_s: float | None, tool_varighed_s: float,
                hjerteslag_s: float = 15.0) -> tuple[dict, float, int]:
    def _langsom(kald, **kw):
        time.sleep(tool_varighed_s)
        return [{"tool_name": "bash", "status": "ok", "result_text": "faerdig"}]

    # Importen er DOVEN og sker inde i run_tool_batch, saa den skal patches paa
    # KILDEmodulet. Foerste udgave patchede `vte` og var groen paa den ene test
    # mens det aegte bash-vaerktoej koerte.
    ste._execute_simple_tool_calls = _langsom

    t0 = time.monotonic()
    er_afbrudt = (lambda: (time.monotonic() - t0) >= afbrudt_efter_s) if afbrudt_efter_s is not None else None
    ud: dict = {}
    _slag = 0
    async for _f in vte.run_tool_batch(
        [{"function": {"name": "bash", "arguments": "{}"}}],
        run=_Run(), loop=asyncio.get_running_loop(), tool_scope="chat",
        step_counter=0, heartbeat_interval_s=hjerteslag_s, heartbeat_phase="t",
        out=ud, er_afbrudt=er_afbrudt,
    ):
        if "heartbeat" in _f:
            _slag += 1
    return ud, time.monotonic() - t0, _slag


def test_stop_under_vaerktoejskoersel_svarer_inden_for_et_sekund():
    """MAALT 12/9: serveren svarede 200 OK paa to tryk 22:51:28 og :30, og
    runnet stoppede 22:52:27 — 59 s senere. Aarsagen var at vente-loekken kun
    ventede paa vaerktoejerne."""
    ud, brugt, _ = asyncio.run(_koer(afbrudt_efter_s=0.2, tool_varighed_s=8.0))
    assert ud.get("afbrudt") is True
    assert ud["results"] == []
    assert brugt < 2.0, f"stop tog {brugt:.1f}s — vaerktoejet varede 8s"


def test_uden_afbrydelse_ventes_vaerktoejet_faerdigt():
    """Vagten maa ikke kunne forveksle «langsom» med «afbrudt»."""
    ud, brugt, _ = asyncio.run(_koer(afbrudt_efter_s=None, tool_varighed_s=1.5))
    assert not ud.get("afbrudt")
    assert ud["results"] and ud["results"][0]["status"] == "ok"
    assert brugt >= 1.4


def test_finere_puls_goer_ikke_hjerteslaget_hurtigere():
    """Afbrydelsen skal ses hvert sekund — men livstegnet skal stadig falde i
    sin egen takt. Ellers betaler responsen for sig med femten gange saa mange
    hjerteslag ud til telefonen."""
    _, _, slag = asyncio.run(_koer(afbrudt_efter_s=None, tool_varighed_s=5.0,
                                   hjerteslag_s=2.0))
    assert slag == 2, f"{slag} hjerteslag paa 5 s med 2 s takt"
