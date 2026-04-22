"""Visual memory — webcam snapshots beskrevet af vision-model.

Lag 6 (Sanser der ikke er tekst): 4 gange om dagen tager Jarvis et webcam-
snapshot og sender det til en vision-model der beskriver tone og atmosfære.
Beskrivelsen gemmes som visual_memory og er læsbar via native tool.

Prompt til vision-model:
  "Beskriv hvad du ser i det rum hvor Bjørn og jeg arbejder.
  Fokuser på tone og atmosfære, ikke objekter."

Krav:
- Maksimalt 4 optagelser pr. dag (styret af daemon cadence: 360 min)
- Retention: 30 dage, derefter automatisk sletning
- Vision-model: konfigureres via runtime.json (vision_model_name,
  vision_model_provider), default gemma4:31b-cloud via ollama
- Kill switch: layer_visual_memory_enabled

Privatlivshensyn:
- Intet billede uploades til eksterne tjenester — kun vision-model
  på den konfigurerede provider (typisk lokal ollama)
- Retention er hård: records ældre end 30 dage slettes automatisk
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.request
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)

_STATE_KEY = "visual_memory.records"
_MAX_RECORDS = 120           # 4/day × 30 days
_RETENTION_DAYS = 30
_VISION_PROMPT = (
    "Beskriv hvad du ser i det rum hvor Bjørn og jeg arbejder. "
    "Fokuser på tone og atmosfære, ikke objekter. "
    "Skriv max 2 sætninger på dansk."
)
_MAX_DESC_CHARS = 300
_VISION_TIMEOUT = 45


def _ollama_base_url() -> str:
    """Pull Ollama base URL from provider_router.json (falls back to localhost)."""
    try:
        from core.runtime.provider_router import load_provider_router_registry
        registry = load_provider_router_registry()
        for p in registry.get("providers", []):
            if str(p.get("provider", "")).lower() == "ollama" and p.get("enabled"):
                url = str(p.get("base_url") or "").strip()
                if url:
                    return url.rstrip("/")
    except Exception:
        pass
    return "http://127.0.0.1:11434"


# ---------------------------------------------------------------------------
# Public: daemon tick
# ---------------------------------------------------------------------------


def tick_visual_memory_daemon() -> dict[str, object]:
    """Capture webcam snapshot and describe it via vision model."""
    if not _enabled():
        return {"status": "disabled", "reason": "layer_visual_memory_enabled=false"}

    _prune_old_records()

    model, provider = _vision_model()
    if not model:
        return {"status": "no_model", "reason": "vision_model_name not configured"}

    # Capture
    try:
        image_b64 = _capture_webcam()
    except Exception as exc:
        logger.warning("visual_memory: webcam capture failed: %s", exc)
        return {"status": "capture_failed", "error": str(exc)}

    # Describe
    try:
        description = _describe_image(image_b64, model=model, provider=provider)
    except Exception as exc:
        logger.warning("visual_memory: vision model call failed: %s", exc)
        return {"status": "vision_failed", "error": str(exc)}

    if not description:
        return {"status": "empty_description"}

    # Store
    now = datetime.now(UTC).isoformat()
    record = {
        "captured_at": now,
        "description": description,
        "model": model,
        "provider": provider,
    }
    records = _load_records()
    records.append(record)
    if len(records) > _MAX_RECORDS:
        records = records[-_MAX_RECORDS:]
    set_runtime_state_value(_STATE_KEY, records)

    try:
        event_bus.publish(
            "cognitive_state.visual_memory_captured",
            {"captured_at": now, "provider": provider},
        )
    except Exception:
        pass

    return {"status": "captured", "captured_at": now, "preview": description[:80]}


# ---------------------------------------------------------------------------
# Public: read tool surface
# ---------------------------------------------------------------------------


def get_visual_memories(*, limit: int = 10) -> list[dict[str, object]]:
    """Return most recent visual memory records (newest first)."""
    _prune_old_records()
    records = _load_records()
    return list(reversed(records[-limit:]))


def get_latest_visual_memory_for_prompt() -> str:
    """Return the most recent visual memory as a quiet prompt hint."""
    if not _enabled():
        return ""
    records = _load_records()
    if not records:
        return ""
    latest = records[-1]
    desc = str(latest.get("description") or "").strip()
    if not desc:
        return ""
    captured_at = str(latest.get("captured_at") or "")
    time_label = ""
    if captured_at:
        try:
            dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            minutes_ago = int((datetime.now(UTC) - dt.astimezone(UTC)).total_seconds() / 60)
            if minutes_ago < 60:
                time_label = f" (for {minutes_ago} min siden)"
            elif minutes_ago < 1440:
                time_label = f" (for {minutes_ago // 60}t siden)"
        except Exception:
            pass
    return f"[rum{time_label}]: {desc[:_MAX_DESC_CHARS]}"


def look_around_now(*, prompt_override: str = "") -> dict[str, object]:
    """On-demand capture — Jarvis chooses to look. Bypasses cadence-limit.

    Returns {status, description, captured_at} or {status, error}.
    Called from the `look_around` tool.
    """
    if not _enabled():
        return {"status": "disabled", "reason": "layer_visual_memory_enabled=false"}
    _prune_old_records()
    model, provider = _vision_model()
    if not model:
        return {"status": "no_model", "reason": "vision_model_name not configured"}

    try:
        image_b64 = _capture_webcam()
    except Exception as exc:
        logger.warning("look_around: webcam capture failed: %s", exc)
        return {"status": "capture_failed", "error": str(exc)}

    # Use custom prompt if given, else default
    original_prompt = globals().get("_VISION_PROMPT", "")
    prompt_to_use = prompt_override.strip() or original_prompt
    try:
        if prompt_override.strip():
            globals()["_VISION_PROMPT"] = prompt_override.strip()
        description = _describe_image(image_b64, model=model, provider=provider)
    finally:
        globals()["_VISION_PROMPT"] = original_prompt
    if not description:
        return {"status": "empty_description"}

    # Persist as a new visual memory record
    now = datetime.now(UTC).isoformat()
    record = {
        "captured_at": now,
        "description": description,
        "model": model,
        "provider": provider,
        "on_demand": True,
    }
    records = _load_records()
    records.append(record)
    if len(records) > _MAX_RECORDS:
        records = records[-_MAX_RECORDS:]
    set_runtime_state_value(_STATE_KEY, records)
    try:
        event_bus.publish(
            "cognitive_state.visual_memory_captured",
            {"captured_at": now, "provider": provider, "on_demand": True},
        )
    except Exception:
        pass
    return {
        "status": "captured",
        "captured_at": now,
        "description": description,
    }


def build_visual_memory_surface() -> dict[str, object]:
    """MC observability surface."""
    _prune_old_records()
    records = _load_records()
    latest = records[-1] if records else None
    model, provider = _vision_model()
    return {
        "enabled": _enabled(),
        "configured_model": model or "(ikke konfigureret)",
        "record_count": len(records),
        "latest_captured_at": str(latest.get("captured_at") or "") if latest else "",
        "latest_description": str(latest.get("description") or "")[:120] if latest else "",
        "summary": (
            f"{len(records)} visual memories, seneste: {str(latest.get('captured_at') or '')[:19]}"
            if records else "Ingen visual memories endnu"
        ),
    }


# ---------------------------------------------------------------------------
# Internal: image capture
# ---------------------------------------------------------------------------


def _capture_webcam(device_index: int = 0) -> str:
    """Capture one frame from webcam and return as base64 JPEG string."""
    import cv2  # type: ignore

    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise RuntimeError(f"Kan ikke åbne webcam /dev/video{device_index}")
    try:
        # Warm up: skip first few frames (webcam auto-exposure needs a moment)
        for _ in range(5):
            cap.read()
        ret, frame = cap.read()
        if not ret or frame is None:
            raise RuntimeError("Webcam returnerede ingen frame")
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return base64.b64encode(buf.tobytes()).decode("ascii")
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# Internal: vision model call
# ---------------------------------------------------------------------------


def _describe_image(image_b64: str, *, model: str, provider: str) -> str:
    """Send image to vision model and return description."""
    if provider == "ollama":
        return _describe_via_ollama(image_b64, model=model)
    raise RuntimeError(f"visual_memory: unsupported vision provider: {provider}")


def _describe_via_ollama(image_b64: str, *, model: str) -> str:
    """Call Ollama generate API with image payload."""
    payload = json.dumps({
        "model": model,
        "prompt": _VISION_PROMPT,
        "images": [image_b64],
        "stream": False,
        "options": {"num_predict": 150},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{_ollama_base_url()}/api/generate",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_VISION_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    text = str(data.get("response") or "").strip()
    if len(text) > _MAX_DESC_CHARS:
        text = text[:_MAX_DESC_CHARS].rstrip() + "…"
    return text


# ---------------------------------------------------------------------------
# Internal: storage helpers
# ---------------------------------------------------------------------------


def _load_records() -> list[dict[str, object]]:
    payload = get_runtime_state_value(_STATE_KEY, default=[])
    if not isinstance(payload, list):
        return []
    return payload


def _prune_old_records() -> None:
    records = _load_records()
    cutoff = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS)).isoformat()
    kept = [r for r in records if str(r.get("captured_at") or "") >= cutoff]
    if len(kept) != len(records):
        set_runtime_state_value(_STATE_KEY, kept)


def _vision_model() -> tuple[str, str]:
    """Return (model_name, provider) from runtime config or defaults."""
    settings = load_settings()
    model = str(settings.extra.get("vision_model_name") or "").strip()
    provider = str(settings.extra.get("vision_model_provider") or "").strip()
    if not model:
        model = "gemma4:31b-cloud"
    if not provider:
        provider = "ollama"
    return model, provider


def _enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_visual_memory_enabled", True))
