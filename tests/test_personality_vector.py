"""Test: personality_vector write-guard stripper snake_case maskin-id (Jarvis-spec #2)."""
from __future__ import annotations


def test_human_filter_strips_machine_ids():
    # Genskab _human-filterets logik (samme regel som write-guarden i update-stien):
    # snake_case event-navne droppes, menneskelæsbare (m. mellemrum) består.
    def _human(items):
        out = []
        for x in items:
            s = str(x).strip()
            core = s.split(":", 1)[-1].strip()
            if core and " " not in core and core.count("_") >= 2:
                continue
            out.append(x)
        return out

    strengths = [
        "sensory_archive_analysis",                       # maskin-id → drop
        "plugin_container_process_kill_load_reduction_success",  # maskin-id → drop
        "tålmodig og grundig fejlsøgning",                # menneske → behold
    ]
    mistakes = [
        "forgetting_to_stage_changes_before_commit",      # maskin-id → drop
        "Svar bliver for lange i simple repo-opgaver",    # menneske → behold
        "genstart løste ikke problemet",                  # menneske → behold
    ]
    assert _human(strengths) == ["tålmodig og grundig fejlsøgning"]
    assert _human(mistakes) == [
        "Svar bliver for lange i simple repo-opgaver",
        "genstart løste ikke problemet",
    ]


def test_personality_vector_module_imports():
    # Sikrer write-guarden ikke brød modulet.
    import core.services.personality_vector as pv
    assert hasattr(pv, "_merge_vector")


# ── Tre felter var uopnåelige fra tomme (målt 25/9-2026) ───────────────────
#
# Over ALLE 1007 versioner af vektoren på CT105:
#
#     learned_preferences      ikke-tom i 728 versioner
#     confidence_by_domain     ikke-tom i   1
#     recurring_mistakes       ikke-tom i   0
#     strengths_discovered     ikke-tom i   0
#
# Skrivevejen virkede — samme funktion, samme merge-logik. Forskellen stod i
# PROMPTEN: `learned_preferences` havde en additiv instruktion («tilføj nye,
# behold gamle»), de tre andre havde en betingelse der forudsatte en værdi der
# allerede var der.
#
# «Tilføj kun hvis gentaget» på en TOM liste er en bootstrap-låsning: den
# første forekomst skrives aldrig, så der bliver aldrig en anden. Og
# `_merge_vector` deduplikerer i forvejen (`if item not in merged`), så listen
# kan slet ikke udtrykke «gentaget» ved antal — feltet er strukturelt
# «observerede fejl», ikke «fejl talt mere end én gang».


def _prompt() -> str:
    from core.services.personality_vector import _build_update_prompt
    return _build_update_prompt()


def test_ingen_betingelse_forudsaetter_en_vaerdi_der_ikke_findes():
    """Vagten mod at bootstrap-låsningen sniger sig ind igen."""
    p = _prompt()
    for forbudt in ("kun hvis gentaget", "kun ved tydelig evidens"):
        assert forbudt not in p, (
            f"«{forbudt}» kan ikke opfyldes fra en tom liste — "
            "den første post bliver aldrig skrevet, så der kommer aldrig en anden"
        )


def test_de_tre_felter_har_en_additiv_instruktion():
    """Samme form som `learned_preferences`, der SOM DEN ENESTE virkede."""
    p = _prompt()
    for felt in ("recurring_mistakes", "strengths_discovered"):
        assert felt in p
    # Begge lister skal sige at også første forekomst tæller.
    assert p.count("også første gang du ser den") == 2
    # Og dict'en skal kunne få sit første domæne.
    assert "Et domæne uden et tal kan aldrig justeres senere" in p


def test_konservatismen_gaelder_TAL_ikke_tomme_felter():
    """«Vær konservativ — kun opdatér det der faktisk ændrede sig» ramte også
    et tomt felt: der var jo ikke sket en ændring, kun en begyndelse."""
    p = _prompt()
    assert "et TOMT felt er ikke en værdi der skal bevares" in p


def test_maskin_navne_frarades_i_prompten():
    """Skrive-vagten (`_human`) strippede snake_case — rod-kilden til
    maskin-id-lækken i den synlige prompt. Nu står det også i prompten, så
    modellen ikke producerer det der alligevel bliver kasseret."""
    p = _prompt()
    assert "sensory_archive_analysis" in p and "menneskelig form" in p


def test_merge_deduplikerer_saa_en_gentagelse_ikke_bliver_to_poster():
    """Grunden til at «gentaget» aldrig kunne måles ved antal."""
    from core.services.personality_vector import _merge_vector

    ud = _merge_vector(
        {"recurring_mistakes": '["glemmer at køre suiten"]'},
        {"recurring_mistakes": ["glemmer at køre suiten", "ny fejl"]},
    )
    assert ud["recurring_mistakes"] == ["glemmer at køre suiten", "ny fejl"]


# ── Svaret naaede sjældent frem (målt 26/9-2026) ───────────────────────────


def test_taenkningen_er_slaaet_FRA_og_budgettet_raekker():
    """Ræsonnementet åd svar-budgettet. Målt på CT105 mod
    `deepseek-v4.1-flash:cloud`, samme prompt og input:

        np=200            content=   0  thinking=  910  done=length
        np=600            content= 399  thinking=  263  done=stop
        np=600            content=   0  thinking= 2421  done=length
        np=1500           content=  53  thinking= 3203  done=stop
        np=600 think=off  content= 359  thinking=    0  done=stop  (3 af 3)

    Ræsonnementets længde svinger fra 263 til 3.203 tegn, så ethvert fast loft
    er et gæt — selv 600 slog fejl. Med `think: False` er der intet at betale
    for, og alle tre kald svarede med `recurring_mistakes` udfyldt.

    Det er den egentlige grund til at feltet aldrig har ændret sig. Ikke
    tærsklen i prompten.
    """
    import ast
    import inspect

    from core.services import personality_vector as PV

    traeet = ast.parse(inspect.getsource(PV._call_llm).lstrip())
    fundet = []
    for n in ast.walk(traeet):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value == "num_predict":
                    fundet.append(v.value)
    assert fundet, "num_predict findes ikke længere — er kaldet lagt om?"
    assert all(v >= 600 for v in fundet), (
        f"num_predict={fundet} er for lavt; ræsonnementet tæller med i "
        "budgettet og content kommer tom tilbage"
    )

    # Selve rettelsen: uden denne er ethvert loft et gæt.
    kilde = inspect.getsource(PV._call_llm)
    assert '"think": False' in kilde, (
        "tænkningen er slået til igen — ræsonnementet æder svar-budgettet, og "
        "kaldet falder tilbage på den deterministiske sti"
    )


def test_et_tomt_svar_logges_frem_for_at_tie(monkeypatch, caplog):
    """En tom `content` er ikke «intet at sige» — den er et afkortet svar.

    Uden logningen kunne de to ikke skelnes, og forskellen kostede at feltet
    stod tomt i månedsvis.
    """
    import json
    import logging

    from core.services import personality_vector as PV

    class _Svar:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"message": {"content": "", "thinking": "x" * 910},
                               "done_reason": "length"}).encode()

    monkeypatch.setattr(PV.urllib_request, "urlopen", lambda *a, **k: _Svar())

    with caplog.at_level(logging.WARNING):
        ud = PV._call_llm({"provider": "ollama", "model": "m", "base_url": "http://x"},
                          "system", "user")

    assert ud == ""
    assert any("tomt svar" in r.message for r in caplog.records), \
        "et afkortet svar blev slugt i tavshed"
    assert any("length" in str(r.args) for r in caplog.records), \
        "done_reason skal med — den siger HVORFOR det var tomt"
