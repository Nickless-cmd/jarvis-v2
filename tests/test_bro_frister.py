"""Vagt: broens svar-frist skal ligge over serverens kommando-frist.

To frister mødes i `tool_invoke` og betyder to forskellige ting:

  * ``timeout_s`` — hvor længe PROCESSEN må LEVE. ``asyncSpawn`` dræber den med
    SIGTERM når den udløber.
  * ``timeout_ms`` — hvor længe vi må VENTE på svar.

Serveren (``core/tools/operator_tools.py``) caper kommandoen ved 300 s og sender
``timeout_s + 25 s`` som dispatch-frist — altså op til **325 s**. Klienten
(``apps/*/electron/bridge.ts``) havde et hardkodet loft på **120 s**.

MÅLT 25/9-2026: for hvert kald over ~110 s gav klienten derfor op FØR serveren.
Kommandoen fuldførte, ``handler_timeout`` gik tilbage, og svaret faldt på gulvet
uden at nogen kaldte det en fejl — den farlige variant, fordi et tabt svar ikke
ligner et tabt svar.

Fejlen kunne ikke ses i nogen af de to filer alene; den opstår først i mødet
mellem dem. Derfor læser denne test begge sider — og læser serverens tal fra
kilden i stedet for at gentage dem her, så et ændret cap tvinger klienten med.

Broen findes i to kopier (``jarvis-desk`` og den ældre ``jarvisx``). De var
identiske da fejlen blev rettet, og der findes ingen mekanisme der holder dem
sådan — så testen kræver det.
"""
from __future__ import annotations

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
KOPIER = [
    REPO / "apps" / "jarvis-desk" / "electron" / "bridge.ts",
    REPO / "apps" / "jarvisx" / "electron" / "bridge.ts",
]
SERVER = REPO / "core" / "tools" / "operator_tools.py"

# Serverens to tal, læst fra kilden. Ændrer nogen cappet eller slacken, skal
# klientens loft følge med — og så skal denne test sige det.
_CMD_CAP = re.compile(r"timeout_s = min\(max\(timeout_s, 1\.0\), ([\d.]+)\)")
_DISPATCH_SLACK = re.compile(r"timeout_s=timeout_s \+ ([\d.]+)")

# Klientens loft skal være bygget af navngivne klodser, ikke et literalt tal.
_LOFT_BYGGET = re.compile(
    r"const HANDLER_CEILING_MS =\s*SERVER_MAX_COMMAND_MS \+ SERVER_DISPATCH_SLACK_MS \+ HANDLER_GRACE_MS"
)
_MIN_BRUGER_LOFTET = re.compile(
    r"const HANDLER_TIMEOUT_MS = Math\.min\(\s*serverTimeoutMs \+ HANDLER_GRACE_MS,\s*HANDLER_CEILING_MS,"
)
# Fejlbeskeden skal nævne det faktiske tal. Den gamle sagde «within 40s» mens
# fristen var op til 120 s — et tal der ikke var tallet.
_HAARDKODET_FEJL = re.compile(r"did not respond within \d+s")
_FEJL_MED_VAERDI = "did not respond within ${"


def _kopi_navn(sti: pathlib.Path) -> str:
    return sti.parent.parent.name


def _ts_tal(tekst: str, navn: str) -> int:
    m = re.search(rf"const {navn} = ([\d_]+)", tekst)
    assert m, (
        f"`const {navn}` blev ikke fundet i broen. Klodsen der bærer forholdet "
        "mellem de to frister er væk — er loftet blevet et hardkodet tal igen?"
    )
    return int(m.group(1).replace("_", ""))


_ASYNC_DEF = re.compile(r"^async def (\w+)\(", re.M)


def _funktion(tekst: str, navn: str) -> str:
    """Kroppen af ``async def navn(...)`` — frem til næste top-level def."""
    start = tekst.index(f"async def {navn}(")
    naeste = _ASYNC_DEF.search(tekst, start + 1)
    return tekst[start : naeste.start() if naeste else len(tekst)]


def _server_tal() -> tuple[int, int]:
    """(kommando-cap, dispatch-slack) i millisekunder for `operator_bash`.

    Tallene læses inde i ``operator_bash_async`` — ikke fra hele filen. Der
    findes flere ``timeout_s=timeout_s + N`` samme sted (screenshot 30 s,
    webfetch 35 s …), og kun den der hører til bash-kaldet gælder for broens
    frist. Målt 25/9-2026: en løs søgning i hele filen gav 30 s og meldte fejl
    om en kode der var rigtig.
    """
    krop = _funktion(SERVER.read_text(encoding="utf-8"), "operator_bash_async")
    cap = _CMD_CAP.search(krop)
    slack = _DISPATCH_SLACK.search(krop)
    assert cap, "kunne ikke læse kommando-cappet i operator_bash_async — er udtrykket flyttet?"
    assert slack, "kunne ikke læse dispatch-slacken i operator_bash_async — er udtrykket flyttet?"
    return int(float(cap.group(1)) * 1000), int(float(slack.group(1)) * 1000)


@pytest.mark.parametrize("sti", KOPIER, ids=_kopi_navn)
def test_loftet_daekker_serverens_maksimum(sti: pathlib.Path):
    """Loftet skal ligge OVER det serveren selv venter — ellers tabes svaret."""
    tekst = sti.read_text(encoding="utf-8")
    cap, slack = _server_tal()
    max_ms = _ts_tal(tekst, "SERVER_MAX_COMMAND_MS")
    slack_ms = _ts_tal(tekst, "SERVER_DISPATCH_SLACK_MS")
    grace_ms = _ts_tal(tekst, "HANDLER_GRACE_MS")

    assert max_ms == cap, (
        f"broens SERVER_MAX_COMMAND_MS ({max_ms} ms) svarer ikke til serverens "
        f"kommando-cap ({cap} ms). Et af tallene er flyttet uden det andet."
    )
    assert slack_ms == slack, (
        f"broens SERVER_DISPATCH_SLACK_MS ({slack_ms} ms) svarer ikke til "
        f"serverens dispatch-slack ({slack} ms)."
    )

    loft = max_ms + slack_ms + grace_ms
    venter = max_ms + slack_ms
    assert loft > venter, (
        f"loftet ({loft} ms) er ikke over serverens maksimale ventetid "
        f"({venter} ms) — klienten giver op før serveren, og et svar der er på "
        "vej falder på gulvet uden at nogen kalder det en fejl."
    )
    assert _LOFT_BYGGET.search(tekst), (
        "loftet er ikke længere bygget af navngivne klodser. Et literalt tal her "
        "kan ikke følge serveren når den ændrer sig."
    )
    assert _MIN_BRUGER_LOFTET.search(tekst), (
        "`HANDLER_TIMEOUT_MS` bruger ikke længere `HANDLER_CEILING_MS` som loft."
    )


@pytest.mark.parametrize("sti", KOPIER, ids=_kopi_navn)
def test_fejlbeskeden_naevner_det_faktiske_tal(sti: pathlib.Path):
    """Et svar der nævner et forkert tal sender læseren længere fra svaret."""
    tekst = sti.read_text(encoding="utf-8")
    assert _FEJL_MED_VAERDI in tekst, (
        "fejlbeskeden indsætter ikke den faktiske frist. Den skal beregnes, "
        "ikke skrives ind."
    )
    haard = _HAARDKODET_FEJL.search(tekst)
    assert not haard, (
        f"fejlbeskeden nævner et hardkodet tal ({haard.group(0)!r}) i stedet for "
        "den frist der faktisk gjaldt."
    )


def test_de_to_kopier_er_ens():
    """To kopier af samme blok driver fra hinanden før eller siden."""
    blokke = []
    for sti in KOPIER:
        tekst = sti.read_text(encoding="utf-8")
        start = tekst.index("const SERVER_MAX_COMMAND_MS")
        slut = tekst.index("const result = await Promise.race", start)
        blokke.append(re.sub(r"\s+", " ", tekst[start:slut]).strip())
    assert blokke[0] == blokke[1], (
        "de to bro-kopier er ikke længere enige om fristerne:\n"
        f"  {_kopi_navn(KOPIER[0])}: {blokke[0][:200]}\n"
        f"  {_kopi_navn(KOPIER[1])}: {blokke[1][:200]}\n"
        "Ret begge — en rettelse i én kopi er en rettelse der ikke findes."
    )
