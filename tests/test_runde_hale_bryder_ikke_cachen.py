"""Per-runde-beskeder maa ikke forskyde historikken.

## Hvad der var galt

Beskedlisten bygges som ``base_messages + exchanges``. De tre per-runde-vink —
budget-varslet, batch-vinket og den tvungne afslutning — blev appendet til
``base_messages``. Kommentarerne i koden kaldte dem «append-only trailing tur»,
men de landede altsaa MIDT i prompten, foran hele den voksende historik.

Maalt paa CT105 28/9-2026, ét synligt run paa 24 runder: batch-vinket (273 tegn
serialiseret, sha 645481) stod paa plads 7 i runde 9, 12 og 14 og var helt
fravaerende i de oevrige. Hver optraeden OG hver forsvinden skubbede alt
bagefter én plads. Praefiks-cachen braekkede ved 156.497 tegn hver gang:

    runde  8   hit 86.016   miss  1.730
    runde  9   hit 64.384   miss 25.224   <- vinket dukker op
    runde 10   hit 88.960   miss  4.338   <- vinket forsvinder igen

De seks ramte runder kostede 6.840 miss-tokens i snit mod 1.109 i de oevrige:
34.388 ekstra, 27 % af hele runets miss. For tre beskeder paa 242 tegn.

## Hvad testene maaler

Ikke at halen «er med» — at den ikke RYKKER noget. En test der kun tjekker at
vinket findes i listen ville vaere groen baade foer og efter rettelsen.
"""
from __future__ import annotations

import ast
import json
import pathlib
from collections.abc import Iterable
from contextlib import contextmanager

import pytest

from core.services import visible_followup as vf


class _FakeResponse:
    def __init__(self, lines: Iterable[bytes]) -> None:
        self._lines = list(lines)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def __iter__(self):
        return iter(self._lines)

    def read(self) -> bytes:
        return b"".join(self._lines)


@contextmanager
def _fanget(monkeypatch: pytest.MonkeyPatch, linjer: Iterable[bytes]):
    fanget: dict[str, object] = {}

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        fanget["body"] = json.loads(req.data.decode("utf-8")) if req.data else None
        return _FakeResponse(linjer)

    monkeypatch.setattr(vf.urllib_request, "urlopen", fake_urlopen)
    yield fanget


_NDJSON = [
    (json.dumps({"message": {"content": "ok"}}) + "\n").encode("utf-8"),
    (json.dumps({"done": True}) + "\n").encode("utf-8"),
]

_BASIS = [
    {"role": "system", "content": "identitet"},
    {"role": "user", "content": "spoergsmaal"},
]


def _udveksling(n: int):
    return vf.ToolExchange(
        text=f"svar {n}",
        tool_calls=[{"id": f"c{n}", "function": {"name": "read_file"}}],
        results=[vf.ToolResult(tool_call_id=f"c{n}", tool_name="read_file",
                               content=f"resultat {n}")],
        reasoning_content="",
    )


def _ollama_beskeder(monkeypatch, *, udvekslinger, hale):
    from core.runtime import provider_router
    monkeypatch.setattr(provider_router, "resolve_provider_router_target",
                        lambda *, lane: {"base_url": "http://ollama.test:11434"})
    with _fanget(monkeypatch, _NDJSON) as f:
        list(vf.stream_visible_followup(
            provider="ollama", model="llama3.1:8b",
            base_messages=_BASIS, exchanges=udvekslinger,
            trailing_messages=hale))
    return f["body"]["messages"]


def test_halen_staar_BAGEST_ikke_midt_i(monkeypatch):
    vink = {"role": "user", "content": "saml dine kald"}
    ud = _ollama_beskeder(monkeypatch, udvekslinger=[_udveksling(1)], hale=[vink])
    assert ud[-1] == vink, "halen skal vaere sidste besked"
    assert ud[0] == _BASIS[0] and ud[1] == _BASIS[1]


def test_et_vink_der_KOMMER_forskyder_ingenting(monkeypatch):
    """Runde N uden vink, runde N+1 med. Alt fra runde N skal staa uroert.

    Det er praecis den overgang der kostede 25.224 miss-tokens.
    """
    uden = _ollama_beskeder(monkeypatch, udvekslinger=[_udveksling(1), _udveksling(2)],
                            hale=[])
    med = _ollama_beskeder(monkeypatch, udvekslinger=[_udveksling(1), _udveksling(2)],
                           hale=[{"role": "user", "content": "saml dine kald"}])
    assert med[:len(uden)] == uden, "historikken flyttede sig da vinket kom"


def test_et_vink_der_FORSVINDER_forskyder_heller_ingenting(monkeypatch):
    """Den anden halvdel: runden efter, hvor vinket er vaek igen og samtalen
    er vokset. Begge retninger braekkede cachen foer."""
    vink = [{"role": "user", "content": "saml dine kald"}]
    med = _ollama_beskeder(monkeypatch, udvekslinger=[_udveksling(1)], hale=vink)
    uden_men_laengere = _ollama_beskeder(
        monkeypatch, udvekslinger=[_udveksling(1), _udveksling(2)], hale=[])
    # Alt FOER halen i den foerste runde skal genfindes uroert i den naeste.
    assert uden_men_laengere[:len(med) - len(vink)] == med[:len(med) - len(vink)]


def test_uden_hale_er_kroppen_byte_identisk_med_foer(monkeypatch):
    """Den almindelige runde maa ikke aendre sig af at parameteren findes."""
    a = _ollama_beskeder(monkeypatch, udvekslinger=[_udveksling(1)], hale=[])
    b = _ollama_beskeder(monkeypatch, udvekslinger=[_udveksling(1)], hale=None)
    assert a == b
    assert all(m.get("content") != "" or "tool_calls" in m for m in a[:2])


def test_flere_vink_bevarer_deres_raekkefoelge(monkeypatch):
    h = [{"role": "user", "content": "et"}, {"role": "user", "content": "to"}]
    ud = _ollama_beskeder(monkeypatch, udvekslinger=[_udveksling(1)], hale=h)
    assert ud[-2:] == h


def test_codex_laegger_ogsaa_halen_bagest():
    """Halen skal naa ALLE adaptere — ellers ser den samme runde forskellig ud
    alt efter udbyder, og cachen braekker paa den ene men ikke den anden."""
    from core.services.visible_followup_adapters import CodexFollowupAdapter
    items = CodexFollowupAdapter()._build_input(
        _BASIS, [_udveksling(1)],
        trailing_messages=[{"role": "user", "content": "sidste ord"}])
    assert items[-1]["content"][0]["text"] == "sidste ord"


# ── Kilde-vagt: vinkene maa ikke finde vej tilbage til base_messages ─────────


def test_ingen_vink_appendes_til_round_base_messages():
    """AST, ikke grep: en streng-soegning ville ikke kunne se forskel paa
    `_round_base_messages = list(_round_base_messages) + [...]` og en kommentar
    der naevner den. Det var den form fejlen havde.
    """
    kilde = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")
    traeet = ast.parse(kilde)
    syndere = []
    for node in ast.walk(traeet):
        if not isinstance(node, ast.Assign):
            continue
        maal = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "_round_base_messages" not in maal:
            continue
        v = node.value
        if isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add) and isinstance(v.right, ast.List):
            syndere.append(node.lineno)
    assert not syndere, (
        "per-runde-beskeder appendet til _round_base_messages paa linje "
        f"{syndere} — de havner foran hele historikken og braekker cachen")
