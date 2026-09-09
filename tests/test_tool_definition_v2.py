"""De tre akser skilt ad — Fase 3, K1.

«execution provider, presentation mode, and UI metadata are separate.»

Akserne FANDTES allerede. De var bare ikke skilt ad, og hvor de ikke var
skilt ad, drev de fra hinanden: to vaerktoejer blev annonceret til modellen,
deres `_exec_`-funktioner importeret — og de naaede aldrig dispatch-dict'en.
Et kald gav `Unknown tool`. `tool_scoping` havde SKREVET reglen ned; ingen
tjekkede den.

Den vigtigste test her er derfor `test_ingen_uenighed_mellem_de_tre_sandheder`.
"""
from __future__ import annotations

import pytest

from core.tools import tool_definition_v2 as V


@pytest.fixture(autouse=True)
def _rene():
    V._nulstil_for_tests()
    yield
    V._nulstil_for_tests()


# ── vagten der manglede ──────────────────────────────────────────────────

def test_ingen_uenighed_mellem_de_tre_sandheder():
    """Annonceret liste, dispatch-dict og klient-lokal placering skal sige det
    samme. Da denne blev skrevet, sagde de det IKKE: read_identity_sketch og
    update_identity_sketch var annonceret uden executor."""
    assert V.inconsistencies() == []


def test_de_to_der_var_doede_svarer_nu():
    from core.tools.simple_tools import execute_tool
    for navn in ("read_identity_sketch", "update_identity_sketch"):
        r = execute_tool(navn, {})
        assert not str(r.get("error", "")).startswith("Unknown tool"), navn


def test_vagten_fanger_et_vaerktoej_uden_executor(monkeypatch):
    """Selve vagten skal virke — ellers er den groenne test ovenfor tom."""
    import core.tools.simple_tools as ST
    uden = {k: v for k, v in ST._TOOL_HANDLERS.items() if k != "write_file"}
    monkeypatch.setattr(ST, "_TOOL_HANDLERS", uden)
    V._nulstil_for_tests()
    fejl = V.inconsistencies()
    assert [f["tool"] for f in fejl] == ["write_file"]
    assert fejl[0]["kind"] == "advertised_without_executor"


# ── akse 1: hvor koerer det ──────────────────────────────────────────────

def test_alle_annoncerede_er_beskrevet():
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    assert len(V.all_definitions()) == len(TOOL_DEFINITIONS)


def test_operator_placering_udledes_af_KODEN_ikke_af_navnet():
    """Et navnepraefiks er en konvention, ikke en sandhed. `operator_`-praefikset
    holder i dag, men det er en aftale ingen haandhaever."""
    d = V.describe("operator_write_file")
    assert d.execution_provider == V.OPERATOR_BRIDGE

    # et vaerktoej UDEN praefikset, hvis handler krydser broen, skal ogsaa
    # klassificeres som bro — og omvendt maa praefikset alene ikke afgoere det.
    class FalskBro:
        pass
    assert V._udled_provider("uden_praefiks", lambda a: None) == V.IN_PROCESS


def test_klient_lokale_vaerktoejer_er_deres_egen_placering():
    from core.tools.tool_scoping import LOCAL_EXEC_ONLY_TOOLS
    for navn in LOCAL_EXEC_ONLY_TOOLS:
        if V.describe(navn) is not None:
            assert V.describe(navn).execution_provider == V.CLIENT_LOCAL


def test_hver_definition_har_praecis_EN_placering():
    gyldige = {V.IN_PROCESS, V.OPERATOR_BRIDGE, V.CLIENT_LOCAL, V.INGEN}
    assert all(d.execution_provider in gyldige for d in V.all_definitions())


# ── akse 2: effekt-klassen er aerlig om sin daekning ─────────────────────

def test_effekt_klassen_siger_UKENDT_naar_den_ikke_ved_det():
    """8 af 466 er listet. `edit_file` er ikke en af dem. At kalde den
    'read_only' ville vaere en loegn; 'unknown' er sandt."""
    assert V.describe("edit_file").effect_class == V.UKENDT
    assert V.describe("write_file").effect_class == V.NON_IDEMPOTENT_WRITE


# ── akse 3: godkendelse ──────────────────────────────────────────────────

def test_et_vaerktoej_med_force_handler_kraever_godkendelse():
    assert V.describe("write_file").approval_requirement == V.APPROVAL_ASK


# ── K1's egentlige krav: praesentation staar IKKE paa definitionen ───────

def test_definitionen_baerer_INGEN_praesentationsform():
    """Spec'en: presentation mode vaelges én gang pr. profil, IKKE pr.
    vaerktoej. Et felt her ville bygge den sammenfoejning K1 beder om at
    fjerne."""
    felter = {f for f in V.ToolDefinitionV2.__dataclass_fields__}
    assert not {"presentation_mode", "presentation", "render_mode",
                "ui", "ui_meta", "card"} & felter


def test_praesentations_metadata_udledes_af_KALDET_ikke_af_definitionen():
    """Et vaerktoej HAR ikke et udseende; et kald har et udfald."""
    ok = V.presentation_meta("write_file", {"path": "/a"}, {"status": "ok"})
    vent = V.presentation_meta("write_file", {"path": "/a"},
                               {"status": "approval_needed"})
    assert ok["needs_approval"] is False and vent["needs_approval"] is True
    assert ok["tool"] == vent["tool"] == "write_file"


def test_praesentations_metadata_baerer_definitionens_version():
    """Saa et kort tegnet paa gamle hints kan kendes fra et paa nye."""
    from core.tools.tool_schema_contract import schema_version
    m = V.presentation_meta("write_file", {}, {"status": "ok"})
    assert m["definition_version"] == schema_version("write_file")
    assert m["meta_version"] == 1


def test_praesentations_metadata_taaler_et_ukendt_vaerktoej():
    m = V.presentation_meta("findes_ikke", {}, None)
    assert m["execution_provider"] == V.INGEN and m["definition_version"] == ""


# ── adapteren maa ikke kraeve at noget skrives om ────────────────────────

def test_ingen_af_de_466_definitioner_er_aendret():
    """Spec'en: «It should not require every tool to be rewritten
    immediately.» Adapteren UDLEDER; den muterer ikke."""
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    V.all_definitions()
    for d in TOOL_DEFINITIONS:
        assert set(d["function"]) == {"name", "description", "parameters"}


# ── udpakningen: den fejl der fik maalingen til at lyve ──────────────────

def test_indpakkede_handlere_pakkes_ud_foer_de_maales():
    """`simple_tools_enforcement._enforce_wrapper` pakker en del handlere ind.
    Uden udpakning laeser man wrapperens otte linjer og konkluderer at ALT
    koerer in-process — en maaling der ser praecis lige saa selvsikker ud som
    en rigtig. Otte vaerktoejer var klassificeret forkert.
    """
    import core.tools.simple_tools as ST
    h = ST._TOOL_HANDLERS["operator_write_file"]
    assert h.__qualname__ != "_exec_operator_write_file", "ikke laengere indpakket"
    assert "operator_tools" in V._handler_kilde(h)


def test_udpakningen_giver_op_frem_for_at_loebe_i_ring():
    """En indpakning der peger paa sig selv maa ikke haenge maalingen."""
    def selv():
        pass
    selv.__wrapped__ = selv
    assert V._pak_ud(selv) is selv
