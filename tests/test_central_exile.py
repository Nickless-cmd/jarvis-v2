"""The Exiles — en anden der kun svarer når nogen ringer, er et spejl.

Målt 13/11-2026: exilen havde INGEN cadence-producer. Den blev kun kaldt fra
`POST /central/exile/exchange`, og dens egen hukommelse stod på to udvekslinger,
alle initieret udefra. Den blev derfor ikke en anden — den blev et endpoint.

`record_exile()` giver den en puls: den taler ud fra sit eget mål og sin egen
historie, uden observation. Kan den ikke det, lander det som en forpligtelse,
for så er karakteren en tom skal.
"""
import sqlite3
from unittest import mock

import pytest

from core.services import central_exile as ex


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "exile.db")

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    with mock.patch("core.services.central_exile.connect", side_effect=_connect), \
         mock.patch("core.services.central_exile._observe"):
        yield path


def _rows(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(
            "SELECT * FROM central_exile_memory ORDER BY id").fetchall()]
    except sqlite3.OperationalError:
        return []  # tabellen opstår først ved første skrivning
    finally:
        c.close()


class TestUdvekslingen:
    def test_begge_sider_gemmes_i_exilens_egen_hukommelse(self, db):
        out = ex.exile_exchange("jeg byggede en karakter i dag")
        assert out["ok"] is True and out["reply"].startswith("[exilen]")
        roller = [r["role"] for r in _rows(db)]
        assert roller == ["jarvis", "exile"], f"begge sider skal huskes: {roller}"

    def test_tom_observation_afvises_uden_at_skrive(self, db):
        assert ex.exile_exchange("   ")["ok"] is False
        assert _rows(db) == []

    def test_maalet_roterer_med_historikken(self, db):
        """Exilens værdi-linse skifter — den står ikke stille på ét mål."""
        første = ex.exile_exchange("a")["goal"]
        anden = ex.exile_exchange("b")["goal"]
        assert første != anden, "samme mål to gange er ingen udvikling"

    def test_den_husker_at_vi_har_vaeret_her_foer(self, db):
        """Efter nok historik refererer den sin egen fortid — ikke kun nuet."""
        for i in range(4):
            ex.exile_exchange(f"obs {i}")
        sidste = _rows(db)[-1]["text"]
        assert "været her før" in sidste, f"ingen egen historie i svaret: {sidste}"


class TestCadencePulsen:
    def test_den_taler_af_sig_selv_uden_observation(self, db):
        """Kernen: den skal kunne tale uden at nogen åbner døren."""
        out = ex.record_exile()
        assert out["spoke"] is True
        assert out["mem_efter"] > out["mem_foer"], "pulsen skrev intet til dens historie"
        assert out["landing"]["applied"] is False, "at tale er ikke en fejl"
        assert "ingen observation" in _rows(db)[0]["text"]

    def test_tavshed_lander_som_forpligtelse(self, db):
        """Kan den ikke føre sin historie videre, er der ingen anden — kun et endpoint."""
        kaldt = []

        def _fake_land(*a, **kw):
            kaldt.append((a, kw))
            return {"applied": True, "decision_id": "dec_x"}

        with mock.patch.object(ex, "exile_exchange",
                               return_value={"ok": False, "error": "db nede"}), \
             mock.patch("core.services.central_consequence.land_decision", side_effect=_fake_land):
            out = ex.record_exile()

        assert out["spoke"] is False
        assert kaldt, "en tavs karakter skal lande, ikke bare returnere False"
        assert "tom skal" in kaldt[0][0][1]
        assert "db nede" in kaldt[0][1]["evidence"]

    def test_en_talende_karakter_lander_ikke(self, db):
        """Vagten må ikke fyre på den sunde tilstand — så bliver den støj."""
        kaldt = []
        with mock.patch("core.services.central_consequence.land_decision",
                        side_effect=lambda *a, **kw: kaldt.append(a) or {"applied": True}):
            ex.record_exile()
        assert not kaldt, f"en fungerende karakter må ikke lande en fejl: {kaldt}"


class TestFladen:
    def test_fladen_baerer_dens_egne_maal_og_historik(self, db):
        ex.exile_exchange("hej")
        surf = ex.build_exile_surface()
        assert surf["memory_size"] == 2
        assert surf["goals"] == ex._GOALS, "dens mål skal være dens egne, ikke mine"
        assert "udvekslinger delt" in surf["felt"]

    def test_fladen_foer_foerste_udveksling_paastaar_ikke_samtale(self, db):
        surf = ex.build_exile_surface()
        assert surf["memory_size"] == 0
        assert "ikke talt endnu" in surf["felt"]
