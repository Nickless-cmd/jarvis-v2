"""Tests for core.services.dictation — diktering-transskription.

faster-whisper mockes, så vi tester glue-logikken (segment-join, config-
default, fejl-håndtering) uden at loade en rigtig model.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import core.services.dictation as d


def _seg(text):
    return SimpleNamespace(text=text)


class TestJoinSegments:

    def test_joins_and_strips(self):
        segs = [_seg("  Hej "), _seg(" Bjørn.")]
        assert d._join_segments(segs) == "Hej Bjørn."

    def test_empty(self):
        assert d._join_segments([]) == ""


class TestResolveModelSize:

    def test_explicit_wins(self):
        assert d._resolve_model_size("medium") == "medium"

    def test_default_when_none(self, monkeypatch):
        monkeypatch.setattr(d, "read_runtime_key", None, raising=False)
        # Ingen runtime-nøgle → default "small"
        with mock.patch("core.runtime.secrets.read_runtime_key", return_value=None):
            assert d._resolve_model_size(None) == "small"


class TestTranscribeFile:

    def setup_method(self):
        d._model_cache.clear()

    def test_happy_path(self):
        fake_info = SimpleNamespace(language="da")
        fake_model = mock.Mock()
        fake_model.transcribe.return_value = ([_seg("hej"), _seg("verden")], fake_info)
        with mock.patch.object(d, "_get_model", return_value=fake_model):
            out = d.transcribe_file("/tmp/x.webm")
        assert out["status"] == "ok"
        assert out["text"] == "hej verden"
        assert out["language"] == "da"

    def test_error_handled(self):
        with mock.patch.object(d, "_get_model", side_effect=RuntimeError("boom")):
            out = d.transcribe_file("/tmp/x.webm")
        assert out["status"] == "error"
        assert out["text"] == ""
        assert "boom" in out["error"]

    def test_model_cached(self):
        fake_model = mock.Mock()
        fake_model.transcribe.return_value = ([], SimpleNamespace(language="en"))
        with mock.patch("faster_whisper.WhisperModel", return_value=fake_model) as ctor:
            d.transcribe_file("/tmp/a.webm", model_size="small")
            d.transcribe_file("/tmp/b.webm", model_size="small")
        assert ctor.call_count == 1  # cachet på (size, device, compute_type)
