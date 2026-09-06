"""Proprioceptionens alarmer skal kunne fyre.

Målt 2026-09-05: `_LATENCY_SLOW_MS` stod på 5000 mod en måling der lever på
0,024 ms — en faktor 208.000. `_measure_self_latency_ms()` lægger tallene
0..999 sammen i en for-løkke og måler hvor lang tid DET tog; det er ikke hans
responstid, det er CPU-hastighed. `proprioception.response_slow` kunne derfor
aldrig fyre. Et smertesignal for langsomhed der målte noget andet end langsomhed.
"""

from __future__ import annotations

from core.services import proprioception_metrics as P


def test_latenstaersklen_ligger_paa_maalingens_egen_skala():
    """Tærsklen skal være inden for rækkevidde af det der faktisk måles."""
    maalt = P._measure_self_latency_ms()
    assert maalt >= 0.0
    assert P._LATENCY_SLOW_MS <= 100, (
        "_LATENCY_SLOW_MS=%s er urimeligt højt for en måling der typisk giver "
        "~%.3f ms — alarmen kan aldrig fyre" % (P._LATENCY_SLOW_MS, maalt)
    )
    # Og den må ikke være så lav at den fyrer på en normal måling.
    assert P._LATENCY_SLOW_MS > maalt, (
        "tærsklen ligger UNDER en normal måling (%.3f ms) — så larmer den altid"
        % maalt
    )


def test_maalingen_er_billig():
    """Den kører hvert 30. sekund i heartbeat — den må ikke koste noget."""
    import time

    t = time.perf_counter()
    P._measure_self_latency_ms()
    forbrugt_ms = (time.perf_counter() - t) * 1000.0
    assert forbrugt_ms < 50.0


def test_snapshot_baerer_proces_kroppen():
    """Latensen maales separat — den ligger IKKE i snapshottet."""
    snap = P._current_snapshot()
    for felt in ("rss_mb", "cpu_pct", "open_fds", "uptime_seconds"):
        assert felt in snap, "proprioceptions-snapshot mangler %s" % felt
    assert snap["rss_mb"] >= 0.0


def test_de_oevrige_taerskler_er_ogsaa_naabare():
    """Samme fejlform kunne ramme fd-lækagen og RSS-springet."""
    snap = P._current_snapshot()
    fds = float(snap.get("open_fds") or 0)
    if fds > 0:
        assert P._FD_LEAK_THRESHOLD < fds * 50, (
            "_FD_LEAK_THRESHOLD=%s ligger urimeligt langt over de målte %d fds"
            % (P._FD_LEAK_THRESHOLD, fds)
        )
    assert 0 < P._RSS_JUMP_PCT <= 100
