"""Tests for scripts/block_literal_credentials.py.

Regressionsværn: et 8-tegns mail-kodeord i en modulkonstant slap forbi
detect-secrets og førte til at kontoen blev misbrugt af tredjepart. Hooken må
aldrig holde op med at fange netop den form.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "block_literal_credentials.py"
_spec = importlib.util.spec_from_file_location("block_literal_credentials", _SCRIPT)
blc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(blc)


# --- skal fanges -----------------------------------------------------------

@pytest.mark.parametrize(
    "line",
    [
        'MAIL_PASS = "abc12345"',                    # den ægte lækage, ordret form
        "password = 's3cret99'",  # pragma: allowlist secret
        'db_password = "hunter22"',  # pragma: allowlist secret
        'api_key = "AKIA1234567890AB"',  # pragma: allowlist secret
        'client_secret = "9f3a2b1c8d"',  # pragma: allowlist secret
        '"api_key": "AKIA1234567890AB"',  # pragma: allowlist secret
        'ACCESS_TOKEN = "ya29.abcdefghij"',  # pragma: allowlist secret
        'const apiKey = "AKIA1234567890AB"',  # pragma: allowlist secret
    ],
)
def test_flags_literal_credentials(line: str) -> None:
    assert blc._suspicious(line) is not None, line


def test_flags_the_historical_leak_shape() -> None:
    """Præcis formen der slap igennem sidst: kort, lowercase, alfanumerisk."""
    hit = blc._suspicious('MAIL_PASS = "qwer1234"')
    assert hit is not None
    name, value = hit
    assert name == "MAIL_PASS"
    assert len(value) == 8


# --- må IKKE fanges --------------------------------------------------------

@pytest.mark.parametrize(
    "line",
    [
        'provider_first_pass_status = "completed"',   # "pass" = en runde
        'bypass_cache = "always"',  # pragma: allowlist secret
        'sort_key = "created_at"',  # pragma: allowlist secret
        '_DEFAULT_TOKEN_URL = "https://example.com/token"',  # pragma: allowlist secret
        '_INTERNAL_TOKEN_HEADER = "X-Jarvis-Token"',  # pragma: allowlist secret
        '_TOKEN_ENV_KEY = "CLAUDE_CODE_OAUTH_TOKEN"',  # pragma: allowlist secret
        'password = os.environ["PW"]',  # pragma: allowlist secret
        'db_password = read_runtime_key("db_password")',  # pragma: allowlist secret
        'password = ""',  # pragma: allowlist secret
        'password = "changeme"',  # pragma: allowlist secret
        'password = "your-password-here"',  # pragma: allowlist secret
        '"bot_token": "[set]"',  # pragma: allowlist secret
        'legacy_pass = "abc12345"  # noqa: literal-credential',  # pragma: allowlist secret
        '_SECRET_KEY = "jarvisx_auth_secret"  # pragma: allowlist secret',
        "{confirm ? 'Sikker? Slet token' : 'Afbryd & slet'}",   # ternary, ikke tildeling
    ],
)
def test_ignores_non_credentials(line: str) -> None:
    assert blc._suspicious(line) is None, line


# --- navne-analyse ---------------------------------------------------------

@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("MAIL_PASS", True),
        ("mailPass", True),
        ("password", True),
        ("api_key", True),
        ("encryption_key", True),
        ("cache_key", False),
        ("sort_key", False),
        ("provider_first_pass_status", False),
        ("bypass", False),
        ("token_url", False),
    ],
)
def test_is_credential_name(name: str, expected: bool) -> None:
    assert blc._is_credential_name(name) is expected


def test_reports_never_include_the_value(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Rapporten må aldrig lække selve hemmeligheden videre i CI-log."""
    f = tmp_path / "leaky.py"
    f.write_text('MAIL_PASS = "topsecret1"\n', encoding="utf-8")
    assert blc.check([str(f)]) == 1
    err = capsys.readouterr().err
    assert "topsecret1" not in err
    assert "MAIL_PASS" in err
    assert "10 tegn" in err


def test_clean_file_passes(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text('pw = read_runtime_key("mail_password")\n', encoding="utf-8")
    assert blc.check([str(f)]) == 0
