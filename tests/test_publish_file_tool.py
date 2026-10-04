"""`publish_file` skriver i BRUGERENS mappe (Bjørn 4/10-2026).

Den vigtigste påstand er ikke at stien er ny. Det er at to brugere med SAMME
filnavn ikke kan overskrive hinanden, og at en kontekstløs kalder slet ikke
får en mappe at skrive i.
"""
from __future__ import annotations

import pytest

from core.identity import workspace_context as wc
from core.tools.publish_file_tool import _exec_publish_file


@pytest.fixture(autouse=True)
def hjem(monkeypatch, tmp_path):
    """Eget JARVIS_HOME. `workspace_paths._jarvis_home()` læser env ved KALDET
    netop for det — ellers ville testen skrive i Bjørns rigtige filmappe."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def brugere(monkeypatch):
    """To kendte brugere. Den rigtige opslagsvej læser `users.json`/SQLite —
    uden en fast oversættelse ville testen måle maskinens bruger-tabel."""
    import core.runtime.workspace_paths as wp
    monkeypatch.setattr(wp, "_user_id_to_workspace_name",
                        lambda uid: {"u-bjorn": "bjorn", "u-lotte": "lotte"}[uid])


def _udgiv(uid: str, navn: str, indhold: str):
    tok = wc.set_context(workspace_name="x", user_id=uid, role="member")
    try:
        return _exec_publish_file({"filename": navn, "content": indhold})
    finally:
        wc.reset_context(tok)


def test_filen_lander_i_brugerens_EGEN_mappe(hjem):
    r = _udgiv("u-bjorn", "rapport.md", "mit indhold")
    assert r.get("status") != "error", r
    assert (hjem / "files" / "u" / "bjorn" / "rapport.md").read_text() == "mit indhold"
    # Og IKKE i den gamle faelles mappe.
    assert not (hjem / "files" / "rapport.md").exists()


def test_to_brugere_med_SAMME_navn_overskriver_ikke_hinanden(hjem):
    """Den flade mappe gjorde filnavnet globalt: to «rapport.md» var ÉN fil,
    og den sidste vandt. Det er ikke kun en lækage — det er datatab."""
    _udgiv("u-bjorn", "rapport.md", "bjoerns")
    _udgiv("u-lotte", "rapport.md", "lottes")
    assert (hjem / "files" / "u" / "bjorn" / "rapport.md").read_text() == "bjoerns"
    assert (hjem / "files" / "u" / "lotte" / "rapport.md").read_text() == "lottes"


def test_UDEN_bruger_udgives_der_INTET(hjem):
    """Fail-closed og typet. Før havde en kontekstløs kalder en mappe at
    skrive i, og den mappe var alles."""
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="")
    try:
        r = _exec_publish_file({"filename": "snig.md", "content": "x"})
    finally:
        wc.reset_context(tok)
    assert r["status"] == "error"
    assert "ingen bruger" in r["error"]
    assert list((hjem / "files").rglob("snig.md")) == []


@pytest.mark.parametrize("ondt", ["../../../etc/passwd", "/etc/passwd", "a/b.md"])
def test_en_sti_kan_ikke_skrive_udenfor(hjem, ondt):
    r = _udgiv("u-bjorn", ondt, "x")
    # Enten afvist, eller renset til et blot navn INDE i mappen.
    skrevne = [p for p in hjem.rglob("*") if p.is_file()]
    for p in skrevne:
        assert (hjem / "files" / "u" / "bjorn") in p.parents, f"skrev udenfor: {p}"
    if r.get("status") != "error":
        assert (hjem / "files" / "u" / "bjorn" / "passwd").exists() or \
               (hjem / "files" / "u" / "bjorn" / "b.md").exists()


def test_ingen_kopi_af_sti_reglen_i_vaerktoejet():
    """Kilde-vagt. Fire steder skal bruge SAMME layout-definition — ruten,
    signeringen, migreringen og dette værktøj. En egen sammensætning her
    ville være den fjerde kopi, og kopier i dette hus driver fra hinanden."""
    import ast
    import pathlib
    traeet = ast.parse(pathlib.Path("core/tools/publish_file_tool.py").read_text())
    navne = {n.name for x in ast.walk(traeet)
             if isinstance(x, ast.ImportFrom) for n in x.names}
    assert "published_file_path" in navne, "bruger ikke den faelles layout-definition"
    kilde = pathlib.Path("core/tools/publish_file_tool.py").read_text()
    assert 'JARVIS_HOME / "files"' not in kilde, "saetter stien sammen selv"
