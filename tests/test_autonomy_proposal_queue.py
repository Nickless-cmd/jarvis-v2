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
    # RESTTILSTAND (3/11-2026, rettet samme aften): jeg skrev først
    # `disk_touched is True` og «filen ER skrevet». Men denne test patcher
    # `write_text` til at gøre INTET — så den beviste at disken var uændret,
    # mens den assert'ede det modsatte. En grøn test der bekræftede sin egen
    # modsætning. Det der kan observeres er tre ting, og de står nu hver for sig:
    assert res["write_attempted"] is True, "kaldet blev gjort — det er observeret"
    assert res["disk_changed"] is False, (
        "write_text gjorde intet, så disken bærer stadig originalen — "
        "disk_changed skal være False, ikke True"
    )
    assert res["requires_inspection"] is True, (
        "et nyt forsøg skal undersøge filen, ikke antage noget om den"
    )


def test_en_skrivning_der_landede_FORKERT_markerer_disk_changed(tmp_path):
    """Den anden gren — og den jeg helt manglede.

    `disk_changed` er sand når readback afviger fra den FØR læste tilstand.
    Det siger intet om hvor mange mellemliggende skrivninger der er sket, men
    det gør resttilstanden målbar: filen er reelt ændret, og et nyt forsøg må
    ikke antage at den er som før.

    Uden denne test kunne `disk_changed` være hardcoded til False og hele
    kontrakten stadig se rigtig ud — samme fejlklasse som `readback_match`.
    """
    from unittest.mock import patch as _patch

    from core.services.autonomy_proposal_queue import _execute_source_edit_proposal

    target = tmp_path / "core" / "halvskrevet.py"
    target.parent.mkdir()
    target.write_text("original = True\n", encoding="utf-8")

    def _skriv_noget_andet(self, data, **kwargs):
        # Skrivningen LANDER, men disken bærer ikke det forventede indhold —
        # fx fordi et filter eller en anden skriver kom imellem.
        with open(self, "w", encoding="utf-8") as fh:
            fh.write("noget_helt_andet = True\n")

    with _patch("pathlib.Path.write_text", _skriv_noget_andet):
        res = _execute_source_edit_proposal(
            {
                "target_path": str(target),
                "new_content": "nyt = True\n",
            }
        )

    assert res["status"] == "error"
    assert res["readback_match"] is False
    assert res["write_attempted"] is True
    assert res["disk_changed"] is True, (
        "filen blev reelt ændret — disk_changed skal være True så næste forsøg "
        "ved at den skal undersøges"
    )
    assert res["current_fingerprint"] != res["readback_fingerprint"]
    assert target.read_text(encoding="utf-8") == "noget_helt_andet = True\n"


def _koer_godkendelse(monkeypatch, *, executor_svar):
    """Kør `approve_proposal` HELT igennem med en source-edit-executor.

    Returnerer (resultat, commit_kaldt, resolved_status). Bruges af begge
    retnings-tests nedenfor, saa den ene ikke kan bestaa ved at commit aldrig
    kaldes for noget som helst.
    """
    from core.services import autonomy_proposal_queue as apq

    commit_kald: list[tuple] = []
    resolved: list[dict] = []

    monkeypatch.setattr(apq, "get_autonomy_proposal", lambda pid: {
        "proposal_id": pid,
        "kind": "source-edit",
        "status": "pending",
        "payload": {"target_path": "/tmp/x.py", "relative_path": "x.py"},
    })
    monkeypatch.setattr(
        apq, "resolve_autonomy_proposal",
        lambda pid, **kw: resolved.append({"status": kw.get("status")}) or {"proposal_id": pid},
    )
    monkeypatch.setitem(apq._PROPOSAL_EXECUTORS, "source-edit", lambda payload: executor_svar)
    monkeypatch.setattr(
        apq, "_auto_commit_after_source_edit",
        lambda proposal, result: commit_kald.append((proposal, result)),
    )

    out = apq.approve_proposal("prop-1")
    return out, commit_kald, resolved[-1]["status"] if resolved else None


def test_et_mismatch_naar_aldrig_commit_grenen(monkeypatch):
    """En readback der ikke matcher maa ikke blive en commit.

    3/11-2026: den foerste udgave af denne test var en grep i kildekoden —
    `inspect.getsource` plus `assert "error" not in ("executed",)`, som er en
    tautologi mellem to konstanter testen selv skrev. Den kunde ALDRIG fejle,
    uanset hvad koden gjorde. Maalt af GPT: den udfoerte ikke engang
    `approve_proposal`. Her kaldes hele kaeden, og commit-funktionen er en spy.
    """
    out, commit_kald, status = _koer_godkendelse(
        monkeypatch,
        executor_svar={"status": "error", "readback_match": False, "error": "readback mismatch"},
    )

    assert out["status"] == "failed", out
    assert status == "failed"
    assert commit_kald == [], f"en ikke-landet skrivning blev committet: {commit_kald}"


def test_en_landet_skrivning_naar_commit_grenen(monkeypatch):
    """Positiv kontrol: uden den beviser testen ovenfor intet.

    En «executed» fra executoren SKAL naa commit-grenen. Ellers kunne den
    negative test bestaa af den forkerte grund — at commit aldrig kaldes.
    """
    out, commit_kald, status = _koer_godkendelse(
        monkeypatch,
        executor_svar={"status": "executed", "readback_match": True},
    )

    assert out["status"] == "executed", out
    assert status == "executed"
    assert len(commit_kald) == 1, "en landet skrivning naaede ikke commit-grenen"
