"""Hugging Face-connector — søg modeller/datasets via Hub API.

Bruger den DELTE owner-token (`huggingface_token` i runtime.json), ikke per-bruger
OAuth — derfor behandlet som en lokal/altid-aktiv connector. Ren læsning.
"""
from __future__ import annotations

_API = "https://huggingface.co/api"

HF_CONNECTOR_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "hf_search_models",
            "description": (
                "Søg efter modeller på Hugging Face Hub. Returnerer id, downloads, likes, tags."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Søgeord, fx 'danish llm'"},
                    "limit": {"type": "integer", "description": "Maks antal (1-25, standard 10)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hf_model_info",
            "description": "Hent detaljer om en bestemt Hugging Face-model via dens id (fx 'meta-llama/Llama-3-8B').",
            "parameters": {
                "type": "object",
                "properties": {"model_id": {"type": "string", "description": "Model-id på Hub"}},
                "required": ["model_id"],
            },
        },
    },
]


def _headers() -> dict:
    try:
        from core.runtime.secrets import read_runtime_key
        tok = read_runtime_key("huggingface_token", env_override="HUGGINGFACE_TOKEN")
    except Exception:
        tok = ""
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _get(path: str, params: dict | None = None) -> dict:
    try:
        import httpx
        r = httpx.get(_API + path, headers=_headers(), params=params or {}, timeout=20)
        if r.status_code == 401:
            return {"status": "error", "error": "hf_token_invalid"}
        if r.status_code == 404:
            return {"status": "error", "error": "hf_not_found"}
        if r.status_code != 200:
            return {"status": "error", "error": f"hf_http_{r.status_code}"}
        return {"status": "ok", "data": r.json()}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"hf_request_failed: {e}"}


def search_models(query: str, *, limit: int = 10) -> dict:
    if not (query or "").strip():
        return {"status": "error", "error": "query_required"}
    try:
        lim = max(1, min(25, int(limit)))
    except (TypeError, ValueError):
        lim = 10
    res = _get("/models", {"search": query, "limit": lim, "sort": "downloads", "direction": -1})
    if res["status"] != "ok":
        return res
    models = [
        {"id": m.get("id") or m.get("modelId"), "downloads": m.get("downloads", 0),
         "likes": m.get("likes", 0), "tags": (m.get("tags") or [])[:8]}
        for m in (res["data"] or []) if isinstance(m, dict)
    ]
    return {"status": "ok", "models": models, "count": len(models)}


def model_info(model_id: str) -> dict:
    if not (model_id or "").strip():
        return {"status": "error", "error": "model_id_required"}
    res = _get(f"/models/{model_id}")
    if res["status"] != "ok":
        return res
    d = res["data"]
    return {
        "status": "ok",
        "id": d.get("id") or d.get("modelId"),
        "downloads": d.get("downloads", 0),
        "likes": d.get("likes", 0),
        "pipeline_tag": d.get("pipeline_tag", ""),
        "tags": (d.get("tags") or [])[:12],
        "library": d.get("library_name", ""),
    }
