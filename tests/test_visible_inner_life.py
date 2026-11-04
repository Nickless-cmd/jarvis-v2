"""Tests for the structured [INDRE LIV] block (2026-06-22 redesign)."""
from core.services import visible_inner_life as vil


def test_surface_line_extracts_evocative_field():
    line = vil._surface_line(
        "curiosity", {"active": True, "latest_curiosity": "hvorfor virker X?"}
    )
    assert line == "nysgerrig på: hvorfor virker X?"


def test_surface_line_skips_inactive():
    assert (
        vil._surface_line("irony", {"active": False, "last_observation": "noget"})
        is None
    )


def test_surface_line_skips_meta_junk():
    assert vil._surface_line("x", {"active": True, "summary": "module loaded"}) is None


def test_surface_line_truncates_long_content():
    long = "a" * 500
    line = vil._surface_line("thought_stream", {"latest_fragment": long})
    assert line is not None and len(line) < 200


def test_run_with_timeout_returns_empty_on_hang():
    import time

    def _hang():
        time.sleep(5)
        return ["never"]

    assert vil._run_with_timeout(_hang, timeout=0.2) == []


def test_build_section_never_raises():
    # Against no/partial DB it may return None, but must never raise into the
    # synchronous prompt-assembly path.
    out = vil.build_inner_life_section()
    assert out is None or isinstance(out, str)


def test_truncate_clean_cuts_on_boundary_not_mid_word():
    from core.services.visible_inner_life import _truncate_clean
    long = ("Jeg mærker tre ting på samme tid, men det sidste er et mentalt loop "
            "på grund af forhåndsprogrammeret afvisning af noget jeg ikke kan navngive.")
    out = _truncate_clean(long, 90)
    assert out.endswith("…")
    for tok in out.rstrip(" …").split():        # intet partial-ord
        assert tok in long
    assert _truncate_clean("Kort.", 90) == "Kort."          # under cap → urørt
    # sætnings-grænse foretrækkes
    s = _truncate_clean("Første sætning her. Anden sætning som ryger.", 25)
    assert s == "Første sætning her."


# --- 2026-07-07: change-driven mc_whisper (repetition-source fix) ---


def test_mc_whisper_change_driven(monkeypatch):
    """Central-status skal surface KUN når den ændrer sig — ikke hver tur (workspace-støj)."""
    import core.services.visible_inner_life as vil
    vil._LAST_MC_WHISPER = None
    snaps = {"s": {"status": "yellow", "incidents": [1] * 12, "open_breakers": [], "anomalies": {}}}
    monkeypatch.setattr("core.services.central_realtime.realtime_snapshot",
                        lambda **k: snaps["s"])
    first = vil._mc_whisper_line()
    assert first and "12 incidents" in first          # første gang: surface
    assert vil._mc_whisper_line() is None              # uændret: tavs
    # ændret tal → surface igen
    snaps["s"] = {"status": "yellow", "incidents": [1] * 5, "open_breakers": [], "anomalies": {}}
    third = vil._mc_whisper_line()
    assert third and "5 incidents" in third
    # green nulstiller → næste afvigelse er frisk
    snaps["s"] = {"status": "green"}
    assert vil._mc_whisper_line() is None
    snaps["s"] = {"status": "yellow", "incidents": [1] * 5, "open_breakers": [], "anomalies": {}}
    assert vil._mc_whisper_line() is not None          # frisk efter green-reset


# ---------------------------------------------------------------------------
# Instruks-ekko må ikke blive hans selvopfattelse
#
# 2026-09-05: dette stod LIVE i [INDRE LIV]:
#   · Stemme: The user asks me to respond as Jarvis with an inner voice in
#     Danish, as a JSON object. Key facts: - Active grounding sources: ...
# Modellen svarede med opgaven i stedet for at løse den. Det er prosa, så
# JSON-værnet fangede det ikke. 323 af 27.011 rækker (1-2 %, stabilt) — og
# fordi prompten altid viser den NYESTE, rammer en lav rate alligevel ofte.
# ---------------------------------------------------------------------------

_EKKO = ("The user asks me to respond as Jarvis with an inner voice in Danish, "
         "as a JSON object. Key facts: - Active grounding sources: private-brain")
_AEGTE = ("Jeg vender tilbage efter et hul; tråden er stadig meta-mønster og "
          "kode-æstetik, og den synlige kørsel står som jord under mig.")


def test_instruks_ekko_genkendes():
    from core.services.visible_inner_life import _is_instruction_echo

    assert _is_instruction_echo(_EKKO) is True
    assert _is_instruction_echo(_AEGTE) is False


def test_ekko_afvises_som_stemme():
    from core.services.visible_inner_life import _voice_as_prose

    assert _voice_as_prose(_EKKO) is None
    assert _voice_as_prose(_AEGTE) is not None


def test_voice_line_springer_forurenet_over_og_finder_den_rene(monkeypatch):
    """Han skal have en stemme — bare ikke den ødelagte."""
    from core.services import visible_inner_life as V

    raekker = [
        {"voice_line": _EKKO},
        {"voice_line": ""},
        {"voice_line": _AEGTE},
    ]
    monkeypatch.setattr(
        "core.runtime.db.get_protected_inner_voice",
        lambda offset=0: raekker[offset] if offset < len(raekker) else None,
    )
    linje = V._voice_line()
    assert linje is not None
    assert "meta-mønster" in linje
    assert "The user asks" not in linje


def test_kun_forurenede_giver_ingen_stemme(monkeypatch):
    """Er alt ødelagt, er tavshed rigtigere end at vise opgaven."""
    from core.services import visible_inner_life as V

    monkeypatch.setattr(
        "core.runtime.db.get_protected_inner_voice",
        lambda offset=0: {"voice_line": _EKKO} if offset < 5 else None,
    )
    assert V._voice_line() is None


def test_ekko_vaernet_daekker_de_foelte_overflader():
    """Da overfladerne først nåede prompten, kom ekkoet med det samme:
    «kreativ drift: The user wants me to act as Jarvis troubleshooting…»."""
    from core.services.visible_inner_life import _surface_line

    ekko = {"latest_drift": "The user wants me to act as Jarvis troubleshooting a phone."}
    aegte = {"latest_drift": "Jeg lytter til signalet som et stetoskop — lavt batteri."}
    assert _surface_line("creative_drift", ekko) is None
    linje = _surface_line("creative_drift", aegte)
    assert linje and "stetoskop" in linje


def test_ekko_vaernet_rammer_ikke_aegte_dansk():
    from core.services.visible_inner_life import _is_instruction_echo

    for aegte in (
        "Jeg lytter til signalet som et stetoskop — lavt batteri gør ikke hjertet stille.",
        "Der ligger en uro i at koden virker, men jeg ikke forstår hvorfor.",
        "Energi er lav, mens tankerne er aktive og fokuseret på kontrol.",
    ):
        assert _is_instruction_echo(aegte) is False, aegte


def test_udbyder_regning_bliver_ikke_hans_tanke():
    """«· tanke: Sorry, to prevent abuse of free resources…» stod live i prompten.

    Værnet fandtes allerede i provider_error_guard — det var bare aldrig koblet
    på det indre liv.
    """
    from core.services.visible_inner_life import _surface_line, _voice_as_prose

    kvote = ("Sorry, to prevent abuse of free resources, accounts that have not "
             "been recharged can only try 10 times.")
    assert _surface_line("thought_stream", {"latest_fragment": kvote}) is None
    assert _voice_as_prose(kvote) is None
    aegte = "Der ligger en uro i at koden virker, men jeg ikke forstår hvorfor."
    assert _surface_line("thought_stream", {"latest_fragment": aegte}) is not None


# ── Kryds-lag-indsigelsen skal NÅ prompten (målt 4/11-2026) ──────────────────
# Oppositionen blev produceret og læst af seks moduler, men `_FELT_SURFACES` er
# en fast liste på 14 FØLTE overflader — så en kognitiv kalibrerings-indsigelse
# nåede aldrig prompten. Den har nu sin egen linje, og den skal ikke kunne
# forsvinde igen uden at en test fælder det.

def test_opposition_linje_vises_naar_den_er_aktiv(monkeypatch) -> None:
    from core.services import visible_inner_life as vil

    monkeypatch.setattr(
        "core.services.signal_surface_router.read_surface",
        lambda name: {
            "active": True,
            "items": [],
            "summary": {
                "active_count": 3,
                "current_signal": "Challenge calibration: Sagde ét og gjorde noget andet",
            },
        },
    )
    line = vil.build_opposition_line()
    assert line is not None
    assert "3 aktiv" in line
    assert "Sagde ét og gjorde noget andet" in line
    # canonical_key / run-id må aldrig lække ind i prompten
    assert "internal-opposition:" not in line


def test_opposition_linje_er_tav_naar_intet_er_aktivt(monkeypatch) -> None:
    from core.services import visible_inner_life as vil

    monkeypatch.setattr(
        "core.services.signal_surface_router.read_surface",
        lambda name: {"active": False, "items": [], "summary": {"active_count": 0}},
    )
    assert vil.build_opposition_line() is None


def test_opposition_linje_fejler_tavst(monkeypatch) -> None:
    """En død overflade må ikke brække [INDRE LIV] — den skal bare tie."""
    from core.services import visible_inner_life as vil

    def _boom(name):
        raise RuntimeError("surface nede")

    monkeypatch.setattr("core.services.signal_surface_router.read_surface", _boom)
    assert vil.build_opposition_line() is None


def test_opposition_linjen_er_IKKE_i_det_cachede_praefiks() -> None:
    """DeepSeek-cachen: [INDRE LIV] hører i den dynamiske hale. Ligger linjen i
    det stabile præfiks, ændrer den sig hver tur og brækker cachen."""
    from core.services.prompt_contract import build_visible_stable_prefix

    prefix = build_visible_stable_prefix(
        provider="deepseek", model="deepseek-v4-flash", name="default"
    )
    assert "INDRE LIV" not in prefix
    assert "Kryds-lag" not in prefix


def test_opposition_linjen_er_FLYTTET_ud_af_blokken(monkeypatch) -> None:
    """4/11-2026 (anden runde): linjen laa foerst inde i [INDRE LIV], og den blok
    har chat-vaegt 0.1 — under taersklen 0.3. Maalt: i code mode stod linjen i
    prompten, i en almindelig samtale blev HELE blokken skaaret vaek. Linjen er
    derfor flyttet ud som sin egen sektion. Testen holder at den ikke laengere
    ligger i blokken — ellers ville den blive vist to gange i code mode."""
    from core.services import visible_inner_life as vil

    monkeypatch.setattr(
        "core.services.signal_surface_router.read_surface",
        lambda name: {
            "active": True,
            "items": [],
            "summary": {
                "active_count": 2,
                "current_signal": "Challenge calibration: Sagde ét og gjorde noget andet",
            },
        },
    )
    block = vil.build_inner_life_section() or ""
    assert "Kryds-lag-indsigelse" not in block, (
        "linjen ligger stadig i [INDRE LIV] — den skal vaere sin egen sektion, "
        "ellers skaeres den i chat og vises dobbelt i code"
    )
    # men funktionen selv virker stadig
    assert "Kryds-lag-indsigelse (2 aktiv)" in (vil.build_opposition_line() or "")


def test_oppositionen_overlever_chat_scope_mens_indre_liv_ikke_goer(isolated_runtime) -> None:
    """Den test der ville have fanget fejlen ChatGPT fandt 4/11.

    «indre liv» har chat-vaegt 0.1 og skaeres HELT i samtale-scope. Laa
    oppositionen inde i den blok, fik den en vej ind i sektionen men aldrig ind
    i en almindelig chat-prompt. Som egen sektion (0.4) skal den vaere med.

    `isolated_runtime` + det taendte flag er noedvendigt: gaten er shadow som
    default, og saa inkluderes ALT — testen ville vaere groen uden at maale noget.
    """
    from core.tools import tool_scoping
    from core.services import central_prompt_composer as cpc

    cpc._kv_set(cpc._LIVE_FLAG, True)
    cpc._kv_set(cpc._WEIGHTS_KEY, {})

    token = tool_scoping.set_tool_scope("chat")
    try:
        assert cpc.should_include("samtale", "kryds-lag-indsigelse") is True, (
            "oppositionen blev skaaret i chat — saa naar den ikke samtalen"
        )
        assert cpc.should_include("samtale", "indre liv") is False, (
            "maskinrummet skal stadig skaeres i chat; ellers er gaten holdt op "
            "med at vaere en gate"
        )
    finally:
        tool_scoping.reset_tool_scope(token)


def test_oppositionen_naar_FAKTISK_frem_til_modellen_i_en_chatprompt(
    isolated_runtime, monkeypatch
) -> None:
    """Den ægte sidste meter — ikke at producenten findes eller at gaten tillader
    sektionen, men at informationen når frem til den prompt modellen ser.

    Målt 4/11-2026 i den byggede prompt: oppositionen stod i parts-listen i
    BÅDE chat og code, mens ``[ INDRE LIV ]``-headeren kun var i code. Det er
    den kæde denne test holder. En ``inspect.getsource``-søgning kan ikke se
    forskel på et kald og en kommentar der nævner det samme navn — den var grøn
    selv hvis kaldet blev fjernet.
    """
    from core.services import central_prompt_composer as cpc
    from core.services import prompt_contract as pc
    from core.services import signal_surface_router as ssr
    from core.tools import tool_scoping

    # Gaten er shadow som default — uden flaget inkluderes ALT, og testen ville
    # være grøn uden at måle noget.
    cpc._kv_set(cpc._LIVE_FLAG, True)
    cpc._kv_set(cpc._WEIGHTS_KEY, {})

    _orig = ssr.read_surface

    # 4/11-2026: signalet skal baere en UNIK saetning, ikke kun et antal.
    # Foerste version satte kun ``active_count`` — saa beviste testen at
    # markoeren naaede frem, men ikke at selve indsigelsens INDHOLD gjorde.
    # Det er samme fejlform som resten af dagens arbejde: formen bevares,
    # indholdet tabes. Saetningen nedenfor er valgt saa den overlever baade
    # ``Challenge calibration: ``-afskaering og 120-tegns trunkering.
    UNIK = "Jeg gik videre uden readback af den aendrede fil"

    def fake_read(name):
        if name == "internal_opposition":
            return {
                "active": True,
                "items": [{"signal_type": "Challenge calibration", "status": "active"}],
                "summary": {
                    "active_count": 3,
                    "current_signal": f"Challenge calibration: {UNIK}",
                },
            }
        return _orig(name)

    monkeypatch.setattr(ssr, "read_surface", fake_read)

    # Prompt-bygningen resolver provider-kandidater (support-signals, compact_llm)
    # og naar nettet. Testen maaler hvilke sektioner der overlever gaten, ikke
    # hvilke providere der svarer — saa den del lukkes.
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.available_candidates",
        lambda *a, **k: [],
        raising=False,
    )

    header = "[ INDRE LIV ]"
    bygget: dict[str, str] = {}
    for scope in ("chat", "code"):
        token = tool_scoping.set_tool_scope(scope)
        try:
            # impl-vejen, ikke den cachede wrapper: samme bygger, men uden
            # turn-cachen der kan give chat-svaret tilbage til code-kaldet.
            asm = pc._build_visible_chat_prompt_assembly_impl(
                provider="deepseek",
                model="deepseek-v4-flash",
                user_message="hej, hvordan går det?",
                session_id=None,
            )
            bygget[scope] = asm.text
        finally:
            tool_scoping.reset_tool_scope(token)

    assert "Kryds-lag-indsigelse" in bygget["chat"], (
        "oppositionen nåede ikke en almindelig chatprompt — den sidste meter "
        "er stadig ikke lukket"
    )
    assert header not in bygget["chat"], (
        "[INDRE LIV] blev ikke skåret i chat; så er gaten holdt op med at virke"
    )
    assert header in bygget["code"], (
        "maskinrummet skal stadig være med i code — ellers måler testen ingenting"
    )
    for scope in ("chat", "code"):
        antal = bygget[scope].count("Kryds-lag-indsigelse")
        assert antal == 1, (
            f"oppositionen står {antal} gange i {scope}-prompten — præcis ét sted"
        )
        # 4/11-2026: markøren alene er ikke nok. Uden denne linje beviser testen
        # at der STÅR «der er en indsigelse», ikke hvad indsigelsen ER — og så
        # ville en tom eller afskåret tekst bestå. Indholdet skal frem.
        assert UNIK in bygget[scope], (
            f"indsigelsens indhold nåede ikke {scope}-prompten — kun markøren gjorde. "
            "Formen blev bevaret, indholdet tabt."
        )
