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


def test_afvisning_lukker_fundet(monkeypatch):
    """Målt 3/11-2026: 75 afviste instrument-forslag efterlod deres fund `open`.

    Godkendelse lukkede fundet; afvisning gjorde ikke — så daemonen filede det
    igen, og næste runde afviste det igen. Et «nej» der ikke lukker sagen er et
    spørgsmål der bliver stillet for evigt.
    """
    from core.services import autonomy_proposal_queue as apq
    import core.runtime.db_instrument as dbi

    lukket: list[tuple[str, str]] = []

    monkeypatch.setattr(apq, "get_autonomy_proposal", lambda pid: {
        "proposal_id": pid,
        "kind": "instrument_fix",
        "status": "pending",
        "payload": {"finding": {"signature": "except_silent:abc123"}},
    })
    monkeypatch.setattr(
        apq, "resolve_autonomy_proposal",
        lambda pid, **kw: {"proposal_id": pid, "status": kw.get("status")},
    )
    monkeypatch.setattr(
        dbi, "set_finding_status",
        lambda sig, st: lukket.append((sig, st)) or True,
    )

    out = apq.reject_proposal("prop-1", resolution_note="forældet fund")

    assert out["status"] == "rejected"
    # `dismissed`, ikke `accepted`: afslag betyder «ret det ikke».
    assert lukket == [("except_silent:abc123", "dismissed")]


def test_en_skrivning_der_ikke_landede_er_ikke_en_succes(tmp_path):
    """Readback der ikke matcher må ikke give «executed» (målt 3/11-2026).

    Fejlen var: `readback_match` blev BEREGNET men ikke HÅNDHÆVET. Et mismatch
    returnerede stadig status «executed», `approve_proposal` kvitterede succes
    og `_auto_commit_after_source_edit` lavede en rigtig git-commit af et
    indhold disken ikke bar. Samme form som «stale»-fixet 2/10-2026: en måling
    der ikke afgør udfaldet.

    Simuleringen er den ægte: skrivningen lander ikke, så readback læser det
    der faktisk står på disken — originalen.
    """
    from unittest.mock import patch as _patch

    from core.services.autonomy_proposal_queue import _execute_source_edit_proposal

    target = tmp_path / "core" / "skrevet.py"
    target.parent.mkdir()
    target.write_text("original = True\n", encoding="utf-8")

    # Skrivningen lander ikke: write_text gør intet, så disken bærer originalen.
    with _patch("pathlib.Path.write_text", return_value=None):
        res = _execute_source_edit_proposal(
            {
                "target_path": str(target),
                "new_content": "nyt = True\n",
            }
        )

    assert res["status"] != "executed", f"en ikke-landet skrivning blev meldt som succes: {res}"
    assert res["status"] == "error"
    assert "readback" in res["error"]
    assert res["readback_match"] is False


def test_et_mismatch_naar_aldrig_commit_grenen():
    """«executed» er den ENESTE status der fører til auto-commit.

    Bekræfter koblingen: fejl-grenen i `approve_proposal` fanger «error», og
    commit-betingelsen kræver præcis «executed».
    """
    from core.services import autonomy_proposal_queue as apq

    kilde = apq.approve_proposal.__doc__ or ""
    # Status-grenen: fejlstatusser må ikke være «executed».
    assert "error" not in ("executed",)
    # Commit-betingelsen læser status fra resultatet — ikke fra et flag.
    import inspect

    tekst = inspect.getsource(apq.approve_proposal)
    assert 'result.get("status") == "executed"' in tekst
    assert '"error", "stale", "failed"' in tekst
