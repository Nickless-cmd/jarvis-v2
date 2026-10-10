"""Identiteten skal kunne taelles — og hullet skal kunne ses.

29/9-2026: `tool_router._always_core_set` bygger kernen som «top-N efter kald
de sidste 7 dage», uden bruger- eller rolle-dimension. Den KUNNE ikke faa en:
identiteten laa inde i `arguments`, saa
`json_extract(payload_json, '$._runtime_user_id')` gav None for alle 59.778
kald. Og 63 % af eventene manglede feltet helt.

Begge dele maales her. Den anden er den vigtigste: et manglende id skal staa
som UKENDT og ikke forsvinde, for en taelling hvor to tredjedele falder ud
lyder som et resultat mens den er et hul.
"""
import pytest

from core.tools import tool_call_telemetry as t


def test_identiteten_staar_i_PAYLOADENS_ROD_ikke_kun_i_argumenterne():
    """Selve fejlen: rangeringen laeser roden, og der stod intet."""
    p = t.byg_payload("bash", {
        "_runtime_user_id": "1246415163603816499",
        "_runtime_session_id": "chat-abc",
        "_runtime_turn_id": "visible-def",
        "command": "ls",
    })
    assert p["user_id"] == "1246415163603816499"
    assert p["session_id"] == "chat-abc"
    assert p["run_id"] == "visible-def"
    assert p["tool"] == "bash"


def test_feltet_bliver_STAAENDE_i_argumenterne():
    """Elleve steder i kodebasen laeser `_runtime_user_id` derfra. Et flyt
    havde braekket dem; det her er en tilfoejelse."""
    p = t.byg_payload("bash", {"_runtime_user_id": "u1", "command": "ls"})
    assert p["arguments"]["_runtime_user_id"] == "u1"


@pytest.mark.parametrize("args,ventet", [
    ({}, {"user_id": t.UKENDT, "session_id": t.UKENDT, "run_id": t.UKENDT}),
    ({"_runtime_user_id": ""}, {"user_id": t.UKENDT, "session_id": t.UKENDT, "run_id": t.UKENDT}),
    ({"_runtime_user_id": "  "}, {"user_id": t.UKENDT, "session_id": t.UKENDT, "run_id": t.UKENDT}),
    ({"_runtime_user_id": "u1"}, {"user_id": "u1", "session_id": t.UKENDT, "run_id": t.UKENDT}),
])
def test_et_manglende_id_bliver_UKENDT_og_ikke_udeladt(args, ventet, monkeypatch):
    """Hele tabellen, ikke ét felt — og tom/whitespace taeller som manglende.

    Uden kontekst maa der ikke opstaa et id ud af ingenting, saa contextvar'en
    slaas fra her; dens egen vej maales i testen nedenfor."""
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: None, raising=False)
    assert t.identitet(args) == ventet


def test_bro_kald_uden_argument_henter_brugeren_fra_KONTEKSTEN(monkeypatch):
    """Desk' `operator_bash` gaar uden om `simple_tool_executor`, som er den
    der normalt haefter id'et paa. Var contextvar'en sat, er svaret rigtigt —
    og det var 63 % af eventene der manglede feltet."""
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: "fra-konteksten", raising=False)
    assert t.identitet({"command": "ls"})["user_id"] == "fra-konteksten"


def test_argumentet_i_args_VINDER_over_konteksten(monkeypatch):
    """Executoren ved hvem der kalder i det run; konteksten kan vaere en anden
    traad. Rækkefølgen skal vaere entydig."""
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: "forkert", raising=False)
    assert t.identitet({"_runtime_user_id": "rigtig"})["user_id"] == "rigtig"


def test_argumenterne_afkortes_stadig_ved_100_tegn():
    """Graensen er BEVARET ved udskillelsen. En udskillelse der aendrer adfaerd
    er ikke en udskillelse."""
    p = t.byg_payload("bash", {"command": "x" * 500})
    assert len(p["arguments"]["command"]) == 100


def test_udgivelsen_maa_ALDRIG_braekke_et_vaerktoejskald(monkeypatch):
    """Telemetri er ikke vigtigere end arbejdet. En doed bus skal koste et
    event, ikke kaldet.

    METODEN lappes, ikke singletonen: `tests/test_event_bus_singleton_maa_ikke
    _udskiftes.py` bevogter netop det — et modul der importeres foerste gang
    mens en attrap staar der, binder attrappen for altid."""
    import core.eventbus.bus as bus
    def doed(*a, **k): raise RuntimeError("bussen er nede")
    monkeypatch.setattr(bus.event_bus, "publish", doed, raising=False)
    t.udgiv_tool_invoked("bash", {"command": "ls"})   # maa ikke rejse


def test_eventet_naar_faktisk_ud_paa_bussen(monkeypatch):
    """De andre tests maaler `byg_payload`. Denne beviser at `udgiv_` KALDER
    den — at fjerne kaldet lod dem alle bestaa."""
    set_kald = []
    import core.eventbus.bus as bus
    monkeypatch.setattr(bus.event_bus, "publish",
                        lambda kind, payload: set_kald.append((kind, payload)),
                        raising=False)
    t.udgiv_tool_invoked("bash", {"_runtime_user_id": "u9", "command": "ls"})
    assert len(set_kald) == 1
    kind, payload = set_kald[0]
    assert kind == "tool.invoked"
    assert payload["user_id"] == "u9"
    assert payload["tool"] == "bash"


# ── tool.completed skal kunne parres med sit kald (3/10-2026) ───────────────

def test_completed_baerer_run_og_kald_id_saa_parringen_kan_lade_sig_goere():
    """Frem til 3/10-2026 bar `tool.completed` kun `{tool, status, mutating}`.

    Et panel der skal vise «hvad kører lige nu» kunne derfor ikke se forskel
    på et kald der var i gang og et der var færdigt — uden at gætte ud fra
    rækkefølgen. Det gæt fejler netop når to kald af samme værktøj går i
    samme runde, hvilket er reglen snarere end undtagelsen.

    Felterne løftes fra `arguments`, hvor `simple_tool_executor` allerede
    hæfter dem. Det er en løftning, ikke en ny måling."""
    p = t.byg_completed_payload("bash", "ok", {
        "_runtime_turn_id": "visible-abc",
        "_runtime_tool_use_id": "toolu_01XYZ",
        "command": "npm test",
    })
    assert p["run_id"] == "visible-abc"
    assert p["tool_use_id"] == "toolu_01XYZ"
    assert p["status"] == "ok"


def test_completed_fra_et_UI_kald_har_TOMME_felter_ikke_gaettede():
    """Desk' egne bro-kald går gennem `execute_tool` uden om executoren og
    bærer hverken run eller kald-id. Tomt er den ærlige beskrivelse; et
    opdigtet id ville parre kaldet med noget der ikke hører til det."""
    p = t.byg_completed_payload("operator_bash", "ok", {"command": "ls"})
    assert p["run_id"] == ""
    assert p["tool_use_id"] == ""


# ── Exit-koden persisteres så detektoren kan måles BAGUD (10/10-2026) ───────

def test_completed_baerer_exit_kode_og_kommando_for_shell_vaerktoejer():
    """`tool.completed` bar ikke exit-koden, så Smiths tavse-kæde-detektor
    kunne kun måles i NUET — den findes kun i `result` og blev smidt væk ved
    udgivelsen. Uden den i `events` har «hvor ofte knækker mine kæder?» intet
    svar bagud. Kommandoen gemmes med, fordi detektoren er en REN funktion af
    (kommando, exit-kode): med begge dele kan historikken afspilles."""
    p = t.byg_completed_payload(
        "bash", "ok", {"command": "cd x && grep -c foo bar"},
        {"exit_code": 1, "status": "ok"},
    )
    assert p["exit_code"] == 1
    assert p["command"] == "cd x && grep -c foo bar"


def test_exit_kode_NUL_gemmes_den_er_et_gyldigt_svar():
    """0 er den vigtigste værdi at have med — den er beviset for at kæden
    kørte hele vejen. Derfor `is not None`, ikke en sandhedstest."""
    p = t.byg_completed_payload(
        "bash", "ok", {"command": "true"}, {"exit_code": 0},
    )
    assert p["exit_code"] == 0


def test_ikke_shell_vaerktoej_faar_hverken_exit_kode_eller_kommando():
    """`read_file` bærer ingen exit-kode. Feltet må ikke opstå af ingenting —
    et gættet exit_code ville forurene enhver bagud-måling."""
    p = t.byg_completed_payload(
        "read_file", "ok", {"path": "/x"}, {"exit_code": 1, "content": "…"},
    )
    assert "exit_code" not in p
    assert "command" not in p


def test_kommandoen_klippes_ved_graensen():
    """En rigtig kommando er 200-400 tegn. `tool.invoked` klipper ved 100,
    hvilket er for kort til at afgøre kæde-strukturen — her klippes ved 400."""
    p = t.byg_completed_payload(
        "bash", "ok", {"command": "x" * 900}, {"exit_code": 1},
    )
    assert len(p["command"]) == t.COMMAND_GRAENSE


def test_uden_result_er_payloaden_uændret():
    """Bagud-kompatibel: kaldes funktionen uden `result` (fx fra en ældre
    kalder), er formen præcis som før."""
    p = t.byg_completed_payload("bash", "ok", {"command": "ls"})
    assert "exit_code" not in p
    assert "command" not in p


def test_operator_bash_er_med_i_shell_familien():
    """`operator_bash` er også et shell-kald med en exit-kode — og i drift er
    den langt det største antal. Uden den i familien ville bagud-målingen se
    4 % af mine shell-kald."""
    assert "operator_bash" in t.SHELL_TOOLS
    p = t.byg_completed_payload(
        "operator_bash", "ok", {"command": "ls && rm x"}, {"exit_code": 2},
    )
    assert p["exit_code"] == 2


# ── Interne kald: systemets egen trafik observeres ikke (10/10-2026) ─────────
#
# Job-pollen er ikke et vaerktoejskald. Den er panelets puls, og alligevel gik
# hvert poll gennem hele observations-laget. Maalt: 34.079 events i doegnet =
# 59 % af hele begivenhedsstroemmen, fra 11.351 kald.

def test_internt_kald_er_per_kontekst_og_nulstilles():
    """Flaget maa ikke laekke: efter blokken er vi tilbage til normale kald."""
    assert t.er_internt_kald() is False
    with t.internt_kald():
        assert t.er_internt_kald() is True
    assert t.er_internt_kald() is False


def test_internt_kald_skriver_ingen_tool_events(monkeypatch):
    """Kontrakten maalt direkte: et internt kald udgiver INTET i tool-laget."""
    from core.services import outcome_learning as ol
    from core.services import silent_chain_break as scb
    from core.tools import simple_tools as st
    from core.tools import tool_call_observation as obs

    spor: list[str] = []

    class _FakeBus:
        def publish(self, kind, payload):
            spor.append(kind)

    monkeypatch.setitem(st._TOOL_HANDLERS, "_probe", lambda args: {"status": "ok"})
    monkeypatch.setattr(st, "event_bus", _FakeBus())
    monkeypatch.setattr(st, "udgiv_tool_invoked", lambda n, a: spor.append("invoked"))
    monkeypatch.setattr(
        st, "_record_tool_outcome_memory", lambda *a, **k: spor.append("memory"))
    monkeypatch.setattr(obs, "observe_tool_call", lambda *a, **k: spor.append("observe"))
    monkeypatch.setattr(ol, "record_outcome", lambda **k: None)
    monkeypatch.setattr(scb, "observe", lambda *a, **k: None)

    st.execute_tool("_probe", {})  # et normalt kald observeres
    assert "invoked" in spor and "observe" in spor, spor

    spor.clear()
    with t.internt_kald():
        st.execute_tool("_probe", {})  # systemets eget kald — usynligt
    assert spor == [], f"et internt kald skrev alligevel: {spor}"
