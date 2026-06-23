"""central_terminal — en command-line ind i Den Intelligente Central (owner-terminal).

Bjørn 2026-06-23: "kan central-siden have en live terminal hvor jeg kan skrive og teste via
commandline i centralen?" Ja. Dette er en tynd REPL der parser en kommando-linje og dispatcher
til central_query (read + toggle, m. fuld sikkerheds-gating) + provider_health, og returnerer
terminal-linjer. Owner-only håndhæves i route'n. Self-safe: enhver fejl → struktureret fejl-linje.

ALDRIG destruktiv ud over hvad central_query allerede tillader (sikkerheds-nerver kan ikke slås
fra). Ny funktionalitet kommer KUN via nye, eksplicit godkendte kommandoer.
"""
from __future__ import annotations

import shlex
from typing import Any

_HELP = [
    "kommandoer:",
    "  status                  — Centralens puls (status/dækning/processer)",
    "  clusters                — sundhed pr. cluster",
    "  incidents [n]           — uløste flag (default 10)",
    "  trace [cluster] [n]     — seneste nerve-fyringer",
    "  nerve <navn>            — spor + lokation + on/off-tilstand",
    "  toggle <nerve> on|off   — tænd/sluk en nerve (sikkerheds-nerver låst)",
    "  scan                    — kør silent-failure-scan (instrument)",
    "  instrument [n]          — top fund fra seneste scan",
    "  providers               — provider-helbred (ping/tør/drift)",
    "  learning | drift | breakers | autonomy",
    "  help                    — denne liste",
]


def _q(action: str, **kw: Any) -> dict[str, Any]:
    from core.tools.central_query_tool import central_query
    return central_query({"action": action, **kw})


def _fmt_envelope(env: dict[str, Any]) -> list[str]:
    """central_query-envelope → terminal-linjer (kompakt, læsbar)."""
    if env.get("status") == "error":
        return [f"! {env.get('error') or 'fejl'}"]
    data = env.get("data")
    action = env.get("action")
    out: list[str] = []
    if action == "status" and isinstance(data, dict):
        cov = data.get("coverage") if isinstance(data.get("coverage"), dict) else {}
        out.append(f"status: {str(data.get('status','?')).upper()}  "
                   f"nerver={cov.get('nerves','?')} clusters={cov.get('clusters','?')} "
                   f"breakers={data.get('open_breakers','?')} flag={data.get('unresolved_incidents','?')}")
        cl = data.get("clusters") if isinstance(data.get("clusters"), dict) else {}
        bad = [f"{k}:{v}" for k, v in cl.items() if v in ("red", "yellow")]
        if bad:
            out.append("  obs: " + ", ".join(bad))
    elif isinstance(data, dict) and isinstance(data.get("items"), list):
        items = data["items"]
        if not items:
            out.append("(ingen)")
        for it in items[:20]:
            if isinstance(it, dict):
                bits = [str(it.get(k)) for k in ("severity", "cluster", "nerve", "kind",
                                                 "decision", "score", "file", "message", "title")
                        if it.get(k) not in (None, "")]
                out.append("  " + " · ".join(bits)[:160])
        if data.get("has_more"):
            out.append(f"  … +{int(data.get('total_count', 0)) - len(items[:20])} flere")
    elif isinstance(data, dict):
        for k, v in list(data.items())[:14]:
            out.append(f"  {k}: {str(v)[:120]}")
    else:
        out.append(str(data)[:200])
    return out or ["(tomt)"]


def run_command(line: str) -> dict[str, Any]:
    """Parse + udfør én terminal-kommando. Returnerer {ok, command, lines}. Self-safe."""
    raw = str(line or "").strip()
    if not raw:
        return {"ok": True, "command": "", "lines": []}
    try:
        parts = shlex.split(raw)
    except Exception:
        parts = raw.split()
    cmd = parts[0].lower()
    args = parts[1:]

    try:
        if cmd in ("help", "?", "h"):
            return {"ok": True, "command": cmd, "lines": list(_HELP)}
        if cmd in ("status", "clusters", "learning", "drift", "breakers", "autonomy"):
            act = "cluster_health" if cmd == "clusters" else cmd
            return {"ok": True, "command": cmd, "lines": _fmt_envelope(_q(act))}
        if cmd == "incidents":
            n = int(args[0]) if args and args[0].isdigit() else 10
            return {"ok": True, "command": cmd, "lines": _fmt_envelope(_q("incidents", limit=n))}
        if cmd == "trace":
            cluster = next((a for a in args if not a.isdigit()), "")
            n = next((int(a) for a in args if a.isdigit()), 15)
            return {"ok": True, "command": cmd,
                    "lines": _fmt_envelope(_q("trace", cluster=cluster, limit=n))}
        if cmd == "nerve":
            if not args:
                return {"ok": False, "command": cmd, "lines": ["! brug: nerve <navn>"]}
            return {"ok": True, "command": cmd, "lines": _fmt_envelope(_q("nerve_detail", nerve=args[0]))}
        if cmd == "toggle":
            if len(args) < 2 or args[1].lower() not in ("on", "off"):
                return {"ok": False, "command": cmd, "lines": ["! brug: toggle <nerve> on|off"]}
            env = _q("toggle_nerve", nerve=args[0], enabled=(args[1].lower() == "on"))
            return {"ok": env.get("status") == "ok", "command": cmd, "lines": _fmt_envelope(env)}
        if cmd in ("scan", "instrument"):
            do_scan = cmd == "scan"
            n = int(args[0]) if args and args[0].isdigit() else 10
            env = _q("instrument", scan=do_scan, limit=n)
            return {"ok": True, "command": cmd, "lines": _fmt_envelope(env)}
        if cmd in ("providers", "provider"):
            from core.services.provider_health_check import build_provider_health_surface
            surf = build_provider_health_surface() or {}
            lines = [str(surf.get("summary") or "providers")]
            for r in (surf.get("providers") or [])[:12]:
                mark = "ok" if r.get("ok") else ("degraderet" if r.get("degraded") else "NEDE")
                lines.append(f"  {r.get('provider'):14} {mark:11} {r.get('latency_ms','?')}ms "
                             f"modeller={r.get('model_count','?')}")
            dry = surf.get("dry_cheap") or []
            if dry:
                lines.append("  tørre (cooldown): " + ", ".join(dry))
            return {"ok": True, "command": cmd, "lines": lines}
        return {"ok": False, "command": cmd,
                "lines": [f"! ukendt kommando '{cmd}' — skriv 'help'"]}
    except Exception as exc:
        return {"ok": False, "command": cmd, "lines": [f"! {type(exc).__name__}: {exc}"[:160]]}
