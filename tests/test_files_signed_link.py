"""Ruten, afgrænsningen og middleware-fritagelsen for udgivne filer.

Bjørn 4/10-2026: «filer skal være per bruger». Tre lag, og de måles hver for
sig — lag-1-dækning skjuler lag-2-huller, målt fire gange i dette hus samme
døgn:

* **Ruten** serverer kun MINE filer, og udsteder kun links til MINE filer.
* **Signaturen** bærer workspacet, så den enes link ikke passer på den andens
  fil med samme navn.
* **Middlewaren** slipper kun en GET af præcis den signerede fil forbi.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from core.identity import workspace_context as wc
from core.services import file_links

BJORN, LOTTE = "u-bjorn", "u-lotte"


@pytest.fixture(autouse=True)
def noegle(monkeypatch):
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "test-grundlag-123")


@pytest.fixture(autouse=True)
def brugere(monkeypatch):
    import core.runtime.workspace_paths as wp
    monkeypatch.setattr(wp, "_user_id_to_workspace_name",
                        lambda uid: {BJORN: "bjorn", LOTTE: "lotte"}[uid])


@pytest.fixture
def hjem(monkeypatch, tmp_path):
    """Rigtige mapper. Ruten slår filen op på disken, så en mock ville måle
    sin egen stub frem for betingelsen «filen skal være din»."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    for ws in ("bjorn", "lotte"):
        d = tmp_path / "files" / "u" / ws
        d.mkdir(parents=True)
        (d / "rapport.pdf").write_bytes(f"%PDF {ws}".encode())
    (tmp_path / "files" / "u" / "bjorn" / "kun-bjorns.md").write_text("hemmelig")
    # Den GAMLE faelles mappe findes stadig paa disken under migreringen.
    (tmp_path / "files" / "gammel-faelles.md").write_text("fra foer")
    return tmp_path


def _som(uid: str):
    return wc.set_context(workspace_name="x", user_id=uid, role="member")


def _foresp(sti: str, metode: str = "GET", query: str = ""):
    from starlette.requests import Request
    return Request({
        "type": "http", "method": metode, "path": sti, "raw_path": sti.encode(),
        "query_string": query.encode(), "headers": [], "scheme": "http",
        "server": ("test", 80), "root_path": "", "http_version": "1.1",
    })


# ── Afgrænsningen ──────────────────────────────────────────────────────────

def test_jeg_henter_MIN_egen_fil(hjem):
    from apps.api.jarvis_api.routes.files import download_file
    tok = _som(BJORN)
    try:
        svar = download_file("rapport.pdf")
        assert svar.path.read_bytes() == b"%PDF bjorn"
    finally:
        wc.reset_context(tok)


def test_samme_navn_giver_HVER_sin_fil(hjem):
    """Det flade lager gjorde filnavnet globalt. Nu betyder «rapport.pdf»
    noget forskelligt for de to."""
    from apps.api.jarvis_api.routes.files import download_file
    for uid, forventet in ((BJORN, b"%PDF bjorn"), (LOTTE, b"%PDF lotte")):
        tok = _som(uid)
        try:
            assert download_file("rapport.pdf").path.read_bytes() == forventet
        finally:
            wc.reset_context(tok)


def test_jeg_kan_IKKE_hente_en_andens_fil_og_faar_404_ikke_403(hjem):
    """404, ikke 403: et 403 ville fortælle at filen FINDES hos en anden.
    En liste over naboens filnavne er også en lækage."""
    from apps.api.jarvis_api.routes.files import download_file
    tok = _som(LOTTE)
    try:
        with pytest.raises(HTTPException) as e:
            download_file("kun-bjorns.md")
        assert e.value.status_code == 404
    finally:
        wc.reset_context(tok)


def test_den_GAMLE_faelles_mappe_naas_IKKE(hjem):
    """Ingen fallback. Et fald til den fælles mappe ville være nøjagtig den
    lækage afgrænsningen lukker — og det ville ske tavst."""
    from apps.api.jarvis_api.routes.files import download_file
    tok = _som(BJORN)
    try:
        with pytest.raises(HTTPException) as e:
            download_file("gammel-faelles.md")
        assert e.value.status_code == 404
    finally:
        wc.reset_context(tok)


def test_listningen_viser_KUN_mine(hjem):
    from apps.api.jarvis_api.routes.files import list_files
    tok = _som(LOTTE)
    try:
        navne = {f["name"] for f in list_files()["files"]}
    finally:
        wc.reset_context(tok)
    assert navne == {"rapport.pdf"}
    assert "kun-bjorns.md" not in navne and "gammel-faelles.md" not in navne


def test_UDEN_bruger_svarer_ruten_401(hjem):
    from apps.api.jarvis_api.routes.files import download_file, list_files
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="")
    try:
        for kald in (lambda: download_file("rapport.pdf"), list_files):
            with pytest.raises(HTTPException) as e:
                kald()
            assert e.value.status_code == 401
    finally:
        wc.reset_context(tok)


# ── Mint-ruten ─────────────────────────────────────────────────────────────

def test_jeg_kan_kun_udstede_link_til_MINE_filer(hjem):
    """Ellers ville signeringen være vejen UDENOM afgrænsningen frem for en
    del af den."""
    from apps.api.jarvis_api.routes.files import LinkOenske, udsted_link
    tok = _som(LOTTE)
    try:
        with pytest.raises(HTTPException) as e:
            udsted_link(LinkOenske(filename="kun-bjorns.md"))
        assert e.value.status_code == 404
        r = udsted_link(LinkOenske(filename="rapport.pdf"))
        assert "ws=lotte" in r["url"]
    finally:
        wc.reset_context(tok)


@pytest.mark.parametrize("ondt", ["../../etc/passwd", "mappe/fil.pdf", "", "   "])
def test_mint_ruten_afviser_en_sti(hjem, ondt):
    from apps.api.jarvis_api.routes.files import LinkOenske, udsted_link
    tok = _som(BJORN)
    try:
        with pytest.raises(HTTPException) as e:
            udsted_link(LinkOenske(filename=ondt))
        assert e.value.status_code == 400
    finally:
        wc.reset_context(tok)


def test_uden_signering_svarer_mint_ruten_503(hjem, monkeypatch):
    from apps.api.jarvis_api.routes.files import LinkOenske, udsted_link
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "")
    tok = _som(BJORN)
    try:
        with pytest.raises(HTTPException) as e:
            udsted_link(LinkOenske(filename="rapport.pdf"))
        assert e.value.status_code == 503
    finally:
        wc.reset_context(tok)


# ── Det signerede link ende til ende ───────────────────────────────────────

def test_et_signeret_link_henter_den_SIGNEREDE_brugers_fil(hjem):
    """Uden token findes ingen kontekst, så `ws` fra adressen afgør mappen —
    og middlewaren har allerede verificeret signaturen over netop den."""
    from apps.api.jarvis_api.routes.files import download_file
    r = file_links.signer("rapport.pdf", workspace="lotte")
    svar = download_file("rapport.pdf", ws="lotte")
    assert svar.path.read_bytes() == b"%PDF lotte"
    assert r["status"] == "ok"


def test_en_AUTENTIFICERET_bruger_kan_ikke_saette_ws_og_laese_med(hjem):
    """`ws` gælder KUN når der intet token er. Ellers kunne enhver
    autentificeret bruger læse naboens filer med én querystring."""
    from apps.api.jarvis_api.routes.files import download_file
    tok = _som(LOTTE)
    try:
        with pytest.raises(HTTPException) as e:
            download_file("kun-bjorns.md", ws="bjorn")
        assert e.value.status_code == 404
    finally:
        wc.reset_context(tok)


@pytest.mark.parametrize("ondt", ["../bjorn", "a/b", "..", "", "/bjorn"])
def test_et_ws_der_er_en_STI_afvises_af_ruten(hjem, ondt):
    from apps.api.jarvis_api.routes.files import download_file
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="")
    try:
        with pytest.raises(HTTPException) as e:
            download_file("rapport.pdf", ws=ondt)
        assert e.value.status_code == 401
    finally:
        wc.reset_context(tok)


# ── Middleware-fritagelsen ─────────────────────────────────────────────────

def _fritaget(sti, query, metode="GET"):
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    return _er_signeret_filhentning(_foresp(sti, metode, query))


def test_et_gyldigt_link_slipper_forbi_auth():
    r = file_links.signer("rapport.pdf", workspace="bjorn")
    assert _fritaget("/files/rapport.pdf",
                     f"ws=bjorn&udloeb={r['udloeb']}&sig={r['sig']}") is True


def test_signaturen_gaelder_KUN_det_signerede_workspace():
    """Kernen i afgrænsningen: Lottes link må ikke åbne Bjørns fil."""
    r = file_links.signer("rapport.pdf", workspace="lotte")
    q = f"udloeb={r['udloeb']}&sig={r['sig']}"
    assert _fritaget("/files/rapport.pdf", f"ws=lotte&{q}") is True
    assert _fritaget("/files/rapport.pdf", f"ws=bjorn&{q}") is False


def test_UDEN_ws_slipper_intet_forbi():
    r = file_links.signer("rapport.pdf", workspace="bjorn")
    assert _fritaget("/files/rapport.pdf",
                     f"udloeb={r['udloeb']}&sig={r['sig']}") is False


def test_UDEN_signatur_slipper_INTET_forbi():
    assert _fritaget("/files/rapport.pdf", "ws=bjorn") is False


def test_signaturen_gaelder_kun_den_signerede_FIL():
    r = file_links.signer("min-egen.pdf", workspace="bjorn")
    assert _fritaget("/files/en-andens.pdf",
                     f"ws=bjorn&udloeb={r['udloeb']}&sig={r['sig']}") is False


def test_en_POST_slipper_ALDRIG_forbi_paa_en_signatur():
    r = file_links.signer("rapport.pdf", workspace="bjorn")
    assert _fritaget("/files/rapport.pdf",
                     f"ws=bjorn&udloeb={r['udloeb']}&sig={r['sig']}", "POST") is False


def test_LISTNINGEN_slipper_ikke_forbi_paa_et_fil_link():
    r = file_links.signer("rapport.pdf", workspace="bjorn")
    q = f"ws=bjorn&udloeb={r['udloeb']}&sig={r['sig']}"
    assert _fritaget("/files/", q) is False
    assert _fritaget("/files/a/b.pdf", q) is False


def test_en_anden_rute_kan_ikke_laane_signaturen():
    r = file_links.signer("rapport.pdf", workspace="bjorn")
    q = f"ws=bjorn&udloeb={r['udloeb']}&sig={r['sig']}"
    for sti in ("/chat/history", "/api/jobs", "/attachments/rapport.pdf"):
        assert _fritaget(sti, q) is False


def test_et_URL_kodet_filnavn_verificerer():
    from urllib.parse import quote
    navn = "oktober tal æøå.xlsx"
    r = file_links.signer(navn, workspace="bjorn")
    assert _fritaget(f"/files/{quote(navn)}",
                     f"ws=bjorn&udloeb={r['udloeb']}&sig={r['sig']}") is True


def test_fritagelsen_fejler_LUKKET_naar_den_ikke_kan_afgoeres(monkeypatch, caplog):
    import logging
    import core.services.file_links as fl
    def eksploder(*a, **k):
        raise RuntimeError("signerings-laget er nede")
    monkeypatch.setattr(fl, "verificer", eksploder)
    with caplog.at_level(logging.WARNING):
        assert _fritaget("/files/rapport.pdf",
                         f"ws=bjorn&udloeb=9999999999&sig={'a'*64}") is False
    assert any("fil-signatur" in x.message for x in caplog.records), \
        "fritagelsen fejlede TAVST"
