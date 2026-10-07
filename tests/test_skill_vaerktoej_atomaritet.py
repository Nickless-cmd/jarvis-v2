"""Prompten bad om et værktøj der ikke lå i kaldet.

## Målt 15/9-2026

Codex' analyse, efterprøvet: af kataloget på 471 værktøjer har 24 «skill» i
navnet, og **ingen** af dem overlevede beskæringen til de 48 i den synlige
lane — heller ikke på «brug pdf skill». Alligevel skriver prompten ordret:

    skill_invoke("<navn>") og læs HELE SKILL.md før du skriver svaret

Jarvis gjorde derfor det rationelle: fandt filen med `explore` og læste
SKILL.md i hånden. Det var ikke ulydighed; det var den eneste vej han kunne se.

## Tredje gang mønsteret bider

Kommentaren over `REQUIRED_LAZY_TOOL_NAMES` beskriver præcis det samme for
`explore` den 6/9: «scope tillod det, kataloget nævnte det, prompten anbefalede
det — og pruneren fjernede det fra selve tool-arrayet».

## Reglen

Runtimen må aldrig instruere modellen i at kalde et værktøj, som ikke findes i
den aktuelle request.
"""
from __future__ import annotations

import pytest

from core.tools import copilot_tool_pruning as p
from core.services import skill_relevance_surface as s


def _navn(t: dict) -> str:
    return t.get("name") or (t.get("function") or {}).get("name") or ""


@pytest.fixture
def katalog():
    from core.tools.simple_tools import get_tool_definitions
    return get_tool_definitions()


# ───────────────────────── pinnet er FAST fra 3/10-2026, ikke betinget

def test_skill_invoke_staar_FAST_i_arrayet():
    """Rettelsen 3/10. Pinnet var betinget af et skill-match, og det gjorde
    vaerktoejs-arrayet besked-afhaengigt — arrayet ligger FOER hele samtalen i
    praefikset, saa én aendring koster alt derfra og frem (92 % -> 26 % hit)."""
    assert "skill_invoke" in p.REQUIRED_LAZY_TOOL_NAMES


def test_arrayet_er_IDENTISK_uanset_beskeden(katalog):
    """Den egentlige kontrakt, og den der var groen af den forkerte grund:
    ved taerskel 0,70 matchede naesten ALT («hej hvordan går det?» matchede
    `ui-ux-pro-max`), saa det betingede pin var i praksis fast. Da gulvet blev
    haevet 3/10, blev en naesten-konstant en aegte variabel.

    Testen maaler nu det der betyder noget: samme array, uanset hvad han
    skriver — og `skill_invoke` ER med, ogsaa uden match."""
    alle = katalog
    pools = {}
    for besked in ("hej hvordan går det?",
                   "ret buggen i prompt contract og kør pytest",
                   "hjaelp mig med excel",
                   ""):
        s._SIDSTE = ("", [])
        s._SIDSTE_TRAEF = ("", [])
        pools[besked] = [_navn(d) for d in p.select_tools_for_visible(
            alle, user_message=besked)]
        assert "skill_invoke" in pools[besked], besked or "(tom)"
    foerste = next(iter(pools.values()))
    for besked, pool in pools.items():
        assert pool == foerste, (
            f"arrayet skiftede paa «{besked or '(tom)'}» — forskel: "
            f"{sorted(set(pool) ^ set(foerste))}")


def test_sporet_faestner_INGENTING():
    """`spor_skill_match` erstattede `_betinget_kraevede`. Den logger stadig, for
    log-linjen er det eneste spor for kaeden matched -> surfaced -> TILGAENGELIG
    -> invoked; `cognitive_state.skill_invoked` baerer hverken run- eller
    session-id. Men den maa ikke fæstne noget."""
    for besked in ("hjaelp mig med excel", "hej", ""):
        assert p.spor_skill_match(besked) == (), besked or "(tom)"
    # Bagudkompatibelt navn — to kaldesteder bruger det endnu.
    assert p._betinget_kraevede is p.spor_skill_match


def test_sporet_logger_ved_match_men_ikke_uden(caplog):
    """Uden log-linjen kan man ikke svare paa «virkede rettelsen». Og en log
    paa HVER tur ville vaere stoej, saa den skal fyre praecis ved et match."""
    import logging
    with caplog.at_level(logging.INFO, logger="core.tools.copilot_tool_pruning"):
        s._SIDSTE = ("", [])
        s._SIDSTE_TRAEF = ("", [])
        p.spor_skill_match("hjaelp mig med excel")
        med = [r for r in caplog.records if "skill-atomaritet" in r.getMessage()]
        caplog.clear()
        s._SIDSTE = ("", [])
        s._SIDSTE_TRAEF = ("", [])
        p.spor_skill_match("")
        uden = [r for r in caplog.records if "skill-atomaritet" in r.getMessage()]
    assert len(med) == 1, "intet spor ved et match"
    assert uden == [], "sporet fyrede uden et match"


def test_sporet_kaster_aldrig(monkeypatch):
    """Et spor maa ikke kunne vaelte en tur."""
    monkeypatch.setattr(s, "matchede_skills",
                        lambda _m: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert p.spor_skill_match("hjaelp mig med excel") == ()


def test_selektionen_laeser_ikke_et_betinget_saet(monkeypatch):
    """Vagten mod at betingetheden sniger sig tilbage: `kraevede` maa bestaa af
    de FASTE lister alene. Et match maa kunne fyre uden at aendre ét navn."""
    import ast
    import inspect
    kilde = inspect.getsource(p.select_tools_for_visible)
    traeet = ast.unparse(ast.parse(inspect.cleandoc(kilde)))
    assert "_betinget_kraevede(user_message))" not in traeet, (
        "det betingede saet er lagt tilbage i `kraevede` — arrayet bliver "
        "besked-afhaengigt, og det koster hele praefikset")


# ──────────────────────────────────── kontrakten, maalt paa det AEGTE katalog

@pytest.mark.parametrize("besked", [
    "hjaelp mig med excel", "lav en pdf rapport",
    "skriv en rapport om kvartalet", "docker container starter ikke",
])
def test_naevner_prompten_det_saa_LIGGER_det_der(katalog, besked):
    """Kontrakten. Før rettelsen fejlede alle fire."""
    naevner = "skill_invoke(" in (s.relevant_skills_section(besked) or "")
    if not naevner:
        pytest.skip(f"matcheren fandt intet for «{besked}» — intet loefte at holde")
    ud = p.select_tools_for_visible(katalog, user_message=besked)
    assert "skill_invoke" in {_navn(t) for t in ud}


@pytest.mark.parametrize("besked", ["hej", "ok tak"])
def test_pladsen_bruges_med_VILJE_ogsaa_uden_match(katalog, besked):
    """VENDT 3/10-2026. Testen haevdede foer at `skill_invoke` IKKE maatte med
    uden et match — «en plads ud af 48 er ikke gratis».

    Den plads bruges nu med vilje. Et betinget pin gjorde arrayet
    besked-afhaengigt, og arrayet ligger foer hele samtalen i praefikset: én
    aendring koster alt derfra og frem. Maalt tre gange — 92 % -> 26 % hit,
    +419 tegn -> 62.672 miss-tokens. Én plads er billigere end praefikset."""
    ud = p.select_tools_for_visible(katalog, user_message=besked)
    assert "skill_invoke" in {_navn(t) for t in ud}


def test_kappen_holder_stadig(katalog):
    """Fæstningen må ikke sprænge loftet — så ville den bare flytte problemet."""
    for besked in ("hjaelp mig med excel", "hej"):
        ud = p.select_tools_for_visible(katalog, user_message=besked)
        assert len(ud) <= p.VISIBLE_MAX_TOOLS, (besked, len(ud))


def test_de_faste_vaerktoejer_overlever_stadig(katalog):
    """`load_more_tools` og `explore` var der før. En ny betinget regel må ikke
    have skubbet dem ud — det var netop sådan `explore` forsvandt 6/9."""
    ud = {_navn(t) for t in p.select_tools_for_visible(katalog, user_message="hjaelp mig med excel")}
    for navn in ("load_more_tools", "scout_agent", "dispatch_code_mode_task"):
        assert navn in ud, navn


# ───────────────────────────────── ÉN faestning, ikke to (den skjulte fejl)

def test_faestningen_findes_praecis_ÉT_sted():
    """Logikken lå i TO kopier i samme funktion — én i den tidlige udgang
    (`remaining <= 0`) og én efter Tier 2. Da reglen blev tilføjet, ramte den
    kun den ene, og rettelsen så ud til ikke at virke: Tier 1 sprænger kappen
    alene i cowork-scope, så det er netop den tidlige udgang der tages.

    To kopier af samme beslutning er dobbelt sandhed.
    """
    import inspect
    kilde = inspect.getsource(p.select_tools_for_copilot)
    assert kilde.count("_faestn_kraevede(") == 2, "de to udgange deler ikke faestningen"
    assert "REQUIRED_LAZY_TOOL_NAMES" not in kilde, "der er stadig en egen kopi"


def test_den_tidlige_udgang_faestner_ogsaa(katalog):
    """Den vej der FAKTISK tages i cowork-scope, hvor Tier 1 alene er over 48."""
    # Tvinger remaining <= 0. Var 8, da de faste var 8; bundet til listens
    # længde nu, så en ny fast post (dispatch_code_mode_task 17/9) ikke gør testen
    # til en test af listens længde.
    #
    # 1/10-2026: loftet skal følge HELE det krævede sæt, ikke kun
    # `REQUIRED_LAZY_TOOL_NAMES`. Da sikkerhedsgulvet blev håndhævet i
    # `_faestn_kraevede` (`75e7aa9a3`, 30/9) voksede sættet fra 13 til 40
    # unikke navne, mens loftet her stod på 14. Så blev `beholdt` længere end
    # `max_tools`, og den afsluttende `[:max_tools]` skar i de KRÆVEDE efter
    # katalog-position — `skill_invoke` ligger som nr. 437 og røg ud.
    #
    # Testen var altså ikke forældet af den betingede fæstning (15/9); den
    # mistede sit eget regnestykke da sættet voksede. Bindes loftet til begge
    # lister, måler den igen præcis det den hedder: at den TIDLIGE udgang
    # fæstner.
    lille = len(set(p.REQUIRED_LAZY_TOOL_NAMES) | set(p.SAFETY_FLOOR)) + 1
    ud = p.select_tools_for_copilot(
        katalog, user_message="hjaelp mig med excel", max_tools=lille, stable_only=True)
    assert "skill_invoke" in {_navn(t) for t in ud}


# ───────────────────────────────────────── ét opslag, to forbrugere

def test_prompt_og_beskaerer_deler_opslaget(monkeypatch):
    """To opslag kunne give to forskellige svar — og så ville kontrakten kunne
    brydes uden at nogen af siderne var forkerte hver for sig."""
    kald = []
    aegte = s._traef
    monkeypatch.setattr(s, "_traef", lambda b: kald.append(b) or aegte(b))
    s._SIDSTE = ("", [])
    s.relevant_skills_section("hjaelp mig med excel")
    n_efter_prompt = len(kald)
    p._betinget_kraevede("hjaelp mig med excel")
    assert len(kald) == n_efter_prompt, "beskaereren slog op igen i stedet for at genbruge"


# ─────────────────────────────── autonome ture (15/9-2026)

@pytest.fixture
def ryd_memo():
    s._SIDSTE = ("", [])
    yield
    s._SIDSTE = ("", [])


def _saet_run(rid: str) -> None:
    import core.services.run_closure_gate as g
    g._set_current_run(rid)


def _saet_origin(o: str) -> None:
    import core.services.run_closure_gate as g
    g._set_current_origin(o)


def test_TELEGRAM_beskeder_beholder_deres_skills(ryd_memo):
    """Fejlen jeg selv lavede, og som denne test findes for at forhindre.

    Første udgave undtog på run-id'ets «autonomous-»-præfiks. Men
    kanal-gatewayen for Telegram og Discord sender HANS beskeder gennem
    `start_autonomous_run`, som giver dem netop det præfiks. Målt: hans samtale
    om aftensmad 15:54 og 16:02 kørte som `autonomous-96c2b` og
    `autonomous-473bd`, og undtagelsen fjernede skills fra dem.

    `origin` skelner hvor præfikset ikke kan. Målt på 478 ture over 14 dage:
    recurring 249 · heartbeat 111 · dream 53 · wakeup 34 · **autonomous 31**,
    og kun den sidste har en bruger bag sig.
    """
    _saet_origin("autonomous")
    try:
        assert s.matchede_skills("lav et regneark over forbruget")
    finally:
        _saet_origin("")


@pytest.mark.parametrize("origin", ["recurring", "heartbeat", "dream"])
def test_selvstartede_ture_faar_ingen_skills(ryd_memo, origin):
    """Maskinen der starter sig selv har ingen opgave fra ham."""
    _saet_origin(origin)
    try:
        assert s.matchede_skills("lav et regneark over forbruget") == []
    finally:
        _saet_origin("")


def test_genoptagelser_beholder_skills(ryd_memo):
    """`wakeup` genoptager HANS afbrudte arbejde — der er en opgave bag den."""
    _saet_origin("wakeup")
    try:
        assert s.matchede_skills("lav et regneark over forbruget")
    finally:
        _saet_origin("")


def test_ukendt_origin_beholder_skills(ryd_memo):
    """Fejlretningen: kender vi ikke turen, er det hans der betyder noget."""
    _saet_origin("")
    assert s.matchede_skills("lav et regneark over forbruget")


def test_autonome_ture_faar_ingen_skills_i_PROMPTEN(ryd_memo):
    """FLYTTET 3/10-2026. Testen maalte `_betinget_kraevede(...) == ()` — men
    efter at pinnet blev FAST returnerer den altid tomt, saa hævdelsen var
    trivielt sand og maalte ingenting.

    Undtagelsen gaelder prompt-siden, og det er der den skal maales: en autonom
    tur maa ikke faa skills foreslaaet, for der er ingen bruger der spurgte om
    noget. Vaerktoejs-arrayet er med VILJE origin-uafhaengigt nu — se
    `test_arrayet_er_IDENTISK_uanset_beskeden`."""
    _saet_origin("heartbeat")
    try:
        assert s.matchede_skills("lav et regneark over forbruget") == []
        assert (s.relevant_skills_section("lav et regneark over forbruget") or "") == ""
    finally:
        _saet_origin("")


def test_arrayet_er_det_SAMME_paa_en_autonom_tur(katalog, ryd_memo):
    """Modstykket: prompten undtager, arrayet goer IKKE. Skiftede arrayet med
    origin, ville hver autonom tur kaste praefikset — og de koerer hele
    doegnet."""
    _saet_origin("")
    hans = [_navn(t) for t in p.select_tools_for_visible(katalog, user_message="hjaelp mig med excel")]
    _saet_origin("heartbeat")
    try:
        auto = [_navn(t) for t in p.select_tools_for_visible(katalog, user_message="hjaelp mig med excel")]
    finally:
        _saet_origin("")
    assert auto == hans, f"arrayet foelger origin — forskel: {sorted(set(auto) ^ set(hans))}"
    assert "skill_invoke" in auto


def test_autonome_ture_faar_ingen_skills(ryd_memo):
    """Målt over tre timer: fladen fyrede tre gange, og alle tre var autonome
    ture. Der var ingen bruger der spurgte om noget.

        autonomous-e  «Begge bekræftet. Dream note verificeret…»
        autonomous-d  «Data samlet. DB er sund (integrity OK)…»
        autonomous-3  «hjemme. Her er den korte rapport…»

    Nul af forslagene blev brugt — hvilket var KORREKT, ikke en fejl. Det
    kostede ~55 ms opslag og en plads ud af 48 på hver baggrundstur.
    """
    # RETTET 15/9: praefikset alene undtager IKKE laengere — det ramte ogsaa
    # hans Telegram-beskeder. Det er `origin` der afgoer.
    _saet_run("autonomous-abc123")
    _saet_origin("heartbeat")
    try:
        assert s.matchede_skills("hjaelp mig med excel") == []
    finally:
        _saet_run(""); _saet_origin("")


def test_synlige_ture_er_uberoerte(ryd_memo):
    _saet_run("visible-abc123")
    try:
        assert s.matchede_skills("hjaelp mig med excel") == ["excel-automation"]
    finally:
        _saet_run("")


def test_uden_et_kendt_run_koerer_vi_som_foer(ryd_memo):
    """Fejlretningen: tvivlen falder ud til at BEHOLDE skills for hans ture.
    Run-id'et sættes kun af `runtime.autonomous_run_started`, så en synlig tur
    har ofte slet intet id — og den må ikke miste sine skills af den grund."""
    _saet_run("")
    assert s.matchede_skills("hjaelp mig med excel") == ["excel-automation"]


def test_beskaereren_foelger_med(ryd_memo):
    """Det er hele pointen med ét delt opslag: prompten og værktøjsvalget kan
    ikke komme til at sige hver sit.

    RETTET 15/9: testen brugte run-id'ets præfiks, som ikke længere undtager —
    det ramte også hans Telegram-beskeder. Det er `origin` der afgør.
    """
    _saet_origin("heartbeat")
    try:
        # MAALT PAA PROMPT-SIDEN 3/10: `_betinget_kraevede` returnerer nu altid
        # tomt, saa den gamle haevdelse var trivielt sand.
        assert s.matchede_skills("hjaelp mig med excel") == []
    finally:
        _saet_origin("")


def test_en_fejl_i_opslaget_undtager_ikke(ryd_memo, monkeypatch):
    """Kan vi ikke afgøre det, er svaret NEJ — altså kør som før."""
    import core.services.session_context_resolve as scr
    monkeypatch.setattr(scr, "aktivt_run_id",
                        lambda standard="": (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert s._er_autonom_tur() is False


# ──────────────────── kalibrering og formulering (15/9-2026)

def test_taersklerne_ligger_i_embedderens_faktiske_interval():
    """De gamle tal (0,30/0,50) stammede fra HuggingFace-embedderen. Den lokale
    har hele sit interval mellem 0,59 og 0,80 — målt på 200 af hans beskeder —
    så en tærskel på 0,50 lå under ALT og gjorde «STÆRKT» til «altid».

    OMSKREVET 3/10-2026. Testen hævdede `_PRIMARY_THRESHOLD > _THRESHOLD`,
    altså at der fandtes et BÅND mellem «sekundært» og «primært» match. Jarvis
    fjernede båndet samme dag (`ef8f7b0d5`): det nederste af det var 88 % støj,
    og gulvet er nu primær-tærsklen. Testen pinnede dermed et design der med
    vilje ikke gælder længere.

    Den pinner nu hensigten: ÉN tærskel, og den ligger inde i embedderens
    faktiske interval. Og den har et loft — et gulv på 0,80 ville lægge sig
    over næsten alt og gøre «STÆRKT» til «aldrig», altså den modsatte fejl af
    den 0,50 lavede.
    """
    assert s._THRESHOLD >= 0.59, "gulvet ligger under embedderens interval"
    assert s._THRESHOLD <= 0.80, "gulvet ligger over embedderens interval"
    assert s._THRESHOLD == s._PRIMARY_THRESHOLD, (
        "baandet er lagt tilbage. Det blev fjernet 3/10 fordi dets nederste "
        "88 % var stoej — genindfoeres det, skal tallene maales igen, ikke "
        "gaettes")


def test_der_er_EN_taerskel_og_ikke_to_kilder():
    """Båndet var to tal der kunne drive fra hinanden. Nu er `_THRESHOLD`
    DEFINERET som `_PRIMARY_THRESHOLD` i kilden — ikke som et andet tal der
    tilfældigvis er ens. Står de som to literaler, kan den ene rettes alene."""
    import ast
    import inspect
    kilde = inspect.getsource(s)
    for node in ast.walk(ast.parse(kilde)):
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", "") == "_THRESHOLD" for t in node.targets)):
            assert isinstance(node.value, ast.Name), (
                "_THRESHOLD staar som sit eget tal — det skal PEGE paa "
                "_PRIMARY_THRESHOLD, saa de to ikke kan drive fra hinanden")
            assert node.value.id == "_PRIMARY_THRESHOLD"
            break
    else:
        raise AssertionError("_THRESHOLD tildeles ikke laengere i modulet")


def test_et_staerkt_match_er_en_INSTRUKS(monkeypatch):
    """Målt: et match på 0,79 blev præsenteret som «Vil du ikke, så lad være»
    og han brugte 47 bash-kald i stedet."""
    monkeypatch.setattr(s, "_traef", lambda b: [{"name": "xlsx", "score": 0.79}])
    ud = s.relevant_skills_section("lav et regneark over noget")
    assert "STÆRKT match" in ud
    assert "Kald skill_invoke" in ud
    assert "skriv kort hvorfor" in ud, "et fravalg skal begrundes"
    assert "lad være" not in ud, "et staerkt match maa ikke lyde som et tilbud"


def test_et_svagt_match_er_stadig_et_TILBUD(monkeypatch):
    """Tærsklen slipper ~4% støj igennem. En hård tone på dem ville gøre hver
    fejlmatch til en blindgyde."""
    monkeypatch.setattr(s, "_traef", lambda b: [{"name": "tdd", "score": 0.72}])
    ud = s.relevant_skills_section("noget helt andet her")
    assert "STÆRKT" not in ud
    assert "tilbud, ikke et krav" in ud
    assert "skriv kort hvorfor" not in ud


def test_aerligheds_klausulen_gaelder_BEGGE_veje(monkeypatch):
    """«Sig aldrig at du brugte et skill uden at have invokeret det» må ikke
    forsvinde i den ene gren."""
    for score in (0.79, 0.72):
        monkeypatch.setattr(s, "_traef", lambda b, _s=score: [{"name": "pdf", "score": _s}])
        ud = s.relevant_skills_section("en opgave om noget")
        assert "Sig aldrig at du brugte et skill" in ud, score


def test_eksplicit_navn_slaar_scoren(monkeypatch):
    """«brug pdf skill» giver 0,76 — under tærsklen. Men et navn han selv
    skriver er det stærkeste signal der findes."""
    monkeypatch.setattr(s, "_traef", lambda b: [{"name": "pdf", "score": 0.76}])
    assert "STÆRKT match" in s.relevant_skills_section("brug pdf skill")
    # Samme score, men navnet staar ikke i beskeden → stadig et tilbud.
    assert "STÆRKT" not in s.relevant_skills_section("lav noget med tal og tabeller")


@pytest.mark.parametrize("navn,besked,forventet", [
    ("pdf", "brug pdf skill", True),
    ("excel-automation", "brug excel automation", True),
    ("pdf", "hej med dig", False),
    ("xlsx", "lav et regneark", False),
    ("ui", "noget om ui her", False),          # for kort til at taelle
])
def test_navne_genkendelsen(navn, besked, forventet):
    assert s._navnet_staar_i(navn, besked) is forventet


def test_origin_bliver_FAKTISK_gemt_fra_eventet(ryd_memo):
    """Mutationen der overlevede: fjern `_set_current_origin` fra
    `_on_run_started`, og alle tests blev grønne — fordi de sætter origin
    direkte og aldrig rører vejen fra eventet.

    Husets hyppigste fejl, endnu en gang: mekanismen findes, kalderen mangler.
    """
    import core.services.run_closure_gate as g
    _saet_origin("")
    try:
        g._on_run_started({"run_id": "autonomous-xyz", "origin": "heartbeat"})
        assert g.aktuel_origin() == "heartbeat"
        # …og det skal faktisk undtage turen.
        assert s.matchede_skills("lav et regneark over forbruget") == []
    finally:
        _saet_origin("")
        g._set_current_run("")


def test_en_fejl_i_origin_opslaget_undtager_IKKE(ryd_memo, monkeypatch):
    """Kan vi ikke læse turen, er det hans ture der betyder noget. Mutationen
    «returnér True ved fejl» ville have taget skills fra alt i stilhed."""
    import core.services.run_closure_gate as g
    monkeypatch.setattr(g, "aktuel_origin",
                        lambda: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert s._er_selvstartet_tur() is False
    assert s.matchede_skills("lav et regneark over forbruget")
