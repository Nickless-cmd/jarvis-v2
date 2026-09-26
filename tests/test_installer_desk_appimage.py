"""Installeren skal holde `.desktop` og AppArmor-profil i takt med AppImage'ens sti.

Baggrund, målt 26/9-2026: to fejl med samme symptom — «ikonet gør ingenting».
`StartupWMClass` pegede på filnavnet i stedet for vinduets klasse, og
AppArmor-profilen manglede, så Electrons zygote døde når gnome-shell startede
appen. Begge er ting der DRIVER når artefakten skifter navn eller sted.

Scriptet udleder derfor alt af AppImage'ens egen indlejrede `.desktop` — den
er sandhedskilden. Testene her måler at intet er hardkodet, og at den ene
rettighed profilen giver ikke vokser.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import installer_desk_appimage as I  # noqa: E402

FELTER = {
    "Name": "J.A.R.V.I.S.",
    "Exec": "AppRun --no-sandbox %U",
    "Terminal": "false",
    "Type": "Application",
    "Icon": "jarvis-desktop",
    "StartupWMClass": "J.A.R.V.I.S.",
    "Comment": "En kommentar",
    "Categories": "Office;",
}


# ── Profilen følger stien ───────────────────────────────────────────────────


def test_profilen_peger_paa_den_sti_den_faar():
    """KERNEN. Skifter AppImage'en sted, skal profilen med — ellers er vi
    tilbage ved «ikonet gør ingenting»."""
    for sti in ("/home/bs/Applications/J.A.R.V.I.S.AppImage",
                "/tmp/nyt-sted/J.A.R.V.I.S.AppImage",
                "/opt/jarvis/J.A.R.V.I.S-0.7.0.AppImage"):
        p = I.byg_profil("jarvis-desktop", Path(sti))
        assert f"profile jarvis-desktop {sti} flags=(unconfined)" in p


def test_profilen_giver_KUN_userns():
    """Den skal give den ene rettighed der manglede — ikke flere.

    `flags=(unconfined)` er Ubuntus egen form (se /etc/apparmor.d/1password):
    profilen findes for at give processen et NAVN og én undtagelse, ikke for
    at åbne noget op.
    """
    p = I.byg_profil("jarvis-desktop", Path("/x/y.AppImage"))
    regler = [l.strip().rstrip(",") for l in p.split("\n")
              if l.startswith("  ") and l.strip() and not l.strip().startswith("#")
              and not l.strip().startswith("include")]
    assert regler == ["userns"], f"profilen giver mere end userns: {regler}"


def test_profilen_siger_hvem_der_ejer_den():
    """Rettes stien i hånden, driver den fra scriptet igen ved næste udgivelse."""
    p = I.byg_profil("jarvis-desktop", Path("/x/y.AppImage"))
    assert "installer_desk_appimage.py" in p
    assert "ret ikke stien i haanden" in p


# ── .desktop udledes, ikke gættes ───────────────────────────────────────────


def test_wm_klassen_kommer_fra_appimagens_egen_fil():
    """Den var sat til filnavnet i hånden. Derfor kunne GNOME ikke koble
    vinduet til ikonet."""
    d = I.byg_desktop(FELTER, Path("/x/y.AppImage"))
    assert "StartupWMClass=J.A.R.V.I.S." in d
    assert "StartupWMClass=jarvis-desktop" not in d


def test_no_sandbox_fjernes():
    """electron-builder lægger `--no-sandbox` i den indlejrede fil. Med
    profilen er den unødvendig, og appen renderer indhold fra nettet."""
    d = I.byg_desktop(FELTER, Path("/x/y.AppImage"))
    assert "--no-sandbox" not in d
    assert "Exec=/x/y.AppImage %U" in d


def test_apprun_erstattes_af_den_rigtige_sti():
    """`AppRun` findes kun inde i mountet — den kan ikke startes udefra."""
    d = I.byg_desktop(FELTER, Path("/x/y.AppImage"))
    assert "AppRun" not in d


def test_uden_placeholder_faar_exec_heller_ingen():
    d = I.byg_desktop(dict(FELTER, Exec="AppRun"), Path("/x/y.AppImage"))
    assert "Exec=/x/y.AppImage\n" in d


def test_genereringen_er_idempotent():
    """Et script der altid melder «opdateret» lærer man at overse.

    Rækkefølgen er electron-builders egen, så en uændret installation ikke
    ser ud som en ændring.
    """
    d = I.byg_desktop(FELTER, Path("/x/y.AppImage"))
    assert I.byg_desktop(FELTER, Path("/x/y.AppImage")) == d
    noegler = [l.split("=")[0] for l in d.split("\n") if "=" in l]
    assert noegler[:3] == ["Name", "Exec", "Terminal"]


# ── Manglende felter skal larme, ikke gætte ────────────────────────────────


@pytest.mark.parametrize("mangler", ["Icon", "StartupWMClass", "Name"])
def test_en_appimage_uden_de_noedvendige_felter_afvises(monkeypatch, tmp_path, mangler):
    """Gætter vi et felt, gætter vi netop det der var fejlen."""
    ufuldstaendig = {k: v for k, v in FELTER.items() if k != mangler}

    def _falsk_udpak(appimage, moenster, ud):
        rod = Path(ud) / "squashfs-root"
        rod.mkdir(parents=True, exist_ok=True)
        tekst = "[Desktop Entry]\n" + "\n".join(
            f"{k}={v}" for k, v in ufuldstaendig.items())
        (rod / "jarvis-desktop.desktop").write_text(tekst, encoding="utf-8")

    monkeypatch.setattr(I, "udpak", _falsk_udpak)
    with pytest.raises(I.Fejl, match=mangler):
        I.laes_indlejret_desktop(tmp_path / "en.AppImage")


def test_en_manglende_build_giver_en_brugbar_besked(monkeypatch, tmp_path):
    monkeypatch.setattr(I, "DESK", tmp_path)
    with pytest.raises(I.Fejl, match="npm run package:linux"):
        I.find_appimage()
