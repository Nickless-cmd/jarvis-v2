"""Korrektionsrunden for prosa: et smøre-afsnit rettes FØR det vises.

Målt 25/10-2026 (Bjørn, to gange om samme svar): «den første.. og i gør commits
skal vises ordenligt og ikk som en lang besked men med den rigtige opstilling»
og «en prosa med en linje til Commit e4036a383 … er rodet».

Guarden fra samme dag SÅ fejlen, men skrev den kun i central_incidents. Et flag
ingen læser er ikke en kontrol. Denne test værner at korrektionen faktisk
omskriver afsnittet — og at den ikke rører et svar der allerede er struktureret.

Hver test er mutationsprøvet: den adfærd testen påstår at måle er slået fra, og
testen er set fejle. Mutationen står i kommentaren over den enkelte test.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.prosa_korrektion import korriger_prosa  # noqa: E402
from core.services.prosa_struktur_guard import fejl_i_prosa  # noqa: E402
from core.services.visible_followup_events import (  # noqa: E402
    FollowupDelta,
    FollowupDone,
    FollowupFailed,
)


def _fake_stream(svar: str, *, fejl: bool = False):
    """En stream_followup der svarer med ``svar`` uden netværk."""

    def _stream(**_kwargs):
        if fejl:
            yield FollowupFailed(round_index=0, error="netværk nede")
            return
        yield FollowupDelta(delta=svar)
        yield FollowupDone(text=svar)

    return _stream


def _kald(tekst: str, fejlliste: list[str], svar: str, **kwargs) -> str:
    return korriger_prosa(
        tekst,
        fejlliste,
        stream_followup=_fake_stream(svar, **kwargs),
        provider="test",
        model="test",
        base_messages=[],
    )


# Bjørns eget eksempel: fire selvstændige fakta i én sætning.
SMOERE = (
    "## ✅ Den er landet\n\n"
    "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
    "core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496, "
    "11 tests grønne, og runtime genstartede 12:40:50.\n"
)

LISTE = (
    "- Commit — e4036a383, kl. 12:38:27, pushet\n"
    "- Filen — core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496\n"
    "- Tests — 11 grønne\n"
    "- Levende — runtime genstartede 12:40:50"
)


# ── 1. Den retter et smøre-afsnit ───────────────────────────────────────────


def test_smoere_omskrives_til_punktopstilling() -> None:
    """Bjørns eksempel bliver fire linjer — og indholdet bæres ordret over."""
    fejl = fejl_i_prosa(SMOERE)
    assert fejl, "guarden skal se fejlen før korrektionen kan kaldes"

    ud = _kald(SMOERE, fejl, LISTE)

    assert ud != SMOERE
    assert "- Commit — e4036a383" in ud
    assert "- Tests — 11 grønne" in ud
    # Overskriften står urørt — kun afsnittet under den er rørt.
    assert "## ✅ Den er landet" in ud
    # Og fejlen er væk bagefter.
    assert fejl_i_prosa(ud) == []


def test_indholdet_baeres_ordret_over() -> None:
    """MUTATION: lad modellen opfinde et tal → hash'en forsvinder → fejler."""
    fejl = fejl_i_prosa(SMOERE)
    ud = _kald(SMOERE, fejl, LISTE)

    for bevaret in ("e4036a383", "12:38:27", "visible_runs.py:6496", "12:40:50"):
        assert bevaret in ud, f"«{bevaret}» forsvandt i korrektionen"


# ── 2. Den rører IKKE et svar der allerede er struktureret ──────────────────


def test_struktureret_svar_roeres_ikke() -> None:
    """MUTATION: fjern `if not tekst or not fejl: return tekst` → fejler."""
    pæn = "## ✅ Den er landet\n\n" + LISTE + "\n"
    fejl = fejl_i_prosa(pæn)
    assert fejl == [], "et struktureret svar må ikke flagges"

    ud = _kald(pæn, fejl, "noget helt andet")
    assert ud == pæn


# ── 3. Fail-open: et svar må aldrig gå tabt ─────────────────────────────────


def test_netvaerksfejl_returnerer_originalen() -> None:
    """MUTATION: returnér `""` i stedet for `tekst` ved FollowupFailed → fejler."""
    fejl = fejl_i_prosa(SMOERE)
    ud = _kald(SMOERE, fejl, LISTE, fejl=True)
    assert ud == SMOERE


def test_svar_uden_liste_forkastes() -> None:
    """MUTATION: fjern liste-kontrollen → prosa erstatter prosa → fejler."""
    fejl = fejl_i_prosa(SMOERE)
    ud = _kald(SMOERE, fejl, "Stadig en lang smøre, bare skrevet igen.")
    assert ud == SMOERE


def test_forkert_antal_afsnit_forkastes() -> None:
    """MUTATION: fjern `len(stykker) != len(par)`-gaten → halvt svar → fejler."""
    fejl = fejl_i_prosa(SMOERE)
    ud = _kald(SMOERE, fejl, "- kun ét afsnit")
    assert ud == SMOERE


def test_korrektion_der_ikke_hjaelper_forkastes() -> None:
    """MUTATION: fjern `len(_fejl_efter(nyt)) >= len(fejl)` → fejler.

    Modellen svarer med en liste, men den er ikke kortere end fejlen — altså
    er der ikke vundet noget, og teksten skal stå uændret.
    """
    fejl = fejl_i_prosa(SMOERE)
    ud = _kald(SMOERE, fejl, "- et\n- b\n- c\n- d")
    assert ud == SMOERE


# ── 4. Kun de ramte afsnit sendes ───────────────────────────────────────────


def test_kun_det_ramte_afsnit_sendes_til_modellen() -> None:
    """MUTATION: send hele teksten i opgaven → den urørte sektion er med → fejler."""
    tekst = (
        "## Første\n\n"
        "Kort og klar pointe her, uden nogen opremsning overhovedet i sig.\n\n"
        "## Andet\n\n"
        "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
        "core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496, "
        "11 tests grønne, og runtime genstartede 12:40:50.\n"
    )
    fejl = fejl_i_prosa(tekst)
    assert len(fejl) == 1

    set_svar: list[str] = []

    def _stream(**kwargs):
        set_svar.append(kwargs["trailing_messages"][0]["content"])
        yield FollowupDelta(delta=LISTE)
        yield FollowupDone(text=LISTE)

    ud = korriger_prosa(
        tekst,
        fejl,
        stream_followup=_stream,
        provider="test",
        model="test",
        base_messages=[],
    )

    assert set_svar, "modellen blev aldrig kaldt"
    assert "Kort og klar pointe" not in set_svar[0], "den urørte sektion blev sendt med"
    assert "e4036a383" in set_svar[0]
    # Den urørte sektion står stadig i det færdige svar.
    assert "Kort og klar pointe" in ud
    assert "- Commit — e4036a383" in ud


# ── 5. Værn der ellers ikke har en test ─────────────────────────────────────


def test_svar_der_ikke_er_en_liste_forkastes_selv_med_rigtigt_antal() -> None:
    """MUTATION: fjern liste-kontrollen → prosa erstatter prosa → fejler.

    Modellen svarer med det rigtige antal dele, men skriver prosa igen. Uden
    liste-kontrollen ville den erstatte et afsnit med en ny smøre — altså
    gøre svaret værre, ikke bedre.
    """
    fejl = fejl_i_prosa(SMOERE)
    ud = _kald(SMOERE, fejl, "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
                             "core/services/prosa_struktur_guard.py, koblet i "
                             "visible_runs.py:6496, 11 tests grønne, og runtime "
                             "genstartede 12:40:50.")
    assert ud == SMOERE


def test_for_faa_afsnit_forkastes_naar_der_er_flere() -> None:
    """MUTATION: fjern `len(stykker) != len(par)`-gaten → halvt svar → fejler.

    To ramte afsnit, men modellen svarer kun med ét. Uden gaten ville det
    første afsnit blive erstattet og det andet stå som prosa — et halvt svar.
    """
    tekst = (
        "## Første\n\n"
        "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
        "core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496, "
        "11 tests grønne, og runtime genstartede 12:40:50.\n\n"
        "## Andet\n\n"
        "Tests kørte 11 grønne kl. 12:38, filen ligger i core/services og "
        "committen hedder e4036a383, og runtime genstartede kl. 12:40:50.\n"
    )
    fejl = fejl_i_prosa(tekst)
    assert len(fejl) == 2, f"forventede to ramte afsnit, fik {len(fejl)}"

    ud = _kald(tekst, fejl, "- kun ét afsnit, med et tal 12:38:27 og e4036a383")
    assert ud == tekst
