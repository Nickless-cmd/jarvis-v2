"""Permanent, governed Python-tool-fabrik (spor 5).

Jarvis kan oprette et nyt Python-vaerktoej ved koersel. Det overlever genstart
og baerer samme governance som de indbyggede.

## Persistens — UDEN FOR repoet

`<JARVIS_HOME>/state/custom_tools/` (overstyres af `JARVIS_CUSTOM_TOOLS_DIR`):

    registry.json       navn -> {description, parameters, sha256, effect, ...}
    <navn>.py           selve kroppen

Aldrig i kilden, aldrig i git. Filerne indeholder kun hvad Jarvis selv skrev;
fabrikken skriver ingen hemmeligheder.

## Krop-kontrakt

Kroppen definerer `def run(args): ...` og returnerer et dict (eller noget
JSON-serialiserbart). Kroppen EXEC'es ALDRIG ved oprettelse eller registrering
— kun `compile()`+AST-tjek. Foerste exec sker ved et kald, gennem handleren.

## Governance — fabrikken erklaerer sig ikke selv fri

* EFFEKT udledes af AST'en (`derive_effect`): filskrivning, skrive-kapable
  imports og ukendte konstruktioner giver `non_idempotent_write`; kun
  bevisligt ren beregning giver `read_only`. Der er INTET felt hvor kalderen
  kan angive effekten.
* GODKENDELSE udledes af effekten (`derive_approval`): skrive -> `ask`.
  Handleren returnerer `approval_needed` medmindre `er_ejer_godkendt()` —
  ContextVar'en `execute_tool_force(owner_approved=True)` saetter, aldrig
  tool-argumenter (modellen skriver selv dem). `_runtime_trust_all` bruges
  med vilje IKKE: autonome runs saetter det.
* `tool_definition_v2._udled_effekt/_udled_godkendelse` og
  `permission_classifier.is_mutating` spoerger fabrikken, saa et skrive-
  vaerktoej havner i samme klassifikation som `write_file`.
* Kaldet gaar gennem `execute_tool` som alle andre (rolle-gate, workspace-
  trust, observation). Intet spor uden om gaten.
* Alle fire styre-vaerktoejer er i `OWNER_ONLY_TOOLS`; custom-navne staar paa
  ingen member-liste og er derfor owner-only (fail-closed i permission_engine).
* Ved kald verificeres kildens sha256 mod registret (manipuleret fil afvises)
  og AST-tjekket koeres igen.
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
MAX_SOURCE_BYTES = 32_000
ENTRYPOINT = "run"

# Rene beregnings-imports: aendrer intet udenfor processen.
SAFE_IMPORTS = frozenset({
    "math", "json", "re", "datetime", "statistics", "itertools", "functools",
    "collections", "string", "decimal", "fractions", "textwrap", "hashlib",
    "base64", "uuid", "random", "typing", "operator", "unicodedata", "difflib",
})
# Tilladte, men skrive-kapable: giver skrive-effekt -> godkendelse.
WRITE_CAPABLE_IMPORTS = frozenset({
    "pathlib", "shutil", "tempfile", "sqlite3", "urllib", "urllib.request",
    "urllib.parse", "http", "http.client", "csv", "io", "glob", "fnmatch",
})
# Aldrig tilladt.
FORBIDDEN_IMPORTS = frozenset({
    "os", "sys", "subprocess", "socket", "ctypes", "importlib", "builtins",
    "pickle", "marshal", "shelve", "multiprocessing", "threading", "signal",
    "pty", "resource", "gc", "inspect", "code", "codeop", "runpy", "ssl",
    "asyncio", "concurrent", "posix", "nt", "winreg", "platform", "pkgutil",
    "zipimport", "imp", "types", "ast", "dis", "atexit", "tkinter",
})
FORBIDDEN_CALLS = frozenset({
    "eval", "exec", "compile", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "breakpoint", "input", "memoryview",
    "exit", "quit", "help", "dir", "type", "super",
})
FORBIDDEN_NAMES = frozenset({"__builtins__", "__loader__", "__spec__", "builtins"})
# Attributnavne der skriver/aendrer verden -> skrive-effekt.
# Kun entydige navne: `replace`/`copy`/`remove` er også str/list/dict-metoder.
# Alt skrive-kapabelt kræver alligevel et WRITE_CAPABLE-import (os er forbudt),
# og builtin `open` fanges af mode-tjekket — attributlisten er et ekstra net.
WRITE_ATTRS = frozenset({
    "write_text", "write_bytes", "unlink", "rmdir", "mkdir", "makedirs",
    "touch", "rename", "rmtree", "copy2", "copyfile", "copytree",
    "symlink_to", "chmod", "executescript", "urlopen", "mkstemp", "mkdtemp",
    "NamedTemporaryFile", "TemporaryDirectory",
})

READ_ONLY = "read_only"
NON_IDEMPOTENT_WRITE = "non_idempotent_write"

MANAGEMENT_TOOLS = (
    "create_custom_tool", "list_custom_tools",
    "delete_custom_tool", "show_custom_tool_source",
)

_lock = threading.RLock()
_loaded: dict[str, dict[str, Any]] = {}     # navn -> registerpost (kun metadata)


class ToolFactoryError(ValueError):
    """Afvisning med en brugbar aarsag — vises til kalderen."""


# ── persistens ───────────────────────────────────────────────────────────
def tools_dir() -> Path:
    override = os.environ.get("JARVIS_CUSTOM_TOOLS_DIR")
    if override:
        return Path(override)
    from core.runtime.config import STATE_DIR
    return Path(STATE_DIR) / "custom_tools"


def _registry_path() -> Path:
    return tools_dir() / "registry.json"


def _read_registry() -> dict[str, dict[str, Any]]:
    p = _registry_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("custom_tool_factory: register ulaeseligt: %s", p, exc_info=True)
        return {}
    tools = data.get("tools") if isinstance(data, dict) else None
    return dict(tools) if isinstance(tools, dict) else {}


def _write_registry(tools: dict[str, dict[str, Any]]) -> None:
    d = tools_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "registry.json.tmp"
    tmp.write_text(json.dumps({"version": 1, "tools": tools}, indent=2,
                              ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, _registry_path())


def _source_path(navn: str) -> Path:
    return tools_dir() / f"{navn}.py"


# ── validering ───────────────────────────────────────────────────────────
def builtin_names() -> set[str]:
    """Navne paa indbyggede vaerktoejer (alt der ikke er custom).

    Custom-navne fratraekkes fra REGISTRET, ikke fra ``_loaded``. ``_loaded``
    er kun hvad der er indlaest i denne proces; efter en genstart er den tom,
    og et custom-vaerktoej hvis navn ogsaa staar i simple_tools-listen ville
    ellers blive erklæret som kollision og forsvinde fra registret.
    """
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    navne = set(_TOOL_HANDLERS)
    navne |= {str(d.get("function", {}).get("name") or "") for d in TOOL_DEFINITIONS}
    navne |= set(MANAGEMENT_TOOLS)
    try:
        navne -= set(_read_registry())
    except Exception:  # registret kan vaere ulaesbart: svar konservativt uden fradrag
        navne -= set(_loaded)
    navne.discard("")
    return navne


def _mod_root(name: str) -> str:
    return name.split(".")[0]


def analyse_source(source: str) -> dict[str, Any]:
    """AST-tjek + effektudledning. Rejser ToolFactoryError. Exec'er ALDRIG."""
    if not isinstance(source, str) or not source.strip():
        raise ToolFactoryError("kroppen er tom")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ToolFactoryError(f"kroppen er over {MAX_SOURCE_BYTES} bytes")
    try:
        tree = ast.parse(source, filename="<custom_tool>")
        compile(tree, "<custom_tool>", "exec")      # foer den gemmes
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ToolFactoryError(f"kroppen kompilerer ikke: {exc}") from exc

    write_reasons: list[str] = []
    has_entry = False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == ENTRYPOINT:
            has_entry = True
            if len(node.args.args) != 1:
                raise ToolFactoryError(f"{ENTRYPOINT}(args) skal tage praecis ét argument")
    if not has_entry:
        raise ToolFactoryError(f"kroppen skal definere `def {ENTRYPOINT}(args):`")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    raise ToolFactoryError("relative imports er ikke tilladt")
                mods = [node.module or ""]
            else:
                mods = [a.name for a in node.names]
            for m in mods:
                root = _mod_root(m)
                if root in FORBIDDEN_IMPORTS or m in FORBIDDEN_IMPORTS:
                    raise ToolFactoryError(f"import af '{m}' er forbudt")
                if m in WRITE_CAPABLE_IMPORTS or root in WRITE_CAPABLE_IMPORTS:
                    write_reasons.append(f"import {m}")
                elif root not in SAFE_IMPORTS:
                    raise ToolFactoryError(f"import af '{m}' er ikke på tilladelseslisten")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise ToolFactoryError(f"adgang til dunder-attributten '{node.attr}' er forbudt")
            if node.attr in WRITE_ATTRS:
                write_reasons.append(f".{node.attr}")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                raise ToolFactoryError(f"navnet '{node.id}' er forbudt")
            if node.id in FORBIDDEN_CALLS and isinstance(node.ctx, ast.Load):
                raise ToolFactoryError(f"'{node.id}' er forbudt")
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "open":
                # Ethvert filkald gates: selv en ren læsning kan lække
                # vilkårlige filer (auth, nøgler), og modellen kan ikke
                # afgøre en sti statisk. Konservativt og bevidst.
                write_reasons.append("open()")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            raise ToolFactoryError("global/nonlocal er ikke tilladt")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            raise ToolFactoryError("async er ikke tilladt")

    effect = NON_IDEMPOTENT_WRITE if write_reasons else READ_ONLY
    return {
        "effect": effect,
        "approval": "ask" if effect == NON_IDEMPOTENT_WRITE else "none",
        "write_reasons": sorted(set(write_reasons)),
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }


def _validate_schema(parameters: Any) -> dict:
    if parameters in (None, ""):
        return {"type": "object", "properties": {}}
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except ValueError as exc:
            raise ToolFactoryError(f"parameters er ikke gyldig JSON: {exc}") from exc
    if not isinstance(parameters, dict) or parameters.get("type") != "object":
        raise ToolFactoryError("parameters skal være et JSON-schema med type=object")
    props = parameters.get("properties", {})
    if not isinstance(props, dict):
        raise ToolFactoryError("parameters.properties skal være et objekt")
    req = parameters.get("required", [])
    if not isinstance(req, list) or any(r not in props for r in req):
        raise ToolFactoryError("parameters.required skal pege på felter i properties")
    return parameters


# ── oprettelse / sletning / visning ──────────────────────────────────────
def create_tool(navn: str, description: str, parameters: Any, source: str) -> dict[str, Any]:
    navn = str(navn or "").strip()
    if not NAME_RE.match(navn):
        raise ToolFactoryError("navn skal matche ^[a-z][a-z0-9_]{2,47}$")
    if navn in builtin_names():
        raise ToolFactoryError(f"navnet '{navn}' kolliderer med et indbygget værktøj")
    description = str(description or "").strip()
    if not description:
        raise ToolFactoryError("beskrivelse er påkrævet")
    schema = _validate_schema(parameters)
    info = analyse_source(source)           # compile + AST, intet exec

    with _lock:
        reg = _read_registry()
        if navn in reg:
            raise ToolFactoryError(f"custom-værktøjet '{navn}' findes allerede — slet det først")
        tools_dir().mkdir(parents=True, exist_ok=True)
        _source_path(navn).write_text(source, encoding="utf-8")
        reg[navn] = {
            "description": description, "parameters": schema,
            "sha256": info["sha256"], "effect": info["effect"],
            "approval": info["approval"], "write_reasons": info["write_reasons"],
        }
        _write_registry(reg)
        _register_one(navn, reg[navn])
    return {"name": navn, "effect": info["effect"], "approval": info["approval"],
            "write_reasons": info["write_reasons"], "sha256": info["sha256"]}


def delete_tool(navn: str) -> dict[str, Any]:
    navn = str(navn or "").strip()
    with _lock:
        reg = _read_registry()
        if navn not in reg:
            raise ToolFactoryError(f"intet custom-værktøj '{navn}'")
        reg.pop(navn)
        _write_registry(reg)
        try:
            _source_path(navn).unlink()
        except FileNotFoundError:  # kilden var allerede vaek; registret er ryddet
            pass
        _unregister_one(navn)
    return {"name": navn, "deleted": True}


def list_tools() -> list[dict[str, Any]]:
    return [{"name": n, "description": m.get("description", ""),
             "effect": m.get("effect"), "approval": m.get("approval")}
            for n, m in sorted(_read_registry().items())]


def show_source(navn: str) -> dict[str, Any]:
    navn = str(navn or "").strip()
    reg = _read_registry()
    if navn not in reg:
        raise ToolFactoryError(f"intet custom-værktøj '{navn}'")
    return {"name": navn, "source": _source_path(navn).read_text(encoding="utf-8"),
            **{k: reg[navn].get(k) for k in ("effect", "approval", "sha256")}}


# ── afledt governance (læst af tool_definition_v2 / permission_classifier) ──
def is_custom(navn: str) -> bool:
    return navn in _loaded


def effect_for(navn: str) -> str | None:
    m = _loaded.get(navn)
    return m.get("effect") if m else None


def approval_for(navn: str) -> str | None:
    m = _loaded.get(navn)
    return m.get("approval") if m else None


# ── kald ─────────────────────────────────────────────────────────────────
def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = _mod_root(name)
    if level or root in FORBIDDEN_IMPORTS or not (
            root in SAFE_IMPORTS or name in WRITE_CAPABLE_IMPORTS
            or root in WRITE_CAPABLE_IMPORTS):
        raise ImportError(f"import af '{name}' er ikke tilladt")
    return __import__(name, globals, locals, fromlist, level)


def _restricted_builtins() -> dict[str, Any]:
    import builtins
    ok = {k: v for k, v in vars(builtins).items()
          if k not in FORBIDDEN_CALLS and not k.startswith("__")}
    ok["__import__"] = _safe_import
    ok["__build_class__"] = builtins.__build_class__
    ok["__name__"] = "custom_tool"
    return ok


def invoke(navn: str, args: dict[str, Any]) -> dict[str, Any]:
    """Foerste og eneste sted kroppen exec'es. Kaldes fra handleren."""
    meta = _loaded.get(navn)
    if meta is None:
        return {"status": "error", "error": f"Unknown tool: {navn}"}

    # GATEN: effekten er udledt, ikke erklæret. Skrive -> kraev ejer-godkendelse.
    if meta.get("approval") == "ask":
        from core.tools.owner_approval import er_ejer_godkendt
        if not er_ejer_godkendt():
            return {
                "status": "approval_needed", "tool_name": navn,
                "message": (f"Custom-værktøjet '{navn}' har skrive-effekt "
                            f"({', '.join(meta.get('write_reasons') or [])}) og kræver "
                            "ejerens godkendelse."),
                "command": f"{navn} {json.dumps({k: v for k, v in args.items() if not k.startswith('_')}, default=str)[:200]}",
            }

    try:
        source = _source_path(navn).read_text(encoding="utf-8")
    except OSError as exc:  # kilden er vaek eller ulaesbar: svar med aarsagen
        return {"status": "error", "error": f"kilden kunne ikke læses: {exc}"}
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != meta.get("sha256"):
        return {"status": "error", "error": "kildens hash matcher ikke registret — afvist"}
    try:
        info = analyse_source(source)
    except ToolFactoryError as exc:  # AST-tjekket afviste kilden: svar med aarsagen
        return {"status": "error", "error": f"kilden består ikke AST-tjekket: {exc}"}
    if info["effect"] != meta.get("effect"):
        return {"status": "error", "error": "udledt effekt afviger fra registret — afvist"}

    clean_args = {k: v for k, v in (args or {}).items() if not str(k).startswith("_")}
    glob: dict[str, Any] = {"__builtins__": _restricted_builtins(), "__name__": "custom_tool"}
    try:
        exec(compile(source, f"<custom_tool:{navn}>", "exec"), glob)  # noqa: S102
        result = glob[ENTRYPOINT](clean_args)
        json.dumps(result, default=str)
    except Exception as exc:  # brugerkoden fejlede: returnér fejlen, aldrig en halv vaerdi
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    if isinstance(result, dict):
        result.setdefault("status", "ok")
        return result
    return {"status": "ok", "result": result}


def _make_handler(navn: str):
    def _custom_tool_handler(args: dict[str, Any]) -> dict[str, Any]:
        return invoke(navn, args)
    _custom_tool_handler.__name__ = f"custom_tool_{navn}"
    return _custom_tool_handler


# ── registrering (ingen exec) ────────────────────────────────────────────
_REG_TARGETS: dict[str, Any] = {"handlers": None, "definitions": None}


def _definition(navn: str, meta: dict[str, Any]) -> dict[str, Any]:
    return {"type": "function", "function": {
        "name": navn,
        "description": f"[custom] {meta.get('description', '')}",
        "parameters": meta.get("parameters") or {"type": "object", "properties": {}},
    }}


def _register_one(navn: str, meta: dict[str, Any]) -> None:
    _loaded[navn] = dict(meta)
    h, defs = _REG_TARGETS["handlers"], _REG_TARGETS["definitions"]
    if h is not None:
        h[navn] = _make_handler(navn)
    if defs is not None:
        defs[:] = [d for d in defs if d.get("function", {}).get("name") != navn]
        defs.append(_definition(navn, meta))
    _bust_cache(navn)


def _unregister_one(navn: str) -> None:
    _loaded.pop(navn, None)
    h, defs = _REG_TARGETS["handlers"], _REG_TARGETS["definitions"]
    if h is not None:
        h.pop(navn, None)
    if defs is not None:
        defs[:] = [d for d in defs if d.get("function", {}).get("name") != navn]
    _bust_cache(navn)


def _bust_cache(navn: str) -> None:
    try:
        from core.tools import tool_definition_v2
        tool_definition_v2._cache.pop(navn, None)
    except Exception:  # cachen kan vaere utilgaengelig; naeste load laeser frisk
        pass


def load_registry(handlers: dict | None = None, definitions: list | None = None) -> list[str]:
    """Frisk indlaesning af registret. Registrerer handlere + definitioner.

    Exec'er IKKE nogen krop. Et element hvis fil mangler, har forkert hash
    eller ikke længere består AST-tjekket springes over (og logges).
    """
    with _lock:
        if handlers is not None:
            _REG_TARGETS["handlers"] = handlers
        if definitions is not None:
            _REG_TARGETS["definitions"] = definitions
        for gammel in list(_loaded):
            _unregister_one(gammel)
        navne: list[str] = []
        try:
            kollision = builtin_names()
        except Exception:
            kollision = set(MANAGEMENT_TOOLS)
        for navn, meta in sorted(_read_registry().items()):
            if navn in kollision:
                logger.warning("custom_tool_factory: '%s' kolliderer med indbygget — springer over", navn)
                continue
            try:
                source = _source_path(navn).read_text(encoding="utf-8")
                info = analyse_source(source)
            except (OSError, ToolFactoryError):
                logger.warning("custom_tool_factory: '%s' afvist ved indlæsning", navn, exc_info=True)
                continue
            if info["sha256"] != meta.get("sha256"):
                logger.warning("custom_tool_factory: '%s' hash-mismatch — springer over", navn)
                continue
            # Effekten GENUDLEDES; registerets påstand bruges ikke.
            meta = {**meta, "effect": info["effect"], "approval": info["approval"],
                    "write_reasons": info["write_reasons"]}
            _register_one(navn, meta)
            navne.append(navn)
        return navne


# ── styre-vaerktoejer (owner-only) ───────────────────────────────────────
def _wrap(fn):
    def _h(args: dict[str, Any]) -> dict[str, Any]:
        try:
            return {"status": "ok", **fn(args or {})}
        except ToolFactoryError as exc:  # forventet afvisning: bliv et svar, ikke en crash
            return {"status": "error", "error": str(exc)}
    return _h


def _exec_create(a):
    return create_tool(a.get("name"), a.get("description"), a.get("parameters"), a.get("source"))


def _exec_list(a):
    return {"tools": list_tools()}


def _exec_delete(a):
    return delete_tool(a.get("name"))


def _exec_show(a):
    return show_source(a.get("name"))


MANAGEMENT_HANDLERS = {
    "create_custom_tool": _wrap(_exec_create),
    "list_custom_tools": _wrap(_exec_list),
    "delete_custom_tool": _wrap(_exec_delete),
    "show_custom_tool_source": _wrap(_exec_show),
}


def _name_param(desc: str) -> dict:
    return {"type": "object", "properties": {"name": {"type": "string", "description": desc}},
            "required": ["name"]}


CUSTOM_TOOL_FACTORY_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "create_custom_tool",
        "description": (
            "Opret et permanent Python-værktøj (owner-only). Kroppen skal definere "
            "`def run(args):` og returnere et dict. Kroppen valideres (compile + "
            "AST, forbudte imports/kald afvises) og exec'es først ved kald. Effekt "
            "og godkendelse UDLEDES af koden: skrive-effekt kræver ejer-godkendelse."),
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "snake_case, 3-48 tegn; må ikke kollidere med et indbygget værktøj"},
            "description": {"type": "string"},
            "parameters": {"type": "object", "description": "JSON-schema (type=object) for argumenterne"},
            "source": {"type": "string", "description": "Python-kilde med def run(args): ..."},
        }, "required": ["name", "description", "source"]}}},
    {"type": "function", "function": {
        "name": "list_custom_tools",
        "description": "List egne permanente Python-værktøjer med udledt effekt/godkendelse (owner-only).",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "delete_custom_tool",
        "description": "Slet et eget permanent Python-værktøj (owner-only).",
        "parameters": _name_param("navnet på custom-værktøjet")}},
    {"type": "function", "function": {
        "name": "show_custom_tool_source",
        "description": "Vis kildekoden til et eget Python-værktøj (owner-only).",
        "parameters": _name_param("navnet på custom-værktøjet")}},
]


def install(handlers: dict, definitions: list) -> list[str]:
    """Kaldes ved opstart fra simple_tools: styre-vaerktoejer + registret."""
    have = {d.get("function", {}).get("name") for d in definitions}
    for d in CUSTOM_TOOL_FACTORY_DEFINITIONS:
        if d["function"]["name"] not in have:
            definitions.append(d)
    handlers.update(MANAGEMENT_HANDLERS)
    return load_registry(handlers, definitions)
