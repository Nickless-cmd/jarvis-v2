"""Read-only db.py dekomponerings-kort — grupperer 171 tabeller i naturlige domæner efter
FUNKTIONS-KOBLING (hvilke tabeller røres af de samme funktioner) og rangerer efter hvor
selvstændige de er → sikker snit-rækkefølge. Kører intet, ændrer intet.
"""
from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict

DB = "core/runtime/db.py"
src = open(DB, encoding="utf-8").read()
lines = src.splitlines()
tree = ast.parse(src)

# 1) tabel-navne
tables = sorted(set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", src)) |
                set(re.findall(r"CREATE TABLE (\w+)", src)))
tset = set(tables)

# 2) top-level funktioner: navn, linjespan, tabeller-rørt
funcs = []
for node in tree.body:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    a, b = node.lineno, (node.end_lineno or node.lineno)
    body = "\n".join(lines[a - 1:b])
    touched = {t for t in tset if re.search(r"\b" + re.escape(t) + r"\b", body)}
    n_create = body.count("CREATE TABLE")
    funcs.append({"name": node.name, "lines": b - a + 1, "tables": touched, "schema": n_create > 5})

schema_funcs = [f for f in funcs if f["schema"]]

# 3) union-find over tabeller via ikke-schema-funktioner (schema-init rører ALT → ville kollapse grafen)
parent = {t: t for t in tables}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    parent[find(a)] = find(b)

for f in funcs:
    if f["schema"]:
        continue
    ts = list(f["tables"])
    for i in range(1, len(ts)):
        union(ts[0], ts[i])

comps = defaultdict(list)
for t in tables:
    comps[find(t)].append(t)

# 4) tildel funktioner + mål grænse-kobling
def comp_of(t):
    return find(t)

comp_stats = {}
for root, ctabs in comps.items():
    cset = set(ctabs)
    pure_funcs = [f for f in funcs if not f["schema"] and f["tables"] and f["tables"] <= cset]
    boundary = [f for f in funcs if not f["schema"] and f["tables"] and
                (f["tables"] & cset) and not (f["tables"] <= cset)]
    pure_lines = sum(f["lines"] for f in pure_funcs)
    # domæne-navn = hyppigste præfiks-token blandt tabellerne
    toks = Counter(t.split("_")[0] for t in ctabs)
    name = toks.most_common(1)[0][0]
    comp_stats[root] = {"name": name, "tables": ctabs, "n_tables": len(ctabs),
                        "pure_funcs": len(pure_funcs), "pure_lines": pure_lines,
                        "boundary_funcs": len(boundary)}

# 5) rangér: sikrest først = 0 grænse-koblinger, derefter størst gevinst (linjer)
ranked = sorted(comp_stats.values(),
                key=lambda c: (c["boundary_funcs"], -c["pure_lines"]))

print(f"db.py: {len(lines)} linjer · {len([f for f in funcs if not f['schema']])} CRUD-funktioner · "
      f"{len(tables)} tabeller · {len(schema_funcs)} schema-init-funktioner (rører alt — flyttes sidst)")
print(f"naturlige domæner (funktions-koblede komponenter): {len(comp_stats)}\n")
print(f"{'#':>3} {'domæne':<22} {'tab':>4} {'func':>5} {'~linjer':>8} {'grænse':>7}  sikkerhed")
print("-" * 74)
safe_lines = 0
for i, c in enumerate(ranked[:30], 1):
    safety = "TRYG" if c["boundary_funcs"] == 0 else ("moderat" if c["boundary_funcs"] <= 3 else "kobl.")
    if c["boundary_funcs"] == 0 and c["n_tables"] <= 8:
        safe_lines += c["pure_lines"]
    print(f"{i:>3} db_{c['name']:<19} {c['n_tables']:>4} {c['pure_funcs']:>5} {c['pure_lines']:>8} "
          f"{c['boundary_funcs']:>7}  {safety}")

# SMÅ trygge domæner = isoleret OG lille (ekskl. den tanglede kerne-komponent)
small_safe = [c for c in ranked if c["boundary_funcs"] == 0 and 0 < c["n_tables"] <= 8]
mega = [c for c in ranked if c["n_tables"] > 20]
print(f"\nSMÅ TRYGGE domæner (0 grænse-kobling, ≤8 tabeller): {len(small_safe)}")
print(f"  → samlet quick-win: ~{sum(c['pure_lines'] for c in small_safe):,} linjer, "
      f"{sum(c['pure_funcs'] for c in small_safe)} funktioner, NUL risiko (re-eksport holder imports)")
print("\nFØRSTE 8 SNIT (rækkefølge — start her, baseline før hver):")
for c in small_safe[:8]:
    print(f"  db_{c['name']}.py  ← {c['n_tables']} tab, {c['pure_funcs']} func, ~{c['pure_lines']} linjer :: "
          f"{', '.join(c['tables'][:4])}{'…' if c['n_tables']>4 else ''}")

if mega:
    m = mega[0]
    print(f"\n⚠️  DEN TANGLEDE KERNE: db_{m['name']} — {m['n_tables']} tabeller, {m['pure_funcs']} funktioner, "
          f"~{m['pure_lines']:,} linjer ({100*m['pure_lines']//len(lines)}% af db.py)")
    mset = set(m["tables"])
    entanglers = sorted(
        ((f["name"], len(f["tables"] & mset), f["lines"]) for f in funcs
         if not f["schema"] and len(f["tables"] & mset) >= 4),
        key=lambda x: -x[1])[:12]
    print("   HVORFOR er den tanglet? Top 'entangler'-funktioner (rører mange tabeller = knuderne):")
    for name, ntab, ln in entanglers:
        print(f"     {name:<42} rører {ntab:>2} tabeller ({ln} linjer)")
    print("   → Fase 2: løsn disse knuder → kernen falder fra hinanden i mange små domæner.")
