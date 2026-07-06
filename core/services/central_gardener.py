"""Gardener Protocol — Centralen tager saksen selv (governed + reversibelt).

Bjørn+Claude (6. jul, tema #4): excess-sansen gav Centralen ØJNE (mærk vægt) + et FØRSTE snit.
Dette giver den HÅNDEN: find konkrete snit, ARKIVÉR dem (regrow — intet går tabt), klip, og lad
kalderen verificere hårdt før deploy. "Yes, Jarvis"-gaten = mennesket kører execute + godkender.

MÅL denne omgang: den brede attrap-beskæring. Coverage-pushet (2026-05-13) tilføjede ~107 par af
`build_*_surface()` (returnerer placeholder {"active": True, "summary": "Module loaded..."}) +
`_emit_*_event()` (docstring: "Cartographer scans for event_bus.publish()") — dødt scaffold hvis
ENESTE formål var at narre cartographer/coverage-scannet. 0 referencer, ingen dynamisk dispatch.

SIKKERHED: (1) kun det PRÆCISE decoy-mønster (placeholder-body / cartographer-docstring) + 0 git-
referencer. (2) ægte build_*_surface (kaldt direkte) røres ALDRIG — de har >1 reference. (3) alt
arkiveres til regrow-store FØR klip. (4) kalderen SKAL compile+importere+teste før deploy; git er
sidste net. Read-only indtil execute=True.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
from datetime import UTC, datetime
from typing import Any

REPO = "/media/projects/jarvis-v2"
_SCAN = os.path.join(REPO, "core", "services")
_REGROW_DIR = os.path.join(REPO, "docs", "gardener")

_DECOY_SURFACE_MARK = "Module loaded; entry points available"
_DECOY_EMIT_MARK = "Cartographer scans for event_bus.publish"


def _ref_count(name: str) -> int:
    """Antal ord-grænsede forekomster i hele repoet INKL. tests (1 = kun dens egen def = frit-
    klipbar). VIGTIGT (6. jul-lære): tests SKAL med — coverage-pushet gav attrapperne smoke-tests,
    så en attrap uden produktions-referencer er stadig test-viklet og IKKE et frit snit."""
    try:
        r = subprocess.run(["git", "-C", REPO, "grep", "-wc", name, "--",
                           "core", "apps", "scripts", "tests"],
                           capture_output=True, text=True, timeout=20)
        return sum(int(l.rsplit(":", 1)[-1]) for l in r.stdout.splitlines() if ":" in l)
    except Exception:
        return 99


def _is_decoy(node: ast.AST, src_segment: str) -> str | None:
    """Returnér decoy-type ('surface'/'emit') hvis noden matcher PRÆCIST attrap-mønster, ellers None."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    name = node.name
    if name.startswith("build_") and name.endswith("_surface") and _DECOY_SURFACE_MARK in src_segment:
        return "surface"
    if name.startswith("_emit_") and name.endswith("_event") and _DECOY_EMIT_MARK in src_segment:
        return "emit"
    return None


def find_decoy_cuts() -> list[dict[str, Any]]:
    """Find alle attrap-funktioner (præcist mønster + 0 referencer). Read-only. Self-safe."""
    cuts: list[dict[str, Any]] = []
    try:
        files = sorted(os.path.join(r, f) for r, _, fs in os.walk(_SCAN)
                       for f in fs if f.endswith(".py"))
    except Exception:
        return cuts
    for path in files:
        try:
            src = open(path, encoding="utf-8").read()
            lines = src.splitlines(keepends=True)
            tree = ast.parse(src)
        except Exception:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            seg = "".join(lines[node.lineno - 1: node.end_lineno])
            kind = _is_decoy(node, seg)
            if not kind:
                continue
            if _ref_count(node.name) > 1:      # kaldt et sted → IKKE en attrap, rør den ikke
                continue
            cuts.append({
                "file": os.path.relpath(path, REPO), "name": node.name, "kind": kind,
                "start": node.lineno, "end": node.end_lineno, "source": seg,
            })
    return cuts


def prune_decoys(*, execute: bool = False, stamp: str = "") -> dict[str, Any]:
    """Beskær attrapperne. execute=False = tør-kørsel (list kun). execute=True = arkivér → klip.
    Klipper bundtop pr. fil så linjenumre holder. Self-safe; returnerer rapport."""
    cuts = find_decoy_cuts()
    report: dict[str, Any] = {
        "found": len(cuts), "files": len(set(c["file"] for c in cuts)),
        "surface": sum(1 for c in cuts if c["kind"] == "surface"),
        "emit": sum(1 for c in cuts if c["kind"] == "emit"),
        "executed": False, "archive": "", "cut": 0,
    }
    if not execute or not cuts:
        report["sample"] = [f"{c['file']}:{c['name']}" for c in cuts[:8]]
        return report

    # 1) ARKIVÉR (regrow) FØR noget klippes
    os.makedirs(_REGROW_DIR, exist_ok=True)
    stamp = stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    archive = os.path.join(_REGROW_DIR, f"pruned-{stamp}.json")
    try:
        with open(archive, "w", encoding="utf-8") as fh:
            json.dump(cuts, fh, ensure_ascii=False, indent=1)
    except Exception:
        report["error"] = "arkivering fejlede — INTET klippet"
        return report
    report["archive"] = os.path.relpath(archive, REPO)

    # 2) KLIP — pr. fil, bundtop (bevar linjenumre)
    by_file: dict[str, list[dict[str, Any]]] = {}
    for c in cuts:
        by_file.setdefault(c["file"], []).append(c)
    cut_n = 0
    for rel, fcuts in by_file.items():
        path = os.path.join(REPO, rel)
        try:
            lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
            for c in sorted(fcuts, key=lambda x: -x["start"]):
                del lines[c["start"] - 1: c["end"]]      # fjern def-blokken
                cut_n += 1
            # kollapsér 3+ tomme linjer → 2
            out, blanks = [], 0
            for ln in lines:
                if ln.strip() == "":
                    blanks += 1
                    if blanks <= 2:
                        out.append(ln)
                else:
                    blanks = 0
                    out.append(ln)
            open(path, "w", encoding="utf-8").write("".join(out))
        except Exception:
            continue
    report["executed"] = True
    report["cut"] = cut_n
    return report
