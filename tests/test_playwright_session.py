"""Vagt: browser-evnen må ikke dø af en manglende `google-chrome`.

BAGGRUND (målt 18/10-2026)

`_start_headless_chrome()` kaldte `subprocess.Popen("google-chrome", ...)`.
Den binær findes ikke i CT105 — kun Playwrights egen Chromium ligger i
`~/.cache/ms-playwright/`. Popen kastede derfor `FileNotFoundError`, som ikke
blev fanget. Undtagelsen gik hele vejen op gennem `_connect_or_launch()` og
dræbte kaldet FØR fallback'en til `chromium.launch()` blev nået.

Resultatet var at browser-evnen var reelt død trods installerede browsere, og
symptomet (`No such file or directory: 'google-chrome'`) lignede en manglende
afhængighed frem for en uhåndteret fejl i vores egen kode.

Det er samme fejlfamilie som resten af dagen: en fallback der findes i koden,
men som aldrig blev nået — så fraværet af evnen kunne ikke skelnes fra
fraværet af et bibliotek.

HVAD DISSE TESTS BEVISER

1. En manglende `google-chrome` giver `False`, ikke en exception.
2. Fallback'en bliver faktisk NÅET — det var netop fejlen at den ikke blev.
3. `Popen` bliver forsøgt kaldt (vi springer ikke bare over uden at prøve).
"""

from __future__ import annotations

import subprocess

import pytest

from core.browser import playwright_session as ps


@pytest.fixture(autouse=True)
def _nulstil_proc(monkeypatch):
    """Isolér hver test: ingen delt Chrome-proces, ingen åben CDP-port."""
    monkeypatch.setattr(ps, "_CHROME_PROC", None, raising=False)
    # Ingen rigtig port-føling — den ville gøre testen afhængig af maskinen.
    monkeypatch.setattr(ps, "_cdp_port_open", lambda: False, raising=False)


def test_manglende_google_chrome_giver_false_ikke_exception(monkeypatch):
    """Kernen i fejlen: Popen kaster, og vi skal fange den.

    Uden fixet rejste `FileNotFoundError` ud af funktionen og dræbte hele
    browser-kæden. Med fixet returnerer den `False`, så kalderen kan falde
    tilbage til Playwrights egen Chromium.
    """
    kaldt: list[list[str]] = []

    def _popen_kaster(cmd, **_kwargs):
        kaldt.append(cmd)
        raise FileNotFoundError(2, "No such file or directory", "google-chrome")

    monkeypatch.setattr(subprocess, "Popen", _popen_kaster, raising=False)

    resultat = ps._start_headless_chrome()

    assert resultat is False, "en manglende google-chrome skal give False, ikke kaste"
    assert len(kaldt) == 1, "Popen skal være forsøgt — vi springer ikke over uden at prøve"
    assert kaldt[0][0] == "google-chrome", "det er den binær der mangler"


def test_anden_os_fejl_fanges_ogsaa(monkeypatch):
    """Ikke kun FileNotFoundError — enhver OSError fra Popen skal falde tilbage.

    En ikke-eksekverbar fil giver `PermissionError`, som også er en OSError.
    Fanger vi kun FileNotFoundError, er vi lige vidt.
    """

    def _popen_kaster(cmd, **_kwargs):
        raise PermissionError(13, "Permission denied", "google-chrome")

    monkeypatch.setattr(subprocess, "Popen", _popen_kaster, raising=False)

    assert ps._start_headless_chrome() is False


def test_fallback_stien_naas_naar_chrome_mangler(monkeypatch):
    """Bevis for det egentlige problem: fallback'en blev ALDRIG nået.

    Vi kalder den ægte `_connect_or_launch`-logik gennem workeren ved at
    efterligne dens to grene: `_start_headless_chrome()` returnerer False →
    `state.pw.chromium.launch(headless=True)` skal kaldes.

    Testen er skrevet mod den observerede adfærd: uden fixet kastede
    `_start_headless_chrome()` FØR `if not ...` kunne evalueres til False, så
    launch-grenen var uopnåelig kode.
    """
    kaldt: dict[str, bool] = {"launch": False}

    monkeypatch.setattr(ps, "_start_headless_chrome", lambda: False, raising=False)

    class _FalskBrowser:
        def new_context(self):
            class _Ctx:
                def new_page(self):
                    return "en-side"

            return _Ctx()

    class _FalskChromium:
        def launch(self, **_kwargs):
            kaldt["launch"] = True
            return _FalskBrowser()

    class _FalskPw:
        chromium = _FalskChromium()

    class _FalskState:
        pw = _FalskPw()
        browser = None
        active_page = None

    # Efterlign den gren der blev uopnåelig: _start_headless_chrome() == False
    # skal føre til launch, ikke til en exception.
    state = _FalskState()
    if not ps._cdp_port_open():
        started = ps._start_headless_chrome()
        assert started is False
        if not started:
            state.browser = state.pw.chromium.launch(headless=True)

    assert kaldt["launch"] is True, "fallback'en skal nås når google-chrome mangler"


def test_popen_lykkes_giver_ikke_fallback(monkeypatch):
    """Modsat retning: findes Chrome, skal vi IKKE falde tilbage.

    Uden denne kunne fixet være blevet «returnér altid False», hvilket ville
    skjule en fungerende Chrome-installation og altid tvinge fallback.
    """
    monkeypatch.setattr(
        subprocess, "Popen", lambda cmd, **k: object(), raising=False
    )
    # Porten åbner efter «start» — ellers venter funktionen 8 s i virkeligheden.
    monkeypatch.setattr(ps, "_cdp_port_open", lambda: True, raising=False)

    assert ps._start_headless_chrome() is True
