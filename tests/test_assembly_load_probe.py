"""Hvad lavede maskinen mens prompten blev samlet? (Bjørn 4/10-2026)

Testene måler det der gjorde målingen nødvendig: at felterne kan SKELNE en
travl maskine fra en rolig. En probe der svarede det samme i begge tilfælde
ville være præcis den sammenblanding den er bygget for at fjerne.
"""
from __future__ import annotations

import re
import threading
import time

from core.services import assembly_load_probe as probe


def _felter(s: str) -> dict[str, float]:
    return {m.group(1): float(m.group(2))
            for m in re.finditer(r"(\w+)=([0-9.]+)", s)}


def test_en_TOM_maaling_giver_lavt_cpu_forhold():
    """Venter vi, er `cpu_pr_sek` nær nul. Det er hele signalet: assemblyen
    brugte ikke CPU, den ventede."""
    t = probe.start()
    time.sleep(0.3)
    f = _felter(probe.afslut(t))
    assert f["cpu_pr_sek"] < 0.3, f"ventetid blev maalt som arbejde: {f}"


def test_en_TRAVL_maaling_giver_hoejt_cpu_forhold():
    """Modprøven. Uden den kunne proben svare «lavt» altid og bestå testen
    ovenfor uden at måle noget."""
    t = probe.start()
    t0 = time.monotonic()
    x = 0
    while time.monotonic() - t0 < 0.3:
        x += 1
    f = _felter(probe.afslut(t))
    assert f["cpu_pr_sek"] > 0.7, f"arbejde blev maalt som ventetid: {f}"


def test_forholdet_kan_overstige_1_naar_FLERE_traade_regner():
    """Over 1 betyder: noget ANDET end assemblyen regnede samtidig i
    processen. Det er netop den tilstand der firedoblede en assembly 4/10 —
    0,44 kerner samtidigt Python-arbejde, 2,0 s → 8,67 s."""
    stop = threading.Event()

    def spin():
        x = 0
        while not stop.is_set():
            x += 1

    traade = [threading.Thread(target=spin, daemon=True) for _ in range(3)]
    for tr in traade:
        tr.start()
    t = probe.start()
    t0 = time.monotonic()
    y = 0
    while time.monotonic() - t0 < 0.4:
        y += 1
    f = _felter(probe.afslut(t))
    stop.set()
    for tr in traade:
        tr.join(timeout=1)
    # GIL'en deler tiden mellem fire traade, saa forholdet naermer sig 1 og
    # kan passere den naar flere kerner faar lov. Paastanden er at proben SER
    # de andre traade — ikke en bestemt vaerdi.
    assert f["traade"] >= 4, f"proben saa ikke de samtidige traade: {f}"
    assert f["cpu_pr_sek"] > 0.7, f


def test_den_baerer_maskinens_tilstand():
    f = _felter(probe.afslut(probe.start()))
    assert f["kerner"] >= 1
    assert "load1" in f
    assert "traade" in f


def test_et_ugyldigt_token_giver_en_TOM_streng_og_kaster_ikke():
    """Linjen skal stadig kunne skrives. En maaling der kan vaelte sin egen
    log-linje er vaerre end ingen maaling."""
    for skrald in (None, "", 0, [], {"ingen": "felter"}):
        assert probe.afslut(skrald) in ("", probe.afslut(skrald))
    assert probe.afslut(None) == ""


def test_et_felt_der_ikke_kan_laeses_fjerner_kun_SIG_SELV(monkeypatch):
    """Hvert felt falder for sig. Kan `loadavg` ikke laeses, maa resten af
    linjen ikke forsvinde med den."""
    import os
    monkeypatch.setattr(os, "getloadavg", lambda: (_ for _ in ()).throw(OSError("nej")))
    s = probe.afslut(probe.start())
    assert "load1=" not in s
    assert "kerner=" in s and "traade=" in s


def test_cpu_feltet_er_ENIGT_med_stdlib():
    """Kilde-uafhaengig kontrol. `/proc/self/stat` og `time.process_time()`
    svarer paa samme spoergsmaal ad to veje; er de uenige, er feltet forkert
    laest — og et forkert indeks i proc(5) ser helt rigtigt ud."""
    a1, b1 = probe._proces_cpu_sek(), time.process_time()
    t0 = time.monotonic()
    x = 0
    while time.monotonic() - t0 < 0.5:
        x += 1
    a2, b2 = probe._proces_cpu_sek(), time.process_time()
    assert a1 is not None and a2 is not None
    assert abs((a2 - a1) - (b2 - b1)) < 0.15, "proc-feltet er ikke CPU-tid"


def test_timing_linjen_BAERER_felterne():
    """Kilde-vagt: proben skal faktisk staa paa den linje der skrives, ikke
    bare findes. Det er husets hyppigste fejl — koden er rigtig og ingen
    kalder den."""
    import ast
    import pathlib
    kilde = pathlib.Path("core/services/prompt_contract.py").read_text()
    traeet = ast.parse(kilde)
    navne = {n.name for x in ast.walk(traeet)
             if isinstance(x, ast.Import) for n in x.names}
    navne |= {n.name for x in ast.walk(traeet)
              if isinstance(x, ast.ImportFrom) for n in x.names}
    assert "assembly_load_probe" in navne, "proben importeres ikke"
    assert "_last_str" in kilde and "prompt-assembly-timing total_ms=" in kilde
    # Og felterne skal staa i SELVE f-strengen, ikke bare vaere beregnet.
    i = kilde.index("prompt-assembly-timing total_ms=")
    assert "{_last_str}" in kilde[i:i + 200], "felterne naar ikke linjen"


# ── Per-builder CPU: grundlaget for at skille CPU fra I/O ──────────────────

def test_hver_builder_maaler_sin_EGEN_traads_cpu():
    """Kilde-vagt. `thread_time()` og ikke `process_time()`.

    Den sidste tæller ALLE trådes CPU, så hver builder ville se CPU-tung ud
    uanset hvad den lavede — og klassifikationen «CPU-bundet vs I/O-bundet»
    ville blive meningsløs præcis når den skal bruges. Det er samme fejltype
    som kostede tre forkerte konklusioner 4/10, bare et lag dybere.
    """
    import ast
    import pathlib

    kilde = pathlib.Path("core/services/prompt_contract.py").read_text()
    traeet = ast.parse(kilde)
    fundet = False
    for node in ast.walk(traeet):
        if not isinstance(node, ast.FunctionDef) or node.name != "_wrapped":
            continue
        krop = ast.unparse(node)
        if "_phase_cpu" not in krop:
            continue
        assert "thread_time" in krop, "builder-CPU maales ikke per TRAAD"
        assert "process_time" not in krop, (
            "process_time() taeller alle traade — hver builder ville se "
            "CPU-tung ud uanset hvad den lavede")
        fundet = True
    assert fundet, "fandt ingen _wrapped der skriver _phase_cpu"


def test_cpu_felterne_naar_timing_linjen():
    """Husets hyppigste fejl: koden er rigtig og ingen skriver den ud."""
    import pathlib
    kilde = pathlib.Path("core/services/prompt_contract.py").read_text()
    assert "_cpu={v}" in kilde, "per-builder CPU naar ikke linjen"
    i = kilde.index("prompt-assembly-timing total_ms=")
    # Felterne bygges ind i `_phases_str`, som staar i selve f-strengen.
    assert "{_phases_str}" in kilde[i:i + 240]
