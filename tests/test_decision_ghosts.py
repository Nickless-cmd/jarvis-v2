"""Tests for decision_ghosts.py"""

import pytest
from core.services.decision_ghosts import (
    record_rejected_path,
    describe_ghost_decision,
    format_decision_ghost_for_prompt,
    reset_decision_ghosts,
    build_decision_ghosts_surface,
)


def setup_function():
    reset_decision_ghosts()


def test_record_rejected_path():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    surface = build_decision_ghosts_surface()
    assert surface["rejected_count"] == 1
    assert surface["active"] is True


def test_describe_ghost_decision():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    desc = describe_ghost_decision()
    assert "choice_b" in desc or "choice_a" in desc


def test_format_decision_ghost_for_prompt():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    result = format_decision_ghost_for_prompt()
    assert "BESLUTNINGSSPØGELSE:" in result


def test_build_decision_ghosts_surface():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    surface = build_decision_ghosts_surface()
    assert surface["active"] is True
    assert surface["rejected_count"] == 1
    assert surface["top_regret"] is not None


def test_reset_decision_ghosts():
    record_rejected_path("choice_a", "too_risky", "choice_b")
    reset_decision_ghosts()
    surface = build_decision_ghosts_surface()
    assert surface["rejected_count"] == 0


def test_empty_decision_ghosts():
    surface = build_decision_ghosts_surface()
    assert surface["active"] is False
    assert surface["rejected_count"] == 0


# ── Tallene er maalte, ikke kastede (25/9-2026) ──────────────────────────
#
# Indtil i dag stod der:
#
#     "regret_potential": random.uniform(0.1, 0.6),
#     "success_echo": random.uniform(0.3, 0.9),
#
# og to modul-globale lister der doede ved genstart. `describe_ghost_decision`
# valgte den «mest saliente» fortrydelse ved `max(..., key=regret_potential)`
# — altsaa det hoejeste terningkast. Han ville have faaet at vide hvad han
# fortrod mest, og svaret var tilfaeldigt.
#
# Modulet havde INGEN kalder, selv om `record_reaffirmed_decision`s docstring
# sagde at den blev kaldt fra beslutnings-gennemgangen.
#
# Kilden er nu `behavioral_decision_reviews` (1101 raekker maalt):
#     kept 538 · broken 299 · partial 263 · fulfilled 1
# med en rigtig `adherence_score`.
import json  # noqa: E402

import core.services.decision_ghosts as DG  # noqa: E402
from core.runtime import state_store


@pytest.fixture(autouse=True)
def _tom_tilstand():
    """Hver test starter paa en tom fil.

    Isolationen kom foer fra at hver test patchede `_storage_path` til sin egen
    `tmp_path`. Med `state_store` er stien skaermet af conftest' autouse-fixture
    `_guard_prod_state_dir` — men den mappe er SESSIONS-bred, saa tilstand
    laekker mellem tests i samme fil hvis ingen rydder op. Det var netop den
    skaerm der manglede for `shared_dir()`: uden den skrev disse tests i den
    aegte `~/.jarvis-v2/shared/runtime/`.
    """
    state_store.save_json("decision_ghosts", {"rejected": [], "confirmed": []})
    yield




def test_sporet_overlever_en_genstart():
    """KERNEN. To modul-globale lister doede med processen."""
    DG.reset_decision_ghosts()
    DG.record_rejected_path("a", "b", "c", 0.4)

    import importlib
    DG2 = importlib.reload(DG)
    assert DG2.build_decision_ghosts_surface()["rejected_count"] == 1


def test_der_er_INTET_random_tilbage():
    """AST, ikke grep: docstringen citerer med vilje den gamle kode."""
    import ast
    import inspect

    traen = ast.parse(inspect.getsource(DG))
    assert not [n.lineno for n in ast.walk(traen)
                if isinstance(n, ast.Attribute)
                and getattr(n.value, "id", None) == "random"], "terningen er tilbage"
    assert not any(isinstance(n, ast.Import) and any(a.name == "random" for a in n.names)
                   for n in ast.walk(traen))


def test_uden_en_maaling_gemmes_None_ikke_et_gaet(tmp_path):
    DG.reset_decision_ghosts()
    DG.record_rejected_path("a", "b", "c")
    gemt = state_store.load_json("decision_ghosts", {})
    assert gemt["rejected"][0]["regret_potential"] is None


def test_den_maalte_vinder_over_den_umaalte():
    """En post uden tal maa ikke kunne rangere over en med."""
    DG.reset_decision_ghosts()
    DG.record_rejected_path("uden tal", "b", "vej-A")
    DG.record_rejected_path("med tal", "b", "vej-B", 0.2)
    assert "vej-B" in DG.describe_ghost_decision()


def test_uden_nogen_tal_vaelges_den_nyeste():
    """Frem for et vilkaarligt valg der LIGNER en rangering."""
    DG.reset_decision_ghosts()
    DG.record_rejected_path("foerste", "b", "vej-A")
    DG.record_rejected_path("nyeste", "b", "vej-B")
    assert "vej-B" in DG.describe_ghost_decision()


def test_en_brudt_beslutning_giver_fortrydelse_lig_1_minus_efterlevelse():
    """Jo mindre han fulgte den, jo mere er der at spoerge om."""
    DG.reset_decision_ghosts()
    DG.record_broken_decision("d1", "skriv tests foerst", adherence_score=0.25,
                              note="jeg sprang dem over")
    top = DG.build_decision_ghosts_surface()["top_regret"]
    assert top["regret_potential"] == 0.75
    assert top["alternative"] == "jeg sprang dem over"


def test_en_holdt_beslutning_baerer_sin_efterlevelse():
    DG.reset_decision_ghosts()
    DG.record_reaffirmed_decision("d2", "maal foer du retter", "kept", adherence_score=1.0)
    assert DG.build_decision_ghosts_surface()["top_echo"]["success_echo"] == 1.0


def test_gennemgangen_skriver_sporet(monkeypatch):
    """DEN manglende kalder. Docstringen sagde den fandtes; det gjorde den ikke."""
    import core.services.behavioral_decisions as B
    DG.reset_decision_ghosts()
    monkeypatch.setattr(B, "append_review", lambda **kw: {
        "decision_id": "d1", "directive": "en direktiv", "adherence_score": 0.4})
    monkeypatch.setattr(B.event_bus, "publish", lambda *a, **k: None)

    B.review_decision(decision_id="d1", verdict="broken", note="noget andet")
    u = DG.build_decision_ghosts_surface()
    assert u["rejected_count"] == 1
    assert u["top_regret"]["regret_potential"] == 0.6

    B.review_decision(decision_id="d1", verdict="kept")
    assert DG.build_decision_ghosts_surface()["confirmed_count"] == 1


def test_et_braekket_spor_vaelter_ikke_gennemgangen(monkeypatch):
    """Gennemgangen er det vigtige; sporet er en biting."""
    import core.services.behavioral_decisions as B
    monkeypatch.setattr(DG, "record_broken_decision",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("i stykker")))
    monkeypatch.setattr(B, "append_review", lambda **kw: {
        "decision_id": "d1", "directive": "x", "adherence_score": 0.4})
    monkeypatch.setattr(B.event_bus, "publish", lambda *a, **k: None)
    assert B.review_decision(decision_id="d1", verdict="broken") is not None
