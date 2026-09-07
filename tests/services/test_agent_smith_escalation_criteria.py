"""Agent Smith eskalerer på DRIFT, ikke frekvens — og kun på EGNE løfter.

OPDATERET 7/9-2026. Fire af testene her udtrykte designet fra 13. juli, hvor
spike og korroboration var selvstændige indgange til stigen. To senere
beslutninger har afløst det, begge dokumenteret i modulet:

* **11. juli, krav 1:** Smith håndhæver Jarvis' EGNE løfter i stedet for at
  opfinde «stop X» ud fra hyppighed. Så et mønster skal være risikabelt eller
  selv-lovet for overhovedet at kunne klatre.
* **19. august:** berettigelsen gælder OGSÅ trin 1. Er mønstret ingen af
  delene, har Smith ingenting at sige om det, og det spores slet ikke.
  «Tavshed er den rigtige adfærd, ikke en blødere tone.»

Spike og korroboration er derfor ikke længere indgange — de afgør hvor hurtigt
et ALLEREDE berettiget mønster klatrer.

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


# ── 1) benign rutine → Smith siger INTET og sporer den ikke (19. aug) ──
def test_benign_rutine_spores_slet_ikke():
    label = "run non-destructive command"
    key = pattern_key("seq", label)
    # 6 cyklusser, HØJ men helt jævn hyppighed (18×) — normalt arbejde
    state, flat = _run([_det("seq", label, 18.0) for _ in range(6)])

    assert key not in state["patterns"], (
        "et mønster der hverken er risikabelt eller selv-lovet skal droppes helt — "
        "ikke parkeres på trin 1, hvor det stadig ville tale"
    )
    assert not any(a["type"] == "mint" for a in flat)
    assert not any(a["type"] == "arm_confront" for a in flat)
    assert not any(a["type"] == "voice" for a in flat), "tavshed, ikke en blødere tone"


# ── 2) SPIKE er ikke længere en selvstændig indgang (11. juli, krav 1) ──
def test_spike_alene_aabner_ikke_stigen():
    """En spike på noget Jarvis aldrig har lovet at stoppe er stadig ikke
    Smiths bord. Spike afgør hvor hurtigt et BERETTIGET mønster klatrer."""
    label = "propose workspace memory update"
    key = pattern_key("seq", label)
    seq = [_det("seq", label, 3.0), _det("seq", label, 3.0),
           _det("seq", label, 10.0), _det("seq", label, 10.0)]
    state, flat = _run(seq)
    assert key not in state["patterns"]
    assert not any(a["type"] == "mint" for a in flat)


def test_spike_paa_et_SELVLOVET_moenster_eskalerer():
    """Og modsat: er mønstret selv-lovet, virker spike som designet."""
    label = "spring verifikation over"
    key = pattern_key("seq", label)
    cfg = {**default_config(),
           "self_commitments": ["spring verifikation over"]}
    seq = [_det("seq", label, 3.0), _det("seq", label, 3.0),
           _det("seq", label, 10.0), _det("seq", label, 10.0)]
    state, flat = _run(seq, cfg=cfg)
    assert int(state["patterns"][key]["rung"]) >= RUNG_BIND
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


# ── 4) korroboration virker INDEN FOR det berettigede sæt ──
def test_korroboration_aabner_ikke_stigen_alene():
    """At et andet værn har flagget normalt arbejde gør det ikke til Smiths
    sag. Berettigelsen kommer først."""
    label = "run non-destructive command"
    key = pattern_key("seq", label)
    state, flat = _run([_det("seq", label, 5.0, corroborated=True) for _ in range(4)])
    assert key not in state["patterns"]


def test_korroboration_paa_et_SELVLOVET_moenster_eskalerer():
    label = "svar uden at laese filen"
    key = pattern_key("seq", label)
    cfg = {**default_config(), "self_commitments": ["svar uden at laese filen"]}
    state, flat = _run([_det("seq", label, 5.0, corroborated=True) for _ in range(4)],
                       cfg=cfg)
    assert int(state["patterns"][key]["rung"]) >= RUNG_BIND
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

    # og omvendt: uden overstyring er samme label hverken risikabelt eller
    # selv-lovet → Smith sporer det slet ikke (19. aug)
    state2, flat2 = _run([_det("seq", label, 4.0) for _ in range(4)])
    assert key not in state2["patterns"]
