"""Stream-cluster — observabilitet for SSE-lanen. IKKE en blokerende gate: streaming er
en LANE med mange fejl-punkter, ikke en beslutning. Gør lanens livscyklus + fejl synlige
i Den Intelligente Central (central.observe) så hængende streams / manglende message_stop
/ zombie-slots FANGES og flagges — i stedet for at Bjørn opdager dem i blinde.

Historisk levede streaming-bugs her usynligt: ~25 tavse ``except: pass`` i SSE-pipelinen,
ingen central trace. Nu emitterer hver lane-overgang (start/stop/idle/cancel/error/zombie/
subscriber_timeout) et central.observe pr. run_id, og en stall-backstop flagger en stream
der fik message_start men ALDRIG message_stop.

Stall-tærsklen (300s) måler STILHED — sekunder siden runnets seneste livstegn — ikke
alder siden message_start. Det er forskellen mellem «denne stream er død» og «denne
stream venter». Før målte vi alder, og et helt legitimt run midt i tre
provider-timeouts à ~90s overskred tærsklen og blev erklæret zombie 1m43s før det
afsluttede RENT (målt 17/10-2026 på incident 14176: runnet kørte videre, retryede
tre gange og sluttede med `run-stream terminal`). En falsk zombie-incident er værre
end ingen: den lærer os at ignorere alarmen.

Aktivitetskilden er ``run_event_log.last_append_at``, som opdateres ved HVER frame
(inkl. 5s-pings). Et virkelig dødt run holder også op med at pinge — så en zombie
fanges stadig, blot 300s efter sidste livstegn frem for 300s efter start.

Tærsklen ligger BEVIDST over translatorens egen idle-oprydning (~180s), så vi kun
flagger ægte zombier (task helt død) — ikke lange legitime runs eller streams som
translatorens finally selv lukker. Incident-severity = 'error' (pollbar, ingen push)
for ikke at vække på en mulig false-positive.

SELV-SIKKER: kaster ALDRIG ind i den hotte SSE-sti.
"""
from __future__ import annotations

import threading
import time
from typing import Any

_CLUSTER = "stream"
_STALL_AFTER_S = 300.0  # ingen livstegn i >5 min → ægte zombie → flag

# run_id -> {"start": monotonic, "last_activity": monotonic, "session_id": str,
#            "meta": dict, "flagged": bool}
_live: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _aktivitet(run_id: str, rec: dict[str, Any]) -> float:
    """Seneste livstegn for runnet (monotonic).

    To kilder, og vi tager den NYESTE af dem: sentinel'ens eget spor (sat ved start
    og opdateret ved hvert ``note_event``) og loggens ``last_append_at``, som
    opdateres ved HVER frame — også de 5s-pings der ikke bærer indhold. Loggen er
    den stærkeste kilde, fordi den ser alle frames; sentinel'ens spor er gulvet hvis
    loggen ikke kender runnet (pruned, eller et run der aldrig fik en log).

    Kaster aldrig: en fejl her må ikke gøre en sweep tavs.
    """
    try:
        sidst = float(rec.get("last_activity") or rec.get("start") or 0.0)
    except (TypeError, ValueError):
        sidst = 0.0
    try:
        from core.services import run_event_log
        fra_log = run_event_log.last_activity_at(run_id)
        if fra_log is not None:
            sidst = max(sidst, float(fra_log))
    except Exception:  # selv-sikker: et aktivitets-opslag må ALDRIG gøre en sweep tavs
        pass
    return sidst


def _observe(nerve: str, run_id: str, session_id: str, **data: Any) -> None:
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": _CLUSTER, "nerve": nerve,
            "run_id": run_id, "session_id": session_id, **data,
        })
    except Exception:
        pass


def note_start(run_id: str, session_id: str = "", **meta: Any) -> None:
    """En SSE-stream sendte message_start. Registrér + observe + opportunistisk stall-sweep."""
    rid = str(run_id or "")
    if not rid:
        return
    try:
        with _lock:
            _nu = time.monotonic()
            _live[rid] = {"start": _nu, "last_activity": _nu,
                          "session_id": str(session_id or ""),
                          "meta": dict(meta), "flagged": False}
        _observe("stream_start", rid, str(session_id or ""), **meta)
        _sweep_stalled()  # ryd/flag gamle ved hver ny start (ingen daemon nødvendig)
    except Exception:
        pass


def note_stop(run_id: str, *, reason: str = "done") -> None:
    """En SSE-stream sendte message_stop (reason='done' normalt, 'fallback' = terminal-garanti)."""
    rid = str(run_id or "")
    if not rid:
        return
    try:
        with _lock:
            rec = _live.pop(rid, None)
        if rec is None:
            return  # idempotent: allerede stoppet (fx done før finally-fallback) → ingen dobbelt-emit
        sid = str(rec.get("session_id") or "")
        dur_ms = int((time.monotonic() - rec["start"]) * 1000)
        _observe("stream_stop", rid, sid, reason=reason, duration_ms=dur_ms)
    except Exception:
        pass


# NOTE (zombie_slot): nerven 'stream_zombie_slot' er BEVIDST uwired her. Den ægte
# zombie-detektion (message_start uden message_stop) dækkes allerede af _sweep_stalled
# → 'stream_stall' + persistent incident. Et separat zombie_slot-kald ville være
# dobbelt-observabilitet for samme tilstand. Wires først hvis en NY zombie-kilde
# (fx run_event_log active-slot der aldrig ryddes) får et entydigt call-site.
def note_event(run_id: str, kind: str, session_id: str = "", **data: Any) -> None:
    """Andre lane-fejl/edge-cases: idle / cancel / error / zombie_slot / subscriber_timeout.

    Et edge-case er også et LIVSTEGN: runnet reagerer, altså lever det. Vi opdaterer
    derfor ``last_activity`` her, så en hændelse kort før en sweep ikke efterlader
    runnet som «stille siden start».
    """
    rid = str(run_id or "")
    try:
        if rid:
            with _lock:
                rec = _live.get(rid)
                if rec is not None:
                    rec["last_activity"] = time.monotonic()
        _observe(f"stream_{kind}", rid, str(session_id or ""), kind=kind, **data)
    except Exception:
        pass


def _sweep_stalled(timeout_s: float = _STALL_AFTER_S) -> None:
    """Ingen livstegn i >timeout_s → ægte zombie → flag ÉN gang pr. run
    (observe + persistent incident severity='error', pollbar af Claude/MC).

    Måler STILHED, ikke alder. Forskellen er hele pointen: et run der venter fire
    minutter på et provider-svar men stadig pinger, er ikke dødt — og et run der ER
    dødt holder også op med at pinge, så den ægte zombie fanges stadig. Før målte vi
    alder og flagede levende runs (incident 14176: flagget 1m43s før runnet
    afsluttede rent).

    ``_aktivitet`` kaldes inde i låsen fordi den er et rent opslag i en anden dict
    (``run_event_log``) og fordi flaget skal sættes atomisk med vurderingen — ellers
    kunne to samtidige sweeps begge flage samme run. Der er ingen omvendt
    låse-rækkefølge i huset: ``run_event_log`` kalder aldrig tilbage i sentinel
    under sin egen lås.
    """
    now = time.monotonic()
    stalled: list[tuple[str, str, float, float]] = []
    try:
        with _lock:
            for rid, rec in list(_live.items()):
                if rec.get("flagged"):
                    continue
                start = float(rec.get("start") or 0.0)
                stille = now - _aktivitet(rid, rec)
                if stille > timeout_s:
                    rec["flagged"] = True
                    stalled.append((rid, str(rec.get("session_id") or ""), stille,
                                    now - start))
        for rid, sid, stille, alder in stalled:
            stille_s, alder_s = int(stille), int(alder)
            _observe("stream_stall", rid, sid, age_s=alder_s, silent_s=stille_s,
                     reason="no_activity")
            try:
                from core.runtime.db_central_incidents import record_central_incident
                record_central_incident(
                    cluster=_CLUSTER, nerve="stream_stall", kind="stall",
                    severity="error", run_id=rid, session_id=sid,
                    message=(
                        f"stream {rid} har ikke givet et livstegn i {stille_s}s "
                        f"(åbnet for {alder_s}s siden) — message_stop mangler stadig"
                    ),
                )
            except Exception:
                pass
    except Exception:
        pass


def sweep() -> int:
    """Eksternt-kaldbar stall-sweep (fx fra heartbeat-kadence). Returnér antal live streams."""
    try:
        _sweep_stalled()
        with _lock:
            return len(_live)
    except Exception:
        return 0


def live_count() -> int:
    with _lock:
        return len(_live)
