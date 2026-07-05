from __future__ import annotations

import argparse
import json

from central_cli.client import CentralClient, CentralError
from central_cli.commands import resolve_command
from central_cli.config import resolve_base_url, resolve_token


def execute(client, *, verb: str, args: list[str], as_json: bool) -> tuple[str, int]:
    """Kør én kommando mod klienten. Returnerer (output_tekst, exit_code)."""
    spec = resolve_command(verb, args)
    try:
        if spec.method == "GET":
            data = client.get_json(spec.path)
        else:
            data = client.post_json(spec.path, spec.body or {})
    except CentralError as exc:
        return (f"fejl ({exc.category}): {exc}", 1)
    if as_json:
        return (json.dumps(data, indent=2, ensure_ascii=False, default=str), 0)
    from rich.console import Console
    from central_cli.renderer import render_status, render_generic
    con = Console(record=True)
    con.print(render_status(data) if verb in ("status", "realtime") and isinstance(data, dict) else render_generic(data))
    return (con.export_text(), 0)


def run_script(ns: argparse.Namespace) -> int:
    if not ns.command:
        print("central --script kræver en kommando", flush=True)
        return 2
    base = resolve_base_url(remote=ns.remote)
    token = resolve_token()
    client = CentralClient(base_url=base, token=token)
    try:
        out, code = execute(client, verb=ns.command, args=list(ns.args), as_json=ns.json)
    finally:
        client.close()
    print(out, flush=True)
    return code
