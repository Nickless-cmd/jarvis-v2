from __future__ import annotations

import pytest
from core.services.code_answer_boundary import ANSWER_MARKER, AnswerMarkerStream, mark_code_answer_start


def scan(chunks):
    parser = AnswerMarkerStream()
    events = [event for chunk in chunks for event in parser.feed(chunk)] + parser.flush()
    return ''.join(v for k, v in events if k == 'text'), sum(k == 'answer_start' for k, _ in events)


@pytest.mark.parametrize('split', range(len(ANSWER_MARKER) + 1))
def test_marker_never_leaks_at_any_token_split(split):
    text, starts = scan(['Commentary\n', ANSWER_MARKER[:split], ANSWER_MARKER[split:] + '\nShort answer'])
    assert text == 'Commentary\n\nShort answer'
    assert starts == 1


def test_quoted_inline_and_fenced_markers_are_literal():
    text = f'`{ANSWER_MARKER}`\n> {ANSWER_MARKER}\n```text\n{ANSWER_MARKER}\n```\n'
    assert scan(list(text)) == (text, 0)


def test_duplicate_declaration_cannot_move_the_boundary():
    text, starts = scan([ANSWER_MARKER + '\nA\n' + ANSWER_MARKER + '\nB'])
    assert text == '\nA\n\nB'
    assert starts == 1


def test_persistence_splits_commentary_and_answer_in_same_segment():
    blocks = [{'type': 'tool_use', 'id': 't'}, {'type': 'text', 'text': 'Long commentary ' * 50 + '\n' + ANSWER_MARKER + '\nOK'}, {'type': 'tool_use', 'id': 'late'}, {'type': 'text', 'text': 'Saved'}]
    mark_code_answer_start(blocks)
    texts = [b for b in blocks if b['type'] == 'text']
    assert 'code_answer_start' not in texts[0]
    assert texts[1]['code_answer_start'] is True
    assert texts[1]['text'].strip() == 'OK'
    assert texts[1]['code_answer_source'] == 'explicit'
    assert texts[2]['text'] == 'Saved'
    before = [dict(b) for b in blocks]
    mark_code_answer_start(blocks)
    assert blocks == before


def test_marker_free_long_commentary_never_becomes_answer_by_length():
    blocks = [{'type': 'tool_use', 'id': 't'}, {'type': 'text', 'text': 'Commentary ' * 500}, {'type': 'tool_use', 'id': 'late'}, {'type': 'text', 'text': 'OK'}]
    mark_code_answer_start(blocks)
    assert not blocks[1].get('code_answer_start')
    assert blocks[-1]['code_answer_start']
    assert blocks[-1]['code_answer_source'] == 'terminal'




def test_truncated_internal_declaration_is_not_leaked_on_stop():
    assert scan(['Readable\n[[jarvis:ans']) == ('Readable\n', 0)


def test_longer_and_indented_fences_keep_markers_literal():
    for text in [f'````text\n```\n{ANSWER_MARKER}\n````\n', f'   ~~~text\n{ANSWER_MARKER}\n   ~~~\n']:
        assert scan(list(text)) == (text, 0)
