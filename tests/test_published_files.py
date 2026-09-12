"""Udgivne filer skal haefte sig paa turen, ellers kan de ikke vises.

publish_file lagde filen i files/ og returnerede en URL — men turen bar den
aldrig. Maalt 12/9-2026 over 3.653 beskeder med content_json: NUL
assistent-beskeder havde en image/file-blok, mod fire bruger-beskeder.
Klienten renderer efter blokke, saa en fil Jarvis lavede kunne kun naevnes i
prosa med en adresse man selv skulle skrive af.

Samme hul som taenkningen havde, og samme loesning: laeg fra dig under turen,
tag imod ved persistering.
"""
from __future__ import annotations

import pytest

from core.services import published_files as P


@pytest.fixture(autouse=True)
def _rent():
    P._nulstil_for_tests()
    yield
    P._nulstil_for_tests()


def test_noteret_fil_kan_tages():
    P.note("run-1", filename="rapport.html", url="https://x/files/rapport.html",
           mime_type="text/html", size_bytes=120)
    poster = P.take("run-1")
    assert len(poster) == 1 and poster[0]["filename"] == "rapport.html"


def test_take_RYDDER_saa_naeste_tur_ikke_arver():
    """Uden det ville en fil fra forrige tur dukke op under et svar den intet
    havde med at goere."""
    P.note("run-1", filename="a.txt", url="u")
    assert len(P.take("run-1")) == 1
    assert P.take("run-1") == []


def test_uden_run_id_gemmes_intet():
    """En post uden tur kan ikke haeftes paa noget; at gemme den ville bare
    lade den ligge til den forkerte."""
    P.note("", filename="a.txt", url="u")
    assert P.take("") == []


def test_loft_pr_tur():
    """En tur der udgiver hundredvis af filer er en fejl i sig selv - og
    blok-arrayet skal ikke vokse ubegraenset fordi den fejl findes."""
    for i in range(P.MAKS_PR_TUR + 5):
        P.note("run-1", filename=f"f{i}.txt", url="u")
    assert len(P.take("run-1")) == P.MAKS_PR_TUR


def test_billede_bliver_image_resten_file():
    b = P.as_blocks([
        {"filename": "a.png", "url": "u1", "mime_type": "image/png"},
        {"filename": "b.html", "url": "u2", "mime_type": "text/html"},
    ])
    assert [x["type"] for x in b] == ["image", "file"]
    assert all(x["kilde"] == "published" for x in b)


def test_blokken_baerer_URL_ikke_attachment_id():
    """En udgivet fil hentes over /files/{navn}, ikke over det
    vedhaeftnings-scopede endpoint. Klienten skal kunne se forskel."""
    b = P.as_blocks([{"filename": "a.html", "url": "https://x/files/a.html"}])
    assert b[0]["url"] == "https://x/files/a.html"
    assert "attachment_id" not in b[0]


def test_poster_uden_navn_springes_over():
    """En halv reference er vaerre end ingen: klienten ville tegne et hul."""
    assert P.as_blocks([{"filename": "", "url": "u"}]) == []


def test_persisteringen_haefter_dem_bagest(monkeypatch):
    """Koblingen. Uden den kan alt ovenfor virke og stadig ikke vises."""
    from core.services import visible_runs_outcomes as O

    class _Run:
        run_id = "run-9"
    P.note("run-9", filename="ny.html", url="https://x/files/ny.html",
           mime_type="text/html")
    ud = O._med_udgivne_filer([{"type": "text", "text": "hej"}], _Run())
    assert [b["type"] for b in ud] == ["text", "file"]
    assert ud[-1]["filename"] == "ny.html"


def test_ingen_udgivne_filer_lader_blokkene_vaere(monkeypatch):
    """Kontrolarm. En tom blok ville faa klienten til at tegne et hul."""
    from core.services import visible_runs_outcomes as O

    class _Run:
        run_id = "run-tom"
    ind = [{"type": "text", "text": "hej"}]
    assert O._med_udgivne_filer(ind, _Run()) == ind


def test_persisteringen_KALDER_den_faktisk():
    """DEN egentlige kobling.

    Testen ovenfor kalder hjaelperen direkte og bestaar derfor ogsaa hvis
    kaldestedet forsvinder - maalt: fjernes linjen i content_json-grenen,
    bliver alle proever groenne alligevel. En hjaelper uden kalder viser
    ingenting, og det er praecis den fejl hele denne fil handler om.
    """
    import inspect
    from core.services import visible_runs_outcomes as O
    kilde = inspect.getsource(O)
    assert "_med_udgivne_filer(_blokke, run)" in kilde, (
        "content_json-grenen kalder ikke laengere _med_udgivne_filer - "
        "udgivne filer vil ikke naa klienten"
    )
