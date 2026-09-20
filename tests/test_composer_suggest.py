"""Forslag i komponisten — hvad der skrives videre mens man skriver.

## Hvorfor lokalt og ikke den betalte lane

Et forslag er baggrundsarbejde, ikke Bjørns tur. Reglen han har gentaget mange
gange — og som blev håndhævet i koden 14/9 — er at den betalte DeepSeek-API kun
må bruges i hans egne kørsler. Et forslag fyrer mens han *skriver*, altså før
der overhovedet er en tur. Derfor lokal ollama, og kun lokal.

Der er en grund mere, og den vejer tungere: **udkastet forlader aldrig
maskinen.** Halvskrevne sætninger er det mest private der findes i en
samtale — de indeholder det man fortryder, omformulerer eller sletter.

## Hvorfor et kort loft på ventetiden

`semantic_memory._ollama_base_url` bærer husets erfaring: recall-embeds
konkurrerede med det synlige svar om GPU-ollamaen og køede **28–91 sekunder**.
Et forslag der kommer efter et sekund er allerede uinteressant — brugeren har
skrevet videre. Derfor et hårdt loft, og tomt svar frem for et sent.
"""
from __future__ import annotations

import pytest

from core.services import composer_suggest as cs


# ─────────────────────────────────────────────────────────── hvad der sendes

def test_forslaget_er_KUN_fortsaettelsen(monkeypatch):
    """Modellen gentager gerne hele sætningen. Gjorde vi ikke noget, ville
    komponisten vise «kan du tjekke kan du tjekke om…»."""
    monkeypatch.setattr(cs, "_kald_model",
                        lambda *a, **k: "kan du lige tjekke om der er fejl i filen")
    assert cs.foreslaa("kan du lige tjekke om der er") == " fejl i filen"


def test_gentagelse_med_ANDEN_store_bogstaver_fanges_ogsaa():
    """Modellen retter gerne begyndelsesbogstavet. Et match der kræver samme
    kasse ville lade gentagelsen slippe igennem."""
    assert cs._afkort("kan du lige", "Kan du lige tjekke det") == " tjekke det"


def test_et_svar_der_IKKE_gentager_bruges_som_det_er():
    """`_afkort` svarer kun paa «hvor meget er gentagelse». Mellemrummet der
    haefter fortsaettelsen paa det sidste ord, saettes i `foreslaa` — ét sted,
    saa det ikke afhaenger af om modellen huskede at skrive det."""
    assert cs._afkort("kan du lige", " tjekke det") == "tjekke det"


def test_foreslaa_HAEFTER_fortsaettelsen_paa_med_et_mellemrum(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: "tjekke det")
    assert cs.foreslaa("kan du lige") == " tjekke det"


def test_tegnsaetning_haefter_UDEN_mellemrum(monkeypatch):
    """«…tjekke det» + «, tak» — ikke «…tjekke det , tak»."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: ", tak")
    assert cs.foreslaa("kan du lige tjekke det") == ", tak"


def test_kun_FOERSTE_linje(monkeypatch):
    """En komponist-linje er én linje. Resten er modellen der begynder at
    skrive svaret i stedet for forslaget."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: " se på det\n\nHer er hvad jeg fandt:")
    assert cs.foreslaa("kan du lige") == " se på det"


def test_omsluttende_anfoerselstegn_fjernes(monkeypatch):
    """Maalt 14/9: qwen svarede `"kan du lige tjekke om der er fejl?"` — med
    citationstegn om hele sætningen."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: '"kan du lige tjekke det"')
    assert cs.foreslaa("kan du lige") == " tjekke det"


def test_forslaget_er_KORT(monkeypatch):
    """Et langt forslag er ikke et forslag, det er et svar. Klippes ved et
    ordskel, ikke midt i et ord — et halvt ord ligner en fejl."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: " " + "ord " * 60)
    ud = cs.foreslaa("skriv")
    assert len(ud) <= cs.MAKS_TEGN
    assert not ud.endswith("or")


# ───────────────────────────────────────────────── hvornaar der IKKE spoerges

def test_for_KORT_udkast_spoerger_slet_ikke(monkeypatch):
    """Under nogle faa tegn er der intet at gaette paa, og et forslag ville
    vaere stoej der flimrer ved hvert tastetryk."""
    kaldt: list[int] = []
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: kaldt.append(1) or "x")
    assert cs.foreslaa("ka") == ""
    assert kaldt == []


def test_tomt_udkast_spoerger_ikke(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa("") == ""
    assert cs.foreslaa("   ") == ""


def test_et_FAERDIGT_udkast_faar_intet_forslag(monkeypatch):
    """Slutter sætningen paa tegnsaetning, er brugeren faerdig. At foreslaa
    videre dér er at tale i munden paa ham."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte alligevel"))
    for slut in ("kan du tjekke det?", "gør det.", "ja!", "vent:"):
        assert cs.foreslaa(slut) == ""


def test_et_MEGET_langt_udkast_spoerger_ikke(monkeypatch):
    """Skriver han et helt afsnit, ved han hvad han vil. Og prompten skal ikke
    vokse ubegraenset."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa("x " * 400) == ""


# ─────────────────────────────────────────────────────────── den maa ikke gøre skade

def test_en_MODELFEJL_giver_tomt_og_kaster_ikke(monkeypatch):
    """Komponisten skal skrive videre uanset. Et forslag er en bekvemmelighed,
    ikke en funktion man kan miste."""
    monkeypatch.setattr(cs, "_kald_model",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert cs.foreslaa("kan du lige tjekke") == ""


def test_et_TOMT_modelsvar_giver_tomt(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: "")
    assert cs.foreslaa("kan du lige tjekke") == ""


def test_et_svar_der_kun_ER_udkastet_giver_tomt(monkeypatch):
    """Modellen gentog og tilfoejede intet. Et tomt forslag er aerligt; et
    forslag der foreslaar det man allerede har skrevet, er stoej."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: "kan du lige tjekke")
    assert cs.foreslaa("kan du lige tjekke") == ""


# ─────────────────────────────────────────────────── den betalte lane er FORBUDT

def test_der_bruges_en_LOKAL_model():
    """Kilde-vagt paa den regel Bjoern har gentaget mange gange: den betalte
    DeepSeek-API er kun til hans egne ture. Et forslag fyrer FOER der er en tur.

    Og udkastet er det mest private i en samtale — halvskrevne saetninger
    indeholder det man fortryder og sletter. Det maa ikke forlade maskinen.
    """
    import inspect
    kilde = inspect.getsource(cs)
    assert "127.0.0.1" in kilde or "_ollama_base_url" in kilde
    assert "deepseek.com" not in kilde


def test_ventetiden_har_et_KORT_loft():
    """Huset har erfaringen skrevet ned: recall-embeds koeede 28-91 sekunder
    bag det synlige svar paa samme GPU-ollama. Et forslag der kommer efter et
    sekund er allerede uinteressant."""
    assert cs.TIMEOUT_S <= 2.0


def test_modellen_kan_saettes_uden_kode_deploy():
    """Bjoern har qwen paa sin GPU i dag; i morgen er det en anden."""
    assert cs.MODEL_NOEGLE == "composer_suggest_model"


# ──────────────────────────────────── forslag til den NAESTE besked (17/9)
#
# Bjoern: «det kommer dumpende mens jeg skriver, det er virkelig traels» — og
# «auto suggest skal jo vaere ud fra konteksten af DIN besked». Forslaget er
# altsaa ikke resten af hans saetning, men et bud paa hvad han kunne sige nu,
# vist dér hvor pladsholderen staar. Kilden er samtalen, ikke tastetrykkene.


def _samtale(*par):
    return [{"role": r, "content": c} for r, c in par]


def test_naeste_forslag_bygger_paa_ASSISTENTENS_SIDSTE_BESKED(monkeypatch):
    """AENDRET 20/9-2026. Foer stod de seks seneste beskeder fra BEGGE sider i
    prompten. Bjoern: «hvis den ska virke rigtigt, skal den kun udlede kontekst
    fra din sidste besked, og hvad naeste step kan vaere». Hans egne tidligere
    formuleringer er stoej for en 4b-model — naeste skridt ligger i svaret,
    ikke i spoergsmaalet der foerte til det."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("user", "hvordan ser cheap lane ud?"),
        ("assistant", "81% succes, 34 udbydere. To staar i karantaene."),
    ))
    sendt: list[str] = []
    monkeypatch.setattr(cs, "_kald_model",
                        lambda p: sendt.append(p) or "vis de to i karantaene")
    assert cs.foreslaa_naeste("s1") == "vis de to i karantaene"
    # Svaret skal FAKTISK med — ellers gaetter modellen i blinde.
    assert "karantaene" in sendt[0]
    # ... og hans eget spoergsmaal skal IKKE.
    assert "cheap lane" not in sendt[0], "brugerens egne beskeder er stoej her"


def test_ANBEFALINGEN_loeftes_ud_saa_modellen_ikke_vaelger_selv(monkeypatch):
    """Bjoern 20/9-2026: «hvis du feks. har skrevet 3 veje hvor du anbefaler en
    boer den gaa med den». En 4b-model laeser en lang besked som en liste af
    muligheder og griber den foerste. Staar anbefalingen ALENE under sin egen
    overskrift, er der ikke noget at vaelge imellem."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant",
        "Tre veje: (a) rydde op i worktrees, (b) genstarte ollama, "
        "(c) lade den ligge til i morgen. Jeg ville tage (b) foerst — "
        "(a) kan vente til der er ro paa.")))
    sendt: list[str] = []
    monkeypatch.setattr(cs, "_kald_model",
                        lambda p: sendt.append(p) or "genstart ollama og se om den kommer op")
    assert cs.foreslaa_naeste("s1") == "genstart ollama og se om den kommer op"
    assert "Assistenten anbefaler: Jeg ville tage (b) foerst" in sendt[0]


def test_den_SIDSTE_anbefaling_vinder():
    """Staar der «jeg ville tage (b)» EFTER «jeg foreslaar tre veje», er det
    (b) der er dommen — ikke den foerste vending der lignede en anbefaling."""
    t = ("Jeg foreslaar vi ser paa tre ting. Jeg ville starte med logfilen.")
    assert cs._anbefaling(t) == "Jeg ville starte med logfilen."


def test_uden_en_anbefaling_staar_beskeden_ALENE(monkeypatch):
    """En besked uden valg skal ikke faa en tom overskrift paahaeftet."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Led Lys er taendt — standerlampen staar stadig off.")))
    sendt: list[str] = []
    monkeypatch.setattr(cs, "_kald_model", lambda p: sendt.append(p) or "taend standerlampen ogsaa")
    cs.foreslaa_naeste("s1")
    assert "anbefaler" not in sendt[0]


def test_en_lang_besked_beholder_BEGGE_ender():
    """En ren `[:maks]` ville tage begyndelsen — og netop dér staar
    anbefalingen ikke. Den staar til sidst, efter mulighederne."""
    lang = "START " + "fyld " * 1000 + "SLUT jeg ville tage (b)."
    ud = cs._klip_kontekst(lang)
    assert ud.startswith("START")
    assert ud.endswith("jeg ville tage (b).")
    assert len(ud) <= cs.MAKS_KONTEKST_TEGN + 10


def test_naeste_forslag_er_en_HEL_besked_uden_hoeftende_mellemrum(monkeypatch):
    """Fortsaettelses-formen haefter et mellemrum paa. Her er der intet at
    haefte paa: feltet er tomt, og et forslag der begynder med mellemrum ville
    blive til en besked der goer det samme."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Det er rettet og verificeret — testene er groenne igen.")))
    monkeypatch.setattr(cs, "_kald_model", lambda p: "  deploy det til ct105  ")
    assert cs.foreslaa_naeste("s1") == "deploy det til ct105"


def test_modellens_ROLLENAVN_fjernes(monkeypatch):
    """Rollerne staar i prompten, saa modellen skriver dem gerne med."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Klar — jeg har bygget det og deployet det til ct105.")))
    monkeypatch.setattr(cs, "_kald_model", lambda p: "Bruger: koer testene igen")
    assert cs.foreslaa_naeste("s1") == "koer testene igen"


def test_uden_SESSION_spoerges_der_ikke(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa_naeste("") == ""
    assert cs.foreslaa_naeste("   ") == ""


def test_en_TOM_samtale_giver_intet_forslag(monkeypatch):
    """Foerste besked i en ny samtale er hans egen. Der er intet at foreslaa
    ud fra, og GreetingHero staar der i forvejen."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [])
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa_naeste("s1") == ""


def test_mens_HANS_besked_venter_paa_svar_foreslaas_intet(monkeypatch):
    """Sidste besked er hans egen → turen er i gang. At foreslaa den naeste
    besked dér er at tale i munden paa et svar der er paa vej."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Det er rettet."), ("user", "og deploy det"),
    ))
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa_naeste("s1") == ""


def test_en_LANG_besked_klippes_i_prompten(monkeypatch):
    """Ét vaerktoejs-svar paa 30k tegn ville ellers skubbe alt det der faktisk
    blev sagt ud af prompten — og koere den lokale model i staa."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", "x" * 5000)))
    sendt: list[str] = []
    monkeypatch.setattr(cs, "_kald_model", lambda p: sendt.append(p) or "ok")
    cs.foreslaa_naeste("s1")
    assert len(sendt[0]) < 2000


def test_en_DB_fejl_giver_tomt_og_kaster_ikke(monkeypatch):
    monkeypatch.setattr(cs, "_samtale",
                        lambda sid: (_ for _ in ()).throw(RuntimeError("laast")))
    assert cs.foreslaa_naeste("s1") == ""


def test_en_MODELFEJL_i_naeste_forslag_giver_tomt(monkeypatch):
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Klar — jeg har bygget det og deployet det til ct105.")))
    monkeypatch.setattr(cs, "_kald_model",
                        lambda p: (_ for _ in ()).throw(RuntimeError("nede")))
    assert cs.foreslaa_naeste("s1") == ""


# ─────────────────────── forslaget skal vaere en ORDRE, ikke en replik (17/9)
#
# Maalt paa ti aegte samtaler: modellen SVAREDE assistenten i stedet for at
# bede om noget — «Fire. Det er nemt.», «4. Takk for det.», «Ja, det kan vi
# lave i morgen!», «Jeg forstaar ikke, hvad du mener». Et svar kan han skrive
# selv; et forslag skal spare ham for at formulere en ordre. Og et forkert
# forslag koster mere end intet: det staar og fylder pladsholderens plads.

_LANGT_SVAR = "Det er rettet og verificeret — begge services koerer igen paa ct105."


@pytest.mark.parametrize("replik", [
    "Ja, det kan vi lave i morgen!",
    "Nej, det behoever du ikke",
    "Tak for det",
    "Okay, saa proever vi det",
    "Jeg forstaar ikke, hvad du mener",
    "Super, det lyder godt",
])
def test_en_REPLIK_er_ikke_et_forslag(monkeypatch, replik):
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", _LANGT_SVAR)))
    monkeypatch.setattr(cs, "_kald_model", lambda p: replik)
    assert cs.foreslaa_naeste("s1") == ""


def test_en_PAASTAND_er_heller_ikke_et_forslag(monkeypatch):
    """Maalt: «Fyrede kl. 20:18, ventetid var 60 sekunder» — en konstatering.
    En ordre begynder aldrig med et datids-verbum, og et spoergsmaal baerer
    sit spoergsmaalstegn; derfor kan de skelnes uden at forstaa saetningen."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", _LANGT_SVAR)))
    monkeypatch.setattr(cs, "_kald_model", lambda p: "Fyrede kl. 20:18, ventetid var 60 sekunder")
    assert cs.foreslaa_naeste("s1") == ""


@pytest.mark.parametrize("ordre", [
    "Deploy det og hold oeje med journalen",
    "Vis mig de to der staar i karantaene",
    "Hvorfor fejler den kun paa ct105?",
    "Ret det og koer testene igen",
    "Jeg vil have dig til at rulle det tilbage",
])
def test_en_ORDRE_slipper_igennem(monkeypatch, ordre):
    """Vagterne maa ikke aede det de er sat til at beskytte. «Jeg vil have dig
    til at…» begynder med «Jeg» men er en ordre, ikke en replik."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", _LANGT_SVAR)))
    monkeypatch.setattr(cs, "_kald_model", lambda p: ordre)
    assert cs.foreslaa_naeste("s1") == ordre


@pytest.mark.parametrize("stump", ["4.", "OK", "Generation cancelled.", "Ja."])
def test_en_STUMP_til_sidst_giver_intet_forslag(monkeypatch, stump):
    """Der er intet naeste skridt at bygge paa. Maalt: praecis dér begyndte
    modellen at foere samtalen i stedet for at foreslaa noget."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", stump)))
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa_naeste("s1") == ""


def test_prompten_forlanger_noget_KONKRET_fra_samtalen():
    """«Saa kan vi gaa videre til naeste trin» er sandt om enhver samtale og
    derfor ubrugeligt i denne. Kravet staar i prompten; dét kan maales."""
    assert "KONKRET" in cs._PROMPT_NAESTE
    assert "ORDRE" in cs._PROMPT_NAESTE


def test_ruten_vaelger_tilstand_efter_om_der_ER_et_udkast(monkeypatch):
    """Samme endpoint, to tilstande. Mobilen sender et udkast og skal stadig
    faa fortsaettelsen; desk sender et tomt felt og skal have naeste besked."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa", lambda u: " tjekke det")
    # Naeste-formen gaar siden 20/9-2026 gennem `foreslaa_naeste_detaljer`,
    # fordi klienten skal have et id at melde sit valg tilbage paa.
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer", lambda s: {
        "forslag": f"naeste til {s}", "forslag_id": "cs-x", "kilde_besked_id": "m1"})
    assert r.suggest(r.Udkast(udkast="kan du lige", session_id="s1"))["forslag"] == " tjekke det"
    assert r.suggest(r.Udkast(udkast="   ", session_id="s1"))["forslag"] == "naeste til s1"
    assert r.suggest(r.Udkast(session_id="s1"))["forslag"] == "naeste til s1"


# ─────────────────────────────────────────────────── fladen skal kunne NAAS

def test_ruten_er_MONTERET_i_appen():
    """En flade ingen kan naa er husets hyppigste fejl. `_runtime_work_surface`
    var korrekt, komplet og usynlig i maanedsvis af praecis den grund."""
    from apps.api.jarvis_api.app import app
    stier = {getattr(r, "path", "") for r in app.routes}
    assert "/composer/suggest" in stier


def test_ruten_svarer_TOMT_frem_for_at_fejle(monkeypatch):
    """Et forslag er en bekvemmelighed. En klient der skulle haandtere
    fejlkoder for at kunne skrive videre, ville holde op med at virke naar
    GPU'en var optaget."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    # Svaret bærer siden 20/9-2026 også `forslag_id` og `kilde_besked_id`
    # (fase 2), men tomme her: der er intet forslag at melde et valg om.
    assert r.suggest(r.Udkast(udkast="kan du lige tjekke")) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_ruten_baerer_forslaget_igennem(monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa", lambda u: " tjekke det")
    assert r.suggest(r.Udkast(udkast="kan du lige"))["forslag"] == " tjekke det"


def test_ruten_taaler_en_tom_krop():
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    assert r.suggest(r.Udkast()) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


# ─────────────────────────────────────────────── valget (fase 2, 20/9-2026)
#
# Bjoern: «vi skal gemme brugerens valg, dvs. om de brugte den suggested (tab)
# i composer eller skrev der egen besked saa naeste forslag bliver mere
# mig/maalrettet». Forslaget skal derfor baere et id ud til klienten, saa
# klienten kan melde tilbage hvad der skete med netop DET forslag.


def test_forslaget_baerer_et_ID_og_beskeden_det_kom_af(monkeypatch):
    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "message-42",
        "content": "Det er rettet og verificeret — testene er groenne igen."}])
    monkeypatch.setattr(cs, "_kald_model", lambda p: "deploy det til ct105")
    d = cs.foreslaa_naeste_detaljer("s1")
    assert d["forslag"] == "deploy det til ct105"
    assert d["forslag_id"].startswith("cs-") and len(d["forslag_id"]) > 8
    assert d["kilde_besked_id"] == "message-42"


def test_to_forslag_faar_FORSKELLIGE_id(monkeypatch):
    """Ellers ville to valg skrive oven i hinanden."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "m1",
        "content": "Det er rettet og verificeret — testene er groenne igen."}])
    monkeypatch.setattr(cs, "_kald_model", lambda p: "deploy det")
    assert cs.foreslaa_naeste_detaljer("s1")["forslag_id"] != \
        cs.foreslaa_naeste_detaljer("s1")["forslag_id"]


def test_INTET_forslag_giver_tomme_id(monkeypatch):
    """Der er ikke noget at melde tilbage om — og en klient der fik et id uden
    et forslag, ville oprette en raekke for noget der aldrig blev vist."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [])
    d = cs.foreslaa_naeste_detaljer("s1")
    assert d == {"forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_den_GAMLE_form_svarer_stadig_med_en_streng(monkeypatch):
    """Mobilen og enhver anden kalder maa ikke braekke af at der kom felter til."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "m1",
        "content": "Det er rettet og verificeret — testene er groenne igen."}])
    monkeypatch.setattr(cs, "_kald_model", lambda p: "deploy det")
    assert cs.foreslaa_naeste("s1") == "deploy det"


def test_ruten_registrerer_VIST_og_derefter_valget(isolated_runtime, monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute
    from core.runtime import db_composer_choice as dc

    rute.choice(rute.Valg(forslag_id="cs-9", session_id="s1",
                          forslag="Ret det og koer testene igen",
                          kilde_besked_id="message-3", valg="vist"))
    assert dc.seneste_valg()[0]["valg"] == "vist"
    rute.choice(rute.Valg(forslag_id="cs-9", valg="accepteret"))
    assert dc.seneste_valg()[0]["valg"] == "accepteret"


def test_ruten_fejler_ALDRIG(isolated_runtime, monkeypatch):
    """Komponisten maa ikke kunne gaa i stykker af en telemetri-skrivning."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute
    from core.runtime import db_composer_choice as dc

    monkeypatch.setattr(dc, "noter_vist",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("basen er nede")))
    assert rute.choice(rute.Valg(forslag_id="cs-1", session_id="s1",
                                 forslag="x", valg="vist")) == {"ok": True}


def test_ruten_svarer_med_id_saa_klienten_kan_melde_tilbage(monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute

    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "m5",
        "content": "Det er rettet og verificeret — testene er groenne igen."}])
    monkeypatch.setattr(cs, "_kald_model", lambda p: "deploy det")
    svar = rute.suggest(rute.Udkast(udkast="", session_id="s1"))
    assert svar["forslag"] == "deploy det"
    assert svar["kilde_besked_id"] == "m5" and svar["forslag_id"]


def test_MOBILENS_form_har_intet_valg_at_registrere(monkeypatch):
    """Fortsaettelses-formen har ingen Tab-tast at trykke paa i et felt man
    skriver i. Tomme id'er, saa der ikke opstaar raekker uden et valg."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute

    monkeypatch.setattr(cs, "_kald_model", lambda p: "tjekke det")
    svar = rute.suggest(rute.Udkast(udkast="kan du lige", session_id="s1"))
    assert svar["forslag"].strip() == "tjekke det"
    assert svar["forslag_id"] == "" and svar["kilde_besked_id"] == ""
