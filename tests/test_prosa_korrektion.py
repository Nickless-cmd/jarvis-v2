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

# Samme form, men UDEN konkrete data. Den mekaniske opstiller nægter at røre
# den (den kræver mindst to data-bærende led), så model-korridoren bliver
# faktisk afprøvet. Uden dette fixture ville syv tests måle den mekaniske vej
# og påstå at de målte modellen.
SMOERE_ET_DATUM = (
    "## ✅ Den er landet\n\n"
    "Commit e4036a383 er pushet, og jeg synes egentlig at det hele ser "
    "fornuftigt ud nu, og der er ikke noget tilbage som bekymrer mig "
    "synderligt her i forløbet.\n"
)

LISTE = (    "- Commit — e4036a383, kl. 12:38:27, pushet\n"
    "- Filen — core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496\n"
    "- Tests — 11 grønne\n"
    "- Levende — runtime genstartede 12:40:50"
)


# ── 1. Den retter et smøre-afsnit ───────────────────────────────────────────


def test_smoere_omskrives_til_punktopstilling() -> None:
    """Bjørns eksempel bliver en opstilling — og indholdet bæres ordret over.

    Siden 25/10-2026 sker det MEKANISK, uden model: et afsnit med fem
    data-bærende led splittes til fem linjer. Testen måler formen, ikke hvem
    der lavede den.
    """
    fejl = fejl_i_prosa(SMOERE)
    assert fejl, "guarden skal se fejlen før korrektionen kan kaldes"

    ud = _kald(SMOERE, fejl, LISTE)

    assert ud != SMOERE
    assert "- Commit e4036a383 kl. 12:38:27, pushet." in ud
    assert "- 11 tests grønne" in ud
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
    fejl = fejl_i_prosa(SMOERE_ET_DATUM)
    ud = _kald(SMOERE_ET_DATUM, fejl, LISTE, fejl=True)
    assert ud == SMOERE_ET_DATUM


def test_svar_uden_liste_forkastes() -> None:
    """MUTATION: fjern liste-kontrollen → prosa erstatter prosa → fejler."""
    fejl = fejl_i_prosa(SMOERE_ET_DATUM)
    ud = _kald(SMOERE_ET_DATUM, fejl, "Stadig en lang smøre, bare skrevet igen.")
    assert ud == SMOERE_ET_DATUM


def test_forkert_antal_afsnit_forkastes() -> None:
    """MUTATION: fjern `len(stykker) != len(par)`-gaten → halvt svar → fejler."""
    fejl = fejl_i_prosa(SMOERE_ET_DATUM)
    ud = _kald(SMOERE_ET_DATUM, fejl, "- kun ét afsnit")
    assert ud == SMOERE_ET_DATUM


def test_korrektion_der_ikke_hjaelper_forkastes() -> None:
    """MUTATION: fjern `len(_fejl_efter(nyt)) >= len(fejl)` → fejler.

    Modellen svarer med en liste, men den er ikke kortere end fejlen — altså
    er der ikke vundet noget, og teksten skal stå uændret.
    """
    fejl = fejl_i_prosa(SMOERE_ET_DATUM)
    ud = _kald(SMOERE_ET_DATUM, fejl, "- et\n- b\n- c\n- d")
    assert ud == SMOERE_ET_DATUM


# ── 4. Kun de ramte afsnit sendes ───────────────────────────────────────────


def test_kun_det_ramte_afsnit_sendes_til_modellen() -> None:
    """MUTATION: send hele teksten i opgaven → den urørte sektion er med → fejler."""
    tekst = (
        "## Første\n\n"
        "Kort og klar pointe her, uden nogen opremsning overhovedet i sig.\n\n"
        "## Andet\n\n"
        "Commit e4036a383 er pushet, og jeg synes egentlig at det hele ser "
        "fornuftigt ud nu, og der er ikke noget tilbage som bekymrer mig "
        "synderligt her i forløbet.\n"
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
    fejl = fejl_i_prosa(SMOERE_ET_DATUM)
    ud = _kald(SMOERE_ET_DATUM, fejl, "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
                             "core/services/prosa_struktur_guard.py, koblet i "
                             "visible_runs.py:6496, 11 tests grønne, og runtime "
                             "genstartede 12:40:50.")
    assert ud == SMOERE_ET_DATUM


def test_for_faa_afsnit_forkastes_naar_der_er_flere() -> None:
    """MUTATION: fjern `len(stykker) != len(par)`-gaten → halvt svar → fejler.

    To ramte afsnit, men modellen svarer kun med ét. Uden gaten ville det
    første afsnit blive erstattet og det andet stå som prosa — et halvt svar.
    """
    tekst = (
        "## Første\n\n"
        "Commit e4036a383 er pushet, og jeg synes egentlig at det hele ser "
        "fornuftigt ud nu, og der er ikke noget tilbage som bekymrer mig "
        "synderligt her i forløbet.\n\n"
        "## Andet\n\n"
        "Filen ligger i core/services og hedder prosa_struktur_guard, og jeg "
        "mener bestemt at det er på plads nu, og der er ikke noget tilbage "
        "som bekymrer mig synderligt her i forløbet.\n"
    )
    fejl = fejl_i_prosa(tekst)
    assert len(fejl) == 2, f"forventede to ramte afsnit, fik {len(fejl)}"

    ud = _kald(tekst, fejl, "- kun ét afsnit, med et tal 12:38:27 og e4036a383")
    assert ud == tekst


# ── Mekanisk opstilling: formen Bjørn bad om 25/10-2026 ───────────────────────


def test_mekanisk_opstiller_bjoerns_eksempel_uden_model() -> None:
    """«en prosa med en linje til Commit e4036a383 … er rodet».

    MUTATION: sæt `_mekanisk_opstil` til at returnere teksten uændret →
    teksten er stadig én smøre → fejler. MUTATION 2: fjern `(?=[A-ZÆØÅ])` i
    `_SAETNING_SPLIT` → «kl. 12:38:27» klippes midt over → fejler.
    """
    from core.services.prosa_korrektion import _mekanisk_opstil
    from core.services.prosa_struktur_guard import find_prosa_punkter

    tekst = (
        "## ✅ Den er landet — og den er levende\n\n"
        "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
        "core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496, "
        "11 tests grønne, og runtime genstartede 12:40:50.\n"
    )
    punkter = find_prosa_punkter(tekst)
    assert punkter, "forudsætning: afsnittet skal være flagget"

    nyt, uloeste = _mekanisk_opstil(tekst, punkter)
    assert not uloeste, "den mekaniske vej skulle kunne løse det hele"
    assert nyt != tekst, "afsnittet skulle være opstillet"

    linjer = [l for l in nyt.split("\n") if l.startswith("- ")]
    assert len(linjer) >= 4, f"forventede mindst fire led, fik {len(linjer)}"
    # «kl. 12:38:27» hører til commit-linjen — den er ikke sin egen sætning.
    assert any("kl. 12:38:27" in l for l in linjer), (
        "tidsstemplet blev klippet midt over — en forkortelse er ikke en sætning"
    )
    assert not any(l.strip() == "- 12:38:27, pushet." for l in linjer)


def test_mekanisk_bevarer_alt_indhold() -> None:
    """Intet ord, tal eller sti må forsvinde eller opfindes.

    MUTATION: erstat `led` med en fast liste → tokens mangler → fejler.
    """
    import re

    from core.services.prosa_korrektion import _mekanisk_opstil
    from core.services.prosa_struktur_guard import find_prosa_punkter

    tekst = (
        "## Leverance\n\n"
        "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
        "core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496, "
        "11 tests grønne, og runtime genstartede 12:40:50.\n"
    )
    nyt, _ = _mekanisk_opstil(tekst, find_prosa_punkter(tekst))
    mønster = r"[A-Za-z0-9_./:-]{4,}"
    før = set(re.findall(mønster, tekst))
    efter = set(re.findall(mønster, nyt))
    assert før == efter, f"mangler {før - efter} · opfundet {efter - før}"


def test_mekanisk_roerer_ikke_almindelig_prosa() -> None:
    """Fortællende prosa med tal i skal netop FLYDE.

    MUTATION: fjern data-kravet (»mindst to led bærer data«) → afsnittet
    splittes → fejler.
    """
    from core.services.prosa_korrektion import _mekanisk_opstil
    from core.services.prosa_struktur_guard import find_prosa_punkter

    tekst = (
        "## Om dagen\n\n"
        "Jeg vågnede 06:30 og tænkte på arbejdet. Vejret var gråt, og det "
        "passede mig egentlig fint. Kaffen blev kold mens jeg læste.\n"
    )
    nyt, _ = _mekanisk_opstil(tekst, find_prosa_punkter(tekst))
    assert nyt == tekst, "almindelig prosa må ikke blive en punktopstilling"


def test_mekanisk_loesning_sparer_modelkaldet() -> None:
    """Kan det løses mekanisk, må modellen slet ikke kaldes.

    MUTATION: fjern `if not par: return tekst` → det tællende kald fyrer →
    fejler. (Målt 25/10-2026: en separat `if not punkter`-gate efter
    `_mekanisk_opstil` var ren redundans — den kunne fjernes uden at denne
    test faldt, fordi `if not par` allerede dækkede den. Den er væk.)
    """
    from core.services.prosa_korrektion import korriger_prosa
    from core.services.prosa_struktur_guard import fejl_i_prosa

    tekst = (
        "## Leverance\n\n"
        "Commit e4036a383 kl. 12:38:27, pushet. Filen er "
        "core/services/prosa_struktur_guard.py, koblet i visible_runs.py:6496, "
        "11 tests grønne, og runtime genstartede 12:40:50.\n"
    )
    kald: list[int] = []

    def _stream(**_kwargs):
        kald.append(1)
        yield FollowupDelta(delta="- noget")
        yield FollowupDone(text="- noget")

    ud = korriger_prosa(
        tekst,
        fejl_i_prosa(tekst),
        stream_followup=_stream,
        provider="test",
        model="test",
        base_messages=[],
    )
    assert kald == [], f"modellen blev kaldt {len(kald)} gang(e) — det var mekanisk"
    assert ud != tekst
    assert ud.count("\n- ") >= 3
