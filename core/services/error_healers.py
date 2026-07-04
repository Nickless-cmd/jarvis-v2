"""HEALER-REGISTRET (Canonical Error System, Fase 1) — det eneste ægte NYE backend-stykke.

Én kanonisk fejl (`kind` fra `central_error_envelope`) → én healer der forsøger at HELBREDE
tilstanden bag fejlen. Modsat resten af error-systemet (der gør en fejl SYNLIG) forsøger
en healer at RETTE den. Derfor er sikkerhed altafgørende:

  SIKKERHEDS-DOKTRIN (læs FØR du tænder noget):
  ─────────────────────────────────────────────
  1. SHADOW-FIRST for alt destruktivt. En healer der laver root-/genstart-handlinger
     (systemctl restart af daemons, pfSense-syslogd-genstart) EKSEKVERER IKKE som default.
     Den BEREGNER planen, skriver den som nerve + incident, og returnerer SHADOW.
     Kun hvis (a) et eksplicit per-healer live-flag er ON  OG  (b) central().decide med
     GateClass.SECURITY returnerer GREEN → må den eksekvere. Gaten fail-closer til RED.
  2. AUTO-RESTART-LØKKER er en reel fare. Derfor er max_attempts + cooldown + circuit-
     breaker OBLIGATORISK pr. (kind, origin). Efter max_attempts → ESCALATE (ingen flere
     forsøg), bump incident. Cooldown undertrykker et gentaget forsøg inden for vinduet.
  3. GLOBAL default OFF. `error_healers_enabled` (via central_switches) er default OFF for
     HELE registret. Når OFF → dispatcher registrerer would-heal + returnerer SHADOW.
     Bjørn tænder eksplicit når han er tryg. Selv når globalt ON er destruktive healers
     STADIG shadow bag deres eget live-flag + gate.
  4. SELF-SAFE overalt. En healer må ALDRIG kaste ind i error-stien (det er per definition
     allerede en fejl-situation). Alt wrappet; ukendt/brudt healer → UNKNOWN, aldrig raise.

  LIVE vs SHADOW-FIRST (se også modul-bunden `HEALER_LIVENESS`):
  ─────────────────────────────────────────────
  * CircuitResetHealer     (central.circuit_open) → LIVE. Nulstiller en in-memory breaker.
                            Ingen root, ingen ekstern effekt, fuldt reversibel. SIKKER.
  * DaemonRestartHealer    (central.daemon_dead)  → SHADOW-FIRST. `sudo systemctl restart`
                            kræver root → aldrig bar systemctl. Flag+gate.
  * SyslogRestartHealer    (infra.syslogd_dead)   → SHADOW-FIRST. Der findes INTET
                            eksisterende genstart-endpoint (pfsense_syslog er read-only
                            listener) → ren shadow indtil et gated restart-kald bygges.
  * DelegatedHealer        (provider.unavailable, model.rate_limited, network.timeout,
                            tool.timeout) → NO-OP. Selve retry/failover sker IN-BAND i
                            visible_runs/kalderen; healeren registrerer blot "handled
                            in-band" og gør INTET centralt (ingen dobbelt-failover-race).
"""
from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from core.services.gate_kernel import Decision, GateClass


# ═══════════════════════════════════════════════════════════════════════════
# Resultat-type
# ═══════════════════════════════════════════════════════════════════════════
class HealingOutcome(enum.Enum):
    SUCCESS = "success"    # tilstanden blev helbredt (fx breaker nulstillet)
    RETRY = "retry"        # ikke helbredt her, men kalderen bør prøve igen (in-band)
    ESCALATE = "escalate"  # opgivet (max forsøg nået / uhelbredelig) → bump incident
    SHADOW = "shadow"      # planen beregnet + registreret, men IKKE eksekveret (skygge)
    UNKNOWN = "unknown"    # ingen healer / healer brød sammen — aldrig en raise


@dataclass
class HealingResult:
    """Struktureret svar fra en heal(). `detail` er menneske-læsbar (til nerve/incident)."""
    outcome: HealingOutcome
    detail: str = ""
    plan: str = ""          # for shadow/destruktive: den handling der VILLE være kørt
    attempts: int = 0       # forsøgstæller på (kind, origin) EFTER dette kald

    def __bool__(self) -> bool:  # bekvem: `if result:` = helbredt
        return self.outcome is HealingOutcome.SUCCESS


# ═══════════════════════════════════════════════════════════════════════════
# Flag-læsning (self-safe, default-OFF for healer-flag — modsat live-switches)
# ═══════════════════════════════════════════════════════════════════════════
_FLAG_TTL = 365 * 24 * 3600.0


def _flag_on(name: str, *, default: bool = False) -> bool:
    """Læs et healer-flag fra shared_cache. Default OFF (healers tændes eksplicit).
    Self-safe: enhver cache-fejl → default (konservativt OFF for destruktivt)."""
    try:
        from core.services import shared_cache
        val = shared_cache.get(f"flag:error_healer.{name}")
        if isinstance(val, dict) and "enabled" in val:
            return bool(val["enabled"])
        if isinstance(val, bool):
            return val
    except Exception:
        pass
    return default


def set_healer_flag(name: str, enabled: bool) -> dict:
    """Tænd/sluk et healer-flag live (til Bjørn/MC). Self-safe."""
    try:
        from core.services import shared_cache
        shared_cache.set(f"flag:error_healer.{name}", {"enabled": bool(enabled)},
                         ttl_seconds=_FLAG_TTL)
        return {"ok": True, "name": name, "enabled": bool(enabled)}
    except Exception as e:
        return {"ok": False, "name": name, "error": type(e).__name__}


# Globalt registret-flag + per-destruktiv-healer live-flag. ALLE default OFF.
_GLOBAL_FLAG = "enabled"                      # error_healer.enabled
_DAEMON_LIVE_FLAG = "daemon_restart_live"     # error_healer.daemon_restart_live
_SYSLOG_LIVE_FLAG = "syslog_restart_live"     # error_healer.syslog_restart_live


def healers_enabled() -> bool:
    """Er HELE registret tændt? Default OFF — dispatcher shadow'er indtil Bjørn tænder."""
    return _flag_on(_GLOBAL_FLAG, default=False)


# ═══════════════════════════════════════════════════════════════════════════
# Forsøgs-/cooldown-bogholderi pr. (kind, origin) — obligatorisk løkke-værn
# ═══════════════════════════════════════════════════════════════════════════
@dataclass
class _AttemptState:
    attempts: int = 0
    last_ts: float = 0.0


class _AttemptLedger:
    """In-memory tæller + cooldown pr. (kind, origin). Nulstilles ved proces-genstart
    (bevidst: genstart = frisk start, ligesom CircuitBreaker.open_nerves-noten). Tråd-sikker."""

    def __init__(self) -> None:
        self._state: dict[tuple[str, str], _AttemptState] = {}
        self._lock = threading.Lock()

    def _key(self, kind: str, origin: str) -> tuple[str, str]:
        return (str(kind or ""), str(origin or ""))

    def in_cooldown(self, kind: str, origin: str, cooldown_seconds: int) -> bool:
        with self._lock:
            st = self._state.get(self._key(kind, origin))
            if st is None or st.last_ts <= 0:
                return False
            return (time.monotonic() - st.last_ts) < max(0, cooldown_seconds)

    def attempts(self, kind: str, origin: str) -> int:
        with self._lock:
            st = self._state.get(self._key(kind, origin))
            return st.attempts if st else 0

    def record_attempt(self, kind: str, origin: str) -> int:
        """Registrér ét forsøg (nu). Returnér ny total."""
        with self._lock:
            k = self._key(kind, origin)
            st = self._state.get(k) or _AttemptState()
            st.attempts += 1
            st.last_ts = time.monotonic()
            self._state[k] = st
            return st.attempts

    def reset(self, kind: str, origin: str) -> None:
        """Nulstil ved SUCCESS — tilstanden er helbredt, tælleren skal ikke hænge."""
        with self._lock:
            self._state.pop(self._key(kind, origin), None)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {f"{k[0]}|{k[1]}": {"attempts": v.attempts, "last_ts": v.last_ts}
                    for k, v in self._state.items()}


_LEDGER = _AttemptLedger()


# ═══════════════════════════════════════════════════════════════════════════
# Base-healer
# ═══════════════════════════════════════════════════════════════════════════
class ErrorHealer:
    """Base for alle healers. Underklasser overrider `_do_heal(...)`.

    Kontrakt:
      * `kind`            — canonical error-kind healeren dækker.
      * `max_attempts`    — efter dette antal forsøg pr. (kind, origin) → ESCALATE.
      * `cooldown_seconds`— minimum mellem to forsøg pr. (kind, origin).
      * `destructive`     — True ⇒ SHADOW-FIRST: kræver live-flag + SECURITY-GREEN for at
                            eksekvere; ellers ren skygge (plan registreret, intet kørt).
    """

    kind: str = ""
    max_attempts: int = 3
    cooldown_seconds: int = 60
    destructive: bool = False
    # per-destruktiv-healer live-flag-navn (subklasser sætter). "" ⇒ ingen live-sti.
    live_flag: str = ""

    # ── skygge-gate for destruktive handlinger ─────────────────────────────
    def _may_execute_destructive(self, ctx: dict[str, Any]) -> tuple[bool, str]:
        """Returnér (må_eksekvere, grund). To betingelser SKAL begge være opfyldt:
          1. per-healer live-flag ON (default OFF), OG
          2. central().decide(SECURITY) → GREEN (fail-closer til RED = deny).
        Self-safe: enhver fejl → (False, grund) → forbliv i skygge (fail-closed)."""
        if not self.destructive:
            return True, "non-destructive"
        # (1) live-flag
        try:
            if not self.live_flag or not _flag_on(self.live_flag, default=False):
                return False, "live_flag_off"
        except Exception:
            return False, "live_flag_error"
        # (2) SECURITY-gate — fail-closed
        try:
            from core.services.central_core import central
            verdict = central().decide(
                f"heal.execute.{self.kind}", ctx,
                lambda c: Decision.GREEN,   # nerven "vil" tillade; gaten kan stadig deny'e
                cluster="execution", klass=GateClass.SECURITY,
            )
            if verdict.decision is Decision.GREEN:
                return True, "gate_green"
            return False, f"gate_{verdict.decision.value}"
        except Exception:
            return False, "gate_error"  # fail-closed: gate-fejl = deny

    # ── overrides ──────────────────────────────────────────────────────────
    def _plan(self, ctx: dict[str, Any]) -> str:
        """Menneske-læsbar beskrivelse af hvad healeren VILLE gøre (til shadow-log)."""
        return f"heal({self.kind})"

    def _do_heal(self, ctx: dict[str, Any]) -> HealingResult:
        """Den faktiske helbredelse. Kaldes KUN når løkke-værn er passeret.
        For destruktive: tjek self._may_execute_destructive FØR nogen sideeffekt."""
        raise NotImplementedError

    # ── offentlig indgang (aldrig raise) ──────────────────────────────────
    def heal(self, ctx: dict[str, Any]) -> HealingResult:
        origin = str(ctx.get("origin") or "")
        try:
            # 1) cooldown-værn
            if _LEDGER.in_cooldown(self.kind, origin, self.cooldown_seconds):
                return HealingResult(HealingOutcome.SHADOW, detail="cooldown",
                                     attempts=_LEDGER.attempts(self.kind, origin))
            # 2) max-attempts-værn → ESCALATE (ingen flere forsøg)
            if _LEDGER.attempts(self.kind, origin) >= self.max_attempts:
                return HealingResult(HealingOutcome.ESCALATE, detail="max_attempts",
                                     attempts=_LEDGER.attempts(self.kind, origin))
            # 3) tæl forsøget FØR handling (så et brud stadig tæller mod loftet)
            n = _LEDGER.record_attempt(self.kind, origin)
            res = self._do_heal(ctx)
            res.attempts = n
            # SUCCESS nulstiller bogholderiet (tilstand helbredt)
            if res.outcome is HealingOutcome.SUCCESS:
                _LEDGER.reset(self.kind, origin)
            return res
        except Exception as e:  # self-safe: aldrig raise ind i error-stien
            return HealingResult(HealingOutcome.UNKNOWN, detail=f"healer_error:{type(e).__name__}")


# ═══════════════════════════════════════════════════════════════════════════
# Konkrete healers
# ═══════════════════════════════════════════════════════════════════════════
class CircuitResetHealer(ErrorHealer):
    """central.circuit_open → LIVE + SIKKER. Nulstiller den in-memory CircuitBreaker for
    nerven (central()._breaker.reset). Ingen root, ingen ekstern effekt, fuldt reversibel.
    Derfor den ENESTE healer der må handle live uden flag/gate."""

    kind = "central.circuit_open"
    max_attempts = 3
    cooldown_seconds = 30
    destructive = False

    def _plan(self, ctx: dict[str, Any]) -> str:
        return f"reset circuit-breaker for nerve={ctx.get('nerve') or ctx.get('origin') or '?'}"

    def _do_heal(self, ctx: dict[str, Any]) -> HealingResult:
        nerve = str(ctx.get("nerve") or ctx.get("origin") or "")
        if not nerve:
            return HealingResult(HealingOutcome.ESCALATE, detail="no_nerve_to_reset")
        try:
            from core.services.central_core import central
            central()._breaker.reset(nerve)
            still_open = central()._breaker.is_open(nerve)
        except Exception as e:
            return HealingResult(HealingOutcome.UNKNOWN, detail=f"reset_failed:{type(e).__name__}")
        if still_open:
            return HealingResult(HealingOutcome.RETRY, detail=f"breaker_still_open:{nerve}")
        return HealingResult(HealingOutcome.SUCCESS, detail=f"breaker_reset:{nerve}")


class DaemonRestartHealer(ErrorHealer):
    """central.daemon_dead → DESTRUKTIV, SHADOW-FIRST. `sudo systemctl restart jarvis-<unit>`
    kræver root → ALDRIG bar systemctl. Default: beregn planen, registrér den, returnér SHADOW.
    Eksekvér KUN hvis error_healer.daemon_restart_live=ON OG SECURITY-gate=GREEN.

    Kun kendte jarvis-units tillades (spejler restart_self_tools.ALLOWED_SERVICES)."""

    kind = "central.daemon_dead"
    max_attempts = 2               # meget lavt loft: en daemon der bliver ved at dø må IKKE loop-genstartes
    cooldown_seconds = 300         # 5 min mellem genstartsforsøg
    destructive = True
    live_flag = _DAEMON_LIVE_FLAG

    _ALLOWED_UNITS = {"jarvis-api", "jarvis-runtime", "jarvis-api-workers"}

    def _unit(self, ctx: dict[str, Any]) -> str:
        raw = str(ctx.get("unit") or ctx.get("daemon") or ctx.get("origin") or "").strip()
        if not raw:
            return ""
        unit = raw if raw.startswith("jarvis-") else f"jarvis-{raw}"
        return unit if unit in self._ALLOWED_UNITS else ""

    def _plan(self, ctx: dict[str, Any]) -> str:
        unit = self._unit(ctx) or "?"
        return f"sudo systemctl restart {unit}"

    def _do_heal(self, ctx: dict[str, Any]) -> HealingResult:
        unit = self._unit(ctx)
        plan = self._plan(ctx)
        if not unit:
            # ukendt/utilladt unit → aldrig gæt, aldrig eksekvér
            return HealingResult(HealingOutcome.ESCALATE, detail="unknown_or_disallowed_unit", plan=plan)
        may, why = self._may_execute_destructive(ctx)
        if not may:
            # SKYGGE: registrér intentionen, kør INTET
            return HealingResult(HealingOutcome.SHADOW, detail=f"shadow:{why}", plan=plan)
        # LIVE-sti (flag ON + gate GREEN) — stadig via den detacherede, kendte restart-sti
        try:
            import subprocess
            subprocess.Popen(
                ["bash", "-c", f"sleep 2 && sudo systemctl restart {unit}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            return HealingResult(HealingOutcome.UNKNOWN, detail=f"restart_failed:{type(e).__name__}", plan=plan)
        return HealingResult(HealingOutcome.SUCCESS, detail=f"restart_scheduled:{unit}", plan=plan)


class SyslogRestartHealer(ErrorHealer):
    """infra.syslogd_dead → DESTRUKTIV, SHADOW-FIRST. VIGTIGT: der findes INTET eksisterende
    genstart-endpoint — `pfsense_syslog` er en ren read-only UDP-lytter (ingen pfSense-API-
    skrivning). Derfor er denne healer i praksis PURE-SHADOW indtil et gated restart-kald
    bygges. Hvis en `pfsense_syslog.restart_syslogd` en dag dukker op, delegerer vi til den
    (flag+gate); ellers registrerer vi kun planen."""

    kind = "infra.syslogd_dead"
    max_attempts = 2
    cooldown_seconds = 300
    destructive = True
    live_flag = _SYSLOG_LIVE_FLAG

    def _plan(self, ctx: dict[str, Any]) -> str:
        host = str(ctx.get("host") or "pfSense (10.0.0.1)")
        return f"restart syslogd on {host} (via pfSense API/ssh — endpoint not yet built)"

    def _do_heal(self, ctx: dict[str, Any]) -> HealingResult:
        plan = self._plan(ctx)
        may, why = self._may_execute_destructive(ctx)
        if not may:
            return HealingResult(HealingOutcome.SHADOW, detail=f"shadow:{why}", plan=plan)
        # Delegér KUN hvis et ægte restart-endpoint findes. Reinventér ALDRIG en root-sti her.
        try:
            from core.services import pfsense_syslog as _ps
            restart_fn = getattr(_ps, "restart_syslogd", None)
        except Exception:
            restart_fn = None
        if not callable(restart_fn):
            return HealingResult(HealingOutcome.SHADOW,
                                 detail="no_restart_endpoint_yet", plan=plan)
        try:
            restart_fn()
        except Exception as e:
            return HealingResult(HealingOutcome.UNKNOWN, detail=f"delegate_failed:{type(e).__name__}", plan=plan)
        return HealingResult(HealingOutcome.SUCCESS, detail="syslogd_restart_delegated", plan=plan)


class DelegatedHealer(ErrorHealer):
    """In-band kinds (provider.unavailable, model.rate_limited, network.timeout, tool.timeout).
    Selve retry/failover sker IN-BAND i visible_runs/kalderen (per-run failover-loop +
    provider-breaker). En central out-of-band healer VILLE race på samme breaker → skade.
    Derfor: gør INTET centralt; registrér blot "handled in-band" og returnér RETRY (signal
    til kalderen om at den in-band-sti ejer det). Ikke-destruktiv, intet loop-værn nødvendigt
    (men arves alligevel)."""

    max_attempts = 999             # in-band ejer retry-loftet; vi tæller ikke reelt imod
    cooldown_seconds = 0
    destructive = False

    def __init__(self, kind: str) -> None:
        self.kind = kind

    def _plan(self, ctx: dict[str, Any]) -> str:
        return f"delegate {self.kind} to in-band handler (visible_runs/caller)"

    def _do_heal(self, ctx: dict[str, Any]) -> HealingResult:
        return HealingResult(HealingOutcome.RETRY, detail="handled_in_band",
                             plan=self._plan(ctx))


# ═══════════════════════════════════════════════════════════════════════════
# Registret + dispatcher
# ═══════════════════════════════════════════════════════════════════════════
HEALER_REGISTRY: dict[str, ErrorHealer] = {}


def register_healer(healer: ErrorHealer) -> None:
    """Registrér en healer på dens `kind`. Self-safe (ignorér healer uden kind)."""
    try:
        if healer and healer.kind:
            HEALER_REGISTRY[healer.kind] = healer
    except Exception:
        pass


def _register_defaults() -> None:
    register_healer(CircuitResetHealer())
    register_healer(DaemonRestartHealer())
    register_healer(SyslogRestartHealer())
    for k in ("provider.unavailable", "model.rate_limited",
              "network.timeout", "tool.timeout"):
        register_healer(DelegatedHealer(k))


_register_defaults()


# Metadata til MC / dokumentation — hvilke er LIVE vs SHADOW-FIRST og hvorfor.
HEALER_LIVENESS: dict[str, dict[str, str]] = {
    "central.circuit_open": {"mode": "LIVE", "why": "in-memory breaker-reset; ingen root, reversibel"},
    "central.daemon_dead": {"mode": "SHADOW-FIRST", "why": "sudo systemctl restart kræver root"},
    "infra.syslogd_dead": {"mode": "SHADOW-FIRST", "why": "intet restart-endpoint findes; pfsense_syslog er read-only"},
    "provider.unavailable": {"mode": "DELEGATED", "why": "failover in-band i visible_runs"},
    "model.rate_limited": {"mode": "DELEGATED", "why": "retry in-band"},
    "network.timeout": {"mode": "DELEGATED", "why": "retry in-band"},
    "tool.timeout": {"mode": "DELEGATED", "why": "retry in-band"},
}


def _observe_heal(kind: str, origin: str, run_id: str, result: HealingResult,
                  *, global_off: bool) -> None:
    """Registrér healing-udfaldet som nerve `heal/<kind>`. Self-safe."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "healing",
            "nerve": f"heal/{kind}",
            "kind": "heal",
            "outcome": result.outcome.value,
            "origin": origin,
            "run_id": run_id,
            "attempts": result.attempts,
            "plan": result.plan,
            "detail": result.detail,
            "global_off": bool(global_off),
        })
    except Exception:
        pass


def _resolve_incident_for(kind: str, origin: str) -> None:
    """Ved SUCCESS: luk stående incidents for healing-nerven. Self-safe."""
    try:
        from core.runtime.db_central_incidents import resolve_central_incidents
        resolve_central_incidents(cluster="healing", nerve=f"heal/{kind}")
    except Exception:
        pass


def _escalate_incident_for(kind: str, origin: str, run_id: str, detail: str) -> None:
    """Ved ESCALATE: bump/opret en incident så det bliver menneske-synligt. Self-safe."""
    try:
        from core.runtime.db_central_incidents import (
            bump_open_incident, record_central_incident)
        if not bump_open_incident(cluster="healing", nerve=f"heal/{kind}",
                                  run_id=run_id, note=detail):
            record_central_incident(cluster="healing", nerve=f"heal/{kind}",
                                    kind="heal_escalated", severity="error",
                                    message=f"healer opgav {kind} ({detail})", run_id=run_id)
    except Exception:
        pass


def heal_error(kind: str, *, origin: str = "", run_id: str = "",
               detail: str = "", **ctx_extra: Any) -> HealingResult:
    """Dispatcher — slå healer op på `kind` og forsøg helbredelse. ALDRIG raise.

    Rækkefølge af værn:
      1. Ukendt kind → UNKNOWN (ingen healer).
      2. GLOBAL flag OFF (default) → registrér would-heal + returnér SHADOW (intet kørt).
      3. Ellers → healer.heal(ctx) (som selv håndterer cooldown/max-attempts/gate/shadow).
      4. Registrér udfald som nerve heal/<kind>; SUCCESS→resolve incident, ESCALATE→bump.
    """
    kind = str(kind or "")
    healer = HEALER_REGISTRY.get(kind)
    if healer is None:
        result = HealingResult(HealingOutcome.UNKNOWN, detail="no_healer_for_kind")
        _observe_heal(kind, origin, run_id, result, global_off=False)
        return result

    ctx: dict[str, Any] = {"kind": kind, "origin": origin, "run_id": run_id,
                           "detail": detail, **ctx_extra}
    # også praktisk: mange healers vil læse `nerve`/`unit` — udled fra origin hvis ikke sat
    ctx.setdefault("nerve", origin)

    global_off = not healers_enabled()
    if global_off:
        # HELE registret er slukket → skygge. Beregn plan til log, kør INTET.
        try:
            plan = healer._plan(ctx)
        except Exception:
            plan = ""
        result = HealingResult(HealingOutcome.SHADOW, detail="registry_disabled", plan=plan)
        _observe_heal(kind, origin, run_id, result, global_off=True)
        return result

    result = healer.heal(ctx)
    _observe_heal(kind, origin, run_id, result, global_off=False)
    if result.outcome is HealingOutcome.SUCCESS:
        _resolve_incident_for(kind, origin)
    elif result.outcome is HealingOutcome.ESCALATE:
        _escalate_incident_for(kind, origin, run_id, result.detail)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# MC-overflade
# ═══════════════════════════════════════════════════════════════════════════
def build_healer_surface() -> dict[str, Any]:
    """Læsbar tilstand til Mission Control: hvilke healers findes, deres mode/flag, og
    det aktuelle forsøgs-bogholderi. Self-safe — kaster aldrig, returnerer altid en dict."""
    try:
        healers: list[dict[str, Any]] = []
        for kind, h in sorted(HEALER_REGISTRY.items()):
            meta = HEALER_LIVENESS.get(kind, {})
            healers.append({
                "kind": kind,
                "mode": meta.get("mode", "DELEGATED"),
                "why": meta.get("why", ""),
                "destructive": bool(h.destructive),
                "max_attempts": h.max_attempts,
                "cooldown_seconds": h.cooldown_seconds,
                "live_flag": h.live_flag or "",
                "live_flag_on": _flag_on(h.live_flag, default=False) if h.live_flag else None,
            })
        return {
            "registry_enabled": healers_enabled(),
            "global_flag": f"error_healer.{_GLOBAL_FLAG}",
            "healers": healers,
            "attempt_ledger": _LEDGER.snapshot(),
        }
    except Exception as e:
        return {"error": type(e).__name__, "registry_enabled": False, "healers": []}


def _reset_for_tests() -> None:
    """Nulstil bogholderi + gen-registrér defaults (til tests). Self-safe."""
    global _LEDGER
    _LEDGER = _AttemptLedger()
    HEALER_REGISTRY.clear()
    _register_defaults()
