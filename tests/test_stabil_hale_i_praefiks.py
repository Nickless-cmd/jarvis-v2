"""De fire uændrede hale-sektioner hører i det cachede præfiks (4/10-2026).

Målt over 99 ture: fire sektioner var BYTE-IDENTISKE hver gang. De lå efter
cache-sentinel'en og var derfor cache-miss i hver tur — og en miss-token
koster 50× en hit-token. Pris: 2,01 M miss-tokens i døgnet = $110/år for
indhold der aldrig ændrer sig.
"""
from __future__ import annotations

import ast
import pathlib

KILDE = pathlib.Path("core/services/prompt_contract.py")


def _markoerer() -> tuple[str, ...]:
    """Hent listen fra kilden, så testen ikke har sin egen kopi — to lister
    ville drive fra hinanden, og det er hele aftenens tema."""
    traeet = ast.parse(KILDE.read_text())
    for node in ast.walk(traeet):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "_STABILE_I_HALEN" for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError("fandt ikke _STABILE_I_HALEN")


def test_de_fire_markoerer_findes():
    m = _markoerer()
    assert len(m) == 4, f"forventede fire stabile sektioner, fandt {len(m)}"
    assert any("Hvad jeg ved nu" in x for x in m)
    assert any("chronicle-entries" in x for x in m)
    assert any("FORBUNDNE APPS" in x for x in m)
    assert any("WORKFLOW" in x for x in m)


def test_hver_markoer_matcher_en_RIGTIG_sektion():
    """Vagten mod tavs tilbagevenden: ændrer nogen ordlyden i en af de fire,
    holder markøren op med at matche, sektionen glider tilbage i halen — og
    ingen opdager det, for prompten ser rigtig ud. Markørerne måles derfor mod
    de kilder der FAKTISK skriver teksten."""
    kilder = {
        "Hvad jeg ved nu": "core/services/prompt_sections/jarvis_brain.py",
        "chronicle-entries": "core/services/chronicle_engine.py",
        "FORBUNDNE APPS": "core/services/prompt_contract.py",
        "WORKFLOW": "core/services/prompt_contract.py",
    }
    for markoer in _markoerer():
        sti = next((v for k, v in kilder.items() if k in markoer), None)
        assert sti, f"ingen kendt kilde for markoeren {markoer!r}"
        tekst = pathlib.Path(sti).read_text()
        # Markoeren skal staa ORDRET i den fil der bygger sektionen.
        assert markoer in tekst, (
            f"markoeren {markoer!r} findes ikke i {sti} — sektionen er "
            "omdoebt og glider tilbage i den dyre hale")


def test_de_stabile_laegges_FOER_sentinel():
    """Efter sentinel'en er alt cache-miss. Ligger de efter, er flytningen
    kosmetisk."""
    kilde = KILDE.read_text()
    i_stabile = kilde.index("parts.extend(_stabile)")
    i_sentinel = kilde.index("parts.append(DYNAMIC_TAIL_SENTINEL)")
    assert i_stabile < i_sentinel, "de stabile lander EFTER sentinel'en"


def test_raekkefoelgen_er_FAST_ikke_bygge_raekkefoelge():
    """Et præfiks skal være byte-identisk mellem ture. Byggerækkefølgen
    afhænger af hvilke futures der blev færdige først, så den må ikke afgøre
    hvor sektionerne står."""
    # Maalt paa REKKEFOELGEN af de to udtryk, ikke paa afstanden mellem dem:
    # foerste udgave kiggede 600 tegn tilbage, og en tilfoejet vagt imellem
    # skubbede `sort` ud af vinduet. En test der maaler afstand maaler
    # formatering, ikke adfaerd.
    kilde = KILDE.read_text()
    i_sort = kilde.index("_stabile.sort(")
    i_brug = kilde.index("parts.extend(_stabile)")
    assert i_sort < i_brug, "raekkefoelgen laases ikke FOER brug"


def test_sentinel_UDELADES_naar_der_intet_er_tilbage():
    """En sentinel uden hale ville lægge en cache-grænse midt i et præfiks der
    ikke har noget efter sig — altså skære cachen over uden grund."""
    kilde = KILDE.read_text()
    i = kilde.index("parts.extend(_stabile)")
    efter = kilde[i:i + 300]
    assert "if _resten:" in efter, "sentinel skrives ubetinget"


def test_warmerens_praefiks_roeres_IKKE():
    """`build_visible_stable_prefix` bygger præfikset selvstændigt og slutter
    efter identitets-filerne. Filen advarer TO gange om at de to skal være
    byte-identiske. Derfor lægges de stabile sidst — så warmerens præfiks
    stadig er et gyldigt præfiks af det levende, bare kortere."""
    traeet = ast.parse(KILDE.read_text())
    for node in ast.walk(traeet):
        if isinstance(node, ast.FunctionDef) and node.name == "build_visible_stable_prefix":
            krop = ast.unparse(node)
            for markoer in _markoerer():
                assert markoer not in krop, (
                    f"{markoer!r} er lagt ind i warmeren — saa skal den staa "
                    "praecis samme sted i begge, og det er en faelde")
            return
    raise AssertionError("fandt ikke build_visible_stable_prefix")
