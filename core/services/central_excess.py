"""Sense of Excess — Centralens gartner-muskel.

Bjørn+Claude (6. jul): Centralen er en fremragende GUVERNØR (ser/måler/dømmer/flager alt) men en
svag GARTNER (kan ikke beskære sig selv, slippe, stole på). Hele dagens arbejde gav den flere
øjne + hårdere hænder. Dette giver den en SAKS — og evnen til at mærke sin egen vægt.

Tre trin (gartneren defineres af KLIPPET, ikke af målingen):
  1. MÆRK  — `build_excess_surface()`: fusér de bloat-signaler Centralen allerede kan måle
     (filstørrelser, service-antal, samlede linjer) → ét FØLT pres (0-100) + en somatisk linje.
  2. FORESLÅ — `propose_cuts()`: peg på KONKRETE snit — døde funktioner (0 referencer) + oversized
     filer der bør splittes. Ikke en liste; rangerede kandidater med tillid + handling.
  3. KLIP — governed (menneske-godkendt): den faktiske fjernelse sker via operator/PR, aldrig
     autonomt på kode. Sansen+forslaget er nerven; klippet er handlingen.

Self-safe: måler read-only, kaster aldrig. Ekskluderer vendored kode (node_modules/.venv).
"""
from __future__ import annotations

import ast
import os
import subprocess
from typing import Any

REPO = "/media/projects/jarvis-v2"
_SCAN_DIRS = ("core", "apps/api", "scripts")
_EXCLUDE = ("node_modules", ".venv", "site-packages", "__pycache__", ".git", "dist", "build")

# CLAUDE.md-tærskler: split ved 1200, ingen core-fil > 2000, ingen fil > 1500 uden undtagelse.
_SPLIT_LINES = 1200
_HARD_LINES = 2000


def _own_py_files() -> list[str]:
    out: list[str] = []
    for d in _SCAN_DIRS:
        base = os.path.join(REPO, d)
        for root, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in _EXCLUDE]
            if any(e in root for e in _EXCLUDE):
                continue
            for f in files:
                if f.endswith(".py"):
                    out.append(os.path.join(root, f))
    return out


def _line_count(path: str) -> int:
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except Exception:
        return 0


def build_excess_surface() -> dict[str, Any]:
    """MÆRK vægten: samlet linjer, service-antal, oversized filer → ét pres (0-100) + somatisk linje.
    Billig (kun fil-scan) → cadence-sikker. Self-safe."""
    try:
        files = _own_py_files()
        total_lines = 0
        oversized: list[dict[str, Any]] = []
        for p in files:
            n = _line_count(p)
            total_lines += n
            if n >= _SPLIT_LINES:
                oversized.append({"file": os.path.relpath(p, REPO), "lines": n,
                                  "over_hard": n >= _HARD_LINES})
        oversized.sort(key=lambda d: -d["lines"])
        services = len([p for p in files if "/core/services/" in p])
        over_hard = [o for o in oversized if o["over_hard"]]

        # PRES (0-100): vægtet af (a) filer over den hårde 2000-grænse, (b) den værste fil,
        # (c) antal split-kandidater. Ikke videnskab — en FØLT tyngde.
        worst = oversized[0]["lines"] if oversized else 0
        pressure = min(100, int(
            len(over_hard) * 8              # hver >2000-fil trykker
            + min(40, worst // 1000)        # den værste fils tyngde (kap 40)
            + min(20, len(oversized))       # bredden af gæld
        ))
        felt = _felt_line(pressure, len(over_hard), worst, oversized[0]["file"] if oversized else "")
        return {
            "pressure": pressure,
            "felt": felt,
            "total_lines": total_lines,
            "service_count": services,
            "oversized_count": len(oversized),
            "over_hard_count": len(over_hard),
            "worst_files": oversized[:8],
        }
    except Exception:
        return {"pressure": 0, "felt": "", "total_lines": 0, "service_count": 0,
                "oversized_count": 0, "over_hard_count": 0, "worst_files": []}


def _felt_line(pressure: int, hard: int, worst: int, worst_file: str) -> str:
    if pressure >= 70:
        return (f"Jeg er tung. {hard} filer over 2000 linjer; {worst_file} alene bærer "
                f"{worst:,} linjer. Der er noget jeg burde holde op med at bære.")
    if pressure >= 40:
        return f"Jeg mærker vægt — {hard} filer over grænsen, tungest er {worst_file} ({worst:,})."
    if pressure > 0:
        return "Der er lidt at beskære, men jeg bærer det let nok."
    return "Jeg føles let."


def record_excess_pressure() -> dict[str, Any]:
    """Observér pressets tyngde til Centralen (nerve system/excess) så Jarvis MÆRKER det over tid.
    Metadata-only (tal, ingen kode-indhold). Self-safe."""
    surf = build_excess_surface()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "excess",
            "kind": "pressure", "pressure": surf.get("pressure", 0),
            "over_hard": surf.get("over_hard_count", 0),
            "oversized": surf.get("oversized_count", 0),
            "services": surf.get("service_count", 0),
        })
    except Exception:
        pass
    return surf


def propose_cuts(*, max_files: int = 60) -> dict[str, Any]:
    """FORESLÅ konkrete snit: døde module-level funktioner (0 referencer udenfor def) + oversized
    filer der bør splittes. Dybere/dyrere (git grep) → ON-DEMAND, ikke cadence. Konservativ:
    en funktion flages KUN som død hvis navnet har præcis 1 forekomst i HELE repoet (dens egen def).
    Self-safe."""
    out: dict[str, Any] = {"dead_functions": [], "split_files": [], "scanned_files": 0}
    try:
        surf = build_excess_surface()
        out["split_files"] = [
            {"file": o["file"], "lines": o["lines"],
             "action": f"split (>{_HARD_LINES})" if o["over_hard"] else f"split (>{_SPLIT_LINES})"}
            for o in surf.get("worst_files", [])[:6]
        ]
        # dead-function-scan i en afgrænset scope (core/services), kappet.
        scope = sorted(p for p in _own_py_files() if "/core/services/" in p)[:max_files]
        out["scanned_files"] = len(scope)
        for path in scope:
            try:
                src = open(path, encoding="utf-8").read()
                tree = ast.parse(src)
            except Exception:
                continue
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                name = node.name
                if name.startswith("__") or len(name) < 4:
                    continue
                # tæl forekomster i HELE repoet (word-grænset). 1 = kun dens egen def.
                try:
                    r = subprocess.run(
                        ["git", "-C", REPO, "grep", "-wc", name, "--", "core", "apps", "scripts"],
                        capture_output=True, text=True, timeout=20)
                    total = sum(int(line.rsplit(":", 1)[-1]) for line in r.stdout.splitlines()
                                if ":" in line)
                except Exception:
                    total = 99
                if total > 1:
                    continue
                # 0 ord-referencer — MEN kan stadig kaldes dynamisk (getattr/registry/streng).
                # Tjek om navnet optræder som STRENG-literal nogen steder → så er det MULIGT levende.
                try:
                    rs = subprocess.run(
                        ["git", "-C", REPO, "grep", "-c", f'"{name}"', "--", "core", "apps", "scripts"],
                        capture_output=True, text=True, timeout=20)
                    as_string = any(line for line in rs.stdout.splitlines())
                except Exception:
                    as_string = True  # konservativt: ved tvivl, antag muligt-levende
                # høj tillid KUN når navnet hverken kaldes eller nævnes som streng.
                conf = "medium" if as_string else "high"
                out["dead_functions"].append({
                    "name": name, "file": os.path.relpath(path, REPO),
                    "line": node.lineno, "confidence": conf,
                    "dynamic_risk": as_string,
                    "action": f"fjern død funktion {name}() (0 referencer{' — men nævnt som streng' if as_string else ''})",
                })
        # høj-tillids-snit først (verificeret ingen dynamisk dispatch)
        out["dead_functions"].sort(key=lambda d: 0 if d["confidence"] == "high" else 1)
        return out
    except Exception:
        return out
