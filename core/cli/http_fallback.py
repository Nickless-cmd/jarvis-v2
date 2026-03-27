from __future__ import annotations

import json
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.runtime.settings import load_settings


def fetch_visible_run_via_api() -> tuple[dict | None, str | None]:
    response, api_error = request_json("GET", "/mc/visible-execution")
    if response is None:
        return None, api_error
    return response.get("visible_run"), None


def cancel_visible_run_via_api(run_id: str) -> tuple[bool, str | None]:
    response, api_error = request_json("POST", f"/chat/runs/{run_id}/cancel")
    if response is None:
        return False, api_error
    return bool(response.get("ok")), None


def request_json(
    method: str, path: str, payload: dict | None = None
) -> tuple[dict | None, str | None]:
    settings = load_settings()
    url = f"http://{settings.host}:{settings.port}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib_request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib_request.urlopen(request, timeout=0.75) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}, None
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        detail = http_error_detail(body)
        if exc.code == 404:
            return None, "not-found"
        return None, detail or f"http-{exc.code}"
    except urllib_error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return None, f"api-unavailable: {reason}"
    except TimeoutError:
        return None, "api-unavailable: timeout"
    except Exception as exc:
        return None, f"api-unavailable: {exc}"


def http_error_detail(body: str) -> str | None:
    try:
        data = json.loads(body)
    except Exception:
        return None
    detail = data.get("detail")
    return str(detail) if detail else None

