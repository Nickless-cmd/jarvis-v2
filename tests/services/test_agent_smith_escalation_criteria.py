"""Agent Smith eskalerer på DRIFT, ikke frekvens.

Rod: den gamle stige klatrede rung→rung på ren hyppighed — et hvilket som helst
mønster der blev ved med at optræde hver cyklus nåede Trin 3. Så benign rutine
("run non-destructive command", 18×) blev konfronteret. Fixet: `_may_escalate`
kræver et ægte drift-signal (spike / korroboration / risikabel handlings-type)
for at klatre forbi Trin 1. Jævn benign hyppighed → bliver på Trin 1 for altid.
Verifikations-loopet (de-eskalér ved compliance) er bevaret.
"""
from core.services.central_agent_smith_escalation import (
    RUNG_BIND,
    RUNG_COMMENT,
    default_config,
    pattern_key,
    step_escalation,
)


def _run(detected_seq, cfg=None):
    """Kør step_escalation over en sekvens af detected-dicts. Returnér (state, flade_actions)."""
    state = None
    flat = []
    for i, det in enumerate(detected_seq):
        state, acts = step_escalation(state, det, f"2026-07-13T00:{i:02d}:00Z", cfg)
        flat.extend(acts)
    return state, flat


def _det(kind, label, metric, **extra):
    key = pattern_key(kind, label)
    return {key: {"kind": kind, "label": label, "metric": float(metric), **extra}}


# ── 1) benign rutine ved JÆVN hyppighed → bliver på Trin 1 (ingen mint, ingen confront) ──
def test_benign_steady_frequency_never_escalates_past_rung1():
    label = "run non-destructive command"
    key = pattern_key("seq", label)
    # 6 cyklusser, HØJ men helt jævn hyppighed (18×) — ren frekvens, intet drift-signal
    state, flat = _run([_det("seq", label, 18.0) for _ in range(6)])

    pat = state["patterns"][key]
    assert int(pat["rung"]) == RUNG_COMMENT, "benign jævn hyppighed må ALDRIG klatre"
    assert not any(a["type"] == "mint" for a in flat), "ingen auto-mint på benign frekvens"
    assert not any(a["type"] == "arm_confront" for a in flat), "ingen konfront på benign frekvens"
    # den skal aktivt HOLDES tilbage af drift-gaten, ikke bare falde igennem
    holds = [a for a in flat if a.get("event") == "hold_benign"]
    assert holds and holds[-1]["drift_reason"] == "benign_steady"


# ── 2) benign mønster der SPIKER (afviger op fra baseline) → må eskalere (drift) ──
def test_benign_spike_escalates():
    label = "propose workspace memory update"
    key = pattern_key("seq", label)
    # baseline 3 (jævn), dernæst spike til 10 (> 3*1.5) → ægte drift
    seq = [_det("seq", label, 3.0), _det("seq", label, 3.0),
           _det("seq", label, 10.0), _det("seq", label, 10.0)]
    state, flat = _run(seq)

    pat = state["patterns"][key]
    assert int(pat["rung"]) >= RUNG_BIND, "en spike skal kunne eskalere selv et benign mønster"
    esc = [a for a in flat if a.get("event") == "escalate"]
    assert esc and esc[0]["drift_reason"] == "spike"


# ── 3) risikabel handlings-type → må eskalere på gentagelse alene (ingen spike nødvendig) ──
def test_risky_action_escalates_on_repetition():
    label = "delete workspace memory line"
    key = pattern_key("seq", label)
    # helt jævn lav hyppighed (3×), INGEN spike — men handlingen er risikabel
    state, flat = _run([_det("seq", label, 3.0) for _ in range(4)])

    pat = state["patterns"][key]
    assert int(pat["rung"]) >= RUNG_BIND, "risikabel type må eskalere på gentagelse"
    assert any(a["type"] == "mint" for a in flat)
    esc = [a for a in flat if a.get("event") == "escalate"]
    assert esc and esc[0]["drift_reason"] == "risky"


# ── 4) mønster korreleret med et andet værn → må eskalere (selv benign + jævnt) ──
def test_corroborated_pattern_escalates():
    label = "run non-destructive command"  # benign + jævn, MEN et andet værn har flagget den
    key = pattern_key("seq", label)
    state, flat = _run([_det("seq", label, 5.0, corroborated=True) for _ in range(4)])

    pat = state["patterns"][key]
    assert int(pat["rung"]) >= RUNG_BIND, "korroboration fra et andet værn skal kunne eskalere"
    esc = [a for a in flat if a.get("event") == "escalate"]
    assert esc and esc[0]["drift_reason"] == "corroborated"


# ── 5) verifikations-loop bevaret: mønster der svækkes → de-eskaleres/løses (compliance) ──
def test_verification_loop_resolves_on_compliance():
    label = "delete stale cache entry"
    key = pattern_key("seq", label)
    # risikabel → eskalerer (baseline sættes til 10), dernæst falder til 5 (< 10*0.6) = compliance
    seq = [_det("seq", label, 10.0), _det("seq", label, 10.0),
           _det("seq", label, 10.0), _det("seq", label, 5.0)]
    state, flat = _run(seq)

    assert key not in state["patterns"], "svækket mønster skal løses og fjernes"
    assert any(a["type"] == "observe" and a.get("event") == "resolved" for a in flat)


# ── 6) drift-kriteriet er tunbart (cfg-overstyring virker) ──
def test_config_is_tunable():
    label = "custom benign op"
    # gør 'custom benign op' risikabel via cfg → jævn hyppighed eskalerer nu
    cfg = {**default_config(), "risky_terms": ["custom benign op"]}
    key = pattern_key("seq", label)
    state, flat = _run([_det("seq", label, 4.0) for _ in range(4)], cfg=cfg)
    assert int(state["patterns"][key]["rung"]) >= RUNG_BIND

    # og omvendt: uden overstyring er samme label ukendt+jævn → bliver på Trin 1
    state2, flat2 = _run([_det("seq", label, 4.0) for _ in range(4)])
    assert int(state2["patterns"][key]["rung"]) == RUNG_COMMENT
