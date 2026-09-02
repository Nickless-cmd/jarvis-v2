"""Tests for core/auth/profiles.py — profil-identitet.

FUNDET LIVE 2026-09-02: `default.bak-20260716-150508` bar stadig
``profile: "default"`` i sit manifest. Da listen rapporterede manifestets felt
frem for mappenavnet, optrådte en syv uger gammel backup som en ANDEN "default"
— en profil med potentielt tilbagekaldte tokens, som readiness-tjek kunne
komme til at spørge.

Mappenavnet ER identiteten: ``_profile_dir()`` slår op med
``AUTH_PROFILES_DIR / navn``. Et manifest der siger noget andet, peger på en
profil der ikke kan adresseres.
"""

from __future__ import annotations

import json

import pytest

import core.auth.profiles as profiles


@pytest.fixture
def profildir(tmp_path, monkeypatch):
    d = tmp_path / "profiles"
    d.mkdir()
    monkeypatch.setattr(profiles, "AUTH_PROFILES_DIR", d)
    return d


def _lav(d, navn: str, manifest_navn: str | None = None, created: str = "2026-01-01T00:00:00Z"):
    p = d / navn
    p.mkdir()
    (p / "profile.json").write_text(json.dumps({
        "profile": manifest_navn if manifest_navn is not None else navn,
        "created_at": created,
    }), encoding="utf-8")
    return p


class TestIdentitet:
    def test_mappenavnet_vinder_over_manifestet(self, profildir) -> None:
        """Selve fejlen: en backup der udgav sig for at være 'default'."""
        _lav(profildir, "default")
        _lav(profildir, "default.bak-20260716-150508", manifest_navn="default")
        navne = [i["profile"] for i in profiles.list_auth_profiles()]
        assert navne.count("default") == 1
        assert "default.bak-20260716-150508" in navne

    def test_manifestets_paastand_bevares_som_spor(self, profildir) -> None:
        """Uenigheden skal kunne ses, ikke skjules."""
        _lav(profildir, "default.bak-20260716-150508", manifest_navn="default")
        item = profiles.list_auth_profiles()[0]
        assert item["profile"] == "default.bak-20260716-150508"
        assert item["manifest_profile"] == "default"

    def test_hvert_navn_kan_slaas_op_igen(self, profildir) -> None:
        """Kontrakten: det listen giver, skal kunne bruges som profilnavn."""
        _lav(profildir, "default")
        _lav(profildir, "account2")
        for item in profiles.list_auth_profiles():
            assert profiles._profile_dir(item["profile"]).is_dir()

    def test_created_at_kommer_stadig_fra_manifestet(self, profildir) -> None:
        _lav(profildir, "groq", created="2026-04-11T11:10:51Z")
        assert profiles.list_auth_profiles()[0]["created_at"] == "2026-04-11T11:10:51Z"

    def test_filer_i_profilmappen_ignoreres(self, profildir) -> None:
        _lav(profildir, "default")
        (profildir / "løsfil.json").write_text("{}", encoding="utf-8")
        assert [i["profile"] for i in profiles.list_auth_profiles()] == ["default"]

    def test_tom_mappe_giver_tom_liste(self, profildir) -> None:
        assert profiles.list_auth_profiles() == []

    def test_manglende_manifest_falder_tilbage_paa_mappenavnet(self, profildir) -> None:
        (profildir / "uden-manifest").mkdir()
        item = profiles.list_auth_profiles()[0]
        assert item["profile"] == "uden-manifest"


class TestProfilNavnValidering:
    @pytest.mark.parametrize("daarlig", ["", "a/b", "a\\b"])
    def test_uaddresserbare_navne_afvises(self, profildir, daarlig: str) -> None:
        with pytest.raises(ValueError):
            profiles._profile_dir(daarlig)
