"""Agentic-round watchdog — hvornår skal en runde opgives?

Udskilt fra ``visible_runs.py`` (Boy Scout, 17. aug 2026) som en selvstændig,
testbar enhed: ren beslutningslogik, ingen I/O, ingen side-effekter.

To ure bevogter en agentic-runde:
  * **total-loft** — forhindrer uendelige provider-kald (hårdt; kan aldrig omgås).
  * **tavsheds-loft** — fanger stallede streams, men tillader lange runder der
    bliver ved med at producere deltas/tool-kald.

**Sult-nåden (rod-årsag 17. aug 2026):** tavsheds-uret var et rent stopur, og det
kunne ikke skelne "provideren er død" fra "vi kunne ikke nå at læse". Da desk'en
pollede API'et 515 req/min hakkede event-loopet (målt loop_lag_peak 347 ms) → det
detached runs frames blev ikke konsumeret i 180 s → watchdog'en kaldte det
provider-silence → runet blev kasseret midt-flugt med ``vis_len=0``, 13 gange i
træk. Brugeren så "Jeg blev afbrudt midt i det" og mistede alt arbejdet.

Tavshed under selv-forskyldt sult er IKKE bevis på en død provider. Når loop-lag
viser at VORES proces var blokeret, udvides tavsheds-budgettet i stedet for at
henrette runden. Nåden er bevidst begrænset (faktor, ikke uendelighed), og
total-loftet gælder altid — så et ægte dødt kald stadig opgives.

Se ``reference_cutoff_rootcause_pollstorm`` + nerven ``stream/cutoff_at_loop_lag``.
"""
from __future__ import annotations

# Over denne peak-lag regnes event-loopet som sultet (normal drift ligger < 50 ms).
STARVATION_LAG_MS = 250.0

# Hvor meget tavsheds-budgettet højst må strækkes når loopet var sultet.
STARVATION_GRACE_FACTOR = 2.0


def effective_silence_budget_s(max_silence_s: float, loop_lag_peak_ms: float) -> float:
    """Tavsheds-budget justeret for hvor blokeret vores eget loop har været.

    ``max_silence_s <= 0`` betyder "slået fra" og forbliver slået fra — sult må
    aldrig genoplive et deaktiveret ur.
    """
    if max_silence_s <= 0:
        return max_silence_s
    if loop_lag_peak_ms < STARVATION_LAG_MS:
        return max_silence_s
    return max_silence_s * STARVATION_GRACE_FACTOR


def agentic_watchdog_timeout_reason(
    *,
    started_at: float,
    last_progress_at: float,
    now: float,
    max_total_s: float,
    max_silence_s: float,
    loop_lag_peak_ms: float = 0.0,
) -> str | None:
    """Returnér watchdog-timeout-grunden, eller None hvis runden må fortsætte.

    ``loop_lag_peak_ms`` er nyligt peak event-loop-lag (se
    ``core.services.central_loop_lag.recent_peak_ms``). Ved sult udvides KUN
    tavsheds-uret; total-loftet er ubetinget.
    """
    silence_budget = effective_silence_budget_s(max_silence_s, loop_lag_peak_ms)
    if silence_budget > 0 and (now - last_progress_at) > silence_budget:
        return "provider-silence-timeout"
    if max_total_s > 0 and (now - started_at) > max_total_s:
        return "provider-round-timeout"
    return None
