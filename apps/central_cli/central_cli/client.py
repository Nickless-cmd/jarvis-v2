from __future__ import annotations

from typing import Any, Iterator

import httpx


class CentralError(Exception):
    """CLI-vendt fejl med kategori (connection/permission/auth/server/client)."""
    def __init__(self, category: str, message: str, status: int | None = None):
        super().__init__(message)
        self.category = category
        self.status = status


def _categorize(status: int) -> str:
    if status in (401,):
        return "auth"
    if status in (403,):
        return "permission"
    if status >= 500:
        return "server"
    return "client"


class CentralClient:
    def __init__(self, *, base_url: str, token: str | None, timeout: float = 20.0, _transport=None):
        self.base_url = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(base_url=self.base_url, headers=headers,
                                    timeout=timeout, transport=_transport)

    def _check(self, resp: httpx.Response) -> httpx.Response:
        if resp.status_code >= 400:
            raise CentralError(_categorize(resp.status_code),
                               f"HTTP {resp.status_code}: {resp.text[:200]}", resp.status_code)
        return resp

    def get_json(self, path: str, params: dict | None = None) -> Any:
        try:
            r = self._check(self._client.get(path, params=params))
        except httpx.RequestError as exc:
            raise CentralError("connection", str(exc)) from exc
        return r.json()

    def post_json(self, path: str, body: dict) -> Any:
        try:
            r = self._check(self._client.post(path, json=body))
        except httpx.RequestError as exc:
            raise CentralError("connection", str(exc)) from exc
        return r.json()

    def iter_sse(self, path: str) -> Iterator[dict]:
        """Yield parsed `data:` JSON-linjer fra en SSE-stream. Self-safe pr. linje."""
        import json
        try:
            with self._client.stream("GET", path, timeout=None) as resp:
                self._check(resp)
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    try:
                        yield json.loads(payload)
                    except ValueError:
                        continue
        except httpx.RequestError as exc:
            raise CentralError("connection", str(exc)) from exc

    def close(self) -> None:
        self._client.close()
