from unittest import mock
from core.services import central_decentralization as dz

def test_classifies_overhead_vs_governs_and_excludes_security():
    fake = {
        "decision_gate": {"cluster":"commit","total":20,"green":20},        # altid-grøn kognitiv → kandidat
        "veto": {"cluster":"commit","total":123,"green":123},               # altid-grøn → kandidat
        "cross_user_share": {"cluster":"privacy","total":36,"green":36},     # SECURITY → ALDRIG kandidat
        "memory_promotion": {"cluster":"memory","total":528,"green":223},    # governer → ikke kandidat
        "central_self_probe": {"cluster":"system","total":14000,"green":14000},  # probe → overhead men ikke kandidat
    }
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake):
        a = dz.analyze_chokepoint()
    cand = {c["nerve"] for c in a["candidates"]}
    assert "decision_gate" in cand and "veto" in cand
    assert "cross_user_share" not in cand      # security aldrig decentraliseret
    assert "central_self_probe" not in cand    # helbreds-probe, ikke governance
    assert "memory_promotion" not in cand      # governer reelt
    assert a["chokepoint_tax_pct"] > 90        # domineret af self-probe-overhead

def test_record_observes_metadata_only():
    obs=[]
    fc=mock.MagicMock(); fc.observe.side_effect=lambda e: obs.append(e)
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value={}), \
            mock.patch("core.services.central_core.central", return_value=fc):
        dz.record_chokepoint()
    assert obs and obs[0]["cluster"]=="system" and obs[0]["nerve"]=="decentralization"
    assert set(obs[0]) <= {"cluster","nerve","kind","tax_pct","candidates","governs"}
