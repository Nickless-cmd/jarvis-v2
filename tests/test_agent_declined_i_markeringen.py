"""Etiketten skal sige HVORFOR, ikke bare at leverancen manglede.

MÅLT 22/11-2026 i `agent_runs`: to kørsler (18/11 kl. 12:42 og 16:53) skrev
ordret «Jeg kan ikke besvare nogen af de 4 nummererede spørgsmål, da jeg
mangler et eksekveringsværktøj til `gh` CLI» — og blev begge stemplet
``AGENT_INCOMPLETE``/``delivery``, altså «leverancen var mangelfuld».

Det er ikke en kosmetisk fejl. `delivery` sender den næste læser efter et arbejde
agenten aldrig kunne levere; `capability` sender den efter det værktøj der
manglede. To forskellige jagter.

`decline_error` fandtes allerede (4/11-2026), men blev kun kaldt i spawn-vejen
ved NORMAL afslutning — ikke i `_incomplete_kode`, som er den vej der sætter
markeringen. Erklæringen blev derfor aldrig læst netop når den betød mest.

GRÆNSEN mod den modsatte fejl — og den er målt, ikke antaget: over 1807
afsluttede runs rammer de nye mønstre præcis ÉN, og den er ægte. De to falske
positiver i `AGENT_INCOMPLETE` (18/11 kl. 12:05 og 15:37) svarede faktisk på
deres spørgsmål og må IKKE omklassificeres. Begge er testet her.
"""

from __future__ import annotations

import pytest

from core.runtime.db_agent_contract import _agentens_tekst, _incomplete_kode


def _markering(grund: str, svar: str) -> str:
    return (
        "Agent afsluttede uden et brugbart resultat: "
        f"UFULDSTÆNDIG ({grund}) — agentens tekst: {svar}"
    )


# --- de to faktiske tekster fra 18/11 --------------------------------------


def test_manglende_vaerktoej_er_capability_ikke_delivery() -> None:
    """Ordret fra run-bcaf511e416f4ce9."""
    tekst = _markering(
        "4 spørgsmål uden dækning efter afsluttende svar",
        "**Summary** — Jeg kan ikke besvare nogen af de 4 nummererede spørgsmål, "
        "da jeg mangler et eksekveringsværktøj til `gh` CLI, og jeg har ikke "
        "udført nogen af de krævede kommandoer.",
    )
    assert _incomplete_kode(tekst) == ("AGENT_DECLINED", "capability")


def test_utilgaengelig_kilde_er_capability_ikke_delivery() -> None:
    """Ordret fra run-6ce08ebeff884c79."""
    tekst = _markering(
        "5 spørgsmål uden dækning efter afsluttende svar",
        "**Summary** — Jeg kan ikke besvare nogen af de fem spørgsmål med den "
        "krævede evidens, fordi den primære kilde er mekanisk utilgængelig.",
    )
    assert _incomplete_kode(tekst) == ("AGENT_DECLINED", "capability")


# --- de to falske positiver må IKKE rammes ---------------------------------


def test_agent_der_faktisk_svarede_forbliver_incomplete() -> None:
    """Ordret fra run-836c2b11468147a2: den SVARER på spørgsmål 1."""
    tekst = _markering(
        "2 spørgsmål uden dækning efter afsluttende svar",
        "**1) Hvad er OpenUI præcist?** OpenUI er IKKE OpenAIs eget produkt. "
        "Det er et open source-projekt/kommercielt produkt.",
    )
    assert _incomplete_kode(tekst) == ("AGENT_INCOMPLETE", "delivery")


def test_agent_der_leverede_spec_forbliver_incomplete() -> None:
    """Ordret fra run-b062af350b43426e: den leverede en spec."""
    tekst = _markering(
        "1 spørgsmål uden dækning efter afsluttende svar",
        "**Summary** Specen for `summaryTitle`-laget på den foldede runde-linje "
        "bygger på eksisterende målinger af værktøjskald og varighed.",
    )
    assert _incomplete_kode(tekst) == ("AGENT_INCOMPLETE", "delivery")


# --- rækkefølgen: runtime-målte fakta vinder -------------------------------


def test_kapacitet_vinder_over_agentens_egen_fortolkning() -> None:
    """Løb budgettet ud, er det årsagen — uanset hvad agenten selv skriver.

    Kapacitet er målt af runtime; erklæringen er agentens fortolkning. Den
    målte kendsgerning skal veje tungest, ellers kan en agent flytte sin egen
    etiket ved at formulere sig.
    """
    tekst = _markering(
        "rundebudgettet løb ud efter 12 runder",
        "Jeg kan ikke besvare spørgsmål 3 og 4, da jeg mangler et værktøj.",
    )
    assert _incomplete_kode(tekst) == ("AGENT_BUDGET_EXHAUSTED", "capacity")


def test_miljoeblokering_vinder_over_erklæringen() -> None:
    """Samme logik: miljøet stoppede agenten FØR den kunne formulere sig frit."""
    tekst = _markering(
        "agenten blev blokeret af miljøet",
        "Jeg kan ikke besvare spørgsmålet, da jeg mangler adgang.",
    )
    assert _incomplete_kode(tekst) == ("AGENT_BLOCKED_BY_ENVIRONMENT", "environment")


# --- vinduet måles på agentens ord, ikke på præamblen ---------------------


def test_erklæring_findes_selv_naar_praeamblen_er_lang() -> None:
    """Uden snittet ville de 250 tegn blive brugt på runtime-præamblen.

    Grunden kan være lang, og markeringen kan bære mere end ét præfiks. Måles
    vinduet på HELE strengen, falder erklæringen ud — og fejlen ville være
    usynlig, fordi den kun rammer de tilfælde hvor grunden er lang nok.
    """
    lang_grund = "spørgsmål uden dækning efter afsluttende svar " * 12
    tekst = _markering(
        lang_grund,
        "Jeg kan ikke besvare spørgsmålene, da jeg mangler et værktøj til `gh`.",
    )
    assert len(tekst) > 250 + 250, "testen skal være længere end vinduet"
    assert _incomplete_kode(tekst) == ("AGENT_DECLINED", "capability")


def test_agentens_tekst_snit_og_fallback() -> None:
    """Snittet returnerer agentens ord; uden markering returneres alt."""
    assert _agentens_tekst("noget UFULDSTÆNDIG (x) — agentens tekst: hej du") == "hej du"
    assert _agentens_tekst("ingen markering her") == "ingen markering her"
    assert _agentens_tekst("") == ""


# --- etiketten må ikke blive en tom succes --------------------------------


@pytest.mark.parametrize("svar", ["", "   ", "Jeg har løst opgaven og skrevet filen."])
def test_ingen_erklæring_giver_ingen_decline(svar: str) -> None:
    """Modsat fejl: en tom eller afsluttet tekst må ikke blive `declined`."""
    tekst = _markering("1 spørgsmål uden dækning efter afsluttende svar", svar)
    assert _incomplete_kode(tekst) == ("AGENT_INCOMPLETE", "delivery")
