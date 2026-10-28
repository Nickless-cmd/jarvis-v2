"""Vagt: PWA-bygget må ikke være ældre end den kilde den er bygget af.

BAGGRUND (målt 28/10-2026). `apps/jarvis-desk/dist-web` er gitignored
(`.gitignore:15`) og bygges lokalt med `scripts/build_desk_web.sh`. API'et
serverer den direkte (`apps/api/jarvis_api/ui_static.py:11`). Der fandtes
ingen automatik der genbyggede den og ingen test der opdagede at den var
forældet.

Hvad det kostede: fixet for «follow-up-run river svaret ned» blev committet
16:58 (`50da5b3e2`), men `dist-web` var bygget 16:13 — 45 minutter bagud.
PWA'en kørte gammel kode indtil Bjørn spurgte «har du bygget pwa osse?».
Ingen test, hook eller CI fangede det.

Electron-releasen er IKKE et bevis: `.github/workflows/desk-release.yml`
kører `npm run build` (dist/), ikke `build:web` (dist-web/). To forskellige
byg af samme kilde, og den ene blev behandlet som bevis for den anden.

HVORFOR TESTEN SKIPPER OG IKKE BESTÅR
`dist-web/` er gitignored, så den findes ikke i CI. En vagt der ikke måler
noget må ikke se grøn ud — den skal sige hvad den ikke kunne måle og hvorfor.
Derfor `pytest.skip` med en konkret grund, aldrig et bart `return`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DIST_WEB = _REPO_ROOT / "apps" / "jarvis-desk" / "dist-web"
_INDEX = _DIST_WEB / "index.html"
_SRC = _REPO_ROOT / "apps" / "jarvis-desk" / "src"

# En commit der kun rører en test-fil ændrer ikke bundlen. Uden dette filter
# ville hver test-commit give en falsk positiv, og så bliver vagten slukket
# i stedet for rettet.
_IKKE_BUNDLE = ("*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx")


def _seneste_kilde_commit_ts() -> int | None:
    """Seneste commit-tid (epoch) for desk-kilden, uden test-filer.

    Returnerer None når git ikke kan svare — så springer testen over i
    stedet for at gætte.
    """
    if not _SRC.is_dir():
        return None
    args = [
        "git", "-C", str(_REPO_ROOT), "log", "-1",
        "--format=%ct", "--",
        "apps/jarvis-desk/src",
        *[f":(exclude)apps/jarvis-desk/src/**/{p}" for p in _IKKE_BUNDLE],
    ]
    try:
        ud = subprocess.run(
            args, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if ud.returncode != 0:
        return None
    raa = ud.stdout.strip()
    return int(raa) if raa.isdigit() else None


def test_dist_web_er_ikke_aeldre_end_kilden() -> None:
    """Fejl hvis PWA-bygget er ældre end den seneste ændring af bundlen.

    Rettelsen er ikke at røre testen, men at køre:
        scripts/build_desk_web.sh
    """
    if not _INDEX.is_file():
        pytest.skip(
            "dist-web/index.html findes ikke (gitignored, bygges lokalt) — "
            "kan ikke måle byggens alder. Byg med scripts/build_desk_web.sh"
        )

    commit_ts = _seneste_kilde_commit_ts()
    if commit_ts is None:
        pytest.skip(
            "kunne ikke læse seneste commit-tid for apps/jarvis-desk/src "
            "(ingen git eller ingen historik) — kan ikke måle byggens alder"
        )

    byg_ts = int(_INDEX.stat().st_mtime)

    # Byggeriet skal være MINDST lige så nyt som den seneste kildeændring.
    # Et par sekunders slæk dækker at git gemmer sekund-præcision.
    if byg_ts + 2 < commit_ts:
        raise AssertionError(
            "PWA-bygget er ældre end kilden — API'et serverer gammel kode.\n"
            f"  dist-web/index.html: {_tid(byg_ts)}\n"
            f"  seneste src-commit:  {_tid(commit_ts)} "
            f"({_varighed(commit_ts - byg_ts)} bagud)\n"
            "  Ret det med: scripts/build_desk_web.sh\n"
            "  (Electron-releasen er IKKE bevis: den bygger dist/, ikke dist-web/.)"
        )


def _tid(epoch: int) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def _varighed(sekunder: int) -> str:
    """Varighed som menneskelig tekst.

    Rettet 28/10-2026: første udgave sendte `commit_ts - byg_ts` gennem `_tid()`,
    som formaterede et sekund-tal som et tidsstempel — fejlbeskeden sagde
    «1970-01-01 01:45:15 bagud» om et byg der var 45 minutter bagud. En
    fejlbesked der lyver om hvor meget der mangler er værre end ingen besked.
    """
    sek = abs(int(sekunder))
    if sek < 90:
        return f"{sek} s"
    minutter = sek // 60
    if minutter < 90:
        return f"{minutter} min"
    timer, rest = divmod(minutter, 60)
    return f"{timer} t {rest} min" if rest else f"{timer} t"


def test_vagten_kan_faktisk_fejle(monkeypatch: pytest.MonkeyPatch) -> None:
    """MODPRØVE: vagten skal afvise et byg der er ældre end kilden.

    Uden denne kunne nogen «løse» opgaven ved at gøre sammenligningen
    tandløs, og testen ovenfor ville stadig være grøn.
    """
    if not _INDEX.is_file():
        pytest.skip("dist-web findes ikke — modprøven kræver en fil at måle på")

    # Simulér: kilden er committet et døgn efter bygget.
    import time
    byg_ts = int(_INDEX.stat().st_mtime)
    monkeypatch.setattr(
        f"{__name__}._seneste_kilde_commit_ts", lambda: byg_ts + 86_400
    )
    with pytest.raises(AssertionError, match="ældre end kilden"):
        test_dist_web_er_ikke_aeldre_end_kilden()
    # og tiden skal stadig flyde normalt i resten af suiten
    assert time.time() > byg_ts
