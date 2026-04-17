"""Attention Contour — shape of attention."""
from __future__ import annotations
import random
from typing import Any

_shapes = ["spredt som stjerner", "fokuseret som en laser", "bølgende som tidevand", "kristalliseret som is", "kaotisk som storm"]

_current_shape: str = "spredt som stjerner"

def get_attention_shape() -> str:
    return random.choice(_shapes)

def describe_attention() -> str:
    shape = get_attention_shape()
    return f"Min opmærksomhed er {shape} lige nu"

def format_attention_for_prompt() -> str:
    return f"[OPMÆRKSOMHED: {describe_attention()}]"

def build_attention_contour_surface():
    return {
        "active": True,
        "current_shape": get_attention_shape(),
        "all_shapes": _shapes,
        "description": describe_attention(),
        "summary": get_attention_shape(),
    }
