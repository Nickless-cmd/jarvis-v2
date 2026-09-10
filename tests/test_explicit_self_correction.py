"""En udtrykkelig korrektion laeres FORELOEBIGT.

Opgave 5. Hidtil kunne en selv-begraensning kun opstaa hvis en aktiv kritiker
allerede stoettede den med mindst to observationer. Det er en god graense mod
stoej — men den betyder at Bjoern kan sige «du tog fejl om dine egne evner» og
runtimen registrerer ingenting.

Den anden yderlighed er vaerre: at tage én saetning for paalydende og skrive den
ind som en sandhed om selvet. Saa kan enhver der skriver til Jarvis omskrive
hans selvbillede med én velformuleret paastand.

Derfor: en udtrykkelig korrektion aabner et FORELOEBIGT signal —
`uncertain`/`medium` — og kun uafhaengig stoette forfremmer det. Det er samme
bevis-disciplin som resten af grenen: én kilde er et spor, to er et faktum.

OG ET SPOERGSMAAL ER IKKE EN KORREKTION. «Husker du din historik?» er en
foresporgsel; «du glemte at tjekke din historik» er en paastand. Kan de to ikke
skelnes, laerer runtimen af sin egen samtalepartners tvivl.
"""
from __future__ import annotations

import pytest

from core.services.self_model_signal_tracking import (
    explicit_self_correction_candidate,
)


@pytest.mark.parametrize("besked", [
    "du glemte at tjekke din historik",
    "du tog fejl om dine egne evner",
    "there is a problem with your self model",
    "you were wrong about your own limits",
    "du har misforstået din egen rolle her",
])
def test_udtrykkelige_korrektioner_fanges(besked):
    k = explicit_self_correction_candidate(besked)
    assert k is not None, f"ikke fanget: {besked!r}"
    assert k["status"] == "uncertain", "en enkelt paastand blev til en sandhed"
    assert k["confidence"] == "medium"
    assert k["support_count"] == 1
    assert k["source_kind"] == "explicit-correction"


@pytest.mark.parametrize("besked", [
    "husker du din historik?",
    "kan du tjekke dine egne evner?",
    "what does your self model say?",
    "din historik er interessant",
    "jeg tog fejl om det",
    "du er god til det her",
    "",
])
def test_spoergsmaal_og_neutrale_omtaler_laerer_INTET(besked):
    """«Husker du din historik?» er en foresporgsel, ikke en paastand. Og
    «jeg tog fejl» handler om BRUGEREN, ikke om Jarvis."""
    assert explicit_self_correction_candidate(besked) is None, (
        f"laerte af noget der ikke var en korrektion: {besked!r}")


def test_korrektionen_baerer_brugerens_egne_ord():
    """Et signal uden citatet kan man ikke stille sig kritisk over for
    bagefter — man kan ikke se HVAD der blev sagt."""
    k = explicit_self_correction_candidate("du glemte at tjekke din historik")
    assert "glemte" in str(k["evidence_summary"])


def test_samme_korrektion_giver_samme_noegle():
    """Ellers ville to udgaver af samme klage se ud som to uafhaengige kilder
    — og forfremme sig selv."""
    a = explicit_self_correction_candidate("du glemte at tjekke din historik")
    b = explicit_self_correction_candidate("Du GLEMTE at tjekke din historik!")
    assert a["canonical_key"] == b["canonical_key"]


def test_det_er_deterministisk():
    """Ingen model, ingen tilfaeldighed: samme input, samme svar. En
    selv-opfattelse der aendrer sig med temperaturen er ikke en maaling."""
    b = "du tog fejl om dine egne evner"
    assert explicit_self_correction_candidate(b) == explicit_self_correction_candidate(b)


def test_korrektionen_er_koblet_ind_i_udtraekket():
    """Uden koblingen ville udtraekkeren findes og aldrig blive kaldt — og saa
    ville «du tog fejl om dine egne evner» stadig registrere ingenting."""
    import inspect

    from core.services import self_model_signal_tracking as t

    kilde = inspect.getsource(t._extract_self_model_candidates)
    assert "explicit_self_correction_candidate(" in kilde


def test_den_kritiker_stoettede_sti_er_UROERT():
    """Den nye sti supplerer, den erstatter ikke. En korrektion med aegte
    kritiker-stoette skal stadig kunne blive `active` med det samme."""
    import inspect

    from core.services import self_model_signal_tracking as t

    kilde = inspect.getsource(t._extract_self_model_candidates)
    assert "_current_limitation_signal(" in kilde
    assert kilde.index("_current_limitation_signal(") < kilde.index(
        "explicit_self_correction_candidate("), (
        "den kritiker-stoettede sti skal stadig komme foerst")
