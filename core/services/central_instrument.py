"""central_instrument — selv-instrumenterende motor (system-cluster nerve, periodisk daemon).

Jarvis-forfattet spec (2026-06-23). Scanner HELE kodebasen (ikke kun commits) for silent-
failure-mønstre via AST — forstår kontrol-flow (er except:pass i en funktion uden ANDEN
fejl-håndtering?), ikke bare grep. Scorer hvert fund efter risiko+kontekst, observerer til
Centralen, og filer reviewbare proposals (score≥3) — ALDRIG auto-merged.

Sikkerheds-invarianter (hardcoded):
  • instrumenterer ALDRIG sig selv (_SELF_EXCLUDE)
  • auto-approver ALDRIG — kun proposals via approval-systemet
  • deterministisk — samme kodebase → samme fund (sorteret, hash-baserede signaturer)
  • incremental — kun ændrede filer re-scannes (indholds-hash-cache i db_instrument)
  • lærer — et fund afvist ≥_REJECT_DEMOTE× sænkes til note (ingen ny proposal)
"""
from __future__ import annotations

import ast
import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Rod = repo-roden (denne fil ligger i core/services/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN_DIRS = ("core", "apps/api")
_SELF_EXCLUDE = "core/services/central_instrument.py"
_EXCLUDE_PARTS = ("__pycache__", "/tests/", "/test_", "node_modules", ".venv", "migrations")

_REJECT_DEMOTE = 3            # fund afvist ≥3× → ingen ny proposal (kun note)
_PROPOSAL_THRESHOLD = 3       # score ≥3 → proposal; <3 → note

# Kald der TÆLLER som fejl-håndtering/synlighed (så en except IKKE er "silent").
_GUARD_SUBSTRINGS = (
    "observe", "decide", "safe_call", "record_", "note_", "capture",
    "logger", "log.", "logging", "warning", "error", "exception", "critical",
    "send_notification", "_record_error", "raise", "report", "emit",
)


# Intent-markører: en except/return mærket BEVIDST self-safe er en KENDT beslutning, ikke en
# ukendt silent failure. Denne kodebase bruger mønsteret massivt ("må aldrig vælte runtime").
# Spec'ens formål er at fange de UMÆRKEDE → mærkede dæmpes under proposal-tærsklen.
_ACK_MARKERS = (
    "self-safe", "selv-safe", "selv-sikker", "self safe", "best-effort", "best effort",
    "må aldrig", "maa aldrig", "aldrig vælte", "aldrig kaste", "noop", "no-op", "no op",
    "ignore", "ignorér", "ignorer", "silent", "bevidst", "med vilje", "defensiv", "fail-open",
    "fail open", "swallow", "bedst-effort", "graceful",
)


@dataclass(frozen=True)
class Finding:
    file: str            # relpath
    line: int
    kind: str            # bare_except|except_pass|except_silent|error_return_no_observe|long_unguarded|todo
    severity: str        # critical|high|medium|low
    snippet: str
    function: str
    success_like: bool = False   # except returnerer success-lignende værdi (scoring +2)
    acknowledged: bool = False   # mærket bevidst self-safe → kendt, ikke proposal-værdig

    @property
    def signature(self) -> str:
        norm = " ".join((self.snippet or "").split())
        h = hashlib.sha1(f"{self.kind}|{self.file}|{self.function}|{norm}".encode()).hexdigest()[:16]
        return f"{self.kind}:{h}"


# ── AST-hjælpere ──────────────────────────────────────────────────────────
def _call_name(node: ast.AST) -> str:
    """Bedste streng-navn for et Call's funktion (foo / obj.foo / a.b.foo)."""
    f = getattr(node, "func", node)
    parts: list[str] = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return ".".join(reversed(parts))


def _has_guard_call(node: ast.AST) -> bool:
    """True hvis subtræet indeholder et kald der tæller som fejl-håndtering/synlighed,
    ELLER en raise (re-raise = ikke silent)."""
    for n in ast.walk(node):
        if isinstance(n, ast.Raise):
            return True
        if isinstance(n, ast.Call):
            name = _call_name(n).lower()
            if any(g in name for g in _GUARD_SUBSTRINGS):
                return True
    return False


def _is_success_like_return(node: ast.AST) -> bool:
    """True hvis except-handleren returnerer en success-lignende værdi (None/{}/[]/True/0/
    dict) → caller kan ikke skelne fejl fra succes. dict med 'error'-nøgle tæller OSSE (stille
    fejl-retur uden trace)."""
    for n in ast.walk(node):
        if isinstance(n, ast.Return):
            v = n.value
            if v is None:
                return True
            if isinstance(v, ast.Constant) and v.value in (None, True, 0, "", False):
                return True
            if isinstance(v, (ast.Dict, ast.List, ast.Tuple)):
                return True
    return False


def _func_of(lineno: int, funcs: list[tuple[int, int, str]]) -> str:
    """Navn på den inderste funktion der omslutter lineno."""
    best = ""
    best_span = 10**9
    for start, end, name in funcs:
        if start <= lineno <= end and (end - start) < best_span:
            best, best_span = name, end - start
    return best


_TODO_RE = re.compile(r"#\s*(TODO|FIXME|HACK)\b", re.IGNORECASE)


def _acknowledged(lines: list[str], start: int, end: int) -> bool:
    """True hvis en intent-markør (self-safe/bevidst/...) findes i vinduet omkring [start,end].
    Vi kigger lidt FØR (kommentar over try) og hele handler-kroppen."""
    lo = max(0, start - 5)
    hi = min(len(lines), end + 1)
    blob = "\n".join(lines[lo:hi]).lower()
    return any(m in blob for m in _ACK_MARKERS)


def scan_source(relpath: str, source: str) -> list[Finding]:
    """AST-scan af ÉN fils kildekode → fund. Deterministisk (sorteret efter linje). Self-safe:
    syntaksfejl/parse-fejl → [] (vi instrumenterer ikke ukompilerbar kode)."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    lines = source.splitlines()

    funcs: list[tuple[int, int, str]] = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append((n.lineno, getattr(n, "end_lineno", n.lineno) or n.lineno, n.name))

    found: list[Finding] = []

    def _snip(lineno: int) -> str:
        return lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""

    # except-handlere
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler):
            fn = _func_of(n.lineno, funcs)
            body_is_pass = len(n.body) == 1 and isinstance(n.body[0], ast.Pass)
            guarded = _has_guard_call(ast.Module(body=n.body, type_ignores=[]))
            succ = _is_success_like_return(ast.Module(body=n.body, type_ignores=[]))
            h_end = getattr(n, "end_lineno", n.lineno) or n.lineno
            ack = _acknowledged(lines, n.lineno, h_end)
            if n.type is None:
                # bare except: — fanger KeyboardInterrupt/SystemExit. Altid kritisk (også mærket).
                found.append(Finding(relpath, n.lineno, "bare_except", "critical",
                                     _snip(n.lineno), fn, succ, acknowledged=False))
            elif body_is_pass:
                found.append(Finding(relpath, n.lineno, "except_pass", "high",
                                     _snip(n.lineno), fn, succ, acknowledged=ack))
            elif not guarded:
                # try/except UDEN observe/log/raise → Centralen ser det aldrig.
                found.append(Finding(relpath, n.lineno, "except_silent", "high",
                                     _snip(n.lineno), fn, succ, acknowledged=ack))

    # error-return uden synlighed + lange uafskærmede funktioner
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(n, "end_lineno", n.lineno) or n.lineno
            length = end - n.lineno
            guarded = _has_guard_call(n)
            # return {"error": ...} uden nogen synlighed i funktionen
            for r in ast.walk(n):
                if isinstance(r, ast.Return) and isinstance(r.value, ast.Dict):
                    keys = [k.value for k in r.value.keys if isinstance(k, ast.Constant)]
                    if "error" in keys and not guarded:
                        found.append(Finding(relpath, r.lineno, "error_return_no_observe",
                                             "high", _snip(r.lineno), n.name))
                        break
            if length > 50 and not guarded:
                found.append(Finding(relpath, n.lineno, "long_unguarded", "medium",
                                     f"def {n.name} ({length} linjer)", n.name))

    # kommentarer (AST ser dem ikke) — TODO/FIXME/HACK
    for i, ln in enumerate(lines, start=1):
        if _TODO_RE.search(ln):
            found.append(Finding(relpath, i, "todo", "low", ln.strip()[:120],
                                 _func_of(i, funcs)))

    found.sort(key=lambda f: (f.line, f.kind))
    return found


# ── scoring (Fase 2) ──────────────────────────────────────────────────────
_SEVERITY_BASE = {"critical": 3, "high": 2, "medium": 1, "low": 0}


def score_finding(f: Finding, *, file_has_central: bool, in_security: bool,
                  hot_path: bool = False, reject_count: int = 0) -> int:
    """Fase 2-score. Base = severity (critical=3→altid proposal). Modifiers fra spec'en:
    security +2 · hot path +1 · success-lignende retur +2 · filen har allerede Central-imports −1.
    Et fund afvist ≥_REJECT_DEMOTE× trækkes ned (lærings-dæmpning)."""
    s = _SEVERITY_BASE.get(f.severity, 0)
    if in_security:
        s += 2
    if hot_path:
        s += 1
    if f.success_like:
        s += 2
    if file_has_central:
        s -= 1
    if reject_count >= _REJECT_DEMOTE:
        s -= 3
    # Bevidst-mærket self-safe = KENDT beslutning → hold under proposal-tærsklen (kun note).
    # bare_except undtages: at fange KeyboardInterrupt/SystemExit er aldrig forsvarligt.
    if getattr(f, "acknowledged", False) and f.kind != "bare_except":
        s = min(s, _PROPOSAL_THRESHOLD - 1)
    return s


# ── kontekst-signaler ─────────────────────────────────────────────────────
def _file_has_central(source: str) -> bool:
    return ("central_core" in source or "central()" in source
            or "from core.services.central" in source or "safe_call" in source)


def _security_files() -> set[str]:
    """Filer der hører til en sikkerheds-cluster (via central_catalog nerve-lokationer)."""
    out: set[str] = set()
    try:
        from core.services import central_catalog as cc
        for c in cc.clusters():
            if not cc.is_security_cluster(c):
                continue
            for spec in cc.by_cluster(c):
                loc = str(getattr(spec, "location", "") or "")
                # location = "core/.../fil.py:func ..." → træk fil-stien ud
                m = re.match(r"([\w/\.]+\.py)", loc)
                if m:
                    out.add(m.group(1))
    except Exception:
        pass
    return out


def _reject_count(canonical_key: str) -> int:
    """Hvor mange gange er en proposal med denne canonical_key blevet afvist? (lærings-signal)."""
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM autonomy_proposals WHERE canonical_key = ? AND status = 'rejected'",
                (str(canonical_key or ""),),
            ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


# ── scan-orkestrering ─────────────────────────────────────────────────────
def _iter_py_files() -> list[str]:
    out: list[str] = []
    for d in _SCAN_DIRS:
        base = _REPO_ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            rel = p.relative_to(_REPO_ROOT).as_posix()
            if rel == _SELF_EXCLUDE or any(part in rel for part in _EXCLUDE_PARTS):
                continue
            out.append(rel)
    return sorted(out)


def scan_repo(*, changed_only: bool = True) -> dict[str, int]:
    """Scan kodebasen (incremental). Persisterer fund pr. fil + opdaterer scoring. Returnerer
    optælling. Self-safe — en enkelt fils fejl stopper ikke resten."""
    from core.runtime import db_instrument as dbi

    sec_files = _security_files()
    scanned = 0
    changed = 0
    total_findings = 0
    for rel in _iter_py_files():
        try:
            source = (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        scanned += 1
        h = hashlib.sha1(source.encode("utf-8", errors="replace")).hexdigest()
        if changed_only and dbi.get_file_hash(rel) == h:
            continue  # uændret → spring over (incremental)
        changed += 1
        findings = scan_source(rel, source)
        has_central = _file_has_central(source)
        in_sec = rel in sec_files
        rows = []
        for f in findings:
            sc = score_finding(f, file_has_central=has_central, in_security=in_sec,
                               reject_count=_reject_count(f.signature))
            rows.append({"signature": f.signature, "line": f.line, "kind": f.kind,
                         "severity": f.severity, "score": sc, "function": f.function,
                         "snippet": f.snippet})
            total_findings += 1
        dbi.replace_file_findings(rel, rows)
        dbi.set_file_hash(rel, h, len(rows))
    return {"scanned": scanned, "changed": changed, "findings": total_findings}


def _file_proposals(max_new: int = 10) -> int:
    """Filer reviewbare proposals for åbne fund med score≥threshold (ikke allerede filed,
    ikke lærings-dæmpet). ALDRIG auto-merged. Returnerer antal nye proposals."""
    from core.runtime import db_instrument as dbi
    filed = 0
    try:
        from core.services.autonomy_proposal_queue import file_proposal, list_pending_proposals
        pending_keys = {str(p.get("canonical_key") or "")
                        for p in (list_pending_proposals(limit=200) or [])}
    except Exception:
        return 0
    for f in dbi.list_findings(status="open", min_score=_PROPOSAL_THRESHOLD, limit=max_new * 3):
        sig = str(f.get("signature") or "")
        if sig in pending_keys:
            continue
        if _reject_count(sig) >= _REJECT_DEMOTE:
            continue  # lært: afvist gentagne gange → ingen ny proposal
        title = f"Silent-failure: {f.get('kind')} i {f.get('file')}:{f.get('line')}"
        rationale = (
            f"Mønster '{f.get('kind')}' (severity {f.get('severity')}, score {f.get('score')}) "
            f"i {f.get('function') or '<modul>'}: {f.get('snippet')}. Forslag: wrap i safe_call() "
            f"/ indsæt central().observe() efter fanget exception / indsæt central().decide() før "
            f"return. ALDRIG auto-anvendt — kræver din godkendelse."
        )
        try:
            file_proposal(kind="instrument_fix", title=title, rationale=rationale,
                          payload={"finding": f}, created_by="central_instrument",
                          canonical_key=sig)
            filed += 1
        except Exception:
            pass
        if filed >= max_new:
            break
    return filed


def run_instrument_scan(*, trigger: str = "cadence", changed_only: bool = True) -> dict[str, object]:
    """Daemon-entry: scan → score → persistér → observe → filer proposals (score≥3). Self-safe."""
    from core.runtime import db_instrument as dbi
    counts = scan_repo(changed_only=changed_only)
    summary = dbi.summary()
    new_proposals = _file_proposals()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "central_instrument",
            "scanned": counts.get("scanned"), "changed": counts.get("changed"),
            "open_findings": summary.get("total"), "critical": summary.get("critical"),
            "high": summary.get("high"), "proposals_open": summary.get("proposals"),
            "new_proposals": new_proposals, "trigger": trigger,
        })
    except Exception:
        pass
    return {"status": "ok", **counts, "summary": summary, "new_proposals": new_proposals}
