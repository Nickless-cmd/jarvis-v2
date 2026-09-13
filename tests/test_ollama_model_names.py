"""Et bart ollama-modelnavn gav 404 — og svaret lød som manglende rettigheder.

MAALT 13/9-2026 kl. 10:25:18, autonomt wakeup-run:

    RuntimeError: Ollama HTTP 404: {"error":"model 'glm-5.2' not found"}

Ollama serverer den som `glm-5.2:cloud`. Uden suffikset findes den ikke.

Det alvorlige er hvad brugeren SAA. Ikke en fejl, men et svar hvor Jarvis
skrev at han «ikke har adgang til at udføre operativsystem- eller
runtime-kommandoer», og tilbød at **simulere** rapporten. En manglende
tag-endelse blev altsaa til en paastand om hans egne rettigheder.

Rettelsen fandtes i forvejen — i `chat_stream_v2.py`, altsaa i ÉN rute, lavet
23/7-2026. Autonome koersler gaar ikke derigennem. Mekanismen fandtes; kalderen
manglede.
"""
import core.services.ollama_model_names as omn


def _tags(monkeypatch, *navne):
    monkeypatch.setattr(omn, "served_tags", lambda: set(navne))


def test_bart_navn_opløses_til_cloud_tagget(monkeypatch):
    """Selve tilfaeldet fra produktionen."""
    _tags(monkeypatch, "glm-5.2:cloud", "deepseek-v4-flash:cloud")
    assert omn.resolve_model_name("glm-5.2") == "glm-5.2:cloud"


def test_et_navn_der_ALLEREDE_er_rigtigt_roeres_ikke(monkeypatch):
    _tags(monkeypatch, "glm-5.2:cloud")
    assert omn.resolve_model_name("glm-5.2:cloud") == "glm-5.2:cloud"


def test_et_navn_ollama_FAKTISK_serverer_omskrives_ikke(monkeypatch):
    """Serverer ollama baade `glm-5.2` OG `glm-5.2:cloud`, skal det bare navn
    bruges som givet. Vi retter en 404 — vi omskriver ikke et valg der virker.

    Mutations-proeven fandt hullet: uden denne test kunne «hvis navnet findes,
    lad det vaere» fjernes uden at én test blev roed, fordi alle de andre
    tilfaelde giver samme svar med og uden den.
    """
    _tags(monkeypatch, "glm-5.2", "glm-5.2:cloud")
    assert omn.resolve_model_name("glm-5.2") == "glm-5.2"


def test_latest_bruges_naar_cloud_ikke_findes(monkeypatch):
    _tags(monkeypatch, "mistral:latest")
    assert omn.resolve_model_name("mistral") == "mistral:latest"


def test_cloud_vinder_over_latest(monkeypatch):
    """Begge findes: cloud er den der bruges i drift."""
    _tags(monkeypatch, "glm-5.2:cloud", "glm-5.2:latest")
    assert omn.resolve_model_name("glm-5.2") == "glm-5.2:cloud"


def test_ukendt_navn_sendes_UAENDRET_videre(monkeypatch):
    """Fail-open: vi gaetter ikke. Ollama skal selv sige at den ikke findes."""
    _tags(monkeypatch, "glm-5.2:cloud")
    assert omn.resolve_model_name("noget-vi-ikke-kender") == "noget-vi-ikke-kender"


def test_ollama_nede_stopper_ikke_kaldet(monkeypatch):
    """Et opslag der fejler maa aldrig kunne stoppe et kald der ellers virker."""
    monkeypatch.setattr(omn, "served_tags", lambda: set())
    assert omn.resolve_model_name("glm-5.2") == "glm-5.2"


def test_tomt_navn_giver_tomt_navn(monkeypatch):
    _tags(monkeypatch, "glm-5.2:cloud")
    assert omn.resolve_model_name("") == ""


def test_OLLAMA_KALDET_selv_oploeser_navnet():
    """Koblingen: rettelsen skal sidde dér hvor navnet BRUGES, ikke hos hver
    kalder der maatte huske det. Ellers gentager vi 23/7-fejlen, hvor kun én
    rute fik den."""
    import inspect

    import core.services.visible_model  # noqa: F401 — bryder cirkulariteten
    import core.services.visible_model_ollama as vmo
    kilde = inspect.getsource(vmo)
    assert kilde.count('"model": _opløs(model)') == 2, \
        "ikke alle payload-steder oploeser navnet"
    assert '"model": model,' not in kilde, "et bart navn slipper stadig igennem"
