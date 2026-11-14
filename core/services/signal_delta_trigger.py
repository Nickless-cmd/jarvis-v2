"""Signal-delta trigger (C2) — pure, NON-LLM event-driven dispatch decision.

Replaces a blind 30-min timer. A daemon today fires an (expensive) LLM every
30 minutes regardless of whether anything changed. This module is the cheap
pure function evaluated each heartbeat that decides whether a *real* change in
Jarvis' signals warrants a dispatch — and, critically, refuses to fire on
noise or flapping so it never out-burns the timer it replaces.

Guarantees:
  * **Pure / NON-LLM.** ``evaluate`` never calls any LLM/provider. It only
    reads baselines (C1) and durable runtime-state.
  * **Self-safe.** Any error → ``None`` (fail-closed: never fire on error).
  * **Composite-coalesced.** At most ONE decision per call, carrying ALL
    crossed signals — never one decision per signal.

Guards (each is an economic guard against burning more than the timer):
  * **Cold-start suppression** — on first sight, establish baselines, never fire.
  * **Hysteresis (Schmitt).** A signal fires when ``|value - baseline| >=
    θ_high``. On firing its baseline advances to the new value and it becomes
    "hot"; while hot it is suppressed until it *settles* back within θ_low of
    baseline (θ_low < θ_high). Kills flapping around the threshold. The hot
    set is DURABLE (runtime-state) so hysteresis survives restart.
  * **Debounce / cooldown.** After any dispatch, a global cooldown (default
    1200s) suppresses further dispatch. The cooldown timestamp is DURABLE
    (runtime-state) so it survives restart.
  * **Absolute-floor OR.** A signal also crosses if its absolute value >=
    θ_abs even with a tiny delta — catches slow-boil drift that never trips
    the delta.

All thresholds are tunable at runtime (runtime-state) without a deploy.
"""
from __future__ import annotations

import time as _time
from typing import Optional

# Durable runtime-state keys.
_KEY_PREFIX = "signal_delta_trigger:"
_KEY_LAST_DISPATCH = _KEY_PREFIX + "last_dispatch_ts"
_KEY_HOT = _KEY_PREFIX + "hot_signals"


def _scoped_key(base: str, scope: str | None) -> str:
    """Namespace a durable key by ``scope``. None → the global key, unchanged."""
    name = str(scope or "").strip()
    if not name:
        return base
    return f"{base}:{name}"

# Tunable defaults (override via runtime-state key ``signal_delta_trigger:<name>``).
_DEFAULT_THETA_HIGH = 0.30
_DEFAULT_THETA_LOW = 0.15
_DEFAULT_THETA_ABS = 0.85
_DEFAULT_COOLDOWN_S = 1200.0
# Drift-tærsklen (14/11-2026): spring-tærsklen ser kun ØJEBLIKKELIGE spring.
# Et signal der driver gradvist — 0.02 ad gangen — krydser den aldrig, uanset
# hvor langt det til sidst er flyttet. Målt 14/11-2026 på 500 ægte samples:
# `creative_drift` sprang 0.33 ad gangen og blev fanget 98 gange, mens de seks
# øvrige signaler havde NUL akkumuleret bevægelse — så på det daværende
# datagrundlag fangede drift-tærsklen intet ekstra. Den findes fordi den
# situation ikke er den eneste mulige: et signal med finere opløsning ville
# være usynligt for spring-grenen.
#
# Formen er NETTO afstand til et anker — ikke summen af ryk. En akkumulator
# over |delta| fyrer på flapping (målt: 18 af 36 fyringer havde netto 0), og
# det er præcis den støj triggeren skal afvise. Ankeret flyttes først når
# signalet har været >= θ_drift fra det i θ_dwell SAMMENHÆNGENDE samples:
# gradvis drift når kravet fordi afstanden vokser, flapping gør ikke fordi
# den aldrig bliver væk længe nok.
_DEFAULT_THETA_DRIFT = 0.30
_DEFAULT_DRIFT_DWELL = 3
_KEY_DRIFT = _KEY_PREFIX + "drift_state"


def _db():
    """Lazy import so this module is importable/pure without a live DB, and so
    tests (and isolated_runtime reloads) always get the current db_core."""
    from core.runtime import db_core

    return db_core


def _baseline():
    """Lazy import of C1's baseline module (built in parallel)."""
    from core.services import signal_baseline

    return signal_baseline


# --- Scope-aware baseline shims -------------------------------------------- #
# The default (global) path calls the baseline module with its ORIGINAL 1-/2-arg
# signatures so behaviour — and any test double — is unchanged. A ``scope`` is
# forwarded only when explicitly given, keying the per-user/session baselines.
def _bl_is_cold_start(baseline, scope):
    if scope is None:
        return baseline.is_cold_start()
    return baseline.is_cold_start(scope=scope)


def _bl_get(baseline, name, scope):
    if scope is None:
        return baseline.get_baseline(name)
    return baseline.get_baseline(name, scope=scope)


def _bl_set(baseline, name, val, scope):
    if scope is None:
        baseline.set_baseline(name, val)
    else:
        baseline.set_baseline(name, val, scope=scope)


def _cfg_float(db, name: str, default: float) -> float:
    try:
        return float(db.get_runtime_state_value(_KEY_PREFIX + name, default))
    except Exception:
        return float(default)


def _load_float(db, key: str, default: float) -> float:
    try:
        return float(db.get_runtime_state_value(key, default))
    except Exception:
        return float(default)


def _store_float(db, key: str, value: float) -> None:
    try:
        db.set_runtime_state_value(key, float(value))
    except Exception:
        pass


def _load_hot(db, key: str = _KEY_HOT) -> dict[str, bool]:
    try:
        raw = db.get_runtime_state_value(key, None)
        if isinstance(raw, dict):
            return {str(k): bool(v) for k, v in raw.items()}
    except Exception:
        pass
    return {}


def _store_hot(db, hot: dict[str, bool], key: str = _KEY_HOT) -> None:
    try:
        db.set_runtime_state_value(key, {str(k): bool(v) for k, v in hot.items()})
    except Exception:
        pass


def _tal(vaerdi, default: float) -> float:
    """Læs ét tal fra en gemt tilstand — ellers ``default``.

    Posten kan være skrevet af en ældre version eller være defekt. Default er
    det sikre valg: et anker der ikke kan læses må ikke blive til et fyr.
    """
    try:
        return float(vaerdi)
    except (TypeError, ValueError):  # ikke et tal -> default, aldrig et fyr på et gæt
        return default


def _load_drift(db, key: str = _KEY_DRIFT) -> dict[str, dict]:
    """Durable drift-tilstand pr. signal: ``{"anchor": float, "away": int}``.

    ``away`` er antallet af SAMMENHÆNGENDE aflæsninger hvor signalet har været
    >= θ_drift fra ankeret. Det er dét tal der skelner drift fra flapping.
    """
    try:
        raw = db.get_runtime_state_value(key, None)
    except Exception:  # uden læsning ankres der forfra; state-laget må ikke vælte triggeren
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict] = {}
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue
        out[str(k)] = {
            "anchor": _tal(v.get("anchor"), 0.0),
            "away": int(_tal(v.get("away"), 0)),
            "side": int(_tal(v.get("side"), 0)),
        }
    return out


def _store_drift(db, state: dict[str, dict], key: str = _KEY_DRIFT) -> None:
    try:
        db.set_runtime_state_value(
            key,
            {
                str(k): {
                    "anchor": float(v.get("anchor", 0.0)),
                    "away": int(v.get("away", 0)),
                    "side": int(v.get("side", 0)),
                }
                for k, v in state.items()
            },
        )
    except Exception:  # en manglende skrivning koster ét anker, ikke et fyr; triggeren må ikke fejle
        pass


def _reason(crossed: list[str], movements: dict[str, float], theta_abs: float) -> str:
    parts = []
    for name in crossed:
        delta = movements.get(name, 0.0)
        parts.append(f"{name} Δ{delta:+.3f}")
    return "signal-delta dispatch: " + ", ".join(parts)


def evaluate(signals: dict[str, float], scope: str | None = None) -> Optional[dict]:
    """Decide whether a real change warrants a dispatch.

    Returns ``None`` when nothing should dispatch. Otherwise returns ONE
    decision dict ``{"crossed": [...], "movements": {sig: delta}, "reason": str}``
    carrying every signal that crossed this call.

    ``scope`` (Bilag 2, "one self, many projections"): ``None`` evaluates the
    GLOBAL self-signals against the global baselines/cooldown/hysteresis exactly
    as before. A ``scope`` (e.g. a ``user_id`` or ``"user_id:session"``)
    evaluates USER/SESSION signals against that scope's OWN baselines, cooldown
    and hot-set — so a per-user delta fires only in that user's room and never
    against, nor bleeds into, another scope. When scoped, the returned decision
    carries a ``"scope"`` key so the nudge path can route it.
    """
    try:
        if not signals:
            return None

        # Coerce input; drop non-numeric entries defensively.
        clean: dict[str, float] = {}
        for k, v in signals.items():
            try:
                clean[str(k)] = float(v)
            except Exception:
                continue
        if not clean:
            return None

        baseline = _baseline()

        # --- Cold-start suppression: establish baselines, never fire. ---------
        try:
            cold = _bl_is_cold_start(baseline, scope)
        except Exception:
            cold = False
        if cold:
            for name, val in clean.items():
                try:
                    _bl_set(baseline, name, val, scope)
                except Exception:
                    pass
            return None

        db = _db()
        theta_high = _cfg_float(db, "theta_high", _DEFAULT_THETA_HIGH)
        theta_low = _cfg_float(db, "theta_low", _DEFAULT_THETA_LOW)
        theta_abs = _cfg_float(db, "theta_abs", _DEFAULT_THETA_ABS)
        cooldown_s = _cfg_float(db, "cooldown_s", _DEFAULT_COOLDOWN_S)
        theta_drift = _cfg_float(db, "theta_drift", theta_high)
        drift_dwell = int(_cfg_float(db, "drift_dwell", float(_DEFAULT_DRIFT_DWELL)))
        if drift_dwell < 1:
            drift_dwell = 1
        # Invariant: θ_low < θ_high (else hysteresis degenerates).
        if theta_low >= theta_high:
            theta_low = theta_high / 2.0

        # Per-scope durable state so a global cooldown/hot-set never gates a
        # user's room and vice-versa. None → the original global keys.
        key_last_dispatch = _scoped_key(_KEY_LAST_DISPATCH, scope)
        key_hot = _scoped_key(_KEY_HOT, scope)
        key_drift = _scoped_key(_KEY_DRIFT, scope)

        now = _time.time()
        last_ts = _load_float(db, key_last_dispatch, 0.0)
        in_cooldown = (now - last_ts) < cooldown_s

        hot = _load_hot(db, key_hot)
        drift_state = _load_drift(db, key_drift)

        crossed: list[str] = []
        movements: dict[str, float] = {}
        new_baselines: dict[str, float] = {}
        drift_crossed: list[str] = []
        drift_movements: dict[str, float] = {}
        settle_changed = False  # hot->settled transitions persist independent of dispatch
        drift_changed = False

        for name, val in clean.items():
            # --- Drift-grenen (kører ALTID, også mens signalet er hot) --------
            # Den måler noget andet end spring-grenen: netto afstand til et
            # anker, holdt i θ_dwell sammenhængende aflæsninger. Derfor kan den
            # ikke arve hot-settet — et hot signal er netop et signal der HAR
            # sprunget, og det er ikke det samme som et der driver.
            #
            # Den ligger FØR baseline-tjekket med vilje: et signal der lige er
            # set første gang får `continue` i baseline-grenen, og hvis ankeret
            # blev sat der, ville det først blive sat ved ANDEN aflæsning — så
            # var den første bevægelse usynlig for drift-grenen.
            st = drift_state.get(name)
            if st is None:
                drift_state[name] = {"anchor": val, "away": 0, "side": 0}
                drift_changed = True
            else:
                anchor = float(st.get("anchor", val))
                away = int(st.get("away", 0))
                side = int(st.get("side", 0))
                afstand = val - anchor
                if abs(afstand) >= theta_drift:
                    # `away` maa kun tælle SAMMENHÆNGENDE aflæsninger på SAMME
                    # side af ankeret. Ellers tæller et signal der svinger
                    # 0.0 <-> 0.40 op til dwell og fyrer på ren flapping —
                    # målt 14/11-2026: 13 falske fyringer uden denne spærre.
                    ny_side = 1 if afstand > 0 else -1
                    away = away + 1 if ny_side == side else 1
                    side = ny_side
                    if away >= drift_dwell:
                        drift_crossed.append(name)
                        drift_movements[name] = afstand
                        st["anchor"] = val
                        away = 0
                        side = 0
                else:
                    away = 0
                    side = 0
                st["away"] = away
                st["side"] = side
                drift_changed = True

            b = _bl_get(baseline, name, scope)
            if b is None:
                # Newly seen signal (post cold-start): seed baseline, never fire.
                try:
                    _bl_set(baseline, name, val, scope)
                except Exception:
                    pass
                continue

            absdelta = abs(val - b)

            if hot.get(name, False):
                # Suppressed while hot; can only re-arm once it settles back
                # within θ_low of baseline. This kills flapping around θ_high.
                if absdelta <= theta_low:
                    hot[name] = False
                    settle_changed = True
                continue

            # Cross on delta OR on absolute floor (slow-boil drift).
            #
            # MÅLT 30/10-2026: θ_abs-grenen fyrede UDEN at nogen bevægelse var
            # målt. 201 af 500 samples havde `crossed` ikke-tom mens
            # `movement = max(abs(v) for v in movements.values())` var præcis
            # 0.0. Årsagen er at grenen sammenlignede NIVEAUET (`val`) med
            # gulvet og aldrig så på `absdelta`: et signal der står stille over
            # θ_abs krydser derfor igen og igen, hver gang det er kølet ned,
            # med `movements[name] = val - b = 0`.
            #
            # "Slow-boil" betyder at noget BEVÆGER sig langsomt — ikke at det
            # står stille højt. Grenen kræver derfor en delta; et helt statisk
            # signal er pr. definition ingen ændring og skal ikke dispatche.
            if absdelta >= theta_high or (val >= theta_abs and absdelta > 0.0):
                crossed.append(name)
                movements[name] = val - b
                new_baselines[name] = val

        # Drift må ikke dobbelt-tælle et signal spring-grenen allerede fangede:
        # et spring ER en stor nok netto-bevægelse, og to fyringer for samme
        # hændelse ville gøre triggeren dyrere end den timer den erstatter.
        drift_only = [n for n in drift_crossed if n not in crossed]

        # --- Dispatch decision (composite-coalesced) --------------------------
        if (crossed or drift_only) and not in_cooldown:
            crossed_sorted = sorted(crossed)
            for name in crossed_sorted:
                # Advance baseline to the new value and arm hysteresis.
                try:
                    _bl_set(baseline, name, new_baselines[name], scope)
                except Exception:
                    pass
                hot[name] = True
            _store_hot(db, hot, key_hot)
            _store_drift(db, drift_state, key_drift)
            _store_float(db, key_last_dispatch, now)
            all_crossed = sorted(set(crossed_sorted) | set(drift_only))
            all_movements = {n: movements[n] for n in crossed_sorted}
            all_movements.update({n: drift_movements[n] for n in drift_only})
            decision = {
                "crossed": all_crossed,
                "movements": all_movements,
                "reason": _reason(all_crossed, all_movements, theta_abs),
            }
            if drift_only:
                decision["drift"] = sorted(drift_only)
            if scope is not None:
                decision["scope"] = str(scope)
            return decision

        # No dispatch (nothing crossed, or crossed-but-in-cooldown). We do NOT
        # advance baselines or arm hot for the crossed-but-cooled signals — the
        # change stays "pending" and can fire once cooldown expires. Only the
        # settle transitions (hysteresis release) and the drift bookkeeping are
        # durably persisted.
        if settle_changed:
            _store_hot(db, hot, key_hot)
        if drift_changed:
            _store_drift(db, drift_state, key_drift)
        return None
    except Exception:
        # Self-safe: any failure must NOT fire (fail-closed).
        return None
