"""Tests for `core/services/chat_crypto.py` (spec §16.2, plan-task 3.3).

Målt på CT105 27/9-2026: `chat_messages.content` var klartekst for ALLE — også
for de tre medlemmer (Mikkel 778 beskeder, Lotte 231, Michelle 162).
Workspace-filerne var krypteret for non-owners; chat-tabellen var det ikke.

Den farligste fejl her er ikke at kryptere for lidt. Det er at kryptere for
meget: 25.212 af 74.411 rækker har tomt `user_id`, og 62.306 ligger i Bjørns
eget workspace. En fail-safe-krypter-alt-ukendt ville gøre hans egen historik
ulæselig, og ingen ville opdage det før de ledte. Derfor handler over halvdelen
af testene her om hvad modulet IKKE krypterer.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import core.services.chat_crypto as cc


@dataclass
class FalskBruger:
    discord_id: str
    name: str
    role: str
    workspace: str


# Id'erne er OPDIGTEDE. Husstandens rigtige bruger-id'er hører ikke til i
# en testfil — detect-secrets fangede dem, og reglen står uafhængigt af
# det: det er navnene og RÆKKETALLENE der bærer forklaringen her.
BRUGERE = [
    FalskBruger("owner-id-opdigtet", "Ejeren", "owner", "bjorn"),
    FalskBruger("partner-id-opdigtet", "Partneren", "partner", "michelle"),
    FalskBruger("member-a-id-opdigtet", "Medlem A", "member", "mikkel"),
    FalskBruger("member-b-id-opdigtet", "Medlem B", "member", "lotte"),
]


@pytest.fixture(autouse=True)
def stub(monkeypatch):
    """Rigtige brugere, forudsigelige nøgler — ingen keyring, ingen filer."""
    import core.identity.users as users
    import core.services.keyring_store as ks
    monkeypatch.setattr(users, "load_users", lambda: list(BRUGERE))
    monkeypatch.setattr(ks, "get_user_key",
                        lambda uid: (str(uid).encode("utf-8") * 32)[:32])
    monkeypatch.delenv("JARVIS_CHAT_ENCRYPTION", raising=False)


class TestHvadDerIKKEKrypteres:
    """Landminen: 25.212 rækker har tomt user_id og er Bjørns."""

    @pytest.mark.parametrize("ws,uid,hvem", [
        ("", "", "tomt begge (25.212 raekker)"),
        ("bjorn", "owner-id-opdigtet", "Bjoerns eget workspace (62.306)"),
        ("bjorn", "", "bjorn-workspace uden bruger (13.792)"),
        ("default", "", "default-bucket (9.053)"),
        ("default", "owner-id-opdigtet", "default med Bjoerns id (147)"),
        ("public", "bjorn", "public med literal 'bjorn' (94)"),
        ("public", "system", "public med 'system' (57)"),
        ("", "test-user", "ukendt id (5)"),
        ("findes-ikke", "hverken-eller", "ukendt workspace OG bruger"),
    ])
    def test_ikke_medlem_giver_klartekst(self, ws, uid, hvem) -> None:
        assert cc.medlem_for_raekke(workspace_name=ws, user_id=uid) is None, hvem
        ud = cc.krypter_raekke({"workspace_name": ws, "user_id": uid,
                                "content": "hemmeligt"})
        assert ud["content"] == "hemmeligt", hvem
        assert ud["encrypted"] == 0, hvem

    def test_ukendt_bruger_krypteres_IKKE(self) -> None:
        """Modsat `workspace_crypto.should_encrypt`, og med vilje.

        For en fil er «ukendt → krypter» rigtigt. For en chat-række ville det
        låse ejerens egen historik, fordi ukendt dér betyder «tom kolonne».
        """
        from core.services.workspace_crypto import should_encrypt
        assert should_encrypt("en-vildt-fremmed-id") is True
        assert cc.medlem_for_raekke(user_id="en-vildt-fremmed-id") is None

    def test_autentificeret_medlem_uden_registrering_afvises(self, monkeypatch) -> None:
        import core.identity.workspace_context as context
        monkeypatch.setattr(context, "current_role", lambda: "member")
        with pytest.raises(RuntimeError, match="member key"):
            cc.krypter_raekke({"user_id": "ukendt", "content": "private"})

    def test_brugerlisten_utilgaengelig_giver_klartekst(self, monkeypatch) -> None:
        """At kryptere på et gæt om hvem rækken er, kan ikke fortrydes."""
        import core.identity.users as users

        def i_stykker():
            raise OSError("brugerfilen kunne ikke læses")

        monkeypatch.setattr(users, "load_users", i_stykker)
        assert cc.medlem_for_raekke(workspace_name="mikkel") is None
        ud = cc.krypter_raekke({"workspace_name": "mikkel", "content": "hej"})
        assert ud["content"] == "hej" and ud["encrypted"] == 0


class TestHvadDerKrypteres:
    @pytest.mark.parametrize("ws,uid,ventet", [
        ("mikkel", "", "member-a-id-opdigtet"),
        ("lotte", "", "member-b-id-opdigtet"),
        ("michelle", "", "partner-id-opdigtet"),
        ("", "member-a-id-opdigtet", "member-a-id-opdigtet"),
        ("", "partner-id-opdigtet", "partner-id-opdigtet"),
    ])
    def test_medlem_findes_paa_workspace_eller_bruger(self, ws, uid, ventet) -> None:
        assert cc.medlem_for_raekke(workspace_name=ws, user_id=uid) == ventet

    def test_partner_taeller_som_medlem(self) -> None:
        """Michelle er `partner`, ikke `member` — men hun er ikke owner."""
        assert cc.medlem_for_raekke(workspace_name="michelle") is not None

    def test_indholdet_er_vaek_af_cifferteksten(self) -> None:
        ud = cc.krypter_raekke({
            "workspace_name": "mikkel", "user_id": "member-a-id-opdigtet",
            "content": "jeg spillede 300 timer", "reasoning_content": "tanker",
            "content_json": '{"a": "b"}',
        })
        assert ud["encrypted"] == 1
        for felt in ("content", "reasoning_content", "content_json"):
            assert cc.er_krypteret(ud[felt]), felt
        samlet = " ".join(str(ud[f]) for f in ("content", "reasoning_content", "content_json"))
        for laek in ("300 timer", "tanker", '"a"'):
            assert laek not in samlet, laek

    def test_rundtur_giver_praecis_det_samme(self) -> None:
        original = {
            "workspace_name": "lotte", "user_id": "",
            "content": "Æbler, øl og ål — 100 % identisk?\n\nlinje to",
            "reasoning_content": "", "content_json": None,
        }
        krypteret = cc.krypter_raekke(original)
        tilbage = cc.dekrypter_raekke(krypteret)
        assert tilbage["content"] == original["content"]
        assert original["content"] != krypteret["content"]

    def test_tomme_felter_roeres_ikke(self) -> None:
        ud = cc.krypter_raekke({"workspace_name": "mikkel", "content": "x",
                                "reasoning_content": "", "content_json": None})
        assert ud["reasoning_content"] == ""
        assert ud["content_json"] is None

    def test_dobbelt_kryptering_sker_ikke(self) -> None:
        en = cc.krypter_raekke({"workspace_name": "mikkel", "content": "hej"})
        to = cc.krypter_raekke(en)
        assert to["content"] == en["content"]
        assert cc.dekrypter_raekke(to)["content"] == "hej"


class TestAdskillelseMellemBrugere:
    def test_en_members_nogle_aabner_ikke_en_andens(self) -> None:
        """Nordstjernen §3: ingen må kunne læse en andens private session."""
        mikkels = cc.krypter("Mikkels besked", "member-a-id-opdigtet")
        med_lottes = cc.dekrypter(mikkels, "member-b-id-opdigtet")
        assert med_lottes == mikkels, "en anden nøgle gav klartekst"
        assert cc.dekrypter(mikkels, "member-a-id-opdigtet") == "Mikkels besked"

    def test_ulaeselig_raekke_vaelter_ikke_samtalen(self) -> None:
        """Slettet bruger (GDPR §15.2) eller beskadiget række: vis cifferteksten."""
        import core.services.keyring_store as ks
        raa = cc.krypter("noget", "member-a-id-opdigtet")

        def ingen_noegle(uid):
            raise KeyError("nøglen er slettet")

        ks_get = ks.get_user_key
        try:
            ks.get_user_key = ingen_noegle
            assert cc.dekrypter(raa, "member-a-id-opdigtet") == raa
        finally:
            ks.get_user_key = ks_get


class TestNoedbremsen:
    def test_taendt_som_standard(self, monkeypatch) -> None:
        """Default TIL er hele pointen: et flag der forsvandt er grunden til
        at filerne har ligget i klartekst siden 14. juni."""
        monkeypatch.delenv("JARVIS_CHAT_ENCRYPTION", raising=False)
        assert cc.kryptering_slaaet_til() is True
        assert cc.krypter_raekke(
            {"workspace_name": "mikkel", "content": "x"})["encrypted"] == 1

    @pytest.mark.parametrize("vaerdi", ["0", "false", "no", "off", "OFF"])
    def test_kan_slukkes_eksplicit(self, monkeypatch, vaerdi) -> None:
        monkeypatch.setenv("JARVIS_CHAT_ENCRYPTION", vaerdi)
        assert cc.kryptering_slaaet_til() is False
        ud = cc.krypter_raekke({"workspace_name": "mikkel", "content": "x"})
        assert ud["content"] == "x" and ud["encrypted"] == 0

    @pytest.mark.parametrize("vaerdi", ["", "1", "true", "ja", "hvadsomhelst"])
    def test_alt_andet_er_taendt(self, monkeypatch, vaerdi) -> None:
        monkeypatch.setenv("JARVIS_CHAT_ENCRYPTION", vaerdi)
        assert cc.kryptering_slaaet_til() is True


class TestKlartekstPassererUroert:
    def test_dekrypter_paa_klartekst_er_en_no_op(self) -> None:
        assert cc.dekrypter("almindelig tekst", "member-a-id-opdigtet") == "almindelig tekst"
        assert cc.er_krypteret("almindelig tekst") is False

    def test_dekrypter_raekke_uden_krypteret_felt_returnerer_samme_objekt(self) -> None:
        r = {"workspace_name": "mikkel", "content": "klar"}
        assert cc.dekrypter_raekke(r) is r


class TestHeleVejenIgennem:
    """Usmocket ved sømmen: skriv en rigtig besked, læs den rå række i
    databasen, og læs den igen gennem sessions-læseren.

    Enhedstests på `krypter_raekke` alene kan ikke se om koblingen mangler —
    og «bygget, aldrig tilsluttet» er husets hyppigste fejl.
    """

    @pytest.fixture
    def db(self, tmp_path, monkeypatch):
        """Egen tom database — conftest'ens delte shield ville lade rækker fra
        andre tests forstyrre tællingerne her."""
        import core.runtime.db_core as dbc
        sti = tmp_path / "jarvis.db"
        monkeypatch.setenv("JARVIS_DB_NOPOOL", "1")
        monkeypatch.setattr(dbc, "_POOL_DISABLED", True, raising=False)
        monkeypatch.setattr(dbc, "DB_PATH", sti, raising=False)
        from core.runtime.db_schema import init_db
        init_db()
        # Sessionerne skrives direkte: `create_chat_session` vælger sit eget
        # id, og testene her skal kunne nævne sessionen ved navn.
        with dbc.connect() as conn:
            for sid in ("s-mikkel", "s-bjorn", "s-tom", "s-lotte"):
                conn.execute(
                    "INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                    "VALUES (?, 'test', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
                    (sid,))
            conn.commit()
        return sti

    @staticmethod
    def _raa(sti, session_id):
        """Den nyeste raekke i sessionen, laest UDENOM al applikationskode."""
        import sqlite3
        c = sqlite3.connect(str(sti))
        try:
            return c.execute(
                "SELECT content, encrypted FROM chat_messages "
                "WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,)).fetchone()
        finally:
            c.close()

    def test_medlems_besked_ligger_krypteret_og_laeses_klar(self, db) -> None:
        from core.services.chat_sessions import (
            append_chat_message, recent_chat_session_messages,
        )
        hemmelig = "Mikkels private besked om noget han ikke vil dele"
        append_chat_message(
            session_id="s-mikkel", role="user", content=hemmelig,
            user_id="member-a-id-opdigtet", workspace_name="mikkel",
        )
        raa, flag = self._raa(db, "s-mikkel")
        assert flag == 1, "encrypted-kolonnen blev ikke sat"
        assert cc.er_krypteret(raa), "raekken ligger i klartekst i databasen"
        assert "private besked" not in raa

        tilbage = recent_chat_session_messages("s-mikkel", limit=10)
        assert [m["content"] for m in tilbage] == [hemmelig]

    def test_medlems_foerste_besked_giver_krypteret_titel(self, db) -> None:
        import sqlite3
        from core.services.chat_sessions import append_chat_message, list_chat_sessions

        with sqlite3.connect(str(db)) as conn:
            conn.execute("UPDATE chat_sessions SET title = 'New chat' WHERE session_id = 's-mikkel'")
        hemmelig = "Privat titel som ikke må stå i databasen"
        append_chat_message(
            session_id="s-mikkel", role="user", content=hemmelig,
            user_id="member-a-id-opdigtet", workspace_name="mikkel",
        )
        with sqlite3.connect(str(db)) as conn:
            raw = conn.execute("SELECT title FROM chat_sessions WHERE session_id = 's-mikkel'").fetchone()[0]
        assert raw.startswith("enc:v1:")
        assert hemmelig not in raw
        sessions = list_chat_sessions(user_id="member-a-id-opdigtet")
        assert sessions[0]["title"] == hemmelig

    def test_gammel_titel_migreres_idempotent(self, db) -> None:
        import sqlite3
        from core.services.chat_sessions import append_chat_message
        from scripts.migrate_member_session_titles import migrate

        append_chat_message(session_id="s-mikkel", role="user", content="Et ord",
                            user_id="member-a-id-opdigtet", workspace_name="mikkel")
        with sqlite3.connect(str(db)) as conn:
            conn.execute("UPDATE chat_sessions SET title='Privat gammel titel' WHERE session_id='s-mikkel'")
            conn.execute("UPDATE chat_sessions SET title='Ejerens titel' WHERE session_id='s-bjorn'")
        assert migrate(dry_run=True)["encrypted"] == 1
        assert migrate(dry_run=False)["encrypted"] == 1
        assert migrate(dry_run=False)["encrypted"] == 0
        with sqlite3.connect(str(db)) as conn:
            member = conn.execute("SELECT title FROM chat_sessions WHERE session_id='s-mikkel'").fetchone()[0]
            owner = conn.execute("SELECT title FROM chat_sessions WHERE session_id='s-bjorn'").fetchone()[0]
        assert member.startswith("enc:v1:")
        assert owner == "Ejerens titel"

    def test_medlemssoegning_finder_krypteret_titel_og_besked(self, db) -> None:
        from core.services.chat_sessions import append_chat_message, search_chat_sessions

        append_chat_message(session_id="s-mikkel", role="user",
                            content="Privat tekst om aebletrae",
                            user_id="member-a-id-opdigtet", workspace_name="mikkel")
        assert any(row["session_id"] == "s-mikkel" for row in search_chat_sessions(
            "aebletrae", user_id="member-a-id-opdigtet"))
        assert search_chat_sessions("aebletrae", user_id="member-b-id-opdigtet") == []

    def test_owners_besked_roeres_ikke(self, db) -> None:
        from core.services.chat_sessions import (
            append_chat_message, recent_chat_session_messages,
        )
        tekst = "Bjørns egen besked"
        append_chat_message(
            session_id="s-bjorn", role="user", content=tekst,
            user_id="owner-id-opdigtet", workspace_name="bjorn",
        )
        raa, flag = self._raa(db, "s-bjorn")
        assert flag == 0 and raa == tekst
        assert [m["content"] for m in recent_chat_session_messages("s-bjorn")] == [tekst]

    def test_besked_uden_bruger_er_ogsaa_owner(self, db) -> None:
        """De 25.212 rækker med tomt user_id."""
        from core.services.chat_sessions import append_chat_message
        append_chat_message(session_id="s-tom", role="user", content="ingen ejer")
        raa, flag = self._raa(db, "s-tom")
        assert flag == 0 and raa == "ingen ejer"

    def test_en_anden_sessions_laeser_faar_IKKE_klartekst(self, db) -> None:
        """Nordstjernen §3 i praksis: rækken er læsbar i sin egen session og
        kun der. Enhver anden læser af tabellen ser ciffertekst."""
        import sqlite3

        from core.services.chat_sessions import append_chat_message
        append_chat_message(
            session_id="s-lotte", role="user", content="Lottes private",
            user_id="member-b-id-opdigtet", workspace_name="lotte",
        )
        c = sqlite3.connect(str(db))
        try:
            alt = " ".join(str(r[0]) for r in c.execute("SELECT content FROM chat_messages"))
        finally:
            c.close()
        assert "Lottes private" not in alt


class TestSessionenErEnheden:
    """Målt i produktionen 27/9-2026, efter første migration: Michelles session
    gav ciffertekst tilbage, fordi hendes EGNE beskeder var tagget `default` og
    kun Jarvis' svar var tagget `michelle`. Og i Mikkels session lå elleve
    tool-rækker tagget `bjorn` — Jarvis' eget output med ejerens mærkat.

    Taggingen pr. række er upålidelig. Samtalen er enheden folk oplever, så
    findes der ét medlem i sessionen, tilhører hele sessionen det medlem.
    """

    @pytest.fixture
    def db(self, tmp_path, monkeypatch):
        import core.runtime.db_core as dbc
        sti = tmp_path / "jarvis.db"
        monkeypatch.setenv("JARVIS_DB_NOPOOL", "1")
        monkeypatch.setattr(dbc, "_POOL_DISABLED", True, raising=False)
        monkeypatch.setattr(dbc, "DB_PATH", sti, raising=False)
        from core.runtime.db_schema import init_db
        init_db()
        return sti

    @staticmethod
    def _raekke(ws, uid, sid, indhold="x"):
        import core.runtime.db_core as dbc
        with dbc.connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages (message_id, session_id, role, content, "
                "user_id, workspace_name, created_at) VALUES (?, ?, 'user', ?, ?, ?, '2026-01-01')",
                ("m-%s-%s" % (sid, indhold), sid, indhold, uid, ws))
            conn.commit()

    def test_medlem_findes_selvom_foerste_raekke_er_default(self, db) -> None:
        """Præcis Michelles tilfælde. Et `LIMIT 1` fandt `default` og svarede
        «ingen ejer»."""
        self._raekke("default", "", "s1", "a")
        self._raekke("michelle", "partner-id-opdigtet", "s1", "b")
        assert cc.medlem_for_session("s1") == "partner-id-opdigtet"

    def test_default_raekke_i_en_medlems_session_krypteres(self, db) -> None:
        self._raekke("michelle", "partner-id-opdigtet", "s2", "b")
        ud = cc.krypter_raekke(
            {"workspace_name": "default", "user_id": "", "session_id": "s2",
             "content": "Michelles egne ord"})
        assert ud["encrypted"] == 1 and cc.er_krypteret(ud["content"])

    def test_bjorn_tagget_raekke_i_en_medlems_session_krypteres_ogsaa(self, db) -> None:
        """De elleve tool-rækker. Mærkatet er Jarvis' eget output, ikke Bjørn."""
        self._raekke("mikkel", "member-a-id-opdigtet", "s3", "b")
        ud = cc.krypter_raekke(
            {"workspace_name": "bjorn", "user_id": "", "session_id": "s3",
             "content": "tool-resultat inde i Mikkels samtale"})
        assert ud["encrypted"] == 1

    def test_en_ren_owner_session_roeres_stadig_ikke(self, db) -> None:
        """Den vigtige modprøve: sessionen må ikke kunne trække owner-rækker med."""
        self._raekke("default", "", "s4", "a")
        self._raekke("bjorn", "owner-id-opdigtet", "s4", "b")
        assert cc.medlem_for_session("s4") is None
        ud = cc.krypter_raekke(
            {"workspace_name": "default", "user_id": "", "session_id": "s4",
             "content": "Bjørns egen"})
        assert ud["encrypted"] == 0 and ud["content"] == "Bjørns egen"

    def test_ukendt_session_falder_tilbage_til_raekken(self, db) -> None:
        """Den allerførste besked i en ny session har ingen naboer at spørge."""
        ud = cc.krypter_raekke(
            {"workspace_name": "mikkel", "user_id": "", "session_id": "helt-ny",
             "content": "foerste besked"})
        assert ud["encrypted"] == 1

    def test_to_medlemmer_i_en_session_krypteres_IKKE(self, db) -> None:
        """Der er ikke ét rigtigt svar. Så siges det højt frem for at vælge."""
        self._raekke("mikkel", "member-a-id-opdigtet", "s5", "a")
        self._raekke("lotte", "member-b-id-opdigtet", "s5", "b")
        assert cc.medlem_for_session("s5") is None
