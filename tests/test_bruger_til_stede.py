"""Hvem startede turen — ankeret under veto-gaten.

## Baggrund

`41d8e076c` rettede en ægte kategorifejl: 244 blokerede rækker i `veto_events`,
hvoraf **105** havde en SYSTEM-prompt som «brugerens besked» — 100 drømme («Du
er i en drømmetilstand…») og 5 self-wakeups («Du bad dig selv: …»). De blev
fodret ind i en detektor bygget til at læse BRUGERENS frustration, så Jarvis'
egne natlige `write_file`/`db_query`-kald kunne blive vetoet på hans egen
nats-prompt. De øvrige 139 er ægte brugerbeskeder — gaten laver rigtigt arbejde.

## Hvad denne fil retter

Commit-beskeden siger at ankeret er `run.origin`. Koden brugte
`not run.autonomous`, og `VisibleRun` havde **intet** `origin`-felt — værdien
blev beregnet af `normalize_origin` og brugt til at route sessionen, men landede
aldrig på kørslen.

`autonomous` virker i dag, men kun ved et sammentræf: enhver system-startet tur
går gennem `start_autonomous_run`. Den dag én ikke gør, vender fejlen tilbage.
"""
from __future__ import annotations

from types import SimpleNamespace as Koersel

import pytest

from core.services.visible_tool_exec import _bruger_til_stede


def test_en_brugertur_har_en_bruger():
    assert _bruger_til_stede(Koersel(origin="", autonomous=False)) is True


@pytest.mark.parametrize("origin", [
    "dream", "council", "work", "outreach", "recurring",
    "heartbeat", "scheduled", "wakeup", "autonomous",
])
def test_enhver_KENDT_system_oprindelse_har_ingen_bruger(origin):
    """Vokabularet er `autonomous_sessions.ORIGINS` — ikke en liste opfundet
    her. To lister ville drive fra hinanden."""
    assert _bruger_til_stede(Koersel(origin=origin, autonomous=True)) is False


def test_origin_vejer_TUNGERE_end_flaget():
    """Det tilfaelde den gamle kode tog fejl af.

    En droem der (af en eller anden grund) ikke er markeret autonom, ville med
    `not run.autonomous` blive laest som en brugertur — og saa er vi tilbage
    ved «Du er i en droemmetilstand…» som bruger-pres.
    """
    assert _bruger_til_stede(Koersel(origin="dream", autonomous=False)) is False


def test_flaget_er_stadig_faldback():
    """Koersler uden en oprindelse skal opfoere sig praecis som foer — en
    udvidelse maa ikke aendre adfaerd for det den ikke handler om."""
    assert _bruger_til_stede(Koersel(origin="", autonomous=True)) is False
    assert _bruger_til_stede(Koersel(origin="", autonomous=False)) is True


def test_en_UKENDT_oprindelse_holder_gaten_TAENDT():
    """Fail-retningen. En oprindelse vi ikke kender maa ikke kunne slukke en
    sikkerheds-gate i stilhed — saa hellere fyre paa en tur uden bruger end at
    tie paa en tur MED."""
    assert _bruger_til_stede(Koersel(origin="noget-nyt", autonomous=False)) is True


def test_den_taaler_rod():
    assert _bruger_til_stede(Koersel(origin="  DREAM  ", autonomous=False)) is False
    assert _bruger_til_stede(Koersel(origin=None, autonomous=False)) is True


def test_den_taaler_en_koersel_uden_felterne():
    """Kaldes fra exec-stien. En manglende attribut maa ikke vaelte et
    vaerktoejskald."""
    class Tom:
        pass
    assert _bruger_til_stede(Tom()) is True


# ------------------------------------------------- feltet skal BAERES med

def test_VisibleRun_har_et_origin_felt():
    import dataclasses

    from core.services.visible_runs import VisibleRun
    felter = {f.name for f in dataclasses.fields(VisibleRun)}
    assert "origin" in felter, \
        "vaerdien beregnes og tabes igen — ankeret kan ikke laeses"


def test_den_autonome_koersel_SAETTER_sin_oprindelse():
    """Kilde-vagt paa konstruktionsstedet. Alle tests her bygger deres egne
    koersels-objekter og roerer aldrig det rigtige sted — feltet kan altsaa
    findes uden nogensinde at blive fyldt. (Samme hul som `user_id` i morges.)
    """
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path("core/services/visible_runs.py").read_text())
    for n in ast.walk(træ):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "VisibleRun":
            nøgler = {k.arg: k.value for k in n.keywords}
            aut = nøgler.get("autonomous")
            if isinstance(aut, ast.Constant) and aut.value is True:
                assert "origin" in nøgler, \
                    f"den autonome koersel paa linje {n.lineno} baerer ingen oprindelse"
                return
    pytest.fail("fandt ingen autonom VisibleRun-konstruktion")


def test_exec_stien_bruger_ankeret():
    """En hjaelper ingen kalder aendrer ingenting."""
    import ast
    import pathlib
    kilde = pathlib.Path("core/services/visible_tool_exec.py").read_text()
    assert "user_present=_bruger_til_stede(run)" in kilde, \
        "exec-stien bruger stadig stedfortraederen"
    assert "user_present=not run.autonomous" not in kilde
