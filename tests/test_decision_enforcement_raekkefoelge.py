"""Rækkefølgen skal kunne bære en dom — brud-detektoren så kun teksten.

Målt 25/9-2026 på en ægte tur: Jarvis skrev hele sit svar (en analyse der
sluttede med et spørgsmål til Bjørn), kaldte `remember_this`, og skrev
«Gemt —». Klienten sætter skillelinjen ved det SIDSTE `tool_use`
(`raekkeModel.ts::opdel`), så hele analysen blev vist som «arbejde» og
kvitteringen som «svaret».

`detect_breach_in_output` fik kun den færdige tekst. Den kunne derfor ikke se
dét forpligtelsen «ingen kald efter svaret» handler om — og kunne i princippet
dømme «kept» på et brud, fordi teksten ikke tilstod noget.
"""

from __future__ import annotations

import json

from core.services import decision_enforcement as DE


# ---------------------------------------------------------------------------
# Rækkefølgen
# ---------------------------------------------------------------------------


def _tur_med_kald_efter_svaret() -> list[dict]:
    """Den målte fejl, i blokke."""
    return [
        {"type": "thinking", "text": "jeg skal svare"},
        {"type": "text", "text": "Her er mit svar. " * 80},  # ~1360 tegn
        {"type": "tool_use", "id": "t1", "name": "remember_this", "input": {}},
        {"type": "tool_result", "tool_use_id": "t1", "status": "done", "content": "ok"},
        {"type": "text", "text": "Gemt — den hører til i mig."},  # 29 tegn
    ]


def test_raekkefoelgen_staar_i_den_orden_den_skete():
    linjer = DE.blok_rekkefoelge(_tur_med_kald_efter_svaret())
    assert linjer[0] == "tanke"
    assert linjer[1].startswith("tekst (")
    assert linjer[2] == "kald: remember_this"
    # Et resultat er ikke en handling nogen kan bryde en forpligtelse med.
    assert not any("tool_result" in x for x in linjer)
    assert linjer[-1].startswith("tekst (")


def test_svaret_der_blev_arbejde_markeres():
    regnskab = DE.svar_blev_arbejde(_tur_med_kald_efter_svaret())
    assert regnskab is not None
    assert regnskab["mistænkelig"] is True
    assert regnskab["stoerste_tekst_foer"] > 800
    assert regnskab["svar_tegn"] < 300
    assert regnskab["kald_efter_tekst"] == ["remember_this"]


def test_sund_form_markeres_ikke():
    """Svaret står sidst — det er den form forpligtelsen beder om."""
    blokke = [
        {"type": "text", "text": "Nu læser jeg filen."},
        {"type": "tool_use", "id": "t1", "name": "read_file", "input": {}},
        {"type": "tool_result", "tool_use_id": "t1", "status": "done", "content": "…"},
        {"type": "text", "text": "Filen gør X. " * 100},
    ]
    regnskab = DE.svar_blev_arbejde(blokke)
    assert regnskab is not None
    assert regnskab["mistænkelig"] is False
    assert regnskab["svar_tegn"] > 800


def test_uden_kald_er_hele_beskeden_svaret():
    """Klientens regel er bundet til `tool_use`, ikke til tekstens plads."""
    assert DE.svar_blev_arbejde([{"type": "text", "text": "bare et svar"}]) is None


def test_kort_narration_foer_kaldet_er_ikke_mistroen():
    """En kort replik og så et kald er normal narration — intet svar at skubbe."""
    blokke = [
        {"type": "text", "text": "Lad mig se."},
        {"type": "tool_use", "id": "t1", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "t1", "status": "done", "content": "ok"},
    ]
    regnskab = DE.svar_blev_arbejde(blokke)
    assert regnskab is not None
    assert regnskab["mistænkelig"] is False


def test_tomt_og_skrae_taales():
    assert DE.svar_blev_arbejde(None) is None
    assert DE.svar_blev_arbejde([]) is None
    assert DE.svar_blev_arbejde(["ikke en blok", 42, None]) is None


# ---------------------------------------------------------------------------
# Prompten
# ---------------------------------------------------------------------------


def test_prompten_baerer_raekkefoelgen_og_markoeren():
    prompt = DE._build_breach_prompt(
        "Gemt — den hører til i mig.", [], _tur_med_kald_efter_svaret(),
    )
    assert "Rækkefølgen i din tur" in prompt
    assert "kald: remember_this" in prompt
    assert "MÅLT" in prompt


def test_prompten_uden_blokke_er_som_foer():
    """Uden blokke må dommeren ikke se en tom sektion — den er som før."""
    prompt = DE._build_breach_prompt("et svar", [], None)
    assert "Rækkefølgen i din tur" not in prompt
    assert "=== Din besked ===" in prompt


# ---------------------------------------------------------------------------
# Blokkene ud af payloaden
# ---------------------------------------------------------------------------


def test_blokke_laeses_fra_beskedens_content_json():
    blokke = [{"type": "text", "text": "hej"}]
    ud = DE._blokke_fra_payload({}, {"content_json": json.dumps(blokke)})
    assert ud == blokke


def test_blokke_laeses_naar_content_json_er_en_liste():
    blokke = [{"type": "text", "text": "hej"}]
    assert DE._blokke_fra_payload({}, {"content_json": blokke}) == blokke


def test_blokke_falder_tilbage_til_basen(monkeypatch):
    """Ældre udgiver uden content_json: besked-id'et slår op i basen."""
    import core.runtime.db as db

    class _Cursor:
        def fetchone(self):
            return (json.dumps([{"type": "text", "text": "fra basen"}]),)

    class _Conn:
        def execute(self, *_a, **_k):
            return _Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(db, "connect", lambda *a, **k: _Conn())
    ud = DE._blokke_fra_payload({}, {"message_id": "m-1"})
    assert ud == [{"type": "text", "text": "fra basen"}]


def test_blokke_uden_spor_giver_none():
    assert DE._blokke_fra_payload({}, {}) is None
    assert DE._blokke_fra_payload({}, None) is None
    assert DE._blokke_fra_payload({}, {"content_json": "ikke json"}) is None


# ---------------------------------------------------------------------------
# Dommeren får blokkene — og Centralen tæller
# ---------------------------------------------------------------------------


def test_dommeren_faar_blokkene_med(monkeypatch):
    set_kald: list[str] = []

    def _fake_llm(prompt, **_k):
        set_kald.append(prompt)
        return "NONE"

    monkeypatch.setattr(DE, "_recent_detection_at", None)
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call", _fake_llm)
    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions",
        lambda limit=10: [{"decision_id": "d1", "directive": "ingen kald efter svaret"}],
    )
    DE.detect_breach_in_output(
        "Her er mit svar, som er langt nok til at passere laengde-tjekket.",
        _tur_med_kald_efter_svaret(),
    )
    assert set_kald, "dommeren blev slet ikke kaldt"
    assert "Rækkefølgen i din tur" in set_kald[0]


def test_centralen_taeller_moensteret(monkeypatch):
    set_obs: list[dict] = []

    class _Central:
        def observe(self, payload):
            set_obs.append(payload)

    monkeypatch.setattr("core.services.central_core.central", lambda: _Central())
    DE._observer_svar_skubbet(_tur_med_kald_efter_svaret())
    assert set_obs and set_obs[0]["nerve"] == "svar_efter_kald"
    assert set_obs[0]["kald_efter_tekst"] == ["remember_this"]


def test_centralen_tier_naar_formen_er_sund(monkeypatch):
    set_obs: list[dict] = []

    class _Central:
        def observe(self, payload):
            set_obs.append(payload)

    monkeypatch.setattr("core.services.central_core.central", lambda: _Central())
    DE._observer_svar_skubbet([
        {"type": "text", "text": "Læser nu."},
        {"type": "tool_use", "id": "t", "name": "read_file", "input": {}},
        {"type": "text", "text": "Svar. " * 200},
    ])
    assert set_obs == []


# ---------------------------------------------------------------------------
# Kilde-vagt: subscriberen SKAL sende blokkene videre
# ---------------------------------------------------------------------------
#
# Uden den her kan nogen fjerne `blokke`-argumentet fra `_poll_loop`, og hele
# fixen dør tavst — testene ovenfor kalder funktionerne direkte og ser det ikke.
# Samme mønster som huset bruger for alders-filteret i
# `test_boot_reconciler_visible_drift.py`.


def test_subscriberen_sender_blokkene_videre():
    import pathlib

    kilde = pathlib.Path(DE.__file__).read_text(encoding="utf-8")
    i = kilde.index("def _poll_loop")
    krop = kilde[i:i + 2600]
    assert "args=(text, blokke)" in krop, "subscriberen sender ikke blokkene videre"
    assert "_observer_svar_skubbet(blokke)" in krop, "mønsteret tælles ikke i Centralen"
