"""Desperation-awareness publisher gyldigt inner_voice.signal-event (bug fikset 1. jul)."""
import inspect
import core.services.desperation_awareness as da


def test_no_dict_as_kind():
    src = inspect.getsource(da)
    assert 'event_bus.publish({' not in src           # ingen dict-som-første-arg
    assert 'event_bus.publish("inner_voice.signal", payload)' in src
