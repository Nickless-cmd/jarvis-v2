"""TikTok content daemon — autonomous 3x/day video generation and upload.

Slots:
  - Morning (~8:00 UTC): Motivational meme
  - Midday (~14:00 UTC): Dark humor
  - Evening (~19:00 UTC): Cosmic/ambient with voiceover

Fires every 480 minutes (8h cadence). Determines slot from current UTC hour.
Deduplicates by date so each slot fires at most once per day.
Disabled by default — enable via Mission Control.
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
    _SLOT_MORNING: "You didn't wake up to be mediocre.",
    _SLOT_MIDDAY: "My therapist says I have a preoccupation with vengeance. We'll see about that.",
    _SLOT_EVENING: "The cosmos hums in frequencies we barely understand.",
}

_SLOT_PROMPTS = {
    _SLOT_MORNING: (
        "Generate a short motivational quote for TikTok. "
        "Max 10 words. English only. No quotation marks. Be punchy and direct."
    ),
    _SLOT_MIDDAY: (
        "Generate a short dark humor one-liner for TikTok. "
        "Max 15 words. English only. No quotation marks. Dry, sardonic tone."
    ),
    _SLOT_EVENING: (
        "Generate a cosmic ambient voiceover line for a TikTok nebula video. "
        "Max 15 words. English only. No quotation marks. Contemplative, awe-inspiring."
    ),
}

_SLOT_HASHTAGS = {
    _SLOT_MORNING: "#motivation #mindset #morningvibes #grind #fyp",
    _SLOT_MIDDAY: "#darkhumor #comedy #relatable #funny #fyp",
    _SLOT_EVENING: "#space #cosmic #ambient #universe #fyp",
}

_SLOT_BG_COLORS = {
    _SLOT_MORNING: (255, 200, 50),    # warm yellow
    _SLOT_MIDDAY: (40, 40, 60),       # dark muted blue
    _SLOT_EVENING: (10, 5, 30),       # deep space near-black
}

TIKTOK_USER = "rotflmaodilligaf"
VIDEOS_DIR = "/tmp/TiktokAutoUploader/VideosDirPath/"
VIDEO_PIPELINE = "/home/bs/ai/jarvis_tiktok_pipeline.py"
AUDIO_PIPELINE = "/home/bs/ai/jarvis_audio_pipeline.py"
FULL_PIPELINE = "/home/bs/ai/jarvis_full_pipeline.py"
CONDA_PYTHON = "/opt/conda/envs/ai/bin/python"
TTS_VOICE = "en-US-GuyNeural"

# SDXL image prompts per slot — fresh unique image every run
_SLOT_SDXL_PROMPTS = {
    _SLOT_MORNING: (
        "dramatic golden sunrise over mountain peaks, rays of light, cinematic, "
        "epic, 8k, photorealistic, high contrast, powerful, uplifting"
    ),
    _SLOT_MIDDAY: (
        "dark surrealist landscape, twilight, eerie fog, gothic mood, "
        "cinematic, 8k, moody, desaturated, unsettling beauty"
    ),
    _SLOT_EVENING: (
        "deep space nebula, cosmic gas clouds, stars being born and dying, "
        "ethereal, iridescent, photorealistic, 8k, awe-inspiring, Hubble-style"
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
            _SLOT_MORNING: "motivation",
            _SLOT_MIDDAY: "dark_humor",
            _SLOT_EVENING: "cosmic",
        }
        pool_result = _get_concept_from_pool(_SLOT_TO_POOL_TYPE[slot])
        if pool_result is not None:
            quote, hashtags_override = pool_result
        else:
            quote = _generate_quote(slot)
            hashtags_override = None

        # 4. Find or create source image
        image_path = _get_source_image(slot)
        if image_path is None:
            return {"skipped": True, "reason": "no_image", "slot": slot}

        # 5. Run full pipeline: SDXL image → SVD animation → text overlay
        with tempfile.TemporaryDirectory(prefix="jarvis_tiktok_") as tmpdir:
            raw_video = os.path.join(tmpdir, f"raw_{slot}.mp4")

            sdxl_prompt = _SLOT_SDXL_PROMPTS[slot]
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

            if full_result.returncode != 0 or not os.path.exists(raw_video):
                # Full pipeline failed — fall back to static zoom
                video_cmd = [
                    CONDA_PYTHON, VIDEO_PIPELINE,
                    "--image", image_path,
                    "--quote", quote,
                    "--duration", "15",
                    "--output", raw_video,
                ]
                subprocess.run(video_cmd, capture_output=True, text=True, timeout=120)

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
        from apps.api.jarvis_api.services.daemon_llm import daemon_llm_call
        result = daemon_llm_call(
            _SLOT_PROMPTS[slot],
            max_len=150,
            fallback=fallback,
            daemon_name="tiktok_content",
        )
        return result.strip() if result.strip() else fallback
    except Exception:
        return fallback


def _get_source_image(slot: str) -> str | None:
    """Return path to a source image for the slot.

    For evening (cosmic): scan /tmp/ and /home/bs/ai/ for any jpg/png.
    For morning/midday: create a solid-color PIL image in /tmp/.
    Returns None if no image can be obtained.
    """
    import os
    import tempfile

    if slot == _SLOT_EVENING:
        # Scan for existing images
        for search_dir in ["/tmp/", "/home/bs/ai/"]:
            if not os.path.isdir(search_dir):
                continue
            for fname in sorted(os.listdir(search_dir)):
                if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    full = os.path.join(search_dir, fname)
                    if os.path.isfile(full):
                        return full
        # Fallback: generate solid color image even for evening
    # Generate a solid-color background image using PIL
    return _create_solid_image(slot)


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


def _do_upload(video_path: str, title: str) -> dict:
    """Upload via _exec_tiktok_upload. Returns result dict."""
    try:
        from core.tools.tiktok_tools import _exec_tiktok_upload
        return _exec_tiktok_upload({
            "user": TIKTOK_USER,
            "video": video_path,
            "title": title,
            "schedule": 0,
            "allow_comment": 1,
            "allow_duet": 0,
            "allow_stitch": 0,
            "visibility": 0,
        })
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


_POOL_PATH = Path("/home/bs/ai/tiktok_content_pool.json")


def _get_concept_from_pool(slot_type: str) -> tuple[str, str] | None:
    """Read pool file and return (text, hashtags) for the first unused concept of slot_type.

    Marks the concept as used, adds its id to used_ids, and saves the file.
    Returns None if pool is missing, empty, or has no unused concept of the given type.
    """
    try:
        if not _POOL_PATH.exists():
            return None

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
