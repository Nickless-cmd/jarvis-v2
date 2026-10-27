from __future__ import annotations

from core.services.run_autonomy_context import reset_autonomous, set_autonomous


def test_autonomous_catalog_hides_agent_and_dispatch_tools():
    from core.tools.simple_tools import get_tool_definitions

    token = set_autonomous(True)
    try:
        names = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    finally:
        reset_autonomous(token)

    assert {"read_file", "search_memory", "remember_this", "goal_create", "todo_add"} <= names
    assert "scout_agent" not in names
    assert "spawn_agent_task" not in names
    assert "dispatch_code_mode_task" not in names
    assert "dispatch_agent" not in names
    assert not any("agent" in name or "dispatch" in name for name in names)
    assert {"bash", "write_file", "operator_bash", "send_ntfy", "mcp", "start_session",
            "web_fetch", "web_search", "schedule_task", "read_archive"}.isdisjoint(names)


def test_autonomous_loaded_tool_cannot_resolve_agent_schema():
    from core.tools.load_more_tools import _tool_load_more_tools

    token = set_autonomous(True)
    try:
        result = _tool_load_more_tools({"names": ["scout_agent"]})
    finally:
        reset_autonomous(token)

    assert result["status"] == "error"
    assert not result.get("tool_definitions")


def test_autonomous_executor_blocks_direct_and_wrapped_agent_calls(monkeypatch):
    from core.services.simple_tool_executor import _prepare_call

    calls = [
        {"function": {"name": "dispatch_agent", "arguments": {}}},
        {"function": {"name": "call_loaded_tool", "arguments": {
            "navn": "scout_agent", "argumenter": {},
        }}},
        {"function": {"name": "bash", "arguments": {"command": "true"}}},
    ]
    token = set_autonomous(True)
    try:
        for call in calls:
            kind, result = _prepare_call(
                call, force=True, run_id="autonomous-test", session_id="auto-test",
                user_message="", controller=None, round_seen=set(), user_present=False,
            )
            assert kind == "result"
            assert result["status"] == "gate_blocked"
            assert result["result"]["gate_type"] == "autonomous_tool_policy"
    finally:
        reset_autonomous(token)


def test_visible_run_keeps_only_contract_agent_creation(isolated_runtime):
    from core.tools.simple_tools import get_tool_definitions
    from core.services.agent_contract_service import set_capability

    set_capability(True, role="owner")
    token = set_autonomous(False)
    try:
        names = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    finally:
        reset_autonomous(token)

    assert "Task" in names
    assert not ({"scout_agent", "spawn_agent_task", "dispatch_code_mode_task",
                 "dispatch_to_claude_code", "task"} & names)


def test_owner_permission_check_cannot_bypass_autonomous_policy():
    from core.tools.tool_scoping import is_tool_allowed

    token = set_autonomous(True)
    try:
        assert is_tool_allowed(role="owner", scope="", name="scout_agent") is False
        assert is_tool_allowed(role="owner", scope="", name="remember_this") is True
    finally:
        reset_autonomous(token)


# ── Delegeret tilladelse pr. oprindelse (10/10-2026) ─────────────────────
#
# Bjørn: «uddelegér tools når du sætter autonome runs og recurring op, så
# autonome runs får kun de tools de behøver». Testene låser at tilladelsen
# følger ORIGIN — og at en ukendt oprindelse aldrig arver en udvidelse.

def _as_origin(origin: str):
    """Sæt autonom-flag + origin; returnér token til oprydning."""
    from core.services.run_autonomy_context import set_run_identity

    token = set_autonomous(True)
    set_run_identity("autonomous-test", origin)
    return token


def _clear_origin() -> None:
    from core.services.run_autonomy_context import set_run_identity

    set_run_identity("", "")


def test_recurring_task_may_send_and_read_runtime():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("recurring")
    try:
        assert is_allowed("send_ntfy") is True
        assert is_allowed("send_discord_dm") is True
        assert is_allowed("web_search") is True
        assert is_allowed("bash") is True
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_unknown_origin_falls_back_to_bundle_alone():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("")
    try:
        assert is_allowed("remember_this") is True
        assert is_allowed("send_ntfy") is False
        assert is_allowed("bash") is False
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_dream_senses_but_does_not_touch_the_world():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("dream")
    try:
        assert is_allowed("look_around") is True
        assert is_allowed("mic_listen") is True
        assert is_allowed("bash") is False
        assert is_allowed("send_ntfy") is False
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_wakeup_may_resume_work_but_not_send_mail():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("wakeup")
    try:
        assert is_allowed("bash") is True
        assert is_allowed("send_webchat_message") is True
        assert is_allowed("write_file") is False
        assert is_allowed("send_discord_dm") is False
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_indbakke_vaekkeren_har_de_vaerktoejer_dens_direktiv_kraever():
    """26/10-2026: `inbox` var klassificeret som vækning, men uden værktøjer.

    `_WAKE_ORIGINS` indeholder «inbox», så politikken REGNEDE den for en
    vækning — men `ORIGIN_TOOLS` havde ingen nøgle, og den faldt derfor til
    bund-sættet: 106 værktøjer og hverken `bash` eller `web_search`.

    Det kostede et rigtigt run. Kl. 17:32 blev en vækning sprunget over fordi
    en tur var aktiv; `inbox_idle_waker` løftede den, og runnet svarede «jeg
    har ikke adgang til tools, systemer eller kommandoer» — fordi dets
    direktiv bad om `ps -eo pid,lstart,cmd` uden at `bash` var bundet.

    Uden denne test kan nøglen forsvinde igen uden at nogen opdager det:
    bund-sættet er stort nok til at se komplet ud.
    """
    from core.tools.autonomous_tool_policy import allowed_tools_for_origin

    vaekning = allowed_tools_for_origin("wakeup")
    indbakke = allowed_tools_for_origin("inbox")

    assert "bash" in indbakke, (
        "inbox mangler bash — dens eget direktiv siger «UDFØR den nu med dine "
        "tools», så politikken forbyder hvad direktivet påbyder"
    )
    assert "web_search" in indbakke
    assert "inbox_done" in indbakke, "posten skal kunne lukke sig selv"
    # De to må ikke drive fra hinanden: begge ER vækninger, og en løftet post
    # skal have præcis samme råderum som den vækning den blev løftet fra.
    assert indbakke == vaekning, (
        f"inbox og wakeup er ikke længere samme sæt: "
        f"inbox-wakeup={sorted(indbakke - vaekning)}, "
        f"wakeup-inbox={sorted(vaekning - indbakke)}"
    )
    # Og den må ikke blive BREDERE end en vækning: en løftet post undersøger og
    # fortæller i sin egen samtale — den skriver ikke filer og sender ikke DM'er.
    assert "write_file" not in indbakke
    assert "send_discord_dm" not in indbakke


def test_de_tre_sidste_autonome_origin_har_de_vaerktoejer_deres_direktiv_kraever():
    """26/10-2026: tre origins startede runs hvis direktiv krævede `bash`.

    Samme fejlklasse som `inbox` samme dag, men fundet ved at måle ALLE
    origins i koden mod `ORIGIN_TOOLS` — ikke ved at vente på endnu et
    tandløst svar. Alle tre faldt til bund-sættet (106 værktøjer, intet
    `bash`), og bund-sættet er stort nok til at se komplet ud:

    * ``scheduled`` — `scheduled_tasks` siger ordret «UDFØR opgaven nu med
      dine tools … så BRUG værktøjet». Målt: 113 fyrede opgaver, og de
      seneste er alle verifikations-opgaver («begge uvicorn-PID'er
      startede», «Tjek desk-release CI»), som kræver `ps`/`git`/`curl`.
    * ``continuation`` — `visible_runs_memory` fyrer den fem sekunder efter
      et run slutter med «Continue without waiting for a reply». Uden `bash`
      kan den ikke fortsætte det den blev startet for.
    * ``agent-completion`` — `agent_message_receipt` leverer en færdig
      agents resultat. Uden `bash` kan runnet ikke efterprøve hvad agenten
      påstod, og byggernes eget ord er ikke et review.

    Uden denne test kan nøglerne forsvinde igen uden at nogen opdager det.
    """
    from core.tools.autonomous_tool_policy import allowed_tools_for_origin

    recurring = allowed_tools_for_origin("recurring")
    wakeup = allowed_tools_for_origin("wakeup")

    planlagt = allowed_tools_for_origin("scheduled")
    fortsaettelse = allowed_tools_for_origin("continuation")
    agent_faerdig = allowed_tools_for_origin("agent-completion")

    # 1) Alle tre skal kunne undersøge. Det er hele grunden til at de findes.
    for navn, saet in (
        ("scheduled", planlagt),
        ("continuation", fortsaettelse),
        ("agent-completion", agent_faerdig),
    ):
        assert "bash" in saet, (
            f"{navn} mangler bash — dens eget direktiv siger «brug værktøjet», "
            f"så politikken forbyder hvad direktivet påbyder"
        )

    # 2) En planlagt opgave er samme KLASSE som en recurring: kalender-drevet,
    #    bestilt af Bjørn, og dens direktiv beder om at rapportere til ham.
    assert planlagt == recurring, (
        f"scheduled og recurring er ikke længere samme sæt: "
        f"scheduled-recurring={sorted(planlagt - recurring)}, "
        f"recurring-scheduled={sorted(recurring - planlagt)}"
    )

    # 3) Fortsættelsen og agent-leverancen er vækningens sæt: de undersøger og
    #    fortæller i en samtale — de handler ikke i verden på egen hånd.
    for navn, saet in (
        ("continuation", fortsaettelse),
        ("agent-completion", agent_faerdig),
    ):
        assert saet == wakeup, (
            f"{navn} og wakeup er ikke længere samme sæt: "
            f"{navn}-wakeup={sorted(saet - wakeup)}, "
            f"wakeup-{navn}={sorted(wakeup - saet)}"
        )

    # 4) Ingen af dem må blive BREDERE end deres opgave: de fyrer AUTOMATISK,
    #    uden at nogen har bedt om netop den kørsel. Skal de skrive, må de sige
    #    det først — ikke gøre det selv.
    for navn, saet in (
        ("scheduled", planlagt),
        ("continuation", fortsaettelse),
        ("agent-completion", agent_faerdig),
    ):
        assert "write_file" not in saet, f"{navn} må ikke skrive filer"
        assert "operator_bash" not in saet, f"{navn} må ikke nå Bjørns maskine"


def test_tilstedevaerelse_aabner_for_ALT_uanset_origin():
    """Origin-saettet er STANDARDEN, ikke en garanti (maalt 26/10-2026).

    Bjoern: «autonomous_tool_policy.py har stadig denne regel: if user_present():
    return True ... hans nye test beviser ikke, at de tre origins aldrig kan faa
    skriveadgang. Den beviser alene, hvad deres autonome standardsaet
    indeholder.»

    Han har ret, og testen ovenfor blev laest som mere end den er. `is_allowed`
    spoerger til tilstedevaerelse FOER den ser paa oprindelsen, saa snart et run
    lander i Bjoerns egen app-samtale mens han er der. Det er et selvstaendigt
    lag bygget 19/10 med hans egne ord («det er en vaekning, ikke et autonomt
    baggrunds-run») - ikke en forglemmelse i origin-tabellen.

    Maalt: presence vender `write_file`, `edit_file`, `operator_bash` og
    `send_discord_dm` fra False til True for ALLE origins. Graensen for HVEM der
    faar saettet ligger altsaa i `presence_for_run` (system-silo? ejerens
    app-kanal? talt for nylig?), ikke her.

    Testen pinner den faktiske adfaerd, saa de to paastande ikke smelter sammen:
    «origin X's standardsaet indeholder ikke write_file» og «origin X kan ikke
    skrive» er IKKE det samme, og kun den foerste er bevist ovenfor.
    """
    from core.services.run_autonomy_context import (
        reset_autonomous, reset_user_present, set_user_present,
    )
    from core.tools.autonomous_tool_policy import is_allowed

    # De to der rammer verden uden for samtalen. `send_discord_dm` er ikke med:
    # den ER i `scheduled`s saet med vilje (den arver `recurring`), saa den kan
    # ikke bruges som bevis paa en graense der ikke findes.
    skrive_og_fjern = ("write_file", "edit_file", "operator_bash")
    alle_fire = (*skrive_og_fjern, "send_discord_dm")

    for origin in ("scheduled", "continuation", "agent-completion"):
        token = _as_origin(origin)
        try:
            tok_p = set_user_present(False)
            try:
                for navn in skrive_og_fjern:
                    assert is_allowed(navn) is False, (
                        f"{origin} slap {navn} igennem UDEN tilstedevaerelse"
                    )
            finally:
                reset_user_present(tok_p)

            tok_p = set_user_present(True)
            try:
                for navn in alle_fire:
                    assert is_allowed(navn) is True, (
                        f"{origin} blev naegtet {navn} MED tilstedevaerelse - "
                        "saa har reglen aendret sig, og skelnen her er foraeldet"
                    )
            finally:
                reset_user_present(tok_p)
        finally:
            reset_autonomous(token)
            _clear_origin()


def test_visible_run_ignores_origin_grants():
    from core.tools.autonomous_tool_policy import is_allowed

    token = set_autonomous(False)
    try:
        assert is_allowed("bash") is True
        assert is_allowed("send_discord_dm") is True
    finally:
        reset_autonomous(token)
        _clear_origin()


# ── Indbakkens udvej (12/10-2026) ────────────────────────────────────────
#
# Målt: `inbox_gate` frigives KUN af `inbox_done`/`inbox_drop` på dens poster
# — og `_prepare_call` tjekker DENNE politik FØR gaten. Var de to ikke i
# bund-sættet, var gaten en fælde: runnet kunne se posten, men aldrig lukke
# den, og dermed heller ikke mutere resten af runnet. 12/10 blev en
# recurring-brief blokeret og kunne ikke frigives.
#
# LÆSNINGEN blev lukket 14/10-2026. Indbakken er principalens kontrolflade —
# et autonomt run der læste den begyndte at arbejde på Bjørns poster og skrev
# konklusionen i en session ingen læser. Udvejen består UDEN den: gatens
# nægtelse NAVNGIVER de id'er der skal lukkes (`inbox_gate._naegtelse`), så
# runnet ikke behøver se listen for at komme fri.

def test_autonomt_run_kan_lukke_sine_egne_indbakke_poster():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("")  # bund-sættet alene: ingen delegeret udvidelse
    try:
        assert is_allowed("inbox_done") is True
        assert is_allowed("inbox_drop") is True
        # Udvejen maa ikke aabne mere end noedvendigt: runnet kan stadig ikke
        # sende eller skrive.
        assert is_allowed("write_file") is False
        assert is_allowed("send_discord_dm") is False
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_LAESNINGEN_af_indbakken_er_lukket_i_ALLE_autonome_origins():
    """14/10-2026: indbakken er den flade hvor Jarvis MØDER Bjørn — den kan
    nægte en mutation, og den læses der hvor nogen kan svare.

    Målt samme dag: et autonomt run kaldte `inbox` fem gange og begyndte at
    arbejde på Bjørns poster («Wakeup'en beder om en konkret måling … jeg
    henter indbakke-konteksten»). Konklusionen endte i en session ingen læser.
    29 af 45 sessioner på en uge var autonome.

    Ingen origin må genåbne den — heller ikke en delegeret udvidelse.
    """
    from core.tools.autonomous_tool_policy import (
        allowed_tools_for_origin, is_allowed,
    )

    for origin in ("", "wakeup", "recurring", "heartbeat", "dream", "inbox"):
        token = _as_origin(origin)
        try:
            assert is_allowed("inbox") is False, f"inbox slipper ind via {origin!r}"
            assert "inbox" not in allowed_tools_for_origin(origin), origin
        finally:
            reset_autonomous(token)
            _clear_origin()

    # Modprøven: udvejen står stadig, i bund-sættet.
    assert "inbox_done" in allowed_tools_for_origin("")
    assert "inbox_drop" in allowed_tools_for_origin("")


def test_autonom_udfoerelsesvej_slipper_inbox_done_igennem():
    """Fælden ende-til-ende: `_prepare_call` svarede `gate_blocked` med
    gate_type `autonomous_tool_policy` på `inbox_done` — altså blev runnet
    nægtet netop det værktøj der kunne frigive det."""
    from core.services.simple_tool_executor import _prepare_call

    call = {"function": {"name": "inbox_done", "arguments": {"id": "wake-x"}}}
    token = set_autonomous(True)
    try:
        kind, payload = _prepare_call(
            call, force=True, run_id="autonomous-test", session_id="auto-test",
            user_message="", controller=None, round_seen=set(), user_present=False,
        )
    finally:
        reset_autonomous(token)
    assert kind == "run", f"inbox_done blev afvist: {payload}"
