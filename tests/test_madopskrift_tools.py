"""Tests for madopskrift-værktøjet — dansk opslagsværk oven på engelske kilder.

Baggrund (25/10-2026, Bjørn): Michelle ville gerne kunne slå opskrifter op.
Der findes ingen dansk opskrift-API — Arla og Valdemarsro har ingen åbne
endpoints — så værktøjet oversætter både søgeord og svar oven på TheMealDB
og MyPlate.food, som begge er nøglefri.

Det centrale krav, som disse tests værner om: **et tomt resultat på et dansk
ord der burde matche er en FEJL, ikke et gyldigt «ingen opskrifter fundet».**
Målt 25/10-2026: `search.php?s=kartoffel` gav `{"meals":null}` — uden
oversættelseslaget ville det se ud som om kartofler ikke findes.

Testene er bevidst offline: netværkskald mockes, så en grøn test betyder
noget om LOGIKKEN og ikke om netværkets humør den dag CI kører.
"""

from __future__ import annotations

import pytest

from core.tools import madopskrift_tools as M


# ── Oversættelseslaget: søgeord ────────────────────────────────────────────


@pytest.mark.parametrize(
    "dansk,forventet",
    [
        ("kartoffel", "potato"),
        ("kylling", "chicken"),
        ("suppe", "soup"),
        ("pasta", "pasta"),
        ("fisk", "fish"),
    ],
)
def test_de_fem_kraevede_danske_ord_oversaettes(dansk: str, forventet: str) -> None:
    """De fem ord Bjørn krævede testet — de skal ramme den engelske term."""
    term, kilde = M.oversaet_ord_til_engelsk(dansk)
    assert term == forventet, f"«{dansk}» blev «{term}», ikke «{forventet}»"
    assert kilde, "kilden skal være angivet, så et gæt kan skelnes fra et opslag"


def test_sammensat_ord_deles_og_oversaettes() -> None:
    """«blomkålssuppe» findes ikke i ordbogen — den skal deles i to led."""
    term, kilde = M.oversaet_ord_til_engelsk("blomkålssuppe")
    assert "cauliflower" in term or "soup" in term, f"fik «{term}»"
    assert kilde == "sammensat", f"kilden var «{kilde}», ikke «sammensat»"


def test_ukendt_ord_giver_ikke_tom_haand(monkeypatch) -> None:
    """Et ord vi ikke kender skal stadig give en brugbar term — ikke kaste.

    Ukendte ord går til cheap-lane, som mockes her: testen skal måle
    LOGIKKEN, ikke om LLM'en svarer den dag CI kører.
    """
    monkeypatch.setattr(M, "_cheap_lane", lambda prompt: "tzatziki")
    term, kilde = M.oversaet_ord_til_engelsk("tzatziki")
    assert term == "tzatziki", f"fik «{term}»"
    assert kilde == "model", "et ord uden for ordbogen skal markeres som gæt"


def test_uoversaetteligt_ord_kaster(monkeypatch) -> None:
    """Kan selv ikke modellen oversætte, må det ikke blive et tomt søg."""
    monkeypatch.setattr(M, "_cheap_lane", lambda prompt: "")
    with pytest.raises(ValueError):
        M.oversaet_ord_til_engelsk("qqqzzz")


# ── Kravet: et tomt svar må ikke være et tavst nej ─────────────────────────


def test_sikkert_ord_med_nul_resultater_proever_bredere_foer_den_giver_op(
    monkeypatch,
) -> None:
    """KERNEN I HELE VÆRKTØJET.

    Målt 25/10-2026: «blomkålssuppe» blev korrekt oversat til «cauliflower
    soup», men TheMealDB har ingen ret med netop det navn — mens den har
    masser med «cauliflower». Uden et bredere forsøg ville Michelle få
    «ingen opskrifter» på et ord der ER dækket.
    """
    kaldt: list[str] = []

    def fake_soeg(term, *, limit=8):
        kaldt.append(term)
        return [{"navn": "Cauliflower Cheese", "id": "themealdb:52812"}] if term == "cauliflower" else []

    monkeypatch.setattr(M, "_themealdb_soeg", fake_soeg)
    monkeypatch.setattr(M, "_myplate_soeg", lambda *a, **k: [])

    r = M._soeg({"handling": "soeg", "soegning": "blomkålssuppe"})

    assert r["status"] == "ok"
    assert r["antal"] == 1, "det bredere søg skulle have fundet noget"
    assert "cauliflower" in kaldt, f"det brede led blev aldrig prøvet — kaldte {kaldt}"


def test_gaet_der_giver_nul_er_en_fejl(monkeypatch) -> None:
    """Er oversættelsen et gæt og giver den nul, er det en fejl — ikke et svar."""
    monkeypatch.setattr(M, "oversaet_ord_til_engelsk", lambda o: ("xyzzy", "model"))
    monkeypatch.setattr(M, "_themealdb_soeg", lambda *a, **k: [])
    monkeypatch.setattr(M, "_myplate_soeg", lambda *a, **k: [])

    r = M._soeg({"handling": "soeg", "soegning": "ukendtord"})

    assert r["status"] == "error", (
        "et gæt der giver nul skal være en fejl — "
        f"fik status={r.get('status')!r}"
    )
    assert r.get("engelsk_term") == "xyzzy", "den oversatte term skal med i fejlen"


def test_sikkert_ord_uden_daekning_siger_det_hoejt(monkeypatch) -> None:
    """Sidste udvej: sikker oversættelse, intet bredere hit — så SIG det.

    Svaret må ikke være en tom liste der ligner et svar: det skal bære den
    oversatte term og en note, så man kan se HVOR det stoppede.
    """
    monkeypatch.setattr(M, "_themealdb_soeg", lambda *a, **k: [])
    monkeypatch.setattr(M, "_myplate_soeg", lambda *a, **k: [])

    r = M._soeg({"handling": "soeg", "soegning": "kartoffel"})

    assert r["status"] == "ok"
    assert r["antal"] == 0
    assert r.get("engelsk_term") == "potato", "den oversatte term skal med"
    assert r.get("note"), "tomt svar skal forklares, ikke bare være tomt"


# ── Hent: fuld opskrift på dansk ───────────────────────────────────────────


def test_hent_giver_dansk_navn_og_fremgangsmaade(monkeypatch) -> None:
    """Verifikationskravet: vis en FAKTISK opskrift på dansk — ikke et 200-svar."""
    monkeypatch.setattr(
        M,
        "_themealdb_hent",
        lambda mid: {
            "navn": "Chicken Handi",
            "ingredienser": ["1.2 kg chicken", "5 onions"],
            "fremgangsmaade": "Heat the oil in a large pot.",
            "kilde": "themealdb",
        },
    )
    monkeypatch.setattr(
        M, "oversaet_til_dansk", lambda tekst, kontekst="opskrift": (f"[da] {tekst}", True)
    )

    r = M._hent({"handling": "hent", "id": "themealdb:52795"})

    assert r["status"] == "ok"
    assert r["navn"].startswith("[da]"), "navnet skal være oversat"
    assert r["ingredienser"], "ingredienslisten må ikke være tom"
    assert r["fremgangsmaade"].startswith("[da]"), "fremgangsmåden skal være oversat"


def test_hent_ukendt_id_giver_fejl(monkeypatch) -> None:
    monkeypatch.setattr(M, "_themealdb_hent", lambda mid: None)
    monkeypatch.setattr(M, "_myplate_hent", lambda slug: None)

    r = M._hent({"handling": "hent", "id": "themealdb:00000"})

    assert r["status"] == "error"
    assert "00000" in r["error"], "fejlen skal nævne det id der ikke blev fundet"


# ── Køleskab: ingrediensliste ind, retter ud ───────────────────────────────


def test_koleskab_oversaetter_ingredienser_og_finder_retter(monkeypatch) -> None:
    sette: list[list[str]] = []

    def fake_koleskab(ingredienser, *, limit=8):
        sette.append(list(ingredienser))
        return [{"navn": "Fried Rice", "id": "myplate:fried-rice", "kilde": "myplate"}]

    monkeypatch.setattr(M, "_myplate_koleskab", fake_koleskab)
    monkeypatch.setattr(
        M, "oversaet_til_dansk", lambda tekst, kontekst="opskrift": (tekst, True)
    )

    r = M._koleskab({"handling": "koleskab", "ingredienser": "kylling, ris, løg"})

    assert r["status"] == "ok"
    assert r["antal"] == 1
    assert sette, "kilden skal have fået ingredienserne"
    assert any("chicken" in i for i in sette[0]), (
        f"ingredienserne skulle være oversat til engelsk, fik {sette[0]}"
    )


def test_koleskab_uden_ingredienser_giver_fejl() -> None:
    r = M._koleskab({"handling": "koleskab", "ingredienser": "  ,  , "})
    assert r["status"] == "error"


# ── Registrering: værktøjet skal faktisk kunne kaldes ──────────────────────


def test_vaerktoejet_er_registreret_i_dispatch_og_definitions() -> None:
    """Et værktøj der ikke er registreret findes ikke — uanset hvor godt det er."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    assert "madopskrift" in _TOOL_HANDLERS, "mangler i dispatch-tabellen"

    navne = [d["function"]["name"] for d in TOOL_DEFINITIONS]
    assert "madopskrift" in navne, "mangler i definitions-listen"

    schema = next(d for d in TOOL_DEFINITIONS if d["function"]["name"] == "madopskrift")
    props = schema["function"]["parameters"]["properties"]
    assert set(props) == {"handling", "soegning", "id", "ingredienser"}
    assert props["handling"]["enum"] == ["soeg", "hent", "koleskab"]
