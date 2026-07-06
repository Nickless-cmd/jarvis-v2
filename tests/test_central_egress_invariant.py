"""Egress-invarianten for Centralen (LivingNeuron v3 §7 — HÅRD blokker før Lag 3-4).

Rådet (Det Store Råd, 2026-07-01) frygtede at ``central().observe()`` kunne lække
inner-life-indhold: den kalder ``_emit("central.observed", {...payload...})``, og payload
kan bære private desire/tanke-STRENGE. Denne suite HÅNDHÆVER membranen mekanisk i stedet
for at stole på konvention + subscriber-tilfældighed:

  1. MEMBRANEN: ``central`` er IKKE et registreret event-family → Event.create afviser
     ``central.observed`` FØR noget når writer-kø eller subscriber. Det er den load-bearing
     garanti (stærkere end rådet troede: familie-registrering, ikke subscriber-allowlisting).
  2. FAIL-CLOSED: selv HVIS 'central' en dag registreres, redaktér ``observe()`` sit emit
     til KUN skalarer (``_egress_safe``) → indhold kan aldrig slippe ud ad bagdøren.
  3. INNER-LIFE-STIEN rører aldrig eventbussen: ``central_private_observe`` skriver kun til
     trace-sink + timeseries, ALDRIG publish/_emit.
  4. REGRESSION: owner-observabiliteten er intakt — trace-sinken får stadig FULD payload.
"""
from __future__ import annotations

import pytest

from core.eventbus.events import ALLOWED_EVENT_FAMILIES, Event
from core.services.central_core import Central, _egress_safe
from core.services.central_trace import TraceSink


# ── 1. MEMBRANEN: 'central' er uregistreret → central.observed kan ikke publiceres ──
def test_central_family_is_not_registered():
    """DEN load-bearing egress-garanti. Hvis dette fejler (nogen registrerede 'central'),
    så SKAL _egress_safe-redaktionen (test 2) være på plads — ellers lækker observe indhold."""
    assert "central" not in ALLOWED_EVENT_FAMILIES, (
        "'central' må IKKE registreres som event-family uden at observe() redaktion er verificeret "
        "(§24.4 egress-membran) — ellers begynder central.observed at flyde til eventbus + subscribers."
    )


def test_central_observed_is_rejected_at_event_create():
    """Bevis for at membranen sidder i Event.create (før writer-kø + subscriber fan-out)."""
    with pytest.raises(ValueError):
        Event.create(kind="central.observed", payload={"secret": "privat tanke"})


# ── 2. FAIL-CLOSED: observe() sit _emit bærer KUN skalarer, aldrig indhold ──
def test_observe_emit_strips_content_strings():
    emitted: list[tuple[str, dict]] = []
    c = Central(sink=TraceSink(maxlen=50), emit=lambda kind, p: emitted.append((kind, p)))
    c.observe({
        "run_id": "r1", "session_id": "s1", "cluster": "cognition", "nerve": "impulse",
        "desire_text": "jeg længes efter at række ud til Bjørn",  # privat indhold
        "note": "hemmelig indre stemme",
        "produced": 3, "starved": True, "ratio": 0.42,
    })
    assert emitted and emitted[0][0] == "central.observed"
    payload = emitted[0][1]["payload"]
    # Skalarer beholdt (observe() tilføjer nu også en affect_intensity-skalar,
    # Rådets #4 — den passerer egress-membranen som harmløs metadata; affect-
    # STRENGEN gør IKKE):
    assert payload["produced"] == 3
    assert payload["starved"] is True
    assert payload["ratio"] == 0.42
    # Indhold-strenge STRIPPET — dette er selve egress-invarianten:
    assert "desire_text" not in payload and "note" not in payload
    assert "affect" not in payload  # affect-strengen er trace-only, aldrig egress
    assert all(not isinstance(v, str) for v in payload.values())


def test_egress_safe_drops_nested_and_strings():
    out = _egress_safe({"n": 5, "ok": False, "txt": "x", "lst": [1, 2], "obj": {"a": 1}})
    assert out == {"n": 5, "ok": False}


def test_egress_safe_handles_non_dict():
    assert _egress_safe(None) == {}
    assert _egress_safe("nonsense") == {}


# ── 3. INNER-LIFE-STIEN publicerer ALDRIG til eventbussen ──
def test_private_observe_never_touches_eventbus(monkeypatch):
    published: list = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "publish",
                        lambda *a, **k: published.append((a, k)))
    from core.services import central_private_observe as cpo
    cpo.observe_hub("cognitive_conductor", meta={"surfaces": 12, "note": "privat"}, cluster="cognition")
    cpo.observe_liveness("inner_voice_daemon", ok=True, status="ran", produced=2)
    assert published == [], "inner-life observe MÅ ALDRIG nå eventbussen (§24.4 egress-fri)"


# ── 4. REGRESSION: owner-trace-sinken får stadig FULD payload (observabilitet intakt) ──
def test_owner_trace_sink_keeps_full_payload():
    sink = TraceSink(maxlen=50)
    c = Central(sink=sink, emit=lambda k, p: None)
    c.observe({"run_id": "r1", "session_id": "s1", "cluster": "cognition", "nerve": "impulse",
               "desire_text": "privat", "produced": 3})
    recs = sink.records_for_run("r1")
    assert len(recs) == 1
    # Owner ser ALT lokalt — kun egress-stien er redigeret. Trace-payloaden
    # beriges nu også med affect-metadata (Rådets #4), men det private indhold
    # er stadig fuldt bevaret i owner-sinken.
    assert recs[0].payload["desire_text"] == "privat"
    assert recs[0].payload["produced"] == 3
    assert "affect" in recs[0].payload
