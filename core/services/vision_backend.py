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

Derfor: et valg, ikke en dom — og valget er MODELVÆLGEREN i composeren, ikke en
skjult nøgle i en konfigfil. Bjørn (5/9): flash UDEN syn er stadig standard; kan
han vælge flash MED syn i vælgeren, skal syns-værktøjerne følge med. Vælger han
den blinde, arbejder de som hidtil.

Rækkefølgen er derfor:
1. Kører der en synlig tur på en model der KAN se? Så bruger værktøjerne DEN —
   øjnene sidder i den model der svarer ham.
2. Ellers `vision_provider` / `vision_model_name` i runtime.json (fallback).
3. Ellers ollama, som hidtil.

Ollama-modeller bærer et tag (`gemma4:31b-cloud`), DeepSeeks API-navne gør ikke
(`deepseek-v4-flash-vision-exp`) — det er nok til at gætte provideren når kun
modelnavnet er sat.

Begge veje rapporterer omkostning: DeepSeek-vejen bogfører rigtigt i hovedbogen
(lane `vision`), ollama-vejen koster ikke pr. token.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_TIMEOUT = 180
_MAX_TOKENS = 400


# Modeller der selv kan se. En model uden syn kan ikke laane oejne af en tur —
# saa falder vi tilbage til den konfigurerede vision-model.
_VISION_CAPABLE = frozenset({"deepseek-v4-flash-vision-exp"})
_SEEING_NAME_RE = re.compile(r"vision|llava|(?:^|[\d\-_.])vl(?:[:\-_.\d]|$)")


def model_can_see(model: str) -> bool:
    """Kan DENNE model selv se et billede?"""
    name = str(model or "").strip().lower()
    if not name:
        return False
    if name in _VISION_CAPABLE:
        return True
    # Navnekonventioner der i praksis altid betyder syn. «vl» skal staa som sit
    # eget led (qwen2.5vl:3b, qwen2-vl) og ikke falde over et tilfaeldigt
    # bogstavpar inde i et andet ord.
    return bool(_SEEING_NAME_RE.search(name))


def active_visible_target() -> tuple[str, str]:
    """(provider, model) for den synlige tur der koerer lige nu — ("","") hvis ingen."""
    try:
        from core.services.visible_runs import _get_active_visible_run_state
        state = _get_active_visible_run_state() or {}
    except Exception:
        return "", ""
    if not bool(state.get("active")) or bool(state.get("cancelled")):
        return "", ""
    return str(state.get("provider") or ""), str(state.get("model") or "")


def resolve_vision_target() -> tuple[str, str, str]:
    """(provider, model, kilde) for syns-vaerktoejerne lige nu.

    kilde er "selected-model" naar oejnene sidder i den model der svarer Bjoern,
    ellers "config".
    """
    provider, model = active_visible_target()
    if model and model_can_see(model):
        return (provider or resolve_vision_provider(model)), model, "selected-model"
    from core.services.attachment_service import _vision_model
    configured = _vision_model()
    return resolve_vision_provider(configured), configured, "config"


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
    provider, model, source = resolve_vision_target()
    return {
        "active": True,
        "provider": provider,
        "model": model,
        "source": source,
        "paid": provider == "deepseek",
        "summary": "syn via %s/%s (%s)" % (provider, model, source),
    }
