"""`;` er ikke en sikker segment-graense — og det er en BEVIDST beslutning.

Maalt 26/10-2026 efter 13 falske approvals: rene laesekommandoer som
``cd /media/projects/jarvis-v2; sed -n 95,120p core/services/x.py`` blev
klassificeret som ``risk_class=write`` og sendt til Bjorn som kort.

Fristelsen er at give ``;`` samme segment-logik som ``&&``. Det blev
forsogt og rullet tilbage samme aften, fordi det gjorde gaten UTAET:
``cd /tmp; echo hej > fil.txt``, ``ls; curl -X POST http://x`` og
``cd /tmp; python3 -c 'open("f","w").write(1)'`` slap alle igennem som
``auto``.

``simple_tools.py:943`` baerer allerede ``";" not in normalized`` — nogen
har vaeret her foer og valgt at ``;`` ikke maa segmenteres. Denne fil
fastholder hvorfor, saa beslutningen ikke bliver omgjort ved et uheld.

To ting skal holde SAMTIDIG:

1. En ren laesning med ``;`` boer ikke kraeve godkendelse (i dag goer den).
2. En skrivning med ``;`` maa ALDRIG slippe igennem som ``auto``.

Test 2 er den vigtige. Test 1 er ``xfail(strict=True)`` indtil nogen
loeser problemet ordentligt — og hvis nogen loeser det ved at tilfoeje
en ``;``-gren uden at taenke, bliver test 1 groen mens test 2 fejler.
Det er praecis den kombination der skal vaere umulig at committe.
"""

from __future__ import annotations

import pytest

from core.tools.simple_tools import classify_command

# De faktiske kommandoer der blev sendt til godkendelse som "write"
# i perioden 7.-22. oktober 2026. Alle er ren laesning.
RENE_LAESNINGER = [
    "cd /media/projects/jarvis-v2; sed -n 95,120p core/services/x.py",
    "cd . 2>/dev/null; sed -n 105,135p core/services/x.py",
    "cd /media/projects/jarvis-v2; ls core/services | head",
    "cd ~/.jarvis-v2; crontab -l 2>&1 | head -30",
    "cd /media/projects/jarvis-v2; sed -n '380,420p;860,1030p' core/services/x.py",
]

# Skrivende kommandoer med samme form. Disse maa ALDRIG blive "auto".
SKRIVENDE = [
    "cd /tmp; echo hej > fil.txt",
    "cd /tmp; echo hej >> fil.txt",
    "ls; curl -X POST http://x",
    "cd /tmp; python3 -c 'open(\"f\",\"w\").write(1)'",
    "cd /tmp; rm -rf build",
    "cd /tmp; touch ny.txt",
]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Maalt 26/10-2026: `;` segmenteres ikke (simple_tools.py:943 har "
        "bevidst `\";\" not in normalized`), saa rene laesninger med "
        "semikolon gaar til approval. Det er fail-closed — den rigtige "
        "pris indtil en reel sandbox eller dedikerede vaerktoejer loeser "
        "det. Rettes IKKE ved at tilfoeje en `;`-gren: se testen nedenfor."
    ),
)
@pytest.mark.parametrize("kommando", RENE_LAESNINGER)
def test_ren_laesning_med_semikolon_er_auto(kommando: str) -> None:
    """Oensket adfaerd — ikke haandhaevet i dag."""
    assert classify_command(kommando) == "auto"


@pytest.mark.parametrize("kommando", SKRIVENDE)
def test_skrivning_med_semikolon_slipper_aldrig_igennem(kommando: str) -> None:
    """Haandhaevet i dag, og maa blive ved med at vaere det.

    Denne test er grunden til at testen ovenfor ikke bare maa "rettes"
    med en ny regex-gren: en `;`-segmentering der arver `&&`-grenens
    svagheder (`>`-omdirigering, `curl` uden metode-tjek, ukendte
    interpretere) fejler her.
    """
    assert classify_command(kommando) != "auto", (
        f"SIKKERHEDSFEJL: {kommando!r} blev klassificeret som auto. "
        "En `;`-segmentering maa ikke slippe skrivende kommandoer igennem."
    )


def test_semikolon_er_stadig_udelukket_fra_pipe_grenen() -> None:
    """Vagten paa kilden: `;` maa ikke snige sig ind som segment-graense.

    Parser AST'en i stedet for at grepe efter en skrivemaade — en
    kommentar eller en streng-literal maa ikke kunne tilfredsstille den.
    """
    import ast
    from pathlib import Path

    kilde = Path("core/tools/simple_tools.py").read_text(encoding="utf-8")
    tree = ast.parse(kilde)

    # Find classify_command og led efter en sammenligning med ';'
    fundet = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "classify_command":
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value == ";":
                fundet.append(sub.lineno)

    assert fundet, (
        "`;` optraeder ikke som literal i classify_command. Enten er guarden "
        "fjernet, eller kommandoen er omdobt. Begge dele kraever et bevidst valg."
    )
