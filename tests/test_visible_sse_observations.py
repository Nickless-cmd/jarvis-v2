from core.services.visible_sse_observations import _parse_legacy_sse
from core.services.visible_runs_sse_v2 import _parse_legacy_sse as compatible_parser


def test_legacy_event_parser_preserves_unicode_payload_and_rejects_incomplete_data():
    assert compatible_parser is _parse_legacy_sse
    assert _parse_legacy_sse('event: delta\ndata: {"delta": "Bjørn"}\n\n') == ('delta', {'delta': 'Bjørn'})
    assert _parse_legacy_sse('event: delta\ndata: not-json\n\n') is None
    assert _parse_legacy_sse('event: delta\ndata: {}') is None
