"""Tests for body_memory.py"""

import pytest
from core.services.body_memory import (
    record_body_snapshot,
    describe_body_memory,
    format_body_for_prompt,
    reset_body_memory,
    build_body_memory_surface,
)


def setup_function():
    reset_body_memory()


def test_record_body_snapshot():
    record_body_snapshot("test_context", "varm", 0.5)
    surface = build_body_memory_surface()
    assert surface["snapshot_count"] == 1
    assert surface["active"] is True


def test_describe_body_memory():
    record_body_snapshot("test_context", "kold", 0.7)
    desc = describe_body_memory()
    assert "kold" in desc
    assert "test_context" in desc


def test_format_body_for_prompt():
    record_body_snapshot("test_context", "tryk", 0.6)
    result = format_body_for_prompt()
    assert "KROP:" in result


def test_build_body_memory_surface():
    record_body_snapshot("test_context", "prikken", 0.4)
    surface = build_body_memory_surface()
    assert surface["active"] is True
    assert surface["snapshot_count"] == 1
    assert surface["latest"] is not None


def test_reset_body_memory():
    record_body_snapshot("test_context", "varm", 0.5)
    reset_body_memory()
    surface = build_body_memory_surface()
    assert surface["snapshot_count"] == 0
    assert surface["active"] is False


def test_empty_body_memory():
    surface = build_body_memory_surface()
    assert surface["active"] is False
    assert surface["snapshot_count"] == 0


# ── Kroppen husker noget MAALT (25/9-2026) ──────────────────────────────
#
# Indtil i dag stod der:
#
#     sensation = sensation or random.choice(["varm", "kold", "tryk", "prikken"])
#     intensity = intensity or random.uniform(0.3, 0.9)
#     _body_snapshots: list[dict] = []
#
# En modul-global liste der doede ved genstart, fyldt med tilfaeldige ord — og
# formuleret som «Jeg mindes en varm fornemmelse fra …». Sproget loej om hvad
# det var. Modulet havde INGEN kalder i produktion, og koden vidste det selv:
# `central_body_mood_feel.py:14` siger «body_memory DROPPET».
#
# Sansningen manglede aldrig: `embodied_state` laeser vaertens tal og er
# importeret 16 steder. Erindringen manglede.
import json  # noqa: E402

import core.services.body_memory as B  # noqa: E402
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
    state_store.save_json("body_memory", [])
    yield



def _krop(monkeypatch, tmp_path, *, load=0.05, tryk=0.4, belastning="low"):
    monkeypatch.setattr(
        "core.services.embodied_state.build_embodied_state_surface",
        lambda: {"strain_level": belastning, "state": "steady",
                 "facts": {"cpu": {"load_per_cpu": load},
                           "memory": {"pressure_ratio": tryk}}})


def test_fornemmelsen_er_udledt_af_maalte_tal(monkeypatch, tmp_path):
    """KERNEN. Og grundlaget gemmes, saa ordet kan efterproeves mod sit tal."""
    _krop(monkeypatch, tmp_path, load=0.9)
    s = B.record_body_snapshot("en tung tur")
    assert s["sensation"] == "varm", s
    assert "0.90" in s["grundlag"], s["grundlag"]
    assert s["intensity"] > 0.8


def test_hoej_belastning_maerkes_tungt(monkeypatch, tmp_path):
    _krop(monkeypatch, tmp_path, belastning="critical", load=0.3)
    assert B.record_body_snapshot("presset")["sensation"] == "tung"


def test_erindringen_overlever_en_genstart(monkeypatch, tmp_path):
    """Det var hele fejlen: en modul-liste der doede med processen."""
    _krop(monkeypatch, tmp_path)
    B.reset_body_memory()
    B.record_body_snapshot("foer")
    # simuler en ny proces: modulet genindlaeses, intet i hukommelsen
    import importlib
    B2 = importlib.reload(B)
    assert B2.build_body_memory_surface()["snapshot_count"] == 1
    assert "foer" in B2.describe_body_memory()


def test_der_er_INTET_random_tilbage():
    """Et gaet med en paenere overflade er stadig et gaet.

    AST, ikke grep: docstringen citerer med vilje den gamle `random.choice`
    saa den naeste der laeser filen kan se hvad der stod. En grep-vagt ville
    fejle paa sin egen dokumentation — og saa ville man fjerne historikken for
    at faa testen groen.
    """
    import ast
    import inspect

    traen = ast.parse(inspect.getsource(B))
    brug = [n.lineno for n in ast.walk(traen)
            if isinstance(n, ast.Attribute)
            and getattr(n.value, "id", None) == "random"]
    assert not brug, f"kroppen gaetter igen paa linje {brug}"
    assert not any(isinstance(n, ast.Import) and any(a.name == "random" for a in n.names)
                   for n in ast.walk(traen)), "random er importeret igen"


def test_tikket_gemmer_kun_naar_kroppen_SKIFTER(monkeypatch, tmp_path):
    """Et snapshot hvert kvarter ville vaere en log, ikke en hukommelse."""
    _krop(monkeypatch, tmp_path, load=0.05, tryk=0.4)
    B.reset_body_memory()
    assert B.tick(30.0)["gemt"] is True
    assert B.tick(30.0)["gemt"] is False, "samme krop blev gemt to gange"
    _krop(monkeypatch, tmp_path, load=0.95, tryk=0.4)
    assert B.tick(30.0)["gemt"] is True, "et skift blev ikke husket"


def test_en_presset_krop_huskes_hver_gang(monkeypatch, tmp_path):
    """Det der goer ondt huskes, ogsaa naar det er det samme som sidst."""
    _krop(monkeypatch, tmp_path, belastning="high", load=0.3)
    B.reset_body_memory()
    assert B.tick(30.0)["gemt"] is True
    assert B.tick(30.0)["gemt"] is True


def test_en_krop_der_ikke_kan_laeses_vaelter_ikke_tikket(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "core.services.embodied_state.build_embodied_state_surface",
        lambda: (_ for _ in ()).throw(RuntimeError("ingen vaert")))
    assert B.tick(30.0) == {"gemt": False}
    assert B.record_body_snapshot("x") is None


def test_hukommelsen_er_afgraenset(monkeypatch, tmp_path):
    """En krop husker ikke alt."""
    _krop(monkeypatch, tmp_path)
    B.reset_body_memory()
    for i in range(B._MAX_SNAPSHOTS + 25):
        B.record_body_snapshot(f"tur {i}")
    gemt = state_store.load_json("body_memory", None)
    assert len(gemt) == B._MAX_SNAPSHOTS
    assert gemt[-1]["context"].endswith(str(B._MAX_SNAPSHOTS + 24))
