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
