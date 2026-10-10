from __future__ import annotations

from core.tools.streaming_subprocess import run_streaming


def test_streaming_subprocess_preserves_split_utf8_and_final_streams(tmp_path):
    seen = []
    result = run_streaming(
        [
            "python",
            "-c",
            "import os,time; os.write(1,b'\\xc3'); time.sleep(.03); "
            "os.write(1,b'\\xa6\\n'); os.write(2,b'fejl\\n')",
        ],
        cwd=str(tmp_path),
        timeout_s=2,
        on_output=lambda stream, chunk: seen.append((stream, chunk)),
    )
    assert result.stdout == "æ\n"
    assert result.stderr == "fejl\n"
    assert "".join(chunk for stream, chunk in seen if stream == "stdout") == "æ\n"
    assert result.first_output_ms is not None
    assert result.timed_out is False


def test_callback_failure_never_changes_final_result(tmp_path):
    def broken(_stream, _chunk):
        raise RuntimeError("projection failed")

    result = run_streaming(
        ["bash", "-c", "printf ok"],
        cwd=str(tmp_path),
        timeout_s=2,
        on_output=broken,
    )
    assert result.stdout == "ok"
    assert result.exit_code == 0


def test_timeout_returns_collected_output(tmp_path):
    result = run_streaming(
        ["bash", "-c", "printf before; sleep 2"],
        cwd=str(tmp_path),
        timeout_s=0.1,
        on_output=None,
    )
    assert result.timed_out is True
    assert result.stdout == "before"
