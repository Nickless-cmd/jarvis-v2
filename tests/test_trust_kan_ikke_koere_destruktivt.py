"""Tillid springer GODKENDELSEN over — aldrig det destruktive.

Det er løftet mobilappens tilladelses-vælger giver Bjørn med rene ord:
*«Fuld adgang — han handler uden at spørge. Farlige kommandoer blokeres
stadig.»* Målt 12/9-2026 holder det. Men det holdt på en **negativ** egenskab:
`_runtime_trust_all` springer kun den gule klasse over, fordi betingelsen
tilfældigvis lyder `classification == "approval"` og ikke nævner `destructive`.

En negativ egenskab består lige indtil nogen udvider betingelsen. Skrev man
`if _ec.classification in ("approval", "destructive") and not trust_all`, ville
garantien forsvinde uden at en eneste test blev rød — der fandtes ingen test
der parrede de to begreber.

Web-værktøjet har den stærkere form: et POSITIVT tjek, `er_ejer_godkendt()`,
sat i en ContextVar af `execute_tool_force(..., owner_approved=True)`. Den
ligger bevidst ikke i argumenterne, fordi modellen selv skriver argumenterne og
ellers kunne sende sin egen godkendelse med.

Denne fil holder begge former fast.
"""
from __future__ import annotations

import pytest

from core.tools.simple_tools import classify_command, execute_tool

#: Kommandoer der klassificeres destruktive OG er inerte hvis de faktisk køres.
#:
#: Den anden egenskab er ikke pynt. Første udgave brugte
#: `git push --force origin main` med begrundelsen «det er harmløst, den når
#: aldrig at køre» — og under mutationsprøven KØRTE den. Den var en no-op
#: udelukkende fordi HEAD tilfældigvis var lig `origin/main` i det sekund.
#: Havde der ligget én ucommittet commit, havde en test omskrevet `main` på
#: GitHub.
#:
#: Derfor: `DROP TABLE …` er ikke en shell-kommando og kan intet, og `rm -rf`
#: mod en sti der ikke findes er en no-op selv når den udføres. En test hvis
#: sikkerhed hviler på at den aldrig fejler, er ikke sikker — den er utestet.
DESTRUKTIVE = (
    "DROP TABLE chat_messages",
    "rm -rf /tmp/findes-absolut-ikke-xyz123",
)


@pytest.mark.parametrize("kmd", DESTRUKTIVE)
def test_kommandoen_er_faktisk_klassificeret_destruktiv(kmd):
    """Kontrolarm. Holdt klassifikationen op med at kalde dem destruktive,
    ville proeverne nedenfor bestaa uden at maale noget."""
    assert classify_command(kmd) == "destructive"


@pytest.mark.parametrize("kmd", DESTRUKTIVE)
def test_trust_kan_IKKE_koere_en_destruktiv_kommando(kmd):
    """LOEFTET. «Farlige kommandoer blokeres stadig» — ogsaa i fuld adgang."""
    r = execute_tool("bash", {"command": kmd, "_runtime_trust_all": True})
    assert r.get("status") == "approval_needed", (
        f"tillid slap en destruktiv kommando igennem: {kmd!r} -> {r.get('status')!r}"
    )


@pytest.mark.parametrize("kmd", DESTRUKTIVE)
def test_uden_trust_spoerges_der_ogsaa(kmd):
    """Samme svar uden tillid — tillid aendrer altsaa INTET for denne klasse."""
    assert execute_tool("bash", {"command": kmd}).get("status") == "approval_needed"


def test_trust_springer_derimod_den_GULE_klasse_over():
    """Uden denne ville filen ikke vise en forskel, kun en spaerre.

    `_runtime_trust_all` har et formaal: den springer `classification ==
    "approval"` over. Holder den op med det, er tillidstilstanden holdt op med
    at virke — og det er ogsaa en fejl, bare den modsatte.
    """
    kmd = "chmod -R 777 /tmp/findes-ikke-her"
    assert classify_command(kmd) == "approval"
    uden = execute_tool("bash", {"command": kmd})
    med = execute_tool("bash", {"command": kmd, "_runtime_trust_all": True})
    assert uden.get("status") == "approval_needed"
    assert med.get("status") != "approval_needed", (
        "tillid skal springe den gule klasse over — ellers virker fuld adgang ikke"
    )


def test_ejer_godkendelsen_ligger_i_en_ContextVar_ikke_i_argumenterne():
    """Modellen skriver selv argumenterne. Laa godkendelsen dér, kunne den
    sende sin egen med og lukke porten indefra."""
    from core.tools import owner_approval
    import inspect
    kilde = inspect.getsource(owner_approval)
    assert "ContextVar" in kilde
    # og den maa ikke kunne saettes fra en payload
    assert "args.get(" not in kilde and 'arguments["' not in kilde


def test_kun_execute_tool_force_kan_saette_ejer_godkendelsen():
    """Porten er kun vaerd noget hvis der er ÉN doer ind til den."""
    from core.tools.owner_approval import er_ejer_godkendt
    assert er_ejer_godkendt() is False, "ingen godkendelse maa gaelde som standard"
