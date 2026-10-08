"""C5b: dispatch_agent(writes=true) - worktree reserveres FOER accept, og hele vejen til diff."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from core.services import agent_sandbox as sb

USABLE, WHY = sb.sandbox_usable()
needs_bwrap = pytest.mark.skipif(not USABLE, reason=f"bwrap kan ikke bruges her: {WHY}")
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}
O, S, R = "bjorn", "sess-1", "visible-p"


def sh(*a, cwd):
    return subprocess.run(a, cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def cw(isolated_runtime, monkeypatch, tmp_path):
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    import core.services.agent_worktrees as W
    from core.services import agent_runtime_spawn as M
    from core.services import in_flight_runs as ifr

    ws = tmp_path / "ws"
    repo = ws / "proj"
    repo.mkdir(parents=True)
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    (repo / "a.txt").write_text("a\n")
    sh("git", "add", "-A", cwd=repo)
    sh("git", "commit", "-q", "-m", "init", cwd=repo)
    monkeypatch.setenv("JARVIS_AGENT_WORKSPACE_ROOTS", str(ws))
    ifr._mutate(lambda r: r.clear())
    svc.set_capability(True, role="owner")
    started = []
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: started.append(fn))

    class H:
        c_, svc_, W_, M_ = c, svc, W, M
        repo_, started_ = str(repo), started

        def d(self, **kw):
            base = dict(owner_user_id=O, origin_session_id=S, goal="skriv en funktion", parent_run_id=R)
            base.update(kw)
            return svc.dispatch_agent(**base)

        def count(self, table):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        def head(self):
            return sh("git", "rev-parse", "HEAD", cwd=repo).strip()

    yield H()
    ifr._mutate(lambda r: r.clear())


@pytest.mark.parametrize("kw", [
    {"writes": True},                                                    # intet workspace
    {"writes": True, "workspace": "  "},
    {"workspace": "/x"},                                                 # workspace uden writes
    {"tool_policy": "worktree-write"},                                   # politikken uden writes
    {"allowed_tools": ["wt_bash"]},                                      # vaerktoejer uden writes
    {"writes": True, "workspace": "WS", "allowed_tools": ["read_file"]}, # kodeagenten har en fast politik
    {"writes": True, "workspace": "WS", "tool_policy": "read-only-runtime"},
])
def test_invalid_write_requests_are_refused_before_anything_is_created(cw, kw):
    kw = {k: (cw.repo_ if v == "WS" else v) for k, v in kw.items()}
    out = cw.d(**kw)
    assert (out["status"], out["code"]) == ("error", "INVALID_SCOPE")
    assert (cw.count("agent_registry"), cw.count("agent_assignments"), cw.count("agent_worktrees"), cw.started_) == (0, 0, 0, [])


def test_a_write_dispatch_reserves_a_worktree_before_accept_and_sets_the_fixed_policy(cw):
    out = cw.d(writes=True, workspace=cw.repo_)
    assert out["status"] == "accepted" and out["worktree"]["branch"] == f"agent/{out['assignment_id']}"
    assert out["worktree"]["base_commit"] == cw.head() and len(cw.started_) == 1
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    ag = get_agent_registry_entry(out["agent_id"])
    assert ag["tool_policy"] == "worktree-write" and "wt_bash" in ag["allowed_tools_json"]
    (row,) = [dict(r) for r in cw.c_._conn().execute("SELECT * FROM agent_worktrees")]
    assert (row["status"], row["owner_user_id"], row["assignment_id"]) == ("active", O, out["assignment_id"])


def test_a_non_write_dispatch_is_unchanged_and_gets_no_worktree(cw):
    out = cw.d()
    assert out["status"] == "accepted" and "worktree" not in out and cw.count("agent_worktrees") == 0


@pytest.mark.parametrize("case", ["kvote", "udenfor-rod", "ikke-repo"])
def test_a_worktree_that_cannot_be_reserved_leaves_no_half_child_behind(cw, monkeypatch, tmp_path, case):
    workspace = cw.repo_
    if case == "kvote":
        monkeypatch.setattr(cw.W_, "MAX_CONCURRENT_WRITING", 0)
    elif case == "udenfor-rod":
        other = tmp_path / "udenfor"; other.mkdir(); sh("git", "init", "-q", cwd=other)
        workspace = str(other)
    else:
        workspace = str(tmp_path / "ws" / "findes-ikke")
    out = cw.d(writes=True, workspace=workspace)
    assert out["status"] == "error" and out["code"] in ("CAPACITY", "INVALID_SCOPE") and out["phase"] == "admission"
    for table in ("agent_registry", "agent_assignments", "agent_runs", "agent_worktrees", "agent_result_outbox",
                  "agent_messages", "agent_artifacts", "agent_leases"):
        assert cw.count(table) == 0, table
    assert cw.started_ == [] and not os.path.isdir(os.path.join(str(cw.W_.worktree_root())))\
        or os.listdir(str(cw.W_.worktree_root())) == []
    from core.runtime.db_agent_artifacts import artifact_root
    assert not artifact_root().exists() or os.listdir(artifact_root()) == []


def test_idempotent_write_dispatch_replays_without_a_second_worktree(cw):
    first = cw.d(writes=True, workspace=cw.repo_, idempotency_key="k1")
    again = cw.d(writes=True, workspace=cw.repo_, idempotency_key="k1")
    assert again["replayed"] is True and again["assignment_id"] == first["assignment_id"]
    assert cw.count("agent_worktrees") == 1 and cw.count("agent_registry") == 1
    clash = cw.d(writes=True, workspace=cw.repo_, idempotency_key="k1", goal="noget andet")
    assert clash["code"] == "IDEMPOTENCY_CONFLICT" and cw.count("agent_worktrees") == 1


def test_discard_unstarted_assignment_only_removes_what_never_started(cw):
    out = cw.d()
    aid, ag = out["assignment_id"], out["agent_id"]
    assert cw.c_.discard_unstarted_assignment(agent_id=ag, owner_user_id="anden") is False       # fremmed ejer
    conn = cw.c_._conn()      # ÉN forbindelse: et nyt _conn()-kald ruller en aaben transaktion tilbage
    conn.execute("UPDATE agent_runs SET started_at='2026-10-07T10:00:00Z' WHERE assignment_id=?", (aid,))
    conn.commit()
    assert cw.c_.discard_unstarted_assignment(agent_id=ag, owner_user_id=O) is False              # er startet
    conn = cw.c_._conn()
    conn.execute("UPDATE agent_runs SET started_at='' WHERE assignment_id=?", (aid,))
    conn.commit()
    assert cw.c_.discard_unstarted_assignment(agent_id=ag, owner_user_id=O) is True
    assert cw.count("agent_registry") == 0 and cw.count("agent_assignments") == 0
    assert cw.c_.discard_unstarted_assignment(agent_id=ag, owner_user_id=O) is False              # allerede vaek


def test_a_finished_assignment_is_never_discarded(cw):
    out = cw.d()
    cw.c_.commit_terminal_outcome(assignment_id=out["assignment_id"], status="completed")
    assert cw.c_.discard_unstarted_assignment(agent_id=out["agent_id"], owner_user_id=O) is False
    assert cw.count("agent_assignments") == 1 and cw.count("agent_result_outbox") == 1


# --- hele vejen: dispatch -> agenten skriver -> diff -> bevaret, ikke merget ------------------------------

@needs_bwrap
@pytest.mark.parametrize("worker_mode", [False, True])
def test_a_code_agent_writes_in_its_worktree_and_delivers_a_diff_without_touching_main(cw, monkeypatch, worker_mode):
    import core.services.agent_runtime_base as base
    from core.runtime import db_agent_artifacts as art
    from core.services import agent_worker_runner as R

    if worker_mode:
        monkeypatch.setattr(R, "_sandbox_ok", (True, ""))
        R.set_worker_mode(True, role="owner")
    replies = [
        {"text": "", "tool_calls": [{"id": "c1", "function": {"name": "wt_write_file", "arguments": json.dumps(
            {"path": "ny.py", "content": "def hej():\n    return 'hej'\n"})}}]},
        {"text": "", "tool_calls": [{"id": "c2", "function": {"name": "wt_bash", "arguments": json.dumps(
            {"command": f"{__import__('sys').executable} -c \"import ny; print(ny.hej())\""})}}]},
        {"text": "Skrev ny.py og koerte den; udskriver hej."},
    ]
    bash_outputs = []

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            return replies.pop(0) | {"input_tokens": 1, "output_tokens": 1}

    monkeypatch.setattr(base, "_facade", lambda: _F())
    monkeypatch.setattr(cw.M_, "_facade", lambda: _F())
    monkeypatch.setattr(cw.M_, "agent_tools_enabled", lambda: True)
    monkeypatch.setattr(base, "agent_tools_enabled", lambda: True)
    head_before = cw.head()
    out = cw.d(writes=True, workspace=cw.repo_)
    cw.M_.execute_agent_task(agent_id=out["agent_id"])
    a = cw.c_.get_assignment(assignment_id=out["assignment_id"], owner_user_id=O)
    assert a["status"] == "completed"
    (m,) = cw.c_.list_pending_results(owner_user_id=O, origin_session_id=S)
    payload = json.loads(m["payload_json"])
    result = json.loads(art.read_artifact(owner_user_id=O, ref=payload["artifact_ref"])["content"])
    assert result["worktree"]["files"] == 1 and result["worktree"]["errors"] == []
    run_id = payload["last_run_id"]
    diff = art.read_artifact(owner_user_id=O, ref=f"{run_id}/diff.patch")["content"]
    assert "ny.py" in diff and "+def hej():" in diff
    (wt,) = [dict(r) for r in cw.c_._conn().execute("SELECT * FROM agent_worktrees")]
    assert wt["status"] == "retained" and os.path.isdir(wt["path"])
    assert cw.head() == head_before and sh("git", "status", "--porcelain", cwd=cw.repo_) == ""
    assert not os.path.exists(os.path.join(cw.repo_, "ny.py"))                # hovedrepoet er urørt
    assert "hej" in payload["summary"]


# ── §11.1's oprydning skal kunne naa sit eget maal (8/10-2026) ──────────────

def test_en_frisk_assignment_kan_kasseres_selv_om_den_straks_er_active(cw):
    """Hullet der kom frem da de fire produktionspunkter blev flettet sammen.

    `discard_unstarted_assignment` stod paa `status='queued'` som proxy for
    «ikke startet». Med den varige scheduler claimer en ny assignment en
    workerplads med det samme og er `active` allerede naar dispatch returnerer.
    Proxyen var altsaa falsk, og §11.1's oprydning efter en admission der
    fejler EFTER accept kunne aldrig naa noget — den efterlod praecis det halve
    barn den er skrevet for at fjerne.
    """
    out = cw.d()
    aid, ag = out["assignment_id"], out["agent_id"]

    status = cw.c_._conn().execute(
        "SELECT status FROM agent_assignments WHERE assignment_id=?", (aid,)).fetchone()["status"]
    assert status == "active", (
        "forudsaetningen for denne test er at scheduleren starter med det samme; "
        "staar den %r, er det den gamle verden og testen maaler ikke hullet" % status)

    assert cw.c_.discard_unstarted_assignment(agent_id=ag, owner_user_id=O) is True
    assert cw.count("agent_assignments") == 0 and cw.count("agent_registry") == 0


def test_et_STARTET_run_kasseres_stadig_ikke_uanset_status(cw):
    """Den vagt der betyder noget: har en worker sat `started_at`, kan der
    vaere sket noget ude i verden, og raekken maa ikke forsvinde."""
    out = cw.d()
    aid, ag = out["assignment_id"], out["agent_id"]
    conn = cw.c_._conn()
    conn.execute("UPDATE agent_runs SET started_at='2026-10-08T06:00:00Z' WHERE assignment_id=?", (aid,))
    conn.commit()

    assert cw.c_.discard_unstarted_assignment(agent_id=ag, owner_user_id=O) is False
    assert cw.count("agent_assignments") == 1


def test_en_afsendt_terminalbesked_spaerrer_ogsaa(cw):
    """Er der sendt et terminalt udfald, har parenten set et svar. Saa er der
    ikke noget «aldrig startet» at rydde op i.

    Kolonnelisten er kopieret fra `db_agent_contract`s egen indsaettelse, saa
    testen ikke opfinder et skema ved siden af produktionens.
    """
    out = cw.d()
    aid, ag = out["assignment_id"], out["agent_id"]
    conn = cw.c_._conn()
    conn.execute(
        "INSERT INTO agent_result_outbox (message_id, assignment_id, result_type, "
        "owner_user_id, origin_session_id, sender_agent_id, recipient_agent_id, "
        "parent_run_id, last_run_id, payload_json, created_at, updated_at) "
        "VALUES ('m1',?,'terminal',?,'s1',?,'jarvis','','','{}',"
        "'2026-10-08T06:00:00Z','2026-10-08T06:00:00Z')",
        (aid, O, ag))
    conn.commit()

    assert cw.c_.discard_unstarted_assignment(agent_id=ag, owner_user_id=O) is False
    assert cw.count("agent_assignments") == 1
