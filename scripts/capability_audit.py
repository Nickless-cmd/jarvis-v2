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
    rel = path.relative_to(repo_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = path.stem
    return ".".join(parts)


def find_python_files(root: Path) -> list[Path]:
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


def git_last_touch(path: Path) -> tuple[int | None, str]:
    rel = path.relative_to(REPO_ROOT)
    log_proc = subprocess.run(
        ["git", "log", "--follow", "--format=%at%x1f%h %s", "--", str(rel)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    entries: list[tuple[int, str]] = []
    for line in log_proc.stdout.splitlines():
        if "\x1f" not in line:
            continue
        timestamp_str, commit = line.split("\x1f", 1)
        if not timestamp_str.strip():
            continue
        entries.append((int(timestamp_str), commit.strip()))
    if not entries:
        return None, "n/a"

    timestamp, commit = entries[0]
    if (
        str(rel).startswith("core/services/")
        and SERVICES_MOVE_COMMIT_PREFIX in commit
        and len(entries) > 1
    ):
        timestamp, commit = entries[1]

    age_days = int((time.time() - timestamp) // 86400)
    return age_days, commit


def entry_modules() -> list[str]:
    modules = [module_name_from_path(REPO_ROOT / entry) for entry in ENTRY_FILES]
    for pattern in ENTRY_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            modules.append(module_name_from_path(path))
    return modules


def service_note(signals: ServiceSignals, score: str) -> str:
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

    signals_list: list[ServiceSignals] = []
    for path in service_paths:
        module_name = module_name_from_path(path)
        service_rel = str(path.relative_to(REPO_ROOT))
        source = path.read_text(encoding="utf-8")
        last_modified_days, last_modified_commit = git_last_touch(path)
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
    total = len(signals_list)
    scores = Counter(score_service(item) for item in signals_list)
    print("Capability Matrix Summary")
    print(f"Total services: {total}")
    for label in ("🟢 LIVE", "🟡 PARTIAL", "🟠 STALE", "🔴 SUSPICIOUS", "⚫ ORPHAN"):
        count = scores[label]
        share = (count / total * 100) if total else 0
        print(f"{label}: {count} ({share:.1f}%)")


def main() -> int:
    signals_list = analyze_services()
    report = render_markdown(signals_list)
    DOCS_OUTPUT.write_text(report, encoding="utf-8")
    print_summary(signals_list)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
