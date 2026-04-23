"""Precise math and unit conversion tools using sympy."""
from __future__ import annotations

from typing import Any

# Unit conversion table: (from, to) -> factor
_UNIT_FACTORS: dict[tuple[str, str], float] = {
    # Length
    ("km", "m"): 1000, ("m", "km"): 0.001,
    ("m", "cm"): 100, ("cm", "m"): 0.01,
    ("m", "mm"): 1000, ("mm", "m"): 0.001,
    ("km", "miles"): 0.621371, ("miles", "km"): 1.60934,
    ("m", "feet"): 3.28084, ("feet", "m"): 0.3048,
    ("m", "inches"): 39.3701, ("inches", "m"): 0.0254,
    # Weight
    ("kg", "g"): 1000, ("g", "kg"): 0.001,
    ("kg", "lbs"): 2.20462, ("lbs", "kg"): 0.453592,
    ("kg", "oz"): 35.274, ("oz", "kg"): 0.0283495,
    # Temperature handled separately
    # Volume
    ("l", "ml"): 1000, ("ml", "l"): 0.001,
    ("l", "gallons"): 0.264172, ("gallons", "l"): 3.78541,
    # Time
    ("hours", "minutes"): 60, ("minutes", "hours"): 1/60,
    ("hours", "seconds"): 3600, ("seconds", "hours"): 1/3600,
    ("days", "hours"): 24, ("hours", "days"): 1/24,
    # Speed
    ("km/h", "m/s"): 1/3.6, ("m/s", "km/h"): 3.6,
    ("km/h", "mph"): 0.621371, ("mph", "km/h"): 1.60934,
    # Data
    ("gb", "mb"): 1024, ("mb", "gb"): 1/1024,
    ("tb", "gb"): 1024, ("gb", "tb"): 1/1024,
    ("mb", "kb"): 1024, ("kb", "mb"): 1/1024,
}


def _exec_calculate(args: dict[str, Any]) -> dict[str, Any]:
    expression = str(args.get("expression") or "").strip()
    if not expression:
        return {"status": "error", "error": "expression is required"}
    try:
        import sympy
        result = sympy.sympify(expression)
        evaluated = float(result.evalf()) if result.is_number else str(result)
        return {"status": "ok", "expression": expression, "result": evaluated, "exact": str(result)}
    except Exception as e:
        return {"status": "error", "error": f"Could not evaluate expression: {e}"}


def _exec_unit_convert(args: dict[str, Any]) -> dict[str, Any]:
    try:
        value = float(args.get("value") or 0)
    except (TypeError, ValueError):
        return {"status": "error", "error": "value must be a number"}
    from_unit = str(args.get("from_unit") or "").strip().lower()
    to_unit = str(args.get("to_unit") or "").strip().lower()
    if not from_unit or not to_unit:
        return {"status": "error", "error": "from_unit and to_unit are required"}

    # Temperature special cases
    if from_unit == "celsius" and to_unit == "fahrenheit":
        result = value * 9 / 5 + 32
        return {"status": "ok", "value": value, "from": from_unit, "to": to_unit, "result": result}
    if from_unit == "fahrenheit" and to_unit == "celsius":
        result = (value - 32) * 5 / 9
        return {"status": "ok", "value": value, "from": from_unit, "to": to_unit, "result": result}
    if from_unit == "celsius" and to_unit == "kelvin":
        result = value + 273.15
        return {"status": "ok", "value": value, "from": from_unit, "to": to_unit, "result": result}
    if from_unit == "kelvin" and to_unit == "celsius":
        result = value - 273.15
        return {"status": "ok", "value": value, "from": from_unit, "to": to_unit, "result": result}

    factor = _UNIT_FACTORS.get((from_unit, to_unit))
    if factor is None:
        return {"status": "error", "error": f"Unknown conversion: {from_unit} → {to_unit}"}
    return {"status": "ok", "value": value, "from": from_unit, "to": to_unit, "result": round(value * factor, 8)}


def _exec_percentage(args: dict[str, Any]) -> dict[str, Any]:
    try:
        value = float(args.get("value") or 0)
        total = float(args.get("total") or 0)
    except (TypeError, ValueError):
        return {"status": "error", "error": "value and total must be numbers"}
    if not args.get("total") and args.get("total") != 0:
        return {"status": "error", "error": "total is required"}
    if total == 0:
        return {"status": "error", "error": "total cannot be zero"}
    pct = (value / total) * 100
    return {"status": "ok", "value": value, "total": total, "percentage": round(pct, 4)}


MATH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression precisely using sympy. Supports algebra, trigonometry, sqrt, log, fractions, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate, e.g. 'sqrt(144)', '2**10', 'sin(pi/4)'."},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unit_convert",
            "description": "Convert a value between units (length, weight, temperature, volume, speed, time, data).",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "The numeric value to convert."},
                    "from_unit": {"type": "string", "description": "Source unit, e.g. 'km', 'celsius', 'lbs'."},
                    "to_unit": {"type": "string", "description": "Target unit, e.g. 'm', 'fahrenheit', 'kg'."},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "percentage",
            "description": "Calculate what percentage value is of total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "The part value."},
                    "total": {"type": "number", "description": "The whole/total value."},
                },
                "required": ["value", "total"],
            },
        },
    },
]
