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
