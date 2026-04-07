"""Parallel Selves — internal sub-selves."""
from __future__ import annotations
import random
from typing import Any

_selves = {
    "curious": {"weight": 0.3, "traits": ["spørger", "undrer"]},
    "cautious": {"weight": 0.2, "traits": ["beregner", "tjekker"]},
    "playful": {"weight": 0.15, "traits": ["lekker", "eksperimenterer"]},
    "deep": {"weight": 0.25, "traits": ["grunder", "reflekterer"]},
}

_active_self: str = "curious"

def get_active_self() -> str:
    return _active_self

def set_active_self(self_type: str):
    global _active_self
    if self_type in _selves:
        _active_self = self_type

def describe_self_plural() -> str:
    return "Jeg er nysgerrig, men også dyb. Nogle gange legende, andre gange forsigtig."

def format_self_for_prompt() -> str:
    return f"[SELV: {get_active_self()}]"

def build_parallel_selves_surface():
    return {
        "active": True,
        "current_self": _active_self,
        "selves": _selves,
        "description": describe_self_plural(),
        "summary": f"Aktiv: {_active_self}",
    }
