"""Tavs kæde-knæk: fang en `&&`-kæde hvor resten ikke kørte.

Klassen er målt tre gange på to dage (9/10-2026). Den dyreste: `grep -c` gav
0 træf → exit 1 → `&&`-kæden brød → pytest kørte aldrig og `cp`-gendannelsen
skete ikke, så målingen fortsatte mod en falsificeret fil.

Testene pinner BEGGE sider: den fanger det ægte knæk, og den AFVISER de former
hvor exit≠0 ikke beviser noget (`;`, `||`, blandet kæde, `&&` i en streng).
Uden afvisningerne ville detektoren støje på hver kommando der nævner `&&`.
"""
from core.services import silent_chain_break as scb


# ── fanger det ægte knæk ────────────────────────────────────────────────────

def test_ren_og_kaede_der_broed_fanges():
    fund = scb.silent_chain_break(
        'grep -c "x" fil && pytest -q && cp a b', exit_code=1,
    )
    assert fund is not None
    assert fund["kind"] == "silent_chain_break"
    assert fund["exit_code"] == 1
    assert fund["led"] == 3


def test_det_faktiske_tilfaelde_fra_9_oktober_fanges():
    """`grep -c` med nul træf → exit 1 → resten kørte ikke."""
    cmd = "cd /repo && grep -c 'agent_smith' fil.py && cp fil.py fil.bak"
    fund = scb.silent_chain_break(cmd, exit_code=1)
    assert fund is not None
    assert "kørte ikke" in fund["reason"]


# ── AFVISER de former hvor exit≠0 ikke beviser noget ────────────────────────

def test_exit_nul_er_ikke_et_knæk():
    assert scb.silent_chain_break("a && b", exit_code=0) is None


def test_semikolon_redder_resten():
    """`;` kører alle led uanset — exit≠0 betyder ikke at noget blev sprunget over."""
    assert scb.silent_chain_break("a ; b", exit_code=1) is None


def test_eller_haandterer_fejlen_med_vilje():
    """`||` kører højre side NETOP fordi venstre fejlede — ikke et tavst knæk."""
    assert scb.silent_chain_break("a || b", exit_code=1) is None


def test_blandet_kaede_er_tvetydig():
    """`a && b || c` håndterer fejlen med vilje — exit-koden kan ikke afgøre noget."""
    assert scb.silent_chain_break("a && b || c", exit_code=1) is None


def test_og_inde_i_en_streng_er_ikke_en_operator():
    """`grep "a && b" fil` nævner operatoren uden at være en kæde."""
    assert scb.silent_chain_break('grep "a && b" fil', exit_code=1) is None


def test_manglende_exit_kode_er_ingen_dom():
    assert scb.silent_chain_break("a && b", exit_code=None) is None
    assert scb.silent_chain_break("a && b", exit_code="nej") is None


def test_tom_kommando_er_intet_knæk():
    assert scb.silent_chain_break("", exit_code=1) is None


# ── observe: koblingen til lessons og shell-vaern ───────────────────────────

def test_observe_skriver_lesson_ved_et_knæk(monkeypatch):
    skrevet: list[dict] = []

    def _fake_upsert(**kw):
        skrevet.append(kw)
        return {"outcome": "created"}

    monkeypatch.setattr(
        "core.runtime.db_lessons.upsert_lesson", _fake_upsert,
    )
    fund = scb.observe(
        "bash",
        {"command": "grep -c x f && pytest && cp a b"},
        {"exit_code": 1, "status": "ok"},
    )
    assert fund is not None
    assert len(skrevet) == 1
    assert skrevet[0]["signature"] == "silent_chain_break: bash: &&"
    assert "kørte ikke" in skrevet[0]["lesson"]


def test_observe_tier_naar_der_ikke_er_et_knæk(monkeypatch):
    kaldt: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_lessons.upsert_lesson",
        lambda **kw: kaldt.append(kw) or {"outcome": "created"},
    )
    # exit 0 → intet fund → ingen lesson
    assert scb.observe("bash", {"command": "a && b"}, {"exit_code": 0}) is None
    assert kaldt == []


def test_observe_ignorerer_ikke_shell_vaerktoejer():
    """En `edit_file` bærer ingen exit-kode — detektoren rører den ikke."""
    assert scb.observe("edit_file", {"path": "x"}, {"status": "ok"}) is None
    assert scb.observe("read_file", {"path": "x"}, {"status": "ok"}) is None


def test_observe_er_self_safe_ved_et_doedt_resultat():
    """Et ikke-dict-resultat eller en kastende kald må ikke vælte tool-flow."""
    assert scb.observe("bash", {"command": "a && b"}, None) is None
    assert scb.observe("bash", None, {"exit_code": 1}) is None
