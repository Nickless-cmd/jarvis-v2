"""To akser: evne og timing er UAFHÆNGIGE.

Hele pointen med modulet er kombinationer der ikke kunne udtrykkes før —
«læs-kun med netværk», «må skrive, spørg ikke». Så det er kombinationerne
der testes, ikke de to akser hver for sig.
"""
import pytest

from core.services.permission_axes import (
    APPROVAL_MODES,
    SandboxProfile,
    format_axes,
    resolve_effective,
    sandbox_kwargs,
)


def test_plan_er_et_haardt_gulv_uanset_profil():
    """En tilstand der hedder 'plan' og alligevel kan skrive er værre end ingen."""
    for p in SandboxProfile:
        d = resolve_effective(p, "plan")
        assert d["allow_write"] is False, p
        assert d["allow_egress"] is False, p


def test_read_only_kan_ikke_skrive_selv_i_full_auto():
    d = resolve_effective(SandboxProfile.READ_ONLY, "full-auto")
    assert d["allow_write"] is False
    assert d["must_prompt"] is False


def test_restricted_maa_skrive_men_ikke_naa_nettet():
    """Kombinationen der ikke kunne udtrykkes før akserne blev skilt ad."""
    d = resolve_effective(SandboxProfile.RESTRICTED, "auto-edit")
    assert d["allow_write"] is True
    assert d["allow_egress"] is False
    assert d["confine_paths"] is True


def test_der_spoerges_ikke_om_noget_der_alligevel_ikke_maa():
    """En prompt for et kald der ikke kan skrive laerer ham at klikke ja."""
    assert resolve_effective(SandboxProfile.READ_ONLY, "ask")["must_prompt"] is False
    assert resolve_effective(SandboxProfile.WORKSPACE_WRITE, "ask")["must_prompt"] is True


def test_full_auto_og_bypass_spoerger_ikke():
    for m in ("full-auto", "bypass"):
        assert resolve_effective(SandboxProfile.WORKSPACE_WRITE, m)["must_prompt"] is False


def test_ukendt_profil_og_tilstand_falder_til_noget_sikkert():
    d = resolve_effective("volapyk", "volapyk")
    assert d["profil"] == "workspace-write"
    assert d["tilstand"] == "ask"
    assert d["must_prompt"] is True, "ukendt input skal spørge, ikke bare køre"


def test_alle_tilstande_giver_en_beslutning():
    for m in APPROVAL_MODES:
        for p in SandboxProfile:
            d = resolve_effective(p, m)
            assert set(d) >= {"allow_write", "allow_egress", "confine_paths", "must_prompt"}


def test_begge_akser_er_synlige_i_formateringen():
    assert format_axes(SandboxProfile.RESTRICTED, "ask") == "restricted · ask"


def test_akserne_oversaettes_til_sandboxen():
    assert sandbox_kwargs(SandboxProfile.READ_ONLY, "full-auto")["allow_egress"] is False
    assert sandbox_kwargs(SandboxProfile.WORKSPACE_WRITE, "ask")["allow_egress"] is True
