from __future__ import annotations
from central_cli import config


def test_base_url_precedence(monkeypatch, tmp_path):
    monkeypatch.delenv("CENTRAL_CLI_API_URL", raising=False)
    assert config.resolve_base_url(remote=None) == "https://api.srvlab.dk"
    assert config.resolve_base_url(remote="http://10.0.0.39:8080") == "http://10.0.0.39:8080"
    monkeypatch.setenv("CENTRAL_CLI_API_URL", "http://env:9000")
    assert config.resolve_base_url(remote=None) == "http://env:9000"


def test_token_reads_jc_file(monkeypatch, tmp_path):
    monkeypatch.delenv("CENTRAL_CLI_TOKEN", raising=False)
    jc = tmp_path / "jarvis-owner-token"
    jc.write_text("TOK-123\n")
    monkeypatch.setattr(config, "_JC_TOKEN_PATH", jc)
    assert config.resolve_token() == "TOK-123"
    monkeypatch.setenv("CENTRAL_CLI_TOKEN", "ENVTOK")
    assert config.resolve_token() == "ENVTOK"


def test_token_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("CENTRAL_CLI_TOKEN", raising=False)
    monkeypatch.setattr(config, "_JC_TOKEN_PATH", tmp_path / "nope")
    assert config.resolve_token() is None
