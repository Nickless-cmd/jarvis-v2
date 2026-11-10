"""To fejl der gjorde en genstart usynlig — målt 25/10-2026.

Bjørns sideopgave: «bekræftelse af genstart i prompten efter genstart».
Symptomet var at jeg startede i en NY samtale uden at vide at genstarten var
sket, selvom `_lever_til_samtalen` skrev posten korrekt til `inbox_items`.

Der var TO fejl, og den anden var den værste:

1. `genstart` blev nævnt NUL gange i `inbox_view.py`. Kilden skrev, visningen
   læste ikke — samme form som de tre foregående fejl i dette spor.

2. `db_inbox.liste_aktiv` sorterede `ORDER BY id ASC LIMIT 500`. Med 600
   rækker i tabellen tog den de ÆLDSTE 500, så de NYESTE åbne poster faldt
   ud mens gamle `done`/`drop` fyldte vinduet. Målt: 5 åbne `genstart`-poster
   var usynlige for visningen — og `venter_paa_dig` var 0, hvor den skulle
   have været 17.

Fejl 2 er ikke kosmetisk: en ÅBEN post forsvandt fordi noget gammelt og
AFGJORT kom først i id-rækkefølgen. Det rammer enhver kildetype, ikke kun
genstart.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox
from core.services import inbox_view

BRUGER = "bjorn"


@pytest.fixture
def lager(monkeypatch):
    """Poster i hukommelsen — `Kilder.poster` byttes ud, ikke DB'en."""
    state: list[dict] = []
    monkeypatch.setattr(
        inbox_view, "_aegte_poster", lambda _b: list(state))
    return state


@pytest.fixture
def db(monkeypatch, tmp_path):
    """Rigtig sqlite mod en midlertidig fil — samme form som test_db_inbox."""
    sti = tmp_path / "inbox.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti, timeout=5.0)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


def _raekke(pid: str, *, kildetype: str, status: str, beskrivelse: str = "") -> dict:
    return {
        "id": pid,
        "kildetype": kildetype,
        "status": status,
        "verificeret_ejer": db_inbox.EJER_UKENDT,
        "kraever_handling": False,
        "beskrivelse": beskrivelse or f"post {pid}",
        "created_at": "2026-10-25T12:00:00+00:00",
        "afgjort_at": "" if status == db_inbox.STATUS_AABEN else "2026-10-25T12:00:00+00:00",
        "output_sti": "",
        "output_bytes": None,
        "bloker": False,
    }


class TestGenstartProjiceres:
    def test_en_aaben_genstart_har_sin_egen_sektion(self, lager):
        """Fejl 1: posten blev skrevet men aldrig projiceret."""
        lager.append(_raekke("genstart-chat-abc", kildetype="genstart",
                             status=db_inbox.STATUS_AABEN,
                             beskrivelse="API'et er genstartet"))

        v = inbox_view.byg_indbakke(BRUGER)

        assert v["status"] == "ok"
        assert len(v["genstarter"]) == 1
        assert "genstartet" in v["genstarter"][0]["linje"].lower()

    def test_genstart_havner_ikke_i_venter_paa_dig(self, lager):
        """En genstart er noget jeg skal VIDE — ikke noget nogen skal svare på.

        Uden grenen faldt den i «VENTER PÅ DIG», fordi `verificeret_ejer` er
        `ukendt`: genstarten har intet levende run at verificere imod.
        """
        lager.append(_raekke("genstart-chat-abc", kildetype="genstart",
                             status=db_inbox.STATUS_AABEN))

        v = inbox_view.byg_indbakke(BRUGER)

        assert v["venter_paa_dig"] == []
        assert len(v["genstarter"]) == 1

    def test_genstart_gater_ikke(self, lager):
        """Den må kunne SES, aldrig nægte en mutation."""
        lager.append(_raekke("genstart-chat-abc", kildetype="genstart",
                             status=db_inbox.STATUS_AABEN))

        v = inbox_view.byg_indbakke(BRUGER)

        assert v["genstarter"][0]["kraever_handling"] is False

    def test_en_lukket_genstart_vises_ikke(self, lager):
        lager.append(_raekke("genstart-chat-abc", kildetype="genstart",
                             status="done"))

        v = inbox_view.byg_indbakke(BRUGER)

        assert v["genstarter"] == []


class TestGenaabnetPostBliverIkkeDraebtIgen:
    """Genåbningen skal rydde `vist_at`, ikke kun `afgjort_at` (målt 10/11-2026).

    Kæden der gjorde genstarten usynlig i drift:

    1. bekræftelsen leveres → `registrer_kilde` → posten var `drop` → genåbnet
    2. `luk_forældede_informerende` dropper informerende poster hvor
       `vist_at` er ældre end 6 timer — og `vist_at` var IKKE ryddet
    3. posten blev derfor dræbt igen ~2 min senere, og Bjørn så den aldrig

    Målt: `afgjort_at` 13:15:26 efter genstart 13:12:58, med `vist_at` fra
    dagen før. Det er samme fælde som `expires_at`, der blev ryddet i 2026.
    """

    def test_genaabning_rydder_vist_at(self, db):
        with db_inbox.connect() as conn:
            db_inbox._ensure_skema(conn)
            conn.execute(
                "INSERT INTO inbox_items (bruger_id, kildetype, kilde_id,"
                " status, verificeret_ejer, kraever_handling, beskrivelse,"
                " created_at, afgjort_at, vist_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (BRUGER, "genstart", "genstart-chat-abc", db_inbox.STATUS_DROP,
                 db_inbox.EJER_UKENDT, 0, "gammel bekræftelse",
                 "2026-11-09T16:00:00+00:00", "2026-11-09T18:00:00+00:00",
                 "2026-11-09T17:00:00+00:00"))
            conn.commit()

        r = db_inbox.genaabn_af_kilde(bruger_id=BRUGER, kilde_id="genstart-chat-abc")

        assert r["status"] == "ok"
        assert r["post"]["status"] == db_inbox.STATUS_AABEN
        assert r["post"]["vist_at"] == "", (
            "vist_at skal ryddes ved genåbning — ellers arver posten den "
            "visning der netop fik den til at blive udsat")

    def test_genaabnet_post_overlever_oprydningen(self, db):
        """Den ægte konsekvens: posten må ikke droppes igen ved næste sweep."""
        with db_inbox.connect() as conn:
            db_inbox._ensure_skema(conn)
            conn.execute(
                "INSERT INTO inbox_items (bruger_id, kildetype, kilde_id,"
                " status, verificeret_ejer, kraever_handling, beskrivelse,"
                " created_at, afgjort_at, vist_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (BRUGER, "genstart", "genstart-chat-abc", db_inbox.STATUS_DROP,
                 db_inbox.EJER_UKENDT, 0, "gammel bekræftelse",
                 "2026-11-09T16:00:00+00:00", "2026-11-09T18:00:00+00:00",
                 "2026-11-09T17:00:00+00:00"))
            conn.commit()

        db_inbox.genaabn_af_kilde(bruger_id=BRUGER, kilde_id="genstart-chat-abc")
        sweep = db_inbox.luk_forældede_informerende(timer=6, maks=500)

        with db_inbox.connect() as conn:
            rad = conn.execute(
                "SELECT status FROM inbox_items WHERE bruger_id=? AND kilde_id=?",
                (BRUGER, "genstart-chat-abc")).fetchone()

        assert sweep["opryddet"] == 0, "den genåbnede post må ikke rammes"
        assert rad["status"] == db_inbox.STATUS_AABEN, (
            "bekræftelsen blev genåbnet og derefter dræbt igen af sit eget "
            "arvede vist_at — præcis den tavshed posten findes for at undgå")


class TestAabnePosterForsvinderIkke:
    def test_aabne_poster_sorteres_foer_afgjorte(self, db):
        """Fejl 2: `ORDER BY id ASC LIMIT 500` tog de ÆLDSTE.

        Målt i produktion: 600 rækker, 500 i vinduet — de 5 åbne
        `genstart`-poster faldt ud bag 343 `done` + 157 `drop`.
        """
        with db_inbox.connect() as conn:
            db_inbox._ensure_skema(conn)
            # 600 afgjorte poster med LAVE id'er, derefter 5 åbne med HØJE.
            for i in range(600):
                conn.execute(
                    "INSERT INTO inbox_items (bruger_id, kildetype, kilde_id,"
                    " status, verificeret_ejer, kraever_handling, beskrivelse,"
                    " created_at, afgjort_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (BRUGER, "wakeup", f"gammel-{i:04d}",
                     "done", db_inbox.EJER_UKENDT, 0, "gammel",
                     "2026-10-01T00:00:00+00:00", "2026-10-01T00:00:00+00:00"))
            for i in range(5):
                conn.execute(
                    "INSERT INTO inbox_items (bruger_id, kildetype, kilde_id,"
                    " status, verificeret_ejer, kraever_handling, beskrivelse,"
                    " created_at, afgjort_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (BRUGER, "genstart", f"aaben-{i}",
                     db_inbox.STATUS_AABEN, db_inbox.EJER_UKENDT, 0, "aaben",
                     "2026-10-25T00:00:00+00:00", ""))
            conn.commit()

        vinduet = db_inbox.liste_aktiv(bruger_id=BRUGER, maks=500)

        aabne = [p for p in vinduet if p["status"] == db_inbox.STATUS_AABEN]
        assert len(aabne) == 5, (
            "en ÅBEN post må ikke forsvinde fordi noget gammelt og AFGJORT "
            f"kom først i id-rækkefølgen (fik {len(aabne)} af 5)")

    def test_afgjorte_poster_er_stadig_i_vinduet(self, db):
        """Retention skal stadig virke — rettelsen må ikke fjerne de lukkede.

        Visningen skal kunne SPRINGE en lukket post over, også når kilden
        stadig rapporterer den. Fjerner man dem helt, mister den evnen.
        """
        with db_inbox.connect() as conn:
            db_inbox._ensure_skema(conn)
            conn.execute(
                "INSERT INTO inbox_items (bruger_id, kildetype, kilde_id,"
                " status, verificeret_ejer, kraever_handling, beskrivelse,"
                " created_at, afgjort_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (BRUGER, "wakeup", "lukket-1", "done",
                 db_inbox.EJER_UKENDT, 0, "lukket",
                 "2026-10-25T00:00:00+00:00", "2026-10-25T00:00:00+00:00"))
            conn.commit()

        vinduet = db_inbox.liste_aktiv(bruger_id=BRUGER, maks=500)

        assert "lukket-1" in [p["kilde_id"] for p in vinduet]
