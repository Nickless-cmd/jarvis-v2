"""bubblewrap-sandbox til en agent-worker (agent-contract-v1 C6b, spec 12.1).

Hver workerproces koerer i et frisk namespace-sæt: ingen netforbindelse, eget pid/ipc/uts/user-
namespace, alle capabilities droppet, ingen ``~/.jarvis-v2`` (dermed hverken credentials eller
andre ejeres runtimefiler), intet repo - kun Python-miljoeet skrivebeskyttet og de tre filer
workeren bruger. Sockets arves som fd. Kan sandboxen ikke etableres, koerer agenten IKKE
(``SandboxUnavailable``): der er ingen stille tilbagegang til en usandboxet proces.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

#: Filer workeren behoever - bindes skrivebeskyttet ind som /worker/<navn>.
logger = logging.getLogger(__name__)

WORKER_FILES = ("agent_worker_main.py", "agent_worker_protocol.py", "agent_loop_core.py")
_SERVICES_DIR = Path(__file__).resolve().parent
#: Systemmapper der bindes skrivebeskyttet hvis de findes (biblioteker og interpreterens afhaengigheder).
_SYSTEM_RO = ("/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/etc/ld.so.cache", "/etc/alternatives")


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
                     worker_files: dict[str, str] | None = None) -> list[str]:
    """Byg ``bwrap``-kommandolinjen for ``command`` (som koeres INDE i sandboxen)."""
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
    argv += ["--chdir", "/tmp", "--"]
    return argv + list(command)


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
                     worker_files: dict[str, str] | None = None) -> subprocess.Popen:
    """Start ``command`` i sandboxen. Egen processgruppe, saa den kan draebes samlet."""
    argv = resource_prefix(address_space=address_space, cpu_seconds=cpu_seconds) + build_bwrap_argv(
        command, pass_fds=pass_fds, extra_env=extra_env, worker_files=worker_files)
    return subprocess.Popen(argv, pass_fds=pass_fds, stdin=subprocess.DEVNULL, stdout=stdout,
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
