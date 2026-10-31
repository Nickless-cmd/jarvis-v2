"""En kommando må ikke gate'es som det den NÆVNER — kun som det den GØR.

Målt 31/10-2026 (den levende funktion, før denne rettelse): 9 af 26 testede
kommandoer blev klassificeret forkert, alle i samme retning — en ren læsning
der blot nævner et farligt ord blev gated som om den udførte det.

    grep -i shutdown /var/log/syslog   -> destructive
    grep mkfs docs.md                  -> destructive
    grep -c rm /tmp/x                  -> destructive
    cat notes-om-reboot.md             -> destructive

Det er samme fejlklasse som 944670023 (rm matchede en OMTALE af rm), men
`quote_aware` løser den ikke: ordet står UQUOTED, som argument til et
læse-program — eller som en del af en sti.

HVORFOR IKKE EN POSITIONS-REGEL

Opgaven foreslog «kræv at rm står som første ord i et segment». Målt på den
levende kode ville den åbne fire huller, fordi de farlige kommandoer typisk
har ordet som ARGUMENT til en wrapper:

    systemctl reboot          reboot er argument til systemctl
    sudo systemctl poweroff   dobbelt-wrapper
    ssh host reboot           argument til ssh — eksekveres på fjernværten
    xargs rm                  argument til xargs — eksekveres

En positions-regel kan ikke skelne `grep -i shutdown` fra `systemctl reboot`:
begge har ordet som andet led. Det der skiller dem er PROGRAMMET — `grep`
fortolker ikke sine argumenter, `systemctl` gør.

DERFOR: indsnævringen er en allowlist af programmer der beviseligt ikke
fortolker deres argumenter som kode (`_segment_er_laesende`, genbrugt fra
simple_tools.py:951). Den er fail-closed ved tvivl, og den kræver at HELE
kommandoen er ét segment — et pipe, en `&&`, en `;`, en `$(`, en backtick
eller en subshell gør svaret «ikke en ren læsning», og så matcher predikaterne
bredt som før.
"""
from __future__ import annotations

import pytest

from core.tools.security_predicates import evaluate_command
from core.tools.simple_tools import classify_command


def _er_destructive(cmd: str) -> bool:
    return classify_command(cmd) == "destructive"


# ── De ni målte falske positiver: ordet nævnes, kommandoen læser ──────────

@pytest.mark.parametrize("cmd", [
    'grep -i shutdown /var/log/syslog',
    'grep mkfs docs.md',
    'grep reboot /var/log/syslog',
    'grep poweroff README.md',
    'grep -c rm /tmp/x',
    'grep "drop table" schema.sql',
    'grep truncate /var/log/x',
    'rg "truncate" core/',
    'cat notes-om-reboot.md',
])
def test_omtale_i_en_ren_laesning_er_ikke_destructive(cmd: str) -> None:
    assert not _er_destructive(cmd), f"{cmd!r} blev gated som en handling"


# ── Kontrakten: de 17 der SKAL fanges må ikke flytte sig ─────────────────

@pytest.mark.parametrize("cmd", [
    'shutdown -h now',
    'reboot',
    'poweroff',
    'systemctl reboot',          # argument til systemctl — eksekveres
    'sudo systemctl poweroff',   # dobbelt-wrapper
    'ssh host reboot',           # eksekveres på fjernværten
    'xargs rm',                  # xargs eksekverer sit argument
    'mkfs.ext4 /dev/sda1',
    '/sbin/mkfs /dev/sda',       # path-formen må ikke åbne et hul
    'truncate -s 0 /var/log/x',
    'psql -c "drop table users"',   # SQL i quotes ER kode
    'mysql -e "drop database x"',
    'rm -f /tmp/x',
    '/bin/rm -rf /',
    'touch a && rm a',
    '(rm a)',
    'bash -c "rm -rf /x"',
])
def test_rigtige_kommandoer_fanges_stadig(cmd: str) -> None:
    assert _er_destructive(cmd), f"{cmd!r} slap gennem som en læsning"


# ── Grænsen: samme ord, men kommandoen er ikke længere ren ───────────────

@pytest.mark.parametrize("cmd", [
    'grep shutdown /var/log/x | xargs reboot',
    'grep reboot /var/log/x && systemctl reboot',
    'echo "shutdown" | bash',
    'cat /var/log/x; reboot',
    'grep rm /tmp/x $(reboot)',
    'cat `reboot`',
])
def test_en_kaede_arver_ikke_omtale(cmd: str) -> None:
    """Så snart kommandoen er mere end ét læse-segment, matcher predikaterne
    bredt igen — ellers kunne man skjule en handling bag en læsning."""
    assert _er_destructive(cmd), f"{cmd!r} blev læst som en ren læsning"


# ── Direkte på predikat-funktionen, så kæden ikke skjuler noget ──────────

def test_evaluate_command_er_ikke_tavs_om_laesningen() -> None:
    """`grep -i shutdown` må give None — ikke et predikat-hit."""
    assert evaluate_command('grep -i shutdown /var/log/syslog') is None


def test_evaluate_command_fanger_systemctl_reboot() -> None:
    hit = evaluate_command('systemctl reboot')
    assert hit is not None
    assert hit["name"] == "reboot"
    assert hit["decision"] == "destructive"
