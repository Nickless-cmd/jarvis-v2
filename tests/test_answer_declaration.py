"""Observed erroneous opening, checked across every token split."""
import pytest
from core.services.answer_declaration import AnswerDeclarationStream
from core.services.code_answer_boundary import ANSWER_MARKER, mark_code_answer_start

OPENING = 'Nu skal jeg måle, ikke bygge. Tre ting skal bevises.'
ANSWER = 'Koblingen virker; her er de målte resultater.'

@pytest.mark.parametrize('split', range(len(OPENING) + 1))
def test_work_opening_is_vetoed_before_any_boundary_is_emitted(split):
    parser = AnswerDeclarationStream()
    events = parser.feed(ANSWER_MARKER + '\n' + OPENING[:split])
    events += parser.feed(OPENING[split:]) + parser.flush()
    assert not any(k == 'answer_start' for k, _ in events)
    assert ''.join(v for k, v in events if k == 'text') == '\n' + OPENING
    assert parser.rejected == 1

@pytest.mark.parametrize('answer', ['Ja.', 'OK', 'Nu', 'Jeg har målt processen.', 'Jeg vil anbefale Python.', 'Du skal teste funktionen.'])
def test_short_answers_and_outcome_prose_keep_their_explicit_boundary(answer):
    parser = AnswerDeclarationStream()
    events = [event for char in ANSWER_MARKER + '\n' + answer for event in parser.feed(char)] + parser.flush()
    assert sum(k == 'answer_start' for k, _ in events) == 1
    assert ''.join(v for k, v in events if k == 'text') == '\n' + answer

@pytest.mark.parametrize('chunked', [False, True])
def test_a_corrected_declaration_can_follow_a_rejected_one_in_the_same_segment(chunked):
    raw = ANSWER_MARKER + '\n' + OPENING + '\n' + ANSWER_MARKER + '\n' + ANSWER
    parser = AnswerDeclarationStream()
    events = [event for chunk in (list(raw) if chunked else [raw]) for event in parser.feed(chunk)] + parser.flush()
    index = next(i for i, (kind, _) in enumerate(events) if kind == 'answer_start')
    assert OPENING in ''.join(v for k, v in events[:index] if k == 'text')
    assert ANSWER in ''.join(v for k, v in events[index:] if k == 'text')
    assert sum(k == 'answer_start' for k, _ in events) == 1


def test_persistence_rejects_the_opening_and_keeps_answer_before_late_tools():
    blocks = [
        {'type': 'text', 'text': ANSWER_MARKER + '\n' + OPENING},
        {'type': 'tool_use', 'id': 'check'},
        {'type': 'text', 'text': ANSWER_MARKER + '\n' + ANSWER},
        {'type': 'tool_use', 'id': 'late'},
        {'type': 'text', 'text': 'Sen syntese.'},
    ]
    mark_code_answer_start(blocks)
    assert not blocks[0].get('code_answer_start')
    assert blocks[2]['code_answer_start'] and blocks[2]['code_answer_source'] == 'explicit'
    assert not blocks[-1].get('code_answer_start')
    assert all(ANSWER_MARKER not in b.get('text', '') for b in blocks)
