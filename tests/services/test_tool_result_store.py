from core.services.tool_result_store import (
    build_tool_result_reference, render_tool_result_for_prompt,
)


def test_stub_render_is_one_line_from_reference():
    ref = build_tool_result_reference(
        "tool-result-abc", tool_name="bash",
        summary="line1\nline2\nline3 lots of output here")
    stub = render_tool_result_for_prompt(ref, expand=False, stub=True)
    assert "tool-result-abc" in stub
    assert "bash" in stub
    assert "read_tool_result" in stub
    assert "\n" not in stub
    assert len(stub) < 120


def test_stub_is_byte_stable_without_disk():
    ref = build_tool_result_reference(
        "tool-result-nonexistent-xyz", tool_name="read_file",
        summary="content summary")
    a = render_tool_result_for_prompt(ref, expand=False, stub=True)
    b = render_tool_result_for_prompt(ref, expand=False, stub=True)
    assert a == b
    assert "tool-result-nonexistent-xyz" in a
