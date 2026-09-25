"""Et mærke skal være sjældent, målt og vedvarende.

Målt 25/9-2026: `_tattoos` var en modul-global liste uden persistering, og
`create_tattoo` havde INGEN kalder. Overfladen sagde «Ingen tatoveringer» og
ville have sagt det for altid.

Kilden er nu `emotional_memory_anchors` (205.961 rækker). Men intensiteten
MÆTTER — 24 % ligger over 0,95 — så en tærskel alene ville give 49.299
«tatoveringer». Det der udskiller er TYPEN: 202.250 af rækkerne er
`perceptual_event`, altså perception, ikke begivenheder. Tilbage står
`cognitive_episode` (2393), `self_repair` (680) og `memory_heading` (597), og
af dem ligger 982 over 0,9 — ca. fem om dagen. Derfor også højst ét i døgnet.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import core.services.memory_tattoos as T
from core.runtime import state_store
import pytest


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
    state_store.save_json("memory_tattoos", [])
    yield



class _Conn:
    def __init__(self, raekke):
        self._raekke = raekke
        self.sidste_sql = ""
        self.sidste_arg: tuple = ()

    def execute(self, sql, args=()):
        self.sidste_sql, self.sidste_arg = sql, args
        return self

    def fetchone(self):
        return self._raekke

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _anker(monkeypatch, raekke):
    conn = _Conn(raekke)
    monkeypatch.setattr("core.runtime.db.connect", lambda *a, **k: conn)
    return conn


def test_maerket_overlever_en_genstart():
    """KERNEN. En modul-global liste døde med processen."""
    T.reset_memory_tattoos()
    T.create_tattoo("noget der prægede", "distressed", 0.95)

    import importlib
    T2 = importlib.reload(T)
    assert T2.build_memory_tattoos_surface()["tattoo_count"] == 1
    assert "noget der prægede" in T2.describe_tattoo()


def test_perceptuelle_ankre_kan_ALDRIG_blive_et_maerke():
    """202.250 af 205.961 er perception. Var de med, ville alt være et mærke."""
    assert "perceptual_event" not in T.MAERKBARE_TYPER
    assert set(T.MAERKBARE_TYPER) == {"self_repair", "cognitive_episode",
                                      "memory_heading"}


def test_tikket_saetter_et_maerke_fra_et_aegte_anker(monkeypatch):
    T.reset_memory_tattoos()
    conn = _anker(monkeypatch, ("a-1", "distressed", 0.97,
                                "Selvreparation udført: decision_review", None,
                                "2026-09-25T10:00:00+00:00"))
    ud = T.tick(30.0)
    assert ud["sat"] is True
    assert ud["maerke"]["event"] == "Selvreparation udført: decision_review"
    assert ud["maerke"]["intensity"] == 0.97
    assert ud["maerke"]["anchor_id"] == "a-1"
    # taerskelen og typerne skal FAKTISK vaere i forespoergslen
    assert T._MIN_INTENSITET in conn.sidste_arg
    for t in T.MAERKBARE_TYPER:
        assert t in conn.sidste_arg


def test_hoejst_ét_maerke_i_doegnet(monkeypatch):
    """Fem om dagen er for mange. Et mærke er hvad der prægede en DAG."""
    T.reset_memory_tattoos()
    _anker(monkeypatch, ("a-1", "euphoric", 0.99, "foerste", None, ""))
    assert T.tick(30.0)["sat"] is True
    _anker(monkeypatch, ("a-2", "euphoric", 0.99, "anden", None, ""))
    assert T.tick(30.0) == {"sat": False, "grund": "for tidligt"}


def test_samme_anker_maerkes_ikke_to_gange(monkeypatch, tmp_path):
    T.reset_memory_tattoos()
    _anker(monkeypatch, ("a-1", "euphoric", 0.99, "foerste", None, ""))
    T.tick(30.0)
    # ryk sidste maerke en uge tilbage saa doegn-reglen ikke blokerer
    maerker = state_store.load_json("memory_tattoos", [])
    maerker[-1]["created_at"] = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    state_store.save_json("memory_tattoos", maerker)
    assert T.tick(30.0) == {"sat": False, "grund": "allerede maerket"}


def test_intet_staerkt_nok_saetter_intet(monkeypatch):
    T.reset_memory_tattoos()
    _anker(monkeypatch, None)
    assert T.tick(30.0)["sat"] is False
    assert T.build_memory_tattoos_surface()["summary"] == "Ingen tatoveringer"


def test_et_anker_uden_note_faar_sin_udloeser(monkeypatch):
    """`cognitive_episode` har ingen note — kun JSON. Den skal stadig kunne
    saettes i en saetning."""
    T.reset_memory_tattoos()
    _anker(monkeypatch, ("a-9", "euphoric", 0.95, None,
                         '{"trigger": "visible-run:ollama/glm-5.2", "x": 1}', ""))
    assert T.tick(30.0)["maerke"]["event"] == "visible-run:ollama/glm-5.2"


def test_en_base_der_ikke_kan_naas_vaelter_ikke_tikket(monkeypatch):
    T.reset_memory_tattoos()
    monkeypatch.setattr("core.runtime.db.connect",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert T.tick(30.0) == {"sat": False, "grund": "ingen ankre"}


def test_der_er_INTET_random():
    """Modulet importerede `random` uden at bruge det. Det skal heller ikke
    snige sig ind."""
    import ast
    import inspect

    traen = ast.parse(inspect.getsource(T))
    assert not any(isinstance(n, ast.Import) and any(a.name == "random" for a in n.names)
                   for n in ast.walk(traen))
