"""Reboot-awareness publisher gyldige events (dict-som-kind-bug fikset 1. jul)."""
import core.services.reboot_awareness_daemon as rad


def test_publish_uses_positional_str_kind(monkeypatch):
    captured = []
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish",
                        lambda kind, payload=None, **k: captured.append((kind, payload)))
    # kald signal-handleren (skriver marker + publisher) via den interne emit på :186-stien
    # her: bekræft at modulet importerer og at publish-formen er (str, dict) i kildekoden
    import inspect
    src = inspect.getsource(rad)
    assert 'event_bus.publish({' not in src  # ingen dict-som-første-arg tilbage
    assert 'event_bus.publish("reboot.imminent"' in src or 'event_bus.publish(result["kind"]' in src


# ── `active` maa ikke vaere et modul-flag pr. proces (25/9-2026) ─────────
#
# Systemet stod «active: false» i mind-rapporten med summary «Genstartet
# uventet efter 42890s nede (oppe 5h14m)». Data'en var aegte — flaget var det
# ikke. `active` returnerede `_DETECTION_RUN`, som saettes naar detektionen
# koerer i DEN proces. `jarvis-api` serverer flader, `jarvis-runtime` tikker,
# saa overfladen blev bygget i en proces der aldrig havde koert detektionen.
#
# Samme fejlklasse som `_PENDING_APPROVALS` samme morgen.
from datetime import UTC, datetime, timedelta  # noqa: E402

import core.services.reboot_awareness_daemon as R  # noqa: E402


def _marker(monkeypatch, tmp_path, **felter):
    import json
    sti = tmp_path / "reboot_markers.json"
    sti.write_text(json.dumps(felter), encoding="utf-8")
    monkeypatch.setattr(R, "_storage_path", lambda: sti)


def _nu(minutter_siden: float = 0.0) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutter_siden)).isoformat()


def test_active_afhaenger_IKKE_af_om_denne_proces_kortede_detektionen(
        monkeypatch, tmp_path):
    """KERNEN. Flaget er falsk her — overfladen skal stadig sige aktiv."""
    monkeypatch.setattr(R, "_DETECTION_RUN", False)
    _marker(monkeypatch, tmp_path,
            last_boot_event={"kind": "reboot.unexpected", "downtime_seconds": 42890},
            last_seen_at=_nu(1), last_boot_at=_nu(300))
    assert R.build_reboot_awareness_surface()["active"] is True, (
        "overfladen rapporterer stadig et modul-flag fra sin egen proces")


def test_uden_et_bod_event_er_den_ikke_aktiv(monkeypatch, tmp_path):
    """Ingen data, ingen lampe — og det er den aerlige udgave af «false»."""
    monkeypatch.setattr(R, "_DETECTION_RUN", True)
    _marker(monkeypatch, tmp_path, last_seen_at=_nu(1))
    assert R.build_reboot_awareness_surface()["active"] is False


def test_et_doedt_hjerteslag_slukker_lampen(monkeypatch, tmp_path):
    """Har ingen tikket i en halv time, er systemet ikke levende.

    Ellers ville lampen lyse for evigt efter den foerste genstart, og saa
    maalte den ingenting."""
    monkeypatch.setattr(R, "_DETECTION_RUN", True)
    _marker(monkeypatch, tmp_path,
            last_boot_event={"kind": "reboot.completed"},
            last_seen_at=_nu(45), last_boot_at=_nu(300))
    assert R.build_reboot_awareness_surface()["active"] is False


def test_et_ulaeseligt_tidsstempel_regnes_som_doedt(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "_DETECTION_RUN", True)
    _marker(monkeypatch, tmp_path,
            last_boot_event={"kind": "reboot.completed"},
            last_seen_at="i gaar ved middagstid")
    assert R.build_reboot_awareness_surface()["active"] is False


def test_summary_og_uptime_er_uroerte(monkeypatch, tmp_path):
    """Kun flaget aendres — indholdet var rigtigt hele tiden."""
    monkeypatch.setattr(R, "_DETECTION_RUN", False)
    _marker(monkeypatch, tmp_path,
            last_boot_event={"kind": "reboot.unexpected", "downtime_seconds": 42890},
            last_seen_at=_nu(1), last_boot_at=_nu(60))
    ud = R.build_reboot_awareness_surface()
    assert ud["summary"], "summary forsvandt"
    assert ud["uptime_seconds"] is not None and ud["uptime_seconds"] > 3000
