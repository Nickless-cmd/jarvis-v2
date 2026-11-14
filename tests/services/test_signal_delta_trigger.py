"""C2 — signal-delta trigger tests (the economic-proof tests).

The trigger REPLACES a blind 30-min timer. These tests prove it fires on real
change but refuses to out-burn the timer: no fire on noise, no flapping, a
durable global cooldown, and cold-start suppression. `evaluate` must be pure
(never touch an LLM/provider).

`signal_baseline` (C1, parallel) and `db_core.get/set_runtime_state_value` are
MOCKED here per the task contract.
"""
from __future__ import annotations

import sys
import time
import types

import pytest


@pytest.fixture(autouse=True)
def _gendan_uret():
    """Gendan ``time.time`` efter hver test.

    Flere tests her fast-forwarder uret ved at tildele ``time.time`` direkte.
    Uden gendannelsen lækker det falske ur til næste testfil i samme kørsel —
    målt 14/11-2026: `test_dispatch_quota` så et ur fra 1970 og meldte en
    passeret codex-grænse som aktiv blokering, mens den var grøn alene.
    """
    oprindelig = time.time
    yield
    time.time = oprindelig


# --------------------------------------------------------------------------- #
# Fixtures: fake baseline module + dict-backed durable runtime-state.
# --------------------------------------------------------------------------- #
@pytest.fixture()
def fake_baseline(monkeypatch):
    """Inject a controllable fake `core.services.signal_baseline`."""
    ns = types.ModuleType("core.services.signal_baseline")
    ns._store = {}
    ns._cold = False

    def get_baseline(signal):
        return ns._store.get(str(signal))

    def set_baseline(signal, value):
        ns._store[str(signal)] = float(value)

    def is_cold_start(min_signals: int = 3):
        return bool(ns._cold)

    ns.get_baseline = get_baseline
    ns.set_baseline = set_baseline
    ns.is_cold_start = is_cold_start

    monkeypatch.setitem(sys.modules, "core.services.signal_baseline", ns)
    import core.services as _svc

    monkeypatch.setattr(_svc, "signal_baseline", ns, raising=False)
    return ns


@pytest.fixture()
def runtime_state(monkeypatch, isolated_runtime):
    """Durable dict-backed runtime-state (proves cooldown survives 'restart')."""
    from core.runtime import db_core

    store: dict = {}

    def _get(key, default=None):
        return store.get(str(key), default)

    def _set(key, value, **_kw):
        store[str(key)] = value

    monkeypatch.setattr(db_core, "get_runtime_state_value", _get)
    monkeypatch.setattr(db_core, "set_runtime_state_value", _set)
    return store


@pytest.fixture()
def trigger(fake_baseline, runtime_state):
    import importlib

    mod = importlib.import_module("core.services.signal_delta_trigger")
    return mod


def _set_cfg(store, **kw):
    for k, v in kw.items():
        store[f"signal_delta_trigger:{k}"] = v


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_fires_on_real_rise(trigger, fake_baseline):
    fake_baseline._store["cpu"] = 0.20
    decision = trigger.evaluate({"cpu": 0.55})
    assert decision is not None
    assert decision["crossed"] == ["cpu"]
    assert "cpu" in decision["movements"]
    assert decision["movements"]["cpu"] == pytest.approx(0.35)
    assert isinstance(decision["reason"], str) and decision["reason"]


def test_flat_does_not_fire(trigger, fake_baseline):
    fake_baseline._store["cpu"] = 0.50
    assert trigger.evaluate({"cpu": 0.50}) is None

    # Purity: the module must never reference an LLM/provider facade.
    import inspect

    src = inspect.getsource(trigger).lower()
    for forbidden in (
        "call_llm",
        "provider_router",
        "visible_model",
        "cheap_provider",
        "openai",
        "anthropic",
        "complete_chat",
        "chat_completion",
    ):
        assert forbidden not in src, f"impure: found {forbidden!r}"


def test_hysteresis_no_reflap(trigger, fake_baseline, runtime_state):
    # Disable cooldown so we isolate hysteresis; keep values below theta_abs.
    _set_cfg(runtime_state, cooldown_s=0)
    fake_baseline._store["q"] = 0.20

    # 1) big rise → fires; baseline moves to 0.55, signal is now "hot".
    assert trigger.evaluate({"q": 0.55}) is not None
    # 2) still far from baseline (delta 0.25 > theta_low 0.15) → suppressed.
    assert trigger.evaluate({"q": 0.80}) is None
    # 3) settle within theta_low of baseline (delta 0.05) → clears hot, no fire.
    assert trigger.evaluate({"q": 0.60}) is None
    # 4) now a fresh large excursion is allowed to fire again.
    assert trigger.evaluate({"q": 0.20}) is not None


def test_cooldown_blocks_second(trigger, fake_baseline, runtime_state):
    # Default cooldown (1200s) active. Two DIFFERENT qualifying signals so
    # hysteresis cannot be the reason the second is blocked — only the global
    # durable cooldown can.
    fake_baseline._store["a"] = 0.20
    fake_baseline._store["b"] = 0.20

    assert trigger.evaluate({"a": 0.55}) is not None
    assert trigger.evaluate({"b": 0.55}) is None
    # cooldown timestamp is durable (written through db_core mock).
    assert "signal_delta_trigger:last_dispatch_ts" in runtime_state


def test_absolute_floor_fires_on_high_value(trigger, fake_baseline):
    # Tiny delta (0.02 << theta_high 0.30) but absolute value >= theta_abs 0.85.
    fake_baseline._store["load"] = 0.84
    decision = trigger.evaluate({"load": 0.86})
    assert decision is not None
    assert "load" in decision["crossed"]


def test_cold_start_establishes_and_suppresses(trigger, fake_baseline):
    fake_baseline._cold = True
    assert trigger.evaluate({"a": 0.10, "b": 0.90, "c": 0.50}) is None
    # baselines established for every signal on first sight.
    assert fake_baseline._store == {"a": 0.10, "b": 0.90, "c": 0.50}


def test_composite_coalesce(trigger, fake_baseline, runtime_state):
    _set_cfg(runtime_state, cooldown_s=0)
    fake_baseline._store["x"] = 0.20
    fake_baseline._store["y"] = 0.20

    decision = trigger.evaluate({"x": 0.60, "y": 0.70})
    # ONE decision carrying BOTH signals — never one-per-signal.
    assert decision is not None
    assert sorted(decision["crossed"]) == ["x", "y"]
    assert set(decision["movements"]) == {"x", "y"}


# --------------------------------------------------------------------------- #
# Bilag 2 — scope-aware evaluate ("one self, many projections")
# --------------------------------------------------------------------------- #
@pytest.fixture()
def scoped_baseline(monkeypatch):
    """Scope-aware fake `signal_baseline` with a per-scope store."""
    ns = types.ModuleType("core.services.signal_baseline")
    ns._stores = {None: {}}  # scope -> {signal: value}
    ns._cold = {}  # scope -> bool

    def _store(scope):
        return ns._stores.setdefault(scope, {})

    def get_baseline(signal, scope=None):
        return _store(scope).get(str(signal))

    def set_baseline(signal, value, scope=None):
        _store(scope)[str(signal)] = float(value)

    def is_cold_start(min_signals: int = 3, scope=None):
        return bool(ns._cold.get(scope, False))

    ns.get_baseline = get_baseline
    ns.set_baseline = set_baseline
    ns.is_cold_start = is_cold_start

    monkeypatch.setitem(sys.modules, "core.services.signal_baseline", ns)
    import core.services as _svc

    monkeypatch.setattr(_svc, "signal_baseline", ns, raising=False)
    return ns


@pytest.fixture()
def scoped_trigger(scoped_baseline, runtime_state):
    import importlib

    mod = importlib.import_module("core.services.signal_delta_trigger")
    return mod


def test_scope_none_is_the_global_default(scoped_trigger, scoped_baseline):
    """(1) The default (scope=None) path is unchanged and carries no scope tag."""
    scoped_baseline._stores[None]["cpu"] = 0.20
    decision = scoped_trigger.evaluate({"cpu": 0.55})
    assert decision is not None
    assert decision["crossed"] == ["cpu"]
    assert "scope" not in decision


def test_scoped_fires_against_own_baseline_and_tags_scope(
    scoped_trigger, scoped_baseline
):
    """(2) A scope evaluates against its OWN baseline and tags the decision."""
    scoped_baseline._stores["userA"] = {"tension": 0.20}
    decision = scoped_trigger.evaluate({"tension": 0.60}, scope="userA")
    assert decision is not None
    assert decision["crossed"] == ["tension"]
    assert decision["scope"] == "userA"


def test_user_scoped_delta_does_not_leak_to_other_scope(
    scoped_trigger, scoped_baseline, runtime_state
):
    """(3) A per-user delta fires in its room without touching another scope."""
    scoped_baseline._stores["userA"] = {"tension": 0.20}
    scoped_baseline._stores["userB"] = {"tension": 0.20}
    scoped_baseline._stores[None] = {"tension": 0.20}

    fired = scoped_trigger.evaluate({"tension": 0.70}, scope="userA")
    assert fired is not None and fired["scope"] == "userA"

    # userB's and the global baseline are untouched by userA's fire.
    assert scoped_baseline._stores["userB"]["tension"] == 0.20
    assert scoped_baseline._stores[None]["tension"] == 0.20
    # Durable hot/cooldown are namespaced to userA only.
    assert "signal_delta_trigger:last_dispatch_ts:userA" in runtime_state
    assert "signal_delta_trigger:last_dispatch_ts" not in runtime_state
    assert "signal_delta_trigger:last_dispatch_ts:userB" not in runtime_state


def test_cooldown_is_per_scope_no_cross_block(
    scoped_trigger, scoped_baseline, runtime_state
):
    """A global (or userA) dispatch's cooldown never gates another scope."""
    # Default cooldown (1200s) is active after the first fire.
    scoped_baseline._stores[None] = {"s": 0.20}
    scoped_baseline._stores["userA"] = {"s": 0.20}

    assert scoped_trigger.evaluate({"s": 0.60}) is not None  # global fires
    # global is now in cooldown, but userA has its OWN cooldown → still fires.
    scoped = scoped_trigger.evaluate({"s": 0.60}, scope="userA")
    assert scoped is not None and scoped["scope"] == "userA"
    # a second global fire IS blocked by the global cooldown (proves it is real).
    scoped_baseline._stores[None]["s"] = 0.20
    assert scoped_trigger.evaluate({"s": 0.61}) is None


# --------------------------------------------------------------------------- #
# Kalibrering mod de ÆGTE 500 samples (14/11-2026)
# --------------------------------------------------------------------------- #
def test_default_theta_er_billigere_end_timeren_den_erstatter(trigger, fake_baseline, runtime_state):
    """Default-θ skal holde dispatch-raten under den 30-min-timer den afløser.

    MÅLT 14/11-2026 på de 500 durable samples i `event_trigger_shadow_log`
    (8/11 20:19 → 14/11 07:17, 5,5 døgn):

      * 27 af 500 samples krydsede θ_high = 0,30  (5,4 %)
      * median-afstand mellem to kryds: 48 min — cooldown (20 min) fangede 0
      * = 4,9 reelle dispatches i døgnet
      * den blinde 30-min-timer: 48 i døgnet

    Timeren er altså ~10x dyrere. Testen låser den egenskab.

    Sekvensen er de faktiske `creative_drift`-niveauer fra sporet (0,333 /
    0,667 / 1,0), ikke en konstrueret trappe. Cooldownen sættes til 0 med
    vilje: ellers maskerer den θ-effekten, og testen ville være grøn uanset
    hvilken θ der blev sat — det blev målt, og det var præcis fejlen i den
    første udgave af denne test.
    """
    _set_cfg(runtime_state, cooldown_s=0.0)
    niveauer = [1.0] * 6 + [0.667] * 2 + [1.0] * 5 + [0.333] * 3 + [1.0] * 4
    fake_baseline._store["creative_drift"] = niveauer[0]

    import time as _t

    nu = 1_000_000.0
    dispatches = 0
    # 5,5 døgn med ét sample hvert ~16. minut (500 samples / 5,5 døgn).
    for niveau in niveauer * 12:
        _t.time = lambda _n=nu: _n  # fast-forward
        if trigger.evaluate({"creative_drift": niveau}) is not None:
            dispatches += 1
        nu += 16 * 60

    dage = (16 * 60 * len(niveauer) * 12) / 86400.0
    pr_doegn = dispatches / dage
    timer_pr_doegn = 24 * 60 / 30  # 48

    assert pr_doegn < timer_pr_doegn, (
        f"triggeren fyrer {pr_doegn:.1f}/døgn — timeren den erstatter fyrer "
        f"{timer_pr_doegn:.0f}/døgn. Er θ sænket uden at økonomien blev regnet efter?"
    )


def test_theta_over_deltaet_fyrer_aldrig(trigger, fake_baseline, runtime_state):
    """θ skal faktisk styre raten — ikke bare stå i en konstant.

    Uden denne test kunne θ gøres til død kode: cooldownen alene kunne bære
    hele begrænsningen, og så ville en sænkning af θ se ud som om den virkede
    mens intet ændrede sig.

    MÅLT 14/11-2026 — og det er en GRÆNSE, ikke en forglemmelse: de ægte
    `creative_drift`-niveauer er 0,0 / 0,333 / 0,667 / 1,0, så deltaerne er
    0,333 og 0,667. Enhver θ mellem 0 og 0,333 fyrer derfor IDENTISK på dette
    signal — der findes ingen mellemstore bevægelser at kalibrere imod. Testen
    bruger derfor den kant der ER målbar: θ over det største delta (0,90)
    skal slukke triggeren helt.
    """
    niveauer = [1.0] * 6 + [0.667] * 2 + [1.0] * 5 + [0.333] * 3 + [1.0] * 4

    def _koer(theta_high: float) -> int:
        runtime_state.clear()
        fake_baseline._store.clear()
        fake_baseline._store["creative_drift"] = niveauer[0]
        _set_cfg(runtime_state, cooldown_s=0.0, theta_high=theta_high, theta_low=theta_high / 2)
        import time as _t

        nu = 1_000_000.0
        n = 0
        for niveau in niveauer * 12:
            _t.time = lambda _n=nu: _n
            if trigger.evaluate({"creative_drift": niveau}) is not None:
                n += 1
            nu += 16 * 60
        return n

    under = _koer(0.30)   # under deltaet -> fyrer
    over = _koer(0.90)    # over deltaet -> fyrer aldrig
    assert under > 0, "θ=0,30 fyrede aldrig — så måler testen ikke triggeren"
    assert over == 0, (
        f"θ=0,90 gav {over} dispatches, men det største delta i sekvensen er "
        f"0,667 — θ styrer ikke raten, så kalibreringen måler ingenting"
    )


# --------------------------------------------------------------------------- #
# Drift-tærsklen (14/11-2026)
#
# Spring-grenen ser kun ØJEBLIKKELIGE spring. Et signal der driver gradvist
# krydser den aldrig — målt: 0 fyringer på 0.0 -> 1.0 i 20 skridt af 0.05.
# Drift-grenen måler NETTO afstand til et anker, holdt i θ_dwell sammenhængende
# aflæsninger. Testene her beviser de tre ting der gør den ægte og ikke teater:
# den fanger gradvis drift, den afviser flapping, og den dobbelt-tæller ikke.
# --------------------------------------------------------------------------- #
def _drift_koer(trigger, runtime_state, fake_baseline, vaerdier, **cfg):
    """Kør en sekvens gennem triggeren og returnér antal fyringer."""
    import time as _t

    fake_baseline._store["d"] = vaerdier[0]
    _set_cfg(runtime_state, cooldown_s=0.0, **cfg)
    nu = 2_000_000.0
    n = 0
    for v in vaerdier:
        _t.time = lambda _n=nu: _n
        if trigger.evaluate({"d": v}) is not None:
            n += 1
        nu += 16 * 60
    return n


def test_gradvis_drift_fanges_selv_naar_intet_spring_er_stort_nok(
    trigger, fake_baseline, runtime_state
):
    """0.0 -> 1.0 i 20 skridt af 0.05: intet enkelt spring naar θ_high.

    Uden drift-grenen ville dette signal være usynligt for triggeren i al
    evighed, uanset at det til sidst har flyttet sig 1.0.
    """
    gradvis = [round(i * 0.05, 3) for i in range(21)]

    # Bevis først at spring-grenen alene ikke ser det: intet delta >= 0.30.
    assert all(abs(gradvis[i] - gradvis[i - 1]) < 0.30 for i in range(1, len(gradvis)))

    n = _drift_koer(trigger, runtime_state, fake_baseline, gradvis)
    assert n > 0, "gradvis drift blev aldrig fanget — så er drift-grenen dekoration"


def test_flapping_fyrer_ikke_paa_drift(trigger, fake_baseline, runtime_state):
    """Frem-og-tilbage omkring et anker er støj, ikke drift.

    Målt 14/11-2026: en akkumulator over |delta| fyrede 36 gange på denne form,
    hvoraf 18 havde netto-bevægelse 0. Netto-formen skal give nul.
    """
    # Svinget skal vaere UNDER theta_high (spring-grenen tavs) men OVER
    # theta_drift, OG hver aflaesning skal ligge paa SKIFTENDE side af ankeret.
    # Det er praecis den form side-spaerren værner: uden den tæller `away` op
    # paa tværs af svingene og fyrer paa ren støj (maalt: 13 falske fyringer).
    flap = [0.0, 0.25] * 20
    n = _drift_koer(
        trigger, runtime_state, fake_baseline, flap, theta_drift=0.20, drift_dwell=3
    )
    assert n == 0, f"flapping gav {n} drift-fyringer — netto-formen virker ikke"

    # Samme form, men ankeret saettes MIDT imellem: signalet svinger 0.10 <-> 0.30
    # omkring et anker paa 0.20, og theta_drift=0.05 goer at BEGGE sider
    # kvalificerer. Uden side-spaerren tæller `away` op paa tværs af svingene og
    # naar dwell efter 3 aflaesninger; med den nulstilles den ved hvert skift.
    import time as _t

    fake_baseline._store["e"] = 0.20
    _set_cfg(runtime_state, cooldown_s=0.0, theta_drift=0.05, drift_dwell=3)
    _t.time = lambda _n=5_000_000.0: _n
    # Foerste kald saetter ankeret paa 0.20 (intet fyr).
    assert trigger.evaluate({"e": 0.20}) is None
    n2 = 0
    for v in [0.10, 0.30] * 10:
        if trigger.evaluate({"e": v}) is not None:
            n2 += 1
    assert n2 == 0, (
        f"flapping omkring et anker gav {n2} fyringer — side-spaerren virker ikke"
    )


def test_stille_signal_fyrer_aldrig(trigger, fake_baseline, runtime_state):
    n = _drift_koer(trigger, runtime_state, fake_baseline, [0.5] * 40)
    assert n == 0


def test_drift_dobbelt_taeller_ikke_et_spring(trigger, fake_baseline, runtime_state):
    """Et spring ER en stor netto-bevægelse. To fyringer for samme hændelse
    ville gøre triggeren dyrere end den timer den erstatter."""
    import time as _t

    fake_baseline._store["d"] = 0.0
    _set_cfg(runtime_state, cooldown_s=0.0)
    _t.time = lambda _n=1_000_000.0: _n

    beslutning = trigger.evaluate({"d": 0.50})
    assert beslutning is not None
    # Signalet står i `crossed` (spring), ikke i `drift`.
    assert beslutning["crossed"] == ["d"]
    assert "drift" not in beslutning


def test_drift_tilstand_er_durabel(trigger, fake_baseline, runtime_state):
    """`away`-tælleren skal overleve en genstart, ellers kan dwell aldrig nås
    for et signal der aflæses sjældnere end dets dwell-krav."""
    import time as _t

    fake_baseline._store["d"] = 0.0
    # theta_high haeves saa spring-grenen er ude af spillet: kun drift kan fyre.
    _set_cfg(
        runtime_state, cooldown_s=0.0, theta_high=0.90, theta_low=0.45,
        theta_drift=0.30, drift_dwell=3,
    )
    _t.time = lambda _n=1_000_000.0: _n

    # Forste aflæsning sætter ankeret (baseline er ny -> intet fyr).
    assert trigger.evaluate({"d": 0.0}) is None
    # Tre aflæsninger der hver er >= θ_drift fra ankeret, men under θ_high.
    assert trigger.evaluate({"d": 0.32}) is None
    assert trigger.evaluate({"d": 0.33}) is None
    # Tredje når dwell → fyrer.
    tredje = trigger.evaluate({"d": 0.34})
    assert tredje is not None
    assert "d" in tredje.get("drift", []), tredje
    # Tilstanden ligger i runtime-state, ikke i hukommelsen.
    assert "signal_delta_trigger:drift_state" in runtime_state


def test_drift_arver_theta_high_naar_den_ikke_er_sat(
    trigger, fake_baseline, runtime_state
):
    """Målt 14/11-2026: med θ_high=0.90 fyrede drift-grenen stadig 24 gange,
    fordi dens egen default var 0.30. En kalibrering af θ_high der ikke flytter
    drift-tærsklen er en kalibrering der ikke virker."""
    import time as _t

    # Trappe hvor intet enkelt spring naar theta_high=0.90: 0 -> 0.4 -> 0.8.
    # Netto-bevægelsen er 0.8, saa drift-grenen VILLE fyre hvis den brugte sin
    # egen default (0.30) i stedet for at arve theta_high.
    trappe = [0.0, 0.4, 0.8] * 12
    fake_baseline._store["d"] = trappe[0]
    _set_cfg(runtime_state, cooldown_s=0.0, theta_high=0.90, theta_low=0.45)
    nu = 3_000_000.0
    n = 0
    for v in trappe:
        _t.time = lambda _n=nu: _n
        if trigger.evaluate({"d": v}) is not None:
            n += 1
        nu += 16 * 60
    assert n == 0, f"θ_high=0.90 gav {n} fyringer — drift-tærsklen følger ikke θ_high"
