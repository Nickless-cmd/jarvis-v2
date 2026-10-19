"""Sætnings-guard for continuation-detektoren — målt mod 8 faktiske tekster.

Baggrund (19/10-2026): `runtime.continuation_triggered` havde fyret 8 gange på
14 dage, og 4 af dem var falske — de startede et autonomt run der svarede i
Bjørns navn uden at nogen havde bedt om det. De falske havde hver sin form,
men fælles fejlklasse: reglen læste et SÆTNINGSFRAGMENT uden at se sætningens
type eller polaritet.

Facit er de 8 tekster hentet fra den levende base (`chat_messages`, den
assistant-besked der lå lige før hver trigger). De er gengivet her i forkortet
form — nok til at bære den egenskab der afgør klassifikationen.

Retningen er konservativ (modulets egen filosofi): et tabt ægte træf koster ét
ping fra Bjørn; et falsk træf starter et autonomt run. Derfor må guarden gerne
være lidt for villig til at sige «ingen pause» — men den må IKKE slå ægte træf
ihjel. Det var præcis fejlen i første forsøg: 4 ægte træf blev dræbt for at
fjerne 2 falske, og det er værre end problemet.
"""
from __future__ import annotations

import pytest

from core.services.unfinished_intent import detect_unfinished_intent


# ── De 4 falske: ingen continuation ────────────────────────────────────────
FALSKE = [
    pytest.param(
        "Og jeg skal lige lukke min egen fejl ordentligt: jeg målte MEMORY.md "
        "på disken og kaldte det promptstørrelse. Det var forkert, og dit tal "
        "står: ~13 % af vinduet, og der er ikke meget at spare.",
        id="19-10-jeg_skal-lukke-verbum",
    ),
    pytest.param(
        "Vil du have at jeg bygger den som en skitse — eller skal vi først "
        "finde ud af om det er hardware, AI-opgaver eller opsætning der skal "
        "stå på den? Jeg har lagt valget op til dig — fire spor, hver med sit "
        "svar på hvad der skal stå på siden. Jeg venter på dit valg.",
        id="18-10-future-spoergsmaal",
    ),
    pytest.param(
        "Jeg skriver ikke noget nu. Sig til hvad du synes om skæringen — "
        "særligt om Milestones skal halveres eller helt ud af README.",
        id="11-10-future-negation-i-match",
    ),
    pytest.param(
        "Vil du have jeg tjekker at 0.6.221 faktisk har alle tre platforme "
        "med, nu hvor workflowen er færdig?",
        id="11-10-future-spoergsmaal-tilbud",
    ),
]


# ── De 4 ægte: continuation skal stadig fyre ───────────────────────────────
AEGTE = [
    pytest.param(
        "Værktøjerne findes — jeg kalder dem nu og tjekker både Gmail og "
        "admin-postkassen på web-containeren, så jeg ikke kun måler én kilde.",
        id="16-10-future-kalder-nu",
    ),
    pytest.param(
        "Koden er ikke i drift, ikke pushet, og hook'en har en indvending jeg "
        "skal svare på først.",
        id="15-10-jeg_skal-svare-paa-foerst",
    ),
    pytest.param(
        "Næste skridt er ikke dit: genstarten ligger klar og fyrer af sig selv, "
        "og hvert værktøjskald jeg laver nu holder mit run i live og udskyder den.",
        id="13-10-future-laver-nu",
    ),
    pytest.param(
        "Stadig åbne fra i går, urørt: GET /chat/sessions → 403 i et væk. "
        "Sig til hvis jeg skal tage dem. Wakeup kl. 20:19 tjekker at 0.6.213 "
        "lander med filer.",
        id="08-10-jeg_skal-tage-dem",
    ),
]


@pytest.mark.parametrize("tekst", FALSKE)
def test_falske_træf_giver_ingen_continuation(tekst: str) -> None:
    """De fire målte falske må ikke starte et autonomt run."""
    assert detect_unfinished_intent(tekst) is None


@pytest.mark.parametrize("tekst", AEGTE)
def test_aegte_træf_bevares(tekst: str) -> None:
    """De fire ægte pauser skal stadig fanges — guarden må ikke være for bred."""
    assert detect_unfinished_intent(tekst) is not None


def test_negation_efter_match_vender_loftet() -> None:
    """«Jeg skriver ikke noget nu» — negationen ligger INDE i matchet."""
    assert detect_unfinished_intent(
        "Jeg skriver ikke noget nu. Sig til hvad du synes."
    ) is None


def test_negation_i_anden_ledsaetning_negerer_ikke_loftet() -> None:
    """«…hvert værktøjskald jeg laver nu…» — «ikke dit» står i en anden ledsætning."""
    assert detect_unfinished_intent(
        "Næste skridt er ikke dit: genstarten fyrer af sig selv, og hvert "
        "værktøjskald jeg laver nu holder mit run i live og udskyder den."
    ) is not None


def test_foerst_skal_jeg_er_ikke_et_spoergsmaal() -> None:
    """«Først skal jeg dog hente …» er en konstatering, ikke et spørgsmål.

    Regression fra 19/10-2026: spørgsmåls-regex'et matchede «skal jeg» og
    dræbte et ægte træf. Kun utvetydige spørgsmål må blokere.
    """
    assert detect_unfinished_intent(
        "Det giver mening at gå i gang nu med det samme. Først skal jeg dog "
        "hente seneste version af filen."
    ) is not None


def test_lukke_verbum_i_anden_saetning_draeber_ikke_aegte_traef() -> None:
    """Lukke-verbum-guarden må kun se på matchet og dets umiddelbare hale."""
    assert detect_unfinished_intent(
        "Jeg skal tjekke om filen er der. Bagefter lukker jeg sagen."
    ) is not None
