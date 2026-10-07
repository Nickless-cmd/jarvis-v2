"""Halen maa ikke forskyde historikken — hverken naar den kommer eller gaar.

## Hvad der var galt

Beskedlisten bygges som ``base_messages + exchanges + hale``. Fem steder i den
agentiske loekke blev der appendet en user-besked til ``base_messages`` midt i
en tur: styringer, hollow-promise-nudgen, hook-noter, baggrunds-shell-noter.
De landede derfor FORAN hele vaerktoejshistorikken.

To ting gik galt af det, og den anden er den dyre:

1. Historikken blev forskudt én plads, saa praefiks-cachen braekkede dér.
2. ``build_lean_base_messages`` finder den tunge hale ved at lede efter den
   SIDSTE user-besked i ``base_messages``. Kom der en ny bagest, pegede den
   ikke laengere paa halen — saa slankningen fandt intet at skaere og gav den
   FULDE hale tilbage resten af turen.

Maalt paa CT105 28/9-2026, run `bedc3ac7cd8e`:

    runde  1-12   hale  5.859 tegn   hit vokser til 130.176
    runde 13      hale 26.838 tegn   hit 9.472     miss 125.101
    runde 14      hale 26.838 tegn

Ét run, én runde: 120.704 tokens tabt genkendelse.
"""
from __future__ import annotations

import ast
import pathlib

from core.services.run_trailing import RundeHale


def test_vedvarende_beskeder_bliver_i_ALLE_foelgende_runder():
    """En styring brugeren skrev midtvejs gaelder resten af turen. Faldt den
    ud, ville historikken skifte mellem runder — samme braek, modsat vej."""
    h = RundeHale()
    h.tilfoej_vedvarende("stop med at lede i loggen", rolle="user")
    h.ny_runde()
    h.ny_runde()
    assert [m["content"] for m in h.som_liste()] == ["stop med at lede i loggen"]


def test_runde_beskeder_ryddes_ved_ny_runde():
    """Et batch-vink hoerer til den runde det blev lavet til. Blev det
    haengende, ville halen vokse for hver runde."""
    h = RundeHale()
    h.tilfoej_runde("saml dine kald")
    h.ny_runde()
    assert h.som_liste() == []


# ── Den tredje levetid: `naeste` (7/10-2026) ────────────────────────────────
#
# De fem gates i loekken fyrer ved runde-SLUT og skal praege praecis den runde
# der kommer. Foer laa de i halen som «vedvarende»: noten blev tilfoejet én
# gang, men halen sendes hver runde, saa den blev gen-sendt til turen sluttede.
# Maalt paa hollow-promise-noten alene: 426 fyringer over 356 ture og 2.226
# gen-sendinger — 5,4 i snit pr. ramt tur, vaerst 40 i én tur.


def test_naeste_gaelder_KUN_den_naeste_runde():
    """Kernen i rettelsen. Var noten «vedvarende», blev den sendt igen i hver
    runde til turen sluttede."""
    h = RundeHale()
    h.tilfoej_naeste("Du lovede lige at handle")
    h.ny_runde()                                    # noten rykker ind
    assert len(h.som_liste()) == 1
    h.ny_runde()                                    # ... og videre ud
    assert h.som_liste() == [], "noten blev haengende — det er den gamle fejl"


def test_naeste_er_USYNLIG_i_den_runde_der_loeb():
    """Gaten fyrer ved runde-SLUT. Runden der allerede er sendt maa ikke se
    noten — den hoerer til den naeste."""
    h = RundeHale()
    h.ny_runde()                                    # runden aabner
    h.tilfoej_naeste("saml dine kald")
    assert h.som_liste() == [], "noten laekkede ind i den runde der loeb"
    h.ny_runde()
    assert len(h.som_liste()) == 1


def test_naeste_staar_FOER_rundens_egne_vink():
    """Noten er aeldst naar runden aabner — den skal laeses foer vinket."""
    h = RundeHale()
    h.tilfoej_naeste("note fra gaten")
    h.ny_runde()
    h.tilfoej_runde("saml dine kald")
    indhold = [m["content"] for m in h.som_liste()]
    assert len(indhold) == 2
    assert "note fra gaten" in indhold[0]
    assert indhold[1].endswith("saml dine kald")


def test_de_tre_levetider_aeder_ikke_hinanden():
    """Den vedvarende bliver, den naeste gaar videre efter én runde, og
    rundens eget vink ryddes ved runde-graensen."""
    h = RundeHale()
    h.tilfoej_vedvarende("resten af turen")
    h.tilfoej_naeste("kun naeste")
    h.ny_runde()
    h.tilfoej_runde("kun denne")
    assert len(h.som_liste()) == 3
    h.ny_runde()
    rest = h.som_liste()
    assert len(rest) == 1 and "resten af turen" in rest[0]["content"], (
        "den vedvarende skulle overleve; naeste og runde skulle vaere vaek")


def test_et_retry_af_samme_runde_ser_den_samme_note():
    """Pumpen binder halen som default-argument for at et retry af runde K
    sender byte-identisk. Noten maa ikke kunne forsvinde under forsoeget."""
    h = RundeHale()
    h.tilfoej_naeste("note")
    h.ny_runde()
    bundet = h.som_liste()                          # pumpen binder denne
    h.ny_runde()                                    # ... og et runde-skift sker
    assert len(bundet) == 1, "retry'et fik en anden hale end foerste forsoeg"


def test_naeste_er_system_med_runtime_ramme():
    h = RundeHale()
    h.tilfoej_naeste("Du lovede lige at handle")
    h.ny_runde()
    m = h.som_liste()[0]
    assert m["role"] == "system"
    assert "ikke en besked fra brugeren" in m["content"]


def test_en_TOM_naeste_besked_kommer_ikke_med():
    """En tom besked ville aabne en ny runde uden at sige noget."""
    h = RundeHale()
    for tom in ("", None, 0):
        h.tilfoej_naeste(tom)                       # type: ignore[arg-type]
    h.ny_runde()
    assert h.som_liste() == []


# ── Kilde-vagt: gaterne maa ikke falde tilbage til «resten af turen» ────────


def test_gaterne_bruger_naeste_ikke_vedvarende():
    """En tilbagevenden til `tilfoej_vedvarende` i loekken genindfoerer
    gen-sendingen i hver runde. Fejlen er usynlig i drift — noten «er jo med»
    — og den kostede op til 40 gentagelser i én tur."""
    kilde = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")
    assert "_tur_hale.tilfoej_vedvarende(" not in kilde, (
        "en gate i loekken er faldet tilbage til «resten af turen»")
    assert kilde.count("_tur_hale.tilfoej_naeste(") >= 5, (
        "de fem gates (hollow-promise, skill, baggrunds-shell, stop-hook, "
        "stillingtagen) skal alle bruge `naeste`")


def test_vedvarende_staar_FOERST_fordi_de_er_aeldst():
    h = RundeHale()
    h.tilfoej_vedvarende("styring", rolle="user")
    h.tilfoej_runde("vink")
    assert h.som_liste()[0]["content"] == "styring"
    assert h.som_liste()[1]["content"].endswith("\nvink")


def test_en_TOM_besked_kommer_ikke_med():
    """En tom besked ville forskyde historikken uden at sige noget."""
    h = RundeHale()
    for tom in ("", None, 0):
        h.tilfoej_vedvarende(tom)          # type: ignore[arg-type]
        h.tilfoej_runde(tom)               # type: ignore[arg-type]
    assert h.som_liste() == []


def test_som_liste_giver_en_KOPI():
    """Pumpen binder halen som default-argument for at et retry sender
    byte-identisk. Gav vi den interne liste, ville en styring der lander
    imens aendre en runde der allerede er sendt."""
    h = RundeHale()
    h.tilfoej_vedvarende("a", rolle="user")
    foerste = h.som_liste()
    h.tilfoej_vedvarende("b", rolle="user")
    assert [m["content"] for m in foerste] == ["a"]


def test_raekkefoelgen_inden_for_hver_slags_bevares():
    h = RundeHale()
    for t in ("en", "to", "tre"):
        h.tilfoej_vedvarende(t, rolle="user")
    assert [m["content"] for m in h.som_liste()] == ["en", "to", "tre"]


def test_interne_beskeder_er_system_og_aegte_styringer_er_user():
    h = RundeHale()
    h.tilfoej_vedvarende("Du lovede lige at handle")
    h.tilfoej_runde("Skriv nu dit endelige svar")
    h.tilfoej_vedvarende("stop med at lede", rolle="user")
    assert [m["role"] for m in h.som_liste()] == ["system", "user", "system"]
    assert "ikke en besked fra brugeren" in h.som_liste()[0]["content"]
    assert h.som_liste()[1]["content"] == "stop med at lede"


# ── Kilde-vagt ──────────────────────────────────────────────────────────────


def test_INTET_appendes_laengere_til_base_messages():
    """AST, ikke grep: en streng-soegning kan ikke skelne kaldet fra en
    kommentar der naevner det — og filen naevner det flere steder netop fordi
    det var fejlen.

    Det er den vagt der skal fange en tilbagevenden. Hver gang nogen skal
    tilfoeje en besked midt i en tur, er `base_messages.append` det nemme
    greb, og det er praecis det der kostede 120.704 tokens paa én runde.
    """
    traeet = ast.parse(pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8"))
    syndere = [
        n.lineno for n in ast.walk(traeet)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "append"
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "base_messages"
    ]
    assert not syndere, (
        f"base_messages.append paa linje {syndere} — beskeden havner foran hele "
        "vaerktoejshistorikken og braekker baade cachen og den slanke prompt")


def test_halen_bruges_FAKTISK_af_loekken():
    """En hale ingen sender er en klasse, ikke en rettelse."""
    kilde = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")
    assert "_tur_hale = RundeHale()" in kilde
    assert "round_trailing=_tur_hale.som_liste()" in kilde


def test_slankningen_efterlader_et_VARIGT_spor():
    """`note_lean_prompt` gaar til en ring-buffer i hukommelsen. Da
    slankningen holdt op med at virke, fandtes der bagefter intet spor af
    det — aarsagen maatte udledes af hale-laengden i cache-telemetrien."""
    kilde = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")
    assert '"context", "lean_prompt"' in kilde
    assert '"applied": bool(_lean_metrics.get("changed"))' in kilde
