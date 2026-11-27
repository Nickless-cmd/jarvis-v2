from core.services.visible_tool_echo import ToolEchoFilter
from core.services.visible_runs_sse_v2 import ToolEchoFilter as CompatibleFilter


def test_split_tool_echo_is_removed_without_swallowing_normal_prose():
    assert CompatibleFilter is ToolEchoFilter
    f = ToolEchoFilter(['bash'])
    assert f.feed('[ba') == ''
    assert f.feed('sh]: internal output\nThe answer') == 'The answer'
    assert f.flush() == ''
    assert f.feed('\n[ordinary]: a reference\n') == '\n[ordinary]: a reference\n'
