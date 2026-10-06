"""Sikkerhedsgraensen om en widget — pinnet, fordi den er en GRAENSE.

Det er den foerste gang model-skrevet markup renderes i en af Bjoerns
klienter. Husets hidtidige regel var et klart nej (`MermaidBlock`:
«bibliotekets tilsigtede API, ikke model-HTML»), saa de egenskaber der
erstatter reglen skal kunne fejle en test hvis nogen svaekker dem.

To lag, uafhaengige: CSP'en her, og sandkassen i klienten. Testene her daekker
laget paa serveren — det der deles af begge klienter og derfor ikke kan drive.
"""

from __future__ import annotations

import pytest

from core.services.widget_dokument import (
    CSP,
    MAX_HTML_BYTES,
    WidgetFejl,
    pak,
)


def test_dokumentet_naegter_ALT_netvaerk():
    """`default-src 'none'` er hele grunden til at vi tør rendere model-HTML:
    selv en perfekt sandkasse-omgaaelse kan ikke sende noget ud."""
    d = pak("<p>hej</p>")
    assert "default-src 'none'" in d
    assert "Content-Security-Policy" in d
    # Ingen af disse maa nogensinde aabne en vej ud.
    for forbudt in ("connect-src", "frame-src", "*", "https:", "http:"):
        assert forbudt not in CSP, f"{forbudt!r} i CSP'en aabner netvaerk"


def test_kun_data_til_billeder_og_fonte():
    """En widget skal baere sit eget indhold, ikke hente det."""
    assert "img-src data:" in CSP and "font-src data:" in CSP


def test_formularer_og_base_er_lukket():
    """`form-action 'none'` lukker den aeldste exfiltrations-vej af alle, og
    `base-uri 'none'` hindrer at en injiceret <base> flytter relative stier."""
    assert "form-action 'none'" in CSP and "base-uri 'none'" in CSP


def test_et_HELT_dokument_afvises():
    """Et dokument med sin egen <head> ville baere sin EGEN (manglende) CSP.
    Vi pakker fragmenter, saa politikken altid er vores."""
    for raa in ("<!doctype html><html><body>x</body></html>",
                "<html><head></head><body>x</body></html>",
                "  <!DOCTYPE HTML>\n<p>x</p>"):
        with pytest.raises(WidgetFejl, match="FRAGMENT"):
            pak(raa)


def test_tom_html_afvises():
    for raa in ("", "   ", "\n\t "):
        with pytest.raises(WidgetFejl, match="tom"):
            pak(raa)


def test_stoerrelses_loftet_haandhaeves():
    assert pak("x" * (MAX_HTML_BYTES - 100))        # lige under skal virke
    with pytest.raises(WidgetFejl, match="hoejst"):
        pak("x" * (MAX_HTML_BYTES + 1))


def test_loftet_maales_i_BYTES_ikke_tegn():
    """Et dansk tegn er to bytes i UTF-8. Maaltes loftet i tegn, kunne en
    widget paa 256k tegn blive en fil paa 512 KB."""
    næsten = "æ" * (MAX_HTML_BYTES // 2 + 10)      # over loftet i bytes
    assert len(næsten) < MAX_HTML_BYTES             # men under i TEGN
    with pytest.raises(WidgetFejl, match="hoejst"):
        pak(næsten)


def test_titlen_kan_ikke_bryde_ud_af_sit_element():
    """Titlen er model-skrevet. `<` og `>` fjernes, saa den ikke kan lukke
    <title> og aabne et <script> FOER CSP-metaen er naaet."""
    d = pak("<p>x</p>", titel="</title><script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in d
    assert "<title>" in d and d.count("<title>") == 1


def test_titlen_falder_tilbage_naar_den_bliver_tom():
    d = pak("<p>x</p>", titel="<<>>")
    assert "<title>widget</title>" in d


def test_baggrunden_er_gennemsigtig_saa_den_foelger_klientens_tema():
    """En widget kan ikke kende hans lyse/moerke tema. Gennemsigtig baggrund +
    `color-scheme: light dark` lader klientens flade skinne igennem."""
    d = pak("<p>x</p>")
    assert "background:transparent" in d and "color-scheme: light dark" in d


def test_links_kan_ikke_klikkes():
    """Navigation ud af en widget er ikke en funktion vi har designet. CSP'en
    ville alligevel blokere hentningen, men en doed klik er aerligere end en
    der fejler i tavshed."""
    assert "pointer-events:none" in pak("<a href='x'>y</a>")


def test_fragmentet_staar_uaendret_i_dokumentet():
    """Vi sanitiserer IKKE — sandkassen er graensen. Testen findes for at
    nogen ikke senere tilfoejer en saniteringsliste og tror den er vaernet."""
    frag = "<div class='k'><b>tal</b> &amp; tegn</div>"
    assert frag in pak(frag)
