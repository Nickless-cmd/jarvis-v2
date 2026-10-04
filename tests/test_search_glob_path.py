"""En sti i `glob` gav stille nul (7/9-2026).

En explore-agent skrev det oplagte — `glob='core/runtime/provider_router.py'` —
og fik «[no matches]» på et mønster der findes 28 gange i filen. `--include=`
(og rg's `-g`) matcher på FILNAVN-mønster, ikke på sti. Ikke en fejl, ikke et
tomt resultat man kan lære af: bare tavshed.
"""
import pathlib
from core.tools.simple_tools_web import _exec_search

FIL = "core/runtime/provider_router.py"



def _linje_for(fil: str, navn: str) -> int:
    """Hvilken linje står `navn` på — udledt med AST, uafhængigt af koden under test.

    Derfor AST og ikke en egen linje-scan: `facit_for` scanner netop linje for
    linje med en regex, så en `enumerate`-løkke her ville være SAMME mekanisme,
    og testen kunne ikke fejle hvis regexen var forkert. `ast` kommer frem ad
    en anden vej og er derfor et ægte uafhængigt svar.
    """
    import ast
    træ = ast.parse(pathlib.Path(fil).read_text(encoding="utf-8"))
    for n in træ.body:                      # modul-niveau, som `^def ` matcher
        if isinstance(n, ast.FunctionDef) and n.name == navn:
            return n.lineno
    raise AssertionError(f"{navn} findes ikke paa modul-niveau i {fil}")


def test_en_sti_i_glob_finder_noget():
    r = _exec_search({"pattern": "^def ", "glob": FIL})
    assert int(r.get("match_count") or 0) > 10, "en sti i glob gav igen nul"


def test_traeffene_baerer_STIEN_ikke_kun_linjenummeret():
    """Uden filnavnet står agenten med «18:def …» og ved ikke hvilken fil.
    Stien er halvdelen af et brugbart fund."""
    r = _exec_search({"pattern": "^def load_provider_router_registry", "glob": FIL})
    linje = (r.get("text") or "").splitlines()[0]
    assert FIL in linje, f"stien mangler i træffet: {linje!r}"


def test_linjenummeret_er_det_RIGTIGE():
    """Agentens svar skal kunne citeres — altså stemme med KILDEN.

    RETTET 4/10-2026 (Opus): docstringen sagde «18 er sandheden i hovedtræet»,
    og det var sandt indtil nogen lagde en linje ind over funktionen. Et
    linjenummer er ikke en sandhed, det er en position — og en test der pinner
    positionen måler ikke om værktøjet citerer rigtigt.
    
    Raekkevidden, saa vagten ikke laeses for bredt: nummeret kommer fra
    ripgrep, en ekstern proces jeg ikke kan mutere.
    """
    sand_linje = _linje_for(FIL, "load_provider_router_registry")
    r = _exec_search({"pattern": "^def load_provider_router_registry", "glob": FIL})
    linje = (r.get("text") or "").splitlines()[0]
    assert f"{FIL}:{sand_linje}:" in linje, (
        f"kilden siger linje {sand_linje}, vaerktoejet siger: {linje!r}")


def test_en_mappe_i_glob_soeger_i_mappen():
    r = _exec_search({"pattern": "^def ", "glob": "core/runtime"})
    assert int(r.get("match_count") or 0) > 0
    assert "core/runtime/" in (r.get("text") or "")


def test_et_almindeligt_glob_moenster_virker_stadig():
    """`*.py` må ikke fanges af sti-logikken."""
    r = _exec_search({"pattern": "^def load_provider_router_registry", "glob": "*.py"})
    assert int(r.get("match_count") or 0) >= 1


def test_soegning_uden_glob_er_uroert():
    r = _exec_search({"pattern": "^def configure_provider_router_entry"})
    assert int(r.get("match_count") or 0) >= 1
    assert FIL in (r.get("text") or "")


def test_en_sti_der_ikke_findes_giver_ikke_et_falsk_traef():
    r = _exec_search({"pattern": "def ", "glob": "core/findes/slet/ikke.py"})
    assert int(r.get("match_count") or 0) == 0
