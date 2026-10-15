"""`trigger` er beskrivende proveniens — legacy-fritekst maa ikke goere posten ulaeselig.

Maalt 15/10-2026: 31 poster i `~/.jarvis-v2/shared/jarvis_brain/` bar
fritekst som `arkiv-migrering (11/10-2026)` (25 stk) og `dybdesession
(30 min)` (3 stk). `BrainEntry.__post_init__` kastede
`ValueError: invalid trigger`, saa `b4_catchup_infer` fejlede hver time
paa dem — og posterne kunne slet ikke laeses.

Vaernet beskyttede intet: `_VALID_TRIGGER` blev kun brugt i
`__post_init__`, intet forgrener paa `trigger`, og skrive-stederne sender
gyldige navne selv. Det eneste det opnaaede var at goere en migrerings
fritekst til en laase paa posten.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.services.jarvis_brain import BrainEntry


def _entry(**kw) -> BrainEntry:
    nu = datetime.now(UTC)
    base: dict = {
        "id": "brn_test",
        "kind": "indsigt",
        "visibility": "personal",
        "domain": "self",
        "title": "t",
        "content": "c",
        "created_at": nu,
        "updated_at": nu,
        "last_used_at": None,
        "salience_base": 1.0,
        "salience_bumps": 0,
    }
    base.update(kw)
    return BrainEntry(**base)


@pytest.mark.parametrize(
    "trigger",
    [
        "arkiv-migrering (11/10-2026)",
        "dybdesession (30 min)",
        "dybdesession (30 min, Bjørn bad)",
        "self-wakeup (nat-vagt)",
        "natligt_dyk",
    ],
)
def test_legacy_fritekst_trigger_er_laesbar(trigger: str):
    """De praecise vaerdier der fejlede i drift skal kunne laeses."""
    assert _entry(trigger=trigger).trigger == trigger


def test_de_fire_kendte_triggere_er_uaendrede():
    for trigger in ("spontaneous", "post_web_search", "reflection_slot", "adopted_proposal"):
        assert _entry(trigger=trigger).trigger == trigger


def test_tom_trigger_er_stadig_en_fejl():
    """Grænsen flyttede sig, den forsvandt ikke: et TOMT navn er en fejl."""
    with pytest.raises(ValueError):
        _entry(trigger="")
    with pytest.raises(ValueError):
        _entry(trigger="   ")
