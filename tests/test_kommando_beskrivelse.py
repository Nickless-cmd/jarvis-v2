"""Jarvis' egen linje: `description` på bash og operator_bash (19/9-2026)."""
from core.tools.kommando_beskrivelse import BESKRIVELSE_PARAM, brugbar_beskrivelse


def test_en_almindelig_beskrivelse_bruges():
    assert brugbar_beskrivelse("Vis arbejdstræets status", "git status") == "Vis arbejdstræets status"


def test_tom_eller_ikke_tekst_bruges_ikke():
    assert brugbar_beskrivelse("", "ls") == ""
    assert brugbar_beskrivelse("   ", "ls") == ""
    assert brugbar_beskrivelse(None, "ls") == ""
    assert brugbar_beskrivelse(42, "ls") == ""


def test_flere_linjer_bruges_ikke():
    """Claude Desktops regel: en linje er én linje."""
    assert brugbar_beskrivelse("Vis filer\nog mere", "ls") == ""


def test_kommandoen_igen_bruges_ikke():
    """Den mekaniske linje viser kommandoen i forvejen."""
    assert brugbar_beskrivelse("git  status", "git status") == ""
    assert brugbar_beskrivelse("GIT STATUS", "git status") == ""


def test_feltet_er_valgfrit_tekst_og_beder_om_dansk():
    assert BESKRIVELSE_PARAM["type"] == "string"
    assert "Danish" in BESKRIVELSE_PARAM["description"]


def test_begge_kommandovaerktoejer_kraever_feltet_i_skemaet():
    """Valgfrit fik DeepSeek til at springe det over: 0 af 108 kald (19/9-2026)."""
    import core.tools.simple_tools_definitions as d
    fundet = {}
    for v in vars(d).values():
        if isinstance(v, list):
            for x in v:
                if isinstance(x, dict) and x.get("function", {}).get("name") in ("bash", "operator_bash"):
                    fundet[x["function"]["name"]] = x["function"]["parameters"]
    assert set(fundet) == {"bash", "operator_bash"}
    for p in fundet.values():
        assert p["properties"]["description"] is BESKRIVELSE_PARAM
        assert p["required"] == ["command", "description"]


def test_et_kald_uden_beskrivelse_er_aldrig_et_haardt_brud():
    """Kontrakt-vaernet maa ikke afvise en kommando fordi linjen mangler."""
    from core.tools.tool_schema_contract import violations, haarde
    for navn in ("bash", "operator_bash"):
        brud = violations(navn, {"command": "ls"})
        assert [b.art for b in brud] == ["anbefalet"]
        assert haarde(brud) == []


def test_en_manglende_kommando_er_stadig_haard():
    from core.tools.tool_schema_contract import violations, haarde
    brud = violations("bash", {"description": "Vis filer"})
    assert [b.art for b in haarde(brud)] == ["required"]
