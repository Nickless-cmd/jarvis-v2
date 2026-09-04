"""Regressionstests for core.tools.simple_tools_web.

Fokus: bash-output-klipning må ALDRIG NameError'e. _exec_bash brugte
_clip_head_tail uden at importere den → "'_clip_head_tail' is not defined"
ramte ethvert bash-kald med >16k output (fx `ls -la /tmp`) og fejlede
tool-kaldet i kode-lanen (2026-07-23).
"""
from __future__ import annotations

import core.tools.simple_tools_web as stw


def test_clip_head_tail_is_bound_in_module():
    """Symbolet skal være importeret i modulets namespace — ellers NameError
    ved runtime på stor bash-output."""
    assert hasattr(stw, "_clip_head_tail")
    assert callable(stw._clip_head_tail)


def test_clip_head_tail_clips_large_output_without_error():
    """Præcis den sti _exec_bash tager for stor output: klip til grænsen uden
    at kaste NameError, og resultatet er kortere end input."""
    big = "x" * (stw.MAX_BASH_OUTPUT_CHARS * 3)
    clipped = stw._clip_head_tail(big, limit=stw.MAX_BASH_OUTPUT_CHARS)
    assert isinstance(clipped, str)
    assert len(clipped) < len(big)


def test_exec_bash_empty_command_is_guarded():
    """Tom kommando kortsluttes før nogen exec/klip — ren fejl, ingen crash."""
    out = stw._exec_bash({"command": "   "})
    assert out.get("status") == "error"
    assert "command" in (out.get("error") or "").lower()


# ---------------------------------------------------------------------------
# 4. sep 2026 (Jarvis' brief): «search returnerer [no matches] for strenge der
# ER i repoet» — og han konkluderede at koden ikke fandtes. Det kostede en halv
# times fejlsøgning i den forkerte retning.
#
# Fejlen kunne ikke genskabes: samme mønstre gav træffere på både workstation
# og container. Så det er sandsynligvis ikke motoren der fejler — det er at
# «[no matches]» ikke skelner mellem «findes ikke» og «du ledte et andet sted».
# ---------------------------------------------------------------------------

def test_nul_traeffere_siger_hvor_der_blev_ledt():
    from core.tools.simple_tools_web import _exec_search

    # Sammensat ved KØRSEL: skrives mønstret som en literal, står det i denne
    # fil — og så finder søgningen sig selv. (Det gjorde den.)
    umuligt = "zzq" + "-findes-ikke-" + "wxy42"
    r = _exec_search({"pattern": umuligt})
    assert r["match_count"] == 0
    assert "[no matches]" in r["text"]
    assert r["searched_root"], "en nul-træffer uden rod er en påstand man ikke kan efterprøve"
    assert r["engine"] in ("rg", "grep")
    assert r["searched_root"] in r["text"]
    assert umuligt in r["text"], "svaret skal gentage hvad der blev søgt efter"


def test_et_glob_der_udelukker_filen_er_synligt_i_svaret():
    """Præcis Jarvis' fejlmønster: strengen FINDES, men globet udelukkede den.
    Uden at globet står i svaret ligner det at koden ikke eksisterer."""
    from core.tools.simple_tools_web import _exec_search

    r = _exec_search({"pattern": "def _exec_search", "glob": "*.md"})
    assert r["match_count"] == 0
    assert "glob=*.md" in r["text"], "globet skal fremgå, ellers drager man en forkert konklusion"


def test_en_traeffer_svarer_stadig_kort_og_uden_stoej():
    """Diagnostikken må kun stå der når der INTET blev fundet."""
    from core.tools.simple_tools_web import _exec_search

    r = _exec_search({"pattern": "def _exec_search"})
    assert r["match_count"] >= 1
    assert "searched_root" not in r
    assert "[no matches]" not in r["text"]
