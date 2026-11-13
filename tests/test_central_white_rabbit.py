"""White Rabbit — serendipitets-motoren, og hvorfor dens dør skal stå stille.

Målt 13/11-2026: `build_white_rabbit_surface()` valgte en NY tilfældig dør ved
hvert kald. Matrix-ensemblet læser surfacen ved hver prompt-assembly, så hans
behov skiftede hvert prompt-build — det kunne aldrig ældes, og karakteren ville
stå i prompten for evigt med en ny sætning hver tur. Det er det modsatte af
«kom og gå efter behov».

Den kaldte også `_observe`, så en LÆSNING blev talt som en hændelse.
"""
from unittest import mock

from core.services import central_white_rabbit as wr


def test_doeren_er_dagstabil():
    a = wr.build_white_rabbit_surface()
    b = wr.build_white_rabbit_surface()
    assert a.get("door") == b.get("door"), "en ny dør pr. kald gør behovet umuligt at ælde"


def test_laesning_observerer_ikke():
    with mock.patch("core.services.central_core.central") as c:
        wr.build_white_rabbit_surface()
    assert c.return_value.observe.call_count == 0, "en læsning er ikke en hændelse"


def test_ingen_aabne_doere_er_aerligt():
    with mock.patch("core.services.central_white_rabbit._dark_doors", return_value=[]):
        s = wr.build_white_rabbit_surface()
    assert s.get("door") is None
    assert "glemt" in s.get("felt", "") or "Ingen" in s.get("felt", "")


def test_follow_rabbit_er_stadig_tilfaeldig_naar_man_beder_om_det():
    """Den målrettede udforskning må gerne være tilfældig — det er hele pointen.
    Det er kun LÆSNINGEN der skal stå stille."""
    with mock.patch("core.services.central_white_rabbit._dark_doors",
                    return_value=["a", "b", "c", "d"]), \
            mock.patch("core.services.central_white_rabbit._observe"):
        a = wr.follow_rabbit(seed=1)
        b = wr.follow_rabbit(seed=2)
    assert a["door"] in {"a", "b", "c", "d"}
    assert b["door"] in {"a", "b", "c", "d"}
