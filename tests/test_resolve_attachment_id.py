"""`read_attachment` fejlede 18 ud af 20 gange — på den forkerte kolonne.

Målt på CT105 27/9-2026 over fjorten dage (`tool.invoked` / `tool.completed`).
16 af de 18 fejlede kald pegede på en vedhæftning der lå i
`channel_attachments` lige nu:

    8 kald sendte FILNAVNET             «Skærmbillede fra 2026-09-23 20-56-18.png»
    4 kald sendte en UUID der er præfiks af filnavnet
    4 kald sendte det GEMTE filnavn     «<id>_<original>.jpeg» (local_path)
    2 kald var reelt opfundne

Det er ikke et værktøj i stykker. Det er et værktøj der kun accepterer det id
ingen kan se — Jarvis ser filnavnet i sin kontekst og sender det han ser.
"""

from __future__ import annotations

import pytest

from core.services.attachment_service import resolve_attachment_id


@pytest.fixture
def vedhaeftninger(tmp_path, monkeypatch):
    """Isoleret database med tre vedhæftninger i de former driften viste."""
    import core.runtime.db_core as dbc
    monkeypatch.setenv("JARVIS_DB_NOPOOL", "1")
    monkeypatch.setattr(dbc, "_POOL_DISABLED", True, raising=False)
    monkeypatch.setattr(dbc, "DB_PATH", str(tmp_path / "jarvis.db"), raising=False)
    from core.runtime.db import _ensure_channel_attachments_table
    with dbc.connect() as conn:
        _ensure_channel_attachments_table(conn)
        for aid, navn, sti in (
            ("aid-1", "2341630b-5e0b-44e5-ad06-edcf69df0f4b.jpeg",
             "/data/uploads/aid1_2341630b-5e0b-44e5-ad06-edcf69df0f4b.jpeg"),
            ("aid-2", "Skærmbillede fra 2026-09-23 20-56-18.png",
             "/data/uploads/aid2_Skærmbillede fra 2026-09-23 20-56-18.png"),
            ("aid-3", "rapport.pdf", "/data/uploads/aid3_rapport.pdf"),
        ):
            conn.execute(
                "INSERT INTO channel_attachments (attachment_id, session_id, "
                "channel_type, filename, mime_type, size_bytes, local_path, "
                "source_url, created_at) VALUES (?, 's', 'chat', ?, 'image/jpeg', "
                "1, ?, '', '2026-09-27T00:00:00Z')", (aid, navn, sti))
        conn.commit()
    return tmp_path


class TestDetEksakteIdVinderAltid:
    def test_et_rigtigt_id_gaar_uroert_igennem(self, vedhaeftninger) -> None:
        assert resolve_attachment_id("aid-2") == "aid-2"

    def test_id_slaar_filnavn_der_ligner(self, vedhaeftninger, monkeypatch) -> None:
        """Et filnavn må ALDRIG kunne skygge for et eksakt id."""
        import core.runtime.db_core as dbc
        with dbc.connect() as conn:
            conn.execute(
                "INSERT INTO channel_attachments (attachment_id, session_id, "
                "channel_type, filename, mime_type, size_bytes, local_path, "
                "source_url, created_at) VALUES ('rapport.pdf', 's', 'chat', "
                "'noget-andet.pdf', 'application/pdf', 1, '/x', '', "
                "'2026-09-28T00:00:00Z')")
            conn.commit()
        # 'rapport.pdf' er BÅDE et id (nyere) og et filnavn (ældre). Id'et vinder.
        assert resolve_attachment_id("rapport.pdf") == "rapport.pdf"


class TestDeTreFormerDriftenViste:
    def test_filnavnet_praecist(self, vedhaeftninger) -> None:
        """8 af de 18 fejlede kald."""
        assert resolve_attachment_id(
            "Skærmbillede fra 2026-09-23 20-56-18.png") == "aid-2"

    def test_det_gemte_filnavn_fra_local_path(self, vedhaeftninger) -> None:
        """4 af de 18 — «<id>_<original>.jpeg»."""
        assert resolve_attachment_id(
            "aid1_2341630b-5e0b-44e5-ad06-edcf69df0f4b.jpeg") == "aid-1"

    def test_en_uuid_der_er_praefiks_af_filnavnet(self, vedhaeftninger) -> None:
        """4 af de 18 — filnavnet uden endelsen."""
        assert resolve_attachment_id(
            "2341630b-5e0b-44e5-ad06-edcf69df0f4b") == "aid-1"

    def test_eksakt_filnavn_slaar_et_NYERE_praefiks_match(self, vedhaeftninger) -> None:
        """Rækkefølgen mellem de to filnavns-opslag har en pointe.

        Præfiks-opslaget matcher også et eksakt navn, så uden dette ville
        «rapport.pdf» kunne ramme «rapport.pdf.bak» hvis den var nyere — og
        ingen test ville se det. Det eksakte navn skal vinde.
        """
        import core.runtime.db_core as dbc
        with dbc.connect() as conn:
            conn.execute(
                "INSERT INTO channel_attachments (attachment_id, session_id, "
                "channel_type, filename, mime_type, size_bytes, local_path, "
                "source_url, created_at) VALUES ('aid-bak', 's', 'chat', "
                "'rapport.pdf.bak', 'application/octet-stream', 1, '/z', '', "
                "'2026-09-28T00:00:00Z')")
            conn.commit()
        assert resolve_attachment_id("rapport.pdf") == "aid-3"


class TestDenGaetterIkke:
    def test_noget_opfundet_returneres_uaendret(self, vedhaeftninger) -> None:
        """2 af de 18 var reelt opfundne. Kalderen skal fejle som før — ikke
        få en tilfældig vedhæftning i hånden."""
        assert resolve_attachment_id("findes-ikke-abc123") == "findes-ikke-abc123"

    def test_tom_vaerdi_er_tom(self, vedhaeftninger) -> None:
        assert resolve_attachment_id("") == ""
        assert resolve_attachment_id("   ") == ""

    def test_et_praefiks_der_passer_paa_INTET_gaetter_ikke(self, vedhaeftninger) -> None:
        assert resolve_attachment_id("zzz") == "zzz"

    def test_database_i_stykker_fejler_ikke_haardere_end_foer(
        self, vedhaeftninger, monkeypatch
    ) -> None:
        import core.runtime.db as db

        def i_stykker(*a, **k):
            raise OSError("databasen er væk")

        monkeypatch.setattr(db, "connect", i_stykker)
        assert resolve_attachment_id("rapport.pdf") == "rapport.pdf"


class TestNyesteVinder:
    def test_to_med_samme_filnavn_giver_den_nyeste(self, vedhaeftninger) -> None:
        """Samme navn sendt to gange: man mener den man lige sendte."""
        import core.runtime.db_core as dbc
        with dbc.connect() as conn:
            conn.execute(
                "INSERT INTO channel_attachments (attachment_id, session_id, "
                "channel_type, filename, mime_type, size_bytes, local_path, "
                "source_url, created_at) VALUES ('aid-ny', 's', 'chat', "
                "'rapport.pdf', 'application/pdf', 1, '/y', '', "
                "'2026-09-28T00:00:00Z')")
            conn.commit()
        assert resolve_attachment_id("rapport.pdf") == "aid-ny"


def test_vaerktoejet_bruger_resolveren() -> None:
    """«Bygget, aldrig tilsluttet» er husets hyppigste fejl.

    At lede efter NAVNET i kilden er ikke nok: en import der bliver stående
    mens kaldet erstattes af `pass` ville bestå. Det er tilslutningen der skal
    pinnes — samme fælde som `cleanup_old_results` samme aften.
    """
    import ast
    import inspect

    from core.tools.simple_tools_native import _exec_read_attachment

    traeet = ast.parse(inspect.getsource(_exec_read_attachment).lstrip())
    kald = [
        n for n in ast.walk(traeet)
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
        and getattr(n.value.func, "id", None) == "resolve_attachment_id"
    ]
    assert kald, "resolve_attachment_id bliver ikke KALDT — kun nævnt"
    assert any(
        isinstance(m, ast.Name) and m.id == "attachment_id"
        for n in kald for m in n.targets
    ), "resultatet bliver ikke brugt som attachment_id"
