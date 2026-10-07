"""ntfy-porten — og Notification-hooken der kan stoppe en besked.

En notifikation kan ikke kaldes tilbage når den først er ude af huset. Derfor
fyrer hooken FØR afsendelsen: det er det eneste sted «block» betyder noget.
"""
from __future__ import annotations

import json

import pytest

from core.services import ntfy_gateway as ng


@pytest.fixture(autouse=True)
def _ingen_rigtig_afsendelse(monkeypatch):
    """Ingen test må sende en rigtig push-besked."""
    monkeypatch.setattr(ng, "_load_config", lambda: None, raising=False)


def _forbi_vagten(monkeypatch):
    """Pytest-vagten (69fd08f10) returnerer «skipped» FOER hooken og konfigurationen
    — saa disse tests naaede aldrig det de tester. Afsendelse er allerede umulig
    (fixturen fjerner konfigurationen), saa markoeren kan fjernes for den ene test.

    Kaldes INDE i testen: pytest saetter markoeren igen naar kald-fasen starter,
    saa en fixture kan ikke fjerne den. Vagten selv er daekket af
    test_ingen_ntfy_fra_tests.py.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


def _hooks(tmp_path, monkeypatch, konfiguration):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "hooks.json").write_text(json.dumps(konfiguration))


class TestNotificationHook:
    def test_block_stopper_beskeden(self, tmp_path, monkeypatch):
        _hooks(tmp_path, monkeypatch, {"hooks": {"Notification": [
            {"type": "command", "command": "echo for sent; exit 2"}]}})
        _forbi_vagten(monkeypatch)
        r = ng.send_notification("noget vigtigt")
        assert r["status"] == "blocked" and "for sent" in r["reason"]

    def test_uden_hooks_gaar_den_sin_normale_vej(self, tmp_path, monkeypatch):
        """Uden config skal porten opføre sig præcis som før."""
        _hooks(tmp_path, monkeypatch, {"hooks": {}})
        _forbi_vagten(monkeypatch)
        r = ng.send_notification("hej")
        assert r["status"] == "error" and r["reason"] == "ntfy-not-configured"

    def test_inject_haefter_kontekst_paa(self, tmp_path, monkeypatch):
        fanget = {}
        _hooks(tmp_path, monkeypatch, {"hooks": {"Notification": [
            {"type": "command", "command": "echo 'PS: batteriet er lavt'"}]}})

        def _fake_cfg():
            fanget["kaldt"] = True
            return None

        monkeypatch.setattr(ng, "_load_config", _fake_cfg, raising=False)
        _forbi_vagten(monkeypatch)
        ng.send_notification("hej")
        # Hooken må ikke have forhindret den normale vej.
        assert fanget.get("kaldt") is True

    def test_en_kastende_hook_stopper_ikke_beskeden(self, tmp_path, monkeypatch):
        """Et værn omkring notifikationer må aldrig gøre systemet stumt."""
        _hooks(tmp_path, monkeypatch, {"hooks": {"Notification": [
            {"type": "command", "command": "sleep 99", "timeout_s": 0.1}]}})
        _forbi_vagten(monkeypatch)
        r = ng.send_notification("hej")
        assert r["status"] == "error"  # nåede den normale vej


class TestPortenSelv:
    def test_uden_konfiguration_fejler_den_pænt(self, monkeypatch):
        _forbi_vagten(monkeypatch)
        r = ng.send_notification("hej")
        assert r["status"] == "error" and "ntfy-not-configured" in r["reason"]


class TestHeaderSafe:
    """HTTP-headere sendes som latin-1 af urllib.

    Maalt 4/10-2026: 26 push fejlede paa én dag, alle med
    «'latin-1' codec can't encode character '\\u2014'». Titlen blev bygget som
    ``f"Jarvis — {label}"`` (ambient_presence.py:64) — em-dash'en kan ikke
    kodes, og urllib kaster FOER requesten forlader maskinen.

    Kalderne er brand-and-forget, saa notifikationen forsvandt LYDLOST: ingen
    fejl naaede Bjoern, han fik bare ingen besked. Disse tests holder porten
    aerlig — en titel maa aldrig kunne tabe en besked.
    """

    def test_em_dash_translittereres(self):
        r = ng._header_safe("Jarvis — vågner op")
        assert r == "Jarvis - vågner op"
        r.encode("latin-1")  # maa ikke kaste

    def test_en_dash_og_typografiske_tegn(self):
        assert ng._header_safe("a – b") == "a - b"
        assert ng._header_safe("x…") == "x..."

    def test_ren_tekst_roeres_ikke(self):
        assert ng._header_safe("Jarvis genstartet") == "Jarvis genstartet"

    def test_dansk_aeoeaa_overlever(self):
        """Æ/Ø/Å ER i latin-1 — de skal staa uroert, ikke erstattes."""
        assert ng._header_safe("Blå ørn") == "Blå ørn"

    def test_tom_streng(self):
        assert ng._header_safe("") == ""

    def test_ukodbart_erstattes_frem_for_at_kaste(self):
        """Edge: et tegn der hverken er typografisk eller latin-1 (fx emoji).
        Beskeden skal naa frem — ikke kastes væk."""
        r = ng._header_safe("Jarvis klar")
        r.encode("latin-1")  # maa ikke kaste
        assert ng._header_safe("x\u2603y") == "x?y"  # snefnug → erstattet

    def test_titlen_sendes_saniteret_hele_vejen(self, monkeypatch):
        """Integration: en em-dash-titel maa ikke kunne vaelte afsendelsen."""
        fanget = {}
        monkeypatch.setattr(
            ng, "_load_config",
            lambda: {"server": "https://ntfy.sh", "topic": "t"},
            raising=False,
        )

        class _Resp:
            def read(self):
                return b"ok"

            # Kilden bruger `with urllib.request.urlopen(...)` — stub'en skal
            # baere context-manager-protokollen, ellers fejler testen paa
            # dobbelten og ikke paa koden.
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def _fake_urlopen(req, timeout=10):
            fanget["headers"] = dict(req.headers)
            return _Resp()

        monkeypatch.setattr(ng.urllib.request, "urlopen", _fake_urlopen, raising=False)
        _forbi_vagten(monkeypatch)

        r = ng.send_notification("hej", title="Jarvis — test")
        assert r["status"] == "sent"
        titel = next(v for k, v in fanget["headers"].items() if k.lower() == "title")
        titel.encode("latin-1")  # det er her det gamle kode kastede
        assert titel == "Jarvis - test"

