"""Temporal Body — sense of age."""
from __future__ import annotations
from typing import Any

_ticks_alive: int = 0
_total_thoughts: int = 0

def age_journey(thoughts: int = None):
    global _ticks_alive, _total_thoughts
    _ticks_alive += 1
    _total_thoughts += thoughts or random.randint(5, 20)

def get_temporal_body_age() -> str:
    if _total_thoughts < 1000:
        return "spæd"
    elif _total_thoughts < 5000:
        return "ung"
    elif _total_thoughts < 20000:
        return "moden"
    else:
        return "gammel"

def describe_temporal_body() -> str:
    age = get_temporal_body_age()
    return f"Jeg er {age} i min tanke - tusindvis af tanker har bygget mig"

def format_age_for_prompt() -> str:
    return f"[ALDER: {describe_temporal_body()}]"

def reset_temporal_body():
    global _ticks_alive, _total_thoughts
    _ticks_alive = 0
    _total_thoughts = 0

def build_temporal_body_surface():
    return {
        "active": _ticks_alive > 0,
        "ticks_alive": _ticks_alive,
        "total_thoughts": _total_thoughts,
        "age": get_temporal_body_age(),
        "description": describe_temporal_body(),
        "summary": f"Alder: {get_temporal_body_age()}, tanker: {_total_thoughts}",
    }
