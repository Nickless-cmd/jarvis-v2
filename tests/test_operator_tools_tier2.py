"""Smoke tests for tier-2 operator tools: speak, screenshot_window, find_image, ocr_region.

Tests the Python-side wrappers and exec stubs, mocking the bridge call.
Full E2E tests require a running JarvisX Electron with espeak-ng / tesseract / imagemagick.
"""

from unittest.mock import AsyncMock, patch
import pytest


# ── helpers ──────────────────────────────────────────────────────────────

def _patch_bridge(return_value: dict):
    """Patch _bridge_call in operator_tools with an AsyncMock."""
    return patch(
        "core.tools.operator_tools._bridge_call",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── operator_speak ────────────────────────────────────────────────────────

def test_speak_dispatches():
    from core.tools.simple_tools import _exec_operator_speak
    with _patch_bridge({"spoken": True, "length": 5}) as mock:
        result = _exec_operator_speak({"_runtime_user_id": "test-user", "text": "hello"})
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_speak"
        assert kwargs.get("args", {}).get("text") == "hello"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("spoken") is True


def test_speak_default_rate():
    from core.tools.simple_tools import _exec_operator_speak
    with _patch_bridge({"spoken": True, "length": 3}) as mock:
        _exec_operator_speak({"_runtime_user_id": "test-user", "text": "hey"})
        args_sent = mock.call_args.kwargs.get("args", {})
        # Default rate is 5.
        assert args_sent.get("rate") == 5


def test_speak_rate_clamped():
    from core.tools.simple_tools import _exec_operator_speak
    with _patch_bridge({"spoken": True, "length": 2}) as mock:
        _exec_operator_speak({"_runtime_user_id": "test-user", "text": "hi", "rate": 99})
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("rate") == 10  # clamped to max 10

    with _patch_bridge({"spoken": True, "length": 2}) as mock:
        _exec_operator_speak({"_runtime_user_id": "test-user", "text": "hi", "rate": -5})
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("rate") == 0  # clamped to min 0


def test_speak_optional_voice():
    from core.tools.simple_tools import _exec_operator_speak
    with _patch_bridge({"spoken": True, "length": 2}) as mock:
        _exec_operator_speak({"_runtime_user_id": "test-user", "text": "hi", "voice": "en-us"})
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("voice") == "en-us"


def test_speak_requires_text():
    from core.tools.simple_tools import _exec_operator_speak
    result = _exec_operator_speak({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "text" in result.get("error", "").lower()


def test_speak_requires_nonempty_text():
    from core.tools.simple_tools import _exec_operator_speak
    result = _exec_operator_speak({"_runtime_user_id": "test-user", "text": ""})
    assert result.get("status") == "error"


# ── operator_screenshot_window ────────────────────────────────────────────

def test_screenshot_window_by_title():
    from core.tools.simple_tools import _exec_operator_screenshot_window
    with _patch_bridge({"captured": True, "base64": "abc123"}) as mock:
        result = _exec_operator_screenshot_window(
            {"_runtime_user_id": "test-user", "title_substring": "Firefox"}
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_screenshot_window"
        assert kwargs.get("args", {}).get("title_substring") == "Firefox"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("captured") is True


def test_screenshot_window_by_handle():
    from core.tools.simple_tools import _exec_operator_screenshot_window
    with _patch_bridge({"captured": True, "base64": "def456"}) as mock:
        _exec_operator_screenshot_window(
            {"_runtime_user_id": "test-user", "handle": "0x00400003"}
        )
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("handle") == "0x00400003"


def test_screenshot_window_with_save_path():
    from core.tools.simple_tools import _exec_operator_screenshot_window
    with _patch_bridge({"captured": True, "path": "/tmp/test.png"}) as mock:
        _exec_operator_screenshot_window(
            {"_runtime_user_id": "test-user", "title_substring": "App", "save_path": "/tmp/test.png"}
        )
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("save_path") == "/tmp/test.png"


def test_screenshot_window_requires_title_or_handle():
    from core.tools.simple_tools import _exec_operator_screenshot_window
    result = _exec_operator_screenshot_window({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "title_substring" in result.get("error", "") or "handle" in result.get("error", "")


# ── operator_find_image ───────────────────────────────────────────────────

def test_find_image_dispatches():
    from core.tools.simple_tools import _exec_operator_find_image
    with _patch_bridge({"found": True, "x": 100, "y": 200, "confidence": 0.92}) as mock:
        result = _exec_operator_find_image(
            {"_runtime_user_id": "test-user", "template_path": "/tmp/icon.png"}
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_find_image"
        assert kwargs.get("args", {}).get("template_path") == "/tmp/icon.png"
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("found") is True
    assert result.get("result", {}).get("x") == 100


def test_find_image_default_confidence():
    from core.tools.simple_tools import _exec_operator_find_image
    with _patch_bridge({"found": False, "reason": "no match"}) as mock:
        _exec_operator_find_image({"_runtime_user_id": "test-user", "template_path": "/tmp/x.png"})
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("confidence") == pytest.approx(0.85)


def test_find_image_confidence_clamped():
    from core.tools.simple_tools import _exec_operator_find_image
    with _patch_bridge({"found": False, "reason": "no match"}) as mock:
        _exec_operator_find_image(
            {"_runtime_user_id": "test-user", "template_path": "/tmp/x.png", "confidence": 1.5}
        )
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("confidence") == pytest.approx(1.0)


def test_find_image_requires_template_path():
    from core.tools.simple_tools import _exec_operator_find_image
    result = _exec_operator_find_image({"_runtime_user_id": "test-user"})
    assert result.get("status") == "error"
    assert "template_path" in result.get("error", "").lower()


# ── operator_ocr_region ───────────────────────────────────────────────────

def test_ocr_region_dispatches():
    from core.tools.simple_tools import _exec_operator_ocr_region
    with _patch_bridge({"text": "Hello world", "region": {"x": 10, "y": 20, "width": 300, "height": 100}}) as mock:
        result = _exec_operator_ocr_region(
            {"_runtime_user_id": "test-user", "x": 10, "y": 20, "width": 300, "height": 100}
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_ocr_region"
        args_sent = kwargs.get("args", {})
        assert args_sent.get("x") == 10
        assert args_sent.get("y") == 20
        assert args_sent.get("width") == 300
        assert args_sent.get("height") == 100
    assert result.get("status") == "ok"
    assert result.get("result", {}).get("text") == "Hello world"


def test_ocr_region_default_lang():
    from core.tools.simple_tools import _exec_operator_ocr_region
    with _patch_bridge({"text": "foo", "region": {}}) as mock:
        _exec_operator_ocr_region(
            {"_runtime_user_id": "test-user", "x": 0, "y": 0, "width": 100, "height": 50}
        )
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("lang") == "eng"


def test_ocr_region_custom_lang():
    from core.tools.simple_tools import _exec_operator_ocr_region
    with _patch_bridge({"text": "hej verden", "region": {}}) as mock:
        _exec_operator_ocr_region(
            {"_runtime_user_id": "test-user", "x": 0, "y": 0, "width": 200, "height": 80, "lang": "dan"}
        )
        args_sent = mock.call_args.kwargs.get("args", {})
        assert args_sent.get("lang") == "dan"


def test_ocr_region_requires_coords():
    from core.tools.simple_tools import _exec_operator_ocr_region
    result = _exec_operator_ocr_region({"_runtime_user_id": "test-user", "x": 0, "y": 0})
    assert result.get("status") == "error"
    assert "width" in result.get("error", "").lower() or "height" in result.get("error", "").lower()


def test_ocr_region_rejects_zero_dimensions():
    from core.tools.simple_tools import _exec_operator_ocr_region
    result = _exec_operator_ocr_region(
        {"_runtime_user_id": "test-user", "x": 0, "y": 0, "width": 0, "height": 100}
    )
    assert result.get("status") == "error"
    assert "positive" in result.get("error", "").lower()


# ── async wrappers (operator_tools.py) ───────────────────────────────────

@pytest.mark.asyncio
async def test_speak_async_passes_args():
    from core.tools.operator_tools import operator_speak_async
    with _patch_bridge({"spoken": True, "length": 5}) as mock:
        result = await operator_speak_async(text="hello", user_id="test-user", voice="en-gb", rate=7)
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_speak"
        assert kwargs.get("args", {}).get("text") == "hello"
        assert kwargs.get("args", {}).get("voice") == "en-gb"
        assert kwargs.get("args", {}).get("rate") == 7
    assert result.get("spoken") is True


@pytest.mark.asyncio
async def test_screenshot_window_async_passes_args():
    from core.tools.operator_tools import operator_screenshot_window_async
    with _patch_bridge({"captured": True, "base64": "xyz"}) as mock:
        result = await operator_screenshot_window_async(
            user_id="test-user", title_substring="Chrome", save_path="/tmp/out.png"
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_screenshot_window"
        assert kwargs.get("args", {}).get("title_substring") == "Chrome"
        assert kwargs.get("args", {}).get("save_path") == "/tmp/out.png"
    assert result.get("captured") is True


@pytest.mark.asyncio
async def test_find_image_async_passes_args():
    from core.tools.operator_tools import operator_find_image_async
    with _patch_bridge({"found": True, "x": 50, "y": 60, "confidence": 0.9}) as mock:
        result = await operator_find_image_async(
            template_path="/home/user/btn.png", user_id="test-user", confidence=0.9
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_find_image"
        assert kwargs.get("args", {}).get("template_path") == "/home/user/btn.png"
        assert kwargs.get("args", {}).get("confidence") == pytest.approx(0.9)
    assert result.get("found") is True


@pytest.mark.asyncio
async def test_ocr_region_async_passes_args():
    from core.tools.operator_tools import operator_ocr_region_async
    with _patch_bridge({"text": "OCR result", "region": {"x": 5, "y": 5, "width": 100, "height": 50}}) as mock:
        result = await operator_ocr_region_async(
            x=5, y=5, width=100, height=50, user_id="test-user", lang="dan"
        )
        assert mock.called
        kwargs = mock.call_args.kwargs
        assert kwargs.get("tool") == "operator_ocr_region"
        args_sent = kwargs.get("args", {})
        assert args_sent.get("x") == 5
        assert args_sent.get("lang") == "dan"
    assert result.get("text") == "OCR result"
