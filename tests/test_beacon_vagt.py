r"""Vagten paa beacon-loggen.

Den vigtigste test er den foerste: den gamle vagt var en haandskrevet regex
(`cpu[=: ]+(\d+)`) mod en log der skriver `pkgC=`. Den kunne ikke ramme noget
som helst, koerte en halv time og meldte «ingen haendelser». Stilhed lignede ro.
"""
import subprocess
import sys
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]


def _koer(linjer: list[str]) -> str:
    r = subprocess.run([sys.executable, str(ROD / "scripts" / "beacon_vagt.py")],
                       input="\n".join(linjer) + "\n", capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _l(tid: str, up: float, *, pkg=40, gpu=40, fan2=5600) -> str:
    return (f"2026-09-16T{tid} up={up} load=0.5 pkgC={pkg}.0 hotC={pkg + 1}.0 sysC=26.0 "
            f"fan1=900,fan2={fan2},fan5=1400 gpuW_C=12.0,{gpu} memkB=26000000 streak=0")


def test_en_rolig_time_siger_INTET():
    ud = _koer([_l(f"20:00:{s:02d}", 100 + s) for s in range(0, 60, 5)])
    assert ud.strip() == ""


def test_et_enkelt_udsving_er_ikke_en_alarm():
    # Vaerten spidser rutinemaessigt til 72 C i tomgang (maalt: p95 60, maks 72).
    # En alarm pr. spids ville vaere stoej hver time.
    ud = _koer([_l("20:00:00", 100), _l("20:00:05", 105, pkg=72), _l("20:00:10", 110)])
    assert "CPU" not in ud


def test_varmt_LAENGE_er_en_alarm():
    ud = _koer([_l(f"20:01:{s:02d}", 100 + s, pkg=70) for s in range(0, 40, 5)])
    assert "CPU 70 C" in ud


def test_en_genstart_meldes_med_det_samme():
    ud = _koer([_l("20:00:00", 5000), _l("20:02:00", 5)])
    assert "GENSTARTET" in ud


def test_pumpen_maales_paa_den_hurtigste_kanal():
    # fan2 er pumpen her; falder den, skal det ses — uanset kanalnavn.
    ud = _koer([_l("20:00:00", 100, fan2=1200)])
    assert "PUMPE" in ud and "1400" in ud   # fan5 er nu den hurtigste


def test_samme_alarm_gentages_ikke_i_ét_vaek():
    ud = _koer([_l(f"20:0{m}:00", 100 + m * 60, gpu=85) for m in range(0, 4)])
    assert ud.count("GPU") == 1
