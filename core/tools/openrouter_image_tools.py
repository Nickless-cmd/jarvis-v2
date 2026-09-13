"""OpenRouter billed-generering — Gemini tegner, diffusion maler (målt 12/9-2026).

## Hvorfor dette værktøj findes

12/9-2026 research: **gratis billedgenerering findes ikke på vores nøgler.**
- Gemini direkte: HTTP 429, "limit: 0" — billed-kald er betalt-only på free tier.
- Hugging Face: hf-inference har droppet billedgenerering (410/400).
- OpenRouter: ingen gratis billed-modeller.

Men OpenRouter med **betalingsnøglen** virker — og kvaliteten er en anden slags.
Gemini's billedmodel er IKKE diffusion: den *tegner*. Vision på resultatet:
"skarp og vektoragtig, helt rene, glatte cirkelbuer med jævn stregtykkelse og
hårde kanter". Flux blev beskrevet som "soft and blurred, melted". Derfor kan
Gemini bruges til ikoner og logoer, hvor diffusion ikke kan.

Værktøjet blev målt live 13/9-2026 før det blev skrevet:
- generering: 3,3 s, 52 KB, **$0,0336** (google/gemini-3.1-flash-lite-image)
- redigering: 5,6 s, 71 KB, **$0,0339**

## API-shape (verificeret mod docs + live kald)

``POST https://openrouter.ai/api/v1/images`` med
``{model, prompt, input_references?, aspect_ratio?, ...}`` svarer med
``{created, data:[{b64_json, media_type}], usage:{prompt_tokens, completion_tokens, cost}}``.

``usage.cost`` er den FAKTISKE pris fra OpenRouter — ikke et estimat. Prislisten
($0,0033) er 10x for lav, fordi billed-tokens tælles med.

## Nøglen — og hvorfor account2 er blokeret

Betalingsnøglen ligger i auth-profilen ``default`` (provider ``openrouter``).
``account2`` er free-tier og har ingen billed-kvote — og Bjørn har eksplicit
forbudt at kalde den direkte fra vores IP (ToS-brud ved flere gratis nøgler).
Den afvises derfor med en tydelig fejl i stedet for et kryptisk 402.

Nøglen læses altid fra auth-laget. Aldrig hardkodet.
"""
from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_ENDPOINT = "https://openrouter.ai/api/v1/images"
_GENERATED_REL = "memory/generated"
_PROVIDER = "openrouter"

# Eventet der annoncerer en generering. Familien `tool` er både tilladt
# (ALLOWED_EVENT_FAMILIES) og routet til Central (FAMILY_ROUTES). Løftet til
# modul-niveau så en test kan verificere at `Event.create` accepterer det —
# det var netop den kobling der var tavst brudt 13/9-2026.
_EVENT_KIND = "tool.openrouter_image_generated"

# Default = den model Bjørn husker, og den der blev målt 12/9. Den tegner skarpt.
# Billigere alternativ: google/gemini-3.1-flash-lite-image (~$0,034).
# Dyrere/bedre: google/gemini-3-pro-image (~$0,13).
_DEFAULT_MODEL = "google/gemini-2.5-flash-image"

_TIMEOUT = 180
_USER_AGENT = "Jarvis-v2/openrouter-image"
_MAX_REFERENCE_BYTES = 8 * 1024 * 1024

# Profilen der IKKE må bruges: free-tier-nøglen. Se modulets docstring.
_FORBUDT_PROFIL = "account2"

_MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def _credentials() -> tuple[str, str]:
    """Returnér (api_key, profil). Læses fra auth-laget — aldrig hardkodet.

    Profilen kan overstyres med ``openrouter_image_profile`` i runtime.json.
    ``account2`` afvises: det er free-tier-nøglen, og direkte brug fra vores IP
    er et ToS-brud Bjørn eksplicit har forbudt.
    """
    profil = "default"
    try:
        from core.runtime.secrets import read_runtime_key
        raw = read_runtime_key("openrouter_image_profile")
        if raw:
            profil = str(raw).strip() or "default"
    except Exception:
        pass

    if profil == _FORBUDT_PROFIL:
        raise RuntimeError(
            f"openrouter_image_profile={_FORBUDT_PROFIL} er free-tier-nøglen. "
            "Den må ikke bruges direkte fra vores IP (ToS), og den har ingen "
            "billed-kvote. Brug profilen 'default'."
        )

    try:
        from core.auth.profiles import get_provider_credentials
        creds = get_provider_credentials(profile=profil, provider=_PROVIDER)
        key = str((creds or {}).get("api_key") or "").strip()
        if key:
            return key, profil
    except Exception as exc:
        logger.debug("openrouter_image: kunne ikke laese auth-profil: %s", exc)

    # Sidste udvej: top-level nøgle i runtime.json.
    try:
        from core.runtime.secrets import read_runtime_key
        key = str(read_runtime_key("openrouter_api_key") or "").strip()
        if key:
            return key, profil
    except Exception:
        pass
    return "", profil


def _generated_dir() -> Path:
    from core.runtime.workspace_paths import shared_dir
    return shared_dir() / _GENERATED_REL


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _safe_filename(prompt: str, gen_id: str, ext: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9æøåÆØÅ_-]+", "-", str(prompt or "").strip())[:60]
    slug = re.sub(r"-+", "-", slug).strip("-") or "image"
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{slug}-{gen_id[-6:]}{ext}"


def _write_sidecar(image_path: Path, metadata: dict[str, Any]) -> None:
    try:
        sidecar = image_path.with_suffix(image_path.suffix + ".json")
        sidecar.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.debug("openrouter_image: sidecar write failed: %s", exc)


def _as_reference(source: str) -> dict[str, Any] | None:
    """Gør en sti/URL/data-URL til et ``input_references``-element.

    Returnerer None hvis kilden ikke kan læses — så fejler kaldet ærligt i
    stedet for at sende en tom reference afsted.
    """
    raw = str(source or "").strip()
    if not raw:
        return None
    if raw.startswith(("http://", "https://")):
        return {"type": "image_url", "image_url": {"url": raw}}
    if raw.startswith("data:"):
        return {"type": "image_url", "image_url": {"url": raw}}
    try:
        sti = Path(raw).expanduser()
        if not sti.is_file():
            return None
        data = sti.read_bytes()
        if not data or len(data) > _MAX_REFERENCE_BYTES:
            return None
        suffix = sti.suffix.lower().lstrip(".")
        mime = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif",
        }.get(suffix, "image/jpeg")
        b64 = base64.b64encode(data).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        }
    except Exception as exc:
        logger.debug("openrouter_image: reference kunne ikke laeses: %s", exc)
        return None


def _report_cost(usage: dict[str, Any], *, model: str, run_id: str = "") -> float:
    """Bogfør den FAKTISKE pris fra OpenRouter. Returnerer cost_usd."""
    try:
        cost = float(usage.get("cost") or 0.0)
    except Exception:
        cost = 0.0
    try:
        from core.costing.ledger import record_cost
        inp = int(usage.get("prompt_tokens") or 0)
        out = int(usage.get("completion_tokens") or 0)
        record_cost(
            lane="image",
            provider=_PROVIDER,
            model=model,
            input_tokens=inp,
            output_tokens=out,
            cache_hit_tokens=0,
            cache_miss_tokens=0,
            cost_usd=cost,
            run_id=str(run_id or ""),
        )
    except Exception as exc:
        logger.debug("openrouter_image: omkostning ikke bogfoert: %s", exc)
    try:
        from core.services.central_llm_egress import observe as _egress_observe
        _egress_observe(
            lane="openrouter_image",
            provider=_PROVIDER,
            model=model,
            purpose="generate",
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            cost_usd=cost,
            autonomous=False,
            source="openrouter:images",
        )
    except Exception as exc:
        logger.debug("openrouter_image: egress-observation fejlede: %s", exc)
    return cost


def _post(body: dict[str, Any], *, timeout: int = _TIMEOUT) -> dict[str, Any]:
    """Ét POST til billed-endpointet. Kaster aldrig — returnerer fejl-dict."""
    key, _profil = _credentials()
    if not key:
        return {
            "status": "error",
            "text": (
                "Ingen OpenRouter-nøgle fundet. Sæt auth-profilen 'default' "
                "(provider openrouter) eller openrouter_api_key i runtime.json."
            ),
        }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _ENDPOINT,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "HTTP-Referer": "https://jarvis.srvlab.dk",
            "X-Title": "Jarvis-v2",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"status": "ok", "data": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        return {"status": "error", "text": f"OpenRouter HTTP {exc.code}: {err_body}"}
    except Exception as exc:
        return {"status": "error", "text": f"OpenRouter fetch failed: {exc}"}


def _save_images(
    data: dict[str, Any],
    *,
    prompt: str,
    model: str,
    gen_id: str,
    save_dir: Path | None = None,
    ekstra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dekodér, gem og registrér billederne fra et svar. Delt af begge veje."""
    items = [d for d in (data.get("data") or []) if isinstance(d, dict) and d.get("b64_json")]
    if not items:
        return {
            "status": "error",
            "text": f"Intet billede i svaret: {json.dumps(data)[:300]}",
        }

    target_dir = save_dir or _generated_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return {"status": "error", "text": f"could not create dir: {exc}"}

    usage = data.get("usage") or {}
    # Prisen fordeles ikke pr. billede her — usage.cost er for HELE kaldet.
    cost = _report_cost(usage, model=model)

    gemte: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        b64 = str(item.get("b64_json") or "")
        try:
            raw = base64.b64decode(b64)
        except Exception as exc:
            logger.debug("openrouter_image: kunne ikke dekode billede %d: %s", idx, exc)
            continue
        if not raw:
            continue
        # Udvidelsen kommer fra media_type — IKKE fra et ønske. Målt 13/9-2026:
        # bad man om png, svarede modellen image/jpeg.
        media_type = str(item.get("media_type") or "image/png")
        ext = _MIME_EXT.get(media_type, ".png")
        filename = _safe_filename(prompt, gen_id, ext)
        path = target_dir / filename
        try:
            path.write_bytes(raw)
        except Exception as exc:
            logger.debug("openrouter_image: kunne ikke skrive: %s", exc)
            continue

        metadata = {
            "generation_id": gen_id,
            "index": idx,
            "prompt": prompt,
            "model": model,
            "media_type": media_type,
            "bytes": len(raw),
            "cost_usd": cost,
            "created_at": datetime.now(UTC).isoformat(),
            "provider": "openrouter.ai",
            **(ekstra or {}),
        }
        _write_sidecar(path, metadata)

        attachment_id = ""
        try:
            from core.services.attachment_service import register_generated_image
            attachment_id = register_generated_image(
                local_path=str(path),
                mime_type=media_type,
                source_url="",
            )
        except Exception as exc:
            # Ikke `pass`: fejler registreringen, ligger billedet på disken men
            # er USYNLIGT i samtalen — og brugeren får et svar uden billede
            # uden at nogen kan se hvorfor.
            logger.warning(
                "openrouter_image: kunne ikke registrere %s som attachment: %s",
                path, exc,
            )

        gemte.append({
            "path": str(path),
            "bytes": len(raw),
            "media_type": media_type,
            "attachment_id": attachment_id,
        })

    if not gemte:
        return {"status": "error", "text": "Svaret indeholdt billeder, men ingen kunne gemmes."}

    try:
        from core.eventbus.bus import event_bus
        # TO-ARG form (kind, payload). Dict-formen `publish({...})` raiser
        # AttributeError inde i Event.create — og fanges af except'en, så
        # eventet ville ALDRIG fyre. Målt 13/9-2026: 26 kaldsteder i kodebasen
        # (pollinations, hf_inference, wake_word, voice_journal, mic_listen +
        # ~15 daemons) brugte samme form, alle tavse; `pollinations.*` og
        # `openrouter_image.*` havde 0 events nogensinde. Familien `tool` er
        # både tilladt (ALLOWED_EVENT_FAMILIES) og routet til Central
        # (FAMILY_ROUTES), så eventet persisterer.
        event_bus.publish(
            _EVENT_KIND,
            {
                "generation_id": gen_id,
                "model": model,
                "count": len(gemte),
                "paths": [g["path"] for g in gemte],
                "cost_usd": cost,
            },
        )
    except Exception as exc:
        # Ikke `pass`: et event der ikke kan udsendes er præcis den slags tavse
        # svigt hele denne kodebase har ondt af.
        logger.debug("openrouter_image: event ikke udsendt: %s", exc)

    return {
        "status": "ok",
        "generation_id": gen_id,
        "model": model,
        "images": gemte,
        "path": gemte[0]["path"],
        "bytes": gemte[0]["bytes"],
        "media_type": gemte[0]["media_type"],
        "attachment_id": gemte[0]["attachment_id"],
        "cost_usd": cost,
        "usage": usage,
    }


def generate_image(
    *,
    prompt: str,
    model: str = _DEFAULT_MODEL,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    quality: str | None = None,
    output_format: str | None = None,
    n: int = 1,
    seed: int | None = None,
    references: list[str] | None = None,
    save_dir: Path | None = None,
    timeout: int = _TIMEOUT,
) -> dict[str, Any]:
    """Generér (eller redigér) et billede via OpenRouter. Betalt — se cost_usd."""
    if not str(prompt or "").strip():
        return {"status": "error", "text": "prompt is empty"}

    body: dict[str, Any] = {"model": str(model or _DEFAULT_MODEL), "prompt": str(prompt).strip()}
    if aspect_ratio:
        body["aspect_ratio"] = str(aspect_ratio)
    if resolution:
        body["resolution"] = str(resolution)
    if quality:
        body["quality"] = str(quality)
    if output_format:
        body["output_format"] = str(output_format)
    if seed is not None:
        try:
            body["seed"] = int(seed)
        except Exception:
            pass
    try:
        n_int = _clamp(n, 1, 10)
    except Exception:
        n_int = 1
    if n_int > 1:
        body["n"] = n_int

    refs: list[dict[str, Any]] = []
    for src in (references or []):
        ref = _as_reference(src)
        if ref is None:
            return {"status": "error", "text": f"reference kunne ikke laeses: {src}"}
        refs.append(ref)
    if refs:
        body["input_references"] = refs

    gen_id = f"orimg-{uuid4().hex[:12]}"
    res = _post(body, timeout=timeout)
    if res.get("status") != "ok":
        return res
    return _save_images(
        res["data"],
        prompt=str(prompt),
        model=body["model"],
        gen_id=gen_id,
        save_dir=save_dir,
        ekstra={"kind": "edit" if refs else "generate",
                "references": [str(r)[:200] for r in (references or [])]},
    )


def edit_image(
    *,
    reference: str,
    prompt: str,
    model: str = _DEFAULT_MODEL,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
    n: int = 1,
    seed: int | None = None,
    save_dir: Path | None = None,
    timeout: int = _TIMEOUT,
) -> dict[str, Any]:
    """Redigér et eksisterende billede: reference + instruktion → nyt billede."""
    return generate_image(
        prompt=prompt,
        model=model,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        n=n,
        seed=seed,
        references=[reference],
        save_dir=save_dir,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Tool executors (Ollama-compatible)
# ---------------------------------------------------------------------------


def _haeng_paa_turen(args: dict[str, Any], result: dict[str, Any]) -> None:
    """Læg det genererede billede på turen, så klienten kan vise det i tråden.

    Målt 13/9-2026: billedet blev skrevet til disken OG registreret som
    attachment — men INGEN besked bar en reference til det. Klienten renderer
    efter blokke, så billedet var usynligt i samtalen selvom det fandtes.

    Samme «læg og tag»-mønster som ``publish_file`` bruger: værktøjet lægger
    posten fra sig under turen, ``visible_runs_outcomes`` tager den når svaret
    persisteres. Referencen er ``attachment_id`` — genererede billeder hentes
    over det user-scopede ``/attachments/image/{id}``, ikke over ``/files/``.

    Kaster aldrig: en visning må ikke brække en generering der lykkedes.
    """
    try:
        from core.services.published_files import note as _note
        sti = str(result.get("path") or "")
        aid = str(result.get("attachment_id") or "")
        if not aid and not sti:
            return
        _note(
            str(args.get("_runtime_turn_id") or args.get("_runtime_run_id") or ""),
            filename=Path(sti).name if sti else "billede",
            mime_type=str(result.get("media_type") or "image/png"),
            size_bytes=int(result.get("bytes") or 0),
            attachment_id=aid,
            tool_use_id=str(args.get("_runtime_tool_use_id") or ""),
        )
    except Exception:
        logger.debug("openrouter_image: kunne ikke haefte paa turen", exc_info=True)


def _exec_openrouter_image(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}
    refs = args.get("references") or args.get("input_references")
    if isinstance(refs, str):
        refs = [refs]
    elif not isinstance(refs, list):
        refs = None
    result = generate_image(
        prompt=prompt,
        model=str(args.get("model") or _DEFAULT_MODEL),
        aspect_ratio=args.get("aspect_ratio"),
        resolution=args.get("resolution"),
        quality=args.get("quality"),
        output_format=args.get("output_format"),
        n=args.get("n") or 1,
        seed=args.get("seed"),
        references=[str(r) for r in refs] if refs else None,
    )
    if result.get("status") == "ok":
        _haeng_paa_turen(args, result)
        return {
            "status": "ok",
            "text": (
                f"Billede genereret ({result['bytes']} bytes, {result['media_type']}, "
                f"${result['cost_usd']:.4f}) gemt i {result['path']}"
            ),
            **result,
        }
    return result


def _exec_openrouter_image_edit(args: dict[str, Any]) -> dict[str, Any]:
    ref = str(
        args.get("reference") or args.get("image_path") or args.get("image_url") or ""
    ).strip()
    if not ref:
        return {"status": "error", "text": "reference required (sti eller URL)"}
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required (hvad skal ændres?)"}
    result = edit_image(
        reference=ref,
        prompt=prompt,
        model=str(args.get("model") or _DEFAULT_MODEL),
        aspect_ratio=args.get("aspect_ratio"),
        resolution=args.get("resolution"),
        n=args.get("n") or 1,
        seed=args.get("seed"),
    )
    if result.get("status") == "ok":
        _haeng_paa_turen(args, result)
        return {
            "status": "ok",
            "text": (
                f"Billede redigeret ({result['bytes']} bytes, {result['media_type']}, "
                f"${result['cost_usd']:.4f}) gemt i {result['path']}"
            ),
            **result,
        }
    return result


OPENROUTER_IMAGE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "openrouter_image",
            "description": (
                "Generate an image via OpenRouter (PAID — roughly $0.034 per image on "
                "the default model; the actual cost is returned in `cost_usd`). "
                "Use this when the image must be SHARP and vector-like — icons, logos, "
                "diagrams, clean illustrations. The Gemini image models DRAW rather than "
                "diffuse, so edges are hard and strokes even; for soft photographic "
                "looks use pollinations_image (free) instead. "
                "Models: google/gemini-2.5-flash-image (default, proven), "
                "google/gemini-3.1-flash-lite-image (cheapest), "
                "google/gemini-3-pro-image (best, ~$0.13). "
                "Returns the saved image path; the image is also registered so it is "
                "visible in the conversation."
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
                        "description": (
                            "google/gemini-2.5-flash-image (default) | "
                            "google/gemini-3.1-flash-lite-image (cheapest) | "
                            "google/gemini-3-pro-image (best) | "
                            "google/gemini-3.1-flash-image | "
                            "black-forest-labs/flux.2-pro | openai/gpt-image-1"
                        ),
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "e.g. '1:1', '16:9', '9:16', '4:3', '3:4'. Default: model's choice.",
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Resolution tier: 512 | 1K | 2K | 4K (model-dependent).",
                    },
                    "quality": {
                        "type": "string",
                        "description": "auto | low | medium | high. Providers without a quality knob ignore it.",
                    },
                    "output_format": {
                        "type": "string",
                        "description": "png | jpeg | webp. If omitted the provider's default applies.",
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of images (1-10). Not all providers support n > 1.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional seed for reproducibility (where supported).",
                    },
                    "references": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional reference images (file paths or URLs) for "
                            "image-to-image. Use openrouter_image_edit for a single "
                            "reference and a simpler call."
                        ),
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "openrouter_image_edit",
            "description": (
                "Edit or transform an EXISTING image via OpenRouter (PAID — roughly "
                "$0.034 per image; the actual cost is returned in `cost_usd`). "
                "Pass the image path (or URL) plus an instruction describing the change "
                "— e.g. 'keep the composition, change the palette to warm orange' or "
                "'make this look like a watercolour painting'. The model preserves "
                "composition far better than diffusion-based tools. "
                "Returns the saved path of the new image."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Path or URL of the image to edit.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "What to change — be specific about what to keep.",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "google/gemini-2.5-flash-image (default) | "
                            "google/gemini-3.1-flash-lite-image (cheapest) | "
                            "google/gemini-3-pro-image (best)"
                        ),
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "Optional output aspect ratio, e.g. '1:1', '16:9'.",
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Resolution tier: 512 | 1K | 2K | 4K (model-dependent).",
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of variants (1-10). Default 1.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional seed for reproducibility.",
                    },
                },
                "required": ["reference", "prompt"],
            },
        },
    },
]
