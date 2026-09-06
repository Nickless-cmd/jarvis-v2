"""Uploadede arkiver pakkes ud inddæmmet — eller slet ikke.

Bjørn bad om at filer og zip-filer kun kunne «køre i chroot mode eller et andet
sikkert virtuelt sted». Faren ligger ikke i eksekvering (intet i systemet kører
en uploadet fil) men i UDPAKNINGEN: zip-slip, zip-bomber og symlinks der peger
ud af sandkassen. Testerne er skrevet mod netop de tre.
"""
from __future__ import annotations

import io
import os
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from core.services import upload_sandbox as us


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(us, "_SANDBOX_ROOT", tmp_path / "_sandbox")
    return tmp_path


def _zip(path: Path, entries: dict[str, bytes], *, compress: bool = False) -> Path:
    # ZipFile komprimerer IKKE som standard (ZIP_STORED). En zip-bombe kræver
    # naturligvis komprimering — ellers måler forholdet 1:1 og testen ville
    # bevise ingenting.
    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(path, "w", compression=mode) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_almindeligt_arkiv_pakkes_ud(sandbox):
    src = _zip(sandbox / "a.zip", {"noter.txt": b"hej", "mappe/b.txt": b"verden"})
    res = us.safe_extract(src, "att1")

    assert res.ok, res.reason
    assert len(res.files) == 2
    assert Path(res.root).is_dir()
    assert (Path(res.root) / "noter.txt").read_bytes() == b"hej"


def test_udpakkede_filer_er_ikke_eksekverbare(sandbox):
    """En fil der ikke kan eksekveres, kan ikke køres ved et uheld — heller ikke
    af en fejl et helt andet sted i systemet."""
    src = _zip(sandbox / "x.zip", {"script.sh": b"#!/bin/sh\necho nej\n"})
    res = us.safe_extract(src, "att2")

    mode = os.stat(res.files[0]).st_mode
    assert not (mode & stat.S_IXUSR)
    assert not (mode & stat.S_IXGRP)
    assert not (mode & stat.S_IXOTH)
    assert stat.S_IMODE(mode) == 0o600


def test_zip_slip_afvises_helt(sandbox):
    """En sti der peger ud af sandkassen er et ANGREB — hele arkivet afvises,
    ikke bare den ene post."""
    src = _zip(sandbox / "evil.zip", {"../../.ssh/authorized_keys": b"noegle"})
    res = us.safe_extract(src, "att3")

    assert res.ok is False
    assert ".." in res.reason or "opad" in res.reason
    assert not (sandbox / ".ssh").exists()


def test_absolut_sti_afvises(sandbox):
    src = _zip(sandbox / "abs.zip", {"/etc/passwd": b"rod"})
    res = us.safe_extract(src, "att4")
    assert res.ok is False
    assert "absolut" in res.reason


def test_for_mange_poster_afvises(sandbox):
    src = _zip(sandbox / "mange.zip", {f"f{i}.txt": b"x" for i in range(us._MAX_ENTRIES + 5)})
    res = us.safe_extract(src, "att5")
    assert res.ok is False
    assert "poster" in res.reason


def test_zip_bombe_afvises_paa_forhold(sandbox, monkeypatch):
    """42 kB der pakker ud til gigabytes. Forholdet afsløres FØR vi skriver
    noget som helst."""
    monkeypatch.setattr(us, "_MAX_RATIO", 5)
    src = _zip(sandbox / "bombe.zip", {"stor.txt": b"a" * 200_000}, compress=True)
    res = us.safe_extract(src, "att6")
    assert res.ok is False
    assert "kompressionsforhold" in res.reason


def test_for_stort_udpakket_afvises(sandbox, monkeypatch):
    monkeypatch.setattr(us, "_MAX_TOTAL_BYTES", 100)
    src = _zip(sandbox / "stor.zip", {"f.txt": b"a" * 5_000})
    res = us.safe_extract(src, "att7")
    assert res.ok is False
    assert "størrelse" in res.reason


def test_symlink_i_tar_springes_over_men_stopper_ikke_arkivet(sandbox):
    """Et link kan være uskyldig rod i et ellers fint arkiv — men det følges
    aldrig, for det er netop vejen UD af sandkassen."""
    src = sandbox / "links.tar"
    with tarfile.open(src, "w") as tf:
        data = b"fin fil"
        info = tarfile.TarInfo("god.txt")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))

        link = tarfile.TarInfo("flugt")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/shadow"
        tf.addfile(link)

    res = us.safe_extract(src, "att8")
    assert res.ok is True
    assert res.skipped == ["flugt"]
    assert not (Path(res.root) / "flugt").exists()
    assert (Path(res.root) / "god.txt").read_bytes() == b"fin fil"


def test_hver_vedhaeftning_faar_sin_egen_mappe(sandbox):
    a = us.safe_extract(_zip(sandbox / "1.zip", {"f": b"1"}), "att-a")
    b = us.safe_extract(_zip(sandbox / "2.zip", {"f": b"2"}), "att-b")
    assert a.root != b.root


def test_id_med_stiseparatorer_kan_ikke_bryde_ud(sandbox):
    """Vedhæftnings-id'et kommer udefra og må ikke kunne styre hvor vi skriver."""
    root = us.sandbox_root_for("../../etc")
    assert ".." not in str(root)


def test_ikke_et_arkiv_giver_aerlig_besked(sandbox):
    plain = sandbox / "billede.png"
    plain.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 50)
    res = us.safe_extract(plain, "att9")
    assert res.ok is False
    assert "arkiv" in res.reason


def test_arkiv_genkendes_paa_indhold_ikke_navn(sandbox):
    """Et navn kan lyve. Signaturen kan ikke."""
    forklaedt = _zip(sandbox / "billede.png", {"f.txt": b"x"})
    assert us.looks_like_archive(forklaedt) is True

    plain = sandbox / "ting.zip"
    plain.write_bytes(b"slet ikke en zip")
    # Suffikset alene er nok til at vi BEHANDLER den som arkiv-kandidat …
    assert us.looks_like_archive(plain) is True
    # … men udpakningen afviser den ærligt.
    assert us.safe_extract(plain, "att10").ok is False


def test_harden_upload_fjerner_eksekverbar_bit(sandbox):
    f = sandbox / "k.sh"
    f.write_text("#!/bin/sh\n")
    os.chmod(f, 0o755)
    us.harden_upload(f)
    assert stat.S_IMODE(os.stat(f).st_mode) == 0o600
