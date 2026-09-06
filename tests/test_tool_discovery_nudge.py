"""Peg paa det usynlige — og ti stille naar der intet er at pege paa.

Spejler tests/test_skill_relevance_surface.py i to grupper (Tavshed / Indhold),
som spec'ens §Tests & edge cases kraever. Matcheren monkeypatches altid —
aldrig et rigtigt embed-kald.
"""

from __future__ import annotations

import pytest

from core.services.prompt_sections import tool_discovery_nudge as T

BESKED = "kan du lægge et møde ind i min kalender på fredag"


@pytest.fixture(autouse=True)
def _grundtilstand(monkeypatch):
    """Taendt, ikke prewarm, tomt katalog, registret kender kalender-toolet."""
    monkeypatch.setattr(T, "_enabled", lambda: True)
    monkeypatch.setattr(T, "_er_prewarm", lambda sid: False)
    monkeypatch.setattr(T, "_katalog_tekst", lambda: "read_file, write_file, bash")
    monkeypatch.setattr(
        T, "_registrerede_navne",
        lambda: {"calendar_create_event", "read_file", "write_file", "bash"},
    )
    monkeypatch.setattr(T, "_undertrykt", lambda sid, navn: False)
    monkeypatch.setattr(T, "_husk_nudge", lambda sid, navn: None)
    monkeypatch.setattr(T, "_log_nudge", lambda navn, sid, score: None)


def _stub(monkeypatch, resultat):
    monkeypatch.setattr(T, "_matches", lambda besked: resultat)


def _maa_ikke_slaa_op(monkeypatch):
    monkeypatch.setattr(
        T, "_matches",
        lambda besked: pytest.fail("måtte ikke betale for opslaget her"),
    )


# ---------------------------------------------------------------------------
# Tavshed hvor der intet er
# ---------------------------------------------------------------------------


def test_kort_besked_springes_over_uden_opslag(monkeypatch):
    """«hej» matcher aldrig noget — så skal vi heller ikke betale for opslaget."""
    _maa_ikke_slaa_op(monkeypatch)
    assert T.tool_discovery_nudge_section("hej") == ""
    assert T.tool_discovery_nudge_section("") == ""
    assert T.tool_discovery_nudge_section("   ") == ""


def test_prewarm_koster_aldrig_et_opslag(monkeypatch):
    """Prewarm varmer cachen — den skal ikke betale for et embedding-kald."""
    monkeypatch.setattr(T, "_er_prewarm", lambda sid: True)
    _maa_ikke_slaa_op(monkeypatch)
    assert T.tool_discovery_nudge_section(BESKED, "__prewarm__") == ""


def test_killswitch_slukker(monkeypatch):
    monkeypatch.setattr(T, "_enabled", lambda: False)
    _stub(monkeypatch, [("calendar_create_event", 0.91)])
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_ingen_traef_giver_tom_sektion(monkeypatch):
    _stub(monkeypatch, [])
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_tom_embedding_db_giver_ingen_nudge(monkeypatch):
    """Første kørsel før warmup: ingen vektorer, ingen crash, ingen nudge."""
    _stub(monkeypatch, [])
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_ollama_nede_vaelter_ikke_prompten(monkeypatch):
    def eksploder(besked):
        raise TimeoutError("ollama svarer ikke")
    monkeypatch.setattr(T, "_matches", eksploder)
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_under_taerskel_giver_tavshed(monkeypatch):
    _stub(monkeypatch, [("calendar_create_event", T._THRESHOLD - 0.01)])
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_foraeldet_vektor_foreslaas_aldrig(monkeypatch):
    """458 vektorer mod 429 registrerede — resten er alias/forældede navne."""
    _stub(monkeypatch, [("runtime_calendar_create_event", 0.93)])
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_tool_der_allerede_staar_i_kataloget_nudges_ikke(monkeypatch):
    """Nudgen må kun pege på det han IKKE kan se."""
    _stub(monkeypatch, [("read_file", 0.95)])
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_uden_register_foreslaar_vi_ingenting(monkeypatch):
    """Kan vi ikke krydstjekke, er tavshed det sikre."""
    monkeypatch.setattr(T, "_registrerede_navne", lambda: set())
    _stub(monkeypatch, [("calendar_create_event", 0.93)])
    assert T.tool_discovery_nudge_section(BESKED) == ""


def test_undertrykt_tool_nudges_ikke_igen(monkeypatch):
    monkeypatch.setattr(T, "_undertrykt", lambda sid, navn: navn == "calendar_create_event")
    _stub(monkeypatch, [("calendar_create_event", 0.93)])
    assert T.tool_discovery_nudge_section(BESKED, "s1") == ""


def test_misformet_traef_springes_over(monkeypatch):
    """top_k_similar giver tupler; en misformet række må ikke vælte sektionen."""
    from core.services import tool_embeddings as TE
    monkeypatch.setattr(TE, "top_k_similar", lambda q, k=8: [None, ("x",), ("calendar_create_event", 0.93)])
    ud = T.tool_discovery_nudge_section(BESKED)
    assert "calendar_create_event" in ud


# ---------------------------------------------------------------------------
# Indholdet
# ---------------------------------------------------------------------------


def test_staerkt_match_giver_nudge_med_load_more_tools(monkeypatch):
    _stub(monkeypatch, [("calendar_create_event", 0.91)])
    ud = T.tool_discovery_nudge_section(BESKED)
    assert "calendar_create_event" in ud
    assert 'load_more_tools(names=["calendar_create_event"])' in ud


def test_praecis_paa_taersklen_er_med(monkeypatch):
    """Spec'en vælger >= (ikke >). Testen låser det."""
    _stub(monkeypatch, [("calendar_create_event", T._THRESHOLD)])
    assert "calendar_create_event" in T.tool_discovery_nudge_section(BESKED)


def test_kun_eet_nudge_selv_med_fire_staerke_matches(monkeypatch):
    _stub(monkeypatch, [
        ("calendar_create_event", 0.93), ("mail_send", 0.92),
        ("drive_upload", 0.91), ("contacts_lookup", 0.90),
    ])
    monkeypatch.setattr(
        T, "_registrerede_navne",
        lambda: {"calendar_create_event", "mail_send", "drive_upload", "contacts_lookup"},
    )
    ud = T.tool_discovery_nudge_section(BESKED)
    assert ud.count("load_more_tools") == 1
    assert "mail_send" not in ud
    assert len(ud.splitlines()) <= 3


def test_naestbedste_bruges_naar_det_bedste_er_undertrykt(monkeypatch):
    monkeypatch.setattr(T, "_undertrykt", lambda sid, navn: navn == "calendar_create_event")
    monkeypatch.setattr(T, "_registrerede_navne", lambda: {"calendar_create_event", "mail_send"})
    _stub(monkeypatch, [("calendar_create_event", 0.93), ("mail_send", 0.88)])
    assert "mail_send" in T.tool_discovery_nudge_section(BESKED, "s1")


def test_manglende_session_id_giver_stadig_et_nudge(monkeypatch):
    """Suppression kan ikke køre uden session — men vi degraderer ikke til tavshed."""
    monkeypatch.undo()
    monkeypatch.setattr(T, "_enabled", lambda: True)
    monkeypatch.setattr(T, "_er_prewarm", lambda sid: False)
    monkeypatch.setattr(T, "_katalog_tekst", lambda: "")
    monkeypatch.setattr(T, "_registrerede_navne", lambda: {"calendar_create_event"})
    monkeypatch.setattr(T, "_log_nudge", lambda navn, sid, score: None)
    _stub(monkeypatch, [("calendar_create_event", 0.91)])
    assert "calendar_create_event" in T.tool_discovery_nudge_section(BESKED, "")


def test_nudget_skriver_en_event_saa_det_kan_maales(monkeypatch):
    """Uden fase-1-logging kan hverken konvertering eller falsk-positiv måles."""
    set_events: list[tuple] = []
    monkeypatch.setattr(T, "_log_nudge", lambda navn, sid, score: set_events.append((navn, sid, score)))
    _stub(monkeypatch, [("calendar_create_event", 0.91)])
    T.tool_discovery_nudge_section(BESKED, "s1")
    assert set_events == [("calendar_create_event", "s1", 0.91)]


def test_nudget_huskes_saa_det_ikke_gentages(monkeypatch):
    husket: list[tuple] = []
    monkeypatch.setattr(T, "_husk_nudge", lambda sid, navn: husket.append((sid, navn)))
    _stub(monkeypatch, [("calendar_create_event", 0.91)])
    T.tool_discovery_nudge_section(BESKED, "s1")
    assert husket == [("s1", "calendar_create_event")]


def test_observationsflade_fortaeller_hvad_der_skete(monkeypatch):
    _stub(monkeypatch, [("calendar_create_event", 0.91)])
    f = T.build_tool_discovery_nudge_surface(BESKED, "s1")
    assert f["matched"] is True and f["active"] is True
    assert f["skipped_short"] is False
    assert f["threshold"] == T._THRESHOLD


def test_observationsflade_paa_kort_besked(monkeypatch):
    _maa_ikke_slaa_op(monkeypatch)
    f = T.build_tool_discovery_nudge_surface("hej", "s1")
    assert f["skipped_short"] is True and f["matched"] is False


def test_session_id_none_lekker_ikke_ind_i_eventen(monkeypatch):
    """prompt-assembly sender session_id=None på ture uden session."""
    set_events: list[tuple] = []
    monkeypatch.setattr(T, "_log_nudge", lambda navn, sid, score: set_events.append((navn, sid)))
    _stub(monkeypatch, [("calendar_create_event", 0.91)])
    ud = T.tool_discovery_nudge_section(BESKED, None)
    assert "calendar_create_event" in ud
    assert set_events == [("calendar_create_event", "")]


# ---------------------------------------------------------------------------
# Integration med prompt-assembly
# ---------------------------------------------------------------------------


def test_nudget_ligger_i_den_VOLATILE_hale(monkeypatch):
    """I det stabile præfiks ville et per-tur-nudge bryde cachen på HVER tur.

    Samme form som tests/test_env_block.py — den eneste måde at bevise
    cache-sikkerheden er at bygge prompten og se HVOR teksten lander.
    """
    from core.services.prompt_contract import (
        DYNAMIC_TAIL_SENTINEL,
        build_visible_chat_prompt_assembly,
    )

    monkeypatch.setattr(T, "_enabled", lambda: True)
    monkeypatch.setattr(T, "_er_prewarm", lambda sid: False)
    monkeypatch.setattr(T, "_katalog_tekst", lambda: "")
    monkeypatch.setattr(T, "_registrerede_navne", lambda: {"calendar_create_event"})
    monkeypatch.setattr(T, "_undertrykt", lambda sid, navn: False)
    monkeypatch.setattr(T, "_husk_nudge", lambda sid, navn: None)
    monkeypatch.setattr(T, "_log_nudge", lambda navn, sid, score: None)
    monkeypatch.setattr(T, "_matches", lambda besked: [("calendar_create_event", 0.91)])

    a = build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash",
        user_message=BESKED, session_id="_default")
    i_sent = a.text.find(DYNAMIC_TAIL_SENTINEL)
    i_nudge = a.text.find("calendar_create_event")
    if i_nudge < 0:
        pytest.skip("nudgen slukket i dette miljø (sektion-override eller kill-switch)")
    assert i_sent > 0
    assert i_nudge > i_sent, "nudget FØR markøren ville brække prefix-cachen"


def test_default_stien_giver_tom_streng_ved_timeout():
    """_timed_result(..., default="") → sektionen forsvinder, assembly er uændret."""
    from core.services.prompt_contract import _phase_timeout  # noqa: F401 (findes)

    # Kontrakten vi læner os op ad: en future der ikke når frem, giver default.
    # Her verificeres selve default-værdien vi registrerer sektionen med.
    import inspect
    from core.services import prompt_contract as PC
    kilde = inspect.getsource(PC._build_visible_chat_prompt_assembly_impl)
    assert '_timed_result(future_tool_discovery, "tool_discovery_nudge", default="")' in kilde


def test_eventen_publiceres_med_det_navn_maalingen_soeger_paa(monkeypatch):
    """SELECT ... WHERE kind LIKE 'tool_discovery%' er målingen i spec'en —
    så navnet er en kontrakt, ikke en detalje."""
    # Grund-fixturen patcher _log_nudge til en no-op — den skal væk her, ellers
    # tester vi attrappen i stedet for den ægte funktion.
    monkeypatch.undo()
    set_kald: list[tuple] = []
    from core.eventbus import bus as B
    monkeypatch.setattr(
        B.event_bus, "publish",
        lambda kind, payload: set_kald.append((kind, payload)),
    )

    T._log_nudge("calendar_create_event", "s1", 0.9137)
    assert set_kald[0][0] == "tool_discovery.nudge"
    assert set_kald[0][1] == {
        "tool": "calendar_create_event", "session_id": "s1", "score": 0.9137,
    }


def test_sektionen_er_registreret_under_en_label_der_kan_slukkes_live():
    """_awareness_add gater på label via central_switches (scope prompt_section)."""
    import inspect
    from core.services import prompt_contract as PC
    kilde = inspect.getsource(PC._build_visible_chat_prompt_assembly_impl)
    assert '"tool discovery nudge"' in kilde


def test_default_er_SLUKKET_indtil_sprog_spoergsmaalet_er_afgjort(monkeypatch):
    """Målt 6/9: nomic-embed-text er engelsk-centrisk, Bjørn skriver dansk.

    «kalender»-beskeden gav curiosity_read_dreams (0,694) over
    calendar_list_events (0,665). Spec'ens egen regel — støj er værre end ingen
    nudge — afgør sagen, så defaulten er OFF indtil modellen kan dansk.
    """
    monkeypatch.undo()

    class TomConfig:
        extra: dict = {}

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: TomConfig())
    assert T._enabled() is False


def test_ulaeselig_config_giver_ogsaa_slukket(monkeypatch):
    """Self-safe den SIKRE vej: kan vi ikke læse flaget, nudger vi ikke."""
    monkeypatch.undo()

    def eksploder():
        raise RuntimeError("config nede")

    monkeypatch.setattr("core.runtime.settings.load_settings", eksploder)
    assert T._enabled() is False


def test_opslaget_gaar_gennem_sprog_broen(monkeypatch):
    """Uden broen kom curiosity_read_dreams (0,694) før calendar_list_events
    (0,665) på en kalender-besked. Den må ikke kunne fjernes i stilhed."""
    monkeypatch.undo()
    set_query: list[str] = []
    from core.services import tool_embeddings as TE
    monkeypatch.setattr(
        TE, "top_k_similar",
        lambda q, k=8: set_query.append(q) or [("calendar_create_event", 0.91)],
    )
    T._matches("kan du lægge et møde ind i min kalender")
    assert set_query == ["kan du lægge et meeting ind i min calendar"]
