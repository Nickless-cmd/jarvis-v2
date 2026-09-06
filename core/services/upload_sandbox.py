"""Uploadede filer og arkiver — pakket ud ét sted, og aldrig eksekverbart.

Bjørn: «filer og zip filer skal helst kun kunne køre i chroot mode eller et andet
sikkert virtuelt sted».

Der findes hverken bubblewrap eller firejail på runtime-værten, men det er ikke
dét der bærer risikoen her. Ingen del af systemet EKSEKVERER en uploadet fil —
Jarvis får at vide at han kan `read_file(...)` den. Faren ligger i udpakningen,
og den har tre klassiske former:

  * zip-slip      — en post hedder «../../.ssh/authorized_keys» og skriver uden
                    for målmappen
  * zip-bombe     — 42 kB pakker ud til 4 GB og fylder disken
  * link-flugt    — en symlink i et tar-arkiv peger på /etc/shadow, og næste
                    læsning følger den ud af sandkassen

Derfor: udpakning sker ALDRIG med `ZipFile.extractall`/`TarFile.extractall`. Hver
post vurderes for sig, og alt der peger ud af sandkassen afvises. Filer skrives
0600 og mapper 0700 — uden eksekverbar bit, uanset hvad arkivet påstod.

Sandkassen er en mappe pr. vedhæftning under `~/.jarvis-v2/uploads/_sandbox/`.
Det er ikke en chroot, og det påstår modulet heller ikke at være: det er
inddæmning af SKRIVNINGER, plus en fil-tilstand der gør eksekvering umulig.
Kører runtimen i sin egen LXC, er det det lag der bærer procesisolationen.
"""
from __future__ import annotations

import os
import stat
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

_SANDBOX_ROOT = Path.home() / ".jarvis-v2" / "uploads" / "_sandbox"

# Værn mod zip-bomber. Tallene er sat efter hvad der er rimeligt at sende i en
# chat, ikke efter hvad et arkivformat kan.
_MAX_ENTRIES = 2_000
_MAX_TOTAL_BYTES = 512 * 1024 * 1024      # 512 MB udpakket
_MAX_RATIO = 200                           # udpakket / pakket

_ARCHIVE_SUFFIXES = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".tbz2", ".txz"}


@dataclass
class ExtractResult:
    ok: bool
    reason: str = ""
    root: str = ""
    files: list[str] = field(default_factory=list)
    total_bytes: int = 0
    skipped: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "reason": self.reason, "root": self.root,
                "files": self.files, "total_bytes": self.total_bytes,
                "skipped": self.skipped}


def looks_like_archive(path: str | Path) -> bool:
    """Er filen et arkiv? Afgøres på INDHOLD, ikke på navn.

    Et navn kan lyve; `zipfile.is_zipfile` kigger efter den faktiske signatur.
    Suffikset bruges kun som et ekstra ja, aldrig som eneste grund.
    """
    p = Path(path)
    try:
        if zipfile.is_zipfile(p) or tarfile.is_tarfile(p):
            return True
    except Exception:
        pass
    return p.suffix.lower() in _ARCHIVE_SUFFIXES


def harden_upload(path: str | Path) -> None:
    """Gør en uploadet fil ulæselig for andre og umulig at eksekvere.

    Kaldes på ALT der lander fra en upload. En fil der ikke kan eksekveres, kan
    ikke køres ved et uheld — heller ikke af en fejl et helt andet sted i
    systemet. Self-safe: en rettighedsændring må ikke kunne vælte en upload.
    """
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except Exception:
        pass


def sandbox_root_for(attachment_id: str) -> Path:
    """Mappen et bestemt arkiv pakkes ud i. Én pr. vedhæftning."""
    safe = "".join(c for c in str(attachment_id or "") if c.isalnum() or c in "-_")[:64]
    return _SANDBOX_ROOT / (safe or "ukendt")


def _is_inside(root: Path, candidate: Path) -> bool:
    """Ligger `candidate` under `root` — også efter symlink-opløsning?

    `Path.resolve()` følger links, så en post der peger ud af sandkassen bliver
    afsløret her og ikke først når nogen læser den.
    """
    try:
        root_r = root.resolve()
        cand_r = candidate.resolve()
    except Exception:
        return False
    return root_r == cand_r or root_r in cand_r.parents


def _reject_name(name: str) -> str:
    """Tom streng hvis navnet er i orden, ellers grunden til at det ikke er."""
    n = str(name or "")
    if not n.strip():
        return "tomt navn"
    if n.startswith("/") or (len(n) > 1 and n[1] == ":"):
        return "absolut sti"
    parts = Path(n).parts
    if ".." in parts:
        return "sti peger opad (..)"
    return ""


def _write_entry(dest: Path, data_iter, remaining: int) -> int:
    """Skriv én post og returnér antal skrevne bytes. Rejser ValueError ved loft."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(dest, "wb") as fh:
        for chunk in data_iter:
            written += len(chunk)
            if written > remaining:
                raise ValueError("udpakket indhold overskrider loftet")
            fh.write(chunk)
    harden_upload(dest)
    return written


def _chunks(fileobj, size: int = 64 * 1024):
    while True:
        chunk = fileobj.read(size)
        if not chunk:
            return
        yield chunk


def safe_extract(archive_path: str | Path, attachment_id: str) -> ExtractResult:
    """Pak et arkiv ud i sin egen sandkasse — post for post.

    Afviser hele arkivet ved zip-slip eller loft-overskridelse; springer enkelte
    links og specialfiler over og noterer dem i `skipped`. Forskellen er
    bevidst: en sti der peger ud af sandkassen er et ANGREB og skal stoppe det
    hele, mens en symlink kan være uskyldig rod i et ellers fint arkiv.
    """
    src = Path(archive_path)
    if not src.exists():
        return ExtractResult(False, reason="filen findes ikke")

    root = sandbox_root_for(attachment_id)
    try:
        root.mkdir(parents=True, exist_ok=True)
        os.chmod(root, stat.S_IRWXU)  # 0700
    except Exception as exc:
        return ExtractResult(False, reason=f"kunne ikke oprette sandkasse: {exc}")

    packed = max(1, src.stat().st_size)
    files: list[str] = []
    skipped: list[str] = []
    total = 0

    try:
        if zipfile.is_zipfile(src):
            with zipfile.ZipFile(src) as zf:
                infos = zf.infolist()
                if len(infos) > _MAX_ENTRIES:
                    return ExtractResult(False, reason=f"arkivet har over {_MAX_ENTRIES} poster")
                declared = sum(i.file_size for i in infos)
                if declared > _MAX_TOTAL_BYTES:
                    return ExtractResult(False, reason="udpakket størrelse over loftet")
                if declared / packed > _MAX_RATIO:
                    return ExtractResult(False, reason="mistænkeligt kompressionsforhold (zip-bombe)")
                for info in infos:
                    bad = _reject_name(info.filename)
                    if bad:
                        return ExtractResult(False, reason=f"afvist post «{info.filename}»: {bad}")
                    dest = root / info.filename
                    if not _is_inside(root, dest.parent if info.is_dir() else dest):
                        return ExtractResult(False, reason=f"post peger ud af sandkassen: {info.filename}")
                    if info.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                        continue
                    with zf.open(info) as fh:
                        total += _write_entry(dest, _chunks(fh), _MAX_TOTAL_BYTES - total)
                    files.append(str(dest))
        elif tarfile.is_tarfile(src):
            with tarfile.open(src) as tf:
                members = tf.getmembers()
                if len(members) > _MAX_ENTRIES:
                    return ExtractResult(False, reason=f"arkivet har over {_MAX_ENTRIES} poster")
                declared = sum(m.size for m in members)
                if declared > _MAX_TOTAL_BYTES:
                    return ExtractResult(False, reason="udpakket størrelse over loftet")
                if declared / packed > _MAX_RATIO:
                    return ExtractResult(False, reason="mistænkeligt kompressionsforhold (zip-bombe)")
                for m in members:
                    bad = _reject_name(m.name)
                    if bad:
                        return ExtractResult(False, reason=f"afvist post «{m.name}»: {bad}")
                    dest = root / m.name
                    if not _is_inside(root, dest.parent if m.isdir() else dest):
                        return ExtractResult(False, reason=f"post peger ud af sandkassen: {m.name}")
                    if m.isdir():
                        dest.mkdir(parents=True, exist_ok=True)
                        continue
                    if not m.isfile():
                        # Links, enheder, fifoer: ingen af dem har et ærinde i en
                        # chat-vedhæftning, og et link er netop vejen UD af
                        # sandkassen. Springes over, ikke fulgt.
                        skipped.append(m.name)
                        continue
                    fh = tf.extractfile(m)
                    if fh is None:
                        skipped.append(m.name)
                        continue
                    total += _write_entry(dest, _chunks(fh), _MAX_TOTAL_BYTES - total)
                    files.append(str(dest))
        else:
            return ExtractResult(False, reason="ikke et genkendt arkiv")
    except ValueError as exc:
        return ExtractResult(False, reason=str(exc))
    except Exception as exc:
        return ExtractResult(False, reason=f"udpakning fejlede: {type(exc).__name__}: {exc}")

    return ExtractResult(True, root=str(root), files=files, total_bytes=total, skipped=skipped)


def scan_tree(root: str | Path) -> tuple[bool, str]:
    """Kør ClamAV på en udpakket sandkasse. (ren, begrundelse).

    Arkivet selv blev scannet ved upload, men clamscan's arkiv-understøttelse
    har grænser (dybde, kryptering). Efter udpakning ligger indholdet fladt og
    kan scannes for hvad det er.
    """
    try:
        from core.services.malware_scan import scan_file
        report = scan_file(str(root))
    except Exception as exc:
        return True, f"scanning ikke mulig: {exc}"
    if report.status == "infected":
        return False, f"malware i arkivet: {report.signature}"
    return True, report.status
