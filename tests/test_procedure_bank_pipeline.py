"""procedure_bank feed (LivingNeuron Fase B) — anti-skrald + navngiven optagelse."""
from core.services import procedure_bank_pipeline as pb


def test_feed_skips_too_few_tools(isolated_runtime):
    assert pb.maybe_record_procedure_from_run(session_id="s", tool_calls=["web_search"]) is None


def test_feed_skips_without_topic(isolated_runtime):
    # nok tools men intet meningsfuldt session-topic → skip (undgå støj-procedurer)
    assert pb.maybe_record_procedure_from_run(session_id="no-topic", tool_calls=["a", "b"]) is None


def test_feed_records_named_procedure(isolated_runtime, monkeypatch):
    # med topic + ≥2 distinkte tools → navngiven procedure gemmes
    monkeypatch.setattr(pb, "load_session_topics",
                        lambda sid: [{"label": "netværks-fejlfinding"}], raising=False)
    # load_session_topics importeres lokalt i funktionen → patch kilden
    import core.services.session_topic_tracker as st
    monkeypatch.setattr(st, "load_session_topics", lambda sid: [{"label": "netværks-fejlfinding"}])
    rec = pb.maybe_record_procedure_from_run(session_id="s1", tool_calls=["ping", "traceroute", "ping"])
    assert rec is not None
    assert "netværks-fejlfinding" in rec["name"]
    assert "→" in rec["procedure"]  # tool-sekvens


# ── emne-vagten (13/11-2026) ────────────────────────────────────────────────
# Fixturen er de FAKTISKE 27 navne målt i den ægte base 13/11-2026, ikke
# opdigtede eksempler. De er alle skrald, og de kom alle igennem den gamle
# `if cand:`-kontrol, fordi den kun spurgte om strengen var tom.
_SKRALD_EMNER = [
    "Titel", "Skriv", "Jarvis", "Læse", "Find", "Rapportér", "Genbesøg",
    "Runtime", "Undersøg", "Send", "Sansernes", "Tick", "Fortsætte",
    "Gennemgå", "Tjek", "Trække", "Hent", "Prøv", "date", "VAERKTOEJS",
    "VÆKKEDE", "mark_wakeup_consumed",
    'inbox_done(id="wake-804cdf6c57")',
    'inbox_done(id="wake-3196468e2d")',
    'inbox_done(id="wake-abdaa04db6")',
    "~/dreams/dream-session-{timestamp}.md",
    "core/services/emotional_controls.py:202-207",
]


def test_alle_27_maalte_skraldnavne_afvises():
    """Vagten skal afvise præcis det der blev målt — ikke bare nogle eksempler."""
    gennem_slaaet = [e for e in _SKRALD_EMNER if pb._meningsfuldt_emne(e)]
    assert gennem_slaaet == [], f"disse slap igennem: {gennem_slaaet}"


def test_et_reelt_emne_slipper_igennem():
    """Positiv kontrol: uden den er den negative test tom — en vagt der afviser
    alt ville også bestå testen ovenfor."""
    for emne in ("netværks-fejlfinding", "procedure-banken skrives fuld af skrald",
                 "Undersøg hvorfor rutinerne kører som session"):
        assert pb._meningsfuldt_emne(emne) is True, emne


def test_skrald_emne_giver_INGEN_raekke(isolated_runtime, monkeypatch):
    """Kernen: står der kun skrald i topic-listen, skrives der intet."""
    import core.services.session_topic_tracker as st
    monkeypatch.setattr(st, "load_session_topics",
                        lambda sid: [{"label": "Titel"}, {"label": "Skriv"}])
    assert pb.maybe_record_procedure_from_run(
        session_id="s-skrald", tool_calls=["bash", "read_file"]) is None


def test_foerste_brugbare_emne_vaelges_frem_for_det_foerste(isolated_runtime, monkeypatch):
    """Den gamle kode tog den FØRSTE kandidat uanset kvalitet. Nu skal den gå
    videre til den første der faktisk beskriver en opgave."""
    import core.services.session_topic_tracker as st
    monkeypatch.setattr(st, "load_session_topics", lambda sid: [
        {"label": "Titel"},
        {"label": "inbox_done(id=\"wake-804cdf6c57\")"},
        {"label": "rydde indbakken for doede forslag"},
    ])
    rec = pb.maybe_record_procedure_from_run(
        session_id="s-blandet", tool_calls=["bash", "read_file"])
    assert rec is not None
    assert "rydde indbakken for doede forslag" in rec["name"]


# ── læseren (13/11-2026, tredje runde) ──────────────────────────────────────
# `match_procedures_for_text` havde NUL kaldere i hele træet. Banken blev fyldt
# og vist, men aldrig læst — så `hit_count` kunne per definition ikke stige, og
# kravet `hit_count > 0` i emergence-tælleren var en betingelse intet kunne
# opfylde. Disse tests måler at læseren findes OG at den tæller.


def test_laeseren_giver_none_naar_intet_matcher(isolated_runtime):
    pb.upsert_procedure(name="daglig mail-check", trigger="tjekke mail",
                        procedure="mail_check → notify")
    assert pb.procedures_prompt_section("hvordan bliver vejret i morgen?") is None


def test_laeseren_viser_matchende_rutine(isolated_runtime):
    """Positiv kontrol: uden den er den negative test ovenfor tom — en læser
    der altid svarer None ville også bestå."""
    pb.upsert_procedure(name="daglig mail-check", trigger="tjekke mail",
                        procedure="mail_check → notify")

    tekst = pb.procedures_prompt_section("kan du tjekke mail for mig?")

    assert tekst is not None
    assert "daglig mail-check" in tekst
    assert "mail_check → notify" in tekst


def test_laeseren_taeller_hittet_saa_taelleren_kan_se_brug(isolated_runtime):
    """Kernen i hele rettelsen: efter et kald er `hit_count` > 0.

    Uden dette kunne emergence-tællerens krav aldrig opfyldes — uanset hvor
    mange gange rutinen blev vist. Det var teateret.
    """
    pb.upsert_procedure(name="daglig mail-check", trigger="tjekke mail",
                        procedure="mail_check → notify")
    foer = pb.get_procedure(procedure_name="daglig mail-check")
    assert foer["hit_count"] == 0

    pb.procedures_prompt_section("kan du tjekke mail for mig?")

    efter = pb.get_procedure(procedure_name="daglig mail-check")
    assert efter["hit_count"] == 1
    assert efter["last_triggered_at"], "et hit skal tidsstemples"


def test_tom_besked_giver_ingen_soegning(isolated_runtime):
    """En tom besked må ikke matche alt — ellers steg hit_count af sig selv."""
    pb.upsert_procedure(name="daglig mail-check", trigger="tjekke mail",
                        procedure="mail_check → notify")

    assert pb.procedures_prompt_section("") is None
    assert pb.get_procedure(procedure_name="daglig mail-check")["hit_count"] == 0

