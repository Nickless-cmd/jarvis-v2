"""Mobilens version står tre steder og skal sige det samme alle tre.

## Hvorfor (målt 7/10-2026)

Den udgivne APK var `0.2.186 (287)` — bekræftet af tre uafhængige kilder:
`latest.json`, APK'ens eget `AndroidManifest.xml`, og det telefonen selv
rapporterer i `X-Jarvis-Klientversion`.

Men **main sagde stadig `0.2.184 (285)`.** Bumpet var lavet i en worktree og
aldrig committet. Konsekvensen er ikke kosmetisk: den næste der bygger fra main
ville producere 286 igen og kollidere med en allerede udgivet APK, eller bygge
en 285 der er ældre end den der ligger på telefonen.

De tre steder findes af en grund — gradle læser `build.gradle`, Expo læser
`app.json`, og npm-værktøjer læser `package.json` — men ingenting holdt dem
sammen. Jeg bumpede dem selv tre gange i dag med en `sed` pr. fil, og det er
præcis den slags hvor én fil bliver glemt uden at noget siger fra.

Testen siger ikke HVILKEN version der er rigtig. Den siger at de tre er enige.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
GRADLE = ROD / "apps/mobile/android/app/build.gradle"
APP_JSON = ROD / "apps/mobile/app.json"
PACKAGE_JSON = ROD / "apps/mobile/package.json"


def _gradle() -> tuple[int, str]:
    tekst = GRADLE.read_text(encoding="utf-8")
    kode = re.search(r"^\s*versionCode\s+(\d+)\s*$", tekst, re.M)
    navn = re.search(r'^\s*versionName\s+"([^"]+)"\s*$', tekst, re.M)
    assert kode and navn, "versionCode/versionName findes ikke i build.gradle"
    return int(kode.group(1)), navn.group(1)


def _app_json() -> tuple[int, str]:
    d = json.loads(APP_JSON.read_text(encoding="utf-8"))
    expo = d.get("expo", d)
    return int(expo["android"]["versionCode"]), str(expo["version"])


def _package_json() -> str:
    return str(json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["version"])


def test_versionskoden_er_ens_i_gradle_og_app_json():
    """`build.gradle` er den gradle FAKTISK bygger med; `app.json` er den Expo
    og opdateringsmanifestet laeser. Er de uenige, bygger og annoncerer vi to
    forskellige ting."""
    g, _ = _gradle()
    a, _ = _app_json()
    assert g == a, f"build.gradle siger {g}, app.json siger {a}"


def test_versionsnavnet_er_ens_alle_tre_steder():
    _, g = _gradle()
    _, a = _app_json()
    p = _package_json()
    assert g == a == p, f"gradle={g} app.json={a} package.json={p}"


def test_versionsnavnet_har_den_forventede_form():
    """Et navn som `0.2.186`. En tastefejl her bliver til et manifest ingen
    klient kan sammenligne paa."""
    _, navn = _gradle()
    assert re.fullmatch(r"\d+\.\d+\.\d+", navn), navn


def test_versionskoden_er_et_positivt_heltal():
    """Android sammenligner opdateringer paa dette tal alene."""
    kode, _ = _gradle()
    assert kode > 0
