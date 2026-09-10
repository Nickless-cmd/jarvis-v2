"""Nedkoeling der overlever en genstart, og ét krav ad gangen.

Opgave 3. `prompt_evolution_runtime._last_run_at` er en MODUL-GLOBAL. To ting
foelger af det, og begge bider i dette hus:

  * En genstart glemmer nedkoelingen. Producenten koerer igen med det samme,
    uanset hvor kort tid siden den koerte.
  * `jarvis-api` og `jarvis-runtime` koerer SAMME app, saa de har hver sin
    kopi. Begge kan koere den samme producent i samme minut.

Kravet ligger derfor i databasen, med en lease saa en doed proces ikke laaser
producenten for evigt.

OG EN FEJLET KOERSEL ER IKKE ET NEDKOELINGS-MAERKE. Ellers ville en producent
der fejler hurtigt faa lov at fejle igen og igen, mens en der fejler LANGSOMT
ville blive holdt ude af sin egen fejl.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services.cadence_claims import (
    claim_idempotency_key,
    claim_producer,
    complete_producer,
)


def _nu(**kw):
    return datetime.now(UTC) + timedelta(**kw)


def test_kun_ÉN_kan_holde_kravet_ad_gangen(isolated_runtime):
    a = claim_producer("p", cooldown_minutes=0, lease_seconds=60, now=_nu())
    assert a.claimed is True and a.lease_token

    b = claim_producer("p", cooldown_minutes=0, lease_seconds=60, now=_nu())
    assert b.claimed is False, "to holdere paa samme tid"
    assert "lease" in b.reason


def test_en_udloebet_lease_kan_overtages(isolated_runtime):
    """En doed proces maa ikke laase producenten for evigt."""
    a = claim_producer("p", cooldown_minutes=0, lease_seconds=1, now=_nu())
    assert a.claimed is True
    b = claim_producer("p", cooldown_minutes=0, lease_seconds=60,
                       now=_nu(seconds=90))
    assert b.claimed is True, "en udloebet lease blev aldrig frigivet"
    assert b.lease_token != a.lease_token


def test_nedkoelingen_OVERLEVER_at_hukommelsen_ryddes(isolated_runtime):
    """Kernen. En modul-global glemmer ved genstart; en raekke goer ikke."""
    import importlib

    from core.services import cadence_claims as cc

    a = claim_producer("p", cooldown_minutes=30, lease_seconds=60, now=_nu())
    assert complete_producer("p", a.lease_token, succeeded=True, now=_nu()) is True

    importlib.reload(cc)                      # som en genstart
    b = cc.claim_producer("p", cooldown_minutes=30, lease_seconds=60, now=_nu())
    assert b.claimed is False, "nedkoelingen forsvandt da hukommelsen blev ryddet"
    assert "cooldown" in b.reason


def test_en_FEJLET_koersel_er_ikke_et_nedkoelings_maerke(isolated_runtime):
    """Ellers ville en producent der fejler hurtigt faa lov at fejle igen og
    igen — og en der fejler langsomt blive holdt ude af sin egen fejl."""
    a = claim_producer("p", cooldown_minutes=30, lease_seconds=60, now=_nu())
    assert complete_producer("p", a.lease_token, succeeded=False, now=_nu()) is True

    b = claim_producer("p", cooldown_minutes=30, lease_seconds=60, now=_nu())
    assert b.claimed is True, "en fejlet koersel blev talt som et gennemfoert pas"


def test_kun_indehaveren_kan_afslutte(isolated_runtime):
    a = claim_producer("p", cooldown_minutes=0, lease_seconds=60, now=_nu())
    assert complete_producer("p", "en-anden-poet", succeeded=True, now=_nu()) is False
    assert complete_producer("p", a.lease_token, succeeded=True, now=_nu()) is True


def test_producenter_er_uafhaengige(isolated_runtime):
    a = claim_producer("p1", cooldown_minutes=60, lease_seconds=60, now=_nu())
    complete_producer("p1", a.lease_token, succeeded=True, now=_nu())
    b = claim_producer("p2", cooldown_minutes=60, lease_seconds=60, now=_nu())
    assert b.claimed is True, "en producents nedkoeling ramte en anden"


def test_idempotens_noeglen_gaelder_ÉN_gang(isolated_runtime):
    assert claim_idempotency_key("scope", "n-1", now=_nu()) is True
    assert claim_idempotency_key("scope", "n-1", now=_nu()) is False
    assert claim_idempotency_key("andet-scope", "n-1", now=_nu()) is True


# ── koblingen: er den globale holdt op med at vaere autoriteten? ────────

def test_prompt_evolution_bruger_det_HOLDBARE_krav():
    """Uden denne test kunne krav-systemet findes og aldrig blive kaldt — og
    saa ville nedkoelingen stadig forsvinde ved genstart."""
    import inspect

    from core.services import prompt_evolution_runtime as pe

    kilde = inspect.getsource(pe.run_prompt_evolution_runtime)
    assert "claim_producer(" in kilde, "producenten tager aldrig et holdbart krav"
    assert "complete_producer(" in kilde


def test_alle_veje_ud_giver_kravet_fri():
    """En tidlig retur der beholder leasen ville laase producenten i 15
    minutter ad gangen, hver gang den blokerede."""
    import inspect

    from core.services import prompt_evolution_runtime as pe

    kilde = inspect.getsource(pe.run_prompt_evolution_runtime)
    linjer = [ln.strip() for ln in kilde.splitlines()]
    returns = [i for i, ln in enumerate(linjer) if ln == "return result"]
    assert returns, "fandt ingen retur-punkter — testen maaler intet"
    for i in returns:
        # Vinduet skal vaere stort nok til at se den omsluttende gren. Med 6
        # linjer ramte testen sin egen graense: grenen «vi fik ikke kravet»
        # HAR intet at give fri, men beviset for det stod uden for vinduet.
        forud = " ".join(linjer[max(0, i - 20):i])
        assert ("complete_producer(" in forud) or ("_krav.claimed" in forud), (
            f"retur-punkt uden at give kravet fri: linje {i}")


# ── invariant 8: nedkoelingen gaelder ALLE producenter ──────────────────
#
# Jarvis laeste design-spec'en og fandt at vaernet kun daekkede ÉN producent,
# mens invariant 8 siger: «Producer cooldown survives service restart and is
# shared across processes.» Han havde ret, og det var STOERRE end han sagde:
# `internal_cadence._last_run_at` er en hukommelses-ordbog for ALLE 41
# producenter. Rettelsen hoerer derfor til i SOMMEN, ikke hos hver kalder.

def test_alle_producenter_gaar_gennem_den_holdbare_tilstand():
    """Uden dette var vaernet koblet paa ét sted og blindt for de andre 40."""
    import inspect

    from core.services import internal_cadence as ic

    laes = inspect.getsource(ic._evaluate_producer)
    # Kaldet sker gennem et alias (`_holdbar`), saa der maa soeges paa
    # importen OG brugen. Foerste udgave af denne test ledte efter
    # «last_success_at(» og fandt intet — testen var forkert, ikke koden.
    assert "last_success_at as _holdbar" in laes, (
        "nedkoelingen laeses stadig KUN fra hukommelsen")
    assert "_holdbar(spec.name)" in laes, (
        "den holdbare tilstand importeres, men bruges ikke")
    skriv = inspect.getsource(ic.run_cadence_tick)
    assert "note_producer_ran(" in skriv, (
        "et gennemfoert pas bogfoeres ikke holdbart — nedkoelingen "
        "forsvinder ved genstart")


def test_den_holdbare_tilstand_vinder_over_cachen(isolated_runtime):
    from datetime import UTC, datetime

    from core.services.cadence_claims import last_success_at, note_producer_ran

    assert last_success_at("p-ny") == "", "ukendt producent gav ikke tom streng"
    nu = datetime.now(UTC)
    assert note_producer_ran("p-ny", now=nu) is True
    assert last_success_at("p-ny").startswith(nu.isoformat()[:16])


def test_en_ulaeselig_tilstand_STOPPER_ikke_kadencen(isolated_runtime, monkeypatch):
    """Modsat `claim_producer`, hvor tvivl betyder «koer ikke». Her ville det
    modsatte vaere galt: en producent der ikke koerer fordi databasen var
    utilgaengelig, ville stoppe det indre liv i stilhed."""
    import core.services.cadence_claims as cc

    monkeypatch.setattr(cc, "connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
    assert cc.last_success_at("p") == ""
