from unittest.mock import patch
from core.services.structured_content_flag import structured_content_v2_enabled


def test_defaults_to_on_when_unset():
    with patch("core.services.structured_content_flag._read_flag", return_value=None):
        assert structured_content_v2_enabled() is True


def test_off_when_explicitly_disabled():
    with patch("core.services.structured_content_flag._read_flag", return_value="off"):
        assert structured_content_v2_enabled() is False


def test_on_when_explicitly_enabled():
    with patch("core.services.structured_content_flag._read_flag", return_value="on"):
        assert structured_content_v2_enabled() is True


def test_read_error_defaults_on():
    with patch("core.services.structured_content_flag._read_flag", side_effect=RuntimeError("db nede")):
        assert structured_content_v2_enabled() is True
