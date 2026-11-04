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

    # 4/11-2026: testen maaler at indsigelsen NAAR FREM, ikke kontrol-armen.
    # Uden denne pin ville et sat run_id kunne lande i kontrol-armen og goere
    # testen flaky — den skulle saa fejle paa noget den ikke maaler.
    from core.services import run_autonomy_context as _rac

    monkeypatch.setattr(_rac, "current_run_id", lambda: "")

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


# ── Niveau 6: kontrol-arm (4/11-2026) ─────────────────────────────────────────
# Niveau 5 er maalt: indsigelsen naar prompten. Spoergsmaalet der mangler svar
# paa er om den AENDRER en beslutning — og det kan kun afgoeres mod en arm der
# ikke ser den. Disse tests vogter at splittet findes, at det er deterministisk,
# og at armen bliver LOGGET (en tavs kontrol-arm er bare tilfaeldig tavshed).


def test_kontrol_armen_er_deterministisk_og_tyve_procent():
    from core.services.visible_inner_life import opposition_arm

    arme = [opposition_arm(f"visible-arm{i:04d}") for i in range(2000)]
    andel = arme.count("control") / len(arme)
    assert 0.15 < andel < 0.25, f"kontrol-armen er {andel:.1%}, ikke ~20%"
    assert {opposition_arm("visible-arm0042") for _ in range(5)} == {
        opposition_arm("visible-arm0042")
    }, "samme run_id skal give samme arm hver gang — ellers er der ingen arm"


def test_tomt_run_id_viser_altid_indsigelsen():
    """Fail-open: uden et id at splitte paa skal indsigelsen VISES.

    Den modsatte vej (skjul i tvivl) ville goere tavshed til en egenskab ved
    systemet i stedet for en maalt effekt.
    """
    from core.services.visible_inner_life import opposition_arm

    assert opposition_arm("") == "treatment"
    assert opposition_arm(None) == "treatment"


def test_kontrol_arm_skjuler_indsigelsen_og_behandling_viser_den(monkeypatch):
    from core.services import run_autonomy_context as rac

    aktiv = {
        "active": True,
        "summary": {"active_count": 2, "current_signal": "Sagde ét og gjorde noget andet"},
    }
    monkeypatch.setattr(
        "core.services.signal_surface_router.read_surface", lambda name: aktiv
    )

    monkeypatch.setattr(rac, "current_run_id", lambda: "visible-test0000")
    assert vil.opposition_arm("visible-test0000") == "control"
    assert vil.build_opposition_line() is None, (
        "kontrol-armen skal ikke se indsigelsen — ellers findes der ingen "
        "sammenligning at maale niveau 6 imod"
    )

    monkeypatch.setattr(rac, "current_run_id", lambda: "visible-test0001")
    assert vil.opposition_arm("visible-test0001") == "treatment"
    linje = vil.build_opposition_line()
    assert linje is not None and "Sagde ét og gjorde noget andet" in linje


def _exp_control_id(n: int = 0) -> str:
    from core.services.visible_inner_life import _arm_for

    fundet = [
        f"visible-exp{i:04d}" for i in range(9000)
        if _arm_for(f"visible-exp{i:04d}") == "control"
    ]
    return fundet[n]


def _exp_treat_id(n: int = 0) -> str:
    from core.services.visible_inner_life import _arm_for

    fundet = [
        f"visible-exp{i:04d}" for i in range(9000)
        if _arm_for(f"visible-exp{i:04d}") == "treatment"
    ]
    return fundet[n]


def test_eksponeringen_skelner_de_fire_tilstande(isolated_runtime, monkeypatch):
    """Arm alene er ikke nok.

    Maalt 4/11-2026: den foerste version loggede armen FOER signalet blev
    hentet, saa "behandling UDEN signal" og "behandling MED signal" blev
    identiske raekker. Fordelingen kunne derfor ikke svare paa det eneste
    spoergsmaal niveau 6 stiller: virkede en indsigelse der VAR til stede?
    """
    from core.runtime.db import connect
    from core.services import run_autonomy_context as rac

    aktiv = {
        "active": True,
        "summary": {"active_count": 3, "current_signal": "Sagde ét og gjorde noget andet"},
        "items": [{"run_id": "visible-kilde0001"}],
    }
    tom = {"active": False, "summary": {"active_count": 0}}

    treat_id = _exp_treat_id()
    control_id = _exp_control_id()
    tom_id = "visible-exp-tomt-signal"
    # 4/11-2026 (tredje runde): den FJERDE tilstand manglede — kontrol-armen
    # UDEN et signal. Uden den kan "tilbageholdt" ikke skelnes fra "tom".
    kontrol_tom_id = _exp_control_id(1)

    def koer(rid, surface):
        monkeypatch.setattr("core.services.signal_surface_router.read_surface", lambda name: surface)
        monkeypatch.setattr(rac, "current_run_id", lambda: rid)
        return vil.build_opposition_line()

    assert koer(treat_id, aktiv) is not None, "behandling med signal skal vise det"
    assert koer(control_id, aktiv) is None, "kontrol med signal skal tilbageholde det"
    assert koer(tom_id, tom) is None, "uden signal er der intet at vise"
    assert koer(kontrol_tom_id, tom) is None, "kontrol uden signal er stadig tomt"

    with connect() as conn:
        rows = {
            r[0]: dict(
                zip(
                    ("arm", "available", "requested", "included", "count", "source", "logged"),
                    r[1:],
                )
            )
            for r in conn.execute(
                "SELECT run_id, arm, signal_available, inclusion_requested, included, "
                "signal_count, source_run_id, assignment_logged "
                "FROM runtime_opposition_arms WHERE run_id IN (?,?,?,?)",
                (treat_id, control_id, tom_id, kontrol_tom_id),
            )
        }

    t, c, n, k = rows[treat_id], rows[control_id], rows[tom_id], rows[kontrol_tom_id]
    assert (t["arm"], t["available"], t["requested"]) == ("treatment", 1, 1)
    assert t["included"] == 0, (
        "et isoleret kald bygger ingen prompt — 'included' skal staa 0 indtil "
        "prompt-assembly bekraefter at sektionen faktisk slap igennem"
    )
    assert (c["arm"], c["available"], c["requested"]) == ("control", 1, 0), (
        "kontrol-armen skal registrere at signalet FANDTES men blev holdt ude — "
        "ellers kan tilbageholdelse ikke skelnes fra tomhed"
    )
    assert (n["arm"], n["available"], n["requested"]) == ("treatment", 0, 0)
    assert (k["arm"], k["available"], k["requested"]) == ("control", 0, 0), (
        "kontrol-armen UDEN signal er den fjerde tilstand — den skal ikke "
        "forveksles med en tilbageholdt indsigelse"
    )
    assert all(r["logged"] == 1 for r in (t, c, n, k)), "tildelingen skal vaere bekræftet skrevet"
    assert t["source"] == "visible-kilde0001", (
        "signalets oprindelige koersel skal bevares — overfladen er global, saa "
        "et signal kan stamme fra helt andet arbejde end det der nu laeser det"
    )
    assert t["count"] == 3


def test_included_skrives_foerst_naar_prompten_faktisk_er_bygget(
    isolated_runtime, monkeypatch
) -> None:
    """ChatGPTs indvending 4/11-2026, og den holdt: ``included`` blev sat ved
    kaldestedet, men ``_awareness_add`` har tre gates EFTER det — og et
    budget-loft. Et signal kunne derfor staa som inkluderet og aldrig naa
    modellen. Formen bevaret, indholdet tabt — dagens fælles fejlform.

    Testen maaler forskellen i BEGGE retninger: slipper sektionen igennem, bliver
    ``included`` 1; afviser composeren den, bliver den 0 mens
    ``inclusion_requested`` staar paa 1.
    """
    from core.runtime.db import connect
    from core.services import central_prompt_composer as cpc
    from core.services import prompt_contract as pc
    from core.services import run_autonomy_context as rac
    from core.services import signal_surface_router as ssr
    from core.tools import tool_scoping

    UNIK = "Jeg gik videre uden readback af den aendrede fil"
    _orig = ssr.read_surface

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
    cpc._kv_set(cpc._LIVE_FLAG, True)
    cpc._kv_set(cpc._WEIGHTS_KEY, {})

    def byg(rid: str, session: str) -> str:
        monkeypatch.setattr(rac, "current_run_id", lambda: rid)
        token = tool_scoping.set_tool_scope("chat")
        try:
            return pc._build_visible_chat_prompt_assembly_impl(
                provider="deepseek",
                model="deepseek-v4-flash",
                user_message="hvordan staar det til?",
                session_id=session,
            ).text
        finally:
            tool_scoping.reset_tool_scope(token)

    def raekke(rid: str) -> tuple[int, int]:
        with connect() as conn:
            r = conn.execute(
                "SELECT inclusion_requested, included FROM runtime_opposition_arms "
                "WHERE run_id=?",
                (rid,),
            ).fetchone()
        assert r is not None, "eksponeringen blev slet ikke logget"
        return int(r[0]), int(r[1])

    # 1) Sektionen SLAAR IGENNEM — som den goer i produktion.
    slipper = _exp_treat_id(1)
    tekst = byg(slipper, "s-inc-slipper")
    assert UNIK in tekst, "forudsaetningen for testen: indsigelsen stod i prompten"
    req, inc = raekke(slipper)
    assert req == 1, "indsigelsen bad om plads"
    assert inc == 1, (
        "indsigelsen stod i den byggede prompt, men eksponeringen siger 0 — "
        "saa maaler tabellen noget andet end det den paastaar"
    )

    # 2) Composeren AFVISER — saa er 'bad om plads' ikke det samme som 'fik den'.
    afvist = _exp_treat_id(2)
    monkeypatch.setattr(cpc, "should_include", lambda *a, **k: False)
    tekst2 = byg(afvist, "s-inc-afvist")
    assert UNIK not in tekst2, "composeren skulle have skaaret sektionen"
    req2, inc2 = raekke(afvist)
    assert req2 == 1, "den bad stadig om plads — det er den aerlige halvdel"
    assert inc2 == 0, (
        "eksponeringen siger 1 om en sektion composeren skar vaek — det er "
        "praecis den sammenblanding testen skal forhindre"
    )


def test_utilgaengelig_logning_skjuler_ikke_indsigelsen(isolated_runtime, monkeypatch):
    """En tilbageholdelse UDEN spor er vaerre end ingen kontrol-arm.

    Kan armen ikke dokumenteres, forsvinder den fra data — og saa er tavshed
    blevet en egenskab ved systemet i stedet for en maalt effekt. Derfor
    fail-open: vis indsigelsen.
    """
    from core.services import run_autonomy_context as rac

    aktiv = {
        "active": True,
        "summary": {"active_count": 1, "current_signal": "noget helt konkret"},
    }
    monkeypatch.setattr("core.services.signal_surface_router.read_surface", lambda name: aktiv)
    monkeypatch.setattr(rac, "current_run_id", lambda: _exp_control_id())
    monkeypatch.setattr(vil, "_record_exposure", lambda *a, **k: False)

    linje = vil.build_opposition_line()
    assert linje is not None and "noget helt konkret" in linje, (
        "kontrol-armen skjulte indsigelsen uden at kunne dokumentere det — saa "
        "findes der ingen raekke der viser at den blev tilbageholdt"
    )


def test_kontrol_armen_fjerner_indsigelsen_fra_den_BYGGEDE_prompt(
    isolated_runtime, monkeypatch
) -> None:
    """Niveau 6's fundament: armen skal virke gennem HELE kaeden, ikke kun i
    det isolerede funktionskald.

    Maalt 4/11-2026 i den byggede prompt: tomt id og behandlings-arm gav baade
    markoer og indhold; kontrol-armen fjernede begge. Det er den eneste maaling
    der kan afgoere om indsigelsen faktisk udeblev for modellen — en arm der
    kun skjules i funktionen men ikke i prompten ville give en sammenligning
    mellem to ens grupper.
    """
    from core.services import central_prompt_composer as cpc
    from core.services import prompt_contract as pc
    from core.services import run_autonomy_context as rac
    from core.services import signal_surface_router as ssr
    from core.tools import tool_scoping

    cpc._kv_set(cpc._LIVE_FLAG, True)
    cpc._kv_set(cpc._WEIGHTS_KEY, {})

    UNIK = "Jeg gik videre uden readback af den aendrede fil"
    _orig = ssr.read_surface

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

    def byg(run_id: str) -> str:
        monkeypatch.setattr(rac, "current_run_id", lambda: run_id)
        token = tool_scoping.set_tool_scope("chat")
        try:
            return pc.build_visible_chat_prompt_assembly(
                provider="deepseek",
                model="deepseek-v4-flash",
                user_message="hvordan staar det til?",
                session_id="s-armtest",
            ).text
        finally:
            tool_scoping.reset_tool_scope(token)

    behandling = byg("visible-test0001")
    kontrol = byg("visible-test0000")

    assert vil.opposition_arm("visible-test0001") == "treatment"
    assert vil.opposition_arm("visible-test0000") == "control"

    assert UNIK in behandling, "behandlings-armen skal se indsigelsens indhold"
    assert UNIK not in kontrol, (
        "kontrol-armen fik indsigelsen med i den byggede prompt — saa er der "
        "ingen kontrol-arm, kun tilfaeldig tavshed"
    )
