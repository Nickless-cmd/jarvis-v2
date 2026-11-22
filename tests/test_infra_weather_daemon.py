"""Smoke tests for infra_weather_daemon.

Specifically guards against the OLLAMA_HOST default reverting from
127.0.0.1 (post-migration localhost) back to the old 10.0.0.25 LXC.
"""
from __future__ import annotations

import os


def test_default_ollama_host_is_localhost():
    """Default OLLAMA_HOST in _network_latency must be 127.0.0.1.

    Was 10.0.0.25 before 2026-05-26 migration. Localhost is correct
    because Ollama now runs on the same host as Jarvis runtime.
    """
    src = open("core/services/infra_weather_daemon.py").read()
    assert 'os.environ.get("OLLAMA_HOST", "127.0.0.1")' in src, (
        "OLLAMA_HOST default must be 127.0.0.1 — see "
        "MEMORY.md reference_ollama_host.md for migration context"
    )
    assert '10.0.0.25' not in src, (
        "10.0.0.25 (defunct LXC 107) must not appear in infra_weather_daemon"
    )


def test_module_imports_clean():
    """Module imports without side-effects requiring runtime."""
    # Ensure clean import
    if "core.services.infra_weather_daemon" in list(__import__("sys").modules):
        del __import__("sys").modules["core.services.infra_weather_daemon"]
    from core.services import infra_weather_daemon  # noqa: F401


# ─── /tmp-observatøren (22/11-2026) ────────────────────────────────────
#
# `/tmp` er en tmpfs på 16 GB. Den blev IKKE målt før 22/11-2026: `infra_sense`
# måler PVE-værten med `df -x tmpfs` (udelukker tmpfs ved design), og
# `embodied_state` måler `Path.cwd()`. Derfor kunne den fyldes til 100 %
# ubemærket, og følgen var 36 tests med Errno 28 og en sampler der tog 148 s.
# Der var en rydder (`tmp_cleanup`) men ingen observatør — disse tests vogter
# at observatøren faktisk ser stedet.

from collections import namedtuple

_Du = namedtuple("_Du", "total used free")


def _falsk_disk(monkeypatch, tal: dict[str, float]):
    """Lad hver sti svare med sin egen brugte procent."""
    import core.services.infra_weather_daemon as iw

    def _usage(path):
        pct = tal[path]
        total = 100 * 1024**3
        free = total * (100.0 - pct) / 100.0
        return _Du(total=total, used=total - free, free=free)

    monkeypatch.setattr(iw.shutil, "disk_usage", _usage)
    monkeypatch.setattr(iw.os.path, "exists", lambda p: p in tal)


def test_tmp_er_med_i_de_maalte_stier():
    """Hele pointen: /tmp skal måles, ellers er der ingen observatør."""
    import core.services.infra_weather_daemon as iw

    assert "/tmp" in iw._DISK_PATHS


def test_tmpfs_advarer_tidligere_end_de_store_diske(monkeypatch):
    """80 % er «clear» for `/` men «under pres» for `/tmp`.

    16 GB fyldes af pytest-mapper; 85 % ville levne ~4 mapper — for sent.
    """
    import core.services.infra_weather_daemon as iw

    _falsk_disk(monkeypatch, {"/": 80.0, "/media/projects": 80.0, "/tmp": 80.0})
    d = iw._disk_pressure()
    assert d["per_path"]["/"]["level"] == "clear"
    assert d["per_path"]["/tmp"]["level"] == "under-pressure"
    assert d["level"] == "under-pressure"


def test_lille_kritisk_tmpfs_tabes_ikke_til_stor_disk_under_pres(monkeypatch):
    """91 % på /tmp (kritisk for tmpfs) vs 92 % på / (blot under pres).

    Den højeste PROCENT er disken, men den værste TILSTAND er tmpfs'en.
    Rangerer man på procent alene, tier alarmen om den disk der faktisk
    løber tør — det er den fejl denne test findes for.
    """
    import core.services.infra_weather_daemon as iw

    _falsk_disk(monkeypatch, {"/": 92.0, "/media/projects": 92.0, "/tmp": 91.0})
    d = iw._disk_pressure()
    assert d["level"] == "critical"
    assert d["worst_path"] == "/tmp"


def test_reasons_navngiver_stien(monkeypatch):
    """«disk=88%» kunne ikke skelne den store disk fra den lille tmpfs."""
    import core.services.infra_weather_daemon as iw

    _falsk_disk(monkeypatch, {"/": 30.0, "/media/projects": 30.0, "/tmp": 92.0})
    monkeypatch.setattr(iw, "_system_load", lambda: {})
    monkeypatch.setattr(iw, "_network_latency", lambda: {})
    monkeypatch.setattr(iw, "_api_cost_today", lambda: 0.0)
    monkeypatch.setattr(iw, "_process_health", lambda: {})
    r = iw._compose_report()
    assert r["label"] == "critical"
    assert any("/tmp" in x for x in r["reasons"]), r["reasons"]


def test_alarmen_baerer_hvilken_sti_der_er_kritisk(monkeypatch):
    """Uden stien kan man ikke se om det er `/` eller `/tmp` der er fuld."""
    import core.services.infra_weather_daemon as iw

    _falsk_disk(monkeypatch, {"/": 30.0, "/media/projects": 30.0, "/tmp": 92.0})
    monkeypatch.setattr(iw, "_system_load", lambda: {})
    monkeypatch.setattr(iw, "_network_latency", lambda: {})
    monkeypatch.setattr(iw, "_api_cost_today", lambda: 0.0)
    monkeypatch.setattr(iw, "_process_health", lambda: {})

    set_payloads: list = []
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(
        bus_mod.event_bus, "publish",
        lambda kind, payload=None, **kw: set_payloads.append((kind, payload)),
    )
    import core.services.alarm_ud as au
    monkeypatch.setattr(au, "send_alert", lambda **kw: True)
    import core.services.shared_cache as sc
    monkeypatch.setattr(sc, "get", lambda k: None)
    monkeypatch.setattr(sc, "set", lambda k, v, *, ttl_seconds: None)

    iw._maybe_emit_critical(iw._compose_report())
    assert set_payloads, "alarmen blev ikke sendt"
    kind, payload = set_payloads[0]
    assert kind == "infra_weather.critical"
    assert payload.get("disk_worst_path") == "/tmp"
