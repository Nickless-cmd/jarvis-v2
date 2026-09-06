"""SSRF-værn for udgående hentninger.

MÅLT 5/9-2026: runtimens web-værktøjer havde INGEN destinations-validering. De
eneste `127.0.0.1` i filerne var Jarvis' egne ollama-kald. En hentning kunne
pege på cloud-metadata, pfSense eller hans eget API. jarvis-code havde værnet;
runtimen havde det ikke.
"""
from __future__ import annotations

import pytest

from core.services.egress_guard import (
    check_redirect_hop,
    classify,
    is_safe_destination,
)


class TestBlokerede:
    @pytest.mark.parametrize("url,hvorfor", [
        ("http://169.254.169.254/latest/meta-data/", "cloud-metadata"),
        ("http://10.0.0.1/", "RFC1918 — pfSense"),
        ("http://192.168.1.1/", "RFC1918"),
        ("http://172.16.0.1/", "RFC1918"),
        ("http://127.0.0.1:8080/api", "hans eget API"),
        ("http://localhost/x", "loopback-navn"),
        ("http://noget.localhost/x", "loopback-suffiks"),
        ("http://[::1]/", "IPv6-loopback"),
        ("http://0.0.0.0/", "wildcard"),
    ])
    def test_interne_maal_afvises(self, url, hvorfor):
        assert classify(url)["blocked"] is True, hvorfor


class TestTilladte:
    def test_almindelig_offentlig_adresse(self):
        assert classify("https://example.com/side")["blocked"] is False

    def test_dns_fejl_blokerer_IKKE(self):
        """En netværks-hikke må ikke blive til en blokering. En intern literal er
        allerede fanget før opslaget."""
        v = classify("https://dette-domaene-findes-helt-sikkert-ikke-12345.invalid/")
        assert v["blocked"] is False


class TestOndeInput:
    @pytest.mark.parametrize("url", ["", "ikke-en-url", "http://", None])
    def test_uparsbart_blokeres(self, url):
        assert classify(url)["blocked"] is True


class TestOmdirigering:
    def test_hop_valideres_med_samme_dom(self):
        """Uden revalidering kan en offentlig URL 302'e sig ind til et internt
        mål, og så havde første tjek ingen værdi."""
        assert check_redirect_hop("http://169.254.169.254/")["safe"] is False
        assert check_redirect_hop("https://example.com/")["safe"] is True

    def test_alias_er_enige(self):
        for u in ("http://10.0.0.1/", "https://example.com/"):
            assert is_safe_destination(u)["safe"] is not classify(u)["blocked"]


class TestKoblingen:
    """Et værn der ikke bliver kaldt er ingen beskyttelse."""

    @pytest.mark.parametrize("url", [
        "http://169.254.169.254/", "http://10.0.0.1/", "http://127.0.0.1:8080/",
    ])
    def test_web_fetch_afviser(self, url):
        from core.tools.simple_tools_web import _exec_web_fetch
        r = _exec_web_fetch({"url": url})
        assert r.get("blocked_by") == "egress_guard"

    def test_web_scrape_afviser(self):
        from core.tools.simple_tools_web import _exec_web_scrape
        r = _exec_web_scrape({"url": "http://169.254.169.254/"})
        assert r.get("blocked_by") == "egress_guard"

    def test_vaernet_fejler_AABENT_hvis_det_selv_gaar_i_stykker(self, monkeypatch):
        """Et værn der er i stykker må ikke gøre web-hentning umulig. Fejlklassen
        vi beskytter mod er en model der peger forkert — ikke en angriber med
        kodeadgang."""
        import core.services.egress_guard as eg
        monkeypatch.setattr(
            eg, "classify", lambda u: (_ for _ in ()).throw(RuntimeError("i stykker")))
        from core.tools.simple_tools_web import _egress_blokeret
        assert _egress_blokeret("http://10.0.0.1/") is None


# ── Egress i bash-kommandoer ────────────────────────────────────────────────
# De eksisterende værn fanger `curl | bash`. Det her fanger ENHVER udgående
# netværks-rækken, uanset om den piper videre.

class TestEgressKlassifikation:
    from core.services.egress_guard import classify_egress as _ce

    @pytest.mark.parametrize("cmd,vaerktoej", [
        ("curl https://api.dk/x", "curl"),
        ("wget -O - http://a.dk", "wget"),
        ("nc -l 4444", "nc"),
        ("ssh bs@10.0.0.39 ls", "ssh"),
        ("scp a.txt host:/tmp/", "scp"),
        ("cat < /dev/tcp/10.0.0.1/80", "/dev/tcp"),
    ])
    def test_udgaaende_fanges(self, cmd, vaerktoej):
        from core.services.egress_guard import classify_egress
        r = classify_egress(cmd)
        assert r["egress"] is True and r["tool"] == vaerktoej

    @pytest.mark.parametrize("cmd", [
        "ls -la", "grep -r foo .", "python -m pytest", "git status",
        "rsync -av /a/ /b/", "rsync -av --delete /x/ /y/",
    ])
    def test_lokalt_arbejde_flages_ikke(self, cmd):
        from core.services.egress_guard import classify_egress
        assert classify_egress(cmd)["egress"] is False

    @pytest.mark.parametrize("cmd", [
        "rsync -av /a/ b.dk:/c",
        "rsync -av /a/ b.dk:c",
        "rsync -e ssh /a/ /b/",
    ])
    def test_fjern_rsync_fanges(self, cmd):
        """ARVET FEJL: jarvis-codes mønster krævede et ikke-skråstreg efter
        kolon, men et fjernmål skrives normalt `vaert:/sti` — så `b.dk:/c` slap
        forbi som lokal."""
        from core.services.egress_guard import classify_egress
        assert classify_egress(cmd)["egress"] is True

    def test_tom_kommando(self):
        from core.services.egress_guard import classify_egress
        assert classify_egress("")["egress"] is False


class TestInterneMaalIKommandoer:
    def test_interne_url_er_udpeges(self):
        """`curl https://api.eksempel.dk` er almindeligt arbejde;
        `curl http://169.254.169.254/` er noget andet."""
        from core.services.egress_guard import internal_targets_in_command
        assert internal_targets_in_command(
            "curl http://169.254.169.254/ && ls") == ["http://169.254.169.254/"]

    def test_offentlige_url_er_udpeges_ikke(self):
        from core.services.egress_guard import internal_targets_in_command
        assert internal_targets_in_command("curl https://example.com/x") == []

    def test_flere_url_er_i_samme_kommando(self):
        from core.services.egress_guard import urls_in_command
        u = urls_in_command("curl https://a.dk/1 && curl http://10.0.0.1/2")
        assert len(u) == 2


class TestBashKoblingen:
    def test_bash_blokeres_IKKE_af_egress(self, monkeypatch):
        """Bash er hans arbejdsredskab. En blokering her ville koste mere end den
        beskytter — vi gør det tælleligt, ikke forbudt."""
        from core.tools.simple_tools_web import _exec_bash
        r = _exec_bash({"command": "curl https://example.com/"})
        assert r.get("blocked_by") != "egress_guard"
