"""C6b: bubblewrap-sandboxen - argv-form OG rigtige graenser (kraever bwrap)."""
from __future__ import annotations

import os
import socket
import subprocess
import sys

import pytest

from core.services import agent_sandbox as sb

USABLE, WHY = sb.sandbox_usable()
needs_bwrap = pytest.mark.skipif(not USABLE, reason=f"bwrap kan ikke bruges her: {WHY}")


def _argv(**kw):
    return sb.build_bwrap_argv([sys.executable, "-c", "pass"], **kw)


def test_argv_has_the_isolation_flags_and_the_command_last():
    a = _argv()
    for flag in ("--unshare-all", "--die-with-parent", "--new-session", "--clearenv"):
        assert flag in a
    assert a[a.index("--cap-drop") + 1] == "ALL"
    assert a[-3:] == [sb.sandbox_path(sys.executable), "-c", "pass"] and a[-4] == "--"
    assert "--share-net" not in a                         # intet netvaerk


def test_argv_binds_neither_the_runtime_home_nor_the_repo():
    joined = " ".join(_argv())
    assert ".jarvis-v2" not in joined
    repo = str(sb._SERVICES_DIR.parents[1])
    binds = [a for a in _argv() if a.startswith(repo)]
    assert all(b.startswith(str(sb._SERVICES_DIR)) and b.endswith(".py") for b in binds)
    assert len(binds) == len(sb.WORKER_FILES)


def test_only_the_three_worker_files_are_bound_read_only_under_worker():
    a = _argv()
    pairs = [(a[i + 1], a[i + 2]) for i, x in enumerate(a) if x == "--ro-bind" and a[i + 2].startswith("/worker/")]
    assert sorted(dst for _, dst in pairs) == sorted(f"/worker/{n}" for n in sb.WORKER_FILES)
    assert "--bind" not in a and "--bind-try" not in a        # intet skrivbart fra vaerten


def test_python_env_is_bound_read_only_at_a_neutral_path_outside_home():
    """Python-prefixet bindes til en NEUTRAL sti, ikke sin egen.

    Ligger miljoeet under /home (fx ~/miniconda3), gen-skaber en bind til samme sti /home/<bruger>
    oven paa ``--tmpfs /home`` - og saa er /home ikke tom, og vaertens brugernavne staar i
    sandkassen. Maalt 8/10-2026: ``os.listdir('/home')`` svarede ['bs'] hvor testen kraever []."""
    a = _argv(extra_env={"EKSTRA": "1"})
    for src, dst in sb.sandbox_python_mounts():
        i = a.index(dst)
        assert a[i - 2] == "--ro-bind" and a[i - 1] == src
        assert not dst.startswith("/home"), dst
    env = {a[i + 1]: a[i + 2] for i, x in enumerate(a) if x == "--setenv"}
    assert env["PYTHONPATH"] == "/worker" and env["HOME"] == "/tmp" and env["EKSTRA"] == "1"
    assert "OPENAI_API_KEY" not in env and set(env) >= {"PATH", "PYTHONDONTWRITEBYTECODE"}


def test_no_mount_target_lies_under_home():
    """Alt hvad der monteres SKAL ligge uden for /home - ellers er /home ikke tom i sandkassen."""
    a = _argv(rw_binds={"/host/wt": "/work"})
    targets = [a[i + 2] for i, x in enumerate(a) if x in ("--ro-bind", "--bind", "--tmpfs")]
    assert targets, "ingen mounts at kontrollere"
    assert not [t for t in targets if t == "/home" or t.startswith("/home/")], targets


def test_sandbox_path_moves_the_python_prefix_and_leaves_everything_else():
    for i, prefix in enumerate(sb.python_prefixes()):
        assert sb.sandbox_path(prefix) == f"{sb._SANDBOX_PYTHON}/{i}"
        assert sb.sandbox_path(prefix + "/bin/python3") == f"{sb._SANDBOX_PYTHON}/{i}/bin/python3"
    for untouched in ("/usr/bin/bash", "/work/fil.py", "/tmp/x", ""):
        assert sb.sandbox_path(untouched) == untouched


def test_a_missing_bwrap_or_prlimit_makes_the_sandbox_unavailable_never_silently_skipped(monkeypatch):
    monkeypatch.setattr(sb.shutil, "which", lambda name: None)
    with pytest.raises(sb.SandboxUnavailable):
        _argv()
    with pytest.raises(sb.SandboxUnavailable):
        sb.resource_prefix(address_space=1, cpu_seconds=1)
    ok, why = sb.sandbox_usable()
    assert ok is False and "installeret" in why


def test_resource_prefix_sets_hard_limits_and_leaves_nproc_alone():
    p = sb.resource_prefix(address_space=1024, cpu_seconds=9)
    assert "--as=1024" in p and "--cpu=9" in p and "--core=0" in p and p[-1] == "--"
    assert not any("nproc" in x for x in p)


def _run(code, *, timeout=30, **kw):
    proc = sb.spawn_in_sandbox([sys.executable, "-c", code], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, worker_files={}, **kw)
    out, err = proc.communicate(timeout=timeout)
    return proc.returncode, out.decode(), err.decode()


@needs_bwrap
def test_the_runtime_home_and_credentials_do_not_exist_inside(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".jarvis-v2" / "config").mkdir(parents=True)
    canary = home / ".jarvis-v2" / "config" / "runtime.json"
    canary.write_text('{"kanari": "HEMMELIG-KANARIFUGL"}')
    monkeypatch.setenv("HOME", str(home))
    rc, out, err = _run(f"import os; print(os.path.exists({str(canary)!r}), os.listdir('/home'), os.path.exists({str(home)!r}))")
    assert rc == 0 and out.strip() == "False [] False"
    rc, out, err = _run(f"print(open({str(canary)!r}).read())")
    assert rc != 0 and "HEMMELIG" not in out + err


@needs_bwrap
def test_the_repository_is_invisible_inside(tmp_path):
    repo = str(sb._SERVICES_DIR.parents[1])
    rc, out, _ = _run(f"import os; print(os.path.exists({repo!r}))")
    assert out.strip() == "False"


@needs_bwrap
def test_there_is_no_network_not_even_loopback_to_a_listener_on_the_host():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        rc, out, err = _run(
            "import socket\ns=socket.socket(); s.settimeout(3)\n"
            f"try:\n    s.connect(('127.0.0.1', {port})); print('FORBUNDET')\n"
            "except OSError as e:\n    print('NEJ', type(e).__name__)")
        assert out.startswith("NEJ"), out + err
        srv.settimeout(0.3)
        with pytest.raises(socket.timeout):
            srv.accept()                              # vaerten saa aldrig en forbindelse
    finally:
        srv.close()


@needs_bwrap
def test_the_process_lives_in_its_own_pid_namespace_and_cannot_see_the_host():
    rc, out, _ = _run("import os; print(os.getpid(), len([p for p in os.listdir('/proc') if p.isdigit()]))")
    pid, n = map(int, out.split())
    assert pid < 50 and n < 10 and pid != os.getpid()


@needs_bwrap
def test_the_filesystem_is_read_only_except_a_private_tmp():
    prefix = sb.sandbox_path(sb.python_prefixes()[0])   # stien som den findes INDE i sandkassen
    code = (f"import os\n"
            f"try:\n    open({prefix + '/ejer-her'!r}, 'w'); print('SKREV-I-MILJOET')\n"
            f"except OSError:\n    print('RO')\n"
            f"open('/tmp/privat', 'w').write('x'); print('TMP-OK')")
    rc, out, err = _run(code)
    assert out.split() == ["RO", "TMP-OK"], out + err
    assert not os.path.exists("/tmp/privat")          # tmpfs: ikke vaertens /tmp


@needs_bwrap
def test_the_host_environment_does_not_leak_in(monkeypatch):
    monkeypatch.setenv("JARVIS_TEST_SECRET", "laekket")
    rc, out, _ = _run("import os; print(os.environ.get('JARVIS_TEST_SECRET'), sorted(os.environ))")
    assert out.startswith("None") and "JARVIS_TEST_SECRET" not in out.split("None", 1)[1]


@needs_bwrap
def test_an_inherited_fd_works_as_the_only_channel_out():
    a, b = socket.socketpair()
    os.set_inheritable(b.fileno(), True)
    proc = sb.spawn_in_sandbox(
        [sys.executable, "-c", f"import socket; s=socket.socket(fileno={b.fileno()}); s.sendall(b'hej')"],
        pass_fds=(b.fileno(),), worker_files={}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    b.close()
    a.settimeout(15)
    assert a.recv(10) == b"hej"
    proc.wait(timeout=15)
    a.close()


@needs_bwrap
def test_the_address_space_limit_stops_a_memory_hog():
    rc, out, err = _run("x = bytearray(1536 * 1024 * 1024); print('FOR-MEGET')", address_space=1024 ** 3)
    assert rc != 0 and "FOR-MEGET" not in out


@needs_bwrap
def test_killing_the_group_kills_everything_inside():
    proc = sb.spawn_in_sandbox([sys.executable, "-c", "import time; time.sleep(60)"],
                               worker_files={}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import signal
    import time
    time.sleep(1.0)
    os.killpg(proc.pid, signal.SIGKILL)
    assert proc.wait(timeout=10) != 0


def test_rw_binds_are_the_only_writable_mounts_and_set_the_working_directory():
    a = sb.build_bwrap_argv(["ls"], rw_binds={"/host/wt": "/work"}, chdir="/work", worker_files={})
    binds = [(a[i + 1], a[i + 2]) for i, x in enumerate(a) if x == "--bind"]
    assert binds == [("/host/wt", "/work")]
    assert a[a.index("--chdir") + 1] == "/work"
    plain = sb.build_bwrap_argv(["ls"], worker_files={})
    assert "--bind" not in plain and plain[plain.index("--chdir") + 1] == "/tmp"
