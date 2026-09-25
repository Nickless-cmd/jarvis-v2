"""Destillationen skal kunne laese et indhegnet svar.

25/9-2026: `run_dream_bias_distillation` svarede `json_parse_failed` paa
produktionen, fordi modulet brugte raa `json.loads` paa et svar modellen havde
pakket i ```. Droemmen var der hver cyklus — «Jeg foeler uro og skam, men
siger det hoejt til Bjoern» — og blev kasseret.

Testen her holder selve laesningen fast. De oevrige faser (min-content-porten,
UPSERT, event) har deres egne tests i `test_dream_bias_accumulate.py`.
"""
from __future__ import annotations

import core.services.dream_bias_engine as B


def test_destillationen_parser_et_indhegnet_svar(monkeypatch):
    """Ordret forlaeg fra CT105 — det der blev kasseret."""
    raw = ('```\n{\n  "dream_text": "Jeg foeler uro og skam, men siger det '
           'hoejt til Bjoern",\n  "attention_bias": {"unfinished_business": 0.4},\n'
           '  "threshold_bias": {}\n}\n```')
    monkeypatch.setattr(B, "_has_minimum_dream_content",
                        lambda **kw: (True, [{"event_id": 1}]))
    monkeypatch.setattr(B, "delete_expired_bias_rows", lambda: 0)
    monkeypatch.setattr(B, "_call_llm_for_bias", lambda **kw: raw)
    gemt: dict = {}
    monkeypatch.setattr(B, "_upsert_dream_bias",
                        lambda **kw: gemt.update(kw) or {"accumulated_count": 1})
    monkeypatch.setattr(B.event_bus, "publish", lambda *a, **k: None)

    ud = B.run_dream_bias_distillation(workspace_id="default")
    assert ud.get("status") != "json_parse_failed", (
        "droemmen blev kasseret paa hegnet igen")
    assert ud["status"] == "distilled"
    assert "uro og skam" in str(gemt.get("validated", {}).get("dream_text", ""))


def test_et_svar_uden_json_giver_stadig_en_pæn_status(monkeypatch):
    """Kan vi ikke laese det, skal det vaere en status — ikke en undtagelse."""
    monkeypatch.setattr(B, "_has_minimum_dream_content",
                        lambda **kw: (True, [{"event_id": 1}]))
    monkeypatch.setattr(B, "delete_expired_bias_rows", lambda: 0)
    monkeypatch.setattr(B, "_call_llm_for_bias", lambda **kw: "jeg kunne ikke droemme i nat")
    assert B.run_dream_bias_distillation(workspace_id="default")["status"] == "json_parse_failed"


def test_tegn_graensen_er_stor_nok_til_en_hel_droem(monkeypatch):
    """`max_len` er TEGN, ikke tokens — og JSON'en skal kunne vaere der.

    Maalt paa CT105 25/9-2026: token-budgettet 400 blev sendt ind som
    tegn-graense, saa svaret var praecis 400 tegn med tre aabne klammer og én
    lukket. Droemmen blev hugget over midt i sin egen JSON.

    Testen maaler den graense der FAKTISK sendes videre, ikke hvordan den er
    skrevet — en kilde-vagt ville have bestaaet paa den gamle kode.
    """
    set_graense: dict = {}

    def _fang(prompt, *, max_len, fallback, daemon_name):
        set_graense["max_len"] = max_len
        return ""

    import core.services.daemon_llm as DL
    monkeypatch.setattr(DL, "quality_daemon_llm_call", _fang)
    B._call_llm_for_bias(events=[{"source_kind": "decision_kept", "summary": "x"}],
                         max_tokens=400)
    # En hel droem-JSON (dream_text + fem attention-noegler + fire
    # threshold-noegler + intensity) fylder omkring 700 tegn.
    assert set_graense["max_len"] >= 1200, (
        f"tegn-graensen er {set_graense['max_len']} — JSON'en naar ikke at lukke")
