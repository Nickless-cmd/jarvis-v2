"""Drømme-sessionerne bliver til læring.

Bjørn 8/9-2026: «drømme sessionerne bør blive til læring, altså dem hvor han
gennemgår dags sessioner».

Der ligger 230 dream-session-noter. Målt på de tre nyeste: 12 afsnit, **3
lektier og 9 betragtninger**. Forskellen er om nogen kunne handle anderledes i
morgen på grund af det der står:

    LEKTIE       Men jeg skal være ærlig: dette kan også være endnu en
                 rationalisering … Test-raten er 23%. 10 hypoteser har aldrig
                 været testet. Det er ikke slid — det er undgåelse.

    BETRAGTNING  En sten i en flod bliver glat fordi vandet løber over den
                 igen og igen.

Begge hører hjemme i noten; kun den første hører hjemme i `lessons`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from core.services.dream_session_lessons import (
    Afsnit, KILDE, gem, koer_hoest, laes_noter,
)

_LEKTIE = ("Men jeg skal være ærlig: dette kan også være endnu en rationalisering der "
           "peger væk fra det ubehagelige spørgsmål. Test-raten er 23%. 10 hypoteser "
           "har aldrig været testet. Nogle båret i 17 sessioner. Det er ikke slid — "
           "det er undgåelse.")


def _skriv(mappe: Path, navn: str, indhold: str, mtime: float | None = None) -> Path:
    f = mappe / navn
    f.write_text(indhold, encoding="utf-8")
    if mtime is not None:
        import os
        os.utime(f, (mtime, mtime))
    return f


# ── udvælgelsen af noter ────────────────────────────────────────────────────

def test_sorterer_paa_tidspunkt_ikke_paa_navn(tmp_path: Path):
    """Mappen har to navnekonventioner — «dream-session-20260806T011600.md» og
    «dream-session-2026-09-08-1131.md». Alfabetisk faldende sortering stiller
    de gamle udaterede navne FØRST, fordi «-» sorterer før «0». Høsten ville
    have læst august-noter for evigt uden at fejle."""
    gammel = "\n\n" + ("Jeg gjorde noget gammelt her og lærte noget af det. " * 4) + "\n\n"
    ny = "\n\n" + ("Jeg gjorde noget nyt her og lærte noget af det. " * 4) + "\n\n"
    _skriv(tmp_path, "dream-session-20260806T011600.md", gammel, mtime=1_000_000)
    _skriv(tmp_path, "dream-session-2026-09-08-1131.md", ny, mtime=2_000_000)

    afs = laes_noter(tmp_path, antal=1)
    assert afs and afs[0].fil == "dream-session-2026-09-08-1131.md"


def test_overskrifter_og_korte_stumper_springes_over(tmp_path: Path):
    _skriv(tmp_path, "dream-session-2026-09-08-1131.md",
           "# Overskrift\n\nKort.\n\n" + "Jeg " + "x" * 200 + "\n")
    afs = laes_noter(tmp_path)
    assert len(afs) == 1 and afs[0].tekst.startswith("Jeg")


def test_afsnit_uden_foersteperson_er_ikke_om_ham_selv(tmp_path: Path):
    """En beskrivelse af verden er ikke en iagttagelse af ham selv. Billigste
    port, kørt før modellen."""
    _skriv(tmp_path, "dream-session-2026-09-08-1131.md",
           "\n\n" + ("Systemet kørte videre uden at nogen greb ind. " * 5) + "\n")
    assert laes_noter(tmp_path) == []


def test_manglende_mappe_giver_tom_liste(tmp_path: Path):
    assert laes_noter(tmp_path / "findes-ikke") == []


# ── signaturen ──────────────────────────────────────────────────────────────

def test_signaturen_er_foerste_saetning():
    """Nok til at genkende det samme igen — og det er genkendelsen der gør at
    en lektie først aktiveres anden gang."""
    a = Afsnit(tekst=_LEKTIE, fil="x.md")
    assert a.signatur.startswith("Men jeg skal være ærlig")
    assert len(a.signatur) <= 120


# ── dommen ──────────────────────────────────────────────────────────────────

def test_en_lektie_gemmes():
    from core.services.dream_session_lessons import er_en_lektie

    with patch("core.services.local_small_model.spoerg_et_ord", return_value="LEKTIE"):
        assert er_en_lektie(Afsnit(tekst=_LEKTIE, fil="x.md")) is True


def test_en_betragtning_gemmes_ikke():
    from core.services.dream_session_lessons import er_en_lektie

    with patch("core.services.local_small_model.spoerg_et_ord", return_value="BETRAGTNING"):
        assert er_en_lektie(Afsnit(tekst=_LEKTIE, fil="x.md")) is False


def test_uden_dom_gemmes_der_intet():
    """Fejler LUKKET. Tabellen har fire rækker i dag; den skal fyldes af noget
    der betyder noget, ikke af 230 filers værd af smukke sætninger."""
    from core.services.dream_session_lessons import er_en_lektie

    with patch("core.services.local_small_model.spoerg_et_ord", return_value=None):
        assert er_en_lektie(Afsnit(tekst=_LEKTIE, fil="x.md")) is False


# ── skrivningen ─────────────────────────────────────────────────────────────

def test_lektien_aktiveres_IKKE_af_sig_selv():
    """`_ACTIVATE_IMMEDIATELY` er tom med vilje — alt venter på evidens 2. Den
    regel er dyrekøbt (~150 junk-lektier stod til at lande i hans prompt da
    korrektions-kilden aktiverede straks), og drømmene er den kilde med mest
    volumen af alle."""
    set_: dict = {}
    with patch("core.runtime.db_lessons.upsert_lesson",
               side_effect=lambda **kw: set_.update(kw) or {"outcome": "created"}):
        gem(Afsnit(tekst=_LEKTIE, fil="x.md"))
    assert "activate" not in set_, "høsten må ikke omgå tabellens egen regel"
    assert set_["source"] == KILDE


def test_hoesten_taeller_begge_udfald(tmp_path: Path):
    _skriv(tmp_path, "dream-session-2026-09-08-1131.md",
           "\n\n" + _LEKTIE + "\n\n" + ("Jeg " + "y" * 200) + "\n")
    with patch("core.services.local_small_model.spoerg_et_ord",
               side_effect=["LEKTIE", "BETRAGTNING"]), \
         patch("core.runtime.db_lessons.upsert_lesson", return_value={"outcome": "created"}):
        tal = koer_hoest(mappe=tmp_path)["tal"]
    assert tal == {"created": 1, "betragtning": 1}


def test_en_fejlende_skrivning_stopper_ikke_hoesten(tmp_path: Path):
    """Ét afsnit der ikke kan gemmes må ikke koste resten af noten."""
    _skriv(tmp_path, "dream-session-2026-09-08-1131.md",
           "\n\n" + _LEKTIE + "\n\n" + ("Jeg lærte også noget andet her. " * 6) + "\n")
    with patch("core.services.local_small_model.spoerg_et_ord", return_value="LEKTIE"), \
         patch("core.runtime.db_lessons.upsert_lesson",
               side_effect=[RuntimeError("db væk"), {"outcome": "created"}]):
        tal = koer_hoest(mappe=tmp_path)["tal"]
    assert tal.get("fejl") == 1 and tal.get("created") == 1
