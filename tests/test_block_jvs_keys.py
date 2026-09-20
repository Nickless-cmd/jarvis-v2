"""Nøgle-vagten skal AFVISE. Den har aldrig haft en test.

Den findes fordi detect-secrets' entropi-detektor MISSEDE den ægte læk i
`a1f1f9ee` (6/5-2026): hex-klumpens entropi i kontekst lå under tærsklen.
Et bogstaveligt regex er utvetydigt — men kun hvis nogen har set det ramme.

Nøglen i testen bygges af stumper ved kørsel, så testfilen aldrig selv
indeholder noget der ligner en nøgle i repoet.
"""
import subprocess
from pathlib import Path

VAGT = Path(__file__).resolve().parents[1] / "scripts/block_jvs_keys.sh"


def _koer(*filer):
    return subprocess.run(["bash", str(VAGT), *map(str, filer)],
                          capture_output=True, text=True, check=False)


def _falsk_noegle() -> str:
    """Formen `jvs-<bruger>-<hex>` — samlet ved kørsel, aldrig som én streng."""
    return "-".join(["jvs", "testbruger", "0" * 24])


def test_en_noegle_i_en_fil_afvises(tmp_path):
    f = tmp_path / "config.py"
    f.write_text(f'NOEGLE = "{_falsk_noegle()}"\n', encoding="utf-8")
    r = _koer(f)
    assert r.returncode == 1
    assert "Jarvis-issued API key found" in r.stderr


def test_en_ren_fil_gaar_igennem(tmp_path):
    f = tmp_path / "ren.py"
    f.write_text("NOEGLE = read_runtime_key('anthropic')\n", encoding="utf-8")
    assert _koer(f).returncode == 0


def test_for_kort_hex_er_ikke_en_noegle(tmp_path):
    """Grænsen er 20 hex-tegn. Under den er det et id, ikke en nøgle."""
    f = tmp_path / "kort.py"
    f.write_text('x = "' + "-".join(["jvs", "bruger", "0" * 8]) + '"\n', encoding="utf-8")
    assert _koer(f).returncode == 0


def test_en_noegle_blandt_flere_filer_faelder_hele_commiten(tmp_path):
    ren, beskidt = tmp_path / "a.py", tmp_path / "b.py"
    ren.write_text("x = 1\n", encoding="utf-8")
    beskidt.write_text(_falsk_noegle() + "\n", encoding="utf-8")
    assert _koer(ren, beskidt).returncode == 1


def test_en_sti_der_ikke_findes_springes_over(tmp_path):
    assert _koer(tmp_path / "findes-ikke.py").returncode == 0
