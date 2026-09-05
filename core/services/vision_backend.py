"""Hvilke øjne bruger han? — valg af vision-model (2026-09-05).

Målt 5/9 før noget blev bygget: han HAVDE syn hele tiden.
`gemma4:31b-cloud` via ollama læste en statusskærm korrekt på 0,5 s — farver,
rækkenavne og småteksten «sidst opdateret 08:41». `deepseek-v4-flash-vision-exp`
løste samme opgave på 1,2 s.

Bjørns argument for at kunne vælge alligevel: vision-varianten er SAMME model som
den han i forvejen taler med, bare med syn, og prisen er den samme med og uden.
Så det er ikke et spørgsmål om at betale for noget dyrere — det er et spørgsmål
om at have øjnene i den model der svarer, når det gør en forskel. Og han betaler
for ollama cloud i forvejen, så ingen af vejene er gratis i egentlig forstand.

Derfor: et valg, ikke en dom. `vision_provider` i runtime.json afgør det;
uden den gættes provideren ud fra modelnavnet, så det rækker at sætte
`vision_model_name`. Ollama-modeller bærer et tag (`gemma4:31b-cloud`),
DeepSeeks gør ikke (`deepseek-v4-flash-vision-exp`).

Begge veje rapporterer omkostning: DeepSeek-vejen bogfører rigtigt i hovedbogen
(lane `vision`), ollama-vejen koster ikke pr. token.
"""
from __future__ import annotations

import base64
import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_TIMEOUT = 180
_MAX_TOKENS = 400


def resolve_vision_provider(model: str) -> str:
    """`"ollama"` eller `"deepseek"`. Eksplicit konfig vinder over gættet."""
    try:
        from core.runtime.secrets import read_runtime_key
        explicit = str(read_runtime_key("vision_provider") or "").strip().lower()
        if explicit in ("ollama", "deepseek"):
            return explicit
    except Exception:
        pass
    name = str(model or "").strip().lower()
    # Ollama-modeller bærer altid et tag efter kolon; DeepSeeks API-navne gør ikke.
    if name.startswith("deepseek") and ":" not in name:
        return "deepseek"
    return "ollama"


def describe_via_deepseek(
    image_b64: str, *, model: str, prompt: str, run_id: str = "",
) -> str:
    """Send billedet til DeepSeeks vision-model og returnér svaret.

    Bogfører sit eget forbrug — et vision-kald må ikke blive endnu et kald
    hovedbogen ikke kender til.
    """
    from core.runtime.secrets import read_runtime_key

    key = str(read_runtime_key("deepseek_api_key") or "").strip()
    if not key:
        raise RuntimeError("deepseek_api_key mangler i runtime.json")
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + image_b64}},
        ]}],
        "max_tokens": _MAX_TOKENS,
    }).encode("utf-8")
    req = urllib.request.Request(
        _DEEPSEEK_URL, data=payload, method="POST",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    _record_cost(data.get("usage") or {}, model=model, run_id=run_id)
    choices = data.get("choices") or []
    content = (choices[0] or {}).get("message", {}).get("content", "") if choices else ""
    return str(content or "").strip()


def _record_cost(usage: dict[str, Any], *, model: str, run_id: str) -> None:
    try:
        from core.costing.ledger import record_cost
        from core.services.llm_pricing import compute_cost_usd
        inp = int(usage.get("prompt_tokens") or 0)
        out = int(usage.get("completion_tokens") or 0)
        hit = int(usage.get("prompt_cache_hit_tokens") or 0)
        miss = int(usage.get("prompt_cache_miss_tokens") or 0)
        if not (inp or out):
            return
        record_cost(
            lane="vision", provider="deepseek", model=model,
            input_tokens=inp, output_tokens=out,
            cache_hit_tokens=hit, cache_miss_tokens=miss,
            cost_usd=compute_cost_usd(
                "deepseek", model, cache_hit_tokens=hit, cache_miss_tokens=miss,
                output_tokens=out, input_tokens=inp),
            run_id=str(run_id or ""),
        )
    except Exception as exc:
        logger.debug("vision_backend: omkostning ikke bogfoert: %s", exc)


def describe(
    image_bytes: bytes | None = None, *, image_b64: str = "",
    model: str, prompt: str, run_id: str = "",
) -> dict[str, Any]:
    """Beskriv/besvar et billede med den valgte backend.

    Returnerer {"text", "provider", "model"}. Kaster videre ved fejl, så
    kaldstedet kan sige ærligt at synet svigtede i stedet for at finde på noget.
    """
    b64 = image_b64 or base64.b64encode(image_bytes or b"").decode("ascii")
    provider = resolve_vision_provider(model)
    if provider == "deepseek":
        text = describe_via_deepseek(b64, model=model, prompt=prompt, run_id=run_id)
    else:
        from core.services.visual_memory import _describe_via_ollama
        text = _describe_via_ollama(b64, model=model, prompt=prompt)
    return {"text": str(text or "").strip(), "provider": provider, "model": model}


def build_vision_backend_surface() -> dict[str, Any]:
    from core.services.attachment_service import _vision_model
    model = _vision_model()
    provider = resolve_vision_provider(model)
    return {
        "active": True,
        "provider": provider,
        "model": model,
        "paid": provider == "deepseek",
        "summary": "syn via %s/%s" % (provider, model),
    }
