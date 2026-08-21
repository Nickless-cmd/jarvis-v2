"""GET /chat/sessions/{id}: desk poller den hvert 6. sekund.

Målt 21. aug 2026 på Bjørns session (381 beskeder): 23ms for at bygge svaret,
6,6ms serialisering og **1,75 MB JSON pr. kald** — 135 MB i kvarteret for at
vise en samtale der ikke havde ændret sig. Prisen vokser med samtalen, fordi
alle beskeder hentes hver gang.

`session_version()` koster 0,6ms og ændrer sig præcis når indholdet gør. Den
bærer både ETag'en (så browseren kan få 304 i stedet for 1,75 MB) og
cache-nøglen (så payloadet ikke bygges igen unødigt).

Den farlige fejl her er ikke langsomhed — det er at vise Bjørn en forældet
samtale. Testene går derfor mest på at versionen faktisk skifter.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from core.services import central_projection_cache as cpc


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "t.db"
    con = sqlite3.connect(str(p))
    con.execute("""CREATE TABLE chat_sessions (session_id TEXT PRIMARY KEY, title TEXT,
                   created_at TEXT, updated_at TEXT, workspace_kind TEXT, workspace_root TEXT)""")
    con.execute("""CREATE TABLE chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   message_id TEXT, session_id TEXT, role TEXT, content TEXT,
                   content_json TEXT, created_at TEXT)""")
    con.execute("INSERT INTO chat_sessions VALUES ('s1','T','2026-08-21','2026-08-21','','')")
    for i in range(3):
        con.execute("INSERT INTO chat_messages (message_id,session_id,role,content,content_json,"
                    "created_at) VALUES (?,?,?,?,?,?)",
                    (f"m{i}", "s1", "user", f"besked {i}", None, "2026-08-21T10:00:00"))
    con.commit()
    return p, con


def _version(db_path, session_id="s1"):
    from core.services import chat_sessions
    import contextlib

    @contextlib.contextmanager
    def _conn():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    with patch.object(chat_sessions, "connect", _conn):
        return chat_sessions.session_version(session_id)


class TestVersion:
    def test_uaendret_session_giver_samme_version(self, db):
        p, _ = db
        assert _version(p) == _version(p)

    def test_ny_besked_bumper_versionen(self, db):
        p, con = db
        før = _version(p)
        con.execute("INSERT INTO chat_messages (message_id,session_id,role,content,content_json,"
                    "created_at) VALUES ('m9','s1','assistant','nyt svar',NULL,'2026-08-21T10:05')")
        con.commit()
        assert _version(p) != før, "en ny besked nåede ikke frem til klienten"

    def test_REDIGERET_besked_bumper_versionen(self, db):
        """Den snigende: samme antal, samme højeste id. Uden SUM(LENGTH(content))
        i nøglen ville en rettelse i en eksisterende besked aldrig blive vist."""
        p, con = db
        før = _version(p)
        con.execute("UPDATE chat_messages SET content='besked 0 RETTET' WHERE message_id='m0'")
        con.commit()
        assert _version(p) != før, "en redigeret besked så uændret ud"

    def test_aendret_content_json_bumper_versionen(self, db):
        """content_json bærer strukturerede blokke — en ændring dér er også indhold."""
        p, con = db
        før = _version(p)
        con.execute("UPDATE chat_messages SET content_json='{\"blocks\":[]}' WHERE message_id='m0'")
        con.commit()
        assert _version(p) != før

    def test_omdoebt_session_bumper_versionen(self, db):
        p, con = db
        før = _version(p)
        con.execute("UPDATE chat_sessions SET updated_at='2026-08-21T11:00' WHERE session_id='s1'")
        con.commit()
        assert _version(p) != før

    def test_slettet_besked_bumper_versionen(self, db):
        p, con = db
        før = _version(p)
        con.execute("DELETE FROM chat_messages WHERE message_id='m1'")
        con.commit()
        assert _version(p) != før

    def test_ukendt_session_giver_None(self, db):
        p, _ = db
        assert _version(p, "findes-ikke") is None

    def test_tomt_id_giver_None(self, db):
        p, _ = db
        assert _version(p, "") is None


class TestVersionsCache:
    def setup_method(self):
        cpc.invalidate()

    def test_samme_version_bygger_ikke_igen(self):
        calls = []
        prod = lambda: (calls.append(1), {"n": len(calls)})[1]
        a, hit_a = cpc.cached_by_version("k", "v1", prod)
        b, hit_b = cpc.cached_by_version("k", "v1", prod)
        assert len(calls) == 1 and a == b
        assert hit_a is False and hit_b is True

    def test_ny_version_bygger_igen(self):
        calls = []
        prod = lambda: (calls.append(1), len(calls))[1]
        cpc.cached_by_version("k", "v1", prod)
        v, hit = cpc.cached_by_version("k", "v2", prod)
        assert v == 2 and hit is False

    def test_kun_een_version_gemmes_pr_noegle(self):
        """En lang samtale må ikke ophobe ét payload pr. besked."""
        cpc.invalidate()
        for i in range(50):
            cpc.cached_by_version("k", f"v{i}", lambda: "x" * 100)
        assert cpc.stats()["keys"] == 1

    def test_invalidate_rydder_ogsaa_versionerede(self):
        cpc.cached_by_version("chat:session:s1", "v1", lambda: 1)
        assert cpc.invalidate("chat:") >= 1
        calls = []
        cpc.cached_by_version("chat:session:s1", "v1", lambda: calls.append(1))
        assert len(calls) == 1, "gammel værdi overlevede invalidate"


class TestEndpoint:
    def _krop(self):
        """Handlerens kode UDEN docstring — ellers matcher '304' i prosaen og
        rækkefølge-tests bliver meningsløse."""
        import ast
        import inspect
        from apps.api.jarvis_api.routes import chat
        fn = ast.parse(inspect.getsource(chat.chat_session)).body[0]
        body = fn.body
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)):
            body = body[1:]
        return "\n".join(ast.unparse(n) for n in body)

    def test_svarer_304_uden_at_bygge_payloadet(self):
        """Hele pointen: 304 skal koste en versions-query, ikke 23ms + 1,75 MB."""
        krop = self._krop()
        i304 = krop.index("status_code=304")
        assert "get_chat_session" not in krop[:i304], (
            "payloadet bygges før 304-tjekket — så sparer 304 ingenting")

    def test_etag_og_no_cache_saettes(self):
        src = self._krop()
        assert "ETag" in src
        assert "no-cache" in src, (
            "uden Cache-Control: no-cache revaliderer browseren ikke, "
            "og så sender den aldrig If-None-Match")
        assert "no-store" not in src, "no-store ville slå revalidering helt fra"

    def test_handler_blokerer_ikke_event_loopet(self):
        """Samme mønster som de 75 central-handlers: synkront DB-arbejde i en
        `async def` fryser loopet."""
        import inspect
        from apps.api.jarvis_api.routes import chat
        assert not inspect.iscoroutinefunction(chat.chat_session)

    def test_prewarm_fyrer_paa_BEGGE_stier(self):
        """Prewarm lå oprindeligt efter session-hentningen. Havner den efter
        304-returnen, holder den op med at fyre ved poll — en adfærdsændring
        smuglet ind under en performance-fix."""
        import inspect
        from apps.api.jarvis_api.routes import chat
        krop = self._krop()
        assert krop.index("warm_session_prefix_async") < krop.index("status_code=304"), \
            "prewarm fyrer ikke længere når svaret er 304"
