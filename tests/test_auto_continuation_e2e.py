"""Auto-fortsaettelsen HELE vejen: udfald → beslutning → nyt run.

Enhedstesten daekker beslutningen. Denne daekker ledningen — og det er dér
fejlene plejer at sidde i dette hus: koden er rigtig, ingen kalder den.
"""
import ast
import inspect
import pathlib

import pytest

import core.services.auto_continuation as ac
import core.services.visible_runs_sections.detached_run as dr


@pytest.fixture(autouse=True)
def _rent_bord():
    ac._UDFALD.clear()
    ac._KAEDE.clear()
    ac._SIDSTE_BRUGER.clear()
    yield
    ac._UDFALD.clear()
    ac._KAEDE.clear()
    ac._SIDSTE_BRUGER.clear()


@pytest.fixture
def startede(monkeypatch):
    """Fanger de runs fortsaettelsen ville starte, i stedet for at starte dem."""
    kald: list[dict] = []
    monkeypatch.setattr(dr, "start_user_run_detached",
                        lambda **kw: kald.append(kw) or "visible-ny")
    return kald


def _koer(run_id="visible-1", sid="s1", startet=0.0):
    dr._fortsaet_hvis_budgettet_loeb_toert(
        run_id=run_id, sid=sid, startet=startet,
        visible_args={"message": "det oprindelige", "session_id": sid,
                      "approval_mode": "ask", "thinking_mode": "think",
                      "force_user_id": None, "tool_scope": "",
                      "provider_override": "", "model_override": "",
                      "local_tool_exec": False},
        eff_model="m", eff_provider="p", lane="primary",
    )


def test_opbrugt_budget_starter_en_fortsaettelse(startede):
    ac.noter_udfald("visible-1", ac.OPBRUGT)
    _koer()
    assert len(startede) == 1
    assert startede[0]["session_id"] == "s1"
    assert "automatisk fortsættelse 1/3" in startede[0]["message"]


def test_faerdig_tur_starter_INTET(startede):
    ac.noter_udfald("visible-1", "completed")
    _koer()
    assert startede == []


def test_ukendt_run_starter_intet(startede):
    """Ingen noteret udfald = vi ved det ikke. Tvivl koster ikke penge."""
    _koer(run_id="visible-findes-ikke")
    assert startede == []


def test_kaeden_taeller_op_og_stopper_ved_loftet(startede):
    for i in range(ac.MAKS_KAEDE):
        ac.noter_udfald(f"visible-{i}", ac.OPBRUGT)
        _koer(run_id=f"visible-{i}")
    assert len(startede) == ac.MAKS_KAEDE
    assert ac.kaede_nr("s1") == ac.MAKS_KAEDE
    # Den fjerde skal blokeres.
    ac.noter_udfald("visible-x", ac.OPBRUGT)
    _koer(run_id="visible-x")
    assert len(startede) == ac.MAKS_KAEDE, "kaeden loeb forbi sit loft"


def test_brugerens_egen_besked_nulstiller_kaeden(startede):
    """Uden nulstillingen ville tre fortsaettelser tidligt paa aftenen spaerre
    for en fortsaettelse ved midnat.

    Runnet skal starte EFTER beskeden — ellers svarer vagten «han tog over»,
    og saa er det den vi maaler i stedet for nulstillingen. (Foerste udgave af
    denne test maalte netop det forkerte og var roed af den rigtige grund.)
    """
    import time
    ac.saet_kaede("s1", ac.MAKS_KAEDE)
    ac.noter_brugerbesked("s1")
    ac.noter_udfald("visible-1", ac.OPBRUGT)
    _koer(startet=time.monotonic() + 1.0)
    assert len(startede) == 1, "kaeden blev ikke nulstillet af en aegte besked"


def test_bruger_der_skriver_MENS_runnet_koerer_tager_over(startede):
    """Ellers taler fortsaettelsen i munden paa ham."""
    ac.noter_udfald("visible-1", ac.OPBRUGT)
    ac.noter_brugerbesked("s1")          # sker EFTER runnets start (0.0)
    ac._KAEDE["s1"] = 1                  # kaeden nulstilles af beskeden ovenfor
    _koer(startet=0.0)
    assert startede == []


def test_fortsaettelsen_arver_turens_indstillinger(startede):
    """Et nyt run med andre tilladelser end det foerste ville vaere en
    stille eskalering."""
    ac.noter_udfald("visible-1", ac.OPBRUGT)
    _koer()
    kw = startede[0]
    assert kw["approval_mode"] == "ask"
    assert kw["thinking_mode"] == "think"
    assert kw["local_tool_exec"] is False


# ── Koblingen opad: saetter loekken overhovedet udfaldet? ────────────────────

def test_loekken_har_en_else_gren_der_melder_opbrugt_budget():
    """`for ... else` koerer KUN naar loekken ikke brod ud — altsaa naar alle
    runder blev brugt. Uden den stod der «completed», og fortsaettelsen ville
    aldrig fyre."""
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    t = ast.parse(kilde)
    loekker = [n for n in ast.walk(t)
               if isinstance(n, ast.For) and "AGENTIC_MAX_ROUNDS" in ast.dump(n.iter)]
    assert loekker, "den agentiske loekke blev ikke fundet"
    assert loekker[0].orelse, "loekken har ingen else-gren"
    assert "OPBRUGT" in ast.dump(ast.Module(body=loekker[0].orelse, type_ignores=[]))


def test_udfaldet_noteres_saa_traaden_kan_laese_det():
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    assert "noter_udfald" in kilde, "udfaldet naar aldrig frem til fortsaettelsen"


def test_fortsaettelsen_kaldes_EFTER_at_runnet_er_markeret_faerdigt():
    """Foer mark_done ser single-flight runnet som levende, og fortsaettelsen
    ville haenge sig paa det doede run i stedet for at starte."""
    k = inspect.getsource(dr.start_user_run_detached)
    assert k.index("mark_done") < k.index("_fortsaet_hvis_budgettet_loeb_toert")
