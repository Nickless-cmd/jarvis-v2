"""Force-handlerne — værktøjer der kører EFTER et menneske har godkendt.

Udskilt fra `simple_tools.py` 7/9-2026 (Boy Scout: 2.267 linjer).
"""

from __future__ import annotations

import ast
import builtins
import pathlib

import pytest

MODUL = pathlib.Path(__file__).resolve().parents[1] / "core" / "tools" / "force_handlers.py"


def test_alle_navne_i_modulet_er_BUNDET():
    """Statisk: kalder filen noget den ikke har importeret?

    Udskillelsen glemte `_guard_py_escapes`, og `write_file`/`edit_file` faldt
    med «name is not defined». Det er ANDEN gang det navn slipper igennem —
    simple_tools.py:596 bærer allerede en advarsel om første gang, hvor det
    brækkede .py-skrivning i syv uger.

    En flytning af kode ser rigtig ud lige indtil et navn står tilbage i den
    gamle fil. Derfor et statisk tjek frem for tillid til at man kiggede godt
    efter.
    """
    træ = ast.parse(MODUL.read_text(encoding="utf-8"))
    bundet = set(dir(builtins))
    for n in ast.walk(træ):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bundet.add(n.name)
            bundet.update(a.arg for a in getattr(n, "args", ast.arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])).args)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            bundet.update((a.asname or a.name.split(".")[0]) for a in n.names)
        elif isinstance(n, ast.Assign):
            bundet.update(t.id for t in n.targets if isinstance(t, ast.Name))
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            bundet.add(n.target.id)

    kaldt = {c.func.id for c in ast.walk(træ)
             if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    mangler = sorted(kaldt - bundet)
    assert not mangler, "kalder navne der ikke er bundet i filen: %s" % mangler


# `write_file` og `edit_file` er PARALLELLE implementeringer: de skriver
# direkte og moeder derfor aldrig en approval-gren at springe over. Resten
# delegerer til deres `_exec_*` med `_runtime_trust_all`. Forskellen er ikke
# tilfaeldig — `_force_bash` var engang ogsaa parallel, og docstringen dér
# beskriver hvorfor det blev lagt sammen (to forskellige bash'er alt efter
# hvem der kaldte). De to sidste staar tilbage.
_DIREKTE = {"_force_write_file", "_force_edit_file"}


def test_de_delegerende_force_handlere_springer_godkendelsen_over():
    """Det ENE de skal goere: saette `_runtime_trust_all` paa vej videre.

    Uden det rammer et godkendt kald sin egen approval-gren igen og svarer
    approval_needed paa ny — i ring. Se test_approval_har_force_handler.py for
    den anden halvdel: at hvert godkendelses-vaerktoej HAR en handler.
    """
    import inspect
    from core.tools import force_handlers as F

    uden = []
    for navn, fn in vars(F).items():
        if not navn.startswith("_force_") or not callable(fn) or navn in _DIREKTE:
            continue
        try:
            kilde = inspect.getsource(fn)
        except OSError:  # pragma: no cover
            continue
        if "_runtime_trust_all" not in kilde:
            uden.append(navn)
    assert not uden, "force-handlere der ikke springer godkendelsen over: %s" % uden


def test_de_direkte_to_moeder_aldrig_en_godkendelse():
    """De skriver selv — men sikkerheds-gaten skal stadig staa.

    En force-handler springer GODKENDELSEN over, ikke sikkerheden. Fjernes
    blocked-tjekket, kan en godkendt skrivning ramme en spaerret sti.
    """
    import inspect
    from core.tools import force_handlers as F

    for navn in _DIREKTE:
        kilde = inspect.getsource(getattr(F, navn))
        assert "blocked_only=True" in kilde, "%s har mistet sin blocked-gate" % navn


def test_registret_daekker_dem_der_findes():
    from core.tools.force_handlers import _FORCE_HANDLERS

    assert len(_FORCE_HANDLERS) >= 16
    for navn, fn in _FORCE_HANDLERS.items():
        assert callable(fn), "%s peger ikke på noget kaldbart" % navn


def test_simple_tools_re_eksporterer_dem_uaendret():
    """Bagudkompatibilitet: udskillelsen må ikke knække eksisterende imports."""
    from core.tools import force_handlers as F
    from core.tools import simple_tools as ST

    assert ST._FORCE_HANDLERS is F._FORCE_HANDLERS
    assert ST._force_bash is F._force_bash


def test_test_patch_soemmet_overlevede_flytningen(monkeypatch):
    """`monkeypatch.setattr(simple_tools, "_exec_bash", ...)` skal stadig virke.

    Importerede force_handlers `_exec_bash` direkte fra simple_tools_web, ville
    sømmet flytte sig, og to eksisterende tests faldt uden at nogen havde
    ændret adfærd. Facaden slår op via simple_tools netop derfor.
    """
    from core.tools import force_handlers as F
    from core.tools import simple_tools as ST

    set_args: dict = {}
    monkeypatch.setattr(ST, "_exec_bash", lambda a: set_args.update(a) or {"status": "ok"})
    F._force_bash({"command": "echo hej"})
    assert set_args.get("command") == "echo hej"
    assert set_args.get("_runtime_trust_all") is True


@pytest.mark.parametrize("navn", ["bash", "write_file", "edit_file", "gmail_send"])
def test_de_vigtigste_er_med(navn):
    from core.tools.force_handlers import _FORCE_HANDLERS

    assert navn in _FORCE_HANDLERS
