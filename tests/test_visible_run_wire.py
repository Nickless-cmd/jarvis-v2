import json
import pytest
from core.services.code_answer_boundary import ANSWER_MARKER
from core.services.visible_run_wire import _sse, explicit_answer_stream


@pytest.mark.asyncio
async def test_wire_emits_boundary_before_answer_and_cleans_all_consumers():
    @explicit_answer_stream
    async def source():
        yield _sse('delta', {'run_id': 'r', 'delta': 'Synthesis'})
        yield _sse('working_step', {'action': 'thinking'})
        for char in ANSWER_MARKER + '\nOK':
            yield _sse('delta', {'run_id': 'r', 'delta': char})
        yield _sse('done', {'text': ANSWER_MARKER + '\nOK', 'status': 'completed'})
    events = [chunk async for chunk in source()]
    assert sum('event: answer_start\n' in chunk for chunk in events) == 1
    assert not any(ANSWER_MARKER in chunk for chunk in events)
    index = next(i for i, chunk in enumerate(events) if 'event: answer_start\n' in chunk)
    answer_deltas = [json.loads(chunk.split('data: ')[1])['delta'] for chunk in events[index+1:] if chunk.startswith('event: delta\n')]
    assert ''.join(answer_deltas).lstrip() == 'OK'
    payloads = [json.loads(chunk.split('data: ')[1]) for chunk in events if chunk.startswith('event: delta\n')]
    assert ''.join(p['delta'] for p in payloads) == 'Synthesis\nOK'


@pytest.mark.asyncio
async def test_work_marker_does_not_fold_and_real_answer_can_precede_late_work():
    @explicit_answer_stream
    async def source():
        yield _sse('delta', {'run_id': 'r', 'delta': ANSWER_MARKER + '\nNu skal jeg måle, ikke bygge.'})
        yield _sse('working_step', {'action': 'thinking'})
        yield _sse('tool_use', {'id': 'check'})
        for char in ANSWER_MARKER + '\nKoblingen virker.':
            yield _sse('delta', {'run_id': 'r', 'delta': char})
        yield _sse('tool_use', {'id': 'late'})
        yield _sse('delta', {'run_id': 'r', 'delta': 'Sen syntese.'})
        yield _sse('done', {'status': 'completed'})
    events = [chunk async for chunk in source()]
    boundary = next(i for i, chunk in enumerate(events) if chunk.startswith('event: answer_start'))
    check = next(i for i, chunk in enumerate(events) if '"check"' in chunk)
    late = next(i for i, chunk in enumerate(events) if '"late"' in chunk)
    assert check < boundary < late
    assert sum(chunk.startswith('event: answer_start') for chunk in events) == 1
    assert not any(ANSWER_MARKER in chunk for chunk in events)
