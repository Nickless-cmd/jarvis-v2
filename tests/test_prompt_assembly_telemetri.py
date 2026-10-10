"""Assembly-telemetrien: navne, halens tegn, og at tallet ER det ucachede.

Udskilt fra prompt_contract 6/10-2026. Den vigtigste test her er
`test_halen_maales_praecis_som_forbrugeren_deler_den`: telemetrien og
`visible_model._split_dynamic_tail` skal regne SAMME tal, ellers maaler
feltet noget andet end det der faktisk ligger uden for cachen — og saa er en
«maalt» beskaering af halen en gaetteleg med et tal paa.
"""

from __future__ import annotations

import pytest

from core.services import prompt_assembly_telemetri as T
from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL
from core.services.visible_model import _split_dynamic_tail

S = DYNAMIC_TAIL_SENTINEL


@pytest.mark.parametrize("text", [
    "",                                             # intet
    "kun praefiks uden hale",                       # ingen sentinel
    "praefiks\n\n" + S + "\n\nhale her",            # normal
    "praefiks\n\n" + S,                             # sentinel men tom hale
    S + "hele teksten er hale",                     # sentinel foerst
    "p\n\n" + S + "\n\n   hale med luft omkring   ",  # strip paa begge sider
    "p\n\n" + S + "\n\nhale " + S + " og en sentinel MERE",  # kun den foerste deler
])
def test_halen_maales_praecis_som_forbrugeren_deler_den(text):
    assert T.hale_tegn(text) == len(_split_dynamic_tail(text)[1])


def test_uden_sentinel_er_halen_nul_ikke_hele_teksten():
    """Fald-retningen betyder noget: 0 betyder «intet uden for cachen», og det
    er sandt uden sentinel. Faldt den mod len(text), ville enhver prompt uden
    hale se ud som om ALT var ucachet."""
    assert T.hale_tegn("en hel prompt uden hale") == 0
    assert T.hale_tegn(None) == 0


def test_eventet_baerer_halen_og_praefikset_og_de_summerer():
    sendt = []

    class FakeBus:
        def publish(self, kind, payload):
            sendt.append((kind, payload))

    import core.eventbus.bus as bus
    gammel = bus.event_bus
    bus.event_bus = FakeBus()
    try:
        parts = ["# Stor\n" + "a" * 500, S, "hale-blok"]
        tekst = "\n\n".join(parts)
        T.rapporter_assembly(parts, assembled_text=tekst, compact=False,
                             session_id="", assembly_ms=12)
    finally:
        bus.event_bus = gammel

    kinds = [k for k, _ in sendt]
    assert "prompt.assembly_size" in kinds, kinds
    p = dict(sendt[kinds.index("prompt.assembly_size")][1])
    assert p["dyn_tail_chars"] == len("hale-blok")
    assert p["cached_prefix_chars"] == p["total_chars"] - p["dyn_tail_chars"]
    assert p["total_chars"] == len(tekst)


def test_telemetri_vaelter_ikke_en_build_naar_bussen_fejler():
    """Self-safe er ikke pynt: en prompt-build maa ikke doe af at maale sig selv."""
    class SprengBus:
        def publish(self, *a, **k):
            raise RuntimeError("bus nede")

    import core.eventbus.bus as bus
    gammel = bus.event_bus
    bus.event_bus = SprengBus()
    try:
        T.rapporter_assembly(["# A\nkrop"], assembled_text="# A\nkrop",
                             compact=True, session_id="", assembly_ms=0)
    finally:
        bus.event_bus = gammel


def test_cache_event_is_opaque_and_has_only_the_diagnostic_contract(monkeypatch):
    sent = []
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", lambda kind, payload: sent.append((kind, payload)))
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "runtime")
    monkeypatch.setattr(T.os, "getpid", lambda: 4242)

    T.rapporter_cache_lookup(
        key=("private-session", 7, "deepseek", "model", "default"),
        outcome="miss",
        cache_age_ms=None,
        lookup_ms=1.25,
        build_ms=12_345.5,
        caller_phase="post_tool",
    )

    assert len(sent) == 1
    kind, payload = sent[0]
    assert kind == "prompt.assembly_cache"
    assert set(payload) == {
        "key_hash",
        "cache_outcome",
        "cache_age_ms",
        "lookup_ms",
        "build_ms",
        "caller_phase",
        "pid",
        "process_role",
    }
    assert payload["key_hash"] != "private-session"
    assert "private-session" not in str(payload)
    assert payload["pid"] == 4242
    assert payload["process_role"] == "runtime"


def test_cache_telemetry_is_self_safe(monkeypatch):
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("bus down")),
    )
    T.rapporter_cache_lookup(
        key=None,
        outcome="unsafe_no_key",
        cache_age_ms=None,
        lookup_ms=0.1,
        build_ms=2.0,
        caller_phase="initial",
    )

    monkeypatch.setattr(
        "core.services.central_xproc.process_role",
        lambda: (_ for _ in ()).throw(RuntimeError("role unavailable")),
    )
    T.rapporter_cache_lookup(
        key=("s", 1),
        outcome="miss",
        cache_age_ms=None,
        lookup_ms=0.1,
        build_ms=2.0,
        caller_phase="initial",
    )
