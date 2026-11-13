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


# ── Fire udfald, ikke ét: «applied: false» må ikke være en samlekasse ──────────
# (13/11-2026, Bjørns indvending) `landing` startede som «ingen sammenligning» og
# blev kun opdateret ved et fald. En kørsel der sammenlignede helt fint kunne
# derfor læses som om der slet ikke blev sammenlignet — samme fejlform som resten
# af dagen: en tekst der ikke beskriver hvad mekanismen faktisk gjorde.
def test_relational_skelner_sammenlignet_uden_fald_fra_intet_grundlag(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({"relational_days_seen": 132.0}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 132.5, "tone": "let", "reboot": False})
    ud = rel.record_relational()
    assert ud["landing"]["outcome"] == "sammenlignet_uden_fald", ud["landing"]
    assert ud["landing"]["forrige"] == 132.0 and ud["landing"]["nu"] == 132.5
    assert "ingen sammenligning" not in str(ud["landing"])


def test_relational_uden_tidligere_maaling_er_intet_grundlag(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 132.0, "tone": "let", "reboot": False})
    ud = rel.record_relational()
    assert ud["landing"]["outcome"] == "intet_grundlag", ud["landing"]
    assert ud["landing"]["applied"] is False


def test_relational_utilgaengelig_maaling_er_ikke_et_grundlag(monkeypatch, landet):
    """Kan varigheden ikke måles, er det hverken «intet grundlag» eller «fald»."""
    _kv(monkeypatch, FakeKV({"relational_days_seen": 132.0}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": None, "tone": "", "reboot": False})
    ud = rel.record_relational()
    assert ud["landing"]["outcome"] == "utilgaengelig", ud["landing"]
    assert not landet


def test_relational_fald_baerer_sit_eget_udfald(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({"relational_days_seen": 200.0}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 12.0, "tone": "let", "reboot": True})
    ud = rel.record_relational()
    assert ud["landing"]["outcome"] == "fald_registreret", ud["landing"]
    assert ud["landing"]["forrige"] == 200.0 and ud["landing"]["nu"] == 12.0


# ── Et fund må ikke forsvinde fordi handlingen fejlede ────────────────────────
# (13/11-2026, Bjørns anden indvending) Faldet blev opdaget, `land_decision` fejlede,
# og `_DAYS_KEY` blev ALLIGEVEL overskrevet med det lave tal. Næste kørsel
# sammenlignede to ens tal — så var der intet fald at se, og fundet var væk uden
# et varigt spor. Observationens historik må ikke afhænge af beslutningens status.
def test_relational_fund_overlever_at_landingen_fejler(monkeypatch):
    kv = _kv(monkeypatch, FakeKV({"relational_days_seen": 200.0}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 12.0, "tone": "let", "reboot": True})

    def raab(*a, **kw):
        raise RuntimeError("beslutnings-tabellen er låst")

    monkeypatch.setattr("core.services.central_consequence.land_decision", raab)
    foerste = rel.record_relational()

    # Fundet står som et fald — ikke som «sammenlignet uden fald»
    assert foerste["landing"]["outcome"] == "fald_registreret", foerste["landing"]
    assert foerste["landing"]["decision_applied"] is False
    assert "fejlede" in foerste["landing"]["reason"], foerste["landing"]

    # og sporet ligger der med sin oprindelige opdagelsestid
    pending = kv.get("relational_pending_fald")
    assert isinstance(pending, list) and len(pending) == 1, pending
    assert pending[0]["forrige"] == 200.0 and pending[0]["nu"] == 12.0, pending

    # Næste kørsel: alderen er nu stabil, så der er intet NYT fald at se.
    # Uden efterslæbet ville fundet her være forsvundet for evigt.
    kaldt: list[str] = []
    monkeypatch.setattr(
        "core.services.central_consequence.land_decision",
        lambda cid, d, **kw: (kaldt.append(d), {"applied": True, "decision_id": "dec_x"})[1],
    )
    anden = rel.record_relational()

    assert anden["efterslaeb"][0]["outcome"] == "efterslaeb_landet", anden["efterslaeb"]
    assert kaldt and "200.0" in kaldt[0] and "12.0" in kaldt[0], kaldt
    assert kv.get("relational_pending_fald") == [], "landet spor skal ryddes"


def test_relational_afvist_gate_bevarer_fundet(monkeypatch):
    """`land_decision` kan svare `applied: false` UDEN at fejle — fx når gaten er
    slukket. Afvigelsen er stadig opdaget, og de to svar må ikke blandes sammen."""
    kv = _kv(monkeypatch, FakeKV({"relational_days_seen": 200.0}))
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 12.0, "tone": "let", "reboot": True})
    monkeypatch.setattr("core.services.central_consequence.land_decision",
                        lambda cid, d, **kw: {"applied": False, "reason": "støj-veto"})
    ud = rel.record_relational()

    assert ud["landing"]["outcome"] == "fald_registreret", ud["landing"]
    assert ud["landing"]["decision_applied"] is False
    assert ud["landing"]["reason"] == "støj-veto"
    assert kv.get("relational_pending_fald")[0]["nu"] == 12.0


def test_relational_fejlet_kv_skrivning_ses_i_svaret(monkeypatch):
    """(13/11-2026, Bjørns tredje indvending) `_kv_set` slugte før fejlen med `pass`.
    Så kunne sporet forsvinde uden at nogen — eller svaret — vidste det. En test med
    en fungerende FakeKV beviser ikke at en fejlet skrivning opdages; derfor fejler
    skrivningen her bevidst, og svaret skal sige det."""
    kv = _kv(monkeypatch, FakeKV({"relational_days_seen": 200.0}))

    def _set(k, v, **kw):
        if k == "relational_pending_fald":
            raise RuntimeError("database is locked")
        kv.set(k, v)

    monkeypatch.setattr("core.runtime.db_core.set_runtime_state_value", _set)
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 12.0, "tone": "let", "reboot": True})
    monkeypatch.setattr("core.services.central_consequence.land_decision",
                        lambda cid, d, **kw: {"applied": False, "reason": "støj-veto"})
    ud = rel.record_relational()

    assert ud["landing"]["outcome"] == "fald_registreret", ud["landing"]
    assert ud["landing"]["spor_gemt"] is False, ud["landing"]
    assert "kunne ikke skrives" in ud["landing"]["spor_note"], ud["landing"]
    assert kv.get("relational_pending_fald") is None, "intet spor blev gemt"


def test_relational_sporet_er_gemt_foer_landingen_forsoeges(monkeypatch):
    """(13/11-2026, Bjørns tredje indvending) Før blev sporet skrevet EFTER et
    mislykket forsøg — så et crash midt i landingen tog fundet med sig. Her
    inspiceres KV'en inde FRA `land_decision`: på det tidspunkt skal sporet
    allerede ligge der."""
    kv = _kv(monkeypatch, FakeKV({"relational_days_seen": 200.0}))
    set_under_kald: list[list] = []

    def _fake(cid, d, **kw):
        set_under_kald.append(list(kv.get("relational_pending_fald") or []))
        return {"applied": True, "decision_id": "dec_x"}

    monkeypatch.setattr("core.services.central_consequence.land_decision", _fake)
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 12.0, "tone": "let", "reboot": True})
    rel.record_relational()

    assert set_under_kald, "land_decision blev slet ikke kaldt"
    assert len(set_under_kald[0]) == 1, f"sporet lå ikke der da handlingen blev forsøgt: {set_under_kald[0]}"
    assert set_under_kald[0][0]["nu"] == 12.0, set_under_kald[0]


def test_relational_to_fund_bevarer_hver_sit_tidspunkt(monkeypatch):
    """(13/11-2026, Bjørns tredje indvending) Med ÉT spor-objekt kunne fund B
    overskrive fund A og arve A's `opdaget_at` — så tidspunktet tilhørte én
    observation og indholdet en anden. To fald i træk skal give to poster med
    hver sin tid og hver sine tal."""
    kv = _kv(monkeypatch, FakeKV({"relational_days_seen": 200.0}))
    tider = iter(["2026-11-13T10:00:00+00:00", "2026-11-13T11:00:00+00:00"])
    monkeypatch.setattr(rel, "_now_iso", lambda: next(tider))
    monkeypatch.setattr("core.services.central_consequence.land_decision",
                        lambda cid, d, **kw: {"applied": False, "reason": "støj-veto"})

    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 12.0, "tone": "let", "reboot": True})
    rel.record_relational()

    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 3.0, "tone": "let", "reboot": True})
    rel.record_relational()

    liste = kv.get("relational_pending_fald")
    assert isinstance(liste, list) and len(liste) == 2, liste
    a, b = liste
    assert (a["forrige"], a["nu"], a["opdaget_at"]) == (200.0, 12.0, "2026-11-13T10:00:00+00:00"), a
    assert (b["forrige"], b["nu"], b["opdaget_at"]) == (12.0, 3.0, "2026-11-13T11:00:00+00:00"), b
    assert a["id"] != b["id"], "to fund skal ikke dele identitet"


def test_ghost_fund_overlever_at_landingen_fejler(monkeypatch):
    """Ghost har samme sårbarhed — men tidligere i forløbet: `update_profile()`
    overskriver fingeraftrykket FØR landingen. Fejler den, sammenligner næste
    kørsel den nye profil med sig selv og svarer «sammenlignet uden skift»."""
    kv = _kv(monkeypatch, FakeKV({}))
    monkeypatch.setattr(gh, "_recent_texts", lambda: ["noget tekst her"])
    monkeypatch.setattr(gh, "get_profile", lambda: dict(_PROFIL_ROLIG))
    monkeypatch.setattr(gh, "byg_profil", lambda t: dict(_PROFIL_SKIFTET))
    monkeypatch.setattr(gh, "klang_drift",
                        lambda a, b: {"drift_pct": 90.0, "baerende": "avg_sentence_len_exact",
                                      "akser": {"avg_sentence_len_exact": 90.0}})

    def raab(*a, **kw):
        raise RuntimeError("beslutnings-tabellen er låst")

    monkeypatch.setattr("core.services.central_consequence.land_decision", raab)
    foerste = gh.record_ghost()

    assert foerste["landing"]["outcome"] == "skift_registreret", foerste["landing"]
    assert foerste["landing"]["decision_applied"] is False
    pending = kv.get("ghost_pending_skift")
    assert isinstance(pending, list) and len(pending) == 1, pending
    assert pending[0]["drift_pct"] == 90.0, pending

    # Næste kørsel: profilen er allerede den nye, så drift er ~0.
    monkeypatch.setattr(gh, "get_profile", lambda: dict(_PROFIL_SKIFTET))
    monkeypatch.setattr(gh, "klang_drift",
                        lambda a, b: {"drift_pct": 0.0, "baerende": [], "akser": {}})
    kaldt: list[str] = []
    monkeypatch.setattr(
        "core.services.central_consequence.land_decision",
        lambda cid, d, **kw: (kaldt.append(d), {"applied": True, "decision_id": "dec_y"})[1],
    )
    anden = gh.record_ghost()

    assert anden["efterslaeb"][0]["outcome"] == "efterslaeb_landet", anden["efterslaeb"]
    assert kaldt and "90.0" in kaldt[0], kaldt
    assert kv.get("ghost_pending_skift") == [], "landet spor skal ryddes"


def test_ghost_profilen_gemmes_efter_fundet_er_registreret(monkeypatch):
    """(13/11-2026, Bjørns tredje indvending) `update_profile()` overskrev
    fingeraftrykket FØR et skift blev landet, så fundet kunne miste det grundlag
    det var målt imod. Nu skal sporet ligge i KV — og profilen stadig være den
    gamle — i det øjeblik handlingen forsøges."""
    kv = _kv(monkeypatch, FakeKV({}))
    set_under_kald: list[tuple[list, object]] = []

    def _fake(cid, d, **kw):
        set_under_kald.append((list(kv.get("ghost_pending_skift") or []),
                               kv.get("ghost_profile")))
        return {"applied": True, "decision_id": "dec_x"}

    monkeypatch.setattr("core.services.central_consequence.land_decision", _fake)
    monkeypatch.setattr(gh, "_recent_texts", lambda: ["noget tekst her"])
    monkeypatch.setattr(gh, "get_profile", lambda: dict(_PROFIL_ROLIG))
    monkeypatch.setattr(gh, "byg_profil", lambda t: dict(_PROFIL_SKIFTET))
    monkeypatch.setattr(gh, "klang_drift",
                        lambda a, b: {"drift_pct": 90.0, "baerende": "avg_sentence_len_exact",
                                      "akser": {"avg_sentence_len_exact": 90.0}})
    gh.record_ghost()

    assert set_under_kald, "land_decision blev slet ikke kaldt"
    spor, profil_under = set_under_kald[0]
    assert len(spor) == 1, f"sporet lå ikke der da handlingen blev forsøgt: {spor}"
    assert profil_under is None, "grundlaget blev overskrevet FØR fundet var registreret"


def test_ghost_skelner_sammenlignet_uden_skift_fra_intet_grundlag(monkeypatch, landet):
    """Samme fejlform i Ghost: et roligt fingeraftryk blev kaldt «ingen sammenligning»."""
    _kv(monkeypatch, FakeKV({}))
    monkeypatch.setattr(gh, "_recent_texts", lambda: ["kort tekst her", "endnu en kort tekst"])
    monkeypatch.setattr(gh, "get_profile", lambda: dict(_PROFIL_ROLIG))
    monkeypatch.setattr(gh, "update_profile", lambda t: dict(_PROFIL_ROLIG))
    monkeypatch.setattr(gh, "klang_drift", lambda a, b: {"drift_pct": 1.0, "baerende": [], "akser": {}})
    ud = gh.record_ghost()
    assert ud["landing"]["outcome"] == "sammenlignet_uden_skift", ud["landing"]
    assert not landet


def test_ghost_uden_profil_er_utilgaengelig(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({}))
    monkeypatch.setattr(gh, "_recent_texts", lambda: [])
    monkeypatch.setattr(gh, "get_profile", lambda: {})
    monkeypatch.setattr(gh, "update_profile", lambda t: {})
    monkeypatch.setattr(gh, "klang_drift", lambda a, b: None)
    ud = gh.record_ghost()
    assert ud["landing"]["outcome"] == "utilgaengelig", ud["landing"]
    assert not landet


def test_hilsenen_paastaar_ikke_utjekket_tillid(monkeypatch):
    """Der stod hardcodet: «Han stolede på mig før genstarten; det gør han stadig.»
    Intet i koden måler Bjørns tillid — påstanden stod på ingenting."""
    monkeypatch.setattr(rel, "relational_state",
                        lambda: {"days_together": 132.1, "tone": "let", "reboot": False})
    hilsen = rel.wake_greeting()
    assert "stolede" not in hilsen.lower(), hilsen
    assert "132" in hilsen, "varigheden skal stadig bære sætningen"


# ── Déjà Vu: tre udfald — kun det UVENTEDE tab er et fund ─────────────────────
def test_dejavu_forventet_afvisning_lander_ikke(monkeypatch, landet):
    """Bjørns fjerde indvending (13/11-2026): cadence har ingen autoritativ
    bruger-scope, så `scoped_recall_policy` afviser — korrekt, hver gang. Det er
    ikke blindhed, det er sikkerhed der virker. Den gamle regel gjorde den til en
    forpligtelse om at være defekt."""
    _kv(monkeypatch, FakeKV({"dejavu_uventet_streak": 9}))
    monkeypatch.setattr(dj, "surface_dejavu",
                        lambda **kw: {"fragment": None, "access": "denied"})
    ud = dj.record_dejavu()

    assert not landet, f"korrekt håndhævet sikkerhed må ikke lande: {landet}"
    assert ud["uventet_streak"] == 0
    assert "Dækningsbegrænsning" in ud["daekning"]
    assert "policyen virker" in ud["landing"]["reason"]


def test_dejavu_lander_naar_maaleevnen_uventet_forsvinder(monkeypatch, landet):
    """Den eneste tilstand der må lande: vi HAVDE lov at kigge og kunne ikke.
    «Må ikke» og «kan ikke» er forskellige svar, og kun det sidste er en fejl."""
    _kv(monkeypatch, FakeKV({"dejavu_uventet_streak": 2}))
    monkeypatch.setattr(dj, "surface_dejavu",
                        lambda **kw: {"fragment": None, "access": "error",
                                      "reason": "kandidatkilden fejlede: import"})
    ud = dj.record_dejavu()

    assert ud["uventet_streak"] == 3
    assert landet and landet[0]["cid"] == "dejavu"
    assert "kan ikke" in landet[0]["directive"].lower()


def test_dejavu_et_enkelt_uventet_tab_lander_ikke(monkeypatch, landet):
    _kv(monkeypatch, FakeKV({}))
    monkeypatch.setattr(dj, "surface_dejavu",
                        lambda **kw: {"fragment": None, "access": "error"})
    ud = dj.record_dejavu()
    assert ud["uventet_streak"] == 1
    assert not landet, f"et enkelt uventet tab er ikke strukturelt: {landet}"


def test_dejavu_nulstiller_naar_den_kunne_undersoeges(monkeypatch, landet):
    """Et fund — eller et ægte tomt resultat — bryder rækken."""
    kv = _kv(monkeypatch, FakeKV({"dejavu_uventet_streak": 5}))
    monkeypatch.setattr(dj, "surface_dejavu",
                        lambda **kw: {"fragment": None, "reason": "ingen resonans"})
    ud = dj.record_dejavu()
    assert ud["uventet_streak"] == 0 and kv.get("dejavu_uventet_streak") == 0
    assert not landet


def test_dejavu_kilde_fejl_er_ikke_et_tomt_fund(monkeypatch):
    """Kilden svarede `[]` både når den var tom og når den kastede. De to må ikke
    læses som det samme — det var præcis kollapsen et lag længere nede."""
    from core.runtime import db as dbmod

    def raab(**kw):
        raise RuntimeError("db nede")

    monkeypatch.setattr(dbmod, "get_experiential_memory_candidates", raab)
    monkeypatch.setattr(dj, "_present_context", lambda: "noget nu")

    cands = dj._candidates(limit=3)
    assert isinstance(cands, dj._UndersoegelseFejlede)
    assert dj.surface_dejavu()["access"] == "error"


# ── Continuity: modelgrænse vs. tomt grundlag ────────────────────────────────
def _fidelity(unmeasured, *, by_design=None, gap=None):
    """Spejler `measure_fidelity`s form — inkl. de to slags umålt (13/11-2026)."""
    return {"fidelity": 1.0, "lost": [], "same_content": 1.0, "drifted": [],
            "moved": [], "measured": 3, "unmeasured": list(unmeasured),
            "by_design": list(by_design or []),
            "unmeasured_gap": list(gap or [])}


def test_maaleevne_er_statisk_ikke_et_spoergsmaal_om_taalmodighed():
    """Forskellen kan afgøres uden at måle: den afhænger kun af om dimensionen HAR
    bærende felter. Derfor kan en `by_design`-dimension ikke blive målbar af at
    blive målt igen — og en række målinger er ikke et fund."""
    assert ch._maaleevne("attention") == ch._MAALEEVNE_BY_DESIGN
    assert ch._maaleevne("narrative") == ch._MAALEEVNE_TOMT_GRUNDLAG


def test_continuity_lander_ikke_paa_en_dimension_der_er_umaalbar_efter_design(monkeypatch, landet):
    """`attention` har ingen bærende felter og kan ALDRIG måles på identitetsaksen.
    At tælle gentagelser gør ikke en grænse i MÅLEMODELLEN til et fund; det gør en
    fungerende model til en defekt. Målt i basen: den gamle regel oprettede
    `dec_835cc0115cac` om netop dette."""
    _kv(monkeypatch, FakeKV({"continuity_unmeasured_streak":
                             {"dims": ["attention"], "streak": 9}}))
    monkeypatch.setattr(ch, "measure_fidelity",
                        lambda: _fidelity(["attention"], by_design=["attention"]))
    monkeypatch.setattr(ch, "capture_snapshot", lambda: {"captured": False})
    ud = ch.run_continuity_healer()

    assert not landet, f"en modelgrænse må ikke blive en bindende beslutning: {landet}"
    assert ud["by_design"] == ["attention"]
    assert ud["unmeasured_gap"] == []
    assert "grænse i målemodellen" in ud["begraensning"]


def test_continuity_lander_paa_et_tomt_grundlag(monkeypatch, landet):
    """Den ANDEN slags umålt: dimensionen er målbar i princippet, men grundlaget var
    tomt. Det kan være reel blindhed — og det er den eneste der må lande."""
    _kv(monkeypatch, FakeKV({"continuity_unmeasured_streak":
                             {"dims": ["narrative"], "streak": 2}}))
    monkeypatch.setattr(ch, "measure_fidelity",
                        lambda: _fidelity(["narrative"], gap=["narrative"]))
    monkeypatch.setattr(ch, "capture_snapshot", lambda: {"captured": False})
    ud = ch.run_continuity_healer()

    assert landet and landet[0]["cid"] == "continuity_healer"
    assert "narrative" in landet[0]["directive"]
    assert "grundlaget" in landet[0]["directive"]
    assert ud["unmeasured"] == ["narrative"]


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
