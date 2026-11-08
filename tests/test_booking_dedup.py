"""Tests for booking_dedup — «er dette allerede booket?».

Anledningen (målt 8/11-2026): to opfølgningsopgaver til samme dato om samme
sag, oprettet 17 minutter fra hinanden, fordi hver booking-vej skrev uden at
læse først. Testene her dækker de grænser der kan gå galt i praksis: for grov
normalisering, for bredt vindue, og sammenlægning på tværs af samtaler.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services.booking_dedup import (
    DUBLET_VINDUE_MINUTTER,
    find_dublet,
    noegle,
    til_tid,
)

NU = datetime(2026, 11, 8, 19, 0, tzinfo=UTC)


def _post(tekst: str, tid: datetime, session: str = "s1") -> dict:
    return {"focus": tekst, "run_at": tid.isoformat(), "session_id": session}


# ── normalisering ────────────────────────────────────────────────────────────


def test_noegle_fjerner_form_men_beholder_indhold():
    assert noegle("RYKKER: GDPR!") == noegle("rykker gdpr")
    assert noegle("  Tjek   deploy  ") == "tjek deploy"


def test_noegle_af_tom_tekst_er_tom():
    assert noegle("") == ""
    assert noegle("   !!!   ") == ""


def test_noegle_skelner_forskelligt_indhold():
    assert noegle("tjek deploy") != noegle("tjek mail")


# ── tids-parsing ─────────────────────────────────────────────────────────────


def test_til_tid_laeser_iso_og_goer_den_tidszonebevidst():
    assert til_tid("2026-11-08T19:00:00Z") == NU
    assert til_tid("2026-11-08T19:00:00").tzinfo is not None


def test_til_tid_afviser_skrald_uden_at_rejse():
    assert til_tid("ikke en dato") is None
    assert til_tid(None) is None
    assert til_tid("") is None


# ── dublet-fundet ────────────────────────────────────────────────────────────


def test_samme_tekst_og_taet_paa_tid_er_en_dublet():
    eksisterende = [_post("Rykker til selskabsinfo", NU)]
    hit = find_dublet(
        tekst="rykker til Selskabsinfo!",
        tid=NU + timedelta(minutes=17),
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="s1",
    )
    assert hit is eksisterende[0]


def test_samme_tekst_langt_fra_i_tid_er_ikke_en_dublet():
    """To bevidste kontrolpunkter må ikke slås sammen."""
    eksisterende = [_post("tjek deploy", NU)]
    hit = find_dublet(
        tekst="tjek deploy",
        tid=NU + timedelta(hours=3),
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="s1",
    )
    assert hit is None


def test_forskellig_tekst_paa_samme_tid_er_ikke_en_dublet():
    eksisterende = [_post("tjek deploy", NU)]
    hit = find_dublet(
        tekst="tjek mail",
        tid=NU,
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="s1",
    )
    assert hit is None


def test_vinduet_er_inkluderende_paa_graensen():
    eksisterende = [_post("tjek deploy", NU)]
    praecis = NU + timedelta(minutes=DUBLET_VINDUE_MINUTTER)
    over = NU + timedelta(minutes=DUBLET_VINDUE_MINUTTER, seconds=1)
    fælles = dict(
        tekst="tjek deploy",
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="s1",
    )
    assert find_dublet(tid=praecis, **fælles) is eksisterende[0]
    assert find_dublet(tid=over, **fælles) is None


# ── samtale-skellet ──────────────────────────────────────────────────────────


def test_to_samtaler_der_bestiller_det_samme_er_to_forpligtelser():
    """Målt 8/11-2026: uden dette skel forsvandt en booking i tavshed."""
    eksisterende = [_post("tjek deploy", NU, session="a")]
    hit = find_dublet(
        tekst="tjek deploy",
        tid=NU,
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="b",
    )
    assert hit is None


def test_samme_samtale_rammer_stadig():
    eksisterende = [_post("tjek deploy", NU, session="a")]
    hit = find_dublet(
        tekst="tjek deploy",
        tid=NU,
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="a",
    )
    assert hit is eksisterende[0]


def test_session_none_sammenligner_ikke_paa_samtale():
    eksisterende = [_post("tjek deploy", NU, session="a")]
    hit = find_dublet(
        tekst="tjek deploy",
        tid=NU,
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session=None,
    )
    assert hit is eksisterende[0]


# ── «ved det ikke» må ikke blive et falsk hit ────────────────────────────────


def test_manglende_tid_paa_den_nye_giver_ingen_dublet():
    eksisterende = [_post("tjek deploy", NU)]
    hit = find_dublet(
        tekst="tjek deploy",
        tid=None,
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="s1",
    )
    assert hit is None


def test_manglende_tid_paa_den_gamle_giver_ingen_dublet():
    eksisterende = [{"focus": "tjek deploy", "run_at": None, "session_id": "s1"}]
    hit = find_dublet(
        tekst="tjek deploy",
        tid=NU,
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="s1",
    )
    assert hit is None


def test_tom_tekst_giver_ingen_dublet():
    eksisterende = [_post("", NU)]
    hit = find_dublet(
        tekst="",
        tid=NU,
        eksisterende=eksisterende,
        tekst_felt="focus",
        tid_felt="run_at",
        session="s1",
    )
    assert hit is None


def test_tom_liste_giver_ingen_dublet():
    assert (
        find_dublet(
            tekst="tjek deploy",
            tid=NU,
            eksisterende=[],
            tekst_felt="focus",
            tid_felt="run_at",
            session="s1",
        )
        is None
    )
