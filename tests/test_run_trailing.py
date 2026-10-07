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
