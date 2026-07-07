"""Read-only god-fil-kort: alle egne .py-filer ≥1500 linjer, karakteriseret (linjer, funktioner,
klasser, blast-radius = hvor mange filer importerer modulet) → prioriteret snit-rækkefølge.
Kører intet, ændrer intet. Genkør efter hvert snit."""
from __future__ import annotations

import ast
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THRESHOLD = 1500


def own_py_files():
    for base in ("core", "apps", "scripts"):
        for root, _dirs, files in os.walk(os.path.join(REPO, base)):
            if "node_modules" in root or "/.venv" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(root, f)


def blast(dotted, target_rel):
    base = dotted.rsplit(".", 1)[-1]
    try:
        out = subprocess.run(["git", "grep", "-l", "-e", dotted, "-e", f"import {base}"],
                             cwd=REPO, capture_output=True, text=True, timeout=30)
        files = {ln for ln in out.stdout.splitlines() if ln.strip() and ln != target_rel}
        return len(files)
    except Exception:
        return -1


rows = []
for path in own_py_files():
    try:
        src = open(path, encoding="utf-8").read()
    except Exception:
        continue
    n = src.count("\n") + 1
    if n < THRESHOLD:
        continue
    rel = os.path.relpath(path, REPO)
    try:
        tree = ast.parse(src)
        defs = sum(1 for x in ast.walk(tree) if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)))
        top_defs = sum(1 for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)))
        classes = sum(1 for x in tree.body if isinstance(x, ast.ClassDef))
        biggest_class = 0
        for x in tree.body:
            if isinstance(x, ast.ClassDef):
                span = (x.end_lineno or x.lineno) - x.lineno
                biggest_class = max(biggest_class, span)
    except Exception:
        defs = top_defs = classes = biggest_class = -1
    dotted = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel
    tables = src.count("CREATE TABLE")
    rows.append({"rel": rel, "lines": n, "defs": defs, "top_defs": top_defs,
                 "classes": classes, "biggest_class": biggest_class, "tables": tables,
                 "blast": blast(dotted, rel)})

rows.sort(key=lambda r: -r["lines"])

print(f"{'fil':<52}{'linjer':>7}{'func':>6}{'klasse':>7}{'størst-kl':>10}{'tabel':>6}{'blast':>7}  karakter")
print("-" * 120)
for r in rows:
    # karakter-heuristik
    if r["tables"] >= 10:
        kar = f"tabel-skuffe ({r['tables']} tabeller) → split pr. domæne"
    elif r["classes"] <= 2 and r["top_defs"] >= 40:
        kar = "funktions-bibliotek → split pr. funktionsgruppe"
    elif r["biggest_class"] >= r["lines"] * 0.5:
        kar = f"gud-klasse ({r['biggest_class']} linjer) → udskil metoder/mixins"
    else:
        kar = "blandet → udskil nærmeste sammenhængende enhed"
    print(f"{r['rel']:<52}{r['lines']:>7}{r['defs']:>6}{r['classes']:>7}{r['biggest_class']:>10}"
          f"{r['tables']:>6}{r['blast']:>7}  {kar}")

total = sum(r["lines"] for r in rows)
print("-" * 120)
print(f"{len(rows)} god-filer · {total:,} linjer tilsammen")
# sikker rækkefølge-forslag: lav blast-radius + klar karakter først
safe = sorted(rows, key=lambda r: (r["blast"] if r["blast"] >= 0 else 9999, -r["lines"]))
print("\nFORESLÅET RÆKKEFØLGE (lav blast-radius = tryggest først):")
for r in safe[:8]:
    print(f"  {r['rel']:<48} blast={r['blast']:<5} {r['lines']:>6} linjer")
