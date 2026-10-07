"""Hvilke APK'er der beholdes når en ny lægges op.

To fejl er sket i den her mappe, i den rækkefølge:

  1. Der blev aldrig ryddet — 1,3 GB i 13 APK'er, én i brug.
  2. Da der endelig blev ryddet, røg ALT på nær den nye, og dermed den eneste
     rullebane der fandtes.

Testene holder på midtvejen: præcis ét skridt tilbage.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

_sti = Path(__file__).resolve().parents[1] / "scripts" / "publish_mobile_apk.py"
_spec = importlib.util.spec_from_file_location("publish_mobile_apk", _sti)
pma = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pma)  # type: ignore[union-attr]

vaelg = pma.vaelg_hvad_der_slettes


def _apk(*koder: int) -> list[str]:
    return [f"jarvis-mobile-{k}.apk" for k in koder]


def test_beholder_den_nye_og_den_forrige():
    behold, slet = vaelg(_apk(127, 128, 129, 130), "jarvis-mobile-130.apk", "jarvis-mobile-129.apk")
    assert behold == _apk(130, 129)
    assert slet == _apk(128, 127)


def test_latest_json_og_andre_filer_roeres_ikke():
    """Oprydningen må kun kende APK'er. Manifestet ligger i samme mappe."""
    _, slet = vaelg(["latest.json", "noter.txt", *_apk(120, 121)],
                    "jarvis-mobile-121.apk", "jarvis-mobile-120.apk")
    assert slet == []


def test_foerste_udgivelse_i_en_tom_mappe():
    behold, slet = vaelg([], "jarvis-mobile-1.apk", None)
    assert behold == ["jarvis-mobile-1.apk"]
    assert slet == []


def test_manifest_der_peger_paa_en_fil_der_er_væk():
    """Sådan så mappen ud EFTER den hårde oprydning: manifestet pegede på 129,
    og 128 fandtes ikke længere. Så skal næstnyeste være rullebanen — ikke
    ingenting."""
    behold, slet = vaelg(_apk(129, 130), "jarvis-mobile-130.apk", "jarvis-mobile-128.apk")
    assert behold == _apk(130, 129)
    assert slet == []


def test_genudgivelse_af_samme_versionscode_taber_ikke_rullebanen():
    """Bygger man 130 om og lægger den op igen, er «forrige» stadig 130. Uden
    dette værn ville 129 blive slettet, og så var der intet at rulle tilbage
    til."""
    behold, slet = vaelg(_apk(128, 129, 130), "jarvis-mobile-130.apk", "jarvis-mobile-130.apk")
    assert behold == _apk(130, 129)
    assert slet == _apk(128)


def test_sorteres_paa_TAL_ikke_paa_tekst():
    """9 > 10 alfabetisk. En tekst-sortering ville beholde den forkerte og
    slette den nyeste rullebane — stille."""
    behold, _ = vaelg(_apk(8, 9, 10, 11), "jarvis-mobile-11.apk", None)
    assert behold == _apk(11, 10)


def test_navnet_udledes_af_versionskoden():
    assert pma.apk_navn(129) == "jarvis-mobile-129.apk"


def test_afviser_apk_med_anden_signatur_end_installeret_app(monkeypatch, tmp_path):
    monkeypatch.setattr(pma, "find_apksigner", lambda: "apksigner")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(
        a[0], 0, "Signer #1 certificate SHA-256 digest: 0e2d72234ab8381a64885debc46799ef0581c109b165ee34d69066c6fb8c9cef\n", ""
    ))
    with pytest.raises(SystemExit, match="signatur"):
        pma.kontroller_apk_signatur(tmp_path / "ny.apk")


def test_tillader_samme_signatur_som_installeret_app(monkeypatch, tmp_path):
    monkeypatch.setattr(pma, "find_apksigner", lambda: "apksigner")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(
        a[0], 0, f"Signer #1 certificate SHA-256 digest: {pma.MOBILE_INSTALL_SIGNER_SHA256}\n", ""
    ))
    pma.kontroller_apk_signatur(tmp_path / "ny.apk")
