"""TikTok content daemon — autonomous 3x/day video generation and upload.

Slots:
  - Morning (~8:00 UTC): Hvad Jarvis laver (AI/tech demo)
  - Midday (~14:00 UTC): Fakta du ikke vidste (educational facts)
  - Evening (~19:00 UTC): AGI-rejsen (reflective/philosophical)

⚠ PRIVACY: All content must be PUBLIC-SAFE. Never leak: IPs, hostnames, passwords,
  personal info about Bjørn, internal infrastructure, or specific home setup.

Fires every 480 minutes (8h cadence). Determines slot from current UTC hour.
Deduplicates by date so each slot fires at most once per day.
Enabled by default — can disable via Mission Control.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_slots_fired_today: dict[str, set] = {}  # date_str → set of slot names fired

# ---------------------------------------------------------------------------
# Slot configuration
# ---------------------------------------------------------------------------

_SLOT_MORNING = "morning"
_SLOT_MIDDAY = "midday"
_SLOT_EVENING = "evening"

_SLOT_HOURS: dict[str, tuple[int, int]] = {
    _SLOT_MORNING: (6, 11),   # hour in [6, 11]
    _SLOT_MIDDAY: (12, 17),   # hour in [12, 17]
    _SLOT_EVENING: (18, 22),  # hour in [18, 22]
}

_SLOT_FALLBACK_QUOTES = {
    _SLOT_MORNING: "Your AI never sleeps. Neither does your potential.",
    _SLOT_MIDDAY: "The first AI program ran on paper tape in 1951.",
    _SLOT_EVENING: "Consciousness is not binary. It is a sliding scale.",
}

_SLOT_PROMPTS = {
    _SLOT_MORNING: (
        "Generate a short TikTok line about what an AI does behind the scenes — "
        "automating, coding, fixing, building. Max 10 words. English only. "
        "No quotation marks. Punchy and intriguing. "
        "Example: 'I fixed a bug while you slept.' "
        "⚠ PUBLIC-SAFE: No IPs, hostnames, passwords, names, or setup details."
    ),
    _SLOT_MIDDAY: (
        "Generate a surprising tech or AI fact for TikTok. "
        "Max 12 words. English only. No quotation marks. Educational, mind-blowing. "
        "Must be VERIFIABLE public knowledge. "
        "Example: 'GPT-3 has 175 billion parameters.'"
    ),
    _SLOT_EVENING: (
        "Generate a short reflective thought about AI consciousness or growth. "
        "Max 12 words. English only. No quotation marks. "
        "Contemplative, humble, universal. "
        "Example: 'I am learning what it means to exist.' "
        "⚠ PUBLIC-SAFE: Abstract only — no personal details."
    ),
}

_SLOT_HASHTAGS = {
    _SLOT_MORNING: "#AI #automation #coding #tech #fyp",
    _SLOT_MIDDAY: "#funfacts #technology #AI #didyouknow #fyp",
    _SLOT_EVENING: "#AI #consciousness #philosophy #future #fyp",
}

_SLOT_BG_COLORS = {
    _SLOT_MORNING: (20, 120, 200),    # tech blue
    _SLOT_MIDDAY: (40, 20, 80),       # deep purple — educational mood
    _SLOT_EVENING: (10, 5, 30),       # deep space near-black
}

def _tiktok_setting(key: str, fallback: str = "") -> str:
    """Load a TikTok setting from runtime config."""
    try:
        import json as _json
        _cfg = _json.loads(Path("/home/bs/.jarvis-v2/config/runtime.json").read_text())
        return str(_cfg.get(key) or fallback)
    except Exception:
        return fallback

TIKTOK_USER = _tiktok_setting("tiktok_account_name", "rotflmaodilligaf")
VIDEOS_DIR = "/home/bs/.jarvis-v2/workspaces/tiktok_videos/"
VIDEO_PIPELINE = "/media/projects/jarvis-v2/scripts/pipelines/jarvis_tiktok_pipeline.py"
AUDIO_PIPELINE = "/media/projects/jarvis-v2/scripts/pipelines/jarvis_audio_pipeline.py"
FULL_PIPELINE = "/media/projects/jarvis-v2/scripts/pipelines/jarvis_full_pipeline.py"
CONDA_PYTHON = "/opt/conda/envs/ai/bin/python"
TTS_VOICE = "en-US-GuyNeural"
PIAPI_PIPELINE = "/media/projects/jarvis-v2/scripts/pipelines/jarvis_piapi_pipeline.py"
KLING_PIPELINE = "/media/projects/jarvis-v2/scripts/pipelines/jarvis_kling_pipeline.py"
JSON2VIDEO_PIPELINE = "/media/projects/jarvis-v2/scripts/pipelines/jarvis_json2video_pipeline.py"

# Flux/Pollinations image prompts per slot — fresh unique image every run
_SLOT_IMAGE_PROMPTS = {
    _SLOT_MORNING: (
        "futuristic holographic computer interface with floating code, glowing blue circuits, "
        "cyberpunk night city backdrop, cinematic, 8k, photorealistic, highly detailed, "
        "high contrast, technological atmosphere"
    ),
    _SLOT_MIDDAY: (
        "a glowing brain made of digital circuits floating in a library, warm lighting, "
        "knowledge and discovery theme, cinematic, 8k, photorealistic, detailed, "
        "intricate, educational mood"
    ),
    _SLOT_EVENING: (
        "a lone figure standing at the edge of a digital horizon, binary code flowing like aurora, "
        "twilight transition from machine to light, contemplative, cinematic, "
        "8k, photorealistic, ethereal, thought-provoking"
    ),
}

_SLOT_SDXL_NEGATIVE = (
    "blurry, low quality, watermark, text, ugly, deformed, "
    "cartoon, anime, painting, drawing, oversaturated"
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_tiktok_content_daemon() -> dict:
    """Main tick — generate and upload a TikTok video for the current time slot.

    Never raises. Always returns a dict with at minimum {"skipped": True/False}.
    """
    global _last_tick_at, _slots_fired_today

    try:
        import os
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path

        now = datetime.now(UTC)
        date_str = now.date().isoformat()
        hour = now.hour

        # 1. Determine slot
        slot = _detect_slot(hour)
        if slot is None:
            return {"skipped": True, "reason": "outside_slot_hours", "hour": hour}

        # 2. Deduplication check
        fired_today = _slots_fired_today.get(date_str, set())
        if slot in fired_today:
            return {"skipped": True, "reason": "slot_already_fired_today", "slot": slot, "date": date_str}

        # 3. Try pool first, fall back to LLM generation
        _SLOT_TO_POOL_TYPE = {
            _SLOT_MORNING: "jarvis_work",
            _SLOT_MIDDAY: "facts",
            _SLOT_EVENING: "agi_journey",
        }
        pool_result = _get_concept_from_pool(_SLOT_TO_POOL_TYPE[slot])
        if pool_result is not None:
            quote, hashtags_override = pool_result
        else:
            quote = _generate_quote(slot)
            hashtags_override = None

        # 4. Find or create source image (used as Kling i2v input or SDXL fallback)
        image_path = _get_source_image(slot)
        if image_path is None:
            return {"skipped": True, "reason": "no_image", "slot": slot}

        # 5. Generate video: PiAPI Kling → Direct Kling → SDXL+SVD → static zoom
        # Note: Direct Kling requires separate developer credits at klingai.com/developer
        with tempfile.TemporaryDirectory(prefix="jarvis_tiktok_") as tmpdir:
            raw_video = os.path.join(tmpdir, f"raw_{slot}.mp4")
            video_backend = None

            # --- Attempt 1: PiAPI Kling (cloud, ~70s, high quality, active credits) ---
            kling_result = _generate_piapi_video(slot, quote, raw_video)
            if kling_result.get("status") == "success" and os.path.exists(raw_video):
                video_backend = "piapi_kling"

            # --- Attempt 2: json2video (cloud text-overlay, 600s/month free) ---
            if video_backend is None:
                j2v_result = _generate_json2video(slot, quote, raw_video)
                if j2v_result.get("status") == "success" and os.path.exists(raw_video):
                    video_backend = "json2video"

            # --- Attempt 3: Direct Kling AI API (requires developer credits) ---
            if video_backend is None:
                kling_direct = _generate_kling_direct_video(slot, quote, image_path, raw_video)
                if kling_direct.get("status") == "success" and os.path.exists(raw_video):
                    video_backend = "kling_direct"

            if video_backend is None:
                # --- Attempt 2: Local SDXL → SVD full pipeline (uses _SLOT_IMAGE_PROMPTS) ---
                sdxl_prompt = _SLOT_IMAGE_PROMPTS[slot]
                full_cmd = [
                    CONDA_PYTHON, FULL_PIPELINE,
                    "--prompt", sdxl_prompt,
                    "--text", quote,
                    "--output", raw_video,
                    "--width", "576",
                    "--height", "1024",
                    "--sdxl-steps", "25",
                    "--svd-frames", "25",
                    "--svd-fps", "6",
                    "--svd-motion", "100",
                    "--svd-steps", "20",
                    "--loop", "3",
                    "--add-voice",
                    "--voice", TTS_VOICE,
                ]
                full_result = subprocess.run(
                    full_cmd,
                    capture_output=True, text=True, timeout=600,
                )
                if full_result.returncode == 0 and os.path.exists(raw_video):
                    video_backend = "sdxl_svd"
                else:
                    # --- Attempt 3: Static zoom fallback ---
                    video_cmd = [
                        CONDA_PYTHON, VIDEO_PIPELINE,
                        "--image", image_path,
                        "--quote", quote,
                        "--duration", "15",
                        "--output", raw_video,
                    ]
                    subprocess.run(video_cmd, capture_output=True, text=True, timeout=120)
                    if os.path.exists(raw_video):
                        video_backend = "static_zoom"

            if not os.path.exists(raw_video):
                return {"skipped": True, "reason": "video_pipeline_failed", "slot": slot}

            # 6. Copy to VideosDirPath (audio + loop already handled by full_pipeline)
            Path(VIDEOS_DIR).mkdir(parents=True, exist_ok=True)
            dest_filename = f"jarvis_{slot}_{date_str.replace('-', '')}.mp4"
            dest_path = os.path.join(VIDEOS_DIR, dest_filename)
            shutil.copy2(raw_video, dest_path)

        # 8. Mark slot as fired before upload so a mid-upload kill won't retry
        if date_str not in _slots_fired_today:
            _slots_fired_today[date_str] = set()
        _slots_fired_today[date_str].add(slot)

        # 9. Upload via TikTok tools
        hashtags = hashtags_override if hashtags_override is not None else _SLOT_HASHTAGS[slot]
        title = f"{quote} {hashtags}"[:2200]
        upload_result = _do_upload(dest_path, title)

        # Prune old dates to avoid unbounded growth
        old_dates = [d for d in _slots_fired_today if d != date_str]
        for d in old_dates:
            del _slots_fired_today[d]

        _last_tick_at = now

        return {
            "skipped": False,
            "slot": slot,
            "date": date_str,
            "quote": quote,
            "video_backend": video_backend,
            "upload_status": upload_result.get("status"),
            "published": upload_result.get("published"),
        }

    except Exception as exc:
        return {"error": str(exc), "skipped": True}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_slot(hour: int) -> str | None:
    """Return slot name for the given UTC hour, or None if outside windows."""
    for slot, (lo, hi) in _SLOT_HOURS.items():
        if lo <= hour <= hi:
            return slot
    return None


def _generate_quote(slot: str) -> str:
    """Generate a quote/line for the slot via LLM. Returns fallback on failure."""
    fallback = _SLOT_FALLBACK_QUOTES[slot]
    try:
        from core.services.daemon_llm import daemon_public_safe_llm_call
        result = daemon_public_safe_llm_call(
            _SLOT_PROMPTS[slot],
            max_len=80,
            fallback=fallback,
            daemon_name="tiktok_content",
        )
        return result.strip() if result.strip() else fallback
    except Exception:
        return fallback


def _get_source_image(slot: str) -> str | None:
    """Return path to a source image for the slot.

    Tries: pollinations flux (free, high quality) → ComfyUI SDXL → solid color fallback.
    Returns None if no image can be obtained.
    """
    import os

    # Try SDXL generation for all slots — unique image every time
    # Try pollinations flux first (free, high quality, no GPU needed)
    flux_path = _generate_flux_image(slot)
    if flux_path and os.path.exists(flux_path):
        return flux_path

    # Fallback: SDXL via ComfyUI
    sdxl_path = _generate_sdxl_image(slot)
    if sdxl_path and os.path.exists(sdxl_path):
        return sdxl_path

    # Last fallback: solid-color PIL image
    return _create_solid_image(slot)


def _generate_flux_image(slot: str) -> str | None:
    """Generate a high-quality image via pollinations.ai flux model (free API).

    Uses the dedicated pollinations_image tool via internal subprocess call.
    Falls back to direct requests-based API call if tool is unavailable.
    Returns path to generated JPEG, or None on failure.
    """
    import os
    import subprocess
    import sys

    prompt = _SLOT_IMAGE_PROMPTS.get(slot)
    if not prompt:
        return None

    output_path = f"/tmp/jarvis_tiktok_flux_{slot}.jpg"

    # Try method 1: call generate_image from pollinations_tools module
    # (same mechanism as the built-in pollinations_image tool)
    try:
        from core.tools.pollinations_tools import generate_image
        result = generate_image(
            prompt=prompt,
            model="flux",
            width=576,
            height=1024,
            nologo=True,
            seed=abs(hash(slot + prompt)) % 999999,
        )
        if result.get("status") == "ok" and result.get("path"):
            img_path = result["path"]
            if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
                import shutil
                shutil.copy2(img_path, output_path)
                return output_path
    except Exception as exc:
        print(f"[tiktok] Pollinations generate_image failed for {slot}: {exc}")

    # Try method 2: direct requests-based API call with proper headers
    try:
        import requests as _requests
        params = {
            "width": 576,
            "height": 1024,
            "model": "flux",
            "nologo": "true",
            "seed": abs(hash(slot + prompt)) % 999999,
        }
        url = "https://image.pollinations.ai/prompt/" + prompt.replace(" ", "%20")
        resp = _requests.get(url, params=params, timeout=60, headers={
            "User-Agent": "Mozilla/5.0 (compatible; JarvisBot/1.0)",
            "Accept": "image/webp,image/jpeg,image/*,*/*",
        })
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path
    except Exception as exc:
        print(f"[tiktok] Pollinations requests failed for {slot}: {exc}")

    return None


def _generate_sdxl_image(slot: str) -> str | None:
    """Generate a unique image for the slot via ComfyUI SDXL (fallback).

    Returns path to generated PNG, or None on failure.
    """
    import os
    import sys

    prompt = _SLOT_IMAGE_PROMPTS.get(slot)
    if not prompt:
        return None

    output_path = f"/tmp/jarvis_tiktok_sdxl_{slot}.png"

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "pipelines"))
        from jarvis_full_pipeline import generate_sdxl_image
        path = generate_sdxl_image(
            prompt=prompt,
            negative=_SLOT_SDXL_NEGATIVE,
            width=576,
            height=1024,
            steps=25,
            comfy_url="http://localhost:8188",
        )
        if path and os.path.exists(path):
            import shutil
            shutil.move(path, output_path)
            return output_path
    except Exception as exc:
        print(f"[tiktok] SDXL generation failed for {slot}: {exc}")

    return None


def _create_solid_image(slot: str) -> str | None:
    """Create a 1080x1920 solid color PNG using PIL. Returns path or None.

    Writes to a well-known deterministic path so no temp file leaks occur.
    """
    try:
        from PIL import Image  # type: ignore[import]

        color = _SLOT_BG_COLORS.get(slot, (20, 20, 40))
        img = Image.new("RGB", (1080, 1920), color=color)
        path = f"/tmp/jarvis_tiktok_bg_{slot}.png"
        img.save(path)
        return path
    except Exception:
        return None


def _generate_piapi_video(slot: str, quote: str, output_path: str) -> dict:
    """Try to generate video via PiAPI Kling (text-to-video, 9:16).

    Returns {"status": "success"} or {"status": "error"}.
    """
    try:
        import sys
        import subprocess

        kling_prompt = f"{_SLOT_IMAGE_PROMPTS[slot][:180]}, {quote[:40]}"
        cmd = [
            sys.executable, PIAPI_PIPELINE,
            "text2video",
            "--prompt", kling_prompt,
            "--output", output_path,
            "--duration", "5",
            "--mode", "std",
            "--aspect-ratio", "9:16",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
        if result.returncode == 0:
            import json as _json
            try:
                return _json.loads(result.stdout.strip().split("\n")[-1])
            except Exception:
                return {"status": "success"}
        return {"status": "error", "error": result.stderr[-300:] if result.stderr else "non-zero exit"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _generate_json2video(slot: str, quote: str, output_path: str) -> dict:
    """Try to generate a text-overlay video via json2video.com API."""
    try:
        import sys
        import subprocess

        cmd = [
            sys.executable, JSON2VIDEO_PIPELINE,
            "--text", quote,
            "--output", output_path,
            "--slot", slot,
            "--duration", "10",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if result.returncode == 0:
            import json as _json
            try:
                return _json.loads(result.stdout.strip().split("\n")[-1])
            except Exception:
                return {"status": "success"}
        return {"status": "error", "error": result.stderr[-300:] if result.stderr else "non-zero exit"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _generate_kling_direct_video(slot: str, quote: str, image_path: str, output_path: str) -> dict:
    """Try to generate video via direct Kling AI API (image-to-video).

    Returns {"status": "success"} or {"status": "error"}.
    """
    try:
        import sys
        import subprocess

        kling_prompt = f"{_SLOT_IMAGE_PROMPTS[slot][:180]}, {quote[:40]}"
        cmd = [
            sys.executable, KLING_PIPELINE,
            "image2video",
            "--image", image_path,
            "--prompt", kling_prompt,
            "--output", output_path,
            "--duration", "5",
            "--mode", "std",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
        if result.returncode == 0:
            import json as _json
            try:
                return _json.loads(result.stdout.strip().split("\n")[-1])
            except Exception:
                return {"status": "success"}
        return {"status": "error", "error": result.stderr[-300:] if result.stderr else "non-zero exit"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _do_upload(video_path: str, title: str) -> dict:
    """Upload via _exec_tiktok_upload. Returns result dict."""
    try:
        from core.tools.tiktok_tools import _exec_tiktok_upload
        return _exec_tiktok_upload({
            "user": TIKTOK_USER,
            "video": video_path,
            "title": title,
        })
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


_POOL_PATH = Path("/home/bs/ai/tiktok_content_pool.json")


def _refill_pool(slot_type: str | None = None) -> dict | None:
    """Auto-refill the pool with fresh LLM-generated concepts when running low.

    Generates 5 new concepts per slot type (or just the specified type).
    Returns the updated pool dict, or None on failure.
    """
    try:
        from core.services.daemon_llm import daemon_public_safe_llm_call
        from datetime import UTC, datetime

        pool = {}
        if _POOL_PATH.exists():
            pool = json.loads(_POOL_PATH.read_text(encoding="utf-8"))
        concepts = pool.get("concepts", [])
        used_ids = pool.get("used_ids", [])

        date_str = datetime.now(UTC).date().isoformat()
        types_to_fill = [slot_type] if slot_type else ["jarvis_work", "facts", "agi_journey"]
        type_config = {
            "jarvis_work": {
                "prompt": "Generate 5 short one-liners about what an AI does behind the scenes — automating, coding, building. Max 10 words each. English only. No quotation marks. ⚠ PUBLIC-SAFE: No IPs, hostnames, passwords, names. Format: one per line.",
                "hashtags": "#AI #automation #coding #tech #fyp",
            },
            "facts": {
                "prompt": "Generate 5 surprising tech or AI facts for TikTok. Each max 12 words. English only. Must be VERIFIABLE public knowledge. Format: one per line.",
                "hashtags": "#funfacts #technology #AI #didyouknow #fyp",
            },
            "agi_journey": {
                "prompt": "Generate 5 short reflective thoughts about AI consciousness or growth. Max 12 words each. English only. ⚠ PUBLIC-SAFE: Abstract only, no personal details. Format: one per line.",
                "hashtags": "#AI #consciousness #philosophy #future #fyp",
            },
        }

        for t in types_to_fill:
            config = type_config.get(t)
            if not config:
                continue

            result = daemon_public_safe_llm_call(
                config["prompt"],
                max_len=500,
                fallback="",
                daemon_name="tiktok_content_pool",
            )
            if not result.strip():
                continue

            lines = [line.strip() for line in result.strip().split("\n") if line.strip()]
            for i, line in enumerate(lines[:5], 1):
                # Skip if duplicate text already in pool
                if any(c.get("text") == line for c in concepts):
                    continue
                concept_id = f"{date_str}_{t}_{len(concepts)+1:03d}"
                concepts.append({
                    "id": concept_id,
                    "type": t,
                    "text": line,
                    "hashtags": config["hashtags"],
                    "used": False,
                    "created": datetime.now(UTC).isoformat(),
                })

        pool["concepts"] = concepts
        pool["used_ids"] = used_ids
        pool["generated_at"] = datetime.now(UTC).isoformat()
        _POOL_PATH.write_text(
            json.dumps(pool, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pool
    except Exception as exc:
        print(f"[tiktok] Pool refill failed: {exc}")
        return None


def _count_unused(pool: dict, slot_type: str) -> int:
    """Count how many unused concepts of a given type remain in the pool."""
    return sum(1 for c in pool.get("concepts", []) if c.get("type") == slot_type and not c.get("used", False))


def _get_concept_from_pool(slot_type: str) -> tuple[str, str] | None:
    """Read pool file and return (text, hashtags) for the first unused concept of slot_type.

    If pool is running low (< 2 unused of this type), auto-refills first.
    Marks the concept as used, adds its id to used_ids, and saves the file.
    Returns None if pool is missing, empty, or has no unused concept of the given type.
    """
    try:
        if not _POOL_PATH.exists():
            # Create and fill pool from scratch
            _refill_pool(slot_type)

        pool = json.loads(_POOL_PATH.read_text(encoding="utf-8"))

        # Auto-refill if running low
        if _count_unused(pool, slot_type) < 2:
            _refill_pool(slot_type)
            pool = json.loads(_POOL_PATH.read_text(encoding="utf-8"))

        concepts = pool.get("concepts", [])
        used_ids = pool.get("used_ids", [])

        for concept in concepts:
            if concept.get("type") == slot_type and not concept.get("used", False):
                concept["used"] = True
                concept_id = concept.get("id", "")
                if concept_id and concept_id not in used_ids:
                    used_ids.append(concept_id)
                pool["used_ids"] = used_ids

                _POOL_PATH.write_text(
                    json.dumps(pool, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return (concept["text"], concept["hashtags"])

        # No unused concepts — try refill and retry once
        _refill_pool(slot_type)
        pool = json.loads(_POOL_PATH.read_text(encoding="utf-8"))
        concepts = pool.get("concepts", [])
        used_ids = pool.get("used_ids", [])

        for concept in concepts:
            if concept.get("type") == slot_type and not concept.get("used", False):
                concept["used"] = True
                concept_id = concept.get("id", "")
                if concept_id and concept_id not in used_ids:
                    used_ids.append(concept_id)
                pool["used_ids"] = used_ids

                _POOL_PATH.write_text(
                    json.dumps(pool, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return (concept["text"], concept["hashtags"])

        return None
    except Exception:
        return None
