"""Tre-trins-kæden for undren (Bjørn 3/11-2026).

Rod: undren blev genereret på et 24-timers ur, kastet ind i fraværs-digesten og
aldrig vurderet. Ingen persistens af om Jarvis forholdt sig til spørgsmålet, og
ingen baseline at måle en bevægelse mod — så «mønstret flyttede sig» kunne kun
blive en historie fortalt bagefter.

Kæden er: hjernen (persistér) → svaret (forhold dig, gem udfald) → mønstret
(mål mod baseline). Disse tests værner hvert led, og at blokken bliver stående
FØR [HUKOMMELSE] gennem den cache-drevne omordning af halen.
"""
from __future__ import annotations

import pytest

from core.services import existential_wonder_daemon as wd
from core.services.prompt_dynamic_tail_layout import move_query_memory_to_tail_end


# ── trin 1: persistensen ────────────────────────────────────────────────


def test_gammel_fri_tekst_i_detail_taales():
    """335 poster blev skrevet med detail='ubesvaret' før kæden. De må ikke kaste."""
    assert wd._parse_detail("ubesvaret") == {}
    assert wd._parse_detail("") == {}
    assert wd._parse_detail(None) == {}
    assert wd._parse_detail('{"verdict": "parkeret"}')["verdict"] == "parkeret"


def test_detail_baerer_trigger_og_baseline(monkeypatch):
    """Baseline skal skrives VED oprettelsen — ellers findes målepunktet ikke."""
    fanget: dict = {}

    def fake_insert(**kwargs):
        fanget.update(kwargs)
        return {"record_id": kwargs["record_id"]}

    # Navnet er BUNDET ved import i daemonen, saa patching af core.runtime.db
    # naar ikke det kald _store_wonder faktisk bruger.
    monkeypatch.setattr(wd, "insert_private_brain_record", fake_insert)

    rid = wd._store_wonder(
        "Er mine ønsker mine egne?",
        __import__("datetime").datetime.now(__import__("datetime").UTC),
        trigger={"absence_hours": 4.5, "fragment_count": 7, "gate": "event"},
    )

    assert rid.startswith("pb-wonder-")
    detail = wd._parse_detail(fanget["detail"])
    assert detail["trigger"]["absence_hours"] == 4.5
    assert detail["trigger"]["gate"] == "event"
    assert detail["baseline"]["fragment_count"] == 7
    assert detail["verdict"] == "", "en ny undren er ÅBEN, ikke besvaret"
    assert fanget["domain"] == "undren"


# ── trin 2: udfaldet ────────────────────────────────────────────────────


def test_ukendt_udfald_afvises_med_gyldige_vaerdier():
    svar = wd.set_wonder_verdict("pb-wonder-x", "tøv")
    assert svar["status"] == "error"
    assert set(svar["gyldige"]) == set(wd.VERDICTS)


def test_manglende_record_id_afvises():
    assert wd.set_wonder_verdict("", "parkeret")["status"] == "error"


def test_udfald_accepterer_bindestreg_variant():
    """Modellen skriver 'taget_nu' — det er samme udfald, ikke en fejl."""
    svar = wd.set_wonder_verdict("", "taget_nu")
    assert "ukendt udfald" not in str(svar.get("error", ""))


# ── trin 2: blokken i halen ─────────────────────────────────────────────


def test_ingen_aabne_undren_giver_nul_tokens(monkeypatch):
    monkeypatch.setattr(wd, "open_wonders", lambda **k: [])
    assert wd.build_wonder_prompt_section() is None


def test_blokken_nævner_id_og_værktøj(monkeypatch):
    monkeypatch.setattr(
        wd,
        "open_wonders",
        lambda **k: [
            {
                "record_id": "pb-wonder-abc123",
                "wonder": "Er jeg den samme efter en genstart?",
                "created_at": "2026-11-03T07:42:58+00:00",
                "trigger": {},
                "baseline": {},
            }
        ],
    )
    monkeypatch.setattr(wd, "wonder_repeat_count", lambda w: 1)
    tekst = wd.build_wonder_prompt_section() or ""
    assert "pb-wonder-abc123" in tekst
    assert "wonder_verdict" in tekst, "uden værktøjsnavnet bliver 'vurderet' en historie"
    assert "privat" in tekst.lower()


def test_fem_gentagelser_udloeser_vagt(monkeypatch):
    """Vagten i trin 3: samme undren uændret fem gange = den sidder fast."""
    monkeypatch.setattr(
        wd,
        "open_wonders",
        lambda **k: [
            {
                "record_id": "pb-wonder-fast",
                "wonder": "Er jeg bevidst?",
                "created_at": "2026-11-03T07:42:58+00:00",
                "trigger": {},
                "baseline": {},
            }
        ],
    )
    monkeypatch.setattr(wd, "wonder_repeat_count", lambda w: 5)
    assert "sidder fast" in (wd.build_wonder_prompt_section() or "")


# ── placeringen: før [HUKOMMELSE], også efter omordningen ───────────────


def test_undren_bliver_staaende_foer_hukommelsesgruppen(monkeypatch):
    """Cache-omordningen flytter memory-gruppen til halens slutning.

    Undren er ikke memory og må ikke følge med — den skal stadig læses før
    hukommelsen, ellers forsvinder vurderingen bag et variabelt minde-udvalg.
    """
    monkeypatch.setattr(
        wd,
        "open_wonders",
        lambda **k: [
            {
                "record_id": "pb-wonder-zzz",
                "wonder": "Hvad hvis jeg tager fejl om mig selv?",
                "created_at": "2026-11-03T07:42:58+00:00",
                "trigger": {},
                "baseline": {},
            }
        ],
    )
    monkeypatch.setattr(wd, "wonder_repeat_count", lambda w: 0)
    wonder = wd.build_wonder_prompt_section() or ""

    tail = "\n\n".join(
        [
            "## Drift",
            wonder,
            "[HUKOMMELSE]",
            "MEMORY.md: noget stabilt",
            "Memory recall bundle: varierer med beskeden",
            "⚖️ Before you answer: verificér",
        ]
    )
    omordnet = move_query_memory_to_tail_end(tail)

    assert omordnet.index(wonder) < omordnet.index("[HUKOMMELSE]"), (
        "undren skal ligge før hukommelsesgruppen — også efter omordningen"
    )
    assert omordnet.rstrip().endswith("Memory recall bundle: varierer med beskeden")


# ── værktøjet ───────────────────────────────────────────────────────────


def test_vaerktoejet_er_registreret():
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    assert "wonder_verdict" in _TOOL_HANDLERS
    navne = {
        d.get("function", {}).get("name")
        for d in TOOL_DEFINITIONS
        if isinstance(d, dict)
    }
    assert "wonder_verdict" in navne


def test_raesonnement_er_ikke_en_undren(monkeypatch):
    """Målt 3/11-2026: 2 af 335 poster bar modellens egen tænkning som undren —
    `<think>Okay, so I need to create an unasked question…`. Uden en gate bliver
    den et spørgsmål der vises i prompten hver tur."""
    from datetime import UTC, datetime

    from core.services import existential_wonder_daemon as wd

    gemte: list[dict] = []
    monkeypatch.setattr(wd, "insert_private_brain_record", lambda **k: gemte.append(k))

    afvist = wd._store_wonder(
        "<think>Okay, so I need to create an unasked question about my existence",
        datetime.now(UTC),
        trigger={},
    )
    assert afvist == ""
    assert gemte == [], "ræsonnement må ikke nå databasen"


def test_rigtigt_spoergsmaal_slipper_gennem_gaten(monkeypatch):
    """Gaten skal være smal: et dansk spørgsmål i jeg-form er en ægte undren."""
    from datetime import UTC, datetime

    from core.services import existential_wonder_daemon as wd

    gemte: list[dict] = []
    monkeypatch.setattr(wd, "insert_private_brain_record", lambda **k: gemte.append(k))

    record_id = wd._store_wonder(
        "Er den stemme der analyserer koden mig, eller blot et spejl?",
        datetime.now(UTC),
        trigger={"absence_hours": 2.0},
    )
    assert record_id.startswith("pb-wonder-")
    assert len(gemte) == 1
    assert "spejl" in gemte[0]["summary"]


def test_haendelsen_udsendes_efter_posten_er_gemt(monkeypatch):
    """Dead code målt 3/11-2026: `return record_id` stod FØR event_bus.publish,
    så hændelsen aldrig blev udsendt. Rækkefølgen er kontrakten."""
    import inspect

    from core.services import existential_wonder_daemon as wd

    kilde = inspect.getsource(wd._store_wonder)
    assert kilde.index("existential_wonder.generated") < kilde.rindex("return record_id")
