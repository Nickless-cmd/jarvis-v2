"""Hugging Face Inference API tools — free-tier text-to-video + fallback image gen.

HF's serverless inference API gives free access (rate-limited, ~200-500
requests/hour on free tier) to warm text-to-video models including:
- Lightricks/LTX-Video — fast, good motion adherence
- Lightricks/LTX-Video-0.9.8-13B-distilled — fastest distilled variant
- tencent/HunyuanVideo — highest quality, slower

Auth: requires huggingface_token in runtime.json. Never hardcoded.

This complements pollinations_tools.py:
- Use pollinations_image for free unlimited images (no auth needed for
  basic, faster with auth)
- Use hf_text_to_video for genuinely-free video generation (rate-limited)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_HF_BASE = "https://router.huggingface.co/hf-inference/models"
_VIDEO_REL = "workspaces/default/memory/generated/video"
_DEFAULT_VIDEO_MODEL = "Lightricks/LTX-Video-0.9.8-13B-distilled"
_ALLOWED_VIDEO_MODELS = (
    "Lightricks/LTX-Video-0.9.8-13B-distilled",
    "Lightricks/LTX-Video",
    "tencent/HunyuanVideo",
)
_REQUEST_TIMEOUT = 600  # inference can queue on free tier
_USER_AGENT = "Jarvis-v2/hf-inference"


def _hf_token() -> str | None:
    """Read HF token from runtime.json (never hardcoded)."""
    try:
        from core.runtime.secrets import read_runtime_key
        key = read_runtime_key("huggingface_token")
        if key:
            return str(key)
    except Exception:
        pass
    return None


def _auth_headers() -> dict[str, str]:
    headers: dict[str, str] = {
        "User-Agent": _USER_AGENT,
        "Content-Type": "application/json",
    }
    token = _hf_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _video_dir() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _VIDEO_REL


def _safe_filename(prompt: str, gen_id: str, ext: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9æøåÆØÅ_-]+", "-", prompt.strip())[:60]
    slug = re.sub(r"-+", "-", slug).strip("-") or "video"
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{slug}-{gen_id[-6:]}{ext}"


def _write_sidecar(path: Path, metadata: dict[str, Any]) -> None:
    try:
        sidecar = path.with_suffix(path.suffix + ".json")
        with sidecar.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.debug("hf_inference_tools: sidecar write failed: %s", exc)


def generate_video(
    *,
    prompt: str,
    model: str = _DEFAULT_VIDEO_MODEL,
    num_frames: int | None = None,
    guidance_scale: float | None = None,
    negative_prompt: str | None = None,
    num_inference_steps: int | None = None,
    seed: int | None = None,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate a video via HF serverless inference API."""
    if not prompt or not str(prompt).strip():
        return {"status": "error", "text": "prompt is empty"}
    if not _hf_token():
        return {
            "status": "error",
            "text": "huggingface_token missing from runtime.json",
        }
    if model not in _ALLOWED_VIDEO_MODELS:
        model = _DEFAULT_VIDEO_MODEL

    parameters: dict[str, Any] = {}
    if num_frames is not None:
        parameters["num_frames"] = int(num_frames)
    if guidance_scale is not None:
        parameters["guidance_scale"] = float(guidance_scale)
    if negative_prompt:
        parameters["negative_prompt"] = [str(negative_prompt)]
    if num_inference_steps is not None:
        parameters["num_inference_steps"] = int(num_inference_steps)
    if seed is not None:
        parameters["seed"] = int(seed)

    payload: dict[str, Any] = {"inputs": prompt.strip()}
    if parameters:
        payload["parameters"] = parameters

    url = f"{_HF_BASE}/{model}"
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=_auth_headers(), method="POST")
    gen_id = f"hfvid-{uuid4().hex[:12]}"
    target_dir = save_dir or _video_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return {"status": "error", "text": f"could not create dir: {exc}"}

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "video/mp4")
            data = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {
            "status": "error",
            "text": f"HF HTTP {exc.code}: {err_body}",
            "url": url,
        }
    except Exception as exc:
        return {"status": "error", "text": f"HF fetch failed: {exc}", "url": url}

    if not data or len(data) < 1024:
        return {
            "status": "error",
            "text": f"response too small ({len(data)} bytes)",
            "content_type": content_type,
        }

    # Infer extension
    ext = ".mp4"
    if "webm" in content_type:
        ext = ".webm"
    elif "image" in content_type:
        ext = ".gif"  # some text-to-video models return animated GIF

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
        "parameters": parameters,
        "url": url,
        "content_type": content_type,
        "bytes": len(data),
        "created_at": datetime.now(UTC).isoformat(),
        "provider": "huggingface",
        "kind": "video",
    }
    _write_sidecar(path, metadata)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "hf_inference.video_generated",
            "payload": {
                "generation_id": gen_id,
                "model": model,
                "path": str(path),
                "bytes": len(data),
            },
        })
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


def _exec_hf_text_to_video(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}
    model = str(args.get("model") or _DEFAULT_VIDEO_MODEL).strip()
    num_frames = args.get("num_frames")
    if num_frames is not None:
        try:
            num_frames = int(num_frames)
        except Exception:
            num_frames = None
    guidance_scale = args.get("guidance_scale")
    if guidance_scale is not None:
        try:
            guidance_scale = float(guidance_scale)
        except Exception:
            guidance_scale = None
    negative = args.get("negative_prompt")
    steps = args.get("num_inference_steps")
    if steps is not None:
        try:
            steps = int(steps)
        except Exception:
            steps = None
    seed = args.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except Exception:
            seed = None

    result = generate_video(
        prompt=prompt,
        model=model,
        num_frames=num_frames,
        guidance_scale=guidance_scale,
        negative_prompt=str(negative) if negative else None,
        num_inference_steps=steps,
        seed=seed,
    )
    if result.get("status") == "ok":
        return {
            "status": "ok",
            "text": (
                f"HF video generated ({result['bytes']} bytes, {result['content_type']}, "
                f"model={result['model']}) saved to {result['path']}"
            ),
            **result,
        }
    return result


# ─── Speech-to-text (Whisper) ──────────────────────────────────────────

_ASR_DEFAULT_MODEL = "openai/whisper-large-v3"
_ASR_ALLOWED_MODELS = (
    "openai/whisper-large-v3",
    "openai/whisper-large-v3-turbo",
    "openai/whisper-base",
)


def _read_audio_bytes(source: str) -> bytes:
    """Read audio from a local path or HTTP(S) URL. Returns raw bytes."""
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            return resp.read()
    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"audio file not found: {path}")
    return path.read_bytes()


def transcribe_audio(
    *,
    audio_source: str,
    model: str = _ASR_DEFAULT_MODEL,
    return_timestamps: bool = False,
    language: str | None = None,
) -> dict[str, Any]:
    """Transcribe audio via HF Whisper. audio_source can be file path or URL."""
    if not _hf_token():
        return {"status": "error", "text": "huggingface_token missing from runtime.json"}
    if model not in _ASR_ALLOWED_MODELS:
        model = _ASR_DEFAULT_MODEL

    try:
        audio_bytes = _read_audio_bytes(audio_source)
    except Exception as exc:
        return {"status": "error", "text": f"could not read audio: {exc}"}
    if not audio_bytes:
        return {"status": "error", "text": "audio payload empty"}

    url = f"{_HF_BASE}/{model}"
    headers = {
        "Authorization": f"Bearer {_hf_token()}",
        "User-Agent": _USER_AGENT,
        "Content-Type": "application/octet-stream",
    }
    # When sending raw bytes we can also pass parameters via query-string-like
    # pattern. Simplest: send raw bytes body, parameters via JSON wrapper.
    # HF accepts raw bytes OR JSON. We use JSON for parameter support.
    import base64
    payload: dict[str, Any] = {
        "inputs": base64.b64encode(audio_bytes).decode("ascii"),
    }
    params: dict[str, Any] = {}
    if return_timestamps:
        params["return_timestamps"] = True
    if language:
        # Whisper respects language via generation_parameters.language
        params.setdefault("generation_parameters", {})["language"] = str(language)
    if params:
        payload["parameters"] = params

    body = json.dumps(payload).encode("utf-8")
    headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {"status": "error", "text": f"HF HTTP {exc.code}: {err_body}"}
    except Exception as exc:
        return {"status": "error", "text": f"ASR fetch failed: {exc}"}

    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "text": f"parse failed: {exc}"}

    text = str(data.get("text") or "").strip()
    chunks = data.get("chunks") if return_timestamps else None

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "hf_inference.transcribed",
            "payload": {
                "model": model,
                "chars": len(text),
                "source": audio_source[:200],
                "has_timestamps": bool(chunks),
            },
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "text": text,
        "chunks": chunks,
        "model": model,
        "bytes_in": len(audio_bytes),
    }


def _exec_hf_transcribe_audio(args: dict[str, Any]) -> dict[str, Any]:
    source = str(args.get("audio_source") or args.get("path") or args.get("url") or "").strip()
    if not source:
        return {"status": "error", "text": "audio_source required (path or URL)"}
    model = str(args.get("model") or _ASR_DEFAULT_MODEL).strip()
    return_timestamps = bool(args.get("return_timestamps", False))
    language = args.get("language")
    result = transcribe_audio(
        audio_source=source, model=model,
        return_timestamps=return_timestamps,
        language=str(language) if language else None,
    )
    if result.get("status") == "ok":
        preview = result["text"][:200]
        return {
            "status": "ok",
            "text": f"Transcribed ({len(result['text'])} chars): {preview}",
            **result,
        }
    return result


# ─── Embeddings (feature extraction) ───────────────────────────────────

_EMBED_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_EMBED_ALLOWED_MODELS = (
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2",
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-large-en-v1.5",
    "intfloat/multilingual-e5-base",
    "intfloat/multilingual-e5-large",
)


def semantic_similarity(
    *,
    source: str,
    candidates: list[str],
    model: str = _EMBED_DEFAULT_MODEL,
) -> dict[str, Any]:
    """Compute cosine similarity between source and each candidate via HF.

    HF-inference's free tier mounts sentence-transformers under the
    sentence-similarity pipeline which returns scores directly — we embrace
    that shape rather than trying to extract raw vectors (which isn't free).
    """
    if not _hf_token():
        return {"status": "error", "text": "huggingface_token missing from runtime.json"}
    if not source or not candidates:
        return {"status": "error", "text": "source and candidates required"}
    if model not in _EMBED_ALLOWED_MODELS:
        model = _EMBED_DEFAULT_MODEL

    clean = [str(c) for c in candidates if str(c).strip()]
    if not clean:
        return {"status": "error", "text": "all candidates empty"}

    url = f"{_HF_BASE}/{model}"
    payload = {
        "inputs": {
            "source_sentence": str(source),
            "sentences": clean,
        }
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=_auth_headers(), method="POST")

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {"status": "error", "text": f"HF HTTP {exc.code}: {err_body}"}
    except Exception as exc:
        return {"status": "error", "text": f"similarity fetch failed: {exc}"}

    try:
        scores = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "text": f"parse failed: {exc}"}

    if not isinstance(scores, list):
        return {"status": "error", "text": f"unexpected shape: {type(scores).__name__}"}

    ranked = [
        {"candidate": c, "score": round(float(s), 4)}
        for c, s in zip(clean, scores)
    ]
    ranked_sorted = sorted(ranked, key=lambda x: x["score"], reverse=True)

    return {
        "status": "ok",
        "source": source,
        "ranked": ranked_sorted,
        "top_candidate": ranked_sorted[0]["candidate"] if ranked_sorted else None,
        "top_score": ranked_sorted[0]["score"] if ranked_sorted else 0.0,
        "model": model,
    }


def _exec_hf_embed(args: dict[str, Any]) -> dict[str, Any]:
    """Semantic similarity via HF sentence-similarity pipeline.

    Requires `source` + `candidates` — HF's free-tier embeddings route
    returns similarity scores directly rather than raw vectors.
    """
    source = args.get("source") or args.get("source_sentence") or args.get("text")
    candidates = args.get("candidates") or args.get("texts") or args.get("sentences")
    if not source or not candidates:
        return {
            "status": "error",
            "text": (
                "hf_embed requires 'source' (reference text) and 'candidates' "
                "(list to compare against). Example: {source: 'AI jeg holder af', "
                "candidates: ['Jarvis er venlig', 'pizza er mad']}"
            ),
        }
    if isinstance(candidates, str):
        candidates = [candidates]
    model = str(args.get("model") or _EMBED_DEFAULT_MODEL).strip()

    result = semantic_similarity(
        source=str(source),
        candidates=[str(c) for c in candidates],
        model=model,
    )
    if result.get("status") != "ok":
        return result

    preview = ", ".join(
        f"{r['candidate'][:30]}={r['score']}"
        for r in result["ranked"][:3]
    )
    return {
        "status": "ok",
        "text": f"Top match: '{result['top_candidate'][:80]}' (score={result['top_score']}) | {preview}",
        **result,
    }


# ─── Zero-shot classification ──────────────────────────────────────────

_ZSC_DEFAULT_MODEL = "facebook/bart-large-mnli"
_ZSC_ALLOWED_MODELS = (
    "facebook/bart-large-mnli",
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",  # multilingual
)


def zero_shot_classify(
    *,
    text: str,
    labels: list[str],
    model: str = _ZSC_DEFAULT_MODEL,
    multi_label: bool = False,
) -> dict[str, Any]:
    """Classify text against provided candidate labels via MNLI."""
    if not _hf_token():
        return {"status": "error", "text": "huggingface_token missing from runtime.json"}
    if not text or not labels:
        return {"status": "error", "text": "text and labels required"}
    if model not in _ZSC_ALLOWED_MODELS:
        model = _ZSC_DEFAULT_MODEL

    url = f"{_HF_BASE}/{model}"
    payload = {
        "inputs": str(text),
        "parameters": {
            "candidate_labels": [str(l) for l in labels],
            "multi_label": bool(multi_label),
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=_auth_headers(), method="POST")

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {"status": "error", "text": f"HF HTTP {exc.code}: {err_body}"}
    except Exception as exc:
        return {"status": "error", "text": f"ZSC fetch failed: {exc}"}

    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "text": f"parse failed: {exc}"}

    # Response can be either {labels, scores} or [{label, score}, ...]
    labels_out: list[str] = []
    scores_out: list[float] = []
    if isinstance(data, dict):
        labels_out = list(data.get("labels") or [])
        scores_out = list(data.get("scores") or [])
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                labels_out.append(str(item.get("label") or ""))
                scores_out.append(float(item.get("score") or 0.0))
    ranked = [
        {"label": l, "score": round(float(s), 4)}
        for l, s in zip(labels_out, scores_out)
    ]
    return {
        "status": "ok",
        "top_label": ranked[0]["label"] if ranked else None,
        "top_score": ranked[0]["score"] if ranked else 0.0,
        "ranked": ranked,
        "model": model,
    }


def _exec_hf_zero_shot_classify(args: dict[str, Any]) -> dict[str, Any]:
    text = str(args.get("text") or "").strip()
    labels = args.get("labels") or []
    if not text:
        return {"status": "error", "text": "text required"}
    if isinstance(labels, str):
        labels = [l.strip() for l in labels.split(",") if l.strip()]
    if not labels:
        return {"status": "error", "text": "labels required (list or comma-separated)"}
    model = str(args.get("model") or _ZSC_DEFAULT_MODEL).strip()
    multi = bool(args.get("multi_label", False))
    result = zero_shot_classify(text=text, labels=list(labels), model=model, multi_label=multi)
    if result.get("status") == "ok":
        preview = ", ".join(f"{r['label']}={r['score']}" for r in result["ranked"][:5])
        return {
            "status": "ok",
            "text": f"top={result['top_label']} ({result['top_score']}) | {preview}",
            **result,
        }
    return result


# ─── Vision LLM (image-to-text / VLM) ─────────────────────────────────

_VLM_DEFAULT_MODEL = "meta-llama/Llama-3.2-11B-Vision-Instruct"
_VLM_ALLOWED_MODELS = (
    "meta-llama/Llama-3.2-11B-Vision-Instruct",
    "Qwen/Qwen2.5-VL-7B-Instruct",
    "HuggingFaceM4/idefics2-8b",
)


def _image_to_data_url(source: str) -> str:
    """Convert file path / URL / raw-bytes path to a data URL for VLM input."""
    import base64
    if source.startswith(("http://", "https://")):
        return source  # VLMs accept URLs directly
    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"image not found: {path}")
    suffix = path.suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}.get(suffix, "image/jpeg")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def vision_analyze(
    *,
    image_source: str,
    prompt: str = "Describe this image in detail.",
    model: str = _VLM_DEFAULT_MODEL,
    max_tokens: int = 512,
) -> dict[str, Any]:
    """Analyze an image via a vision-language model. image_source = path or URL."""
    if not _hf_token():
        return {"status": "error", "text": "huggingface_token missing from runtime.json"}
    if model not in _VLM_ALLOWED_MODELS:
        model = _VLM_DEFAULT_MODEL

    try:
        image_url = _image_to_data_url(image_source)
    except Exception as exc:
        return {"status": "error", "text": f"could not prepare image: {exc}"}

    # Use the OpenAI-compatible chat completion endpoint
    url = "https://router.huggingface.co/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": str(prompt)},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "max_tokens": int(max_tokens),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=_auth_headers(), method="POST")

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {"status": "error", "text": f"HF HTTP {exc.code}: {err_body}"}
    except Exception as exc:
        return {"status": "error", "text": f"VLM fetch failed: {exc}"}

    try:
        data = json.loads(raw.decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
    except Exception as exc:
        return {"status": "error", "text": f"parse failed: {exc}"}

    return {
        "status": "ok",
        "text": str(text),
        "model": model,
        "usage": data.get("usage") if isinstance(data, dict) else None,
    }


def _exec_hf_vision_analyze(args: dict[str, Any]) -> dict[str, Any]:
    source = str(args.get("image_source") or args.get("path") or args.get("url") or "").strip()
    if not source:
        return {"status": "error", "text": "image_source required (path or URL)"}
    prompt = str(args.get("prompt") or "Describe this image in detail.")
    model = str(args.get("model") or _VLM_DEFAULT_MODEL).strip()
    try:
        max_tokens = int(args.get("max_tokens") or 512)
    except Exception:
        max_tokens = 512
    return vision_analyze(
        image_source=source, prompt=prompt, model=model, max_tokens=max_tokens,
    )


HF_INFERENCE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "hf_text_to_video",
            "description": (
                "Generate a video from a text prompt via Hugging Face serverless "
                "inference API. Genuinely free (rate-limited on free tier). "
                "Models: Lightricks/LTX-Video-0.9.8-13B-distilled (default, fast) | "
                "Lightricks/LTX-Video (higher quality) | tencent/HunyuanVideo (best, slowest). "
                "Returns saved MP4 path."
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
                            "Lightricks/LTX-Video-0.9.8-13B-distilled (default) | "
                            "Lightricks/LTX-Video | tencent/HunyuanVideo"
                        ),
                    },
                    "num_frames": {
                        "type": "integer",
                        "description": "Number of frames to generate. Model-dependent.",
                    },
                    "guidance_scale": {
                        "type": "number",
                        "description": "Prompt adherence strength. Typical 3-9.",
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "What to avoid in the video.",
                    },
                    "num_inference_steps": {
                        "type": "integer",
                        "description": "Denoising steps. Higher = better quality, slower.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional seed for reproducibility.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hf_transcribe_audio",
            "description": (
                "Transcribe audio to text via HuggingFace Whisper-v3. "
                "audio_source can be a local file path or HTTP(S) URL. "
                "Supports all major audio formats (mp3, wav, m4a, ogg, flac). "
                "Returns transcribed text. Optionally timestamps and language hint."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "audio_source": {
                        "type": "string",
                        "description": "Local file path or URL to audio file.",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "openai/whisper-large-v3 (default) | "
                            "openai/whisper-large-v3-turbo | openai/whisper-base"
                        ),
                    },
                    "return_timestamps": {
                        "type": "boolean",
                        "description": "Return text chunks with timestamps. Default false.",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language hint (e.g. 'da', 'en'). Default: auto-detect.",
                    },
                },
                "required": ["audio_source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hf_embed",
            "description": (
                "Compute sentence embeddings for semantic search, clustering, "
                "similarity. Default model all-MiniLM-L6-v2 (384-dim, fast). "
                "Pass compare_to for automatic cosine-similarity matrix against "
                "a reference text/list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "texts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Texts to embed (or pass a single string as 'text').",
                    },
                    "text": {
                        "type": "string",
                        "description": "Single text to embed (alternative to 'texts').",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "sentence-transformers/all-MiniLM-L6-v2 (default) | "
                            "all-mpnet-base-v2 | BAAI/bge-small-en-v1.5 | "
                            "BAAI/bge-large-en-v1.5 | intfloat/multilingual-e5-base"
                        ),
                    },
                    "compare_to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional reference texts. If provided, returns a "
                            "similarity matrix between inputs and references."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hf_zero_shot_classify",
            "description": (
                "Classify text against user-provided candidate labels. No training "
                "data needed — uses NLI model (BART-MNLI by default). Fast and "
                "cheap triage before committing to a full LLM call."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to classify.",
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Candidate labels (list or comma-separated string).",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "facebook/bart-large-mnli (default) | "
                            "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (multilingual)"
                        ),
                    },
                    "multi_label": {
                        "type": "boolean",
                        "description": "Allow multiple labels to be true. Default false.",
                    },
                },
                "required": ["text", "labels"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hf_vision_analyze",
            "description": (
                "Analyze an image with a vision-language model via HF router. "
                "image_source = local path or URL. "
                "NOTE: HF free tier (2026) does NOT include VLM access — this tool "
                "requires an enabled paid provider (e.g. Groq, Fireworks, Novita). "
                "Returns clean error when not enabled. For existing free image "
                "analysis use the analyze_image tool (uses paid chat provider "
                "Jarvis already has access to)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "image_source": {
                        "type": "string",
                        "description": "Local path or HTTP(S) URL to image.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Question or instruction for the VLM.",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "meta-llama/Llama-3.2-11B-Vision-Instruct (default) | "
                            "Qwen/Qwen2.5-VL-7B-Instruct | HuggingFaceM4/idefics2-8b"
                        ),
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Max tokens in response. Default 512.",
                    },
                },
                "required": ["image_source"],
            },
        },
    },
]
