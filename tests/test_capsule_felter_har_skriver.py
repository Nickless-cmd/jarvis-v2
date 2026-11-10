"""Strukturel vagt: hvert kapsel-felt i CONTINUITY-blokken skal have en skriver.

Maalt 10/11-2026 blev tre varianter af samme fejl fundet paa een dag:

* fatigue/frustration/confidence havde ingen skriver og blev arvet for evigt.
* current_focus havde en kilde, men «maalt tomt» blev sendt som en tom dict,
  saa et 51-tegns foraeldet fokus overlevede i ugevis.
* open_thread blev vist som aktuel tilstand, selv om kun schema-defaulten
  nogensinde skrev feltet.

En CONTINUITY-blok er en paastand om tilstanden nu. Derfor udleder denne test
felterne fra selve visningskoden og kraever en ikke-konstant skriver paa den
faktiske kapsel-skrivevej. Mutationstesten beviser, at vagten ogsaa kan afvise.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTINUITY = ROOT / "core" / "services" / "continuity.py"
SOURCE_ROOTS = (
    ROOT / "core" / "services",
    ROOT / "core" / "runtime",
)

CAPSULE_SECTIONS = {
    "wake_provenance",
    "handover",
    "mood",
    "attention",
    "relation",
    "somatic",
    "goals",
}

CAPSULE_SINKS = {
    "write_capsule",
    "capture_state",
    "live_update_after_turn",
}

# Hver post er dokumenteret gaeld, ikke en generel tilladelse.
UNDTAEDE_FELTER = {
    # Kun schema-defaulten findes. Feltet vises stadig, men har ingen maaling.
    ("attention", "open_thread"): "doedt felt; ingen producer uden for default",

    # Begge relation-felter er historiske schema-defaults. Ingen aktiv
    # capsule-producer skriver dem med en observeret vaerdi.
    ("relation", "relationship_phase"): "kun schema-default; ingen maaling",
    ("relation", "last_interaction_type"): "kun schema-default; ingen maaling",

    # Somatic-sektionen kan merges ind via API'et, men repositoryets aktive
    # capsule-skrivevej producerer ingen af disse tre konkrete noegler.
    ("somatic", "last_visual"): "ingen aktiv capsule-producer",
    ("somatic", "last_audio"): "ingen aktiv capsule-producer",
    ("somatic", "atmosphere"): "ingen aktiv capsule-producer",

    # Goals kan modtages som en generisk dict, men ingen aktiv skriver
    # konstruerer disse viste noegler. De boer fjernes eller faa en kilde.
    ("goals", "active_goals"): "ingen aktiv capsule-producer",
    ("goals", "recent_completions"): "ingen aktiv capsule-producer",
}


Field = tuple[str, str]
Evidence = tuple[str, int, str]


def _function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    raise AssertionError(f"funktionen {name!r} blev ikke fundet")


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _calls_any(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    names: set[str],
) -> bool:
    return any(
        isinstance(node, ast.Call) and _called_name(node) in names
        for node in ast.walk(function)
    )


def _literal_loop_values(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    for node in ast.walk(function):
        if not (
            isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and isinstance(node.iter, (ast.Tuple, ast.List))
        ):
            continue
        if all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in node.iter.elts
        ):
            values[node.target.id] = {
                item.value for item in node.iter.elts  # type: ignore[union-attr]
            }
    return values


def _capsule_aliases(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, str]:
    """Find fx ``mood = capsule.get("mood", {})``.

    BoolOp-formen bruges ogsaa:
    ``handover = capsule.get("handover") or {}``.
    """
    aliases: dict[str, str] = {}

    for node in ast.walk(function):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        sections: set[str] = set()

        for child in ast.walk(node.value):
            if not (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "get"
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "capsule"
                and child.args
                and isinstance(child.args[0], ast.Constant)
                and isinstance(child.args[0].value, str)
            ):
                continue
            if child.args[0].value in CAPSULE_SECTIONS:
                sections.add(child.args[0].value)

        if len(sections) != 1:
            continue

        section = next(iter(sections))
        for target in targets:
            if isinstance(target, ast.Name):
                aliases[target.id] = section

    return aliases


def _displayed_fields_from_source(source: str) -> dict[Field, set[int]]:
    """Returner kapsel-felter som flyder ind i ``lines.append(...)``."""
    tree = ast.parse(source)
    function = _function(tree, "build_wake_up_block")
    aliases = _capsule_aliases(function)
    loop_values = _literal_loop_values(function)
    dependencies: dict[str, set[tuple[str, str, int]]] = defaultdict(set)

    def expression_dependencies(node: ast.AST) -> set[tuple[str, str, int]]:
        found: set[tuple[str, str, int]] = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                found.update(dependencies[child.id])

            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "get"
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id in aliases
                and child.args
            ):
                key = child.args[0]
                section = aliases[child.func.value.id]
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    found.add((section, key.value, child.lineno))
                elif isinstance(key, ast.Name):
                    found.update(
                        (section, value, child.lineno)
                        for value in loop_values.get(key.id, set())
                    )

            if (
                isinstance(child, ast.Subscript)
                and isinstance(child.value, ast.Name)
                and child.value.id in aliases
                and isinstance(child.slice, ast.Constant)
                and isinstance(child.slice.value, str)
            ):
                found.add(
                    (
                        aliases[child.value.id],
                        child.slice.value,
                        child.lineno,
                    )
                )

        return found

    # Fixpunktet foelger lokale variable, +=, for-loop targets og opsamlinger
    # som mood_parts.append(...), indtil ingen ny afhaengighed findes.
    for _ in range(100):
        changed = False

        for node in ast.walk(function):
            assignments: list[tuple[ast.AST, ast.AST]] = []

            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                assignments.extend((target, node.value) for target in targets)
            elif isinstance(node, ast.AugAssign):
                assignments.append((node.target, node.value))
            elif isinstance(node, ast.For):
                assignments.append((node.target, node.iter))

            for target, value in assignments:
                if not isinstance(target, ast.Name):
                    continue
                before = len(dependencies[target.id])
                dependencies[target.id].update(expression_dependencies(value))
                changed |= len(dependencies[target.id]) != before

            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id != "lines"
                and node.args
            ):
                continue

            container = node.func.value.id
            before = len(dependencies[container])
            dependencies[container].update(expression_dependencies(node.args[0]))
            changed |= len(dependencies[container]) != before

        if not changed:
            break
    else:
        raise AssertionError("display-afhaengigheder naaede ikke et fixpunkt")

    displayed: dict[Field, set[int]] = defaultdict(set)
    for node in ast.walk(function):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "lines"
            and node.args
        ):
            continue

        for section, key, line in expression_dependencies(node.args[0]):
            displayed[(section, key)].add(line)

    return dict(displayed)


def _is_constant_expression(node: ast.AST) -> bool:
    """True for literals, including sammensatte literals som [] og {}."""
    try:
        ast.literal_eval(node)
    except (TypeError, ValueError):
        return False
    return True


def _writer_evidence_from_sources(
    sources: dict[str, str],
) -> dict[str, list[Evidence]]:
    """Find ikke-konstante noegleskrivere paa den faktiske capsule-skrivevej.

    Repo-global soegning efter fx ``confidence`` er utilstraekkelig: noeglen
    findes i mange uvedkommende payloads. En funktion taeller derfor kun, hvis
    den kalder en capsule-sink, eller er en lokal helper kaldt transitivt af
    en saadan funktion.
    """
    evidence: dict[str, list[Evidence]] = defaultdict(list)

    for filename, source in sorted(sources.items()):
        tree = ast.parse(source, filename=filename)
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        connected = {
            name
            for name, function in functions.items()
            if _calls_any(function, CAPSULE_SINKS)
        }

        # Lokale helpers som _attention_fra_aktive_goals bliver forbundet via
        # den funktion, der sender resultatet til live_update_after_turn.
        while True:
            newly_connected = {
                candidate
                for candidate in functions
                if candidate not in connected
                and any(
                    _calls_any(functions[caller], {candidate})
                    for caller in connected
                )
            }
            if not newly_connected:
                break
            connected.update(newly_connected)

        def record(
            key_node: ast.AST,
            value_node: ast.AST,
            line: int,
            function_name: str,
        ) -> None:
            if not (
                isinstance(key_node, ast.Constant)
                and isinstance(key_node.value, str)
                and not _is_constant_expression(value_node)
            ):
                return
            evidence[key_node.value].append(
                (filename, line, function_name)
            )

        for function_name in sorted(connected):
            if function_name == "build_wake_up_block":
                continue
            function = functions[function_name]

            for node in ast.walk(function):
                # {"current_focus": measured_title}
                if isinstance(node, ast.Dict):
                    for key, value in zip(node.keys, node.values):
                        if key is not None:
                            record(key, value, node.lineno, function_name)

                # mood_update["fatigue"] = snap.fatigue
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = (
                        node.targets
                        if isinstance(node, ast.Assign)
                        else [node.target]
                    )
                    for target in targets:
                        if isinstance(target, ast.Subscript):
                            record(
                                target.slice,
                                node.value,
                                node.lineno,
                                function_name,
                            )

                # state.update({"field": measured}) og
                # state.update(field=measured)
                elif (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "update"
                ):
                    if node.args and isinstance(node.args[0], ast.Dict):
                        update_dict = node.args[0]
                        for key, value in zip(
                            update_dict.keys,
                            update_dict.values,
                        ):
                            if key is not None:
                                record(key, value, node.lineno, function_name)

                    for keyword in node.keywords:
                        if keyword.arg is not None:
                            record(
                                ast.Constant(keyword.arg),
                                keyword.value,
                                node.lineno,
                                function_name,
                            )

    return dict(evidence)


def _repository_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for source_root in SOURCE_ROOTS:
        for path in sorted(source_root.rglob("*.py")):
            sources[str(path.relative_to(ROOT))] = path.read_text(encoding="utf-8")
    return sources


def _missing_fields(
    displayed: set[Field],
    writers: dict[str, list[Evidence]],
    exceptions: set[Field],
) -> set[Field]:
    return {
        field
        for field in displayed
        if field not in exceptions and field[1] not in writers
    }


def test_hvert_vist_capsule_felt_har_en_ikke_konstant_skriver():
    """En vist nutidstilstand maa ikke leve alene paa default eller arv.

    Tre fund paa een dag viste, at manuel kontrol af fatigue/fokus/open_thread
    ikke skalerer. Felterne udledes derfor fra build_wake_up_block, mens
    skriverne skal kunne spores til capsule-sinks — generiske merges med en
    ukendt dict beviser ikke, at en konkret noegle nogensinde bliver maalt.
    """
    displayed_with_lines = _displayed_fields_from_source(
        CONTINUITY.read_text(encoding="utf-8")
    )
    displayed = set(displayed_with_lines)
    exceptions = set(UNDTAEDE_FELTER)

    stale_exceptions = exceptions - displayed
    assert not stale_exceptions, (
        "Undtagelseslisten indeholder felter som ikke laengere vises; "
        f"fjern den afviklede gaeld: {sorted(stale_exceptions)}"
    )

    writers = _writer_evidence_from_sources(_repository_sources())
    missing = _missing_fields(displayed, writers, exceptions)

    details = {
        f"{section}.{key}": sorted(displayed_with_lines[(section, key)])
        for section, key in sorted(missing)
    }
    assert not missing, (
        "CONTINUITY viser kapsel-felter uden en ikke-konstant skriver paa "
        f"capsule-skrivevejen: {details}. Tilfoej en maalt producer, fjern "
        "feltet fra visningen, eller dokumenter gaelden eksplicit."
    )


def test_vagten_afviser_et_vist_felt_uden_skriver():
    """Mutation: et nyt vist felt uden producer skal give et konkret fund.

    Uden denne negative kontrol kunne en AST-vagt returnere en tom maengde,
    eller acceptere alle dict-noegler, og stadig se groen ud.
    """
    mutated_source = '''
def build_wake_up_block(capsule):
    mood = capsule.get("mood", {})
    unmeasured = mood.get("unmeasured_signal")
    lines = []
    if unmeasured:
        lines.append(f"Mood: {unmeasured}")
    return "\\n".join(lines)


def persist_something_else(measured):
    write_capsule({"mood": {"measured_signal": measured}})
'''

    displayed = set(_displayed_fields_from_source(mutated_source))
    writers = _writer_evidence_from_sources(
        {"synthetic_continuity.py": mutated_source}
    )

    assert displayed == {("mood", "unmeasured_signal")}
    assert _missing_fields(displayed, writers, set()) == {
        ("mood", "unmeasured_signal")
    }
