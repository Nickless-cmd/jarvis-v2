"""Loftet på `brain_temporal_edges` skal gælde ved SKRIVNING, ikke ved oprydning.

Målt 27/9-2026 på CT105: `TEMPORAL_EDGE_MAX_PER_NODE` (64) fandtes kun i
`prune_dense_edges`, som kører én gang i døgnet. Skriveren havde intet loft.

Gennemsnittet så fint ud — en ny post skriver ~50 kanter, under loftet. Det var
udskriderne: to poster fra samme formiddag havde 8.024 kanter HVER, 125 gange
loftet, og stod for 16.048 af dagens 18.304 kanter. Oprydningen ville have
fjernet 15.945 rækker næste gang den kørte, altså op til et døgn senere.

Læseren tager MAX(confidence) pr. kandidat. Af den nye posts egne kanter læses
altså nøjagtig ÉN. Testene her pinner at loftet skærer, at det skærer de
SVAGESTE (ikke bare de sidst mødte), og at tallet kommer fra konstanten.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

import numpy as np
import pytest

import core.services.brain_vector_cache as bvc
import core.services.jarvis_brain as jb
import core.services.multi_signal_retrieval as msr


NU = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def brain_db(tmp_path, monkeypatch):
    sti = tmp_path / "brain_index.sqlite"
    monkeypatch.setattr(jb, "index_db_path", lambda: sti)
    bvc.ryd()
    yield sti
    bvc.ryd()


def _post(eid: str) -> jb.BrainEntry:
    return jb.BrainEntry(
        id=eid, kind="fakta", visibility="personal", domain="test",
        title=eid, content="indhold", created_at=NU, updated_at=NU,
        last_used_at=None, salience_base=0.5, salience_bumps=0,
        importance=0.5, related=[], tags=[], trigger="spontaneous",
        status="active",
    )


def _kandidater(antal: int) -> None:
    v = np.ones(8, dtype=np.float32)
    conn = jb.connect_index()
    try:
        for i in range(antal):
            conn.execute(
                """INSERT OR REPLACE INTO brain_index
                   (id, path, kind, visibility, domain, title, created_at,
                    updated_at, file_hash, embedding, embedding_dim, indexed_at)
                   VALUES (?, ?, 'fakta', 'personal', 'test', ?, ?, ?, 'h', ?, 8, ?)""",
                (f"brn_k{i:04d}", f"p/k{i}.md", f"k{i}",
                 NU.isoformat(), NU.isoformat(), v.tobytes(), NU.isoformat()),
            )
        conn.commit()
    finally:
        conn.close()


def _skrevne_konfidenser(antal_kandidater: int, konfidenser, monkeypatch) -> list[float]:
    """Kør `infer_temporal_edges` med kendte konfidenser og se hvad der blev skrevet."""
    _kandidater(antal_kandidater)
    monkeypatch.setattr(jb, "read_entry", lambda eid: _post(eid))
    monkeypatch.setattr(jb, "_embed_text", lambda t: np.ones(8, dtype=np.float32))
    monkeypatch.setattr(jb, "_extract_text_for_entry",
                        lambda eid, rel_path=None, title=None: "tekst")
    monkeypatch.setattr(msr, "entity_overlap_score", lambda a, b: 0.0)

    koe = iter(konfidenser)
    monkeypatch.setattr(jb, "_compute_temporal_confidence",
                        lambda **kw: next(koe))

    skrevet: list[tuple] = []
    monkeypatch.setattr(jb, "_store_temporal_edges_batch",
                        lambda kanter, now=None: skrevet.extend(kanter))

    antal = jb.infer_temporal_edges("brn_ny", now=NU)
    assert antal == len(skrevet), "returtallet skal være det der faktisk blev skrevet"
    return [k[2] for k in skrevet]


class TestLoftetSkaerer:
    def test_over_loftet_skrives_kun_max_per_node(self, brain_db, monkeypatch) -> None:
        loft = jb.TEMPORAL_EDGE_MAX_PER_NODE
        konf = [0.5 + i / 1000.0 for i in range(loft + 30)]
        skrevet = _skrevne_konfidenser(loft + 30, konf, monkeypatch)
        assert len(skrevet) == loft

    def test_under_loftet_skrives_alt(self, brain_db, monkeypatch) -> None:
        konf = [0.5 + i / 1000.0 for i in range(10)]
        skrevet = _skrevne_konfidenser(10, konf, monkeypatch)
        assert len(skrevet) == 10
        assert sorted(skrevet) == sorted(konf)

    def test_praecis_paa_loftet_skaeres_ingenting(self, brain_db, monkeypatch) -> None:
        """Grænsetilfældet. Et `>=` i stedet for `>` ville stadig give 64 rækker,
        men et `[:loft-1]` ville ikke — og kun denne test ser forskellen."""
        loft = jb.TEMPORAL_EDGE_MAX_PER_NODE
        konf = [0.5 + i / 1000.0 for i in range(loft)]
        skrevet = _skrevne_konfidenser(loft, konf, monkeypatch)
        assert len(skrevet) == loft
        assert sorted(skrevet) == sorted(konf)


class TestDetErDeStaerkesteDerOverlever:
    def test_de_svageste_skaeres_væk_uanset_raekkefoelge(
        self, brain_db, monkeypatch
    ) -> None:
        """Uden sorteringen ville de 64 FØRST mødte overleve.

        Konfidenserne er blandet, så «de første 64» og «de 64 største» er to
        forskellige mængder. En `pending_edges[:64]` uden sortering giver et
        andet svar her — og det er hele pointen med testen.
        """
        loft = jb.TEMPORAL_EDGE_MAX_PER_NODE
        antal = loft + 40
        alle = [round(0.50 + i * 0.004, 4) for i in range(antal)]
        blandet = list(alle)
        random.Random(1312).shuffle(blandet)
        assert sorted(blandet[:loft]) != sorted(alle[-loft:]), (
            "blandingen skal faktisk adskille «de første» fra «de største»"
        )

        skrevet = _skrevne_konfidenser(antal, blandet, monkeypatch)

        assert sorted(skrevet) == sorted(alle[-loft:])
        assert min(skrevet) > max(sorted(alle)[: antal - loft])


class TestTalletKommerFraKonstanten:
    def test_loftet_er_ikke_et_tal_i_koden(self) -> None:
        """Skriver og oprydning skal bruge SAMME konstant — det var netop to
        tal om samme ting, sat hvert sit sted, der lod tabellen vokse til
        2,81 mio. rækker uden at oprydningen kunne bide."""
        import inspect
        kilde = inspect.getsource(jb.infer_temporal_edges)
        assert "TEMPORAL_EDGE_MAX_PER_NODE" in kilde
        assert inspect.signature(jb.prune_dense_edges).parameters[
            "max_per_node"
        ].default == jb.TEMPORAL_EDGE_MAX_PER_NODE

    def test_et_hoejere_loft_skriver_flere(self, brain_db, monkeypatch) -> None:
        """Loftet skal faktisk LÆSES fra konstanten, ikke bare nævnes i kilden."""
        monkeypatch.setattr(jb, "TEMPORAL_EDGE_MAX_PER_NODE", 5)
        konf = [0.5 + i / 1000.0 for i in range(20)]
        skrevet = _skrevne_konfidenser(20, konf, monkeypatch)
        assert len(skrevet) == 5
