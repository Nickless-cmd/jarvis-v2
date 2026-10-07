"""bubblewrap-sandbox til en agent-worker (agent-contract-v1 C6b, spec 12.1).

Hver workerproces koerer i et frisk namespace-sæt: ingen netforbindelse, eget pid/ipc/uts/user-
namespace, alle capabilities droppet, ingen ``~/.jarvis-v2`` (dermed hverken credentials eller
andre ejeres runtimefiler), intet repo - kun Python-miljoeet skrivebeskyttet og de tre filer
workeren bruger. Sockets arves som fd. Kan sandboxen ikke etableres, koerer agenten IKKE
(``SandboxUnavailable``): der er ingen stille tilbagegang til en usandboxet proces.

Processer: hver sandbox startes i sin EGEN cgroup-scope (``systemd-run --user --scope -p TasksMax=N``),
saa en fork-bombe rammer et loft paa N processer+traade og ikke vaerten. ``prlimit --nproc`` er bevidst
ikke brugt (taelles pr. bruger paa hele vaerten), og ``pid_max`` i pid-namespacet kan agenten selv haeve.
Kan scopen ikke laves (ingen brugermanager), koerer agenten ikke - kun ``JARVIS_AGENT_PIDS_LIMIT=off``
fravaelger graensen.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

#: Filer workeren behoever - bindes skrivebeskyttet ind som /worker/<navn>.
logger = logging.getLogger(__name__)

WORKER_FILES = ("agent_worker_main.py", "agent_worker_protocol.py", "agent_loop_core.py")
_SERVICES_DIR = Path(__file__).resolve().parent
#: Systemmapper der bindes skrivebeskyttet hvis de findes (biblioteker og interpreterens afhaengigheder).
_SYSTEM_RO = ("/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/etc/ld.so.cache", "/etc/alternatives")


#: Loft for antal processer+traade i EN sandbox (cgroup ``pids.max``). Workeren har traade til
#: modelkald; en kommando i et worktree maa gerne bygge/teste parallelt men ikke bombe vaerten.
PIDS_WORKER = 256
PIDS_COMMAND = 512
PIDS_OFF_ENV = "JARVIS_AGENT_PIDS_LIMIT"          # "off" = bevidst fravalg (aldrig default)
_PROBE_TTL_S = 30.0
_probe_lock = threading.Lock()
_probe_cache: tuple[float, tuple[bool, str]] | None = None


class SandboxUnavailable(RuntimeError):
    """Sandboxen kan ikke etableres - agentens loekke maa ikke koere usandboxet."""


def bwrap_path() -> str:
    path = shutil.which("bwrap")
    if not path:
        raise SandboxUnavailable("bwrap er ikke installeret")
    return path


def python_prefixes() -> list[str]:
    seen: list[str] = []
    for p in (sys.prefix, sys.base_prefix, os.path.dirname(os.path.dirname(os.path.realpath(sys.executable)))):
        if p and p not in seen and os.path.isdir(p):
            seen.append(p)
    return seen


def build_bwrap_argv(command: list[str], *, pass_fds: tuple[int, ...] = (),
                     extra_env: dict[str, str] | None = None,
                     worker_files: dict[str, str] | None = None,
                     rw_binds: dict[str, str] | None = None, chdir: str = "/tmp",
                     mounts: list[tuple[str, str, str]] | None = None) -> list[str]:
    """Byg ``bwrap``-kommandolinjen for ``command`` (som koeres INDE i sandboxen).

    ``mounts`` er en ORDNET liste af ``(art, kilde, maal)`` hvor art er ``ro`` (skrivebeskyttet bind),
    ``rw`` (skrivbar bind) eller ``tmpfs`` (kilde ignoreres). Rækkefølgen bevares: en ``tmpfs`` skal
    staa foer de binds der lægges ind i den."""
    argv = [bwrap_path(), "--unshare-all", "--die-with-parent", "--new-session",
            "--cap-drop", "ALL", "--clearenv"]
    for d in _SYSTEM_RO:
        if os.path.exists(d):
            argv += ["--ro-bind", d, d]
    argv += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", "/home"]
    for prefix in python_prefixes():
        argv += ["--ro-bind", prefix, prefix]
    files = worker_files if worker_files is not None else {n: str(_SERVICES_DIR / n) for n in WORKER_FILES}
    for name, src in files.items():
        argv += ["--ro-bind", src, f"/worker/{name}"]
    env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "PYTHONPATH": "/worker",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "LANG": "C.UTF-8"}
    env.update(extra_env or {})
    for k, v in env.items():
        argv += ["--setenv", k, v]
    # Skrivbare mounts: UDELUKKENDE de eksplicit navngivne (agentens eget worktree). Alt andet er
    # skrivebeskyttet eller en privat tmpfs der forsvinder med sandboxen.
    for src, dst in (rw_binds or {}).items():
        argv += ["--bind", src, dst]
    for kind, src, dst in (mounts or []):
        if kind == "tmpfs":
            argv += ["--tmpfs", dst]
        elif kind in ("ro", "rw"):
            argv += ["--ro-bind" if kind == "ro" else "--bind", src, dst]
        else:
            raise ValueError(f"ukendt mount-art {kind!r}")
    argv += ["--chdir", chdir, "--"]
    return argv + list(command)


def pids_limit_disabled() -> bool:
    return os.environ.get(PIDS_OFF_ENV, "").strip().lower() == "off"


def scope_env() -> dict[str, str]:
    """Miljoeet ``systemd-run --user`` skal bruge. En systemd-service har ofte ikke ``XDG_RUNTIME_DIR``."""
    env = dict(os.environ)
    runtime_dir = f"/run/user/{os.getuid()}"
    if not env.get("XDG_RUNTIME_DIR") and os.path.isdir(runtime_dir):
        env["XDG_RUNTIME_DIR"] = runtime_dir
    return env


def _scope_argv(limit: int) -> list[str]:
    exe = shutil.which("systemd-run")
    if not exe:
        raise SandboxUnavailable("systemd-run er ikke installeret - pids-graensen kan ikke haandhaeves")
    return [exe, "--user", "--scope", "--quiet", "--collect", "-p", f"TasksMax={int(limit)}"]


def cgroup_pids_available(*, force: bool = False) -> tuple[bool, str]:
    """Kan vi lave en cgroup-scope med ``TasksMax`` for den aktuelle bruger? Cachet i 30 s (brugerens
    systemd-manager kan komme og gaa, f.eks. uden ``loginctl enable-linger``)."""
    global _probe_cache
    with _probe_lock:
        now = time.monotonic()
        if not force and _probe_cache and now - _probe_cache[0] < _PROBE_TTL_S:
            return _probe_cache[1]
        try:
            proc = subprocess.run([*_scope_argv(64), "true"], env=scope_env(), capture_output=True, timeout=15)
            result = (True, "") if proc.returncode == 0 else (
                False, (proc.stderr.decode("utf-8", "replace").strip()[:200] or f"exit {proc.returncode}"))
        except SandboxUnavailable as exc:
            result = (False, str(exc))
        except Exception as exc:
            logger.warning("cgroup-probe fejlede", exc_info=True)
            result = (False, f"{type(exc).__name__}: {exc}")
        _probe_cache = (now, result)
        return result


def pids_prefix(limit: int | None) -> list[str]:
    """``systemd-run --user --scope -p TasksMax=N`` foer bwrap, eller ``[]`` hvis graensen er fravalgt.
    Kan cgroup-graensen ikke haandhaeves, koerer agenten IKKE (fail-closed som resten af sandboxen) -
    medmindre ejeren eksplicit har sat ``JARVIS_AGENT_PIDS_LIMIT=off``."""
    if limit is None or pids_limit_disabled():
        return []
    ok, why = cgroup_pids_available()
    if not ok:
        raise SandboxUnavailable(f"pids-graense kan ikke haandhaeves (cgroup): {why}")
    return _scope_argv(limit)


def resource_prefix(*, address_space: int, cpu_seconds: int, open_files: int = 256,
                    file_size: int = 64 * 1024 * 1024) -> list[str]:
    """``prlimit`` foer bwrap: graenserne arves af workeren og kan ikke haeves derinde.
    NPROC saettes bevidst IKKE: den taelles pr. bruger paa hele vaerten og ville ramme
    uvedkommende processer."""
    prlimit = shutil.which("prlimit")
    if not prlimit:
        raise SandboxUnavailable("prlimit er ikke installeret")
    return [prlimit, f"--as={address_space}", f"--cpu={cpu_seconds}", f"--nofile={open_files}",
            f"--fsize={file_size}", "--core=0", "--"]


def spawn_in_sandbox(command: list[str], *, pass_fds: tuple[int, ...] = (), stdout=None, stderr=None,
                     address_space: int = 2 * 1024 ** 3, cpu_seconds: int = 4 * 3600,
                     extra_env: dict[str, str] | None = None,
                     worker_files: dict[str, str] | None = None,
                     rw_binds: dict[str, str] | None = None, chdir: str = "/tmp",
                     stdin=None, file_size: int = 64 * 1024 * 1024,
                     mounts: list[tuple[str, str, str]] | None = None,
                     pids_limit: int | None = PIDS_WORKER) -> subprocess.Popen:
    """Start ``command`` i sandboxen under en cgroup-scope med ``TasksMax=pids_limit`` (fork-bombe-vaern).
    Egen processgruppe, saa den kan draebes samlet."""
    argv = resource_prefix(address_space=address_space, cpu_seconds=cpu_seconds, file_size=file_size
                           ) + pids_prefix(pids_limit) + build_bwrap_argv(
        command, pass_fds=pass_fds, extra_env=extra_env, worker_files=worker_files,
        rw_binds=rw_binds, chdir=chdir, mounts=mounts)
    return subprocess.Popen(argv, pass_fds=pass_fds, env=scope_env() if pids_limit is not None else None,
                            stdin=stdin if stdin is not None else subprocess.DEVNULL, stdout=stdout,
                            stderr=stderr, start_new_session=True, close_fds=True)


def sandbox_usable() -> tuple[bool, str]:
    """Smoketest: kan et trivielt program koere i sandboxen? (ja/nej, grund)"""
    try:
        proc = spawn_in_sandbox([sys.executable, "-c", "print('ok')"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, worker_files={})
        out, err = proc.communicate(timeout=20)
    except SandboxUnavailable as exc:
        logger.warning("sandbox ikke tilgaengelig: %s", exc)
        return False, str(exc)
    except Exception as exc:
        logger.warning("sandbox-smoketest fejlede: %s", exc, exc_info=True)
        return False, f"{type(exc).__name__}: {exc}"
    if proc.returncode == 0 and out.strip() == b"ok":
        return True, ""
    return False, (err.decode("utf-8", "replace")[:300] or f"exit {proc.returncode}")
