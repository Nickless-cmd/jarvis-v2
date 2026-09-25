"""Der må kun være ÉN vej til godkendelses-filen — og den går gennem låsen.

25/9-2026, Jarvis' fund ved gennemlæsning af min egen rettelse fra aftenen før:

`_persist_pending_approvals()` stod stadig tilbage i sin gamle form — en ulåst
skrivning af hele processens dict — med to kaldesteder der begge lå **lige
efter** `saet_godkendelse`, som allerede havde gemt kortet under lås.

Kaldet var redundant. Værre: det genindførte præcis den fejlklasse låsen
fjernede. Skriver den anden proces et kort i vinduet mellem låse-udslippet og
persist-skrivningen, bliver det overskrevet af vores kopi og tabt. Vinduet er
mikroskopisk, men det sad på de to steder hvor et kort BLIVER lavet.

Det er tredje gang på to dage samme form dukker op: en spærre der er lavet
rigtigt, men ikke gjort til den eneste vej. `_HOT_RESOLVE_CAP_S` cappede tre af
fire resolves. `embed_ollama_base_url` blev honoreret af ét modul ud af fire.
`_record_heartbeat_outcome` skrev uret, men ikke fra den sti planlæggeren
bruger.

Derfor denne vagt: en AST-kontrol af hvem der overhovedet må røre filen.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
KILDE = ROD / "core" / "services" / "visible_runs.py"

#: De eneste funktioner der må skrive godkendelses-filen. Begge tager låsen.
TILLADTE_SKRIVERE = {"saet_godkendelse", "fjern_godkendelse"}


def _funktion_omkring(træ: ast.Module, linje: int) -> str:
    """Navnet på den nærmeste omsluttende funktion, eller '<modul>'."""
    bedst, bedst_linje = "<modul>", -1
    for n in ast.walk(træ):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.lineno <= linje <= (n.end_lineno or n.lineno) and n.lineno > bedst_linje:
                bedst, bedst_linje = n.name, n.lineno
    return bedst


def test_kun_de_laaste_accessorer_skriver_filen() -> None:
    """Hvert kald til `_save_approvals_state` skal bo i en låst accessor.

    Grep duer ikke her — navnet står også i importen og i kommentarer. AST'en
    fortæller hvor kaldet FAKTISK sker.
    """
    træ = ast.parse(KILDE.read_text(encoding="utf-8"))
    skrivere: dict[str, list[int]] = {}
    for n in ast.walk(træ):
        if not isinstance(n, ast.Call):
            continue
        navn = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
        if navn != "_save_approvals_state":
            continue
        skrivere.setdefault(_funktion_omkring(træ, n.lineno), []).append(n.lineno)

    ulovlige = {f: l for f, l in skrivere.items() if f not in TILLADTE_SKRIVERE}
    assert not ulovlige, (
        "godkendelses-filen skrives uden om låsen — en skrivning af hele "
        f"processens kopi kan slette den anden proces' kort: {ulovlige}"
    )
    assert set(skrivere) == TILLADTE_SKRIVERE, (
        f"forventede præcis {TILLADTE_SKRIVERE} som skrivere, fik {set(skrivere)}"
    )


def test_begge_skrivere_tager_laasen() -> None:
    """En accessor der glemmer `med_laas` er værre end ingen accessor.

    Så ser koden rigtig ud på kaldestedet, mens garantien er væk.
    """
    træ = ast.parse(KILDE.read_text(encoding="utf-8"))
    for n in ast.walk(træ):
        if not isinstance(n, ast.FunctionDef) or n.name not in TILLADTE_SKRIVERE:
            continue
        laase = [
            w for w in ast.walk(n)
            if isinstance(w, ast.With)
            and any(getattr(getattr(i.context_expr, "func", None), "attr", None) == "med_laas"
                    for i in w.items)
        ]
        assert laase, f"{n.name} skriver uden `med_laas` — låsen er ikke taget"


def test_den_gamle_ulaaste_vej_er_vaek() -> None:
    """`_persist_pending_approvals` må ikke findes igen.

    En NameError er den rigtige reaktion hvis nogen kalder den gamle vej — den
    fejler højlydt i stedet for at tabe et kort i stilhed.
    """
    import core.services.visible_runs as vr

    assert not hasattr(vr, "_persist_pending_approvals"), (
        "den ulåste skrivning er tilbage — den taber kort fra den anden proces"
    )


def test_laesningen_gaar_ogsaa_kun_én_vej() -> None:
    """Og `godkendelser_nu` skal være den eneste der læser filen.

    Ellers kan en læser komme til at bruge processens forældede kopi igen —
    hele den oprindelige fejl.
    """
    træ = ast.parse(KILDE.read_text(encoding="utf-8"))
    læsere: dict[str, list[int]] = {}
    for n in ast.walk(træ):
        if not isinstance(n, ast.Call):
            continue
        navn = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
        if navn != "_load_approvals_state":
            continue
        læsere.setdefault(_funktion_omkring(træ, n.lineno), []).append(n.lineno)

    # `<modul>` er opstarts-indlæsningen på modul-niveau; den er med vilje.
    tilladt = {"godkendelser_nu", "saet_godkendelse", "fjern_godkendelse", "<modul>"}
    ulovlige = {f: l for f, l in læsere.items() if f not in tilladt}
    assert not ulovlige, f"filen læses uden om accessorerne: {ulovlige}"
