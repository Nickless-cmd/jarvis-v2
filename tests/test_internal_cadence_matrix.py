"""Regressions-guard: en producers depends_on må ALDRIG pege på en producer med
højere (senere) priority — så ville dependencyen aldrig være i `ran_this_tick` når
afhængeren evalueres (én global tick, sorteret efter priority), og afhængeren ville
være PERMANENT blokeret.

Rod-bug (2026-07-15): trainman(p5)→dream_distillation_daemon(p22) og
continuity_healer(p2)→central_self_state(p7) var begge altid blokeret → Trainman
vævede 0 narrative erindringer trods drømme i kø; continuity_healer healede aldrig.

Statisk kilde-scan (ingen runtime-side-effekter: registreringen spawner daemon-tråde
+ tunge imports, som ville forstyrre andre tests). Regex spejler produktions-
registreringernes ProducerSpec(...)-form.
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _strip_comments(text: str) -> str:
    """Fjern #-kommentarer (en kommentar der nævner depends_on=[...] må ikke narre scannet)."""
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in text.splitlines())


def _collect_producers() -> dict[str, int]:
    """name → priority for alle ProducerSpec(...) på tværs af services."""
    prod: dict[str, int] = {}
    for f in glob.glob(str(_REPO / "core/services/*.py")):
        txt = Path(f).read_text(encoding="utf-8")
        for m in re.finditer(r"ProducerSpec\((.*?)\)\)", txt, re.S):
            blk = m.group(1)
            nm = re.search(r"""name=["']([^"']+)""", blk)
            if not nm:
                continue
            pr = re.search(r"priority=(\d+)", blk)
            prod[nm.group(1)] = int(pr.group(1)) if pr else 999
    return prod


def _collect_deps() -> list[tuple[str, int, list[str]]]:
    """(name, priority, deps) for hver ProducerSpec med en ikke-tom depends_on."""
    out: list[tuple[str, int, list[str]]] = []
    for f in glob.glob(str(_REPO / "core/services/*.py")):
        txt = Path(f).read_text(encoding="utf-8")
        for m in re.finditer(r"ProducerSpec\((.*?)\)\)", txt, re.S):
            blk = m.group(1)
            nm = re.search(r"""name=["']([^"']+)""", blk)
            dep = re.search(r"depends_on=\[([^\]]*)\]", blk)
            if not nm or not dep or not dep.group(1).strip():
                continue
            pr = re.search(r"priority=(\d+)", blk)
            deps = re.findall(r"""["']([^"']+)["']""", dep.group(1))
            out.append((nm.group(1), int(pr.group(1)) if pr else 999, deps))
    return out


def test_no_dependency_runs_after_its_dependent():
    prod = _collect_producers()
    assert prod, "fandt ingen ProducerSpec — regex/parsing brudt?"
    offenders = []
    for name, pri, deps in _collect_deps():
        for dep in deps:
            dp = prod.get(dep)
            if dp is None:
                offenders.append(f"{name}(p{pri}) → ukendt producer-dep '{dep}'")
            elif dp >= pri:
                offenders.append(
                    f"{name}(p{pri}) → '{dep}'(p{dp}) kører senere = ALTID BLOKERET")
    assert not offenders, "inverteret dependency-priority:\n" + "\n".join(offenders)
