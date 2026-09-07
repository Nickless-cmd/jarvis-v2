"""Lær af Jarvis' EGEN indrømmelse, ikke af at gætte på Bjørns tekst.

Målt 7/9-2026 på 4.131 tur-par fra rigtig historik. At detektere rettelsen i
Bjørns besked gav **12 % dækning og 3 % præcision** — han afviser sjældent,
han leverer den manglende kendsgerning:

    "https://ollama.com/library/qwen3.6 det er ikke en cloud model"
    "Ollama kør på din container"
    "i jarvis-code køre vi osse fuld jarvis... identitet er legacy"

Ingen markør. De er kun rettelser i forhold til hvad Jarvis lige har sagt.

Men hans EGNE erkendelser er formelagtige — et simpelt mønster fandt **52 rene
træf** i de samme par. Så vend det om: skriv lektien når han indrømmer det.
"""

from __future__ import annotations

import pytest

from core.services.experience_correction_listener import (
    _looks_like_acknowledgement as ack,
)


@pytest.mark.parametrize("svar", [
    "Du har helt ret — jeg tog fejl. B4 er Temporal linking, ikke recall.",
    "Min fejl — kaldet blev sendt med forkert felt.",
    "Fair nok, min fejl — jeg gættede i stedet for at grave.",
    "Åh, du har helt ret! Tak for rettelsen — det er den 6. maj.",
    "Jeg konkluderede forkert. Downgrade var ikke det der fixede det.",
])
def test_erkendelser_fanges(svar):
    assert ack(svar) is True


def test_du_har_ret_alene_er_IKKE_en_erkendelse():
    """182 af 3.000 svar indeholdt «du har ret» — en talemåde.

    Tages den med, måler man høflighed i stedet for rettelser: facittet gik fra
    52 rene træf til 212, hvoraf 86 % var almindelig enighed.
    """
    assert ack("Du har ret — det passer, og det er en god idé.") is False
    assert ack("Du har nok ret. Og det sjove er at det måske...") is False


def test_spoegefuld_indroemmelse_taeller_ikke():
    """«Haha, min fejl! 😄 Troede du var på vej i seng» er ikke en rettelse."""
    assert ack("Haha, min fejl! 😄 Troede du var på vej i seng.") is False
    assert ack("min fejl 🤣 troede du sov") is False


def test_en_aegte_min_fejl_taeller_stadig():
    """Værnet må ikke smide de rigtige ud sammen med spøgen."""
    assert ack("Min fejl. Jeg læste tabellen forkert — der står 4 rækker, ikke 40.") is True


def test_tomt_svar_er_ikke_en_erkendelse():
    assert ack("") is False
    assert ack("   ") is False


def test_kilden_aktiveres_IKKE_straks():
    """Den er en slutning, ikke en detekteret rettelse.

    ~15 % af erkendelserne er i spøg eller uden en rigtig rettelse bag. Ville
    de gå direkte i prompten, ville vi bytte den gamle støj ud med ny. De
    venter i stedet på at gentage sig (evidens 2).
    """
    from core.runtime.db_lessons import SOURCE_SELF_ACK, _ACTIVATE_IMMEDIATELY

    assert SOURCE_SELF_ACK not in _ACTIVATE_IMMEDIATELY


def test_for_kort_brugerbesked_giver_ingen_lektie(monkeypatch):
    """«ja» er ikke en rettelse, uanset hvad han svarer bagefter.

    Målt: skærer 6 tomme fra af 50.
    """
    from core.services import experience_correction_listener as L

    skrevet: list[str] = []
    monkeypatch.setattr(L, "_previous_user_text", lambda sid: "ja")
    monkeypatch.setattr(
        "core.services.lessons.record_self_acknowledged_correction",
        lambda **kw: skrevet.append(kw.get("user_words", "")),
    )
    L._record_self_ack_lesson("chat-1", "Jeg tog fejl — det er B4.")
    assert skrevet == []


def test_bjoerns_ord_bliver_til_lektien(monkeypatch):
    """Selve pointen: HANS besked er rettelsen, ikke Jarvis' svar."""
    from core.services import experience_correction_listener as L

    fanget: dict = {}
    monkeypatch.setattr(
        L, "_previous_user_text",
        lambda sid: "https://ollama.com/library/qwen3.6 det er ikke en cloud model",
    )
    monkeypatch.setattr(
        "core.services.lessons.record_self_acknowledged_correction",
        lambda **kw: fanget.update(kw),
    )
    L._record_self_ack_lesson("chat-1", "Du har ret! Qwen3.6 er ikke en cloud-model.")
    assert "qwen3.6" in fanget["user_words"]
    assert "cloud-model" in fanget["jarvis_words"]


def test_INGEN_kilde_aktiveres_straks():
    """Målt: mønsteret på Bjørns tekst har 3 % præcision og 156 træf i
    historikken. Med straks-aktivering var det ~150 junk-lektier direkte i
    prompten — vi ville have byttet den gamle støj ud med ny.

    Alt venter nu på evidens 2: en ægte tilbagevendende rettelse gentager sig,
    en enkeltstående hilsen gør ikke.
    """
    from core.runtime.db_lessons import _ACTIVATE_IMMEDIATELY, _ACTIVATE_AT_EVIDENCE

    assert not _ACTIVATE_IMMEDIATELY
    assert _ACTIVATE_AT_EVIDENCE >= 2
