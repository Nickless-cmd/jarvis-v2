"""Skallen må ikke caches — ellers peger den på et bundt der ikke findes mere.

## Målt 15/9-2026

Bjørn loggede ind, der skete intet, og «da jeg manuelt opdaterede siden kom jeg
ind». Tokenet var gemt hele tiden; det var siden der var gammel.

Vite giver hvert bundt et indholds-hash i navnet, så navnet **skifter ved hver
bygning**. `index.html` peger på det aktuelle navn. StaticFiles satte kun etag
og last-modified — ingen `Cache-Control`. Uden den cacher browsere heuristisk
(typisk 10% af filens alder), og filen på serveren havde ligget urørt siden
6. juli, så vinduet var dage.

Aktiverne må til gengæld gerne caches for evigt: deres navn ændrer sig når
indholdet gør, så en cache kan ikke blive forkert.
"""
from __future__ import annotations

import inspect

from apps.api.jarvis_api import app as app_modul


def _ui_filer_kilde() -> str:
    """Klassen er defineret inde i create_app, så den hentes fra kilden."""
    return inspect.getsource(app_modul)


def test_skallen_faar_no_cache():
    k = _ui_filer_kilde()
    assert '"no-cache"' in k, "index.html kan stadig caches heuristisk"


def test_aktiverne_maa_caches_laenge():
    """De er indholds-hashede. Ville vi også no-cache dem, hentede hver
    sidevisning 1,6 MB JS igen."""
    k = _ui_filer_kilde()
    assert "immutable" in k
    assert "max-age=31536000" in k


def test_reglen_skelner_paa_assets_praefikset():
    k = _ui_filer_kilde()
    assert 'path.startswith("assets/")' in k, "alt faar samme regel"


def test_klassen_er_faktisk_MONTERET():
    """Husets gennemgående lektie: en mekanisme ingen kalder er død kode.
    Sætter man reglen op og monterer StaticFiles alligevel, sker der intet."""
    k = _ui_filer_kilde()
    assert "_UiFiler(directory=_ui_dist" in k, "den gamle StaticFiles er stadig monteret"
    assert 'app.mount("/", StaticFiles(directory=_ui_dist' not in k
