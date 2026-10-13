"""Sessionen doebes efter sin foerste brugerbesked — ogsaa kode-sessioner.

Fejlen, fundet 16/9-2026: pladsholder-saettet indeholdt «kode session» med
MELLEMRUM, mens desk opretter sessionen som «Kode-session» med BINDESTREG. Ét
tegn, og omdoebningen fyrede aldrig. Tolv kode-sessioner stod som
«Kode-session» med foerste beskeder som «Godmorgen» og «Er du der?» der aldrig
blev brugt.

Testen maaler stavemaaderne, fordi det var praecis dér fejlen laa.
"""
import pytest

from core.services.chat_sessions import _er_pladsholder


@pytest.mark.parametrize("titel", [
    "Kode-session",      # desk (bindestreg) — DEN der fejlede
    "kode-session",
    "Kode session",      # mellemrum
    "kode_session",      # understreg
    "Kode  Session",     # dobbelt mellemrum
    "  Ny samtale  ",
    "New Chat",
    "Ny chat",
    "untitled",
    "uden titel",
    "",
    "   ",
])
def test_pladsholdere_kan_omdoebes(titel):
    assert _er_pladsholder(titel) is True, f"{titel!r} burde kunne omdoebes"


@pytest.mark.parametrize("titel", [
    "Godmorgen ven",
    "Kode-session om broen",          # brugerens EGET navn der ligner en pladsholder
    "Autonom · Hjerteslag · 04:00",   # maskin-titel MED betydning
    "💭 Proaktive spoergsmaal",
    "Ny samtale om pumpen",
])
def test_rigtige_navne_roeres_ALDRIG(titel):
    # Har brugeren selv navngivet sessionen — eller baerer den en maskin-titel
    # med betydning — skal den staa. En omdoebning her ville slette et valg.
    assert _er_pladsholder(titel) is False, f"{titel!r} er ikke en pladsholder"


def test_BEGGE_listninger_sender_projektet_med():
    """Listningen har TO forespoergsler — med og uden bruger-id.

    Foerste rettelse ramte kun den ene, og kaldet uden bruger-id svarede
    videre uden `workspace_root`. Listen saa tom ud paa praecis det felt der
    var hele pointen med aendringen, og intet fejlede.

    Der maales paa SQL'en, fordi det er dér de to kan drive fra hinanden.
    """
    from pathlib import Path
    kilde = Path("core/services/chat_sessions.py").read_text(encoding="utf-8")
    start = kilde.index("def list_chat_sessions(")
    slut = kilde.index("\ndef ", start + 10)
    krop = kilde[start:slut]
    assert krop.count("FROM chat_sessions s") == 2, "antallet af forespoergsler har aendret sig"
    assert krop.count("s.workspace_root") == 2, "kun den ene forespoergsel sender projektet med"


# ── Titling-sweepet (13/10-2026) ────────────────────────────────────────────
# Titlen blev sat til den RÅ første besked, klippet ved 48 tegn. Sidebaren
# hed «hey», «yo», «Godmorgen» — 608 sessioner, målt. Sweepet må KUN røre den
# klasse. Rammer det et rigtigt navn, sletter det et valg.


@pytest.mark.parametrize("titel", [
    "hey", "Hey", "HEY!",
    "yo", "Yo...",
    "Godmorgen", "godaften",
    "hey j..",            # den klippede hale fra skaermbilledet
    "hej du",
    "Er du der?",
    "New chat",           # pladsholder
    "Kode-session",
])
def test_ubrugelige_titler_maa_omdoebes(titel):
    from core.services.session_titling import er_ubrugelig_titel
    assert er_ubrugelig_titel(titel) is True, f"{titel!r} burde kunne navngives"


@pytest.mark.parametrize("titel", [
    "Autonom · Drømme · 2026-10-13",     # maskin-titel MED betydning
    "Autonom · Hjerteslag · 04:00",
    "Discord DM — 1246415163603816499",
    "WAL-checkpoint og journal_size_limit",
    "hvornår ser systemerne ud idag? pve 10.0.0.2",
    # En RIGTIG saetning der tilfaeldigt starter med en hilsen er en titel.
    # Uden laengde-graensen ville den blive klippet ned til en hilsen.
    "hej, hvad er status på pve-værten?",
])
def test_rigtige_titler_roeres_ALDRIG_af_sweepet(titel):
    from core.services.session_titling import er_ubrugelig_titel
    assert er_ubrugelig_titel(titel) is False, f"{titel!r} er ikke en hilsen"


@pytest.mark.parametrize("raa,forventet", [
    ('"Systemstatus for pve"', "Systemstatus for pve"),
    ("Titel: WAL-checkpoint", "WAL-checkpoint"),
    ("  To ord  ", "To ord"),
    ("Punktum til sidst.", "Punktum til sidst"),
    # En hel saetning er ikke en titel — hellere ingen end en forkert.
    ("Dette er en meget lang forklaring på hvad samtalen handlede om og hvorfor", ""),
    ("", ""),
])
def test_modellens_svar_renses_til_en_titel(raa, forventet):
    from core.services.session_titling import _rens_titel
    assert _rens_titel(raa) == forventet


def test_sweepet_feiler_aldrig_hoejt():
    """Det koerer fra heartbeat-stien. En tom ko er ikke en fejl."""
    from core.services import session_titling
    kaldt = {"n": 0}

    def _tom(*a, **k):
        kaldt["n"] += 1
        return []

    oprindelig = session_titling._kandidater
    session_titling._kandidater = _tom
    try:
        svar = session_titling.sweep()
    finally:
        session_titling._kandidater = oprindelig
    assert svar["status"] == "ok"
    assert svar["omdoebt"] == []
    assert kaldt["n"] == 1


# ── Ollama-lanen foerst (Bjørn, 13/10-2026) ─────────────────────────────────
# Målt på de samme fem kandidater skrev ollama-lanen kortere og mere præcist
# dansk end billig-lanens «default»-tier. Rækkefølgen er hele pointen, og den
# skal derfor måles — ikke bare stå i en kommentar.


def test_generer_titel_bruger_ollama_lanen_foerst(monkeypatch):
    """Svarer ollama-lanen, må billig-lanen ALDRIG kaldes."""
    from core.services import session_titling
    import core.services.non_visible_lane_execution as nvle

    monkeypatch.setattr(
        session_titling, "_ollama_lane_titel", lambda _s: "CI-fejl og broen nede"
    )

    def _forbudt(*_a, **_k):
        raise AssertionError("billig-lanen blev kaldt selv om ollama svarede")

    monkeypatch.setattr(nvle, "execute_cheap_lane", _forbudt)
    assert session_titling.generer_titel("Bjørn: hej\nJarvis: hej") == "CI-fejl og broen nede"


def test_generer_titel_falder_til_billig_lanen(monkeypatch):
    """Tomt ollama-svar = lanen svarede ikke. Så overtager billig-lanen."""
    from core.services import session_titling
    import core.services.non_visible_lane_execution as nvle

    monkeypatch.setattr(session_titling, "_ollama_lane_titel", lambda _s: "")
    monkeypatch.setattr(
        nvle, "execute_cheap_lane", lambda **_k: {"text": "WAL og journal_size_limit"}
    )
    assert session_titling.generer_titel("Bjørn: hej") == "WAL og journal_size_limit"


def test_ollama_lanen_naegter_en_fremmed_udbyder(monkeypatch):
    """Peger local-lanen ikke på ollama, sender vi ikke til den alligevel."""
    from core.services import session_titling
    import core.runtime.provider_router as pr

    monkeypatch.setattr(
        pr,
        "resolve_provider_router_target",
        lambda **_k: {"provider": "openai", "model": "gpt", "base_url": "http://x"},
    )
    assert session_titling._ollama_lane_titel("Bjørn: hej") == ""


def test_tom_samtale_koster_intet_kald(monkeypatch):
    """En session uden læsbart materiale må ikke give et modelkald."""
    from core.services import session_titling

    def _forbudt(*_a, **_k):
        raise AssertionError("tom samtale gav et modelkald")

    monkeypatch.setattr(session_titling, "_ollama_lane_titel", _forbudt)
    assert session_titling.generer_titel("   ") == ""
