"""Pollinations.ai tools — free, no-auth image + video generation.

Pollinations is a URL-based gen-AI API: a GET request returns an image or
video bytes. No key, no account, no RAM footprint on SRVLAB — all heavy
compute happens on their end. Perfect for the TikTok content pipeline
where ComfyUI was eating local memory.

Endpoints used:
- https://image.pollinations.ai/prompt/{URL-encoded prompt}
  Optional query params: width, height, model, seed, nologo, enhance
  Models: flux, turbo (fastest), variation, anime
- https://text.pollinations.ai/{URL-encoded prompt}
  (Text only — we skip it; Jarvis has better text lanes)

Video: Pollinations' video path is still beta / not URL-GET-shaped in
public docs. We expose a placeholder that errors cleanly so Jarvis can
try it but not silently fail.

All images are saved into the workspace under
~/.jarvis-v2/shared/memory/generated/ with a short metadata
JSON sidecar.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_IMAGE_ENDPOINT = "https://image.pollinations.ai/prompt"
_VIDEO_ENDPOINT = "https://gen.pollinations.ai/video"
_GENERATED_REL = "memory/generated"
_VIDEO_REL = "memory/generated/video"
_DEFAULT_MODEL = "flux"  # Options: flux, turbo, variation, anime
_ALLOWED_MODELS = ("flux", "turbo", "variation", "anime")
_DEFAULT_VIDEO_MODEL = "wan-fast"
#: Maalt mod `gen.pollinations.ai/video/models` 28/9-2026. To navne i den
#: gamle liste fandtes ikke laengere: `seedance` og `ltx-2`. Vaelger man et
#: ukendt navn, falder koden TAVST tilbage til standardmodellen — saa hvis
#: Jarvis bad om `ltx-2`, fik han `wan-fast` uden at nogen sagde noget, og
#: resultatet var bare «en anden video end forventet».
#:
#: Fallbacken bliver staaende: et ukendt navn maa ikke vaelte en tur. Men saa
#: skal listen til gengaeld vaere sand. Maal den igen naar du bruger den:
#:     curl -s https://gen.pollinations.ai/video/models | jq -r '.[].aliases[]?'
_ALLOWED_VIDEO_MODELS = (
    # de syv fra den gamle liste der stadig svarer
    "veo", "seedance-pro", "wan", "wan-fast",
    "grok-video-pro", "p-video", "nova-reel",
    # nyere modeller kataloget har faaet siden
    "wan-2.7", "wan-3.0", "seedance-2.0", "seedance-2.5",
    "minimax-h3", "grok-imagine-video-1.5", "happyhorse",
)
#: De modeller der FAKTISK kan tage en video ind. Maalt mod
#: `gen.pollinations.ai/video/models` 28/9-2026: af nitten video-modeller
#: oplyser fem `reference_videos` i deres `video_capabilities`. De oevrige
#: fjorten kan kun start-/slutbillede. Vaelger man en af dem, ville
#: `reference_videos` blive ignoreret TAVST, og man ville faa en helt ny video
#: der intet havde med originalen at goere.
_VIDEO_EDIT_MODELS = (
    "wan-2.7", "wan-3.0", "seedance-2.0", "seedance-2.5", "minimax/minimax-h3-max",
)
#: `wan-2.7` er valgt som standard fordi den er den eneste af de fem med et
#: 1080p-alias og det bredeste sæt aliaser i kataloget.
_DEFAULT_VIDEO_EDIT_MODEL = "wan-2.7"

_DEFAULT_WIDTH = 1024
_DEFAULT_HEIGHT = 1024
_MAX_WIDTH = 2048
_MAX_HEIGHT = 2048
_REQUEST_TIMEOUT = 120
_VIDEO_TIMEOUT = 600  # video generation takes longer
_USER_AGENT = "Jarvis-v2/pollinations-tool"


def _api_key() -> str | None:
    """Read pollinations API key from runtime.json (never hardcoded)."""
    try:
        from core.runtime.secrets import read_runtime_key
        key = read_runtime_key("pollinations_api_key")
        if key:
            return str(key)
    except Exception:
        pass
    return None


def _auth_headers() -> dict[str, str]:
    headers: dict[str, str] = {"User-Agent": _USER_AGENT}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _generated_dir() -> Path:
    from core.runtime.workspace_paths import shared_dir
    return shared_dir() / _GENERATED_REL


def _video_dir() -> Path:
    from core.runtime.workspace_paths import shared_dir
    return shared_dir() / _VIDEO_REL


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _safe_filename(prompt: str, gen_id: str, ext: str) -> str:
    # Slug the prompt into a short filename token
    import re
    slug = re.sub(r"[^a-zA-Z0-9æøåÆØÅ_-]+", "-", prompt.strip())[:60]
    slug = re.sub(r"-+", "-", slug).strip("-") or "image"
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{slug}-{gen_id[-6:]}{ext}"


def _write_sidecar(image_path: Path, metadata: dict[str, Any]) -> None:
    try:
        sidecar = image_path.with_suffix(image_path.suffix + ".json")
        with sidecar.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.debug("pollinations_tools: sidecar write failed: %s", exc)


def generate_image(
    *,
    prompt: str,
    model: str = _DEFAULT_MODEL,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    seed: int | None = None,
    nologo: bool = True,
    enhance: bool = False,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """Fetch an image from Pollinations and save to disk. Returns result dict."""
    if not prompt or not str(prompt).strip():
        return {"status": "error", "text": "prompt is empty"}

    if model not in _ALLOWED_MODELS:
        model = _DEFAULT_MODEL

    width = _clamp(width, 256, _MAX_WIDTH)
    height = _clamp(height, 256, _MAX_HEIGHT)

    encoded = urllib.parse.quote(prompt.strip(), safe="")
    params: dict[str, str] = {
        "model": model,
        "width": str(width),
        "height": str(height),
    }
    if seed is not None:
        params["seed"] = str(int(seed))
    if nologo:
        params["nologo"] = "true"
    if enhance:
        params["enhance"] = "true"
    qs = urllib.parse.urlencode(params)
    url = f"{_IMAGE_ENDPOINT}/{encoded}?{qs}"

    gen_id = f"gen-{uuid4().hex[:12]}"
    target_dir = save_dir or _generated_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return {"status": "error", "text": f"could not create dir: {exc}"}

    req = urllib.request.Request(url, headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            data = resp.read()
    except Exception as exc:
        return {"status": "error", "text": f"fetch failed: {exc}", "url": url}

    # Determine extension from content-type
    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"

    filename = _safe_filename(prompt, gen_id, ext)
    path = target_dir / filename
    try:
        path.write_bytes(data)
    except Exception as exc:
        return {"status": "error", "text": f"write failed: {exc}"}

    metadata = {
        "generation_id": gen_id,
        "prompt": prompt,
        "model": model,
        "width": width,
        "height": height,
        "seed": seed,
        "enhance": enhance,
        "nologo": nologo,
        "url": url,
        "content_type": content_type,
        "bytes": len(data),
        "created_at": datetime.now(UTC).isoformat(),
        "provider": "pollinations.ai",
    }
    _write_sidecar(path, metadata)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "pollinations.image_generated",
            {
                "generation_id": gen_id,
                "model": model,
                "path": str(path),
                "bytes": len(data),
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "generation_id": gen_id,
        "path": str(path),
        "bytes": len(data),
        "content_type": content_type,
        "model": model,
        "width": width,
        "height": height,
    }


# ---------------------------------------------------------------------------
# Tool executors (Ollama-compatible)
# ---------------------------------------------------------------------------


def _exec_pollinations_image(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}

    model = str(args.get("model") or _DEFAULT_MODEL).lower().strip()
    try:
        width = int(args.get("width") or _DEFAULT_WIDTH)
    except Exception:
        width = _DEFAULT_WIDTH
    try:
        height = int(args.get("height") or _DEFAULT_HEIGHT)
    except Exception:
        height = _DEFAULT_HEIGHT
    seed = args.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except Exception:
            seed = None
    nologo = bool(args.get("nologo", True))
    enhance = bool(args.get("enhance", False))

    result = generate_image(
        prompt=prompt, model=model, width=width, height=height,
        seed=seed, nologo=nologo, enhance=enhance,
    )
    if result.get("status") == "ok":
        # GØR DET SYNLIGT. Filen blev skrevet til workspace'et og var dermed
        # usynlig for enhver klient: målt 12/9-2026 havde de 392
        # assistent-beskeder med billed-blokke NUL af typen `image`, og alle
        # 72 rækker i channel_attachments var uploads. Jarvis kunne lave et
        # billede man aldrig kunne se.
        #
        # Fejler registreringen, svarer værktøjet præcis som før — en
        # genereret fil må ikke gå tabt fordi et opslag ikke kunne skrives.
        attachment_id = ""
        try:
            from core.services.attachment_service import register_generated_image
            attachment_id = register_generated_image(
                local_path=str(result.get("path") or ""),
                mime_type=str(result.get("content_type") or "image/jpeg"),
                source_url=str(result.get("url") or ""),
            )
        except Exception:
            attachment_id = ""
        # LÆG DET PÅ TUREN. Registreringen alene gør billedet hentbart, men
        # INGEN besked bar en reference til det — og klienten renderer efter
        # blokke, så det var usynligt i tråden. Samme «læg og tag»-mønster som
        # publish_file: her lægges posten, visible_runs_outcomes tager den når
        # svaret persisteres. Referencen er attachment_id (user-scopet
        # /attachments/image/{id}), ikke en /files/-adresse.
        try:
            from core.services.published_files import note as _note
            _sti = str(result.get("path") or "")
            _note(
                str(args.get("_runtime_turn_id") or args.get("_runtime_run_id") or ""),
                filename=_sti.replace("\\", "/").rsplit("/", 1)[-1] or "billede",
                mime_type=str(result.get("content_type") or "image/jpeg"),
                size_bytes=int(result.get("bytes") or 0),
                attachment_id=attachment_id,
                # Ankeret der bestemmer HVOR i traaden billedet lander.
                # `_indsaet_ved_deres_vaerktoej` matcher det mod progress-
                # blokkens id. Uden det havnede pollinations-billeder BAGEST,
                # efter prosaen — praecis den fejl openrouter_image fik rettet
                # 13/9-2026, og som blev glemt her. Fundet 28/9 mens video fik
                # samme behandling.
                tool_use_id=str(args.get("_runtime_tool_use_id") or ""),
            )
        except Exception:
            pass
        return {
            "status": "ok",
            "text": (
                f"Image generated ({result['bytes']} bytes, {result['content_type']}) "
                f"saved to {result['path']}"
            ),
            **result,
            "attachment_id": attachment_id,
        }
    return result


def generate_video(
    *,
    prompt: str,
    model: str = _DEFAULT_VIDEO_MODEL,
    duration: int | None = None,
    aspect_ratio: str | None = None,
    audio: bool = False,
    image_url: str | None = None,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate a video via pollinations.ai. Requires pollinations_api_key
    in runtime.json. Returns saved MP4 path + metadata.
    """
    if not prompt or not str(prompt).strip():
        return {"status": "error", "text": "prompt is empty"}
    if not _api_key():
        return {
            "status": "error",
            "text": "pollinations_api_key missing from runtime.json — video requires auth",
        }
    if model not in _ALLOWED_VIDEO_MODELS:
        model = _DEFAULT_VIDEO_MODEL

    encoded = urllib.parse.quote(prompt.strip(), safe="")
    params: dict[str, str] = {"model": model}
    if duration is not None:
        try:
            params["duration"] = str(int(duration))
        except Exception:
            pass
    if aspect_ratio:
        params["aspectRatio"] = str(aspect_ratio)
    if audio:
        params["audio"] = "true"
    if image_url:
        params["image"] = str(image_url)
    qs = urllib.parse.urlencode(params)
    url = f"{_VIDEO_ENDPOINT}/{encoded}?{qs}"

    return _hent_video(url=url, model=model, prompt=prompt, save_dir=save_dir)


def _hent_video(*, url: str, model: str, prompt: str,
                save_dir: Path | None = None) -> dict[str, Any]:
    """Hent, gem og beskriv en video. Faelles for generering og redigering.

    Udskilt 28/9-2026 da `edit_video` kom til: de to bygger hver sin URL og
    goer PRAECIS det samme derefter. En kopi ville have vaeret to steder at
    rette naeste gang et felt skifter navn.
    """
    gen_id = f"vid-{uuid4().hex[:12]}"
    target_dir = save_dir or _video_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return {"status": "error", "text": f"could not create dir: {exc}"}

    req = urllib.request.Request(url, headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=_VIDEO_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "video/mp4")
            data = resp.read()
    except Exception as exc:
        return {"status": "error", "text": f"video fetch failed: {exc}", "url": url}

    if not data or len(data) < 1024:
        return {
            "status": "error",
            "text": f"response too small ({len(data)} bytes) — model may be rate-limited or prompt rejected",
            "content_type": content_type,
        }

    ext = ".mp4"
    if "webm" in content_type:
        ext = ".webm"
    elif "quicktime" in content_type or "mov" in content_type:
        ext = ".mov"

    filename = _safe_filename(prompt, gen_id, ext)
    path = target_dir / filename
    try:
        path.write_bytes(data)
    except Exception as exc:
        return {"status": "error", "text": f"write failed: {exc}"}

    metadata = {
        "generation_id": gen_id,
        "prompt": prompt,
        "model": model,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "audio": audio,
        "image_reference": image_url,
        "url": url,
        "content_type": content_type,
        "bytes": len(data),
        "created_at": datetime.now(UTC).isoformat(),
        "provider": "pollinations.ai",
        "kind": "video",
    }
    _write_sidecar(path, metadata)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "pollinations.video_generated",
            {
                "generation_id": gen_id,
                "model": model,
                "path": str(path),
                "bytes": len(data),
                "duration": duration,
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "generation_id": gen_id,
        "path": str(path),
        "bytes": len(data),
        "content_type": content_type,
        "model": model,
    }


def _registrer_video(result: dict[str, Any], args: dict[str, Any], *,
                     hvad: str = "Video generated") -> dict[str, Any]:
    """Goer videoen synlig: registrér den, og laeg den paa turen.

    Faelles for generering og redigering — begge skal ende i traaden, og
    ingen af dem maa gaa tabt fordi et opslag fejlede. Ved op til ti
    minutters arbejde er det ikke en teoretisk bekymring.
    """
    attachment_id = ""
    try:
        from core.services.attachment_service import register_generated_media
        attachment_id = register_generated_media(
            local_path=str(result.get("path") or ""),
            mime_type=str(result.get("content_type") or "video/mp4"),
            source_url=str(result.get("url") or ""),
        )
    except Exception:  # registreringen maa ALDRIG koste en generering der tog
        # op til ti minutter. Tomt id er aerligt: klienten faar stien.
        attachment_id = ""
    try:
        from core.services.published_files import note as _note
        _sti = str(result.get("path") or "")
        _note(
            str(args.get("_runtime_turn_id") or args.get("_runtime_run_id") or ""),
            filename=_sti.replace("\\", "/").rsplit("/", 1)[-1] or "video",
            mime_type=str(result.get("content_type") or "video/mp4"),
            size_bytes=int(result.get("bytes") or 0),
            attachment_id=attachment_id,
            # Ankeret der bestemmer HVOR i traaden den lander.
            # `_indsaet_ved_deres_vaerktoej` matcher det mod progress-blokkens
            # id; uden det ryger videoen bagest, efter prosaen — praecis den
            # fejl billederne havde indtil 13/9-2026.
            tool_use_id=str(args.get("_runtime_tool_use_id") or ""),
        )
    except Exception:  # samme grund: posten er hvordan videoen naar traaden,
        # men filen findes uanset om posten kunne skrives.
        pass
    return {
        "status": "ok",
        "text": (
            f"{hvad} ({result['bytes']} bytes, {result['content_type']}, "
            f"model={result['model']}) saved to {result['path']}"
        ),
        **result,
        "attachment_id": attachment_id,
    }


def edit_video(
    *,
    prompt: str,
    video_url: str,
    model: str = _DEFAULT_VIDEO_EDIT_MODEL,
    duration: int | None = None,
    aspect_ratio: str | None = None,
    audio: bool = False,
) -> dict[str, Any]:
    """Lav en NY video ud fra en eksisterende + en instruktion.

    ## Hvad der faktisk er muligt (maalt 28/9-2026)

    Pollinations' video-endpoint tager `reference_videos`: «public HTTP(S)
    video URLs for motion or style guidance». Fem af nitten video-modeller
    oplyser den evne i deres `video_capabilities`; de oevrige fjorten kan kun
    start- og slutbillede.

    ## Den graense der betyder noget

    Ordet er **public**. Udbyderen henter selv videoen over nettet. Jarvis'
    egne videoer ligger bag `/attachments/` og `/files/`, og begge svarede
    401 uden token da det blev maalt paa CT105 samme dag — der er ingen
    offentlig base-URL konfigureret. Derfor kan dette vaerktoej i dag redigere
    en video fra nettet, men IKKE en Jarvis lige selv har lavet.

    Det loeses ikke her: at give en genereret fil en offentlig adresse er en
    sikkerhedsbeslutning, ikke en teknisk detalje. Vaerktoejet siger det derfor
    tydeligt frem for at sende en adresse udbyderen faar 401 paa — den ville
    ellers svare med en helt ny video der intet havde med originalen at goere,
    og det ligner et resultat.
    """
    if not _api_key():
        return {
            "status": "error",
            "text": "pollinations_api_key missing from runtime.json — video requires auth",
        }
    kilde = str(video_url or "").strip()
    if not kilde:
        return {"status": "error", "text": "video_url required"}
    if not kilde.lower().startswith(("http://", "https://")):
        return {
            "status": "error",
            "text": (
                "video_url skal vaere en OFFENTLIG http(s)-adresse. Udbyderen henter "
                "selv videoen, saa en lokal sti eller en /attachments/-adresse virker "
                "ikke — de kraever token. En video du selv lige har genereret kan "
                "derfor ikke redigeres endnu."
            ),
        }
    if model not in _VIDEO_EDIT_MODELS:
        model = _DEFAULT_VIDEO_EDIT_MODEL

    params: dict[str, str] = {"model": model, "reference_videos": kilde}
    if duration is not None:
        params["duration"] = str(duration)
    if aspect_ratio:
        params["aspectRatio"] = str(aspect_ratio)
    if audio:
        params["audio"] = "true"
    encoded = urllib.parse.quote(prompt.strip(), safe="")
    url = f"{_VIDEO_ENDPOINT}/{encoded}?{urllib.parse.urlencode(params)}"
    return _hent_video(url=url, model=model, prompt=prompt)


def _exec_pollinations_video_edit(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}
    duration = args.get("duration")
    if duration is not None:
        try:
            duration = int(duration)
        except Exception:  # en ulaeselig varighed er ikke vaerd at afvise paa —
            # udbyderen har sin egen standard pr. model.
            duration = None
    result = edit_video(
        prompt=prompt,
        video_url=str(args.get("video_url") or args.get("video") or ""),
        model=str(args.get("model") or _DEFAULT_VIDEO_EDIT_MODEL).lower().strip(),
        duration=duration,
        aspect_ratio=str(args.get("aspect_ratio") or args.get("aspectRatio") or "") or None,
        audio=bool(args.get("audio", False)),
    )
    if result.get("status") == "ok":
        return _registrer_video(result, args, hvad="Video edited")
    return result


def _exec_pollinations_video(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}
    model = str(args.get("model") or _DEFAULT_VIDEO_MODEL).lower().strip()
    duration = args.get("duration")
    if duration is not None:
        try:
            duration = int(duration)
        except Exception:
            duration = None
    aspect_ratio = args.get("aspect_ratio") or args.get("aspectRatio")
    audio = bool(args.get("audio", False))
    image_url = args.get("image_url") or args.get("image")

    result = generate_video(
        prompt=prompt,
        model=model,
        duration=duration,
        aspect_ratio=str(aspect_ratio) if aspect_ratio else None,
        audio=audio,
        image_url=str(image_url) if image_url else None,
    )
    if result.get("status") == "ok":
        # SAMME BEHANDLING SOM BILLEDER. Indtil 28/9-2026 gjorde denne gren
        # ingen af de to ting billed-grenen goer: filen blev hverken
        # registreret eller lagt paa turen. En video Jarvis lavede kunne
        # derfor aldrig naa traaden.
        return _registrer_video(result, args)
    return result


POLLINATIONS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "pollinations_image",
            "description": (
                "Generate a free image via pollinations.ai (no API key, no RAM cost). "
                "Ideal for TikTok content when ComfyUI is too heavy. Returns saved "
                "image path. Models: flux (default, best quality), turbo (fastest), "
                "variation, anime."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt describing the image.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model: flux | turbo | variation | anime. Default: flux.",
                    },
                    "width": {
                        "type": "integer",
                        "description": "Width in pixels (256-2048). Default 1024.",
                    },
                    "height": {
                        "type": "integer",
                        "description": "Height in pixels (256-2048). Default 1024.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional seed for reproducibility.",
                    },
                    "nologo": {
                        "type": "boolean",
                        "description": "Remove pollinations watermark. Default true.",
                    },
                    "enhance": {
                        "type": "boolean",
                        "description": "Enable LLM prompt enhancement. Default false.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pollinations_video",
            "description": (
                "Generate a text-to-video via pollinations.ai (requires API key in "
                "runtime.json). Returns saved MP4 path. Models: wan-fast (default, "
                "fast), wan, wan-2.7, wan-3.0, seedance-pro, seedance-2.0, "
                "seedance-2.5, veo (Google), minimax-h3, grok-video-pro, "
                "grok-imagine-video-1.5, p-video, nova-reel, happyhorse. "
                "Optionally pass image_url to seed image-to-video."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt describing the video.",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "wan-fast (default) | wan | wan-2.7 | wan-3.0 | "
                            "seedance-pro | seedance-2.0 | seedance-2.5 | veo | "
                            "minimax-h3 | grok-video-pro | grok-imagine-video-1.5 | "
                            "p-video | nova-reel | happyhorse"
                        ),
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Video length in seconds (model-dependent; try 4-8).",
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "e.g. '16:9', '9:16' for TikTok/shorts, '1:1'.",
                    },
                    "audio": {
                        "type": "boolean",
                        "description": "Include generated soundtrack. Default false.",
                    },
                    "image_url": {
                        "type": "string",
                        "description": "Optional URL of a reference image for image-to-video.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pollinations_video_edit",
            "description": (
                "Edit an EXISTING video with an instruction (video-to-video). "
                "IMPORTANT: video_url must be a PUBLIC http(s) URL — the provider "
                "fetches it itself. A video you just generated is stored behind "
                "authentication and CANNOT be used yet; say so instead of guessing. "
                "Models that support this: wan-2.7 (default), wan-3.0, seedance-2.0, "
                "seedance-2.5, minimax/minimax-h3-max. Other video models silently "
                "ignore the reference and return an unrelated video."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "What to change about the video.",
                    },
                    "video_url": {
                        "type": "string",
                        "description": "PUBLIC http(s) URL of the video to edit.",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "wan-2.7 (default) | wan-3.0 | seedance-2.0 | "
                            "seedance-2.5 | minimax/minimax-h3-max"
                        ),
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Length in seconds (model-dependent).",
                    },
                    "aspect_ratio": {"type": "string", "description": "e.g. '16:9'."},
                    "audio": {"type": "boolean", "description": "Generated soundtrack."},
                },
                "required": ["prompt", "video_url"],
            },
        },
    },
]
