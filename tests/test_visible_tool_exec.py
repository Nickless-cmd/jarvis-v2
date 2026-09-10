"""Hook-parringen er en invariant — Fase 12.

`PreToolUse` fyrer foer vaerktoejet, `PostToolUse` efter. Ventetiden brugte
`asyncio.wait_for(..., timeout=...)` med `except asyncio.TimeoutError` som
ENESTE gren, saa enhver anden undtagelse fra vaerktoejs-opgaven propagerede ud
af funktionen og sprang PostToolUse-blokken over.

En hook-forfatter der aabner noget i `pre` og lukker det i `post` — et span, en
laas, en maaling — ville lække praecis dér.

MAALT: det er ALDRIG sket i produktion (nul kast paa syv dage). Det er altsaa
en strukturel invariant, ikke en observeret fejl — men den koster tre linjer,
og spec'en navngiver den.

Fejlen rejses stadig bagefter, saa kalderen ser praecis det samme som foer.
Det eneste der er aendret er at parringen holder.
"""
from __future__ import annotations

import inspect

import core.services.visible_tool_exec as vte


def _kilde() -> str:
    return inspect.getsource(vte.run_tool_batch)


def test_kastet_fanges_saa_PostToolUse_naas():
    k = _kilde()
    i_await = k.index("await _tool_task")
    i_post = k.index("PostToolUse-hook")
    mellem = k[i_await:i_post]
    assert "except BaseException" in mellem, (
        "et kast fra vaerktoejs-opgaven springer stadig PostToolUse over — "
        "parringen brydes")


def test_fejlen_rejses_igen_EFTER_hooken():
    """Vagten maa ikke sluge fejlen. Kalderen skal se praecis det samme som
    foer; det eneste der er aendret er at parringen holder."""
    k = _kilde()
    i_post = k.index("PostToolUse-hook")
    efter = k[i_post:]
    assert "raise _tool_exc" in efter, (
        "undtagelsen bliver slugt — en fejlet tur ville se ud som en gennemfoert")
    assert efter.index("raise _tool_exc") < efter.index('out["results"]'), (
        "fejlen rejses efter at resultatet er skrevet — saa ville et tomt "
        "resultat naa kalderen foerst")


def test_timeout_grenen_er_uroert():
    """Heartbeat-loekken skal stadig kunne taale en TimeoutError uden at
    behandle den som en fejl — den ER det normale ved lange vaerktoejer."""
    k = _kilde()
    assert "except asyncio.TimeoutError:" in k
    i_to = k.index("except asyncio.TimeoutError:")
    i_be = k.index("except BaseException")
    assert i_to < i_be, "timeout-grenen skal komme foerst"
