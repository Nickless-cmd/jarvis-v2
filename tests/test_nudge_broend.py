"""nudge_broend.push: dual-write passerer 'kind' igennem til outbound-ledger (så
Matrix-karakter-nudges bevarer kind='matrix_character' i stedet for at blive mærket
'action_router')."""
from core.services import nudge_broend as nb


def _isolate(monkeypatch, captured):
    monkeypatch.setattr(nb, "_save", lambda x: None)
    monkeypatch.setattr(nb, "_load", lambda: [])
    monkeypatch.setattr("core.services.outbound_nudges.push_nudge",
                        lambda **kw: captured.update(kw))


def test_push_passes_kind_to_outbound(monkeypatch):
    cap = {}
    _isolate(monkeypatch, cap)
    nb.push(source="matrix/smith", kind="matrix_character", message="hej", importance="normal")
    assert cap.get("kind") == "matrix_character"


def test_push_defaults_kind_for_plain_info(monkeypatch):
    cap = {}
    _isolate(monkeypatch, cap)
    nb.push(source="x", kind="info", message="m")
    assert cap.get("kind") == "action_router"   # "info"/tom → fallback
