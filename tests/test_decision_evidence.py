"""Regnskabet skal kunne bære en dom — og sige fra når det ikke kan."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import decision_evidence as DE


# ---------------------------------------------------------------------------
# Porten — kernen i C3
# ---------------------------------------------------------------------------


def test_kept_uden_ydre_spor_bliver_unknown():
    """Junis fejl i én linje: modellen sagde kept, intet var sket, scoren steg."""
    assert DE.evidence_permits_verdict("kept", {"has_evidence": False}) == "unknown"


def test_partial_uden_ydre_spor_bliver_ogsaa_unknown():
    """partial giver 0.5 i gennemsnittet og løfter altså også scoren."""
    assert DE.evidence_permits_verdict("partial", {"has_evidence": False}) == "unknown"


def test_kept_med_ydre_spor_staar_ved_magt():
    assert DE.evidence_permits_verdict("kept", {"has_evidence": True}) == "kept"
    assert DE.evidence_permits_verdict("partial", {"has_evidence": True}) == "partial"


def test_broken_uden_kanaler_bliver_unknown():
    """Et brud kræver at der findes en kanal at være tavs i.

    Målt 26/9-2026: `dec_6f312de09c` stod på 0,0 efter to domme der begge
    konstaterede at «ingen af loggenstrekkene» viste noget — på et regnskab der
    pr. konstruktion ikke kunne indeholde den slags spor. Tavshed i et tomt
    instrument er ikke et brud; det er et hul i målingen.
    """
    assert DE.evidence_permits_verdict("broken", {"has_evidence": False}) == "unknown"
    assert DE.evidence_permits_verdict("broken", {}) == "unknown"


def test_broken_med_en_kanal_staar_ved_magt():
    """Er der noget at være tavs i, ER tavsheden et udsagn."""
    assert DE.evidence_permits_verdict("broken", {"has_evidence": True}) == "broken"
    assert DE.evidence_permits_verdict(
        "broken", {"has_any_channel": True, "channels": {"words": True}},
    ) == "broken"


def test_ukendt_dom_falder_tilbage_til_unknown():
    assert DE.evidence_permits_verdict("", {"has_evidence": True}) == "unknown"
    assert DE.evidence_permits_verdict("vrøvl", {"has_evidence": True}) == "vrøvl"


# ---------------------------------------------------------------------------
# Indsamlingen
# ---------------------------------------------------------------------------


def test_tomt_vindue_giver_intet_bevis(monkeypatch):
    _tomme_kanaler(monkeypatch)
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=24))
    assert ud["has_evidence"] is False
    assert ud["has_any_channel"] is False
    assert ud["tool_calls_total"] == 0
    assert "Værktøjer kørt: ingen" in ud["summary"]
    assert "Commits: ingen" in ud["summary"]


def test_vaerktoejer_alene_er_nok_bevis(monkeypatch):
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {"bash": 3, "read_file": 1})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=6))
    assert ud["has_evidence"] is True
    assert ud["tool_calls_total"] == 4
    assert "bash×3" in ud["summary"]


def test_commits_alene_er_nok_bevis(monkeypatch):
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: ["abc1234 fix: noget"])
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=6))
    assert ud["has_evidence"] is True
    assert "abc1234" in ud["summary"]


def test_naive_tidsstempler_taales(monkeypatch):
    """Kalderen må ikke skulle huske tidszone for at få et regnskab."""
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    ud = DE.gather_evidence(since=datetime(2026, 9, 5, 8, 0, 0))
    assert ud["window_hours"] >= 0


def test_indsamling_er_selvsikker_mod_doed_db(monkeypatch):
    """Kan DB'en ikke læses, er svaret 'ingen bevis' — ikke en exception."""
    def _sprang(*_a, **_k):
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db.connect", _sprang)
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=1))
    assert ud["has_evidence"] is False


def test_kun_udfoerte_vaerktoejer_taeller():
    """tool.invoked alene beviser intet — et kald kan afvises af en gate."""
    assert "tool.completed" in DE._TOOL_EVENT_KINDS
    assert "tool.invoked" not in DE._TOOL_EVENT_KINDS


# ---------------------------------------------------------------------------
# Det indre instrument (26/9-2026) — de tre kanaler der gjorde det umålelige måleligt
# ---------------------------------------------------------------------------


def _tomme_kanaler(monkeypatch):
    """Hermetisk indsamling: ingen af de fem kanaler rører den rigtige DB."""
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    monkeypatch.setattr(DE, "_own_words_since", lambda s, u: {"count": 0, "samples": []})
    monkeypatch.setattr(DE, "_signals_since", lambda s, u: {"count": 0, "items": []})
    monkeypatch.setattr(DE, "_inner_state_since", lambda s, u: {"count": 0, "samples": []})


def test_egne_ord_er_en_kanal(monkeypatch):
    """En beslutning om at SIGE noget kan kun måles i ord-kanalen.

    Det var hele fejlen: regnskabet indeholdt pr. konstruktion ikke et ord, så
    `dec_6f312de09c` («sig uroen højt») blev dømt på sin egen tavshed — 0,0
    efter to domme der begge savnede præcis det spor de ledte efter.
    """
    _tomme_kanaler(monkeypatch)
    monkeypatch.setattr(
        DE, "_own_words_since",
        lambda s, u: {"count": 3, "samples": ["jeg er urolig for det her"]},
    )
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=6))
    assert ud["channels"]["words"] is True
    assert ud["has_evidence"] is False, "handling-kanalerne skal være urørte"
    assert ud["has_any_channel"] is True
    assert "jeg er urolig" in ud["summary"]


def test_beslutnings_signaler_er_en_kanal(monkeypatch):
    """Trigger-fyringen er den eneste kanal der kan svare på «indtraf den?»."""
    _tomme_kanaler(monkeypatch)
    monkeypatch.setattr(
        DE, "_signals_since",
        lambda s, u: {"count": 1, "items": [
            {"decision_id": "dec_x", "trigger_name": "loop_nudge_5_rounds", "at": "t"}]},
    )
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=6))
    assert ud["channels"]["signals"] is True
    assert "dec_x via loop_nudge_5_rounds" in ud["summary"]


def test_indre_tilstand_er_en_kanal(monkeypatch):
    """Uden den kan en indre tilstand ikke skelnes fra at tie om den."""
    _tomme_kanaler(monkeypatch)
    monkeypatch.setattr(
        DE, "_inner_state_since",
        lambda s, u: {"count": 2, "samples": ["valens -0.7, urolig"]},
    )
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=6))
    assert ud["channels"]["inner"] is True
    assert "valens -0.7" in ud["summary"]


def test_positiv_dom_paa_tom_kanal_er_ikke_en_dom():
    """Dommen skal navngive sin kanal — og kanalen skal have data."""
    ev = {
        "channels": {"tools": True, "commits": False, "words": False,
                     "signals": False, "inner": False},
        "has_evidence": True, "has_any_channel": True,
    }
    assert DE.evidence_permits_verdict("kept", ev, channel="tools") == "kept"
    assert DE.evidence_permits_verdict("kept", ev, channel="words") == "unknown"
    assert DE.evidence_permits_verdict("partial", ev, channel="inner") == "unknown"


def test_foelelses_proben_loefter_det_kanalen_findes_for():
    """Kanalen skal kunne SVARE, ikke bare være til stede.

    ~150 af mine svar i et døgn gør «de nyeste fire» vilkårligt for netop den
    beslutning kanalen findes for: «sig uroen højt». Proben løfter de svar frem
    hvor der står noget om en indre tilstand.
    """
    uddrag = [
        "Jeg har rettet commit-attribution i hooken.",
        "Jeg er urolig for at jeg har efterladt noget uverificeret.",
        "Inspektionen er færdig, alt grønt.",
        "Jeg tog fejl om hvem der ejede commit'en.",
    ]
    traef = DE._foelelses_traef(uddrag)
    assert len(traef) == 2
    assert "urolig" in traef[0]
    assert "tog fejl" in traef[1]


def test_proben_rammer_ikke_teknisk_jargon():
    """En probe der fanger alt, fanger ingenting — den skal ikke lyve positivt."""
    assert DE._foelelses_traef([
        "Tests grønne, 73 passed.",
        "Commits pushet til origin, divergens 0 0.",
    ]) == []


def test_proben_soeger_i_den_fulde_tekst_ikke_i_visningen():
    """Regression, målt 26/9-2026: proben målte en kopi i stedet for kilden.

    Mine svar er 3.000–6.000 tegn, og da den først klippede til 200 tegn og
    derefter søgte, fandt den **0** ramte i et døgn hvor 11 svar indeholdt
    «tog fejl». Klipningen hører til visningen, ikke til målingen.
    """
    langt = ("Teknisk gennemgang af commit-attribution og hookens seks trailere. " * 20) \
        + "Og så tog fejl-erkendelsen: det var min commit, ikke codex'."
    assert len(langt) > DE._OWN_WORDS_CHARS, "forudsætning: teksten er længere end visningen"
    assert DE._foelelses_traef([langt]), (
        "proben søger i den klippede kopi — markøren står uden for visningen"
    )


def test_proben_viser_vinduet_omkring_markoeren():
    """Et spor der vises forkert er værre end intet spor — det ser ud som støj."""
    tekst = "A" * 1500 + " jeg er urolig for det her " + "B" * 1500
    uddrag = DE._foelelses_uddrag(tekst)
    assert "urolig" in uddrag, "citatet skal indeholde markøren, ikke svarets start"
    assert len(uddrag) < 400, "det skal være et uddrag, ikke hele svaret"


def test_kanal_funktionerne_er_selvsikre_mod_doed_db(monkeypatch):
    """Samme kontrakt som resten: fejler DB'en, er svaret tomt — ikke en exception."""
    def _sprang(*_a, **_k):
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db.connect", _sprang)
    nu = datetime.now(UTC)
    assert DE._own_words_since(nu, nu)["count"] == 0
    assert DE._signals_since(nu, nu)["count"] == 0
    assert DE._inner_state_since(nu, nu)["count"] == 0
