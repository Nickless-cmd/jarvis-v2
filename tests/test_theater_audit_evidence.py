"""Bevis for theater-auditens ene undertrykkelse (målt 7/11-2026).

`identity_preamble_pressure` matcher SYMBOLET `build_identity_preamble`, ikke om
værdien er målt. Auditen fandt 18 forekomster, men preamblen er fuldt signal-drevet:
navn fra IDENTITY.md, `current_bearing` fra personlighedsvektoren og `energy_level`
fra body_state. Fundene var derfor navne-artefakter, ikke teater.

Undertrykkelsen må ikke være en antagelse. Testene her fejler hvis:
  - preamblen holder op med at læse signaler (så er fundene pludselig ægte), eller
  - undertrykkelsen bliver tavs (så forsvinder den uden spor).
"""

from __future__ import annotations


def test_identity_preamble_er_bygget_af_signaler(monkeypatch) -> None:
    """Preamblen skal ændre sig når signalerne ændrer sig — ellers er den hardcoded."""
    from core.services import identity_composer as ic
    from core.services import tick_cache

    monkeypatch.setattr(tick_cache, "get", lambda key: None)
    monkeypatch.setattr(tick_cache, "set", lambda key, value: None)
    monkeypatch.setattr(ic, "get_entity_name", lambda: "TestEnhed")
    monkeypatch.setattr(ic, "_read_bearing", lambda: "rolig-men-vågen")
    monkeypatch.setattr(ic, "_read_energy", lambda: "moderat")

    preamble = ic.build_identity_preamble()

    assert "TestEnhed" in preamble, f"navnet kom ikke fra signalet: {preamble!r}"
    assert "rolig-men-vågen" in preamble, f"bearing kom ikke fra signalet: {preamble!r}"
    assert "moderat" in preamble, f"energien kom ikke fra signalet: {preamble!r}"


def test_identity_preamble_er_tom_uden_signaler(monkeypatch) -> None:
    """Uden signaler må preamblen ikke opfinde en tilstand."""
    from core.services import identity_composer as ic
    from core.services import tick_cache

    monkeypatch.setattr(tick_cache, "get", lambda key: None)
    monkeypatch.setattr(tick_cache, "set", lambda key, value: None)
    monkeypatch.setattr(ic, "get_entity_name", lambda: "TestEnhed")
    monkeypatch.setattr(ic, "_read_bearing", lambda: "")
    monkeypatch.setattr(ic, "_read_energy", lambda: "")

    assert ic.build_identity_preamble() == "TestEnhed."


def test_auditen_rapporterer_hvad_den_undertrykker() -> None:
    """Undertrykkelsen skal være synlig i fladen, ikke tavs."""
    from core.services.theater_audit import build_theater_audit_surface

    summary = build_theater_audit_surface()["summary"]

    assert "suppressed_verified" in summary
    assert summary["suppressed_verified"] > 0
    assert summary["suppressed_by_kind"].get("identity_preamble_pressure", 0) > 0


def test_undertrykt_moenster_staar_stadig_i_patterns() -> None:
    """Mønstret må ikke slettes — så ville historikken og begrundelsen forsvinde."""
    from core.services.theater_audit import _PATTERNS

    verified = [p for p in _PATTERNS if p.get("verified_signal_driven")]
    assert verified, "en verificeret undertrykkelse skal stå i _PATTERNS med sin begrundelse"
    assert verified[0]["id"] == "identity_preamble_pressure"
