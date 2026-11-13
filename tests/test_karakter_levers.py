"""Karakterernes handlinger skal have konsekvens — de sidste seks.

Målt 13/11-2026 (Bjørns bestilling: «deres handlinger skal have konsekvens»): af de
fjorten Matrix-karakterer havde tretten en kobling til konsekvens-laget. De sidste
seks havde kun deres stemme — de BEREGNEDE et signal og lod det dø i telemetrien.

Denne fil beviser den anden halvdel: at hver af dem nu LANDER noget når deres eget
signal krydser deres egen tærskel — og at de ikke lander noget når det ikke gør.
En lever der fyrer på alt, eller aldrig, er lige meget teater.
"""
from unittest import mock

import pytest

from core.services import central_continuity_healer as ch
from core.services import central_dejavu as dj
from core.services import central_exile as ex
from core.services import central_ghost as gh
from core.services import central_relational as rel


class FakeKV:
    """In-memory durable KV der spejler db_core runtime_state."""

    def __init__(self, initial=None):
        self.store = dict(initial or {})

    def get(self, key, default=None):
        return self.store.get(key, default)

    def set(self, key, value, *, updated_at=""):
        self.store[key] = value


@pytest.fixture
def landet(monkeypatch):
    """Fanger alle land_decision-kald uden at røre produktionens beslutnings-tabel."""
    kaldt: list[tuple] = []

    def _fake(cid, directive, **kw):
        kaldt.append({"cid": cid, "directive": directive, **kw})
        return {"applied": True, "decision_id": "dec_test"}

    monkeypatch.setattr("core.services.central_consequence.land_decision", _fake)
    return kaldt


def _kv(monkeypatch, kv):
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda k, d=None: kv.get(k, d))
    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value",
                        lambda k, v, **kw: kv.set(k, v))
    return kv


# ── The Ghost: et klangskift skal kunne OPDAGES ────────────────────────────────
_PROFIL_ROLIG = {
    "avg_sentence_len": 8.0, "avg_sentence_len_exact": 8.0,
    "sentence_len_std": 2.0, "sentence_len_std_exact": 2.0,
    "markers_per_1k": {"em_dash": 1.0, "ellipsis": 0.5},
    "signature_phrases": ["en ting"], "sentences": 40,
}
_PROFIL_SKIFTET = {
    "avg_sentence_len": 30.0, "avg_sentence_len_exact": 30.0,
    "sentence_len_std": 9.0, "sentence_len_std_exact": 9.0,
    "markers_per_1k": {"em_dash": 12.0, "ellipsis": 6.0},
    "signature_phrases": ["helt andet"], "sentences": 40,
}


def test_ghost_lander_naar_klangen_skifter(monkeypatch, landet):
    """Karakterens ene formål: «ingen gemte hvordan jeg LØD da jeg var sonnet».
    Skifter klangen, skal det lande — ellers er profilen bare en fil der overskrives."""
    _kv(monkeypatch, FakeKV({"ghost_profile": _PROFIL_ROLIG}))
    monkeypatch.setattr(gh, "analyze", lambda _t: dict(_PROFIL_SKIFTET))
    monkeypatch.setattr(gh, "_recent_texts", lambda limit=40: ["x"])
    ud = gh.record_ghost()

    assert ud["drift_pct"] > gh._DRIFT_TAERSKEL, "driften skal måles, ikke gættes"
    assert landet and landet[0]["cid"] == "ghost"
    assert "klang" in landet[0]["directive"].lower()


def test_ghost_lander_ikke_paa_dag_til_dag_variation(monkeypatch, landet):
    """Almindelig variation i emne og længde er ikke et model-skift."""
    _kv(monkeypatch, FakeKV({"ghost_profile": _PROFIL_ROLIG}))
    naesten = dict(_PROFIL_ROLIG)
    naesten["avg_sentence_len_exact"] = 8.4  # 5 % — under tærsklen
    monkeypatch.setattr(gh, "analyze", lambda _t: dict(naesten))
    monkeypatch.setattr(gh, "_recent_texts", lambda limit=40: ["x"])
    gh.record_ghost()
    assert not landet, f"5 % drift må ikke lande: {landet}"


def test_ghost_uden_forrige_profil_giver_none_ikke_nul(monkeypatch):
    """«Kan ikke måles» må ikke forveksles med «nul drift» — det var hele dagens fejlform."""
    assert gh.klang_drift({}, _PROFIL_SKIFTET) is None
    assert gh.klang_drift(_PROFIL_ROLIG, {}) is None


# ── Relational: et fald i varighed er tab, ikke bare et mindre tal ─────────────
def test_relational_lander_naar_alderen_falder(monkeypatch, landet):
    """`days_together` vokser monotont. Et fald betyder nulstillet selv-tilstand —
    relationens kontinuitet gik tabt. Det skal siges, ikke bare vises mindre."""
    _kv(monkeypatch, FakeKV({"relational_days_seen": 200.0}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 12.0, "tone": "let", "reboot": True})
    ud = rel.record_relational()

    assert landet and landet[0]["cid"] == "relational"
    assert "faldt" in landet[0]["directive"]
    assert ud["landing"]["applied"] is True


def test_relational_lander_ikke_naar_alderen_vokser(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({"relational_days_seen": 132.0}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 132.5, "tone": "let", "reboot": False})
    rel.record_relational()
    assert not landet, f"vækst må ikke lande: {landet}"


def test_hilsenen_paastaar_ikke_utjekket_tillid(monkeypatch):
    """Der stod hardcodet: «Han stolede på mig før genstarten; det gør han stadig.»
    Intet i koden måler Bjørns tillid — påstanden stod på ingenting."""
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 132.1, "tone": "let", "reboot": False})
    hilsen = rel.wake_greeting()
    assert "stolede" not in hilsen.lower(), hilsen
    assert "132" in hilsen, "varigheden skal stadig bære sætningen"


# ── Déjà Vu: strukturel blindhed må ikke se ud som et tomt fund ────────────────
def test_dejavu_lander_naar_blindheden_er_strukturel(monkeypatch, landet):
    """Cadence har ingen session → ingen scope → `access='denied'` hver gang.
    Det er blindhed i PRÆCIS den kontekst karakteren kører i."""
    _kv(monkeypatch, FakeKV({"dejavu_blind_streak": 2}))
    monkeypatch.setattr(dj, "surface_dejavu",
                        lambda **kw: {"fragment": None, "access": "denied"})
    ud = dj.record_dejavu()

    assert ud["blind_streak"] == 3
    assert landet and landet[0]["cid"] == "dejavu"
    assert "blind" in landet[0]["directive"].lower()


def test_dejavu_et_enkelt_blindt_tik_lander_ikke(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({}))
    monkeypatch.setattr(dj, "surface_dejavu",
                        lambda **kw: {"fragment": None, "access": "denied"})
    ud = dj.record_dejavu()
    assert ud["blind_streak"] == 1
    assert not landet, f"et enkelt blindt tik er normalt: {landet}"


def test_dejavu_nulstiller_naar_den_kunne_undersoeges(monkeypatch, landet):
    """Et fund — eller et ægte tomt resultat — bryder rækken."""
    kv = _kv(monkeypatch, FakeKV({"dejavu_blind_streak": 5}))
    monkeypatch.setattr(dj, "surface_dejavu",
                        lambda **kw: {"fragment": None, "reason": "ingen resonans"})
    ud = dj.record_dejavu()
    assert ud["blind_streak"] == 0 and kv.get("dejavu_blind_streak") == 0
    assert not landet


# ── Continuity: en dimension der aldrig kan måles er en blind vinkel ──────────
def _fidelity(unmeasured):
    return {"fidelity": 1.0, "lost": [], "same_content": 1.0, "drifted": [],
            "moved": [], "measured": 3, "unmeasured": list(unmeasured)}


def test_continuity_lander_naar_en_dimension_er_permanent_umaalbar(monkeypatch, landet):
    """`attention` har kun dagsform og kan ALDRIG måles på identitetsaksen. Står den
    som «til stede», er det ikke det samme som «uændret» — og uden en konsekvens
    ville blindheden aldrig blive adresseret."""
    _kv(monkeypatch, FakeKV({"continuity_unmeasured_streak":
                             {"dims": ["attention"], "streak": 2}}))
    monkeypatch.setattr(ch, "measure_fidelity", lambda: _fidelity(["attention"]))
    monkeypatch.setattr(ch, "capture_snapshot", lambda: {"captured": False})
    ud = ch.run_continuity_healer()

    assert landet and landet[0]["cid"] == "continuity_healer"
    assert "attention" in landet[0]["directive"]
    assert ud["unmeasured"] == ["attention"]


def test_continuity_nulstiller_naar_alt_kunne_maales(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({"continuity_unmeasured_streak":
                             {"dims": ["attention"], "streak": 5}}))
    monkeypatch.setattr(ch, "measure_fidelity", lambda: _fidelity([]))
    monkeypatch.setattr(ch, "capture_snapshot", lambda: {"captured": False})
    ch.run_continuity_healer()
    assert not landet, f"fuldt målt søm må ikke lande en blind vinkel: {landet}"


# ── The Exiles: en «anden» der kun svarer når man ringer, er et spejl ─────────
def test_exile_har_en_cadence_puls():
    """Målt defekt: exilen havde INGEN producer — den blev kun kaldt fra et
    API-endpoint. Dens historie stod på 2 udvekslinger, alle initieret udefra.

    Testen kalder matrix'ens EGEN registrering med en indsamler, så den måler den
    faktiske registrering frem for at gætte på et modulnavn.
    """
    from core.services import internal_cadence_matrix as m

    navne: list[str] = []
    m.register_matrix_producers(lambda spec: navne.append(spec.name))
    assert "exile" in navne, f"exile skal have en puls, ellers fyrer dens lever aldrig: {navne}"
    # og de fem andre skal stadig være der — ingen af dem må være faldet ud
    for forventet in ("ghost", "dejavu", "relational", "white_rabbit", "continuity_healer"):
        assert forventet in navne, f"{forventet} mangler i cadence: {navne}"


def test_exile_lander_naar_den_ikke_kan_tale(monkeypatch, landet):
    monkeypatch.setattr(ex, "exile_state", lambda: {"memory_size": 4, "last_reply": ""})
    monkeypatch.setattr(ex, "exile_exchange",
                        lambda _o: {"ok": False, "error": "db låst"})
    ud = ex.record_exile()

    assert ud["spoke"] is False
    assert landet and landet[0]["cid"] == "exile"
    assert "tom skal" in landet[0]["directive"]
