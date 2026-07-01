"""Anomali-detektor — fanger de fejl Centralen IKKE selv har en nerve til endnu.

Centralens 113 nerver fanger KENDTE fejl-punkter. Men der findes fejl der er usynlige:
uinstrumenterede kode-stier, helt nye fejl-mønstre, og fejl UDEN FOR Centralen (uhåndterede
exceptions, ERROR-logs ingen nerve dækker). Dette modul er sikkerhedsnettet under nettet:

  GLOBALE HOOKS (sys.excepthook + threading.excepthook + asyncio + root-ERROR-log)
        → KLASSIFICÉR (kategori + importance: low/medium/high/critical)
        → DEFINÉR (ny signatur = ny fejl-type Centralen netop lærte; db_anomalies UPSERT)
        → FLAG (første sigtning af high/critical → central incident + observe)
        → LÆR (recurring → central_learning's rod-årsager/forslag fanger dem)

Selv-sikker + reentrancy-guard: at fange en fejl må ALDRIG udløse en ny fejl (uendelig
løkke), og må aldrig vælte processen. Importance-heuristik er deterministisk.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

_installed = False
_guard = threading.local()              # reentrancy-flag (undgå anomali-om-anomali)
_cooldown: dict[str, float] = {}        # signatur → sidste DB-skriv (monotonic); beskytter DB
_COOLDOWN_S = 12.0
_RE_HEX = re.compile(r"\b[0-9a-f]{8,}\b", re.I)
_RE_NUM = re.compile(r"\d+")
_RE_PATH = re.compile(r"(/[\w.\-]+)+")
_RE_ADDR = re.compile(r"0x[0-9a-f]+", re.I)

# Loggere/moduler vi ALDRIG må fange fra (egne stier → rekursion, eller allerede-nervede
# støj-kilder der ville oversvømme registeret).
_SKIP_PREFIXES = (
    "core.services.central_anomaly", "core.runtime.db_anomalies",
    "core.runtime.db_central_incidents", "core.services.central_core",
    "core.services.central_trace", "core.services.central_switches",
)

# Importance-signaler (deterministisk klassifikation).
_CRITICAL_HINTS = ("security", "permission denied", "unauthorized", "leak", "corrupt",
                   "data loss", "datatab", "secret", "credential", "fail-open", "fail_open")
_HIGH_TYPES = {"KeyError", "AttributeError", "TypeError", "RecursionError",
               "AssertionError", "UnboundLocalError", "IndexError", "NameError"}
_CRITICAL_TYPES = {"MemoryError", "SystemError"}
_LOW_HINTS = ("timeout", "timed out", "connection", "temporarily", "rate limit",
              "rate-limit", "429", "retry", "unavailable", "econnreset", "broken pipe")


def _signature(category: str, message: str) -> str:
    """Stabil signatur: kategori + normaliseret besked (strip id'er/tal/stier/adresser)."""
    m = str(message or "")
    m = _RE_ADDR.sub("<addr>", m)
    m = _RE_HEX.sub("<id>", m)
    m = _RE_PATH.sub("<path>", m)
    m = _RE_NUM.sub("<n>", m)
    return f"{category}|{' '.join(m.split())[:140]}"


def _classify(exc_type: str, message: str, source: str) -> tuple[str, str]:
    """→ (kategori, importance). Deterministisk."""
    et = str(exc_type or "Error").strip() or "Error"
    low_msg = str(message or "").lower()
    # importance
    if et in _CRITICAL_TYPES or any(h in low_msg for h in _CRITICAL_HINTS):
        importance = "critical"
    elif source in ("uncaught", "thread", "asyncio") or et in _HIGH_TYPES:
        importance = "high"
    elif any(h in low_msg for h in _LOW_HINTS):
        importance = "low"
    else:
        importance = "medium"
    # kategori: kilde + exception-type (menneskelæsbar, stabil)
    category = f"{source}:{et}" if source else et
    return category, importance


def _tb_location(tb: Any) -> str:
    """Sidste frame i et traceback → 'fil:linje in funktion' (HVOR fejlede den). Self-safe."""
    try:
        import traceback as _tbmod
        frames = _tbmod.extract_tb(tb)
        if not frames:
            return ""
        last = frames[-1]
        fn = str(last.filename or "")
        # kort repo-relativ sti
        if "/jarvis-v2/" in fn:
            fn = fn.split("/jarvis-v2/", 1)[1]
        return f"{fn}:{last.lineno} in {last.name}"
    except Exception:
        return ""


def _full_trace(tb: Any) -> str:
    """Fuld stack trace (sidste 15 frames) som formateret streng, max 2000 tegn. Self-safe.
    R1: dokumentér ALT ved en ukendt fejl — ikke kun sidste frame — så rod-årsagen kan
    diagnosticeres uden manuelt gravearbejde."""
    try:
        import traceback as _tbmod
        frames = _tbmod.extract_tb(tb)
        if not frames:
            return ""
        return "".join(_tbmod.format_list(frames[-15:]))[:2000]
    except Exception:
        return ""


def record_anomaly(*, source: str, exc_type: str, message: str, module: str = "",
                   location: str = "", trace: str = "") -> None:
    """Klassificér + registrér én udefineret fejl + HVOR (lokation) + fuld trace. Self-safe +
    reentrancy-beskyttet. Hvis signaturen allerede er et KENDT signal (§4), routes/optælles den
    i stedet for at logge som ukendt anomali."""
    if getattr(_guard, "busy", False):
        return
    _guard.busy = True
    try:
        if module and any(module.startswith(p) for p in _SKIP_PREFIXES):
            return
        category, importance = _classify(exc_type, message, source)
        sig = _signature(category, message)
        now = time.monotonic()
        last = _cooldown.get(sig)
        if last is not None and (now - last) < _COOLDOWN_S:
            return                       # samme signatur lige registreret → skån DB
        _cooldown[sig] = now
        if len(_cooldown) > 4000:        # soft cap
            _cooldown.clear()
        # ── KENDT SIGNAL? (§4 — tjek FØR anomaly-log) ────────────────────────
        # En promoveret signatur skal ikke længere stå som "ukendt". Afhængig af
        # action route'es den til den rigtige nerve / optælles bare / falder igennem.
        try:
            from core.runtime.db_anomalies import (
                get_known_signal, bump_known_signal_count,
            )
            known = get_known_signal(sig)
        except Exception:
            known = None
        if known:
            act = str(known.get("action") or "observe")
            if act in ("route_to_nerve", "log_as_known"):
                try:
                    bump_known_signal_count(sig)
                except Exception:
                    pass
                if act == "route_to_nerve":
                    try:
                        from core.services.central_core import central
                        central().observe({
                            "cluster": str(known.get("cluster") or "anomaly"),
                            "nerve": str(known.get("nerve") or category),
                            "category": category, "importance": importance,
                            "source": source, "location": location,
                            "known_signal": True})
                    except Exception:
                        pass
                return  # håndteret som kendt signal → IKKE som anomali
            # act == "observe" → "under observation": fald igennem til normal anomaly-log
        # ── Ukendt → normal anomaly-log (dokumentér ALT: trace + location) ───
        _sample = str(message or "")[:480]
        if trace:
            _sample = (_sample + "\n--- trace ---\n" + str(trace))[:2000]
        from core.runtime.db_anomalies import record_anomaly_signature
        is_new = record_anomaly_signature(
            signature=sig, category=category, importance=importance,
            source=str(source or ""), sample=_sample,
            location=str(location or ""))
        # observe (synligt i Centralen som anomali-cluster) — nu MED hvor (lokation)
        try:
            from core.services.central_core import central
            central().observe({"cluster": "anomaly", "nerve": "undefined_error",
                               "category": category, "importance": importance,
                               "is_new": is_new, "source": source, "location": location})
        except Exception:
            pass
        # anomaly.captured → eventbus (spec §3.0): så andre subscribers + både-veje ser
        # signalet i realtid (bro'en router 'anomaly'-familien). Self-safe.
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish("anomaly.captured", {
                "signature": sig, "category": category, "importance": importance,
                "is_new": is_new, "location": str(location or ""), "source": str(source or "")})
        except Exception:
            pass
        # Eskalér til persistent incident KUN ved første sigtning af high/critical
        # (så incident-loggen ikke spammes; registeret holder det fulde billede).
        if is_new and importance in ("high", "critical"):
            try:
                from core.runtime.db_central_incidents import record_central_incident
                _loc = f" @ {location}" if location else ""
                record_central_incident(
                    cluster="anomaly", nerve=category, kind="undefined_error",
                    severity="severe" if importance == "critical" else "error",
                    message=f"NY udefineret fejl ({importance}){_loc}: {message}"[:400])
            except Exception:
                pass
    except Exception:
        pass
    finally:
        _guard.busy = False


class _AnomalyLogHandler(logging.Handler):
    """Fanger ERROR/CRITICAL-logs ingen nerve dækker → record_anomaly."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno < logging.ERROR:
                return
            name = record.name or ""
            if any(name.startswith(p) for p in _SKIP_PREFIXES):
                return
            exc_type = "Error"
            loc = ""
            trace = ""
            if record.exc_info and record.exc_info[0] is not None:
                exc_type = record.exc_info[0].__name__
                loc = _tb_location(record.exc_info[2])   # hvor exception'en faktisk skete
                trace = _full_trace(record.exc_info[2])
            if not loc:
                # ellers: hvor log-linjen blev emitteret fra (stadig HVOR)
                fn = str(getattr(record, "pathname", "") or "")
                if "/jarvis-v2/" in fn:
                    fn = fn.split("/jarvis-v2/", 1)[1]
                loc = f"{fn}:{getattr(record, 'lineno', '?')}" if fn else ""
            record_anomaly(source="log", exc_type=exc_type,
                           message=record.getMessage(), module=name, location=loc, trace=trace)
        except Exception:
            pass


def install_hooks() -> dict[str, Any]:
    """Installér globale fang-hooks (idempotent). Kaldes ved proces-start."""
    global _installed
    if _installed:
        return {"installed": False, "reason": "allerede installeret"}
    import sys
    try:
        _prev_excepthook = sys.excepthook

        def _excepthook(exc_type, exc, tb):
            try:
                record_anomaly(source="uncaught", exc_type=getattr(exc_type, "__name__", "Error"),
                               message=str(exc), location=_tb_location(tb), trace=_full_trace(tb),
                               module=getattr(getattr(tb, "tb_frame", None),
                                              "f_globals", {}).get("__name__", ""))
            except Exception:
                pass
            try:
                _prev_excepthook(exc_type, exc, tb)
            except Exception:
                pass

        sys.excepthook = _excepthook
    except Exception:
        pass
    try:
        _prev_thook = getattr(threading, "excepthook", None)

        def _thook(args):
            try:
                record_anomaly(source="thread",
                               exc_type=getattr(args.exc_type, "__name__", "Error"),
                               message=str(args.exc_value),
                               location=_tb_location(getattr(args, "exc_traceback", None)),
                               trace=_full_trace(getattr(args, "exc_traceback", None)))
            except Exception:
                pass
            if _prev_thook:
                try:
                    _prev_thook(args)
                except Exception:
                    pass

        threading.excepthook = _thook
    except Exception:
        pass
    try:
        root = logging.getLogger()
        if not any(isinstance(h, _AnomalyLogHandler) for h in root.handlers):
            h = _AnomalyLogHandler(level=logging.ERROR)
            root.addHandler(h)
    except Exception:
        pass
    _installed = True
    return {"installed": True}


def install_asyncio_hook(loop) -> None:
    """Installér asyncio-exception-handler på en kørende event-loop (self-safe)."""
    try:
        _prev = loop.get_exception_handler()

        def _handler(lp, context):
            try:
                exc = context.get("exception")
                record_anomaly(source="asyncio",
                               exc_type=type(exc).__name__ if exc else "Error",
                               message=str(exc) if exc else str(context.get("message") or ""),
                               location=_tb_location(getattr(exc, "__traceback__", None)) if exc else "",
                               trace=_full_trace(getattr(exc, "__traceback__", None)) if exc else "")
            except Exception:
                pass
            if _prev:
                try:
                    _prev(lp, context)
                except Exception:
                    pass
            else:
                lp.default_exception_handler(context)

        loop.set_exception_handler(_handler)
    except Exception:
        pass


def anomaly_summary(*, limit: int = 8) -> dict[str, Any]:
    """Til realtime-panelet: tæller pr. importance + de seneste/vigtigste anomalier."""
    try:
        from core.runtime.db_anomalies import list_anomalies, anomaly_counts
        recent = list_anomalies(limit=limit, unresolved_only=True)
        return {"counts": anomaly_counts(), "recent": recent}
    except Exception:
        return {"counts": {"total": 0}, "recent": []}
