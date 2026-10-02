from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from core.services.attributed_git_commit import AttributedCommitResult
from core.services.autonomy_proposal_queue import (
    _auto_commit_after_source_edit,
    _execute_git_commit_proposal,
    approve_proposal,
)


def _successful_add(*args, **kwargs):
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_source_edit_commit_carries_proposal_attribution(tmp_path):
    target = tmp_path / "core" / "changed.py"
    target.parent.mkdir()
    target.write_text("changed = True\n")
    proposal = {
        "proposal_id": "proposal-1",
        "run_id": "run-1",
        "session_id": "session-1",
        "rationale": "Fix the runtime",
        "payload": {
            "project_root": str(tmp_path),
            "target_path": str(target),
            "relative_path": "core/changed.py",
        },
    }

    with patch("subprocess.run", side_effect=_successful_add), patch(
        "core.services.autonomy_proposal_queue.commit_with_attribution",
        return_value=AttributedCommitResult(0, sha="abc123"),
    ) as commit:
        _auto_commit_after_source_edit(proposal, {"status": "executed"})

    kwargs = commit.call_args.kwargs
    assert kwargs["paths"] == ("core/changed.py",)
    assert kwargs["author"] == "Jarvis <jarvis@srvlab.dk>"
    assert kwargs["attribution"].actor == "jarvis"
    assert kwargs["attribution"].run_id == "run-1"
    assert kwargs["attribution"].session_id == "session-1"
    assert kwargs["attribution"].origin == "autonomous"
    assert kwargs["attribution"].approved_by == "bjorn"


def test_git_commit_proposal_uses_reserved_approval_context(tmp_path):
    payload = {
        "files": ["core/changed.py"],
        "message": "fix: approved proposal",
        "project_root": str(tmp_path),
        "_proposal_context": {
            "proposal_id": "proposal-2",
            "run_id": "run-2",
            "session_id": "session-2",
            "approved_by": "bjorn",
        },
    }

    with patch("subprocess.run", side_effect=_successful_add), patch(
        "core.services.autonomy_proposal_queue.commit_with_attribution",
        return_value=AttributedCommitResult(0, stdout="committed", sha="def456"),
    ) as commit:
        result = _execute_git_commit_proposal(payload)

    assert result["status"] == "executed"
    assert result["commit"] == "def456"
    attribution = commit.call_args.kwargs["attribution"]
    assert attribution.run_id == "run-2"
    assert attribution.session_id == "session-2"
    assert attribution.approved_by == "bjorn"


def test_approval_passes_proposal_context_to_executor():
    captured = {}

    def executor(payload):
        captured.update(payload)
        return {"status": "executed"}

    proposal = {
        "proposal_id": "proposal-3",
        "run_id": "run-3",
        "session_id": "session-3",
        "status": "pending",
        "kind": "test-attribution",
        "payload": {"value": 42},
    }

    with patch(
        "core.services.autonomy_proposal_queue.get_autonomy_proposal",
        return_value=proposal,
    ), patch(
        "core.services.autonomy_proposal_queue.resolve_autonomy_proposal",
        return_value=proposal,
    ), patch.dict(
        "core.services.autonomy_proposal_queue._PROPOSAL_EXECUTORS",
        {"test-attribution": executor},
        clear=False,
    ):
        result = approve_proposal("proposal-3")

    assert result["status"] == "executed"
    assert captured["value"] == 42
    assert captured["_proposal_context"] == {
        "proposal_id": "proposal-3",
        "run_id": "run-3",
        "session_id": "session-3",
        "approved_by": "bjorn",
    }


# ── instrument_fix — den manglende executor ───────────────────────────────
# Før 29/9-2026 havde kind'en ingen executor: godkendelse satte status til
# 'approved' med «no executor registered» og gjorde intet (1.129 forslag fra
# 23/6). Disse tests fastholder at godkendelse nu LUKKER fundet.

def test_instrument_fix_executor_lukker_fundet(isolated_runtime):
    from core.runtime import db_instrument as dbi
    from core.services.autonomy_proposal_queue import _execute_instrument_fix_proposal

    dbi.replace_file_findings("core/q.py", [
        {"signature": "sig-q", "line": 7, "kind": "except_silent", "severity": "high",
         "score": 5, "function": "f", "snippet": "x"},
    ])
    out = _execute_instrument_fix_proposal(
        {"finding": {"signature": "sig-q", "file": "core/q.py", "line": 7}}
    )
    assert out["status"] == "executed"
    assert out["action"] == "finding_accepted"
    assert not any(r["signature"] == "sig-q" for r in dbi.list_findings(status="open", limit=10))


def test_instrument_fix_er_registreret():
    """Kind'en skal have en executor — ellers er godkendelse igen en tom status."""
    from core.services.autonomy_proposal_queue import _PROPOSAL_EXECUTORS
    assert "instrument_fix" in _PROPOSAL_EXECUTORS


def test_instrument_fix_uden_signatur_er_fejl():
    from core.services.autonomy_proposal_queue import _execute_instrument_fix_proposal

    assert _execute_instrument_fix_proposal({})["status"] == "error"
    assert _execute_instrument_fix_proposal({"finding": {}})["status"] == "error"
    assert _execute_instrument_fix_proposal({"finding": "ikke-et-objekt"})["status"] == "error"


# ── Den falske kvittering (2/10-2026) ─────────────────────────────────────
# Foer blev proposalen sat til «executed» uanset hvad executoren svarede. Et
# «stale»-svar (filen aendret under forslaget) blev derfor meldt som SUCCES.
# Maalt samme dag: 3 af 5 source-edits skrev INTET til disken og meldte
# alligevel «executed successfully».


def test_executorens_STALE_svar_meldes_IKKE_som_success():
    """Den falske kvittering er farligere end fejlen — den skjuler den."""
    kaldt: dict[str, object] = {}

    def executor(payload):
        return {"status": "stale", "error": "file changed under proposal: base=a now=b"}

    def fake_resolve(pid, **kwargs):
        kaldt.update(kwargs)
        return {"proposal_id": pid, **kwargs}

    proposal = {
        "proposal_id": "proposal-stale",
        "status": "pending",
        "kind": "test-stale",
        "payload": {},
    }

    with patch(
        "core.services.autonomy_proposal_queue.get_autonomy_proposal",
        return_value=proposal,
    ), patch(
        "core.services.autonomy_proposal_queue.resolve_autonomy_proposal",
        side_effect=fake_resolve,
    ), patch.dict(
        "core.services.autonomy_proposal_queue._PROPOSAL_EXECUTORS",
        {"test-stale": executor},
        clear=False,
    ):
        result = approve_proposal("proposal-stale")

    assert result["status"] == "failed", "et stale-svar blev meldt som success"
    assert kaldt["status"] == "failed", "proposal-status blev ikke sat til failed"
    assert "stale" in str(kaldt["resolution_note"]), "aarsagen forsvandt ud af noten"


def test_executorens_ERROR_svar_meldes_IKKE_som_success():
    """Samme vagt for det raa error-svar."""

    def executor(payload):
        return {"status": "error", "error": "finding not found: abc"}

    def fake_resolve(pid, **kwargs):
        return {"proposal_id": pid, **kwargs}

    proposal = {
        "proposal_id": "proposal-err",
        "status": "pending",
        "kind": "test-err",
        "payload": {},
    }

    with patch(
        "core.services.autonomy_proposal_queue.get_autonomy_proposal",
        return_value=proposal,
    ), patch(
        "core.services.autonomy_proposal_queue.resolve_autonomy_proposal",
        side_effect=fake_resolve,
    ), patch.dict(
        "core.services.autonomy_proposal_queue._PROPOSAL_EXECUTORS",
        {"test-err": executor},
        clear=False,
    ):
        result = approve_proposal("proposal-err")

    assert result["status"] == "failed"
    assert result["error"] == "finding not found: abc"


def test_list_proposals_viser_FULD_noegle():
    """Den viste noegle skal kunne bruges direkte i approve_proposal.

    Her stod [:18] — «prop-» er 5 tegn, saa der blev vist 13 af 16 hex, og
    praecis den streng brugeren kunne kopiere gav «not-found».
    """
    from core.tools.simple_tools_native import _exec_list_proposals

    fuld = "prop-0123456789abcdef"
    surface = {
        "items": [
            {"proposal_id": fuld, "kind": "x", "title": "t", "status": "pending"}
        ]
    }

    with patch(
        "core.services.autonomy_proposal_queue.build_autonomy_proposal_surface",
        return_value=surface,
    ):
        out = _exec_list_proposals({})

    assert fuld in str(out.get("text") or ""), "noeglen er klippet — approve svarer not-found"
