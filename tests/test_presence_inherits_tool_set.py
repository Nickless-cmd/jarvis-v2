"""En vækning i Bjørns samtale arver den sessions værktøjssæt.

Baggrund (Bjørn 19/10-2026): «en autonom vækning i en tilstedeværelse-session
bør arve den igangværende sessions permissions og tool-sæt — det er en vækning,
ikke et autonomt baggrunds-run».

Målt før rettelsen: værktøjssættet blev valgt af kørslens ``origin``, ikke af
sessionen. ``origin="inbox"`` (den vej en session-rutine vækker mig) faldt
tilbage til bund-sættet: 104 værktøjer, hverken ``bash``, ``web_search`` eller
``notify_user``. Svaret landede stadig i Bjørns samtale — det var tandløst.

To ting måles her, og de er lige vigtige:

1. Tilstedeværelse GIVER sættet — ellers er rettelsen virkningsløs.
2. Fravær af tilstedeværelse beholder spærringen — ellers har vi åbnet en dør
   for baggrunds-runs, og det er en sikkerhedsregression, ikke en forbedring.
"""
from __future__ import annotations

import pytest

from core.services.run_autonomy_context import (
    reset_autonomous,
    reset_user_present,
    set_autonomous,
    set_run_identity,
    set_user_present,
    user_present,
)


class _Run:
    """Minimal run — kun de felter politikken læser."""

    def __init__(self, *, session_id="", origin="", autonomous=True):
        self.session_id = session_id
        self.origin = origin
        self.autonomous = autonomous
        self.run_id = "visible-test"


# ── 1. Session-klassifikationen ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "session_id,forventet",
    [
        ("auto-recurring-20261019", True),
        ("auto-heartbeat-20261019", True),
        ("dreaming-20261019-120000", True),
        ("autonomous-abc", True),
        ("chat-e82192b29646453aaf688e2043e43d89", False),
        ("discord-1234", False),
        ("", False),
        (None, False),
    ],
)
def test_system_session_skelner_silo_fra_samtale(session_id, forventet):
    from core.services.autonomous_sessions import is_system_session

    assert is_system_session(session_id) is forventet


# ── 2. presence_for_run: sessionen først, oprindelsen aldrig ─────────────────


def test_presence_kraever_en_samtale_ikke_en_silo(monkeypatch):
    from core.tools.autonomous_tool_policy import presence_for_run

    # Selv hvis nogen TALTE i siloen, er den ikke et sted nogen sidder.
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    silo = _Run(session_id="auto-recurring-20261019", origin="recurring")
    assert presence_for_run(silo) is False


def test_presence_kraever_at_han_faktisk_har_talt_der(monkeypatch):
    """En app-session der ikke er rørt i timer er en gammel række, ikke et menneske."""
    from core.tools.autonomous_tool_policy import presence_for_run

    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: False,
    )
    gammel = _Run(session_id="chat-gammel", origin="wakeup")
    assert presence_for_run(gammel) is False


def test_presence_naar_han_er_i_samtalen(monkeypatch):
    from core.tools.autonomous_tool_policy import presence_for_run

    # Kanal-beviset er en DB-læsning. Kæde-testen måler LOGIKKEN; den ægte
    # klassifikation måles i `test_en_ekstern_kanal_aabner_ikke_saettet`, som er
    # markeret `real_db`. Uden denne linje rammer testen en tom shield-DB og
    # består (eller fejler) af den forkerte grund.
    monkeypatch.setattr(
        "core.identity.owner_resolver.is_owner_app_session", lambda _s: True,
    )
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    live = _Run(session_id="chat-e82192b29646453aaf688e2043e43d89", origin="inbox")
    assert presence_for_run(live) is True


def test_presence_uden_session_er_fail_closed():
    from core.tools.autonomous_tool_policy import presence_for_run

    assert presence_for_run(_Run(session_id="", origin="wakeup")) is False


def test_ukendt_session_aabner_ikke_saettet(monkeypatch):
    """FAIL-OPEN'EN DER BLEV LUKKET (19/10-2026).

    Før spurgte vi `session_is_external_channel`, som ved tvivl svarer «ikke
    ekstern» — den er fail-OPEN med vilje, fordi den bruges til at ROUTE en
    besked. Brugt som tilstedeværelses-bevis betød det at en session der ikke
    kunne slås op blev behandlet som Bjørns egen app-samtale.

    Målt i drift: `parse_channel_from_session_title(None)` giver
    `("webchat", None)`, så fraværet af svar blev læst som et ja. Her er
    historik-læseren tvunget til «han skrev lige», så kanal-beviset er det
    ENESTE der holder — og det skal holde.
    """
    from core.tools.autonomous_tool_policy import presence_for_run

    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    ukendt = _Run(session_id="chat-findes-ikke-1234567890", origin="wakeup")
    assert presence_for_run(ukendt) is False


def test_krypteret_medlems_samtale_aabner_ikke_saettet(monkeypatch):
    """En `enc:v1:`-titel er en MEDLEMS-session — ikke Bjørns.

    `chat_crypto`: «hverken Bjørn eller Jarvis må kunne læse andres private
    sessioner». En wakeup routet dertil må ikke operere med hans rettigheder.
    """
    from core.tools.autonomous_tool_policy import presence_for_run

    monkeypatch.setattr(
        "core.identity.owner_resolver.is_owner_app_session", lambda _s: False,
    )
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    medlem = _Run(session_id="chat-19d9fc4151b346e", origin="wakeup")
    assert presence_for_run(medlem) is False


@pytest.mark.real_db
@pytest.mark.parametrize(
    "sid",
    [
        # Ægte rækker målt 19/10-2026 mod den levende base.
        "chat-e82192b29646453aaf688e2043e43d89",   # hans egen app-samtale
        "chat-19d9fc4151b346e",                    # enc:v1: — medlems-session
        "auto-recurring-20261019",                 # autonom silo
        "chat-findes-ikke-1234567890",             # findes ikke
    ],
)
def test_kanal_beviset_mod_den_aegte_base(sid):
    """Klassifikationen selv — målt mod den levende DB, ikke en shield-fil.

    `real_db` er nødvendig: uden den peger `_guard_prod_db_path` på en tom
    DB, `SELECT title` finder intet, og ALLE cases ville svare False — også
    hans egen samtale. Så var testen grøn af den forkerte grund.
    """
    from core.identity.owner_resolver import is_owner_app_session

    svar = is_owner_app_session(sid)
    if sid == "chat-e82192b29646453aaf688e2043e43d89":
        assert svar is True, "hans egen app-samtale skal bevises"
    else:
        assert svar is False, f"{sid} må ikke åbne sættet"


def test_presence_kaaster_aldrig(monkeypatch):
    """En brækket historik-læsning må ikke åbne sættet — den skal lukke det."""
    from core.tools.autonomous_tool_policy import presence_for_run

    def _boom(_s):
        raise RuntimeError("historikken kunne ikke læses")

    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", _boom,
    )
    assert presence_for_run(_Run(session_id="chat-x", origin="wakeup")) is False


# ── 2b. Kun hans EGEN app-samtale tæller (Bjørn 19/10-2026) ─────────────────


@pytest.mark.real_db
@pytest.mark.parametrize(
    "sid",
    [
        # Ægte sessioner fra DB (målt 19/10-2026): titlen bærer kanalen, ikke
        # id'et. `chat-…` er også Discord — præfikset lyver, titlen gør ikke.
        #
        # `real_db` er nødvendig: uden den peger `_guard_prod_db_path` på en tom
        # shield-DB, `get_chat_session` finder ingen titel, og klassifikationen
        # falder tilbage til «ikke ekstern». Testen ville da bestå af den
        # forkerte grund — den skulle måle virkeligheden, ikke en tom base.
        "chat-4fa3d42f08f946d0966e9d5d11303d21",  # "Discord DM — 1246415163603816499"
        "chat-4b20d15a71ed40c0be31f9db5740c5f9",  # "Telegram DM"
        "chat-fcf35d02d59c401b9c7159610ff5595d",  # "Discord DM"
    ],
)
def test_en_ekstern_kanal_er_ikke_tilstedevaerelse(monkeypatch, sid):
    """Han kan have talt der for et minut siden — det gør ikke kanalen til ham.

    En wakeup routet hertil ville ellers operere med hans rettigheder
    (`bash`, `operator_bash`, `write_file`) foran et publikum.
    """
    from core.tools.autonomous_tool_policy import presence_for_run

    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    assert presence_for_run(_Run(session_id=sid, origin="wakeup")) is False


def test_hans_egen_app_samtale_er_stadig_tilstedevaerelse(monkeypatch):
    """Grænsen må ikke ramme den samtale den blev bygget for."""
    from core.tools.autonomous_tool_policy import presence_for_run

    monkeypatch.setattr(
        "core.identity.owner_resolver.is_owner_app_session", lambda _s: True,
    )
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    app = _Run(session_id="chat-e82192b29646453aaf688e2043e43d89", origin="inbox")
    assert presence_for_run(app) is True


def test_en_ekstern_kanal_aabner_ikke_saettet(monkeypatch):
    """Kontrakten målt på politikken, ikke kun på hjælpefunktionen.

    Måler de værktøjer der KUN kommer fra tilstedeværelse. `bash` og
    `web_search` er bevidst ikke med: `wakeup`-origin har dem allerede i
    `ORIGIN_TOOLS`, så de siger intet om hvorvidt KANALEN åbnede sættet.

    (27/10-2026: `web_search` blev føjet til `wakeup`/`inbox`-originens sæt
    26/10 fordi inbox-vækkeren ellers svarede «jeg har ikke adgang til tools».
    Denne test listede den dengang som tilstedeværelses-bevis og fejlede
    derfor — af den forkerte grund. Grænsen selv var intakt: målt uden
    tilstedeværelse slipper kun originens egne værktøjer igennem.)
    """
    from core.tools.autonomous_tool_policy import is_allowed, presence_for_run

    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel",
        lambda sid: str(sid or "").startswith("discord-"),
    )

    assert presence_for_run(_Run(session_id="discord-1234", origin="wakeup")) is False

    tok_a = set_autonomous(True)
    set_run_identity("visible-test", "wakeup")
    tok_p = set_user_present(False)
    try:
        for navn in (
            "operator_bash", "write_file", "edit_file", "notify_user",
            "dispatch_agent", "send_discord_dm",
        ):
            assert is_allowed(navn) is False, navn
    finally:
        reset_user_present(tok_p)
        reset_autonomous(tok_a)


def test_en_brækket_kanal_klassifikation_lukker(monkeypatch):
    """Kan vi ikke afgøre om det er en ekstern kanal, må svaret være nej."""
    from core.tools.autonomous_tool_policy import presence_for_run

    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )

    def _boom(_sid):
        raise RuntimeError("titlen kunne ikke læses")

    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel", _boom,
    )
    assert presence_for_run(_Run(session_id="chat-x", origin="wakeup")) is False


# ── 3. Politikken: gaten der faktisk afgør ──────────────────────────────────


def test_autonom_uden_tilstedevaerelse_er_stadig_spaerret():
    """Regressionen der ikke må ske: baggrunds-runs må ikke få sættet."""
    from core.tools.autonomous_tool_policy import is_allowed

    tok_a = set_autonomous(True)
    set_run_identity("visible-test", "inbox")
    tok_p = set_user_present(False)
    try:
        # `bash` og `web_search` er IKKE med: `inbox`-originens eget sæt
        # tildeler dem (26/10-2026), så de måler ikke tilstedeværelse.
        for navn in (
            "write_file", "edit_file", "notify_user", "operator_bash",
            "dispatch_agent", "send_discord_dm",
        ):
            assert is_allowed(navn) is False, navn
    finally:
        reset_user_present(tok_p)
        reset_autonomous(tok_a)


def test_tilstedevaerelse_giver_hele_saettet():
    from core.tools.autonomous_tool_policy import is_allowed

    tok_a = set_autonomous(True)
    set_run_identity("visible-test", "inbox")
    tok_p = set_user_present(True)
    try:
        for navn in ("web_search", "write_file", "notify_user", "bash", "dispatch_agent"):
            assert is_allowed(navn) is True, navn
    finally:
        reset_user_present(tok_p)
        reset_autonomous(tok_a)


def test_almindelig_brugertur_er_upaa_virket():
    from core.tools.autonomous_tool_policy import is_allowed

    tok_a = set_autonomous(False)
    try:
        assert is_allowed("web_search") is True
        assert is_allowed("dispatch_agent") is True
    finally:
        reset_autonomous(tok_a)


# ── 4. Kataloget, ikke kun udførslen ────────────────────────────────────────


def test_kataloget_foelger_tilstedevaerelsen():
    """Modellen skal SE værktøjerne — ikke bare få dem afvist ved brug."""
    from core.tools.simple_tools import get_tool_definitions

    tok_a = set_autonomous(True)
    set_run_identity("visible-test", "inbox")
    try:
        tok_p = set_user_present(False)
        uden = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
        reset_user_present(tok_p)

        tok_p = set_user_present(True)
        med = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
        reset_user_present(tok_p)
    finally:
        reset_autonomous(tok_a)

    # `write_file` er tilstedeværelses-beviset: den findes hverken i
    # `AUTONOMOUS_TOOLS` eller i `inbox`-originens sæt. `web_search` blev
    # flyttet til originens sæt 26/10-2026 og kan derfor ikke bruges her.
    assert "write_file" not in uden
    assert "write_file" in med
    assert len(med) > len(uden)


# ── 5. _bruger_til_stede: godkendelses-gaten ────────────────────────────────


def test_vaekning_i_hans_samtale_har_et_menneske(monkeypatch):
    from core.services.visible_tool_exec import _bruger_til_stede

    monkeypatch.setattr(
        "core.identity.owner_resolver.is_owner_app_session", lambda _s: True,
    )
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    run = _Run(session_id="chat-e82192b29646453aaf688e2043e43d89", origin="wakeup")
    assert _bruger_til_stede(run) is True


def test_vaekning_i_en_silo_har_intet_menneske(monkeypatch):
    from core.services.visible_tool_exec import _bruger_til_stede

    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    run = _Run(session_id="auto-recurring-20261019", origin="recurring")
    assert _bruger_til_stede(run) is False


def test_godkendelses_gaten_er_levende_naar_han_er_der():
    """`force` må ikke omgå godkendelser når der ER nogen til at svare.

    Uden dette led arvede kørslen rettighederne uden at arve spørgsmålet.
    """
    from core.services.visible_tool_exec import _bruger_til_stede

    run = _Run(session_id="chat-x", origin="wakeup")
    tok_p = set_user_present(True)
    try:
        tilstede = _bruger_til_stede(run)
    finally:
        reset_user_present(tok_p)

    # Formlen fra visible_tool_exec — samme udtryk, målt direkte.
    assert (run.autonomous and not tilstede) is False


def test_konteksten_nulstilles_mellem_koersler():
    """Executor-tråde genbruges: tilstedeværelse må ikke lække videre."""
    tok = set_user_present(True)
    assert user_present() is True
    reset_user_present(tok)
    assert user_present() is False


# ── 2c. EJERSKABS-BEVISET (Bjørn 19/10-2026) ───────────────────────────────
#
# «Giv sessioner et ejerskabs-bevis i stedet for kanal-gæt.»
#
# Testene her bygger deres EGEN base i stedet for at læse de levende
# sessioner. Det er med vilje: en hardkodet session kan ændre sig, og en
# `real_db`-test kan ikke skelne «reglen virker» fra «rækken findes
# tilfældigvis». Her er hver række noget testen selv lagde der.


def _base(tmp_path, monkeypatch):
    """Egen DB med skemaet — så hvert eneste svar er testens eget."""
    import core.runtime.db as db
    import core.runtime.db_core as db_core

    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "ejerskab.db")
    db.init_db()
    return db


def _session(conn, sid: str, title: str) -> None:
    conn.execute(
        "INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
        "VALUES (?, ?, '2026-10-19T12:00:00+00:00', '2026-10-19T12:00:00+00:00')",
        (sid, title),
    )


def _besked(conn, sid: str, user_id: str, i: int) -> None:
    conn.execute(
        "INSERT INTO chat_messages (message_id, session_id, role, content, "
        "created_at, user_id) VALUES (?, ?, 'user', 'hej', ?, ?)",
        (f"{sid}-{i}", sid, f"2026-10-19T12:0{i}:00+00:00", user_id),
    )


def test_kun_hans_egen_samtale_bevises(tmp_path, monkeypatch):
    """Kernen i beviset: hans id — og INGEN andres."""
    from core.identity.owner_resolver import is_owner_app_session, owner_user_id

    db = _base(tmp_path, monkeypatch)
    ejer = owner_user_id()
    assert ejer, "testen kræver en kendt ejer"

    with db.connect() as c:
        _session(c, "s-kun-ham", "en almindelig titel")
        _besked(c, "s-kun-ham", ejer, 1)

        _session(c, "s-ingen-beskeder", "en almindelig titel")

        _session(c, "s-kun-andre", "en almindelig titel")
        _besked(c, "s-kun-andre", "en-fremmed-bruger", 1)

        # Den farlige: begge har talt her. Et rent «har han skrevet?» ville
        # åbne den — målt 19/10-2026 i seks levende sessioner.
        _session(c, "s-delt", "en almindelig titel")
        _besked(c, "s-delt", ejer, 1)
        _besked(c, "s-delt", "en-fremmed-bruger", 2)

    assert is_owner_app_session("s-kun-ham") is True
    assert is_owner_app_session("s-ingen-beskeder") is False
    assert is_owner_app_session("s-kun-andre") is False
    assert is_owner_app_session("s-delt") is False, (
        "en delt samtale må ikke åbnes af et tilstedeværelses-bevis"
    )


def test_tomt_user_id_hverken_hjaelper_eller_blokerer(tmp_path, monkeypatch):
    """877 rækker i den levende base har intet stempel — de er ældre, ikke fremmede."""
    from core.identity.owner_resolver import is_owner_app_session, owner_user_id

    db = _base(tmp_path, monkeypatch)
    ejer = owner_user_id()
    with db.connect() as c:
        _session(c, "s-blandet-tom", "titel")
        _besked(c, "s-blandet-tom", ejer, 1)
        _besked(c, "s-blandet-tom", "", 2)

    assert is_owner_app_session("s-blandet-tom") is True


def test_krypteret_medlems_session_lukkes_ogsaa_uden_beskeder(tmp_path, monkeypatch):
    """Krypterings-leddet skal holde selvstændigt, ikke kun via ejer-stemplet."""
    from core.identity.owner_resolver import is_owner_app_session

    db = _base(tmp_path, monkeypatch)
    with db.connect() as c:
        _session(c, "s-medlem", "enc:v1:60UhWQs6Nu2MlruEKA4CGA0")

    assert is_owner_app_session("s-medlem") is False


# ── VÆKNING vs. BAGGRUNDS-RUN (19/10-2026) ──────────────────────────────────
#
# Målt i drift: en session-rutine fyrer kl. 07, hvor Bjørn ikke har skrevet
# siden aftenen før. `_bruger_skrev_for_nylig` svarede False, så morgenmedicinen
# landede i hans samtale UDEN `write_file`, `edit_file` og `inbox` — kun med
# `bash` og `web_search`, som kommer fra `recurring`-originens eget sæt.
#
# Friskhedskravet var dermed døden for præcis det tilfælde grænsen blev bygget
# til. Skelnen er hvad kørslen ER: en vækning efterlader et svar han kan læse;
# et baggrunds-run har intet svar at efterlade.


def _klassifikation(monkeypatch, *, hans=True):
    """Gør kanal- og ejerskabs-beviset til et konstant svar (ingen DB)."""
    monkeypatch.setattr(
        "core.identity.owner_resolver.is_owner_app_session", lambda _s: hans,
    )
    monkeypatch.setattr(
        "core.services.autonomous_sessions.is_system_session", lambda _s: False,
    )


@pytest.mark.parametrize("origin", ["wakeup", "recurring", "inbox"])
def test_en_vaekning_arver_uden_friskhed(monkeypatch, origin):
    """Kernen i Bjørns pointe: det er en vækning, ikke et baggrunds-run."""
    from core.tools.autonomous_tool_policy import presence_for_run

    _klassifikation(monkeypatch)
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: False,
    )
    assert presence_for_run(_Run(session_id="chat-live", origin=origin)) is True


@pytest.mark.parametrize("origin", ["heartbeat", "dream", "autonomous", ""])
def test_et_baggrunds_run_kraever_at_han_er_der_nu(monkeypatch, origin):
    """Regressionen: et run uden et svar at efterlade må ikke arve sættet.

    ``set_run_identity("", "")`` rydder ContextVar'en: med en tom ``origin``
    falder politikken tilbage til ``current_origin()``, og uden oprydning læste
    testen en lækket værdi fra en tidligere test — den bestod af den forkerte
    grund i stedet for at måle faldbacken.
    """
    from core.tools.autonomous_tool_policy import presence_for_run

    _klassifikation(monkeypatch)
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: False,
    )
    set_run_identity("", "")
    assert presence_for_run(_Run(session_id="chat-live", origin=origin)) is False


def test_baggrunds_run_arver_stadig_naar_han_er_der(monkeypatch):
    """Friskhedskravet er ikke fjernet — det gælder stadig hvor det passer."""
    from core.tools.autonomous_tool_policy import presence_for_run

    _klassifikation(monkeypatch)
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    assert presence_for_run(_Run(session_id="chat-live", origin="heartbeat")) is True


def test_vaekning_i_fremmed_samtale_arver_ikke(monkeypatch):
    """Vækning eller ej: kanalen skal stadig være BEVIST hans egen."""
    from core.tools.autonomous_tool_policy import presence_for_run

    _klassifikation(monkeypatch, hans=False)
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    assert presence_for_run(_Run(session_id="chat-fremmed", origin="wakeup")) is False


def test_vaekning_i_en_silo_arver_ikke(monkeypatch):
    """En auto-silo er ikke et sted nogen sidder — uanset oprindelsen."""
    from core.tools.autonomous_tool_policy import presence_for_run

    monkeypatch.setattr(
        "core.identity.owner_resolver.is_owner_app_session", lambda _s: True,
    )
    monkeypatch.setattr(
        "core.services.autonomous_sessions.is_system_session",
        lambda s: str(s).startswith("auto-"),
    )
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: True,
    )
    assert presence_for_run(
        _Run(session_id="auto-recurring-20261019", origin="recurring")
    ) is False
