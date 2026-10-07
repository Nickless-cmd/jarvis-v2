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
    def test_samme_billede_kommer_kun_med_een_gang(self) -> None:
        """`allerede_sendt` er grunden til at et senere billedkald ikke
        gensender turens tidligere billeder."""
        pf.note("r7", filename="k.png", mime_type="image/png",
                attachment_id="att-7", tool_use_id="t7")
        sendt: set[str] = set()
        assert len(sse._live_udgivne_blokke("t7", sendt)) == 1
        assert sse._live_udgivne_blokke("t7", sendt) == [], "billedet blev sendt igen"

    def test_noten_findes_SELVOM_run_id_er_et_andet(self) -> None:
        """DRIFTENS form, målt 27/9-2026 med logning i begge ender:

            note:        run_id='visible-a75f…'  tool_use_id='call_00_bUh…'
            tool_result: run_id='visible-8fa4…'  tool_id='call_00_bUh…'

        Samme proces, samme sekund, samme kald-id — men TO forskellige run'er,
        fordi `_state["run_id"]` sættes én gang og turen spænder over flere.
        Slår opslaget på run'et, findes noten aldrig. Det er dét her er.
        """
        pf.note("visible-a75f4f3f", filename="k.png", mime_type="image/png",
                attachment_id="att-8", tool_use_id="call_00_bUhJiD6P")
        blokke = sse._live_udgivne_blokke("call_00_bUhJiD6P", set())
        assert len(blokke) == 1
        assert blokke[0]["attachment_id"] == "att-8"

    def test_blokken_baerer_referencen_og_ankeret(self) -> None:
        pf.note("r3", filename="k.png", mime_type="image/png",
                attachment_id="att-3", tool_use_id="t3")
        blokke = sse._live_udgivne_blokke("t3", set())
        assert len(blokke) == 1
        assert blokke[0]["type"] == "image"
        assert blokke[0]["attachment_id"] == "att-3"
        assert blokke[0]["tool_use_id"] == "t3", "ankeret mangler"
        assert blokke[0]["kilde"] == "generated"

    def test_en_fil_der_IKKE_er_et_billede_kommer_OGSAA_med(self) -> None:
        """Vendt om 7/10-2026, og det er pointen i `382e1dcb5`.

        Funktionen hed `_live_billedblokke` og havde
        `if b.get("type") != "image": continue`. En widget er `text/html` →
        typen `file`, saa fladen blev droppet netop her og naaede aldrig en
        klient; den dukkede foerst op naar traaden blev genindlaest fra
        `content_json`. Samme hul ramte `video` og `publish_file`.

        Den gamle udgave af DENNE test pinnede hullet som om det var reglen.
        """
        pf.note("r4", filename="rapport.md", mime_type="text/markdown",
                url="/files/rapport.md", tool_use_id="t4")
        blokke = sse._live_udgivne_blokke("t4", set())
        assert len(blokke) == 1, blokke
        assert blokke[0]["filename"] == "rapport.md"

    def test_en_ikke_billed_blok_faar_INGEN_data_url(self, monkeypatch) -> None:
        """En `file` er en REFERENCE. Lagde vi et helt HTML-dokument i
        stroemmen, ville fladen blive sendt som data i stedet for at lade
        klienten hente den med sit token."""
        pf.note("r4b", filename="widget.html", mime_type="text/html",
                attachment_id="att-w", tool_use_id="t4b")
        import core.services.attachment_service as a
        monkeypatch.setattr(a, "image_data_url",
                            lambda aid: pytest.fail("data-URL for en file-blok"))
        blokke = sse._live_udgivne_blokke("t4b", set())
        assert len(blokke) == 1
        assert "src" not in blokke[0]
        assert blokke[0]["attachment_id"] == "att-w"

    def test_tomt_run_id_giver_ingen_blokke(self) -> None:
        assert sse._live_udgivne_blokke("", set()) == []

    def test_data_url_lagges_paa_naar_den_findes(self, monkeypatch) -> None:
        pf.note("r5", filename="k.png", mime_type="image/png",
                attachment_id="att-5", tool_use_id="t5")
        import core.services.attachment_service as a
        monkeypatch.setattr(a, "image_data_url", lambda aid: "data:image/png;base64,AAA")
        blokke = sse._live_udgivne_blokke("t5", set())
        assert blokke[0]["src"] == "data:image/png;base64,AAA"

    def test_for_stort_billede_sendes_stadig_med_sin_reference(self, monkeypatch) -> None:
        """`image_data_url` returnerer None når billedet er for stort til at
        ligge i konteksten. Blokken skal alligevel af sted: attachment'en er
        allerede registreret, så adressen virker med det samme."""
        pf.note("r6", filename="stor.png", mime_type="image/png",
                attachment_id="att-6", tool_use_id="t6")
        import core.services.attachment_service as a
        monkeypatch.setattr(a, "image_data_url", lambda aid: None)
        blokke = sse._live_udgivne_blokke("t6", set())
        assert len(blokke) == 1
        assert "src" not in blokke[0]
        assert blokke[0]["attachment_id"] == "att-6"


class TestIngenVaerktoejsGate:
    """Konstanten `_BILLEDVAERKTOEJER` er FJERNET 7/10-2026, med vilje.

    Den gatede den levende udgivelses-blok til billedvaerktoejerne alene. En
    widget udgives af `vis_widget`, som ikke er et billedvaerktoej — saa
    fladen blev aldrig sendt. Udsenderen kalder nu funktionen for ETHVERT
    vaerktoej; `peek_efter_tool_use` giver tom liste for alle andre, saa det
    koster intet.

    Den gamle klasse her pinnede konstanten og de tre navne i den. Den
    invariant findes ikke laengere — men en NY goer: at kaldet ikke er gatet
    paa et vaerktoejsnavn. Genindfoeres en saadan gate, forsvinder widgets fra
    den levende stroem igen, praecis som de gjorde.
    """

    def test_konstanten_er_vaek(self) -> None:
        assert not hasattr(sse, "_BILLEDVAERKTOEJER"), (
            "gaten er tilbage — widgets forsvinder fra den levende stroem")

    def test_kaldet_er_ikke_gatet_paa_et_vaerktoejsnavn(self) -> None:
        """Kilde-vagt paa TRAEET, ikke paa teksten.

        Foerste udgave greppede et vindue paa otte linjer omkring kaldet — og
        fejlede paa en KOMMENTAR der naevnte billedvaerktoejerne. En kilde-vagt
        der leder efter en streng maaler naesten ingenting; den skal spoerge
        strukturen. Her: ingen betingelse der omslutter kaldet maa proeve paa
        et vaerktoejsnavn eller paa den fjernede konstant.

        BAADE `if` OG `x if c else y`: foerste udgave af vagten saa kun
        `ast.If`, og en gate skrevet som betinget UDTRYK — den eneste form der
        kan indsaettes uden at roere indrykningen — var sluppet lige forbi.
        """
        import ast
        import inspect

        traed = ast.parse(inspect.getsource(sse))
        FORBUDT = {"openrouter_image", "openrouter_image_edit",
                   "pollinations_image", "_BILLEDVAERKTOEJER"}

        foraeldre: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(traed):
            for barn in ast.iter_child_nodes(node):
                foraeldre[barn] = node

        kald = [n for n in ast.walk(traed)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "_live_udgivne_blokke"]
        assert kald, "fandt ikke kaldet til _live_udgivne_blokke"

        for n in kald:
            node: ast.AST | None = n
            while node is not None:
                mor = foraeldre.get(node)
                if isinstance(mor, (ast.If, ast.IfExp)):
                    navne = {t.id for t in ast.walk(mor.test) if isinstance(t, ast.Name)}
                    navne |= {t.value for t in ast.walk(mor.test)
                              if isinstance(t, ast.Constant) and isinstance(t.value, str)}
                    ramt = navne & FORBUDT
                    assert not ramt, f"kaldet er gatet paa {sorted(ramt)}"
                node = mor

    def test_et_vilkaarligt_vaerktoej_kan_udgive(self) -> None:
        """`vis_widget` er ikke et billedvaerktoej og skal alligevel igennem."""
        pf.note("r9", filename="widget-x.html", mime_type="text/html",
                attachment_id="att-9", tool_use_id="call_vis_widget_1")
        blokke = sse._live_udgivne_blokke("call_vis_widget_1", set())
        assert len(blokke) == 1 and blokke[0]["attachment_id"] == "att-9"
