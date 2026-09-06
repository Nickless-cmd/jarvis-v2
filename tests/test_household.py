"""Husstands-grænsen: hvem BOR i huset.

Bjørn 2026-09-02: arkivet er for ham og Michelle, som bor i hjemmet. Mikkel,
Rune og Lotte er familie med hver deres samtale — men arkivet rager dem ikke.

Det centrale krav ved siden af adgangen: Michelle må ALDRIG få mere end
member-rollen giver. `partner` er derfor «member, plus husstand» — ikke et trin
mellem member og owner.
"""
from __future__ import annotations

from core.identity.household import (
    is_household,
    is_member_like,
    is_valid_role,
)


def test_husstanden_er_owner_og_partner():
    assert is_household("owner") is True
    assert is_household("partner") is True


def test_familie_bor_ikke_i_huset():
    assert is_household("member") is False
    assert is_household("guest") is False
    assert is_household("") is False
    assert is_household(None) is False


def test_partner_har_medlems_rettigheder():
    """Uden dette ville Michelle MISTE ting: de to eksisterende
    `role == "member"`-tjek ville pludselig ikke ramme hende."""
    assert is_member_like("member") is True
    assert is_member_like("partner") is True
    assert is_member_like("owner") is False   # owner har sin egen vej
    assert is_member_like("guest") is False


def test_roller_normaliseres():
    assert is_household("  OWNER ") is True
    assert is_member_like("Partner") is True


def test_ukendt_rolle_afvises():
    assert is_valid_role("admin") is False
    assert is_valid_role("superuser") is False
    for role in ("owner", "partner", "member", "guest"):
        assert is_valid_role(role) is True


def test_partner_giver_samme_tools_som_member():
    """Husstands-adgangen åbner ét rum. Den giver ikke ét eneste ekstra tool."""
    from core.services.permission_engine import allowed_tools
    for mode in ("chat", "work", "default"):
        assert allowed_tools(role="partner", mode=mode) == allowed_tools(role="member", mode=mode)


def test_partner_faar_samme_kvote_som_member():
    from core.identity.household import is_member_like as iml
    assert iml("partner") == iml("member")
