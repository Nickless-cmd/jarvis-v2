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
    assert any('"O"' in chunk for chunk in events[index+1:])
    payloads = [json.loads(chunk.split('data: ')[1]) for chunk in events if chunk.startswith('event: delta\n')]
    assert ''.join(p['delta'] for p in payloads) == 'Synthesis\nOK'
