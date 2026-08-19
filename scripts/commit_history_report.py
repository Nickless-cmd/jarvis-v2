#!/usr/bin/env python3
"""Generér en læsbar commit-historie grupperet pr. måned og uge.

Formål (Bjørn, 19. aug 2026): finde systemer der blev bygget og siden ligger stille.
Derfor er rapporten TO ting:

1. **Kronologien** — hver commit, grupperet pr. måned → ISO-uge, med dato-spænd.
2. **Fødsels-indekset** — hver ny fil under ``core/services/``, hvornår den kom, og om
   nogen importerer den i dag. En fil ingen importerer er ikke nødvendigvis død (den kan
   være en cadence-producer eller en route), men den er stedet at kigge først.

Kør: ``python scripts/commit_history_report.py [output.md]``
Statisk — kører ikke systemet, kalder ingen modeller.
"""
from __future__ import annotations

import collections
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

_SEP = "\x1f"
_MONTHS_DA = {
    1: "januar", 2: "februar", 3: "marts", 4: "april", 5: "maj", 6: "juni",
    7: "juli", 8: "august", 9: "september", 10: "oktober", 11: "november", 12: "december",
}
# Conventional-commit-typer → læsbar dansk overskrift. Rækkefølgen er visnings-rækkefølgen.
_TYPE_LABELS = [
    ("feat", "Nyt"),
    ("fix", "Rettelser"),
    ("refactor", "Omstrukturering"),
    ("perf", "Ydelse"),
    ("test", "Tests"),
    ("docs", "Dokumentation"),
    ("chore", "Vedligehold"),
    ("style", "Formatering"),
    ("build", "Build"),
    ("ci", "CI"),
    ("revert", "Tilbagerulning"),
]
_KNOWN_TYPES = {t for t, _ in _TYPE_LABELS}
_SUBJECT_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?!?:\s*(?P<rest>.*)$")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          check=True).stdout


def _commits() -> list[dict]:
    fmt = _SEP.join(["%h", "%ad", "%an", "%s"])
    raw = _git("log", "--reverse", f"--pretty=format:{fmt}", "--date=format:%Y-%m-%d")
    out = []
    for line in raw.splitlines():
        parts = line.split(_SEP)
        if len(parts) != 4:
            continue
        h, d, author, subject = parts
        m = _SUBJECT_RE.match(subject)
        ctype = (m.group("type") if m else "") or ""
        out.append({
            "hash": h, "date": d, "author": author, "subject": subject,
            "type": ctype if ctype in _KNOWN_TYPES else "andet",
            "scope": (m.group("scope") if m else "") or "",
            "text": (m.group("rest") if m else subject),
        })
    return out


def _week_span(iso_year: int, iso_week: int) -> str:
    monday = date.fromisocalendar(iso_year, iso_week, 1)
    sunday = monday + timedelta(days=6)
    if monday.month == sunday.month:
        return f"{monday.day}.–{sunday.day}. {_MONTHS_DA[monday.month]}"
    return (f"{monday.day}. {_MONTHS_DA[monday.month]} – "
            f"{sunday.day}. {_MONTHS_DA[sunday.month]}")


def _new_service_files() -> list[dict]:
    """Hver fil der nogensinde blev TILFØJET under core/services/, med fødselsdato."""
    raw = _git("log", "--reverse", "--diff-filter=A", "--name-only",
               f"--pretty=format:{_SEP}%h{_SEP}%ad", "--date=format:%Y-%m-%d",
               "--", "core/services/")
    out, h, d = [], "", ""
    for line in raw.splitlines():
        if line.startswith(_SEP):
            _, h, d = line.split(_SEP)
            continue
        p = line.strip()
        # __init__.py er pakke-stilladser, ikke systemer — de ville fylde listen med støj.
        if p.endswith(".py") and p.startswith("core/services/") \
                and Path(p).name != "__init__.py":
            out.append({"path": p, "hash": h, "date": d})
    return out


def _import_counts(paths: list[str]) -> dict[str, int]:
    """Hvor mange andre filer nævner modulet? 0 = værd at kigge på først.

    Mønsteret er modul-NAVNET med ordgrænser, ikke ``services.<navn>``. Første udgave
    brugte det sidste og udpegede derfor hele `prompt_sections/` som forældreløst —
    de importeres som `core.services.prompt_sections.causal_alerts`, hvor `services.`
    efterfølges af pakken, ikke modulet. En falsk forældreløs er værre end ingen liste:
    den sender oprydning efter noget der lever. Navnet alene overmatcher en anelse
    (en omtale i en kommentar tæller med), og den retning er den sikre.
    """
    counts: dict[str, int] = {}
    for p in paths:
        mod = Path(p).stem
        try:
            r = subprocess.run(
                ["grep", "-rlw", "--include=*.py", mod, "core", "apps", "scripts"],
                capture_output=True, text=True)
            hits = {ln for ln in r.stdout.splitlines() if ln and not ln.endswith(p)}
        except Exception:
            hits = set()
        counts[p] = len(hits)
    return counts


def build(out_path: Path) -> None:
    commits = _commits()
    if not commits:
        raise SystemExit("ingen commits fundet")

    by_month: dict[str, list[dict]] = collections.OrderedDict()
    for c in commits:
        by_month.setdefault(c["date"][:7], []).append(c)

    first, last = commits[0]["date"], commits[-1]["date"]
    authors = collections.Counter(c["author"] for c in commits)
    types = collections.Counter(c["type"] for c in commits)

    L: list[str] = []
    A = L.append
    A("# Jarvis V2 — komplet commit-historie")
    A("")
    A(f"**{len(commits):,} commits** fra {first} til {last} · "
      f"{len(by_month)} måneder · genereret af `scripts/commit_history_report.py`")
    A("")
    A("Formål: finde systemer der blev bygget og siden ligger stille. Se "
      "**[Fødsels-indekset](#fødsels-indeks--nye-systemer-i-coreservices)** nederst — "
      "det er dér man leder først.")
    A("")

    A("## Fordeling")
    A("")
    A("| Type | Antal | Andel |")
    A("|---|---:|---:|")
    for t, label in _TYPE_LABELS + [("andet", "Uden type-præfiks")]:
        n = types.get(t, 0)
        if n:
            A(f"| {label} (`{t}`) | {n:,} | {n / len(commits):.0%} |")
    A("")
    if len(authors) > 1:
        A("| Forfatter | Commits |")
        A("|---|---:|")
        for a, n in authors.most_common():
            A(f"| {a} | {n:,} |")
        A("")

    A("## Indhold")
    A("")
    for ym, cs in by_month.items():
        y, mm = int(ym[:4]), int(ym[5:])
        A(f"- [{_MONTHS_DA[mm].capitalize()} {y}](#{_MONTHS_DA[mm]}-{y}) — {len(cs):,} commits")
    A("- [Fødsels-indeks](#fødsels-indeks--nye-systemer-i-coreservices)")
    A("")
    A("---")
    A("")

    for ym, cs in by_month.items():
        y, mm = int(ym[:4]), int(ym[5:])
        A(f"## {_MONTHS_DA[mm].capitalize()} {y}")
        A("")
        A(f"*{len(cs):,} commits · {cs[0]['date']} → {cs[-1]['date']}*")
        A("")
        by_week: dict[tuple[int, int], list[dict]] = collections.OrderedDict()
        for c in cs:
            dt = datetime.strptime(c["date"], "%Y-%m-%d").date()
            iso = dt.isocalendar()
            by_week.setdefault((iso[0], iso[1]), []).append(c)
        for (iy, iw), wcs in by_week.items():
            A(f"### Uge {iw} · {_week_span(iy, iw)} — {len(wcs)} commits")
            A("")
            grouped: dict[str, list[dict]] = collections.OrderedDict()
            for t, _ in _TYPE_LABELS:
                grouped[t] = []
            grouped["andet"] = []
            for c in wcs:
                grouped[c["type"]].append(c)
            for t, label in _TYPE_LABELS + [("andet", "Øvrigt")]:
                items = grouped.get(t) or []
                if not items:
                    continue
                A(f"**{label}**")
                A("")
                for c in items:
                    scope = f"**{c['scope']}** · " if c["scope"] else ""
                    A(f"- `{c['hash']}` {c['date']} — {scope}{c['text']}")
                A("")
        A("---")
        A("")

    # ── Fødsels-indeks ────────────────────────────────────────────────────────
    A("## Fødsels-indeks — nye systemer i `core/services/`")
    A("")
    news = _new_service_files()
    alive = [n for n in news if Path(n["path"]).exists()]
    gone = len(news) - len(alive)
    counts = _import_counts([n["path"] for n in alive])
    orphans = [n for n in alive if counts.get(n["path"], 0) == 0]

    A(f"**{len(news)} filer** er blevet tilføjet under `core/services/` gennem historien. "
      f"**{len(alive)}** findes stadig ({gone} er siden slettet eller flyttet).")
    A("")
    A(f"**{len(orphans)} af dem importeres ingen steder** i `core/`, `apps/` eller "
      f"`scripts/` i dag. Det betyder ikke automatisk at de er døde — en cadence-producer "
      f"eller en route kan blive nået dynamisk — men det er stedet at lede først.")
    A("")
    A("> Kør `python scripts/capability_audit.py` for den dybere live/stale/orphan-analyse "
      "(`docs/capability_matrix.md`).")
    A("")
    if orphans:
        A("### Uden importører i dag")
        A("")
        A("| Fil | Født | Commit |")
        A("|---|---|---|")
        for n in sorted(orphans, key=lambda z: z["date"]):
            A(f"| `{Path(n['path']).name}` | {n['date']} | `{n['hash']}` |")
        A("")
    A("### Alle nye systemer, i fødselsrækkefølge")
    A("")
    A("| Fil | Født | Commit | Importører |")
    A("|---|---|---|---:|")
    for n in sorted(alive, key=lambda z: z["date"]):
        c = counts.get(n["path"], 0)
        mark = " ⚠️" if c == 0 else ""
        A(f"| `{Path(n['path']).name}` | {n['date']} | `{n['hash']}` | {c}{mark} |")
    A("")

    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{out_path}: {len(commits):,} commits · {len(by_month)} måneder · "
          f"{len(alive)} levende service-filer · {len(orphans)} uden importører")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/COMMIT_HISTORY.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    build(target)
