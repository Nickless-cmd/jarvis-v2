"""Det aktive ntfy-topic-navn må ikke stå i den offentlige kilde.

## Hvorfor (målt 7/10-2026)

`runtime.json` ligger uden for repoet, men navnet stod i kilden: i
værktøjsbeskrivelsen for `send_ntfy` (den går i PROMPTEN og dermed til
model-provideren), i fire docstrings og i to tests. Repoet er **offentligt**,
så navnet var læsbart for enhver.

Og en ntfy.sh-topic har ingen adgangskontrol: enhver med navnet kan læse hver
besked. Målt på den åbne topic: 32 beskeder på 12 timer — blandt dem
helbredsoplysninger, værtens temperatur og hvad driften koster. Detaljerne
står ikke her; det er hele pointen med denne fil.

Navnet blev skiftet til en uopdagelig streng, og de gamle forekomster fjernet.
Men et navn kan ikke usynliggøres i git-historikken — derfor er det gamle navn
permanent kompromitteret, og et nyt var den eneste rigtige løsning.

## Hvad vagten gør

Den læser det navn der står i config'en NU og kræver at det ikke findes i nogen
versioneret fil. Det fanger både en fremtidig tilbageskrivning og et nyt navn
nogen skriver ind i kilden.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

# Bygget af to dele med vilje: ellers ville strengen stå i denne fil og
# vagten ville fælde sig selv. De er de navne der VAR i brug og er
# kompromitterede — de skal heller ikke tilbage.
GAMLE_NAVNE = ["jarvis" + "-heartbeat"]

REPO = Path(__file__).resolve().parents[1]

# Filtyper der kan bære et navn. Binære springes over.
TEKST_SUFFIKSER = {
    ".py", ".ts", ".tsx", ".js", ".json", ".md", ".sh", ".yml", ".yaml",
    ".toml", ".cfg", ".ini", ".txt", ".html", ".css",
}


def _aktive_navne() -> list[str]:
    """Det topic-navn der er i brug lige nu, læst fra runtime.json."""
    cfg = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
    try:
        navn = json.loads(cfg.read_text(encoding="utf-8")).get("ntfy_topic")
    except Exception:
        return []
    return [str(navn)] if navn else []


def _versionerede_filer() -> list[Path]:
    ud = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, timeout=60
    )
    if ud.returncode != 0:
        return []
    return [REPO / linje for linje in ud.stdout.splitlines() if linje.strip()]


def _find_navn(navne: list[str]) -> list[str]:
    """Returnerer 'fil:linje: navn' for hvert træf i versioneret kildetekst."""
    traef: list[str] = []
    for fil in _versionerede_filer():
        if fil.suffix.lower() not in TEKST_SUFFIKSER:
            continue
        try:
            tekst = fil.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for nr, linje in enumerate(tekst.splitlines(), 1):
            for navn in navne:
                if navn in linje:
                    try:
                        vis = fil.relative_to(REPO)
                    except ValueError:
                        vis = fil
                    traef.append(f"{vis}:{nr}: {navn}")
    return traef


def test_det_aktive_topic_navn_staar_ikke_i_kilden():
    navne = _aktive_navne()
    if not navne:
        import pytest

        pytest.skip("intet ntfy-topic konfigureret i dette miljø")
    traef = _find_navn(navne)
    assert not traef, (
        "Det aktive ntfy-topic-navn står i den offentlige kilde — enhver med "
        "navnet kan læse hver besked:\n  " + "\n  ".join(traef)
    )


def test_de_gamle_kompromitterede_navne_er_væk():
    traef = _find_navn(GAMLE_NAVNE)
    assert not traef, (
        "Et kompromitteret topic-navn er skrevet tilbage i kilden:\n  "
        + "\n  ".join(traef)
    )
