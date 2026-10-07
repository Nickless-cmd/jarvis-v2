"""Invarianter for de delte exec-konstanter (core/tools/workspace_capabilities_const.py).

Modulet er ren data, men det er den ENE sandhed for hvad der maa koere i
workspace-capabilities — saa en fejl her er ikke kosmetisk. Maalt 3/10-2026:
allowlisten matcher en PRAECIS form, og `("status",)` daekkede ikke
`status --short`, saa heartbeat'ens `inspect_repo_context` blev afvist som
`blocked-git-command` i 3,5 uge (45 blokerede ticks).

Testene her laaser baade den konkrete regression og de invarianter der goer
listen sikker at udvide.
"""
from __future__ import annotations

from core.tools.workspace_capabilities_const import (
    GIT_BLOCKED_SUBCOMMANDS,
    GIT_MUTATING_SUBCOMMANDS,
    GIT_READ_EXEC_ALLOWLIST,
    HARD_BLOCKED_EXEC_TOKENS,
    MUTATING_EXEC_PROPOSAL_TOKENS,
    NON_DESTRUCTIVE_EXEC_ALLOWLIST,
    NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS,
    NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS,
)


# ── Regressionen (3/10-2026) ────────────────────────────────────────────────
def test_status_short_er_i_git_laese_allowlisten() -> None:
    """`git status --short` er en ren laesning og skal vaere tilladt.

    Foer rettelsen faldt den udenfor fordi allowlisten matcher paa form, og
    `("status",)` kun daekker `git status` uden flag.
    """
    assert ("status", "--short") in GIT_READ_EXEC_ALLOWLIST


def test_den_komponerede_heartbeat_kommando_bestaa_af_tilladte_dele() -> None:
    """Heartbeat'ens kontekst-kommando bruger `;` som separator.

    Testen fanger begge fejlklasser paa én gang: en separator der ikke er
    registreret, eller et git-shape der ikke er i laese-allowlisten.
    """
    dele = [
        ("status", "--short"),
        ("branch", "--show-current"),
        ("log", "--oneline", "-n", "5"),
    ]
    assert ";" in NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS
    # `log` har sin egen bounded form-check i exec-laget, ikke i allowlisten.
    for shape in (dele[0], dele[1]):
        assert shape in GIT_READ_EXEC_ALLOWLIST


# ── Invarianter der goer listen sikker at udvide ────────────────────────────
def test_laese_allowlisten_er_ikke_tomme_streng_tupler() -> None:
    """En tom streng ville matche bredere end den ser ud til."""
    assert GIT_READ_EXEC_ALLOWLIST
    for shape in GIT_READ_EXEC_ALLOWLIST:
        assert isinstance(shape, tuple)
        assert shape, f"tom form i allowlisten: {shape!r}"
        for del_ in shape:
            assert isinstance(del_, str) and del_.strip() == del_ and del_


def test_laesning_og_mutation_er_adskilte() -> None:
    """En subkommando maa ikke baade kunne laeses og mutere."""
    laesbare = {shape[0] for shape in GIT_READ_EXEC_ALLOWLIST}
    assert laesbare.isdisjoint(GIT_MUTATING_SUBCOMMANDS)
    assert laesbare.isdisjoint(GIT_BLOCKED_SUBCOMMANDS)
    assert GIT_MUTATING_SUBCOMMANDS.isdisjoint(GIT_BLOCKED_SUBCOMMANDS)


def test_find_og_ls_er_tilladte_kommandoer() -> None:
    """`find` baerer nu heartbeat'ens projekt-listning efter det doede id."""
    assert "find" in NON_DESTRUCTIVE_EXEC_ALLOWLIST
    assert "ls" in NON_DESTRUCTIVE_EXEC_ALLOWLIST


def test_redirection_er_registreret_som_ikke_tilladt() -> None:
    """Komponerede kommandoer maa ikke skrive — vinklerne skal fanges."""
    assert set(NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS) == {">>", "<<", ">", "<"}


def test_de_haardt_blokerede_tokens_er_ikke_ogsaa_foreslaaede() -> None:
    """Et token maa ikke baade vaere haardt blokeret og kunne foreslaas."""
    assert HARD_BLOCKED_EXEC_TOKENS.isdisjoint(MUTATING_EXEC_PROPOSAL_TOKENS)
    assert "rm" in HARD_BLOCKED_EXEC_TOKENS
