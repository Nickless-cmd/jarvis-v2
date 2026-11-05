"""Kvote-læseren: tal når den kan måle, en grund når den ikke kan."""
from __future__ import annotations

import json
import time
import urllib.error
from datetime import datetime, timedelta

import pytest

from core.services import dispatch_quota

# Målt 4/11-2026 mod det ægte endpoint (HTTP 200), forkortet til de felter
# læseren bruger. Formen er kopieret, ikke opfundet.
CLAUDE_PAYLOAD = {
    "five_hour": {
        "utilization": 100.0,
        "resets_at": "2026-11-04T22:29:59.625524+00:00",
    },
    "seven_day": {
        "utilization": 14.0,
        "resets_at": "2026-11-09T00:59:59.625547+00:00",
    },
}


class _Resp:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    dispatch_quota.reset_cache()
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")
    # Testene maa ikke laane maskinens EGEN credentials-fil: den findes paa
    # CheifOne og er udloebet, saa uden denne linje afhaenger resultatet af
    # hvilken maskine suiten koerer paa. Maalt 4/11-2026.
    monkeypatch.setattr(dispatch_quota, "_CLAUDE_CREDENTIALS_FILE",
                        str(tmp_path / "ingen-credentials.json"))
    yield
    dispatch_quota.reset_cache()


def _patch_urlopen(monkeypatch, payload=None, error=None):
    seen: list[object] = []

    def fake(request, timeout=None):
        seen.append(request)
        if error is not None:
            raise error
        return _Resp(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake)
    return seen


# ── Claude ─────────────────────────────────────────────────────────────────

def test_claude_quota_laeser_baade_vinduer(monkeypatch):
    _patch_urlopen(monkeypatch, CLAUDE_PAYLOAD)

    reading = dispatch_quota.claude_quota()

    assert reading.ok is True
    assert reading.get("five_hour_pct") == 100.0
    assert reading.get("seven_day_pct") == 14.0
    assert reading.get("five_hour_resets_at").startswith("2026-11-04T22:29")
    assert reading.get("seven_day_resets_at").startswith("2026-11-09T00:59")


def test_claude_quota_sender_beta_header(monkeypatch):
    """Uden anthropic-beta er svaret ikke til at stole på — det er målt."""
    seen = _patch_urlopen(monkeypatch, CLAUDE_PAYLOAD)

    dispatch_quota.claude_quota()

    assert seen, "endpointet blev slet ikke kaldt"
    headers = {k.lower(): v for k, v in seen[0].headers.items()}
    assert headers.get("anthropic-beta") == "oauth-2025-04-20"
    assert headers.get("authorization", "").startswith("Bearer ")


def test_claude_quota_uden_token_er_ikke_nul_procent(monkeypatch, tmp_path):
    """Et manglende token må aldrig ligne «0 % brugt»."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(
        dispatch_quota, "_CLAUDE_ENV_FILE", str(tmp_path / "findes-ikke.env")
    )

    reading = dispatch_quota.claude_quota()

    assert reading.ok is False
    assert "CLAUDE_CODE_OAUTH_TOKEN" in reading.error
    assert reading.values == {}


def test_claude_quota_http_401_giver_grund_ikke_tal(monkeypatch):
    err = urllib.error.HTTPError(
        "https://x", 401, "Unauthorized", {}, None,
    )
    _patch_urlopen(monkeypatch, error=err)

    reading = dispatch_quota.claude_quota()

    assert reading.ok is False
    assert "401" in reading.error


def test_claude_quota_401_er_hard_block(monkeypatch):
    """Et afvist token er VIDEN, ikke uvidenhed: `claude -p` fejler med samme
    token, så preflighten skal blokere og spare worktreet.

    Målt 5/11-2026: uden hard_block blev et dødt token meldt som «kunne ikke
    måles» og sluppet igennem, hvorefter dispatchen døde efter sekunder.
    """
    err = urllib.error.HTTPError(
        "https://x", 401, "Unauthorized", {},
        _Resp(b'{"type":"error","error":{"type":"authentication_error"}}'),
    )
    _patch_urlopen(monkeypatch, error=err)

    reading = dispatch_quota.claude_quota()

    assert reading.ok is False
    assert reading.hard_block is True
    preflight = dispatch_quota.quota_preflight("claude")
    assert preflight["allow"] is False
    assert preflight["severity"] == "block"


def test_claude_quota_403_scope_blokerer_ikke(monkeypatch):
    """Et `claude setup-token` har kun inference-scopes.

    Målt 5/11-2026: det kører `claude -p` (svar OK, exit 0), men
    kvote-endpointet kræver `user:profile` og svarer 403. Det er hverken et
    dødt token eller en netværksfejl — så det må ALDRIG blive hard_block, for
    så blokerer preflighten en backend der virker. Beskeden skal navngive
    scopet, så den ikke bliver jagtet som et netværksproblem.
    """
    body = (
        b'{"type":"error","error":{"type":"permission_error",'
        b'"message":"OAuth token does not meet scope requirement user:profile",'
        b'"error_code":"oauth_scope_insufficient"}}'
    )
    err = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, _Resp(body))
    _patch_urlopen(monkeypatch, error=err)

    reading = dispatch_quota.claude_quota()

    assert reading.ok is False
    assert reading.hard_block is False
    assert "user:profile" in reading.error
    preflight = dispatch_quota.quota_preflight("claude")
    assert preflight["allow"] is True
    assert preflight["severity"] == "unknown"


def test_claude_quota_429_blokerer_ikke(monkeypatch):
    """429 fra kvote-endpointet er en rate limit på MÅLINGEN, ikke på kvoten.

    Målt 5/11-2026 efter få kald i træk. Behandlede vi den som «brugt op»,
    blev vagten selv den ting der standsede alt arbejde.
    """
    err = urllib.error.HTTPError(
        "https://x", 429, "Too Many Requests", {},
        _Resp(b'{"type":"error","error":{"type":"rate_limit_error"}}'),
    )
    _patch_urlopen(monkeypatch, error=err)

    reading = dispatch_quota.claude_quota()

    assert reading.ok is False
    assert reading.hard_block is False
    assert dispatch_quota.quota_preflight("claude")["allow"] is True


def test_claude_quota_ikke_json_giver_grund(monkeypatch):
    _patch_urlopen(monkeypatch, payload=None)
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _Resp(b"<html>ikke json</html>")
    )

    reading = dispatch_quota.claude_quota()

    assert reading.ok is False
    assert "JSON" in reading.error


def test_cache_sparer_kald(monkeypatch):
    seen = _patch_urlopen(monkeypatch, CLAUDE_PAYLOAD)

    dispatch_quota.claude_quota()
    second = dispatch_quota.claude_quota()

    assert len(seen) == 1, "cachen blev ikke brugt"
    assert second.cached is True


# ── Codex ──────────────────────────────────────────────────────────────────

def _write_rollout(root, primary, secondary) -> None:
    path = root / "2026" / "11" / "04"
    path.mkdir(parents=True, exist_ok=True)
    event = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "rate_limits": {
                "limit_id": "codex",
                "plan_type": "plus",
                "primary": {
                    "used_percent": primary[0],
                    "window_minutes": 300,
                    "resets_at": primary[1],
                },
                "secondary": {
                    "used_percent": secondary[0],
                    "window_minutes": 10080,
                    "resets_at": secondary[1],
                },
            },
        },
    }
    (path / "rollout-2026-11-04T21-57-29-test.jsonl").write_text(
        json.dumps({"type": "session_meta"}) + "\n" + json.dumps(event) + "\n",
        encoding="utf-8",
    )


def test_codex_quota_laeser_5_timer_og_uge(monkeypatch, tmp_path):
    now = time.time()
    _write_rollout(tmp_path, (61.0, now + 3600), (68.0, now + 86400))
    monkeypatch.setattr(dispatch_quota, "_CODEX_SESSIONS", str(tmp_path))

    reading = dispatch_quota.codex_quota()

    assert reading.ok is True
    assert reading.get("primary_pct") == 61.0
    assert reading.get("primary_window_minutes") == 300
    assert reading.get("secondary_pct") == 68.0
    assert reading.get("secondary_window_minutes") == 10080


def test_codex_quota_udloebet_vindue_nulstilles(monkeypatch, tmp_path):
    """Er reset-tidspunktet passeret, er vinduet nulstillet — aritmetik, ikke gæt."""
    now = time.time()
    _write_rollout(tmp_path, (99.0, now - 60), (68.0, now + 86400))
    monkeypatch.setattr(dispatch_quota, "_CODEX_SESSIONS", str(tmp_path))

    reading = dispatch_quota.codex_quota()

    assert reading.ok is True
    assert reading.get("primary_pct") == 0.0
    assert reading.get("primary_expired") is True
    assert reading.get("secondary_pct") == 68.0


def test_codex_quota_uden_rollout_giver_grund(monkeypatch, tmp_path):
    monkeypatch.setattr(dispatch_quota, "_CODEX_SESSIONS", str(tmp_path))

    reading = dispatch_quota.codex_quota()

    assert reading.ok is False
    assert "rollout" in reading.error


def test_codex_quota_uden_rate_limits_giver_grund(monkeypatch, tmp_path):
    path = tmp_path / "2026" / "11" / "04"
    path.mkdir(parents=True)
    (path / "rollout-2026-11-04T21-57-29-test.jsonl").write_text(
        json.dumps({"type": "session_meta"}) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(dispatch_quota, "_CODEX_SESSIONS", str(tmp_path))

    reading = dispatch_quota.codex_quota()

    assert reading.ok is False
    assert "rate_limits" in reading.error


# ── Preflight ──────────────────────────────────────────────────────────────

def test_preflight_blokerer_ved_hundrede_procent(monkeypatch):
    _patch_urlopen(monkeypatch, CLAUDE_PAYLOAD)

    result = dispatch_quota.quota_preflight("claude")

    assert result["allow"] is False
    assert result["severity"] == "block"
    assert "100" in result["reason"]


def test_preflight_advarer_men_slipper_igennem_ved_halvfems(monkeypatch):
    payload = {
        "five_hour": {"utilization": 92.0, "resets_at": "2026-11-04T22:29:59+00:00"},
        "seven_day": {"utilization": 10.0, "resets_at": "2026-11-09T00:59:59+00:00"},
    }
    _patch_urlopen(monkeypatch, payload)

    result = dispatch_quota.quota_preflight("claude")

    assert result["allow"] is True
    assert result["severity"] == "warn"


def test_preflight_fail_open_naar_kvoten_ikke_kan_maales(monkeypatch, tmp_path):
    """En målefejl er ikke et bevis for at kvoten er brugt."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(
        dispatch_quota, "_CLAUDE_ENV_FILE", str(tmp_path / "findes-ikke.env")
    )

    result = dispatch_quota.quota_preflight("claude")

    assert result["allow"] is True
    assert result["severity"] == "unknown"


def test_preflight_standser_foer_worktree_oprettes(monkeypatch):
    """Uden denne test kan preflight-blokken fjernes uden at nogen test fejler."""
    import core.tools.claude_dispatch.runner as runner
    from core.tools.claude_dispatch.spec import TaskSpec
    monkeypatch.delenv("JARVIS_DISPATCH_PREFLIGHT", raising=False)
    monkeypatch.setattr(runner, "quota_preflight", lambda b: {
        "allow": False, "severity": "block", "pct": 100.0,
        "reason": "100 % af 5-timers-kvoten er brugt",
        "resets_at": "2026-11-04T22:30:00+00:00", "reading": None})
    def _spraeng(task_id):
        raise AssertionError("worktree oprettet trods blokerende kvote")
    monkeypatch.setattr(runner, "create_worktree", _spraeng)
    monkeypatch.setattr(runner, "start_audit_row", lambda *a, **k: None)
    skrevet = {}
    monkeypatch.setattr(runner, "finalize_audit_row", lambda *a, **k: skrevet.update(k))
    class _B:
        def check_and_reserve(self): pass
    monkeypatch.setattr(runner, "BudgetTracker", _B)
    class _Bus:
        def publish(self, *a, **k): pass
    spec = TaskSpec(goal="g", scope_files=("a.py",), allowed_tools=())
    res = runner.run_dispatch(spec, _Bus())
    assert res["failure_kind"] == "quota_exhausted"
    assert res["status"] == "error" and res["needs_human"] is False
    assert skrevet.get("failure_kind") == "quota_exhausted"


# ── «Opbrugt» skal læses som opbrugt, ikke som nul ───────────────────────────
# Målt 4/11-2026 på CheifOne: codex' rate_limits havde primary=null og
# secondary=null, credits.balance="0", og den seneste task_complete bar
# «You've hit your usage limit … try again at Nov 5th, 2026 2:09 AM».
# Læseren tog null for 0 % og preflighten svarede «tillad». Det er den
# fejlform der ser ud som en måling uden at være det.

_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _codex_limit_label(moment: "datetime") -> str:
    """Samme form codex selv skriver — bygget uden locale-afhaengighed."""
    hour12 = moment.hour % 12 or 12
    ampm = "AM" if moment.hour < 12 else "PM"
    return f"{_MON[moment.month - 1]} {moment.day}, {moment.year} {hour12}:{moment.minute:02d} {ampm}"


def _write_exhausted_rollout(tmp_path, reset_at: "datetime") -> None:
    path = tmp_path / "2026" / "11" / "04"
    path.mkdir(parents=True, exist_ok=True)
    token_count = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "rate_limits": {
                "limit_id": "premium",
                "primary": None,
                "secondary": None,
                "credits": {"has_credits": False, "unlimited": False, "balance": "0"},
                "plan_type": "plus",
            },
        },
    }
    complete = {
        "type": "event_msg",
        "payload": {
            "type": "task_complete",
            "error": {
                "message": "You’ve hit your usage limit. Upgrade to Pro "
                           f"(https://chatgpt.com/explore/pro) … or try again at "
                           f"{_codex_limit_label(reset_at)}."
            },
        },
    }
    (path / "rollout-2026-11-04T21-09-27-test.jsonl").write_text(
        json.dumps({"type": "session_meta"}) + "\n"
        + json.dumps(token_count) + "\n" + json.dumps(complete) + "\n",
        encoding="utf-8",
    )


def test_codex_usage_limit_blokerer_selv_naar_vinduerne_er_null(monkeypatch, tmp_path):
    reset = datetime.now() + timedelta(hours=3)
    _write_exhausted_rollout(tmp_path, reset)
    monkeypatch.setattr(dispatch_quota, "_CODEX_SESSIONS", str(tmp_path))

    reading = dispatch_quota.codex_quota()
    preflight = dispatch_quota.quota_preflight("codex")

    assert reading.ok is True
    assert reading.hard_block is True
    assert reading.get("primary_pct") == 100.0
    assert reading.get("rate_limit_reached_type") == "usage_limit"
    assert preflight["allow"] is False
    assert preflight["severity"] == "block"


def test_codex_usage_limit_efter_reset_slipper_igennem(monkeypatch, tmp_path):
    """Er «try again at» passeret, er grænsen historie — ikke en blokering."""
    reset = datetime.now() - timedelta(hours=3)
    _write_exhausted_rollout(tmp_path, reset)
    monkeypatch.setattr(dispatch_quota, "_CODEX_SESSIONS", str(tmp_path))

    reading = dispatch_quota.codex_quota()

    assert reading.hard_block is False
    assert dispatch_quota.quota_preflight("codex")["allow"] is True


def test_claude_udloebet_credentials_token_blokerer(monkeypatch, tmp_path):
    """Udløbet token er MÅLT død — ikke «kunne ikke måles», som er fail-open."""
    cred = tmp_path / ".credentials.json"
    cred.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "sk-ant-oat01-udloebet",
            "expiresAt": (time.time() - 3600) * 1000,
        }
    }), encoding="utf-8")
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(dispatch_quota, "_CLAUDE_ENV_FILE", str(tmp_path / "ingen.env"))
    monkeypatch.setattr(dispatch_quota, "_CLAUDE_CREDENTIALS_FILE", str(cred))

    reading = dispatch_quota.claude_quota()
    preflight = dispatch_quota.quota_preflight("claude")

    assert reading.ok is False
    assert reading.hard_block is True
    assert "udløbet" in reading.error
    assert preflight["allow"] is False
    assert preflight["severity"] == "block"


def test_claude_gyldigt_credentials_token_bruges(monkeypatch, tmp_path):
    """Et levende token i credentials-filen skal bruges som kilde."""
    cred = tmp_path / ".credentials.json"
    cred.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "sk-ant-oat01-levende",
            "expiresAt": (time.time() + 3600) * 1000,
        }
    }), encoding="utf-8")
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(dispatch_quota, "_CLAUDE_ENV_FILE", str(tmp_path / "ingen.env"))
    monkeypatch.setattr(dispatch_quota, "_CLAUDE_CREDENTIALS_FILE", str(cred))
    monkeypatch.setattr(dispatch_quota.urllib.request, "urlopen",
                        lambda *a, **k: _Resp(json.dumps(CLAUDE_PAYLOAD).encode()))

    reading = dispatch_quota.claude_quota()

    assert reading.ok is True
    assert reading.get("token_source") == "credentials_file"
