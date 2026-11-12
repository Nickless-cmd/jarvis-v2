"""Boy Scout: autonom run-starter udskilt fra visible_runs - re-eksporten og opslaget ved kald bevarer adfaerden."""
from __future__ import annotations

import time
from types import SimpleNamespace

from core.eventbus.bus import event_bus


def test_visible_runs_re_exports_the_very_same_objects():
    from core.services import visible_autonomous_run as new
    from core.services import visible_runs as old
    assert old.start_autonomous_run is new.start_autonomous_run
    assert old._observe_autonomous_run is new._observe_autonomous_run


def test_a_patch_on_visible_runs_still_steers_the_moved_starter(isolated_runtime, monkeypatch):
    """load_settings og _stream_visible_run slaas op paa visible_runs ved KALDET, ikke ved import."""
    from core.services import visible_runs as vr
    seen = {"settings": 0, "frames": 0}

    def settings():
        seen["settings"] += 1
        return SimpleNamespace(primary_model_lane="visible", visible_model_provider="p", visible_model_name="m",
                               autonomous_model_provider="ap", autonomous_model_name="am")

    async def stream(run):
        seen["frames"] += 1
        yield "frame"

    monkeypatch.setattr(vr, "load_settings", settings)
    monkeypatch.setattr(vr, "_stream_visible_run", stream)
    vr.start_autonomous_run("flyt-test", session_id="sess-boyscout")
    deadline = time.time() + 3.0
    kinds: set[str] = set()
    while time.time() < deadline and "runtime.autonomous_run_completed" not in kinds:
        kinds = {str(e.get("kind") or "") for e in event_bus.recent(limit=30)
                 if str((e.get("payload") or {}).get("session_id") or "") == "sess-boyscout"}
        time.sleep(0.05)
    assert seen == {"settings": 1, "frames": 1}
    assert {"runtime.autonomous_run_started", "runtime.autonomous_run_completed"} <= kinds


def test_ejeren_saettes_paa_runnet_naar_kalderen_ikke_giver_den(monkeypatch):
    """8/11-2026: `force_user_id` er tom for ALLE autonome producenter.

    Maalt konsekvens foer rettelsen: `in_flight_runs` skrev `force_user_id: ""`
    for hvert autonomt run, og `verificeret_jarvis_run` afviser netop den form
    («er den tom, er der intet bevis»). Derfor kunne en autonom koersel aldrig
    laegge sin rapport i ownerens indbakke — den blev afvist hver gang.

    Testen maaler run-OBJEKTET, ikke indbakke-posten (den har sin egen suite).
    """
    from types import SimpleNamespace

    from core.services import visible_runs as vr

    kaldt: list[object] = []

    def settings():
        return SimpleNamespace(primary_model_lane="visible", visible_model_provider="p",
                               visible_model_name="m", autonomous_model_provider="ap",
                               autonomous_model_name="am")

    async def stream(run, **kw):
        kaldt.append(run)
        yield "frame"

    monkeypatch.setattr(vr, "load_settings", settings)
    monkeypatch.setattr(vr, "_stream_visible_run", stream)
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id",
                        lambda: "owner-42")
    monkeypatch.setattr("core.services.inbox_state.registrer_kilde",
                        lambda **k: {"status": "ok", "post": {}})
    monkeypatch.setattr("core.services.run_guard.blokeringsgrund",
                        lambda *a, **k: "")

    vr.start_autonomous_run("ejer-test", session_id="sess-ejer")
    deadline = time.time() + 5.0
    while time.time() < deadline and not kaldt:
        time.sleep(0.05)

    assert kaldt, "runnet blev aldrig startet"
    assert kaldt[0].user_id == "owner-42", (
        f"runnet baerer ikke ejeren: {kaldt[0].user_id!r}"
    )


def test_en_eksplicit_ejer_vinder_over_fallback(monkeypatch):
    """Fallback'et maa kun fylde et HUL, aldrig overskrive en eksplicit binding.

    discord_gateway binder Michelles id; et run for hende maa ikke loeftes til
    owner — det er den anden halvdel af sikkerheden.
    """
    from types import SimpleNamespace

    from core.services import visible_runs as vr

    kaldt: list[object] = []

    def settings():
        return SimpleNamespace(primary_model_lane="visible", visible_model_provider="p",
                               visible_model_name="m", autonomous_model_provider="ap",
                               autonomous_model_name="am")

    async def stream(run, **kw):
        kaldt.append(run)
        yield "frame"

    monkeypatch.setattr(vr, "load_settings", settings)
    monkeypatch.setattr(vr, "_stream_visible_run", stream)
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id",
                        lambda: "owner-42")
    monkeypatch.setattr("core.services.inbox_state.registrer_kilde",
                        lambda **k: {"status": "ok", "post": {}})
    monkeypatch.setattr("core.services.run_guard.blokeringsgrund",
                        lambda *a, **k: "")

    vr.start_autonomous_run("michelle-test", session_id="sess-michelle",
                            force_user_id="michelle-7")
    deadline = time.time() + 5.0
    while time.time() < deadline and not kaldt:
        time.sleep(0.05)

    assert kaldt, "runnet blev aldrig startet"
    assert kaldt[0].user_id == "michelle-7", (
        f"fallback overskrev en eksplicit ejer: {kaldt[0].user_id!r}"
    )


def test_modulet_kan_importeres_isoleret():
    """Den cirkulære import maa ikke komme tilbage (8/11-2026).

    `visible_runs` re-eksporterede de autonome symboler med en HAARD import paa
    modulniveau, mens `visible_autonomous_run` importerer `visible_runs` i
    toppen. De to moduler kunne derfor ikke importeres ISOLERET — maalt:
    `import core.services.visible_autonomous_run` fejlede med «partially
    initialized module», mens den omvendte raekkefoelge virkede.

    Fejlen var usynlig i drift, fordi tjenesten altid importerer den anden vej
    foerst. Den blev foerst fanget af deployets stikproeve, som importerer hvert
    aendret modul ALENE — og den faeldede deployet 8/11 kl. 20:17.

    Testen koerer i en frisk subprocess: cirklen opstaar kun ved kold start, saa
    en in-process import ville se det allerede-indlaeste modul og bestaa.
    """
    import subprocess
    import sys

    for modul in (
        "core.services.visible_autonomous_run",
        "core.services.visible_runs",
    ):
        res = subprocess.run(
            [sys.executable, "-c", f"import {modul}"],
            capture_output=True, text=True, timeout=120,
        )
        assert res.returncode == 0, (
            f"{modul} kunne ikke importeres isoleret:\n{res.stderr[-800:]}"
        )


def test_re_eksporten_er_doven_men_virker():
    """Navnene skal stadig kunne hentes gennem `visible_runs` (PEP 562)."""
    from core.services import visible_runs as vr

    assert callable(vr.start_autonomous_run)
    assert callable(vr._observe_autonomous_run)
    # Ukendte navne skal fejle som normalt — ellers skjuler __getattr__ slaa-fejl.
    import pytest

    with pytest.raises(AttributeError):
        vr.findes_ikke_her


# ── En vækning i en SAMTALE bruger samtalens model (Bjørn 12/11-2026) ─────────
#
# Bjørn er den eneste der bruger DeepSeek-API'et; de andre bruger DeepSeek via
# ollama cloud. Vækninger gik til baggrundsmodellen (ollama/glm-5.3-flash), og
# `resolve_autonomous_model` klemmer bevidst den betalte provider væk. Resultatet:
# vækningens svar kom fra en anden model end den han havde valgt, midt i hans samtale
# — og uden hans prompt-cache. `session_model_pin` kender allerede samtalens model.
# Heartbeat, drømme m.fl. lander i `auto-*`-siloer og bliver på den billige lane.
def _start_og_fang_run(monkeypatch, session_id):
    from types import SimpleNamespace

    from core.services import visible_runs as vr

    kaldt: list[object] = []

    def settings():
        return SimpleNamespace(primary_model_lane="visible", visible_model_provider="p",
                               visible_model_name="m", autonomous_model_provider="ap",
                               autonomous_model_name="am")

    async def stream(run, **kw):
        kaldt.append(run)
        yield "frame"

    monkeypatch.setattr(vr, "load_settings", settings)
    monkeypatch.setattr(vr, "_stream_visible_run", stream)
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "owner-42")
    monkeypatch.setattr("core.services.inbox_state.registrer_kilde",
                        lambda **k: {"status": "ok", "post": {}})
    monkeypatch.setattr("core.services.run_guard.blokeringsgrund", lambda *a, **k: "")

    vr.start_autonomous_run("vaekning", session_id=session_id)
    deadline = time.time() + 5.0
    while time.time() < deadline and not kaldt:
        time.sleep(0.05)
    assert kaldt, "runnet blev aldrig startet"
    return kaldt[0]


def _billig_lane() -> tuple[str, str]:
    from core.services.central_router_adapt import resolve_autonomous_model

    return resolve_autonomous_model(autonomous_provider="ap", autonomous_model="am")


def test_en_vaekning_i_en_samtale_bruger_samtalens_pinnede_model(isolated_runtime, monkeypatch):
    from core.services import session_model_pin as smp

    smp.pin("chat-pinnet", "deepseek", "deepseek-flash")   # Bjørns: det betalte API

    run = _start_og_fang_run(monkeypatch, "chat-pinnet")

    assert (run.provider, run.model) == ("deepseek", "deepseek-flash")
    assert (run.provider, run.model) != _billig_lane()


def test_en_vaekning_i_en_anden_brugers_samtale_bruger_den_samtales_model(isolated_runtime, monkeypatch):
    from core.services import session_model_pin as smp

    smp.pin("chat-medlem", "ollama", "deepseek-v4-flash:cloud")   # de andre: via ollama cloud

    run = _start_og_fang_run(monkeypatch, "chat-medlem")

    assert (run.provider, run.model) == ("ollama", "deepseek-v4-flash:cloud")


def test_uden_en_pin_bliver_vaekningen_paa_den_billige_lane(isolated_runtime, monkeypatch):
    run = _start_og_fang_run(monkeypatch, "chat-uden-pin")

    assert (run.provider, run.model) == _billig_lane()


def test_en_auto_silo_bruger_aldrig_en_pin_selv_om_der_findes_en(isolated_runtime, monkeypatch):
    """Heartbeat, drømme og rutiner lander i `auto-*` — dem er det den billige lane til."""
    from core.services import session_model_pin as smp

    smp.pin("auto-heartbeat-20261112", "deepseek", "deepseek-flash")

    run = _start_og_fang_run(monkeypatch, "auto-heartbeat-20261112")

    assert (run.provider, run.model) == _billig_lane()


def test_en_ugyldig_pin_falder_tilbage_til_den_billige_lane(isolated_runtime, monkeypatch):
    """En død/ukendt model må ikke kile vækningen fast: samme retning som `release`."""
    from core.services import session_model_pin as smp

    smp.pin("chat-doed-pin", "ollama", "findes-ikke-9000")   # resolve_safe afviser ukendte ollama-modeller

    run = _start_og_fang_run(monkeypatch, "chat-doed-pin")

    assert (run.provider, run.model) == _billig_lane()
