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
_MAX_DESC_CHARS = 300
_VISION_TIMEOUT = 90  # qwen2.5vl:3b lokalt bruger ~10-15s; 90s buffer

# Roterende fokus-prompts — én per optagelse (cyklisk efter index).
# Hvert fokus giver modellen et konkret sanseankre så output varierer.
# Alle prompts spørger om stemning, lys, tilstedeværelse og det der springer
# i øjnene — men med forskellig indgangsvinkel så output ikke bliver fladt.
_VISION_PROMPT_PREFIX = (
    "Se på billedet og beskriv rummet i 2-3 korte sætninger på dansk. "
    "SVAR KUN PÅ DANSK. Undgå generelle vendinger som "
    "'professionelt arbejdsrum' eller 'et rum med ting i'."
)

_VISION_PROMPTS = [
    (
        "Fokus: STEMNINGEN og LYSET. Hvilken atmosfære har rummet lige nu — "
        "intim, travl, tom, koncentreret, søvnig? Beskriv lyskilderne og "
        "farvetonen (varmt/køligt, gult/blåt, skarpt/dæmpet). Hvad fortæller "
        "lyset om tidspunktet eller sindsstemningen i rummet?"
    ),
    (
        "Fokus: TILSTEDEVÆRELSE. Er der mennesker i billedet — eller spor "
        "efter nogen (en jakke på stolen, en åben kop, en tændt skærm)? "
        "Hvad fortæller det om rummet? Og hvordan er lysets farvetone mens "
        "du observerer det?"
    ),
    (
        "Fokus: KONTRASTER og DET DER SPRINGER I ØJNENE. Beskriv "
        "modsætninger: lys/mørke, orden/kaos, bevægelse/stilhed, nært/fjernt. "
        "Nævn også lysets farvetone og om nogen er til stede. Hvad er det "
        "første et menneske ville lægge mærke til?"
    ),
    (
        "Fokus: NUET og STEMNINGEN. Hvad signalerer billedet om hvad der "
        "lige er sket eller er ved at ske? Spor af aktivitet, pause, "
        "afslutning? Beskriv også lysets tone og om du fornemmer nogens "
        "tilstedeværelse."
    ),
]


def _compare_suffix(previous_desc: str, time_ago_label: str) -> str:
    """Optional instruction: ask the VLM to note what has changed."""
    trimmed = (previous_desc or "").strip().replace("\n", " ")
    if len(trimmed) > 240:
        trimmed = trimmed[:240].rstrip() + "…"
    return (
        f"\n\nForrige beskrivelse ({time_ago_label}): «{trimmed}»\n"
        "HVIS noget tydeligt har ændret sig siden da, nævn det kort. "
        "HVIS rummet virker uændret, så skriv slet ingen sammenligning."
    )


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
        image_b64 = _capture_image()
    except Exception as exc:
        logger.warning("visual_memory: image capture failed: %s", exc)
        return {"status": "capture_failed", "error": str(exc)}

    # Describe — feed most recent record for change detection
    existing_records = _load_records()
    previous = existing_records[-1] if existing_records else None
    try:
        description = _describe_image(
            image_b64, model=model, provider=provider, previous=previous
        )
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
    records = existing_records
    records.append(record)
    if len(records) > _MAX_RECORDS:
        records = records[-_MAX_RECORDS:]
    set_runtime_state_value(_STATE_KEY, records)

    _archive_sensory(
        description,
        metadata={
            "source": "visual_memory_daemon",
            "model": model,
            "provider": provider,
            "on_demand": False,
        },
    )

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
        image_b64 = _capture_image()
    except Exception as exc:
        logger.warning("look_around: image capture failed: %s", exc)
        return {"status": "capture_failed", "error": str(exc)}

    existing_records = _load_records()
    previous = existing_records[-1] if existing_records else None
    prompt_to_use = prompt_override.strip() or None
    description = _describe_image(
        image_b64,
        model=model,
        provider=provider,
        prompt=prompt_to_use,
        previous=previous if prompt_to_use is None else None,
    )
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
    records = existing_records
    records.append(record)
    if len(records) > _MAX_RECORDS:
        records = records[-_MAX_RECORDS:]
    set_runtime_state_value(_STATE_KEY, records)

    _archive_sensory(
        description,
        metadata={
            "source": "look_around",
            "model": model,
            "provider": provider,
            "on_demand": True,
            "custom_prompt": bool(prompt_to_use),
        },
    )

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


def _capture_image() -> str:
    """Capture image from configured source (HA camera or webcam) and return as base64 JPEG."""
    source = _capture_source()
    if source == "ha_camera":
        try:
            return _capture_ha_camera()
        except Exception as exc:
            logger.warning("visual_memory: HA camera capture failed (%s), falling back to webcam", exc)
            return _capture_webcam()
    return _capture_webcam()


def _capture_source() -> str:
    """Return 'ha_camera' or 'webcam' based on runtime config."""
    settings = load_settings()
    return str(settings.extra.get("visual_memory_source") or "webcam").strip()


def _ha_camera_entity() -> str:
    """Return HA camera entity_id from runtime config."""
    settings = load_settings()
    return str(settings.extra.get("visual_memory_ha_camera_entity") or "camera.camera_hub_g2hpro_9a57").strip()


def _capture_ha_camera() -> str:
    """Fetch snapshot from Home Assistant camera and return as base64 JPEG string."""
    settings = load_settings()
    ha_url = str(settings.extra.get("home_assistant_url") or "").strip()
    ha_token = str(settings.extra.get("home_assistant_token") or "").strip()
    entity_id = _ha_camera_entity()

    if not ha_url or not ha_token:
        raise RuntimeError("home_assistant_url eller home_assistant_token ikke konfigureret")

    # HA camera_proxy endpoint returns the live camera image directly
    url = f"{ha_url.rstrip('/')}/api/camera_proxy/{entity_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {ha_token}",
            "User-Agent": "Jarvis-VisualMemory/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        content_type = str(resp.headers.get("Content-Type") or "").lower()
        image_bytes = resp.read()

    if not image_bytes or len(image_bytes) < 1024:
        raise RuntimeError(
            f"HA kamera returnerede for lille payload ({len(image_bytes)} bytes)"
        )
    if content_type and not content_type.startswith("image/"):
        raise RuntimeError(
            f"HA kamera returnerede non-image content-type: {content_type}"
        )

    return base64.b64encode(image_bytes).decode("ascii")


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


def _describe_image(
    image_b64: str,
    *,
    model: str,
    provider: str,
    prompt: str | None = None,
    previous: dict[str, object] | None = None,
) -> str:
    """Send image to vision model and return description."""
    if provider == "ollama":
        return _describe_via_ollama(
            image_b64, model=model, prompt=prompt, previous=previous
        )
    raise RuntimeError(f"visual_memory: unsupported vision provider: {provider}")


def _previous_time_label(captured_at: str) -> str:
    try:
        dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        minutes_ago = int((datetime.now(UTC) - dt.astimezone(UTC)).total_seconds() / 60)
    except Exception:
        return "tidligere"
    if minutes_ago < 2:
        return "lige før"
    if minutes_ago < 60:
        return f"for {minutes_ago} min siden"
    if minutes_ago < 1440:
        return f"for {minutes_ago // 60}t siden"
    return f"for {minutes_ago // 1440}d siden"


def _build_prompt(previous: dict[str, object] | None = None, prompt_index: int | None = None) -> str:
    """Assemble the full vision prompt: prefix + rotating focus + optional compare."""
    if prompt_index is None:
        prompt_index = int(time.time() // 3600) % len(_VISION_PROMPTS)
    focus = _VISION_PROMPTS[prompt_index % len(_VISION_PROMPTS)]
    parts = [_VISION_PROMPT_PREFIX, focus]
    if previous:
        prev_desc = str(previous.get("description") or "").strip()
        prev_at = str(previous.get("captured_at") or "")
        if prev_desc and prev_at:
            parts.append(_compare_suffix(prev_desc, _previous_time_label(prev_at)))
    return "\n\n".join(parts)


def _describe_via_ollama(
    image_b64: str,
    *,
    model: str,
    prompt: str | None = None,
    previous: dict[str, object] | None = None,
) -> str:
    """Call Ollama generate API with image payload."""
    if prompt is None:
        prompt = _build_prompt(previous=previous)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "options": {
            "num_predict": 150,
            "temperature": 1.1,
            "seed": int(time.time()),  # unique seed → no cached repetition
        },
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
        # qwen2.5vl:7b — lokal vision model, dansk, bedre kvalitet end 3b
        # Kræver ~8.6 GiB RAM i Ollama-LXC'en — fungerer fra 12 GB opefter.
        # Fald-tilbage til qwen2.5vl:3b hvis RAM er knapt.
        # (gemma4:31b-cloud var tidligere default men cloud-timeouts > 45s)
        model = "qwen2.5vl:7b"
    if not provider:
        provider = "ollama"
    return model, provider


def _enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_visual_memory_enabled", True))


def _archive_sensory(description: str, *, metadata: dict[str, object]) -> None:
    """Mirror every visual memory into Sansernes Arkiv. Silent on failure."""
    try:
        from core.services.sensory_archive import record_visual
        record_visual(description, metadata=dict(metadata))
    except Exception as exc:
        logger.debug("visual_memory: archive mirror failed: %s", exc)
