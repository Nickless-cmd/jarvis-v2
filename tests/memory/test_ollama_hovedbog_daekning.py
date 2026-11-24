"""Vagt: ethvert Ollama-chat/generate-kald i `core/` skal skrive i HOVEDBOGEN.

HVORFOR (målt 24/11-2026). Ollamas eget API svarede **19.816 kald / $34,67** for
syv dage, mens `costs` havde 1.212 kald / $3,87 — 6,1 % af kaldene. Årsagen var
ikke én manglende pris-tabel men en række kodeveje der kaldte Ollama uden at
bogføre: `_call_ollama_chat` i enrichment, konsoliderings-fallbacken,
`analyze_image`, `_describe_via_ollama` og elleve andre. Flere af dem skrev kun
til `central_llm_egress.observe`, som er en in-memory ring-buffer på 100 samples
— den forsvinder ved genstart og efterlader ingen række.

Vagten er STRUKTUREL, ikke tekstbaseret: den finder det faktiske HTTP-kald hvis
argument nævner en Ollama-chat-sti. En ren grep efter `/api/chat` giver falske
positiver i serializers og docstrings (målt: 8 af 25 træf).

Den ser med vilje IKKE på `/api/tags` (model-metadata, koster intet) eller
`/api/embed`/`/api/embeddings` (embedding-lane, separat regnskab).
"""

from __future__ import annotations

import ast
import pathlib

import pytest

# De stier der koster penge pr. token.
_CHAT_STIER = ("/api/chat", "/api/generate")

# Funktioner der bevidst ikke bogfører selv, med begrundelse.
# `visible_model_ollama` er den primære visible-vej: bogføringen sker i kalderen
# (`visible_model`/run-pipelinen), og `primary`-lanen har rækker — målt 24/11.
_WHITELIST = {
    ("core/services/visible_model_ollama.py", "_execute_ollama_model"),
    ("core/services/visible_model_ollama.py", "_stream_ollama_model"),
}


def _er_ollama_chat_kald(node: ast.AST) -> bool:
    """Et FAKTISK HTTP-kald hvis argument nævner en chat/generate-sti."""
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    navn = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
    if navn not in ("urlopen", "Request", "post", "get", "request"):
        return False

    def _rammer(v: ast.AST) -> bool:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            return any(s in v.value for s in _CHAT_STIER)
        if isinstance(v, ast.JoinedStr):
            return any(
                isinstance(x, ast.Constant)
                and isinstance(x.value, str)
                and any(s in x.value for s in _CHAT_STIER)
                for x in v.values
            )
        return False

    return any(_rammer(a) for a in node.args)


def _u_bogfoerte_kald(rod: pathlib.Path) -> list[str]:
    """Returnér 'fil:funktion' for hvert ubookført Ollama-chat-kald under `rod`."""
    fundet: list[str] = []
    for fil in sorted(rod.rglob("*.py")):
        try:
            trae = ast.parse(fil.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(trae):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(_er_ollama_chat_kald(n) for n in ast.walk(node)):
                continue
            if "bogfoer_ollama_kald" in ast.dump(node):
                continue
            noegle = (str(fil), node.name)
            if noegle in _WHITELIST:
                continue
            fundet.append(f"{fil}:{node.name}")
    return fundet


def test_alle_ollama_chat_kald_i_core_bogfoerer():
    mangler = _u_bogfoerte_kald(pathlib.Path("core"))
    assert not mangler, (
        "Disse funktioner kalder Ollama uden at skrive i hovedbogen:\n  "
        + "\n  ".join(mangler)
        + "\n\nTilføj `bogfoer_ollama_kald(...)` med tokens fra Ollamas egne felter "
        "(`prompt_eval_count`/`eval_count`) og cache-splittet beregnet INLINE — "
        "ikke importeret fra `visible_model_ollama`, som er cirkulært. Er vejen "
        "bevidst uden regnskab, tilføj den til _WHITELIST med en begrundelse."
    )


def test_vagten_kan_fejle(tmp_path):
    """Negativ afprøvning: en fil med et ubookført kald skal AFVISES."""
    daarlig = tmp_path / "daarlig.py"
    daarlig.write_text(
        "import urllib.request\n"
        "def f():\n"
        "    return urllib.request.urlopen('http://127.0.0.1:11434/api/chat')\n"
    )
    assert _u_bogfoerte_kald(tmp_path), "vagten fandt intet i en fil der HAR et ubookført kald"

    # Fjern den dårlige FØR den gode tjekkes — ellers finder vagten den
    # stadig, og testen måler sin egen opsætning i stedet for vagten.
    daarlig.unlink()
    god = tmp_path / "god.py"
    god.write_text(
        "import urllib.request\n"
        "def f():\n"
        "    from core.services.ollama_usage import bogfoer_ollama_kald\n"
        "    return urllib.request.urlopen('http://127.0.0.1:11434/api/chat')\n"
    )
    assert not _u_bogfoerte_kald(tmp_path), "vagten afviste en fil der bogfører korrekt"

    # /api/tags er metadata og må ikke tælle som et betalende kald.
    tags = tmp_path / "tags.py"
    tags.write_text(
        "import urllib.request\n"
        "def f():\n"
        "    return urllib.request.urlopen('http://127.0.0.1:11434/api/tags')\n"
    )
    (god).unlink()
    assert not _u_bogfoerte_kald(tmp_path), "vagten tæller /api/tags som et betalende kald"
