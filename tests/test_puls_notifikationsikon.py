"""Notifikationsikonet i statuslinjen skal være Puls — ikke en taleboble.

Målt 7/10-2026: `ic_notification.xml` indeholdt en generisk, fuldt udfyldt
taleboble. Android bruger kun alpha-kanalen i `smallIcon` og farver resten
hvidt, så den blev læst som «ny besked» i den sammenfoldede statuslinje —
mens app-ikonet i den udfoldede liste var korrekt (Bjørn, med to skærmbilleder).

Filen var lagt ind i hånden 26/9-2026 som passager på en Android
13-tilladelsesrettelse og var aldrig født af `assets/brand/puls.svg` som alle
andre ikoner. Testene her holder den på kilden.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts.generate_puls_icons import SOURCE, notifikations_vektor

ROOT = Path(__file__).resolve().parents[1]
IKON = ROOT / 'apps/mobile/android/app/src/main/res/drawable/ic_notification.xml'
ANDROID = '{http://schemas.android.com/apk/res/android}'


def _kilde_bjaelker() -> list[tuple[float, float, float, float]]:
    """De tre bjælker fra brand-mærket, som (x, y, bredde, højde)."""
    root = ET.parse(SOURCE).getroot()
    return [
        (float(r.attrib['x']), float(r.attrib['y']),
         float(r.attrib['width']), float(r.attrib['height']))
        for r in root.findall('{http://www.w3.org/2000/svg}rect')
    ]


def test_ikonet_er_skrevet_af_generatoren():
    """Filen på disken skal være byte-identisk med generatorens udskrift.

    Er den ikke det, er den rettet i hånden igen — og så driver den fra
    brand-mærket, præcis som da fejlen opstod.
    """
    assert IKON.exists(), f'{IKON} mangler — Android har intet smallIcon'
    assert IKON.read_text() == notifikations_vektor(), (
        'ic_notification.xml er ikke generatorens udskrift. '
        'Kør `python scripts/generate_puls_icons.py` i stedet for at rette filen i hånden.'
    )


def test_ikonet_har_praecis_tre_bjaelker():
    """Puls er tre bjælker. En taleboble er én form — det var fejlen."""
    root = ET.fromstring(IKON.read_text())
    paths = root.findall('path')
    assert len(paths) == 3, (
        f'forventede 3 bjælker (Puls), fandt {len(paths)} form(er) — '
        'en enkelt form er sandsynligvis en taleboble igen'
    )


def test_bjaelkerne_matcher_brandmaerket():
    """Hver bjælkes position og størrelse skal komme fra `assets/brand/puls.svg`."""
    root = ET.fromstring(IKON.read_text())
    forventet = _kilde_bjaelker()
    assert len(forventet) == 3, 'brand-mærket selv er ændret — testen kan ikke måle'

    for path, (x, y, w, h) in zip(root.findall('path'), forventet):
        data = path.attrib[f'{ANDROID}pathData']
        tal = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', data)]
        # Mønsteret er M{x},{y} h{w} v{h} h-{w} z
        assert tal[:4] == pytest.approx([x, y, w, h]), (
            f'bjælken {data!r} matcher ikke brand-mærkets ({x}, {y}, {w}, {h})'
        )


def test_ikonet_er_monokromt_og_uden_baggrund():
    """Android farver selv. En baggrund ville blive en hvid klods."""
    root = ET.fromstring(IKON.read_text())
    assert root.tag.endswith('vector'), 'skal være et Android vector-drawable'
    assert root.findall('path'), 'ingen former at tegne'
    # Ingen fyldt baggrund: alle paths skal være de tre bjælker, ikke et rektangel
    # der dækker hele fladen.
    for path in root.findall('path'):
        data = path.attrib[f'{ANDROID}pathData']
        tal = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', data)]
        bredde = max(tal[0::2]) - min(tal[0::2]) if tal else 0
        assert bredde < 100, (
            f'en form dækker hele bredden ({bredde}) — det er en baggrund, ikke en bjælke'
        )


def test_viewbox_er_100():
    """Bjælkerne er angivet i brand-mærkets 0-100-koordinater."""
    root = ET.fromstring(IKON.read_text())
    assert root.attrib[f'{ANDROID}viewportWidth'] == '100'
    assert root.attrib[f'{ANDROID}viewportHeight'] == '100'
