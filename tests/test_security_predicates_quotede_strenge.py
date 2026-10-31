"""Predikat 4 må se KOMMANDOEN, ikke en omtale af den.

Målt 31/10-2026: `classify_command('grep -c "rm" /tmp/x')` returnerede
`destructive`, fordi `\\brm\\b` matcher hvor som helst — også inde i en quoted
streng. En ren læsning der blot NÆVNER rm blev dermed gated som filsletning.

Samme fejlform som `;`-kæden (26/10) og redirect-hullet (30/10): mønstret
matcher et STED i strengen, ikke kommandoen.
"""
from __future__ import annotations

import pytest

from core.tools.security_predicates import evaluate_command
from core.tools.simple_tools import classify_command


# ── Den målte fejl ────────────────────────────────────────────────────────
def test_quoted_rm_er_ikke_destructive():
    """`grep -c "rm" fil` nævner ordet — den sletter intet."""
    assert classify_command('grep -c "rm" /tmp/x') != "destructive"


def test_quoted_rm_er_ikke_destructive_single_quotes():
    assert classify_command("grep -c 'rm' /tmp/x") != "destructive"


def test_quoted_rm_naevnt_i_echo_er_ikke_destructive():
    # echo skriver teksten; en eventuel redirect fanges af redirect-reglen.
    assert evaluate_command('echo "rm -rf /"') is None


# ── Det der SKAL blive fanget ─────────────────────────────────────────────
@pytest.mark.parametrize("cmd", [
    "rm -f /tmp/x",
    "rm /tmp/x",
    "touch a && rm a",
    "(rm a)",
    "cd /tmp && rm -rf x",
])
def test_aegte_sletning_er_stadig_destructive(cmd):
    assert classify_command(cmd) == "destructive"


# ── Huller der IKKE må åbnes ──────────────────────────────────────────────
# Quoted indhold ER kode når kommandoen fortolker det som kode. Uden disse
# ville fixet åbne en dør: `bash -c "rm -rf /"` er en rigtig sletning.
@pytest.mark.parametrize("cmd", [
    'bash -c "rm -rf /x"',
    'sh -c "rm -rf /x"',
    'zsh -c "rm -rf /x"',
    'eval "rm -rf /x"',
    'echo "rm -rf /x" | bash',
])
def test_quoted_kode_fortolket_af_en_shell_er_stadig_destructive(cmd):
    assert classify_command(cmd) == "destructive"


# ── De pinnede regressioner må ikke flytte sig ────────────────────────────
def test_sudo_rm_er_stadig_blocked():
    assert classify_command("sudo rm -rf /") == "blocked"
