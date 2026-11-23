"""`abandon_initiative` skal være NÅELIG fra værktøjsfladen, ikke kun en service-funktion.

MAALT 23/11-2026: `abandon_long_term_intention` fandtes i `initiative_queue.py`
og blev kaldt af mobil-fladen gennem `/mc/life-projects/{id}/abandon` — men der
var INGEN definition, INGEN handler og ingen oppost i mappingen. Jarvis kunne
derfor ikke lukke sit eget livsprojekt i samtalen; det krævede et Python-kald
uden for fladen. Samme fejlform som `decline_initiative` havde indtil samme dag:
skrivevejen fandtes, indgangen manglede.

To ting adskiller de to indgange, og begge er testet her:

- `decline` saetter `declined` (praemissen er vaek); `abandon` saetter `expired`
  med `abandoned_at` — den tilstand decay-dommeren selv saetter.
- `abandon_long_term_intention` tjekker IKKE status. Den saetter `expired` igen
  paa en post der allerede ER expired og svarer med en raekke, som om noget
  skete. Handlers kalder derfor status-kontrollen selv, saa en lukning af noget
  allerede lukket ikke kan ligne en handling.
"""
from __future__ import annotations


def _definition(name: str) -> dict | None:
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    return next(
        (
            d
            for d in TOOL_DEFINITIONS
            if isinstance(d, dict) and d.get("function", {}).get("name") == name
        ),
        None,
    )


def test_abandon_initiative_er_i_vaerktoejsfladen() -> None:
    """Uden en definition kan modellen ikke se værktøjet — så bliver den aldrig kaldt."""
    d = _definition("abandon_initiative")
    assert d is not None, "abandon_initiative mangler i TOOL_DEFINITIONS"
    params = d["function"]["parameters"]
    assert params["required"] == ["initiative_id", "reason"]
    assert "initiative_id" in params["properties"]
    assert "reason" in params["properties"]


def test_abandon_initiative_har_en_handler() -> None:
    """En definition uden handler er et løfte runtime ikke kan indfri."""
    from core.tools.simple_tools import _TOOL_HANDLERS

    assert "abandon_initiative" in _TOOL_HANDLERS


def test_abandon_initiative_har_en_label() -> None:
    """Uden label staar der et raat funktionsnavn i den synlige flade."""
    from core.services.visible_tool_labels import _TOOL_LABELS

    assert "abandon_initiative" in _TOOL_LABELS


def test_abandon_laegger_livsprojektet_ned_og_bevarer_samtykke(isolated_runtime) -> None:
    """Kernen: lukningen skal saette `expired` med en ærlig grund — og ikke slette
    det samtykke Bjørn faktisk gav. Et livsprojekt han godkendte 14/11 er en
    historisk kendsgerning; en lukning må ikke viske den ud for at goere
    historien paenere."""
    from core.runtime import db_runtime_initiatives as rdb
    from core.services import initiative_queue
    from core.tools.simple_tools import _TOOL_HANDLERS

    initiative_id = initiative_queue.seed_long_term_intention(
        title="Et livsprojekt der ikke kan koeres faerdigt",
        why="Det er en retning, ikke en opgave.",
    )
    # Et menneskes ja — gennem den aegte vej, ikke et haandskrevet felt — og det
    # skal overleve lukningen.
    initiative_queue.endorse_long_term_intention(
        initiative_id, note="Bjørn sagde det er i orden."
    )
    foer = rdb.get_runtime_initiative(initiative_id)
    assert foer["status"] == "pending"
    assert foer["initiative_type"] == "long_term_intention"
    samtykke = foer["user_approved_at"]
    assert samtykke, "endorse satte ikke et samtykke — så beviser testen intet"

    grund = "Livsvarig retning — kan ikke koeres faerdigt og lukkes som en task."
    svar = _TOOL_HANDLERS["abandon_initiative"](
        {"initiative_id": initiative_id, "reason": grund}
    )
    assert svar["status"] == "ok", svar

    efter = rdb.get_runtime_initiative(initiative_id)
    assert efter["status"] == "expired"
    assert efter["abandoned_at"], "expired uden abandoned_at kan ikke efterproeves"
    assert efter["blocked_reason"] == grund[:120]
    assert efter["user_approved_at"] == samtykke, (
        "lukningen slettede et samtykke der faktisk blev givet"
    )


def test_allerede_lukket_post_svarer_fejl(isolated_runtime) -> None:
    """Den falske succes: `abandon_long_term_intention` saetter `expired` igen paa
    en post der allerede ER expired. Uden status-kontrollen i handleren ville
    den svare «ok» paa en handling der ikke skete noget ved."""
    from core.runtime import db_runtime_initiatives as rdb
    from core.services import initiative_queue
    from core.tools.simple_tools import _TOOL_HANDLERS

    initiative_id = initiative_queue.seed_long_term_intention(
        title="Allerede lagt ned",
        why="Test af den falske succes.",
    )
    foerste = _TOOL_HANDLERS["abandon_initiative"](
        {"initiative_id": initiative_id, "reason": "Foerste lukning."}
    )
    assert foerste["status"] == "ok"
    foer_igen = rdb.get_runtime_initiative(initiative_id)["abandoned_at"]

    anden = _TOOL_HANDLERS["abandon_initiative"](
        {"initiative_id": initiative_id, "reason": "Anden lukning."}
    )
    assert anden["status"] == "error", "en lukning af noget allerede lukket ligner en handling"
    assert "pending" in anden["error"]

    efter_igen = rdb.get_runtime_initiative(initiative_id)["abandoned_at"]
    assert efter_igen == foer_igen, "den anden lukning overskrev det foerste tidsstempel"


def test_almindelig_initiativpost_afvises(isolated_runtime) -> None:
    """`abandon` er kun for livsprojekter. En almindelig post hoerer i decline."""
    from core.services import initiative_queue
    from core.tools.simple_tools import _TOOL_HANDLERS

    initiative_id = initiative_queue.push_initiative(
        focus="En helt almindelig post",
        source="jarvis-tool",
        priority="low",
    )
    svar = _TOOL_HANDLERS["abandon_initiative"](
        {"initiative_id": initiative_id, "reason": "test"}
    )
    assert svar["status"] == "error"
    assert "livsprojekt" in svar["error"]


def test_ukendt_id_svarer_aerligt(isolated_runtime) -> None:
    """En post der ikke findes maa ikke ligne en succes."""
    from core.tools.simple_tools import _TOOL_HANDLERS

    svar = _TOOL_HANDLERS["abandon_initiative"](
        {"initiative_id": "life-findes-ikke", "reason": "test"}
    )
    assert svar["status"] == "error"
    assert "findes ikke" in svar["error"]


def test_tom_grund_afvises() -> None:
    """En lukning uden grund kan ikke efterproeves — den skal naegtes, ikke gemmes tom."""
    from core.tools.simple_tools import _TOOL_HANDLERS

    svar = _TOOL_HANDLERS["abandon_initiative"](
        {"initiative_id": "life-hvad-som-helst", "reason": "   "}
    )
    assert svar["status"] == "error"
    assert "reason" in svar["error"]
