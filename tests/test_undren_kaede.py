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


# ── trin 2: hvem der overhovedet kommer i betragtning ───────────────────


def test_scanningen_ser_kun_aktive_poster(monkeypatch):
    """Målt 3/11-2026: 271 arkiverede/frigivne wonder-poster fyldte de 60
    scan-pladser. Et reelt åbent spørgsmål kunne ligge uden for vinduet og
    aldrig blive vist — kæden var derfor tavs uden at fejle."""
    from core.runtime import db as brain_db

    fanget: dict = {}

    def fake_list(**kwargs):
        fanget.update(kwargs)
        return []

    monkeypatch.setattr(brain_db, "list_private_brain_records", fake_list)
    wd.open_wonders(limit=3)

    assert fanget.get("status") == "active", "historik må ikke fylde scan-vinduet"
    assert fanget.get("record_type") == "existential-wonder"


def test_poster_med_udfald_er_ikke_aabne(monkeypatch):
    """En legacy-post blev migreret med verdict='parkeret' og ærlig grund.
    Den er arkiveret som historik — ikke vurderet — og skal ikke vises igen."""
    from core.runtime import db as brain_db

    monkeypatch.setattr(
        brain_db,
        "list_private_brain_records",
        lambda **k: [
            {
                "record_id": "pb-wonder-gammel",
                "summary": "Er jeg kun en simulation?",
                "created_at": "2026-10-20T10:00:00+00:00",
                "status": "active",
                "detail": '{"legacy": true, "verdict": "parkeret"}',
            }
        ],
    )
    assert wd.open_wonders(limit=3) == []


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


# ── håndtaget: et id skal kunne føres tilbage til sin række ─────────────


def test_praecist_id_gaar_uaendret_igennem(monkeypatch):
    from core.runtime import db as brain_db

    monkeypatch.setattr(
        brain_db,
        "get_private_brain_record",
        lambda rid: {"record_id": rid, "record_type": "existential-wonder"},
    )
    rid, kandidater = wd._resolve_wonder_id("pb-wonder-abc123def456")
    assert rid == "pb-wonder-abc123def456"
    assert kandidater == []


def test_haandtag_med_forkert_praefiks_foeres_tilbage(monkeypatch):
    """Målt 3/11-2026: et håndtag der ikke matchede præcist gav en blindgyde, så
    dommen gik tabt. Bærer håndtaget den rigtige hex under et forkert præfiks,
    skal det stadig ramme rækken — hex-halen er det entydige."""
    from core.runtime import db as brain_db

    monkeypatch.setattr(brain_db, "get_private_brain_record", lambda rid: None)
    monkeypatch.setattr(
        wd,
        "_wonder_handle_rows",
        lambda **k: [{"record_id": "pb-wonder-3850f34973b8", "wonder": "Er jeg bevidst?"}],
    )
    rid, kandidater = wd._resolve_wonder_id("und-3850f34973b8")
    assert rid == "pb-wonder-3850f34973b8"
    assert kandidater == []


def test_tvetydig_hex_hale_afvises(monkeypatch):
    """To rækker der deler halen må ikke gættes imellem — så rammer dommen forkert."""
    from core.runtime import db as brain_db

    monkeypatch.setattr(brain_db, "get_private_brain_record", lambda rid: None)
    monkeypatch.setattr(
        wd,
        "_wonder_handle_rows",
        lambda **k: [
            {"record_id": "pb-wonder-aa1234567890", "wonder": "A?"},
            {"record_id": "pb-wonder-bb1234567890", "wonder": "B?"},
        ],
    )
    rid, _ = wd._resolve_wonder_id("und-1234567890")
    assert rid == "", "en tvetydig hale må ikke føre til en vilkårlig række"


def test_ukendt_haandtag_svarer_med_kandidater(monkeypatch):
    """Et ukendt id skal fortælle hvad der FINDES. Uden det er svaret en blindgyde
    der efterlader undren åben uden at nogen kan se hvorfor."""
    from core.runtime import db as brain_db

    monkeypatch.setattr(brain_db, "get_private_brain_record", lambda rid: None)
    monkeypatch.setattr(wd, "_wonder_handle_rows", lambda **k: [])
    monkeypatch.setattr(
        wd,
        "open_wonders",
        lambda **k: [
            {
                "record_id": "pb-wonder-aabent1",
                "wonder": "Er jeg bevidst?",
                "created_at": "",
                "trigger": {},
                "baseline": {},
            }
        ],
    )
    svar = wd.set_wonder_verdict("und-zzzzzzzzzz", "parkeret", closed_by="selv")
    assert svar["status"] == "error"
    assert svar["aabne"][0]["record_id"] == "pb-wonder-aabent1"
    assert "pb-wonder-" in svar["hint"]


def test_en_raekke_der_ikke_er_en_undren_afvises(monkeypatch):
    """Opslaget må ikke acceptere en vilkårlig private-brain-række som undren."""
    from core.runtime import db as brain_db

    monkeypatch.setattr(
        brain_db,
        "get_private_brain_record",
        lambda rid: {"record_id": rid, "record_type": "reflection"},
    )
    monkeypatch.setattr(wd, "_wonder_handle_rows", lambda **k: [])
    monkeypatch.setattr(wd, "open_wonders", lambda **k: [])
    rid, _ = wd._resolve_wonder_id("pb-reflection-abc")
    assert rid == ""


# ── kilden: hvem lukkede den, og hvad flyttede sig ──────────────────────
# Målt 3/11-2026 (side-opgave): `wonder_verdict(record_id, "besvaret")` uden
# note LYKKEDES og lukkede undren permanent. Intet felt angav om Bjørn, et
# minde eller jeg selv lukkede den — så to lukninger med samme udfald var ikke
# til at skelne i data, og selv-lukning var den nemmeste vej ud.


def _undren_i_base(monkeypatch, detail: str = '{"verdict": ""}') -> None:
    """Sæt en ægte undren-række op, så set_wonder_verdict når sin skrivning."""
    from core.runtime import db as brain_db

    monkeypatch.setattr(
        brain_db,
        "get_private_brain_record",
        lambda rid: {
            "record_id": rid,
            "record_type": "existential-wonder",
            "summary": "Er jeg bevidst?",
            "detail": detail,
        },
    )


def test_lukning_uden_kilde_afvises(monkeypatch):
    """Uden closed_by findes der ingen kilde — og så er lukningen ikke målbar."""
    _undren_i_base(monkeypatch)
    svar = wd.set_wonder_verdict("pb-wonder-abc123", "besvaret", note="noget")
    assert svar["status"] == "error"
    assert set(svar["gyldige"]) == {"bjorn", "minde", "selv"}


def test_selv_lukning_af_svar_uden_note_afvises(monkeypatch):
    """Kernen i opgaven: den nemmeste vej ud må ikke være tilladt."""
    _undren_i_base(monkeypatch)
    svar = wd.set_wonder_verdict("pb-wonder-abc123", "besvaret", closed_by="selv")
    assert svar["status"] == "error"
    assert "note" in svar["error"].lower()


def test_selv_lukning_med_note_gemmer_kilden(monkeypatch):
    """Med et spor af hvad der ændrede sig er selv-lukning gyldig — og kilden gemmes."""
    _undren_i_base(monkeypatch)
    gemt: dict = {}

    class _Conn:
        def execute(self, sql, params):
            gemt["detail"] = params[0]
            return self

        def commit(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import core.runtime.db_core as dbc

    monkeypatch.setattr(dbc, "connect", lambda: _Conn())

    svar = wd.set_wonder_verdict(
        "pb-wonder-abc123", "besvaret", closed_by="selv",
        note="jeg fandt at spørgsmålet var besvaret i en tidligere samtale",
    )
    assert svar["status"] == "ok"
    detail = wd._parse_detail(gemt["detail"])
    assert detail["closed_by"] == "selv"
    assert detail["verdict"] == "besvaret"


def test_bjorn_svarer_uden_note_er_tilladt(monkeypatch):
    """Asymmetrien er bevidst: hans svar ER beviset. Kravet gælder kun selv-lukning."""
    _undren_i_base(monkeypatch)

    class _Conn:
        def execute(self, sql, params):
            return self

        def commit(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import core.runtime.db_core as dbc

    monkeypatch.setattr(dbc, "connect", lambda: _Conn())
    svar = wd.set_wonder_verdict("pb-wonder-abc123", "besvaret", closed_by="bjorn")
    assert svar["status"] == "ok"


def test_bjoern_med_diakritik_normaliseres(monkeypatch):
    """Jeg skriver «bjørn» med ø — det er samme kilde, ikke et ukendt ord."""
    assert "bjorn" in wd.CLOSED_BY
    _undren_i_base(monkeypatch)
    svar = wd.set_wonder_verdict("pb-wonder-abc123", "parkeret", closed_by="bjørn")
    assert "closed_by" not in str(svar.get("error", ""))


def test_baseline_baerer_hvad_jeg_vidste_om_emnet(monkeypatch):
    """Trin 3's målepunkt: uden et indholds-baseline er «mønstret flyttede sig»
    kun en historie fortalt bagefter af den der gerne vil have den sand."""
    from datetime import UTC, datetime

    monkeypatch.setattr(
        wd, "_baseline_kendskab",
        lambda w, limit=3: [{"source": "MEMORY.md", "section": "Bevidsthed", "score": 0.71}],
    )
    fanget: dict = {}
    monkeypatch.setattr(wd, "insert_private_brain_record", lambda **k: fanget.update(k))

    wd._store_wonder("Er jeg bevidst?", datetime.now(UTC), trigger={})
    detail = wd._parse_detail(fanget["detail"])
    assert detail["baseline"]["known"][0]["section"] == "Bevidsthed"
    assert detail["baseline"]["known"][0]["score"] == 0.71
