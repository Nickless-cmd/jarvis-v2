"""Gaten må se HELE kommandoen, ikke kun dens første ord.

Målt 30/10-2026 mod den levende funktion: fem skrivende kommandoer blev
klassificeret som ``auto`` og kørte uden at Bjørn blev spurgt.

    classify_command('echo foo > /tmp/x')                       -> auto
    classify_command('echo foo >> /media/projects/.../README.md') -> auto
    classify_command('cat /etc/passwd > /tmp/x')                 -> auto
    classify_command('grep -r foo . | tee /tmp/out')             -> auto
    classify_command('find . -name x -delete')                   -> auto

Årsagen er ikke at listerne er for korte — ``echo``, ``cat``, ``grep`` og
``find`` ER legitime læsninger og skal blive ved med at være det. Det der
mangler er at klassifikatoren kun ser det FORRESTE ord: en redirect, et
skrivende pipe-segment og et ``find``-flag bliver aldrig inspiceret.

Kommentaren i ``simple_tools.py:675`` dokumenterede allerede svagheden ordret
(«because ``echo`` is in _READ_ONLY_COMMAND_PREFIXES (no redirect awareness)»)
— den blev aldrig fulgt op.

Testen er skrevet FØR rettelsen, så den er rød på den nuværende kode. Den
kører mod den ægte ``classify_command``; en fake klassifikator ville svare det
samme uanset input og kunne aldrig se hullet.
"""

from __future__ import annotations

import pytest

from core.tools.simple_tools import classify_command


# ---------------------------------------------------------------------------
# De fem målte huller — ingen af dem må give ``auto``.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command",
    [
        "echo foo > /tmp/x",
        "echo foo >> /media/projects/jarvis-v2/README.md",
        "cat /etc/passwd > /tmp/x",
        "grep -r foo . | tee /tmp/out",
        "find . -name x -delete",
    ],
)
def test_skrivende_kommando_er_ikke_auto(command: str) -> None:
    assert classify_command(command) != "auto", (
        f"{command!r} skriver til disken men blev klassificeret som auto"
    )


def test_find_delete_gaar_til_approval() -> None:
    """Opgavens eksplicitte efterprøvning: ``find . -delete`` skal mindst give approval."""
    assert classify_command("find . -name x -delete") in {"approval", "destructive"}


# ---------------------------------------------------------------------------
# Redirects: ``>`` og ``>>`` uden for quotes gør kommandoen muterende.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command",
    [
        "echo foo > /tmp/x",
        "echo foo >> /tmp/x",
        "printf 'a' > /tmp/x",
        "cat /etc/hosts > /tmp/out",
        "ls > /tmp/listing",
        "grep foo /etc/hosts > /tmp/x",
        "head -5 /etc/hosts > /tmp/x",
        "wc -l /etc/hosts > /tmp/x",
    ],
)
def test_redirect_uden_for_quotes_er_ikke_auto(command: str) -> None:
    assert classify_command(command) != "auto", (
        f"{command!r} omdirigerer output til en fil men blev auto"
    )


def test_redirect_inde_i_quotes_taeller_ikke() -> None:
    """En ``>`` inde i en streng er tekst, ikke en omdirigering."""
    assert classify_command("echo 'a > b'") == "auto"
    assert classify_command('grep "x > y" /etc/hosts') == "auto"


# ---------------------------------------------------------------------------
# Pipe-segmenter: ``tee``/``sponge`` skriver, også når segmentet før læser.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command",
    [
        "grep -r foo . | tee /tmp/out",
        "cat /etc/hosts | tee /tmp/out",
        "ls -la | tee -a /tmp/log",
        "echo hej | tee /tmp/x",
        "cat /etc/hosts | sponge /tmp/x",
        "find . -name '*.py' | tee /tmp/list",
    ],
)
def test_skrivende_pipe_segment_er_ikke_auto(command: str) -> None:
    assert classify_command(command) != "auto", (
        f"{command!r} skriver gennem et pipe-segment men blev auto"
    )


def test_ren_laesende_pipe_er_stadig_auto() -> None:
    """Pipe uden skrivende segment er stadig en læsning — vi må ikke brække den."""
    assert classify_command("cat /etc/hosts | grep localhost") == "auto"
    assert classify_command("grep -r foo . | head -5") == "auto"
    assert classify_command("cat /etc/hosts | wc -l") == "auto"
    assert classify_command("ls -la | sort") == "auto"


# ---------------------------------------------------------------------------
# ``find`` med skrivende flag.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command",
    [
        "find . -name x -delete",
        "find /tmp -delete",
        "find . -fprint /tmp/out",
        "find . -fprint0 /tmp/out",
        "find . -fprintf /tmp/out '%p'",
        "find . -ok rm {} ;",
        "find . -okdir rm {} ;",
    ],
)
def test_find_med_skrivende_flag_er_ikke_auto(command: str) -> None:
    assert classify_command(command) != "auto", (
        f"{command!r} muterer gennem et find-flag men blev auto"
    )


def test_find_uden_skrivende_flag_er_stadig_auto() -> None:
    assert classify_command("find . -name '*.py'") == "auto"
    assert classify_command("find . -name '*.py' -type f") == "auto"
    assert classify_command("find . -newer /etc/hosts") == "auto"


# ---------------------------------------------------------------------------
# De beslutninger der ALLEREDE virkede må ikke ændre sig.
# ---------------------------------------------------------------------------

def test_eksisterende_beslutninger_uaendrede() -> None:
    # ;-kæder er fail-closed → approval (bevidst, 26/10).
    assert classify_command("ls; systemctl stop jarvis-runtime") == "approval"
    assert classify_command("ls; rm -rf /tmp/x") in {"approval", "destructive"}
    # sed -i er muterende.
    assert classify_command("sed -i 's/a/b/' /tmp/x") != "auto"
    # rene læsninger er stadig auto.
    assert classify_command("ls -la") == "auto"
    assert classify_command("cat /etc/hosts") == "auto"
    assert classify_command("grep -r foo .") == "auto"
    assert classify_command("git status") == "auto"
    assert classify_command("git log --oneline") == "auto"


def test_ukendt_pipe_segment_er_fail_closed() -> None:
    """Et segment vi ikke kender må ikke arve «read-only» fra segmentet før."""
    assert classify_command("cat /etc/hosts | ukendt-vaerktoej --flag") == "approval"
