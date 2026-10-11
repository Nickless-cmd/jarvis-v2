from __future__ import annotations

import ast
import statistics
import subprocess
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIR = REPO_ROOT / "core" / "services"
DOCS_OUTPUT = REPO_ROOT / "docs" / "capability_matrix.md"
SCAN_ROOTS = ("core", "apps", "scripts", "tests")
ENTRY_FILES = (
    "apps/api/jarvis_api/app.py",
    "scripts/jarvis.py",
    "core/services/heartbeat_runtime.py",
)
ENTRY_GLOBS = (
    "apps/api/jarvis_api/routes/*.py",
    "scripts/pipelines/jarvis_*_pipeline.py",
)
SERVICES_MOVE_COMMIT_PREFIX = "refactor(services): flyt services/ fra apps/api/ til core/"
EMIT_PATTERNS = (
    "emit_event(",
    "event_bus.emit(",
    "EventBus.emit(",
    "event_bus.publish(",
)
SUBSCRIBE_PATTERNS = (
    "@event_bus.subscribe(",
    ".on_event(",
)
DAEMON_PATTERNS = (
    "register_daemon(",
    "@daemon",
)


@dataclass(frozen=True)
class ServiceSignals:
    service: str
    size_lines: int
    last_modified_days: int | None
    last_modified_commit: str
    reachable_from_entry: bool
    reachable_via: list[str]
    test_references: int
    test_files: list[str]
    emits_events: bool
    subscribes_events: bool
    has_daemon_hook: bool
    imports_count: int
    imported_by_count: int


def module_name_from_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    """Return the dotted module name for a file path relative to repo_root.

    Strips a trailing ``__init__.py`` and drops the ``.py`` suffix.
    """
    rel = path.relative_to(repo_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = path.stem
    return ".".join(parts)


def find_python_files(root: Path) -> list[Path]:
    """Return sorted .py files under the SCAN_ROOTS subdirs of root, skipping __pycache__."""
    files: list[Path] = []
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def resolve_relative_import(current_module: str | None, module: str | None, level: int) -> str | None:
    """Resolve a relative ``from ... import`` into an absolute dotted module name.

    ``level`` is the number of leading dots. For ``level == 0`` returns ``module``
    unchanged; otherwise walks up from ``current_module``'s package and appends
    ``module``. Returns None when nothing resolves.
    """
    if level == 0:
        return module
    if not current_module:
        return module
    package_parts = current_module.split(".")
    if package_parts and package_parts[-1] != "__init__":
        package_parts = package_parts[:-1]
    if level > len(package_parts):
        base_parts: list[str] = []
    else:
        base_parts = package_parts[: len(package_parts) - level + 1]
    if module:
        base_parts.extend(module.split("."))
    return ".".join(part for part in base_parts if part)


def normalize_candidates(candidates: Iterable[str], known_modules: set[str] | None) -> set[str]:
    """Reduce raw import candidates to modules that actually exist in the repo.

    When ``known_modules`` is None, returns all non-empty candidates. Otherwise
    keeps each candidate if known, else trims dotted suffixes until a known
    ancestor module is found (mapping e.g. ``pkg.mod.symbol`` to ``pkg.mod``).
    """
    if known_modules is None:
        return {candidate for candidate in candidates if candidate}

    normalized: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        if candidate in known_modules:
            normalized.add(candidate)
            continue
        probe = candidate
        while "." in probe:
            probe = probe.rsplit(".", 1)[0]
            if probe in known_modules:
                normalized.add(probe)
                break
    return normalized


def parse_imports(
    path: Path,
    *,
    current_module: str | None = None,
    known_modules: set[str] | None = None,
) -> set[str]:
    """Parse a file's AST and return the set of modules it imports.

    Covers ``import``/``from`` statements (resolving relative imports),
    ``importlib.import_module``/``__import__`` calls, and string literals
    referencing ``core.services.``, route, or pipeline module prefixes. The
    result is filtered through ``normalize_candidates`` against ``known_modules``.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_name = current_module or path.stem
    candidates: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidates.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = resolve_relative_import(module_name, node.module, node.level)
            if not resolved:
                continue
            if any(alias.name == "*" for alias in node.names):
                candidates.add(resolved)
                continue
            for alias in node.names:
                candidates.add(f"{resolved}.{alias.name}")
                candidates.add(resolved)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "import_module":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    candidates.add(node.args[0].value)
            elif isinstance(func, ast.Name) and func.id == "__import__":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    candidates.add(node.args[0].value)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for prefix in ("core.services.", "apps.api.jarvis_api.routes.", "scripts.pipelines."):
                start = node.value.find(prefix)
                if start >= 0:
                    literal = node.value[start:]
                    end = 0
                    while end < len(literal) and (literal[end].isalnum() or literal[end] in "._"):
                        end += 1
                    candidates.add(literal[:end])

    return normalize_candidates(candidates, known_modules)


def compute_reachability(
    graph: Mapping[str, set[str]],
    entry_modules: Iterable[str],
) -> tuple[set[str], dict[str, set[str]]]:
    """BFS the import graph from entry_modules.

    Returns the set of reachable modules and a mapping of each module to the
    parents through which it was reached.
    """
    reachable: set[str] = set()
    parents: dict[str, set[str]] = defaultdict(set)
    queue = deque(entry_modules)

    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        for dependency in graph.get(current, set()):
            parents[dependency].add(current)
            if dependency not in reachable:
                queue.append(dependency)

    return reachable, parents


def score_service(signals: Mapping[str, object] | ServiceSignals) -> str:
    """Classify a service into a colored liveness label from its signals.

    Returns one of LIVE, STALE, PARTIAL, SUSPICIOUS or ORPHAN based on
    reachability, recency, event/daemon/test signals and importer count.
    """
    data = asdict(signals) if isinstance(signals, ServiceSignals) else dict(signals)
    reachable = bool(data["reachable_from_entry"])
    last_modified_days = data["last_modified_days"]
    emits_events = bool(data["emits_events"])
    has_daemon_hook = bool(data["has_daemon_hook"])
    test_references = int(data["test_references"])
    imported_by_count = int(data["imported_by_count"])

    is_live = (
        reachable
        and (test_references >= 1 or emits_events or has_daemon_hook)
        and isinstance(last_modified_days, int)
        and last_modified_days < 60
    )
    if is_live:
        return "🟢 LIVE"
    if reachable and isinstance(last_modified_days, int) and last_modified_days > 180:
        return "🟠 STALE"
    if reachable:
        return "🟡 PARTIAL"
    if imported_by_count > 0:
        return "🔴 SUSPICIOUS"
    return "⚫ ORPHAN"


@dataclass(frozen=True)
class GitTouchIndex:
    """Repo-wide git history built from ONE ``git log`` call.

    ``touches`` maps a repo-relative path to its commits, newest first, as
    ``(unix timestamp, "shorthash subject")``. ``renamed_from`` maps a path to the
    path it was renamed from, so a rename chain can be walked backwards the way
    ``git log --follow`` used to do per file.
    """

    touches: Mapping[str, tuple[tuple[int, str], ...]]
    renamed_from: Mapping[str, str]


def build_git_touch_index(repo_root: Path = REPO_ROOT) -> GitTouchIndex:
    """Build the repo-wide touch index in a single ``git log --name-status -M`` pass.

    Replaces one ``git log --follow`` per file, which cost ~0.24 s each and ~4-5
    minutes for the ~1161 files under ``core/services/``. ``-M`` adds rename
    detection in the same pass, so a renamed file's history can be chained back to
    its pre-rename path without a second call. A failed git call yields an empty
    index, so every path then reports ``(None, "n/a")`` rather than raising.
    """
    log_proc = subprocess.run(
        ["git", "log", "--format=\x01%at\x1f%h %s", "--name-status", "-M"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    touches: dict[str, list[tuple[int, str]]] = defaultdict(list)
    renamed_from: dict[str, str] = {}
    current: tuple[int, str] | None = None

    for line in log_proc.stdout.splitlines():
        if line.startswith("\x01"):
            body = line[1:]
            if "\x1f" not in body:
                current = None
                continue
            timestamp_str, commit = body.split("\x1f", 1)
            try:
                current = (int(timestamp_str), commit.strip())
            except ValueError:
                current = None
            continue
        if current is None or not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            touches[parts[2]].append(current)
            renamed_from.setdefault(parts[2], parts[1])
        elif len(parts) == 2:
            touches[parts[1]].append(current)

    return GitTouchIndex(
        touches={path: tuple(entries) for path, entries in touches.items()},
        renamed_from=renamed_from,
    )


def git_last_touch(path: Path, index: GitTouchIndex) -> tuple[int | None, str]:
    """Return (age in days, short commit) of the most recent git change to path.

    Reads the shared ``index`` (see ``build_git_touch_index``) instead of running
    ``git log --follow`` per file. A renamed path is chained back to the path it
    came from, so pre-rename history is kept. Skips the bulk services-move commit
    in favor of the next real change when it is the latest touch on a
    ``core/services/`` file. Returns ``(None, "n/a")`` when there is no history.
    """
    rel = str(path.relative_to(REPO_ROOT))
    entries: list[tuple[int, str]] = list(index.touches.get(rel, ()))
    seen = {rel}
    chain = rel
    while chain in index.renamed_from:
        chain = index.renamed_from[chain]
        if chain in seen:
            break
        seen.add(chain)
        entries.extend(index.touches.get(chain, ()))

    if not entries:
        return None, "n/a"

    timestamp, commit = entries[0]
    if (
        rel.startswith("core/services/")
        and SERVICES_MOVE_COMMIT_PREFIX in commit
        and len(entries) > 1
    ):
        timestamp, commit = entries[1]

    age_days = int((time.time() - timestamp) // 86400)
    return age_days, commit


def entry_modules() -> list[str]:
    """Return the dotted module names of the reachability entry points (ENTRY_FILES + ENTRY_GLOBS)."""
    modules = [module_name_from_path(REPO_ROOT / entry) for entry in ENTRY_FILES]
    for pattern in ENTRY_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            modules.append(module_name_from_path(path))
    return modules


def service_note(signals: ServiceSignals, score: str) -> str:
    """Build a short human note explaining why a service scored low.

    Joins reasons (unreachable, no importers, cold file, no test imports) into
    a single string, falling back to ``"review manually"``.
    """
    parts: list[str] = []
    if score == "🔴 SUSPICIOUS":
        parts.append("not reachable from configured entry points")
    if score == "⚫ ORPHAN":
        parts.append("no reachable path and no importers")
    if signals.last_modified_days is not None and signals.last_modified_days > 180:
        parts.append("cold file")
    if not signals.test_references:
        parts.append("no direct test imports")
    return "; ".join(parts) or "review manually"


def render_markdown(signals_list: list[ServiceSignals]) -> str:
    """Render the full capability matrix report as a Markdown string.

    Produces the summary table, Boy Scout candidates (>1000 lines),
    consolidation/removal candidates, and the full per-service matrix.
    """
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    total = len(signals_list)
    scores = Counter(score_service(item) for item in signals_list)
    sizes = [item.size_lines for item in signals_list]
    median_lines = int(statistics.median(sizes)) if sizes else 0
    total_lines = sum(sizes)
    over_1000 = [item for item in signals_list if item.size_lines > 1000]

    lines: list[str] = [
        "# Capability Matrix",
        "",
        "Statisk audit af `core/services/` genereret af `scripts/capability_audit.py`.  ",
        f"Sidst kørt: {now}  ",
        f"Total services: {total}",
        "",
        "## Sammenfatning",
        "",
        "| Score | Antal | Andel |",
        "|---|---:|---:|",
    ]
    for label in ("🟢 LIVE", "🟡 PARTIAL", "🟠 STALE", "🔴 SUSPICIOUS", "⚫ ORPHAN"):
        count = scores[label]
        share = (count / total * 100) if total else 0
        lines.append(f"| {label} | {count} | {share:.1f}% |")

    lines.extend(
        [
            "",
            f"**Median filstørrelse:** {median_lines} linjer  ",
            f"**Totale linjer:** {total_lines}  ",
            f"**Services > 1000 linjer:** {len(over_1000)}",
            "",
            "## Boy Scout Candidates",
            "",
            "Services over 1000 linjer der trænger til at blive skåret ned (prioriteret efter størrelse):",
            "",
            "| Fil | Linjer | Score | Sidst rørt |",
            "|---|---:|---|---|",
        ]
    )
    for item in sorted(over_1000, key=lambda entry: (-entry.size_lines, entry.service)):
        touched = f"{item.last_modified_days}d" if item.last_modified_days is not None else "n/a"
        lines.append(f"| `{item.service}` | {item.size_lines} | {score_service(item)} | {touched} |")
    if not over_1000:
        lines.append("| _(ingen)_ | 0 | n/a | n/a |")

    lines.extend(
        [
            "",
            "## Kandidater til konsolidering eller fjernelse",
            "",
            "Services med score 🔴 SUSPICIOUS eller ⚫ ORPHAN — ejeren skal gennemgå dem manuelt:",
            "",
            "| Service | Score | Linjer | Sidst rørt | Imported by | Bemærk |",
            "|---|---|---:|---|---:|---|",
        ]
    )
    review_candidates = [
        item for item in signals_list if score_service(item) in {"🔴 SUSPICIOUS", "⚫ ORPHAN"}
    ]
    for item in review_candidates:
        touched = f"{item.last_modified_days}d" if item.last_modified_days is not None else "n/a"
        lines.append(
            f"| `{item.service}` | {score_service(item)} | {item.size_lines} | {touched} | "
            f"{item.imported_by_count} | {service_note(item, score_service(item))} |"
        )
    if not review_candidates:
        lines.append("| _(ingen)_ | n/a | 0 | n/a | 0 | n/a |")

    lines.extend(
        [
            "",
            "## Fuld matrix",
            "",
            "| Service | Score | Linjer | Sidst rørt | Reachable | Via | Tests | Testfiler | Imported by | Imports | Emits | Subscribes | Daemon |",
            "|---|---|---:|---|---|---|---:|---|---:|---:|---|---|---|",
        ]
    )
    for item in signals_list:
        touched = f"{item.last_modified_days}d" if item.last_modified_days is not None else "n/a"
        via = ", ".join(item.reachable_via[:3]) or "—"
        tests = ", ".join(item.test_files[:3]) or "—"
        lines.append(
            f"| `{item.service}` | {score_service(item)} | {item.size_lines} | {touched} | "
            f"{'yes' if item.reachable_from_entry else 'no'} | {via} | {item.test_references} | "
            f"{tests} | {item.imported_by_count} | {item.imports_count} | "
            f"{'yes' if item.emits_events else 'no'} | {'yes' if item.subscribes_events else 'no'} | "
            f"{'yes' if item.has_daemon_hook else 'no'} |"
        )

    return "\n".join(lines) + "\n"


def analyze_services() -> list[ServiceSignals]:
    """Scan the repo and build ServiceSignals for every module in core/services/.

    Builds the import graph and its reverse, computes reachability from the
    entry modules, and gathers per-service size, git recency, test importers
    and event/daemon flags. Returns the signals sorted by service path.
    """
    python_files = find_python_files(REPO_ROOT)
    module_map = {module_name_from_path(path): path for path in python_files}
    known_modules = set(module_map)

    graph: dict[str, set[str]] = {}
    reverse_graph: dict[str, set[str]] = defaultdict(set)
    for module_name, path in module_map.items():
        imports = parse_imports(path, current_module=module_name, known_modules=known_modules)
        graph[module_name] = imports
        for dependency in imports:
            reverse_graph[dependency].add(module_name)

    reachable, parents = compute_reachability(graph, entry_modules())
    service_paths = sorted(path for path in SERVICE_DIR.glob("*.py") if path.name != "__init__.py")
    test_modules = {name for name in module_map if name.startswith("tests.")}
    touch_index = build_git_touch_index(REPO_ROOT)

    signals_list: list[ServiceSignals] = []
    for path in service_paths:
        module_name = module_name_from_path(path)
        service_rel = str(path.relative_to(REPO_ROOT))
        source = path.read_text(encoding="utf-8")
        last_modified_days, last_modified_commit = git_last_touch(path, touch_index)
        direct_test_importers = sorted(
            reverse_graph.get(module_name, set()).intersection(test_modules)
        )
        emit_flag = any(pattern in source for pattern in EMIT_PATTERNS)
        subscribe_flag = any(pattern in source for pattern in SUBSCRIBE_PATTERNS)
        daemon_flag = any(pattern in source for pattern in DAEMON_PATTERNS)
        reachable_parents = sorted(parents.get(module_name, set()))
        imported_by = {
            importer
            for importer in reverse_graph.get(module_name, set())
            if importer != module_name
        }
        signals_list.append(
            ServiceSignals(
                service=service_rel,
                size_lines=len(source.splitlines()),
                last_modified_days=last_modified_days,
                last_modified_commit=last_modified_commit,
                reachable_from_entry=module_name in reachable,
                reachable_via=reachable_parents[:3],
                test_references=len(direct_test_importers),
                test_files=[module_map[name].name for name in direct_test_importers[:3]],
                emits_events=emit_flag,
                subscribes_events=subscribe_flag,
                has_daemon_hook=daemon_flag,
                imports_count=len(graph.get(module_name, set())),
                imported_by_count=len(imported_by),
            )
        )
    return sorted(signals_list, key=lambda item: item.service)


def print_summary(signals_list: list[ServiceSignals]) -> None:
    """Print the total service count and per-score counts/shares to stdout."""
    total = len(signals_list)
    scores = Counter(score_service(item) for item in signals_list)
    print("Capability Matrix Summary")
    print(f"Total services: {total}")
    for label in ("🟢 LIVE", "🟡 PARTIAL", "🟠 STALE", "🔴 SUSPICIOUS", "⚫ ORPHAN"):
        count = scores[label]
        share = (count / total * 100) if total else 0
        print(f"{label}: {count} ({share:.1f}%)")


def main() -> int:
    """Run the audit, write the report to DOCS_OUTPUT, print the summary; return 0."""
    signals_list = analyze_services()
    report = render_markdown(signals_list)
    DOCS_OUTPUT.write_text(report, encoding="utf-8")
    print_summary(signals_list)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
