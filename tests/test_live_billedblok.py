"""Billedet i den LEVENDE stream (spec §billedgenerering, 27/9-2026).

Indtil nu lagde billedværktøjet en note fra sig under turen, og blokken blev
først bygget når svaret blev PERSISTERET. Under kørslen var der bogstaveligt
talt intet at tegne: animationen vistes, fordi den er sin egen komponent, men
billedet havde ingen blok at bo i før turen var slut.

Begge klienter havde grenen klar — desk skriver det selv i `sseProtocol.ts`:
«LIVE bærer det en `src`, PERSISTERET bærer det en REFERENCE». Den havde bare
aldrig fået noget at tage imod.

Testene her dækker backend-halvdelen: at noten kan læses UDEN at rydde den, og
at blokken bygges for ALLE TRE billedværktøjer.
"""

from __future__ import annotations

import pytest

from core.services import published_files as pf
from core.services import visible_runs_sse_v2 as sse


@pytest.fixture(autouse=True)
def ryd():
    pf._nulstil_for_tests()
    yield
    pf._nulstil_for_tests()


class TestPeekRydderIkke:
    """`take` popper, fordi den kaldes når svaret persisteres. Læste den
    levende stream med `take`, ville billedet forsvinde fra den GEMTE besked —
    altså præcis den fejl 13/9 rettede."""

    def test_peek_lader_noten_ligge_til_den_der_gemmer(self) -> None:
        pf.note("r1", filename="a.png", mime_type="image/png",
                attachment_id="att-1", tool_use_id="t1")
        assert len(pf.peek("r1")) == 1
        assert len(pf.peek("r1")) == 1, "peek fjernede noten"
        assert len(pf.take("r1")) == 1, "den der gemmer fandt den ikke"
        assert pf.peek("r1") == []

    def test_peek_afgraenser_til_eet_vaerktoejskald(self) -> None:
        pf.note("r2", filename="a.png", mime_type="image/png",
                attachment_id="att-a", tool_use_id="t-a")
        pf.note("r2", filename="b.png", mime_type="image/png",
                attachment_id="att-b", tool_use_id="t-b")
        assert [p["filename"] for p in pf.peek("r2", tool_use_id="t-a")] == ["a.png"]

    def test_tom_run_id_giver_tom_liste(self) -> None:
        assert pf.peek("") == []


class TestBlokkenBygges:
    def test_blokken_baerer_referencen_og_ankeret(self) -> None:
        pf.note("r3", filename="k.png", mime_type="image/png",
                attachment_id="att-3", tool_use_id="t3")
        blokke = sse._live_billedblokke("r3", "t3")
        assert len(blokke) == 1
        assert blokke[0]["type"] == "image"
        assert blokke[0]["attachment_id"] == "att-3"
        assert blokke[0]["tool_use_id"] == "t3", "ankeret mangler"
        assert blokke[0]["kilde"] == "generated"

    def test_en_fil_der_ikke_er_et_billede_kommer_ikke_med(self) -> None:
        pf.note("r4", filename="rapport.md", mime_type="text/markdown",
                url="/files/rapport.md", tool_use_id="t4")
        assert sse._live_billedblokke("r4", "t4") == []

    def test_tomt_run_id_giver_ingen_blokke(self) -> None:
        assert sse._live_billedblokke("", "t") == []

    def test_data_url_lagges_paa_naar_den_findes(self, monkeypatch) -> None:
        pf.note("r5", filename="k.png", mime_type="image/png",
                attachment_id="att-5", tool_use_id="t5")
        import core.services.attachment_service as a
        monkeypatch.setattr(a, "image_data_url", lambda aid: "data:image/png;base64,AAA")
        blokke = sse._live_billedblokke("r5", "t5")
        assert blokke[0]["src"] == "data:image/png;base64,AAA"

    def test_for_stort_billede_sendes_stadig_med_sin_reference(self, monkeypatch) -> None:
        """`image_data_url` returnerer None når billedet er for stort til at
        ligge i konteksten. Blokken skal alligevel af sted: attachment'en er
        allerede registreret, så adressen virker med det samme."""
        pf.note("r6", filename="stor.png", mime_type="image/png",
                attachment_id="att-6", tool_use_id="t6")
        import core.services.attachment_service as a
        monkeypatch.setattr(a, "image_data_url", lambda aid: None)
        blokke = sse._live_billedblokke("r6", "t6")
        assert len(blokke) == 1
        assert "src" not in blokke[0]
        assert blokke[0]["attachment_id"] == "att-6"


class TestAlleTreVaerktoejer:
    """`openrouter_image_edit` er et TYNDT LAG over `generate_image` og deler
    hele kæden efter kaldet — samme `_save_images`, samme
    `register_generated_image`, samme note. Den eneste forskel er ét felt i
    sidecar'en (`kind: "edit"`).

    En betingelse på `openrouter_image` alene ville derfor glemme redigeringen
    OG `pollinations_image`. Det er præcis den slags der er let at overse,
    fordi man tester med det værktøj man selv bruger.
    """

    @pytest.mark.parametrize("navn", [
        "openrouter_image", "openrouter_image_edit", "pollinations_image",
    ])
    def test_vaerktoejet_er_med(self, navn) -> None:
        assert navn in sse._BILLEDVAERKTOEJER

    def test_ingen_andre_er_med(self) -> None:
        assert sse._BILLEDVAERKTOEJER == {
            "openrouter_image", "openrouter_image_edit", "pollinations_image",
        }

    def test_navnene_findes_faktisk_som_vaerktoejer(self) -> None:
        """Et navn med en tastefejl ville aldrig matche, og ingen test der kun
        læste konstanten ville opdage det."""
        import core.tools.openrouter_image_tools as o
        import core.tools.pollinations_tools as p
        kilde = o.__file__ and open(o.__file__, encoding="utf-8").read()
        kilde += open(p.__file__, encoding="utf-8").read()
        for navn in sse._BILLEDVAERKTOEJER:
            assert '"name": "%s"' % navn in kilde, navn
