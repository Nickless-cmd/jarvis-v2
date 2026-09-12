"""Oprydningen af foraeldreloese brain_index-raekker.

Fejlen var ikke at oprydningen var forkert - den fandtes ikke. En kommentar i
inferens-loekken lovede at raekken ville blive ryddet "by the next
consolidation pass", og den pass er en stub der returnerer 0. Der har aldrig
vaeret et `DELETE FROM brain_index` i repoet.

Derfor er den vigtigste proeve her ikke at sletningen virker, men at VAERNET
holder: «filen findes ikke» betyder det samme for én slettet post og for en
mappe der ikke er monteret, og kun det ene af dem er en oprydning.
"""
from __future__ import annotations

import pytest

from core.services import jarvis_brain as B


@pytest.fixture
def brain(isolated_runtime):
    B.brain_dir().mkdir(parents=True, exist_ok=True)
    return B


def _lav(n: int) -> list[str]:
    ider = []
    for i in range(n):
        e = B.write_entry(kind="fakta", title=f"post {i}", content="krop",
                          domain="projects", visibility="personal",
                          trigger="spontaneous")
        ider.append(e)
    return ider


def _antal() -> int:
    c = B.connect_index()
    try:
        return c.execute("SELECT COUNT(*) FROM brain_index").fetchone()[0]
    finally:
        c.close()


def _slet_fil(entry_id: str) -> None:
    c = B.connect_index()
    try:
        sti = c.execute("SELECT path FROM brain_index WHERE id = ?", (entry_id,)).fetchone()[0]
    finally:
        c.close()
    (B._workspace_root() / str(sti)).unlink()


def test_en_raekke_uden_fil_fjernes(brain):
    ider = _lav(20)
    _slet_fil(ider[0])
    r = B.prune_orphaned_index_rows()
    assert r["fjernet"] == 1 and r["afvist"] == 0
    assert _antal() == 19


def test_raekker_MED_fil_roeres_ikke(brain):
    """Kontrolarm. Uden den ville en funktion der slettede ALT bestaa ovenfor."""
    _lav(5)
    r = B.prune_orphaned_index_rows()
    assert r["fjernet"] == 0
    assert _antal() == 5


def test_VAERNET_afviser_naar_for_mange_mangler(brain):
    """En mappe der ikke er monteret ser ud som «alle filer er slettet».
    Uden vaernet ville den situation toemme indekset og se vellykket ud."""
    ider = _lav(10)
    for i in ider[:5]:          # 50% > loftet paa 10%
        _slet_fil(i)
    r = B.prune_orphaned_index_rows()
    assert r["afvist"] == 1 and r["fjernet"] == 0
    assert _antal() == 10, "intet maa vaere slettet naar koerslen afvises"


def test_vaernet_siger_hvor_mange_der_manglede(brain):
    ider = _lav(10)
    for i in ider[:5]:
        _slet_fil(i)
    assert B.prune_orphaned_index_rows()["foraeldreloese"] == 5


def test_manglende_mappe_goer_ingenting(brain):
    _lav(3)
    import shutil
    shutil.rmtree(B.brain_dir())
    r = B.prune_orphaned_index_rows()
    assert r == {"fjernet": 0, "foraeldreloese": 0, "afvist": 1}
    assert _antal() == 3


def test_reindex_once_KALDER_oprydningen(brain, monkeypatch):
    """Koblingen. Mekanismen fandtes ikke foer; nu skal den ogsaa naas."""
    kaldt: list[bool] = []
    monkeypatch.setattr(B, "prune_orphaned_index_rows",
                        lambda **k: kaldt.append(True) or {"fjernet": 0})
    from core.services.jarvis_brain_daemon import reindex_once
    reindex_once()
    assert kaldt == [True]
