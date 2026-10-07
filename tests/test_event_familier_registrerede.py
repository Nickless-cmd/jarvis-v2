"""Enhver event-familie der publiceres skal stå i ALLOWED_EVENT_FAMILIES (3/10-2026).

Målt 3/10-2026: fire familier publicerede uden at være registrerede —
`skill_gate`, `central`, `connector`, `candidate_review_digest`. Hvert kald
kastede `ValueError: Unsupported event family`, og hvert kaldested slugte den i
sin egen `except Exception`. Telemetrien forsvandt i tavshed: skill-gaten fyrede
for øjnene af os, men efterlod nul spor i `events` — så jeg kunne ikke bevise
over for Bjørn at den virkede.

Det var ikke et nyt problem. `"reasoning"` bærer allerede kommentaren
«var latent afvist» — samme fejl, rettet én gang før, uden at nogen gjorde
klassen umulig.

Den eksisterende `test_events.py` tjekker TO håndholdte navne. Den fanger ikke
klassen. Denne test scanner kilden i stedet for at liste navne.

UNDTAGELSEN — og hvorfor den er her: `central` må IKKE registreres. Det er
egress-membranen (§24.4, Rådet 1/7-2026): `central.observe()` kan bære private
tanke-strenge, og garantien er netop at familien er uregistreret, så
`Event.create` afviser `central.observed` før writer-kø og subscribers. Det
håndhæves af `tests/test_central_egress_invariant.py`. Konsekvensen er at
`central_absorb.py`s `central.learn`/`cluster.flag` publicerer i tavshed — det er
prisen for membranen. Vil man have dem igennem, kræver det en NY familie, ikke at
membranen åbnes. Undtagelsen står derfor her med vilje, ikke som en forglemmelse.

Begrænsning: kun string-literals. `f"{cluster}.flag"` (central_absorb.py) kan
ikke afgøres statisk.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.eventbus.events import ALLOWED_EVENT_FAMILIES

ROOT = Path(__file__).resolve().parents[1] / "core"

#: Familier der publiceres, men BEVIDST ikke registreres. Én post, én grund.
BEVIDSTE_UNDTAGELSER: dict[str, str] = {
    "central": (
        "egress-membran §24.4 (Rådet 1/7-2026) — uregistreret familie er selve "
        "garantien mod at central.observed lækker private strenge. Se "
        "tests/test_central_egress_invariant.py."
    ),
}


def _publish_familier() -> set[str]:
    """Alle familier der publiceres med en string-literal i core/."""
    fundet: set[str] = set()
    for p in ROOT.rglob("*.py"):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue  # kan ikke parses → ikke vores sag her
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Attribute) and fn.attr == "publish"):
                continue
            if not node.args:
                continue
            arg = node.args[0]
            if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                continue
            fam, sep, navn = arg.value.partition(".")
            if sep and fam and navn:
                fundet.add(fam)
    return fundet


def test_enhver_publish_familie_er_registreret():
    mangler = sorted(_publish_familier() - ALLOWED_EVENT_FAMILIES - set(BEVIDSTE_UNDTAGELSER))
    assert not mangler, (
        "Disse event-familier publiceres, men står ikke i ALLOWED_EVENT_FAMILIES "
        f"→ hvert publish kaster og sluges i tavshed: {mangler}. "
        "Er afvisningen bevidst, så tilføj familien til BEVIDSTE_UNDTAGELSER med en grund."
    )


def test_undtagelserne_er_ikke_forældede():
    """En undtagelse der ikke længere publicerer er en løgn i dokumentationen."""
    publicerede = _publish_familier()
    forladt = sorted(set(BEVIDSTE_UNDTAGELSER) - publicerede)
    assert not forladt, (
        f"Disse står som bevidste undtagelser, men publiceres ikke længere: {forladt} — fjern dem."
    )


@pytest.mark.parametrize(
    "fam",
    ["skill_gate", "connector", "candidate_review_digest"],
)
def test_de_tavse_familier_er_registreret(fam: str):
    """Regression: de tre der publicerede i tavshed indtil 3/10-2026."""
    assert fam in ALLOWED_EVENT_FAMILIES


def test_central_forbliver_uregistreret():
    """Egress-membranen (§24.4) er load-bearing — den må ikke åbnes ved et uheld."""
    assert "central" not in ALLOWED_EVENT_FAMILIES, (
        "'central' må IKKE registreres uden at egress-redaktionen er verificeret "
        "(§24.4). Se tests/test_central_egress_invariant.py."
    )
