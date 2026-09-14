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
    assert r.suggest(r.Udkast(udkast="kan du lige tjekke")) == {"forslag": ""}


def test_ruten_baerer_forslaget_igennem(monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa", lambda u: " tjekke det")
    assert r.suggest(r.Udkast(udkast="kan du lige")) == {"forslag": " tjekke det"}


def test_ruten_taaler_en_tom_krop():
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    assert r.suggest(r.Udkast()) == {"forslag": ""}
