"""Et autonomt run skal kunne ses af den det handler om.

24/9-2026, Bjørn: «hvorfor ser jeg ikke hans drømme-sessioner i hans autonome
runs?» Drømmene kørte hver eneste dag — 3468 beskeder — men sessionslisten
viser kun en session hvis mindst én besked bærer den spørgendes `user_id`
(privatlivs-værnet mod at se andres samtaler). Drømmenes beskeder bar ingen.

Kontrasten der afslørede det, målt på CT105:

    auto-recurring-   8859 beskeder   user_id = 1246415163603816499  → ses
    auto-dream-       3468 beskeder   user_id = tom                  → ses ikke
    auto-heartbeat-   2287 beskeder   user_id = tom                  → ses ikke
    auto-wakeup-      2779 beskeder   user_id = tom                  → ses ikke

`auto-recurring` virkede kun fordi `scheduled_tasks` selv binder
`user_context` før den fyrer. Rettelsen bor derfor i den fælles tragt.
"""
from __future__ import annotations



def _fyr_autonomt_run(monkeypatch, *, ejer: str = "ejer-42"):
    """Kør `start_autonomous_run` uden at starte en tråd, og fang hvem der var
    bundet PRÆCIS da konteksten blev kopieret ind i tråden.

    Det er det eneste øjeblik der betyder noget: er ejeren ikke bundet dér, er
    kopien tom, beskederne skrives ustemplet, og sessionen er usynlig.

    En kilde-vagt duer ikke her. Første udgave af denne test greppede efter
    strengen «bind_context_if_unset», og da jeg muterede selve kaldet væk,
    bestod den stadig — navnet stod jo i import-linjen. Se
    `source_guards_need_ast`.
    """
    import contextvars
    import threading

    from core.identity import workspace_context as wc
    from core.services import visible_runs

    set_ved_kopiering: dict[str, str] = {}
    aegte_copy = contextvars.copy_context

    def _spion():
        set_ved_kopiering["uid"] = wc.current_user_id()
        return aegte_copy()

    monkeypatch.setattr(contextvars, "copy_context", _spion)
    monkeypatch.setattr(threading, "Thread",
                        lambda **kw: type("T", (), {"start": lambda s: None})())
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: ejer)

    visible_runs.start_autonomous_run("hej", session_id="test-session", origin="dream")
    return set_ved_kopiering.get("uid", ""), wc.current_user_id()


def test_ejeren_er_bundet_naar_traadens_kontekst_tages(monkeypatch) -> None:
    """Kernen: uden dette er drømmenes beskeder ustemplede og sessionen usynlig."""
    ved_kopiering, _ = _fyr_autonomt_run(monkeypatch)
    assert ved_kopiering == "ejer-42", (
        f"ingen ejer bundet da konteksten blev kopieret (fik {ved_kopiering!r}) — "
        f"turens beskeder får tom user_id og sessionen kan aldrig vises"
    )


def test_bindingen_smitter_ikke_paa_kalderen(monkeypatch) -> None:
    """Kalderens egen kontekst må ikke bære ejeren videre efter kaldet."""
    _, efter = _fyr_autonomt_run(monkeypatch)
    assert efter != "ejer-42", "ejer-bindingen lækkede ud i kalderens kontekst"


def test_en_eksplicit_bruger_overskrives_ikke(monkeypatch) -> None:
    """Et run bundet til en anden bruger forbliver hendes.

    `bind_context_if_unset` er valgt netop fordi discord_gateway binder
    Michelle før den fyrer. Ville vi binde ejeren ubetinget, ville hendes
    beskeder blive stemplet som hans.
    """
    from core.identity import workspace_context as wc

    token = wc.set_context(workspace_name="michelle", user_id="michelle-123")
    try:
        assert wc.bind_context_if_unset(user_id="bjorn-999") is None
        assert wc.current_user_id() == "michelle-123"
    finally:
        wc.reset_context(token)


def test_ejeren_findes_ogsaa_naar_kun_users_json_har_ham(monkeypatch) -> None:
    """`owner_user_id` må ikke give op fordi DB-tabellen mangler ejeren.

    Målt på CT105: `users`-tabellen har 14 rækker, alle `role='member'`, og
    Bjørns id står slet ikke i den. Han står som `owner` i `users.json`. Et
    opslag der kun spørger tabellen finder ingen ejer — og det var derfor
    HVER «Ny version er klar» forsvandt: `notifikations_emittere.system()`
    returnerer uden at skrive når ejeren er ukendt. Nul release-rækker fra
    0.6.43 til 0.6.94.
    """
    from core.identity import owner_resolver

    class _FalskBruger:
        role = "owner"
        discord_id = "1246415163603816499"

    def _tom_db():
        raise RuntimeError("ingen users-tabel her")

    monkeypatch.setattr("core.runtime.db.connect", lambda *a, **k: _tom_db())
    monkeypatch.setattr("core.identity.users.load_users", lambda: [_FalskBruger()])

    assert owner_resolver.owner_user_id() == "1246415163603816499"


def test_systemnotifikationen_tier_ikke_naar_ejeren_mangler(monkeypatch) -> None:
    """Kan ejeren ikke findes, skal det LOGGES.

    Før returnerede `_owner_id()` bare None, og `system()` gik videre uden at
    skrive. Der var intet spor nogen steder — den eneste måde at opdage det på
    var at tælle rækker i databasen og undre sig over at der var nul.
    """
    from core.services import notifikations_emittere as ne

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "")
    advarsler: list[str] = []
    monkeypatch.setattr(ne._log, "warning",
                        lambda msg, *a, **k: advarsler.append(str(msg)))

    assert ne._owner_id() is None
    assert advarsler, "ingen ejer fundet — og intet blev logget"
    assert "ejer" in advarsler[0].lower()
