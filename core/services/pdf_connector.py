"""PDF-connector (lokal) — læs/ekstraher tekst fra PDF-filer.

Lokalt værktøj, ingen OAuth. Kilde kan være en filsti (på runtime-maskinen) eller
en http(s)-URL (hentes og parses i hukommelsen). Ren læsning — ingen approval.
"""
from __future__ import annotations

_MAX_PAGES = 50
_MAX_CHARS = 40000

PDF_CONNECTOR_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "pdf_read",
            "description": (
                "Læs og ekstraher tekst fra en PDF — enten en filsti på maskinen eller en "
                "http(s)-URL. Returnerer tekst (afkortet) + sidetal. Til at analysere/opsummere "
                "PDF-indhold."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Filsti eller http(s)-URL til PDF'en"},
                    "max_pages": {"type": "integer", "description": "Maks sider der læses (1-50, standard 20)"},
                },
                "required": ["source"],
            },
        },
    },
]


def _load_bytes(source: str) -> tuple[bytes | None, str | None]:
    """→ (bytes, None) ved succes, ellers (None, fejlkode)."""
    s = (source or "").strip()
    if not s:
        return None, "source_required"
    if s.lower().startswith(("http://", "https://")):
        try:
            import httpx
            r = httpx.get(s, timeout=30, follow_redirects=True)
            if r.status_code != 200:
                return None, f"fetch_http_{r.status_code}"
            return r.content, None
        except Exception as e:  # noqa: BLE001
            return None, f"fetch_failed: {e}"
    try:
        import os
        if not os.path.isfile(s):
            return None, "file_not_found"
        with open(s, "rb") as fh:
            return fh.read(), None
    except Exception as e:  # noqa: BLE001
        return None, f"read_failed: {e}"


def read_pdf(source: str, *, max_pages: int = 20) -> dict:
    data, err = _load_bytes(source)
    if err:
        return {"status": "error", "error": err}
    try:
        n = max(1, min(_MAX_PAGES, int(max_pages)))
    except (TypeError, ValueError):
        n = 20
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        total = len(reader.pages)
        parts: list[str] = []
        for page in reader.pages[:n]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                continue
        text = "\n".join(parts).strip()
        truncated = len(text) > _MAX_CHARS
        return {
            "status": "ok",
            "total_pages": total,
            "pages_read": min(n, total),
            "truncated": truncated or n < total,
            "text": text[:_MAX_CHARS],
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"parse_failed: {e}"}
