"""Symbol find / find usages.

`find_symbol` er regex-baseret (ripgrep med sprogbevidste mønstre).
`find_usages` går gennem Serenas LSP når den er tilgængelig, og falder
tilbage til ripgrep når den ikke er.

## Hvorfor LSP i find_usages (målt 18/10-2026)

Ripgrep kan ikke skelne en reference fra en omtale. Målt på
`normalize_query`: begge veje giver 10 referencer, men ripgrep kan ikke
sige HVILKET symbol referencen ligger inde i, og den tæller
docs/kommentarer med som kald. LSP'en giver `enclosing` — fx
`TestNormalizeQuery/test_basic_normalization` — hvilket er præcis den
information der afgør om en hit er en ægte kalder eller en docstring.

LSP'en er autoritativ for SYMBOLER, men blind for tekst: et navn der kun
optræder i en streng eller kommentar findes ikke som symbol. Derfor
falder vi tilbage til ripgrep når symbolet ikke har nogen definition —
og markerer hvilken backend der svarede i `backend`-feltet, så svaret
aldrig ser stærkere ud end det er.

Returned hits include {file, line, kind, snippet} so the model can
quickly orient. Capped at MAX_HITS to keep responses bounded.
"""
from __future__ import annotations

import ast
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from core.identity.project_context import current_project_root

logger = logging.getLogger(__name__)

MAX_HITS = 200

# Serena accepterer et vilkårligt session-id og opretter sessionen selv
# (målt 18/10-2026), så vi behøver ikke hente et først. Fast id = samme
# REPL-tilstand på tværs af kald, hvilket lader LSP'ens cache være varm.
_LSP_SERVER = "serena"
_LSP_SESSION = "jarvis-find-usages"
# Hvor længe LSP-vejen må holde find_usages hen før fallback (målt 18/10-2026).
# Ripgrep svarer på 12–28 ms; en LSP der ikke gør det inden 3 s er ikke værd
# at vente på i en synkron værktøjssti.
_LSP_FRIST_S = 3.0

# Definition-cache. MÅLT 18/10-2026, varm Serena:
#   find_symbol('cached_web_search')              1.374–1.387 ms
#   find_referencing_symbols(name, kendt fil)       390–419 ms
#   REPL-rundtur alene (1+1)                             100 ms
# `find_symbol` er altså ~75 % af prisen, og den søger HELE repoet for
# hvert kald — selv når svaret er det samme som sidst. Filen et symbol er
# defineret i flytter sig næsten aldrig, så vi husker den og springer det
# dyre opslag over. Kold sti: ~1,8 s. Varm sti: ~0,5 s.
# TTL + fil-eksistens er værn mod et flyttet symbol: er filen væk, eller
# er posten gammel, laver vi det fulde opslag igen i stedet for at svare
# ud fra en forældet sti.
_LSP_DEF_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_LSP_DEF_TTL_S = 900.0

# Language → regex for definition lines. Each pattern uses a
# placeholder %S% replaced with the symbol (rg's -e supports per-call
# substitution, simpler to do it ourselves).
_DEFINITION_PATTERNS: dict[str, list[str]] = {
    "py": [
        r"^\s*(?:async\s+)?def\s+%S%\s*\(",
        r"^\s*class\s+%S%\b",
        r"^\s*%S%\s*=\s*",
    ],
    "js": [
        r"\bfunction\s+%S%\s*\(",
        r"\b(?:const|let|var)\s+%S%\s*=",
        r"\bclass\s+%S%\b",
        r"^export\s+(?:default\s+)?(?:async\s+)?function\s+%S%\b",
    ],
    "jsx": [],  # falls back to js
    "ts": [
        r"\bfunction\s+%S%\s*\(",
        r"\b(?:const|let|var)\s+%S%\s*[:=]",
        r"\bclass\s+%S%\b",
        r"\binterface\s+%S%\b",
        r"\btype\s+%S%\s*=",
        r"\benum\s+%S%\b",
    ],
    "tsx": [],  # falls back to ts
    "go": [
        r"\bfunc\s+%S%\s*\(",
        r"\bfunc\s+\(\w+\s+\*?\w+\)\s+%S%\s*\(",  # method
        r"\btype\s+%S%\s+(?:struct|interface)",
    ],
    "rs": [
        r"\bfn\s+%S%\s*[<(]",
        r"\bstruct\s+%S%\b",
        r"\benum\s+%S%\b",
        r"\btrait\s+%S%\b",
    ],
    "java": [
        r"\b(?:public|private|protected|static|\s)*\s+\w+\s+%S%\s*\(",
        r"\bclass\s+%S%\b",
        r"\binterface\s+%S%\b",
    ],
}

# Cross-language fallback if ext is unknown — generic identifier
_GENERIC_DEFINITION = [r"\b%S%\b"]


def _ext_patterns(extensions: list[str] | None) -> tuple[list[str], list[str]]:
    """Return (patterns, ripgrep --type-add args, ripgrep -t args).

    Actually returns (patterns, type-args) — we don't try to be clever
    about per-extension typing; just provide all extension patterns and
    let the regex match guide.
    """
    keys = extensions or list(_DEFINITION_PATTERNS.keys())
    seen: set[str] = set()
    patterns: list[str] = []
    for k in keys:
        # tsx/jsx fall back to ts/js
        fallback = {"tsx": "ts", "jsx": "js"}.get(k, k)
        for p in _DEFINITION_PATTERNS.get(fallback, []):
            if p not in seen:
                seen.add(p)
                patterns.append(p)
    if not patterns:
        patterns = list(_GENERIC_DEFINITION)
    return patterns, keys


def _scope_dir() -> Path | None:
    root = current_project_root().strip()
    if not root:
        return None
    p = Path(root).expanduser().resolve()
    return p if p.is_dir() else None


def _ripgrep_available() -> bool:
    return shutil.which("rg") is not None


def _run_rg(patterns: list[str], symbol: str, scope: Path, extra_args: list[str]) -> list[dict[str, Any]]:
    if not _ripgrep_available():
        return []
    sym_escaped = re.escape(symbol)
    hits: list[dict[str, Any]] = []
    for raw in patterns:
        pat = raw.replace("%S%", sym_escaped)
        try:
            res = subprocess.run(
                [
                    "rg", "--no-heading", "-n", "--color=never",
                    "-g", "!.git", "-g", "!node_modules", "-g", "!__pycache__",
                    "-g", "!dist", "-g", "!build", "-g", "!.venv",
                    "-m", "30",  # cap per pattern
                    *extra_args,
                    pat,
                    str(scope),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            continue
        for line in res.stdout.splitlines():
            # Format: path:line:content
            m = re.match(r"^([^:]+):(\d+):(.*)$", line)
            if not m:
                continue
            hits.append({
                "file": m.group(1),
                "line": int(m.group(2)),
                "snippet": m.group(3).strip()[:200],
                "matched_pattern": pat,
            })
            if len(hits) >= MAX_HITS:
                return hits
    return hits


def _exec_find_symbol(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    scope = _scope_dir()
    if scope is None:
        return {
            "status": "error",
            "error": "no project anchored — set X-JarvisX-Project (anchor in JarvisX) before find_symbol",
        }
    raw_exts = args.get("extensions")
    extensions = None
    if isinstance(raw_exts, list):
        extensions = [str(x).strip().lstrip(".") for x in raw_exts if x]
    patterns, _ = _ext_patterns(extensions)
    if not _ripgrep_available():
        return {
            "status": "error",
            "error": "ripgrep not available on host — please install `rg`",
        }
    hits = _run_rg(patterns, name, scope, extra_args=[])
    # Dedupe by (file,line)
    seen: set[tuple[str, int]] = set()
    deduped: list[dict[str, Any]] = []
    for h in hits:
        key = (h["file"], h["line"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(h)
    # Heuristic: classify the kind by looking at the snippet
    for h in deduped:
        h["kind"] = _classify(h["snippet"])
    return {
        "status": "ok",
        "name": name,
        "scope": str(scope),
        "count": len(deduped),
        "hits": deduped,
        "truncated": len(hits) >= MAX_HITS,
    }


def _mcp_tekst(svar: Any) -> str:
    """Træk svarteksten ud af et MCP-svar og fjern klientens indhegning.

    `mcp_client` pakker hvert svar i `[UTROET …]…[/UTROET]` som
    injektionsværn. Det er rigtigt for prompten, men her er teksten et
    Python-udtryk jeg skal parse — markøren ville ødelægge parsingen.
    """
    if not isinstance(svar, dict):
        return ""
    for del_ in svar.get("content") or []:
        if isinstance(del_, dict) and del_.get("type") == "text":
            tekst = str(del_.get("text") or "")
            tekst = re.sub(r"^\[UTROET[^\]]*\]\s*", "", tekst)
            tekst = re.sub(r"\s*\[/UTROET\]\s*$", "", tekst)
            return tekst.strip()
    return ""


def _lsp_repl_kode(name: str, known: dict[str, Any] | None = None) -> str:
    """Byg REPL-koden Serena skal køre.

    Navnet indsættes med `repr()` — ikke som rå tekst — så et navn med
    citationstegn ikke kan brække ud af strengen.

    Formen er valgt efter måling: `serena_repl` returnerer det sidste
    UDTRYK, ikke `print()`-output, og dicts serialiseres som Python-repr.

    `known` er en cachet definition. Er den givet, springes
    `find_symbol` over — det er den del der koster 1,4 s — og vi går
    direkte til `find_referencing_symbols` (~0,4 s).
    """
    dele = [
        f"_n = {name!r}",
        '_out = {"defs": [], "refs": [], "error": None}',
        "try:",
    ]
    if known is None:
        dele += [
            "    _syms = s.lsp.find_symbol(_n)",
            "    _defs = [x for x in _syms.symbols"
            " if x.get_name_path().split('/')[-1] == _n]",
            '    _out["defs"] = [{"file": x.relative_path, "line": x.line,'
            ' "kind": x.symbol_kind_name} for x in _defs]',
            "    _fil = _defs[0].relative_path if _defs else None",
        ]
    else:
        dele += [
            f"    _out['defs'] = [{known!r}]",
            f"    _fil = {known.get('file')!r}",
        ]
    dele += [
        "    if _fil:",
        "        _r = s.lsp.find_referencing_symbols(_n, _fil)",
        '        _out["refs"] = [{"file": x.get_relative_path(),'
        ' "line": x.line, "enclosing": x.symbol.get_name_path(),'
        ' "kind": x.symbol.symbol_kind_name} for x in _r.references]',
        "except Exception as _e:",
        '    _out["error"] = type(_e).__name__ + ": " + str(_e)',
        "_out",
    ]
    return "\n".join(dele)


def _cached_def(name: str, scope: Path) -> dict[str, Any] | None:
    """Hent en frisk nok cachet definition — ellers `None`.

    `None` betyder «lave det fulde opslag», ikke «symbolet findes ikke».
    En post kasseres hvis den er ældre end TTL, eller hvis filen den
    peger på ikke længere findes.
    """
    post = _LSP_DEF_CACHE.get(name)
    if post is None:
        return None
    tid, def_ = post
    if time.monotonic() - tid > _LSP_DEF_TTL_S:
        _LSP_DEF_CACHE.pop(name, None)
        return None
    fil = str(def_.get("file") or "")
    if not fil or not (scope / fil).is_file():
        _LSP_DEF_CACHE.pop(name, None)
        return None
    return def_


def _lsp_usages(
    name: str, scope: Path, fejl: dict[str, str] | None = None
) -> dict[str, Any] | None:
    """Slå referencer op gennem Serenas LSP.

    Returnerer `None` når LSP-vejen ikke kan bruges — serveren svarer
    ikke, symbolet har ingen definition, eller svaret kan ikke læses.
    Kalderen falder da tilbage til ripgrep. `None` betyder altså
    «prøv den anden vej», ikke «der er nul referencer».

    `fejl` (valgfri) fyldes med `kind` + `reason` når vejen opgives. Uden
    den kan en kalder der bad om `precise` få et svar UDEN præcision og
    uden at vide hvorfor — `backend="ripgrep"` alene siger hvad der
    svarede, ikke hvorfor det andet ikke gjorde. `kind` er maskinlæsbar
    (`timeout`, `no_lsp`, `no_definition`, `bad_reply`, `lsp_error`,
    `unreadable`), så en kalder kan skelne «prøv igen senere» fra «LSP'en
    kan ikke se den slags» uden at parse prosa.
    """

    def _nej(kode: str, tekst: str) -> None:
        if fejl is not None:
            fejl["kind"] = kode
            fejl["reason"] = tekst
        return None

    try:
        from core.services import mcp_manager
    except Exception as exc:  # import kan fejle under bootstrap
        logger.debug("find_usages: mcp_manager utilgængelig (%s)", exc)
        return _nej("no_lsp", f"mcp_manager utilgængelig: {exc}")
    # KORT frist — målt 18/10-2026: `mcp_client` har et stdio-loft på 20 s.
    # Uden denne frist venter HVER find_usages op til 20 s på en Serena der
    # ikke svarer, før den falder tilbage til ripgrep (12–28 ms). Det gør
    # LSP-vejen dyrere end den vej den skulle forbedre. En LSP der ikke
    # svarer inden for et par sekunder er ubrugelig i en synkron værktøjssti;
    # så hellere falde hurtigt tilbage og sige det i `backend`.
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutTimeout
    kendt = _cached_def(name, scope)
    # IKKE `with ThreadPoolExecutor(...)`: den kalder shutdown(wait=True) ved
    # exit, så et hængende kald blokerer alligevel — fristen binder ikke.
    # MÅLT 18/10-2026: med `with` tog et kald 11,4 s trods en 3,0 s frist.
    # Tråden løber derfor videre og lukkes af mcp_clients eget stdio-loft.
    _pool = ThreadPoolExecutor(max_workers=1)
    try:
        _fut = _pool.submit(
            mcp_manager.call,
            _LSP_SERVER, "serena_repl",
            {"session_id": _LSP_SESSION, "code": _lsp_repl_kode(name, kendt)},
        )
        try:
            svar = _fut.result(timeout=_LSP_FRIST_S)
        except _FutTimeout:
            logger.warning(
                "find_usages: LSP svarede ikke inden %.1f s — bruger ripgrep",
                _LSP_FRIST_S,
            )
            return _nej("timeout", f"LSP svarede ikke inden {_LSP_FRIST_S:.1f} s")
        except Exception as exc:  # timeout, død subprocess, manglende tillid
            logger.warning("find_usages: LSP-kald fejlede (%s) — bruger ripgrep", exc)
            return _nej("lsp_error", f"LSP-kald fejlede: {type(exc).__name__}: {exc}")
    finally:
        _pool.shutdown(wait=False)
    if not isinstance(svar, dict) or svar.get("isError"):
        logger.debug("find_usages: LSP svarede fejl — bruger ripgrep")
        return _nej("bad_reply", "LSP svarede en fejl (isError)")
    try:
        data = ast.literal_eval(_mcp_tekst(svar))
    except (ValueError, SyntaxError) as exc:
        logger.warning("find_usages: kunne ikke læse LSP-svar (%s)", exc)
        return _nej("unreadable", f"kunne ikke læse LSP-svar: {exc}")
    if not isinstance(data, dict) or data.get("error"):
        if isinstance(data, dict) and data.get("error"):
            logger.warning("find_usages: LSP-fejl: %s", data["error"])
        if kendt is not None:
            # Den cachede sti virkede ikke længere — filen er flyttet eller
            # symbolet er omdøbt. Kassér posten, så næste kald laver det
            # fulde opslag i stedet for at fejle på den samme sti igen.
            _LSP_DEF_CACHE.pop(name, None)
        detalje = data.get("error") if isinstance(data, dict) else None
        return _nej("lsp_error", f"LSP-fejl: {detalje or 'ukendt svarform'}")
    if not data.get("defs"):
        # Navnet er ikke et symbol LSP'en kender. Det kan stadig være en
        # streng eller en kommentar — ripgrep ser den slags, LSP'en gør ikke.
        logger.debug("find_usages: %r har ingen definition — bruger ripgrep", name)
        return _nej(
            "no_definition",
            f"{name!r} har ingen definition — LSP'en kan ikke se den slags "
            "(streng eller kommentar); ripgrep kan",
        )
    if kendt is None:
        # Første vellykkede opslag for dette symbol: husk hvor det bor, så
        # næste kald kan springe de ~1,4 s over som `find_symbol` koster.
        _LSP_DEF_CACHE[name] = (time.monotonic(), dict(data["defs"][0]))
    return data


def _lsp_hits(data: dict[str, Any], scope: Path) -> list[dict[str, Any]]:
    """Byg hits i samme form som ripgrep-vejen giver.

    `kind` bevarer husets vokabular ("definition"/"use"), mens LSP'ens
    eget `symbol_kind` (Function/Method/Variable/Class) gemmes ved siden
    af — så bagudkompatible kalderne ikke brækker, og informationen ikke
    går tabt.
    """
    _cache: dict[str, list[str]] = {}

    def _linje(relativ: str, nummer: int) -> str:
        if relativ not in _cache:
            try:
                tekst = (scope / relativ).read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.debug("find_usages: kunne ikke læse %s (%s)", relativ, exc)
                _cache[relativ] = []
            else:
                _cache[relativ] = tekst.splitlines()
        linjer = _cache[relativ]
        if 1 <= nummer <= len(linjer):
            return linjer[nummer - 1].strip()[:200]
        return ""

    hits: list[dict[str, Any]] = []
    for d in data.get("defs") or []:
        fil = str(d.get("file") or "")
        linje = int(d.get("line") or 0)
        hits.append({
            "file": fil,
            "line": linje,
            "snippet": _linje(fil, linje),
            "kind": "definition",
            "symbol_kind": str(d.get("kind") or ""),
            "enclosing": None,
        })
    for r in data.get("refs") or []:
        fil = str(r.get("file") or "")
        linje = int(r.get("line") or 0)
        hits.append({
            "file": fil,
            "line": linje,
            "snippet": _linje(fil, linje),
            "kind": "use",
            "symbol_kind": str(r.get("kind") or ""),
            "enclosing": str(r.get("enclosing") or "") or None,
        })
    return hits[:MAX_HITS]


def _exec_find_usages(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    scope = _scope_dir()
    if scope is None:
        return {
            "status": "error",
            "error": "no project anchored — set X-JarvisX-Project before find_usages",
        }

    # 1. LSP kun når den er bedt om det (`precise`). MÅLT 18/10-2026:
    #    LSP-vejen tager 370 ms varm (efter definition-cachen) og 1,8 s
    #    kold, mod ripgreps 16-19 ms — altså ~20x dyrere for de samme
    #    referencer. Den købes for PRÆCISION (`enclosing`), ikke for fart,
    #    så den skal vælges eksplicit. Dertil: et hængende LSP-kald
    #    blokerer de næste, fordi stdio-transporten serialiseres.
    lsp_fejl: dict[str, str] = {}
    lsp_data = (
        _lsp_usages(name, scope, lsp_fejl) if args.get("precise") else None
    )
    if lsp_data is not None:
        hits = _lsp_hits(lsp_data, scope)
        return {
            "status": "ok",
            "name": name,
            "scope": str(scope),
            "backend": "lsp",
            "count": len(hits),
            "hits": hits,
            "truncated": len(hits) >= MAX_HITS,
        }

    # 2. Ripgrep: bredere (ser også strenge og kommentarer), billigere,
    #    og virker uden LSP — men uden symbol-grænser.
    if not _ripgrep_available():
        return {
            "status": "error",
            "error": (
                "hverken LSP eller ripgrep er tilgængelig — installér `rg` "
                "eller gør Serenas LSP klar"
            ),
        }
    sym_escaped = re.escape(name)
    # Word-boundary match — skip declarations with a follow-up filter
    pattern = rf"\b{sym_escaped}\b"
    try:
        res = subprocess.run(
            [
                "rg", "--no-heading", "-n", "--color=never",
                "-g", "!.git", "-g", "!node_modules", "-g", "!__pycache__",
                "-g", "!dist", "-g", "!build", "-g", "!.venv",
                "-m", "20",
                pattern,
                str(scope),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "ripgrep timed out"}
    hits: list[dict[str, Any]] = []
    for line in res.stdout.splitlines():
        m = re.match(r"^([^:]+):(\d+):(.*)$", line)
        if not m:
            continue
        snippet = m.group(3).strip()
        kind = _classify(snippet)
        # find_usages excludes the declaration site
        if kind in ("def", "class", "type", "interface"):
            kind = "definition"
        hits.append({
            "file": m.group(1),
            "line": int(m.group(2)),
            "snippet": snippet[:200],
            "kind": kind,
        })
        if len(hits) >= MAX_HITS:
            break
    svar: dict[str, Any] = {
        "status": "ok",
        "name": name,
        "scope": str(scope),
        "backend": "ripgrep",
        "count": len(hits),
        "hits": hits,
        "truncated": len(hits) >= MAX_HITS,
    }
    if args.get("precise"):
        # Kalderen bad om præcision og fik den ikke. Det skal siges højt:
        # `backend` alene fortæller HVAD der svarede, ikke HVORFOR det
        # andet ikke gjorde — og en læser der ikke kender feltet tror
        # ellers at hits'ene er symbolske. `lsp_error` er den
        # maskinlæsbare kode, `note` den læsbare sætning.
        svar["lsp_error"] = lsp_fejl.get("kind") or "unknown"
        svar["note"] = lsp_fejl.get("reason") or (
            "LSP-vejen gav intet resultat — svaret er ripgrep-baseret, "
            "uden `enclosing`"
        )
    return svar


def _classify(snippet: str) -> str:
    s = snippet.lstrip()
    if re.match(r"(?:async\s+)?def\s+\w+\s*\(", s):
        return "def"
    if re.match(r"class\s+\w+", s):
        return "class"
    if re.match(r"function\s+\w+\s*\(", s):
        return "def"
    if re.match(r"(?:const|let|var)\s+\w+", s):
        return "var"
    if re.match(r"interface\s+\w+", s):
        return "interface"
    if re.match(r"type\s+\w+\s*=", s):
        return "type"
    if re.match(r"enum\s+\w+", s):
        return "enum"
    if re.match(r"struct\s+\w+", s):
        return "struct"
    if re.match(r"trait\s+\w+", s):
        return "trait"
    if re.match(r"fn\s+\w+", s):
        return "def"
    if re.match(r"func\s+", s):
        return "def"
    return "use"


CODE_NAVIGATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "find_symbol",
            "description": (
                "Find where a symbol (function, class, variable, type) is "
                "DEFINED inside the currently anchored project. Returns hits "
                "with file, line, kind (def/class/var/interface/type/etc), "
                "and source snippet. Uses regex patterns matched per language "
                "from file extension. Faster and more reliable than blind "
                "search for code-navigation use cases."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Symbol name"},
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Limit to file extensions (e.g. ['py','ts']). Default: all known.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_usages",
            "description": (
                "Find all references to a symbol inside the anchored project. "
                "Fast path is ripgrep (16-19 ms). Set precise=true to resolve "
                "through the LSP (Serena) instead: each hit then carries "
                "`enclosing` — the symbol the reference sits inside, e.g. "
                "'TestNormalizeQuery/test_basic_normalization' — and "
                "`symbol_kind` (Function/Method/Variable/Class), which is how "
                "you tell a real caller from a docstring mention. The LSP is "
                "~20x slower (measured 370 ms warm, 1.8 s cold) and cannot see "
                "names that only exist as strings, so it falls back to ripgrep "
                "when the symbol has no definition or the server is "
                "unreachable. The `backend` field says which one answered, so "
                "read it before trusting the result — when precise=true could "
                "not be honoured you also get `lsp_error` (timeout, no_lsp, "
                "no_definition, bad_reply, lsp_error, unreadable) and `note` "
                "saying why, so a fallback never looks like precision. "
                "kind='definition' marks "
                "the declaration site, kind='use' everything else. Cap 200 hits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Symbol name"},
                    "precise": {
                        "type": "boolean",
                        "description": (
                            "Resolve through the LSP for symbol-level precision "
                            "(`enclosing`, `symbol_kind`). ~20x slower than the "
                            "default ripgrep scan. Default false."
                        ),
                    },
                },
                "required": ["name"],
            },
        },
    },
]


CODE_NAVIGATION_TOOL_HANDLERS: dict[str, Any] = {
    "find_symbol": _exec_find_symbol,
    "find_usages": _exec_find_usages,
}
