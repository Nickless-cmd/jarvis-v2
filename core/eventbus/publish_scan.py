"""Find hvert publish-kald med en familie.navn-literal — statisk, uden at koere noget.

Eksemplet skrives med vilje ikke som et rigtigt kald: gjorde det det, ville
scanneren finde sin egen docstring og opfinde familien «familie».

Baggrund: tre gange paa to dage fandt vi det samme moenster — noget bygget, men
kun *naesten* tilsluttet:

  · `tool_discovery.nudge` blev afvist af ALLOWED_EVENT_FAMILIES; kaldstedets
    except slugte det til en debug-linje, og skygge-maalingen ville have vist
    nul i ugevis.
  · `pause_and_ask`-resultater blev aldrig parset i desk — spoergsmaalet stod
    som raa JSON.
  · `threshold_proposed` blev beregnet gennem 656 beslutninger og aldrig anvendt.

Kun den foerste klasse er statisk afgoerbar, og den er til gengaeld eksakt:
`publish()` kalder `Event.create()` som kalder `validate()`, saa en familie der
ikke staar i ALLOWED_EVENT_FAMILIES raiser — hver gang, tavst.

Maalt 6/9-2026: **64 familier** publiceres i core/apps/scripts uden at vaere
tilladt. Nul events i databasen for dem alle.
"""

from __future__ import annotations

import re
from pathlib import Path

# Matcher et publish-kald med en streng-literal som foerste argument.
# Eksemplet skrives IKKE som et rigtigt kald her: gjorde det det, ville
# scanneren finde sin egen docstring og opfinde en familie.
#
# Navne-delen er bevidst bred (`[^'"]+`): et foerste forsoeg brugte
# [a-zA-Z0-9_.{}] og var dermed BLIND for navne med aeoaa. Min egen
# verifikations-proeve slap igennem, fordi jeg havde doebt den «haendelse».
# En scanner med et hul er vaerre end ingen scanner: den giver falsk tryghed.
_PUBLISH = re.compile(r'publish\(\s*[\'"]([a-zA-Z_][a-zA-Z0-9_]*)\.([^\'"]+)[\'"]')

_ROEDDER = ("core", "apps", "scripts")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def scan_published_families(rod: Path | None = None) -> dict[str, list[str]]:
    """familie → liste af "sti:linje" hvor den publiceres.

    Worktrees og node_modules udelades: de er kopier, og de ville faa hvert fund
    til at taelle flere gange.
    """
    base = rod or _repo_root()
    ud: dict[str, list[str]] = {}
    for navn in _ROEDDER:
        for p in (base / navn).rglob("*.py"):
            # Maalt RELATIVT til roden. Foer stod der `".worktrees" in str(p)`
            # paa den ABSOLUTTE sti — og et worktree ligger SELV under
            # .worktrees/, saa hver eneste fil blev sprunget over og scanningen
            # fandt nul. Den var altsaa blind praecis dér hvor Codex' grene
            # bygges.
            rel = p.relative_to(base)
            # Paa KOMPONENTER, ikke praefiks: saa rammer den ogsaa en kopi der
            # ligger dybere end roden, og den kan stadig ikke udelukke sig selv
            # naar basen SELV er et worktree (den relative sti naevner det ikke).
            if {"node_modules", ".worktrees"} & set(rel.parts):
                continue
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for m in _PUBLISH.finditer(txt):
                linje = txt[: m.start()].count("\n") + 1
                ud.setdefault(m.group(1), []).append(f"{p.relative_to(base)}:{linje}")
    return ud


def unregistered_families(rod: Path | None = None) -> dict[str, list[str]]:
    """De publicerede familier der IKKE er tilladt → publish raiser tavst."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES

    return {
        f: steder
        for f, steder in scan_published_families(rod).items()
        if f not in ALLOWED_EVENT_FAMILIES
    }


def dict_form_publish_calls(rod: Path | None = None) -> list[str]:
    """Find hvert ``X.publish({...})``-kald — dict-formen der ALTID raiser på event_bus.

    Målt 13/9-2026: 24 kaldesteder skrev
    ``event_bus.publish({"kind": .., "payload": ..})``. ``EventBus.publish`` tager
    ``(kind, payload)``; et dict som ``kind`` gør at ``Event.validate`` kalder
    ``kind.partition(".")`` på et dict → ``AttributeError`` — og hvert kaldsteds
    ``except`` sluger den. Regex-scanneren ovenfor er BLIND for formen (den kræver
    et streng-literal som første argument), så gælden var usynlig i månedsvis.

    Derfor AST i stedet for regex her: vi leder efter en *struktur* (et dict-agtigt
    objekt som første argument), ikke en tekststreng. Formen fanges i alle tre
    skikkelser — ``{...}``, ``{k: v for ...}`` og ``dict(...)`` — for alle tre ville
    give samme fejl på event_bus. (Målt: `bridge_presence`-kaldet er en DictComp,
    så en scanner der kun kendte ``ast.Dict`` var blind for det.)

    Returnerer ``"sti:linje (receiver)"``. ``bridge_presence.publish(dict)`` er en
    ANDEN, legitim signatur (dict ER første argument der) — den listes også, så
    kalderen selv kan skelne. Filtrér på ``(event_bus)`` for bus-kaldene.
    """
    import ast
    import warnings

    base = rod or _repo_root()
    ud: list[str] = []
    for navn in _ROEDDER:
        for p in (base / navn).rglob("*.py"):
            rel = p.relative_to(base)
            if {"node_modules", ".worktrees"} & set(rel.parts):
                continue
            try:
                txt = p.read_text(encoding="utf-8")
                with warnings.catch_warnings():
                    # Andre filers ugyldige escape-sekvenser er ikke vores sag —
                    # uden dette drukner scanningen i DeprecationWarnings.
                    warnings.simplefilter("ignore")
                    tree = ast.parse(txt)
            except Exception:
                continue
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "publish"
                    and node.args
                ):
                    continue
                first = node.args[0]
                dict_agtig = isinstance(first, (ast.Dict, ast.DictComp)) or (
                    isinstance(first, ast.Call)
                    and isinstance(first.func, ast.Name)
                    and first.func.id == "dict"
                )
                if dict_agtig:
                    ud.append(f"{rel}:{node.lineno} ({ast.unparse(node.func.value)})")
    return sorted(ud)
