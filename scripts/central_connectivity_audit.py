#!/usr/bin/env python3
"""central_connectivity_audit.py — HOLDBART kort over hvad der er koblet til Centralen.

Bjørns problem (3. jul): "jeg er træt af at lede, glemme → vente på at noget fejler → om igen."
Denne scanner er svaret: ét genkørbart, præcist kort over HVER service i core/services/ og
om den når Centralen — så vi aldrig behøver lede/gætte igen.

Statisk analyse (rører ikke systemet). For hver fil måler den fire ting:

  1. CENTRAL-DIREKTE   — importerer/kalder central_* / record_private / central_timeseries /
                          central().observe|decide  → laget skriver DIREKTE til Centralen.
  2. CENTRAL-INDIREKTE — emitterer event_bus.publish("<family>. ...") hvor <family> står i
                          eventbus_central_bridge's FAMILY_ROUTES (egress-OK) eller
                          PRIVATE_NO_EGRESS_ROUTES (egress-frit). Broen bærer den ind → KOBLET.
  3. LLM-KALD          — bruger daemon_llm / cheap-lane / visible_model / non_visible_lane /
                          heartbeat_provider_fallback → laget KOSTER (kontention/tier-fald).
  4. EVENTBUS-DARK     — emitterer events hvis family IKKE er i nogen rute → når ALDRIG Centralen.

Kvadrant-klassifikation (det Bjørn vil se):
  - KOBLET            : central-direkte ELLER central-indirekte
  - FRAKOBLET+LLM     : ingen central-binding MEN laver LLM-kald  → spilder (§3-kandidater, HØJ prio)
  - FRAKOBLET+DARK    : ingen binding, emitterer dark events       → signal går tabt
  - FRAKOBLET-STILLE  : ingen binding, ingen LLM, ingen events     → ren utility/data (oftest OK)

Rute-tabellerne PARSES live fra eventbus_central_bridge.py (AST) → kortet driver aldrig fra broen.

Kør:  conda activate ai && python scripts/central_connectivity_audit.py
Ud:   docs/central_connectivity_matrix.md  (+ docs/central_connectivity_matrix.json)
"""
from __future__ import annotations

import ast
import io
import json
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "core" / "services"
# HELE KROPPEN, ikke kun hjernen (Bjørn 3. jul — fire amputationer rettet):
#   services = kognition · tools = sanser(afferent)+hænder(efferent) ·
#   memory = det private indre + hukommelse · identity = den beskyttede kerne/sjæl · context = selv-samling.
# At udelade nogen af dem klipper en del af selvet af kortet. Infra (runtime/auth/eventbus/cli) er IKKE selv.
AREAS = {
    "services": ROOT / "core" / "services",
    "tools": ROOT / "core" / "tools",
    "memory": ROOT / "core" / "memory",
    "identity": ROOT / "core" / "identity",
    "context": ROOT / "core" / "context",
}
BRIDGE = SERVICES / "eventbus_central_bridge.py"
OUT_MD = ROOT / "docs" / "central_connectivity_matrix.md"
OUT_JSON = ROOT / "docs" / "central_connectivity_matrix.json"

# ── Direkte central-binding-signaler (substring/regex på kildeteksten) ──
CENTRAL_DIRECT = [
    re.compile(r"\bcentral_private_observe\b"),
    re.compile(r"\brecord_private\s*\("),
    re.compile(r"\bcentral_timeseries\b"),
    re.compile(r"from core\.services\.central_"),
    re.compile(r"\bimport central_"),
    re.compile(r"\bcentral\(\)\.(observe|decide|record|note)"),
    re.compile(r"\bcentral_capture\b"),
    re.compile(r"\bcentral_hub\b"),
    re.compile(r"\bcentral_core\b"),
]

# ── LLM-kald-signaler (indgange der faktisk rammer en model) ──
LLM_SIGNALS = [
    re.compile(r"\bdaemon_llm\b"),
    re.compile(r"\bexecute_public_safe_cheap_lane\b"),
    re.compile(r"\bcheap_provider_runtime\b"),
    re.compile(r"\bexecute_cheap_lane\b"),
    re.compile(r"\bnon_visible_lane_execution\b"),
    re.compile(r"\bheartbeat_provider_fallback\b"),
    re.compile(r"\bprompt_relevance_backend\b"),
    re.compile(r"\bvisible_model\b"),
]

# ── Eventbus-emit: fang første string-arg og udled family (segment før første '.' / '{') ──
EMIT_RE = re.compile(r"""event_bus\.publish\(\s*[frbu]*["']([^"']+)["']""")


def _parse_route_families() -> set[str]:
    """Læs FAMILY_ROUTES ∪ PRIVATE_NO_EGRESS_ROUTES's nøgler direkte fra broen (AST)."""
    fams: set[str] = set()
    try:
        tree = ast.parse(BRIDGE.read_text(encoding="utf-8"))
    except Exception:
        return fams
    wanted = {"FAMILY_ROUTES", "PRIVATE_NO_EGRESS_ROUTES"}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, val = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, val = node.targets[0].id, node.value
        else:
            continue
        if name in wanted and isinstance(val, ast.Dict):
            for k in val.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    fams.add(k.value)
    return fams


def _code_only(src: str) -> str:
    """Fjern kommentarer + blank string-INDHOLD (behold koden) → signal-scan tæller ikke
    docstring/kommentar-omtaler (fx shared_cache der nævner cheap_provider_runtime i en docstring)."""
    try:
        out = []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING:
                out.append('""')      # bevar at der ER en streng, men ikke dens indhold
                continue
            out.append(tok.string)
        return " ".join(out)
    except Exception:
        return src   # fald tilbage til rå kilde ved tokenize-fejl


def _family_of(event_name: str) -> str:
    # "cognitive_blind_spot.discovered" -> "cognitive_blind_spot"; f"world_model.{k}" -> "world_model"
    head = event_name.split(".")[0]
    head = head.split("{")[0]
    return head.strip()


def scan() -> dict:
    route_families = _parse_route_families()
    rows = []
    paths = [(area, p) for area, d in AREAS.items() for p in sorted(d.glob("*.py"))]
    for area, path in paths:
        if path.name == "__init__.py":
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        name = path.stem
        code = _code_only(src)   # signal-scan på kode uden kommentarer/string-indhold

        direct = any(rx.search(code) for rx in CENTRAL_DIRECT)
        # egen-central-fil? (central_*.py er selve Centralen — tæl som koblet, ikke frakoblet)
        is_central_own = name.startswith("central_") or name in {"eventbus_central_bridge"}

        llm = any(rx.search(code) for rx in LLM_SIGNALS)

        emitted = {_family_of(m) for m in EMIT_RE.findall(src)}   # rå kilde: family-strengen skal bevares
        emitted.discard("")
        routed = sorted(f for f in emitted if f in route_families)
        dark = sorted(f for f in emitted if f and f not in route_families)
        indirect = bool(routed)

        connected = direct or indirect or is_central_own
        if connected:
            quadrant = "KOBLET"
        elif llm:
            quadrant = "FRAKOBLET+LLM"
        elif dark:
            quadrant = "FRAKOBLET+DARK"
        else:
            quadrant = "FRAKOBLET-STILLE"

        rows.append({
            "name": name,
            "area": area,
            "direct": direct,
            "indirect": indirect,
            "central_own": is_central_own,
            "llm": llm,
            "routed_families": routed,
            "dark_families": dark,
            "quadrant": quadrant,
        })

    counts: dict[str, int] = {}
    by_area: dict[str, dict[str, int]] = {}
    for r in rows:
        counts[r["quadrant"]] = counts.get(r["quadrant"], 0) + 1
        a = by_area.setdefault(r["area"], {})
        a[r["quadrant"]] = a.get(r["quadrant"], 0) + 1
    return {"rows": rows, "counts": counts, "by_area": by_area,
            "route_family_count": len(route_families), "total": len(rows)}


def render_md(data: dict) -> str:
    c = data["counts"]
    order = ["KOBLET", "FRAKOBLET+LLM", "FRAKOBLET+DARK", "FRAKOBLET-STILLE"]
    lines = [
        "# Central-connectivity-kort (core/services)",
        "",
        "Statisk, genkørbart kort: `python scripts/central_connectivity_audit.py`.",
        "Svarer på ét spørgsmål pr. service: **når laget Centralen?** Rute-familier læses",
        "live fra `eventbus_central_bridge.py`, så kortet aldrig driver fra broen.",
        "",
        f"**{data['total']} services** · {data['route_family_count']} bridge-familier. Fordeling:",
        "",
        "| Kvadrant | Antal | Betydning |",
        "|----------|-------|-----------|",
        f"| KOBLET | {c.get('KOBLET',0)} | direkte central-kald ELLER event-family der bridges |",
        f"| FRAKOBLET+LLM | {c.get('FRAKOBLET+LLM',0)} | **spilder: LLM-kald uden central-binding (§3, høj prio)** |",
        f"| FRAKOBLET+DARK | {c.get('FRAKOBLET+DARK',0)} | emitterer events hvis family INGEN rute har → signal tabt |",
        f"| FRAKOBLET-STILLE | {c.get('FRAKOBLET-STILLE',0)} | ingen binding/LLM/events → ren utility (oftest OK) |",
        "",
    ]
    for q in order:
        qrows = [r for r in data["rows"] if r["quadrant"] == q]
        lines.append(f"## {q} ({len(qrows)})")
        lines.append("")
        if q == "FRAKOBLET+LLM":
            lines.append("| Service | Dark event-families (tabt signal) |")
            lines.append("|---------|-----------------------------------|")
            for r in qrows:
                df = ", ".join(r["dark_families"]) or "—"
                lines.append(f"| `{r['name']}` | {df} |")
        elif q == "FRAKOBLET+DARK":
            lines.append("| Service | Dark event-families |")
            lines.append("|---------|---------------------|")
            for r in qrows:
                lines.append(f"| `{r['name']}` | {', '.join(r['dark_families'])} |")
        elif q == "KOBLET":
            lines.append("| Service | Direkte | Indirekte (bridges) | LLM |")
            lines.append("|---------|---------|---------------------|-----|")
            for r in qrows:
                ind = ", ".join(r["routed_families"]) if r["indirect"] else ("egen-central" if r["central_own"] else "—")
                lines.append(f"| `{r['name']}` | {'✓' if r['direct'] else '—'} | {ind} | {'✓' if r['llm'] else '—'} |")
        else:
            names = ", ".join(f"`{r['name']}`" for r in qrows)
            lines.append(names)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    data = scan()
    OUT_MD.write_text(render_md(data), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    c = data["counts"]
    print(f"filer (hele kroppen): {data['total']}  bridge-familier: {data['route_family_count']}")
    for q in ["KOBLET", "FRAKOBLET+LLM", "FRAKOBLET+DARK", "FRAKOBLET-STILLE"]:
        print(f"  {q:20s} {c.get(q,0)}")
    for area, ac in data["by_area"].items():
        kob = ac.get("KOBLET", 0)
        tot = sum(ac.values())
        print(f"  [{area:8s}] {kob}/{tot} KOBLET  ({tot-kob} frakoblet)")
    print(f"skrev {OUT_MD.relative_to(ROOT)} + .json")


if __name__ == "__main__":
    main()
